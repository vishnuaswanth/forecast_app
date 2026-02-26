"""
Chat Service - Orchestrates chat interactions between user, LLM, and tools.

New Flow (CoT agent):
  1. Sanitize input
  2. Get message history
  3. LLMService.run_agent() → CoT reasoning + tool call + UI generation
  4. Return {response_type, message, ui_component, metadata}

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

from chat_app.utils.llm_logger import (
    get_llm_logger,
    create_correlation_id,
    CorrelationContext,
)
from chat_app.exceptions import (
    LLMError,
    APIError,
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
    Factory: return mock or real LLM service based on configuration.
    """
    if settings.CHAT_CONFIG.get('mock_mode', True):
        from chat_app.services.mock_llm_service import MockLLMService
        return MockLLMService()
    from chat_app.services.llm_service import LLMService
    return LLMService()


class ChatService:
    """
    Main chat orchestration service.
    """

    def __init__(self):
        self.llm_service = get_llm_service()

    async def process_message(
        self,
        user_text: str,
        conversation_id: str,
        user,
        message_id: str = None,
        selected_row: dict = None,
    ) -> Dict[str, Any]:
        """
        Process user message and return an assistant response immediately.

        Flow:
          1. Sanitize user input
          2. Get message history
          3. Run CoT agent (reason → tool → UI)
          4. Return result

        Args:
            user_text: Raw user input
            conversation_id: Current conversation ID
            user: Django user object
            message_id: Unique message identifier (optional)
            selected_row: Selected forecast row data (optional)

        Returns:
            Dictionary with response_type, message, ui_component, metadata
        """
        correlation_id = create_correlation_id(conversation_id, message_id)
        user_id = getattr(user, 'portal_id', str(user.id)) if user else 'anonymous'
        start_time = time.time()

        async with CorrelationContext(
            correlation_id=correlation_id,
            message_id=message_id,
            conversation_id=conversation_id,
            user_id=user_id,
        ):
            llm_logger.log_message_processing_start(
                correlation_id=correlation_id,
                conversation_id=conversation_id,
                user_id=user_id,
                message_type='user_message',
            )

            try:
                # STEP 1: Sanitize user input
                from chat_app.utils.input_sanitizer import get_sanitizer
                sanitizer = get_sanitizer()
                sanitized_text, sanitization_metadata = sanitizer.sanitize(user_text)

                llm_logger.log_user_input(
                    correlation_id=correlation_id,
                    raw_input=user_text,
                    sanitized_input=sanitized_text,
                    context={'sanitization': sanitization_metadata},
                    conversation_id=conversation_id,
                    user_id=user_id,
                )

                if sanitization_metadata['threats_detected']:
                    logger.warning(
                        f"[Chat Service] Security threats: "
                        f"{', '.join(sanitization_metadata['threats_detected'])}"
                    )

                if not sanitized_text:
                    logger.warning("[Chat Service] Sanitized text is empty")
                    return {
                        'response_type': 'assistant_response',
                        'message': "Your message could not be processed. Please try again.",
                        'ui_component': generate_error_ui(
                            "Your message could not be processed. Please try again with a different query.",
                            error_type='validation',
                            admin_contact=False,
                        ),
                        'metadata': {
                            'error': 'empty_after_sanitization',
                            'correlation_id': correlation_id,
                        },
                    }

                # STEP 2: Get recent message history
                message_history = await self._get_message_history(conversation_id, limit=10)

                # STEP 3: Run CoT agent
                result = await self.llm_service.run_agent(
                    user_text=sanitized_text,
                    conversation_id=conversation_id,
                    message_history=message_history,
                    selected_row=selected_row,
                )

                total_duration_ms = (time.time() - start_time) * 1000
                llm_logger.log_message_processing_complete(
                    correlation_id=correlation_id,
                    success=True,
                    total_duration_ms=total_duration_ms,
                    category='assistant_response',
                )

                return {
                    'response_type': 'assistant_response',
                    'message': result.get('text', ''),
                    'ui_component': result.get('ui_component', ''),
                    'metadata': {
                        'correlation_id': correlation_id,
                        'sanitization': sanitization_metadata,
                        'data': result.get('data', {}),
                    },
                }

            except LLMError as e:
                total_duration_ms = (time.time() - start_time) * 1000
                logger.error(f"[Chat Service] LLM error: {e.error_code}: {str(e)}", exc_info=True)
                log_error(
                    logger, e,
                    {'conversation_id': conversation_id, 'user_id': user_id, 'duration_ms': total_duration_ms},
                    correlation_id, 'process_message',
                )
                llm_logger.log_message_processing_complete(
                    correlation_id=correlation_id, success=False,
                    total_duration_ms=total_duration_ms, category='llm_error',
                )
                return create_error_response(error=e, correlation_id=correlation_id, category='llm_error')

            except APIClientError as e:
                total_duration_ms = (time.time() - start_time) * 1000
                logger.warning(f"[Chat Service] API client error: {e.error_code}: {str(e)}")
                llm_logger.log_message_processing_complete(
                    correlation_id=correlation_id, success=False,
                    total_duration_ms=total_duration_ms, category='api_client_error',
                )
                return {
                    'response_type': 'assistant_response',
                    'message': e.user_message,
                    'ui_component': generate_error_ui(
                        error_type='validation',
                        user_message=e.user_message,
                        admin_contact=False,
                        error_code=e.error_code,
                    ),
                    'metadata': {
                        'error': True,
                        'error_type': 'api_client_error',
                        'error_code': e.error_code,
                        'correlation_id': correlation_id,
                        'details': e.details,
                    },
                }

            except APIError as e:
                total_duration_ms = (time.time() - start_time) * 1000
                logger.error(f"[Chat Service] API server error: {e.error_code}: {str(e)}", exc_info=True)
                log_error(
                    logger, e,
                    {'conversation_id': conversation_id, 'user_id': user_id, 'duration_ms': total_duration_ms},
                    correlation_id, 'process_message',
                )
                llm_logger.log_message_processing_complete(
                    correlation_id=correlation_id, success=False,
                    total_duration_ms=total_duration_ms, category='api_error',
                )
                return create_error_response(error=e, correlation_id=correlation_id, category='api_error')

            except ValidationError as e:
                total_duration_ms = (time.time() - start_time) * 1000
                logger.warning(f"[Chat Service] Validation error: {e.error_code}: {str(e)}")
                llm_logger.log_message_processing_complete(
                    correlation_id=correlation_id, success=False,
                    total_duration_ms=total_duration_ms, category='validation_error',
                )
                return {
                    'response_type': 'assistant_response',
                    'message': e.user_message,
                    'ui_component': generate_error_ui(
                        error_type='validation',
                        user_message=e.user_message,
                        admin_contact=False,
                        error_code=e.error_code,
                    ),
                    'metadata': {
                        'error': True,
                        'error_type': 'validation',
                        'error_code': e.error_code,
                        'correlation_id': correlation_id,
                    },
                }

            except ContextError as e:
                total_duration_ms = (time.time() - start_time) * 1000
                logger.warning(f"[Chat Service] Context error: {e.error_code}: {str(e)}")
                llm_logger.log_message_processing_complete(
                    correlation_id=correlation_id, success=False,
                    total_duration_ms=total_duration_ms, category='context_error',
                )
                return {
                    'response_type': 'assistant_response',
                    'message': e.user_message,
                    'ui_component': generate_error_ui(
                        error_type='context',
                        user_message=e.user_message,
                        admin_contact=False,
                        error_code=e.error_code,
                    ),
                    'metadata': {
                        'error': True,
                        'error_type': 'context',
                        'error_code': e.error_code,
                        'correlation_id': correlation_id,
                    },
                }

            except Exception as e:
                total_duration_ms = (time.time() - start_time) * 1000
                logger.error(f"[Chat Service] Unexpected error: {str(e)}", exc_info=True)
                llm_logger.log_error(
                    correlation_id=correlation_id,
                    error=e,
                    stage='process_message',
                    context={'duration_ms': total_duration_ms},
                )
                llm_logger.log_message_processing_complete(
                    correlation_id=correlation_id, success=False,
                    total_duration_ms=total_duration_ms, category='error',
                )
                return {
                    'response_type': 'assistant_response',
                    'message': "An unexpected error occurred. Please try again.",
                    'ui_component': generate_error_ui(
                        error_type='unknown',
                        user_message="An unexpected error occurred. Please try again.",
                        admin_contact=True,
                        error_code='UNKNOWN_ERROR',
                    ),
                    'metadata': {
                        'error': True,
                        'error_type': 'unknown',
                        'correlation_id': correlation_id,
                    },
                }

    async def execute_confirmed_forecast_fetch(
        self,
        conversation_id: str,
        user,
    ) -> Dict[str, Any]:
        """
        Execute the confirmed forecast data fetch using params stored in context.

        Args:
            conversation_id: Current conversation ID
            user: Django user object

        Returns:
            Dictionary with success status, message, and ui_component
        """
        from chat_app.utils.context_manager import get_context_manager
        from chat_app.services.tools.forecast_tools import fetch_forecast_data
        from chat_app.services.tools.validation import ForecastQueryParams
        from chat_app.services.tools.ui_tools import (
            generate_forecast_table_html,
            generate_totals_table_html,
            generate_error_ui,
        )
        import calendar

        context_manager = get_context_manager()
        ctx = await context_manager.get_context(conversation_id)

        params_dict = ctx.pending_forecast_fetch

        # Fallback: if pending params are missing, rebuild from current context
        if not params_dict:
            if not ctx.forecast_report_month or not ctx.forecast_report_year:
                msg = "No report period in context. Please request forecast data first."
                return {
                    "success": False,
                    "message": msg,
                    "ui_component": generate_error_ui(msg, error_type="validation", admin_contact=False),
                }
            logger.info(
                "[Chat Service] pending_forecast_fetch missing — rebuilding params from context"
            )
            params_dict = {
                'month': ctx.forecast_report_month,
                'year': ctx.forecast_report_year,
                'platforms': ctx.active_platforms or [],
                'markets': ctx.active_markets or [],
                'localities': ctx.active_localities or [],
                'main_lobs': ctx.active_main_lobs or [],
                'states': ctx.active_states or [],
                'case_types': ctx.active_case_types or [],
                'forecast_months': ctx.active_forecast_months or [],
                'show_totals_only': ctx.user_preferences.get('show_totals_only', False),
            }

        month = params_dict.get('month')
        year = params_dict.get('year')

        try:
            params = ForecastQueryParams(
                month=month,
                year=year,
                platforms=params_dict.get('platforms') or [],
                markets=params_dict.get('markets') or [],
                localities=params_dict.get('localities') or [],
                main_lobs=params_dict.get('main_lobs') or [],
                states=params_dict.get('states') or [],
                case_types=params_dict.get('case_types') or [],
                forecast_months=params_dict.get('forecast_months') or [],
                show_totals_only=params_dict.get('show_totals_only', False),
            )
            data = await fetch_forecast_data(params, enable_validation=False)
        except Exception as e:
            logger.error(f"[Chat Service] Forecast fetch error: {e}")
            msg = f"Failed to fetch forecast data: {str(e)}"
            return {
                "success": False,
                "message": msg,
                "ui_component": generate_error_ui(
                    "Data service temporarily unavailable.",
                    error_type="api", admin_contact=True,
                ),
            }

        # Update context with fetched data
        months_from_api = data.get('months', {})
        report_config = data.get('configuration')
        await context_manager.update_entities(
            conversation_id,
            active_report_type='forecast',
            last_forecast_data=data,
            forecast_report_month=month,
            forecast_report_year=year,
            current_forecast_month=month,
            current_forecast_year=year,
            active_main_lobs=params.main_lobs or None,
            active_platforms=params.platforms or [],
            active_markets=params.markets or [],
            active_localities=params.localities or [],
            active_states=params.states or [],
            active_case_types=params.case_types or [],
            forecast_months=months_from_api,
            report_configuration=report_config,
            last_successful_query=params.model_dump(),
            pending_forecast_fetch=None,  # clear pending
        )

        # Generate UI
        records = data.get('records', [])
        months = data.get('months', {})

        if params.show_totals_only:
            ui = generate_totals_table_html(data.get('totals', {}), months)
            message = f"Forecast totals for {calendar.month_name[month]} {year}"
        else:
            if records:
                ui = generate_forecast_table_html(
                    records, months,
                    show_full=(len(records) <= 5),
                    max_preview=5,
                )
                message = (
                    f"Found {len(records)} forecast records for "
                    f"{calendar.month_name[month]} {year}."
                    if len(records) <= 5
                    else f"Showing 5 of {len(records)} records. Click 'View All' to see more."
                )
            else:
                ui = generate_error_ui(
                    f"No records found for {calendar.month_name[month]} {year} with the applied filters.",
                    error_type="validation", admin_contact=False,
                )
                message = "No records found for the given filters."

        return {
            "success": True,
            "message": message,
            "ui_component": ui,
        }

    async def execute_cph_update(
        self,
        update_data: dict,
        conversation_id: str,
        user,
    ) -> Dict[str, Any]:
        """
        Execute the confirmed CPH update (destructive action, still needs confirm step).

        Args:
            update_data: CPH update data including old/new values and row info
            conversation_id: Current conversation ID
            user: Django user object

        Returns:
            Dictionary with success status and message
        """
        try:
            logger.info(f"[Chat Service] CPH Update requested: {update_data}")

            main_lob = update_data.get('main_lob', 'N/A')
            state = update_data.get('state', 'N/A')
            old_cph = update_data.get('old_cph', 0)
            new_cph = update_data.get('new_cph', 0)

            # TODO: When API is ready, call backend update endpoint here
            ui_component = f"""
            <div class="update-success-card">
                <div class="success-icon">&#10003;</div>
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
                'ui_component': ui_component,
            }

        except Exception as e:
            logger.error(f"[Chat Service] Error in execute_cph_update: {e}")
            return {
                'success': False,
                'message': f'Failed to update CPH: {str(e)}',
                'ui_component': '',
            }

    async def process_ramp_submission(
        self,
        ramp_submission: dict,
        conversation_id: str,
        user,
    ) -> Dict[str, Any]:
        """
        Validate and persist pending ramp week data from the modal form.

        Args:
            ramp_submission: Dict with 'weeks' list and optional 'totalRampEmployees'
            conversation_id: Current conversation ID
            user: Django user object

        Returns:
            Dictionary with ui_component (confirmation card) and message
        """
        from chat_app.utils.context_manager import get_context_manager
        from chat_app.services.tools.ui_tools import generate_ramp_confirmation_ui, generate_error_ui
        import calendar as cal

        context_manager = get_context_manager()
        ctx = await context_manager.get_context(conversation_id)

        weeks = ramp_submission.get('weeks', [])
        errors = []

        for i, w in enumerate(weeks):
            working_days = w.get('workingDays', 0)
            ramp_pct = w.get('rampPercent', 0)
            ramp_emp = w.get('rampEmployees', 0)
            label = w.get('label', f'Week {i+1}')

            if not isinstance(working_days, (int, float)) or working_days <= 0:
                errors.append(f"{label}: workingDays must be > 0 (got {working_days})")
            if not isinstance(ramp_pct, (int, float)) or not (0 <= ramp_pct <= 100):
                errors.append(f"{label}: rampPercent must be 0–100 (got {ramp_pct})")
            if not isinstance(ramp_emp, (int, float)) or ramp_emp < 0:
                errors.append(f"{label}: rampEmployees must be >= 0 (got {ramp_emp})")
            elif isinstance(ramp_emp, float) and not ramp_emp.is_integer():
                errors.append(f"{label}: rampEmployees must be a whole number, no decimals (got {ramp_emp})")

        if not errors and not any(w.get('rampEmployees', 0) > 0 for w in weeks):
            errors.append("At least one week must have Ramp Employees > 0")

        if errors:
            msg = "Validation failed: " + "; ".join(errors)
            logger.warning(f"[Chat Service] Ramp submission validation errors: {errors}")
            return {
                "success": False,
                "message": msg,
                "ui_component": generate_error_ui(msg, error_type="validation", admin_contact=False),
            }

        total_ramp_employees = int(ramp_submission.get(
            'totalRampEmployees',
            sum(w.get('rampEmployees', 0) for w in weeks)
        ))
        payload = {"weeks": weeks, "totalRampEmployees": total_ramp_employees}

        await context_manager.update_entities(conversation_id, pending_ramp_data=payload)

        row_data = ctx.selected_forecast_row or {}
        main_lob = row_data.get('main_lob', 'N/A')
        state = row_data.get('state', 'N/A')
        case_type = row_data.get('case_type', 'N/A')
        row_label = f"{main_lob} | {state} | {case_type}"

        month_key = ctx.selected_ramp_month_key or ''
        try:
            year, month = int(month_key[:4]), int(month_key[5:7])
            month_label = f"{cal.month_name[month]} {year}"
        except (ValueError, IndexError):
            month_label = month_key

        ui = generate_ramp_confirmation_ui(row_label, month_label, weeks)
        return {
            "success": True,
            "message": f"Ramp data ready for {row_label} — {month_label}",
            "ui_component": ui,
        }

    async def execute_ramp_preview(
        self,
        conversation_id: str,
        user,
    ) -> Dict[str, Any]:
        """
        Call the backend preview API and return a preview diff card.

        Args:
            conversation_id: Current conversation ID
            user: Django user object

        Returns:
            Dictionary with ui_component (preview card) and message
        """
        from chat_app.utils.context_manager import get_context_manager
        from chat_app.services.tools.forecast_tools import call_preview_ramp
        from chat_app.services.tools.ui_tools import generate_ramp_preview_ui, generate_error_ui
        import calendar as cal

        context_manager = get_context_manager()
        ctx = await context_manager.get_context(conversation_id)

        row_data = ctx.selected_forecast_row
        month_key = ctx.selected_ramp_month_key
        pending_data = ctx.pending_ramp_data

        if not row_data or not month_key or not pending_data:
            msg = "Missing ramp context. Please resubmit ramp data."
            return {
                "success": False,
                "message": msg,
                "ui_component": generate_error_ui(msg, error_type="validation", admin_contact=False),
            }

        forecast_id = int(row_data.get('forecast_id', row_data.get('id', 0)))

        try:
            preview_response = await call_preview_ramp(forecast_id, month_key, pending_data)
        except Exception as e:
            logger.error(f"[Chat Service] Ramp preview API error: {e}")
            return {
                "success": False,
                "message": f"Preview failed: {str(e)}",
                "ui_component": generate_error_ui(
                    "Could not retrieve ramp preview from server.",
                    error_type="api", admin_contact=True
                ),
            }

        await context_manager.update_entities(
            conversation_id, pending_ramp_preview=preview_response
        )

        try:
            year, month = int(month_key[:4]), int(month_key[5:7])
            month_label = f"{cal.month_name[month]} {year}"
        except (ValueError, IndexError):
            month_label = month_key

        main_lob = row_data.get('main_lob', 'N/A')
        ui = generate_ramp_preview_ui(preview_response)
        return {
            "success": True,
            "message": f"Ramp preview ready for {main_lob} — {month_label}",
            "ui_component": ui,
        }

    async def execute_ramp_apply(
        self,
        conversation_id: str,
        user,
    ) -> Dict[str, Any]:
        """
        Call the backend apply API and clear ramp state on success.

        Args:
            conversation_id: Current conversation ID
            user: Django user object

        Returns:
            Dictionary with success status, message, and ui_component
        """
        from chat_app.utils.context_manager import get_context_manager
        from chat_app.services.tools.forecast_tools import call_apply_ramp
        from chat_app.services.tools.ui_tools import generate_ramp_result_ui, generate_error_ui

        context_manager = get_context_manager()
        ctx = await context_manager.get_context(conversation_id)

        row_data = ctx.selected_forecast_row
        month_key = ctx.selected_ramp_month_key
        pending_data = ctx.pending_ramp_data

        if not row_data or not month_key or not pending_data:
            msg = "Missing ramp context. Please resubmit ramp data."
            return {
                "success": False,
                "message": msg,
                "ui_component": generate_error_ui(msg, error_type="validation", admin_contact=False),
            }

        forecast_id = int(row_data.get('forecast_id', row_data.get('id', 0)))

        try:
            await call_apply_ramp(forecast_id, month_key, pending_data)
        except Exception as e:
            logger.error(f"[Chat Service] Ramp apply API error: {e}")
            return {
                "success": False,
                "message": f"Apply failed: {str(e)}",
                "ui_component": generate_ramp_result_ui(False, f"Apply failed: {str(e)}"),
            }

        # Clear ramp state
        fresh_ctx = await context_manager.get_context(conversation_id)
        fresh_ctx.clear_ramp_state()
        await context_manager.save_context(fresh_ctx)

        main_lob = row_data.get('main_lob', 'N/A')
        ui = generate_ramp_result_ui(True, f"Ramp applied successfully for {main_lob} — {month_key}")
        return {
            "success": True,
            "message": f"Ramp applied for {main_lob} — {month_key}",
            "ui_component": ui,
        }

    async def _get_message_history(self, conversation_id: str, limit: int = 10) -> list:
        """
        Retrieve recent message history from database as role/content dicts.
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
                return [
                    {'role': msg.role, 'content': msg.content}
                    for msg in reversed(messages)
                ]
            except ChatConversation.DoesNotExist:
                logger.warning(f"Conversation {conversation_id} not found")
                return []
            except Exception as e:
                logger.error(f"Error retrieving message history: {str(e)}")
                return []

        return await get_messages()
