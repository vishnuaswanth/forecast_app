"""
Conversation Context Manager
Manages conversation state across turns for context-aware responses.
"""
import logging
from typing import Optional
from datetime import datetime
from chat_app.services.tools.validation import ConversationContext

logger = logging.getLogger(__name__)


class ConversationContextManager:
    """
    Manages conversation context across turns.

    Stores and retrieves conversation entities, filters, and cached data
    to enable context-aware responses.

    Currently uses in-memory storage. Can be extended to use Redis for
    distributed systems.
    """

    def __init__(self, redis_client=None):
        """
        Initialize context manager.

        Args:
            redis_client: Optional Redis client for distributed storage
        """
        self.redis = redis_client  # Optional Redis for distributed systems
        self.local_cache = {}  # Fallback to in-memory storage
        logger.info("[Context Manager] Initialized with in-memory storage")

    async def get_context(self, conversation_id: str) -> ConversationContext:
        """
        Retrieve conversation context.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            ConversationContext object with current state
        """
        # Try Redis first if available
        if self.redis:
            try:
                data = await self.redis.get(f"context:{conversation_id}")
                if data:
                    logger.debug(f"[Context Manager] Retrieved from Redis: {conversation_id}")
                    return ConversationContext.parse_raw(data)
            except Exception as e:
                logger.warning(f"[Context Manager] Redis error: {e}, falling back to local cache")

        # Fallback to local cache
        if conversation_id in self.local_cache:
            logger.debug(f"[Context Manager] Retrieved from local cache: {conversation_id}")
            return self.local_cache[conversation_id]

        # Create new context if not found
        logger.info(f"[Context Manager] Creating new context: {conversation_id}")
        return ConversationContext(conversation_id=conversation_id)

    async def save_context(self, context: ConversationContext):
        """
        Persist conversation context.

        Args:
            context: ConversationContext object to save
        """
        # Save to Redis if available
        if self.redis:
            try:
                await self.redis.setex(
                    f"context:{context.conversation_id}",
                    3600,  # 1 hour TTL
                    context.json()
                )
                logger.debug(f"[Context Manager] Saved to Redis: {context.conversation_id}")
            except Exception as e:
                logger.warning(f"[Context Manager] Redis save error: {e}")

        # Always save to local cache as backup
        self.local_cache[context.conversation_id] = context
        logger.debug(f"[Context Manager] Saved to local cache: {context.conversation_id}")

    async def update_entities(
        self,
        conversation_id: str,
        **updates
    ):
        """
        Update specific context fields.

        Args:
            conversation_id: Conversation identifier
            **updates: Key-value pairs to update in context

        Example:
            await context_manager.update_entities(
                "conv-123",
                current_forecast_month=3,
                current_forecast_year=2025,
                active_platforms=["Amisys"]
            )
        """
        context = await self.get_context(conversation_id)

        # Update provided fields
        updated_count = 0
        for key, value in updates.items():
            if hasattr(context, key):
                setattr(context, key, value)
                updated_count += 1
            else:
                logger.warning(f"[Context Manager] Unknown field: {key}")

        # Update metadata
        context.last_updated = datetime.now()
        context.turn_count += 1

        # Save updated context
        await self.save_context(context)

        logger.info(
            f"[Context Manager] Updated {updated_count} fields "
            f"for {conversation_id}, turn {context.turn_count}"
        )

    async def clear_context(self, conversation_id: str):
        """
        Clear conversation context.

        Args:
            conversation_id: Conversation identifier to clear
        """
        # Remove from Redis if available
        if self.redis:
            try:
                await self.redis.delete(f"context:{conversation_id}")
                logger.debug(f"[Context Manager] Cleared from Redis: {conversation_id}")
            except Exception as e:
                logger.warning(f"[Context Manager] Redis delete error: {e}")

        # Remove from local cache
        if conversation_id in self.local_cache:
            del self.local_cache[conversation_id]
            logger.info(f"[Context Manager] Cleared context: {conversation_id}")

    def get_cache_size(self) -> int:
        """
        Get number of cached conversations.

        Returns:
            Number of conversations in local cache
        """
        return len(self.local_cache)

    async def cleanup_old_contexts(self, max_age_hours: int = 24):
        """
        Clean up old conversation contexts from local cache.

        Args:
            max_age_hours: Maximum age in hours to keep contexts
        """
        now = datetime.now()
        removed = 0

        for conv_id, context in list(self.local_cache.items()):
            age_hours = (now - context.last_updated).total_seconds() / 3600

            if age_hours > max_age_hours:
                del self.local_cache[conv_id]
                removed += 1

        if removed > 0:
            logger.info(
                f"[Context Manager] Cleaned up {removed} contexts "
                f"older than {max_age_hours} hours"
            )
