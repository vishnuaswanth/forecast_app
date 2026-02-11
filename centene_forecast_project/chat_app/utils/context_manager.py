"""
Conversation Context Manager

Manages conversation state across turns for context-aware responses.
Enhanced with database persistence fallback chain: Redis -> Local Cache -> Database -> New

The context manager is the source of truth for conversation state. Every user input
updates the store, and the store context is ALWAYS sent to LLM as readable text.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from channels.db import database_sync_to_async

from chat_app.services.tools.validation import ConversationContext, PreprocessedMessage

logger = logging.getLogger(__name__)


class ConversationContextManager:
    """
    Manages conversation context across turns.

    Stores and retrieves conversation entities, filters, and cached data
    to enable context-aware responses.

    Persistence chain (tries in order):
    1. Redis (if configured) - for distributed systems
    2. Local cache - fast in-memory storage
    3. Database - persistent storage (ConversationContextModel)
    4. New context - if nothing found

    Key principle: The context store is the source of truth.
    """

    def __init__(self, redis_client=None):
        """
        Initialize context manager.

        Args:
            redis_client: Optional Redis client for distributed storage
        """
        self.redis = redis_client  # Optional Redis for distributed systems
        self.local_cache: Dict[str, ConversationContext] = {}  # In-memory storage
        self._db_enabled = True  # Database persistence enabled by default
        logger.info("[Context Manager] Initialized with in-memory storage + DB fallback")

    async def get_context(self, conversation_id: str) -> ConversationContext:
        """
        Retrieve conversation context using fallback chain.

        Tries: Redis -> Local Cache -> Database -> New

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
                    context = ConversationContext.model_validate_json(data)
                    # Update local cache
                    self.local_cache[conversation_id] = context
                    return context
            except Exception as e:
                logger.warning(f"[Context Manager] Redis error: {e}, trying local cache")

        # Try local cache
        if conversation_id in self.local_cache:
            logger.debug(f"[Context Manager] Retrieved from local cache: {conversation_id}")
            return self.local_cache[conversation_id]

        # Try database
        if self._db_enabled:
            try:
                context = await self._load_from_database(conversation_id)
                if context:
                    logger.debug(f"[Context Manager] Retrieved from database: {conversation_id}")
                    # Update local cache
                    self.local_cache[conversation_id] = context
                    return context
            except Exception as e:
                logger.warning(f"[Context Manager] Database error: {e}, creating new context")

        # Create new context if not found
        logger.info(f"[Context Manager] Creating new context: {conversation_id}")
        return ConversationContext(conversation_id=conversation_id)

    async def save_context(self, context: ConversationContext):
        """
        Persist conversation context to all available storage layers.

        Args:
            context: ConversationContext object to save
        """
        # Save to Redis if available
        if self.redis:
            try:
                await self.redis.setex(
                    f"context:{context.conversation_id}",
                    3600,  # 1 hour TTL
                    context.model_dump_json()
                )
                logger.debug(f"[Context Manager] Saved to Redis: {context.conversation_id}")
            except Exception as e:
                logger.warning(f"[Context Manager] Redis save error: {e}")

        # Always save to local cache
        self.local_cache[context.conversation_id] = context
        logger.debug(f"[Context Manager] Saved to local cache: {context.conversation_id}")

        # Save to database asynchronously (don't block)
        if self._db_enabled:
            try:
                await self._save_to_database(context)
                logger.debug(f"[Context Manager] Saved to database: {context.conversation_id}")
            except Exception as e:
                logger.warning(f"[Context Manager] Database save error: {e}")

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
                forecast_report_month=3,
                forecast_report_year=2025,
                active_platforms=["Amisys"]
            )
        """
        context = await self.get_context(conversation_id)

        # Update provided fields
        updated_count = 0
        for key, value in updates.items():
            # Special handling for preference updates
            if key == '_update_preference_show_totals':
                context.user_preferences['show_totals_only'] = value
                updated_count += 1
            elif hasattr(context, key):
                setattr(context, key, value)
                updated_count += 1
            else:
                logger.warning(f"[Context Manager] Unknown field: {key}")

        # Sync legacy fields
        context.sync_legacy_fields()

        # Update metadata
        context.last_updated = datetime.now()
        context.turn_count += 1

        # Save updated context
        await self.save_context(context)

        logger.info(
            f"[Context Manager] Updated {updated_count} fields "
            f"for {conversation_id}, turn {context.turn_count}"
        )

    async def update_from_entities(
        self,
        conversation_id: str,
        extracted_entities: Dict[str, List[str]],
        implicit_info: Dict[str, Any] = None
    ):
        """
        Update context from preprocessed message entities.

        This is the primary method for updating context from user input.
        Called after MessagePreprocessor extracts entities.

        Args:
            conversation_id: Conversation identifier
            extracted_entities: Dict of entity_type -> values from preprocessor
            implicit_info: Dict of implicit information (uses_previous_context, operation, etc.)
        """
        from chat_app.services.entity_extraction import (
            get_extraction_service,
            ExtractedEntities
        )

        context = await self.get_context(conversation_id)
        extraction_service = get_extraction_service()

        # Build ExtractedEntities from dict
        entities = ExtractedEntities(
            report_month=int(extracted_entities['month'][0]) if extracted_entities.get('month') else None,
            report_year=int(extracted_entities['year'][0]) if extracted_entities.get('year') else None,
            platforms=extracted_entities.get('platforms', []),
            markets=extracted_entities.get('markets', []),
            localities=extracted_entities.get('localities', []),
            states=extracted_entities.get('states', []),
            case_types=extracted_entities.get('case_types', []),
            main_lobs=extracted_entities.get('main_lobs', []),
            forecast_months=extracted_entities.get('active_forecast_months', []),
            show_totals_only=extracted_entities.get('show_totals_only', [None])[0] if extracted_entities.get('show_totals_only') else None,
            uses_previous_context=(implicit_info or {}).get('uses_previous_context', False),
            operation=(implicit_info or {}).get('operation'),
            reset_filter=(implicit_info or {}).get('reset_filter', False)
        )

        # Merge with context
        updated_context = extraction_service.merge_with_context(entities, context)

        # Update metadata
        updated_context.last_updated = datetime.now()
        updated_context.turn_count += 1

        # Save
        await self.save_context(updated_context)

        logger.info(
            f"[Context Manager] Updated from entities for {conversation_id}, "
            f"turn {updated_context.turn_count}"
        )

    async def update_from_preprocessed(
        self,
        conversation_id: str,
        preprocessed: PreprocessedMessage
    ):
        """
        Update context from a PreprocessedMessage.

        Convenience method that extracts entities and implicit info
        from the preprocessed message.

        Args:
            conversation_id: Conversation identifier
            preprocessed: PreprocessedMessage from MessagePreprocessor
        """
        await self.update_from_entities(
            conversation_id,
            preprocessed.extracted_entities,
            preprocessed.implicit_info
        )

    async def update_selected_row(
        self,
        conversation_id: str,
        row_data: dict
    ):
        """
        Update the selected forecast row in context.

        Args:
            conversation_id: Conversation identifier
            row_data: Selected row data from forecast table
        """
        context = await self.get_context(conversation_id)

        # Generate row key
        new_row_key = f"{row_data.get('main_lob')}|{row_data.get('state')}|{row_data.get('case_type')}"

        # Check if we should clear (different row being selected)
        if context.should_clear_selected_row(new_row_key=new_row_key):
            logger.debug(f"[Context Manager] Clearing previous row, selecting new: {new_row_key}")

        # Update selected row
        context.update_selected_row(row_data)
        context.last_updated = datetime.now()

        await self.save_context(context)
        logger.info(f"[Context Manager] Updated selected row: {new_row_key}")

    async def reset_filters(
        self,
        conversation_id: str,
        keep_month_year: bool = True,
        reset_preferences: bool = False
    ) -> ConversationContext:
        """
        Reset filter fields while optionally preserving month/year.

        Use this for "get all data" or "reset filters" scenarios where
        the user wants to clear filters but keep the report period.

        Args:
            conversation_id: Conversation identifier
            keep_month_year: If True, preserve forecast_report_month/year
            reset_preferences: If True, also reset user_preferences

        Returns:
            Updated ConversationContext
        """
        context = await self.get_context(conversation_id)

        # Store values to preserve
        saved_month = context.forecast_report_month if keep_month_year else None
        saved_year = context.forecast_report_year if keep_month_year else None

        # Reset all filter fields
        context.active_platforms = []
        context.active_markets = []
        context.active_localities = []
        context.active_states = []
        context.active_case_types = []
        context.active_main_lobs = None
        context.active_forecast_months = None
        context.selected_forecast_row = None
        context.selected_row_key = None
        context.selected_row = None  # Legacy field

        # Restore preserved values
        if keep_month_year:
            context.forecast_report_month = saved_month
            context.forecast_report_year = saved_year

        # Reset preferences if requested
        if reset_preferences:
            context.user_preferences = {
                'show_totals_only': False,
                'max_preview_records': 5,
                'auto_apply_last_filters': True,
            }

        # Sync legacy fields
        context.sync_legacy_fields()
        context.last_updated = datetime.now()

        await self.save_context(context)

        logger.info(
            f"[Context Manager] Reset filters for {conversation_id}, "
            f"kept month/year: {keep_month_year}"
        )

        return context

    async def clear_context(self, conversation_id: str):
        """
        Clear conversation context from all storage layers.

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

        # Remove from database
        if self._db_enabled:
            try:
                await self._delete_from_database(conversation_id)
            except Exception as e:
                logger.warning(f"[Context Manager] Database delete error: {e}")

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

    # ===== DATABASE OPERATIONS =====

    @database_sync_to_async
    def _load_from_database(self, conversation_id: str) -> Optional[ConversationContext]:
        """Load context from database."""
        from chat_app.models import ConversationContextModel, ChatConversation

        try:
            # Get the conversation
            conversation = ChatConversation.objects.get(id=conversation_id)

            # Get context model
            context_model = ConversationContextModel.objects.filter(
                conversation=conversation
            ).first()

            if context_model:
                return context_model.to_conversation_context()

        except ChatConversation.DoesNotExist:
            logger.debug(f"[Context Manager] Conversation not found in DB: {conversation_id}")
        except Exception as e:
            logger.warning(f"[Context Manager] Database load error: {e}")

        return None

    @database_sync_to_async
    def _save_to_database(self, context: ConversationContext):
        """Save context to database."""
        from chat_app.models import ConversationContextModel, ChatConversation

        try:
            # Get the conversation
            conversation = ChatConversation.objects.get(id=context.conversation_id)

            # Save context model
            ConversationContextModel.from_conversation_context(context, conversation)

        except ChatConversation.DoesNotExist:
            logger.warning(
                f"[Context Manager] Cannot save - conversation not found: "
                f"{context.conversation_id}"
            )
        except Exception as e:
            logger.warning(f"[Context Manager] Database save error: {e}")

    @database_sync_to_async
    def _delete_from_database(self, conversation_id: str):
        """Delete context from database."""
        from chat_app.models import ConversationContextModel, ChatConversation

        try:
            conversation = ChatConversation.objects.get(id=conversation_id)
            ConversationContextModel.objects.filter(conversation=conversation).delete()
        except ChatConversation.DoesNotExist:
            pass
        except Exception as e:
            logger.warning(f"[Context Manager] Database delete error: {e}")

    # ===== CONTEXT SUMMARY FOR LLM =====

    async def get_context_summary(self, conversation_id: str) -> str:
        """
        Get a readable context summary for LLM prompts.

        Args:
            conversation_id: Conversation identifier

        Returns:
            Readable string summary of current context
        """
        context = await self.get_context(conversation_id)
        return context.get_context_summary_for_llm()


# Singleton instance
_context_manager: Optional[ConversationContextManager] = None


def get_context_manager(redis_client=None) -> ConversationContextManager:
    """Get or create context manager singleton."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ConversationContextManager(redis_client=redis_client)
    return _context_manager
