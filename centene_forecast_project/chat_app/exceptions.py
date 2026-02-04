"""
Custom exceptions for chat_app with error codes and user-friendly messages.

Exception Hierarchy:
- ChatAppError (base)
  - LLMError (LLM-related issues - contact admin)
    - LLMConnectionError
    - LLMTimeoutError
    - LLMResponseError
  - APIError (Backend API issues - contact admin)
    - APIConnectionError
    - APITimeoutError
    - APIResponseError
  - ValidationError (User input issues - no admin contact needed)
  - ContextError (Session/context issues - refresh and retry)
"""
from typing import Optional, Dict, Any


class ChatAppError(Exception):
    """
    Base exception for all chat_app errors.

    Provides standardized error handling with:
    - error_code: Machine-readable identifier for filtering/alerting
    - user_message: Safe, user-friendly message to display
    - admin_contact: Whether to show "contact admin" guidance
    - details: Additional context for logging (not shown to users)
    """

    error_code: str = "CHAT_ERROR"
    user_message: str = "An error occurred. Please try again."
    admin_contact: bool = False

    def __init__(
        self,
        message: str = None,
        error_code: str = None,
        user_message: str = None,
        admin_contact: bool = None,
        details: Dict[str, Any] = None
    ):
        """
        Initialize ChatAppError.

        Args:
            message: Technical error message for logging
            error_code: Override default error code
            user_message: Override default user message
            admin_contact: Override default admin contact flag
            details: Additional context for logging
        """
        self.message = message or self.__class__.__doc__ or "An error occurred"
        if error_code is not None:
            self.error_code = error_code
        if user_message is not None:
            self.user_message = user_message
        if admin_contact is not None:
            self.admin_contact = admin_contact
        self.details = details or {}

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "admin_contact": self.admin_contact,
            "details": self.details,
            "exception_type": self.__class__.__name__
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.error_code}, message={self.message!r})"


# =============================================================================
# LLM Errors - AI service issues (always suggest contacting admin)
# =============================================================================

class LLMError(ChatAppError):
    """LLM-related errors (connection, timeout, response parsing)."""

    error_code = "LLM_ERROR"
    user_message = "AI service is temporarily unavailable. Please contact admin."
    admin_contact = True


class LLMConnectionError(LLMError):
    """LLM connection failed - cannot reach the LLM API."""

    error_code = "LLM_CONNECTION"
    user_message = "Cannot connect to AI service. Please contact admin if this persists."


class LLMTimeoutError(LLMError):
    """LLM request timed out - the AI took too long to respond."""

    error_code = "LLM_TIMEOUT"
    user_message = "AI service is taking too long to respond. Please try again or contact admin."


class LLMResponseError(LLMError):
    """LLM returned invalid/unexpected response - parsing or format issue."""

    error_code = "LLM_RESPONSE"
    user_message = "Received an unexpected response from AI service. Please try again."


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""

    error_code = "LLM_RATE_LIMIT"
    user_message = "AI service is currently busy. Please wait a moment and try again."


class LLMAuthenticationError(LLMError):
    """LLM API key or authentication issue."""

    error_code = "LLM_AUTH"
    user_message = "AI service authentication issue. Please contact admin."


# =============================================================================
# API Errors - Backend data service issues
# =============================================================================
# Two categories:
# 1. Server Errors (5xx, connection, timeout) - System issue, contact admin
# 2. Client Errors (4xx) - User-caused, explain what's wrong so user can fix

class APIError(ChatAppError):
    """Base class for all API errors."""

    error_code = "API_ERROR"
    user_message = "Data service error. Please try again."
    admin_contact = True


# -----------------------------------------------------------------------------
# Server Errors (5xx, connection issues) - System failures, contact admin
# -----------------------------------------------------------------------------

class APIServerError(APIError):
    """API server-side errors (5xx status codes, connection failures)."""

    error_code = "API_SERVER_ERROR"
    user_message = "Data service is temporarily unavailable. Please contact admin."
    admin_contact = True


class APIConnectionError(APIServerError):
    """API connection failed - cannot reach the backend API."""

    error_code = "API_CONNECTION"
    user_message = "Cannot connect to data service. Please contact admin if this persists."


class APITimeoutError(APIServerError):
    """API request timed out - the backend took too long to respond."""

    error_code = "API_TIMEOUT"
    user_message = "Data service is taking too long to respond. Please try again or contact admin."


class APIInternalError(APIServerError):
    """API returned 500 Internal Server Error."""

    error_code = "API_INTERNAL"
    user_message = "Data service encountered an internal error. Please contact admin."


# -----------------------------------------------------------------------------
# Client Errors (4xx) - User-caused issues, explain so user can fix
# -----------------------------------------------------------------------------

class APIClientError(APIError):
    """
    API client-side errors (4xx status codes) - User can fix these.

    These are NOT system failures. The user's request has issues that
    they can correct (missing params, invalid filters, no data for criteria).
    """

    error_code = "API_CLIENT_ERROR"
    user_message = "There was an issue with your request. Please check your input."
    admin_contact = False  # User can fix this


class APIBadRequestError(APIClientError):
    """
    API returned 400 Bad Request - invalid input parameters.

    Common causes:
    - Missing required parameters (month, year)
    - Invalid filter values
    - Malformed request
    """

    error_code = "API_BAD_REQUEST"
    user_message = "Invalid request parameters. Please check your input."

    def __init__(
        self,
        message: str = None,
        status_code: int = 400,
        response_body: str = None,
        missing_fields: list = None,
        invalid_fields: dict = None,
        **kwargs
    ):
        """
        Initialize APIBadRequestError with request-specific details.

        Args:
            message: Error message
            status_code: HTTP status code (default 400)
            response_body: Raw response body
            missing_fields: List of missing required field names
            invalid_fields: Dict of {field_name: error_message}
            **kwargs: Additional arguments for parent
        """
        self.status_code = status_code
        self.response_body = response_body
        self.missing_fields = missing_fields or []
        self.invalid_fields = invalid_fields or {}

        # Build helpful user message
        if missing_fields:
            user_msg = f"Missing required fields: {', '.join(missing_fields)}. Please provide these values."
        elif invalid_fields:
            issues = [f"{k}: {v}" for k, v in invalid_fields.items()]
            user_msg = f"Invalid values: {'; '.join(issues)}"
        elif response_body:
            # Try to extract message from response
            user_msg = f"Request error: {response_body[:200]}"
        else:
            user_msg = "Invalid request parameters. Please check your input."

        super().__init__(message=message, user_message=user_msg, **kwargs)
        self.details["status_code"] = status_code
        self.details["response_body"] = response_body
        self.details["missing_fields"] = missing_fields
        self.details["invalid_fields"] = invalid_fields


class APINotFoundError(APIClientError):
    """
    API returned 404 Not Found - no data matches the criteria.

    This is NOT a system error. The user's filters are valid but
    no data exists for that combination.
    """

    error_code = "API_NOT_FOUND"
    user_message = "No data found for your search criteria. Try adjusting your filters."

    def __init__(
        self,
        message: str = None,
        filters_used: dict = None,
        suggestions: list = None,
        **kwargs
    ):
        """
        Initialize APINotFoundError with search-specific details.

        Args:
            message: Error message
            filters_used: Dict of filters that were applied
            suggestions: List of suggested alternative queries
            **kwargs: Additional arguments for parent
        """
        self.filters_used = filters_used or {}
        self.suggestions = suggestions or []

        # Build helpful user message
        if filters_used:
            filter_desc = ", ".join(f"{k}={v}" for k, v in filters_used.items() if v)
            user_msg = f"No data found for: {filter_desc}. Try different filters."
        else:
            user_msg = "No data found for your search criteria. Try adjusting your filters."

        if suggestions:
            user_msg += f" Suggestions: {', '.join(suggestions[:3])}"

        super().__init__(message=message, user_message=user_msg, **kwargs)
        self.details["filters_used"] = filters_used
        self.details["suggestions"] = suggestions


class APIValidationError(APIClientError):
    """
    API returned validation error - filter values are invalid.

    The filter names are valid but the values don't match known options.
    """

    error_code = "API_VALIDATION"

    def __init__(
        self,
        message: str = None,
        field_name: str = None,
        invalid_value: str = None,
        valid_options: list = None,
        **kwargs
    ):
        """
        Initialize APIValidationError with validation-specific details.

        Args:
            message: Error message
            field_name: Name of the invalid field
            invalid_value: The value that was rejected
            valid_options: List of valid options for this field
            **kwargs: Additional arguments for parent
        """
        self.field_name = field_name
        self.invalid_value = invalid_value
        self.valid_options = valid_options or []

        # Build helpful user message
        if field_name and invalid_value:
            user_msg = f"'{invalid_value}' is not a valid {field_name}."
            if valid_options:
                user_msg += f" Valid options: {', '.join(valid_options[:5])}"
                if len(valid_options) > 5:
                    user_msg += f" (and {len(valid_options) - 5} more)"
        else:
            user_msg = "Some filter values are invalid. Please check your input."

        super().__init__(message=message, user_message=user_msg, **kwargs)
        self.details["field_name"] = field_name
        self.details["invalid_value"] = invalid_value
        self.details["valid_options"] = valid_options


# Legacy alias for backward compatibility
class APIResponseError(APIError):
    """API returned error status or invalid response (legacy - use specific subclasses)."""

    error_code = "API_RESPONSE"
    user_message = "Data service returned an error. Please try again."

    def __init__(
        self,
        message: str = None,
        status_code: int = None,
        response_body: str = None,
        **kwargs
    ):
        """
        Initialize APIResponseError with HTTP-specific details.

        Args:
            message: Error message
            status_code: HTTP status code
            response_body: Raw response body
            **kwargs: Additional arguments for parent
        """
        # Determine if this is a client error (4xx) or server error (5xx)
        if status_code and 400 <= status_code < 500:
            self.admin_contact = False
            self.user_message = "There was an issue with your request. Please check your input."
        else:
            self.admin_contact = True
            self.user_message = "Data service returned an error. Please contact admin."

        super().__init__(message=message, **kwargs)
        self.status_code = status_code
        self.response_body = response_body
        self.details["status_code"] = status_code
        self.details["response_body"] = response_body


# =============================================================================
# Validation Errors - User input issues (no admin contact needed)
# =============================================================================

class ValidationError(ChatAppError):
    """User input validation errors (not admin-contact)."""

    error_code = "VALIDATION"
    user_message = "Invalid input. Please check your request."
    admin_contact = False


class MissingParameterError(ValidationError):
    """Required parameter is missing from user input."""

    error_code = "MISSING_PARAM"

    def __init__(
        self,
        message: str = None,
        missing_fields: list = None,
        **kwargs
    ):
        """
        Initialize MissingParameterError.

        Args:
            message: Error message
            missing_fields: List of missing field names
            **kwargs: Additional arguments for parent
        """
        self.missing_fields = missing_fields or []
        if not message and missing_fields:
            message = f"Missing required fields: {', '.join(missing_fields)}"
        user_msg = f"Please provide: {', '.join(missing_fields)}" if missing_fields else "Please provide the required information."
        super().__init__(message=message, user_message=user_msg, **kwargs)
        self.details["missing_fields"] = self.missing_fields


class InvalidFilterError(ValidationError):
    """Invalid filter value provided by user."""

    error_code = "INVALID_FILTER"

    def __init__(
        self,
        message: str = None,
        field_name: str = None,
        invalid_value: str = None,
        suggestions: list = None,
        **kwargs
    ):
        """
        Initialize InvalidFilterError with filter-specific details.

        Args:
            message: Error message
            field_name: Name of the invalid field
            invalid_value: The invalid value provided
            suggestions: List of valid alternatives
            **kwargs: Additional arguments for parent
        """
        self.field_name = field_name
        self.invalid_value = invalid_value
        self.suggestions = suggestions or []

        if not message:
            message = f"Invalid {field_name}: '{invalid_value}'"

        user_msg = f"'{invalid_value}' is not a valid {field_name}."
        if suggestions:
            user_msg += f" Did you mean: {', '.join(suggestions[:3])}?"

        super().__init__(message=message, user_message=user_msg, **kwargs)
        self.details["field_name"] = field_name
        self.details["invalid_value"] = invalid_value
        self.details["suggestions"] = suggestions


class DateRangeError(ValidationError):
    """Invalid date/month/year provided."""

    error_code = "DATE_RANGE"
    user_message = "Please provide a valid month (1-12) and year."


# =============================================================================
# Context Errors - Session/state issues
# =============================================================================

class ContextError(ChatAppError):
    """Context management errors."""

    error_code = "CONTEXT_ERROR"
    user_message = "Session error. Please refresh and try again."
    admin_contact = False


class ContextNotFoundError(ContextError):
    """Conversation context not found."""

    error_code = "CONTEXT_NOT_FOUND"
    user_message = "Your session has expired. Please start a new conversation."


class ContextCorruptedError(ContextError):
    """Conversation context is corrupted or invalid."""

    error_code = "CONTEXT_CORRUPTED"
    user_message = "Session data is corrupted. Please refresh and start over."


# =============================================================================
# Helper Functions
# =============================================================================

def classify_openai_error(error: Exception) -> LLMError:
    """
    Convert OpenAI/LangChain exceptions to appropriate LLMError subclass.

    Args:
        error: The original exception

    Returns:
        Appropriate LLMError subclass
    """
    error_str = str(error).lower()
    error_type = type(error).__name__

    # Check for connection errors
    if any(term in error_str for term in ["connection", "connect", "network", "unreachable"]):
        return LLMConnectionError(
            message=str(error),
            details={"original_error": error_type}
        )

    # Check for timeout errors
    if any(term in error_str for term in ["timeout", "timed out", "deadline"]):
        return LLMTimeoutError(
            message=str(error),
            details={"original_error": error_type}
        )

    # Check for rate limit errors
    if any(term in error_str for term in ["rate limit", "too many requests", "429"]):
        return LLMRateLimitError(
            message=str(error),
            details={"original_error": error_type}
        )

    # Check for authentication errors
    if any(term in error_str for term in ["auth", "api key", "unauthorized", "401", "403"]):
        return LLMAuthenticationError(
            message=str(error),
            details={"original_error": error_type}
        )

    # Check for response/parsing errors
    if any(term in error_str for term in ["parse", "json", "invalid response", "unexpected"]):
        return LLMResponseError(
            message=str(error),
            details={"original_error": error_type}
        )

    # Default to generic LLM error
    return LLMError(
        message=str(error),
        details={"original_error": error_type}
    )


def classify_httpx_error(error: Exception, endpoint: str = None) -> APIError:
    """
    Convert httpx exceptions to appropriate APIError subclass.

    Differentiates between:
    - Client errors (4xx) - User can fix these (bad request, not found, validation)
    - Server errors (5xx, connection, timeout) - System issue, contact admin

    Args:
        error: The original exception
        endpoint: The API endpoint being called (for logging)

    Returns:
        Appropriate APIError subclass
    """
    import json

    error_type = type(error).__name__
    details = {"original_error": error_type}
    if endpoint:
        details["endpoint"] = endpoint

    # Check for connection errors - SYSTEM ERROR
    if error_type in ["ConnectError", "ConnectTimeout"]:
        return APIConnectionError(
            message=str(error),
            details=details
        )

    # Check for timeout errors - SYSTEM ERROR
    if error_type in ["ReadTimeout", "WriteTimeout", "PoolTimeout", "TimeoutException"]:
        return APITimeoutError(
            message=str(error),
            details=details
        )

    # Check for HTTP status errors
    if error_type == "HTTPStatusError":
        status_code = getattr(error, 'response', {})
        if hasattr(status_code, 'status_code'):
            status_code = status_code.status_code
        else:
            status_code = None

        response_body = None
        response_json = None
        if hasattr(error, 'response') and hasattr(error.response, 'text'):
            response_body = error.response.text[:500]  # Truncate for logging
            # Try to parse JSON for structured error info
            try:
                response_json = json.loads(error.response.text)
            except (json.JSONDecodeError, TypeError):
                pass

        # === CLIENT ERRORS (4xx) - User can fix ===

        if status_code == 400:
            # Bad Request - missing/invalid parameters
            missing_fields = None
            invalid_fields = None

            if response_json:
                # Try to extract structured error info
                missing_fields = response_json.get('missing_fields', response_json.get('missing'))
                invalid_fields = response_json.get('invalid_fields', response_json.get('errors'))
                error_msg = response_json.get('detail', response_json.get('message', response_body))
            else:
                error_msg = response_body

            return APIBadRequestError(
                message=str(error),
                status_code=status_code,
                response_body=error_msg,
                missing_fields=missing_fields,
                invalid_fields=invalid_fields,
                details=details
            )

        if status_code == 404:
            # Not Found - no data for criteria
            filters_used = None
            if response_json:
                filters_used = response_json.get('filters', response_json.get('criteria'))

            return APINotFoundError(
                message=str(error),
                filters_used=filters_used,
                details=details
            )

        if status_code == 422:
            # Unprocessable Entity - validation error
            field_name = None
            invalid_value = None
            valid_options = None

            if response_json:
                # FastAPI validation errors have specific format
                if 'detail' in response_json and isinstance(response_json['detail'], list):
                    first_error = response_json['detail'][0] if response_json['detail'] else {}
                    field_name = first_error.get('loc', [None])[-1]
                    invalid_value = first_error.get('input')
                else:
                    field_name = response_json.get('field')
                    invalid_value = response_json.get('value')
                    valid_options = response_json.get('valid_options')

            return APIValidationError(
                message=str(error),
                field_name=field_name,
                invalid_value=invalid_value,
                valid_options=valid_options,
                details=details
            )

        # Other 4xx errors
        if status_code and 400 <= status_code < 500:
            return APIClientError(
                message=str(error),
                user_message=f"Request error ({status_code}). Please check your input.",
                details=details
            )

        # === SERVER ERRORS (5xx) - System issue ===

        if status_code == 500:
            return APIInternalError(
                message=str(error),
                details=details
            )

        if status_code and status_code >= 500:
            return APIServerError(
                message=str(error),
                user_message=f"Data service error ({status_code}). Please contact admin.",
                details=details
            )

        # Fallback for unknown status codes
        return APIResponseError(
            message=str(error),
            status_code=status_code,
            response_body=response_body,
            details=details
        )

    # Default to generic API error (server-side assumption)
    return APIServerError(
        message=str(error),
        details=details
    )
