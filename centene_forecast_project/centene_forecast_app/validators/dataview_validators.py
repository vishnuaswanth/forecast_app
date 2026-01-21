"""
Data View Validators

Validation functions for data view parameters.
Validates year, month, platform, market, locality, and worktype parameters.
"""

import re
from typing import Optional
from datetime import datetime


class ValidationError(Exception):
    """Custom validation error exception"""
    pass


def validate_year(year: str) -> int:
    """
    Validate year parameter.

    Args:
        year: Year string (e.g., '2025')

    Returns:
        Validated year as integer

    Raises:
        ValidationError: If year is invalid

    Example:
        >>> validate_year('2025')
        2025
    """
    if not year:
        raise ValidationError("Year is required")

    try:
        year_int = int(year)
    except ValueError:
        raise ValidationError(f"Invalid year format: {year}. Expected 4-digit number")

    # Reasonable range check
    if not (2020 <= year_int <= 2030):
        raise ValidationError(f"Year must be between 2020 and 2030, got {year_int}")

    return year_int


def validate_month(month: str) -> int:
    """
    Validate month parameter.

    Args:
        month: Month string (e.g., '1' or '12')

    Returns:
        Validated month as integer (1-12)

    Raises:
        ValidationError: If month is invalid

    Example:
        >>> validate_month('7')
        7
    """
    if not month:
        raise ValidationError("Month is required")

    try:
        month_int = int(month)
    except ValueError:
        raise ValidationError(f"Invalid month format: {month}. Expected number 1-12")

    if not (1 <= month_int <= 12):
        raise ValidationError(f"Month must be between 1 and 12, got {month_int}")

    return month_int


def validate_platform(platform: str) -> str:
    """
    Validate platform parameter (formerly boc).

    Args:
        platform: Platform string (e.g., 'amisys', 'facets', 'xcelys')

    Returns:
        Validated platform string

    Raises:
        ValidationError: If platform is invalid

    Example:
        >>> validate_platform('amisys')
        'amisys'
    """
    if not platform or platform == 'select':
        raise ValidationError("Platform is required")

    # Allow only letters
    if not re.match(r'^[a-zA-Z]+$', platform):
        raise ValidationError("Invalid platform format")

    if len(platform) > 50:
        raise ValidationError("Platform name too long (max 50 characters)")

    return platform.strip()


def validate_market(market: str) -> str:
    """
    Validate market parameter (formerly insurance_type).

    Args:
        market: Market string (e.g., 'medicaid', 'medicare', 'marketplace')

    Returns:
        Validated market string

    Raises:
        ValidationError: If market is invalid

    Example:
        >>> validate_market('medicaid')
        'medicaid'
    """
    if not market or market == 'select':
        raise ValidationError("Market is required")

    # Allow letters, hyphen and space
    if not re.match(r'^[a-zA-Z\s\-]+$', market):
        raise ValidationError("Invalid market format")

    if len(market) > 50:
        raise ValidationError("Market name too long (max 50 characters)")

    return market.strip()


def validate_locality(locality: Optional[str]) -> Optional[str]:
    """
    Validate locality parameter (optional).

    Args:
        locality: Optional locality string (e.g., 'domestic', 'global','(global)','(local)')

    Returns:
        Validated locality string or None

    Raises:
        ValidationError: If locality format is invalid

    Example:
        >>> validate_locality('domestic')
        'domestic'
        >>> validate_locality('')
        None
    """
    # Empty or 'select' means no locality filter (optional)
    if not locality or locality == 'select':
        return None

    # Allow only letters and brackets
    if not re.match(r'^[a-zA-Z\(\)]+$', locality):
        raise ValidationError("Invalid locality format - only letters and brackets allowed")

    if len(locality) > 50:
        raise ValidationError("Locality name too long (max 50 characters)")

    return locality.strip()


def validate_worktype(worktype: str) -> str:
    """
    Validate worktype parameter (formerly process).

    Args:
        worktype: Worktype string (e.g., 'FTC-Basic/Non MMP', 'FTC COB NON MMP')

    Returns:
        Validated worktype string

    Raises:
        ValidationError: If worktype is invalid

    Example:
        >>> validate_worktype('claims')
        'claims'
    """
    if not worktype or worktype == 'select':
        raise ValidationError("Worktype is required")

    # Allow letters, numbers, spaces, hyphens, forward slashes
    if not re.match(r'^[a-zA-Z0-9\s\-/]+$', worktype):
        raise ValidationError("Invalid worktype format") 

    if len(worktype) > 100:
        raise ValidationError("Worktype name too long (max 100 characters)")

    return worktype.strip()


def validate_forecast_filters(
    year: str,
    month: str,
    platform: str,
    market: str,
    worktype: str,
    locality: Optional[str] = None
) -> dict:
    """
    Validate all forecast filter parameters together.

    Args:
        year: Year string (required)
        month: Month string (required)
        platform: Platform string (required, formerly boc)
        market: Market string (required, formerly insurance_type)
        worktype: Worktype string (required, formerly process)
        locality: Locality string (optional)

    Returns:
        Dictionary with validated parameters

    Raises:
        ValidationError: If any parameter is invalid

    Example:
        >>> validate_forecast_filters('2025', '7', 'amisys', 'medicaid', 'claims', 'domestic')
        {
            'year': 2025,
            'month': 7,
            'platform': 'amisys',
            'market': 'medicaid',
            'worktype': 'claims',
            'locality': 'domestic'
        }
    """
    validated_data = {
        'year': validate_year(year),
        'month': validate_month(month),
        'platform': validate_platform(platform),
        'market': validate_market(market),
        'worktype': validate_worktype(worktype),
        'locality': validate_locality(locality)
    }

    return validated_data


def validate_cascade_request(
    year: Optional[str] = None,
    month: Optional[str] = None,
    platform: Optional[str] = None,
    market: Optional[str] = None,
    locality: Optional[str] = None
) -> dict:
    """
    Validate parameters for cascading dropdown requests.
    Less strict than full validation - only validates provided params.

    Args:
        year: Optional year string
        month: Optional month string
        platform: Optional platform string
        market: Optional market string
        locality: Optional locality string

    Returns:
        Dictionary with validated parameters (only those provided)

    Raises:
        ValidationError: If any provided parameter is invalid

    Example:
        >>> validate_cascade_request(year='2025', platform='amisys')
        {'year': 2025, 'platform': 'amisys'}
    """
    validated_data = {}

    if year:
        validated_data['year'] = validate_year(year)

    if month:
        validated_data['month'] = validate_month(month)

    if platform and platform != 'select':
        validated_data['platform'] = validate_platform(platform)

    if market and market != 'select':
        validated_data['market'] = validate_market(market)

    if locality and locality != 'select':
        validated_data['locality'] = validate_locality(locality)

    return validated_data