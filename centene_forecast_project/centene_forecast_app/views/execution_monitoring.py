"""
Execution Monitoring Views Module

Django views for execution monitoring page and AJAX API endpoints.
Handles page rendering, data fetching, KPI calculations, and file downloads.
"""

import logging
from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

# Import validators
from centene_forecast_app.validators.execution_validators import (
    validate_execution_filters,
    validate_kpi_filters,
    validate_execution_id,
    validate_report_type,
    ValidationError
)

# Import services
from centene_forecast_app.services.execution_service import (
    get_executions_list,
    get_execution_details,
    get_execution_kpis,
    download_execution_report
)

# Import serializers
from centene_forecast_app.serializers.execution_serializers import (
    serialize_executions_list_response,
    serialize_execution_details_response,
    serialize_kpi_response,
    serialize_error_response,
    serialize_download_error_response
)

# Import config
from core.config import ExecutionMonitoringConfig

logger = logging.getLogger('django')


# ============================================================================
# Page View
# ============================================================================

@require_http_methods(["GET"])
def execution_monitoring_page(request):
    """
    Render the execution monitoring page with initial configuration.

    This view serves the main HTML template and passes configuration
    to the frontend via context variables.

    Args:
        request: Django HttpRequest object

    Returns:
        Rendered HTML template

    Template:
        centene_forecast_app/execution_monitoring.html

    Context Variables:
        - config: ExecutionMonitoringConfig dictionary
        - page_title: Page title
        - valid_months: List of valid month names
        - valid_years: List of valid years (2020-2100)
        - valid_statuses: List of valid status values
    """
    try:
        logger.info("[Execution Monitoring Page] Rendering page")

        # Get configuration
        config = ExecutionMonitoringConfig.get_config_dict()

        # Generate filter options
        valid_months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        valid_years = list(range(2020, 2101))  # 2020-2100

        valid_statuses = [
            {"value": "PENDING", "display": "Pending"},
            {"value": "IN_PROGRESS", "display": "In Progress"},
            {"value": "SUCCESS", "display": "Success"},
            {"value": "FAILED", "display": "Failed"},
            {"value": "PARTIAL_SUCCESS", "display": "Partial Success"}
        ]

        # Context for template
        context = {
            'config': config,
            'page_title': 'Execution Monitoring',
            'valid_months': valid_months,
            'valid_years': valid_years,
            'valid_statuses': valid_statuses,
        }

        logger.info("[Execution Monitoring Page] Page rendered successfully")

        return render(
            request,
            'centene_forecast_app/execution_monitoring.html',
            context
        )

    except Exception as e:
        logger.error(
            f"[Execution Monitoring Page Error] Failed to render page: {e}",
            exc_info=True
        )
        return render(
            request,
            'centene_forecast_app/manager_view_error.html',
            {'error_message': 'Failed to load execution monitoring page'},
            status=500
        )


# ============================================================================
# API Endpoints
# ============================================================================

@require_http_methods(["GET"])
@csrf_exempt  # Safe for read-only GET requests
def execution_list_api(request):
    """
    API endpoint: Get list of executions with filters and pagination.

    Query Parameters:
        - month (str, optional): Filter by month name (e.g., "January")
        - year (int, optional): Filter by year (e.g., 2025)
        - status (str[], optional): Filter by status (can pass multiple)
        - uploaded_by (str, optional): Filter by username
        - limit (int, optional): Records per page (default: 50, max: 100)
        - offset (int, optional): Pagination offset (default: 0)

    Returns:
        JsonResponse with execution list and pagination info

    Status Codes:
        - 200: Success
        - 400: Validation error
        - 500: Server error

    Example:
        GET /api/execution-monitoring/list/?month=January&year=2025&limit=50&offset=0

    Response:
        {
            'success': True,
            'data': [...],
            'pagination': {
                'total': 150,
                'limit': 50,
                'offset': 0,
                'count': 50,
                'has_more': True
            },
            'timestamp': '2025-01-15T14:30:00'
        }
    """
    try:
        logger.info("[Execution List API] Request received")

        # Validate request parameters
        try:
            filters = validate_execution_filters(request.GET)
        except ValidationError as e:
            logger.warning(f"[Execution List API] Validation error: {e}")
            error_response = serialize_error_response(str(e), 400, 'ValidationError')
            return JsonResponse(error_response, status=400)

        # Get data from service
        try:
            data = get_executions_list(filters)
        except Exception as e:
            logger.error(f"[Execution List API] Service error: {e}", exc_info=True)
            error_response = serialize_error_response(
                "Failed to fetch executions",
                500,
                'ServiceError'
            )
            return JsonResponse(error_response, status=500)

        # Serialize response
        response = serialize_executions_list_response(data)

        logger.info(
            f"[Execution List API] Successfully returned "
            f"{len(response.get('data', []))} executions"
        )

        return JsonResponse(response, status=200)

    except Exception as e:
        logger.error(
            f"[Execution List API] Unexpected error: {e}",
            exc_info=True
        )
        error_response = serialize_error_response(
            "An unexpected error occurred",
            500,
            'UnexpectedError'
        )
        return JsonResponse(error_response, status=500)


@require_http_methods(["GET"])
@csrf_exempt
def execution_details_api(request, execution_id):
    """
    API endpoint: Get detailed information about a specific execution.

    Path Parameters:
        - execution_id (str): UUID of the execution

    Returns:
        JsonResponse with detailed execution information

    Status Codes:
        - 200: Success
        - 400: Validation error (invalid execution ID format)
        - 404: Execution not found
        - 500: Server error

    Example:
        GET /api/execution-monitoring/details/550e8400-e29b-41d4-a716-446655440000/

    Response:
        {
            'success': True,
            'data': {
                'execution_id': '550e8400-...',
                'month': 'January',
                'year': 2025,
                'status': 'SUCCESS',
                'start_time': '2025-01-15T10:30:00',
                'end_time': '2025-01-15T10:35:00',
                'duration_seconds': 300.5,
                'config_snapshot': {...},
                ...
            },
            'timestamp': '2025-01-15T14:30:00'
        }
    """
    try:
        logger.info(f"[Execution Details API] Request for ID: {execution_id}")

        # Validate execution ID
        try:
            validated_id = validate_execution_id(execution_id)
        except ValidationError as e:
            logger.warning(f"[Execution Details API] Validation error: {e}")
            error_response = serialize_error_response(str(e), 400, 'ValidationError')
            return JsonResponse(error_response, status=400)

        # Get data from service
        try:
            data = get_execution_details(validated_id)
        except Exception as e:
            error_message = str(e)

            # Check if it's a 404 (execution not found)
            if '404' in error_message or 'not found' in error_message.lower():
                logger.warning(f"[Execution Details API] Execution not found: {validated_id}")
                error_response = serialize_error_response(
                    f"Execution with ID {validated_id} not found",
                    404,
                    'NotFoundError'
                )
                return JsonResponse(error_response, status=404)

            # Other service errors
            logger.error(f"[Execution Details API] Service error: {e}", exc_info=True)
            error_response = serialize_error_response(
                "Failed to fetch execution details",
                500,
                'ServiceError'
            )
            return JsonResponse(error_response, status=500)

        # Serialize response
        response = serialize_execution_details_response(data)

        logger.info(f"[Execution Details API] Successfully returned details for {validated_id}")

        return JsonResponse(response, status=200)

    except Exception as e:
        logger.error(
            f"[Execution Details API] Unexpected error: {e}",
            exc_info=True
        )
        error_response = serialize_error_response(
            "An unexpected error occurred",
            500,
            'UnexpectedError'
        )
        return JsonResponse(error_response, status=500)


@require_http_methods(["GET"])
@csrf_exempt
def execution_kpis_api(request):
    """
    API endpoint: Get KPI metrics for executions with optional filters.

    Query Parameters:
        - month (str, optional): Filter by month name
        - year (int, optional): Filter by year
        - status (str[], optional): Filter by status (can pass multiple)
        - uploaded_by (str, optional): Filter by username

    Returns:
        JsonResponse with KPI metrics

    Status Codes:
        - 200: Success
        - 400: Validation error
        - 500: Server error

    Example:
        GET /api/execution-monitoring/kpis/?month=January&year=2025

    Response:
        {
            'success': True,
            'data': {
                'total_executions': 150,
                'success_rate': 0.85,
                'average_duration_seconds': 320.5,
                'failed_count': 12,
                ...
            },
            'timestamp': '2025-01-15T14:30:00'
        }
    """
    try:
        logger.info("[Execution KPIs API] Request received")

        # Validate request parameters
        try:
            filters = validate_kpi_filters(request.GET)
        except ValidationError as e:
            logger.warning(f"[Execution KPIs API] Validation error: {e}")
            error_response = serialize_error_response(str(e), 400, 'ValidationError')
            return JsonResponse(error_response, status=400)

        # Get data from service
        try:
            data = get_execution_kpis(filters)
        except Exception as e:
            logger.error(f"[Execution KPIs API] Service error: {e}", exc_info=True)
            error_response = serialize_error_response(
                "Failed to fetch KPIs",
                500,
                'ServiceError'
            )
            return JsonResponse(error_response, status=500)

        # Serialize response
        response = serialize_kpi_response(data)

        logger.info("[Execution KPIs API] Successfully returned KPIs")

        return JsonResponse(response, status=200)

    except Exception as e:
        logger.error(
            f"[Execution KPIs API] Unexpected error: {e}",
            exc_info=True
        )
        error_response = serialize_error_response(
            "An unexpected error occurred",
            500,
            'UnexpectedError'
        )
        return JsonResponse(error_response, status=500)


@require_http_methods(["GET"])
@csrf_exempt
def download_execution_report_api(request, execution_id, report_type):
    """
    API endpoint: Download Excel report for a specific execution.

    This endpoint streams the Excel file directly from FastAPI to the browser.

    Path Parameters:
        - execution_id (str): UUID of the execution
        - report_type (str): One of 'bucket_summary', 'bucket_after_allocation', 'roster_allotment'

    Returns:
        StreamingHttpResponse with Excel file

    Status Codes:
        - 200: Success (file download)
        - 400: Validation error
        - 404: Report not available
        - 500: Server error

    Example:
        GET /api/execution-monitoring/download/550e8400-.../bucket_summary/

    Response Headers:
        Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
        Content-Disposition: attachment; filename="bucket_summary_550e8400.xlsx"
    """
    try:
        logger.info(
            f"[Download Report API] Request: {report_type} for {execution_id}"
        )

        # Validate execution ID
        try:
            validated_id = validate_execution_id(execution_id)
        except ValidationError as e:
            logger.warning(f"[Download Report API] Invalid execution ID: {e}")
            error_response = serialize_error_response(str(e), 400, 'ValidationError')
            return JsonResponse(error_response, status=400)

        # Validate report type
        try:
            validated_type = validate_report_type(report_type)
        except ValidationError as e:
            logger.warning(f"[Download Report API] Invalid report type: {e}")
            error_response = serialize_error_response(str(e), 400, 'ValidationError')
            return JsonResponse(error_response, status=400)

        # Get streaming response from service
        try:
            streaming_response = download_execution_report(validated_id, validated_type)
        except ValueError as e:
            # Invalid report type (shouldn't happen after validation, but be safe)
            logger.error(f"[Download Report API] Value error: {e}")
            error_response = serialize_error_response(str(e), 400, 'ValidationError')
            return JsonResponse(error_response, status=400)
        except Exception as e:
            error_message = str(e)

            # Check if it's a 404 (report not available)
            if '404' in error_message or 'not found' in error_message.lower():
                logger.warning(
                    f"[Download Report API] Report not found: "
                    f"{validated_type} for {validated_id}"
                )
                error_response = serialize_download_error_response(
                    "Report not available for this execution",
                    validated_id,
                    validated_type
                )
                return JsonResponse(error_response, status=404)

            # Other service errors
            logger.error(f"[Download Report API] Service error: {e}", exc_info=True)
            error_response = serialize_download_error_response(
                "Failed to download report",
                validated_id,
                validated_type
            )
            return JsonResponse(error_response, status=500)

        # Create streaming HTTP response
        # Use iterator to stream chunks from the response
        def file_iterator():
            try:
                for chunk in streaming_response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            except Exception as e:
                logger.error(f"[Download Report API] Stream error: {e}", exc_info=True)
                raise

        # Generate filename
        filename = f"{validated_type}_{validated_id[:8]}.xlsx"

        # Create response with proper headers
        response = StreamingHttpResponse(
            file_iterator(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        logger.info(
            f"[Download Report API] Successfully initiated download: "
            f"{validated_type} for {validated_id}"
        )

        return response

    except Exception as e:
        logger.error(
            f"[Download Report API] Unexpected error: {e}",
            exc_info=True
        )
        error_response = serialize_download_error_response(
            "An unexpected error occurred during download",
            execution_id,
            report_type
        )
        return JsonResponse(error_response, status=500)


# ============================================================================
# Health Check (Optional)
# ============================================================================

@require_http_methods(["GET"])
def execution_monitoring_health(request):
    """
    Health check endpoint for execution monitoring.

    Returns:
        JsonResponse with health status

    Example:
        GET /api/execution-monitoring/health/

    Response:
        {
            'success': True,
            'status': 'healthy',
            'service': 'execution_monitoring',
            'timestamp': '2025-01-15T14:30:00'
        }
    """
    from datetime import datetime

    return JsonResponse({
        'success': True,
        'status': 'healthy',
        'service': 'execution_monitoring',
        'timestamp': datetime.now().isoformat()
    }, status=200)