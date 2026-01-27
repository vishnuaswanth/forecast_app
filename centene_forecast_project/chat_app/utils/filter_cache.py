"""
Filter Options Cache Manager
Centralized caching for /api/llm/forecast/filter-options with TTL management.
"""

from typing import Optional, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class FilterOptionsCache:
    """
    Manages caching of filter options with 5-minute TTL.

    Cache key structure: "filter_options:{year}:{month}"

    This cache stores the available filter values (platforms, markets, localities,
    states, case_types, etc.) for each month/year combination to minimize API calls
    during filter validation.

    Example:
        >>> cache = FilterOptionsCache()
        >>> cache.set(3, 2025, {'platforms': ['Amisys', 'Facets'], ...})
        >>> options = cache.get(3, 2025)
        >>> print(options['platforms'])
        ['Amisys', 'Facets']
    """

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache with configurable TTL.

        Args:
            ttl_seconds: Time-to-live in seconds (default: 300 = 5 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, dict] = {}
        self.timestamps: Dict[str, datetime] = {}

        logger.info(f"[Filter Cache] Initialized with TTL={ttl_seconds}s")

    def _make_key(self, month: int, year: int) -> str:
        """
        Generate cache key for month/year combination.

        Args:
            month: Report month (1-12)
            year: Report year

        Returns:
            Cache key string in format "filter_options:{year}:{month}"

        Example:
            >>> cache._make_key(3, 2025)
            'filter_options:2025:3'
        """
        return f"filter_options:{year}:{month}"

    def get(self, month: int, year: int) -> Optional[dict]:
        """
        Retrieve cached filter options if not expired.

        Args:
            month: Report month (1-12)
            year: Report year

        Returns:
            Filter options dict or None if expired/missing

        Example:
            >>> cache = FilterOptionsCache()
            >>> cache.set(3, 2025, {'platforms': ['Amisys']})
            >>> options = cache.get(3, 2025)
            >>> print(options['platforms'])
            ['Amisys']
        """
        key = self._make_key(month, year)

        if key not in self.cache:
            logger.debug(f"[Filter Cache] MISS: {key} (not in cache)")
            return None

        # Check TTL
        cached_time = self.timestamps.get(key)
        if not cached_time:
            logger.debug(f"[Filter Cache] MISS: {key} (no timestamp)")
            return None

        age = (datetime.now() - cached_time).total_seconds()
        if age > self.ttl_seconds:
            logger.debug(f"[Filter Cache] EXPIRED: {key} (age: {age:.1f}s)")
            self.invalidate(month, year)
            return None

        logger.info(f"[Filter Cache] HIT: {key} (age: {age:.1f}s)")
        return self.cache[key]

    def set(self, month: int, year: int, filter_options: dict):
        """
        Cache filter options with current timestamp.

        Args:
            month: Report month (1-12)
            year: Report year
            filter_options: Dictionary of filter options from API

        Example:
            >>> cache = FilterOptionsCache()
            >>> cache.set(3, 2025, {
            ...     'platforms': ['Amisys', 'Facets'],
            ...     'markets': ['Medicaid', 'Medicare']
            ... })
        """
        key = self._make_key(month, year)
        self.cache[key] = filter_options
        self.timestamps[key] = datetime.now()
        logger.info(f"[Filter Cache] SET: {key}")

    def invalidate(self, month: int, year: int):
        """
        Invalidate cache for specific month/year.

        Args:
            month: Report month (1-12)
            year: Report year

        Example:
            >>> cache = FilterOptionsCache()
            >>> cache.set(3, 2025, {'platforms': ['Amisys']})
            >>> cache.invalidate(3, 2025)
            >>> cache.get(3, 2025)  # Returns None
        """
        key = self._make_key(month, year)
        if key in self.cache:
            del self.cache[key]
            del self.timestamps[key]
            logger.info(f"[Filter Cache] INVALIDATED: {key}")
        else:
            logger.debug(f"[Filter Cache] INVALIDATE: {key} (not in cache)")

    def clear_all(self):
        """
        Clear entire cache (use after data upload).

        This should be called after forecast data uploads to ensure
        filter options are refreshed from the API.

        Example:
            >>> cache = FilterOptionsCache()
            >>> # After user uploads new forecast file
            >>> cache.clear_all()
        """
        count = len(self.cache)
        self.cache.clear()
        self.timestamps.clear()
        logger.info(f"[Filter Cache] CLEARED ALL ({count} entries)")

    def get_stats(self) -> dict:
        """
        Get cache statistics for monitoring.

        Returns:
            Dictionary with cache statistics

        Example:
            >>> cache = FilterOptionsCache()
            >>> stats = cache.get_stats()
            >>> print(stats['entry_count'])
            5
        """
        return {
            'entry_count': len(self.cache),
            'ttl_seconds': self.ttl_seconds,
            'entries': list(self.cache.keys())
        }


# Singleton instance
_filter_cache = FilterOptionsCache()


def get_filter_cache() -> FilterOptionsCache:
    """
    Get singleton filter cache instance.

    Returns:
        Singleton FilterOptionsCache instance

    Example:
        >>> cache = get_filter_cache()
        >>> cache.set(3, 2025, {'platforms': ['Amisys']})
        >>> # Later in another module
        >>> cache = get_filter_cache()  # Same instance
        >>> options = cache.get(3, 2025)
    """
    return _filter_cache
