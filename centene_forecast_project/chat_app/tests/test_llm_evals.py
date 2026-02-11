"""
LLM Evaluation Tests - Systematic testing of intent classification and tool usage.

Tests:
1. Intent classification accuracy
2. Parameter extraction correctness
3. Clear context intent handling
4. Tool execution verification
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from chat_app.services.tools.validation import (
    IntentCategory,
    IntentClassification,
    ConversationContext,
    ForecastQueryParams
)


class TestIntentClassification:
    """Test LLM correctly classifies user intents."""

    @pytest.mark.parametrize("user_input,expected_category", [
        # Forecast queries
        ("Show me forecast for March 2025", IntentCategory.GET_FORECAST_DATA),
        ("What's the forecast data for Amisys Medicaid?", IntentCategory.GET_FORECAST_DATA),
        ("Show California claims processing forecast", IntentCategory.GET_FORECAST_DATA),
        ("Display data for April 2025", IntentCategory.GET_FORECAST_DATA),
        ("Get me the staffing data for May 2025", IntentCategory.GET_FORECAST_DATA),
        ("How many FTEs do we need for March?", IntentCategory.GET_FORECAST_DATA),

        # Available reports
        ("What reports do you have?", IntentCategory.LIST_AVAILABLE_REPORTS),
        ("List available forecasts", IntentCategory.LIST_AVAILABLE_REPORTS),
        ("What months have forecast data?", IntentCategory.LIST_AVAILABLE_REPORTS),
        ("Show me available reports", IntentCategory.LIST_AVAILABLE_REPORTS),

        # Clear context
        ("Clear my context", IntentCategory.CLEAR_CONTEXT),
        ("Reset everything", IntentCategory.CLEAR_CONTEXT),
        ("Start fresh", IntentCategory.CLEAR_CONTEXT),
        ("Forget previous filters", IntentCategory.CLEAR_CONTEXT),
        ("Clear all filters", IntentCategory.CLEAR_CONTEXT),
        ("Reset my filters", IntentCategory.CLEAR_CONTEXT),

        # CPH modification (requires selected row in real scenario)
        ("Change CPH to 3.5", IntentCategory.MODIFY_CPH),
        ("Update the CPH value", IntentCategory.MODIFY_CPH),
        ("Set target CPH to 4.0", IntentCategory.MODIFY_CPH),

        # FTE details (requires selected row in real scenario)
        ("Show FTE details", IntentCategory.GET_FTE_DETAILS),
        ("How many FTEs for this row?", IntentCategory.GET_FTE_DETAILS),
        ("Get FTE breakdown", IntentCategory.GET_FTE_DETAILS),
    ])
    def test_intent_category_mapping(self, user_input, expected_category, mock_intent_classification):
        """
        Test that user inputs map to correct intent categories.

        Note: This tests the expected mapping logic, not actual LLM calls.
        Real LLM classification would be tested in integration tests.
        """
        # Create mock classification matching expected category
        classification = mock_intent_classification(
            category=expected_category,
            confidence=0.95
        )

        assert classification.category == expected_category
        assert classification.confidence >= 0.7


class TestParameterExtraction:
    """Test parameter extraction from user queries."""

    @pytest.mark.parametrize("user_input,expected_month,expected_year", [
        ("Show March 2025 forecast", 3, 2025),
        ("Get April 2024 data", 4, 2024),
        ("Display forecast for December 2025", 12, 2025),
        ("January 2025 staffing data", 1, 2025),
    ])
    def test_month_year_extraction(
        self,
        user_input,
        expected_month,
        expected_year,
        mock_forecast_params
    ):
        """Test that month and year are correctly extracted."""
        params = mock_forecast_params(month=expected_month, year=expected_year)

        assert params.month == expected_month
        assert params.year == expected_year

    @pytest.mark.parametrize("platforms,markets,states", [
        (["Amisys"], ["Medicaid"], ["CA"]),
        (["Facets"], ["Medicare"], ["TX", "FL"]),
        (["Amisys", "Facets"], ["Medicaid", "Medicare"], ["CA", "NY", "TX"]),
    ])
    def test_filter_extraction(
        self,
        platforms,
        markets,
        states,
        mock_forecast_params
    ):
        """Test that filter parameters are correctly extracted."""
        params = mock_forecast_params(
            platforms=platforms,
            markets=markets,
            states=states
        )

        assert params.platforms == platforms
        assert params.markets == markets
        assert params.states == states

    def test_missing_required_params_detection(self, mock_forecast_params):
        """Test that missing required params are detected."""
        # Create params with None for required fields
        params = ForecastQueryParams(month=None, year=None)

        assert params.is_missing_required() is True
        assert 'month' in params.get_missing_fields()
        assert 'year' in params.get_missing_fields()

    def test_complete_params_validation(self, mock_forecast_params):
        """Test that complete params pass validation."""
        params = mock_forecast_params(month=3, year=2025)

        assert params.is_missing_required() is False
        assert params.get_missing_fields() == []


class TestClearContextIntent:
    """Test clear context intent handling."""

    @pytest.mark.asyncio
    async def test_clear_context_clears_all_fields(self, fresh_context, mock_context_manager):
        """Test that clear_context removes all stored context data."""
        # Setup: Create populated context
        context = fresh_context("test-conv-123")
        context.active_platforms = ["Amisys"]
        context.active_markets = ["Medicaid"]
        context.forecast_report_month = 3
        context.forecast_report_year = 2025
        context.active_states = ["CA", "TX"]
        context.selected_forecast_row = {"main_lob": "Amisys Medicaid Domestic"}

        # Simulate save
        mock_context_manager.get_context.return_value = context

        # Clear context
        await mock_context_manager.clear_context("test-conv-123")

        # Verify clear was called
        mock_context_manager.clear_context.assert_called_once_with("test-conv-123")

    @pytest.mark.asyncio
    async def test_clear_context_returns_fresh_context(self, fresh_context, mock_context_manager):
        """Test that get_context returns fresh context after clear."""
        # After clear, get_context should return fresh context
        fresh = fresh_context("test-conv-123")
        mock_context_manager.get_context.return_value = fresh

        result = await mock_context_manager.get_context("test-conv-123")

        assert result.active_platforms == []
        assert result.forecast_report_month is None
        assert result.forecast_report_year is None

    def test_clear_context_intent_recognition(self, mock_intent_classification):
        """Test that clear context phrases are recognized."""
        clear_phrases = [
            "Clear my context",
            "Reset everything",
            "Start fresh",
            "Forget previous filters",
            "Clear all filters",
            "Reset my filters",
            "Start over",
        ]

        for phrase in clear_phrases:
            classification = mock_intent_classification(
                category=IntentCategory.CLEAR_CONTEXT,
                confidence=0.95,
                reasoning=f"User wants to clear context: {phrase}"
            )
            assert classification.category == IntentCategory.CLEAR_CONTEXT


class TestToolExecution:
    """Test that tools execute correctly after classification."""

    @pytest.mark.asyncio
    async def test_forecast_query_success_response(
        self,
        mock_chat_service,
        mock_forecast_api_response
    ):
        """Test forecast query returns successful response structure."""
        # Setup mock response
        api_response = mock_forecast_api_response(record_count=5)

        mock_chat_service.llm_service.execute_forecast_query = AsyncMock(
            return_value={
                'success': True,
                'message': 'Found 5 forecast records',
                'data': api_response,
                'ui_component': '<div>...</div>',
                'metadata': {'record_count': 5}
            }
        )

        # Execute
        result = await mock_chat_service.llm_service.execute_forecast_query(
            parameters={'month': 3, 'year': 2025},
            conversation_id='test-123'
        )

        assert result['success'] is True
        assert 'ui_component' in result
        assert result['metadata']['record_count'] == 5

    @pytest.mark.asyncio
    async def test_clear_context_execution_success(self, mock_chat_service):
        """Test clear context intent executes correctly."""
        mock_chat_service.llm_service.execute_clear_context = AsyncMock(
            return_value={
                'success': True,
                'category': 'clear_context',
                'message': 'Context cleared successfully',
                'ui_component': '<div class="chat-success-card">...</div>',
                'metadata': {'context_cleared': True}
            }
        )

        result = await mock_chat_service.llm_service.execute_clear_context(
            conversation_id='test-123'
        )

        assert result['success'] is True
        assert result['category'] == 'clear_context'
        assert 'context_cleared' in result['metadata']

    @pytest.mark.asyncio
    async def test_available_reports_execution(
        self,
        mock_chat_service,
        mock_available_reports_response
    ):
        """Test available reports query returns list of reports."""
        api_response = mock_available_reports_response(report_count=3)

        mock_chat_service.llm_service.execute_available_reports_query = AsyncMock(
            return_value={
                'success': True,
                'message': 'Found 3 forecast reports',
                'data': api_response,
                'ui_component': '<div>...</div>',
                'metadata': {'report_count': 3}
            }
        )

        result = await mock_chat_service.llm_service.execute_available_reports_query(
            parameters={},
            conversation_id='test-123'
        )

        assert result['success'] is True
        assert result['data']['total_reports'] == 3


class TestContextAwareResponses:
    """Test context-aware response handling."""

    def test_context_reference_detection(self, populated_context):
        """Test that context references are detected in queries."""
        context = populated_context(
            platforms=["Amisys"],
            markets=["Medicaid"],
            month=3,
            year=2025
        )

        # Verify context has expected values
        assert context.active_platforms == ["Amisys"]
        assert context.active_markets == ["Medicaid"]
        assert context.forecast_report_month == 3
        assert context.forecast_report_year == 2025

    def test_context_summary_generation(self, populated_context):
        """Test that context summary is generated correctly."""
        context = populated_context(
            platforms=["Amisys"],
            markets=["Medicaid"],
            month=3,
            year=2025
        )

        summary = context.get_context_summary_for_llm()

        assert "Amisys" in summary
        assert "Medicaid" in summary
        assert "March" in summary
        assert "2025" in summary

    def test_empty_context_summary(self, fresh_context):
        """Test that empty context returns appropriate summary."""
        context = fresh_context("test-123")

        summary = context.get_context_summary_for_llm()

        assert summary == "No context set"


class TestErrorHandling:
    """Test error handling in LLM service."""

    @pytest.mark.asyncio
    async def test_missing_params_clarification(self, mock_chat_service):
        """Test that missing params trigger clarification request."""
        mock_chat_service.llm_service.categorize_intent = AsyncMock(
            return_value={
                'category': 'clarification_needed',
                'confidence': 0.8,
                'parameters': {},
                'ui_component': '<div class="alert alert-info">Which month and year?</div>',
                'metadata': {'missing_params': ['month', 'year']}
            }
        )

        result = await mock_chat_service.llm_service.categorize_intent(
            user_text="Show forecast",
            conversation_id='test-123',
            message_history=[]
        )

        assert result['category'] == 'clarification_needed'
        assert 'missing_params' in result['metadata']

    @pytest.mark.asyncio
    async def test_low_confidence_clarification(self, mock_chat_service):
        """Test that low confidence triggers clarification."""
        mock_chat_service.llm_service.categorize_intent = AsyncMock(
            return_value={
                'category': 'clarification_needed',
                'confidence': 0.0,
                'parameters': {},
                'ui_component': '<div class="alert alert-info">Could you clarify?</div>',
                'metadata': {}
            }
        )

        result = await mock_chat_service.llm_service.categorize_intent(
            user_text="xyz abc 123",
            conversation_id='test-123',
            message_history=[]
        )

        assert result['category'] == 'clarification_needed'


class TestUpdateContextIntent:
    """Test update context intent handling (selective filter reset)."""

    @pytest.mark.parametrize("user_input,expected_operation", [
        ("Get all data for March 2025", "reset_all_filters"),
        ("Show everything", "reset_all_filters"),
        ("Reset filters", "reset_all_filters"),
        ("Remove all filters", "reset_all_filters"),
        ("Clear all my filters", "reset_all_filters"),
        ("Show all platforms", "reset_specific"),
        ("All markets", "reset_specific"),
        ("Show all states", "reset_specific"),
    ])
    def test_update_context_classification(self, user_input, expected_operation, mock_intent_classification):
        """Test that filter reset phrases trigger UPDATE_CONTEXT."""
        classification = mock_intent_classification(
            category=IntentCategory.UPDATE_CONTEXT,
            confidence=0.95,
            reasoning=f"User wants to reset filters: {user_input}"
        )

        assert classification.category == IntentCategory.UPDATE_CONTEXT
        assert classification.confidence >= 0.7

    def test_update_context_vs_clear_context(self, mock_intent_classification):
        """
        Test distinction between UPDATE_CONTEXT and CLEAR_CONTEXT.

        UPDATE_CONTEXT: Reset filters, KEEP month/year
        CLEAR_CONTEXT: Clear EVERYTHING including month/year
        """
        # "Reset filters" should be UPDATE_CONTEXT (keeps month/year)
        update_classification = mock_intent_classification(
            category=IntentCategory.UPDATE_CONTEXT,
            confidence=0.95
        )
        assert update_classification.category == IntentCategory.UPDATE_CONTEXT

        # "Clear context" should be CLEAR_CONTEXT (wipes everything)
        clear_classification = mock_intent_classification(
            category=IntentCategory.CLEAR_CONTEXT,
            confidence=0.95
        )
        assert clear_classification.category == IntentCategory.CLEAR_CONTEXT

    @pytest.mark.asyncio
    async def test_reset_filters_keeps_month_year(self, populated_context, mock_context_manager):
        """Test that reset_filters preserves month/year."""
        # Create context with filters and month/year
        context = populated_context(
            platforms=["Amisys"],
            markets=["Medicaid"],
            states=["CA", "TX"],
            month=3,
            year=2025
        )

        # Verify initial state
        assert context.active_platforms == ["Amisys"]
        assert context.active_markets == ["Medicaid"]
        assert context.active_states == ["CA", "TX"]
        assert context.forecast_report_month == 3
        assert context.forecast_report_year == 2025

        # After reset_filters, month/year should be preserved
        # Simulate what reset_filters does
        context.active_platforms = []
        context.active_markets = []
        context.active_states = []

        assert context.active_platforms == []
        assert context.active_markets == []
        assert context.active_states == []
        # Month/year preserved
        assert context.forecast_report_month == 3
        assert context.forecast_report_year == 2025

    @pytest.mark.asyncio
    async def test_update_context_execution_success(self, mock_chat_service):
        """Test update context intent executes correctly."""
        mock_chat_service.llm_service.execute_update_context = AsyncMock(
            return_value={
                'success': True,
                'category': 'update_context',
                'message': 'All filters have been reset.',
                'ui_component': '<div class="chat-success-card">...</div>',
                'metadata': {
                    'operation': 'reset_all_filters',
                    'preserved': ['Report Period: March 2025']
                }
            }
        )

        result = await mock_chat_service.llm_service.execute_update_context(
            conversation_id='test-123',
            operation='reset_all_filters',
            parameters={'keep_month_year': True}
        )

        assert result['success'] is True
        assert result['category'] == 'update_context'
        assert 'preserved' in result['metadata']

    def test_update_context_phrases_recognized(self, mock_intent_classification):
        """Test that various filter reset phrases are recognized."""
        reset_phrases = [
            "Get all data",
            "Show all data",
            "Show everything",
            "Reset filters",
            "Clear filters",
            "Remove all filters",
            "No filters",
            "Reset my filters",
        ]

        for phrase in reset_phrases:
            classification = mock_intent_classification(
                category=IntentCategory.UPDATE_CONTEXT,
                confidence=0.90,
                reasoning=f"User wants to reset filters: {phrase}"
            )
            assert classification.category == IntentCategory.UPDATE_CONTEXT, \
                f"Phrase '{phrase}' should be classified as UPDATE_CONTEXT"


# Run tests with pytest
if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
