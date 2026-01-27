"""
Chat Service - Orchestrates chat interactions between user, LLM, and tools.
Handles message processing, tool execution, and UI generation.
"""
import logging
from typing import Dict, Any
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


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

    async def process_message(self, user_text: str, conversation_id: str, user) -> Dict[str, Any]:
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

        Returns:
            Dictionary with category, confidence, and UI component
        """
        try:
            # STEP 1: Sanitize user input
            from chat_app.utils.input_sanitizer import get_sanitizer
            sanitizer = get_sanitizer()

            sanitized_text, sanitization_metadata = sanitizer.sanitize(user_text)

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
                return {
                    'category': 'error',
                    'confidence': 0.0,
                    'parameters': {},
                    'ui_component': self._build_error_ui(
                        "Your message could not be processed. Please try again with a different query."
                    ),
                    'metadata': {'error': 'empty_after_sanitization'}
                }

            # STEP 2: Get recent message history for context
            message_history = await self._get_message_history(conversation_id, limit=10)

            # STEP 3: Categorize user intent with LLM (with sanitized input)
            result = await self.llm_service.categorize_intent(
                user_text=sanitized_text,  # ← Sanitized input
                conversation_id=conversation_id,
                message_history=message_history
            )

            category = result.get('category')
            confidence = result.get('confidence')
            parameters = result.get('parameters', {})
            ui_component = result.get('ui_component')  # LLM service now generates UI

            logger.info(f"[Chat Service] Categorized as '{category}' with {confidence:.2f} confidence")

            # Add sanitization metadata to result
            result_metadata = result.get('metadata', {})
            result_metadata['sanitization'] = sanitization_metadata

            return {
                'category': category,
                'confidence': confidence,
                'parameters': parameters,
                'ui_component': ui_component,
                'metadata': result_metadata
            }

        except Exception as e:
            logger.error(f"[Chat Service] Error processing message: {str(e)}", exc_info=True)
            return {
                'category': 'error',
                'confidence': 0.0,
                'parameters': {},
                'ui_component': self._build_error_ui(str(e)),
                'metadata': {'error': str(e)}
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

        except Exception as e:
            logger.error(f"Error executing action: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': str(e),
                'ui_component': self._build_error_ui(str(e)),
                'metadata': {'error': str(e)}
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
        """Build HTML error UI"""
        html = f"""
        <div class="alert alert-danger" role="alert">
            <strong>Error:</strong> {error_message}
        </div>
        """
        return html

    def _format_json_params(self, params: Dict[str, Any]) -> str:
        """Format parameters as JSON string for data attribute"""
        import json
        return json.dumps(params).replace('"', '&quot;')

    def _format_json_data(self, data: Any) -> str:
        """Format data as JSON string for data attribute"""
        import json
        return json.dumps(data).replace('"', '&quot;')
