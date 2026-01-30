"""
Mock Data for Forecast Filters

Provides mock data for cascade filters in the forecast view.
Includes: years, months, platforms, markets, localities, and worktypes.

Replace with actual FastAPI endpoint calls when backend is ready.
"""

from typing import List, Dict, Optional
import logging

logger = logging.getLogger('django')


def get_forecast_filter_years() -> Dict:
    """
    Get available years for forecast filter.

    Returns:
        Dictionary with years list

    Example:
        {
            'years': [
                {'value': '2025', 'display': '2025'},
                {'value': '2024', 'display': '2024'}
            ]
        }
    """
    logger.info("Using mock data for forecast filter years")
    return {
        'years': [
            {'value': '2025', 'display': '2025'},
            {'value': '2024', 'display': '2024'},
            {'value': '2023', 'display': '2023'}
        ]
    }


def get_forecast_months_for_year(year: int) -> List[Dict[str, str]]:
    """
    Get available months for the selected year.

    Args:
        year: Selected year (e.g., 2025)

    Returns:
        List of month options with value and display

    Example:
        [
            {'value': '1', 'display': 'January'},
            {'value': '2', 'display': 'February'},
            ...
        ]
    """
    logger.info(f"Using mock data for forecast months - year: {year}")

    # Return all months for now (real API would return only months with data)
    return [
        {'value': '1', 'display': 'January'},
        {'value': '2', 'display': 'February'},
        {'value': '3', 'display': 'March'},
        {'value': '4', 'display': 'April'},
        {'value': '5', 'display': 'May'},
        {'value': '6', 'display': 'June'},
        {'value': '7', 'display': 'July'},
        {'value': '8', 'display': 'August'},
        {'value': '9', 'display': 'September'},
        {'value': '10', 'display': 'October'},
        {'value': '11', 'display': 'November'},
        {'value': '12', 'display': 'December'}
    ]


def get_forecast_platforms(year: int, month: int) -> List[Dict[str, str]]:
    """
    Get available platforms (formerly boc) for selected year and month.

    Args:
        year: Selected year
        month: Selected month (1-12)

    Returns:
        List of platform options

    Example:
        [
            {'value': 'amisys', 'display': 'Amisys'},
            {'value': 'facets', 'display': 'Facets'}
        ]
    """
    logger.info(f"Using mock data for forecast platforms - year: {year}, month: {month}")

    return [
        {'value': 'Amisys', 'display': 'Amisys'},
        {'value': 'Facets', 'display': 'Facets'},
        {'value': 'Xcelys', 'display': 'Xcelys'}
    ]


def get_forecast_markets(
    year: int,
    month: int,
    platform: str
) -> List[Dict[str, str]]:
    """
    Get available markets (formerly insurance_type) for selected platform.

    Args:
        year: Selected year
        month: Selected month
        platform: Selected platform

    Returns:
        List of market options filtered by platform

    Example:
        [
            {'value': 'medicaid', 'display': 'Medicaid'},
            {'value': 'medicare', 'display': 'Medicare'}
        ]
    """
    logger.info(
        f"Using mock data for forecast markets - "
        f"year: {year}, month: {month}, platform: {platform}"
    )

    # Return different markets based on platform for realistic cascading
    return [
        {'value': 'Medicaid', 'display': 'Medicaid'},
        {'value': 'Medicare', 'display': 'Medicare'},
        {'value': 'Marketplace', 'display': 'Marketplace'}
    ]


def get_forecast_localities(
    year: int,
    month: int,
    platform: str,
    market: str
) -> List[Dict[str, str]]:
    """
    Get available localities for selected platform and market.

    Args:
        year: Selected year
        month: Selected month
        platform: Selected platform
        market: Selected market

    Returns:
        List of locality options (includes 'All' since optional)

    Example:
        [
            {'value': '', 'display': '-- All Localities --'},
            {'value': 'domestic', 'display': 'Domestic'},
            {'value': 'offshore', 'display': 'Offshore'}
        ]
    """
    logger.info(
        f"Using mock data for forecast localities - "
        f"year: {year}, month: {month}, platform: {platform}, market: {market}"
    )

    return [
        {'value': '', 'display': '-- All Localities --'},
        {'value': 'DOMESTIC', 'display': 'Domestic'},
        {'value': 'GLOBAL', 'display': 'Global'},
        {'value': '(DOMESTIC)', 'display': '(Domestic)'},
        {'value': '(GLOBAL)', 'display': '(Global)'},
    ]


def get_forecast_worktypes(
    year: int,
    month: int,
    platform: str,
    market: str,
    locality: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Get available worktypes (formerly process) for selected filters.

    Args:
        year: Selected year
        month: Selected month
        platform: Selected platform
        market: Selected market
        locality: Optional selected locality

    Returns:
        List of worktype options

    Example:
        [
            {'value': 'claims', 'display': 'Claims Processing'},
            {'value': 'enrollment', 'display': 'Enrollment'}
        ]
    """
    logger.info(
        f"Using mock data for forecast worktypes - "
        f"year: {year}, month: {month}, platform: {platform}, "
        f"market: {market}, locality: {locality or 'all'}"
    )

    return [
        {'value': 'select', 'display': 'Select'},
        {'value': 'ADJ-Basic/NON MMP', 'display': 'ADJ-Basic NON MMP'},
        {'value': 'ADJ-COB NON MMP', 'display': 'ADJ-COB NON MMP'},
        {'value': 'APP-BASIC/NON MMP', 'display': 'APP-BASIC NON MMP'},
        {'value': 'APP-COB NON MMP', 'display': 'APP-COB NON MMP'},
        {'value': 'COR-Basic/NON MMP', 'display': 'COR-Basic NON MMP'},
        {'value': 'COR-COB NON MMP', 'display': 'COR-COB NON MMP'},
        {'value': 'FTC-Basic/Non MMP', 'display': 'FTC-Basic Non MMP'},
        {'value': 'FTC-COB NON MMP', 'display': 'FTC-COB NON MMP'},
        {'value': 'OMN-Basic/NON MMP', 'display': 'OMN-Basic NON MMP'},
        {'value': 'OMN-COB NON MMP', 'display': 'OMN-COB NON MMP'},
    ]
