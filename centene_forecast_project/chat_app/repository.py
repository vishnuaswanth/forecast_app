"""
API Client for Chat App
Handles HTTP requests to FastAPI backend's LLM endpoints with proper error handling and retry logic.
"""
import logging
from typing import Dict, Optional
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class ChatAPIClient:
    """
    API Client for chat app LLM endpoints.

    Handles HTTP requests to FastAPI backend with proper error handling,
    timeouts, and retry logic.

    Usage:
        client = ChatAPIClient()
        data = client.get_forecast_data(month="March", year=2025, platform=["Amisys"])
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize Chat API Client.

        Args:
            base_url: Base URL for API endpoints (default: from settings.API_BASE_URL)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retry attempts for failed requests (default: 3)
        """
        self.base_url = (base_url or getattr(settings, 'API_BASE_URL', 'http://127.0.0.1:8888')).rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries

        # Configure HTTPX client with retry strategy
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            # Disable SSL verification for corporate networks if needed
            verify=False
        )

        logger.info(f"ChatAPIClient initialized with base_url: {self.base_url}")

    def get(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make GET request to API endpoint.

        Args:
            endpoint: API endpoint path (e.g., '/api/llm/forecast')
            params: URL query parameters
            **kwargs: Additional arguments passed to httpx.get

        Returns:
            HTTPX Response object

        Raises:
            httpx.HTTPStatusError: On HTTP error response
            httpx.TimeoutException: On request timeout
            httpx.RequestError: On connection or other request errors
        """
        url = f"{self.base_url}{endpoint}"

        # Retry logic
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"[Chat API] GET {url} - Attempt {attempt + 1}/{self.max_retries}")
                logger.debug(f"[Chat API] Params: {params}")

                response = self.client.get(
                    endpoint,
                    params=params,
                    **kwargs
                )

                response.raise_for_status()

                logger.debug(f"[Chat API] GET {url} - Status: {response.status_code}")
                return response

            except httpx.TimeoutException:
                logger.error(f"[Chat API] Request timeout after {self.timeout}s: GET {url}")
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(f"[Chat API] Retrying... ({attempt + 1}/{self.max_retries})")

            except httpx.HTTPStatusError as e:
                logger.error(f"[Chat API] HTTP error {e.response.status_code}: GET {url}")
                logger.error(f"[Chat API] Response: {e.response.text}")
                raise

            except httpx.RequestError as e:
                logger.error(f"[Chat API] Request error: {type(e).__name__} - {str(e)}")
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(f"[Chat API] Retrying... ({attempt + 1}/{self.max_retries})")

        # Should not reach here
        raise Exception("Max retries exceeded")

    def get_forecast_data(
        self,
        month: str,
        year: int,
        **filters
    ) -> Dict:
        """
        Get forecast data from /api/llm/forecast endpoint.

        Args:
            month: Month name (e.g., "March", "April")
            year: Year (e.g., 2025)
            **filters: Optional filter parameters:
                - platform: List[str]
                - market: List[str]
                - locality: List[str]
                - main_lob: List[str]
                - state: List[str]
                - case_type: List[str]
                - forecast_months: List[str]

        Returns:
            Dictionary with forecast data (JSON response)

        Example:
            >>> client = ChatAPIClient()
            >>> data = client.get_forecast_data(
            ...     month="March",
            ...     year=2025,
            ...     platform=["Amisys"],
            ...     state=["CA", "TX"]
            ... )
        """
        # Build params with array syntax for multi-value filters
        params = {
            'month': month,
            'year': year
        }

        # Add multi-value filters using array syntax
        for key, value in filters.items():
            if value:  # Only add non-empty filters
                if isinstance(value, list):
                    # Use array syntax: platform[]=Amisys&platform[]=Facets
                    params[f'{key}[]'] = value
                else:
                    params[key] = value

        try:
            response = self.get('/api/llm/forecast', params=params)
            data = response.json()

            # Validate response structure
            if not data.get('success', False):
                error_msg = data.get('error', 'Unknown error from API')
                logger.error(f"[Chat API] API returned error: {error_msg}")
                raise ValueError(f"API Error: {error_msg}")

            logger.info(
                f"[Chat API] Forecast data retrieved successfully - "
                f"{data.get('total_records', 0)} records"
            )

            return data

        except Exception as e:
            logger.error(f"[Chat API] Failed to get forecast data: {str(e)}", exc_info=True)
            raise

    def get_filter_options(
        self,
        month: str,
        year: int
    ) -> Dict:
        """
        Get available filter options from /api/llm/forecast/filter-options endpoint.

        This endpoint returns all valid filter values for a given month/year combination,
        used for pre-flight validation and filter value suggestions.

        Args:
            month: Month name (e.g., "March", "April")
            year: Year (e.g., 2025)

        Returns:
            Dictionary with filter options (JSON response):
            {
                'success': True,
                'month': 'March',
                'year': 2025,
                'filter_options': {
                    'platforms': ['Amisys', 'Facets', 'Xcelys'],
                    'markets': ['Medicaid', 'Medicare'],
                    'localities': ['Domestic', 'Global'],
                    'main_lobs': ['Amisys Medicaid Domestic', ...],
                    'states': ['CA', 'TX', 'FL', ...],
                    'case_types': ['Claims Processing', ...],
                    'forecast_months': ['Apr-25', 'May-25', ...]
                },
                'record_count': 1250
            }

        Raises:
            ValueError: If API returns error
            httpx.HTTPStatusError: On HTTP error
            httpx.RequestError: On connection error

        Example:
            >>> client = ChatAPIClient()
            >>> options = client.get_filter_options("March", 2025)
            >>> print(options['filter_options']['platforms'])
            ['Amisys', 'Facets', 'Xcelys']
        """
        params = {
            'month': month,
            'year': year
        }

        try:
            response = self.get('/api/llm/forecast/filter-options', params=params)
            data = response.json()

            # Validate response structure
            if not data.get('success', False):
                error_msg = data.get('error', 'Unknown error from API')
                logger.error(f"[Chat API] Filter options API returned error: {error_msg}")
                raise ValueError(f"API Error: {error_msg}")

            logger.info(
                f"[Chat API] Filter options retrieved successfully - "
                f"{data.get('record_count', 0)} records available for {month} {year}"
            )

            return data

        except Exception as e:
            logger.error(f"[Chat API] Failed to get filter options: {str(e)}", exc_info=True)
            raise

    def get_available_reports(self) -> Dict:
        """
        Get available forecast reports from /api/llm/forecast/available-reports endpoint.

        Returns a list of all available forecast reports sorted newest-first,
        including month, year, status, record count, and data freshness.

        Returns:
            Dictionary with available reports (JSON response):
            {
                'success': True,
                'reports': [
                    {'month': 'March', 'year': 2025, 'is_valid': True, 'record_count': 1250, ...},
                    ...
                ],
                'total_reports': 3
            }

        Raises:
            ValueError: If API returns error
            httpx.HTTPStatusError: On HTTP error
            httpx.RequestError: On connection error
        """
        try:
            response = self.get('/api/llm/forecast/available-reports')
            data = response.json()

            if not data.get('success', False):
                error_msg = data.get('error', 'Unknown error from API')
                logger.error(f"[Chat API] Available reports API returned error: {error_msg}")
                raise ValueError(f"API Error: {error_msg}")

            logger.info(
                f"[Chat API] Available reports retrieved successfully - "
                f"{data.get('total_reports', 0)} reports found"
            )

            return data

        except Exception as e:
            logger.error(f"[Chat API] Failed to get available reports: {str(e)}", exc_info=True)
            raise

    def post(
        self,
        endpoint: str,
        json_data: Optional[Dict] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make POST request to API endpoint.

        Args:
            endpoint: API endpoint path (e.g., '/api/v1/forecasts/1/months/2026-01/ramp/preview')
            json_data: JSON request body
            **kwargs: Additional arguments passed to httpx.post

        Returns:
            HTTPX Response object

        Raises:
            httpx.HTTPStatusError: On HTTP error response
            httpx.TimeoutException: On request timeout
            httpx.RequestError: On connection or other request errors
        """
        url = f"{self.base_url}{endpoint}"

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"[Chat API] POST {url} - Attempt {attempt + 1}/{self.max_retries}")

                response = self.client.post(
                    endpoint,
                    json=json_data,
                    **kwargs
                )

                response.raise_for_status()

                logger.debug(f"[Chat API] POST {url} - Status: {response.status_code}")
                return response

            except httpx.TimeoutException:
                logger.error(f"[Chat API] Request timeout after {self.timeout}s: POST {url}")
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(f"[Chat API] Retrying... ({attempt + 1}/{self.max_retries})")

            except httpx.HTTPStatusError as e:
                logger.error(f"[Chat API] HTTP error {e.response.status_code}: POST {url}")
                logger.error(f"[Chat API] Response: {e.response.text}")
                raise

            except httpx.RequestError as e:
                logger.error(f"[Chat API] Request error: {type(e).__name__} - {str(e)}")
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(f"[Chat API] Retrying... ({attempt + 1}/{self.max_retries})")

        raise Exception("Max retries exceeded")

    def preview_ramp_calculation(
        self,
        forecast_id: int,
        month_key: str,
        ramp_payload: Dict
    ) -> Dict:
        """
        Preview the impact of a ramp calculation without applying it.

        POST /api/v1/forecasts/{forecastId}/months/{monthKey}/ramp/preview

        Args:
            forecast_id: Forecast record ID
            month_key: Month key in 'YYYY-MM' format (e.g. '2026-01')
            ramp_payload: Dict containing 'weeks' list and 'totalRampEmployees'

        Returns:
            Dictionary with preview data (current, projected, diff values)
        """
        endpoint = f"/api/v1/forecasts/{forecast_id}/months/{month_key}/ramp/preview"
        try:
            response = self.post(endpoint, json_data=ramp_payload)
            data = response.json()
            logger.info(f"[Chat API] Ramp preview retrieved for forecast {forecast_id}, month {month_key}")
            return data
        except Exception as e:
            logger.error(f"[Chat API] Failed to preview ramp calculation: {str(e)}", exc_info=True)
            raise

    def apply_ramp_calculation(
        self,
        forecast_id: int,
        month_key: str,
        ramp_payload: Dict
    ) -> Dict:
        """
        Apply a ramp calculation to persist it.

        POST /api/v1/forecasts/{forecastId}/months/{monthKey}/ramp/apply

        Args:
            forecast_id: Forecast record ID
            month_key: Month key in 'YYYY-MM' format (e.g. '2026-01')
            ramp_payload: Dict containing 'weeks' list and 'totalRampEmployees'

        Returns:
            Dictionary with apply result
        """
        endpoint = f"/api/v1/forecasts/{forecast_id}/months/{month_key}/ramp/apply"
        try:
            response = self.post(endpoint, json_data=ramp_payload)
            data = response.json()
            logger.info(f"[Chat API] Ramp applied for forecast {forecast_id}, month {month_key}")
            return data
        except Exception as e:
            logger.error(f"[Chat API] Failed to apply ramp calculation: {str(e)}", exc_info=True)
            raise

    def get_applied_ramp(
        self,
        forecast_id: int,
        month_key: str
    ) -> Dict:
        """
        Retrieve the currently applied ramp for a forecast row and month.

        GET /api/v1/forecasts/{forecastId}/months/{monthKey}/ramp

        Args:
            forecast_id: Forecast record ID
            month_key: Month key in 'YYYY-MM' format (e.g. '2026-01')

        Returns:
            Dictionary with applied ramp data
        """
        endpoint = f"/api/v1/forecasts/{forecast_id}/months/{month_key}/ramp"
        try:
            response = self.get(endpoint)
            data = response.json()
            logger.info(f"[Chat API] Applied ramp retrieved for forecast {forecast_id}, month {month_key}")
            return data
        except Exception as e:
            logger.error(f"[Chat API] Failed to get applied ramp: {str(e)}", exc_info=True)
            raise

    def close(self):
        """Close the HTTP client and cleanup resources."""
        self.client.close()
        logger.info("[Chat API] Client closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Singleton instance for application-wide use
_chat_api_client_instance: Optional[ChatAPIClient] = None


def get_chat_api_client() -> ChatAPIClient:
    """
    Get or create singleton ChatAPIClient instance.

    Returns:
        Configured ChatAPIClient instance

    Usage:
        from chat_app.repository import get_chat_api_client

        client = get_chat_api_client()
        data = client.get_forecast_data("March", 2025, platform=["Amisys"])
    """
    global _chat_api_client_instance

    if _chat_api_client_instance is None:
        base_url = getattr(settings, 'API_BASE_URL', 'http://127.0.0.1:8888')
        timeout = 30

        _chat_api_client_instance = ChatAPIClient(
            base_url=base_url,
            timeout=timeout
        )
        logger.info("[Chat API] Created new ChatAPIClient singleton instance")

    return _chat_api_client_instance


def reset_chat_api_client():
    """
    Reset singleton instance (useful for testing).

    Usage:
        from chat_app.repository import reset_chat_api_client

        reset_chat_api_client()  # Force recreation on next get_chat_api_client() call
    """
    global _chat_api_client_instance
    if _chat_api_client_instance:
        _chat_api_client_instance.close()
        _chat_api_client_instance = None
        logger.info("[Chat API] ChatAPIClient singleton instance reset")
