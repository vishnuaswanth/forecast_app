"""
Core Configuration Module

Business logic configuration for the application.
Separate from Django settings.py for better modularity and testability.
"""

from typing import Optional


class ManagerViewConfig:
    """
    Manager View Dashboard Configuration
    
    Controls display and calculation logic for executive capacity planning reports.
    These values can be easily migrated to database models in the future for
    per-user or per-organization customization.
    """
    
    # Display Configuration
    MONTHS_TO_DISPLAY: int = 6
    """
    Number of forecast months to display in the manager view table.
    Default: 6 months
    Range: 1-12 months
    
    Example: If report_month is "2025-02" (February 2025 report), 
    displays Feb, Mar, Apr, May, Jun, Jul (6 months)
    
    Note: Actual months displayed depend on data returned from API
    """
    
    KPI_MONTH_INDEX: int = 1
    """
    Zero-based index of which displayed month to use for KPI summary cards.
    Default: 1 (second month in the displayed range)
    
    Example: If displaying [Feb, Mar, Apr, May, Jun, Jul], 
    index 1 = March data shown in KPI cards
    
    Range: 0 to (MONTHS_TO_DISPLAY - 1)
    """
    
    MAX_HIERARCHY_DEPTH: int = 6
    """
    Maximum depth of category hierarchy tree.
    Default: 6 levels
    
    Hierarchy structure example:
    Level 1: Amisys Onshore (top-level category)
      Level 2: Manual
        Level 3: FL & GA
          Level 4: FL
            Level 5: [Optional sub-category]
                Level 6: [Optional sub-category]
    """
    

    # Dropdown configurations
    ENABLE_SEARCHABLE_DROPDOWNS: bool = True
    """
    Enable searchable dropdowns using Select2 JS library for Report Month and Category Filters.
    Allows user to type and search instead of scrolling through long lists.
    """

    REPORT_MONTH_SORT_ORDER: str = 'desc'
    """
    Sort order for Report Month dropdown.
    Options: 'asc' (oldest to newest), 'desc' (newest to oldest)
    Default: 'desc' (newest months first)
    """
    
    CATEGORY_SORT_ORDER: str = 'asc'
    """ 
    Sort order for Category dropdown.
    Options: 'asc' (A-Z), 'desc' (Z-A)
    Default: 'asc' (A-Z)
    """

    # UI Configuration
    ENABLE_EXPAND_ALL: bool = True
    """Enable 'Expand All' / 'Collapse All' buttons in table header"""
    
    ENABLE_CATEGORY_FILTER: bool = True
    """Enable category dropdown filter (if False, shows all categories always)"""
    
    DEFAULT_TABLE_COLLAPSED: bool = True
    """
    Initial table state when page loads.
    True: Only level-1 categories visible
    False: All categories expanded
    """
    
    # Performance Configuration
    CACHE_TIMEOUT_SECONDS: int = 300
    """Cache timeout for manager view data (5 minutes = 300 seconds)"""
    
    ENABLE_DATA_CACHING: bool = True # Non functional
    """Enable/disable caching of manager view data. Default: False for development"""

    FILTERS_TTL: int= 300
    """
    Cache timeout for manager view filters dropdown.
    Default: 5 minutes (300 seconds)

    Actual data fetched for display in tables.
    """
    MANAGER_DATA_TTL: int=900
    """
    Cache timeout for manager view data.
    Default: 15 minutes (900 seconds)

    Actual data fetched for display in tables.
    """
    
    # Validation Methods
    @classmethod
    def validate(cls) -> None:
        """
        Validate configuration values.
        Raises ValueError if any configuration is invalid.
        """
        # Validate MONTHS_TO_DISPLAY
        if not isinstance(cls.MONTHS_TO_DISPLAY, int):
            raise ValueError(f"MONTHS_TO_DISPLAY must be an integer, got {type(cls.MONTHS_TO_DISPLAY)}")
        
        if not (1 <= cls.MONTHS_TO_DISPLAY <= 12):
            raise ValueError(
                f"MONTHS_TO_DISPLAY must be between 1 and 12, got {cls.MONTHS_TO_DISPLAY}"
            )
        
        # Validate KPI_MONTH_INDEX
        if not isinstance(cls.KPI_MONTH_INDEX, int):
            raise ValueError(f"KPI_MONTH_INDEX must be an integer, got {type(cls.KPI_MONTH_INDEX)}")
        
        if not (0 <= cls.KPI_MONTH_INDEX < cls.MONTHS_TO_DISPLAY):
            raise ValueError(
                f"KPI_MONTH_INDEX must be between 0 and {cls.MONTHS_TO_DISPLAY - 1}, "
                f"got {cls.KPI_MONTH_INDEX}"
            )
        
        # Validate MAX_HIERARCHY_DEPTH
        if not isinstance(cls.MAX_HIERARCHY_DEPTH, int):
            raise ValueError(f"MAX_HIERARCHY_DEPTH must be an integer, got {type(cls.MAX_HIERARCHY_DEPTH)}")
        
        if not (1 <= cls.MAX_HIERARCHY_DEPTH <= 10):
            raise ValueError(
                f"MAX_HIERARCHY_DEPTH must be between 1 and 10, got {cls.MAX_HIERARCHY_DEPTH}"
            )
    
    @classmethod
    def get_months_to_display(cls, user: Optional[object] = None) -> int:
        """
        Get number of months to display.
        
        Future: Can be customized per user/organization from database.
        
        Args:
            user: Optional user object for per-user configuration
            
        Returns:
            Number of months to display
        """
        # TODO: Implement database lookup when feature is ready
        # if user and hasattr(user, 'manager_view_config'):
        #     return user.manager_view_config.months_to_display
        
        return cls.MONTHS_TO_DISPLAY
    
    @classmethod
    def get_kpi_month_index(cls, user: Optional[object] = None) -> int:
        """
        Get KPI month index.
        
        Future: Can be customized per user/organization from database.
        
        Args:
            user: Optional user object for per-user configuration
            
        Returns:
            Zero-based index for KPI month
        """
        # TODO: Implement database lookup when feature is ready
        # if user and hasattr(user, 'manager_view_config'):
        #     return user.manager_view_config.kpi_month_index
        
        return cls.KPI_MONTH_INDEX
    
    @classmethod
    def get_config_dict(cls) -> dict:
        """
        Get all configuration as a dictionary.
        Useful for passing to templates or APIs.
        
        Returns:
            Dictionary of all configuration values
        """
        return {
            'months_to_display': cls.MONTHS_TO_DISPLAY,
            'kpi_month_index': cls.KPI_MONTH_INDEX,
            'max_hierarchy_depth': cls.MAX_HIERARCHY_DEPTH,
            'enable_searchable_dropdowns': cls.ENABLE_SEARCHABLE_DROPDOWNS,
            'report_month_sort_order': cls.REPORT_MONTH_SORT_ORDER,
            'category_sort_order': cls.CATEGORY_SORT_ORDER,
            'enable_expand_all': cls.ENABLE_EXPAND_ALL,
            'enable_category_filter': cls.ENABLE_CATEGORY_FILTER,
            'default_table_collapsed': cls.DEFAULT_TABLE_COLLAPSED,
            'cache_timeout_seconds': cls.CACHE_TIMEOUT_SECONDS,
            'enable_data_caching': cls.ENABLE_DATA_CACHING,
        }


# Validate configuration on module import
try:
    ManagerViewConfig.validate()
except ValueError as e:
    raise RuntimeError(f"Invalid ManagerViewConfig: {e}")


class ForecastCacheConfig:
    """
    Forecast Data Caching Configuration

    Controls caching behavior for forecast-related data fetching operations.
    Uses Django's local memory cache for fast, lightweight caching without
    external dependencies.
    """

    # Cache TTLs (Time To Live in seconds)
    CASCADE_TTL: int = 300
    """
    Cache timeout for cascade dropdown data (years, months, platforms, etc.)
    Default: 5 minutes (300 seconds)

    These change infrequently and can be cached longer.
    """

    DATA_TTL: int = 900
    """
    Cache timeout for roster and forecast data records.
    Default: 15 minutes (900 seconds)

    Actual data fetched for display in tables.
    """

    SCHEMA_TTL: int = 900
    """
    Cache timeout for schema metadata (forecast/roster schemas).
    Default: 15 minutes (900 seconds)

    Schema definitions that describe table structures.
    """

    SUMMARY_TTL: int = 900
    """
    Cache timeout for HTML summary table responses.
    Default: 15 minutes (900 seconds)

    Pre-rendered HTML tables from backend.
    """

    ENABLE_CACHING: bool = True
    """
    Master switch to enable/disable all caching.
    Default: True

    Set to False to disable caching for debugging.
    """

    CACHE_BACKEND: str = 'default'
    """
    Django cache backend to use.
    Default: 'default' (uses settings.CACHES['default'])
    options: 'default', 'filebased'.

    For development: Uses locmem (local memory cache)
    For production: Can switch to file-based or Redis
    """

    @classmethod
    def get_config_dict(cls) -> dict:
        """
        Get all configuration as a dictionary.

        Returns:
            Dictionary of all cache configuration values
        """
        return {
            'cascade_ttl': cls.CASCADE_TTL,
            'data_ttl': cls.DATA_TTL,
            'schema_ttl': cls.SCHEMA_TTL,
            'summary_ttl': cls.SUMMARY_TTL,
            'enable_caching': cls.ENABLE_CACHING,
            'cache_backend': cls.CACHE_BACKEND,
        }

class ExecutionMonitoringConfig:
    """
    Execution Monitoring Page Configuration

    Controls display, pagination, polling, and caching behavior for the
    allocation execution monitoring dashboard.
    """

    # Pagination Configuration
    INITIAL_PAGE_SIZE: int = 100
    """
    Number of records to load on initial page load.
    Default: 100 records

    This provides data for the first 10 pages (10 items per page).
    """

    LAZY_LOAD_PAGE_SIZE: int = 100
    """
    Number of records to load in each subsequent lazy load batch.
    Default: 100 records

    Triggered when user navigates to LAZY_LOAD_TRIGGER_PAGE.
    """

    LAZY_LOAD_TRIGGER_PAGE: int = 9
    """
    Page number that triggers the next batch load.
    Default: Page 9

    When user clicks page 9, the next 100 records will be loaded automatically.
    """

    ITEMS_PER_PAGE: int = 10
    """
    Number of items to display per page in the table.
    Default: 10 items per page
    """

    # Refresh & Polling Configuration
    HERO_REFRESH_INTERVAL: int = 5000
    """
    Polling interval for hero card auto-refresh in milliseconds.
    Default: 5000ms (5 seconds)

    Only polls when latest execution status is IN_PROGRESS.
    Stops automatically when status changes to SUCCESS/FAILED/PARTIAL_SUCCESS.
    """

    POLLING_ENABLED_STATUSES: list = ['IN_PROGRESS']
    """
    Status values that trigger auto-refresh polling.
    Default: ['IN_PROGRESS']

    Hero card will only poll when the latest execution has one of these statuses.
    """

    # Cache TTL Configuration (in seconds)
    LIST_CACHE_TTL: int = 30
    """
    Cache timeout for execution list API responses.
    Default: 30 seconds

    Balances freshness with performance for frequently accessed lists.
    """

    DETAIL_CACHE_TTL_IN_PROGRESS: int = 5
    """
    Cache timeout for execution details when status is IN_PROGRESS.
    Default: 5 seconds

    Short TTL ensures near-real-time updates for active executions.
    """

    DETAIL_CACHE_TTL_COMPLETED: int = 3600
    """
    Cache timeout for execution details when status is SUCCESS/FAILED/PARTIAL_SUCCESS.
    Default: 3600 seconds (1 hour)

    Longer TTL for completed executions since data is immutable.
    """

    KPI_CACHE_TTL: int = 60
    """
    Cache timeout for KPI aggregation API responses.
    Default: 60 seconds (1 minute)

    KPIs are expensive to calculate but don't need real-time accuracy.
    """

    # Toast Notification Configuration
    TOAST_DURATION: int = 3000
    """
    Toast notification auto-hide duration in milliseconds.
    Default: 3000ms (3 seconds)
    """

    TOAST_SUCCESS_BG: str = 'bg-success'
    """Bootstrap 5 background class for success toasts"""

    TOAST_ERROR_BG: str = 'bg-danger'
    """Bootstrap 5 background class for error toasts"""

    TOAST_INFO_BG: str = 'bg-info'
    """Bootstrap 5 background class for info toasts"""

    TOAST_WARNING_BG: str = 'bg-warning'
    """Bootstrap 5 background class for warning toasts"""

    # Download Configuration
    ENABLE_DOWNLOADS: bool = True
    """
    Enable/disable download functionality for Excel reports.
    Default: True
    """

    DOWNLOAD_TIMEOUT: int = 60
    """
    Timeout for download requests in seconds.
    Default: 60 seconds

    Longer timeout since Excel file generation can be slow.
    """

    # Validation Methods
    @classmethod
    def validate(cls) -> None:
        """
        Validate configuration values.
        Raises ValueError if any configuration is invalid.
        """
        # Validate pagination
        if not isinstance(cls.INITIAL_PAGE_SIZE, int) or cls.INITIAL_PAGE_SIZE < 1:
            raise ValueError(f"INITIAL_PAGE_SIZE must be a positive integer, got {cls.INITIAL_PAGE_SIZE}")

        if not isinstance(cls.LAZY_LOAD_PAGE_SIZE, int) or cls.LAZY_LOAD_PAGE_SIZE < 1:
            raise ValueError(f"LAZY_LOAD_PAGE_SIZE must be a positive integer, got {cls.LAZY_LOAD_PAGE_SIZE}")

        if not isinstance(cls.ITEMS_PER_PAGE, int) or cls.ITEMS_PER_PAGE < 1:
            raise ValueError(f"ITEMS_PER_PAGE must be a positive integer, got {cls.ITEMS_PER_PAGE}")

        if not isinstance(cls.LAZY_LOAD_TRIGGER_PAGE, int) or cls.LAZY_LOAD_TRIGGER_PAGE < 1:
            raise ValueError(f"LAZY_LOAD_TRIGGER_PAGE must be a positive integer, got {cls.LAZY_LOAD_TRIGGER_PAGE}")

        # Validate polling
        if not isinstance(cls.HERO_REFRESH_INTERVAL, int) or cls.HERO_REFRESH_INTERVAL < 1000:
            raise ValueError(f"HERO_REFRESH_INTERVAL must be at least 1000ms, got {cls.HERO_REFRESH_INTERVAL}")

        # Validate cache TTLs
        if not isinstance(cls.LIST_CACHE_TTL, int) or cls.LIST_CACHE_TTL < 0:
            raise ValueError(f"LIST_CACHE_TTL must be non-negative, got {cls.LIST_CACHE_TTL}")

        if not isinstance(cls.KPI_CACHE_TTL, int) or cls.KPI_CACHE_TTL < 0:
            raise ValueError(f"KPI_CACHE_TTL must be non-negative, got {cls.KPI_CACHE_TTL}")

        # Validate toast duration
        if not isinstance(cls.TOAST_DURATION, int) or cls.TOAST_DURATION < 1000:
            raise ValueError(f"TOAST_DURATION must be at least 1000ms, got {cls.TOAST_DURATION}")

    @classmethod
    def get_config_dict(cls) -> dict:
        """
        Get all configuration as a dictionary.
        Useful for passing to templates or APIs.

        Returns:
            Dictionary of all configuration values
        """
        return {
            'initial_page_size': cls.INITIAL_PAGE_SIZE,
            'lazy_load_page_size': cls.LAZY_LOAD_PAGE_SIZE,
            'lazy_load_trigger_page': cls.LAZY_LOAD_TRIGGER_PAGE,
            'items_per_page': cls.ITEMS_PER_PAGE,
            'hero_refresh_interval': cls.HERO_REFRESH_INTERVAL,
            'polling_enabled_statuses': cls.POLLING_ENABLED_STATUSES,
            'list_cache_ttl': cls.LIST_CACHE_TTL,
            'detail_cache_ttl_in_progress': cls.DETAIL_CACHE_TTL_IN_PROGRESS,
            'detail_cache_ttl_completed': cls.DETAIL_CACHE_TTL_COMPLETED,
            'kpi_cache_ttl': cls.KPI_CACHE_TTL,
            'toast_duration': cls.TOAST_DURATION,
            'toast_success_bg': cls.TOAST_SUCCESS_BG,
            'toast_error_bg': cls.TOAST_ERROR_BG,
            'toast_info_bg': cls.TOAST_INFO_BG,
            'toast_warning_bg': cls.TOAST_WARNING_BG,
            'enable_downloads': cls.ENABLE_DOWNLOADS,
            'download_timeout': cls.DOWNLOAD_TIMEOUT,
        }


# Validate execution monitoring configuration on module import
try:
    ExecutionMonitoringConfig.validate()
except ValueError as e:
    raise RuntimeError(f"Invalid ExecutionMonitoringConfig: {e}")


class EditViewConfig:
    """
    Edit View Configuration

    Controls display, validation, and transaction behavior for the
    allocation forecast edit view feature.
    """

    # Preview Configuration
    PREVIEW_REFRESH_INTERVAL: int = 5000
    """
    Preview auto-refresh interval in milliseconds.
    Default: 5000ms (5 seconds)

    Used for real-time preview updates when data changes frequently.
    Set to 0 to disable auto-refresh.
    """

    MAX_ROWS_PER_BATCH: int = 100
    """
    Maximum number of rows that can be updated in a single batch.
    Default: 100 rows

    Prevents transaction timeouts and memory issues.
    """

    PREVIEW_TIMEOUT_SECONDS: int = 30
    """
    Timeout for preview generation requests in seconds.
    Default: 30 seconds

    Preview calculations can be expensive for large datasets.
    """

    # Update Configuration
    ENABLE_ATOMIC_UPDATES: bool = True
    """
    Enable atomic transaction updates (all-or-nothing).
    Default: True

    When True, if any row fails validation or update, all changes are rolled back.
    When False, partial updates are allowed (not recommended).
    """

    ROLLBACK_ON_ERROR: bool = True
    """
    Automatically rollback all changes if any error occurs.
    Default: True

    Should always be True for production to maintain data consistency.
    """

    UPDATE_TIMEOUT_SECONDS: int = 60
    """
    Timeout for update requests in seconds.
    Default: 60 seconds

    Batch updates can take time, especially with backend validation.
    """

    # History Configuration
    HISTORY_PAGE_SIZE: int = 20
    """
    Number of history entries to display per page.
    Default: 20 entries

    Balances between user experience and performance.
    """

    MAX_HISTORY_ENTRIES: int = 1000
    """
    Maximum number of history entries to retain per execution.
    Default: 1000 entries

    Older entries are archived or deleted to prevent database bloat.
    """

    HISTORY_CACHE_TTL: int = 60
    """
    Cache timeout for history log API responses in seconds.
    Default: 60 seconds (1 minute)

    History data changes infrequently and can be cached.
    """

    # Cache Configuration (for repository methods)
    ALLOCATION_REPORTS_TTL: int = 900
    """
    Cache timeout for allocation reports dropdown in seconds.
    Default: 900 seconds (15 minutes)

    Allocation reports change infrequently, safe to cache longer.
    """

    PREVIEW_CACHE_TTL: int = 300
    """
    Cache timeout for preview data in seconds.
    Default: 300 seconds (5 minutes)

    Preview calculations can be cached temporarily for repeated views.
    """

    DOWNLOAD_TIMEOUT_SECONDS: int = 60
    """
    Timeout for Excel download requests in seconds.
    Default: 60 seconds

    Large Excel files may take time to generate and download.
    """

    # UI Configuration
    ENABLE_PREVIEW_WARNINGS: bool = True
    """
    Show warning messages in preview (e.g., capacity limits exceeded).
    Default: True

    Helps users identify potential issues before submitting.
    """

    ENABLE_PREVIEW_SUMMARY: bool = True
    """
    Show summary statistics in preview (e.g., total FTE increase).
    Default: True

    Provides quick overview of changes before confirmation.
    """

    DEFAULT_TAB: str = 'bench-allocation'
    """
    Default tab to show on page load.
    Default: 'bench-allocation'

    Options: 'bench-allocation', 'cph-update', 'manual-update', 'history-log'
    """

    MAX_USER_NOTES_LENGTH: int = 500
    """
    Maximum length for user notes in bench allocation updates.
    Default: 500 characters
    """

    # Validation Configuration
    VALIDATE_BEFORE_PREVIEW: bool = True
    """
    Validate input fields before generating preview.
    Default: True

    Prevents unnecessary API calls with invalid data.
    """

    VALIDATE_BEFORE_UPDATE: bool = True
    """
    Validate row data before submitting update.
    Default: True

    Final validation before transaction to catch any issues.
    """

    # Validation Methods
    @classmethod
    def validate(cls) -> None:
        """
        Validate configuration values.
        Raises ValueError if any configuration is invalid.
        """
        # Validate preview configuration
        if not isinstance(cls.PREVIEW_REFRESH_INTERVAL, int) or cls.PREVIEW_REFRESH_INTERVAL < 0:
            raise ValueError(
                f"PREVIEW_REFRESH_INTERVAL must be non-negative, got {cls.PREVIEW_REFRESH_INTERVAL}"
            )

        if not isinstance(cls.MAX_ROWS_PER_BATCH, int) or cls.MAX_ROWS_PER_BATCH < 1:
            raise ValueError(
                f"MAX_ROWS_PER_BATCH must be a positive integer, got {cls.MAX_ROWS_PER_BATCH}"
            )

        if not isinstance(cls.PREVIEW_TIMEOUT_SECONDS, int) or cls.PREVIEW_TIMEOUT_SECONDS < 1:
            raise ValueError(
                f"PREVIEW_TIMEOUT_SECONDS must be a positive integer, got {cls.PREVIEW_TIMEOUT_SECONDS}"
            )

        # Validate update configuration
        if not isinstance(cls.UPDATE_TIMEOUT_SECONDS, int) or cls.UPDATE_TIMEOUT_SECONDS < 1:
            raise ValueError(
                f"UPDATE_TIMEOUT_SECONDS must be a positive integer, got {cls.UPDATE_TIMEOUT_SECONDS}"
            )

        # Validate history configuration
        if not isinstance(cls.HISTORY_PAGE_SIZE, int) or cls.HISTORY_PAGE_SIZE < 1:
            raise ValueError(
                f"HISTORY_PAGE_SIZE must be a positive integer, got {cls.HISTORY_PAGE_SIZE}"
            )

        if not isinstance(cls.MAX_HISTORY_ENTRIES, int) or cls.MAX_HISTORY_ENTRIES < 1:
            raise ValueError(
                f"MAX_HISTORY_ENTRIES must be a positive integer, got {cls.MAX_HISTORY_ENTRIES}"
            )

        if not isinstance(cls.HISTORY_CACHE_TTL, int) or cls.HISTORY_CACHE_TTL < 0:
            raise ValueError(
                f"HISTORY_CACHE_TTL must be non-negative, got {cls.HISTORY_CACHE_TTL}"
            )

        # Validate default tab
        valid_tabs = ['bench-allocation', 'cph-update', 'manual-update', 'history-log']
        if cls.DEFAULT_TAB not in valid_tabs:
            raise ValueError(
                f"DEFAULT_TAB must be one of {valid_tabs}, got {cls.DEFAULT_TAB}"
            )

    @classmethod
    def get_config_dict(cls) -> dict:
        """
        Get all configuration as a dictionary.
        Useful for passing to templates or APIs.

        Returns:
            Dictionary of all configuration values
        """
        return {
            'preview_refresh_interval': cls.PREVIEW_REFRESH_INTERVAL,
            'max_rows_per_batch': cls.MAX_ROWS_PER_BATCH,
            'preview_timeout_seconds': cls.PREVIEW_TIMEOUT_SECONDS,
            'enable_atomic_updates': cls.ENABLE_ATOMIC_UPDATES,
            'rollback_on_error': cls.ROLLBACK_ON_ERROR,
            'update_timeout_seconds': cls.UPDATE_TIMEOUT_SECONDS,
            'history_page_size': cls.HISTORY_PAGE_SIZE,
            'max_history_entries': cls.MAX_HISTORY_ENTRIES,
            'history_cache_ttl': cls.HISTORY_CACHE_TTL,
            'allocation_reports_ttl': cls.ALLOCATION_REPORTS_TTL,
            'preview_cache_ttl': cls.PREVIEW_CACHE_TTL,
            'download_timeout_seconds': cls.DOWNLOAD_TIMEOUT_SECONDS,
            'enable_preview_warnings': cls.ENABLE_PREVIEW_WARNINGS,
            'enable_preview_summary': cls.ENABLE_PREVIEW_SUMMARY,
            'default_tab': cls.DEFAULT_TAB,
            'validate_before_preview': cls.VALIDATE_BEFORE_PREVIEW,
            'validate_before_update': cls.VALIDATE_BEFORE_UPDATE,
        }


# Validate edit view configuration on module import
try:
    EditViewConfig.validate()
except ValueError as e:
    raise RuntimeError(f"Invalid EditViewConfig: {e}")


# Example usage in code:
# from core.config import ManagerViewConfig
# 
# months_count = ManagerViewConfig.get_months_to_display(request.user)
# kpi_index = ManagerViewConfig.get_kpi_month_index(request.user)
# exec_config = ExecutionMonitoringConfig.get_config_dict()
# edit_config = EditViewConfig.get_config_dict()