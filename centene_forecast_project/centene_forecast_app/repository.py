# repository.py
import logging
from io import BytesIO
from typing import Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from django.conf import settings

# Import mock data (will be replaced with API calls)
from centene_forecast_app.mock_data import (
    get_available_change_types,
)

# Import caching utilities
from centene_forecast_app.app_utils.cache_utils import cache_with_ttl
from core.config import ForecastCacheConfig, ManagerViewConfig, ExecutionMonitoringConfig, EditViewConfig, ConfigurationViewConfig

logger = logging.getLogger('django')

class APIClient:
    """
    API Client for external service communication.

    Handles HTTP requests to FastAPI backend with proper error handling,
    timeouts, and retry logic.

    Usage:
        client = APIClient(base_url='http://localhost:8888/')
        data = client.get_manager_view_data('2025-02', 'amisys-onshore')
    """
    def __init__(
        self,
        base_url: str,
        default_headers: Optional[Dict[str, str]]=None,
        timeout: int = 30,
        max_retries: int = 3
    ):

        """
        Initialize API Client.

        Args:
            base_url: Base URL for API endpoints
            timeout: Request timeout in seconds (default: 30)
            headers: Optional custom headers dict
            max_retries: Maximum number of retry attempts for failed requests (default: 3)
        """
        self.base_url = base_url.rstrip('/')
        self.headers = default_headers or {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        self.timeout = timeout
        self.month_mapper = {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December"
        }

        # Configure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,  # Wait 1, 2, 4 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info(f"APIClient initialized with base_url: {self.base_url}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        timeout: Optional[int] = None,
        **kwargs
    ) -> Dict:
        """
        Internal method to make HTTP requests with error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (e.g., '/manager-view/data')
            params: URL query parameters
            data: Request body data (for POST/PUT)
            timeout: Request timeout in seconds (uses self.timeout if not provided)
            **kwargs: Additional arguments passed to requests

        Returns:
            Response data as dictionary

        Raises:
            requests.exceptions.RequestException: On request failure
        """
        url = f"{self.base_url}{endpoint}"
        request_timeout = timeout if timeout is not None else self.timeout

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=self.headers,
                timeout=request_timeout,
                **kwargs
            )

            # Handle 4XX client errors - return error dict instead of raising
            if 400 <= response.status_code < 500:
                error_detail = None
                try:
                    error_json = response.json()
                    # FastAPI typically uses 'detail' for error messages
                    error_detail = error_json.get('detail') or error_json.get('message') or error_json.get('error')
                except (ValueError, KeyError):
                    error_detail = response.text or f"HTTP {response.status_code} error"

                logger.warning(
                    f"API {method} {url} - Client error {response.status_code}: {error_detail}"
                )
                return {
                    'success': False,
                    'error': error_detail,
                    'status_code': response.status_code
                }

            # Raise for 5XX server errors
            response.raise_for_status()

            logger.debug(f"API {method} {url} - Status: {response.status_code}")

            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout after {request_timeout}s: {method} {url}")
            return {
                'success': False,
                'error': f'Request timeout after {request_timeout}s',
                'status_code': 408
            }
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error: {method} {url}")
            return {
                'success': False,
                'error': 'Connection error: Unable to reach the API server',
                'status_code': 503
            }
        except requests.exceptions.HTTPError as e:
            # 5XX server errors
            error_detail = None
            try:
                error_json = e.response.json()
                error_detail = error_json.get('detail') or error_json.get('message') or str(e)
            except (ValueError, AttributeError):
                error_detail = str(e)

            logger.error(f"HTTP error {e.response.status_code}: {method} {url} - {error_detail}")
            return {
                'success': False,
                'error': error_detail,
                'status_code': e.response.status_code if e.response else 500
            }
        except Exception as e:
            logger.error(f"Unexpected error in API request: {str(e)}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'status_code': 500
            }

    def _upload_file(self, endpoint: str, file_content: bytes, filename: str, user: str):
        url = f"{self.base_url}{endpoint}"
        params = {'user': user}

        if filename.endswith('.csv'):
            content_type = 'text/csv'
        elif filename.endswith('.xlsx'):
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:
            content_type = 'application/octet-stream'

        headers = self.headers.copy()
        headers.pop('accept', None)
        headers.pop('Content-Type', None)  # Remove to allow multipart/form-data

        files = {
            'file': (filename, file_content, content_type)
        }

        try:
            response = requests.post(url, params=params, files=files, headers=headers, timeout=(30, 300))
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as http_err:
            try:
                error_response = response.json()
                detail = error_response.get('detail', str(http_err))
                logger.error(f"[Upload Error] {endpoint} | User: {user} | File: {filename} | Detail: {detail}")
                return {'error': detail}
            except Exception:
                logger.exception(f"[Upload Error - Invalid JSON] {endpoint} | User: {user} | File: {filename} | Error: {http_err}")
                return {'error': 'Internal server error, upload failed.'}

        except Exception as e:
            logger.exception(f"[Upload Error - Exception] {endpoint} | User: {user} | File: {filename} | Error: {e}")
            return {'error': str(e)}



    def get(self, endpoint: str, params: dict = None, headers: dict = None):
        url = f"{self.base_url}{endpoint}"
        req_headers = self.headers.copy()
        if headers:
            req_headers.update(headers)
        try:
            response = requests.get(url, params=params, headers=req_headers, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API call error: {e}")
            return None
        except ValueError as e:
            logger.error(f"JSON decode error: {e}")
            return None

    @cache_with_ttl(ttl=ManagerViewConfig.FILTERS_TTL, key_prefix='manager_view:filters')
    def get_manager_view_filters(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Get filter options for manager view (report months and categories).

        Returns:
            Dictionary with 'report_months' and 'categories' lists

        Example:
            {
                'report_months': [
                    {'value': '2025-04', 'display': 'April 2025'},
                    ...
                ],
                'categories': [
                    {'value': '', 'display': '-- All Categories --'},
                    ...
                ]
            }
        """
        return self._make_request('GET', '/api/manager-view/filters')

    def get_manager_view_data(
        self,
        report_month: str,
        category: Optional[str] = None
    ) -> Dict:
        """
        Get manager view data for specified report month and optional category.

        Args:
            report_month: Report month in YYYY-MM format (e.g., '2025-02')
            category: Optional category filter (e.g., 'amisys-onshore')

        Returns:
            Dictionary containing hierarchical capacity data

        Example:
            {
                'report_month': '2025-02',
                'months': ['2025-02', '2025-03', ...],
                'categories': [...],
                'category_name': 'Amisys Onshore' or 'All Categories'
            }

        Raises:
            ValueError: If report_month or category is invalid
            requests.exceptions.RequestException: On API request failure
        """
        params = {'report_month': report_month}
        if category:
            params['category'] = category
        return self._make_request('GET', '/api/manager-view/data', params=params)

    @cache_with_ttl(ttl=ForecastCacheConfig.DATA_TTL, key_prefix='roster')
    def get_all_roster(self, roster_type, search=None, searchable_field='', global_filter=None, limit=100, month: int = None, year: int = None):
        all_records = []
        skip = 0
        all_keys = set()
        url = '/records/'+roster_type
        while True:
            params = {
                'skip': skip,
                'limit': limit,
                'search': search,
                'searchable_field': searchable_field,
                'global_filter': global_filter
            }

            if month and year:
                params['month'] = self.month_mapper.get(month, "Invalid Month")
                params['year'] = year

            params = {k: v for k, v in params.items() if v not in [None, '', []]}

            response = self.get(url, params=params)
            if not response:
                break

            records = response.get('records', [])
            total = response.get('total', 0)

            # Collect all keys from this batch
            for rec in records:
                all_keys.update(rec.keys())

            all_records.extend(records)
            skip += limit
            if skip >= total or not records:
                break

        # Normalize each record so all have same keys
        normalized_records = []
        for rec in all_records:
            normalized = {key: rec.get(key) for key in all_keys}
            normalized_records.append(normalized)

        return normalized_records

    @cache_with_ttl(ttl=ForecastCacheConfig.DATA_TTL, key_prefix='forecast')
    def get_all_forecast_records(
        self,
        month: int,
        year: int,
        forecast_month: int,
        main_lob: str = None,
        case_type: str = None,
        search: str = None,
        searchable_field: str = '',
        global_filter: str = '',
        limit: int = 100
    ):
        """
        Fetch all forecast records with pagination.

        Args:
            month (int): Target month (e.g., 7 for July)
            year (int): Target year (e.g., 2025)
            forecast_month (int): Forecast month (e.g., 8 for August)
            main_lob (str): Main line of business
            case_type (str): Type of case
            search (str): Search term
            searchable_field (str): Specific searchable field
            global_filter (str): Global filter for records
            limit (int): Number of records per page

        Returns:
            list[dict]: List of all forecast records (normalized)
        """
        endpoint = "/records/forecast"
        all_records = []
        skip = 0
        all_keys = set()

        # Validate months
        month_name = self.month_mapper.get(month)
        # forecast_month_name = self.month_mapper.get(forecast_month)
        if not month_name or not forecast_month:
            logger.error(f"[Forecast Fetch Error] Invalid month or forecast month: {month}, {forecast_month}")
            return []

        while True:
            params = {
                'skip': skip,
                'limit': limit,
                'month': month_name,
                'year': year,
                'forecast_month': forecast_month,
                'search': search,
                'searchable_field': searchable_field,
                'global_filter': global_filter,
                'main_lob': main_lob,
                'case_type': case_type
            }

            # Remove empty/None fields
            params = {k: v for k, v in params.items() if v not in [None, '', []]}

            logger.debug(f"[Forecast Fetch] Requesting {endpoint} with params: {params}")
            response = self.get(endpoint, params=params)

            if not response:
                logger.warning(f"[Forecast Fetch Warning] No response for skip={skip}")
                break

            records = response.get('data', [])
            total = response.get('total', 0)

            for rec in records:
                all_keys.update(rec.keys())
            all_records.extend(records)

            logger.debug(f"[Forecast Fetch] Received {len(records)} records (skip={skip}, total={total})")

            skip += limit
            if skip >= total or not records:
                break

        # Normalize records to have same keys
        normalized_records = []
        for rec in all_records:
            normalized = {k: rec.get(k) for k in all_keys}
            normalized_records.append(normalized)

        logger.info(f"[Forecast Fetch Complete] Total records fetched: {len(normalized_records)}")
        return normalized_records

    def upload_roster_file(self, file_content: bytes, filename: str, user: str):
        return self._upload_file('/upload/upload_roster', file_content, filename, user)

    def upload_forecast_file(self, file_content: bytes, filename: str, user: str):
        return self._upload_file('/upload/forecast', file_content, filename, user)

    def upload_altered_forecast_file(self, file_content: bytes, filename: str, user: str):
        return self._upload_file('/upload/altered_forecast', file_content, filename, user)

    def upload_prod_team_roster_file(self, file_content: bytes, filename: str, user: str):
        """ Uploads a production team roster file"""
        return self._upload_file('/upload/prod_team_roster', file_content, filename, user)

    @cache_with_ttl(ttl=ForecastCacheConfig.SUMMARY_TTL, key_prefix='summary')
    def get_table_summary(self, summary_type: str, month: int, year: int):
        if month not in self.month_mapper:
            return {"error": f"Invalid month number: {month}"}

        month_str = self.month_mapper[month]
        url = f"{self.base_url}/table/summary/{summary_type}"
        params = {"month": month_str, "year": year}

        try:
            response = requests.get(
                url,
                params=params,
                headers={'accept': 'text/html'},  # HTML response expected
                timeout=self.timeout
            )

            # Handle 400 and 404 with JSON response expected
            if response.status_code in (400, 404):
                try:
                    error_detail = response.json().get('detail', 'Unknown error')
                except Exception:
                    error_detail = response.text or 'Unknown error'
                logger.error(f"[Fetch Error] {url} Detail: {error_detail}")
                return {"error": error_detail}

            response.raise_for_status()
            return response.text  # On success: HTML table

        except requests.RequestException as e:
            # Other network or HTTP errors
            logger.exception(f"[Fetch Error - Exception] {url} | Error: {e}")
            return {"error": str(e)}

    def get_all_record_history(self, skip=0, limit=100):
        """
        Fetch paginated record history from `/record_history/all` endpoint.

        Args:
            skip (int): Number of records to skip (pagination offset)
            limit (int): Number of records to return

        Returns:
            dict or None: API JSON response with record history
        """
        params = {
            'skip': skip,
            'limit': limit
        }

        return self.get("/record_history/all", params=params)
    
    def get_roster_page(self, skip=0, limit=10, search=None, searchable_field='', global_filter=None):
        params = {
            'skip': skip,
            'limit': limit,
            'search': search,
            'searchable_field': searchable_field,
            'global_filter': global_filter,
        }
        params = {k: v for k, v in params.items() if v not in [None, '', []]}

        response = self.get("/records/roster", params=params)
        if not response:
            return None  # or raise exception

        records = response.get('records', [])
        if not records:
            return response  # No records, just return as is

        # Collect all keys in this batch
        all_keys = set()
        for rec in records:
            all_keys.update(rec.keys())

        # Normalize each record so all have same keys
        normalized_records = []
        for rec in records:
            normalized = {key: rec.get(key) for key in all_keys}
            normalized_records.append(normalized)

        # Replace records with normalized ones before returning
        response['records'] = normalized_records
        return response


    def download_file_stream(self, file_type: str, month: int, year: int):
        """
        Streams a file download from the API and returns an in-memory buffer and filename.

        Args:
            file_type (str): Type of file to download (e.g., 'roster', 'forecast').
            month (int): Month for which the file is requested.
            year (int): Year for which the file is requested.

        Returns:
            Tuple[BytesIO, str] or (None, None) if error
        """
        endpoint = f"/download_file/{file_type}"
        params = {"month": self.month_mapper.get(month, "Invalid Month"), "year": year}

        try:
            response = requests.get(f"{self.base_url}{endpoint}", params=params, stream=True, timeout=(30,300))
            # if response.status_code == 404:
            #     logger.error(f"Download error: File not found for {file_type}, month={month}, year={year}")
            #     raise FileNotFoundError(f"File not found for {file_type}, month={month}, year={year}")
            response.raise_for_status()

            filename = f"{file_type}.xlsx"
            file_buffer = BytesIO(response.content)
            file_buffer.seek(0)

            return file_buffer, filename

        except requests.RequestException as e:
            logger.error(f"Download error: {e}")
            return None, None

    @cache_with_ttl(ttl=ForecastCacheConfig.SCHEMA_TTL, key_prefix='schema:roster')
    def get_roster_model_schema(self, roster_type:str, month: int, year:int):
        """
        Fetch the roster model schema for the given month and year.

        Args:
            month (int): Numeric month (1–12)
            year (int): Four-digit year

        Returns:
            dict or None: API response as dictionary or None on failure
        """
        endpoint = "/model_schema/"+roster_type
        month_name = self.month_mapper.get(month)

        if not month_name:
            logger.error(f"[Schema Fetch Error] Invalid month provided: {month}")
            return {'error': f"Invalid month number: {month}"}

        params = {
            'month': month_name,
            'year': year
        }

        logger.debug(f"[Schema Fetch] Calling {endpoint} with params: {params}")

        response = self.get(endpoint, params=params)

        if response is None:
            logger.error(f"[Schema Fetch Error] No response from {endpoint} | Params: {params}")
            return {'error': 'No response from server'}

        logger.debug(f"[Schema Fetch Success] Response: {response}")
        return response

    @cache_with_ttl(ttl=ForecastCacheConfig.SCHEMA_TTL, key_prefix='schema:forecast')
    def get_forecast_model_schema(self, month: int, year: int, main_lob: str = None, case_type: str = None):
        """
        Fetch the forecast model schema for the given parameters.

        Args:
            month (int): Numeric month (1–12)
            year (int): Four-digit year
            main_lob (str, optional): Line of business (e.g., "Amisys Medicaid DOMESTIC")
            case_type (str, optional): Type of case (can be 'null' or None)

        Returns:
            dict or None: API response as dictionary or None on failure
        """
        endpoint = "/model_schema/forecast"
        month_name = self.month_mapper.get(month)

        if not month_name:
            logger.error(f"[Schema Fetch Error] Invalid month provided: {month}")
            return {'error': f"Invalid month number: {month}"}

        # Prepare query parameters
        params = {
            'month': month_name,
            'year': year
        }

        if main_lob:
            params['main_lob'] = main_lob
        if case_type:  # Avoid adding 'null' as a string unless explicitly passed
            if case_type.lower() != "null":
                params['case_type'] = case_type

        logger.debug(f"[Schema Fetch] Calling {endpoint} with params: {params}")

        response = self.get(endpoint, params=params)

        if response is None:
            logger.error(f"[Schema Fetch Error] No response from {endpoint} | Params: {params}")
            return {'error': 'No response from server'}

        logger.debug(f"[Schema Fetch Success] Response: {response}")
        return response

    def get_month_and_year_for_dropdown_options(self):
        """
        Fetch available months and years for dropdowns.

        Returns:
            dict or None: API response as dictionary or None on failure
        """
        endpoint = "/metadata/months_years"
        response = self.get(endpoint)
        data = response.get('data', {}) if response else {}
        if response is None:
            logger.error(f"[Dropdown Fetch Error] No response from {endpoint}")
            return {'error': 'No response from server'}

        logger.debug(f"[Dropdown Fetch Success] Response: {response}")
        return data

    @cache_with_ttl(ttl=ForecastCacheConfig.CASCADE_TTL, key_prefix='cascade:years')
    def get_forecast_filter_years(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Get available years for forecast filter dropdowns.

        Returns:
            Dictionary with 'years' list

        Example:
            {
                'years': [
                    {'value': '2025', 'display': '2025'},
                    {'value': '2024', 'display': '2024'}
                ]
            }
        """
        return self._make_request('GET', '/forecast/filter-years')

    @cache_with_ttl(ttl=ForecastCacheConfig.CASCADE_TTL, key_prefix='cascade:months')
    def get_forecast_months_for_year(self, year: int) -> List[Dict[str, str]]:
        """
        Get available months for the selected year.

        Args:
            year: Selected year (e.g., 2025)

        Returns:
            List of month options with value and display

        Example:
            [
                {'value': '1', 'display': 'January'},
                {'value': '2', 'display': 'February'},
                ...
            ]
        """
        return self._make_request('GET', f'/forecast/months/{year}')

    @cache_with_ttl(ttl=ForecastCacheConfig.CASCADE_TTL, key_prefix='cascade:platforms')
    def get_forecast_platforms(self, year: int, month: int) -> List[Dict[str, str]]:
        """
        Get available platforms (formerly boc) for selected year and month.

        Args:
            year: Selected year
            month: Selected month (1-12)

        Returns:
            List of platform options

        Example:
            [
                {'value': 'amisys', 'display': 'Amisys'},
                {'value': 'facets', 'display': 'Facets'}
            ]
        """
        params = {'year': year, 'month': month}
        return self._make_request('GET', '/forecast/platforms', params=params)

    @cache_with_ttl(ttl=ForecastCacheConfig.CASCADE_TTL, key_prefix='cascade:markets')
    def get_forecast_markets(
        self,
        year: int,
        month: int,
        platform: str
    ) -> List[Dict[str, str]]:
        """
        Get available markets (formerly insurance_type) for selected platform.

        Args:
            year: Selected year
            month: Selected month
            platform: Selected platform

        Returns:
            List of market options filtered by platform

        Example:
            [
                {'value': 'medicaid', 'display': 'Medicaid'},
                {'value': 'medicare', 'display': 'Medicare'}
            ]
        """
        params = {'year': year, 'month': month, 'platform': platform}
        return self._make_request('GET', '/forecast/markets', params=params)

    @cache_with_ttl(ttl=ForecastCacheConfig.CASCADE_TTL, key_prefix='cascade:localities')
    def get_forecast_localities(
        self,
        year: int,
        month: int,
        platform: str,
        market: str
    ) -> List[Dict[str, str]]:
        """
        Get available localities for selected platform and market.

        Args:
            year: Selected year
            month: Selected month
            platform: Selected platform
            market: Selected market

        Returns:
            List of locality options (includes 'All' since optional)

        Example:
            [
                {'value': '', 'display': '-- All Localities --'},
                {'value': 'domestic', 'display': 'Domestic'},
                {'value': 'offshore', 'display': 'Offshore'}
            ]
        """
        params = {'year': year, 'month': month, 'platform': platform, 'market': market}
        return self._make_request('GET', '/forecast/localities', params=params)

    @cache_with_ttl(ttl=ForecastCacheConfig.CASCADE_TTL, key_prefix='cascade:worktypes')
    def get_forecast_worktypes(
        self,
        year: int,
        month: int,
        platform: str,
        market: str,
        locality: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Get available worktypes (formerly process) for selected filters.

        Args:
            year: Selected year
            month: Selected month
            platform: Selected platform
            market: Selected market
            locality: Optional selected locality

        Returns:
            List of worktype options

        Example:
            [
                {'value': 'claims', 'display': 'Claims Processing'},
                {'value': 'enrollment', 'display': 'Enrollment'}
            ]
        """
        params = {
            'year': year,
            'month': month,
            'platform': platform,
            'market': market
        }
        if locality:
            params['locality'] = locality
        return self._make_request('GET', '/forecast/worktypes', params=params)

    # ============================================================================
    # Execution Monitoring Methods
    # ============================================================================

    @cache_with_ttl(ttl=30, key_prefix='execution_list')
    def get_executions(
        self,
        month: Optional[str] = None,
        year: Optional[int] = None,
        status: Optional[List[str]] = None,
        uploaded_by: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict:
        """
        Get list of allocation executions with filters and pagination.

        Args:
            month: Filter by month name (e.g., "January")
            year: Filter by year (e.g., 2025)
            status: List of status values to filter by
            uploaded_by: Filter by username
            limit: Max records per page (default: 50)
            offset: Pagination offset (default: 0)

        Returns:
            Dictionary with execution list and pagination info

        Example:
            {
                'success': True,
                'data': [...],
                'pagination': {
                    'total': 150,
                    'limit': 50,
                    'offset': 0,
                    'count': 50,
                    'has_more': True
                }
            }
        """
        endpoint = '/api/allocation/executions'
        params = {
            'limit': limit,
            'offset': offset
        }

        if month:
            params['month'] = month
        if year:
            params['year'] = year
        if uploaded_by:
            params['uploaded_by'] = uploaded_by
        if status and isinstance(status, list):
            # For multiple status values, use the same param key multiple times
            params['status'] = status

        try:
            logger.debug(f"[Execution List] Fetching with params: {params}")
            response = self._make_request('GET', endpoint, params=params)
            logger.info(f"[Execution List] Fetched {len(response.get('data', []))} executions")
            return response

        except requests.exceptions.RequestException as e:
            logger.error(f"[Execution List Error] Failed to fetch executions: {e}")
            raise

    def get_execution_details(self, execution_id: str) -> Dict:
        """
        Get detailed information about a specific execution with dynamic caching.

        This method uses dynamic cache TTL based on execution status:
        - IN_PROGRESS: 5 seconds (near-real-time updates)
        - Completed statuses: 1 hour (immutable data)

        Args:
            execution_id: UUID of the execution

        Returns:
            Dictionary with detailed execution information

        Example:
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
                }
            }
        """

        endpoint = f'/api/allocation/executions/{execution_id}'

        try:
            logger.debug(f"[Execution Details] Fetching for ID: {execution_id}")

            # First fetch to check status
            response = self._make_request('GET', endpoint)
            status = response.get('data', {}).get('status', 'SUCCESS')

            # Determine TTL based on status
            if status == 'IN_PROGRESS':
                ttl = ExecutionMonitoringConfig.DETAIL_CACHE_TTL_IN_PROGRESS
            else:
                ttl = ExecutionMonitoringConfig.DETAIL_CACHE_TTL_COMPLETED

            logger.debug(f"[Execution Details] Status: {status}, Cache TTL: {ttl}s")

            # Apply dynamic caching
            @cache_with_ttl(ttl=ttl, key_prefix=f'execution_detail:{execution_id}')
            def _get_cached_details():
                return response

            cached_response = _get_cached_details()
            logger.info(f"[Execution Details] Fetched execution {execution_id}")
            return cached_response

        except requests.exceptions.RequestException as e:
            logger.error(f"[Execution Details Error] Failed to fetch execution {execution_id}: {e}")
            raise

    @cache_with_ttl(ttl=60, key_prefix='execution_kpi')
    def get_execution_kpis(
        self,
        month: Optional[str] = None,
        year: Optional[int] = None,
        status: Optional[List[str]] = None,
        uploaded_by: Optional[str] = None
    ) -> Dict:
        """
        Get KPI metrics for executions with optional filters.

        Args:
            month: Filter by month name
            year: Filter by year
            status: List of status values to filter by
            uploaded_by: Filter by username

        Returns:
            Dictionary with KPI metrics

        Example:
            {
                'success': True,
                'data': {
                    'total_executions': 150,
                    'success_rate': 0.85,
                    'average_duration_seconds': 320.5,
                    'failed_count': 12,
                    'partial_success_count': 8,
                    'in_progress_count': 2,
                    'pending_count': 3,
                    'success_count': 125,
                    'total_records_processed': 187500,
                    'total_records_failed': 9375
                },
                'timestamp': '2025-01-15T14:30:00Z'
            }
        """
        endpoint = '/api/allocation/executions_kpi'
        params = {}

        if month:
            params['month'] = month
        if year:
            params['year'] = year
        if uploaded_by:
            params['uploaded_by'] = uploaded_by
        if status and isinstance(status, list):
            params['status'] = status

        try:
            logger.debug(f"[Execution KPIs] Fetching with params: {params}")
            response = self._make_request('GET', endpoint, params=params)
            logger.info(f"[Execution KPIs] Fetched successfully")
            return response

        except requests.exceptions.RequestException as e:
            logger.error(f"[Execution KPIs Error] Failed to fetch KPIs: {e}")
            raise

    def download_execution_report(
        self,
        execution_id: str,
        report_type: str
    ):
        """
        Download Excel report for a specific execution.

        NO CACHING - Always fetch fresh file stream.

        Args:
            execution_id: UUID of the execution
            report_type: One of 'bucket_summary', 'bucket_after_allocation', 'roster_allotment'

        Returns:
            requests.Response object with streaming content

        Raises:
            ValueError: If report_type is invalid
            requests.exceptions.RequestException: On download failure

        Example:
            response = client.download_execution_report(exec_id, 'bucket_summary')
            # Stream response content to file or browser
        """
        # Map report types to endpoints
        endpoint_map = {
            'bucket_summary': f'/api/allocation/executions/{execution_id}/reports/bucket_summary',
            'bucket_after_allocation': f'/api/allocation/executions/{execution_id}/reports/bucket_after_allocation',
            'roster_allotment': f'/api/allocation/executions/{execution_id}/reports/roster_allotment'
        }

        endpoint = endpoint_map.get(report_type)
        if not endpoint:
            raise ValueError(
                f"Invalid report_type: {report_type}. "
                f"Must be one of: {list(endpoint_map.keys())}"
            )

        url = f"{self.base_url}{endpoint}"

        try:
            logger.info(f"[Download Report] Starting download: {report_type} for {execution_id}")

            # Use longer timeout for file downloads
            timeout = ExecutionMonitoringConfig.DOWNLOAD_TIMEOUT

            # Stream the response
            response = self.session.get(
                url,
                stream=True,
                timeout=timeout,
                headers=self.headers
            )
            response.raise_for_status()

            logger.info(f"[Download Report] Successfully initiated download: {report_type}")
            return response

        except requests.exceptions.Timeout:
            logger.error(f"[Download Report Timeout] {report_type} for {execution_id} after {timeout}s")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"[Download Report HTTP Error] {e.response.status_code}: {report_type} for {execution_id}")
            raise
        except Exception as e:
            logger.error(f"[Download Report Error] {report_type} for {execution_id}: {str(e)}")
            raise

    # ============================================================
    # EDIT VIEW API METHODS
    # ============================================================

    @cache_with_ttl(ttl=EditViewConfig.ALLOCATION_REPORTS_TTL, key_prefix='edit_view:reports')
    def get_allocation_reports(self) -> Dict:
        """
        Get available allocation reports for dropdown.

        Returns:
            Dictionary with report options:
            {
                'success': True,
                'data': [{'value': '2025-04', 'display': 'April 2025'}, ...],
                'total': 15
            }

        Example:
            >>> client = get_api_client()
            >>> reports = client.get_allocation_reports()
            >>> len(reports['data'])
            15
        """
        endpoint = "/api/allocation-reports"
        response = self._make_request('GET', endpoint)
        return response

    @cache_with_ttl(ttl=EditViewConfig.PREVIEW_CACHE_TTL, key_prefix='edit_view:preview')
    def get_bench_allocation_preview(self, month: str, year: int) -> Dict:
        """
        Calculate bench allocation preview (modified records only).

        IMPORTANT: Backend MUST follow the standardized format in PREVIEW_RESPONSE_STANDARD.md

        Standard Response Format (CURRENT - with nested months):
        {
            'success': True,
            'months': {                              // Top-level month index mapping
                'month1': 'Jun-25',
                'month2': 'Jul-25',
                'month3': 'Aug-25',
                'month4': 'Sep-25',
                'month5': 'Oct-25',
                'month6': 'Nov-25'
            },
            'total_modified': 15,
            'modified_records': [
                {
                    'main_lob': 'Medicaid',
                    'state': 'MO',
                    'case_type': 'Appeals',
                    'target_cph': 100,                // Integer values
                    'target_cph_change': 5,
                    'modified_fields': ['target_cph', 'Jun-25.forecast', 'Jun-25.fte_req', ...],
                    'months': {                       // Month data NESTED under 'months' object
                        'Jun-25': {
                            'forecast': 12500,        // Integer values
                            'fte_req': 11,
                            'fte_avail': 8,
                            'capacity': 400,
                            'forecast_change': 0,     // Always included
                            'fte_req_change': 2,
                            'fte_avail_change': 1,
                            'capacity_change': 50
                        }
                    }
                }
            ],
            'summary': {'total_fte_change': 45, 'total_capacity_change': 2250},
            'message': None
        }

        NOTE: When sending to update endpoint, months are flattened (see update_bench_allocation)

        Args:
            month: Month name (e.g., 'April')
            year: Year (e.g., 2025)

        Returns:
            Dictionary with modified records following standardized format

        Example:
            >>> client = get_api_client()
            >>> preview = client.get_bench_allocation_preview('April', 2025)
            >>> preview['total_modified']
            15
        """
        endpoint = "/api/bench-allocation/preview"
        data = {'month': month, 'year': year}
        response = self._make_request('POST', endpoint, data=data)
        return response

    def update_bench_allocation(
        self,
        month: str,
        year: int,
        months: dict,
        modified_records: list,
        user_notes: str
    ) -> Dict:
        """
        Save bench allocation changes (NO CACHE - write operation).

        IMPORTANT: Send the FULL record structure from preview response as per API spec.
        - Input: Records with nested 'months' object (from preview response)
        - Output: Send complete structure to backend (API spec Section 3)
        - Backend expects: Full nested structure with months mapping

        Args:
            month: Month name (e.g., 'April')
            year: Year (e.g., 2025)
            months: Month index mapping (month1-month6 to labels). Required for backend processing.
            modified_records: List of modified record dictionaries (with nested 'months' structure)
            user_notes: User-provided description

        Returns:
            Success response:
            {
                'success': True,
                'message': 'Bench allocation updated successfully',
                'records_updated': 15,
                'history_log_id': '550e8400-e29b-41d4-a716-446655440000'
            }

        Example:
            >>> client = get_api_client()
            >>> months_map = {'month1': 'Jun-25', 'month2': 'Jul-25', ...}
            >>> records_with_nested_months = [{'main_lob': 'Amisys', 'months': {'Jun-25': {...}}}]
            >>> response = client.update_bench_allocation(
            ...     'April', 2025, months_map, records_with_nested_months, 'Allocated bench capacity'
            ... )
            >>> response['success']
            True
            >>> response['history_log_id']
            '550e8400-e29b-41d4-a716-446655440000'
        """
        # Send FULL structure as per API spec - DO NOT transform
        # API spec Section 3: "Send the FULL record structure from the preview response"
        # Backend handles the transformation internally
        endpoint = "/api/bench-allocation/update"
        data = {
            'month': month,
            'year': year,
            'months': months,
            'modified_records': modified_records,  # Send as-is from preview
            'user_notes': user_notes
        }
        response = self._make_request('POST', endpoint, data=data)
        return response

    # ============================================================
    # TARGET CPH UPDATE METHODS
    # ============================================================

    @cache_with_ttl(ttl=900, key_prefix='cph_data')  # 15 minutes
    def get_target_cph_data(self, month: str, year: int) -> Dict:
        """
        Get CPH records for editing in Target CPH tab.

        Args:
            month: Month name (e.g., 'April')
            year: Year (e.g., 2025)

        Returns:
            Dictionary with CPH records:
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
                'total': 12
            }

        Example:
            >>> client = get_api_client()
            >>> data = client.get_target_cph_data('April', 2025)
            >>> data['total']
            12
        """
        endpoint = "/api/edit-view/target-cph/data/"
        params = {'month': month, 'year': year}
        response = self._make_request('GET', endpoint, params=params)
        return response

    @cache_with_ttl(ttl=300, key_prefix='cph_preview')  # 5 minutes
    def get_target_cph_preview(
        self,
        month: str,
        year: int,
        modified_records: list
    ) -> Dict:
        """
        Calculate forecast impact of CPH changes (preview).

        IMPORTANT: Backend MUST follow the SAME standardized format as bench allocation
        (see PREVIEW_RESPONSE_STANDARD.md)

        Standard Response Format (CURRENT - IDENTICAL to bench allocation with nested months):
        {
            'success': True,
            'months': {                              // Top-level month index mapping
                'month1': 'Jun-25',
                'month2': 'Jul-25',
                'month3': 'Aug-25',
                'month4': 'Sep-25',
                'month5': 'Oct-25',
                'month6': 'Nov-25'
            },
            'total_modified': 15,
            'modified_records': [
                {
                    'main_lob': 'Medicaid',
                    'state': 'MO',
                    'case_type': 'Appeals',
                    'case_id': 'CASE-123',           // Include for CPH preview (differs from bench)
                    'target_cph': 50,                // Include for CPH preview
                    'target_cph_change': 5,
                    'modified_fields': ['target_cph', 'Jun-25.forecast', 'Jun-25.fte_req', ...],
                    'months': {                      // Month data NESTED under 'months' object
                        'Jun-25': {
                            'forecast': 12500,       // Integer values
                            'fte_req': 11,
                            'fte_avail': 8,
                            'capacity': 400,
                            'forecast_change': 0,    // Always included
                            'fte_req_change': 2,
                            'fte_avail_change': 1,
                            'capacity_change': 50
                        }
                    }
                }
            ],
            'summary': {'total_fte_change': 45, 'total_capacity_change': 2250},
            'message': None
        }

        Args:
            month: Month name (e.g., 'April')
            year: Year (e.g., 2025)
            modified_records: List of modified CPH records

        Returns:
            Dictionary with forecast impact using SAME structure as bench allocation

        Example:
            >>> client = get_api_client()
            >>> modified = [{'id': 'cph_1', 'lob': '...', 'case_type': '...', 'target_cph': 50, 'modified_target_cph': 52}]
            >>> preview = client.get_target_cph_preview('April', 2025, modified)
            >>> preview['total_modified']
            15
        """
        endpoint = "/api/edit-view/target-cph/preview/"
        data = {'month': month, 'year': year, 'modified_records': modified_records}
        response = self._make_request('POST', endpoint, data=data)
        return response

    def submit_target_cph_update(
        self,
        month: str,
        year: int,
        months: dict,
        modified_records: list,
        user_notes: str
    ) -> Dict:
        """
        Save CPH changes (NO CACHE - write operation).

        IMPORTANT: Send FULL structure as per API spec Section 9.
        CPH update uses ModifiedForecastRecord format (same as bench allocation).
        Each record includes:
        - target_cph (float): NEW CPH value
        - target_cph_change (float): Delta from original
        - Nested months object with forecast impact data (integers)
        - modified_fields array (includes "target_cph" + month fields)

        Args:
            month: Month name (e.g., 'April')
            year: Year (e.g., 2025)
            months: Month index mapping (month1-month6 to labels)
            modified_records: List of ModifiedForecastRecord dicts
            user_notes: User-provided description

        Returns:
            Success response:
            {
                'success': True,
                'message': 'CPH updated successfully',
                'cph_changes_applied': 5,
                'forecast_rows_affected': 15,
                'history_log_id': 'uuid-string'
            }

        Example:
            >>> client = get_api_client()
            >>> months_map = {'month1': 'Jun-25', 'month2': 'Jul-25', ...}
            >>> response = client.submit_target_cph_update(
            ...     'April', 2025, months_map, [...], 'Increased CPH for high-volume LOBs'
            ... )
            >>> response['success']
            True
        """
        # Send FULL structure as per API spec Section 9 - DO NOT transform
        # API spec: "Send the FULL record structure from the preview response"
        # Backend handles the transformation internally
        endpoint = "/api/edit-view/target-cph/update/"
        data = {
            'month': month,
            'year': year,
            'months': months,  # Required top-level months mapping
            'modified_records': modified_records,  # Send as-is from preview
            'user_notes': user_notes
        }
        timeout = 60  # Update timeout
        response = self._make_request('POST', endpoint, data=data, timeout=timeout)
    
        # Clear CPH caches after successful update
        try:
            from centene_forecast_app.app_utils.cache_utils import delete_pattern

            # Clear CPH data cache (get_target_cph_data)
            cph_data_cleared = delete_pattern('cph_data:*')

            # Clear CPH preview cache (get_target_cph_preview)
            cph_preview_cleared = delete_pattern('cph_preview:*')

            logger.info(
                f"[CPH Update] Cleared {cph_data_cleared} CPH data cache entries "
                f"and {cph_preview_cleared} CPH preview cache entries"
            )
        except Exception as e:
            logger.warning(f"[CPH Update] Failed to clear CPH caches: {e}")

        return response

    @cache_with_ttl(ttl= EditViewConfig.HISTORY_CACHE_TTL, key_prefix='edit_view:history')
    def get_history_log(
        self,
        month: str = None,
        year: int = None,
        page: int = 1,
        limit: int = 25,
        change_types: list = None
    ) -> Dict:
        """
        Get history log entries with pagination and filtering.

        Args:
            month: Optional month filter (e.g., 'April')
            year: Optional year filter (e.g., 2025)
            page: Page number (default: 1)
            limit: Records per page (default: 25)
            change_types: Optional list of change types to filter by

        Returns:
            Dictionary with history entries (flat pagination per API spec):
            {
                'success': True,
                'data': [
                    {
                        'history_log_id': '550e8400-e29b-41d4-a716-446655440000',
                        'change_type': 'Bench Allocation',
                        'month': 'April',
                        'year': 2025,
                        'created_at': '2025-04-15T14:30:00',
                        'user': 'system',
                        'user_notes': 'Allocated excess bench capacity for Q2',
                        'records_modified': 15,
                        'summary_data': {...}
                    }
                ],
                'total': 127,
                'page': 1,
                'limit': 25,
                'has_more': True
            }

        Example:
            >>> client = get_api_client()
            >>> history = client.get_history_log(month='April', year=2025, page=1, change_types=['Bench Allocation'])
            >>> len(history['data'])
            25
            >>> history['total']
            127
        """
        endpoint = "/api/history-log"
        params = {'page': page, 'limit': limit}
        if month:
            params['month'] = month
        if year:
            params['year'] = year
        if change_types:
            params['change_types'] = change_types
        params = {k: v for k, v in params.items() if v is not None}
        response = self._make_request('GET', endpoint, params=params)
        return response

    def download_history_excel(self, history_log_id: str) -> bytes:
        """
        Download Excel file for history entry (NO CACHE - file download).

        Args:
            history_log_id: UUID of history log entry

        Returns:
            Excel file bytes

        Raises:
            requests.exceptions.RequestException: On download failure

        Example:
            >>> client = get_api_client()
            >>> excel_bytes = client.download_history_excel('uuid-123')
            >>> len(excel_bytes) > 0
            True
        """
        # TODO: Replace with actual API call when endpoint is ready
        endpoint = f"/api/history-log/{history_log_id}/download"
        from core.config import EditViewConfig
        timeout = EditViewConfig.DOWNLOAD_TIMEOUT_SECONDS
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url, stream=True, timeout=timeout, headers=self.headers)
        response.raise_for_status()
        excel_bytes = response.content
        return excel_bytes

    @cache_with_ttl(ttl=EditViewConfig.CHANGE_TYPES_TTL, key_prefix='edit_view:change_types')
    def get_available_change_types(self) -> Dict:
        """
        Get available change types with dynamic colors for history log.

        Returns:
            Dictionary with change type options:
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
            >>> client = get_api_client()
            >>> change_types = client.get_available_change_types()
            >>> len(change_types['data'])
            10
        """
        # TODO: Replace with actual API call when endpoint is ready
        # endpoint = "/api/edit-view/change-types"
        # return self._make_request('GET', endpoint)

        # MOCK: Using mock change types data for now
        return get_available_change_types()

    # ============================================================
    # FORECAST REALLOCATION API METHODS
    # ============================================================

    @cache_with_ttl(ttl=300, key_prefix='reallocation:filters')
    def get_reallocation_filter_options(self, month: str, year: int) -> Dict:
        """
        Get available filter options (LOBs, States, Case Types) for forecast reallocation.

        NOTE: This endpoint is DEPRECATED. Filter options are now extracted client-side
        from the loaded data. This method remains for backward compatibility.

        Args:
            month: Month name (e.g., 'April')
            year: Year (e.g., 2025)

        Returns:
            Dictionary with filter options:
            {
                'success': True,
                'main_lobs': ['Medicaid', 'Medicare', ...],
                'states': ['MO', 'TX', 'FL', ...],
                'case_types': ['Appeals', 'Claims', ...]
            }

        Example:
            >>> client = get_api_client()
            >>> filters = client.get_reallocation_filter_options('April', 2025)
            >>> len(filters['main_lobs'])
            5
        """
        endpoint = "/api/edit-view/forecast-reallocation/filters/"
        params = {'month': month, 'year': year}
        logger.debug(f"[Reallocation Filters] Fetching for {month} {year}")
        response = self._make_request('GET', endpoint, params=params)
        logger.info(f"[Reallocation Filters] Retrieved filter options for {month} {year}")
        return response

    @cache_with_ttl(ttl=900, key_prefix='reallocation:data')
    def get_reallocation_data(
        self,
        month: str,
        year: int,
        main_lobs: Optional[List[str]] = None,
        case_types: Optional[List[str]] = None,
        states: Optional[List[str]] = None
    ) -> Dict:
        """
        Get editable forecast records for reallocation.

        Note: The typical workflow loads ALL records without filters. Filtering
        is done client-side after data is loaded (load-then-filter pattern).

        Args:
            month: Month name (e.g., 'April')
            year: Year (e.g., 2025)
            main_lobs: Optional list of Main LOBs to filter (typically not used)
            case_types: Optional list of Case Types to filter (typically not used)
            states: Optional list of States to filter (typically not used)

        Returns:
            Dictionary with forecast records:
            {
                'success': True,
                'months': {'month1': 'Apr-25', ..., 'month6': 'Sep-25'},
                'data': [{
                    'case_id': 'uuid',
                    'main_lob': 'Medicaid',
                    'state': 'MO',
                    'case_type': 'Appeals',
                    'target_cph': 100.0,
                    'months': {
                        'Apr-25': {'forecast': 12500, 'fte_req': 125, 'fte_avail': 120, 'capacity': 12000},
                        ...
                    }
                }],
                'total': 150
            }

        Example:
            >>> client = get_api_client()
            >>> data = client.get_reallocation_data('April', 2025)
            >>> len(data['data'])
            150
        """
        endpoint = "/api/edit-view/forecast-reallocation/data/"
        params = {'month': month, 'year': year}

        # Add optional filter parameters (typically not used in load-then-filter workflow)
        if main_lobs:
            params['main_lobs[]'] = main_lobs
        if case_types:
            params['case_types[]'] = case_types
        if states:
            params['states[]'] = states

        logger.debug(f"[Reallocation Data] Fetching for {month} {year}")
        response = self._make_request('GET', endpoint, params=params)
        record_count = len(response.get('data', []))
        logger.info(f"[Reallocation Data] Retrieved {record_count} records for {month} {year}")
        return response

    def get_reallocation_preview(
        self,
        month: str,
        year: int,
        modified_records: list
    ) -> Dict:
        """
        Calculate preview with user-edited Target CPH and FTE Available values (NO CACHE).

        Backend recalculates:
        - FTE Required based on new CPH
        - Capacity based on new FTE Available and CPH

        Args:
            month: Month name (e.g., 'April')
            year: Year (e.g., 2025)
            modified_records: List of modified record dictionaries with:
                - case_id, main_lob, state, case_type
                - target_cph, target_cph_change
                - modified_fields (DOT notation array)
                - months (object with month-specific data including fte_avail_change)

        Returns:
            Dictionary with preview data:
            {
                'success': True,
                'months': {'month1': 'Apr-25', ..., 'month6': 'Sep-25'},
                'month': 'April',
                'year': 2025,
                'modified_records': [...with recalculated fte_req and capacity...],
                'total_modified': 1,
                'summary': {'total_fte_change': 10, 'total_capacity_change': 5025}
            }

        Example:
            >>> client = get_api_client()
            >>> preview = client.get_reallocation_preview('April', 2025, modified_records)
            >>> preview['total_modified']
            1
        """
        endpoint = "/api/edit-view/forecast-reallocation/preview/"
        data = {
            'month': month,
            'year': year,
            'modified_records': modified_records
        }
        logger.debug(f"[Reallocation Preview] Calculating for {month} {year} with {len(modified_records)} records")
        response = self._make_request('POST', endpoint, data=data, timeout=EditViewConfig.PREVIEW_TIMEOUT)
        total_modified = response.get('total_modified', 0)
        logger.info(f"[Reallocation Preview] Preview calculated: {total_modified} records affected")
        return response

    def submit_reallocation_update(
        self,
        month: str,
        year: int,
        months: dict,
        modified_records: list,
        user_notes: str
    ) -> Dict:
        """
        Submit and save reallocation changes (NO CACHE - write operation).

        Creates a history log entry with change type 'Forecast Reallocation'.

        Args:
            month: Month name (e.g., 'April')
            year: Year (e.g., 2025)
            months: Month index mapping (month1-month6 to labels) - REQUIRED
            modified_records: List of modified record dictionaries from preview response
                - Must include: case_id, main_lob, state, case_type
                - Must include: target_cph, target_cph_change, modified_fields
                - Must include: months object with all 6 months and *_change fields
            user_notes: User-provided description (required, max 500 chars)

        Returns:
            Success response:
            {
                'success': True,
                'message': 'Forecast reallocation updated successfully',
                'records_updated': 1,
                'history_log_id': 'uuid-string'
            }

        Example:
            >>> client = get_api_client()
            >>> months_map = {'month1': 'Apr-25', 'month2': 'May-25', ...}
            >>> response = client.submit_reallocation_update(
            ...     'April', 2025, months_map, modified_records, 'Reallocated FTE for Q2'
            ... )
            >>> response['success']
            True
        """
        endpoint = "/api/edit-view/forecast-reallocation/update/"
        data = {
            'month': month,
            'year': year,
            'months': months,
            'modified_records': modified_records,
            'user_notes': user_notes
        }
        logger.info(f"[Reallocation Update] Submitting {len(modified_records)} records for {month} {year}")
        response = self._make_request('POST', endpoint, data=data, timeout=EditViewConfig.UPDATE_TIMEOUT)

        # Clear reallocation caches after successful update
        if response.get('success'):
            try:
                from centene_forecast_app.app_utils.cache_utils import delete_pattern

                # Clear reallocation data cache
                data_cleared = delete_pattern('reallocation:data:*')

                # Clear reallocation filter cache
                filter_cleared = delete_pattern('reallocation:filters:*')

                # Also clear bench allocation preview since data changed
                bench_cleared = delete_pattern('bench_allocation:*')

                logger.info(
                    f"[Reallocation Update] Cleared {data_cleared} data cache entries, "
                    f"{filter_cleared} filter cache entries, {bench_cleared} bench allocation entries"
                )
            except Exception as e:
                logger.warning(f"[Reallocation Update] Failed to clear caches: {e}")

            records_updated = response.get('records_updated', 0)
            history_log_id = response.get('history_log_id', 'N/A')
            logger.info(f"[Reallocation Update] Success: {records_updated} records, history_log_id: {history_log_id}")

        return response

    # ============================================================
    # CONFIGURATION VIEW API METHODS
    # ============================================================

    # --- Month Configuration Methods ---

    @cache_with_ttl(ttl=ConfigurationViewConfig.LIST_CACHE_TTL, key_prefix='config:month_list')
    def get_month_configurations(
        self,
        month: Optional[str] = None,
        year: Optional[int] = None,
        work_type: Optional[str] = None
    ) -> Dict:
        """
        Get month configurations with optional filtering.

        Args:
            month: Optional month name filter (e.g., 'January')
            year: Optional year filter (e.g., 2025)
            work_type: Optional work type filter ('Domestic' or 'Global')

        Returns:
            Dictionary with configurations:
            {
                'success': True,
                'data': [...],
                'total': 50
            }
        """
        endpoint = "/api/month-config"
        params = {}

        if month:
            params['month'] = month
        if year:
            params['year'] = year
        if work_type:
            params['work_type'] = work_type

        logger.debug(f"[Month Config] Fetching with params: {params}")
        response = self._make_request('GET', endpoint, params=params)
        # Extract configurations from nested data structure
        configs = response.get('data', {}).get('configurations', []) if isinstance(response.get('data'), dict) else response.get('data', [])
        logger.info(f"[Month Config] Fetched {len(configs)} configurations")
        return response

    def create_month_configuration(self, data: Dict) -> Dict:
        """
        Create a new month configuration.

        Args:
            data: Configuration data with month, year, work_type, working_days,
                  occupancy, shrinkage, work_hours, created_by

        Returns:
            Success response with created configuration
        """
        endpoint = "/api/month-config"
        logger.info(f"[Month Config] Creating: {data.get('month')} {data.get('year')} {data.get('work_type')}")
        response = self._make_request('POST', endpoint, data=data)

        # Clear cache after successful creation
        if response.get('success', True):
            self._clear_month_config_cache()

        return response

    def bulk_create_month_configurations(
        self,
        configs: List[Dict],
        created_by: str,
        skip_validation: bool = False
    ) -> Dict:
        """
        Bulk create month configurations.

        Args:
            configs: List of configuration dictionaries
            created_by: Username creating the configs
            skip_validation: Whether to skip duplicate validation

        Returns:
            Success response with created count
        """
        endpoint = "/api/month-config/bulk"
        data = {
            'configurations': configs,
            'created_by': created_by,
            'skip_pairing_validation': skip_validation
        }
        logger.info(f"[Month Config] Bulk creating {len(configs)} configurations")
        response = self._make_request('POST', endpoint, data=data)

        # Clear cache after successful creation
        if response.get('success', True):
            self._clear_month_config_cache()

        return response

    def update_month_configuration(self, config_id: int, data: Dict) -> Dict:
        """
        Update an existing month configuration.

        Args:
            config_id: ID of the configuration to update
            data: Updated configuration data

        Returns:
            Success response with updated configuration
        """
        endpoint = f"/api/month-config/{config_id}"
        logger.info(f"[Month Config] Updating ID: {config_id}")
        response = self._make_request('PUT', endpoint, params=data)

        # Clear cache after successful update
        if response.get('success', True):
            self._clear_month_config_cache()

        return response

    def delete_month_configuration(self, config_id: int, allow_orphan: bool = False) -> Dict:
        """
        Delete a month configuration.

        Args:
            config_id: ID of the configuration to delete
            allow_orphan: Whether to allow deletion even if it creates orphan

        Returns:
            Success response or error with orphan warning
        """
        endpoint = f"/api/month-config/{config_id}"
        params = {'allow_orphan': str(allow_orphan).lower()} if allow_orphan else {}
        logger.info(f"[Month Config] Deleting ID: {config_id}, allow_orphan: {allow_orphan}")
        response = self._make_request('DELETE', endpoint, params=params)

        # Clear cache after successful deletion
        if response.get('success', True):
            self._clear_month_config_cache()

        return response

    def validate_month_configurations(self) -> Dict:
        """
        Validate month configurations for orphaned records.

        Returns:
            Validation result with orphaned records list
        """
        endpoint = "/api/month-config/validate"
        logger.info("[Month Config] Running validation check")
        response = self._make_request('GET', endpoint)
        return response

    def _clear_month_config_cache(self):
        """Clear month configuration cache after modifications."""
        try:
            from centene_forecast_app.app_utils.cache_utils import delete_pattern
            cleared = delete_pattern('config:month_list:*')
            logger.info(f"[Month Config] Cleared {cleared} cache entries")
        except Exception as e:
            logger.warning(f"[Month Config] Failed to clear cache: {e}")

    # --- Target CPH Configuration Methods ---

    @cache_with_ttl(ttl=ConfigurationViewConfig.LIST_CACHE_TTL, key_prefix='config:target_cph_list')
    def get_target_cph_configurations(
        self,
        main_lob: Optional[str] = None,
        case_type: Optional[str] = None
    ) -> Dict:
        """
        Get Target CPH configurations with optional filtering.

        Args:
            main_lob: Optional Main LOB filter
            case_type: Optional Case Type filter

        Returns:
            Dictionary with configurations:
            {
                'success': True,
                'data': [...],
                'total': 50
            }
        """
        endpoint = "/api/target-cph"
        params = {}

        if main_lob:
            params['main_lob'] = main_lob
        if case_type:
            params['case_type'] = case_type

        logger.debug(f"[Target CPH Config] Fetching with params: {params}")
        response = self._make_request('GET', endpoint, params=params)
        # Extract configurations from nested data structure
        configs = response.get('data', {}).get('configurations', []) if isinstance(response.get('data'), dict) else response.get('data', [])
        logger.info(f"[Target CPH Config] Fetched {len(configs)} configurations")
        return response

    def get_target_cph_by_id(self, config_id: int) -> Dict:
        """
        Get a specific Target CPH configuration by ID.

        Args:
            config_id: Configuration ID

        Returns:
            Configuration data or error response
        """
        endpoint = f"/api/target-cph/{config_id}"
        logger.debug(f"[Target CPH Config] Fetching ID: {config_id}")
        response = self._make_request('GET', endpoint)
        return response

    def create_target_cph_configuration(self, data: Dict) -> Dict:
        """
        Create a new Target CPH configuration.

        Args:
            data: Configuration data with main_lob, case_type, target_cph, updated_by

        Returns:
            Success response with created configuration
        """
        endpoint = "/api/target-cph"
        logger.info(f"[Target CPH Config] Creating: {data.get('main_lob')} / {data.get('case_type')}")
        response = self._make_request('POST', endpoint, data=data)

        # Clear cache after successful creation
        if response.get('success', True):
            self._clear_target_cph_config_cache()

        return response

    def bulk_create_target_cph_configurations(self, configs: List[Dict]) -> Dict:
        """
        Bulk create Target CPH configurations.

        Args:
            configs: List of configuration dictionaries

        Returns:
            Success response with created count
        """
        endpoint = "/api/target-cph/bulk"
        data = {'configurations': configs}
        logger.info(f"[Target CPH Config] Bulk creating {len(configs)} configurations")
        response = self._make_request('POST', endpoint, data=data)

        # Clear cache after successful creation
        if response.get('success', True):
            self._clear_target_cph_config_cache()

        return response

    def update_target_cph_configuration(self, config_id: int, data: Dict) -> Dict:
        """
        Update an existing Target CPH configuration.

        Args:
            config_id: ID of the configuration to update
            data: Updated configuration data

        Returns:
            Success response with updated configuration
        """
        endpoint = f"/api/target-cph/{config_id}"
        logger.info(f"[Target CPH Config] Updating ID: {config_id}")
        response = self._make_request('PUT', endpoint, data=data)

        # Clear cache after successful update
        if response.get('success', True):
            self._clear_target_cph_config_cache()

        return response

    def delete_target_cph_configuration(self, config_id: int) -> Dict:
        """
        Delete a Target CPH configuration.

        Args:
            config_id: ID of the configuration to delete

        Returns:
            Success response
        """
        endpoint = f"/api/target-cph/{config_id}"
        logger.info(f"[Target CPH Config] Deleting ID: {config_id}")
        response = self._make_request('DELETE', endpoint)

        # Clear cache after successful deletion
        if response.get('success', True):
            self._clear_target_cph_config_cache()

        return response

    @cache_with_ttl(ttl=ConfigurationViewConfig.DISTINCT_VALUES_TTL, key_prefix='config:distinct_lobs')
    def get_distinct_main_lobs(self) -> Dict:
        """
        Get distinct Main LOB values for dropdown.

        Returns:
            Dictionary with distinct values:
            {
                'success': True,
                'data': [{'value': 'LOB1', 'display': 'LOB1'}, ...],
                'total': 10
            }
        """
        endpoint = "/api/target-cph/distinct/main-lobs"
        logger.debug("[Target CPH Config] Fetching distinct Main LOBs")
        response = self._make_request('GET', endpoint)
        return response

    @cache_with_ttl(ttl=ConfigurationViewConfig.DISTINCT_VALUES_TTL, key_prefix='config:distinct_case_types')
    def get_distinct_case_types(self, main_lob: Optional[str] = None) -> Dict:
        """
        Get distinct Case Type values for dropdown.

        Args:
            main_lob: Optional Main LOB to filter case types

        Returns:
            Dictionary with distinct values
        """
        endpoint = "/api/target-cph/distinct/case-types"
        params = {'main_lob': main_lob} if main_lob else {}
        logger.debug(f"[Target CPH Config] Fetching distinct Case Types for LOB: {main_lob}")
        response = self._make_request('GET', endpoint, params=params)
        return response

    def _clear_target_cph_config_cache(self):
        """Clear Target CPH configuration cache after modifications."""
        try:
            from centene_forecast_app.app_utils.cache_utils import delete_pattern

            # Clear list cache
            list_cleared = delete_pattern('config:target_cph_list:*')

            # Clear distinct values cache
            lob_cleared = delete_pattern('config:distinct_lobs:*')
            case_type_cleared = delete_pattern('config:distinct_case_types:*')

            logger.info(
                f"[Target CPH Config] Cleared cache - list: {list_cleared}, "
                f"lobs: {lob_cleared}, case_types: {case_type_cleared}"
            )
        except Exception as e:
            logger.warning(f"[Target CPH Config] Failed to clear cache: {e}")

    def close(self):
        """Close the session and cleanup resources."""
        self.session.close()
        logger.info("APIClient session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        """Context manager exit."""
        self.close()

# Singleton instance for application-wide use
# Can be configured via Django settings
_api_client_instance: Optional[APIClient] = None


def get_api_client() -> APIClient:
    """
    Get or create singleton APIClient instance.

    Returns:
        Configured APIClient instance

    Usage:
        from apps.reports.repository import get_api_client

        client = get_api_client()
        data = client.get_manager_view_data('2025-02')
    """
    global _api_client_instance

    if _api_client_instance is None:

        base_url = getattr(settings, 'API_BASE_URL' , "http://127.0.0.1:8888")
        timeout = 30

        _api_client_instance = APIClient(
            base_url=base_url,
            timeout=timeout
        )
        logger.info("Created new APIClient singleton instance")

    return _api_client_instance


def reset_api_client():
    """
    Reset singleton instance (useful for testing).

    Usage:
        from apps.reports.repository import reset_api_client

        reset_api_client()  # Force recreation on next get_api_client() call
    """
    global _api_client_instance
    if _api_client_instance:
        _api_client_instance.close()
        _api_client_instance = None
        logger.info("APIClient singleton instance reset")


# Convenience wrapper functions for backward compatibility
def get_manager_view_filters() -> Dict[str, List[Dict[str, str]]]:
    """Convenience function to get manager view filters."""
    client = get_api_client()
    return client.get_manager_view_filters()


def get_manager_view_data(
    report_month: str,
    category: Optional[str] = None
) -> Dict:
    """Convenience function to get manager view data."""
    client = get_api_client()
    return client.get_manager_view_data(report_month, category)

# Forecast cascade convenience wrapper functions
def get_forecast_filter_years() -> Dict[str, List[Dict[str, str]]]:
    """Convenience function to get forecast filter years."""
    client = get_api_client()
    return client.get_forecast_filter_years()


def get_forecast_months_for_year(year: int) -> List[Dict[str, str]]:
    """Convenience function to get months for selected year."""
    client = get_api_client()
    return client.get_forecast_months_for_year(year)


def get_forecast_platforms(year: int, month: int) -> List[Dict[str, str]]:
    """Convenience function to get platforms for year/month."""
    client = get_api_client()
    return client.get_forecast_platforms(year, month)


def get_forecast_markets(
    year: int,
    month: int,
    platform: str
) -> List[Dict[str, str]]:
    """Convenience function to get markets for platform."""
    client = get_api_client()
    return client.get_forecast_markets(year, month, platform)


def get_forecast_localities(
    year: int,
    month: int,
    platform: str,
    market: str
) -> List[Dict[str, str]]:
    """Convenience function to get localities for platform/market."""
    client = get_api_client()
    return client.get_forecast_localities(year, month, platform, market)


def get_forecast_worktypes(
    year: int,
    month: int,
    platform: str,
    market: str,
    locality: Optional[str] = None
) -> List[Dict[str, str]]:
    """Convenience function to get worktypes for selected filters."""
    client = get_api_client()
    return client.get_forecast_worktypes(year, month, platform, market, locality)
