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

    HISTORY_INITIAL_LOAD: int = 3
    """
    Number of history entries to load on initial page load or filter application.
    Default: 3 entries

    Used for lazy loading - determines the initial batch size.
    """

    HISTORY_LAZY_LOAD_SIZE: int = 3
    """
    Number of additional history entries to load when "Load More" is clicked.
    Default: 3 entries

    Used for lazy loading - determines subsequent batch sizes.
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

    MAX_USER_NOTES_LENGTH: int = 500
    """
    Maximum length of user notes field for bench allocation approval/rejection.
    Default: 500 characters

    Prevents overly long notes and ensures database field compatibility.
    """

    # Cache Configuration (for repository methods)
    ALLOCATION_REPORTS_TTL: int = 900
    """
    Cache timeout for allocation reports dropdown in seconds.
    Default: 900 seconds (15 minutes)

    Allocation reports change infrequently, safe to cache longer.
    """

    CHANGE_TYPES_TTL: int = 3600
    """
    Cache timeout for available change types in seconds.
    Default: 3600 seconds (1 hour)

    Change types don't change often, safe to cache for longer periods.
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

    # Standard Colors Configuration
    STANDARD_COLORS: list = [
        '#0d6efd', '#198754', '#ffc107', '#dc3545', '#6f42c1', '#fd7e14',
        '#20c997', '#e91e63', '#9c27b0', '#673ab7', '#3f51b5', '#2196f3',
        '#03a9f4', '#00bcd4', '#009688', '#4caf50', '#8bc34a', '#cddc39',
        '#ffeb3b', '#ffc107', '#ff9800', '#ff5722', '#795548', '#9e9e9e',
        '#607d8b', '#f44336', '#e91e63', '#9c27b0', '#673ab7', '#3f51b5',
        '#2196f3', '#03a9f4', '#00bcd4', '#009688', '#4caf50', '#8bc34a',
        '#cddc39', '#ffeb3b', '#ff9800', '#ff5722', '#795548', '#9e9e9e',
        '#607d8b', '#1976d2', '#388e3c', '#f57c00', '#d32f2f', '#7b1fa2',
        '#512da8', '#303f9f'
    ]
    """
    List of 50 predefined colors for change types.
    Colors are selected for good contrast and visual distinction.
    """

    FALLBACK_COLOR: str = '#6c757d'
    """
    Fallback color for change types when all standard colors are exhausted.
    Default: Bootstrap gray color

    Should be a valid hex color code.
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

        if not isinstance(cls.HISTORY_INITIAL_LOAD, int) or cls.HISTORY_INITIAL_LOAD < 1:
            raise ValueError(
                f"HISTORY_INITIAL_LOAD must be a positive integer, got {cls.HISTORY_INITIAL_LOAD}"
            )

        if not isinstance(cls.HISTORY_LAZY_LOAD_SIZE, int) or cls.HISTORY_LAZY_LOAD_SIZE < 1:
            raise ValueError(
                f"HISTORY_LAZY_LOAD_SIZE must be a positive integer, got {cls.HISTORY_LAZY_LOAD_SIZE}"
            )

        # Validate user notes length
        if not isinstance(cls.MAX_USER_NOTES_LENGTH, int) or cls.MAX_USER_NOTES_LENGTH < 1:
            raise ValueError(
                f"MAX_USER_NOTES_LENGTH must be a positive integer, got {cls.MAX_USER_NOTES_LENGTH}"
            )

        # Validate default tab
        valid_tabs = ['bench-allocation', 'cph-update', 'manual-update', 'history-log']
        if cls.DEFAULT_TAB not in valid_tabs:
            raise ValueError(
                f"DEFAULT_TAB must be one of {valid_tabs}, got {cls.DEFAULT_TAB}"
            )

        # Validate standard colors
        if not isinstance(cls.STANDARD_COLORS, list) or len(cls.STANDARD_COLORS) == 0:
            raise ValueError(
                f"STANDARD_COLORS must be a non-empty list, got {type(cls.STANDARD_COLORS)}"
            )

        # Validate each color format
        for i, color in enumerate(cls.STANDARD_COLORS):
            if not isinstance(color, str) or not color.startswith('#') or len(color) != 7:
                raise ValueError(
                    f"STANDARD_COLORS[{i}] must be a valid hex color (e.g., '#6c757d'), got {color}"
                )

        # Validate fallback color format (basic hex color validation)
        if not isinstance(cls.FALLBACK_COLOR, str) or not cls.FALLBACK_COLOR.startswith('#') or len(cls.FALLBACK_COLOR) != 7:
            raise ValueError(
                f"FALLBACK_COLOR must be a valid hex color (e.g., '#6c757d'), got {cls.FALLBACK_COLOR}"
            )

        # Validate change types TTL
        if not isinstance(cls.CHANGE_TYPES_TTL, int) or cls.CHANGE_TYPES_TTL < 0:
            raise ValueError(
                f"CHANGE_TYPES_TTL must be a non-negative integer, got {cls.CHANGE_TYPES_TTL}"
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
            'history_initial_load': cls.HISTORY_INITIAL_LOAD,
            'history_lazy_load_size': cls.HISTORY_LAZY_LOAD_SIZE,
            'max_user_notes_length': cls.MAX_USER_NOTES_LENGTH,
            'allocation_reports_ttl': cls.ALLOCATION_REPORTS_TTL,
            'change_types_ttl': cls.CHANGE_TYPES_TTL,
            'preview_cache_ttl': cls.PREVIEW_CACHE_TTL,
            'download_timeout_seconds': cls.DOWNLOAD_TIMEOUT_SECONDS,
            'standard_colors': cls.STANDARD_COLORS,
            'fallback_color': cls.FALLBACK_COLOR,
            'enable_preview_warnings': cls.ENABLE_PREVIEW_WARNINGS,
            'enable_preview_summary': cls.ENABLE_PREVIEW_SUMMARY,
            'default_tab': cls.DEFAULT_TAB,
            'validate_before_preview': cls.VALIDATE_BEFORE_PREVIEW,
            'validate_before_update': cls.VALIDATE_BEFORE_UPDATE,
            'cph_config': TargetCPHConfig.get_config_dict(),
        }


# Validate edit view configuration on module import
try:
    EditViewConfig.validate()
except ValueError as e:
    raise RuntimeError(f"Invalid EditViewConfig: {e}")


class TargetCPHConfig:
    """
    Target CPH Update Configuration

    Controls pagination, validation, and caching behavior for the
    Target CPH tab in Edit View.
    """

    # Pagination Configuration
    RECORDS_PER_PAGE: int = 20
    """
    Number of CPH records to display per page in CPH table.
    Default: 20 records per page

    Balances between scrolling and pagination performance.
    """

    # Increment Configuration
    DEFAULT_INCREMENT_UNIT: float = 1.0
    """
    Default CPH increment/decrement unit for ±buttons.
    Default: 1.0 (whole number increments)

    Fixed at 1.0 (no UI selector in Phase 1).
    Can be 0.5 or 0.1 for finer control in future phases.
    """

    # Validation Configuration
    MIN_CPH_VALUE: float = 0.0
    """
    Minimum allowed CPH value.
    Default: 0.0 (allows zero CPH)

    CPH must be non-negative but can be zero for certain cases.
    """

    MAX_CPH_VALUE: float = 200.0
    """
    Maximum allowed CPH value.
    Default: 200.0

    Prevents unrealistic CPH values per API specification.
    """

    CPH_DECIMAL_PLACES: int = 2
    """
    Number of decimal places to round CPH values.
    Default: 2 decimal places (e.g., 125.45)

    Ensures consistent formatting in UI and database.
    """

    # Preview Configuration
    PREVIEW_PAGE_SIZE: int = 25
    """
    Number of preview records to display per page.
    Default: 25 records per page

    Matches bench allocation preview pagination for consistency.
    """

    # Cache Configuration
    CPH_DATA_TTL: int = 900
    """
    Cache timeout for CPH data API in seconds.
    Default: 900 seconds (15 minutes)

    CPH data changes infrequently, safe to cache longer.
    """

    CPH_PREVIEW_TTL: int = 300
    """
    Cache timeout for CPH preview API in seconds.
    Default: 300 seconds (5 minutes)

    Preview calculations can be cached temporarily.
    """

    MAX_USER_NOTES_LENGTH: int = 500
    """
    Maximum length of user notes field.
    Default: 500 characters

    Matches bench allocation user notes limit.
    """

    # Validation Methods
    @classmethod
    def validate(cls) -> None:
        """
        Validate configuration values.
        Raises ValueError if any configuration is invalid.
        """
        # Validate pagination
        if not isinstance(cls.RECORDS_PER_PAGE, int) or cls.RECORDS_PER_PAGE < 1:
            raise ValueError(
                f"RECORDS_PER_PAGE must be a positive integer, got {cls.RECORDS_PER_PAGE}"
            )

        if not isinstance(cls.PREVIEW_PAGE_SIZE, int) or cls.PREVIEW_PAGE_SIZE < 1:
            raise ValueError(
                f"PREVIEW_PAGE_SIZE must be a positive integer, got {cls.PREVIEW_PAGE_SIZE}"
            )

        # Validate increment unit
        if not isinstance(cls.DEFAULT_INCREMENT_UNIT, (int, float)) or cls.DEFAULT_INCREMENT_UNIT <= 0:
            raise ValueError(
                f"DEFAULT_INCREMENT_UNIT must be a positive number, got {cls.DEFAULT_INCREMENT_UNIT}"
            )

        # Validate CPH range
        if not isinstance(cls.MIN_CPH_VALUE, (int, float)) or cls.MIN_CPH_VALUE < 0:
            raise ValueError(
                f"MIN_CPH_VALUE must be non-negative, got {cls.MIN_CPH_VALUE}"
            )

        if not isinstance(cls.MAX_CPH_VALUE, (int, float)) or cls.MAX_CPH_VALUE <= 0:
            raise ValueError(
                f"MAX_CPH_VALUE must be positive, got {cls.MAX_CPH_VALUE}"
            )

        if cls.MIN_CPH_VALUE >= cls.MAX_CPH_VALUE:
            raise ValueError(
                f"MIN_CPH_VALUE ({cls.MIN_CPH_VALUE}) must be less than "
                f"MAX_CPH_VALUE ({cls.MAX_CPH_VALUE})"
            )

        # Validate decimal places
        if not isinstance(cls.CPH_DECIMAL_PLACES, int) or cls.CPH_DECIMAL_PLACES < 0:
            raise ValueError(
                f"CPH_DECIMAL_PLACES must be non-negative integer, got {cls.CPH_DECIMAL_PLACES}"
            )

        # Validate cache TTLs
        if not isinstance(cls.CPH_DATA_TTL, int) or cls.CPH_DATA_TTL < 0:
            raise ValueError(
                f"CPH_DATA_TTL must be non-negative, got {cls.CPH_DATA_TTL}"
            )

        if not isinstance(cls.CPH_PREVIEW_TTL, int) or cls.CPH_PREVIEW_TTL < 0:
            raise ValueError(
                f"CPH_PREVIEW_TTL must be non-negative, got {cls.CPH_PREVIEW_TTL}"
            )

        # Validate user notes length
        if not isinstance(cls.MAX_USER_NOTES_LENGTH, int) or cls.MAX_USER_NOTES_LENGTH < 1:
            raise ValueError(
                f"MAX_USER_NOTES_LENGTH must be a positive integer, got {cls.MAX_USER_NOTES_LENGTH}"
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
            'records_per_page': cls.RECORDS_PER_PAGE,
            'default_increment_unit': cls.DEFAULT_INCREMENT_UNIT,
            'min_cph_value': cls.MIN_CPH_VALUE,
            'max_cph_value': cls.MAX_CPH_VALUE,
            'cph_decimal_places': cls.CPH_DECIMAL_PLACES,
            'preview_page_size': cls.PREVIEW_PAGE_SIZE,
            'cph_data_ttl': cls.CPH_DATA_TTL,
            'cph_preview_ttl': cls.CPH_PREVIEW_TTL,
            'max_user_notes_length': cls.MAX_USER_NOTES_LENGTH,
        }


# Validate Target CPH configuration on module import
try:
    TargetCPHConfig.validate()
except ValueError as e:
    raise RuntimeError(f"Invalid TargetCPHConfig: {e}")


class ConfigurationViewConfig:
    """
    Configuration View Page Configuration

    Controls display, validation, and caching behavior for the
    Month Configuration and Target CPH Configuration management page.
    """

    # Display settings
    PAGE_SIZE: int = 25
    """
    Number of records to display per page in configuration tables.
    Default: 25 records per page
    """

    MAX_BULK_RECORDS: int = 100
    """
    Maximum number of records that can be created in a single bulk operation.
    Default: 100 records
    """

    # Cache TTLs (seconds)
    LIST_CACHE_TTL: int = 300
    """
    Cache timeout for configuration list API responses.
    Default: 300 seconds (5 minutes)
    """

    DISTINCT_VALUES_TTL: int = 900
    """
    Cache timeout for distinct values (LOBs, Case Types) API responses.
    Default: 900 seconds (15 minutes)
    """

    # Validation ranges
    MIN_YEAR: int = 2020
    """Minimum allowed year for month configurations"""

    MAX_YEAR: int = 2100
    """Maximum allowed year for month configurations"""

    # Month names for dropdowns
    MONTH_NAMES: list = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]
    """List of valid month names for dropdown selection"""

    # Work types
    WORK_TYPES: list = ['Domestic', 'Global']
    """List of valid work types for month configuration"""

    # Validation ranges for month configuration fields
    MIN_WORKING_DAYS: int = 1
    MAX_WORKING_DAYS: int = 31
    MIN_OCCUPANCY: float = 0.0
    MAX_OCCUPANCY: float = 1.0
    MIN_SHRINKAGE: float = 0.0
    MAX_SHRINKAGE: float = 1.0
    MIN_WORK_HOURS: float = 1.0
    MAX_WORK_HOURS: float = 24.0

    # Target CPH validation
    MIN_TARGET_CPH: float = 0.0
    """Minimum allowed Target CPH value (must be non-negative)"""

    MAX_LOB_LENGTH: int = 255
    """Maximum length for Main LOB field"""

    MAX_CASE_TYPE_LENGTH: int = 255
    """Maximum length for Case Type field"""

    # Validation Methods
    @classmethod
    def validate(cls) -> None:
        """
        Validate configuration values.
        Raises ValueError if any configuration is invalid.
        """
        # Validate page size
        if not isinstance(cls.PAGE_SIZE, int) or cls.PAGE_SIZE < 1:
            raise ValueError(f"PAGE_SIZE must be a positive integer, got {cls.PAGE_SIZE}")

        # Validate max bulk records
        if not isinstance(cls.MAX_BULK_RECORDS, int) or cls.MAX_BULK_RECORDS < 1:
            raise ValueError(f"MAX_BULK_RECORDS must be a positive integer, got {cls.MAX_BULK_RECORDS}")

        # Validate year range
        if not isinstance(cls.MIN_YEAR, int) or cls.MIN_YEAR < 1900:
            raise ValueError(f"MIN_YEAR must be >= 1900, got {cls.MIN_YEAR}")

        if not isinstance(cls.MAX_YEAR, int) or cls.MAX_YEAR <= cls.MIN_YEAR:
            raise ValueError(f"MAX_YEAR must be > MIN_YEAR, got {cls.MAX_YEAR}")

        # Validate month names
        if not isinstance(cls.MONTH_NAMES, list) or len(cls.MONTH_NAMES) != 12:
            raise ValueError("MONTH_NAMES must be a list of 12 month names")

        # Validate work types
        if not isinstance(cls.WORK_TYPES, list) or len(cls.WORK_TYPES) == 0:
            raise ValueError("WORK_TYPES must be a non-empty list")

        # Validate working days range
        if cls.MIN_WORKING_DAYS < 1 or cls.MAX_WORKING_DAYS > 31:
            raise ValueError("Working days range must be 1-31")

        # Validate percentage ranges
        if cls.MIN_OCCUPANCY < 0 or cls.MAX_OCCUPANCY > 1:
            raise ValueError("Occupancy range must be 0.0-1.0")

        if cls.MIN_SHRINKAGE < 0 or cls.MAX_SHRINKAGE > 1:
            raise ValueError("Shrinkage range must be 0.0-1.0")

        # Validate work hours range
        if cls.MIN_WORK_HOURS < 1 or cls.MAX_WORK_HOURS > 24:
            raise ValueError("Work hours range must be 1-24")

    @classmethod
    def get_config_dict(cls) -> dict:
        """
        Get all configuration as a dictionary.
        Useful for passing to templates or APIs.

        Returns:
            Dictionary of all configuration values
        """
        return {
            'page_size': cls.PAGE_SIZE,
            'max_bulk_records': cls.MAX_BULK_RECORDS,
            'list_cache_ttl': cls.LIST_CACHE_TTL,
            'distinct_values_ttl': cls.DISTINCT_VALUES_TTL,
            'min_year': cls.MIN_YEAR,
            'max_year': cls.MAX_YEAR,
            'month_names': cls.MONTH_NAMES,
            'work_types': cls.WORK_TYPES,
            'min_working_days': cls.MIN_WORKING_DAYS,
            'max_working_days': cls.MAX_WORKING_DAYS,
            'min_occupancy': cls.MIN_OCCUPANCY,
            'max_occupancy': cls.MAX_OCCUPANCY,
            'min_shrinkage': cls.MIN_SHRINKAGE,
            'max_shrinkage': cls.MAX_SHRINKAGE,
            'min_work_hours': cls.MIN_WORK_HOURS,
            'max_work_hours': cls.MAX_WORK_HOURS,
            'min_target_cph': cls.MIN_TARGET_CPH,
            'max_lob_length': cls.MAX_LOB_LENGTH,
            'max_case_type_length': cls.MAX_CASE_TYPE_LENGTH,
        }


# Validate configuration view configuration on module import
try:
    ConfigurationViewConfig.validate()
except ValueError as e:
    raise RuntimeError(f"Invalid ConfigurationViewConfig: {e}")


class ForecastReallocationConfig:
    """
    Forecast Reallocation Configuration

    Controls display, validation, and caching behavior for the
    Forecast Reallocation tab in Edit View. Allows manual editing
    of target_cph and fte_avail values with preview and update workflow.
    """

    # Display Configuration
    MAX_MONTHS_DISPLAY: int = 6
    """
    Maximum number of months to display in the reallocation table.
    Default: 6 months

    Users can select which months to show using checkboxes.
    """

    RECORDS_PER_PAGE: int = 25
    """
    Number of records to display per page in the data table.
    Default: 25 records per page

    Balances between scrolling and pagination performance.
    """

    PREVIEW_PAGE_SIZE: int = 25
    """
    Number of preview records to display per page.
    Default: 25 records per page

    Matches bench allocation preview pagination for consistency.
    """

    # Validation Configuration - Target CPH
    MIN_TARGET_CPH: float = 0.0
    """
    Minimum allowed Target CPH value.
    Default: 0.0 (allows zero CPH)

    CPH must be non-negative but can be zero for certain cases.
    """

    MAX_TARGET_CPH: float = 200.0
    """
    Maximum allowed Target CPH value.
    Default: 200.0

    Prevents unrealistic CPH values per API specification.
    """

    CPH_INCREMENT_UNIT: float = 1.0
    """
    Default CPH increment/decrement unit for ± buttons.
    Default: 1.0 (whole number increments)
    """

    CPH_DECIMAL_PLACES: int = 2
    """
    Number of decimal places for CPH values.
    Default: 2 decimal places (e.g., 125.45)
    """

    # Validation Configuration - FTE Available
    MIN_FTE_AVAIL: int = 0
    """
    Minimum allowed FTE Available value.
    Default: 0 (allows zero FTE)
    """

    MAX_FTE_AVAIL: int = 999
    """
    Maximum allowed FTE Available value.
    Default: 999

    Prevents unrealistic FTE values.
    """

    FTE_INCREMENT_UNIT: int = 1
    """
    Default FTE increment/decrement unit for ± buttons.
    Default: 1 (whole number increments)
    """

    # Cache Configuration
    DATA_CACHE_TTL: int = 900
    """
    Cache timeout for reallocation data API in seconds.
    Default: 900 seconds (15 minutes)
    """

    FILTER_CACHE_TTL: int = 300
    """
    Cache timeout for filter options (LOBs, States, Case Types) in seconds.
    Default: 300 seconds (5 minutes)
    """

    PREVIEW_CACHE_TTL: int = 300
    """
    Cache timeout for preview calculations in seconds.
    Default: 300 seconds (5 minutes)
    """

    # UI Configuration
    FROZEN_COLUMNS_COUNT: int = 4
    """
    Number of columns to freeze on the left side of the table.
    Default: 4 (Main LOB, State, Case Type, Target CPH)
    """

    MAX_USER_NOTES_LENGTH: int = 500
    """
    Maximum length of user notes field.
    Default: 500 characters
    """

    # Validation Methods
    @classmethod
    def validate(cls) -> None:
        """
        Validate configuration values.
        Raises ValueError if any configuration is invalid.
        """
        # Validate display settings
        if not isinstance(cls.MAX_MONTHS_DISPLAY, int) or cls.MAX_MONTHS_DISPLAY < 1:
            raise ValueError(
                f"MAX_MONTHS_DISPLAY must be a positive integer, got {cls.MAX_MONTHS_DISPLAY}"
            )

        if not isinstance(cls.RECORDS_PER_PAGE, int) or cls.RECORDS_PER_PAGE < 1:
            raise ValueError(
                f"RECORDS_PER_PAGE must be a positive integer, got {cls.RECORDS_PER_PAGE}"
            )

        if not isinstance(cls.PREVIEW_PAGE_SIZE, int) or cls.PREVIEW_PAGE_SIZE < 1:
            raise ValueError(
                f"PREVIEW_PAGE_SIZE must be a positive integer, got {cls.PREVIEW_PAGE_SIZE}"
            )

        # Validate CPH range
        if not isinstance(cls.MIN_TARGET_CPH, (int, float)) or cls.MIN_TARGET_CPH < 0:
            raise ValueError(
                f"MIN_TARGET_CPH must be non-negative, got {cls.MIN_TARGET_CPH}"
            )

        if not isinstance(cls.MAX_TARGET_CPH, (int, float)) or cls.MAX_TARGET_CPH <= 0:
            raise ValueError(
                f"MAX_TARGET_CPH must be positive, got {cls.MAX_TARGET_CPH}"
            )

        if cls.MIN_TARGET_CPH >= cls.MAX_TARGET_CPH:
            raise ValueError(
                f"MIN_TARGET_CPH ({cls.MIN_TARGET_CPH}) must be less than "
                f"MAX_TARGET_CPH ({cls.MAX_TARGET_CPH})"
            )

        # Validate FTE range
        if not isinstance(cls.MIN_FTE_AVAIL, int) or cls.MIN_FTE_AVAIL < 0:
            raise ValueError(
                f"MIN_FTE_AVAIL must be non-negative integer, got {cls.MIN_FTE_AVAIL}"
            )

        if not isinstance(cls.MAX_FTE_AVAIL, int) or cls.MAX_FTE_AVAIL <= 0:
            raise ValueError(
                f"MAX_FTE_AVAIL must be positive integer, got {cls.MAX_FTE_AVAIL}"
            )

        if cls.MIN_FTE_AVAIL >= cls.MAX_FTE_AVAIL:
            raise ValueError(
                f"MIN_FTE_AVAIL ({cls.MIN_FTE_AVAIL}) must be less than "
                f"MAX_FTE_AVAIL ({cls.MAX_FTE_AVAIL})"
            )

        # Validate cache TTLs
        if not isinstance(cls.DATA_CACHE_TTL, int) or cls.DATA_CACHE_TTL < 0:
            raise ValueError(
                f"DATA_CACHE_TTL must be non-negative, got {cls.DATA_CACHE_TTL}"
            )

        if not isinstance(cls.FILTER_CACHE_TTL, int) or cls.FILTER_CACHE_TTL < 0:
            raise ValueError(
                f"FILTER_CACHE_TTL must be non-negative, got {cls.FILTER_CACHE_TTL}"
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
            'max_months_display': cls.MAX_MONTHS_DISPLAY,
            'records_per_page': cls.RECORDS_PER_PAGE,
            'preview_page_size': cls.PREVIEW_PAGE_SIZE,
            'min_target_cph': cls.MIN_TARGET_CPH,
            'max_target_cph': cls.MAX_TARGET_CPH,
            'cph_increment_unit': cls.CPH_INCREMENT_UNIT,
            'cph_decimal_places': cls.CPH_DECIMAL_PLACES,
            'min_fte_avail': cls.MIN_FTE_AVAIL,
            'max_fte_avail': cls.MAX_FTE_AVAIL,
            'fte_increment_unit': cls.FTE_INCREMENT_UNIT,
            'data_cache_ttl': cls.DATA_CACHE_TTL,
            'filter_cache_ttl': cls.FILTER_CACHE_TTL,
            'preview_cache_ttl': cls.PREVIEW_CACHE_TTL,
            'frozen_columns_count': cls.FROZEN_COLUMNS_COUNT,
            'max_user_notes_length': cls.MAX_USER_NOTES_LENGTH,
        }


# Validate Forecast Reallocation configuration on module import
try:
    ForecastReallocationConfig.validate()
except ValueError as e:
    raise RuntimeError(f"Invalid ForecastReallocationConfig: {e}")


# Example usage in code:
# from core.config import ManagerViewConfig, ExecutionMonitoringConfig, EditViewConfig, ConfigurationViewConfig, ForecastReallocationConfig
#
# months_count = ManagerViewConfig.get_months_to_display(request.user)
# kpi_index = ManagerViewConfig.get_kpi_month_index(request.user)
# exec_config = ExecutionMonitoringConfig.get_config_dict()
# edit_config = EditViewConfig.get_config_dict()
# config_config = ConfigurationViewConfig.get_config_dict()
# reallocation_config = ForecastReallocationConfig.get_config_dict()