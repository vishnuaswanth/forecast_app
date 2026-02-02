import uuid
from django.db import models
from django.utils import timezone
from core.models import User


class ChatConversation(models.Model):
    """
    Represents a chat conversation session for a user.
    Tracks the overall conversation context and metadata.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_conversations')
    title = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'chat_conversations'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
        ]

    def __str__(self):
        return f"Conversation {self.id} - {self.user.portal_id} - {self.title or 'Untitled'}"


class ChatMessage(models.Model):
    """
    Represents an individual message in a conversation.
    Can be from user, assistant, or system.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]

    def __str__(self):
        return f"{self.role.title()} message in {self.conversation.id}"


class ConversationContextModel(models.Model):
    """
    Persistent storage for conversation context.

    Stores the conversation state (entities, filters, preferences) to enable
    context-aware responses across sessions and server restarts.

    This provides database-level persistence as a fallback when Redis/cache
    is unavailable.
    """
    conversation = models.OneToOneField(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name='context'
    )

    # Quick access fields for common queries
    active_report_type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Current report type: 'forecast' or 'roster'"
    )
    current_month = models.IntegerField(
        null=True,
        blank=True,
        help_text="Report month (1-12)"
    )
    current_year = models.IntegerField(
        null=True,
        blank=True,
        help_text="Report year"
    )

    # Full context data as JSON
    context_data = models.JSONField(
        default=dict,
        help_text="Full ConversationContext serialized as JSON"
    )

    # Metadata
    turn_count = models.IntegerField(
        default=0,
        help_text="Number of conversation turns"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chat_conversation_contexts'
        indexes = [
            models.Index(fields=['conversation']),
            models.Index(fields=['updated_at']),
        ]

    def __str__(self):
        return f"Context for {self.conversation.id}"

    def to_conversation_context(self):
        """
        Convert database model to ConversationContext Pydantic model.

        Returns:
            ConversationContext instance
        """
        from chat_app.services.tools.validation import ConversationContext

        # Start with stored JSON data
        data = dict(self.context_data)

        # Ensure conversation_id is set
        data['conversation_id'] = str(self.conversation.id)

        # Sync quick access fields
        if self.active_report_type:
            data['active_report_type'] = self.active_report_type
        if self.current_month:
            data['forecast_report_month'] = self.current_month
            data['current_forecast_month'] = self.current_month
        if self.current_year:
            data['forecast_report_year'] = self.current_year
            data['current_forecast_year'] = self.current_year
        data['turn_count'] = self.turn_count

        return ConversationContext(**data)

    @classmethod
    def from_conversation_context(cls, context, conversation):
        """
        Create or update database model from ConversationContext.

        Args:
            context: ConversationContext Pydantic model
            conversation: ChatConversation instance

        Returns:
            ConversationContextModel instance (saved)
        """
        # Serialize context to dict
        context_dict = context.model_dump(mode='json')

        # Remove fields that will be stored separately
        context_dict.pop('conversation_id', None)

        # Create or update
        obj, created = cls.objects.update_or_create(
            conversation=conversation,
            defaults={
                'active_report_type': context.active_report_type,
                'current_month': context.forecast_report_month or context.current_forecast_month,
                'current_year': context.forecast_report_year or context.current_forecast_year,
                'context_data': context_dict,
                'turn_count': context.turn_count,
            }
        )

        return obj


class ChatToolExecution(models.Model):
    """
    Logs tool executions (API calls) made during chat conversations.
    Tracks what tools were called, with what parameters, and what results were returned.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('error', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='tool_executions'
    )
    tool_name = models.CharField(max_length=100)
    parameters = models.JSONField()
    result = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    executed_at = models.DateTimeField(default=timezone.now)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'chat_tool_executions'
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['message', '-executed_at']),
            models.Index(fields=['tool_name', 'status']),
        ]

    def __str__(self):
        return f"{self.tool_name} - {self.status}"
