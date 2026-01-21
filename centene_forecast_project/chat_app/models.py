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
