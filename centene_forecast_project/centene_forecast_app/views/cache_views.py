"""
Cache Management Views

Provides endpoints for cache debugging, inspection, and manual cache clearing.
Useful for development and troubleshooting cache issues.
"""

import logging
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from centene_forecast_app.app_utils.cache_utils import (
    get_cache_stats,
    inspect_cache_value,
    clear_forecast_cache,
    clear_roster_cache,
    clear_summary_cache,
    clear_cascade_caches,
    clear_all_caches
)
from core.config import ForecastCacheConfig

logger = logging.getLogger('django')


def _serialize_cache_error(message: str, status_code: int) -> dict:
    """
    Serialize error response for cache endpoints with consistent format.

    Args:
        message: Human-readable error message
        status_code: HTTP status code

    Returns:
        JSON-ready error response dictionary
    """
    return {
        'success': False,
        'error': message,
        'status_code': status_code,
        'timestamp': datetime.now().isoformat()
    }


# ============================================================================
# Cache Statistics & Inspection
# ============================================================================


@require_http_methods(["GET"])
def cache_stats_view(request):
    """
    Get cache statistics and configuration.

    GET /api/cache/stats/

    Returns:
        {
            "enabled": true,
            "backend": "default",
            "ttls": {
                "cascade": 300,
                "data": 900,
                "schema": 900,
                "summary": 900
            },
            "sample_cached_keys": ["cascade:years", "forecast:7:2025"],
            "sample_count": 2
        }
    """
    try:
        stats = get_cache_stats()
        logger.info("Cache stats retrieved successfully")
        return JsonResponse({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return JsonResponse(
            _serialize_cache_error(str(e), 500),
            status=500
        )



@require_http_methods(["GET"])
def inspect_cache_view(request):
    """
    Inspect a specific cache key.

    GET /api/cache/inspect/?key=forecast:7:2025

    Query Parameters:
        key (required): Cache key to inspect

    Returns:
        {
            "success": true,
            "key": "forecast:7:2025",
            "exists": true,
            "value_type": "list",
            "value_size": 1234
        }
    """
    cache_key = request.GET.get('key')

    if not cache_key:
        return JsonResponse(
            _serialize_cache_error('Missing required parameter: key', 400),
            status=400
        )

    try:
        value = inspect_cache_value(cache_key)

        if value is not None:
            return JsonResponse({
                'success': True,
                'key': cache_key,
                'exists': True,
                'value_type': type(value).__name__,
                'value_size': len(str(value)) if value else 0,
                # Don't return full value - could be huge
                'preview': str(value)[:200] if value else None
            })
        else:
            return JsonResponse({
                'success': True,
                'key': cache_key,
                'exists': False,
                'message': 'Cache key not found or expired'
            })

    except Exception as e:
        logger.error(f"Failed to inspect cache key '{cache_key}': {e}")
        return JsonResponse(
            _serialize_cache_error(str(e), 500),
            status=500
        )


# ============================================================================
# Cache Clearing Endpoints
# ============================================================================


@require_http_methods(["POST"])
def clear_forecast_cache_view(request):
    """
    Clear forecast cache for specific month and year.

    POST /api/cache/clear/forecast/
    Body: {"month": 7, "year": 2025}

    Returns:
        {"success": true, "message": "Cleared forecast cache for 7/2025"}
    """
    try:
        month = request.POST.get('month') or request.GET.get('month')
        year = request.POST.get('year') or request.GET.get('year')

        if not month or not year:
            return JsonResponse(
                _serialize_cache_error('Missing required parameters: month and year', 400),
                status=400
            )

        month = int(month)
        year = int(year)

        clear_forecast_cache(month, year)

        logger.info(f"Cleared forecast cache for {month}/{year} via API")
        return JsonResponse({
            'success': True,
            'message': f'Cleared forecast cache for {month}/{year}',
            'timestamp': datetime.now().isoformat()
        })

    except ValueError as e:
        return JsonResponse(
            _serialize_cache_error(f'Invalid month or year: {e}', 400),
            status=400
        )
    except Exception as e:
        logger.error(f"Failed to clear forecast cache: {e}")
        return JsonResponse(
            _serialize_cache_error(str(e), 500),
            status=500
        )



@require_http_methods(["POST"])
def clear_roster_cache_view(request):
    """
    Clear roster cache for specific month and year.

    POST /api/cache/clear/roster/
    Body: {"month": 7, "year": 2025, "roster_type": "roster"}  # roster_type optional

    Returns:
        {"success": true, "message": "Cleared roster cache for 7/2025"}
    """
    try:
        month = request.POST.get('month') or request.GET.get('month')
        year = request.POST.get('year') or request.GET.get('year')
        roster_type = request.POST.get('roster_type') or request.GET.get('roster_type')

        if not month or not year:
            return JsonResponse(
                _serialize_cache_error('Missing required parameters: month and year', 400),
                status=400
            )

        month = int(month)
        year = int(year)

        clear_roster_cache(month, year, roster_type)

        logger.info(f"Cleared roster cache for {month}/{year} (type: {roster_type}) via API")
        return JsonResponse({
            'success': True,
            'message': f'Cleared roster cache for {month}/{year}',
            'timestamp': datetime.now().isoformat()
        })

    except ValueError as e:
        return JsonResponse(
            _serialize_cache_error(f'Invalid month or year: {e}', 400),
            status=400
        )
    except Exception as e:
        logger.error(f"Failed to clear roster cache: {e}")
        return JsonResponse(
            _serialize_cache_error(str(e), 500),
            status=500
        )



@require_http_methods(["POST"])
def clear_summary_cache_view(request):
    """
    Clear summary cache for specific month and year.

    POST /api/cache/clear/summary/
    Body: {"month": 7, "year": 2025, "summary_type": "capacity"}  # summary_type optional

    Returns:
        {"success": true, "message": "Cleared summary cache for 7/2025"}
    """
    try:
        month = request.POST.get('month') or request.GET.get('month')
        year = request.POST.get('year') or request.GET.get('year')
        summary_type = request.POST.get('summary_type') or request.GET.get('summary_type')

        if not month or not year:
            return JsonResponse(
                _serialize_cache_error('Missing required parameters: month and year', 400),
                status=400
            )

        month = int(month)
        year = int(year)

        clear_summary_cache(month, year, summary_type)

        logger.info(f"Cleared summary cache for {month}/{year} (type: {summary_type}) via API")
        return JsonResponse({
            'success': True,
            'message': f'Cleared summary cache for {month}/{year}',
            'timestamp': datetime.now().isoformat()
        })

    except ValueError as e:
        return JsonResponse(
            _serialize_cache_error(f'Invalid month or year: {e}', 400),
            status=400
        )
    except Exception as e:
        logger.error(f"Failed to clear summary cache: {e}")
        return JsonResponse(
            _serialize_cache_error(str(e), 500),
            status=500
        )



@require_http_methods(["POST"])
def clear_cascade_caches_view(request):
    """
    Clear all cascade dropdown caches.

    POST /api/cache/clear/cascade/

    Returns:
        {"success": true, "message": "Cleared all cascade caches"}
    """
    try:
        clear_cascade_caches()

        logger.info("Cleared cascade caches via API")
        return JsonResponse({
            'success': True,
            'message': 'Cleared all cascade caches (years, months)',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Failed to clear cascade caches: {e}")
        return JsonResponse(
            _serialize_cache_error(str(e), 500),
            status=500
        )



@require_http_methods(["POST"])
def clear_all_caches_view(request):
    """
    Clear ALL caches (nuclear option).

    POST /api/cache/clear/all/

    Warning: Clears everything. Use with caution.

    Returns:
        {"success": true, "message": "Cleared all caches"}
    """
    try:
        # Require explicit confirmation for this dangerous operation
        confirm = request.POST.get('confirm') or request.GET.get('confirm')

        if confirm != 'yes':
            return JsonResponse(
                _serialize_cache_error('Confirmation required. Send confirm=yes to proceed.', 400),
                status=400
            )

        clear_all_caches()

        logger.warning("Cleared ALL caches via API (nuclear option)")
        return JsonResponse({
            'success': True,
            'message': 'Cleared all caches. Performance may be impacted temporarily.',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Failed to clear all caches: {e}")
        return JsonResponse(
            _serialize_cache_error(str(e), 500),
            status=500
        )


# ============================================================================
# Cache Configuration Endpoint
# ============================================================================


@require_http_methods(["GET"])
def cache_config_view(request):
    """
    Get current cache configuration.

    GET /api/cache/config/

    Returns:
        {
            "cascade_ttl": 300,
            "data_ttl": 900,
            "schema_ttl": 900,
            "summary_ttl": 900,
            "enable_caching": true,
            "cache_backend": "default"
        }
    """
    try:
        config = ForecastCacheConfig.get_config_dict()

        return JsonResponse({
            'success': True,
            'data': config
        })

    except Exception as e:
        logger.error(f"Failed to get cache config: {e}")
        return JsonResponse(
            _serialize_cache_error(str(e), 500),
            status=500
        )