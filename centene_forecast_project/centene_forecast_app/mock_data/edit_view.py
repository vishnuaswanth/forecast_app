"""
Mock Data for Edit View

Provides mock data for edit view features:
- Allocation reports dropdown
- Bench allocation preview
- History log entries
- Excel file downloads

Replace with actual FastAPI endpoint calls when backend is ready.
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger('django')


def get_allocation_reports() -> Dict:
    """
    Get available allocation reports for dropdown.

    Returns:
        Dictionary with success flag, data list, and total count

    Example:
        {
            'success': True,
            'data': [
                {'value': '2025-04', 'display': 'April 2025'},
                {'value': '2025-03', 'display': 'March 2025'}
            ],
            'total': 6
        }
    """
    logger.info("[Edit View] Using mock data for allocation reports")

    mock_reports = {
        'success': True,
        'data': [
            {'value': '2025-04', 'display': 'April 2025'},
            {'value': '2025-03', 'display': 'March 2025'},
            {'value': '2025-02', 'display': 'February 2025'},
            {'value': '2025-01', 'display': 'January 2025'},
            {'value': '2024-12', 'display': 'December 2024'},
            {'value': '2024-11', 'display': 'November 2024'},
        ],
        'total': 6
    }

    logger.info(f"[Edit View] Retrieved {mock_reports['total']} allocation reports (MOCK)")
    return mock_reports


def get_bench_allocation_preview(month: str, year: int) -> Dict:
    """
    Calculate bench allocation preview (modified records only).

    IMPORTANT: Backend MUST follow the standardized format in PREVIEW_RESPONSE_STANDARD.md

    Standard Response Format:
    {
        'success': True,
        'months': {                              // Month index mapping for FastAPI processing
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
                'id': 'uuid',
                'main_lob': 'Medicaid',
                'state': 'MO',
                'case_type': 'Appeals',
                'target_cph': 100.0,              // Include for bench allocation
                'target_cph_change': 5.0,         // Include if modified
                'modified_fields': ['target_cph', 'Jun-25.fte_req'],  // Use DOT notation
                'Jun-25': {                       // Month data DIRECTLY on record (not nested)
                    'forecast': 12500,            // Use 'forecast' not 'cf'
                    'fte_req': 10.5,             // Use 'fte_req' not 'fte_required'
                    'fte_req_change': 2.3,
                    'fte_avail': 8.2,            // Use 'fte_avail' not 'fte_available'
                    'fte_avail_change': 1.5,
                    'capacity': 0.78,
                    'capacity_change': 0.05
                }
            }
        ],
        'summary': {'total_fte_change': 45.5, 'total_capacity_change': 2250},
        'message': None
    }

    Args:
        month: Month name (e.g., 'April')
        year: Year (e.g., 2025)

    Returns:
        Dictionary with modified records following standardized format
    """
    logger.info(f"[Edit View] Using mock data for preview - {month} {year}")

    mock_preview = {
        'success': True,
        'modified_records': [
            # Record 1: Amisys Medicaid DOMESTIC - Claims Processing
            {
                'main_lob': 'Amisys Medicaid DOMESTIC',
                'state': 'LA',
                'case_type': 'Claims Processing',
                'case_id': 'CL-001',
                'target_cph': 50,
                'target_cph_change': 0,
                'modified_fields': ['target_cph', 'Jun-25.forecast', 'Jun-25.fte_req', 'Jun-25.fte_avail', 'Jun-25.capacity', 'Aug-25.forecast', 'Aug-25.fte_req', 'Aug-25.fte_avail', 'Aug-25.capacity', 'Oct-25.forecast', 'Oct-25.fte_req', 'Oct-25.fte_avail', 'Oct-25.capacity'],
                'months': {
                    'Jun-25': {'forecast': 12500, 'fte_req': 25, 'fte_avail': 28, 'capacity': 1400, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 3, 'capacity_change': 150},
                    'Jul-25': {'forecast': 13000, 'fte_req': 26, 'fte_avail': 28, 'capacity': 1400, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Aug-25': {'forecast': 13500, 'fte_req': 27, 'fte_avail': 30, 'capacity': 1500, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 3, 'capacity_change': 100},
                    'Sep-25': {'forecast': 14000, 'fte_req': 28, 'fte_avail': 30, 'capacity': 1500, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Oct-25': {'forecast': 14500, 'fte_req': 29, 'fte_avail': 32, 'capacity': 1600, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 2, 'capacity_change': 100},
                    'Nov-25': {'forecast': 15000, 'fte_req': 30, 'fte_avail': 32, 'capacity': 1600, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0}
                }
            },
            # Record 2: Amisys Medicaid DOMESTIC - Enrollment
            {
                'main_lob': 'Amisys Medicaid DOMESTIC',
                'state': 'TX',
                'case_type': 'Enrollment',
                'case_id': 'EN-002',
                'target_cph': 65,
                'target_cph_change': 0,
                'modified_fields': ['Jun-25.forecast', 'Jun-25.fte_req', 'Jun-25.fte_avail', 'Jun-25.capacity', 'Aug-25.forecast', 'Aug-25.fte_req', 'Aug-25.fte_avail', 'Aug-25.capacity', 'Oct-25.forecast', 'Oct-25.fte_req', 'Oct-25.fte_avail', 'Oct-25.capacity'],
                'months': {
                    'Jun-25': {'forecast': 8000, 'fte_req': 12, 'fte_avail': 14, 'capacity': 910, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 2, 'capacity_change': 130},
                    'Jul-25': {'forecast': 8500, 'fte_req': 13, 'fte_avail': 14, 'capacity': 910, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Aug-25': {'forecast': 9000, 'fte_req': 14, 'fte_avail': 15, 'capacity': 975, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 1, 'capacity_change': 65},
                    'Sep-25': {'forecast': 9500, 'fte_req': 15, 'fte_avail': 15, 'capacity': 975, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Oct-25': {'forecast': 10000, 'fte_req': 15, 'fte_avail': 16, 'capacity': 1040, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 1, 'capacity_change': 65},
                    'Nov-25': {'forecast': 10500, 'fte_req': 16, 'fte_avail': 16, 'capacity': 1040, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0}
                }
            },
            # Record 3: Amisys Medicare OFFSHORE - Claims Processing
            {
                'main_lob': 'Amisys Medicare OFFSHORE',
                'state': 'FL',
                'case_type': 'Claims Processing',
                'case_id': 'CL-003',
                'target_cph': 55,
                'target_cph_change': 0,
                'modified_fields': ['target_cph', 'Jun-25.forecast', 'Jun-25.fte_req', 'Jun-25.fte_avail', 'Jun-25.capacity', 'Jul-25.forecast', 'Jul-25.fte_req', 'Jul-25.fte_avail', 'Jul-25.capacity', 'Sep-25.forecast', 'Sep-25.fte_req', 'Sep-25.fte_avail', 'Sep-25.capacity', 'Nov-25.forecast', 'Nov-25.fte_req', 'Nov-25.fte_avail', 'Nov-25.capacity'],
                'months': {
                    'Jun-25': {'forecast': 18000, 'fte_req': 33, 'fte_avail': 30, 'capacity': 1650, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Jul-25': {'forecast': 19000, 'fte_req': 35, 'fte_avail': 35, 'capacity': 1925, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 5, 'capacity_change': 275},
                    'Aug-25': {'forecast': 20000, 'fte_req': 36, 'fte_avail': 35, 'capacity': 1925, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Sep-25': {'forecast': 21000, 'fte_req': 38, 'fte_avail': 40, 'capacity': 2200, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 4, 'capacity_change': 220},
                    'Oct-25': {'forecast': 22000, 'fte_req': 40, 'fte_avail': 40, 'capacity': 2200, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Nov-25': {'forecast': 23000, 'fte_req': 42, 'fte_avail': 42, 'capacity': 2310, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 2, 'capacity_change': 110}
                }
            },
            # Record 4: Facets Medicaid DOMESTIC - Member Services
            {
                'main_lob': 'Facets Medicaid DOMESTIC',
                'state': 'CA',
                'case_type': 'Member Services',
                'case_id': 'MS-004',
                'target_cph': 40,
                'target_cph_change': 0,
                'modified_fields': ['Jun-25.forecast', 'Jun-25.fte_req', 'Jun-25.fte_avail', 'Jun-25.capacity', 'Aug-25.forecast', 'Aug-25.fte_req', 'Aug-25.fte_avail', 'Aug-25.capacity', 'Oct-25.forecast', 'Oct-25.fte_req', 'Oct-25.fte_avail', 'Oct-25.capacity'],
                'months': {
                    'Jun-25': {'forecast': 6000, 'fte_req': 15, 'fte_avail': 16, 'capacity': 640, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 1, 'capacity_change': 40},
                    'Jul-25': {'forecast': 6500, 'fte_req': 16, 'fte_avail': 16, 'capacity': 640, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Aug-25': {'forecast': 7000, 'fte_req': 18, 'fte_avail': 18, 'capacity': 720, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 2, 'capacity_change': 80},
                    'Sep-25': {'forecast': 7500, 'fte_req': 19, 'fte_avail': 18, 'capacity': 720, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Oct-25': {'forecast': 8000, 'fte_req': 20, 'fte_avail': 20, 'capacity': 800, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 2, 'capacity_change': 80},
                    'Nov-25': {'forecast': 8500, 'fte_req': 21, 'fte_avail': 20, 'capacity': 800, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0}
                }
            },
            # Record 5: Facets Medicare OFFSHORE - Provider Services
            {
                'main_lob': 'Facets Medicare OFFSHORE',
                'state': 'NY',
                'case_type': 'Provider Services',
                'case_id': 'PS-005',
                'target_cph': 45,
                'target_cph_change': 0,
                'modified_fields': ['target_cph', 'Jun-25.forecast', 'Jun-25.fte_req', 'Jun-25.fte_avail', 'Jun-25.capacity', 'Aug-25.forecast', 'Aug-25.fte_req', 'Aug-25.fte_avail', 'Aug-25.capacity', 'Oct-25.forecast', 'Oct-25.fte_req', 'Oct-25.fte_avail', 'Oct-25.capacity'],
                'months': {
                    'Jun-25': {'forecast': 10000, 'fte_req': 22, 'fte_avail': 24, 'capacity': 1080, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 2, 'capacity_change': 90},
                    'Jul-25': {'forecast': 11000, 'fte_req': 24, 'fte_avail': 24, 'capacity': 1080, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Aug-25': {'forecast': 12000, 'fte_req': 27, 'fte_avail': 27, 'capacity': 1215, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 3, 'capacity_change': 135},
                    'Sep-25': {'forecast': 13000, 'fte_req': 29, 'fte_avail': 27, 'capacity': 1215, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Oct-25': {'forecast': 14000, 'fte_req': 31, 'fte_avail': 32, 'capacity': 1440, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 5, 'capacity_change': 225},
                    'Nov-25': {'forecast': 15000, 'fte_req': 33, 'fte_avail': 32, 'capacity': 1440, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0}
                }
            },
            # Record 6: QNXT Commercial DOMESTIC - Claims Processing
            {
                'main_lob': 'QNXT Commercial DOMESTIC',
                'state': 'IL',
                'case_type': 'Claims Processing',
                'case_id': 'CL-006',
                'target_cph': 60,
                'target_cph_change': 0,
                'modified_fields': ['Jun-25.forecast', 'Jun-25.fte_req', 'Jun-25.fte_avail', 'Jun-25.capacity', 'Aug-25.forecast', 'Aug-25.fte_req', 'Aug-25.fte_avail', 'Aug-25.capacity', 'Oct-25.forecast', 'Oct-25.fte_req', 'Oct-25.fte_avail', 'Oct-25.capacity'],
                'months': {
                    'Jun-25': {'forecast': 20000, 'fte_req': 33, 'fte_avail': 35, 'capacity': 2100, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 2, 'capacity_change': 120},
                    'Jul-25': {'forecast': 21000, 'fte_req': 35, 'fte_avail': 35, 'capacity': 2100, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Aug-25': {'forecast': 22000, 'fte_req': 37, 'fte_avail': 38, 'capacity': 2280, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 3, 'capacity_change': 180},
                    'Sep-25': {'forecast': 23000, 'fte_req': 38, 'fte_avail': 38, 'capacity': 2280, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Oct-25': {'forecast': 24000, 'fte_req': 40, 'fte_avail': 42, 'capacity': 2520, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 4, 'capacity_change': 240},
                    'Nov-25': {'forecast': 25000, 'fte_req': 42, 'fte_avail': 42, 'capacity': 2520, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0}
                }
            },
            # Record 7: QNXT Commercial OFFSHORE - Enrollment
            {
                'main_lob': 'QNXT Commercial OFFSHORE',
                'state': 'GA',
                'case_type': 'Enrollment',
                'case_id': 'EN-007',
                'target_cph': 70,
                'target_cph_change': 0,
                'modified_fields': ['target_cph', 'Jun-25.forecast', 'Jun-25.fte_req', 'Jun-25.fte_avail', 'Jun-25.capacity', 'Aug-25.forecast', 'Aug-25.fte_req', 'Aug-25.fte_avail', 'Aug-25.capacity', 'Oct-25.forecast', 'Oct-25.fte_req', 'Oct-25.fte_avail', 'Oct-25.capacity'],
                'months': {
                    'Jun-25': {'forecast': 16000, 'fte_req': 23, 'fte_avail': 25, 'capacity': 1750, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 3, 'capacity_change': 210},
                    'Jul-25': {'forecast': 17000, 'fte_req': 24, 'fte_avail': 25, 'capacity': 1750, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Aug-25': {'forecast': 18000, 'fte_req': 26, 'fte_avail': 27, 'capacity': 1890, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 2, 'capacity_change': 140},
                    'Sep-25': {'forecast': 19000, 'fte_req': 27, 'fte_avail': 27, 'capacity': 1890, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Oct-25': {'forecast': 20000, 'fte_req': 29, 'fte_avail': 30, 'capacity': 2100, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 3, 'capacity_change': 210},
                    'Nov-25': {'forecast': 21000, 'fte_req': 30, 'fte_avail': 30, 'capacity': 2100, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0}
                }
            },
            # Record 8: Amisys Medicaid DOMESTIC - Provider Services
            {
                'main_lob': 'Amisys Medicaid DOMESTIC',
                'state': 'FL',
                'case_type': 'Provider Services',
                'case_id': 'PS-008',
                'target_cph': 42,
                'target_cph_change': 0,
                'modified_fields': ['Jun-25.forecast', 'Jun-25.fte_req', 'Jun-25.fte_avail', 'Jun-25.capacity', 'Aug-25.forecast', 'Aug-25.fte_req', 'Aug-25.fte_avail', 'Aug-25.capacity', 'Oct-25.forecast', 'Oct-25.fte_req', 'Oct-25.fte_avail', 'Oct-25.capacity'],
                'months': {
                    'Jun-25': {'forecast': 7500, 'fte_req': 18, 'fte_avail': 19, 'capacity': 798, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 1, 'capacity_change': 42},
                    'Jul-25': {'forecast': 8000, 'fte_req': 19, 'fte_avail': 19, 'capacity': 798, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Aug-25': {'forecast': 8500, 'fte_req': 20, 'fte_avail': 21, 'capacity': 882, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 2, 'capacity_change': 84},
                    'Sep-25': {'forecast': 9000, 'fte_req': 21, 'fte_avail': 21, 'capacity': 882, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Oct-25': {'forecast': 9500, 'fte_req': 23, 'fte_avail': 23, 'capacity': 966, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 2, 'capacity_change': 84},
                    'Nov-25': {'forecast': 10000, 'fte_req': 24, 'fte_avail': 23, 'capacity': 966, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0}
                }
            },
            # Record 9: Facets Medicare DOMESTIC - Claims Processing
            {
                'main_lob': 'Facets Medicare DOMESTIC',
                'state': 'OH',
                'case_type': 'Claims Processing',
                'case_id': 'CL-009',
                'target_cph': 52,
                'target_cph_change': 0,
                'modified_fields': ['target_cph', 'Jun-25.forecast', 'Jun-25.fte_req', 'Jun-25.fte_avail', 'Jun-25.capacity', 'Jul-25.forecast', 'Jul-25.fte_req', 'Jul-25.fte_avail', 'Jul-25.capacity', 'Sep-25.forecast', 'Sep-25.fte_req', 'Sep-25.fte_avail', 'Sep-25.capacity', 'Nov-25.forecast', 'Nov-25.fte_req', 'Nov-25.fte_avail', 'Nov-25.capacity'],
                'months': {
                    'Jun-25': {'forecast': 14000, 'fte_req': 27, 'fte_avail': 28, 'capacity': 1456, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 1, 'capacity_change': 52},
                    'Jul-25': {'forecast': 15000, 'fte_req': 29, 'fte_avail': 30, 'capacity': 1560, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 2, 'capacity_change': 104},
                    'Aug-25': {'forecast': 16000, 'fte_req': 31, 'fte_avail': 30, 'capacity': 1560, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Sep-25': {'forecast': 17000, 'fte_req': 33, 'fte_avail': 33, 'capacity': 1716, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 3, 'capacity_change': 156},
                    'Oct-25': {'forecast': 18000, 'fte_req': 35, 'fte_avail': 33, 'capacity': 1716, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Nov-25': {'forecast': 19000, 'fte_req': 37, 'fte_avail': 37, 'capacity': 1924, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 4, 'capacity_change': 208}
                }
            },
            # Record 10: Facets Medicare OFFSHORE - Member Services
            {
                'main_lob': 'Facets Medicare OFFSHORE',
                'state': 'AZ',
                'case_type': 'Member Services',
                'case_id': 'MS-010',
                'target_cph': 38,
                'target_cph_change': 0,
                'modified_fields': ['Jun-25.forecast', 'Jun-25.fte_req', 'Jun-25.fte_avail', 'Jun-25.capacity', 'Aug-25.forecast', 'Aug-25.fte_req', 'Aug-25.fte_avail', 'Aug-25.capacity', 'Oct-25.forecast', 'Oct-25.fte_req', 'Oct-25.fte_avail', 'Oct-25.capacity'],
                'months': {
                    'Jun-25': {'forecast': 5500, 'fte_req': 15, 'fte_avail': 15, 'capacity': 570, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 1, 'capacity_change': 38},
                    'Jul-25': {'forecast': 6000, 'fte_req': 16, 'fte_avail': 15, 'capacity': 570, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Aug-25': {'forecast': 6500, 'fte_req': 17, 'fte_avail': 18, 'capacity': 684, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 3, 'capacity_change': 114},
                    'Sep-25': {'forecast': 7000, 'fte_req': 18, 'fte_avail': 18, 'capacity': 684, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Oct-25': {'forecast': 7500, 'fte_req': 20, 'fte_avail': 20, 'capacity': 760, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 2, 'capacity_change': 76},
                    'Nov-25': {'forecast': 8000, 'fte_req': 21, 'fte_avail': 20, 'capacity': 760, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0}
                }
            },
            # Record 11: QNXT Medicaid DOMESTIC - Member Services
            {
                'main_lob': 'QNXT Medicaid DOMESTIC',
                'state': 'MI',
                'case_type': 'Member Services',
                'case_id': 'MS-011',
                'target_cph': 44,
                'target_cph_change': -2,
                'modified_fields': ['target_cph', 'Jun-25.forecast', 'Jun-25.fte_req', 'Jun-25.fte_avail', 'Jun-25.capacity', 'Aug-25.forecast', 'Aug-25.fte_req', 'Aug-25.fte_avail', 'Aug-25.capacity', 'Oct-25.forecast', 'Oct-25.fte_req', 'Oct-25.fte_avail', 'Oct-25.capacity'],
                'months': {
                    'Jun-25': {'forecast': 9000, 'fte_req': 21, 'fte_avail': 22, 'capacity': 968, 'forecast_change': 0, 'fte_req_change': -1, 'fte_avail_change': 1, 'capacity_change': 44},
                    'Jul-25': {'forecast': 9500, 'fte_req': 22, 'fte_avail': 22, 'capacity': 968, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Aug-25': {'forecast': 10000, 'fte_req': 23, 'fte_avail': 24, 'capacity': 1056, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 2, 'capacity_change': 88},
                    'Sep-25': {'forecast': 10500, 'fte_req': 24, 'fte_avail': 24, 'capacity': 1056, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Oct-25': {'forecast': 11000, 'fte_req': 25, 'fte_avail': 26, 'capacity': 1144, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 2, 'capacity_change': 88},
                    'Nov-25': {'forecast': 11500, 'fte_req': 26, 'fte_avail': 26, 'capacity': 1144, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0}
                }
            },
            # Record 12: QNXT Medicare DOMESTIC - Enrollment
            {
                'main_lob': 'QNXT Medicare DOMESTIC',
                'state': 'NC',
                'case_type': 'Enrollment',
                'case_id': 'EN-012',
                'target_cph': 68,
                'target_cph_change': 0,
                'modified_fields': ['Jun-25.forecast', 'Jun-25.fte_req', 'Jun-25.fte_avail', 'Jun-25.capacity', 'Aug-25.forecast', 'Aug-25.fte_req', 'Aug-25.fte_avail', 'Aug-25.capacity', 'Oct-25.forecast', 'Oct-25.fte_req', 'Oct-25.fte_avail', 'Oct-25.capacity'],
                'months': {
                    'Jun-25': {'forecast': 11000, 'fte_req': 16, 'fte_avail': 17, 'capacity': 1156, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 1, 'capacity_change': 68},
                    'Jul-25': {'forecast': 12000, 'fte_req': 18, 'fte_avail': 17, 'capacity': 1156, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Aug-25': {'forecast': 13000, 'fte_req': 19, 'fte_avail': 20, 'capacity': 1360, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 3, 'capacity_change': 204},
                    'Sep-25': {'forecast': 14000, 'fte_req': 21, 'fte_avail': 20, 'capacity': 1360, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Oct-25': {'forecast': 15000, 'fte_req': 22, 'fte_avail': 23, 'capacity': 1564, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 3, 'capacity_change': 204},
                    'Nov-25': {'forecast': 16000, 'fte_req': 24, 'fte_avail': 23, 'capacity': 1564, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0}
                }
            },
            # Record 13: Amisys Commercial DOMESTIC - Claims Processing
            {
                'main_lob': 'Amisys Commercial DOMESTIC',
                'state': 'WA',
                'case_type': 'Claims Processing',
                'case_id': 'CL-013',
                'target_cph': 58,
                'target_cph_change': 4,
                'modified_fields': ['target_cph', 'Jun-25.forecast', 'Jun-25.fte_req', 'Jun-25.fte_avail', 'Jun-25.capacity', 'Aug-25.forecast', 'Aug-25.fte_req', 'Aug-25.fte_avail', 'Aug-25.capacity', 'Oct-25.forecast', 'Oct-25.fte_req', 'Oct-25.fte_avail', 'Oct-25.capacity'],
                'months': {
                    'Jun-25': {'forecast': 17500, 'fte_req': 30, 'fte_avail': 32, 'capacity': 1856, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 2, 'capacity_change': 116},
                    'Jul-25': {'forecast': 18500, 'fte_req': 32, 'fte_avail': 32, 'capacity': 1856, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Aug-25': {'forecast': 19500, 'fte_req': 34, 'fte_avail': 35, 'capacity': 2030, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 3, 'capacity_change': 174},
                    'Sep-25': {'forecast': 20500, 'fte_req': 35, 'fte_avail': 35, 'capacity': 2030, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Oct-25': {'forecast': 21500, 'fte_req': 37, 'fte_avail': 38, 'capacity': 2204, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 3, 'capacity_change': 174},
                    'Nov-25': {'forecast': 22500, 'fte_req': 39, 'fte_avail': 38, 'capacity': 2204, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0}
                }
            },
            # Record 14: Facets Commercial OFFSHORE - Provider Services
            {
                'main_lob': 'Facets Commercial OFFSHORE',
                'state': 'VA',
                'case_type': 'Provider Services',
                'case_id': 'PS-014',
                'target_cph': 48,
                'target_cph_change': 0,
                'modified_fields': ['Jun-25.forecast', 'Jun-25.fte_req', 'Jun-25.fte_avail', 'Jun-25.capacity', 'Jul-25.forecast', 'Jul-25.fte_req', 'Jul-25.fte_avail', 'Jul-25.capacity', 'Sep-25.forecast', 'Sep-25.fte_req', 'Sep-25.fte_avail', 'Sep-25.capacity', 'Nov-25.forecast', 'Nov-25.fte_req', 'Nov-25.fte_avail', 'Nov-25.capacity'],
                'months': {
                    'Jun-25': {'forecast': 13000, 'fte_req': 27, 'fte_avail': 28, 'capacity': 1344, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 1, 'capacity_change': 48},
                    'Jul-25': {'forecast': 14000, 'fte_req': 29, 'fte_avail': 30, 'capacity': 1440, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 2, 'capacity_change': 96},
                    'Aug-25': {'forecast': 15000, 'fte_req': 31, 'fte_avail': 30, 'capacity': 1440, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Sep-25': {'forecast': 16000, 'fte_req': 33, 'fte_avail': 34, 'capacity': 1632, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 4, 'capacity_change': 192},
                    'Oct-25': {'forecast': 17000, 'fte_req': 35, 'fte_avail': 34, 'capacity': 1632, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Nov-25': {'forecast': 18000, 'fte_req': 38, 'fte_avail': 38, 'capacity': 1824, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 4, 'capacity_change': 192}
                }
            },
            # Record 15: QNXT Commercial DOMESTIC - Member Services
            {
                'main_lob': 'QNXT Commercial DOMESTIC',
                'state': 'MA',
                'case_type': 'Member Services',
                'case_id': 'MS-015',
                'target_cph': 41,
                'target_cph_change': 0,
                'modified_fields': ['Jun-25.forecast', 'Jun-25.fte_req', 'Jun-25.fte_avail', 'Jun-25.capacity', 'Aug-25.forecast', 'Aug-25.fte_req', 'Aug-25.fte_avail', 'Aug-25.capacity', 'Oct-25.forecast', 'Oct-25.fte_req', 'Oct-25.fte_avail', 'Oct-25.capacity'],
                'months': {
                    'Jun-25': {'forecast': 7000, 'fte_req': 17, 'fte_avail': 18, 'capacity': 738, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 1, 'capacity_change': 41},
                    'Jul-25': {'forecast': 7500, 'fte_req': 18, 'fte_avail': 18, 'capacity': 738, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Aug-25': {'forecast': 8000, 'fte_req': 20, 'fte_avail': 20, 'capacity': 820, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 2, 'capacity_change': 82},
                    'Sep-25': {'forecast': 8500, 'fte_req': 21, 'fte_avail': 20, 'capacity': 820, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0},
                    'Oct-25': {'forecast': 9000, 'fte_req': 22, 'fte_avail': 22, 'capacity': 902, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 2, 'capacity_change': 82},
                    'Nov-25': {'forecast': 9500, 'fte_req': 23, 'fte_avail': 22, 'capacity': 902, 'forecast_change': 0, 'fte_req_change': 0, 'fte_avail_change': 0, 'capacity_change': 0}
                }
            }
        ],
        'months': {
            'month1': 'Jun-25',
            'month2': 'Jul-25',
            'month3': 'Aug-25',
            'month4': 'Sep-25',
            'month5': 'Oct-25',
            'month6': 'Nov-25'
        },
        'total_modified': 15,
        'summary': {
            'total_fte_change': 128.0,
            'total_capacity_change': 4786
        },
        'message': None
    }

    logger.info(f"[Edit View] Preview calculated - {mock_preview['total_modified']} modified records (MOCK)")
    return mock_preview


def get_history_log(
    month: Optional[str] = None,
    year: Optional[int] = None,
    change_types: Optional[List[str]] = None,
    page: int = 1,
    limit: int = 10
) -> Dict:
    """
    Get history log entries with filtering and pagination.

    Uses centralized mock data from manager_view.py.

    Args:
        month: Optional month name filter (e.g., "April")
        year: Optional year filter (e.g., 2025)
        change_types: Optional list of change types to filter by
        page: Page number (default: 1)
        limit: Records per page (default: 10)

    Returns:
        Dictionary with paginated history entries
    """
    from mock_data.manager_view import get_history_log_mock_data

    logger.info(
        f"[Edit View] Using mock history - month: {month}, year: {year}, "
        f"page: {page}, change_types: {change_types}"
    )

    # Get all entries from centralized mock data
    all_entries = get_history_log_mock_data()

    # Apply filtering by change_types if provided
    if change_types and len(change_types) > 0:
        filtered_entries = [
            entry for entry in all_entries
            if entry.get('change_type') in change_types
        ]
        logger.info(
            f"[Edit View] Filtered by change types {change_types}: "
            f"{len(filtered_entries)} of {len(all_entries)} entries"
        )
    else:
        filtered_entries = all_entries

    # Calculate pagination
    total = len(filtered_entries)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_entries = filtered_entries[start_idx:end_idx]

    mock_history = {
        'success': True,
        'data': paginated_entries,
        'pagination': {
            'total': total,
            'page': page,
            'limit': limit,
            'has_more': end_idx < total
        }
    }

    entries_count = len(mock_history['data'])
    total = mock_history['pagination']['total']
    logger.info(f"[Edit View] Retrieved {entries_count} of {total} history entries (MOCK)")
    return mock_history


def get_excel_download_bytes(history_log_id: str) -> bytes:
    """
    Download Excel file for history entry.

    Args:
        history_log_id: UUID of history log entry

    Returns:
        Excel file bytes
    """
    logger.info(f"[Edit View] Using mock Excel download for history log: {history_log_id}")

    # Create a minimal mock Excel file (empty workbook bytes)
    mock_excel_bytes = b'PK\x03\x04' + b'\x00' * 100  # Minimal Excel file signature

    logger.info(f"[Edit View] Excel download successful - {len(mock_excel_bytes)} bytes (MOCK)")
    return mock_excel_bytes
