"""
WebSocket consumers for real-time chat communication.
Handles WebSocket connections, message routing, and chat orchestration.
"""
import json
import logging
import time
from typing import Optional, Dict, Any, Union
from uuid import UUID
from datetime import datetime, date
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth.models import AbstractUser

from chat_app.models import ChatConversation, ChatMessage
from chat_app.services.chat_service import ChatService
from chat_app.utils.llm_logger import get_llm_logger, create_correlation_id

logger = logging.getLogger(__name__)
llm_logger = get_llm_logger()


class SafeJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime, UUID, and other non-serializable types."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Main WebSocket consumer for chat interface.
    Handles user messages, LLM processing, and tool execution.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user: Optional[AbstractUser] = None
        self.conversation_id: Optional[str] = None
        self.chat_service: Optional[ChatService] = None

    async def send_json(self, data: dict) -> None:
        """Send JSON data with safe serialization of datetime/UUID objects."""
        await self.send(text_data=json.dumps(data, cls=SafeJSONEncoder))

    async def connect(self) -> None:
        """
        Handle WebSocket connection.
        Authenticate user and create/retrieve conversation.
        """
        # Get user from Django session
        self.user = self.scope.get('user')

        # Reject unauthenticated connections
        if not self.user or not self.user.is_authenticated:
            logger.warning("Unauthenticated WebSocket connection attempt")
            await self.close(code=4001)
            return

        # Ensure user has required attributes
        if not hasattr(self.user, 'portal_id'):
            logger.error(f"User {self.user.id} missing portal_id attribute")
            await self.close(code=4002)
            return

        # Accept the connection
        await self.accept()

        # Get or create conversation for this user
        try:
            self.conversation_id = await self.get_or_create_conversation()
        except Exception as e:
            logger.error(f"Failed to create conversation for user {self.user.portal_id}: {str(e)}")
            await self.close(code=4003)
            return

        # Initialize chat service
        self.chat_service = ChatService()

        logger.info(f"User {self.user.portal_id} connected to chat (conversation: {self.conversation_id})")

        # Log WebSocket connection
        llm_logger.log_websocket_connect(
            user_id=self.user.portal_id,
            conversation_id=str(self.conversation_id)
        )

        # Send welcome message
        await self.send_json({
            'type': 'system',
            'message': 'Connected to chat. How can I help you today?',
            'conversation_id': str(self.conversation_id)
        })

    async def disconnect(self, close_code: int) -> None:
        """
        Handle WebSocket disconnection.
        """
        if hasattr(self, 'user') and self.user and hasattr(self.user, 'portal_id'):
            logger.info(f"User {self.user.portal_id} disconnected from chat (code: {close_code})")

            # Log WebSocket disconnection
            llm_logger.log_websocket_disconnect(
                user_id=self.user.portal_id,
                conversation_id=str(self.conversation_id) if self.conversation_id else None,
                close_code=close_code
            )

    async def receive(self, text_data: str) -> None:
        """
        Handle incoming WebSocket messages.
        Routes messages to appropriate handlers based on message type.
        """
        if not text_data or not text_data.strip():
            await self.send_error("Empty message received")
            return

        try:
            data = json.loads(text_data)
            if not isinstance(data, dict):
                await self.send_error("Message must be a JSON object")
                return

            message_type = data.get('type')
            if not message_type:
                await self.send_error("Message type is required")
                return

            if message_type == 'user_message':
                await self.handle_user_message(data)
            elif message_type == 'new_conversation':
                await self.handle_new_conversation(data)
            elif message_type == 'confirm_cph_update':
                await self.handle_confirm_cph_update(data)
            elif message_type == 'submit_ramp_data':
                await self.handle_submit_ramp_data(data)
            elif message_type == 'confirm_ramp_submission':
                await self.handle_confirm_ramp_submission(data)
            elif message_type == 'apply_ramp_calculation':
                await self.handle_apply_ramp_calculation(data)
            elif message_type == 'confirm_forecast_fetch':
                await self.handle_confirm_forecast_fetch(data)
            else:
                await self.send_error(f"Unknown message type: {message_type}")

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON received: {str(e)}")
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            await self.send_error(f"Error processing message: {str(e)}")

    async def handle_user_message(self, data: Dict[str, Any]) -> None:
        """
        Handle user's chat message.
        Process through LLM and return categorization confirmation.
        """
        if not self.chat_service or not self.conversation_id:
            await self.send_error("Chat service not initialized")
            return

        user_text = data.get('message', '').strip()
        selected_row = data.get('selected_row')  # Get selected row context if available

        if not user_text:
            await self.send_error("Empty message")
            return

        # Create correlation ID for this message
        correlation_id = create_correlation_id(str(self.conversation_id))
        user_id = self.user.portal_id if hasattr(self.user, 'portal_id') else str(self.user.id)
        start_time = time.time()

        # Log message processing start
        llm_logger.log_message_processing_start(
            correlation_id=correlation_id,
            conversation_id=str(self.conversation_id),
            user_id=user_id,
            message_type='user_message'
        )

        # Save user message to database
        try:
            message_id = await self.save_message('user', user_text)
        except Exception as e:
            logger.error(f"Failed to save user message: {str(e)}")
            llm_logger.log_error(
                correlation_id=correlation_id,
                error=e,
                stage='save_user_message'
            )
            await self.send_error("Failed to save message")
            return

        # Send typing indicator
        await self.send_json({
            'type': 'typing',
            'is_typing': True
        })

        # Process message through chat service (async method, call directly)
        try:
            response = await self.chat_service.process_message(
                user_text=user_text,
                conversation_id=self.conversation_id,
                user=self.user,
                message_id=str(message_id),
                selected_row=selected_row  # Pass selected row context
            )
        except Exception as e:
            logger.error(f"Failed to process message through chat service: {str(e)}")
            total_duration_ms = (time.time() - start_time) * 1000
            llm_logger.log_error(
                correlation_id=correlation_id,
                error=e,
                stage='process_message',
                context={'duration_ms': total_duration_ms}
            )
            await self.send_error("Failed to process message")
            return

        # Stop typing indicator
        await self.send_json({
            'type': 'typing',
            'is_typing': False
        })

        # Save assistant response to database
        assistant_text = response.get('message', '')
        if assistant_text:
            try:
                await self.save_message('assistant', assistant_text, metadata=response.get('metadata', {}))
            except Exception as e:
                logger.error(f"Failed to save assistant response: {str(e)}")

        # Send response to client – always assistant_response in the new flow
        await self.send_json({
            'type': 'assistant_response',
            'ui_component': response.get('ui_component', ''),
            'message_id': str(message_id),
            'message': assistant_text,
            'metadata': response.get('metadata', {})
        })

    async def handle_confirm_cph_update(self, data: Dict[str, Any]) -> None:
        """
        Handle confirmed CPH update request.
        """
        if not self.chat_service or not self.conversation_id:
            await self.send_error("Chat service not initialized")
            return

        update_data = data.get('update_data', {})

        if not update_data:
            await self.send_json({
                'type': 'cph_update_result',
                'success': False,
                'message': 'No update data provided'
            })
            return

        # Send typing indicator
        await self.send_json({
            'type': 'typing',
            'is_typing': True
        })

        try:
            result = await self.chat_service.execute_cph_update(
                update_data=update_data,
                conversation_id=self.conversation_id,
                user=self.user
            )

            # Stop typing indicator
            await self.send_json({
                'type': 'typing',
                'is_typing': False
            })

            await self.send_json({
                'type': 'cph_update_result',
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'ui_component': result.get('ui_component', '')
            })

        except Exception as e:
            logger.error(f"Error executing CPH update: {e}")
            await self.send_json({'type': 'typing', 'is_typing': False})
            await self.send_json({
                'type': 'cph_update_result',
                'success': False,
                'message': str(e)
            })

    async def handle_submit_ramp_data(self, data: Dict[str, Any]) -> None:
        """
        Handle ramp week data submitted from the ramp modal.
        Validates the submission and returns a confirmation card.
        """
        if not self.chat_service or not self.conversation_id:
            await self.send_error("Chat service not initialized")
            return

        ramp_submission = data.get('ramp_submission', {})

        if not ramp_submission or not ramp_submission.get('weeks'):
            await self.send_json({
                'type': 'ramp_confirmation',
                'success': False,
                'message': 'No ramp data provided',
                'ui_component': '',
            })
            return

        await self.send_json({'type': 'typing', 'is_typing': True})

        try:
            result = await self.chat_service.process_ramp_submission(
                ramp_submission=ramp_submission,
                conversation_id=self.conversation_id,
                user=self.user,
            )

            await self.send_json({'type': 'typing', 'is_typing': False})

            await self.send_json({
                'type': 'ramp_confirmation',
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'ui_component': result.get('ui_component', ''),
            })

        except Exception as e:
            logger.error(f"Error processing ramp submission: {e}")
            await self.send_json({'type': 'typing', 'is_typing': False})
            await self.send_json({
                'type': 'ramp_confirmation',
                'success': False,
                'message': str(e),
                'ui_component': '',
            })

    async def handle_confirm_ramp_submission(self, data: Dict[str, Any]) -> None:
        """
        Handle user confirming the ramp submission (Yes, Proceed).
        Calls the backend preview API and returns a diff card.
        """
        if not self.chat_service or not self.conversation_id:
            await self.send_error("Chat service not initialized")
            return

        await self.send_json({'type': 'typing', 'is_typing': True})

        try:
            result = await self.chat_service.execute_ramp_preview(
                conversation_id=self.conversation_id,
                user=self.user,
            )

            await self.send_json({'type': 'typing', 'is_typing': False})

            await self.send_json({
                'type': 'ramp_preview',
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'ui_component': result.get('ui_component', ''),
            })

        except Exception as e:
            logger.error(f"Error executing ramp preview: {e}")
            await self.send_json({'type': 'typing', 'is_typing': False})
            await self.send_json({
                'type': 'ramp_preview',
                'success': False,
                'message': str(e),
                'ui_component': '',
            })

    async def handle_apply_ramp_calculation(self, data: Dict[str, Any]) -> None:
        """
        Handle user confirming the ramp apply (Confirm Apply).
        Calls the backend apply API and clears ramp state.
        """
        if not self.chat_service or not self.conversation_id:
            await self.send_error("Chat service not initialized")
            return

        await self.send_json({'type': 'typing', 'is_typing': True})

        try:
            result = await self.chat_service.execute_ramp_apply(
                conversation_id=self.conversation_id,
                user=self.user,
            )

            await self.send_json({'type': 'typing', 'is_typing': False})

            await self.send_json({
                'type': 'ramp_apply_result',
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'ui_component': result.get('ui_component', ''),
            })

        except Exception as e:
            logger.error(f"Error applying ramp calculation: {e}")
            await self.send_json({'type': 'typing', 'is_typing': False})
            await self.send_json({
                'type': 'ramp_apply_result',
                'success': False,
                'message': str(e),
                'ui_component': '',
            })

    async def handle_confirm_forecast_fetch(self, data: Dict[str, Any]) -> None:
        """
        Handle user confirming a proposed forecast data fetch.
        Executes the actual API call using params stored in context.
        """
        if not self.chat_service or not self.conversation_id:
            await self.send_error("Chat service not initialized")
            return

        await self.send_json({'type': 'typing', 'is_typing': True})

        fetch_params = data.get('fetch_params')

        try:
            result = await self.chat_service.execute_confirmed_forecast_fetch(
                conversation_id=self.conversation_id,
                user=self.user,
                fetch_params=fetch_params,
            )

            await self.send_json({'type': 'typing', 'is_typing': False})

            await self.send_json({
                'type': 'assistant_response',
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'ui_component': result.get('ui_component', ''),
                'metadata': {},
            })

        except Exception as e:
            logger.error(f"Error executing confirmed forecast fetch: {e}")
            await self.send_json({'type': 'typing', 'is_typing': False})
            await self.send_json({
                'type': 'assistant_response',
                'success': False,
                'message': str(e),
                'ui_component': '',
                'metadata': {},
            })

    async def handle_new_conversation(self, data: Dict[str, Any]) -> None:
        """
        Handle user request to start a new conversation.
        Marks current conversation as inactive, clears its context, and creates a new one.
        """
        from chat_app.utils.context_manager import get_context_manager

        old_conversation_id = data.get('old_conversation_id')

        # Mark old conversation as inactive and clear its context (if exists)
        if old_conversation_id:
            try:
                await self.mark_conversation_inactive(old_conversation_id)
            except Exception as e:
                logger.error(f"Failed to mark conversation inactive: {str(e)}")
                # Continue - don't fail new conversation creation

            # Clear old conversation's context from all storage layers
            try:
                context_manager = get_context_manager()
                await context_manager.clear_context(old_conversation_id)
                logger.info(f"Cleared context for old conversation: {old_conversation_id}")
            except Exception as e:
                logger.error(f"Failed to clear context for old conversation: {str(e)}")
                # Continue - don't fail new conversation creation

        # Create new conversation
        try:
            self.conversation_id = await self.create_new_conversation()
        except Exception as e:
            logger.error(f"Failed to create new conversation: {str(e)}")
            await self.send_error("Failed to create new conversation")
            return

        # Send confirmation with new conversation ID
        await self.send_json({
            'type': 'system',
            'message': 'New conversation started. Previous conversation has been archived.',
            'conversation_id': str(self.conversation_id)
        })

        if hasattr(self.user, 'portal_id'):
            logger.info(f"User {self.user.portal_id} started new conversation: {self.conversation_id}")

    async def send_error(self, error_message: str) -> None:
        """
        Send error message to client.
        """
        try:
            await self.send_json({
                'type': 'error',
                'message': error_message
            })
        except Exception as e:
            logger.error(f"Failed to send error message: {str(e)}")

    @database_sync_to_async
    def get_or_create_conversation(self) -> str:
        """
        Get or create active conversation for the user.
        """
        if not self.user:
            raise ValueError("User is required to create conversation")

        conversation, created = ChatConversation.objects.get_or_create(
            user=self.user,
            is_active=True,
            defaults={'title': 'New Chat'}
        )
        return str(conversation.id)

    @database_sync_to_async
    def mark_conversation_inactive(self, conversation_id: str) -> None:
        """
        Mark a conversation as inactive (archive it).
        """
        if not self.user:
            raise ValueError("User is required to mark conversation inactive")

        try:
            # Validate UUID format
            try:
                UUID(conversation_id)
            except ValueError:
                logger.warning(f"Invalid conversation ID format: {conversation_id}")
                return

            conversation = ChatConversation.objects.get(id=conversation_id, user=self.user)
            conversation.is_active = False
            conversation.save(update_fields=['is_active', 'updated_at'])
            logger.info(f"Marked conversation {conversation_id} as inactive")
        except ChatConversation.DoesNotExist:
            user_id = getattr(self.user, 'portal_id', self.user.id) if self.user else 'unknown'
            logger.warning(f"Conversation {conversation_id} not found for user {user_id}")

    @database_sync_to_async
    def create_new_conversation(self) -> str:
        """
        Create a new active conversation for the user.
        Sets title with timestamp for easy identification.
        """
        from datetime import datetime

        if not self.user:
            raise ValueError("User is required to create conversation")

        conversation = ChatConversation.objects.create(
            user=self.user,
            title=f'Chat - {datetime.now().strftime("%Y-%m-%d %H:%M")}',
            is_active=True
        )
        return str(conversation.id)

    @database_sync_to_async
    def save_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Save message to database.
        """
        if not self.conversation_id:
            raise ValueError("Conversation ID is required to save message")
        if not content.strip():
            raise ValueError("Message content cannot be empty")
        if role not in ['user', 'assistant', 'system']:
            raise ValueError(f"Invalid role: {role}")

        try:
            # Validate UUID format
            UUID(self.conversation_id)
        except ValueError:
            raise ValueError(f"Invalid conversation ID format: {self.conversation_id}")

        try:
            conversation = ChatConversation.objects.get(id=self.conversation_id)
        except ChatConversation.DoesNotExist:
            raise ValueError(f"Conversation {self.conversation_id} not found")

        message = ChatMessage.objects.create(
            conversation=conversation,
            role=role,
            content=content,
            metadata=metadata or {}
        )
        return message.id


class TestConsumer(AsyncWebsocketConsumer):
    """
    Simple test consumer for debugging WebSocket connections.
    Echoes back any message it receives.
    """

    async def connect(self) -> None:
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'WebSocket test connection successful'
        }))

    async def disconnect(self, close_code: int) -> None:
        pass

    async def receive(self, text_data: str) -> None:
        """Echo back the received message"""
        if not text_data or not text_data.strip():
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Empty message received'
            }))
            return

        try:
            data = json.loads(text_data)
            if not isinstance(data, dict):
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Message must be a JSON object'
                }))
                return

            await self.send(text_data=json.dumps({
                'type': 'echo',
                'received': data,
                'timestamp': str(data.get('timestamp', ''))
            }))
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            logger.error(f"Unexpected error in TestConsumer: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))
