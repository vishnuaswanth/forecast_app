"""
Data View Service Layer

Business logic for data view cascading dropdowns and filter management.
Handles interactions with repository layer and data transformations.
"""

import logging
from typing import Dict, List, Optional
from centene_forecast_app.repository import (
    get_forecast_filter_years,
    get_forecast_months_for_year,
    get_forecast_platforms,
    get_forecast_markets,
    get_forecast_localities,
    get_forecast_worktypes
)

logger = logging.getLogger('django')


class ForecastFilterService:
    """
    Service class for data View filter logic.

    Provides methods to get cascading dropdown options based on
    user selections. Each method fetches filtered data from repository.
    """

    @staticmethod
    def get_initial_filter_options() -> Dict[str, List[Dict[str, str]]]:
        """
        Get initial filter options (years only for cascade start).

        Returns:
            Dictionary containing years list:
            {
                'years': [
                    {'value': '2025', 'display': '2025'},
                    {'value': '2024', 'display': '2024'}
                ]
            }

        Example:
            >>> service = ForecastFilterService()
            >>> options = service.get_initial_filter_options()
            >>> print(options['years'])
            [{'value': '2025', 'display': '2025'}]
        """
        logger.info("Fetching initial forecast filter options (years)")

        try:
            filters = get_forecast_filter_years()

            logger.debug(f"Retrieved {len(filters['years'])} years")

            return filters

        except Exception as e:
            logger.error(f"Failed to get initial filter options: {str(e)}")
            return {'years': []}

    @staticmethod
    def get_months_for_year(year: int) -> List[Dict[str, str]]:
        """
        Get available months for the selected year.

        Args:
            year: Selected year (e.g., 2025)

        Returns:
            List of month options:
            [
                {'value': '1', 'display': 'January'},
                {'value': '2', 'display': 'February'},
                ...
            ]

        Example:
            >>> service = ForecastFilterService()
            >>> months = service.get_months_for_year(2025)
        """
        logger.info(f"Fetching months for year: {year}")

        try:
            months = get_forecast_months_for_year(year)

            logger.debug(f"Retrieved {len(months)} months for year {year}")

            return months

        except Exception as e:
            logger.error(f"Failed to get months for year {year}: {str(e)}")
            return []

    @staticmethod
    def get_platforms_for_selection(year: int, month: int) -> List[Dict[str, str]]:
        """
        Get available platforms for selected year and month.

        Args:
            year: Selected year
            month: Selected month (1-12)

        Returns:
            List of platform options (formerly boc)

        Example:
            >>> service = ForecastFilterService()
            >>> platforms = service.get_platforms_for_selection(2025, 7)
        """
        logger.info(f"Fetching platforms for year: {year}, month: {month}")

        try:
            platforms = get_forecast_platforms(year, month)

            logger.debug(f"Retrieved {len(platforms)} platforms")

            return platforms

        except Exception as e:
            logger.error(f"Failed to get platforms: {str(e)}")
            return []

    @staticmethod
    def get_markets_for_platform(
        year: int,
        month: int,
        platform: str
    ) -> List[Dict[str, str]]:
        """
        Get available markets for selected platform (formerly insurance types).

        Args:
            year: Selected year
            month: Selected month
            platform: Selected platform

        Returns:
            List of market options filtered by platform

        Example:
            >>> service = ForecastFilterService()
            >>> markets = service.get_markets_for_platform(2025, 7, 'amisys')
        """
        logger.info(
            f"Fetching markets for platform: {platform}, "
            f"year: {year}, month: {month}"
        )

        try:
            markets = get_forecast_markets(year, month, platform)

            logger.debug(f"Retrieved {len(markets)} markets for platform {platform}")

            return markets

        except Exception as e:
            logger.error(f"Failed to get markets for platform {platform}: {str(e)}")
            return []

    @staticmethod
    def get_localities_for_selection(
        year: int,
        month: int,
        platform: str,
        market: str
    ) -> List[Dict[str, str]]:
        """
        Get available localities for selected platform and market (optional filter).

        Args:
            year: Selected year
            month: Selected month
            platform: Selected platform
            market: Selected market

        Returns:
            List of locality options (includes 'All' option since optional)

        Example:
            >>> service = ForecastFilterService()
            >>> localities = service.get_localities_for_selection(
            ...     2025, 7, 'amisys', 'medicaid'
            ... )
        """
        logger.info(
            f"Fetching localities for platform: {platform}, market: {market}, "
            f"year: {year}, month: {month}"
        )

        try:
            localities = get_forecast_localities(year, month, platform, market)

            logger.debug(f"Retrieved {len(localities)} localities")

            return localities

        except Exception as e:
            logger.error(
                f"Failed to get localities for platform {platform}, "
                f"market {market}: {str(e)}"
            )
            return [{'value': '', 'display': '-- All Localities --'}]

    @staticmethod
    def get_worktypes_for_selection(
        year: int,
        month: int,
        platform: str,
        market: str,
        locality: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Get available worktypes for selected filters (formerly process).

        Args:
            year: Selected year
            month: Selected month
            platform: Selected platform
            market: Selected market
            locality: Optional selected locality

        Returns:
            List of worktype options

        Example:
            >>> service = ForecastFilterService()
            >>> worktypes = service.get_worktypes_for_selection(
            ...     2025, 7, 'amisys', 'medicaid', 'domestic'
            ... )
        """
        logger.info(
            f"Fetching worktypes for platform: {platform}, market: {market}, "
            f"locality: {locality or 'all'}, year: {year}, month: {month}"
        )

        try:
            worktypes = get_forecast_worktypes(
                year, month, platform, market, locality
            )

            logger.debug(f"Retrieved {len(worktypes)} worktypes")

            return worktypes

        except Exception as e:
            logger.error(
                f"Failed to get worktypes for platform {platform}, "
                f"market {market}, locality {locality}: {str(e)}"
            )
            return []


# Convenience functions for direct use
def get_initial_filter_options() -> Dict[str, List[Dict[str, str]]]:
    """Get initial filter options (years)"""
    return ForecastFilterService.get_initial_filter_options()


def get_months_for_year(year: int) -> List[Dict[str, str]]:
    """Get months for selected year"""
    return ForecastFilterService.get_months_for_year(year)


def get_platforms_for_selection(year: int, month: int) -> List[Dict[str, str]]:
    """Get platforms for selected year/month"""
    return ForecastFilterService.get_platforms_for_selection(year, month)


def get_markets_for_platform(
    year: int,
    month: int,
    platform: str
) -> List[Dict[str, str]]:
    """Get markets for selected platform"""
    return ForecastFilterService.get_markets_for_platform(year, month, platform)


def get_localities_for_selection(
    year: int,
    month: int,
    platform: str,
    market: str
) -> List[Dict[str, str]]:
    """Get localities for selected platform/market"""
    return ForecastFilterService.get_localities_for_selection(
        year, month, platform, market
    )


def get_worktypes_for_selection(
    year: int,
    month: int,
    platform: str,
    market: str,
    locality: Optional[str] = None
) -> List[Dict[str, str]]:
    """Get worktypes for selected filters"""
    return ForecastFilterService.get_worktypes_for_selection(
        year, month, platform, market, locality
    )