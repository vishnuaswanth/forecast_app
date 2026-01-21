"""
Manager View - Django Views

Handles HTTP requests for Manager View dashboard.
Follows Django best practices and matches existing app patterns.
"""

import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import uuid

from utils import *
from centene_forecast_app.app_utils import *


from centene_forecast_app.validators.manager_validators import (
    validate_manager_view_request,
    ValidationError
)
from centene_forecast_app.services.manager_service import (
    ManagerViewService,
    get_filter_options
)
from centene_forecast_app.serializers.manager_serializers import (
    serialize_data_response,
    serialize_kpi_response,
    serialize_error_response
)
from centene_forecast_app.repository import get_api_client
from core.config import ManagerViewConfig

logger = logging.getLogger(__name__)

@login_required
@permission_required(get_permission_name("view"), raise_exception=True)
@require_http_methods(["GET"])
def manager_view_page(request):
    """
    Render the Manager View dashboard page.
    
    This is the main view that loads the template with filter dropdowns.
    Data is populated via AJAX calls to the API endpoints.
    
    URL: /reports/manager-view/
    Template: apps/reports/templates/reports/manager_view.html
    
    Returns:
        Rendered HTML page with filter options in context
        
    Context Variables:
        - report_months: List of available report months for dropdown
        - categories: List of available categories for dropdown
        - config: ManagerViewConfig settings for JavaScript
        - page_title: Page title for template
        
    Example Usage:
        Navigate to: http://localhost:8000/reports/manager-view/
    """
    logger.info(f"Manager view page accessed by user: {request.user.username}")
    
    try:
        # Get filter options from service
        filters = get_filter_options()
        
        # Get config settings for template/JavaScript
        config = ManagerViewConfig.get_config_dict()
        
        # Build context for template
        # Note: user_name, timezone, utcoffset, etc. are already provided by context processor
        context = {
            'report_months': filters['report_months'],
            'categories': filters['categories'],
            'config': config,
            'page_title': 'Executive View - Capacity Planning',
        }
        
        logger.debug(
            f"Rendering manager view with {len(filters['report_months'])} report months, "
            f"{len(filters['categories'])} categories"
        )
        
        return render(request, 'centene_forecast_app/manager_view.html', context)
        
    except ValidationError as e: 
        logger.error(f"validation error: {e}")
        return render(
            request, 
            'centene_forecast_app/manager_view_error.html', 
            { 
                'error_type': 'validation', 
                'error_message': str(e), 
                'debug_mode': settings.DEBUG, 
                'request_id': str(uuid.uuid4()) 
                
            }, 
            status=400
        ) 
    
    except Exception as e: 
        logger.error(f"server error: {e}")

        return render(
            request, 
            'centene_forecast_app/manager_view_error.html', 
            { 
                'error_type': 'server', 
                'error_message': 'An error occurred', 
                'error_details': str(e), 
                'debug_mode': settings.DEBUG, 
                'request_id': str(uuid.uuid4()) 
            }, 
            status=500
        )

@login_required
@require_http_methods(["GET"])
@csrf_exempt  # Safe for read-only GET requests
def manager_view_data_api(request):
    """
    API endpoint for fetching table data.
    
    Returns hierarchical category data with 6 months of forecast information.
    Called via AJAX when user selects filters or page loads.
    
    URL: /reports/api/manager-view/data/
    Method: GET
    
    Query Parameters:
        - report_month (required): Report month in YYYY-MM format (e.g., '2025-02')
        - category (optional): Category filter (e.g., 'amisys-onshore' or empty for all)
        
    Returns:
        JSON response with table data
        
    Response Format (Success):
        {
            'success': True,
            'report_month': '2025-02',
            'report_month_display': 'February 2025',
            'category_name': 'Amisys Onshore',
            'months': ['2025-02', '2025-03', ...],
            'months_display': ['Feb 2025', 'Mar 2025', ...],
            'categories': [...],
            'total_categories': 3,
            'timestamp': '2025-10-16T15:30:00'
        }
        
    Response Format (Error):
        {
            'success': False,
            'error': 'Invalid report month format',
            'status_code': 400,
            'timestamp': '2025-10-16T15:30:00'
        }
        
    Example AJAX Call:
        $.ajax({
            url: '{% url "reports:manager_view_data" %}',
            method: 'GET',
            data: {
                report_month: '2025-02',
                category: 'amisys-onshore'
            },
            success: function(response) {
                if (response.success) {
                    populateTable(response.categories, response.months);
                }
            }
        });
    """
    # Get query parameters
    report_month = request.GET.get('report_month', '').strip()
    category = request.GET.get('category', '').strip()
    
    logger.info(
        f"Manager view data API called - report_month: {report_month}, "
        f"category: {category or 'all'} (user: {request.user.username})"
    )
    
    try:
        # Validate parameters
        validated = validate_manager_view_request(report_month, category)
        
        # Get data from API client
        client = get_api_client()
        data = client.get_manager_view_data(
            validated['report_month'],
            validated['category']
        )
        
        # Serialize for JSON response
        response = serialize_data_response(data)
        
        logger.info(
            f"Manager view data API success - {response['total_categories']} categories returned"
        )
        
        return JsonResponse(response, status=200)
        
    except ValidationError as e:
        logger.warning(f"Validation error in manager view data API: {str(e)}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)
        
    except ValueError as e:
        logger.warning(f"Value error in manager view data API: {str(e)}")
        return JsonResponse(serialize_error_response(str(e), 404), status=404)
        
    except Exception as e:
        logger.error(f"Unexpected error in manager view data API: {str(e)}", exc_info=True)
        return JsonResponse(
            serialize_error_response("An unexpected error occurred", 500),
            status=500
        )

@login_required
@require_http_methods(["GET"])
@csrf_exempt  # Safe for read-only GET requests
def manager_view_kpi_api(request):
    """
    API endpoint for fetching KPI summary card data.
    
    Returns aggregated metrics for the KPI month (configured via ManagerViewConfig.KPI_MONTH_INDEX).
    Called via AJAX when user selects filters.
    
    URL: /reports/api/manager-view/kpi/
    Method: GET
    
    Query Parameters:
        - report_month (required): Report month in YYYY-MM format (e.g., '2025-02')
        - category (optional): Category filter (e.g., 'amisys-onshore' or empty for all)
        
    Returns:
        JSON response with KPI data
        
    Response Format (Success):
        {
            'success': True,
            'kpi': {
                'client_forecast': 10750,
                'client_forecast_formatted': '10,750',
                'head_count': 108,
                'head_count_formatted': '108',
                'capacity': 10260,
                'capacity_formatted': '10,260',
                'capacity_gap': -490,
                'capacity_gap_formatted': '-490',
                'kpi_month': '2025-03',
                'kpi_month_display': 'March 2025',
                'is_shortage': True,
                'status_message': '⚠️ Shortage in March 2025',
                'status_class': 'text-danger',
                'gap_percentage': 4.56
            },
            'timestamp': '2025-10-16T15:30:00'
        }
        
    Response Format (Error):
        {
            'success': False,
            'error': 'Invalid report month format',
            'status_code': 400,
            'timestamp': '2025-10-16T15:30:00'
        }
        
    Example AJAX Call:
        $.ajax({
            url: '{% url "reports:manager_view_kpi" %}',
            method: 'GET',
            data: {
                report_month: '2025-02',
                category: 'amisys-onshore'
            },
            success: function(response) {
                if (response.success) {
                    updateKPICards(response.kpi);
                }
            }
        });
    """
    # Get query parameters
    report_month = request.GET.get('report_month', '').strip()
    category = request.GET.get('category', '').strip()
    
    logger.info(
        f"Manager view KPI API called - report_month: {report_month}, "
        f"category: {category or 'all'} (user: {request.user.username})"
    )
    
    try:
        # Validate parameters
        validated = validate_manager_view_request(report_month, category)
        
        # Calculate KPI data
        service = ManagerViewService()
        kpi_data = service.calculate_kpi_data(
            validated['report_month'],
            validated['category']
        )
        
        # Serialize for JSON response
        response = serialize_kpi_response(kpi_data)
        
        logger.info(
            f"Manager view KPI API success - Gap: {kpi_data['capacity_gap']}, "
            f"Month: {kpi_data['kpi_month_display']}"
        )
        
        return JsonResponse(response, status=200)
        
    except ValidationError as e:
        logger.warning(f"Validation error in manager view KPI API: {str(e)}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)
        
    except ValueError as e:
        logger.warning(f"Value error in manager view KPI API: {str(e)}")
        return JsonResponse(serialize_error_response(str(e), 404), status=404)
        
    except Exception as e:
        logger.error(f"Unexpected error in manager view KPI API: {str(e)}", exc_info=True)
        return JsonResponse(
            serialize_error_response("An unexpected error occurred", 500),
            status=500
        )


# Optional: Health check endpoint for monitoring
@require_http_methods(["GET"])
def manager_view_health(request):
    """
    Health check endpoint for monitoring.
    
    URL: /reports/api/manager-view/health/
    
    Returns:
        JSON response with system health status
    """
    try:
        # Test API client connection
        client = get_api_client()
        filters = client.get_manager_view_filters()
        
        return JsonResponse({
            'status': 'healthy',
            'service': 'manager_view',
            'available_report_months': len(filters['report_months']),
            'available_categories': len(filters['categories'])
        }, status=200)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JsonResponse({
            'status': 'unhealthy',
            'service': 'manager_view',
            'error': str(e)
        }, status=503)
