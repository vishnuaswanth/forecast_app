"""
LLM Service
Real LLM-powered chat service using LangChain + OpenAI for intent classification and query execution.

Error Handling:
- All LLM calls are wrapped with proper exception handling
- OpenAI/LangChain errors are converted to LLMError subclasses
- API errors from forecast tools are converted to APIError subclasses
- All error responses include safe UI components and proper logging
"""
import logging
import calendar
import time
from typing import Dict, List, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from django.conf import settings
import httpx

from chat_app.services.tools.validation_tools import CombinationDiagnosticResult
from chat_app.services.tools.forecast_tools import (
    get_forecast_data_tool,
    fetch_forecast_data,
    fetch_available_reports,
    validate_report_exists
)
from chat_app.services.tools.ui_tools import (
    generate_forecast_table_html,
    generate_totals_table_html,
    generate_confirmation_ui,
    generate_error_ui,
    generate_clarification_ui,
    generate_available_reports_ui
)
from chat_app.services.tools.validation import (
    ForecastQueryParams,
    IntentClassification,
    ConversationContext,
    IntentCategory
)
from chat_app.utils.context_manager import ConversationContextManager
from chat_app.utils.chunking import ForecastDataChunker
from chat_app.prompts.system_prompts import CLASSIFICATION_SYSTEM_PROMPT
from chat_app.utils.llm_logger import get_llm_logger, get_correlation_id, create_correlation_id
from chat_app.exceptions import (
    ChatAppError,
    LLMError,
    LLMConnectionError,
    LLMTimeoutError,
    LLMResponseError,
    LLMRateLimitError,
    APIError,
    APIServerError,
    APIClientError,
    APIConnectionError,
    APITimeoutError,
    ValidationError,
    classify_openai_error,
)
from chat_app.utils.error_handler import create_error_response, log_error

logger = logging.getLogger(__name__)
llm_logger = get_llm_logger()


class LLMService:
    """
    Real LLM-powered chat service using LangChain + OpenAI.

    Handles intent classification, parameter extraction, and forecast query execution.
    """

    def __init__(self):
        """Initialize LLM service with OpenAI client and supporting services."""
        # SSL handling for corporate networks (both sync and async clients)
        self.http_client = httpx.Client(
            verify=False,
            timeout=30.0,
            transport=httpx.HTTPTransport(verify=False)
        )
        self.http_async_client = httpx.AsyncClient(
            verify=False,
            timeout=30.0,
            transport=httpx.AsyncHTTPTransport(verify=False)
        )

        # Get LLM configuration from settings
        llm_config = getattr(settings, 'LLM_CONFIG', {})

        # Store config for logging
        self.model_name = llm_config.get('model', 'gpt-4o-mini')
        self.temperature = llm_config.get('temperature', 0.1)
        self.max_tokens = llm_config.get('max_tokens', 4096)

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            openai_api_key=llm_config.get('api_key'),
            max_tokens=self.max_tokens,
            http_client=self.http_client,
            http_async_client=self.http_async_client
        )

        # Structured output LLM for classification
        self.structured_llm = self.llm.with_structured_output(IntentClassification)

        # Context manager
        self.context_manager = ConversationContextManager()

        # Data chunker
        self.chunker = ForecastDataChunker()

        logger.info(f"[LLM Service] Initialized with model: {self.model_name}")

        # Log service initialization
        llm_logger._log(
            logging.INFO,
            'llm_service_initialized',
            {
                'model': self.model_name,
                'temperature': self.temperature,
                'max_tokens': self.max_tokens,
            }
        )

    async def categorize_intent(
        self,
        user_text: str,
        conversation_id: str,
        message_history: List[dict] = None,
        selected_row: dict = None
    ) -> Dict:
        """
        Classify user intent with LLM.

        Args:
            user_text: User's message (already sanitized by ChatService)
            conversation_id: Conversation identifier
            message_history: Optional list of previous messages
            selected_row: Optional selected forecast row data for context

        Returns:
            Dictionary with:
                - category: Intent category
                - confidence: Confidence score
                - parameters: Extracted parameters
                - ui_component: HTML for UI
                - metadata: Additional info
        """
        # Get or create correlation ID
        correlation_id = get_correlation_id() or create_correlation_id(conversation_id)
        start_time = time.time()

        logger.info(f"[LLM Service] Categorizing intent for: '{user_text[:100]}...'")

        # Log user input received
        llm_logger.log_user_input(
            correlation_id=correlation_id,
            raw_input=user_text,
            sanitized_input=user_text,  # Already sanitized by ChatService
            conversation_id=conversation_id
        )

        # Get conversation context
        context = await self.context_manager.get_context(conversation_id)

        # Store selected row in context if provided
        if selected_row:
            await self.context_manager.update_entities(
                conversation_id,
                selected_row=selected_row
            )

        # Build comprehensive context dictionary for LLM
        # Include all context fields for context-aware responses
        context_dict = {
            # Report type
            'report_type': context.active_report_type,

            # Time period (prefer new fields, fall back to legacy)
            'report_month': context.forecast_report_month or context.current_forecast_month,
            'report_year': context.forecast_report_year or context.current_forecast_year,

            # Filters (with main_lobs precedence)
            'main_lobs': context.active_main_lobs,
            'platforms': context.active_platforms if not context.active_main_lobs else None,
            'markets': context.active_markets if not context.active_main_lobs else None,
            'localities': context.active_localities if not context.active_main_lobs else None,
            'states': context.active_states,
            'case_types': context.active_case_types,

            # Forecast month columns
            'forecast_months': context.forecast_months,  # {0: "Apr-25", 1: "May-25", ...}
            'active_forecast_months': context.active_forecast_months,  # Which months to show
            'forecast_month_filter_active': context.should_apply_forecast_month_filter(),

            # Preferences
            'show_totals_only': context.user_preferences.get('show_totals_only', False),

            # Selected row
            'selected_row_key': context.selected_row_key,

            # Full context summary
            'context_summary': context.get_context_summary_for_llm(),
        }

        # Format input into clear, compact prompt
        from chat_app.utils.input_sanitizer import get_sanitizer
        sanitizer = get_sanitizer()

        # Build legacy format dict for backward compatibility with format_for_llm
        legacy_context = {
            'current_forecast_month': context_dict['report_month'],
            'current_forecast_year': context_dict['report_year'],
            'last_platform': context.active_platforms[0] if context.active_platforms else None,
            'last_market': context.active_markets[0] if context.active_markets else None,
        }

        # Format prompt: clear separation of context and user query
        formatted_prompt = sanitizer.format_for_llm(user_text, legacy_context)

        # Append comprehensive context summary for better LLM understanding
        if context_dict['context_summary'] and context_dict['context_summary'] != "No context set":
            formatted_prompt += f"\nActive Context: {context_dict['context_summary']}"

        logger.debug(f"[LLM Service] Formatted prompt: {formatted_prompt}")

        # Build system prompt with selected row context
        system_prompt = self._build_system_prompt_with_row_context(selected_row)

        # Build messages with history
        messages = [SystemMessage(content=system_prompt)]

        # Add recent conversation history (last 5 turns)
        if message_history:
            for msg in message_history[-5:]:
                if msg['role'] == 'user':
                    messages.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    messages.append(AIMessage(content=msg['content']))

        # Add formatted user query (compact, clear, preserves all parameters)
        messages.append(HumanMessage(content=formatted_prompt))

        # Log LLM request
        llm_logger.log_llm_request(
            correlation_id=correlation_id,
            model=self.model_name,
            messages=[{'role': type(m).__name__, 'content': m.content} for m in messages],
            config={'temperature': self.temperature, 'max_tokens': self.max_tokens},
            request_type='intent_classification'
        )

        # Classify with structured output
        llm_start_time = time.time()
        try:
            classification: IntentClassification = await self.structured_llm.ainvoke(messages)
            llm_duration_ms = (time.time() - llm_start_time) * 1000

            logger.info(
                f"[LLM Service] Classification: {classification.category.value} "
                f"(confidence: {classification.confidence:.2f})"
            )

            # Log LLM response
            llm_logger.log_llm_response(
                correlation_id=correlation_id,
                response={'category': classification.category.value, 'confidence': classification.confidence},
                duration_ms=llm_duration_ms,
                model=self.model_name
            )

            # Log intent classification
            llm_logger.log_intent_classification(
                correlation_id=correlation_id,
                category=classification.category.value,
                confidence=classification.confidence,
                reasoning=classification.reasoning,
                duration_ms=llm_duration_ms
            )

        except Exception as e:
            llm_duration_ms = (time.time() - llm_start_time) * 1000
            logger.error(f"[LLM Service] Classification error: {str(e)}", exc_info=True)

            # Convert to appropriate LLM error type
            llm_error = classify_openai_error(e)

            # Log error with proper context
            log_error(
                logger,
                llm_error,
                context={
                    'conversation_id': conversation_id,
                    'duration_ms': llm_duration_ms,
                    'user_text_length': len(user_text),
                },
                correlation_id=correlation_id,
                stage='intent_classification'
            )

            # Also log to llm_logger for structured logging
            llm_logger.log_error(
                correlation_id=correlation_id,
                error=e,
                stage='intent_classification',
                context={'duration_ms': llm_duration_ms, 'error_code': llm_error.error_code}
            )

            # Return error response with proper UI
            return create_error_response(
                error=llm_error,
                correlation_id=correlation_id,
                category='llm_error'
            )

        # Check if we need clarification
        if classification.requires_clarification or classification.confidence < 0.7:
            return await self._handle_clarification(classification, context, user_text)

        # Handle CLEAR_CONTEXT intent - directly execute without confirmation
        if classification.category == IntentCategory.CLEAR_CONTEXT:
            return await self.execute_clear_context(conversation_id)

        # Handle UPDATE_CONTEXT intent - directly execute without confirmation
        if classification.category == IntentCategory.UPDATE_CONTEXT:
            # Extract operation from classification (default to reset_all_filters)
            operation = 'reset_all_filters'
            specific_filter = None

            # Try to get extracted parameters if the LLM populated them
            extracted = getattr(classification, 'extracted_parameters', {}) or {}
            if extracted:
                operation = extracted.get('operation', 'reset_all_filters')
                specific_filter = extracted.get('specific_filter')

            return await self.execute_update_context(
                conversation_id=conversation_id,
                operation=operation,
                parameters={'specific_filter': specific_filter, 'keep_month_year': True}
            )

        # Handle FTE/CPH intents with selected row
        if classification.category == IntentCategory.GET_FTE_DETAILS:
            if selected_row:
                return await self.generate_fte_details(selected_row, conversation_id)
            else:
                return {
                    'category': classification.category.value,
                    'confidence': classification.confidence,
                    'parameters': {},
                    'ui_component': generate_error_ui("Please select a row from the forecast table first."),
                    'response_type': 'assistant_response',
                    'metadata': {'error': 'no_row_selected', 'correlation_id': correlation_id}
                }

        if classification.category == IntentCategory.MODIFY_CPH:
            if selected_row:
                # Extract new CPH value from user text
                try:
                    new_cph = await self.extract_cph_value(user_text, selected_row.get('target_cph', 0))
                    return await self.generate_cph_preview(selected_row, new_cph, conversation_id, context)
                except ValueError as e:
                    return {
                        'category': classification.category.value,
                        'confidence': classification.confidence,
                        'parameters': {},
                        'ui_component': generate_error_ui(f"Could not understand CPH value: {str(e)}"),
                        'response_type': 'assistant_response',
                        'metadata': {'error': 'invalid_cph_value', 'correlation_id': correlation_id}
                    }
            else:
                return {
                    'category': classification.category.value,
                    'confidence': classification.confidence,
                    'parameters': {},
                    'ui_component': generate_error_ui("Please select a row from the forecast table first."),
                    'response_type': 'assistant_response',
                    'metadata': {'error': 'no_row_selected', 'correlation_id': correlation_id}
                }

        # Extract parameters for other intents
        params = await self._extract_parameters(user_text, classification, context)

        # Check if required parameters are missing (for forecast queries)
        if params.get('_missing_required'):
            missing_fields = params.pop('_missing_required')
            logger.info(f"[LLM Service] Missing required parameters: {missing_fields}")

            # Build a helpful clarification message
            if 'month' in missing_fields and 'year' in missing_fields:
                clarification_text = "Which report month and year would you like to see forecast data for? For example, 'March 2025'."
            elif 'month' in missing_fields:
                clarification_text = "Which month would you like to see forecast data for?"
            else:
                clarification_text = "Which year would you like to see forecast data for?"

            return {
                'category': 'clarification_needed',
                'confidence': classification.confidence,
                'parameters': params,
                'ui_component': generate_clarification_ui(clarification_text),
                'metadata': {
                    'reasoning': 'Missing required month/year parameters',
                    'missing_params': missing_fields,
                    'original_classification': classification.category.value,
                    'correlation_id': correlation_id
                }
            }

        # Build confirmation UI
        ui_component = generate_confirmation_ui(classification.category.value, params)

        total_duration_ms = (time.time() - start_time) * 1000
        llm_logger.log_message_processing_complete(
            correlation_id=correlation_id,
            success=True,
            total_duration_ms=total_duration_ms,
            category=classification.category.value
        )

        return {
            'category': classification.category.value,
            'confidence': classification.confidence,
            'parameters': params,
            'ui_component': ui_component,
            'metadata': {
                'reasoning': classification.reasoning,
                'missing_params': classification.missing_parameters,
                'context_used': context.model_dump(mode='json') if context else {},
                'correlation_id': correlation_id
            }
        }

    async def _extract_parameters(
        self,
        user_text: str,
        classification: IntentClassification,
        context: ConversationContext
    ) -> dict:
        """
        Extract parameters using LLM with Pydantic validation.

        Args:
            user_text: User's message
            classification: Intent classification result
            context: Conversation context

        Returns:
            Dictionary of extracted parameters
        """
        correlation_id = get_correlation_id()
        start_time = time.time()

        if classification.category == IntentCategory.GET_FORECAST_DATA:
            # Use structured output with ForecastQueryParams
            # Build comprehensive context summary
            context_summary = context.get_context_summary_for_llm()

            # Build context parts for backward compatibility
            context_parts = []
            report_month = context.forecast_report_month or context.current_forecast_month
            report_year = context.forecast_report_year or context.current_forecast_year

            if report_month:
                month_name = calendar.month_name[report_month]
                context_parts.append(f"Period: {month_name} {report_year or ''}")

            if context.active_main_lobs:
                context_parts.append(f"LOBs: {', '.join(context.active_main_lobs[:3])}")
            else:
                if context.active_platforms:
                    context_parts.append(f"Platforms: {', '.join(context.active_platforms[:3])}")
                if context.active_markets:
                    context_parts.append(f"Markets: {', '.join(context.active_markets[:3])}")
                if context.active_localities:
                    context_parts.append(f"Localities: {', '.join(context.active_localities[:3])}")

            if context.active_states:
                context_parts.append(f"States: {', '.join(context.active_states[:5])}")
            if context.active_case_types:
                context_parts.append(f"Case Types: {', '.join(context.active_case_types[:3])}")

            if context.should_apply_forecast_month_filter():
                context_parts.append(f"Month Filter: {', '.join(context.active_forecast_months)}")

            if context.user_preferences.get('show_totals_only'):
                context_parts.append("Display: Totals Only")

            context_str = " | ".join(context_parts) if context_parts else "No previous context"

            # Compact extraction prompt - preserves all parameters
            extraction_prompt = f"""
Query: {user_text}
Active Context: {context_str}

Extract: month (1-12), year, platforms[], markets[], localities[], main_lobs[], states[], case_types[], forecast_months[]

Context-Aware Rules:
- If user says "same month", "that platform", "like before" → USE values from Active Context
- If query references context ("that report", "same filters") → preserve context values
- If user EXPLICITLY specifies new values → use those instead
- If user did NOT specify month/year and context has them AND user uses context reference words → use context values
- If query is vague WITHOUT context references → set month=null, year=null

Standard Rules:
- Multi-values → lists: "CA and TX" → ["CA", "TX"]
- Month names → numbers: "March" → 3
- "totals only" → show_totals_only=True
- main_lobs (e.g., "Amisys Medicaid Domestic") → overrides platform/market/locality
- Preserve exact case type names: "Claims Processing", "Enrollment"

Examples:
- "get forecast data" → month=null, year=null (no context reference)
- "same month but for Texas" → use context month/year, add states=["TX"]
- "show March 2025 data" → month=3, year=2025 (explicit)
- "also include California" → add "CA" to existing states (extend operation)
- "just April and May columns" → forecast_months=["Apr-25", "May-25"]
"""

            param_llm = self.llm.with_structured_output(ForecastQueryParams)

            try:
                params = await param_llm.ainvoke([HumanMessage(content=extraction_prompt)])
                duration_ms = (time.time() - start_time) * 1000

                logger.info(f"[LLM Service] Extracted parameters: {params.model_dump()}")

                # Log parameter extraction
                llm_logger.log_parameter_extraction(
                    correlation_id=correlation_id,
                    params=params.model_dump(),
                    source='llm',
                    duration_ms=duration_ms
                )

                # Check if required fields are missing - flag for clarification
                params_dict = params.model_dump()
                if params.is_missing_required():
                    params_dict['_missing_required'] = params.get_missing_fields()
                    logger.info(f"[LLM Service] Missing required fields: {params_dict['_missing_required']}")

                return params_dict
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.warning(f"[LLM Service] Parameter extraction failed: {str(e)}")

                # Log error
                llm_logger.log_error(
                    correlation_id=correlation_id,
                    error=e,
                    stage='parameter_extraction',
                    context={'duration_ms': duration_ms}
                )

                # Check if we have context values to fall back to
                has_context_month = context.current_forecast_month is not None
                has_context_year = context.current_forecast_year is not None

                fallback_params = {
                    'month': context.current_forecast_month,
                    'year': context.current_forecast_year
                }

                # Flag missing fields if no context available
                missing = []
                if not has_context_month:
                    missing.append('month')
                if not has_context_year:
                    missing.append('year')

                if missing:
                    fallback_params['_missing_required'] = missing
                    logger.info(f"[LLM Service] Fallback has missing required: {missing}")

                llm_logger.log_parameter_extraction(
                    correlation_id=correlation_id,
                    params=fallback_params,
                    source='context_fallback',
                    duration_ms=duration_ms
                )

                return fallback_params

        return {}

    async def _handle_clarification(
        self,
        classification: IntentClassification,
        context: ConversationContext,
        user_text: str
    ) -> dict:
        """
        Generate clarification request.

        Args:
            classification: Intent classification result
            context: Conversation context
            user_text: User's message

        Returns:
            Dictionary with clarification response
        """
        logger.info(f"[LLM Service] Handling clarification for: {classification.category.value}")

        # Use LLM to generate natural clarification
        clarification_prompt = f"""
The user said: "{user_text}"

Classification: {classification.category}
Confidence: {classification.confidence}
Missing: {classification.missing_parameters}

Generate a friendly, concise clarification question asking for the missing information.
Be specific about what's needed.
"""

        try:
            response = await self.llm.ainvoke([HumanMessage(content=clarification_prompt)])
            clarification_text = response.content
        except Exception as e:
            logger.error(f"[LLM Service] Clarification generation error: {str(e)}")
            # Convert to LLM error for logging
            llm_error = classify_openai_error(e)
            log_error(
                logger,
                llm_error,
                context={'stage': 'clarification_generation'},
                stage='_handle_clarification'
            )
            # Use fallback message instead of failing
            clarification_text = "I need more information to help you. Could you please provide more details?"

        return {
            'category': 'clarification_needed',
            'confidence': 0.0,
            'parameters': {},
            'ui_component': generate_clarification_ui(clarification_text),
            'metadata': {'original_classification': classification.model_dump(mode='json') if classification else {}}
        }

    async def execute_clear_context(
        self,
        conversation_id: str
    ) -> Dict:
        """
        Clear conversation context and return confirmation UI.

        Clears all filters, selected rows, and cached data from the
        conversation context across all storage layers (Redis, cache, DB).

        Args:
            conversation_id: Conversation identifier

        Returns:
            Dictionary with:
                - success: Boolean
                - category: 'clear_context'
                - message: Confirmation message
                - ui_component: HTML confirmation card
                - metadata: Additional info
        """
        from chat_app.services.tools.ui_tools import generate_clear_context_ui

        correlation_id = get_correlation_id() or create_correlation_id(conversation_id)

        logger.info(f"[LLM Service] Clearing context for conversation: {conversation_id}")

        try:
            await self.context_manager.clear_context(conversation_id)

            logger.info(f"[LLM Service] Context cleared successfully for: {conversation_id}")

            return {
                'success': True,
                'category': 'clear_context',
                'confidence': 1.0,
                'message': 'Context cleared successfully. All filters and selections have been reset.',
                'ui_component': generate_clear_context_ui(),
                'response_type': 'assistant_response',
                'metadata': {
                    'context_cleared': True,
                    'correlation_id': correlation_id
                }
            }

        except Exception as e:
            logger.error(f"[LLM Service] Error clearing context: {str(e)}", exc_info=True)

            return {
                'success': False,
                'category': 'clear_context',
                'confidence': 1.0,
                'message': 'Failed to clear context.',
                'ui_component': generate_error_ui(
                    "Failed to clear context. Please try again.",
                    error_type="context",
                    admin_contact=False,
                    error_code="CONTEXT_CLEAR_ERROR"
                ),
                'response_type': 'assistant_response',
                'metadata': {
                    'error': True,
                    'correlation_id': correlation_id
                }
            }

    async def execute_update_context(
        self,
        conversation_id: str,
        operation: str,
        parameters: dict = None
    ) -> Dict:
        """
        Update context selectively based on operation.

        Different from clear_context - this resets filters while preserving
        month/year. Use for "get all data", "reset filters", "show all platforms".

        Args:
            conversation_id: Conversation identifier
            operation: "reset_all_filters" | "reset_specific"
            parameters: Optional - specific_filter, keep_month_year

        Returns:
            Dict with success, message, ui_component, metadata
        """
        from chat_app.services.tools.ui_tools import generate_context_update_ui

        correlation_id = get_correlation_id() or create_correlation_id(conversation_id)

        params = parameters or {}
        keep_month_year = params.get('keep_month_year', True)
        specific_filter = params.get('specific_filter')

        logger.info(
            f"[LLM Service] Updating context for {conversation_id}: "
            f"operation={operation}, keep_month_year={keep_month_year}"
        )

        try:
            if operation == 'reset_all_filters':
                updated_context = await self.context_manager.reset_filters(
                    conversation_id,
                    keep_month_year=keep_month_year
                )
                message = "All filters have been reset."

            elif operation == 'reset_specific' and specific_filter:
                # Reset only the specified filter
                context = await self.context_manager.get_context(conversation_id)

                # Map filter name to field
                filter_field_map = {
                    'platforms': 'active_platforms',
                    'markets': 'active_markets',
                    'localities': 'active_localities',
                    'states': 'active_states',
                    'case_types': 'active_case_types',
                }

                field_name = filter_field_map.get(specific_filter, f'active_{specific_filter}')
                if hasattr(context, field_name):
                    setattr(context, field_name, [])
                    context.sync_legacy_fields()
                    await self.context_manager.save_context(context)
                    updated_context = context
                    message = f"{specific_filter.replace('_', ' ').title()} filter has been reset."
                else:
                    # Unknown filter, just reset all
                    updated_context = await self.context_manager.reset_filters(
                        conversation_id,
                        keep_month_year=True
                    )
                    message = "Filters have been reset."

            else:
                # Default: reset all filters
                updated_context = await self.context_manager.reset_filters(
                    conversation_id,
                    keep_month_year=True
                )
                message = "Filters have been reset."

            # Build summary of what's preserved
            preserved_items = []
            if updated_context.forecast_report_month and updated_context.forecast_report_year:
                month_name = calendar.month_name[updated_context.forecast_report_month]
                preserved_items.append(f"Report Period: {month_name} {updated_context.forecast_report_year}")

            logger.info(
                f"[LLM Service] Context updated for {conversation_id}: "
                f"{message}, preserved: {preserved_items}"
            )

            return {
                'success': True,
                'category': 'update_context',
                'confidence': 1.0,
                'message': message,
                'ui_component': generate_context_update_ui(message, preserved_items),
                'response_type': 'assistant_response',
                'metadata': {
                    'operation': operation,
                    'preserved': preserved_items,
                    'context_summary': updated_context.get_context_summary_for_llm(),
                    'correlation_id': correlation_id
                }
            }

        except Exception as e:
            logger.error(f"[LLM Service] Error updating context: {str(e)}", exc_info=True)

            return {
                'success': False,
                'category': 'update_context',
                'confidence': 1.0,
                'message': 'Failed to update context.',
                'ui_component': generate_error_ui(
                    "Failed to update context. Please try again.",
                    error_type="context",
                    admin_contact=False,
                    error_code="CONTEXT_UPDATE_ERROR"
                ),
                'response_type': 'assistant_response',
                'metadata': {
                    'error': True,
                    'correlation_id': correlation_id
                }
            }

    async def execute_available_reports_query(
        self,
        parameters: dict,
        conversation_id: str
    ) -> Dict:
        """
        List available forecast reports.

        Fetches all available reports from the backend and generates a UI card
        with report details. Uses the LLM to generate a natural language summary.

        Args:
            parameters: Query parameters (unused for this query, no params required)
            conversation_id: Conversation identifier

        Returns:
            Dictionary with:
                - success: Boolean
                - message: Natural language summary
                - data: Raw reports data
                - ui_component: HTML card listing reports
                - metadata: Report count info
        """
        logger.info("[LLM Service] Executing available reports query")

        correlation_id = get_correlation_id() or create_correlation_id(conversation_id)

        try:
            data = await fetch_available_reports()
        except APIError as e:
            # API-specific errors (connection, timeout, response)
            logger.error(f"[LLM Service] Failed to fetch available reports: {str(e)}", exc_info=True)
            log_error(
                logger,
                e,
                context={'conversation_id': conversation_id},
                correlation_id=correlation_id,
                stage='execute_available_reports_query'
            )
            return create_error_response(
                error=e,
                correlation_id=correlation_id,
                category='api_error'
            )
        except Exception as e:
            # Unexpected errors
            logger.error(f"[LLM Service] Failed to fetch available reports: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': "Failed to retrieve available reports",
                'ui_component': generate_error_ui(
                    "Data service is temporarily unavailable. Please contact admin.",
                    error_type="api",
                    admin_contact=True,
                    error_code="API_ERROR"
                ),
                'metadata': {'error': True, 'correlation_id': correlation_id}
            }

        # Generate UI card
        ui_html = generate_available_reports_ui(data)

        # Build natural language summary
        reports = data.get('reports', [])
        current_reports = [r for r in reports if r.get('is_valid', False)]
        total = len(reports)

        if total == 0:
            message = (
                "There are no forecast reports currently available. "
                "Please upload forecast data to get started."
            )
        else:
            # Build summary of available periods
            report_periods = [f"{r.get('month', '?')} {r.get('year', '?')}" for r in reports[:5]]
            periods_str = ", ".join(report_periods)
            if total > 5:
                periods_str += f", and {total - 5} more"

            message = (
                f"I found {total} forecast report{'s' if total != 1 else ''} available"
                f" ({len(current_reports)} current). "
                f"Available periods: {periods_str}."
            )

        logger.info(f"[LLM Service] Available reports query complete - {total} reports")

        return {
            'success': True,
            'message': message,
            'data': data,
            'ui_component': ui_html,
            'metadata': {
                'report_count': total,
                'current_count': len(current_reports)
            }
        }

    async def execute_forecast_query(
        self,
        parameters: dict,
        conversation_id: str
    ) -> Dict:
        """
        Execute forecast data query with pre-flight validation and combination diagnosis.

        NEW FEATURES:
        1. Pre-flight validation using FilterValidator
        2. Auto-correction for high-confidence typos (>90%)
        3. Confirmation UI for medium-confidence matches (60-90%)
        4. Combination diagnosis when query returns 0 records

        Args:
            parameters: Query parameters
            conversation_id: Conversation identifier

        Returns:
            Dictionary with:
                - success: Boolean
                - message: Status message
                - data: Forecast data
                - ui_component: HTML for display
                - metadata: Additional info (including validation_summary)
        """
        correlation_id = get_correlation_id() or create_correlation_id(conversation_id)
        query_start_time = time.time()

        logger.info(f"[LLM Service] Executing forecast query with params: {parameters}")

        # Log tool execution start
        llm_logger.log_tool_execution(
            correlation_id=correlation_id,
            tool_name='execute_forecast_query',
            parameters=parameters,
            status='started'
        )

        # Check for missing required parameters first
        if parameters.get('month') is None or parameters.get('year') is None:
            missing = []
            if parameters.get('month') is None:
                missing.append('month')
            if parameters.get('year') is None:
                missing.append('year')
            logger.warning(f"[LLM Service] Missing required parameters: {missing}")
            return {
                'success': False,
                'message': f"Missing required parameters: {', '.join(missing)}",
                'ui_component': generate_clarification_ui(
                    "Which report month and year would you like to see forecast data for? "
                    "For example, 'March 2025'."
                ),
                'metadata': {'missing_params': missing, 'requires_clarification': True}
            }

        # Validate parameters
        try:
            params = ForecastQueryParams(**parameters)
        except Exception as e:
            logger.error(f"[LLM Service] Parameter validation error: {str(e)}")
            return {
                'success': False,
                'message': f"Invalid parameters: {str(e)}",
                'ui_component': generate_error_ui(f"Invalid parameters: {str(e)}")
            }

        # STEP 0: Validate report exists for the given month/year
        try:
            validation = await validate_report_exists(params.month, params.year)

            if not validation['exists']:
                month_name = calendar.month_name[params.month]
                logger.info(
                    f"[LLM Service] No report for {month_name} {params.year} - "
                    f"showing available reports"
                )

                # Build UI showing available reports
                available_reports = validation.get('available_reports', [])
                reports_data = {
                    'reports': available_reports,
                    'total_reports': len(available_reports)
                }
                ui_html = generate_available_reports_ui(reports_data)

                # Add header message about the missing report
                no_data_header = f'''
                <div class="alert alert-warning mb-3">
                    <h6 class="alert-heading">
                        <i class="bi bi-exclamation-triangle"></i> No Data Available
                    </h6>
                    <p class="mb-0">
                        No forecast report exists for <strong>{month_name} {params.year}</strong>.
                        Please choose from the available reports below, or upload data for this period.
                    </p>
                </div>
                '''

                return {
                    'success': False,
                    'message': f'No forecast report found for {month_name} {params.year}.',
                    'ui_component': no_data_header + ui_html,
                    'metadata': {
                        'report_validation': 'no_report',
                        'requested_period': f'{month_name} {params.year}',
                        'available_report_count': len(available_reports)
                    }
                }
        except Exception as e:
            # If validation fails, log and proceed (don't block the query)
            logger.warning(
                f"[LLM Service] Report validation failed: {str(e)} - proceeding without validation"
            )

        # PRE-FLIGHT FILTER VALIDATION
        from chat_app.services.tools.validation_tools import FilterValidator, ConfidenceLevel
        from chat_app.services.tools.validation import FilterValidationSummary
        from chat_app.services.tools.ui_tools import generate_validation_confirmation_ui

        validator = FilterValidator()
        validation_start_time = time.time()

        try:
            validation_results = await validator.validate_all(params)
        except Exception as e:
            logger.warning(f"[LLM Service] Validation failed: {e} - proceeding without validation")
            validation_results = {}

        # Process validation results
        validation_summary = FilterValidationSummary()
        auto_corrected_count = 0
        needs_confirmation_count = 0
        rejected_count = 0

        for field_name, results in validation_results.items():
            for result in results:
                # Log each validation result
                llm_logger.log_validation(
                    correlation_id=correlation_id,
                    field=field_name,
                    original_value=result.original_value,
                    corrected_value=result.corrected_value,
                    confidence=result.confidence,
                    is_valid=result.is_valid,
                    suggestions=result.suggestions
                )

                if result.confidence_level == ConfidenceLevel.HIGH:
                    # Auto-correct (>90% confidence)
                    if result.corrected_value:
                        validation_summary.auto_corrected.setdefault(field_name, []).append(
                            result.corrected_value
                        )
                        # Apply correction to params
                        field_list = getattr(params, field_name, None)
                        if field_list and result.original_value in field_list:
                            idx = field_list.index(result.original_value)
                            field_list[idx] = result.corrected_value
                            auto_corrected_count += 1
                            logger.info(
                                f"[LLM Service] Auto-corrected: "
                                f"{result.original_value} → {result.corrected_value}"
                            )

                elif result.confidence_level == ConfidenceLevel.MEDIUM:
                    # Needs confirmation (60-90% confidence)
                    validation_summary.needs_confirmation.setdefault(field_name, []).append(
                        (result.original_value, result.corrected_value, result.confidence)
                    )
                    needs_confirmation_count += 1

                elif not result.is_valid:
                    # Rejected (<60% confidence)
                    validation_summary.rejected.setdefault(field_name, []).append(
                        (result.original_value, result.suggestions)
                    )
                    rejected_count += 1

        # Log validation summary
        validation_duration_ms = (time.time() - validation_start_time) * 1000
        total_validated = sum(len(v) for v in validation_results.values())
        llm_logger.log_validation_summary(
            correlation_id=correlation_id,
            total_validated=total_validated,
            auto_corrected=auto_corrected_count,
            needs_confirmation=needs_confirmation_count,
            rejected=rejected_count,
            duration_ms=validation_duration_ms
        )

        # VALIDATION DISABLED: Skip confirmation UI, proceed directly to data fetch
        # If we have confirmations or rejections, log but don't block
        if validation_summary.has_issues():
            logger.info(
                f"[LLM Service] Validation issues (ignored): "
                f"{validation_summary.get_confirmation_count()} confirmations, "
                f"{validation_summary.get_rejection_count()} rejections"
            )
            # Validation disabled - continue to fetch data instead of returning

        # Fetch data using tool (with validation disabled since we already validated)
        fetch_start_time = time.time()
        try:
            data = await fetch_forecast_data(params, enable_validation=False)
            fetch_duration_ms = (time.time() - fetch_start_time) * 1000

            # Log API call success
            llm_logger.log_api_call(
                correlation_id=correlation_id,
                endpoint='/api/forecast/data',
                method='GET',
                params={'month': params.month, 'year': params.year},
                response_status=200,
                duration_ms=fetch_duration_ms
            )

        except APIClientError as e:
            # API Client errors (4xx) - User can fix these (bad filters, no data, invalid params)
            # These are NOT system failures - show user what's wrong
            fetch_duration_ms = (time.time() - fetch_start_time) * 1000
            logger.warning(f"[LLM Service] API client error: {e.error_code}: {str(e)}")

            # Log API call (warning level, not error)
            llm_logger.log_api_call(
                correlation_id=correlation_id,
                endpoint='/api/forecast/data',
                method='GET',
                params={'month': params.month, 'year': params.year},
                response_status=getattr(e, 'status_code', 400),
                duration_ms=fetch_duration_ms,
                error=str(e)
            )

            # Return user-friendly error with NO "contact admin" message
            return {
                'success': False,
                'message': e.user_message,
                'ui_component': generate_error_ui(
                    e.user_message,
                    error_type="validation",  # Use validation styling (info icon)
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
            fetch_duration_ms = (time.time() - fetch_start_time) * 1000
            logger.error(f"[LLM Service] API server error: {str(e)}", exc_info=True)

            # Log error with context
            log_error(
                logger,
                e,
                context={
                    'conversation_id': conversation_id,
                    'month': params.month,
                    'year': params.year,
                    'duration_ms': fetch_duration_ms,
                },
                correlation_id=correlation_id,
                stage='execute_forecast_query'
            )

            # Log API call failure
            llm_logger.log_api_call(
                correlation_id=correlation_id,
                endpoint='/api/forecast/data',
                method='GET',
                params={'month': params.month, 'year': params.year},
                response_status=getattr(e, 'status_code', 500),
                duration_ms=fetch_duration_ms,
                error=str(e)
            )

            return create_error_response(
                error=e,
                correlation_id=correlation_id,
                category='api_error'
            )

        except ValidationError as e:
            # Handle validation errors (user can fix these)
            fetch_duration_ms = (time.time() - fetch_start_time) * 1000
            logger.warning(f"[LLM Service] Validation error: {str(e)}")

            return {
                'success': False,
                'message': e.user_message,
                'ui_component': generate_error_ui(
                    e.user_message,
                    error_type="validation",
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

        except Exception as e:
            # Handle unexpected errors
            fetch_duration_ms = (time.time() - fetch_start_time) * 1000
            logger.error(f"[LLM Service] API call failed: {str(e)}", exc_info=True)

            # Log API call failure
            llm_logger.log_api_call(
                correlation_id=correlation_id,
                endpoint='/api/forecast/data',
                method='GET',
                params={'month': params.month, 'year': params.year},
                response_status=500,
                duration_ms=fetch_duration_ms,
                error=str(e)
            )

            return {
                'success': False,
                'message': "Failed to fetch data",
                'ui_component': generate_error_ui(
                    "Data service is temporarily unavailable. Please contact admin.",
                    error_type="api",
                    admin_contact=True,
                    error_code="API_ERROR"
                ),
                'metadata': {
                    'error': True,
                    'error_type': 'api',
                    'correlation_id': correlation_id
                }
            }

        # Cache data in context (including report configuration for CPH calculations)
        # Also store forecast_months from API response for filtering
        report_config = data.get('configuration', None)
        months_from_api = data.get('months', {})  # {0: "Apr-25", 1: "May-25", ...}

        await self.context_manager.update_entities(
            conversation_id,
            # Report type and data
            active_report_type='forecast',
            last_forecast_data=data,
            # Time period (both new and legacy fields)
            forecast_report_month=params.month,
            forecast_report_year=params.year,
            current_forecast_month=params.month,
            current_forecast_year=params.year,
            # Filters
            active_main_lobs=params.main_lobs or None,
            active_platforms=params.platforms or [],
            active_markets=params.markets or [],
            active_localities=params.localities or [],
            active_states=params.states or [],
            active_case_types=params.case_types or [],
            # Forecast months from response (for filtering options)
            forecast_months=months_from_api,
            # Report configuration
            report_configuration=report_config
        )

        if report_config:
            logger.debug(f"[LLM Service] Stored report configuration in context: {list(report_config.keys()) if isinstance(report_config, dict) else 'N/A'}")
        if months_from_api:
            logger.debug(f"[LLM Service] Stored forecast months: {list(months_from_api.values())}")

        # Check if we got 0 records - trigger combination diagnosis (NEW)
        if len(data.get('records', [])) == 0:
            logger.info("[LLM Service] Query returned 0 records - starting combination diagnosis")

            from chat_app.services.tools.validation_tools import CombinationDiagnostic

            diagnostic = CombinationDiagnostic()
            diagnosis_start_time = time.time()

            try:
                diagnosis_result = await diagnostic.diagnose(params, data)
                diagnosis_duration_ms = (time.time() - diagnosis_start_time) * 1000

                # Log combination diagnostic
                llm_logger.log_combination_diagnostic(
                    correlation_id=correlation_id,
                    is_data_issue=diagnosis_result.is_data_issue,
                    is_combination_issue=diagnosis_result.is_combination_issue,
                    problematic_filters=diagnosis_result.problematic_filters,
                    total_records_available=diagnosis_result.total_records_available,
                    working_combinations=diagnosis_result.working_combinations,
                    duration_ms=diagnosis_duration_ms
                )

                # Generate diagnostic UI with LLM-powered guidance
                ui_html = await self._generate_diagnostic_guidance(
                    params,
                    diagnosis_result
                )

                # Log query execution result
                total_duration_ms = (time.time() - query_start_time) * 1000
                llm_logger.log_query_execution(
                    correlation_id=correlation_id,
                    params=parameters,
                    record_count=0,
                    duration_ms=total_duration_ms,
                    success=False,
                    error='No records found - combination issue'
                )

                return {
                    'success': False,
                    'message': 'No records found - diagnosis provided',
                    'data': data,
                    'ui_component': ui_html,
                    'metadata': {
                        'diagnosis': {
                            'is_data_issue': diagnosis_result.is_data_issue,
                            'is_combination_issue': diagnosis_result.is_combination_issue,
                            'problematic_filters': diagnosis_result.problematic_filters,
                            'total_records_available': diagnosis_result.total_records_available
                        },
                        'validation_summary': validation_summary.model_dump(),
                        'correlation_id': correlation_id
                    }
                }

            except Exception as e:
                logger.error(f"[LLM Service] Diagnosis failed: {e}", exc_info=True)
                # Fallback to existing _generate_no_data_guidance
                ui_html = await self._generate_no_data_guidance(params, data)

                return {
                    'success': False,
                    'message': 'No data found - suggestions provided',
                    'data': data,
                    'ui_component': ui_html,
                    'metadata': {'validation_summary': validation_summary.model_dump()}
                }

        # Cache data in context (including report configuration for CPH calculations)
        # Note: This is a second update point - first is after initial fetch
        await self.context_manager.update_entities(
            conversation_id,
            # Report type and data
            active_report_type='forecast',
            last_forecast_data=data,
            # Time period
            forecast_report_month=params.month,
            forecast_report_year=params.year,
            current_forecast_month=params.month,
            current_forecast_year=params.year,
            # Filters
            active_main_lobs=params.main_lobs or None,
            active_platforms=params.platforms or [],
            active_markets=params.markets or [],
            active_localities=params.localities or [],
            active_states=params.states or [],
            active_case_types=params.case_types or [],
            # Forecast months from response
            forecast_months=data.get('months', {}),
            # Report configuration
            report_configuration=data.get('configuration', None),
            # Store last successful query for repeat functionality
            last_successful_query=params.model_dump()
        )

        # Generate UI based on user preference
        if params.show_totals_only:
            ui_html = generate_totals_table_html(data.get('totals', {}), data.get('months', {}))
            message = f"Here are the forecast totals for {calendar.month_name[params.month]} {params.year}"
        else:
            records = data.get('records', [])

            if len(records) <= 5:
                # Show all records
                ui_html = generate_forecast_table_html(records, data.get('months', {}), show_full=True)
                message = f"Found {len(records)} forecast records"
            else:
                # Show top 5 with "View Full" button
                ui_html = generate_forecast_table_html(
                    records,
                    data.get('months', {}),
                    show_full=False,
                    max_preview=5
                )
                message = f"Showing 5 of {len(records)} forecast records. Click 'View All' to see more."

        # Add validation summary note if auto-corrections were made
        if validation_summary.get_correction_count() > 0:
            corrections_note = "<div class='alert alert-info mt-2'><small>"
            corrections_note += f"Note: Auto-corrected {validation_summary.get_correction_count()} filter value(s). "
            for field_name, corrections in validation_summary.auto_corrected.items():
                corrections_note += f"{field_name}: {', '.join(corrections)}. "
            corrections_note += "</small></div>"
            ui_html += corrections_note

        record_count = len(data.get('records', []))
        logger.info(f"[LLM Service] Query executed successfully - {record_count} records")

        # Log successful query execution
        total_duration_ms = (time.time() - query_start_time) * 1000
        llm_logger.log_query_execution(
            correlation_id=correlation_id,
            params=parameters,
            record_count=record_count,
            duration_ms=total_duration_ms,
            success=True
        )

        # Log tool execution complete
        llm_logger.log_tool_execution(
            correlation_id=correlation_id,
            tool_name='execute_forecast_query',
            parameters=parameters,
            result_summary={'record_count': record_count, 'status': 'success'},
            duration_ms=total_duration_ms,
            status='success'
        )

        return {
            'success': True,
            'message': message,
            'data': data,
            'ui_component': ui_html,
            'metadata': {
                'record_count': record_count,
                'months_included': list(data.get('months', {}).values()),
                'filters_applied': data.get('filters_applied', {}),
                'validation_summary': validation_summary.model_dump(),
                'correlation_id': correlation_id
            }
        }

    async def _generate_no_data_guidance(
        self,
        params: ForecastQueryParams,
        api_response: dict
    ) -> str:
        """
        Generate helpful LLM-powered guidance when no forecast data is found.

        Uses the LLM to provide actionable suggestions based on the query parameters
        and API response context.

        Args:
            params: Query parameters that returned no results
            api_response: Full API response (with empty records)

        Returns:
            HTML string with helpful guidance
        """
        correlation_id = get_correlation_id()
        start_time = time.time()

        # Build context for LLM
        month_name = calendar.month_name[params.month]

        # Extract applied filters
        applied_filters = []
        if params.platforms:
            applied_filters.append(f"Platforms: {', '.join(params.platforms)}")
        if params.markets:
            applied_filters.append(f"Markets: {', '.join(params.markets)}")
        if params.localities:
            applied_filters.append(f"Localities: {', '.join(params.localities)}")
        if params.main_lobs:
            applied_filters.append(f"LOBs: {', '.join(params.main_lobs)}")
        if params.states:
            applied_filters.append(f"States: {', '.join(params.states)}")
        if params.case_types:
            applied_filters.append(f"Case Types: {', '.join(params.case_types)}")
        if params.forecast_months:
            applied_filters.append(f"Forecast Months: {', '.join(params.forecast_months)}")

        filters_text = "\n- ".join(applied_filters) if applied_filters else "None (querying all data)"

        # Create LLM prompt for helpful guidance
        guidance_prompt = f"""
The user queried forecast data with these parameters:
- Report Month: {month_name} {params.year}
- Filters Applied:
  {filters_text}

The API returned ZERO records (no data found).

Generate a helpful, empathetic response that:
1. Acknowledges that no data was found for their specific query
2. Provides 2-3 actionable suggestions such as:
   - Check if forecast data has been uploaded for {month_name} {params.year}
   - Try removing some filters to broaden the search
   - Verify the month/year combination is correct
   - Check if data exists for nearby months (e.g., {calendar.month_name[params.month - 1 if params.month > 1 else 12]} or {calendar.month_name[params.month + 1 if params.month < 12 else 1]})
   - Upload forecast data if it hasn't been uploaded yet
3. Offer to help with a different query

Keep the tone friendly, professional, and solution-oriented. Format as plain text (not HTML).
Be concise - maximum 4-5 sentences.
"""

        try:
            logger.info(f"[LLM Service] Generating no-data guidance for {month_name} {params.year}")

            # Log LLM request for guidance
            llm_logger.log_llm_request(
                correlation_id=correlation_id,
                model=self.model_name,
                messages=[{'role': 'HumanMessage', 'content': guidance_prompt}],
                request_type='no_data_guidance'
            )

            llm_start = time.time()
            response = await self.llm.ainvoke([HumanMessage(content=guidance_prompt)])
            llm_duration_ms = (time.time() - llm_start) * 1000
            guidance_text = response.content.strip()

            # Log LLM response
            llm_logger.log_llm_response(
                correlation_id=correlation_id,
                response=guidance_text,
                duration_ms=llm_duration_ms,
                model=self.model_name
            )

            logger.info(f"[LLM Service] Generated guidance: {guidance_text[:100]}...")
        except Exception as e:
            logger.error(f"[LLM Service] Failed to generate guidance: {str(e)}")

            # Convert to LLM error and log properly
            llm_error = classify_openai_error(e)
            log_error(
                logger,
                llm_error,
                context={'month': month_name, 'year': params.year},
                correlation_id=correlation_id,
                stage='no_data_guidance_generation'
            )

            # Log error to structured logger
            llm_logger.log_error(
                correlation_id=correlation_id,
                error=e,
                stage='no_data_guidance_generation',
                context={'error_code': llm_error.error_code}
            )

            # Fallback message (LLM failure shouldn't block user experience)
            guidance_text = (
                f"No forecast data was found for {month_name} {params.year} with your specified filters. "
                f"Please check if the data has been uploaded for this period, or try adjusting your filters."
            )

        # Build HTML with helpful styling
        html = f'''
        <div class="alert alert-warning" role="alert">
            <h6 class="alert-heading"><i class="bi bi-exclamation-triangle"></i> No Data Found</h6>
            <p class="mb-2">{guidance_text}</p>
            <hr>
            <div class="mt-2">
                <strong>Your Query:</strong>
                <ul class="mb-0 mt-1">
                    <li>Report Period: {month_name} {params.year}</li>
                    {f'<li>Filters: {", ".join(applied_filters)}</li>' if applied_filters else '<li>No filters applied</li>'}
                </ul>
            </div>
            <div class="mt-3">
                <small class="text-muted">
                    <strong>Suggestions:</strong> Try uploading forecast data for this period,
                    or ask me to show data for a different month/year.
                </small>
            </div>
        </div>
        '''

        return html

    async def _generate_diagnostic_guidance(
        self,
        params: ForecastQueryParams,
        diagnosis: CombinationDiagnosticResult
    ) -> str:
        """
        Generate LLM-powered diagnostic guidance for filter combination issues.

        Uses the LLM to explain the diagnosis in natural language and provide
        actionable recommendations.

        Args:
            params: Original query parameters
            diagnosis: Combination diagnostic result from CombinationDiagnostic

        Returns:
            HTML string with diagnostic guidance
        """
        from langchain_core.messages import HumanMessage
        from chat_app.services.tools.ui_tools import generate_combination_diagnostic_ui

        correlation_id = get_correlation_id()

        # Build context for LLM
        month_name = calendar.month_name[params.month]

        if diagnosis.is_data_issue:
            # Simple data availability issue - use basic template
            return generate_combination_diagnostic_ui(
                diagnosis.diagnosis_message,
                {},
                diagnosis.total_records_available
            )

        # Build LLM prompt for combination issue
        guidance_prompt = f"""
The user queried forecast data but got 0 results due to filter combination issues.

Query Details:
- Month/Year: {month_name} {params.year}
- Total records available: {diagnosis.total_records_available}

Problematic Filters: {', '.join(diagnosis.problematic_filters)}

Applied Filters:
"""

        if params.platforms:
            guidance_prompt += f"\n- Platforms: {', '.join(params.platforms)}"
        if params.markets:
            guidance_prompt += f"\n- Markets: {', '.join(params.markets)}"
        if params.localities:
            guidance_prompt += f"\n- Localities: {', '.join(params.localities)}"
        if params.states:
            guidance_prompt += f"\n- States: {', '.join(params.states)}"
        if params.case_types:
            guidance_prompt += f"\n- Case Types: {', '.join(params.case_types)}"

        guidance_prompt += f"\n\nWorking Combinations:"
        for filter_name, valid_values in diagnosis.working_combinations.items():
            guidance_prompt += f"\n- {filter_name}: {', '.join(valid_values[:5])}"
            if len(valid_values) > 5:
                guidance_prompt += f" (and {len(valid_values) - 5} more)"

        guidance_prompt += """

Generate a helpful, empathetic response that:
1. Explains why the combination didn't work
2. Suggests removing the problematic filter(s)
3. Provides 2-3 specific alternatives using the working combinations
4. Offers to help with a different query

Keep the tone friendly and solution-oriented. Format as plain text (not HTML).
Be concise - maximum 5-6 sentences.
"""

        try:
            logger.info(f"[LLM Service] Generating combination diagnostic guidance")

            # Log LLM request for diagnostic guidance
            llm_logger.log_llm_request(
                correlation_id=correlation_id,
                model=self.model_name,
                messages=[{'role': 'HumanMessage', 'content': guidance_prompt}],
                request_type='diagnostic_guidance'
            )

            llm_start = time.time()
            response = await self.llm.ainvoke([HumanMessage(content=guidance_prompt)])
            llm_duration_ms = (time.time() - llm_start) * 1000
            guidance_text = response.content.strip()

            # Log LLM response
            llm_logger.log_llm_response(
                correlation_id=correlation_id,
                response=guidance_text,
                duration_ms=llm_duration_ms,
                model=self.model_name
            )

            logger.info(f"[LLM Service] Generated diagnostic guidance: {guidance_text[:100]}...")
        except Exception as e:
            logger.error(f"[LLM Service] Failed to generate diagnostic guidance: {str(e)}")

            # Convert to LLM error and log properly
            llm_error = classify_openai_error(e)
            log_error(
                logger,
                llm_error,
                context={'is_data_issue': diagnosis.is_data_issue},
                correlation_id=correlation_id,
                stage='diagnostic_guidance_generation'
            )

            # Log error to structured logger
            llm_logger.log_error(
                correlation_id=correlation_id,
                error=e,
                stage='diagnostic_guidance_generation',
                context={'error_code': llm_error.error_code}
            )

            # Fallback to simple message (LLM failure shouldn't block user experience)
            guidance_text = diagnosis.diagnosis_message

        # Generate HTML UI with LLM guidance
        return generate_combination_diagnostic_ui(
            guidance_text,
            diagnosis.working_combinations,
            diagnosis.total_records_available
        )

    def _build_context_prompt(self, context: ConversationContext) -> str:
        """
        Build context information for LLM classification.

        Args:
            context: Conversation context

        Returns:
            Context prompt string
        """
        month_name = (
            calendar.month_name[context.current_forecast_month]
            if context.current_forecast_month else 'None'
        )

        # Build active filters summary
        active_filters = []
        if context.active_platforms:
            active_filters.append(f"Platforms={context.active_platforms}")
        if context.active_markets:
            active_filters.append(f"Markets={context.active_markets}")
        if context.active_localities:
            active_filters.append(f"Localities={context.active_localities}")
        if context.active_states:
            active_filters.append(f"States={context.active_states}")

        filters_str = ", ".join(active_filters) if active_filters else "None"

        last_record_count = (
            context.last_forecast_data.get('total_records', 0)
            if context.last_forecast_data else 0
        )

        return f"""
Conversation Context:
- Forecast period: {month_name} {context.current_forecast_year or 'None'}
- Active filters: {filters_str}
- Turn count: {context.turn_count}
- Has cached data: {'Yes' if context.last_forecast_data else 'No'}
- Last query returned: {last_record_count} records
"""

    def _build_system_prompt_with_row_context(self, selected_row: dict = None) -> str:
        """
        Build system prompt with optional selected row context.

        Args:
            selected_row: Selected forecast row data (optional)

        Returns:
            System prompt string with row context if available
        """
        import json

        base_prompt = CLASSIFICATION_SYSTEM_PROMPT

        if selected_row:
            row_info = f"""

SELECTED ROW CONTEXT:
The user has selected a forecast row with the following data:
- Main LOB: {selected_row.get('main_lob', 'N/A')}
- State: {selected_row.get('state', 'N/A')}
- Case Type: {selected_row.get('case_type', 'N/A')}
- Target CPH: {selected_row.get('target_cph', 'N/A')}
- Monthly Data: {json.dumps(selected_row.get('months', {}), indent=2)}

If the user asks about "this row", "the selected row", "FTEs", "FTE details", or wants to modify/change CPH,
they are referring to this selected row.

Additional categories to recognize:
- GET_FTE_DETAILS: User wants FTE information for the selected row (e.g., "get FTEs", "show FTE details", "what are the FTEs for this row")
- MODIFY_CPH: User wants to change the target CPH value (e.g., "change CPH to 3.5", "increase CPH by 10%", "set target CPH to 4")
"""
            return base_prompt + row_info

        return base_prompt

    async def generate_fte_details(self, row_data: dict, conversation_id: str) -> dict:
        """
        Generate FTE details response for selected row.

        Args:
            row_data: Selected forecast row data
            conversation_id: Conversation identifier

        Returns:
            Dictionary with FTE details UI and metadata
        """
        correlation_id = get_correlation_id() or create_correlation_id(conversation_id)

        logger.info(f"[LLM Service] Generating FTE details for row: {row_data.get('main_lob')}")

        # Determine domestic vs global
        main_lob = row_data.get('main_lob', '').lower()
        case_type = row_data.get('case_type', '').lower()
        is_domestic = 'domestic' in main_lob or 'domestic' in case_type
        config_type = 'DOMESTIC' if is_domestic else 'GLOBAL'

        # Build monthly details HTML
        months_html = ""
        for month_name, month_data in row_data.get('months', {}).items():
            gap = month_data.get('gap', 0)
            gap_class = 'gap-negative' if gap < 0 else 'gap-positive' if gap > 0 else ''

            fte_req = month_data.get('fte_required', 0)
            fte_avail = month_data.get('fte_available', 0)

            months_html += f"""
            <div class="fte-detail-item">
                <div class="fte-detail-label">{month_name}</div>
                <div class="fte-detail-value">
                    FTE Req: {fte_req} |
                    FTE Avail: {fte_avail} |
                    <span class="{gap_class}">Gap: {gap:+d}</span>
                </div>
            </div>
            """

        badge_class = 'bg-primary' if is_domestic else 'bg-secondary'
        ui_component = f"""
        <div class="fte-details-card">
            <div class="fte-details-header">
                FTE Details: {row_data.get('main_lob')} | {row_data.get('state')} | {row_data.get('case_type')}
            </div>
            <div class="fte-config-badge" style="margin-bottom: 12px;">
                <span class="badge {badge_class}">
                    {config_type} Configuration
                </span>
                <span style="margin-left: 8px;">Target CPH: {row_data.get('target_cph', 'N/A')}</span>
            </div>
            <div class="fte-details-grid">
                {months_html}
            </div>
        </div>
        """

        return {
            'success': True,
            'category': 'get_fte_details',
            'confidence': 1.0,
            'message': f"FTE details for {row_data.get('main_lob')}",
            'ui_component': ui_component,
            'response_type': 'fte_details',
            'metadata': {
                'config_type': config_type,
                'row_key': f"{row_data.get('main_lob')}|{row_data.get('state')}|{row_data.get('case_type')}",
                'correlation_id': correlation_id
            }
        }

    async def generate_cph_preview(
        self,
        row_data: dict,
        new_cph: float,
        conversation_id: str,
        context: 'ConversationContext' = None
    ) -> dict:
        """
        Calculate new values with modified CPH and generate preview.

        Formulas (using configuration parameters):
        - fte_required = ceil(forecast / (working_days * work_hours * (1 - shrinkage) * target_cph))
        - capacity = fte_available * working_days * work_hours * (1 - shrinkage) * target_cph
        - gap = capacity - forecast

        Args:
            row_data: Selected forecast row data
            new_cph: New CPH value to apply
            conversation_id: Conversation identifier
            context: Conversation context with report_configuration

        Returns:
            Dictionary with CPH preview UI and calculated values
        """
        import json
        from chat_app.services.tools.calculation_tools import (
            calculate_cph_impact,
            determine_locality,
            validate_cph_value
        )

        correlation_id = get_correlation_id() or create_correlation_id(conversation_id)

        logger.info(f"[LLM Service] Generating CPH preview: {row_data.get('target_cph')} -> {new_cph}")

        # Validate the new CPH value
        is_valid, error_msg = validate_cph_value(new_cph)
        if not is_valid:
            return {
                'success': False,
                'category': 'modify_cph',
                'confidence': 1.0,
                'message': error_msg,
                'ui_component': generate_error_ui(error_msg),
                'response_type': 'assistant_response',
                'metadata': {'error': 'invalid_cph_value', 'correlation_id': correlation_id}
            }

        old_cph = row_data.get('target_cph', 0)

        # Determine locality (Domestic vs Global)
        main_lob = row_data.get('main_lob', '')
        case_type = row_data.get('case_type', '')
        locality = determine_locality(main_lob, case_type)
        config_type = locality.upper()

        # Get report configuration from context
        report_configuration = None
        if context and context.report_configuration:
            report_configuration = context.report_configuration
            logger.debug(f"[LLM Service] Using report configuration from context for {locality}")
        else:
            logger.warning("[LLM Service] No report configuration in context, using defaults")

        # Calculate impact using proper business formulas
        impact_data = calculate_cph_impact(row_data, new_cph, report_configuration)

        # Build preview data structure
        preview_data = {
            'main_lob': main_lob,
            'state': row_data.get('state'),
            'case_type': case_type,
            'old_cph': old_cph,
            'new_cph': new_cph,
            'config_type': config_type,
            'locality': locality,
            'months': impact_data
        }

        months_preview_html = ""

        for month_name, month_impact in impact_data.items():
            old_values = month_impact['old']
            new_values = month_impact['new']
            config_used = month_impact.get('config', {})

            old_fte_req = old_values['fte_required']
            old_capacity = old_values['capacity']
            old_gap = old_values['gap']

            new_fte_req = new_values['fte_required']
            new_capacity = new_values['capacity']
            new_gap = new_values['gap']

            # Gap color class
            new_gap_class = 'gap-positive' if new_gap >= 0 else 'gap-negative'

            # Show config info if available
            config_info = ""
            if config_used:
                config_info = f"""
                <div class="cph-config-info" style="font-size: 10px; color: #888; margin-top: 4px;">
                    {config_used.get('working_days', 22)}d × {config_used.get('work_hours', 8)}h ×
                    {100 - int(config_used.get('shrinkage', 0.15) * 100)}% productivity
                </div>
                """

            months_preview_html += f"""
            <div class="cph-month-preview">
                <strong>{month_name}</strong>
                <div class="cph-preview-row">
                    <span class="cph-preview-label">FTE Required:</span>
                    <span class="cph-preview-old">{old_fte_req}</span>
                    <span class="cph-preview-arrow">→</span>
                    <span class="cph-preview-new">{new_fte_req}</span>
                </div>
                <div class="cph-preview-row">
                    <span class="cph-preview-label">Capacity:</span>
                    <span class="cph-preview-old">{old_capacity:,}</span>
                    <span class="cph-preview-arrow">→</span>
                    <span class="cph-preview-new">{new_capacity:,}</span>
                </div>
                <div class="cph-preview-row">
                    <span class="cph-preview-label">Gap:</span>
                    <span class="cph-preview-old">{old_gap:+d}</span>
                    <span class="cph-preview-arrow">→</span>
                    <span class="cph-preview-new {new_gap_class}">{new_gap:+d}</span>
                </div>
                {config_info}
            </div>
            """

        # Escape JSON for HTML attribute
        preview_data_json = json.dumps(preview_data).replace('"', '&quot;')

        is_domestic = locality == 'Domestic'
        badge_class = 'bg-primary' if is_domestic else 'bg-secondary'
        ui_component = f"""
        <div class="cph-preview-card">
            <div class="cph-preview-header">
                CPH Change Preview
                <span class="badge {badge_class} ms-2">{config_type}</span>
            </div>
            <div class="cph-preview-row" style="margin-bottom: 16px;">
                <span class="cph-preview-label">Target CPH:</span>
                <span class="cph-preview-old">{old_cph}</span>
                <span class="cph-preview-arrow">→</span>
                <span class="cph-preview-new">{new_cph}</span>
            </div>
            <div class="cph-preview-subtitle">
                <strong>{main_lob}</strong> | {row_data.get('state')} | {case_type}
            </div>
            <div class="cph-months-preview">
                {months_preview_html}
            </div>
            <div class="cph-preview-actions">
                <button class="cph-confirm-btn" data-update="{preview_data_json}">
                    Confirm Change
                </button>
                <button class="cph-reject-btn">Cancel</button>
            </div>
        </div>
        """

        return {
            'success': True,
            'category': 'modify_cph',
            'confidence': 1.0,
            'message': f"Preview of CPH change from {old_cph} to {new_cph}",
            'ui_component': ui_component,
            'response_type': 'cph_preview',
            'preview_data': preview_data,
            'metadata': {
                'old_cph': old_cph,
                'new_cph': new_cph,
                'config_type': config_type,
                'locality': locality,
                'correlation_id': correlation_id
            }
        }

    async def extract_cph_value(self, user_text: str, current_cph: float) -> float:
        """
        Extract new CPH value from user message.
        Handles: "change to 3.5", "increase by 10%", "decrease to 2.0"

        Args:
            user_text: User's message
            current_cph: Current CPH value for percentage calculations

        Returns:
            New CPH value as float

        Raises:
            ValueError: If CPH value cannot be extracted
        """
        import re

        prompt = f"""Extract the new CPH value from this user message.
Current CPH: {current_cph}

User message: "{user_text}"

Rules:
- If user says "change to X" or "set to X" or just mentions a number, return X
- If user says "increase by X%", calculate: {current_cph} * (1 + X/100)
- If user says "decrease by X%", calculate: {current_cph} * (1 - X/100)
- If user says "increase by X" (not %), calculate: {current_cph} + X
- If user says "decrease by X" (not %), calculate: {current_cph} - X

Return ONLY the numeric value, nothing else. Round to 2 decimal places."""

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            result_text = response.content.strip()

            # Try to parse the numeric value
            try:
                return round(float(result_text), 2)
            except ValueError:
                # Try to extract number from response
                numbers = re.findall(r'[\d.]+', result_text)
                if numbers:
                    return round(float(numbers[0]), 2)
                raise ValueError(f"Could not extract CPH value from response: {result_text}")

        except Exception as e:
            logger.error(f"[LLM Service] Error extracting CPH value: {e}")

            # Log the LLM error (but don't fail hard - try fallback)
            llm_error = classify_openai_error(e)
            log_error(
                logger,
                llm_error,
                context={'user_text': user_text[:100], 'current_cph': current_cph},
                stage='extract_cph_value',
                include_traceback=False  # Don't need full trace for this
            )

            # Fallback: try simple regex extraction from user text
            numbers = re.findall(r'[\d.]+', user_text)
            if numbers:
                # Return the last number found (most likely the target value)
                return round(float(numbers[-1]), 2)

            raise ValueError(f"Could not extract CPH value from: {user_text}")
