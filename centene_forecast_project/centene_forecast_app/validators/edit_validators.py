# edit_validators.py
"""
Validation functions for Edit View feature.

Follows the validation pattern from manager_validators.py.
All validators raise ValidationError on failure and return cleaned values on success.
"""

import re
from datetime import datetime
from typing import Optional
from core.config import EditViewConfig


class ValidationError(Exception):
    """Custom validation error for Edit View"""
    pass


def validate_allocation_report(report_value: str) -> str:
    """
    Validate allocation report format (YYYY-MM).

    Args:
        report_value: Report month in YYYY-MM format

    Returns:
        Cleaned report value

    Raises:
        ValidationError: If format is invalid or date is out of range

    Example:
        >>> validate_allocation_report('2025-04')
        '2025-04'
        >>> validate_allocation_report('invalid')
        ValidationError: Invalid format...
    """
    if not report_value:
        raise ValidationError("Allocation report is required")

    # Strip whitespace
    report_value = report_value.strip()

    # Format validation (YYYY-MM)
    pattern = r'^\d{4}-(0[1-9]|1[0-2])$'
    if not re.match(pattern, report_value):
        raise ValidationError(
            "Invalid format. Expected YYYY-MM (e.g., '2025-04')"
        )

    # Date validation
    try:
        year, month = report_value.split('-')
        datetime(int(year), int(month), 1)
    except ValueError:
        raise ValidationError(f"Invalid date: {report_value}")

    # Range validation (2020-2030)
    year_int = int(year)
    if not (2020 <= year_int <= 2030):
        raise ValidationError(
            f"Year must be between 2020-2030, got {year_int}"
        )

    return report_value


def validate_user_notes(notes: str) -> Optional[str]:
    """
    Validate user notes (optional field).

    Args:
        notes: User-provided notes string

    Returns:
        None if empty, cleaned string if valid

    Raises:
        ValidationError: If notes exceed maximum length

    Example:
        >>> validate_user_notes('Good allocation')
        'Good allocation'
        >>> validate_user_notes('')
        None
        >>> validate_user_notes('a' * 600)
        ValidationError: Notes exceed max length...
    """
    if not notes:
        return None

    notes = notes.strip()

    if not notes:
        return None

    max_length = EditViewConfig.MAX_USER_NOTES_LENGTH
    if len(notes) > max_length:
        raise ValidationError(
            f"Notes exceed max length ({max_length} chars), got {len(notes)} chars"
        )

    return notes


def validate_modified_records(records: list) -> list:
    """
    Validate modified records structure.

    Ensures:
    - Input is a list
    - List is not empty
    - Each record has required fields

    Args:
        records: List of modified record dictionaries

    Returns:
        Validated records list

    Raises:
        ValidationError: If structure is invalid or required fields missing

    Example:
        >>> validate_modified_records([{'main_lob': 'A', 'state': 'TX', ...}])
        [{'main_lob': 'A', ...}]
        >>> validate_modified_records([])
        ValidationError: No modified records provided
    """
    if not isinstance(records, list):
        raise ValidationError("modified_records must be a list")

    if len(records) == 0:
        raise ValidationError("No modified records provided")

    required_fields = ['main_lob', 'state', 'case_type', 'case_id', '_modified_fields']

    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValidationError(f"Record {idx} must be a dictionary")

        for field in required_fields:
            if field not in record:
                raise ValidationError(
                    f"Record {idx} missing required field: {field}"
                )

        # Validate _modified_fields structure
        modified_fields = record.get('_modified_fields')
        if not isinstance(modified_fields, dict):
            raise ValidationError(
                f"Record {idx}: _modified_fields must be a dictionary"
            )

    return records


def validate_bench_allocation_preview_request(month: str, year: int) -> dict:
    """
    Validate preview request parameters.

    Args:
        month: Month name (e.g., 'April')
        year: Year as integer (e.g., 2025)

    Returns:
        Dictionary with validated parameters

    Raises:
        ValidationError: If parameters are invalid

    Example:
        >>> validate_bench_allocation_preview_request('April', 2025)
        {'month': 'April', 'year': 2025}
        >>> validate_bench_allocation_preview_request('InvalidMonth', 2025)
        ValidationError: Invalid month name...
    """
    # Validate year
    if not isinstance(year, int) or not (2020 <= year <= 2030):
        raise ValidationError(
            f"Invalid year: {year}. Must be integer between 2020-2030"
        )

    # Month name to number mapping
    month_map = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }

    if month not in month_map:
        raise ValidationError(
            f"Invalid month name: {month}. Must be full month name (e.g., 'April')"
        )

    # Validate as YYYY-MM format using existing validator
    month_num = month_map[month]
    report_value = f"{year}-{month_num:02d}"
    validate_allocation_report(report_value)

    return {'month': month, 'year': year}


def validate_bench_allocation_update_request(
    month: str,
    year: int,
    modified_records: list,
    user_notes: Optional[str] = None
) -> dict:
    """
    Validate update request (combines multiple validators).

    Args:
        month: Month name
        year: Year as integer
        modified_records: List of modified record dictionaries
        user_notes: Optional user notes

    Returns:
        Dictionary with all validated parameters

    Raises:
        ValidationError: If any validation fails

    Example:
        >>> validate_bench_allocation_update_request(
        ...     'April', 2025, [...], 'Notes'
        ... )
        {'month': 'April', 'year': 2025, 'modified_records': [...], 'user_notes': 'Notes'}
    """
    # Validate month and year
    preview_validation = validate_bench_allocation_preview_request(month, year)

    return {
        'month': preview_validation['month'],
        'year': preview_validation['year'],
        'modified_records': validate_modified_records(modified_records),
        'user_notes': validate_user_notes(user_notes)
    }


def validate_history_log_request(
    month: Optional[str] = None,
    year: Optional[int] = None,
    page: int = 1,
    limit: int = 25
) -> dict:
    """
    Validate history log request parameters.

    Args:
        month: Optional month filter
        year: Optional year filter
        page: Page number (default: 1)
        limit: Records per page (default: 25)

    Returns:
        Dictionary with validated parameters

    Raises:
        ValidationError: If parameters are invalid

    Example:
        >>> validate_history_log_request(month='April', year=2025, page=1)
        {'month': 'April', 'year': 2025, 'page': 1, 'limit': 25}
    """
    # Validate page
    if not isinstance(page, int) or page < 1:
        raise ValidationError(f"Page must be a positive integer, got {page}")

    # Validate limit
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise ValidationError(
            f"Limit must be between 1-100, got {limit}"
        )

    # Validate month and year if provided
    if month and year:
        validate_bench_allocation_preview_request(month, year)
    elif month or year:
        # If only one is provided, raise error
        raise ValidationError(
            "Both month and year must be provided together, or neither"
        )

    return {
        'month': month,
        'year': year,
        'page': page,
        'limit': limit
    }


# Example usage:
# from edit_validators import (
#     ValidationError,
#     validate_allocation_report,
#     validate_bench_allocation_preview_request,
#     validate_bench_allocation_update_request
# )
#
# try:
#     validated = validate_bench_allocation_preview_request('April', 2025)
#     print(f"Valid: {validated}")
# except ValidationError as e:
#     print(f"Validation failed: {e}")