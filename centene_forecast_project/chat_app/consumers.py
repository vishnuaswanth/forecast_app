"""
WebSocket consumers for real-time chat communication.
Handles WebSocket connections, message routing, and chat orchestration.
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings

from chat_app.models import ChatConversation, ChatMessage
from chat_app.services.chat_service import ChatService

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Main WebSocket consumer for chat interface.
    Handles user messages, LLM processing, and tool execution.
    """

    async def connect(self):
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

        # Accept the connection
        await self.accept()

        # Get or create conversation for this user
        self.conversation_id = await self.get_or_create_conversation()

        # Initialize chat service
        self.chat_service = ChatService()

        logger.info(f"User {self.user.portal_id} connected to chat (conversation: {self.conversation_id})")

        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'system',
            'message': 'Connected to chat. How can I help you today?',
            'conversation_id': str(self.conversation_id)
        }))

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.
        """
        if hasattr(self, 'user') and self.user:
            logger.info(f"User {self.user.portal_id} disconnected from chat (code: {close_code})")

    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages.
        Routes messages to appropriate handlers based on message type.
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'user_message':
                await self.handle_user_message(data)
            elif message_type == 'confirm_category':
                await self.handle_confirm_category(data)
            elif message_type == 'reject_category':
                await self.handle_reject_category(data)
            else:
                await self.send_error(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            await self.send_error(f"Error processing message: {str(e)}")

    async def handle_user_message(self, data):
        """
        Handle user's chat message.
        Process through LLM and return categorization confirmation.
        """
        user_text = data.get('message', '').strip()

        if not user_text:
            await self.send_error("Empty message")
            return

        # Save user message to database
        message_id = await self.save_message('user', user_text)

        # Send typing indicator
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'is_typing': True
        }))

        # Process message through chat service
        response = await database_sync_to_async(self.chat_service.process_message)(
            user_text=user_text,
            conversation_id=self.conversation_id,
            user=self.user
        )

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

    async def handle_confirm_category(self, data):
        """
        Handle user confirmation of categorized intent.
        Execute the tool and return results.
        """
        category = data.get('category')
        parameters = data.get('parameters', {})
        message_id = data.get('message_id')

        # Send typing indicator
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'is_typing': True
        }))

        # Execute the confirmed action
        result = await database_sync_to_async(self.chat_service.execute_confirmed_action)(
            category=category,
            parameters=parameters,
            conversation_id=self.conversation_id,
            user=self.user
        )

        # Stop typing indicator
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'is_typing': False
        }))

        # Save assistant response
        await self.save_message('assistant', result.get('message', ''), metadata=result.get('metadata', {}))

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

    async def handle_reject_category(self, data):
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

        await self.save_message('assistant', message)

        await self.send(text_data=json.dumps({
            'type': 'rejection_response',
            'message': message,
            'rejected_category': category
        }))

    async def send_error(self, error_message):
        """
        Send error message to client.
        """
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': error_message
        }))

    @database_sync_to_async
    def get_or_create_conversation(self):
        """
        Get or create active conversation for the user.
        """
        conversation, created = ChatConversation.objects.get_or_create(
            user=self.user,
            is_active=True,
            defaults={'title': 'New Chat'}
        )
        return conversation.id

    @database_sync_to_async
    def save_message(self, role, content, metadata=None):
        """
        Save message to database.
        """
        conversation = ChatConversation.objects.get(id=self.conversation_id)
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

    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'WebSocket test connection successful'
        }))

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        """Echo back the received message"""
        try:
            data = json.loads(text_data)
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
