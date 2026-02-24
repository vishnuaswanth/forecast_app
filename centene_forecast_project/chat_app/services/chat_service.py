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
