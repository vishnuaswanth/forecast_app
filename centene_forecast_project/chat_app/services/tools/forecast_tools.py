"""
Forecast API Tools
LangChain tools for making forecast API calls and processing data.
"""
import logging
import calendar
from typing import Dict, List, Optional
from langchain.tools import tool
from pydantic import BaseModel, Field
import httpx

from chat_app.services.tools.validation import ForecastQueryParams
from chat_app.repository import get_chat_api_client

logger = logging.getLogger(__name__)


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
        logger.error(f"[Forecast Tools] API validation error: {str(e)}")
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"[Forecast Tools] API HTTP error {e.response.status_code}: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"[Forecast Tools] API call failed: {str(e)}", exc_info=True)
        raise


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
