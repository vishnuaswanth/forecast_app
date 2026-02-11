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

        # Check if service returned an error response
        if not data.get('success', True):
            error_msg = data.get('error') or data.get('message', 'Failed to calculate preview')
            recommendation = data.get('recommendation')
            status_code = data.get('status_code', 400)

            logger.warning(f"[Edit View API] Preview failed: {error_msg}")
            logger.debug(f"[Edit View API] Returning error response with status_code={status_code}")

            try:
                error_response = serialize_error_response(error_msg, status_code, recommendation)
                logger.debug(f"[Edit View API] Serialized error response: {error_response}")
                return JsonResponse(error_response, status=status_code)
            except Exception as serialize_error:
                logger.error(f"[Edit View API] Failed to serialize error response: {serialize_error}", exc_info=True)
                return JsonResponse({'success': False, 'error': str(error_msg)}, status=status_code)

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
        months = body.get('months', {})
        modified_records = body.get('modified_records', [])
        user_notes = body.get('user_notes', '').strip()

        logger.info(
            f"[Edit View API] Update request - {month} {year} "
            f"({len(modified_records)} records)"
        )

        # Validate
        validated = validate_bench_allocation_update_request(
            month, year, months, modified_records, user_notes
        )

        # Submit update
        data = submit_bench_allocation_update(
            validated['month'],
            validated['year'],
            validated['months'],
            validated['modified_records'],
            validated['user_notes']
        )

        # Check if service returned an error response
        if not data.get('success', True):
            error_msg = data.get('error') or data.get('message', 'Failed to update allocation')
            recommendation = data.get('recommendation')
            status_code = data.get('status_code', 400)

            logger.warning(f"[Edit View API] Update failed: {error_msg}")
            return JsonResponse(
                serialize_error_response(error_msg, status_code, recommendation),
                status=status_code
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

        # Extract change_types (can have multiple values)
        change_types = request.GET.getlist('change_types')  # Returns list of values

        logger.info(
            f"[Edit View API] History request - month: {month}, year: {year}, "
            f"page: {page}, limit: {limit}, change_types: {change_types}"
        )

        # Validate
        validated = validate_history_log_request(month, year, page, limit, change_types)

        # Get history data
        data = get_history_log(
            validated['month'],
            validated['year'],
            validated['page'],
            validated['limit'],
            validated['change_types']
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


@require_http_methods(["GET"])
@csrf_exempt
def available_change_types_api(request):
    """
    API: Get available change types with colors for history log.

    Method: GET
    Auth: None (read-only)

    Returns:
        JSON with change type options:
        {
            'success': True,
            'data': [
                {'value': 'Bench Allocation', 'display': 'Bench Allocation', 'color': '#0d6efd'},
                {'value': 'CPH Update', 'display': 'CPH Update', 'color': '#198754'},
                ...
            ],
            'total': 10
        }

    Example:
        GET /api/edit-view/available-change-types/
    """
    logger.info("[Edit View API] Fetching available change types")

    try:
        # Get API client
        client = get_api_client()

        # Get change types data
        data = client.get_available_change_types()

        logger.info(f"[Edit View API] Change types fetched - {data.get('total', 0)} items")
        return JsonResponse(data, status=200)

    except Exception as e:
        logger.error(f"[Edit View API] Failed to fetch change types: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to fetch available change types", 500),
            status=500
        )


# ============================================================
# TARGET CPH API ENDPOINTS
# ============================================================

@require_http_methods(["GET"])
@csrf_exempt
def target_cph_data_api(request):
    """
    API: Get CPH records for editing in Target CPH tab.

    Method: GET
    Auth: None (read-only)

    Query Parameters:
        - month: Month name (e.g., 'April')
        - year: Year (e.g., 2025)

    Returns:
        JSON with CPH records:
        {
            'success': True,
            'data': [
                {
                    'id': 'cph_1',
                    'lob': 'Amisys Medicaid DOMESTIC',
                    'case_type': 'Claims Processing',
                    'target_cph': 50.0,
                    'modified_target_cph': 50.0
                },
                ...
            ],
            'total': 12,
            'timestamp': '2024-12-06T...'
        }

    Example:
        GET /api/edit-view/target-cph/data/?month=April&year=2025
    """
    from centene_forecast_app.services.edit_service import get_target_cph_data
    from centene_forecast_app.serializers.edit_serializers import serialize_target_cph_data_response
    from centene_forecast_app.validators.edit_validators import ValidationError, validate_bench_allocation_preview_request

    logger.info("[CPH API] Fetching CPH data")

    try:
        # Extract query parameters
        month = request.GET.get('month', '').strip()
        year_str = request.GET.get('year', '').strip()

        if not month or not year_str:
            return JsonResponse(
                serialize_error_response("Month and year are required", 400),
                status=400
            )

        year = int(year_str)

        # Validate month and year
        validated = validate_bench_allocation_preview_request(month, year)

        # Get CPH data from service
        data = get_target_cph_data(validated['month'], validated['year'])

        # Serialize response
        response = serialize_target_cph_data_response(data)

        logger.info(f"[CPH API] CPH data fetched - {response['total']} records")
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"[CPH API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except ValueError as e:
        logger.warning(f"[CPH API] Invalid parameter: {e}")
        return JsonResponse(
            serialize_error_response(f"Invalid parameter: {e}", 400),
            status=400
        )

    except Exception as e:
        logger.error(f"[CPH API] Failed to fetch CPH data: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to fetch CPH data", 500),
            status=500
        )


@require_http_methods(["POST"])
@csrf_exempt
def target_cph_preview_api(request):
    """
    API: Calculate CPH change preview (forecast impact).

    Method: POST
    Auth: None
    Content-Type: application/json

    Request JSON:
        {
            'month': 'April',
            'year': 2025,
            'modified_records': [
                {
                    'id': 'cph_1',
                    'lob': 'Amisys Medicaid DOMESTIC',
                    'case_type': 'Claims Processing',
                    'target_cph': 50.0,
                    'modified_target_cph': 52.0
                },
                ...
            ]
        }

    Returns:
        JSON with forecast impact (same structure as bench allocation):
        {
            'success': True,
            'modified_records': [...],  # Forecast rows affected
            'total_modified': 15,
            'summary': {...},
            'message': 'Preview shows forecast impact of X CPH changes',
            'timestamp': '2024-12-06T...'
        }

    Example:
        POST /api/edit-view/target-cph/preview/
        Body: {"month": "April", "year": 2025, "modified_records": [...]}
    """
    from centene_forecast_app.services.edit_service import calculate_target_cph_preview
    from centene_forecast_app.serializers.edit_serializers import serialize_target_cph_preview_response
    from centene_forecast_app.validators.edit_validators import ValidationError, validate_target_cph_preview_request

    try:
        # Parse request body
        body = json.loads(request.body)
        month = body.get('month', '').strip()
        year = body.get('year')
        modified_records = body.get('modified_records', [])

        logger.info(
            f"[CPH API] Preview request - month: {month}, year: {year}, "
            f"records: {len(modified_records)}"
        )

        # Validate
        validated = validate_target_cph_preview_request(month, year, modified_records)

        # Calculate preview
        data = calculate_target_cph_preview(
            validated['month'],
            validated['year'],
            validated['modified_records']
        )

        # Check if service returned an error response
        if not data.get('success', True):
            error_msg = data.get('error') or data.get('message', 'Failed to calculate CPH preview')
            recommendation = data.get('recommendation')
            status_code = data.get('status_code', 400)

            logger.warning(f"[CPH API] Preview failed: {error_msg}")
            return JsonResponse(
                serialize_error_response(error_msg, status_code, recommendation),
                status=status_code
            )

        # Serialize response
        response = serialize_target_cph_preview_response(data)

        logger.info(
            f"[CPH API] Preview success - {response['total_modified']} forecast rows "
            f"affected by {len(validated['modified_records'])} CPH changes"
        )
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"[CPH API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except json.JSONDecodeError:
        logger.warning("[CPH API] Invalid JSON in request body")
        return JsonResponse(serialize_error_response("Invalid JSON", 400), status=400)

    except Exception as e:
        logger.error(f"[CPH API] Preview failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to calculate CPH preview", 500),
            status=500
        )


@require_http_methods(["POST"])
@csrf_exempt
def target_cph_update_api(request):
    """
    API: Accept and save CPH changes.

    Method: POST
    Auth: None
    Content-Type: application/json

    Request JSON:
        {
            'month': 'April',
            'year': 2025,
            'modified_records': [...],  # Modified CPH records
            'user_notes': 'Optional description'
        }

    Returns:
        JSON with update result:
        {
            'success': True,
            'message': 'CPH updated successfully',
            'records_updated': 5,
            'cph_changes_applied': 5,
            'forecast_rows_affected': 15,
            'timestamp': '2024-12-06T...'
        }

    Example:
        POST /api/edit-view/target-cph/update/
        Body: {"month": "April", "year": 2025, "modified_records": [...], "user_notes": "..."}
    """
    from centene_forecast_app.services.edit_service import submit_target_cph_update
    from centene_forecast_app.serializers.edit_serializers import serialize_target_cph_update_response
    from centene_forecast_app.validators.edit_validators import ValidationError, validate_target_cph_update_request

    try:
        # Parse request body
        body = json.loads(request.body)
        month = body.get('month', '').strip()
        year = body.get('year')
        months = body.get('months', {})
        modified_records = body.get('modified_records', [])
        user_notes = body.get('user_notes', '').strip()

        logger.info(
            f"[CPH API] Update request - {month} {year} "
            f"({len(modified_records)} CPH changes)"
        )

        # Validate
        validated = validate_target_cph_update_request(
            month, year, months, modified_records, user_notes
        )

        # Submit update
        data = submit_target_cph_update(
            validated['month'],
            validated['year'],
            validated['months'],
            validated['modified_records'],
            validated['user_notes']
        )

        # Check if service returned an error response
        if not data.get('success', True):
            error_msg = data.get('error') or data.get('message', 'Failed to update CPH')
            recommendation = data.get('recommendation')
            status_code = data.get('status_code', 400)

            logger.warning(f"[CPH API] Update failed: {error_msg}")
            return JsonResponse(
                serialize_error_response(error_msg, status_code, recommendation),
                status=status_code
            )

        # Serialize response
        response = serialize_target_cph_update_response(data)

        logger.info(
            f"[CPH API] Update success - {response['records_updated']} CPH records updated, "
            f"{response['forecast_rows_affected']} forecast rows affected"
        )
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"[CPH API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except json.JSONDecodeError:
        logger.warning("[CPH API] Invalid JSON in request body")
        return JsonResponse(serialize_error_response("Invalid JSON", 400), status=400)

    except Exception as e:
        logger.error(f"[CPH API] Update failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to update CPH", 500),
            status=500
        )


# ============================================================
# FORECAST REALLOCATION API ENDPOINTS
# ============================================================

@require_http_methods(["GET"])
@csrf_exempt
def forecast_reallocation_filters_api(request):
    """
    API: Get filter options (LOBs, States, Case Types) for reallocation.

    Method: GET
    Auth: None (read-only)

    Query Parameters:
        - month: Month name (e.g., 'April')
        - year: Year (e.g., 2025)

    Returns:
        JSON with filter options:
        {
            'success': True,
            'main_lobs': ['Medicaid', 'Medicare', ...],
            'states': ['MO', 'TX', ...],
            'case_types': ['Appeals', 'Claims', ...],
            'timestamp': '2024-12-06T...'
        }

    Example:
        GET /api/edit-view/forecast-reallocation/filters/?month=April&year=2025
    """
    from centene_forecast_app.services.edit_service import get_reallocation_filter_options
    from centene_forecast_app.serializers.edit_serializers import serialize_reallocation_filters_response
    from centene_forecast_app.validators.edit_validators import (
        ValidationError, validate_bench_allocation_preview_request
    )

    logger.info("[Reallocation API] Fetching filter options")

    try:
        # Extract query parameters
        month = request.GET.get('month', '').strip()
        year_str = request.GET.get('year', '').strip()

        if not month or not year_str:
            return JsonResponse(
                serialize_error_response("Month and year are required", 400),
                status=400
            )

        year = int(year_str)

        # Validate month and year
        validated = validate_bench_allocation_preview_request(month, year)

        # Get filter options from service
        data = get_reallocation_filter_options(validated['month'], validated['year'])

        # Serialize response
        response = serialize_reallocation_filters_response(data)

        logger.info(
            f"[Reallocation API] Filters fetched - "
            f"{len(response.get('main_lobs', []))} LOBs, "
            f"{len(response.get('states', []))} States"
        )
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"[Reallocation API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except ValueError as e:
        logger.warning(f"[Reallocation API] Invalid parameter: {e}")
        return JsonResponse(
            serialize_error_response(f"Invalid parameter: {e}", 400),
            status=400
        )

    except Exception as e:
        logger.error(f"[Reallocation API] Failed to fetch filters: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to fetch filter options", 500),
            status=500
        )


@require_http_methods(["GET"])
@csrf_exempt
def forecast_reallocation_data_api(request):
    """
    API: Get editable forecast records for reallocation.

    Method: GET
    Auth: None (read-only)

    Query Parameters:
        - month: Month name (e.g., 'April')
        - year: Year (e.g., 2025)
        - main_lobs[]: Optional list of Main LOBs to filter
        - case_types[]: Optional list of Case Types to filter
        - states[]: Optional list of States to filter

    Returns:
        JSON with forecast records:
        {
            'success': True,
            'months': {'month1': 'Jun-25', ..., 'month6': 'Nov-25'},
            'data': [{
                'case_id': 'uuid',
                'main_lob': 'Medicaid',
                'state': 'MO',
                'case_type': 'Appeals',
                'target_cph': 100,
                'months': {
                    'Jun-25': {'forecast': 12500, 'fte_req': 11, 'fte_avail': 8, 'capacity': 400},
                    ...
                }
            }],
            'total': 150,
            'timestamp': '2024-12-06T...'
        }

    Example:
        GET /api/edit-view/forecast-reallocation/data/?month=April&year=2025&main_lobs[]=Medicaid
    """
    from centene_forecast_app.services.edit_service import get_reallocation_data
    from centene_forecast_app.serializers.edit_serializers import serialize_reallocation_data_response
    from centene_forecast_app.validators.edit_validators import (
        ValidationError, validate_reallocation_data_request
    )

    logger.info("[Reallocation API] Fetching data")

    try:
        # Extract query parameters
        month = request.GET.get('month', '').strip()
        year_str = request.GET.get('year', '').strip()

        if not month or not year_str:
            return JsonResponse(
                serialize_error_response("Month and year are required", 400),
                status=400
            )

        year = int(year_str)

        # Extract optional filter lists
        main_lobs = request.GET.getlist('main_lobs[]') or None
        case_types = request.GET.getlist('case_types[]') or None
        states = request.GET.getlist('states[]') or None

        logger.info(
            f"[Reallocation API] Data request - month: {month}, year: {year}, "
            f"main_lobs: {main_lobs}, case_types: {case_types}, states: {states}"
        )

        # Validate
        validated = validate_reallocation_data_request(
            month, year, main_lobs, case_types, states
        )

        # Get data from service
        data = get_reallocation_data(
            validated['month'],
            validated['year'],
            validated['main_lobs'],
            validated['case_types'],
            validated['states']
        )

        # Check if service returned an error
        if not data.get('success', True):
            error_msg = data.get('error') or data.get('message', 'Failed to fetch data')
            recommendation = data.get('recommendation')
            status_code = data.get('status_code', 400)

            logger.warning(f"[Reallocation API] Data fetch failed: {error_msg}")
            return JsonResponse(
                serialize_error_response(error_msg, status_code, recommendation),
                status=status_code
            )

        # Serialize response
        response = serialize_reallocation_data_response(data)

        logger.info(f"[Reallocation API] Data fetched - {response['total']} records")
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"[Reallocation API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except ValueError as e:
        logger.warning(f"[Reallocation API] Invalid parameter: {e}")
        return JsonResponse(
            serialize_error_response(f"Invalid parameter: {e}", 400),
            status=400
        )

    except Exception as e:
        logger.error(f"[Reallocation API] Failed to fetch data: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to fetch reallocation data", 500),
            status=500
        )


@require_http_methods(["POST"])
@csrf_exempt
def forecast_reallocation_preview_api(request):
    """
    API: Calculate preview with user-edited values.

    Method: POST
    Auth: None
    Content-Type: application/json

    Request JSON:
        {
            'month': 'April',
            'year': 2025,
            'modified_records': [{
                'case_id': 'uuid',
                'main_lob': '...',
                'state': '...',
                'case_type': '...',
                'target_cph': 105,
                'target_cph_change': 5,
                'modified_fields': ['target_cph', 'Jun-25.fte_avail'],
                'months': {
                    'Jun-25': {
                        'forecast': 12500,
                        'fte_req': 12,
                        'fte_avail': 10,
                        'capacity': 500,
                        'fte_avail_change': 2,
                        ...
                    }
                }
            }]
        }

    Returns:
        JSON with preview data (same structure as bench allocation)

    Example:
        POST /api/edit-view/forecast-reallocation/preview/
    """
    from centene_forecast_app.services.edit_service import calculate_reallocation_preview
    from centene_forecast_app.serializers.edit_serializers import serialize_reallocation_preview_response
    from centene_forecast_app.validators.edit_validators import (
        ValidationError, validate_reallocation_preview_request
    )

    try:
        # Parse request body
        body = json.loads(request.body)
        month = body.get('month', '').strip()
        year = body.get('year')
        modified_records = body.get('modified_records', [])

        logger.info(
            f"[Reallocation API] Preview request - month: {month}, year: {year}, "
            f"records: {len(modified_records)}"
        )

        # Validate
        validated = validate_reallocation_preview_request(month, year, modified_records)

        # Calculate preview
        data = calculate_reallocation_preview(
            validated['month'],
            validated['year'],
            validated['modified_records']
        )

        # Check if service returned an error
        if not data.get('success', True):
            error_msg = data.get('error') or data.get('message', 'Failed to calculate preview')
            recommendation = data.get('recommendation')
            status_code = data.get('status_code', 400)

            logger.warning(f"[Reallocation API] Preview failed: {error_msg}")
            return JsonResponse(
                serialize_error_response(error_msg, status_code, recommendation),
                status=status_code
            )

        # Serialize response
        response = serialize_reallocation_preview_response(data)

        logger.info(f"[Reallocation API] Preview success - {response['total_modified']} records")
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"[Reallocation API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except json.JSONDecodeError:
        logger.warning("[Reallocation API] Invalid JSON in request body")
        return JsonResponse(serialize_error_response("Invalid JSON", 400), status=400)

    except Exception as e:
        logger.error(f"[Reallocation API] Preview failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to calculate reallocation preview", 500),
            status=500
        )


@require_http_methods(["POST"])
@csrf_exempt
def forecast_reallocation_update_api(request):
    """
    API: Submit and save reallocation changes.

    Method: POST
    Auth: None
    Content-Type: application/json

    Request JSON:
        {
            'month': 'April',
            'year': 2025,
            'months': {'month1': 'Jun-25', ..., 'month6': 'Nov-25'},
            'modified_records': [...],
            'user_notes': 'Optional description'
        }

    Returns:
        JSON with update result:
        {
            'success': True,
            'message': 'Forecast reallocation updated successfully',
            'records_updated': 15,
            'timestamp': '2024-12-06T...'
        }

    Example:
        POST /api/edit-view/forecast-reallocation/update/
    """
    from centene_forecast_app.services.edit_service import submit_reallocation_update
    from centene_forecast_app.serializers.edit_serializers import serialize_reallocation_update_response
    from centene_forecast_app.validators.edit_validators import (
        ValidationError, validate_reallocation_update_request
    )

    try:
        # Parse request body
        body = json.loads(request.body)
        month = body.get('month', '').strip()
        year = body.get('year')
        months = body.get('months', {})
        modified_records = body.get('modified_records', [])
        user_notes = body.get('user_notes', '').strip()

        logger.info(
            f"[Reallocation API] Update request - {month} {year} "
            f"({len(modified_records)} records)"
        )

        # Validate
        validated = validate_reallocation_update_request(
            month, year, months, modified_records, user_notes
        )

        # Submit update
        data = submit_reallocation_update(
            validated['month'],
            validated['year'],
            validated['months'],
            validated['modified_records'],
            validated['user_notes']
        )

        # Check if service returned an error
        if not data.get('success', True):
            error_msg = data.get('error') or data.get('message', 'Failed to update reallocation')
            recommendation = data.get('recommendation')
            status_code = data.get('status_code', 400)

            logger.warning(f"[Reallocation API] Update failed: {error_msg}")
            return JsonResponse(
                serialize_error_response(error_msg, status_code, recommendation),
                status=status_code
            )

        # Serialize response
        response = serialize_reallocation_update_response(data)

        logger.info(f"[Reallocation API] Update success - {response['records_updated']} records")
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"[Reallocation API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except json.JSONDecodeError:
        logger.warning("[Reallocation API] Invalid JSON in request body")
        return JsonResponse(serialize_error_response("Invalid JSON", 400), status=400)

    except Exception as e:
        logger.error(f"[Reallocation API] Update failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to update forecast reallocation", 500),
            status=500
        )


# Example usage in urls.py:
# from edit_view import (
#     edit_view_page,
#     allocation_reports_api,
#     bench_allocation_preview_api,
#     bench_allocation_update_api,
#     history_log_api,
#     download_history_excel_api,
#     forecast_reallocation_filters_api,
#     forecast_reallocation_data_api,
#     forecast_reallocation_preview_api,
#     forecast_reallocation_update_api
# )
#
# urlpatterns = [
#     path("edit-view/", edit_view_page, name="edit_view_page"),
#     path("api/edit-view/allocation-reports/", allocation_reports_api, name="allocation_reports"),
#     path("api/edit-view/bench-allocation/preview/", bench_allocation_preview_api, name="bench_allocation_preview"),
#     path("api/edit-view/bench-allocation/update/", bench_allocation_update_api, name="bench_allocation_update"),
#     path("api/edit-view/history-log/", history_log_api, name="history_log"),
#     path("api/edit-view/history-log/<str:history_log_id>/download/", download_history_excel_api, name="download_history_excel"),
#     path("api/edit-view/forecast-reallocation/filters/", forecast_reallocation_filters_api, name="forecast_reallocation_filters"),
#     path("api/edit-view/forecast-reallocation/data/", forecast_reallocation_data_api, name="forecast_reallocation_data"),
#     path("api/edit-view/forecast-reallocation/preview/", forecast_reallocation_preview_api, name="forecast_reallocation_preview"),
#     path("api/edit-view/forecast-reallocation/update/", forecast_reallocation_update_api, name="forecast_reallocation_update"),
# ]
