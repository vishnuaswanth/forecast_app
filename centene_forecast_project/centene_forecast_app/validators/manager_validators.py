"""
Manager View Validators

Simple validation functions for manager view parameters.
Validates report_month format and category existence.
"""

import re
from typing import Optional
from datetime import datetime


class ValidationError(Exception):
    """Custom validation error exception"""
    pass


def validate_report_month(report_month: str) -> str:
    """
    Validate report month format (YYYY-MM).
    
    Args:
        report_month: Report month string (e.g., '2025-02')
        
    Returns:
        Validated report_month string
        
    Raises:
        ValidationError: If format is invalid or date is unrealistic
        
    Example:
        >>> validate_report_month('2025-02')
        '2025-02'
        >>> validate_report_month('invalid')
        ValidationError: Invalid report month format
    """
    if not report_month:
        raise ValidationError("Report month is required")
    
    # Check format: YYYY-MM
    pattern = r'^\d{4}-(0[1-9]|1[0-2])$'
    if not re.match(pattern, report_month):
        raise ValidationError(
            "Invalid report month format. Expected format: YYYY-MM (e.g., '2025-02')"
        )
    
    # Validate it's a real date
    try:
        year, month = report_month.split('-')
        datetime(int(year), int(month), 1)
    except ValueError:
        raise ValidationError(f"Invalid date: {report_month}")
    
    # Reasonable date range check (2020-2030)
    year_int = int(year)
    if not (2020 <= year_int <= 2030):
        raise ValidationError(
            f"Report month year must be between 2020 and 2030, got {year_int}"
        )
    
    return report_month


def validate_category(category: Optional[str]) -> Optional[str]:
    """
    Validate category parameter.
    
    Args:
        category: Optional category filter (e.g., 'amisys-onshore' or None)
        
    Returns:
        Validated category string or None
        
    Raises:
        ValidationError: If category format is invalid
        
    Example:
        >>> validate_category('amisys-onshore')
        'amisys-onshore'
        >>> validate_category('')
        None
        >>> validate_category(None)
        None
    """
    # Empty string or None = all categories (valid)
    if not category:
        return None
    
    # Check format: lowercase letters, numbers, hyphens only
    pattern = r'^[a-z0-9-]+$'
    if not re.match(pattern, category):
        raise ValidationError(
            "Invalid category format. Use lowercase letters, numbers, and hyphens only"
        )
    
    # Length check (reasonable limits)
    if len(category) > 50:
        raise ValidationError("Category name too long (max 50 characters)")
    
    return category


def validate_manager_view_request(report_month: str, category: Optional[str] = None) -> dict:
    """
    Validate all manager view request parameters together.
    
    Args:
        report_month: Report month in YYYY-MM format
        category: Optional category filter
        
    Returns:
        Dictionary with validated parameters
        
    Raises:
        ValidationError: If any parameter is invalid
        
    Example:
        >>> validate_manager_view_request('2025-02', 'amisys-onshore')
        {'report_month': '2025-02', 'category': 'amisys-onshore'}
    """
    validated_data = {
        'report_month': validate_report_month(report_month),
        'category': validate_category(category)
    }
    
    return validated_data
