"""
Pytest Configuration and Fixtures for Chat App Tests

Provides fixtures for:
- LLM service mocking
- Context manager mocking
- Database fixtures
- API response mocking
"""
import os
import sys
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Configure Django settings before importing Django modules
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'centene_forecast_project.settings')

import django
django.setup()

from chat_app.services.tools.validation import (
    IntentCategory,
    IntentClassification,
    ConversationContext,
    ForecastQueryParams
)


# ===== INTENT CLASSIFICATION FIXTURES =====

@pytest.fixture
def mock_intent_classification():
    """Factory fixture for creating mock IntentClassification objects."""
    def _create(
        category: IntentCategory,
        confidence: float = 0.95,
        reasoning: str = "Test classification",
        requires_clarification: bool = False,
        missing_parameters: list = None
    ) -> IntentClassification:
        return IntentClassification(
            category=category,
            confidence=confidence,
            reasoning=reasoning,
            requires_clarification=requires_clarification,
            missing_parameters=missing_parameters or []
        )
    return _create


@pytest.fixture
def mock_forecast_params():
    """Factory fixture for creating mock ForecastQueryParams."""
    def _create(
        month: int = 3,
        year: int = 2025,
        platforms: list = None,
        markets: list = None,
        states: list = None,
        case_types: list = None,
        **kwargs
    ) -> ForecastQueryParams:
        return ForecastQueryParams(
            month=month,
            year=year,
            platforms=platforms,
            markets=markets,
            states=states,
            case_types=case_types,
            **kwargs
        )
    return _create


# ===== CONTEXT MANAGER FIXTURES =====

@pytest.fixture
def mock_context_manager():
    """Mock context manager for isolated testing."""
    manager = AsyncMock()

    # Default context for new conversations
    default_context = ConversationContext(conversation_id="test-123")
    manager.get_context.return_value = default_context
    manager.save_context.return_value = None
    manager.clear_context.return_value = None
    manager.update_entities.return_value = None
    manager.reset_filters.return_value = default_context

    return manager


@pytest.fixture
def fresh_context():
    """Create a fresh ConversationContext for testing."""
    def _create(conversation_id: str = "test-conv-123") -> ConversationContext:
        return ConversationContext(conversation_id=conversation_id)
    return _create


@pytest.fixture
def populated_context():
    """Create a ConversationContext with sample data."""
    def _create(
        conversation_id: str = "test-conv-123",
        platforms: list = None,
        markets: list = None,
        states: list = None,
        localities: list = None,
        case_types: list = None,
        month: int = 3,
        year: int = 2025
    ) -> ConversationContext:
        context = ConversationContext(
            conversation_id=conversation_id,
            active_report_type='forecast',
            forecast_report_month=month,
            forecast_report_year=year,
            active_platforms=platforms or ["Amisys"],
            active_markets=markets or ["Medicaid"],
            active_localities=localities or ["Domestic"],
            active_states=states or ["CA", "TX"],
            active_case_types=case_types or ["Claims Processing"],
        )
        return context
    return _create


# ===== LLM SERVICE FIXTURES =====

@pytest_asyncio.fixture
async def mock_llm_service():
    """Mock LLM service for testing without actual API calls."""
    with patch('chat_app.services.llm_service.ChatOpenAI') as mock_openai:
        # Mock the LLM responses
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock()
        mock_openai.return_value = mock_llm

        from chat_app.services.llm_service import LLMService

        # Patch the context manager
        with patch('chat_app.services.llm_service.get_context_manager') as mock_cm:
            mock_cm_instance = AsyncMock()
            mock_cm_instance.get_context.return_value = ConversationContext(conversation_id="test-123")
            mock_cm.return_value = mock_cm_instance

            service = LLMService()
            service.context_manager = mock_cm_instance

            yield service


@pytest_asyncio.fixture
async def mock_chat_service():
    """Mock chat service for testing message processing."""
    with patch('chat_app.services.chat_service.get_llm_service') as mock_get_llm:
        mock_llm_service = AsyncMock()
        mock_get_llm.return_value = mock_llm_service

        from chat_app.services.chat_service import ChatService

        service = ChatService()
        service.llm_service = mock_llm_service

        yield service


# ===== API RESPONSE FIXTURES =====

@pytest.fixture
def mock_forecast_api_response():
    """Factory fixture for creating mock forecast API responses."""
    def _create(
        record_count: int = 10,
        months: dict = None
    ) -> dict:
        if months is None:
            months = {
                "Month1": "Apr-25",
                "Month2": "May-25",
                "Month3": "Jun-25",
                "Month4": "Jul-25",
                "Month5": "Aug-25",
                "Month6": "Sep-25"
            }

        records = []
        for i in range(record_count):
            record = {
                'id': i + 1,
                'main_lob': f"Amisys Medicaid {'Domestic' if i % 2 == 0 else 'Global'}",
                'state': ['CA', 'TX', 'FL', 'NY', 'GA'][i % 5],
                'case_type': 'Claims Processing',
                'target_cph': 3.5,
                'months': {
                    month_name: {
                        'forecast': 1000 + i * 100,
                        'fte_required': 10 + i,
                        'fte_available': 8 + i,
                        'capacity': 900 + i * 90,
                        'gap': -100 - i * 10
                    }
                    for month_name in months.values()
                }
            }
            records.append(record)

        return {
            'records': records,
            'total_records': record_count,
            'months': months,
            'totals': {
                month_name: {
                    'forecast_total': sum(r['months'][month_name]['forecast'] for r in records),
                    'fte_required_total': sum(r['months'][month_name]['fte_required'] for r in records),
                    'fte_available_total': sum(r['months'][month_name]['fte_available'] for r in records),
                    'capacity_total': sum(r['months'][month_name]['capacity'] for r in records),
                    'gap_total': sum(r['months'][month_name]['gap'] for r in records)
                }
                for month_name in months.values()
            }
        }
    return _create


@pytest.fixture
def mock_available_reports_response():
    """Factory fixture for creating mock available reports API response."""
    def _create(report_count: int = 3) -> dict:
        reports = []
        for i in range(report_count):
            month_num = ((i % 12) + 1)
            year = 2025 if i < 12 else 2024
            import calendar
            month_name = calendar.month_name[month_num]

            reports.append({
                'month': month_name,
                'year': year,
                'is_valid': i < 2,  # First 2 are current
                'records_count': 100 + i * 50,
                'data_freshness': f"{i + 1} day{'s' if i > 0 else ''} ago"
            })

        return {
            'reports': reports,
            'total_reports': report_count
        }
    return _create


# ===== DATABASE FIXTURES =====

@pytest.fixture
def mock_db_conversation():
    """Mock ChatConversation model instance."""
    conversation = MagicMock()
    conversation.id = "test-conv-uuid-123"
    conversation.user = MagicMock()
    conversation.user.portal_id = "test_user"
    conversation.is_active = True
    conversation.title = "Test Chat"
    conversation.created_at = datetime.now()
    conversation.updated_at = datetime.now()
    return conversation


@pytest.fixture
def mock_db_message():
    """Factory fixture for creating mock ChatMessage instances."""
    def _create(
        role: str = "user",
        content: str = "Test message",
        conversation_id: str = "test-conv-uuid-123"
    ):
        message = MagicMock()
        message.id = 1
        message.role = role
        message.content = content
        message.conversation_id = conversation_id
        message.created_at = datetime.now()
        message.metadata = {}
        return message
    return _create


# ===== CONSUMER FIXTURES =====

@pytest_asyncio.fixture
async def mock_consumer():
    """Mock WebSocket consumer for testing."""
    from chat_app.consumers import ChatConsumer

    consumer = ChatConsumer()
    consumer.user = MagicMock()
    consumer.user.portal_id = "test_user"
    consumer.user.is_authenticated = True
    consumer.conversation_id = "test-conv-uuid-123"
    consumer.chat_service = AsyncMock()
    consumer.send_json = AsyncMock()
    consumer.send_error = AsyncMock()

    return consumer


# ===== PYTEST CONFIGURATION =====

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow-running"
    )


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # Reset context manager singleton
    import chat_app.utils.context_manager as cm_module
    cm_module._context_manager = None

    yield

    # Cleanup after test
    cm_module._context_manager = None
