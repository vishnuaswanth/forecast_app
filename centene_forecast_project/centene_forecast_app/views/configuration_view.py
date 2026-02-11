# configuration_view.py
"""
Django views for Configuration Management feature.

Follows the view pattern from edit_view.py.
- 1 page render view
- Multiple API endpoints for Month Configuration and Target CPH Configuration
- Comprehensive error handling
- Logging at all key points
"""

import json
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from centene_forecast_app.services.configuration_service import (
    get_month_configurations,
    create_month_configuration,
    bulk_create_month_configurations,
    update_month_configuration,
    delete_month_configuration,
    validate_month_configurations,
    get_target_cph_configurations,
    create_target_cph_configuration,
    bulk_create_target_cph_configurations,
    update_target_cph_configuration,
    delete_target_cph_configuration,
    get_distinct_main_lobs,
    get_distinct_case_types,
)
from centene_forecast_app.validators.configuration_validators import (
    ValidationError,
    validate_month_config_create,
    validate_month_config_update,
    validate_month_config_bulk,
    validate_target_cph_create,
    validate_target_cph_update,
    validate_target_cph_bulk,
    validate_config_id,
    validate_filter_params,
)
from centene_forecast_app.serializers.configuration_serializers import (
    serialize_month_config_list,
    serialize_month_config_response,
    serialize_validation_response,
    serialize_target_cph_list,
    serialize_target_cph_response,
    serialize_distinct_values,
    serialize_bulk_response,
    serialize_delete_response,
    serialize_error_response,
)
from core.config import ConfigurationViewConfig

logger = logging.getLogger('django')


# ============================================================
# PAGE VIEW
# ============================================================

@require_http_methods(["GET"])
def configuration_view_page(request):
    """
    Configuration Management page - Month Config & Target CPH Config.

    Renders template with:
    - Configuration for JavaScript
    - Two tabs: Month Configuration, Target CPH Configuration

    Returns:
        Rendered HTML template

    Example:
        Access at: /forecast/configuration/
    """
    try:
        logger.info("[Configuration View Page] Rendering configuration page")

        # Get config for template/JavaScript
        config = ConfigurationViewConfig.get_config_dict()

        context = {
            'config': config,
            'page_title': 'Configuration Management',
        }

        return render(request, 'centene_forecast_app/configuration_view.html', context)

    except Exception as e:
        logger.error(f"[Configuration View Page] Error rendering page: {e}", exc_info=True)
        return render(request, 'error.html', {
            'error_message': 'Failed to load configuration page'
        }, status=500)


# ============================================================
# MONTH CONFIGURATION API ENDPOINTS
# ============================================================

@require_http_methods(["GET"])
@csrf_exempt
def month_config_list_api(request):
    """
    API: Get month configurations with optional filtering.

    Method: GET
    Auth: None (read-only)

    Query Parameters:
        - month: Optional month name filter (e.g., 'January')
        - year: Optional year filter (e.g., 2025)
        - work_type: Optional work type filter ('Domestic' or 'Global')

    Returns:
        JSON with configurations:
        {
            'success': True,
            'data': [...],
            'total': 50,
            'timestamp': '...'
        }

    Example:
        GET /api/configuration/month-config/?year=2025&work_type=Domestic
    """
    try:
        # Extract query parameters
        month = request.GET.get('month', '').strip() or None
        year_str = request.GET.get('year', '').strip()
        year = int(year_str) if year_str else None
        work_type = request.GET.get('work_type', '').strip() or None

        logger.info(
            f"[Config API] Month config list - month: {month}, year: {year}, "
            f"work_type: {work_type}"
        )

        # Validate filter params if provided
        if month or year or work_type:
            validate_filter_params(month, year, work_type)

        # Get data from service
        data = get_month_configurations(month, year, work_type)

        # Check for error response
        if not data.get('success', True):
            error_msg = data.get('error', 'Failed to fetch configurations')
            status_code = data.get('status_code', 400)
            return JsonResponse(
                serialize_error_response(error_msg, status_code),
                status=status_code
            )

        # Serialize response
        response = serialize_month_config_list(data)

        logger.info(f"[Config API] Month config list - {response['total']} items")
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"[Config API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except ValueError as e:
        logger.warning(f"[Config API] Invalid parameter: {e}")
        return JsonResponse(
            serialize_error_response(f"Invalid parameter: {e}", 400),
            status=400
        )

    except Exception as e:
        logger.error(f"[Config API] Month config list failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to fetch month configurations", 500),
            status=500
        )


@require_http_methods(["POST"])
@csrf_exempt
def month_config_create_api(request):
    """
    API: Create a new month configuration.

    Method: POST
    Auth: None
    Content-Type: application/json

    Request JSON:
        {
            'month': 'January',
            'year': 2025,
            'work_type': 'Domestic',
            'working_days': 22,
            'occupancy': 0.85,
            'shrinkage': 0.20,
            'work_hours': 8.0,
            'updated_by': 'admin'  // Optional
        }

    Returns:
        JSON with created configuration

    Example:
        POST /api/configuration/month-config/create/
    """
    try:
        # Parse request body
        body = json.loads(request.body)

        # Add created_by from request user if not provided (API spec uses created_by)
        if not body.get('created_by') and hasattr(request, 'user') and request.user.is_authenticated:
            body['created_by'] = request.user.username

        logger.info(
            f"[Config API] Creating month config - {body.get('month')} "
            f"{body.get('year')} {body.get('work_type')}"
        )

        # Validate
        validated = validate_month_config_create(body)

        # Create configuration
        data = create_month_configuration(validated)

        # Check for error response
        if not data.get('success', True):
            error_msg = data.get('error', 'Failed to create configuration')
            status_code = data.get('status_code', 400)
            return JsonResponse(
                serialize_error_response(error_msg, status_code),
                status=status_code
            )

        # Serialize response
        response = serialize_month_config_response(data)

        logger.info("[Config API] Month config created successfully")
        return JsonResponse(response, status=201)

    except ValidationError as e:
        logger.warning(f"[Config API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except json.JSONDecodeError:
        logger.warning("[Config API] Invalid JSON in request body")
        return JsonResponse(serialize_error_response("Invalid JSON", 400), status=400)

    except Exception as e:
        logger.error(f"[Config API] Month config create failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to create month configuration", 500),
            status=500
        )


@require_http_methods(["POST"])
@csrf_exempt
def month_config_bulk_create_api(request):
    """
    API: Bulk create month configurations.

    Method: POST
    Auth: None
    Content-Type: application/json

    Request JSON:
        {
            'configs': [
                {'month': 'January', 'year': 2025, 'work_type': 'Domestic', ...},
                {'month': 'January', 'year': 2025, 'work_type': 'Global', ...},
                ...
            ],
            'skip_validation': false  // Optional, skip duplicate check
        }

    Returns:
        JSON with created count

    Example:
        POST /api/configuration/month-config/bulk/
    """
    try:
        # Parse request body
        body = json.loads(request.body)
        # Support both 'configurations' (API spec) and 'configs' (legacy)
        configs = body.get('configurations') or body.get('configs', [])
        skip_validation = body.get('skip_pairing_validation', body.get('skip_validation', False))

        # Get username
        created_by = 'system'
        if hasattr(request, 'user') and request.user.is_authenticated:
            created_by = request.user.username

        logger.info(f"[Config API] Bulk creating {len(configs)} month configs by {created_by}")

        # Validate
        validated_configs = validate_month_config_bulk(configs)

        # Add created_by to each config (API spec uses created_by)
        for config in validated_configs:
            config['created_by'] = created_by

        # Bulk create
        data = bulk_create_month_configurations(validated_configs, created_by, skip_validation)

        # Check for error response
        if not data.get('success', True):
            error_msg = data.get('error', 'Failed to bulk create configurations')
            status_code = data.get('status_code', 400)
            return JsonResponse(
                serialize_error_response(error_msg, status_code),
                status=status_code
            )

        # Serialize response
        response = serialize_bulk_response(data)

        logger.info(f"[Config API] Bulk created {response['created_count']} month configs")
        return JsonResponse(response, status=201)

    except ValidationError as e:
        logger.warning(f"[Config API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except json.JSONDecodeError:
        logger.warning("[Config API] Invalid JSON in request body")
        return JsonResponse(serialize_error_response("Invalid JSON", 400), status=400)

    except Exception as e:
        logger.error(f"[Config API] Bulk create failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to bulk create month configurations", 500),
            status=500
        )


@require_http_methods(["PUT"])
@csrf_exempt
def month_config_update_api(request, config_id):
    """
    API: Update an existing month configuration.

    Method: PUT
    Auth: None
    Content-Type: application/json

    Path Parameter:
        config_id: ID of the configuration to update

    Request JSON:
        {
            'month': 'January',
            'year': 2025,
            'work_type': 'Domestic',
            'working_days': 22,
            'occupancy': 0.85,
            'shrinkage': 0.20,
            'work_hours': 8.0
        }

    Returns:
        JSON with updated configuration

    Example:
        PUT /api/configuration/month-config/123/
    """
    try:
        # Parse request body
        body = json.loads(request.body)

        # Add updated_by from request user
        if hasattr(request, 'user') and request.user.is_authenticated:
            body['updated_by'] = request.user.username

        logger.info(f"[Config API] Updating month config ID: {config_id}")

        # Validate
        validated = validate_month_config_update(config_id, body)
        validated_id = validated.pop('config_id')

        # Update configuration
        data = update_month_configuration(validated_id, validated)

        # Check for error response
        if not data.get('success', True):
            error_msg = data.get('error', 'Failed to update configuration')
            status_code = data.get('status_code', 400)
            return JsonResponse(
                serialize_error_response(error_msg, status_code),
                status=status_code
            )

        # Serialize response
        response = serialize_month_config_response(data)

        logger.info(f"[Config API] Month config {config_id} updated")
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"[Config API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except json.JSONDecodeError:
        logger.warning("[Config API] Invalid JSON in request body")
        return JsonResponse(serialize_error_response("Invalid JSON", 400), status=400)

    except Exception as e:
        logger.error(f"[Config API] Month config update failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to update month configuration", 500),
            status=500
        )


@require_http_methods(["DELETE"])
@csrf_exempt
def month_config_delete_api(request, config_id):
    """
    API: Delete a month configuration.

    Method: DELETE
    Auth: None

    Path Parameter:
        config_id: ID of the configuration to delete

    Query Parameter:
        allow_orphan: If 'true', allows deletion even if it creates orphan

    Returns:
        JSON with success message or orphan warning

    Example:
        DELETE /api/configuration/month-config/123/delete/
        DELETE /api/configuration/month-config/123/delete/?allow_orphan=true
    """
    try:
        allow_orphan = request.GET.get('allow_orphan', '').lower() == 'true'

        logger.info(
            f"[Config API] Deleting month config ID: {config_id}, "
            f"allow_orphan: {allow_orphan}"
        )

        # Validate config_id
        validated_id = validate_config_id(config_id)

        # Delete configuration
        data = delete_month_configuration(validated_id, allow_orphan)

        # Check for error response
        if not data.get('success', True):
            error_msg = data.get('error', 'Failed to delete configuration')
            status_code = data.get('status_code', 400)
            recommendation = data.get('recommendation')
            return JsonResponse(
                serialize_error_response(error_msg, status_code, recommendation),
                status=status_code
            )

        # Serialize response
        response = serialize_delete_response(data)

        logger.info(f"[Config API] Month config {config_id} deleted")
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"[Config API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except Exception as e:
        logger.error(f"[Config API] Month config delete failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to delete month configuration", 500),
            status=500
        )


@require_http_methods(["GET"])
@csrf_exempt
def month_config_validate_api(request):
    """
    API: Validate month configurations for orphaned records.

    Method: GET
    Auth: None (read-only)

    Returns:
        JSON with validation results:
        {
            'success': True,
            'is_valid': False,
            'orphaned_count': 5,
            'orphaned_records': [...],
            'recommendation': 'Add missing configurations...'
        }

    Example:
        GET /api/configuration/month-config/validate/
    """
    try:
        logger.info("[Config API] Running month config validation")

        # Run validation
        data = validate_month_configurations()

        # Check for error response
        if not data.get('success', True):
            error_msg = data.get('error', 'Failed to validate configurations')
            status_code = data.get('status_code', 400)
            return JsonResponse(
                serialize_error_response(error_msg, status_code),
                status=status_code
            )

        # Serialize response
        response = serialize_validation_response(data)

        logger.info(
            f"[Config API] Validation complete - valid: {response['is_valid']}, "
            f"orphaned: {response['orphaned_count']}"
        )
        return JsonResponse(response, status=200)

    except Exception as e:
        logger.error(f"[Config API] Validation failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to validate month configurations", 500),
            status=500
        )


# ============================================================
# TARGET CPH CONFIGURATION API ENDPOINTS
# ============================================================

@require_http_methods(["GET"])
@csrf_exempt
def target_cph_list_api(request):
    """
    API: Get Target CPH configurations with optional filtering.

    Method: GET
    Auth: None (read-only)

    Query Parameters:
        - main_lob: Optional Main LOB filter
        - case_type: Optional Case Type filter

    Returns:
        JSON with configurations:
        {
            'success': True,
            'data': [...],
            'total': 50,
            'timestamp': '...'
        }

    Example:
        GET /api/configuration/target-cph/?main_lob=Amisys
    """
    try:
        # Extract query parameters
        main_lob = request.GET.get('main_lob', '').strip() or None
        case_type = request.GET.get('case_type', '').strip() or None

        logger.info(
            f"[Config API] Target CPH list - main_lob: {main_lob}, case_type: {case_type}"
        )

        # Get data from service
        data = get_target_cph_configurations(main_lob, case_type)

        # Check for error response
        if not data.get('success', True):
            error_msg = data.get('error', 'Failed to fetch configurations')
            status_code = data.get('status_code', 400)
            return JsonResponse(
                serialize_error_response(error_msg, status_code),
                status=status_code
            )

        # Serialize response
        response = serialize_target_cph_list(data)

        logger.info(f"[Config API] Target CPH list - {response['total']} items")
        return JsonResponse(response, status=200)

    except Exception as e:
        logger.error(f"[Config API] Target CPH list failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to fetch Target CPH configurations", 500),
            status=500
        )


@require_http_methods(["POST"])
@csrf_exempt
def target_cph_create_api(request):
    """
    API: Create a new Target CPH configuration.

    Method: POST
    Auth: None
    Content-Type: application/json

    Request JSON:
        {
            'main_lob': 'Amisys Medicaid',
            'case_type': 'Claims Processing',
            'target_cph': 125.5,
            'updated_by': 'admin'  // Optional
        }

    Returns:
        JSON with created configuration

    Example:
        POST /api/configuration/target-cph/create/
    """
    try:
        # Parse request body
        body = json.loads(request.body)

        # Add created_by from request user if not provided (API spec uses created_by)
        if not body.get('created_by') and hasattr(request, 'user') and request.user.is_authenticated:
            body['created_by'] = request.user.username

        logger.info(
            f"[Config API] Creating Target CPH - {body.get('main_lob')} / {body.get('case_type')}"
        )

        # Validate
        validated = validate_target_cph_create(body)

        # Create configuration
        data = create_target_cph_configuration(validated)

        # Check for error response
        if not data.get('success', True):
            error_msg = data.get('error', 'Failed to create configuration')
            status_code = data.get('status_code', 400)
            return JsonResponse(
                serialize_error_response(error_msg, status_code),
                status=status_code
            )

        # Serialize response
        response = serialize_target_cph_response(data)

        logger.info("[Config API] Target CPH created successfully")
        return JsonResponse(response, status=201)

    except ValidationError as e:
        logger.warning(f"[Config API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except json.JSONDecodeError:
        logger.warning("[Config API] Invalid JSON in request body")
        return JsonResponse(serialize_error_response("Invalid JSON", 400), status=400)

    except Exception as e:
        logger.error(f"[Config API] Target CPH create failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to create Target CPH configuration", 500),
            status=500
        )


@require_http_methods(["POST"])
@csrf_exempt
def target_cph_bulk_create_api(request):
    """
    API: Bulk create Target CPH configurations.

    Method: POST
    Auth: None
    Content-Type: application/json

    Request JSON:
        {
            'configs': [
                {'main_lob': 'Amisys', 'case_type': 'Claims', 'target_cph': 125.5},
                ...
            ]
        }

    Returns:
        JSON with created count

    Example:
        POST /api/configuration/target-cph/bulk/
    """
    try:
        # Parse request body
        body = json.loads(request.body)
        # Support both 'configurations' (API spec) and 'configs' (legacy)
        configs = body.get('configurations') or body.get('configs', [])

        # Get username
        created_by = 'system'
        if hasattr(request, 'user') and request.user.is_authenticated:
            created_by = request.user.username

        logger.info(f"[Config API] Bulk creating {len(configs)} Target CPH configs")

        # Validate
        validated_configs = validate_target_cph_bulk(configs)

        # Add created_by to each config (API spec uses created_by)
        for config in validated_configs:
            config['created_by'] = created_by

        # Bulk create
        data = bulk_create_target_cph_configurations(validated_configs)

        # Check for error response
        if not data.get('success', True):
            error_msg = data.get('error', 'Failed to bulk create configurations')
            status_code = data.get('status_code', 400)
            return JsonResponse(
                serialize_error_response(error_msg, status_code),
                status=status_code
            )

        # Serialize response
        response = serialize_bulk_response(data)

        logger.info(f"[Config API] Bulk created {response['created_count']} Target CPH configs")
        return JsonResponse(response, status=201)

    except ValidationError as e:
        logger.warning(f"[Config API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except json.JSONDecodeError:
        logger.warning("[Config API] Invalid JSON in request body")
        return JsonResponse(serialize_error_response("Invalid JSON", 400), status=400)

    except Exception as e:
        logger.error(f"[Config API] Bulk create failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to bulk create Target CPH configurations", 500),
            status=500
        )


@require_http_methods(["PUT"])
@csrf_exempt
def target_cph_update_api(request, config_id):
    """
    API: Update an existing Target CPH configuration.

    Method: PUT
    Auth: None
    Content-Type: application/json

    Path Parameter:
        config_id: ID of the configuration to update

    Request JSON:
        {
            'main_lob': 'Amisys Medicaid',
            'case_type': 'Claims Processing',
            'target_cph': 130.0
        }

    Returns:
        JSON with updated configuration

    Example:
        PUT /api/configuration/target-cph/123/
    """
    try:
        # Parse request body
        body = json.loads(request.body)

        # Add updated_by from request user
        if hasattr(request, 'user') and request.user.is_authenticated:
            body['updated_by'] = request.user.username

        logger.info(f"[Config API] Updating Target CPH ID: {config_id}")

        # Validate
        validated = validate_target_cph_update(config_id, body)
        validated_id = validated.pop('config_id')

        # Update configuration
        data = update_target_cph_configuration(validated_id, validated)

        # Check for error response
        if not data.get('success', True):
            error_msg = data.get('error', 'Failed to update configuration')
            status_code = data.get('status_code', 400)
            return JsonResponse(
                serialize_error_response(error_msg, status_code),
                status=status_code
            )

        # Serialize response
        response = serialize_target_cph_response(data)

        logger.info(f"[Config API] Target CPH {config_id} updated")
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"[Config API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except json.JSONDecodeError:
        logger.warning("[Config API] Invalid JSON in request body")
        return JsonResponse(serialize_error_response("Invalid JSON", 400), status=400)

    except Exception as e:
        logger.error(f"[Config API] Target CPH update failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to update Target CPH configuration", 500),
            status=500
        )


@require_http_methods(["DELETE"])
@csrf_exempt
def target_cph_delete_api(request, config_id):
    """
    API: Delete a Target CPH configuration.

    Method: DELETE
    Auth: None

    Path Parameter:
        config_id: ID of the configuration to delete

    Returns:
        JSON with success message

    Example:
        DELETE /api/configuration/target-cph/123/delete/
    """
    try:
        logger.info(f"[Config API] Deleting Target CPH ID: {config_id}")

        # Validate config_id
        validated_id = validate_config_id(config_id)

        # Delete configuration
        data = delete_target_cph_configuration(validated_id)

        # Check for error response
        if not data.get('success', True):
            error_msg = data.get('error', 'Failed to delete configuration')
            status_code = data.get('status_code', 400)
            return JsonResponse(
                serialize_error_response(error_msg, status_code),
                status=status_code
            )

        # Serialize response
        response = serialize_delete_response(data)

        logger.info(f"[Config API] Target CPH {config_id} deleted")
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"[Config API] Validation error: {e}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except Exception as e:
        logger.error(f"[Config API] Target CPH delete failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to delete Target CPH configuration", 500),
            status=500
        )


@require_http_methods(["GET"])
@csrf_exempt
def target_cph_distinct_lobs_api(request):
    """
    API: Get distinct Main LOB values for dropdown.

    Method: GET
    Auth: None (read-only)

    Returns:
        JSON with distinct Main LOB values:
        {
            'success': True,
            'data': [{'value': 'LOB1', 'display': 'LOB1'}, ...],
            'total': 10
        }

    Example:
        GET /api/configuration/target-cph/distinct/main-lobs/
    """
    try:
        logger.info("[Config API] Fetching distinct Main LOBs")

        # Get data from service
        data = get_distinct_main_lobs()

        # Check for error response
        if not data.get('success', True):
            error_msg = data.get('error', 'Failed to fetch Main LOBs')
            status_code = data.get('status_code', 400)
            return JsonResponse(
                serialize_error_response(error_msg, status_code),
                status=status_code
            )

        # Serialize response
        response = serialize_distinct_values(data)

        logger.info(f"[Config API] Distinct Main LOBs - {response['total']} items")
        return JsonResponse(response, status=200)

    except Exception as e:
        logger.error(f"[Config API] Distinct LOBs failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to fetch distinct Main LOBs", 500),
            status=500
        )


@require_http_methods(["GET"])
@csrf_exempt
def target_cph_distinct_case_types_api(request):
    """
    API: Get distinct Case Type values for dropdown.

    Method: GET
    Auth: None (read-only)

    Query Parameters:
        - main_lob: Optional Main LOB to filter case types

    Returns:
        JSON with distinct Case Type values:
        {
            'success': True,
            'data': [{'value': 'Type1', 'display': 'Type1'}, ...],
            'total': 5
        }

    Example:
        GET /api/configuration/target-cph/distinct/case-types/
        GET /api/configuration/target-cph/distinct/case-types/?main_lob=Amisys
    """
    try:
        main_lob = request.GET.get('main_lob', '').strip() or None

        logger.info(f"[Config API] Fetching distinct Case Types for LOB: {main_lob}")

        # Get data from service
        data = get_distinct_case_types(main_lob)

        # Check for error response
        if not data.get('success', True):
            error_msg = data.get('error', 'Failed to fetch Case Types')
            status_code = data.get('status_code', 400)
            return JsonResponse(
                serialize_error_response(error_msg, status_code),
                status=status_code
            )

        # Serialize response
        response = serialize_distinct_values(data)

        logger.info(f"[Config API] Distinct Case Types - {response['total']} items")
        return JsonResponse(response, status=200)

    except Exception as e:
        logger.error(f"[Config API] Distinct Case Types failed: {e}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to fetch distinct Case Types", 500),
            status=500
        )
