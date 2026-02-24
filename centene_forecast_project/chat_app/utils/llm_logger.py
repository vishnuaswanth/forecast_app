"""
LLM Workflow Logger - Comprehensive logging for LLM workflow debugging.

Provides structured JSON logging for the full LLM workflow including:
- User inputs (sanitized)
- LLM prompts and responses
- Intent classification
- Parameter extraction
- Validation results
- Query execution
- Error tracking

All logs use correlation IDs to trace full request lifecycle.
"""

import json
import logging
import time
import traceback
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from contextvars import ContextVar
from dataclasses import dataclass, field, asdict
from functools import wraps

from django.conf import settings


# Context variables for request propagation through async calls
_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
_conversation_id: ContextVar[Optional[str]] = ContextVar('conversation_id', default=None)


# =============================================================================
# CONFIGURATION
# =============================================================================

def get_llm_logging_config() -> dict:
    """Get LLM logging configuration from settings with defaults."""
    return getattr(settings, 'LLM_LOGGING_CONFIG', {
        'enabled': True,
        'log_level': 'DEBUG' if getattr(settings, 'DEBUG', False) else 'INFO',
        'log_full_prompts': getattr(settings, 'DEBUG', False),
        'log_full_responses': getattr(settings, 'DEBUG', False),
        'max_preview_length': 500,
        'redact_api_keys': True,
        'redact_user_pii': not getattr(settings, 'DEBUG', False),
    })


# =============================================================================
# LOG DATA REDACTOR
# =============================================================================

class LogDataRedactor:
    """Redacts sensitive data from log entries."""

    # Patterns for sensitive data
    API_KEY_PATTERNS = [
        re.compile(r'(sk-[a-zA-Z0-9]{20,})'),  # OpenAI API keys
        re.compile(r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([^"\'\s]+)', re.IGNORECASE),
        re.compile(r'(bearer\s+)([a-zA-Z0-9._-]+)', re.IGNORECASE),
        re.compile(r'(authorization["\']?\s*[:=]\s*["\']?)([^"\'\s]+)', re.IGNORECASE),
    ]

    PII_PATTERNS = [
        re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),  # Email
        re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),  # Phone number
        re.compile(r'\b\d{3}[-]?\d{2}[-]?\d{4}\b'),  # SSN
    ]

    def __init__(self, redact_api_keys: bool = True, redact_pii: bool = False):
        self.redact_api_keys = redact_api_keys
        self.redact_pii = redact_pii

    def redact(self, data: Any) -> Any:
        """Redact sensitive data from any data structure."""
        if isinstance(data, str):
            return self._redact_string(data)
        elif isinstance(data, dict):
            return {k: self.redact(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.redact(item) for item in data]
        return data

    def _redact_string(self, text: str) -> str:
        """Redact sensitive patterns from a string."""
        if not text:
            return text

        result = text

        # Redact API keys
        if self.redact_api_keys:
            for pattern in self.API_KEY_PATTERNS:
                result = pattern.sub(r'\1[REDACTED]', result)

        # Redact PII
        if self.redact_pii:
            for pattern in self.PII_PATTERNS:
                result = pattern.sub('[REDACTED_PII]', result)

        return result


# =============================================================================
# CORRELATION CONTEXT
# =============================================================================

@dataclass
class CorrelationContext:
    """Context for correlation ID propagation through async calls."""

    correlation_id: str
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    user_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)

    def __enter__(self):
        self._corr_token = _correlation_id.set(self.correlation_id)
        self._conv_token = _conversation_id.set(self.conversation_id) if self.conversation_id else None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _correlation_id.reset(self._corr_token)
        if self._conv_token is not None:
            _conversation_id.reset(self._conv_token)
        return False

    async def __aenter__(self):
        self._corr_token = _correlation_id.set(self.correlation_id)
        self._conv_token = _conversation_id.set(self.conversation_id) if self.conversation_id else None
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        _correlation_id.reset(self._corr_token)
        if self._conv_token is not None:
            _conversation_id.reset(self._conv_token)
        return False


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return _correlation_id.get()


def get_conversation_id() -> Optional[str]:
    """Get current conversation ID from context."""
    return _conversation_id.get()


def create_correlation_id(
    conversation_id: Optional[str] = None,
    message_id: Optional[str] = None
) -> str:
    """
    Create a correlation ID for request tracing.

    Format: {conversation_id_prefix}-{message_id_prefix}-{timestamp}
    """
    conv_prefix = (conversation_id or 'none')[:8]
    msg_prefix = (message_id or 'none')[:8]
    timestamp = int(time.time() * 1000)  # Milliseconds
    return f"{conv_prefix}-{msg_prefix}-{timestamp}"


# =============================================================================
# JSON FORMATTER
# =============================================================================

class LLMLogFormatter(logging.Formatter):
    """Custom JSON formatter for structured LLM workflow logs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config = get_llm_logging_config()
        self.redactor = LogDataRedactor(
            redact_api_keys=config.get('redact_api_keys', True),
            redact_pii=config.get('redact_user_pii', False)
        )

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log entry
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
        }

        # Add correlation ID if available
        correlation_id = get_correlation_id()
        if correlation_id:
            log_entry['correlation_id'] = correlation_id

        # Add extra fields from record
        if hasattr(record, 'correlation_id'):
            log_entry['correlation_id'] = record.correlation_id
        if hasattr(record, 'conversation_id'):
            log_entry['conversation_id'] = record.conversation_id
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'event'):
            log_entry['event'] = record.event
        if hasattr(record, 'data'):
            log_entry['data'] = self.redactor.redact(record.data)

        # Add message if not structured data
        if record.msg and not hasattr(record, 'data'):
            log_entry['message'] = self.redactor.redact(record.getMessage())

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str, ensure_ascii=False)


# =============================================================================
# LLM WORKFLOW LOGGER
# =============================================================================

class LLMWorkflowLogger:
    """
    Main logger for LLM workflow events.

    Provides structured logging methods for each stage of LLM processing.
    All methods accept a correlation_id for request tracing.
    """

    def __init__(self, logger_name: str = 'llm_workflow'):
        self.logger = logging.getLogger(logger_name)
        self.config = get_llm_logging_config()
        self.redactor = LogDataRedactor(
            redact_api_keys=self.config.get('redact_api_keys', True),
            redact_pii=self.config.get('redact_user_pii', False)
        )

    def _log(
        self,
        level: int,
        event: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> None:
        """Internal logging method with structured data."""
        if not self.config.get('enabled', True):
            return

        # Create log record with extra fields
        extra = {
            'event': event,
            'data': data,
        }

        if correlation_id:
            extra['correlation_id'] = correlation_id
        elif get_correlation_id():
            extra['correlation_id'] = get_correlation_id()

        if conversation_id:
            extra['conversation_id'] = conversation_id
        elif get_conversation_id():
            extra['conversation_id'] = get_conversation_id()

        if user_id:
            extra['user_id'] = user_id

        self.logger.log(level, '', extra=extra)

    def _truncate(self, text: str, max_length: Optional[int] = None) -> str:
        """Truncate text to max length for non-debug logging."""
        max_len = max_length or self.config.get('max_preview_length', 500)
        if len(text) <= max_len:
            return text
        return text[:max_len] + f'... [truncated, {len(text)} total chars]'

    # -------------------------------------------------------------------------
    # USER INPUT LOGGING
    # -------------------------------------------------------------------------

    def log_user_input(
        self,
        correlation_id: str,
        raw_input: str,
        sanitized_input: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> None:
        """Log user input received for processing."""
        data = {
            'raw_input_length': len(raw_input),
            'sanitized_input_length': len(sanitized_input),
            'was_modified': raw_input != sanitized_input,
        }

        # Include full input only in DEBUG mode
        if self.config.get('log_full_prompts', False):
            data['raw_input'] = raw_input
            data['sanitized_input'] = sanitized_input
        else:
            data['input_preview'] = self._truncate(sanitized_input)

        if context:
            data['context'] = context

        self._log(
            logging.INFO,
            'user_input_received',
            data,
            correlation_id=correlation_id,
            conversation_id=conversation_id,
            user_id=user_id
        )

    # -------------------------------------------------------------------------
    # LLM REQUEST/RESPONSE LOGGING
    # -------------------------------------------------------------------------

    def log_llm_request(
        self,
        correlation_id: str,
        model: str,
        messages: List[Dict[str, Any]],
        config: Optional[Dict[str, Any]] = None,
        request_type: str = 'chat_completion'
    ) -> None:
        """Log LLM API request."""
        data = {
            'model': model,
            'request_type': request_type,
            'message_count': len(messages),
        }

        if config:
            # Redact any API keys in config
            data['config'] = self.redactor.redact(config)

        # Include full messages only in DEBUG mode
        if self.config.get('log_full_prompts', False):
            data['messages'] = messages
        else:
            # Log message roles and truncated content
            data['messages_preview'] = [
                {
                    'role': msg.get('role', 'unknown'),
                    'content_preview': self._truncate(str(msg.get('content', ''))[:200])
                }
                for msg in messages[:5]  # First 5 messages only
            ]
            if len(messages) > 5:
                data['messages_truncated'] = True

        self._log(logging.DEBUG, 'llm_request', data, correlation_id=correlation_id)

    def log_llm_response(
        self,
        correlation_id: str,
        response: Any,
        token_usage: Optional[Dict[str, int]] = None,
        duration_ms: Optional[float] = None,
        model: Optional[str] = None
    ) -> None:
        """Log LLM API response."""
        data = {
            'duration_ms': duration_ms,
        }

        if model:
            data['model'] = model

        if token_usage:
            data['token_usage'] = token_usage

        # Extract response content
        response_content = None
        if hasattr(response, 'content'):
            response_content = response.content
        elif isinstance(response, dict):
            response_content = response.get('content') or response.get('message', {}).get('content')
        elif isinstance(response, str):
            response_content = response

        if response_content:
            data['response_length'] = len(str(response_content))
            if self.config.get('log_full_responses', False):
                data['response'] = response_content
            else:
                data['response_preview'] = self._truncate(str(response_content))

        self._log(logging.INFO, 'llm_response', data, correlation_id=correlation_id)

    # -------------------------------------------------------------------------
    # INTENT CLASSIFICATION LOGGING
    # -------------------------------------------------------------------------

    def log_intent_classification(
        self,
        correlation_id: str,
        category: str,
        confidence: float,
        reasoning: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None
    ) -> None:
        """Log intent classification result."""
        data = {
            'category': category,
            'confidence': round(confidence, 4),
        }

        if reasoning:
            data['reasoning'] = self._truncate(reasoning, 300)

        if params:
            data['extracted_params'] = params

        if duration_ms is not None:
            data['duration_ms'] = round(duration_ms, 2)

        self._log(logging.INFO, 'intent_classification', data, correlation_id=correlation_id)

    def log_parameter_extraction(
        self,
        correlation_id: str,
        params: Dict[str, Any],
        source: str = 'llm',
        duration_ms: Optional[float] = None
    ) -> None:
        """Log parameter extraction result."""
        data = {
            'param_count': len(params),
            'params': params,
            'source': source,
        }

        if duration_ms is not None:
            data['duration_ms'] = round(duration_ms, 2)

        self._log(logging.INFO, 'parameter_extraction', data, correlation_id=correlation_id)

    # -------------------------------------------------------------------------
    # VALIDATION LOGGING
    # -------------------------------------------------------------------------

    def log_validation(
        self,
        correlation_id: str,
        field: str,
        original_value: Any,
        corrected_value: Optional[Any] = None,
        confidence: Optional[float] = None,
        is_valid: bool = True,
        suggestions: Optional[List[str]] = None
    ) -> None:
        """Log filter validation result."""
        data = {
            'field': field,
            'original_value': original_value,
            'is_valid': is_valid,
        }

        if corrected_value is not None:
            data['corrected_value'] = corrected_value
            data['was_corrected'] = original_value != corrected_value

        if confidence is not None:
            data['confidence'] = round(confidence, 4)

        if suggestions:
            data['suggestions'] = suggestions[:5]  # Top 5 suggestions

        self._log(logging.DEBUG, 'filter_validation', data, correlation_id=correlation_id)

    def log_validation_summary(
        self,
        correlation_id: str,
        total_validated: int,
        auto_corrected: int,
        needs_confirmation: int,
        rejected: int,
        duration_ms: Optional[float] = None
    ) -> None:
        """Log validation summary."""
        data = {
            'total_validated': total_validated,
            'auto_corrected': auto_corrected,
            'needs_confirmation': needs_confirmation,
            'rejected': rejected,
        }

        if duration_ms is not None:
            data['duration_ms'] = round(duration_ms, 2)

        self._log(logging.INFO, 'validation_summary', data, correlation_id=correlation_id)

    # -------------------------------------------------------------------------
    # QUERY EXECUTION LOGGING
    # -------------------------------------------------------------------------

    def log_query_execution(
        self,
        correlation_id: str,
        params: Dict[str, Any],
        record_count: int,
        duration_ms: float,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """Log query execution result."""
        data = {
            'params': params,
            'record_count': record_count,
            'duration_ms': round(duration_ms, 2),
            'success': success,
        }

        if error:
            data['error'] = error

        level = logging.INFO if success else logging.WARNING
        self._log(level, 'query_execution', data, correlation_id=correlation_id)

    def log_tool_execution(
        self,
        correlation_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        result_summary: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        status: str = 'success',
        error: Optional[str] = None
    ) -> None:
        """Log tool execution."""
        data = {
            'tool_name': tool_name,
            'parameters': parameters,
            'status': status,
        }

        if result_summary:
            data['result_summary'] = result_summary

        if duration_ms is not None:
            data['duration_ms'] = round(duration_ms, 2)

        if error:
            data['error'] = error

        level = logging.INFO if status == 'success' else logging.WARNING
        event = 'tool_execution_completed' if status == 'success' else 'tool_execution_failed'
        self._log(level, event, data, correlation_id=correlation_id)

    def log_api_call(
        self,
        correlation_id: str,
        endpoint: str,
        method: str = 'GET',
        params: Optional[Dict[str, Any]] = None,
        response_status: Optional[int] = None,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None
    ) -> None:
        """Log external API call."""
        data = {
            'endpoint': endpoint,
            'method': method,
        }

        if params:
            data['params'] = params

        if response_status is not None:
            data['response_status'] = response_status

        if duration_ms is not None:
            data['duration_ms'] = round(duration_ms, 2)

        if error:
            data['error'] = error

        level = logging.DEBUG if response_status and 200 <= response_status < 300 else logging.INFO
        self._log(level, 'api_call', data, correlation_id=correlation_id)

    # -------------------------------------------------------------------------
    # DIAGNOSIS LOGGING
    # -------------------------------------------------------------------------

    def log_combination_diagnostic(
        self,
        correlation_id: str,
        is_data_issue: bool,
        is_combination_issue: bool,
        problematic_filters: List[str],
        total_records_available: int,
        working_combinations: Optional[Dict[str, List[str]]] = None,
        duration_ms: Optional[float] = None
    ) -> None:
        """Log combination diagnostic result."""
        data = {
            'is_data_issue': is_data_issue,
            'is_combination_issue': is_combination_issue,
            'problematic_filters': problematic_filters,
            'total_records_available': total_records_available,
        }

        if working_combinations:
            # Truncate working combinations for logging
            data['working_combinations'] = {
                k: v[:5] for k, v in working_combinations.items()
            }

        if duration_ms is not None:
            data['duration_ms'] = round(duration_ms, 2)

        self._log(logging.INFO, 'combination_diagnostic', data, correlation_id=correlation_id)

    # -------------------------------------------------------------------------
    # ERROR LOGGING
    # -------------------------------------------------------------------------

    def log_error(
        self,
        correlation_id: str,
        error: Union[str, Exception],
        error_traceback: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        stage: str = 'unknown'
    ) -> None:
        """Log error with context."""
        data = {
            'stage': stage,
            'error_type': type(error).__name__ if isinstance(error, Exception) else 'string',
            'error_message': str(error),
        }

        if error_traceback:
            data['traceback'] = error_traceback
        elif isinstance(error, Exception):
            data['traceback'] = traceback.format_exc()

        if context:
            data['context'] = context

        self._log(logging.ERROR, 'error', data, correlation_id=correlation_id)

    # -------------------------------------------------------------------------
    # WEBSOCKET LOGGING
    # -------------------------------------------------------------------------

    def log_websocket_connect(
        self,
        user_id: str,
        conversation_id: str
    ) -> None:
        """Log WebSocket connection."""
        data = {
            'user_id': user_id,
            'conversation_id': conversation_id,
        }
        self._log(logging.INFO, 'websocket_connect', data,
                  conversation_id=conversation_id, user_id=user_id)

    def log_websocket_disconnect(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
        close_code: Optional[int] = None
    ) -> None:
        """Log WebSocket disconnection."""
        data = {
            'user_id': user_id,
            'close_code': close_code,
        }
        if conversation_id:
            data['conversation_id'] = conversation_id
        self._log(logging.INFO, 'websocket_disconnect', data, user_id=user_id)

    def log_message_processing_start(
        self,
        correlation_id: str,
        conversation_id: str,
        user_id: str,
        message_type: str = 'user_message'
    ) -> None:
        """Log start of message processing."""
        data = {
            'message_type': message_type,
        }
        self._log(
            logging.INFO,
            'message_processing_start',
            data,
            correlation_id=correlation_id,
            conversation_id=conversation_id,
            user_id=user_id
        )

    def log_message_processing_complete(
        self,
        correlation_id: str,
        success: bool,
        total_duration_ms: float,
        category: Optional[str] = None
    ) -> None:
        """Log completion of message processing."""
        data = {
            'success': success,
            'total_duration_ms': round(total_duration_ms, 2),
        }
        if category:
            data['category'] = category

        level = logging.INFO if success else logging.WARNING
        self._log(level, 'message_processing_complete', data, correlation_id=correlation_id)


# =============================================================================
# SINGLETON LOGGER INSTANCE
# =============================================================================

_llm_logger: Optional[LLMWorkflowLogger] = None


def get_llm_logger() -> LLMWorkflowLogger:
    """Get singleton LLM workflow logger instance."""
    global _llm_logger
    if _llm_logger is None:
        _llm_logger = LLMWorkflowLogger()
    return _llm_logger
