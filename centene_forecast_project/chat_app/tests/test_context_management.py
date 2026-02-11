"""
Context Management Tests - Test context lifecycle and storage.

Tests:
1. Context creation for new conversations
2. Context persistence across requests
3. Context clearing on new chat
4. Context isolation between conversations
5. Database persistence and recovery
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from chat_app.services.tools.validation import ConversationContext


class TestContextLifecycle:
    """Test context creation, persistence, and cleanup."""

    @pytest.mark.asyncio
    async def test_new_context_created_for_new_conversation(self, fresh_context):
        """New conversation should get fresh context with no filters."""
        context = fresh_context("new-conv-id")

        assert context.conversation_id == "new-conv-id"
        assert context.active_platforms == []
        assert context.active_markets == []
        assert context.active_states == []
        assert context.forecast_report_month is None
        assert context.forecast_report_year is None
        assert context.active_report_type is None

    @pytest.mark.asyncio
    async def test_context_persists_across_requests(self, mock_context_manager, populated_context):
        """Context should persist within same conversation."""
        conv_id = "persist-test-123"

        # First request: Set context
        context = populated_context(
            conversation_id=conv_id,
            platforms=["Amisys"],
            markets=["Medicaid"],
            month=3,
            year=2025
        )

        # Configure mock to return the populated context
        mock_context_manager.get_context.return_value = context

        # Second request: Should retrieve same context
        retrieved = await mock_context_manager.get_context(conv_id)

        assert retrieved.active_platforms == ["Amisys"]
        assert retrieved.active_markets == ["Medicaid"]
        assert retrieved.forecast_report_month == 3
        assert retrieved.forecast_report_year == 2025

    @pytest.mark.asyncio
    async def test_context_update_increments_turn_count(self, fresh_context):
        """Updating context should increment turn count."""
        context = fresh_context("turn-count-test")

        initial_count = context.turn_count
        context.turn_count += 1

        assert context.turn_count == initial_count + 1

    @pytest.mark.asyncio
    async def test_context_update_updates_timestamp(self, fresh_context):
        """Updating context should update last_updated timestamp."""
        context = fresh_context("timestamp-test")

        initial_time = context.last_updated
        context.last_updated = datetime.now()

        assert context.last_updated >= initial_time


class TestContextClearingOnNewChat:
    """Test that context is cleared when starting new chat."""

    @pytest.mark.asyncio
    async def test_clear_context_removes_all_filters(self, mock_context_manager, populated_context):
        """Starting new chat should clear old context filters."""
        old_conv_id = "old-conv-123"

        # Setup old context
        old_context = populated_context(
            conversation_id=old_conv_id,
            platforms=["Facets"],
            markets=["Medicare"],
            month=6,
            year=2025
        )

        # Verify old context has data
        assert old_context.active_platforms == ["Facets"]
        assert old_context.forecast_report_month == 6

        # Clear context
        await mock_context_manager.clear_context(old_conv_id)

        # Verify clear was called
        mock_context_manager.clear_context.assert_called_once_with(old_conv_id)

    @pytest.mark.asyncio
    async def test_clear_context_removes_selected_row(self, populated_context):
        """Clear context should remove selected row."""
        context = populated_context("selected-row-test")
        context.selected_forecast_row = {
            "main_lob": "Amisys Medicaid Domestic",
            "state": "CA",
            "case_type": "Claims Processing"
        }
        context.selected_row_key = "Amisys Medicaid Domestic|CA|Claims Processing"

        # Clear selected row
        context.clear_selected_row()

        assert context.selected_forecast_row is None
        assert context.selected_row_key is None

    @pytest.mark.asyncio
    async def test_new_chat_triggers_context_clear(self, mock_consumer, mock_context_manager):
        """New chat handler should clear old context."""
        old_conv_id = "old-conv-uuid-123"

        # Setup: Mock the context manager
        with patch('chat_app.consumers.get_context_manager', return_value=mock_context_manager):
            # Mock create_new_conversation
            mock_consumer.create_new_conversation = AsyncMock(return_value="new-conv-uuid-456")
            mock_consumer.mark_conversation_inactive = AsyncMock()

            # Call handle_new_conversation
            await mock_consumer.handle_new_conversation({
                'old_conversation_id': old_conv_id
            })

            # Verify context was cleared for old conversation
            mock_context_manager.clear_context.assert_called_once_with(old_conv_id)


class TestContextIsolation:
    """Test that contexts are isolated between conversations."""

    @pytest.mark.asyncio
    async def test_different_conversations_have_separate_contexts(self, fresh_context):
        """Two conversations should not share context."""
        context1 = fresh_context("conv-1")
        context1.active_platforms = ["Amisys"]

        context2 = fresh_context("conv-2")
        context2.active_platforms = ["Facets"]

        # Verify isolation
        assert context1.active_platforms == ["Amisys"]
        assert context2.active_platforms == ["Facets"]
        assert context1.conversation_id != context2.conversation_id

    @pytest.mark.asyncio
    async def test_context_tied_to_conversation_id(self, fresh_context):
        """Context should be uniquely identified by conversation_id."""
        context = fresh_context("unique-id-test")

        assert context.conversation_id == "unique-id-test"

    @pytest.mark.asyncio
    async def test_modifying_one_context_doesnt_affect_another(
        self,
        populated_context
    ):
        """Modifying one context should not affect another."""
        context1 = populated_context(
            conversation_id="context-1",
            platforms=["Amisys"],
            month=3,
            year=2025
        )

        context2 = populated_context(
            conversation_id="context-2",
            platforms=["Facets"],
            month=4,
            year=2025
        )

        # Modify context1
        context1.active_platforms.append("Xcelys")
        context1.active_states = ["CA", "TX"]

        # Verify context2 is unchanged
        assert context2.active_platforms == ["Facets"]
        assert context2.active_states == ["CA", "TX"]  # Original default


class TestContextPersistence:
    """Test context persistence to database."""

    @pytest.mark.asyncio
    async def test_context_survives_cache_clear(self, mock_context_manager, populated_context):
        """Context should be recoverable from database after cache clear."""
        conv_id = "persistence-test"

        # Setup context
        context = populated_context(
            conversation_id=conv_id,
            platforms=["Amisys"],
            month=3,
            year=2025
        )

        # Simulate save to database
        await mock_context_manager.save_context(context)

        # Verify save was called
        mock_context_manager.save_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_model_serialization(self, populated_context):
        """Context should serialize to/from JSON correctly."""
        context = populated_context(
            conversation_id="serialize-test",
            platforms=["Amisys", "Facets"],
            markets=["Medicaid"],
            month=3,
            year=2025
        )

        # Serialize
        json_str = context.model_dump_json()

        # Deserialize
        restored = ConversationContext.model_validate_json(json_str)

        assert restored.conversation_id == context.conversation_id
        assert restored.active_platforms == context.active_platforms
        assert restored.forecast_report_month == context.forecast_report_month


class TestSelectedRowPersistence:
    """Test selected row persistence rules."""

    def test_selected_row_persists_within_same_report(self, populated_context):
        """Selected row should persist within same report type."""
        context = populated_context("row-persist-test")
        context.active_report_type = "forecast"

        row_data = {
            "main_lob": "Amisys Medicaid Domestic",
            "state": "CA",
            "case_type": "Claims Processing"
        }
        context.update_selected_row(row_data)

        # Verify persistence
        assert context.selected_forecast_row == row_data
        assert context.selected_row_key == "Amisys Medicaid Domestic|CA|Claims Processing"

    def test_selected_row_cleared_on_report_type_change(self, populated_context):
        """Selected row should clear when report type changes."""
        context = populated_context("row-clear-test")
        context.active_report_type = "forecast"

        row_data = {"main_lob": "Test", "state": "CA", "case_type": "Claims"}
        context.update_selected_row(row_data)

        # Check if should clear when changing to roster
        should_clear = context.should_clear_selected_row(new_report_type="roster")

        assert should_clear is True

    def test_selected_row_cleared_on_different_row_selection(self, populated_context):
        """Selecting different row should clear previous selection."""
        context = populated_context("row-replace-test")

        row1 = {"main_lob": "Row1", "state": "CA", "case_type": "Claims"}
        context.update_selected_row(row1)
        row1_key = context.selected_row_key

        # New row with different key
        new_row_key = "Row2|TX|Enrollment"

        should_clear = context.should_clear_selected_row(new_row_key=new_row_key)

        assert should_clear is True


class TestContextSummary:
    """Test context summary generation for LLM."""

    def test_summary_includes_period(self, populated_context):
        """Summary should include report period."""
        context = populated_context(month=3, year=2025)

        summary = context.get_context_summary_for_llm()

        assert "March" in summary
        assert "2025" in summary

    def test_summary_includes_filters(self, populated_context):
        """Summary should include active filters."""
        context = populated_context(platforms=["Amisys"], markets=["Medicaid"])

        summary = context.get_context_summary_for_llm()

        assert "Amisys" in summary
        assert "Medicaid" in summary

    def test_summary_includes_states(self, populated_context):
        """Summary should include active states."""
        context = populated_context()
        context.active_states = ["CA", "TX", "FL"]

        summary = context.get_context_summary_for_llm()

        assert "CA" in summary or "States" in summary

    def test_empty_context_summary(self, fresh_context):
        """Empty context should return 'No context set'."""
        context = fresh_context("empty-summary-test")

        summary = context.get_context_summary_for_llm()

        assert summary == "No context set"


class TestLegacyFieldSync:
    """Test backward compatibility with legacy field names."""

    def test_sync_new_to_legacy_fields(self, fresh_context):
        """New field values should sync to legacy fields."""
        context = fresh_context("sync-test")

        # Set new fields
        context.forecast_report_month = 3
        context.forecast_report_year = 2025

        # Sync
        context.sync_legacy_fields()

        # Verify legacy fields
        assert context.current_forecast_month == 3
        assert context.current_forecast_year == 2025

    def test_sync_legacy_to_new_fields(self, fresh_context):
        """Legacy field values should sync to new fields."""
        context = fresh_context("sync-legacy-test")

        # Set legacy fields
        context.current_forecast_month = 4
        context.current_forecast_year = 2024

        # Sync
        context.sync_legacy_fields()

        # Verify new fields
        assert context.forecast_report_month == 4
        assert context.forecast_report_year == 2024


# Run tests with pytest
if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
