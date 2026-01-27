"""
WebSocket consumers for real-time chat communication.
Handles WebSocket connections, message routing, and chat orchestration.
"""
import json
import logging
from typing import Optional, Dict, Any, Union
from uuid import UUID
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth.models import AbstractUser

from chat_app.models import ChatConversation, ChatMessage
from chat_app.services.chat_service import ChatService

logger = logging.getLogger(__name__)


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

        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'system',
            'message': 'Connected to chat. How can I help you today?',
            'conversation_id': str(self.conversation_id)
        }))

    async def disconnect(self, close_code: int) -> None:
        """
        Handle WebSocket disconnection.
        """
        if hasattr(self, 'user') and self.user and hasattr(self.user, 'portal_id'):
            logger.info(f"User {self.user.portal_id} disconnected from chat (code: {close_code})")

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
            elif message_type == 'confirm_category':
                await self.handle_confirm_category(data)
            elif message_type == 'reject_category':
                await self.handle_reject_category(data)
            elif message_type == 'new_conversation':
                await self.handle_new_conversation(data)
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

        if not user_text:
            await self.send_error("Empty message")
            return

        # Save user message to database
        try:
            message_id = await self.save_message('user', user_text)
        except Exception as e:
            logger.error(f"Failed to save user message: {str(e)}")
            await self.send_error("Failed to save message")
            return

        # Send typing indicator
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'is_typing': True
        }))

        # Process message through chat service (async method, call directly)
        try:
            response = await self.chat_service.process_message(
                user_text=user_text,
                conversation_id=self.conversation_id,
                user=self.user
            )
        except Exception as e:
            logger.error(f"Failed to process message through chat service: {str(e)}")
            await self.send_error("Failed to process message")
            return

        # Stop typing indicator
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'is_typing': False
        }))

        # Send response to client
        await self.send(text_data=json.dumps({
            'type': 'assistant_response',
            'category': response.get('category'),
            'confidence': response.get('confidence'),
            'ui_component': response.get('ui_component'),
            'message_id': str(message_id),
            'metadata': response.get('metadata', {})
        }))

    async def handle_confirm_category(self, data: Dict[str, Any]) -> None:
        """
        Handle user confirmation of categorized intent.
        Execute the tool and return results.
        """
        if not self.chat_service or not self.conversation_id:
            await self.send_error("Chat service not initialized")
            return
            
        category = data.get('category')
        if not category:
            await self.send_error("Category is required")
            return
            
        parameters = data.get('parameters', {})
        message_id = data.get('message_id')

        # Send typing indicator
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'is_typing': True
        }))

        # Execute the confirmed action (async method, call directly)
        try:
            result = await self.chat_service.execute_confirmed_action(
                category=category,
                parameters=parameters,
                conversation_id=self.conversation_id,
                user=self.user
            )
        except Exception as e:
            logger.error(f"Failed to execute confirmed action: {str(e)}")
            await self.send_error("Failed to execute action")
            return

        # Stop typing indicator
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'is_typing': False
        }))

        # Save assistant response
        try:
            await self.save_message('assistant', result.get('message', ''), metadata=result.get('metadata', {}))
        except Exception as e:
            logger.error(f"Failed to save assistant response: {str(e)}")
            # Continue execution - don't fail the entire operation for logging issues

        # Send result to client
        await self.send(text_data=json.dumps({
            'type': 'tool_result',
            'category': category,
            'success': result.get('success', False),
            'ui_component': result.get('ui_component'),
            'message': result.get('message'),
            'data': result.get('data'),
            'metadata': result.get('metadata', {})
        }))

    async def handle_reject_category(self, data: Dict[str, Any]) -> None:
        """
        Handle user rejection of categorized intent.
        Show fallback message to contact admin.
        """
        category = data.get('category')

        message = (
            "I understand this isn't quite what you're looking for. "
            "Please contact the administrator to request this feature. "
            "We're constantly improving and your feedback helps us prioritize new capabilities."
        )

        try:
            await self.save_message('assistant', message)
        except Exception as e:
            logger.error(f"Failed to save rejection response: {str(e)}")
            # Continue execution - don't fail for logging issues

        await self.send(text_data=json.dumps({
            'type': 'rejection_response',
            'message': message,
            'rejected_category': category
        }))

    async def handle_new_conversation(self, data: Dict[str, Any]) -> None:
        """
        Handle user request to start a new conversation.
        Marks current conversation as inactive and creates a new one.
        """
        old_conversation_id = data.get('old_conversation_id')

        # Mark old conversation as inactive (if exists)
        if old_conversation_id:
            try:
                await self.mark_conversation_inactive(old_conversation_id)
            except Exception as e:
                logger.error(f"Failed to mark conversation inactive: {str(e)}")
                # Continue - don't fail new conversation creation

        # Create new conversation
        try:
            self.conversation_id = await self.create_new_conversation()
        except Exception as e:
            logger.error(f"Failed to create new conversation: {str(e)}")
            await self.send_error("Failed to create new conversation")
            return

        # Send confirmation with new conversation ID
        await self.send(text_data=json.dumps({
            'type': 'system',
            'message': 'New conversation started. Previous conversation has been archived.',
            'conversation_id': str(self.conversation_id)
        }))

        if hasattr(self.user, 'portal_id'):
            logger.info(f"User {self.user.portal_id} started new conversation: {self.conversation_id}")

    async def send_error(self, error_message: str) -> None:
        """
        Send error message to client.
        """
        try:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': error_message
            }))
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
