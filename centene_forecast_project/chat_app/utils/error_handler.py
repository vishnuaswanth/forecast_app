"""
Centralized error handling utilities for chat_app.

Provides:
- Safe error response creation with proper typing
- HTML error UI generation with XSS protection
- Comprehensive error logging with correlation tracking
"""
import html
import logging
import uuid
from typing import Dict, Any, Optional, Union
from datetime import datetime

from chat_app.exceptions import (
    ChatAppError,
    LLMError,
    APIError,
    ValidationError,
    ContextError,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Error Response Creation
# =============================================================================

def create_error_response(
    error: Union[Exception, ChatAppError],
    correlation_id: str = None,
    include_details: bool = False,
    category: str = "error"
) -> Dict[str, Any]:
    """
    Create safe, structured error response for chat service.

    Returns a dictionary that can be safely returned from any chat service method
    with consistent typing and safe values.

    Args:
        error: The exception that occurred
        correlation_id: Optional request correlation ID for tracing
        include_details: Whether to include technical details (dev mode only)
        category: Category to use in response (default: "error")

    Returns:
        Dictionary with:
            - success: False
            - category: str
            - confidence: 0.0
            - parameters: {}
            - ui_component: str (safe HTML)
            - metadata: dict with error info
    """
    correlation_id = correlation_id or str(uuid.uuid4())[:8]

    # Determine error type and get appropriate values
    if isinstance(error, ChatAppError):
        error_type = _get_error_type(error)
        error_code = error.error_code
        user_message = error.user_message
        admin_contact = error.admin_contact
        details = error.details if include_details else {}
    else:
        # Generic exception - treat as unknown error
        error_type = "unknown"
        error_code = "UNKNOWN_ERROR"
        user_message = "An unexpected error occurred. Please try again."
        admin_contact = True
        details = {"exception_type": type(error).__name__} if include_details else {}

    # Generate safe HTML UI
    ui_component = generate_error_ui(
        error_type=error_type,
        user_message=user_message,
        admin_contact=admin_contact,
        error_code=error_code
    )

    return {
        "success": False,
        "category": category,
        "confidence": 0.0,
        "parameters": {},
        "ui_component": ui_component,
        "response_type": "error_response",
        "metadata": {
            "error": True,
            "error_type": error_type,
            "error_code": error_code,
            "correlation_id": correlation_id,
            "admin_contact": admin_contact,
            "details": details,
        }
    }


def _get_error_type(error: ChatAppError) -> str:
    """Get error type string from ChatAppError subclass."""
    if isinstance(error, LLMError):
        return "llm"
    elif isinstance(error, APIError):
        return "api"
    elif isinstance(error, ValidationError):
        return "validation"
    elif isinstance(error, ContextError):
        return "context"
    else:
        return "unknown"


# =============================================================================
# Error UI Generation
# =============================================================================

def generate_error_ui(
    error_type: str,
    user_message: str,
    admin_contact: bool = False,
    error_code: str = None
) -> str:
    """
    Generate safe HTML error UI with proper escaping.

    All user-visible text is HTML-escaped to prevent XSS.

    Args:
        error_type: Type of error ('llm', 'api', 'validation', 'context', 'unknown')
        user_message: User-friendly error message to display
        admin_contact: Whether to show "contact admin" guidance
        error_code: Optional error code to display

    Returns:
        HTML string for error display card
    """
    # HTML-escape all user-visible text
    safe_message = html.escape(user_message)
    safe_error_code = html.escape(error_code) if error_code else None

    # Select icon and styling based on error type
    error_config = _get_error_config(error_type)

    # Build error code footer if provided
    error_code_html = ""
    if safe_error_code:
        error_code_html = f'<span class="error-code">Error: {safe_error_code}</span>'

    # Build admin contact guidance if needed
    admin_html = ""
    if admin_contact:
        admin_html = '<span class="admin-contact">Please contact admin if this persists.</span>'

    # Build footer with error code and admin contact
    footer_html = ""
    if error_code_html or admin_html:
        footer_parts = [p for p in [error_code_html, admin_html] if p]
        footer_html = f'''
            <div class="error-footer">
                <small class="text-muted">{" ".join(footer_parts)}</small>
            </div>
        '''

    return f'''
    <div class="chat-error-card error-{html.escape(error_type)}" role="alert">
        <div class="error-icon">{error_config["icon"]}</div>
        <div class="error-content">
            <strong class="error-title">{error_config["title"]}</strong>
            <p class="error-message">{safe_message}</p>
            {footer_html}
        </div>
    </div>
    '''


def _get_error_config(error_type: str) -> Dict[str, str]:
    """Get icon and title configuration for error type."""
    configs = {
        "llm": {
            "icon": "\u26a0\ufe0f",  # Warning sign
            "title": "AI Service Issue",
        },
        "api": {
            "icon": "\u26a0\ufe0f",  # Warning sign
            "title": "Data Service Issue",
        },
        "validation": {
            "icon": "\u2139\ufe0f",  # Info sign
            "title": "Invalid Input",
        },
        "context": {
            "icon": "\u2139\ufe0f",  # Info sign
            "title": "Session Issue",
        },
        "unknown": {
            "icon": "\u26a0\ufe0f",  # Warning sign
            "title": "Unexpected Error",
        },
    }
    return configs.get(error_type, configs["unknown"])


def generate_simple_error_html(message: str) -> str:
    """
    Generate simple error alert HTML with XSS protection.

    Use this for simple error messages that don't need the full error card styling.

    Args:
        message: Error message to display

    Returns:
        HTML string for Bootstrap-style error alert
    """
    safe_message = html.escape(message)
    return f'<div class="alert alert-danger" role="alert"><strong>Error:</strong> {safe_message}</div>'


def generate_warning_html(message: str) -> str:
    """
    Generate warning alert HTML with XSS protection.

    Args:
        message: Warning message to display

    Returns:
        HTML string for Bootstrap-style warning alert
    """
    safe_message = html.escape(message)
    return f'<div class="alert alert-warning" role="alert">{safe_message}</div>'


# =============================================================================
# Error Logging
# =============================================================================

def log_error(
    log: logging.Logger,
    error: Union[Exception, ChatAppError],
    context: Dict[str, Any] = None,
    correlation_id: str = None,
    stage: str = None,
    include_traceback: bool = True
) -> None:
    """
    Comprehensive error logging with context.

    Logs all relevant error information for debugging while protecting
    sensitive data.

    Args:
        log: Logger instance to use
        error: The exception that occurred
        context: Additional context dictionary (conversation_id, user_id, etc.)
        correlation_id: Request correlation ID for tracing
        stage: Processing stage where error occurred
        include_traceback: Whether to include stack trace
    """
    context = context or {}
    correlation_id = correlation_id or context.get("correlation_id", "unknown")

    # Build error details
    if isinstance(error, ChatAppError):
        error_type = _get_error_type(error)
        error_code = error.error_code
        error_details = error.details
    else:
        error_type = "unknown"
        error_code = "UNKNOWN_ERROR"
        error_details = {}

    # Build log message
    log_message = f"[{error_type.upper()}] {error_code}"
    if stage:
        log_message += f" at {stage}"
    log_message += f": {str(error)}"

    # Build extra dict for structured logging
    extra = {
        "error_code": error_code,
        "error_type": error_type,
        "correlation_id": correlation_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Add context (with sensitive data filtering)
    if context:
        # Filter out sensitive fields
        safe_context = _filter_sensitive_data(context)
        extra["context"] = safe_context

    if stage:
        extra["stage"] = stage

    if error_details:
        extra["error_details"] = error_details

    # Log with appropriate level
    log.error(
        log_message,
        extra=extra,
        exc_info=include_traceback
    )


def _filter_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter sensitive data from context before logging.

    Removes or masks fields that might contain sensitive information.
    """
    sensitive_keys = {
        "password", "token", "api_key", "secret", "credential",
        "authorization", "cookie", "session"
    }

    filtered = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            filtered[key] = "[REDACTED]"
        elif isinstance(value, dict):
            filtered[key] = _filter_sensitive_data(value)
        elif isinstance(value, str) and len(value) > 500:
            # Truncate long strings (could be user input)
            filtered[key] = value[:500] + "...[TRUNCATED]"
        else:
            filtered[key] = value

    return filtered


# =============================================================================
# Safe Return Type Helpers
# =============================================================================

def safe_response(
    success: bool,
    category: str = None,
    confidence: float = None,
    parameters: Dict[str, Any] = None,
    ui_component: str = None,
    message: str = None,
    data: Any = None,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Create a safe, well-typed response dictionary.

    Ensures all response fields have valid types and default values,
    preventing None/undefined issues in downstream code.

    Args:
        success: Whether the operation succeeded
        category: Intent/action category
        confidence: Classification confidence (0.0-1.0)
        parameters: Extracted parameters
        ui_component: HTML for display
        message: Status message
        data: Response data
        metadata: Additional metadata

    Returns:
        Dictionary with all fields having safe default values
    """
    return {
        "success": bool(success),
        "category": str(category) if category else ("success" if success else "error"),
        "confidence": float(confidence) if confidence is not None else (1.0 if success else 0.0),
        "parameters": dict(parameters) if parameters else {},
        "ui_component": str(ui_component) if ui_component else "",
        "message": str(message) if message else "",
        "data": data,
        "metadata": dict(metadata) if metadata else {},
    }
