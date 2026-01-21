"""
Execution Monitoring Validators Module

Validation functions for execution monitoring request parameters.
Ensures data integrity before hitting the service/repository layer.
"""

import re
import logging
from typing import Optional, List, Dict

logger = logging.getLogger('django')


class ValidationError(Exception):
    """Custom validation error exception for execution monitoring."""
    pass


# ============================================================================
# Valid Constants
# ============================================================================

VALID_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

VALID_STATUSES = [
    "PENDING",
    "IN_PROGRESS",
    "SUCCESS",
    "FAILED",
    "PARTIAL_SUCCESS"
]

VALID_REPORT_TYPES = [
    "bucket_summary",
    "bucket_after_allocation",
    "roster_allotment"
]


# ============================================================================
# Individual Parameter Validators
# ============================================================================

def validate_month(month: Optional[str]) -> Optional[str]:
    """
    Validate month parameter.

    Args:
        month: Month name (e.g., "January")

    Returns:
        Validated month name or None

    Raises:
        ValidationError: If month is invalid

    Example:
        >>> validate_month("January")
        'January'
        >>> validate_month("Janaury")
        ValidationError: Invalid month: Janaury
    """
    if not month:
        return None

    if month not in VALID_MONTHS:
        raise ValidationError(
            f"Invalid month: {month}. "
            f"Must be one of: {', '.join(VALID_MONTHS)}"
        )

    return month


def validate_year(year: Optional[str]) -> Optional[int]:
    """
    Validate year parameter.

    Args:
        year: Year as string or int (e.g., "2025")

    Returns:
        Validated year as integer or None

    Raises:
        ValidationError: If year is invalid or out of range

    Example:
        >>> validate_year("2025")
        2025
        >>> validate_year("1999")
        ValidationError: Year must be 2020-2100, got 1999
    """
    if not year:
        return None

    try:
        year_int = int(year)

        if not (2020 <= year_int <= 2100):
            raise ValidationError(
                f"Year must be 2020-2100, got {year_int}"
            )

        return year_int

    except ValueError:
        raise ValidationError(
            f"Invalid year format: {year}. Must be a valid integer."
        )


def validate_status_list(status_list: List[str]) -> List[str]:
    """
    Validate list of status values.

    Args:
        status_list: List of status strings

    Returns:
        Validated list of status values

    Raises:
        ValidationError: If any status is invalid

    Example:
        >>> validate_status_list(["SUCCESS", "FAILED"])
        ['SUCCESS', 'FAILED']
        >>> validate_status_list(["SUCCESS", "INVALID"])
        ValidationError: Invalid statuses: INVALID
    """
    if not status_list:
        return []

    # Find invalid statuses
    invalid_statuses = [s for s in status_list if s not in VALID_STATUSES]

    if invalid_statuses:
        raise ValidationError(
            f"Invalid statuses: {', '.join(invalid_statuses)}. "
            f"Valid statuses are: {', '.join(VALID_STATUSES)}"
        )

    return status_list


def validate_uploaded_by(username: Optional[str]) -> Optional[str]:
    """
    Validate username parameter.

    Args:
        username: Username string

    Returns:
        Validated username or None

    Raises:
        ValidationError: If username format is invalid or too long

    Example:
        >>> validate_uploaded_by("john.doe")
        'john.doe'
        >>> validate_uploaded_by("john@doe!")
        ValidationError: Invalid username format
    """
    if not username:
        return None

    # Length check
    if len(username) > 500:
        raise ValidationError(
            f"Username too long (max 500 characters), got {len(username)}"
        )

    # Format check: allow alphanumeric, dots, hyphens, underscores, spaces
    if not re.match(r'^[a-zA-Z0-9._\-\s]+$', username):
        raise ValidationError(
            f"Invalid username format: {username}. "
            "Only alphanumeric characters, dots, hyphens, and underscores are allowed."
        )

    return username


def validate_pagination(
    limit: Optional[str],
    offset: Optional[str]
) -> tuple:
    """
    Validate pagination parameters.

    Args:
        limit: Max records per page (1-100)
        offset: Pagination offset (0+)

    Returns:
        Tuple of (limit_int, offset_int)

    Raises:
        ValidationError: If pagination parameters are invalid

    Example:
        >>> validate_pagination("50", "0")
        (50, 0)
        >>> validate_pagination("200", "0")
        ValidationError: Limit must be 1-100, got 200
    """
    try:
        # Parse with defaults
        limit_int = int(limit) if limit else 50
        offset_int = int(offset) if offset else 0

        # Validate limit range
        if limit_int < 1 or limit_int > 100:
            raise ValidationError(
                f"Limit must be 1-100, got {limit_int}"
            )

        # Validate offset
        if offset_int < 0:
            raise ValidationError(
                f"Offset must be >= 0, got {offset_int}"
            )

        return limit_int, offset_int

    except ValueError:
        raise ValidationError(
            f"Invalid pagination parameters. Limit and offset must be integers."
        )


def validate_execution_id(execution_id: str) -> str:
    """
    Validate execution ID (UUID format).

    Args:
        execution_id: UUID string

    Returns:
        Validated execution ID

    Raises:
        ValidationError: If execution ID is invalid

    Example:
        >>> validate_execution_id("550e8400-e29b-41d4-a716-446655440000")
        '550e8400-e29b-41d4-a716-446655440000'
        >>> validate_execution_id("invalid-uuid")
        ValidationError: Invalid execution ID format
    """
    if not execution_id:
        raise ValidationError("Execution ID is required")

    # UUID v4 format pattern
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'

    if not re.match(uuid_pattern, execution_id.lower()):
        raise ValidationError(
            f"Invalid execution ID format: {execution_id}. "
            "Must be a valid UUID."
        )

    return execution_id


def validate_report_type(report_type: str) -> str:
    """
    Validate report type for downloads.

    Args:
        report_type: One of the valid report types

    Returns:
        Validated report type

    Raises:
        ValidationError: If report type is invalid

    Example:
        >>> validate_report_type("bucket_summary")
        'bucket_summary'
        >>> validate_report_type("invalid_report")
        ValidationError: Invalid report type: invalid_report
    """
    if not report_type:
        raise ValidationError("Report type is required")

    if report_type not in VALID_REPORT_TYPES:
        raise ValidationError(
            f"Invalid report type: {report_type}. "
            f"Valid types are: {', '.join(VALID_REPORT_TYPES)}"
        )

    return report_type


# ============================================================================
# Combined Request Validators
# ============================================================================

def validate_execution_filters(request_params) -> Dict:
    """
    Validate all execution list filter parameters.

    This is the main validation function used by the list API view.
    Validates month, year, status list, uploaded_by, limit, and offset.

    Args:
        request_params: Django request.GET QueryDict object

    Returns:
        Dictionary of validated parameters

    Raises:
        ValidationError: If any parameter is invalid

    Example:
        >>> filters = validate_execution_filters(request.GET)
        >>> # Returns: {'month': 'January', 'year': 2025, 'status': ['SUCCESS'], ...}
    """
    try:
        # Validate month
        month = validate_month(request_params.get('month', '').strip() or None)

        # Validate year
        year = validate_year(request_params.get('year', '').strip() or None)

        # Validate status list (Django QueryDict supports getlist)
        status_list = []
        if hasattr(request_params, 'getlist'):
            status_list = request_params.getlist('status')
        elif 'status' in request_params:
            # Handle single status value
            single_status = request_params.get('status')
            if single_status:
                status_list = [single_status]

        statuses = validate_status_list(status_list)

        # Validate uploaded_by
        uploaded_by = validate_uploaded_by(
            request_params.get('uploaded_by', '').strip() or None
        )

        # Validate pagination
        limit, offset = validate_pagination(
            request_params.get('limit'),
            request_params.get('offset')
        )

        validated = {
            'month': month,
            'year': year,
            'status': statuses,
            'uploaded_by': uploaded_by,
            'limit': limit,
            'offset': offset
        }

        logger.debug(f"[Validation Success] Execution filters: {validated}")
        return validated

    except ValidationError as e:
        logger.warning(f"[Validation Error] Execution filters: {str(e)}")
        raise


def validate_kpi_filters(request_params) -> Dict:
    """
    Validate KPI request filter parameters.

    Similar to execution filters but without pagination.

    Args:
        request_params: Django request.GET QueryDict object

    Returns:
        Dictionary of validated parameters

    Raises:
        ValidationError: If any parameter is invalid

    Example:
        >>> filters = validate_kpi_filters(request.GET)
        >>> # Returns: {'month': 'January', 'year': 2025, 'status': ['SUCCESS'], ...}
    """
    try:
        # Validate month
        month = validate_month(request_params.get('month', '').strip() or None)

        # Validate year
        year = validate_year(request_params.get('year', '').strip() or None)

        # Validate status list
        status_list = []
        if hasattr(request_params, 'getlist'):
            status_list = request_params.getlist('status')
        elif 'status' in request_params:
            single_status = request_params.get('status')
            if single_status:
                status_list = [single_status]

        statuses = validate_status_list(status_list)

        # Validate uploaded_by
        uploaded_by = validate_uploaded_by(
            request_params.get('uploaded_by', '').strip() or None
        )

        validated = {
            'month': month,
            'year': year,
            'status': statuses,
            'uploaded_by': uploaded_by
        }

        logger.debug(f"[Validation Success] KPI filters: {validated}")
        return validated

    except ValidationError as e:
        logger.warning(f"[Validation Error] KPI filters: {str(e)}")
        raise


# ============================================================================
# Convenience Validation Functions
# ============================================================================

def is_valid_uuid(uuid_string: str) -> bool:
    """
    Check if a string is a valid UUID format without raising exception.

    Args:
        uuid_string: String to check

    Returns:
        True if valid UUID format, False otherwise

    Example:
        >>> is_valid_uuid("550e8400-e29b-41d4-a716-446655440000")
        True
        >>> is_valid_uuid("not-a-uuid")
        False
    """
    try:
        validate_execution_id(uuid_string)
        return True
    except ValidationError:
        return False


def sanitize_string(value: str, max_length: int = 255) -> str:
    """
    Sanitize string input by stripping whitespace and enforcing max length.

    Args:
        value: String to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string

    Example:
        >>> sanitize_string("  hello world  ")
        'hello world'
    """
    if not value:
        return ""

    sanitized = value.strip()

    if len(sanitized) > max_length:
        logger.warning(f"String truncated from {len(sanitized)} to {max_length} chars")
        sanitized = sanitized[:max_length]

    return sanitized


# Example usage in views:
# from execution_validators import validate_execution_filters, ValidationError
#
# try:
#     filters = validate_execution_filters(request.GET)
#     # filters is now safe to use
# except ValidationError as e:
#     return JsonResponse({'success': False, 'error': str(e)}, status=400)