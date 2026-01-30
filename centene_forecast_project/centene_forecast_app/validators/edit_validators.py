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
    - Each record has nested months object with valid structure

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

    required_fields = ['main_lob', 'state', 'case_type', 'case_id', 'modified_fields', 'months']

    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValidationError(f"Record {idx} must be a dictionary")

        for field in required_fields:
            if field not in record:
                raise ValidationError(
                    f"Record {idx} missing required field: {field}"
                )

        # Validate modified_fields structure
        modified_fields = record.get('modified_fields')
        if not isinstance(modified_fields, list):
            raise ValidationError(
                f"Record {idx}: modified_fields must be a list"
            )

        if len(modified_fields) == 0:
            raise ValidationError(
                f"Record {idx}: modified_fields cannot be empty"
            )

        # Validate that modified_fields contains valid field names (not the months object itself)
        for field_name in modified_fields:
            if not isinstance(field_name, str):
                raise ValidationError(
                    f"Record {idx}: modified_fields must contain strings, got {type(field_name)}"
                )
            # Field names should be like "target_cph", "Jun-25.fte_req", etc.
            if not field_name.strip():
                raise ValidationError(
                    f"Record {idx}: modified_fields cannot contain empty strings"
                )

        # Validate months structure (nested object)
        months = record.get('months')
        if not isinstance(months, dict):
            raise ValidationError(
                f"Record {idx}: months must be a dictionary (nested object)"
            )

        if len(months) == 0:
            raise ValidationError(
                f"Record {idx}: months object cannot be empty"
            )

        # Validate each month's data structure
        required_month_fields = ['forecast', 'fte_req', 'fte_avail', 'capacity',
                                'forecast_change', 'fte_req_change', 'fte_avail_change', 'capacity_change']

        for month_key, month_data in months.items():
            if not isinstance(month_data, dict):
                raise ValidationError(
                    f"Record {idx}, month {month_key}: month data must be a dictionary"
                )

            for field in required_month_fields:
                if field not in month_data:
                    raise ValidationError(
                        f"Record {idx}, month {month_key}: missing required field '{field}'"
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
    months: dict,
    modified_records: list,
    user_notes: Optional[str] = None
) -> dict:
    """
    Validate update request (combines multiple validators).

    Args:
        month: Month name
        year: Year as integer
        months: Month index mapping (month1-month6 to labels)
        modified_records: List of modified record dictionaries
        user_notes: Optional user notes

    Returns:
        Dictionary with all validated parameters

    Raises:
        ValidationError: If any validation fails

    Example:
        >>> validate_bench_allocation_update_request(
        ...     'April', 2025, {'month1': 'Jun-25', ...}, [...], 'Notes'
        ... )
        {'month': 'April', 'year': 2025, 'months': {...}, 'modified_records': [...], 'user_notes': 'Notes'}
    """
    # Validate month and year
    preview_validation = validate_bench_allocation_preview_request(month, year)

    # Validate months mapping
    if not isinstance(months, dict):
        raise ValidationError("months must be a dictionary")

    required_month_keys = ['month1', 'month2', 'month3', 'month4', 'month5', 'month6']
    for key in required_month_keys:
        if key not in months:
            raise ValidationError(f"months mapping must include {key}")
        if not isinstance(months[key], str) or not months[key]:
            raise ValidationError(f"months[{key}] must be a non-empty string")

    return {
        'month': preview_validation['month'],
        'year': preview_validation['year'],
        'months': months,
        'modified_records': validate_modified_records(modified_records),
        'user_notes': validate_user_notes(user_notes)
    }


def validate_history_log_request(
    month: Optional[str] = None,
    year: Optional[int] = None,
    page: int = 1,
    limit: int = 25,
    change_types: Optional[list] = None
) -> dict:
    """
    Validate history log request parameters.

    Args:
        month: Optional month filter
        year: Optional year filter
        page: Page number (default: 1)
        limit: Records per page (default: 25)
        change_types: Optional list of change types to filter by

    Returns:
        Dictionary with validated parameters

    Raises:
        ValidationError: If parameters are invalid

    Example:
        >>> validate_history_log_request(month='April', year=2025, page=1, change_types=['Bench Allocation'])
        {'month': 'April', 'year': 2025, 'page': 1, 'limit': 25, 'change_types': ['Bench Allocation']}
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

    # Validate change_types if provided
    if change_types is not None:
        if not isinstance(change_types, list):
            raise ValidationError(
                f"change_types must be a list, got {type(change_types)}"
            )
        if len(change_types) > 20:
            raise ValidationError(
                f"Too many change types (max 20), got {len(change_types)}"
            )
        # Each change type must be a non-empty string
        for ct in change_types:
            if not isinstance(ct, str) or not ct.strip():
                raise ValidationError(
                    f"Each change type must be a non-empty string, got {ct}"
                )

    return {
        'month': month,
        'year': year,
        'page': page,
        'limit': limit,
        'change_types': change_types or []
    }


# ============================================================
# TARGET CPH VALIDATORS
# ============================================================

def validate_target_cph_value(cph_value: float) -> float:
    """
    Validate single CPH value.

    Args:
        cph_value: CPH value to validate

    Returns:
        Validated and rounded CPH value

    Raises:
        ValidationError: If value is invalid

    Example:
        >>> validate_target_cph_value(125.456)
        125.46
        >>> validate_target_cph_value(-10)
        ValidationError: CPH value cannot be negative
    """
    from core.config import TargetCPHConfig

    # Check if value is numeric
    if not isinstance(cph_value, (int, float)):
        raise ValidationError(
            f"CPH value must be a number, got {type(cph_value).__name__}"
        )

    # Convert to float
    cph_value = float(cph_value)

    # Check minimum
    if cph_value < TargetCPHConfig.MIN_CPH_VALUE:
        raise ValidationError(
            f"CPH value cannot be less than {TargetCPHConfig.MIN_CPH_VALUE}, got {cph_value}"
        )

    # Check maximum
    if cph_value > TargetCPHConfig.MAX_CPH_VALUE:
        raise ValidationError(
            f"CPH value cannot exceed {TargetCPHConfig.MAX_CPH_VALUE}, got {cph_value}"
        )

    # Round to configured decimal places
    rounded_value = round(cph_value, TargetCPHConfig.CPH_DECIMAL_PLACES)

    return rounded_value


def validate_cph_record(record: dict) -> dict:
    """
    Validate CPH record structure.

    Args:
        record: CPH record dictionary

    Returns:
        Validated record with cleaned values

    Raises:
        ValidationError: If record structure is invalid

    Example:
        >>> record = {'id': 'cph_1', 'lob': 'Amisys', 'case_type': 'Claims', 'target_cph': 50, 'modified_target_cph': 52}
        >>> validate_cph_record(record)
        {'id': 'cph_1', 'lob': 'Amisys', ...}
    """
    if not isinstance(record, dict):
        raise ValidationError(f"CPH record must be a dictionary, got {type(record).__name__}")

    # Required fields
    required_fields = ['id', 'lob', 'case_type', 'target_cph', 'modified_target_cph']

    for field in required_fields:
        if field not in record:
            raise ValidationError(f"CPH record missing required field: {field}")

    # Clean string fields
    record['id'] = str(record['id']).strip()
    record['lob'] = str(record['lob']).strip()
    record['case_type'] = str(record['case_type']).strip()

    if not record['id']:
        raise ValidationError("CPH record ID cannot be empty")
    if not record['lob']:
        raise ValidationError("CPH record LOB cannot be empty")
    if not record['case_type']:
        raise ValidationError("CPH record case_type cannot be empty")

    # Validate CPH values
    record['target_cph'] = validate_target_cph_value(record['target_cph'])
    record['modified_target_cph'] = validate_target_cph_value(record['modified_target_cph'])

    return record


def validate_target_cph_preview_request(
    month: str,
    year: int,
    modified_records: list
) -> dict:
    """
    Validate CPH preview request.

    Args:
        month: Month name (e.g., 'April')
        year: Year (e.g., 2025)
        modified_records: List of modified CPH records

    Returns:
        Dictionary with validated parameters

    Raises:
        ValidationError: If parameters are invalid

    Example:
        >>> validate_target_cph_preview_request('April', 2025, [...])
        {'month': 'April', 'year': 2025, 'modified_records': [...]}
    """
    # Reuse month/year validation from bench allocation
    preview_validation = validate_bench_allocation_preview_request(month, year)

    # Validate modified_records is a list
    if not isinstance(modified_records, list):
        raise ValidationError(
            f"modified_records must be a list, got {type(modified_records).__name__}"
        )

    if len(modified_records) == 0:
        raise ValidationError("No modified CPH records provided")

    # Validate each record
    validated_records = []
    for idx, record in enumerate(modified_records):
        try:
            validated_record = validate_cph_record(record)
            validated_records.append(validated_record)
        except ValidationError as e:
            raise ValidationError(f"Record {idx}: {e}")

    # Filter out unchanged records (where target_cph == modified_target_cph)
    changed_records = [
        r for r in validated_records
        if r['target_cph'] != r['modified_target_cph']
    ]

    if len(changed_records) == 0:
        raise ValidationError(
            "No actual CPH changes detected. All modified_target_cph values match target_cph."
        )

    return {
        'month': preview_validation['month'],
        'year': preview_validation['year'],
        'modified_records': changed_records
    }


def validate_cph_modified_record(record: dict, idx: int = 0) -> None:
    """
    Validate that a ModifiedForecastRecord includes CPH fields as floats.

    Args:
        record: Record dictionary
        idx: Record index for error messages

    Raises:
        ValidationError: If CPH fields are missing or invalid

    Example:
        >>> validate_cph_modified_record({'target_cph': 50.0, 'target_cph_change': 5.0, ...})
    """
    # Check required CPH fields
    if 'target_cph' not in record:
        raise ValidationError(f"Record {idx}: missing required field 'target_cph'")
    if 'target_cph_change' not in record:
        raise ValidationError(f"Record {idx}: missing required field 'target_cph_change'")

    # Validate CPH values are numeric (floats)
    try:
        target_cph = float(record['target_cph'])
        _target_cph_change = float(record['target_cph_change'])  # noqa: F841 - validated, not used
    except (ValueError, TypeError):
        raise ValidationError(
            f"Record {idx}: target_cph and target_cph_change must be numeric"
        )

    # Validate CPH range (per API spec: 0.0 to 200.0)
    if not (0.0 <= target_cph <= 200.0):
        raise ValidationError(
            f"Record {idx}: target_cph must be between 0.0 and 200.0, got {target_cph}"
        )


def validate_target_cph_update_request(
    month: str,
    year: int,
    months: dict,
    modified_records: list,
    user_notes: Optional[str] = None
) -> dict:
    """
    Validate CPH update request using SAME format as bench allocation.

    CPH update uses ModifiedForecastRecord format with:
    - Top-level months mapping (month1-month6)
    - Nested months object in each record
    - target_cph and target_cph_change fields (floats)
    - All standard forecast fields (integers)

    Args:
        month: Month name
        year: Year
        months: Month index mapping (month1-month6 to labels)
        modified_records: List of ModifiedForecastRecord dictionaries
        user_notes: Optional user notes

    Returns:
        Dictionary with all validated parameters

    Raises:
        ValidationError: If any validation fails

    Example:
        >>> validate_target_cph_update_request(
        ...     'April', 2025, {'month1': 'Jun-25', ...}, [...], 'Updated CPH'
        ... )
        {'month': 'April', 'year': 2025, 'months': {...}, 'modified_records': [...], 'user_notes': 'Updated CPH'}
    """
    # Validate month and year
    preview_validation = validate_bench_allocation_preview_request(month, year)

    # Validate months mapping (same as bench allocation)
    if not isinstance(months, dict):
        raise ValidationError("months must be a dictionary")

    required_month_keys = ['month1', 'month2', 'month3', 'month4', 'month5', 'month6']
    for key in required_month_keys:
        if key not in months:
            raise ValidationError(f"months mapping must include {key}")
        if not isinstance(months[key], str) or not months[key]:
            raise ValidationError(f"months[{key}] must be a non-empty string")

    # Validate modified_records structure (same as bench allocation)
    validated_records = validate_modified_records(modified_records)

    # Additional CPH-specific validation: ensure target_cph fields exist
    for idx, record in enumerate(validated_records):
        validate_cph_modified_record(record, idx)

    return {
        'month': preview_validation['month'],
        'year': preview_validation['year'],
        'months': months,
        'modified_records': validated_records,
        'user_notes': validate_user_notes(user_notes)
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
