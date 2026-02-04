"""
Chat Service - Orchestrates chat interactions between user, LLM, and tools.
Handles message processing, tool execution, and UI generation.

Enhanced with message preprocessing pipeline for entity extraction and context management.

Error Handling:
- All exceptions are caught at the orchestration level
- Errors are converted to appropriate ChatAppError subclasses
- Safe, user-friendly error responses are always returned
- All errors are logged with correlation IDs for tracing
"""
import logging
import time
from typing import Dict, Any
from django.conf import settings
from django.template.loader import render_to_string

from chat_app.utils.llm_logger import (
    get_llm_logger,
    create_correlation_id,
    CorrelationContext
)
from chat_app.utils.context_manager import get_context_manager
from chat_app.exceptions import (
    ChatAppError,
    LLMError,
    APIError,
    APIServerError,
    APIClientError,
    ValidationError,
    ContextError,
)
from chat_app.utils.error_handler import (
    create_error_response,
    generate_error_ui,
    log_error,
)

logger = logging.getLogger(__name__)
llm_logger = get_llm_logger()


def get_llm_service():
    """
    Factory function to get appropriate LLM service based on configuration.
    Returns mock service in Phase 1, real LLM service in Phase 2+.
    """
    if settings.CHAT_CONFIG.get('mock_mode', True):
        from chat_app.services.mock_llm_service import MockLLMService
        return MockLLMService()
    else:
        # Phase 2+: Import and return real LLM service
        from chat_app.services.llm_service import LLMService
        return LLMService()


class ChatService:
    """
    Main chat orchestration service.
    Coordinates between LLM, tools, and UI generation.
    """

    def __init__(self):
        """Initialize chat service with LLM service"""
        self.llm_service = get_llm_service()

    async def process_message(
        self,
        user_text: str,
        conversation_id: str,
        user,
        message_id: str = None,
        selected_row: dict = None
    ) -> Dict[str, Any]:
        """
        Process user message and return categorization with confirmation UI.

        Flow:
        1. Sanitize user input (remove threats, normalize whitespace)
        2. Format prompt (clear, compact, preserve parameters)
        3. Categorize intent with LLM
        4. Return result with UI

        Args:
            user_text: User's input message (raw)
            conversation_id: Current conversation ID
            user: Django user object
            message_id: Unique identifier for the message (optional)
            selected_row: Selected forecast row data (optional)

        Returns:
            Dictionary with category, confidence, and UI component
        """
        # Create correlation ID for tracing this request
        correlation_id = create_correlation_id(conversation_id, message_id)
        user_id = getattr(user, 'portal_id', str(user.id)) if user else 'anonymous'
        start_time = time.time()

        # Create correlation context for this request
        async with CorrelationContext(
            correlation_id=correlation_id,
            message_id=message_id,
            conversation_id=conversation_id,
            user_id=user_id
        ):
            # Log message processing start
            llm_logger.log_message_processing_start(
                correlation_id=correlation_id,
                conversation_id=conversation_id,
                user_id=user_id,
                message_type='user_message'
            )

            try:
                # STEP 1: Sanitize user input
                from chat_app.utils.input_sanitizer import get_sanitizer
                sanitizer = get_sanitizer()

                sanitized_text, sanitization_metadata = sanitizer.sanitize(user_text)

                # Log user input with sanitization details
                llm_logger.log_user_input(
                    correlation_id=correlation_id,
                    raw_input=user_text,
                    sanitized_input=sanitized_text,
                    context={'sanitization': sanitization_metadata},
                    conversation_id=conversation_id,
                    user_id=user_id
                )

                # Log sanitization results
                if sanitization_metadata['threats_detected']:
                    logger.warning(
                        f"[Chat Service] Security threats detected in user input: "
                        f"{', '.join(sanitization_metadata['threats_detected'])}"
                    )

                if sanitization_metadata['truncated']:
                    logger.info(
                        f"[Chat Service] Input truncated from "
                        f"{sanitization_metadata['original_length']} to "
                        f"{sanitization_metadata['sanitized_length']} characters"
                    )

                # If sanitized text is empty, return error
                if not sanitized_text:
                    logger.warning("[Chat Service] Sanitized text is empty")

                    llm_logger.log_error(
                        correlation_id=correlation_id,
                        error='Sanitized text is empty',
                        stage='input_sanitization',
                        context={'sanitization': sanitization_metadata}
                    )

                    return {
                        'category': 'error',
                        'confidence': 0.0,
                        'parameters': {},
                        'ui_component': self._build_error_ui(
                            "Your message could not be processed. Please try again with a different query."
                        ),
                        'metadata': {'error': 'empty_after_sanitization', 'correlation_id': correlation_id}
                    }

                # STEP 2: Preprocess message (normalize, spell-correct, entity tag)
                from chat_app.services.message_preprocessor import get_preprocessor

                # Get preprocessor (with LLM if available for entity tagging)
                preprocessor = get_preprocessor(llm=self.llm_service.llm if hasattr(self.llm_service, 'llm') else None)
                preprocessed = await preprocessor.preprocess(sanitized_text)

                logger.info(
                    f"[Chat Service] Preprocessed - entities: {list(preprocessed.extracted_entities.keys())}, "
                    f"confidence: {preprocessed.parsing_confidence:.2f}"
                )

                # STEP 3: Update context store with extracted entities
                context_manager = get_context_manager()
                await context_manager.update_from_preprocessed(conversation_id, preprocessed)

                # Log preprocessing results
                llm_logger._log(
                    logging.DEBUG,
                    'message_preprocessed',
                    {
                        'correlation_id': correlation_id,
                        'entities_extracted': list(preprocessed.extracted_entities.keys()),
                        'corrections_made': len(preprocessed.corrections_made),
                        'confidence': preprocessed.parsing_confidence,
                        'uses_previous_context': preprocessed.uses_previous_context()
                    }
                )

                # STEP 4: Get recent message history for context
                message_history = await self._get_message_history(conversation_id, limit=10)

                # STEP 5: Categorize user intent with LLM (with preprocessed input)
                # Pass the tagged text if available for better LLM understanding
                llm_input_text = preprocessed.tagged_text if preprocessed.tagged_text else sanitized_text

                result = await self.llm_service.categorize_intent(
                    user_text=llm_input_text,  # Use tagged/preprocessed text
                    conversation_id=conversation_id,
                    message_history=message_history,
                    selected_row=selected_row  # Pass selected row context
                )

                # Add preprocessing metadata to result
                if 'metadata' not in result:
                    result['metadata'] = {}
                result['metadata']['preprocessing'] = {
                    'entities_extracted': list(preprocessed.extracted_entities.keys()),
                    'corrections_made': preprocessed.corrections_made,
                    'parsing_confidence': preprocessed.parsing_confidence,
                    'uses_previous_context': preprocessed.uses_previous_context()
                }

                category = result.get('category')
                confidence = result.get('confidence')
                parameters = result.get('parameters', {})
                ui_component = result.get('ui_component')  # LLM service now generates UI

                logger.info(f"[Chat Service] Categorized as '{category}' with {confidence:.2f} confidence")

                # Add sanitization metadata to result
                result_metadata = result.get('metadata', {})
                result_metadata['sanitization'] = sanitization_metadata
                result_metadata['correlation_id'] = correlation_id

                # Log message processing complete
                total_duration_ms = (time.time() - start_time) * 1000
                llm_logger.log_message_processing_complete(
                    correlation_id=correlation_id,
                    success=True,
                    total_duration_ms=total_duration_ms,
                    category=category
                )

                return {
                    'category': category,
                    'confidence': confidence,
                    'parameters': parameters,
                    'ui_component': ui_component,
                    'metadata': result_metadata
                }

            except LLMError as e:
                # LLM-specific errors (connection, timeout, response issues)
                total_duration_ms = (time.time() - start_time) * 1000
                logger.error(f"[Chat Service] LLM error: {e.error_code}: {str(e)}", exc_info=True)

                log_error(
                    logger,
                    e,
                    context={
                        'conversation_id': conversation_id,
                        'user_id': user_id,
                        'duration_ms': total_duration_ms,
                    },
                    correlation_id=correlation_id,
                    stage='process_message'
                )

                llm_logger.log_message_processing_complete(
                    correlation_id=correlation_id,
                    success=False,
                    total_duration_ms=total_duration_ms,
                    category='llm_error'
                )

                return create_error_response(
                    error=e,
                    correlation_id=correlation_id,
                    category='llm_error'
                )

            except APIClientError as e:
                # API Client errors (4xx) - User can fix these (bad filters, missing params, no data)
                # These are NOT system failures - show user what's wrong so they can correct it
                total_duration_ms = (time.time() - start_time) * 1000
                logger.warning(f"[Chat Service] API client error: {e.error_code}: {str(e)}")

                llm_logger.log_message_processing_complete(
                    correlation_id=correlation_id,
                    success=False,
                    total_duration_ms=total_duration_ms,
                    category='api_client_error'
                )

                # Return user-friendly error with no "contact admin" message
                return {
                    'category': 'api_client_error',
                    'confidence': 0.0,
                    'parameters': {},
                    'ui_component': generate_error_ui(
                        error_type='validation',  # Use validation styling (info icon, no admin contact)
                        user_message=e.user_message,
                        admin_contact=False,  # User can fix this
                        error_code=e.error_code
                    ),
                    'metadata': {
                        'error': True,
                        'error_type': 'api_client_error',
                        'error_code': e.error_code,
                        'correlation_id': correlation_id,
                        'details': e.details,
                    }
                }

            except APIError as e:
                # API Server errors (5xx, connection, timeout) - System failure, contact admin
                total_duration_ms = (time.time() - start_time) * 1000
                logger.error(f"[Chat Service] API server error: {e.error_code}: {str(e)}", exc_info=True)

                log_error(
                    logger,
                    e,
                    context={
                        'conversation_id': conversation_id,
                        'user_id': user_id,
                        'duration_ms': total_duration_ms,
                    },
                    correlation_id=correlation_id,
                    stage='process_message'
                )

                llm_logger.log_message_processing_complete(
                    correlation_id=correlation_id,
                    success=False,
                    total_duration_ms=total_duration_ms,
                    category='api_error'
                )

                return create_error_response(
                    error=e,
                    correlation_id=correlation_id,
                    category='api_error'
                )

            except ValidationError as e:
                # Validation errors (user can fix these - no admin contact)
                total_duration_ms = (time.time() - start_time) * 1000
                logger.warning(f"[Chat Service] Validation error: {e.error_code}: {str(e)}")

                llm_logger.log_message_processing_complete(
                    correlation_id=correlation_id,
                    success=False,
                    total_duration_ms=total_duration_ms,
                    category='validation_error'
                )

                return {
                    'category': 'validation_error',
                    'confidence': 0.0,
                    'parameters': {},
                    'ui_component': generate_error_ui(
                        error_type='validation',
                        user_message=e.user_message,
                        admin_contact=False,
                        error_code=e.error_code
                    ),
                    'metadata': {
                        'error': True,
                        'error_type': 'validation',
                        'error_code': e.error_code,
                        'correlation_id': correlation_id
                    }
                }

            except ContextError as e:
                # Context/session errors
                total_duration_ms = (time.time() - start_time) * 1000
                logger.warning(f"[Chat Service] Context error: {e.error_code}: {str(e)}")

                llm_logger.log_message_processing_complete(
                    correlation_id=correlation_id,
                    success=False,
                    total_duration_ms=total_duration_ms,
                    category='context_error'
                )

                return {
                    'category': 'context_error',
                    'confidence': 0.0,
                    'parameters': {},
                    'ui_component': generate_error_ui(
                        error_type='context',
                        user_message=e.user_message,
                        admin_contact=False,
                        error_code=e.error_code
                    ),
                    'metadata': {
                        'error': True,
                        'error_type': 'context',
                        'error_code': e.error_code,
                        'correlation_id': correlation_id
                    }
                }

            except Exception as e:
                # Unexpected errors - log fully and show generic message
                total_duration_ms = (time.time() - start_time) * 1000
                logger.error(f"[Chat Service] Unexpected error: {str(e)}", exc_info=True)

                # Log error with full context
                llm_logger.log_error(
                    correlation_id=correlation_id,
                    error=e,
                    stage='process_message',
                    context={'duration_ms': total_duration_ms}
                )

                llm_logger.log_message_processing_complete(
                    correlation_id=correlation_id,
                    success=False,
                    total_duration_ms=total_duration_ms,
                    category='error'
                )

                # Return safe error response (don't expose internal errors to user)
                return {
                    'category': 'error',
                    'confidence': 0.0,
                    'parameters': {},
                    'ui_component': generate_error_ui(
                        error_type='unknown',
                        user_message="An unexpected error occurred. Please try again.",
                        admin_contact=True,
                        error_code='UNKNOWN_ERROR'
                    ),
                    'metadata': {
                        'error': True,
                        'error_type': 'unknown',
                        'correlation_id': correlation_id
                    }
                }

    async def execute_cph_update(
        self,
        update_data: dict,
        conversation_id: str,
        user
    ) -> Dict[str, Any]:
        """
        Execute the confirmed CPH update.
        Note: Actual API call is stubbed - backend API is in planning phase.

        Args:
            update_data: CPH update data including old/new values and row info
            conversation_id: Current conversation ID
            user: Django user object

        Returns:
            Dictionary with success status and message
        """
        try:
            logger.info(f"[Chat Service] CPH Update requested: {update_data}")

            # Extract update details for logging
            main_lob = update_data.get('main_lob', 'N/A')
            state = update_data.get('state', 'N/A')
            old_cph = update_data.get('old_cph', 0)
            new_cph = update_data.get('new_cph', 0)

            # TODO: When API is ready, call:
            # result = await self.llm_service.submit_cph_update(update_data)

            # For now, return success with note about API status
            ui_component = f"""
            <div class="update-success-card">
                <div class="success-icon">✓</div>
                <div class="success-message">
                    <strong>Update Recorded</strong>
                    <p>CPH changed from {old_cph} to {new_cph}
                    for {main_lob} - {state}</p>
                    <small class="text-muted">Note: Backend API integration pending</small>
                </div>
            </div>
            """

            return {
                'success': True,
                'message': 'CPH update recorded. Note: Backend update API is in planning phase.',
                'ui_component': ui_component
            }

        except Exception as e:
            logger.error(f"[Chat Service] Error in execute_cph_update: {e}")
            return {
                'success': False,
                'message': f'Failed to update CPH: {str(e)}',
                'ui_component': ''
            }

    async def _get_message_history(self, conversation_id: str, limit: int = 10) -> list:
        """
        Get recent message history from database.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to retrieve

        Returns:
            List of message dictionaries with role and content
        """
        from chat_app.models import ChatMessage, ChatConversation
        from channels.db import database_sync_to_async

        @database_sync_to_async
        def get_messages():
            try:
                conversation = ChatConversation.objects.get(id=conversation_id)
                messages = ChatMessage.objects.filter(
                    conversation=conversation
                ).order_by('-created_at')[:limit]

                # Reverse to get chronological order
                return [
                    {
                        'role': msg.role,
                        'content': msg.content
                    }
                    for msg in reversed(messages)
                ]
            except ChatConversation.DoesNotExist:
                logger.warning(f"Conversation {conversation_id} not found")
                return []
            except Exception as e:
                logger.error(f"Error retrieving message history: {str(e)}")
                return []

        return await get_messages()

    async def execute_confirmed_action(self, category: str, parameters: Dict[str, Any],
                                       conversation_id: str, user) -> Dict[str, Any]:
        """
        Execute confirmed action and return results with UI.

        Args:
            category: Confirmed category
            parameters: Extracted parameters
            conversation_id: Current conversation ID
            user: Django user object

        Returns:
            Dictionary with success status, data, and UI component
        """
        try:
            # Handle new Phase 2 categories with LLM service
            if category == 'get_forecast_data':
                return await self.llm_service.execute_forecast_query(
                    parameters=parameters,
                    conversation_id=conversation_id
                )
            elif category == 'list_available_reports':
                return await self.llm_service.execute_available_reports_query(
                    parameters=parameters,
                    conversation_id=conversation_id
                )
            # Legacy Phase 1 categories (mock mode)
            elif category == 'forecast_query':
                return self._handle_forecast_query(parameters)
            elif category == 'roster_query':
                return self._handle_roster_query(parameters)
            elif category == 'execution_status':
                return self._handle_execution_status(parameters)
            elif category == 'ramp_query':
                return self._handle_ramp_query(parameters)
            else:
                return {
                    'success': False,
                    'message': f"Unknown category: {category}",
                    'ui_component': self._build_error_ui(f"Cannot handle category: {category}")
                }

        except LLMError as e:
            logger.error(f"[Chat Service] LLM error in execute_confirmed_action: {str(e)}", exc_info=True)
            return create_error_response(error=e, category='llm_error')

        except APIClientError as e:
            # API Client errors (4xx) - User can fix (bad filters, no data for criteria)
            logger.warning(f"[Chat Service] API client error in execute_confirmed_action: {str(e)}")
            return {
                'success': False,
                'message': e.user_message,
                'ui_component': generate_error_ui(
                    error_type='validation',  # Use validation styling
                    user_message=e.user_message,
                    admin_contact=False,  # User can fix
                    error_code=e.error_code
                ),
                'metadata': {'error': True, 'error_code': e.error_code, 'error_type': 'api_client_error'}
            }

        except APIError as e:
            # API Server errors (5xx, connection) - System issue
            logger.error(f"[Chat Service] API server error in execute_confirmed_action: {str(e)}", exc_info=True)
            return create_error_response(error=e, category='api_error')

        except ValidationError as e:
            logger.warning(f"[Chat Service] Validation error in execute_confirmed_action: {str(e)}")
            return {
                'success': False,
                'message': e.user_message,
                'ui_component': generate_error_ui(
                    error_type='validation',
                    user_message=e.user_message,
                    admin_contact=False,
                    error_code=e.error_code
                ),
                'metadata': {'error': True, 'error_code': e.error_code}
            }

        except Exception as e:
            logger.error(f"[Chat Service] Unexpected error in execute_confirmed_action: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': "An unexpected error occurred",
                'ui_component': generate_error_ui(
                    error_type='unknown',
                    user_message="An unexpected error occurred. Please try again.",
                    admin_contact=True,
                    error_code='UNKNOWN_ERROR'
                ),
                'metadata': {'error': True}
            }

    def _handle_forecast_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle forecast data query"""
        # Get mock data
        data = self.llm_service.get_mock_forecast_data(parameters)

        # Build result UI
        ui_component = self._build_forecast_table_ui(data, parameters)

        return {
            'success': True,
            'message': f"Retrieved {len(data)} forecast records",
            'data': data,
            'ui_component': ui_component,
            'metadata': {'record_count': len(data)}
        }

    def _handle_roster_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle roster data query"""
        data = self.llm_service.get_mock_roster_data(parameters)

        ui_component = self._build_roster_table_ui(data, parameters)

        return {
            'success': True,
            'message': f"Retrieved {len(data)} roster records",
            'data': data,
            'ui_component': ui_component,
            'metadata': {'record_count': len(data)}
        }

    def _handle_execution_status(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle execution status query"""
        status = self.llm_service.get_mock_execution_status(parameters)

        ui_component = self._build_status_ui(status)

        return {
            'success': True,
            'message': f"Execution is {status['status']}",
            'data': status,
            'ui_component': ui_component,
            'metadata': status
        }

    def _handle_ramp_query(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ramp resources query"""
        # Use forecast data as placeholder for ramp
        data = self.llm_service.get_mock_forecast_data(parameters)

        ui_component = self._build_forecast_table_ui(data, parameters)

        return {
            'success': True,
            'message': f"Retrieved {len(data)} ramp records",
            'data': data,
            'ui_component': ui_component,
            'metadata': {'record_count': len(data)}
        }

    def _build_confirmation_ui(self, category: str, parameters: Dict[str, Any],
                               original_text: str) -> str:
        """
        Build HTML confirmation UI component.
        Simple confirmation card with Yes/No buttons.
        """
        # Category display names
        category_names = {
            'forecast_query': 'Forecast Data',
            'roster_query': 'Roster Data',
            'execution_status': 'Execution Status',
            'ramp_query': 'Ramp Resources',
            'unknown': 'Unknown Request'
        }

        display_name = category_names.get(category, category)

        # Build parameter summary
        param_summary = []
        if parameters.get('month'):
            month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
            param_summary.append(f"Month: {month_names[parameters['month']]}")
        if parameters.get('year'):
            param_summary.append(f"Year: {parameters['year']}")
        if parameters.get('platform'):
            param_summary.append(f"Platform: {parameters['platform']}")
        if parameters.get('market'):
            param_summary.append(f"Market: {parameters['market']}")
        if parameters.get('worktype'):
            param_summary.append(f"Worktype: {parameters['worktype']}")

        param_text = ', '.join(param_summary) if param_summary else 'All data'

        html = f"""
        <div class="chat-confirmation-card">
            <div class="confirmation-header">
                <strong>{display_name}</strong>
            </div>
            <div class="confirmation-body">
                <p>Would you like to view {display_name.lower()} with the following filters?</p>
                <div class="confirmation-parameters">
                    <small>{param_text}</small>
                </div>
            </div>
            <div class="confirmation-actions">
                <button class="btn btn-primary btn-sm chat-confirm-btn"
                        data-category="{category}"
                        data-parameters='{self._format_json_params(parameters)}'>
                    Yes, Show Data
                </button>
                <button class="btn btn-secondary btn-sm chat-reject-btn"
                        data-category="{category}">
                    No, That's Not Right
                </button>
            </div>
        </div>
        """

        return html

    def _build_forecast_table_ui(self, data: list, parameters: Dict[str, Any]) -> str:
        """
        Build HTML forecast table UI (5 row preview + View Full button).
        """
        if not data:
            return "<p class='text-muted'>No forecast data available.</p>"

        # Build table rows (first 5 only)
        rows_html = []
        for row in data[:5]:
            # Format gaps with color
            gaps_html = []
            for i in range(1, 7):
                gap = row.get(f'month{i}_gap', 0)
                gap_class = 'text-danger' if gap < 0 else 'text-success' if gap > 0 else 'text-muted'
                gaps_html.append(f"<td class='{gap_class}'>{gap:+d}</td>")

            row_html = f"""
            <tr>
                <td>{row['platform']}</td>
                <td>{row['market']}</td>
                <td>{row['worktype']}</td>
                <td>{row['month1_forecast']:,}</td>
                {gaps_html[0]}
                <td>{row['month2_forecast']:,}</td>
                {gaps_html[1]}
                <td>{row['month3_forecast']:,}</td>
                {gaps_html[2]}
                <td>{row['month4_forecast']:,}</td>
                {gaps_html[3]}
                <td>{row['month5_forecast']:,}</td>
                {gaps_html[4]}
                <td>{row['month6_forecast']:,}</td>
                {gaps_html[5]}
                <td>{row['cph']:.1f}</td>
            </tr>
            """
            rows_html.append(row_html)

        html = f"""
        <div class="chat-data-preview">
            <div class="table-responsive">
                <table class="table table-sm table-bordered">
                    <thead class="table-light">
                        <tr>
                            <th>Platform</th>
                            <th>Market</th>
                            <th>Worktype</th>
                            <th>M1 Forecast</th>
                            <th>M1 Gap</th>
                            <th>M2 Forecast</th>
                            <th>M2 Gap</th>
                            <th>M3 Forecast</th>
                            <th>M3 Gap</th>
                            <th>M4 Forecast</th>
                            <th>M4 Gap</th>
                            <th>M5 Forecast</th>
                            <th>M5 Gap</th>
                            <th>M6 Forecast</th>
                            <th>M6 Gap</th>
                            <th>CPH</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows_html)}
                    </tbody>
                </table>
            </div>
            <div class="preview-footer">
                <small class="text-muted">Showing {min(5, len(data))} of {len(data)} records</small>
                <button class="btn btn-outline-primary btn-sm chat-view-full-btn"
                        data-full-data='{self._format_json_data(data)}'>
                    View Full Data
                </button>
            </div>
        </div>
        """

        return html

    def _build_roster_table_ui(self, data: list, parameters: Dict[str, Any]) -> str:
        """Build HTML roster table UI"""
        if not data:
            return "<p class='text-muted'>No roster data available.</p>"

        rows_html = []
        for row in data[:5]:
            rows_html.append(f"""
            <tr>
                <td>{row['name']}</td>
                <td>{row['platform']}</td>
                <td>{row['market']}</td>
                <td>{row['role']}</td>
                <td>{row['fte']}</td>
            </tr>
            """)

        html = f"""
        <div class="chat-data-preview">
            <div class="table-responsive">
                <table class="table table-sm table-bordered">
                    <thead class="table-light">
                        <tr>
                            <th>Name</th>
                            <th>Platform</th>
                            <th>Market</th>
                            <th>Role</th>
                            <th>FTE</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows_html)}
                    </tbody>
                </table>
            </div>
            <div class="preview-footer">
                <small class="text-muted">Showing {min(5, len(data))} of {len(data)} records</small>
            </div>
        </div>
        """

        return html

    def _build_status_ui(self, status: Dict[str, Any]) -> str:
        """Build HTML status UI"""
        progress = status.get('progress_percentage', 0)
        status_text = status.get('status', 'unknown')

        html = f"""
        <div class="chat-status-card">
            <h6>Execution Status</h6>
            <div class="progress mb-2">
                <div class="progress-bar" role="progressbar"
                     style="width: {progress}%"
                     aria-valuenow="{progress}" aria-valuemin="0" aria-valuemax="100">
                    {progress}%
                </div>
            </div>
            <div class="status-details">
                <p><strong>Status:</strong> {status_text.title()}</p>
                <p><strong>Total Tasks:</strong> {status.get('total_tasks', 0)}</p>
                <p><strong>Completed:</strong> {status.get('completed', 0)}</p>
                <p><strong>In Progress:</strong> {status.get('in_progress', 0)}</p>
                <p><strong>Failed:</strong> {status.get('failed', 0)}</p>
            </div>
        </div>
        """

        return html

    def _build_error_ui(self, error_message: str) -> str:
        """Build HTML error UI with XSS protection."""
        # Use the centralized error UI generator for proper escaping
        return generate_error_ui(
            error_type='unknown',
            user_message=error_message,
            admin_contact=False
        )

    def _format_json_params(self, params: Dict[str, Any]) -> str:
        """Format parameters as JSON string for data attribute"""
        import json
        return json.dumps(params).replace('"', '&quot;')

    def _format_json_data(self, data: Any) -> str:
        """Format data as JSON string for data attribute"""
        import json
        return json.dumps(data).replace('"', '&quot;')
