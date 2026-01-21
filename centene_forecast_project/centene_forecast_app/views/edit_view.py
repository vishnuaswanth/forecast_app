# edit_view.py
"""
Django views for Edit View feature.

Follows the view pattern from manager_view.py.
- 1 page render view
- 5 API endpoints
- Comprehensive error handling
- Logging at all key points
"""

import json
import logging
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from centene_forecast_app.services.edit_service import (
    get_allocation_reports,
    calculate_bench_allocation_preview,
    submit_bench_allocation_update,
    get_history_log
)
from centene_forecast_app.validators.edit_validators import (
    ValidationError,
    validate_bench_allocation_preview_request,
    validate_bench_allocation_update_request,
    validate_history_log_request
)
from centene_forecast_app.serializers.edit_serializers import (
    serialize_allocation_reports_response,
    serialize_preview_response,
    serialize_update_response,
    serialize_history_log_response,
    serialize_error_response
)
from core.config import EditViewConfig
from centene_forecast_app.repository import get_api_client

logger = logging.getLogger('django')


# ============================================================
# PAGE VIEW
# ============================================================

@require_http_methods(["GET"])
def edit_view_page(request):
    """
    Edit View page - Bench Allocation & History Log.

    Renders template with:
    - Configuration for JavaScript
    - Two tabs: Bench Allocation, History Log

    Returns:
        Rendered HTML template

    Example:
        Access at: /edit-view/
    """
    try:
        logger.info("[Edit View Page] Rendering edit view page")

        # Get config for template/JavaScript
        config = EditViewConfig.get_config_dict()

        context = {
            'config': config,
            'page_title': 'Edit View - Allocation Management',
        }

        return render(request, 'centene_forecast_app/edit_view.html', context)

    except Exception as e:
        logger.error(f"[Edit View Page] Error rendering page: {e}", exc_info=True)
        return render(request, 'error.html', {
            'error_message': 'Failed to load edit view page'
        }, status=500)


# ============================================================
# API ENDPOINTS
# ============================================================

@require_http_methods(["GET"])
@csrf_exempt
def allocation_reports_api(request):
    """
    API: Get allocation reports for dropdown.

    Method: GET
    Auth: None (read-only)

    Returns:
        JSON with report options:
        {
            'success': True,
            'data': [{'value': '2025-04', 'display': 'April 2025'}, ...],
            'total': 15,
            'timestamp': '2024-12-06T...'
        }

    Example:
        GET /api/edit-view/allocation-reports/
    """
    logger.info("[Edit View API] Fetching allocation reports")

    try:
        # Get data from service
        data = get_allocation_reports()

        # Serialize response
        response = serialize_allocation_reports_response(data)

        logger.info(f"[Edit View API] Reports fetched - {response['total']} items")
        return JsonResponse(response, status=200)

    except Exception as e:
        logger.error(f"[Edit View API] Failed to fetch reports: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to fetch allocation reports", 500),
            status=500
        )


@require_http_methods(["POST"])
@csrf_exempt
def bench_allocation_preview_api(request):
    """
    API: Calculate bench allocation preview.

    Method: POST
    Auth: None
    Content-Type: application/json

    Request JSON:
        {
            'month': 'April',
            'year': 2025
        }

    Returns:
        JSON with modified records:
        {
            'success': True,
            'modified_records': [...],
            'total_modified': 15,
            'message': None or error message,
            'timestamp': '2024-12-06T...'
        }

    Example:
        POST /api/edit-view/bench-allocation/preview/
        Body: {"month": "April", "year": 2025}
    """
    try:
        # Parse request body
        body = json.loads(request.body)
        month = body.get('month', '').strip()
        year = body.get('year')

        logger.info(f"[Edit View API] Preview request - month: {month}, year: {year}")

        # Validate
        validated = validate_bench_allocation_preview_request(month, year)

        # Calculate preview
        data = calculate_bench_allocation_preview(
            validated['month'],
            validated['year']
        )

        # Serialize response
        response = serialize_preview_response(data)

        logger.info(f"[Edit View API] Preview success - {response['total_modified']} records")
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"[Edit View API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except json.JSONDecodeError:
        logger.warning("[Edit View API] Invalid JSON in request body")
        return JsonResponse(serialize_error_response("Invalid JSON", 400), status=400)

    except Exception as e:
        logger.error(f"[Edit View API] Preview failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to calculate preview", 500),
            status=500
        )


@require_http_methods(["POST"])
@csrf_exempt
def bench_allocation_update_api(request):
    """
    API: Accept and save bench allocation changes.

    Method: POST
    Auth: None
    Content-Type: application/json

    Request JSON:
        {
            'month': 'April',
            'year': 2025,
            'modified_records': [...],
            'user_notes': 'Optional description'
        }

    Returns:
        JSON with update result:
        {
            'success': True,
            'message': 'Allocation updated successfully',
            'records_updated': 15,
            'timestamp': '2024-12-06T...'
        }

    Example:
        POST /api/edit-view/bench-allocation/update/
        Body: {"month": "April", "year": 2025, "modified_records": [...], "user_notes": "..."}
    """
    try:
        # Parse request body
        body = json.loads(request.body)
        month = body.get('month', '').strip()
        year = body.get('year')
        modified_records = body.get('modified_records', [])
        user_notes = body.get('user_notes', '').strip()

        logger.info(
            f"[Edit View API] Update request - {month} {year} "
            f"({len(modified_records)} records)"
        )

        # Validate
        validated = validate_bench_allocation_update_request(
            month, year, modified_records, user_notes
        )

        # Submit update
        data = submit_bench_allocation_update(
            validated['month'],
            validated['year'],
            validated['modified_records'],
            validated['user_notes']
        )

        # Serialize response
        response = serialize_update_response(data)

        logger.info(f"[Edit View API] Update success - {response['records_updated']} records")
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"[Edit View API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except json.JSONDecodeError:
        logger.warning("[Edit View API] Invalid JSON in request body")
        return JsonResponse(serialize_error_response("Invalid JSON", 400), status=400)

    except Exception as e:
        logger.error(f"[Edit View API] Update failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to update allocation", 500),
            status=500
        )


@require_http_methods(["GET"])
@csrf_exempt
def history_log_api(request):
    """
    API: Get history log entries with pagination.

    Method: GET
    Auth: None (read-only)

    Query Parameters:
        - month: Optional month filter (e.g., 'April')
        - year: Optional year filter (e.g., 2025)
        - page: Page number (default: 1)
        - limit: Records per page (default: from config)

    Returns:
        JSON with history entries:
        {
            'success': True,
            'data': [...],
            'pagination': {
                'total': 127,
                'page': 1,
                'limit': 25,
                'has_more': True
            },
            'timestamp': '2024-12-06T...'
        }

    Example:
        GET /api/edit-view/history-log/?month=April&year=2025&page=1&limit=25
    """
    try:
        # Extract query parameters
        month = request.GET.get('month', '').strip() or None
        year_str = request.GET.get('year', '').strip()
        year = int(year_str) if year_str else None
        page_str = request.GET.get('page', '1').strip()
        page = int(page_str) if page_str else 1
        limit_str = request.GET.get('limit', str(EditViewConfig.HISTORY_PAGE_SIZE)).strip()
        limit = int(limit_str) if limit_str else EditViewConfig.HISTORY_PAGE_SIZE

        logger.info(
            f"[Edit View API] History request - month: {month}, year: {year}, "
            f"page: {page}, limit: {limit}"
        )

        # Validate
        validated = validate_history_log_request(month, year, page, limit)

        # Get history data
        data = get_history_log(
            validated['month'],
            validated['year'],
            validated['page'],
            validated['limit']
        )

        # Serialize response
        response = serialize_history_log_response(data)

        total = response['pagination'].get('total', 0)
        logger.info(
            f"[Edit View API] History fetched - {len(response['data'])} of {total} entries"
        )
        return JsonResponse(response, status=200)

    except ValueError as e:
        logger.warning(f"[Edit View API] Invalid parameter: {e}")
        return JsonResponse(
            serialize_error_response(f"Invalid parameter: {e}", 400),
            status=400
        )

    except ValidationError as e:
        logger.warning(f"[Edit View API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except Exception as e:
        logger.error(f"[Edit View API] History fetch failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to fetch history log", 500),
            status=500
        )


@require_http_methods(["GET"])
def download_history_excel_api(request, history_log_id):
    """
    API: Download Excel file for specific history entry.

    Method: GET
    Auth: None (read-only)

    Path Parameter:
        history_log_id: UUID of history log entry

    Returns:
        Excel file (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
        Filename: bench_allocation_{history_log_id}.xlsx

    Example:
        GET /api/edit-view/history-log/550e8400-e29b-41d4-a716-446655440000/download/
    """
    try:
        logger.info(f"[Edit View API] Excel download request - ID: {history_log_id}")

        # Get API client
        client = get_api_client()

        # Download Excel bytes
        excel_bytes = client.download_history_excel(history_log_id)

        # Create HTTP response with Excel file
        response = HttpResponse(
            excel_bytes,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = (
            f'attachment; filename="bench_allocation_{history_log_id}.xlsx"'
        )

        logger.info(f"[Edit View API] Excel download successful - ID: {history_log_id}")
        return response

    except Exception as e:
        logger.error(f"[Edit View API] Excel download failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to download Excel file", 500),
            status=500
        )


# Example usage in urls.py:
# from edit_view import (
#     edit_view_page,
#     allocation_reports_api,
#     bench_allocation_preview_api,
#     bench_allocation_update_api,
#     history_log_api,
#     download_history_excel_api
# )
#
# urlpatterns = [
#     path("edit-view/", edit_view_page, name="edit_view_page"),
#     path("api/edit-view/allocation-reports/", allocation_reports_api, name="allocation_reports"),
#     path("api/edit-view/bench-allocation/preview/", bench_allocation_preview_api, name="bench_allocation_preview"),
#     path("api/edit-view/bench-allocation/update/", bench_allocation_update_api, name="bench_allocation_update"),
#     path("api/edit-view/history-log/", history_log_api, name="history_log"),
#     path("api/edit-view/history-log/<str:history_log_id>/download/", download_history_excel_api, name="download_history_excel"),
# ]