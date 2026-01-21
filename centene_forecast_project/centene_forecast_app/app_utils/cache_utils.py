"""
Cache Utilities for Forecast Data

Provides caching decorator and cache management functions for Django local memory cache.
Lightweight, fast, zero-dependency caching for development and single-worker deployments.
"""

import logging
import hashlib
import inspect
import os
import fnmatch
from functools import wraps
from typing import Any, Callable, Optional, List
from django.core.cache import cache
from django.conf import settings
from core.config import ForecastCacheConfig
from core.constants import SUMMARY_TYPES

logger = logging.getLogger('django')

# Key registry for locmem cache (to enable pattern matching)
_CACHE_KEY_REGISTRY = set()


# ============================================================================
# Cache Backend Detection & Pattern Matching Utilities
# ============================================================================

def _get_cache_backend_type() -> str:
    """
    Detect the cache backend type.

    Returns:
        'filebased', 'locmem', 'redis', or 'unknown'
    """
    try:
        backend = settings.CACHES.get('default', {}).get('BACKEND', '')

        if 'FileBasedCache' in backend:
            return 'filebased'
        elif 'LocMemCache' in backend:
            return 'locmem'
        elif 'redis' in backend.lower() or 'RedisCache' in backend:
            return 'redis'
        else:
            return 'unknown'
    except Exception as e:
        logger.debug(f"Could not detect cache backend: {e}")
        return 'unknown'


def _get_filebased_cache_location() -> Optional[str]:
    """
    Get the file path for file-based cache.

    Returns:
        Cache directory path or None if not file-based cache
    """
    try:
        if _get_cache_backend_type() == 'filebased':
            return settings.CACHES.get('default', {}).get('LOCATION')
    except Exception as e:
        logger.debug(f"Could not get cache location: {e}")
    return None

# TODO: FIX this: doesnot give output matching the pattern style.
def _match_pattern_filebased(pattern: str) -> List[str]:
    """
    Match cache files in file-based cache using filesystem.

    Args:
        pattern: Wildcard pattern (e.g., 'cascade:*', 'forecast:7:*')

    Returns:
        List of matching file paths (not keys, as file cache hashes keys)
    """
    cache_dir = _get_filebased_cache_location()
    if not cache_dir or not os.path.exists(cache_dir):
        logger.warning(f"Cache directory not found: {cache_dir}")
        return []

    matching_files = []

    try:
        # Remove special chars from pattern for filename matching
        pattern_parts = pattern.replace(':', '_').replace('*', '').split('_')

        for filename in os.listdir(cache_dir):
            filepath = os.path.join(cache_dir, filename)

            if not os.path.isfile(filepath):
                continue

            # Check if filename contains pattern elements
            # Django file cache hashes keys, so we match on hash content
            if any(part in filename for part in pattern_parts if part):
                matching_files.append(filepath)

    except Exception as e:
        logger.warning(f"Error matching file-based cache pattern '{pattern}': {e}")

    return matching_files

def _match_pattern_locmem(pattern: str) -> List[str]:
    """
    Match cache keys in local memory cache using registry.

    Args:
        pattern: Wildcard pattern (e.g., 'cascade:*', 'forecast:7:*')

    Returns:
        List of matching cache keys
    """
    matching_keys = []

    # Use fnmatch for Unix-style pattern matching
    for key in _CACHE_KEY_REGISTRY:
        if fnmatch.fnmatch(key, pattern):
            matching_keys.append(key)

    return matching_keys


def delete_pattern(pattern: str) -> int:
    """
    Delete cache keys matching a wildcard pattern.

    Works with:
    - File-based cache: Lists files and matches patterns
    - Local memory cache: Uses internal registry to match keys
    - Redis: Not implemented 

    Args:
        pattern: Wildcard pattern using * and ?
                 Examples: 'cascade:*', 'forecast:7:*', 'roster:*:2025'

    Returns:
        Number of keys deleted

    Usage:
        delete_pattern('cascade:*')         # Delete all cascade cache entries
        delete_pattern('forecast:7:*')      # Delete all forecast for month 7
        delete_pattern('*:2025')            # Delete all entries for year 2025
    """
    backend_type = _get_cache_backend_type()
    logger.debug(f"Deleting cache keys matching pattern '{pattern}' (backend: {backend_type})")

    if backend_type == 'filebased':
        # File-based cache: use helper to match files
        matching_files = _match_pattern_filebased(pattern)

        # Delete matched files
        deleted_count = 0
        for filepath in matching_files:
            try:
                os.remove(filepath)
                deleted_count += 1
                logger.debug(f"Deleted cache file: {filepath}")
            except Exception as e:
                logger.warning(f"Could not delete cache file {filepath}: {e}")

        logger.info(f"Deleted {deleted_count} file-based cache entries matching '{pattern}'")
        return deleted_count

    elif backend_type == 'locmem':
        # Local memory cache: use registry
        matching_keys = _match_pattern_locmem(pattern)

        deleted_count = 0
        for key in matching_keys:
            if cache.delete(key):
                deleted_count += 1
                _unregister_cache_key(key)
                logger.debug(f"Deleted cache key: {key}")

        logger.info(f"Deleted {deleted_count} locmem cache entries matching '{pattern}'")
        return deleted_count

    else:
        logger.warning(
            f"Pattern matching not implemented for backend '{backend_type}'. "
            f"Use specific key deletion instead."
        )
        return 0


def _register_cache_key(key: str):
    """
    Register a cache key in the registry (for locmem pattern matching only).

    Args:
        key: Cache key to register
    """
    # Only register if using local memory cache
    if _get_cache_backend_type() == 'locmem':
        _CACHE_KEY_REGISTRY.add(key)


def _unregister_cache_key(key: str):
    """
    Remove a cache key from the registry (for locmem only).

    Args:
        key: Cache key to unregister
    """
    # Only unregister if using local memory cache
    if _get_cache_backend_type() == 'locmem':
        _CACHE_KEY_REGISTRY.discard(key)


# ============================================================================
# DRY Helper Functions
# ============================================================================

def _clear_cache_keys(keys: List[str], description: str = "cache") -> int:
    """
    Helper function to clear multiple cache keys (DRY principle).

    Args:
        keys: List of cache keys to clear
        description: Description for logging (e.g., "forecast", "roster")

    Returns:
        Number of keys successfully cleared
    """
    cleared_count = 0
    for key in keys:
        if cache.delete(key):
            _unregister_cache_key(key)
            cleared_count += 1
            logger.debug(f"Cleared cache: {key}")

    if cleared_count > 0:
        logger.info(f"Cleared {cleared_count} {description} entries")

    return cleared_count



def _generate_cache_key(key_prefix: str, *args, **kwargs) -> str:
    """
    Generate a unique cache key from function arguments.

    Args:
        key_prefix: Prefix for the cache key (e.g., 'forecast', 'roster')
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key

    Returns:
        Cache key string 

    Example:
        _generate_cache_key('forecast', 7, 2025) → 'forecast:7:2025'
    """
    # Convert args to strings and filter out None values
    key_parts = [key_prefix]

    for arg in args:
        if arg is not None:
            # Replace spaces and special chars for cleaner keys
            arg_str = str(arg).replace(' ', '_').replace(':', '_')
            key_parts.append(arg_str)

    # Add kwargs in sorted order for consistency
    for k in sorted(kwargs.keys()):
        v = kwargs[k]
        if v is not None:
            v_str = str(v).replace(' ', '_').replace(':', '_')
            key_parts.append(f"{k}={v_str}")

    cache_key = ':'.join(key_parts)

    # If key is too long, hash it
    if len(cache_key) > 200:
        hash_suffix = hashlib.md5(cache_key.encode()).hexdigest()[:8]
        cache_key = f"{key_prefix}:hash:{hash_suffix}"

    return cache_key

def cache_with_ttl(ttl: int, key_prefix: str):
    """
    Decorator to cache function results with custom TTL.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key (e.g., 'cascade', 'forecast')

    Usage:
        # On instance methods:
        @cache_with_ttl(ttl=300, key_prefix='cascade:months')
        def get_months_for_year(self, year: int):
            # This result will be cached for 5 minutes
            return expensive_api_call(year)

        # On regular functions:
        @cache_with_ttl(ttl=300, key_prefix='utility:data')
        def process_data(data: dict):
            return expensive_processing(data)

    Cache key format: {key_prefix}:{arg1}:{arg2}:...

    Example keys:
        cascade:years
        cascade:months:2025
        roster:roster:7:2025
        forecast:7:2025

    Note: Automatically detects and skips 'self' for instance methods using inspect.
    """
    def decorator(func: Callable) -> Callable:
        # Inspect function signature at decoration time
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())

        # Detect if first parameter is 'self' or 'cls' (instance/class method)
        is_method = len(params) > 0 and params[0] in ('self', 'cls')

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Check if caching is enabled
            if not ForecastCacheConfig.ENABLE_CACHING:
                logger.debug(f"Cache disabled, calling {func.__name__} directly")
                return func(*args, **kwargs)

            # Skip 'self' or 'cls' argument for instance/class methods
            # Use signature inspection instead of hasattr check
            if is_method and args:
                cache_args = args[1:]  # Skip first argument (self/cls)
            else:
                cache_args = args

            # Generate cache key
            cache_key = _generate_cache_key(key_prefix, *cache_args, **kwargs)

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.info(f"Cache HIT: {cache_key}")  # TODO: change to debug
                return cached_value

            # Cache miss - call function
            logger.debug(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)

            # Store in cache
            if result is not None:
                cache.set(cache_key, result, ttl)
                _register_cache_key(cache_key)
                logger.debug(f"Cache SET: {cache_key} (TTL: {ttl}s)")

            return result

        return wrapper
    return decorator

# ============================================================================
# Cache Clearing Functions
# ============================================================================

def clear_forecast_cache(month: int, year: int):
    """
    Clear all forecast-related caches for a specific month and year.

    Args:
        month: Month number (1-12)
        year: Year (e.g., 2025)

    Clears:
        - Forecast data records
        - Forecast schema

    Usage:
        clear_forecast_cache(7, 2025)  # Clears July 2025 forecast data
    """
    keys_to_clear = [
        f"forecast:{month}:{year}",
        f"schema:forecast:{month}:{year}",
    ]

    _clear_cache_keys(keys_to_clear, f"forcast cache for {month}/{year}")
    

def clear_roster_cache(month: int, year: int, roster_type: str = None):
    """
    Clear all roster-related caches for a specific month and year.

    Args:
        month: Month number (1-12)
        year: Year (e.g., 2025)
        roster_type: Optional specific roster type (e.g., 'roster', 'prod_team_roster')

    Clears:
        - Roster data records
        - Roster schema

    Usage:
        clear_roster_cache(7, 2025)                    # Clear all roster types
        clear_roster_cache(7, 2025, 'roster')         # Clear specific type
    """
    if roster_type:
        keys_to_clear = [
            f"roster:{roster_type}:{month}:{year}",
            f"schema:roster:{roster_type}:{month}:{year}",
        ]
    else:
        # Clear both roster types
        keys_to_clear = [
            f"roster:roster:{month}:{year}",
            f"roster:prod_team_roster:{month}:{year}",
            f"schema:roster:roster:{month}:{year}",
            f"schema:roster:prod_team_roster:{month}:{year}",
        ]

    _clear_cache_keys(keys_to_clear, f"roster cache for {month}/{year}")
    

def clear_summary_cache(month: int, year: int, summary_type: str = None):
    """
    Clear HTML summary cache for a specific month and year.

    Args:
        month: Month number (1-12)
        year: Year (e.g., 2025)
        summary_type: Optional specific summary type (e.g., 'marketplace')

    Clears:
        - Summary HTML tables

    Usage:
        clear_summary_cache(7, 2025)                   # Clear all summary types
        clear_summary_cache(7, 2025, 'marketplace')      # Clear specific type
    """
    if summary_type:
        keys_to_clear = [f"summary:{summary_type}:{month}:{year}"]
    else:
        # Clear all known summary types
        summary_types = SUMMARY_TYPES
        keys_to_clear = [f"summary:{st}:{month}:{year}" for st in summary_types]

    _clear_cache_keys(keys_to_clear, f"summary cache for {month}/{year}")
    

def clear_cascade_caches():
    """
    Clear all cascade dropdown caches using pattern matching.

    Clears:
        - Years
        - Months (all years)
        - Platforms (all year/month combinations)
        - Markets, Localities, Worktypes

    Usage:
        clear_cascade_caches()  # Clear all dropdowns

    Note: Uses custom pattern matching for locmem and file-based cache.
    """
    logger.info("Clearing cascade dropdown caches using pattern matching")

    # Use pattern matching to clear all cascade entries
    cleared = delete_pattern('cascade:*')

    logger.info(f"Cleared {cleared} cascade cache entries using pattern 'cascade:*'")

# ============================================================================
# Debug Utilities
# ============================================================================

def get_cache_stats() -> dict:
    """
    Get cache statistics for debugging.

    Returns:
        Dictionary with cache information

    Usage:
        stats = get_cache_stats()
        print(f"Cache enabled: {stats['enabled']}")
        print(f"Keys: {stats['sample_keys']}")

    Note: Local memory cache doesn't provide hit rate or size stats.
    For detailed stats, use Redis in production.
    """
    # Try to get some sample keys (this is limited with locmem)
    sample_keys = []

    # Try common patterns
    test_patterns = [
        'cascade:years',
        'cascade:months:2025',
        'forecast:7:2025',
        'roster:roster:7:2025',
        'summary:capacity:7:2025',
    ]

    for key in test_patterns:
        if cache.get(key) is not None:
            sample_keys.append(key)

    stats = {
        'enabled': ForecastCacheConfig.ENABLE_CACHING,
        'backend': ForecastCacheConfig.CACHE_BACKEND,
        'ttls': {
            'cascade': ForecastCacheConfig.CASCADE_TTL,
            'data': ForecastCacheConfig.DATA_TTL,
            'schema': ForecastCacheConfig.SCHEMA_TTL,
            'summary': ForecastCacheConfig.SUMMARY_TTL,
        },
        'sample_cached_keys': sample_keys,
        'sample_count': len(sample_keys),
    }

    logger.debug(f"Cache stats: {stats}")
    return stats


def inspect_cache_value(key: str) -> Optional[Any]:
    """
    Inspect a specific cache value for debugging.

    Args:
        key: Cache key to inspect

    Returns:
        Cached value or None if not found

    Usage:
        value = inspect_cache_value('forecast:7:2025')
        print(f"Cached data: {value}")
    """
    value = cache.get(key)

    if value is not None:
        logger.info(f"Cache key '{key}' exists")
        logger.debug(f"Value type: {type(value)}, Size: {len(str(value))} chars")
    else:
        logger.info(f"Cache key '{key}' not found or expired")

    return value


# Convenience function for clearing all caches
def clear_all_caches():
    """
    Clear ALL caches (nuclear option).

    Clears:
    - All cached data
    - Registry for locmem 
    - index file for file-based cache

    Use with caution - clears all cached data.
    Useful after major data updates or for testing.

    Usage:
        clear_all_caches()  # Clear everything
    """
    logger.warning("Clearing ALL caches - this may impact performance temporarily")
    cache.clear()
    backend_type = _get_cache_backend_type()
    if backend_type == 'locmem':
        _CACHE_KEY_REGISTRY.clear()
        logger.debug("Cleared locmem cache key registry")
    logger.info("All caches cleared")