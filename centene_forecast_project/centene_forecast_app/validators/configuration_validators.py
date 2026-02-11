# configuration_validators.py
"""
Validation functions for Configuration View feature.

Follows the validation pattern from edit_validators.py.
All validators raise ValidationError on failure and return cleaned values on success.
"""

from typing import Optional, List, Dict
from core.config import ConfigurationViewConfig


class ValidationError(Exception):
    """Custom validation error for Configuration View"""
    pass


# ============================================================
# MONTH CONFIGURATION VALIDATORS
# ============================================================

def validate_month_name(month: str) -> str:
    """
    Validate month name.

    Args:
        month: Month name to validate

    Returns:
        Cleaned month name

    Raises:
        ValidationError: If month is invalid

    Example:
        >>> validate_month_name('January')
        'January'
        >>> validate_month_name('Invalid')
        ValidationError: Invalid month name...
    """
    if not month:
        raise ValidationError("Month is required")

    month = month.strip()

    if month not in ConfigurationViewConfig.MONTH_NAMES:
        raise ValidationError(
            f"Invalid month name: '{month}'. "
            f"Must be one of: {', '.join(ConfigurationViewConfig.MONTH_NAMES)}"
        )

    return month


def validate_year(year) -> int:
    """
    Validate year value.

    Args:
        year: Year value (int or string)

    Returns:
        Validated year as integer

    Raises:
        ValidationError: If year is invalid or out of range

    Example:
        >>> validate_year(2025)
        2025
        >>> validate_year('2025')
        2025
        >>> validate_year(1900)
        ValidationError: Year must be between...
    """
    if year is None:
        raise ValidationError("Year is required")

    try:
        year_int = int(year)
    except (ValueError, TypeError):
        raise ValidationError(f"Year must be a valid integer, got: {year}")

    min_year = ConfigurationViewConfig.MIN_YEAR
    max_year = ConfigurationViewConfig.MAX_YEAR

    if not (min_year <= year_int <= max_year):
        raise ValidationError(
            f"Year must be between {min_year} and {max_year}, got: {year_int}"
        )

    return year_int


def validate_work_type(work_type: str) -> str:
    """
    Validate work type.

    Args:
        work_type: Work type to validate ('Domestic' or 'Global')

    Returns:
        Cleaned work type

    Raises:
        ValidationError: If work type is invalid

    Example:
        >>> validate_work_type('Domestic')
        'Domestic'
        >>> validate_work_type('Invalid')
        ValidationError: Invalid work type...
    """
    if not work_type:
        raise ValidationError("Work type is required")

    work_type = work_type.strip()

    if work_type not in ConfigurationViewConfig.WORK_TYPES:
        raise ValidationError(
            f"Invalid work type: '{work_type}'. "
            f"Must be one of: {', '.join(ConfigurationViewConfig.WORK_TYPES)}"
        )

    return work_type


def validate_working_days(days) -> int:
    """
    Validate working days value.

    Args:
        days: Working days value (1-31)

    Returns:
        Validated working days as integer

    Raises:
        ValidationError: If working days is out of range

    Example:
        >>> validate_working_days(22)
        22
        >>> validate_working_days(0)
        ValidationError: Working days must be between...
    """
    if days is None:
        raise ValidationError("Working days is required")

    try:
        days_int = int(days)
    except (ValueError, TypeError):
        raise ValidationError(f"Working days must be a valid integer, got: {days}")

    min_days = ConfigurationViewConfig.MIN_WORKING_DAYS
    max_days = ConfigurationViewConfig.MAX_WORKING_DAYS

    if not (min_days <= days_int <= max_days):
        raise ValidationError(
            f"Working days must be between {min_days} and {max_days}, got: {days_int}"
        )

    return days_int


def validate_occupancy(value) -> float:
    """
    Validate occupancy value (0.0 to 1.0).

    Args:
        value: Occupancy value as decimal (e.g., 0.85 for 85%)

    Returns:
        Validated occupancy as float

    Raises:
        ValidationError: If occupancy is out of range

    Example:
        >>> validate_occupancy(0.85)
        0.85
        >>> validate_occupancy(1.5)
        ValidationError: Occupancy must be between...
    """
    if value is None:
        raise ValidationError("Occupancy is required")

    try:
        value_float = float(value)
    except (ValueError, TypeError):
        raise ValidationError(f"Occupancy must be a valid number, got: {value}")

    min_val = ConfigurationViewConfig.MIN_OCCUPANCY
    max_val = ConfigurationViewConfig.MAX_OCCUPANCY

    if not (min_val <= value_float <= max_val):
        raise ValidationError(
            f"Occupancy must be between {min_val} and {max_val} (0-100%), got: {value_float}"
        )

    return round(value_float, 4)


def validate_shrinkage(value) -> float:
    """
    Validate shrinkage value (0.0 to 1.0).

    Args:
        value: Shrinkage value as decimal (e.g., 0.20 for 20%)

    Returns:
        Validated shrinkage as float

    Raises:
        ValidationError: If shrinkage is out of range

    Example:
        >>> validate_shrinkage(0.20)
        0.2
        >>> validate_shrinkage(1.5)
        ValidationError: Shrinkage must be between...
    """
    if value is None:
        raise ValidationError("Shrinkage is required")

    try:
        value_float = float(value)
    except (ValueError, TypeError):
        raise ValidationError(f"Shrinkage must be a valid number, got: {value}")

    min_val = ConfigurationViewConfig.MIN_SHRINKAGE
    max_val = ConfigurationViewConfig.MAX_SHRINKAGE

    if not (min_val <= value_float <= max_val):
        raise ValidationError(
            f"Shrinkage must be between {min_val} and {max_val} (0-100%), got: {value_float}"
        )

    return round(value_float, 4)


def validate_work_hours(hours) -> float:
    """
    Validate work hours value (1.0 to 24.0).

    Args:
        hours: Work hours value

    Returns:
        Validated work hours as float

    Raises:
        ValidationError: If work hours is out of range

    Example:
        >>> validate_work_hours(8.0)
        8.0
        >>> validate_work_hours(25)
        ValidationError: Work hours must be between...
    """
    if hours is None:
        raise ValidationError("Work hours is required")

    try:
        hours_float = float(hours)
    except (ValueError, TypeError):
        raise ValidationError(f"Work hours must be a valid number, got: {hours}")

    min_val = ConfigurationViewConfig.MIN_WORK_HOURS
    max_val = ConfigurationViewConfig.MAX_WORK_HOURS

    if not (min_val <= hours_float <= max_val):
        raise ValidationError(
            f"Work hours must be between {min_val} and {max_val}, got: {hours_float}"
        )

    return round(hours_float, 2)


def validate_month_config_create(data: Dict) -> Dict:
    """
    Validate month configuration create request.

    Args:
        data: Dictionary with configuration data

    Returns:
        Validated data dictionary

    Raises:
        ValidationError: If any field is invalid

    Example:
        >>> data = {'month': 'January', 'year': 2025, 'work_type': 'Domestic', ...}
        >>> validated = validate_month_config_create(data)
    """
    if not isinstance(data, dict):
        raise ValidationError("Data must be a dictionary")

    validated = {
        'month': validate_month_name(data.get('month', '')),
        'year': validate_year(data.get('year')),
        'work_type': validate_work_type(data.get('work_type', '')),
        'working_days': validate_working_days(data.get('working_days')),
        'occupancy': validate_occupancy(data.get('occupancy')),
        'shrinkage': validate_shrinkage(data.get('shrinkage')),
        'work_hours': validate_work_hours(data.get('work_hours')),
    }

    # Optional updated_by field
    updated_by = data.get('updated_by', '').strip()
    if updated_by:
        validated['updated_by'] = updated_by

    return validated


def validate_month_config_update(config_id, data: Dict) -> Dict:
    """
    Validate month configuration update request.

    Args:
        config_id: ID of configuration to update
        data: Dictionary with updated configuration data

    Returns:
        Validated data dictionary with config_id

    Raises:
        ValidationError: If any field is invalid
    """
    if config_id is None:
        raise ValidationError("Configuration ID is required")

    try:
        config_id_int = int(config_id)
    except (ValueError, TypeError):
        raise ValidationError(f"Configuration ID must be a valid integer, got: {config_id}")

    if config_id_int < 1:
        raise ValidationError(f"Configuration ID must be positive, got: {config_id_int}")

    validated = validate_month_config_create(data)
    validated['config_id'] = config_id_int

    return validated


def validate_month_config_bulk(configs: List[Dict]) -> List[Dict]:
    """
    Validate bulk month configuration create request.

    Args:
        configs: List of configuration dictionaries

    Returns:
        List of validated configuration dictionaries

    Raises:
        ValidationError: If any configuration is invalid
    """
    if not isinstance(configs, list):
        raise ValidationError("Configs must be a list")

    if len(configs) == 0:
        raise ValidationError("At least one configuration is required")

    max_bulk = ConfigurationViewConfig.MAX_BULK_RECORDS
    if len(configs) > max_bulk:
        raise ValidationError(
            f"Too many configurations. Maximum allowed: {max_bulk}, got: {len(configs)}"
        )

    validated_configs = []
    for idx, config in enumerate(configs):
        try:
            validated = validate_month_config_create(config)
            validated_configs.append(validated)
        except ValidationError as e:
            raise ValidationError(f"Configuration {idx + 1}: {e}")

    return validated_configs


# ============================================================
# TARGET CPH CONFIGURATION VALIDATORS
# ============================================================

def validate_main_lob(lob: str) -> str:
    """
    Validate Main LOB value.

    Args:
        lob: Main LOB string

    Returns:
        Cleaned Main LOB string

    Raises:
        ValidationError: If LOB is empty or exceeds max length

    Example:
        >>> validate_main_lob('Amisys Medicaid')
        'Amisys Medicaid'
        >>> validate_main_lob('')
        ValidationError: Main LOB is required
    """
    if not lob:
        raise ValidationError("Main LOB is required")

    lob = lob.strip()

    if not lob:
        raise ValidationError("Main LOB cannot be empty or whitespace only")

    max_length = ConfigurationViewConfig.MAX_LOB_LENGTH
    if len(lob) > max_length:
        raise ValidationError(
            f"Main LOB exceeds maximum length of {max_length} characters, got: {len(lob)}"
        )

    return lob


def validate_case_type(case_type: str) -> str:
    """
    Validate Case Type value.

    Args:
        case_type: Case Type string

    Returns:
        Cleaned Case Type string

    Raises:
        ValidationError: If case type is empty or exceeds max length

    Example:
        >>> validate_case_type('Claims Processing')
        'Claims Processing'
        >>> validate_case_type('')
        ValidationError: Case Type is required
    """
    if not case_type:
        raise ValidationError("Case Type is required")

    case_type = case_type.strip()

    if not case_type:
        raise ValidationError("Case Type cannot be empty or whitespace only")

    max_length = ConfigurationViewConfig.MAX_CASE_TYPE_LENGTH
    if len(case_type) > max_length:
        raise ValidationError(
            f"Case Type exceeds maximum length of {max_length} characters, got: {len(case_type)}"
        )

    return case_type


def validate_target_cph_value(value) -> float:
    """
    Validate Target CPH value.

    Args:
        value: Target CPH value (must be a positive number)

    Returns:
        Validated Target CPH as float

    Raises:
        ValidationError: If value is negative or invalid

    Example:
        >>> validate_target_cph_value(125.5)
        125.5
        >>> validate_target_cph_value(-10)
        ValidationError: Target CPH must be...
    """
    if value is None:
        raise ValidationError("Target CPH is required")

    try:
        value_float = float(value)
    except (ValueError, TypeError):
        raise ValidationError(f"Target CPH must be a valid number, got: {value}")

    min_val = ConfigurationViewConfig.MIN_TARGET_CPH

    if value_float < min_val:
        raise ValidationError(
            f"Target CPH must be at least {min_val}, got: {value_float}"
        )

    return round(value_float, 2)


def validate_target_cph_create(data: Dict) -> Dict:
    """
    Validate Target CPH configuration create request.

    Args:
        data: Dictionary with configuration data

    Returns:
        Validated data dictionary

    Raises:
        ValidationError: If any field is invalid

    Example:
        >>> data = {'main_lob': 'Amisys', 'case_type': 'Claims', 'target_cph': 125.5}
        >>> validated = validate_target_cph_create(data)
    """
    if not isinstance(data, dict):
        raise ValidationError("Data must be a dictionary")

    validated = {
        'main_lob': validate_main_lob(data.get('main_lob', '')),
        'case_type': validate_case_type(data.get('case_type', '')),
        'target_cph': validate_target_cph_value(data.get('target_cph')),
    }

    # Optional updated_by field
    updated_by = data.get('updated_by', '').strip() if data.get('updated_by') else ''
    if updated_by:
        validated['updated_by'] = updated_by

    return validated


def validate_target_cph_update(config_id, data: Dict) -> Dict:
    """
    Validate Target CPH configuration update request.

    Args:
        config_id: ID of configuration to update
        data: Dictionary with updated configuration data

    Returns:
        Validated data dictionary with config_id

    Raises:
        ValidationError: If any field is invalid
    """
    if config_id is None:
        raise ValidationError("Configuration ID is required")

    try:
        config_id_int = int(config_id)
    except (ValueError, TypeError):
        raise ValidationError(f"Configuration ID must be a valid integer, got: {config_id}")

    if config_id_int < 1:
        raise ValidationError(f"Configuration ID must be positive, got: {config_id_int}")

    validated = validate_target_cph_create(data)
    validated['config_id'] = config_id_int

    return validated


def validate_target_cph_bulk(configs: List[Dict]) -> List[Dict]:
    """
    Validate bulk Target CPH configuration create request.

    Args:
        configs: List of configuration dictionaries

    Returns:
        List of validated configuration dictionaries

    Raises:
        ValidationError: If any configuration is invalid
    """
    if not isinstance(configs, list):
        raise ValidationError("Configs must be a list")

    if len(configs) == 0:
        raise ValidationError("At least one configuration is required")

    max_bulk = ConfigurationViewConfig.MAX_BULK_RECORDS
    if len(configs) > max_bulk:
        raise ValidationError(
            f"Too many configurations. Maximum allowed: {max_bulk}, got: {len(configs)}"
        )

    validated_configs = []
    for idx, config in enumerate(configs):
        try:
            validated = validate_target_cph_create(config)
            validated_configs.append(validated)
        except ValidationError as e:
            raise ValidationError(f"Configuration {idx + 1}: {e}")

    return validated_configs


def validate_config_id(config_id) -> int:
    """
    Validate a configuration ID.

    Args:
        config_id: Configuration ID to validate

    Returns:
        Validated ID as integer

    Raises:
        ValidationError: If ID is invalid
    """
    if config_id is None:
        raise ValidationError("Configuration ID is required")

    try:
        config_id_int = int(config_id)
    except (ValueError, TypeError):
        raise ValidationError(f"Configuration ID must be a valid integer, got: {config_id}")

    if config_id_int < 1:
        raise ValidationError(f"Configuration ID must be positive, got: {config_id_int}")

    return config_id_int


def validate_filter_params(
    month: Optional[str] = None,
    year: Optional[int] = None,
    work_type: Optional[str] = None
) -> Dict:
    """
    Validate filter parameters for month configuration list.

    Args:
        month: Optional month filter
        year: Optional year filter
        work_type: Optional work type filter

    Returns:
        Dictionary with validated filter values (None values filtered out)

    Raises:
        ValidationError: If any filter value is invalid
    """
    validated = {}

    if month:
        validated['month'] = validate_month_name(month)

    if year is not None:
        validated['year'] = validate_year(year)

    if work_type:
        validated['work_type'] = validate_work_type(work_type)

    return validated
