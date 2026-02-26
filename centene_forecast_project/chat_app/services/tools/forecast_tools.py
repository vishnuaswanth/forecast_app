"""
Forecast API Tools
LangChain tools for making forecast API calls and processing data.

Error Handling:
- All API calls are wrapped with proper exception handling
- httpx errors are converted to APIError subclasses
- Validation errors are converted to ValidationError subclasses
"""
import logging
import calendar
from typing import Dict, List, Optional
from langchain.tools import tool
from pydantic import BaseModel, Field
import httpx

from chat_app.services.tools.validation import ForecastQueryParams
from chat_app.repository import get_chat_api_client
from chat_app.exceptions import (
    APIError,
    APIServerError,
    APIClientError,
    APIConnectionError,
    APITimeoutError,
    APIInternalError,
    APIResponseError,
    APIBadRequestError,
    APINotFoundError,
    APIValidationError,
    ValidationError,
    InvalidFilterError,
    classify_httpx_error,
)

logger = logging.getLogger(__name__)


async def fetch_available_reports() -> dict:
    """
    Fetch available forecast reports from API.

    Returns:
        Dictionary with available reports from /api/llm/forecast/available-reports

    Raises:
        APIConnectionError: If cannot connect to API
        APITimeoutError: If API request times out
        APIResponseError: If API returns error status
        APIError: On other API errors
    """
    endpoint = "/api/llm/forecast/available-reports"
    try:
        client = get_chat_api_client()
        data = client.get_available_reports()
        logger.info(f"[Forecast Tools] Fetched {data.get('total_reports', 0)} available reports")
        return data
    except httpx.ConnectError as e:
        logger.error(f"[Forecast Tools] Connection error: {str(e)}", exc_info=True)
        raise APIConnectionError(
            message=f"Cannot connect to forecast API: {str(e)}",
            details={"endpoint": endpoint}
        )
    except httpx.TimeoutException as e:
        logger.error(f"[Forecast Tools] Timeout error: {str(e)}", exc_info=True)
        raise APITimeoutError(
            message=f"Forecast API request timed out: {str(e)}",
            details={"endpoint": endpoint}
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"[Forecast Tools] HTTP error {e.response.status_code}: {e.response.text}", exc_info=True)
        raise APIResponseError(
            message=f"Forecast API error: {str(e)}",
            status_code=e.response.status_code,
            response_body=e.response.text[:500] if e.response.text else None,
            details={"endpoint": endpoint}
        )
    except Exception as e:
        logger.error(f"[Forecast Tools] Failed to fetch available reports: {str(e)}", exc_info=True)
        # Convert generic exceptions to APIError
        raise classify_httpx_error(e, endpoint)


async def validate_report_exists(month: int, year: int) -> dict:
    """
    Check if a forecast report exists for the given month/year.

    Pre-flight validation helper that checks whether data exists for a
    given month/year before attempting a full forecast query.

    Args:
        month: Month number (1-12)
        year: Year (e.g., 2025)

    Returns:
        Dictionary with:
            - exists: bool - Whether a report exists for this period
            - report: dict|None - The matching report if found
            - available_reports: list - All available reports
    """
    month_name = calendar.month_name[month]

    try:
        data = await fetch_available_reports()
        reports = data.get('reports', [])

        # Find matching report
        for report in reports:
            if report.get('month') == month_name and report.get('year') == year:
                logger.info(f"[Forecast Tools] Report exists for {month_name} {year}")
                return {"exists": True, "report": report, "available_reports": reports}

        logger.info(f"[Forecast Tools] No report found for {month_name} {year}")
        return {"exists": False, "report": None, "available_reports": reports}

    except Exception as e:
        logger.warning(
            f"[Forecast Tools] Could not validate report for {month_name} {year}: {str(e)}. "
            f"Proceeding without validation."
        )
        # Return exists=True to avoid blocking the query on validation failure
        return {"exists": True, "report": None, "available_reports": []}


class ForecastQueryInput(BaseModel):
    """Input schema for forecast query tool - all parameters from /api/llm/forecast endpoint"""
    month: int = Field(description="Report month (1-12)")
    year: int = Field(description="Report year")
    platforms: List[str] = Field(default=[], description="Platform filters: Amisys, Facets, Xcelys")
    markets: List[str] = Field(default=[], description="Market filters: Medicaid, Medicare")
    localities: List[str] = Field(default=[], description="Locality filters: Domestic, Global")
    main_lobs: List[str] = Field(default=[], description="Full LOB strings: 'Amisys Medicaid Domestic'")
    states: List[str] = Field(default=[], description="State filters: CA, TX, or N/A")
    case_types: List[str] = Field(default=[], description="Case type filters: Claims Processing, Enrollment")
    forecast_months: List[str] = Field(default=[], description="Month filters: Apr-25, May-25, etc")


async def fetch_forecast_data(
    params: ForecastQueryParams,
    enable_validation: bool = True
) -> dict:
    """
    Fetch forecast data from API with optional pre-flight validation.

    NEW: Pre-flight validation using FilterValidator to catch typos and invalid values
    before making the actual API call.

    Maps ForecastQueryParams Pydantic model to /api/llm/forecast API parameters.

    API Spec: /api/llm/forecast
    - Required: month (string), year (integer)
    - Optional: platform[], market[], locality[], main_lob[], state[], case_type[], forecast_months[]
    - Returns: JSON with records, totals, business_insights, metadata, configuration

    Args:
        params: ForecastQueryParams with validated parameters
        enable_validation: Whether to perform pre-flight validation (default: True)

    Returns:
        Dictionary with forecast data from API

    Raises:
        ValueError: If API returns error or validation fails
        httpx.HTTPStatusError: On HTTP error
        Exception: On other errors
    """
    # PRE-FLIGHT VALIDATION (NEW)
    if enable_validation:
        from chat_app.services.tools.validation_tools import FilterValidator

        validator = FilterValidator()
        validation_results = await validator.validate_all(params)

        # Check for validation issues (rejections and low-confidence matches)
        has_invalid = any(
            not result.is_valid
            for results_list in validation_results.values()
            for result in results_list
        )

        if has_invalid:
            # Build error message with suggestions
            error_parts = ["Filter validation failed:"]
            for field_name, results in validation_results.items():
                for result in results:
                    if not result.is_valid:
                        suggestions_str = ', '.join(result.suggestions[:3])
                        error_parts.append(
                            f"  - {field_name}: '{result.original_value}' is invalid. "
                            f"Did you mean: {suggestions_str}?"
                        )

            error_message = '\n'.join(error_parts)
            logger.warning(f"[Forecast Tools] {error_message}")
            raise ValueError(error_message)

        # Apply auto-corrections (>90% confidence)
        for field_name, results in validation_results.items():
            for result in results:
                if result.confidence >= FilterValidator.HIGH_CONFIDENCE and result.corrected_value:
                    # Update params with corrected value
                    field_list = getattr(params, field_name, None)
                    if field_list and result.original_value in field_list:
                        idx = field_list.index(result.original_value)
                        field_list[idx] = result.corrected_value
                        logger.info(
                            f"[Forecast Tools] Auto-corrected {field_name}: "
                            f"'{result.original_value}' → '{result.corrected_value}' "
                            f"(confidence: {result.confidence:.2f})"
                        )

    # Map Pydantic model to API parameters
    api_params = {
        'month': calendar.month_name[params.month],  # Convert 3 → "March"
        'year': params.year,
    }

    # Build filter mapping for repository
    filters = {}

    if params.platforms:
        filters['platform'] = params.platforms

    if params.markets:
        filters['market'] = params.markets

    if params.localities:
        filters['locality'] = params.localities

    if params.main_lobs:
        # This overrides platform/market/locality per API spec
        filters['main_lob'] = params.main_lobs

    if params.states:
        filters['state'] = params.states

    if params.case_types:
        # Note: API parameter is 'case_type' (singular)
        filters['case_type'] = params.case_types

    if params.forecast_months:
        # Filters which months appear in response (doesn't filter records, just output columns)
        filters['forecast_months'] = params.forecast_months

    # Make API call using chat_app repository (cached for 60s by backend)
    endpoint = "/api/llm/forecast"
    try:
        logger.info(
            f"[Forecast Tools] Fetching data for {api_params['month']} {api_params['year']} "
            f"with filters: {filters}"
        )

        client = get_chat_api_client()

        # Use repository method which handles array syntax internally
        data = client.get_forecast_data(
            month=api_params['month'],
            year=api_params['year'],
            **filters
        )

        logger.info(
            f"[Forecast Tools] Received {data.get('total_records', 0)} records "
            f"for {api_params['month']} {api_params['year']}"
        )

        return data

    except ValueError as e:
        # Validation errors from API
        logger.error(f"[Forecast Tools] API validation error: {str(e)}")
        raise ValidationError(
            message=str(e),
            user_message="Invalid query parameters. Please check your filters."
        )
    except httpx.ConnectError as e:
        logger.error(f"[Forecast Tools] Connection error: {str(e)}", exc_info=True)
        raise APIConnectionError(
            message=f"Cannot connect to forecast API: {str(e)}",
            details={"endpoint": endpoint, "month": api_params['month'], "year": api_params['year']}
        )
    except httpx.TimeoutException as e:
        logger.error(f"[Forecast Tools] Timeout error: {str(e)}", exc_info=True)
        raise APITimeoutError(
            message=f"Forecast API request timed out: {str(e)}",
            details={"endpoint": endpoint, "month": api_params['month'], "year": api_params['year']}
        )
    except httpx.HTTPStatusError as e:
        import json

        status_code = e.response.status_code
        response_text = e.response.text[:500] if e.response.text else None

        # Try to parse JSON response for structured error info
        response_json = None
        try:
            response_json = json.loads(e.response.text) if e.response.text else None
        except (json.JSONDecodeError, TypeError):
            pass

        # === CLIENT ERRORS (4xx) - User can fix these ===

        if status_code == 400:
            # Bad Request - missing/invalid parameters
            logger.warning(f"[Forecast Tools] Bad request (400): {response_text}")

            missing_fields = None
            invalid_fields = None
            if response_json:
                missing_fields = response_json.get('missing_fields', response_json.get('missing'))
                invalid_fields = response_json.get('invalid_fields', response_json.get('errors'))

            raise APIBadRequestError(
                message=f"Invalid request for {api_params['month']} {api_params['year']}",
                status_code=status_code,
                response_body=response_text,
                missing_fields=missing_fields,
                invalid_fields=invalid_fields,
                details={"endpoint": endpoint, "filters": filters}
            )

        if status_code == 404:
            # Not Found - no data for the given criteria
            logger.info(f"[Forecast Tools] No data found (404) for {api_params['month']} {api_params['year']} with filters: {filters}")

            raise APINotFoundError(
                message=f"No forecast data found for {api_params['month']} {api_params['year']}",
                filters_used={"month": api_params['month'], "year": api_params['year'], **filters},
                details={"endpoint": endpoint}
            )

        if status_code == 422:
            # Validation Error - invalid filter values
            logger.warning(f"[Forecast Tools] Validation error (422): {response_text}")

            field_name = None
            invalid_value = None
            valid_options = None
            if response_json:
                # FastAPI validation errors
                if 'detail' in response_json and isinstance(response_json['detail'], list):
                    first_error = response_json['detail'][0] if response_json['detail'] else {}
                    field_name = first_error.get('loc', [None])[-1]
                    invalid_value = first_error.get('input')
                else:
                    field_name = response_json.get('field')
                    invalid_value = response_json.get('value')
                    valid_options = response_json.get('valid_options')

            raise APIValidationError(
                message=f"Invalid filter value for {api_params['month']} {api_params['year']}",
                field_name=field_name,
                invalid_value=invalid_value,
                valid_options=valid_options,
                details={"endpoint": endpoint, "filters": filters}
            )

        # Other 4xx errors - user-fixable
        if 400 <= status_code < 500:
            logger.warning(f"[Forecast Tools] Client error ({status_code}): {response_text}")
            raise APIClientError(
                message=f"Request error ({status_code}) for {api_params['month']} {api_params['year']}",
                user_message=f"There was an issue with your request. Please check your filters and try again.",
                details={"endpoint": endpoint, "status_code": status_code, "filters": filters}
            )

        # === SERVER ERRORS (5xx) - System issue, contact admin ===

        if status_code == 500:
            logger.error(f"[Forecast Tools] Internal server error (500): {response_text}")
            raise APIInternalError(
                message=f"Internal server error for {api_params['month']} {api_params['year']}",
                details={"endpoint": endpoint}
            )

        if status_code >= 500:
            logger.error(f"[Forecast Tools] Server error ({status_code}): {response_text}")
            raise APIServerError(
                message=f"Server error ({status_code}) for {api_params['month']} {api_params['year']}",
                details={"endpoint": endpoint, "status_code": status_code}
            )

        # Fallback for unknown status codes
        logger.error(f"[Forecast Tools] Unexpected HTTP error {status_code}: {response_text}")
        raise APIResponseError(
            message=f"Forecast API error: HTTP {status_code}",
            status_code=status_code,
            response_body=response_text,
            details={"endpoint": endpoint}
        )
    except Exception as e:
        logger.error(f"[Forecast Tools] API call failed: {str(e)}", exc_info=True)
        # Convert generic exceptions to APIError
        raise classify_httpx_error(e, endpoint)


@tool("get_forecast_data", args_schema=ForecastQueryInput, return_direct=False)
async def get_forecast_data_tool(
    month: int,
    year: int,
    platforms: List[str] = None,
    markets: List[str] = None,
    localities: List[str] = None,
    main_lobs: List[str] = None,
    states: List[str] = None,
    case_types: List[str] = None,
    forecast_months: List[str] = None,
) -> dict:
    """
    Fetch forecast data from API.

    Args:
        month: Report month (1-12)
        year: Report year
        platforms: Optional platform filters (Amisys, Facets, Xcelys)
        markets: Optional market filters (Medicaid, Medicare)
        localities: Optional locality filters (Domestic, Global)
        main_lobs: Optional specific LOB strings (e.g., "Amisys Medicaid Domestic")
                   Note: If provided, platforms/markets/localities are ignored
        states: Optional state filters (CA, TX, N/A)
        case_types: Optional case type filters (Claims Processing, Enrollment)
        forecast_months: Optional month filters (Apr-25, May-25) - filters output months

    Returns:
        Dictionary with forecast records, totals, and insights
    """
    params = ForecastQueryParams(
        month=month,
        year=year,
        platforms=platforms or [],
        markets=markets or [],
        localities=localities or [],
        main_lobs=main_lobs or [],
        states=states or [],
        case_types=case_types or [],
        forecast_months=forecast_months or []
    )

    try:
        data = await fetch_forecast_data(params)
        return {
            "success": True,
            "data": data,
            "record_count": len(data.get('records', []))
        }
    except Exception as e:
        logger.error(f"[Forecast Tools] Tool execution failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@tool("get_available_reports", return_direct=False)
async def get_available_reports_tool() -> dict:
    """
    List all available forecast reports with their month, year, and status.

    Returns a list of forecast reports including period, record count,
    and whether the report is current or outdated.

    Returns:
        Dictionary with success status and available reports data
    """
    try:
        data = await fetch_available_reports()
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"[Forecast Tools] Available reports tool failed: {str(e)}")
        return {"success": False, "error": str(e)}


async def call_preview_ramp(forecast_id: int, month_key: str, ramp_payload: dict) -> dict:
    """
    Preview the impact of a ramp calculation without applying it.

    Args:
        forecast_id: Forecast record ID
        month_key: Month key in 'YYYY-MM' format (e.g. '2026-01')
        ramp_payload: Dict containing 'weeks' list and 'totalRampEmployees'

    Returns:
        Dictionary with preview data from backend

    Raises:
        APIConnectionError: If cannot connect to API
        APITimeoutError: If API request times out
        APIResponseError: If API returns error status
    """
    import asyncio
    endpoint = f"/api/v1/forecasts/{forecast_id}/months/{month_key}/ramp/preview"
    try:
        client = get_chat_api_client()
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None,
            lambda: client.preview_ramp_calculation(forecast_id, month_key, ramp_payload)
        )
        logger.info(f"[Forecast Tools] Ramp preview fetched for forecast {forecast_id}, month {month_key}")
        return data
    except httpx.ConnectError as e:
        raise APIConnectionError(message=f"Cannot connect to API: {str(e)}", details={"endpoint": endpoint})
    except httpx.TimeoutException as e:
        raise APITimeoutError(message=f"API request timed out: {str(e)}", details={"endpoint": endpoint})
    except httpx.HTTPStatusError as e:
        raise APIResponseError(
            message=f"API error: {str(e)}",
            status_code=e.response.status_code,
            response_body=e.response.text[:500] if e.response.text else None,
            details={"endpoint": endpoint}
        )
    except Exception as e:
        logger.error(f"[Forecast Tools] Failed to preview ramp: {str(e)}", exc_info=True)
        raise classify_httpx_error(e, endpoint)


async def call_apply_ramp(forecast_id: int, month_key: str, ramp_payload: dict) -> dict:
    """
    Apply a ramp calculation to persist it.

    Args:
        forecast_id: Forecast record ID
        month_key: Month key in 'YYYY-MM' format (e.g. '2026-01')
        ramp_payload: Dict containing 'weeks' list and 'totalRampEmployees'

    Returns:
        Dictionary with apply result from backend

    Raises:
        APIConnectionError: If cannot connect to API
        APITimeoutError: If API request times out
        APIResponseError: If API returns error status
    """
    import asyncio
    endpoint = f"/api/v1/forecasts/{forecast_id}/months/{month_key}/ramp/apply"
    try:
        client = get_chat_api_client()
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None,
            lambda: client.apply_ramp_calculation(forecast_id, month_key, ramp_payload)
        )
        logger.info(f"[Forecast Tools] Ramp applied for forecast {forecast_id}, month {month_key}")
        return data
    except httpx.ConnectError as e:
        raise APIConnectionError(message=f"Cannot connect to API: {str(e)}", details={"endpoint": endpoint})
    except httpx.TimeoutException as e:
        raise APITimeoutError(message=f"API request timed out: {str(e)}", details={"endpoint": endpoint})
    except httpx.HTTPStatusError as e:
        raise APIResponseError(
            message=f"API error: {str(e)}",
            status_code=e.response.status_code,
            response_body=e.response.text[:500] if e.response.text else None,
            details={"endpoint": endpoint}
        )
    except Exception as e:
        logger.error(f"[Forecast Tools] Failed to apply ramp: {str(e)}", exc_info=True)
        raise classify_httpx_error(e, endpoint)


async def call_get_applied_ramp(forecast_id: int, month_key: str) -> dict:
    """
    Retrieve the currently applied ramp for a forecast row and month.

    Args:
        forecast_id: Forecast record ID
        month_key: Month key in 'YYYY-MM' format (e.g. '2026-01')

    Returns:
        Dictionary with applied ramp data from backend

    Raises:
        APIConnectionError: If cannot connect to API
        APITimeoutError: If API request times out
        APIResponseError: If API returns error status
    """
    import asyncio
    endpoint = f"/api/v1/forecasts/{forecast_id}/months/{month_key}/ramp"
    try:
        client = get_chat_api_client()
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None,
            lambda: client.get_applied_ramp(forecast_id, month_key)
        )
        logger.info(f"[Forecast Tools] Applied ramp fetched for forecast {forecast_id}, month {month_key}")
        return data
    except httpx.ConnectError as e:
        raise APIConnectionError(message=f"Cannot connect to API: {str(e)}", details={"endpoint": endpoint})
    except httpx.TimeoutException as e:
        raise APITimeoutError(message=f"API request timed out: {str(e)}", details={"endpoint": endpoint})
    except httpx.HTTPStatusError as e:
        raise APIResponseError(
            message=f"API error: {str(e)}",
            status_code=e.response.status_code,
            response_body=e.response.text[:500] if e.response.text else None,
            details={"endpoint": endpoint}
        )
    except Exception as e:
        logger.error(f"[Forecast Tools] Failed to get applied ramp: {str(e)}", exc_info=True)
        raise classify_httpx_error(e, endpoint)


@tool("calculate_forecast_totals")
async def calculate_totals_tool(forecast_data: dict) -> dict:
    """
    Calculate totals from forecast data.

    Args:
        forecast_data: Raw forecast data from API

    Returns:
        Dictionary with totals per month
    """
    totals = forecast_data.get('totals', {})
    logger.info(f"[Forecast Tools] Calculated totals for {len(totals)} months")
    return totals
