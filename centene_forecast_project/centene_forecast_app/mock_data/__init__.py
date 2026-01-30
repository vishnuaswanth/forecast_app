"""
Mock Data Package

This package contains all mock data organized by feature area.
Replace these with actual FastAPI endpoint calls when backend is ready.

Package Structure:
- manager_view.py: Manager view filters and hierarchical data
- forecast_filters.py: Forecast cascade filter options
- edit_view.py: Edit view allocation and history data
- target_cph.py: Target CPH data and previews

Usage:
    from mock_data import get_report_months, get_categories
    from mock_data.forecast_filters import get_forecast_filter_years
    from mock_data.edit_view import get_allocation_reports
    from mock_data.target_cph import get_target_cph_data
"""

# Manager View exports (backward compatibility with existing imports)
from mock_data.manager_view import (
    get_report_months,
    get_categories,
    get_manager_data,
    get_history_log_mock_data,
    get_available_change_types
)

# Forecast Filters exports
from mock_data.forecast_filters import (
    get_forecast_filter_years,
    get_forecast_months_for_year,
    get_forecast_platforms,
    get_forecast_markets,
    get_forecast_localities,
    get_forecast_worktypes
)

# Edit View exports
from mock_data.edit_view import (
    get_allocation_reports,
    get_bench_allocation_preview,
    get_history_log,
    get_excel_download_bytes
)

# Target CPH exports
from mock_data.target_cph import (
    get_target_cph_data,
    get_target_cph_preview
)

__all__ = [
    # Manager View
    'get_report_months',
    'get_categories',
    'get_manager_data',
    'get_history_log_mock_data',
    'get_available_change_types',

    # Forecast Filters
    'get_forecast_filter_years',
    'get_forecast_months_for_year',
    'get_forecast_platforms',
    'get_forecast_markets',
    'get_forecast_localities',
    'get_forecast_worktypes',

    # Edit View
    'get_allocation_reports',
    'get_bench_allocation_preview',
    'get_history_log',
    'get_excel_download_bytes',

    # Target CPH
    'get_target_cph_data',
    'get_target_cph_preview',
]
