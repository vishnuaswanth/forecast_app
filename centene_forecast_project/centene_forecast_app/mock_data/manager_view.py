"""
Mock Data for Manager View

This module provides mock data for the Manager View dashboard.
Replace this with actual FastAPI endpoint calls when backend is ready.

Data Structure:
- Report months: Available months for the dropdown filter
- Categories: Top-level categories (Amisys Onshore, Facets, etc.)
- Hierarchical data: Multi-level category trees with forecast data
"""

from typing import Dict, List, Optional


class ManagerViewMockData:
    """
    Mock data provider for Manager View.

    When ready to connect to FastAPI:
    1. Replace method implementations with API calls
    2. Keep method signatures the same
    3. Data structure remains identical
    """

    @staticmethod
    def get_available_report_months() -> List[Dict[str, str]]:
        """
        Get list of available report months for dropdown filter.

        Returns:
            List of dicts with 'value' and 'display' keys

        Example:
            [
                {'value': '2025-03', 'display': 'March 2025'}
                {'value': '2025-02', 'display': 'February 2025'},
            ]
        """
        return [
            {'value': '2025-04', 'display': 'April 2025'},
            {'value': '2025-03', 'display': 'March 2025'},
            {'value': '2025-02', 'display': 'February 2025'},
        ]

    @staticmethod
    def get_available_categories() -> List[Dict[str, str]]:
        """
        Get list of available top-level categories for dropdown filter.

        Returns:
            List of dicts with 'value' and 'display' keys

        Example:
            [
                {'value': '', 'display': '-- All Categories --'},
                {'value': 'amisys-onshore', 'display': 'Amisys Onshore'}
            ]
        """
        return [
            {'value': '', 'display': '-- All Categories --'},
            {'value': 'amisys-onshore', 'display': 'Amisys Onshore'},
            {'value': 'amisys-offshore', 'display': 'Amisys Offshore'},
            {'value': 'facets', 'display': 'Facets'},
            {'value': 'xcelys-offshore', 'display': 'Xcelys Offshore'},
            {'value': 'xcelys-onshore', 'display': 'Xcelys Onshore'},
        ]

    @staticmethod
    def get_manager_view_data(report_month: str, category: Optional[str] = None) -> Dict:
        """
        Get manager view data for specified report month and optional category filter.

        Args:
            report_month: Report month in YYYY-MM format (e.g., '2025-02')
            category: Optional category filter (e.g., 'amisys-onshore')

        Returns:
            Dictionary containing:
            - report_month: Selected report month
            - months: List of forecast months (6 months)
            - categories: Hierarchical category data
            - category_name: Display name if filtered by category

        Example:
            {
                'report_month': '2025-02',
                'months': ['2025-02', '2025-03', '2025-04', '2025-05', '2025-06', '2025-07'],
                'categories': [...],
                'category_name': 'Amisys Onshore' or 'All Categories'
            }
        """
        # Get the data based on report month
        all_data = ManagerViewMockData._get_all_categories_data()

        if report_month not in all_data:
            raise ValueError(f"No data available for report month: {report_month}")

        data = all_data[report_month]

        # Filter by category if specified
        if category:
            category_data = next(
                (cat for cat in data['categories'] if cat['id'] == category),
                None
            )
            if not category_data:
                raise ValueError(f"Category not found: {category}")

            return {
                'report_month': report_month,
                'months': data['months'],
                'categories': [category_data],  # Return only filtered category
                'category_name': category_data['name']
            }

        # Return all categories
        return {
            'report_month': report_month,
            'months': data['months'],
            'categories': data['categories'],
            'category_name': 'All Categories'
        }

    @staticmethod
    def _get_all_categories_data() -> Dict:
        """
        Internal method containing all mock data organized by report month.

        Data structure for each category:
        {
            'id': 'unique-id',
            'name': 'Display Name',
            'level': 1,  # Hierarchy level (1-5)
            'has_children': True/False,
            'data': {
                '2025-02': {'cf': 4100, 'hc': 41, 'cap': 3895, 'gap': -205},
                '2025-03': {...},
                ...
            },
            'children': [...]  # Optional nested categories
        }
        """
        return {
            # February 2025 Report
            '2025-02': {
                'months': ['2025-03', '2025-04', '2025-05', '2025-06', '2025-07', '2025-08'],
                'categories': [
                    # Amisys Onshore
                    {
                        'id': 'amisys-onshore',
                        'name': 'Amisys Onshore',
                        'level': 1,
                        'has_children': True,
                        'data': {
                            '2025-03': {'cf': 185698, 'hc': 206, 'cap': 227690, 'gap': 41992},
                            '2025-04': {'cf': 185484, 'hc': 207, 'cap': 284107, 'gap': -550},
                            '2025-05': {'cf': 11100, 'hc': 112, 'cap': 10640, 'gap': -460},
                            '2025-06': {'cf': 11250, 'hc': 113, 'cap': 10735, 'gap': -515},
                            '2025-07': {'cf': 11400, 'hc': 115, 'cap': 10925, 'gap': -475},
                            '2025-08': {'cf': 10750, 'hc': 108, 'cap': 10260, 'gap': -490},
                        },
                        'children': [
                            # Commercial
                            {
                                'id': 'commercial',
                                'name': 'Commercial',
                                'level': 2,
                                'has_children': True,
                                'data': {
                                    '2025-02': {'cf': 4100, 'hc': 41, 'cap': 3895, 'gap': -205},
                                    '2025-03': {'cf': 4150, 'hc': 42, 'cap': 3990, 'gap': -160},
                                    '2025-04': {'cf': 4200, 'hc': 42, 'cap': 3990, 'gap': -210},
                                    '2025-05': {'cf': 4250, 'hc': 43, 'cap': 4085, 'gap': -165},
                                    '2025-06': {'cf': 4300, 'hc': 43, 'cap': 4085, 'gap': -215},
                                    '2025-07': {'cf': 4350, 'hc': 44, 'cap': 4180, 'gap': -170},
                                },
                                'children': [
                                    # Claims Processing
                                    {
                                        'id': 'claims-processing',
                                        'name': 'Claims Processing',
                                        'level': 3,
                                        'has_children': True,
                                        'data': {
                                            '2025-02': {'cf': 2600, 'hc': 26, 'cap': 2470, 'gap': -130},
                                            '2025-03': {'cf': 2650, 'hc': 27, 'cap': 2565, 'gap': -85},
                                            '2025-04': {'cf': 2700, 'hc': 27, 'cap': 2565, 'gap': -135},
                                            '2025-05': {'cf': 2750, 'hc': 28, 'cap': 2660, 'gap': -90},
                                            '2025-06': {'cf': 2800, 'hc': 28, 'cap': 2660, 'gap': -140},
                                            '2025-07': {'cf': 2850, 'hc': 29, 'cap': 2755, 'gap': -95},
                                        },
                                        'children': [
                                            # Standard Claims
                                            {
                                                'id': 'standard-claims',
                                                'name': 'Standard Claims',
                                                'level': 4,
                                                'has_children': False,
                                                'data': {
                                                    '2025-02': {'cf': 1750, 'hc': 18, 'cap': 1710, 'gap': -40},
                                                    '2025-03': {'cf': 1780, 'hc': 18, 'cap': 1710, 'gap': -70},
                                                    '2025-04': {'cf': 1800, 'hc': 18, 'cap': 1710, 'gap': -90},
                                                    '2025-05': {'cf': 1850, 'hc': 19, 'cap': 1805, 'gap': -45},
                                                    '2025-06': {'cf': 1880, 'hc': 19, 'cap': 1805, 'gap': -75},
                                                    '2025-07': {'cf': 1900, 'hc': 19, 'cap': 1805, 'gap': -95},
                                                },
                                                'children': []
                                            },
                                            # Complex Claims
                                            {
                                                'id': 'complex-claims',
                                                'name': 'Complex Claims',
                                                'level': 4,
                                                'has_children': False,
                                                'data': {
                                                    '2025-02': {'cf': 850, 'hc': 8, 'cap': 760, 'gap': -90},
                                                    '2025-03': {'cf': 870, 'hc': 9, 'cap': 855, 'gap': -15},
                                                    '2025-04': {'cf': 900, 'hc': 9, 'cap': 855, 'gap': -45},
                                                    '2025-05': {'cf': 900, 'hc': 9, 'cap': 855, 'gap': -45},
                                                    '2025-06': {'cf': 920, 'hc': 9, 'cap': 855, 'gap': -65},
                                                    '2025-07': {'cf': 950, 'hc': 10, 'cap': 950, 'gap': 0},
                                                },
                                                'children': []
                                            }
                                        ]
                                    },
                                    # Customer Service
                                    {
                                        'id': 'customer-service',
                                        'name': 'Customer Service',
                                        'level': 3,
                                        'has_children': False,
                                        'data': {
                                            '2025-02': {'cf': 1500, 'hc': 15, 'cap': 1425, 'gap': -75},
                                            '2025-03': {'cf': 1500, 'hc': 15, 'cap': 1425, 'gap': -75},
                                            '2025-04': {'cf': 1500, 'hc': 15, 'cap': 1425, 'gap': -75},
                                            '2025-05': {'cf': 1500, 'hc': 15, 'cap': 1425, 'gap': -75},
                                            '2025-06': {'cf': 1500, 'hc': 15, 'cap': 1425, 'gap': -75},
                                            '2025-07': {'cf': 1500, 'hc': 15, 'cap': 1425, 'gap': -75},
                                        },
                                        'children': []
                                    }
                                ]
                            },
                            # Medicare
                            {
                                'id': 'medicare',
                                'name': 'Medicare',
                                'level': 2,
                                'has_children': False,
                                'data': {
                                    '2025-02': {'cf': 3600, 'hc': 36, 'cap': 3420, 'gap': -180},
                                    '2025-03': {'cf': 3650, 'hc': 37, 'cap': 3515, 'gap': -135},
                                    '2025-04': {'cf': 3700, 'hc': 37, 'cap': 3515, 'gap': -185},
                                    '2025-05': {'cf': 3750, 'hc': 38, 'cap': 3610, 'gap': -140},
                                    '2025-06': {'cf': 3800, 'hc': 38, 'cap': 3610, 'gap': -190},
                                    '2025-07': {'cf': 3850, 'hc': 39, 'cap': 3705, 'gap': -145},
                                },
                                'children': []
                            },
                            # Medicaid
                            {
                                'id': 'medicaid',
                                'name': 'Medicaid',
                                'level': 2,
                                'has_children': False,
                                'data': {
                                    '2025-02': {'cf': 3050, 'hc': 31, 'cap': 2945, 'gap': -105},
                                    '2025-03': {'cf': 3075, 'hc': 31, 'cap': 2945, 'gap': -130},
                                    '2025-04': {'cf': 3100, 'hc': 31, 'cap': 2945, 'gap': -155},
                                    '2025-05': {'cf': 3100, 'hc': 31, 'cap': 2945, 'gap': -155},
                                    '2025-06': {'cf': 3150, 'hc': 32, 'cap': 3040, 'gap': -110},
                                    '2025-07': {'cf': 3200, 'hc': 32, 'cap': 3040, 'gap': -160},
                                },
                                'children': []
                            }
                        ]
                    },
                    # Amisys Offshore
                    {
                        'id': 'amisys-offshore',
                        'name': 'Amisys Offshore',
                        'level': 1,
                        'has_children': True,
                        'data': {
                            '2025-02': {'cf': 9250, 'hc': 93, 'cap': 8835, 'gap': -415},
                            '2025-03': {'cf': 9400, 'hc': 94, 'cap': 8930, 'gap': -470},
                            '2025-04': {'cf': 9500, 'hc': 95, 'cap': 9025, 'gap': -475},
                            '2025-05': {'cf': 9650, 'hc': 97, 'cap': 9215, 'gap': -435},
                            '2025-06': {'cf': 9800, 'hc': 98, 'cap': 9310, 'gap': -490},
                            '2025-07': {'cf': 9950, 'hc': 100, 'cap': 9500, 'gap': -450},
                        },
                        'children': [
                            {
                                'id': 'operations',
                                'name': 'Operations',
                                'level': 2,
                                'has_children': False,
                                'data': {
                                    '2025-02': {'cf': 6200, 'hc': 62, 'cap': 5890, 'gap': -310},
                                    '2025-03': {'cf': 6300, 'hc': 63, 'cap': 5985, 'gap': -315},
                                    '2025-04': {'cf': 6400, 'hc': 64, 'cap': 6080, 'gap': -320},
                                    '2025-05': {'cf': 6500, 'hc': 65, 'cap': 6175, 'gap': -325},
                                    '2025-06': {'cf': 6600, 'hc': 66, 'cap': 6270, 'gap': -330},
                                    '2025-07': {'cf': 6700, 'hc': 67, 'cap': 6365, 'gap': -335},
                                },
                                'children': []
                            },
                            {
                                'id': 'support',
                                'name': 'Support',
                                'level': 2,
                                'has_children': False,
                                'data': {
                                    '2025-02': {'cf': 3050, 'hc': 31, 'cap': 2945, 'gap': -105},
                                    '2025-03': {'cf': 3100, 'hc': 31, 'cap': 2945, 'gap': -155},
                                    '2025-04': {'cf': 3100, 'hc': 31, 'cap': 2945, 'gap': -155},
                                    '2025-05': {'cf': 3150, 'hc': 32, 'cap': 3040, 'gap': -110},
                                    '2025-06': {'cf': 3200, 'hc': 32, 'cap': 3040, 'gap': -160},
                                    '2025-07': {'cf': 3250, 'hc': 33, 'cap': 3135, 'gap': -115},
                                },
                                'children': []
                            }
                        ]
                    },
                    # Facets (other categories abbreviated for space)
                    {
                        'id': 'facets',
                        'name': 'Facets',
                        'level': 1,
                        'has_children': True,
                        'data': {
                            '2025-02': {'cf': 17750, 'hc': 178, 'cap': 16910, 'gap': -840},
                            '2025-03': {'cf': 17900, 'hc': 180, 'cap': 17100, 'gap': -800},
                            '2025-04': {'cf': 18000, 'hc': 180, 'cap': 17100, 'gap': -900},
                            '2025-05': {'cf': 18150, 'hc': 182, 'cap': 17290, 'gap': -860},
                            '2025-06': {'cf': 18300, 'hc': 183, 'cap': 17385, 'gap': -915},
                            '2025-07': {'cf': 18450, 'hc': 185, 'cap': 17575, 'gap': -875},
                        },
                        'children': [
                            {
                                'id': 'enrollment',
                                'name': 'Enrollment',
                                'level': 2,
                                'has_children': False,
                                'data': {
                                    '2025-02': {'cf': 8100, 'hc': 81, 'cap': 7695, 'gap': -405},
                                    '2025-03': {'cf': 8150, 'hc': 82, 'cap': 7790, 'gap': -360},
                                    '2025-04': {'cf': 8200, 'hc': 82, 'cap': 7790, 'gap': -410},
                                    '2025-05': {'cf': 8250, 'hc': 83, 'cap': 7885, 'gap': -365},
                                    '2025-06': {'cf': 8300, 'hc': 83, 'cap': 7885, 'gap': -415},
                                    '2025-07': {'cf': 8350, 'hc': 84, 'cap': 7980, 'gap': -370},
                                },
                                'children': []
                            },
                            {
                                'id': 'claims',
                                'name': 'Claims',
                                'level': 2,
                                'has_children': False,
                                'data': {
                                    '2025-02': {'cf': 9650, 'hc': 97, 'cap': 9215, 'gap': -435},
                                    '2025-03': {'cf': 9750, 'hc': 98, 'cap': 9310, 'gap': -440},
                                    '2025-04': {'cf': 9800, 'hc': 98, 'cap': 9310, 'gap': -490},
                                    '2025-05': {'cf': 9900, 'hc': 99, 'cap': 9405, 'gap': -495},
                                    '2025-06': {'cf': 10000, 'hc': 100, 'cap': 9500, 'gap': -500},
                                    '2025-07': {'cf': 10100, 'hc': 101, 'cap': 9595, 'gap': -505},
                                },
                                'children': []
                            }
                        ]
                    },
                    # Additional categories (Xcelys Offshore, Xcelys Onshore) can be added similarly
                ]
            },
            # March 2025 Report (slightly different numbers)
            '2025-03': {
                'months': ['2025-03', '2025-04', '2025-05', '2025-06', '2025-07', '2025-08'],
                'categories': [
                    {
                        'id': 'amisys-onshore',
                        'name': 'Amisys Onshore',
                        'level': 1,
                        'has_children': True,
                        'data': {
                            '2025-03': {'cf': 10900, 'hc': 110, 'cap': 10450, 'gap': -450},
                            '2025-04': {'cf': 11050, 'hc': 111, 'cap': 10545, 'gap': -505},
                            '2025-05': {'cf': 11200, 'hc': 112, 'cap': 10640, 'gap': -560},
                            '2025-06': {'cf': 11350, 'hc': 114, 'cap': 10830, 'gap': -520},
                            '2025-07': {'cf': 11500, 'hc': 115, 'cap': 10925, 'gap': -575},
                            '2025-08': {'cf': 11650, 'hc': 117, 'cap': 11115, 'gap': -535},
                        },
                        'children': []  # Simplified for mock
                    }
                ]
            },
            # April 2025 Report
            '2025-04': {
                'months': ['2025-04', '2025-05', '2025-06', '2025-07', '2025-08', '2025-09'],
                'categories': [
                    {
                        'id': 'amisys-onshore',
                        'name': 'Amisys Onshore',
                        'level': 1,
                        'has_children': True,
                        'data': {
                            '2025-04': {'cf': 11100, 'hc': 111, 'cap': 10545, 'gap': -555},
                            '2025-05': {'cf': 11250, 'hc': 113, 'cap': 10735, 'gap': -515},
                            '2025-06': {'cf': 11400, 'hc': 114, 'cap': 10830, 'gap': -570},
                            '2025-07': {'cf': 11550, 'hc': 116, 'cap': 11020, 'gap': -530},
                            '2025-08': {'cf': 11700, 'hc': 117, 'cap': 11115, 'gap': -585},
                            '2025-09': {'cf': 11850, 'hc': 119, 'cap': 11305, 'gap': -545},
                        },
                        'children': []  # Simplified for mock
                    }
                ]
            }
        }


# ============================================================================
# EDIT VIEW MOCK DATA
# ============================================================================

def get_available_change_types() -> Dict:
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
            'total': 4
        }

    Note: Colors are assigned from the STANDARD_COLORS array in config.py
    """
    # Import standard colors from config
    from core.config import EditViewConfig

    # Define all change types (must match backend constants)
    change_types = [
        'Bench Allocation',
        'CPH Update',
        'Manual Update',
        'Forecast Update'
    ]

    # Assign colors from standard colors list
    standard_colors = EditViewConfig.STANDARD_COLORS

    data = []
    for idx, change_type in enumerate(change_types):
        # Use modulo to cycle through colors if we have more types than colors
        color = standard_colors[idx % len(standard_colors)]
        data.append({
            'value': change_type,
            'display': change_type,
            'color': color
        })

    return {
        'success': True,
        'data': data,
        'total': len(data)
    }


def get_history_log_mock_data() -> List[Dict]:
    """
    Get mock history log entries for testing lazy loading.

    Returns:
        List of 20 diverse history log entries with:
        - All 4 change types (Bench Allocation, CPH Update, Manual Update, Forecast Update)
        - Varying timestamps (2 hours to 60 days ago)
        - Different users and report months
        - Complete summary_data structure

    Example entry:
        {
            'id': 'uuid-string',
            'change_type': 'Bench Allocation',
            'report_title': 'Bench Allocation, April 2025',
            'month': 'April',
            'year': 2025,
            'timestamp': '2025-01-15T10:30:00',
            'user': 'john.doe',
            'description': 'Allocated excess bench capacity...',
            'records_modified': 15,
            'summary_data': {...}
        }
    """
    from datetime import datetime, timedelta
    import uuid

    # Generate 20 diverse mock entries
    entries = [
        # Entry 1: Bench Allocation - 2 hours ago
        {
            'id': '550e8400-e29b-41d4-a716-446655440000',
            'change_type': 'Bench Allocation',
            'report_title': 'Bench Allocation, April 2025',
            'month': 'April',
            'year': 2025,
            'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
            'user': 'john.doe',
            'description': 'Allocated excess bench capacity for Q2 planning',
            'records_modified': 15,
            'summary_data': {
                'report_month': 'April',
                'report_year': 2025,
                'months': ['Apr-25', 'May-25', 'Jun-25', 'Jul-25', 'Aug-25', 'Sep-25'],
                'totals': {
                    'Apr-25': {'total_forecast': {'old': 125000, 'new': 125000}, 'total_fte_required': {'old': 250, 'new': 255}, 'total_fte_available': {'old': 275, 'new': 285}, 'total_capacity': {'old': 13750, 'new': 14250}},
                    'May-25': {'total_forecast': {'old': 130000, 'new': 130000}, 'total_fte_required': {'old': 260, 'new': 265}, 'total_fte_available': {'old': 285, 'new': 295}, 'total_capacity': {'old': 14250, 'new': 14750}},
                    'Jun-25': {'total_forecast': {'old': 135000, 'new': 135000}, 'total_fte_required': {'old': 270, 'new': 275}, 'total_fte_available': {'old': 295, 'new': 305}, 'total_capacity': {'old': 14750, 'new': 15250}},
                    'Jul-25': {'total_forecast': {'old': 140000, 'new': 140000}, 'total_fte_required': {'old': 280, 'new': 285}, 'total_fte_available': {'old': 305, 'new': 315}, 'total_capacity': {'old': 15250, 'new': 15750}},
                    'Aug-25': {'total_forecast': {'old': 145000, 'new': 145000}, 'total_fte_required': {'old': 290, 'new': 295}, 'total_fte_available': {'old': 315, 'new': 325}, 'total_capacity': {'old': 15750, 'new': 16250}},
                    'Sep-25': {'total_forecast': {'old': 150000, 'new': 150000}, 'total_fte_required': {'old': 300, 'new': 305}, 'total_fte_available': {'old': 325, 'new': 335}, 'total_capacity': {'old': 16250, 'new': 16750}}
                }
            }
        },
        # Entry 2: CPH Update - 1 day ago
        {
            'id': '660f9511-f39c-52e5-b827-557766551111',
            'change_type': 'CPH Update',
            'report_title': 'CPH Update, March 2025',
            'month': 'March',
            'year': 2025,
            'timestamp': (datetime.now() - timedelta(days=1)).isoformat(),
            'user': 'jane.smith',
            'description': 'Updated target CPH values based on performance analysis',
            'records_modified': 8,
            'summary_data': {
                'report_month': 'March',
                'report_year': 2025,
                'months': ['Mar-25', 'Apr-25', 'May-25', 'Jun-25', 'Jul-25', 'Aug-25'],
                'totals': {
                    'Mar-25': {'total_forecast': {'old': 120000, 'new': 120000}, 'total_fte_required': {'old': 240, 'new': 235}, 'total_fte_available': {'old': 260, 'new': 260}, 'total_capacity': {'old': 13000, 'new': 13200}},
                    'Apr-25': {'total_forecast': {'old': 125000, 'new': 125000}, 'total_fte_required': {'old': 250, 'new': 245}, 'total_fte_available': {'old': 270, 'new': 270}, 'total_capacity': {'old': 13500, 'new': 13700}},
                    'May-25': {'total_forecast': {'old': 130000, 'new': 130000}, 'total_fte_required': {'old': 260, 'new': 255}, 'total_fte_available': {'old': 280, 'new': 280}, 'total_capacity': {'old': 14000, 'new': 14200}},
                    'Jun-25': {'total_forecast': {'old': 135000, 'new': 135000}, 'total_fte_required': {'old': 270, 'new': 265}, 'total_fte_available': {'old': 290, 'new': 290}, 'total_capacity': {'old': 14500, 'new': 14700}},
                    'Jul-25': {'total_forecast': {'old': 140000, 'new': 140000}, 'total_fte_required': {'old': 280, 'new': 275}, 'total_fte_available': {'old': 300, 'new': 300}, 'total_capacity': {'old': 15000, 'new': 15200}},
                    'Aug-25': {'total_forecast': {'old': 145000, 'new': 145000}, 'total_fte_required': {'old': 290, 'new': 285}, 'total_fte_available': {'old': 310, 'new': 310}, 'total_capacity': {'old': 15500, 'new': 15700}}
                }
            }
        },
        # Entry 3: Manual Update - 3 days ago
        {
            'id': '770g0622-g40d-63f6-c938-668877662222',
            'change_type': 'Manual Update',
            'report_title': 'Manual Update, February 2025',
            'month': 'February',
            'year': 2025,
            'timestamp': (datetime.now() - timedelta(days=3)).isoformat(),
            'user': 'mike.johnson',
            'description': 'Manual adjustments for special project requirements',
            'records_modified': 5,
            'summary_data': {
                'report_month': 'February',
                'report_year': 2025,
                'months': ['Feb-25', 'Mar-25', 'Apr-25', 'May-25', 'Jun-25', 'Jul-25'],
                'totals': {
                    'Feb-25': {'total_forecast': {'old': 115000, 'new': 115000}, 'total_fte_required': {'old': 230, 'new': 235}, 'total_fte_available': {'old': 250, 'new': 255}, 'total_capacity': {'old': 12500, 'new': 12750}},
                    'Mar-25': {'total_forecast': {'old': 120000, 'new': 120000}, 'total_fte_required': {'old': 240, 'new': 245}, 'total_fte_available': {'old': 260, 'new': 265}, 'total_capacity': {'old': 13000, 'new': 13250}},
                    'Apr-25': {'total_forecast': {'old': 125000, 'new': 125000}, 'total_fte_required': {'old': 250, 'new': 255}, 'total_fte_available': {'old': 270, 'new': 275}, 'total_capacity': {'old': 13500, 'new': 13750}},
                    'May-25': {'total_forecast': {'old': 130000, 'new': 130000}, 'total_fte_required': {'old': 260, 'new': 265}, 'total_fte_available': {'old': 280, 'new': 285}, 'total_capacity': {'old': 14000, 'new': 14250}},
                    'Jun-25': {'total_forecast': {'old': 135000, 'new': 135000}, 'total_fte_required': {'old': 270, 'new': 275}, 'total_fte_available': {'old': 290, 'new': 295}, 'total_capacity': {'old': 14500, 'new': 14750}},
                    'Jul-25': {'total_forecast': {'old': 140000, 'new': 140000}, 'total_fte_required': {'old': 280, 'new': 285}, 'total_fte_available': {'old': 300, 'new': 305}, 'total_capacity': {'old': 15000, 'new': 15250}}
                }
            }
        },
        # Entry 4: Capacity Update - 5 days ago
        {
            'id': '880h1733-h51e-74g7-d049-779988773333',
            'change_type': 'Capacity Update',
            'report_title': 'Capacity Update, January 2025',
            'month': 'January',
            'year': 2025,
            'timestamp': (datetime.now() - timedelta(days=5)).isoformat(),
            'user': 'sarah.williams',
            'description': 'Capacity adjustment based on Q1 forecast review',
            'records_modified': 25,
            'summary_data': {
                'report_month': 'January',
                'report_year': 2025,
                'months': ['Jan-25', 'Feb-25', 'Mar-25', 'Apr-25', 'May-25', 'Jun-25'],
                'totals': {
                    'Jan-25': {'total_forecast': {'old': 110000, 'new': 112000}, 'total_fte_required': {'old': 220, 'new': 225}, 'total_fte_available': {'old': 240, 'new': 248}, 'total_capacity': {'old': 12000, 'new': 12400}},
                    'Feb-25': {'total_forecast': {'old': 115000, 'new': 117000}, 'total_fte_required': {'old': 230, 'new': 235}, 'total_fte_available': {'old': 250, 'new': 258}, 'total_capacity': {'old': 12500, 'new': 12900}},
                    'Mar-25': {'total_forecast': {'old': 120000, 'new': 122000}, 'total_fte_required': {'old': 240, 'new': 245}, 'total_fte_available': {'old': 260, 'new': 268}, 'total_capacity': {'old': 13000, 'new': 13400}},
                    'Apr-25': {'total_forecast': {'old': 125000, 'new': 127000}, 'total_fte_required': {'old': 250, 'new': 255}, 'total_fte_available': {'old': 270, 'new': 278}, 'total_capacity': {'old': 13500, 'new': 13900}},
                    'May-25': {'total_forecast': {'old': 130000, 'new': 132000}, 'total_fte_required': {'old': 260, 'new': 265}, 'total_fte_available': {'old': 280, 'new': 288}, 'total_capacity': {'old': 14000, 'new': 14400}},
                    'Jun-25': {'total_forecast': {'old': 135000, 'new': 137000}, 'total_fte_required': {'old': 270, 'new': 275}, 'total_fte_available': {'old': 290, 'new': 298}, 'total_capacity': {'old': 14500, 'new': 14900}}
                }
            }
        },
        # Entry 5: FTE Update - 7 days ago
        {
            'id': '990i2844-i62f-85h8-e150-880099884444',
            'change_type': 'FTE Update',
            'report_title': 'FTE Update, December 2024',
            'month': 'December',
            'year': 2024,
            'timestamp': (datetime.now() - timedelta(days=7)).isoformat(),
            'user': 'admin',
            'description': 'FTE availability update for December planning',
            'records_modified': 12,
            'summary_data': {
                'report_month': 'December',
                'report_year': 2024,
                'months': ['Dec-24', 'Jan-25', 'Feb-25', 'Mar-25', 'Apr-25', 'May-25'],
                'totals': {
                    'Dec-24': {'total_forecast': {'old': 105000, 'new': 105000}, 'total_fte_required': {'old': 210, 'new': 210}, 'total_fte_available': {'old': 230, 'new': 240}, 'total_capacity': {'old': 11500, 'new': 12000}},
                    'Jan-25': {'total_forecast': {'old': 110000, 'new': 110000}, 'total_fte_required': {'old': 220, 'new': 220}, 'total_fte_available': {'old': 240, 'new': 250}, 'total_capacity': {'old': 12000, 'new': 12500}},
                    'Feb-25': {'total_forecast': {'old': 115000, 'new': 115000}, 'total_fte_required': {'old': 230, 'new': 230}, 'total_fte_available': {'old': 250, 'new': 260}, 'total_capacity': {'old': 12500, 'new': 13000}},
                    'Mar-25': {'total_forecast': {'old': 120000, 'new': 120000}, 'total_fte_required': {'old': 240, 'new': 240}, 'total_fte_available': {'old': 260, 'new': 270}, 'total_capacity': {'old': 13000, 'new': 13500}},
                    'Apr-25': {'total_forecast': {'old': 125000, 'new': 125000}, 'total_fte_required': {'old': 250, 'new': 250}, 'total_fte_available': {'old': 270, 'new': 280}, 'total_capacity': {'old': 13500, 'new': 14000}},
                    'May-25': {'total_forecast': {'old': 130000, 'new': 130000}, 'total_fte_required': {'old': 260, 'new': 260}, 'total_fte_available': {'old': 280, 'new': 290}, 'total_capacity': {'old': 14000, 'new': 14500}}
                }
            }
        },
        # Entry 6: Forecast Update - 10 days ago
        {
            'id': 'aa0j3955-j73g-96i9-f261-991100995555',
            'change_type': 'Forecast Update',
            'report_title': 'Forecast Update, November 2024',
            'month': 'November',
            'year': 2024,
            'timestamp': (datetime.now() - timedelta(days=10)).isoformat(),
            'user': 'john.doe',
            'description': 'Updated forecast based on Q4 actuals',
            'records_modified': 35,
            'summary_data': {
                'report_month': 'November',
                'report_year': 2024,
                'months': ['Nov-24', 'Dec-24', 'Jan-25', 'Feb-25', 'Mar-25', 'Apr-25'],
                'totals': {
                    'Nov-24': {'total_forecast': {'old': 100000, 'new': 103000}, 'total_fte_required': {'old': 200, 'new': 206}, 'total_fte_available': {'old': 220, 'new': 225}, 'total_capacity': {'old': 11000, 'new': 11250}},
                    'Dec-24': {'total_forecast': {'old': 105000, 'new': 108000}, 'total_fte_required': {'old': 210, 'new': 216}, 'total_fte_available': {'old': 230, 'new': 235}, 'total_capacity': {'old': 11500, 'new': 11750}},
                    'Jan-25': {'total_forecast': {'old': 110000, 'new': 113000}, 'total_fte_required': {'old': 220, 'new': 226}, 'total_fte_available': {'old': 240, 'new': 245}, 'total_capacity': {'old': 12000, 'new': 12250}},
                    'Feb-25': {'total_forecast': {'old': 115000, 'new': 118000}, 'total_fte_required': {'old': 230, 'new': 236}, 'total_fte_available': {'old': 250, 'new': 255}, 'total_capacity': {'old': 12500, 'new': 12750}},
                    'Mar-25': {'total_forecast': {'old': 120000, 'new': 123000}, 'total_fte_required': {'old': 240, 'new': 246}, 'total_fte_available': {'old': 260, 'new': 265}, 'total_capacity': {'old': 13000, 'new': 13250}},
                    'Apr-25': {'total_forecast': {'old': 125000, 'new': 128000}, 'total_fte_required': {'old': 250, 'new': 256}, 'total_fte_available': {'old': 270, 'new': 275}, 'total_capacity': {'old': 13500, 'new': 13750}}
                }
            }
        },
        # Entry 7: Roster Update - 14 days ago
        {
            'id': 'bb1k4066-k84h-07j0-g372-002211006666',
            'change_type': 'Roster Update',
            'report_title': 'Roster Update, October 2024',
            'month': 'October',
            'year': 2024,
            'timestamp': (datetime.now() - timedelta(days=14)).isoformat(),
            'user': 'jane.smith',
            'description': 'Roster changes for new hires in October',
            'records_modified': 18,
            'summary_data': {
                'report_month': 'October',
                'report_year': 2024,
                'months': ['Oct-24', 'Nov-24', 'Dec-24', 'Jan-25', 'Feb-25', 'Mar-25'],
                'totals': {
                    'Oct-24': {'total_forecast': {'old': 95000, 'new': 95000}, 'total_fte_required': {'old': 190, 'new': 190}, 'total_fte_available': {'old': 210, 'new': 220}, 'total_capacity': {'old': 10500, 'new': 11000}},
                    'Nov-24': {'total_forecast': {'old': 100000, 'new': 100000}, 'total_fte_required': {'old': 200, 'new': 200}, 'total_fte_available': {'old': 220, 'new': 230}, 'total_capacity': {'old': 11000, 'new': 11500}},
                    'Dec-24': {'total_forecast': {'old': 105000, 'new': 105000}, 'total_fte_required': {'old': 210, 'new': 210}, 'total_fte_available': {'old': 230, 'new': 240}, 'total_capacity': {'old': 11500, 'new': 12000}},
                    'Jan-25': {'total_forecast': {'old': 110000, 'new': 110000}, 'total_fte_required': {'old': 220, 'new': 220}, 'total_fte_available': {'old': 240, 'new': 250}, 'total_capacity': {'old': 12000, 'new': 12500}},
                    'Feb-25': {'total_forecast': {'old': 115000, 'new': 115000}, 'total_fte_required': {'old': 230, 'new': 230}, 'total_fte_available': {'old': 250, 'new': 260}, 'total_capacity': {'old': 12500, 'new': 13000}},
                    'Mar-25': {'total_forecast': {'old': 120000, 'new': 120000}, 'total_fte_required': {'old': 240, 'new': 240}, 'total_fte_available': {'old': 260, 'new': 270}, 'total_capacity': {'old': 13000, 'new': 13500}}
                }
            }
        },
        # Entry 8: Headcount Update - 15 days ago
        {
            'id': 'cc2l5177-l95i-18k1-h483-113322117777',
            'change_type': 'Headcount Update',
            'report_title': 'Headcount Update, September 2024',
            'month': 'September',
            'year': 2024,
            'timestamp': (datetime.now() - timedelta(days=15)).isoformat(),
            'user': 'mike.johnson',
            'description': 'Headcount adjustments for September attrition',
            'records_modified': 22,
            'summary_data': {
                'report_month': 'September',
                'report_year': 2024,
                'months': ['Sep-24', 'Oct-24', 'Nov-24', 'Dec-24', 'Jan-25', 'Feb-25'],
                'totals': {
                    'Sep-24': {'total_forecast': {'old': 90000, 'new': 90000}, 'total_fte_required': {'old': 180, 'new': 175}, 'total_fte_available': {'old': 200, 'new': 195}, 'total_capacity': {'old': 10000, 'new': 9750}},
                    'Oct-24': {'total_forecast': {'old': 95000, 'new': 95000}, 'total_fte_required': {'old': 190, 'new': 185}, 'total_fte_available': {'old': 210, 'new': 205}, 'total_capacity': {'old': 10500, 'new': 10250}},
                    'Nov-24': {'total_forecast': {'old': 100000, 'new': 100000}, 'total_fte_required': {'old': 200, 'new': 195}, 'total_fte_available': {'old': 220, 'new': 215}, 'total_capacity': {'old': 11000, 'new': 10750}},
                    'Dec-24': {'total_forecast': {'old': 105000, 'new': 105000}, 'total_fte_required': {'old': 210, 'new': 205}, 'total_fte_available': {'old': 230, 'new': 225}, 'total_capacity': {'old': 11500, 'new': 11250}},
                    'Jan-25': {'total_forecast': {'old': 110000, 'new': 110000}, 'total_fte_required': {'old': 220, 'new': 215}, 'total_fte_available': {'old': 240, 'new': 235}, 'total_capacity': {'old': 12000, 'new': 11750}},
                    'Feb-25': {'total_forecast': {'old': 115000, 'new': 115000}, 'total_fte_required': {'old': 230, 'new': 225}, 'total_fte_available': {'old': 250, 'new': 245}, 'total_capacity': {'old': 12500, 'new': 12250}}
                }
            }
        },
        # Entry 9: Gap Analysis - 18 days ago
        {
            'id': 'dd3m6288-m06j-29l2-i594-224433228888',
            'change_type': 'Gap Analysis',
            'report_title': 'Gap Analysis, August 2024',
            'month': 'August',
            'year': 2024,
            'timestamp': (datetime.now() - timedelta(days=18)).isoformat(),
            'user': 'sarah.williams',
            'description': 'Gap analysis and capacity planning for Q3',
            'records_modified': 30,
            'summary_data': {
                'report_month': 'August',
                'report_year': 2024,
                'months': ['Aug-24', 'Sep-24', 'Oct-24', 'Nov-24', 'Dec-24', 'Jan-25'],
                'totals': {
                    'Aug-24': {'total_forecast': {'old': 85000, 'new': 88000}, 'total_fte_required': {'old': 170, 'new': 176}, 'total_fte_available': {'old': 190, 'new': 196}, 'total_capacity': {'old': 9500, 'new': 9800}},
                    'Sep-24': {'total_forecast': {'old': 90000, 'new': 93000}, 'total_fte_required': {'old': 180, 'new': 186}, 'total_fte_available': {'old': 200, 'new': 206}, 'total_capacity': {'old': 10000, 'new': 10300}},
                    'Oct-24': {'total_forecast': {'old': 95000, 'new': 98000}, 'total_fte_required': {'old': 190, 'new': 196}, 'total_fte_available': {'old': 210, 'new': 216}, 'total_capacity': {'old': 10500, 'new': 10800}},
                    'Nov-24': {'total_forecast': {'old': 100000, 'new': 103000}, 'total_fte_required': {'old': 200, 'new': 206}, 'total_fte_available': {'old': 220, 'new': 226}, 'total_capacity': {'old': 11000, 'new': 11300}},
                    'Dec-24': {'total_forecast': {'old': 105000, 'new': 108000}, 'total_fte_required': {'old': 210, 'new': 216}, 'total_fte_available': {'old': 230, 'new': 236}, 'total_capacity': {'old': 11500, 'new': 11800}},
                    'Jan-25': {'total_forecast': {'old': 110000, 'new': 113000}, 'total_fte_required': {'old': 220, 'new': 226}, 'total_fte_available': {'old': 240, 'new': 246}, 'total_capacity': {'old': 12000, 'new': 12300}}
                }
            }
        },
        # Entry 10: Reallocation - 20 days ago
        {
            'id': 'ee4n7399-n17k-30m3-j605-335544339999',
            'change_type': 'Reallocation',
            'report_title': 'Reallocation, July 2024',
            'month': 'July',
            'year': 2024,
            'timestamp': (datetime.now() - timedelta(days=20)).isoformat(),
            'user': 'admin',
            'description': 'Resource reallocation across teams',
            'records_modified': 42,
            'summary_data': {
                'report_month': 'July',
                'report_year': 2024,
                'months': ['Jul-24', 'Aug-24', 'Sep-24', 'Oct-24', 'Nov-24', 'Dec-24'],
                'totals': {
                    'Jul-24': {'total_forecast': {'old': 80000, 'new': 80000}, 'total_fte_required': {'old': 160, 'new': 165}, 'total_fte_available': {'old': 180, 'new': 185}, 'total_capacity': {'old': 9000, 'new': 9250}},
                    'Aug-24': {'total_forecast': {'old': 85000, 'new': 85000}, 'total_fte_required': {'old': 170, 'new': 175}, 'total_fte_available': {'old': 190, 'new': 195}, 'total_capacity': {'old': 9500, 'new': 9750}},
                    'Sep-24': {'total_forecast': {'old': 90000, 'new': 90000}, 'total_fte_required': {'old': 180, 'new': 185}, 'total_fte_available': {'old': 200, 'new': 205}, 'total_capacity': {'old': 10000, 'new': 10250}},
                    'Oct-24': {'total_forecast': {'old': 95000, 'new': 95000}, 'total_fte_required': {'old': 190, 'new': 195}, 'total_fte_available': {'old': 210, 'new': 215}, 'total_capacity': {'old': 10500, 'new': 10750}},
                    'Nov-24': {'total_forecast': {'old': 100000, 'new': 100000}, 'total_fte_required': {'old': 200, 'new': 205}, 'total_fte_available': {'old': 220, 'new': 225}, 'total_capacity': {'old': 11000, 'new': 11250}},
                    'Dec-24': {'total_forecast': {'old': 105000, 'new': 105000}, 'total_fte_required': {'old': 210, 'new': 215}, 'total_fte_available': {'old': 230, 'new': 235}, 'total_capacity': {'old': 11500, 'new': 11750}}
                }
            }
        },
        # Entry 11: Bench Allocation - 22 days ago
        {
            'id': 'ff5o8400-o28l-41n4-k716-446655440000',
            'change_type': 'Bench Allocation',
            'report_title': 'Bench Allocation, June 2024',
            'month': 'June',
            'year': 2024,
            'timestamp': (datetime.now() - timedelta(days=22)).isoformat(),
            'user': 'john.doe',
            'description': 'Bench capacity allocation for June projects',
            'records_modified': 16,
            'summary_data': {
                'report_month': 'June',
                'report_year': 2024,
                'months': ['Jun-24', 'Jul-24', 'Aug-24', 'Sep-24', 'Oct-24', 'Nov-24'],
                'totals': {
                    'Jun-24': {'total_forecast': {'old': 75000, 'new': 75000}, 'total_fte_required': {'old': 150, 'new': 155}, 'total_fte_available': {'old': 170, 'new': 178}, 'total_capacity': {'old': 8500, 'new': 8900}},
                    'Jul-24': {'total_forecast': {'old': 80000, 'new': 80000}, 'total_fte_required': {'old': 160, 'new': 165}, 'total_fte_available': {'old': 180, 'new': 188}, 'total_capacity': {'old': 9000, 'new': 9400}},
                    'Aug-24': {'total_forecast': {'old': 85000, 'new': 85000}, 'total_fte_required': {'old': 170, 'new': 175}, 'total_fte_available': {'old': 190, 'new': 198}, 'total_capacity': {'old': 9500, 'new': 9900}},
                    'Sep-24': {'total_forecast': {'old': 90000, 'new': 90000}, 'total_fte_required': {'old': 180, 'new': 185}, 'total_fte_available': {'old': 200, 'new': 208}, 'total_capacity': {'old': 10000, 'new': 10400}},
                    'Oct-24': {'total_forecast': {'old': 95000, 'new': 95000}, 'total_fte_required': {'old': 190, 'new': 195}, 'total_fte_available': {'old': 210, 'new': 218}, 'total_capacity': {'old': 10500, 'new': 10900}},
                    'Nov-24': {'total_forecast': {'old': 100000, 'new': 100000}, 'total_fte_required': {'old': 200, 'new': 205}, 'total_fte_available': {'old': 220, 'new': 228}, 'total_capacity': {'old': 11000, 'new': 11400}}
                }
            }
        },
        # Entry 12: Manual Update - 25 days ago
        {
            'id': 'gg6p9511-p39m-52o5-l827-557766551111',
            'change_type': 'Manual Update',
            'report_title': 'Manual Update, May 2024',
            'month': 'May',
            'year': 2024,
            'timestamp': (datetime.now() - timedelta(days=25)).isoformat(),
            'user': 'jane.smith',
            'description': 'Manual FTE adjustments for May planning',
            'records_modified': 14,
            'summary_data': {
                'report_month': 'May',
                'report_year': 2024,
                'months': ['May-24', 'Jun-24', 'Jul-24', 'Aug-24', 'Sep-24', 'Oct-24'],
                'totals': {
                    'May-24': {'total_forecast': {'old': 70000, 'new': 70000}, 'total_fte_required': {'old': 140, 'new': 145}, 'total_fte_available': {'old': 160, 'new': 165}, 'total_capacity': {'old': 8000, 'new': 8250}},
                    'Jun-24': {'total_forecast': {'old': 75000, 'new': 75000}, 'total_fte_required': {'old': 150, 'new': 155}, 'total_fte_available': {'old': 170, 'new': 175}, 'total_capacity': {'old': 8500, 'new': 8750}},
                    'Jul-24': {'total_forecast': {'old': 80000, 'new': 80000}, 'total_fte_required': {'old': 160, 'new': 165}, 'total_fte_available': {'old': 180, 'new': 185}, 'total_capacity': {'old': 9000, 'new': 9250}},
                    'Aug-24': {'total_forecast': {'old': 85000, 'new': 85000}, 'total_fte_required': {'old': 170, 'new': 175}, 'total_fte_available': {'old': 190, 'new': 195}, 'total_capacity': {'old': 9500, 'new': 9750}},
                    'Sep-24': {'total_forecast': {'old': 90000, 'new': 90000}, 'total_fte_required': {'old': 180, 'new': 185}, 'total_fte_available': {'old': 200, 'new': 205}, 'total_capacity': {'old': 10000, 'new': 10250}},
                    'Oct-24': {'total_forecast': {'old': 95000, 'new': 95000}, 'total_fte_required': {'old': 190, 'new': 195}, 'total_fte_available': {'old': 210, 'new': 215}, 'total_capacity': {'old': 10500, 'new': 10750}}
                }
            }
        },
        # Entry 13: CPH Update - 28 days ago
        {
            'id': 'hh7q0622-q40n-63p6-m938-668877662222',
            'change_type': 'CPH Update',
            'report_title': 'CPH Update, April 2024',
            'month': 'April',
            'year': 2024,
            'timestamp': (datetime.now() - timedelta(days=28)).isoformat(),
            'user': 'mike.johnson',
            'description': 'CPH target adjustments for Q2',
            'records_modified': 9,
            'summary_data': {
                'report_month': 'April',
                'report_year': 2024,
                'months': ['Apr-24', 'May-24', 'Jun-24', 'Jul-24', 'Aug-24', 'Sep-24'],
                'totals': {
                    'Apr-24': {'total_forecast': {'old': 65000, 'new': 65000}, 'total_fte_required': {'old': 130, 'new': 127}, 'total_fte_available': {'old': 150, 'new': 150}, 'total_capacity': {'old': 7500, 'new': 7650}},
                    'May-24': {'total_forecast': {'old': 70000, 'new': 70000}, 'total_fte_required': {'old': 140, 'new': 137}, 'total_fte_available': {'old': 160, 'new': 160}, 'total_capacity': {'old': 8000, 'new': 8150}},
                    'Jun-24': {'total_forecast': {'old': 75000, 'new': 75000}, 'total_fte_required': {'old': 150, 'new': 147}, 'total_fte_available': {'old': 170, 'new': 170}, 'total_capacity': {'old': 8500, 'new': 8650}},
                    'Jul-24': {'total_forecast': {'old': 80000, 'new': 80000}, 'total_fte_required': {'old': 160, 'new': 157}, 'total_fte_available': {'old': 180, 'new': 180}, 'total_capacity': {'old': 9000, 'new': 9150}},
                    'Aug-24': {'total_forecast': {'old': 85000, 'new': 85000}, 'total_fte_required': {'old': 170, 'new': 167}, 'total_fte_available': {'old': 190, 'new': 190}, 'total_capacity': {'old': 9500, 'new': 9650}},
                    'Sep-24': {'total_forecast': {'old': 90000, 'new': 90000}, 'total_fte_required': {'old': 180, 'new': 177}, 'total_fte_available': {'old': 200, 'new': 200}, 'total_capacity': {'old': 10000, 'new': 10150}}
                }
            }
        },
        # Entry 14: Capacity Update - 30 days ago
        {
            'id': 'ii8r1733-r51o-74q7-n049-779988773333',
            'change_type': 'Capacity Update',
            'report_title': 'Capacity Update, March 2024',
            'month': 'March',
            'year': 2024,
            'timestamp': (datetime.now() - timedelta(days=30)).isoformat(),
            'user': 'sarah.williams',
            'description': 'End of quarter capacity review and adjustments',
            'records_modified': 28,
            'summary_data': {
                'report_month': 'March',
                'report_year': 2024,
                'months': ['Mar-24', 'Apr-24', 'May-24', 'Jun-24', 'Jul-24', 'Aug-24'],
                'totals': {
                    'Mar-24': {'total_forecast': {'old': 60000, 'new': 62000}, 'total_fte_required': {'old': 120, 'new': 124}, 'total_fte_available': {'old': 140, 'new': 146}, 'total_capacity': {'old': 7000, 'new': 7300}},
                    'Apr-24': {'total_forecast': {'old': 65000, 'new': 67000}, 'total_fte_required': {'old': 130, 'new': 134}, 'total_fte_available': {'old': 150, 'new': 156}, 'total_capacity': {'old': 7500, 'new': 7800}},
                    'May-24': {'total_forecast': {'old': 70000, 'new': 72000}, 'total_fte_required': {'old': 140, 'new': 144}, 'total_fte_available': {'old': 160, 'new': 166}, 'total_capacity': {'old': 8000, 'new': 8300}},
                    'Jun-24': {'total_forecast': {'old': 75000, 'new': 77000}, 'total_fte_required': {'old': 150, 'new': 154}, 'total_fte_available': {'old': 170, 'new': 176}, 'total_capacity': {'old': 8500, 'new': 8800}},
                    'Jul-24': {'total_forecast': {'old': 80000, 'new': 82000}, 'total_fte_required': {'old': 160, 'new': 164}, 'total_fte_available': {'old': 180, 'new': 186}, 'total_capacity': {'old': 9000, 'new': 9300}},
                    'Aug-24': {'total_forecast': {'old': 85000, 'new': 87000}, 'total_fte_required': {'old': 170, 'new': 174}, 'total_fte_available': {'old': 190, 'new': 196}, 'total_capacity': {'old': 9500, 'new': 9800}}
                }
            }
        },
        # Entry 15: FTE Update - 35 days ago
        {
            'id': 'jj9s2844-s62p-85r8-o150-880099884444',
            'change_type': 'FTE Update',
            'report_title': 'FTE Update, February 2024',
            'month': 'February',
            'year': 2024,
            'timestamp': (datetime.now() - timedelta(days=35)).isoformat(),
            'user': 'admin',
            'description': 'FTE availability changes for February',
            'records_modified': 11,
            'summary_data': {
                'report_month': 'February',
                'report_year': 2024,
                'months': ['Feb-24', 'Mar-24', 'Apr-24', 'May-24', 'Jun-24', 'Jul-24'],
                'totals': {
                    'Feb-24': {'total_forecast': {'old': 55000, 'new': 55000}, 'total_fte_required': {'old': 110, 'new': 110}, 'total_fte_available': {'old': 130, 'new': 138}, 'total_capacity': {'old': 6500, 'new': 6900}},
                    'Mar-24': {'total_forecast': {'old': 60000, 'new': 60000}, 'total_fte_required': {'old': 120, 'new': 120}, 'total_fte_available': {'old': 140, 'new': 148}, 'total_capacity': {'old': 7000, 'new': 7400}},
                    'Apr-24': {'total_forecast': {'old': 65000, 'new': 65000}, 'total_fte_required': {'old': 130, 'new': 130}, 'total_fte_available': {'old': 150, 'new': 158}, 'total_capacity': {'old': 7500, 'new': 7900}},
                    'May-24': {'total_forecast': {'old': 70000, 'new': 70000}, 'total_fte_required': {'old': 140, 'new': 140}, 'total_fte_available': {'old': 160, 'new': 168}, 'total_capacity': {'old': 8000, 'new': 8400}},
                    'Jun-24': {'total_forecast': {'old': 75000, 'new': 75000}, 'total_fte_required': {'old': 150, 'new': 150}, 'total_fte_available': {'old': 170, 'new': 178}, 'total_capacity': {'old': 8500, 'new': 8900}},
                    'Jul-24': {'total_forecast': {'old': 80000, 'new': 80000}, 'total_fte_required': {'old': 160, 'new': 160}, 'total_fte_available': {'old': 180, 'new': 188}, 'total_capacity': {'old': 9000, 'new': 9400}}
                }
            }
        },
        # Entry 16: Forecast Update - 40 days ago
        {
            'id': 'kk0t3955-t73q-96s9-p261-991100995555',
            'change_type': 'Forecast Update',
            'report_title': 'Forecast Update, January 2024',
            'month': 'January',
            'year': 2024,
            'timestamp': (datetime.now() - timedelta(days=40)).isoformat(),
            'user': 'john.doe',
            'description': 'Q1 forecast revision based on year-end data',
            'records_modified': 38,
            'summary_data': {
                'report_month': 'January',
                'report_year': 2024,
                'months': ['Jan-24', 'Feb-24', 'Mar-24', 'Apr-24', 'May-24', 'Jun-24'],
                'totals': {
                    'Jan-24': {'total_forecast': {'old': 50000, 'new': 53000}, 'total_fte_required': {'old': 100, 'new': 106}, 'total_fte_available': {'old': 120, 'new': 125}, 'total_capacity': {'old': 6000, 'new': 6250}},
                    'Feb-24': {'total_forecast': {'old': 55000, 'new': 58000}, 'total_fte_required': {'old': 110, 'new': 116}, 'total_fte_available': {'old': 130, 'new': 135}, 'total_capacity': {'old': 6500, 'new': 6750}},
                    'Mar-24': {'total_forecast': {'old': 60000, 'new': 63000}, 'total_fte_required': {'old': 120, 'new': 126}, 'total_fte_available': {'old': 140, 'new': 145}, 'total_capacity': {'old': 7000, 'new': 7250}},
                    'Apr-24': {'total_forecast': {'old': 65000, 'new': 68000}, 'total_fte_required': {'old': 130, 'new': 136}, 'total_fte_available': {'old': 150, 'new': 155}, 'total_capacity': {'old': 7500, 'new': 7750}},
                    'May-24': {'total_forecast': {'old': 70000, 'new': 73000}, 'total_fte_required': {'old': 140, 'new': 146}, 'total_fte_available': {'old': 160, 'new': 165}, 'total_capacity': {'old': 8000, 'new': 8250}},
                    'Jun-24': {'total_forecast': {'old': 75000, 'new': 78000}, 'total_fte_required': {'old': 150, 'new': 156}, 'total_fte_available': {'old': 170, 'new': 175}, 'total_capacity': {'old': 8500, 'new': 8750}}
                }
            }
        },
        # Entry 17: Roster Update - 45 days ago
        {
            'id': 'll1u4066-u84r-07t0-q372-002211006666',
            'change_type': 'Roster Update',
            'report_title': 'Roster Update, December 2023',
            'month': 'December',
            'year': 2023,
            'timestamp': (datetime.now() - timedelta(days=45)).isoformat(),
            'user': 'jane.smith',
            'description': 'Year-end roster adjustments and holiday scheduling',
            'records_modified': 20,
            'summary_data': {
                'report_month': 'December',
                'report_year': 2023,
                'months': ['Dec-23', 'Jan-24', 'Feb-24', 'Mar-24', 'Apr-24', 'May-24'],
                'totals': {
                    'Dec-23': {'total_forecast': {'old': 45000, 'new': 45000}, 'total_fte_required': {'old': 90, 'new': 90}, 'total_fte_available': {'old': 110, 'new': 118}, 'total_capacity': {'old': 5500, 'new': 5900}},
                    'Jan-24': {'total_forecast': {'old': 50000, 'new': 50000}, 'total_fte_required': {'old': 100, 'new': 100}, 'total_fte_available': {'old': 120, 'new': 128}, 'total_capacity': {'old': 6000, 'new': 6400}},
                    'Feb-24': {'total_forecast': {'old': 55000, 'new': 55000}, 'total_fte_required': {'old': 110, 'new': 110}, 'total_fte_available': {'old': 130, 'new': 138}, 'total_capacity': {'old': 6500, 'new': 6900}},
                    'Mar-24': {'total_forecast': {'old': 60000, 'new': 60000}, 'total_fte_required': {'old': 120, 'new': 120}, 'total_fte_available': {'old': 140, 'new': 148}, 'total_capacity': {'old': 7000, 'new': 7400}},
                    'Apr-24': {'total_forecast': {'old': 65000, 'new': 65000}, 'total_fte_required': {'old': 130, 'new': 130}, 'total_fte_available': {'old': 150, 'new': 158}, 'total_capacity': {'old': 7500, 'new': 7900}},
                    'May-24': {'total_forecast': {'old': 70000, 'new': 70000}, 'total_fte_required': {'old': 140, 'new': 140}, 'total_fte_available': {'old': 160, 'new': 168}, 'total_capacity': {'old': 8000, 'new': 8400}}
                }
            }
        },
        # Entry 18: Headcount Update - 48 days ago
        {
            'id': 'mm2v5177-v95s-18u1-r483-113322117777',
            'change_type': 'Headcount Update',
            'report_title': 'Headcount Update, November 2023',
            'month': 'November',
            'year': 2023,
            'timestamp': (datetime.now() - timedelta(days=48)).isoformat(),
            'user': 'mike.johnson',
            'description': 'Headcount changes for year-end planning',
            'records_modified': 26,
            'summary_data': {
                'report_month': 'November',
                'report_year': 2023,
                'months': ['Nov-23', 'Dec-23', 'Jan-24', 'Feb-24', 'Mar-24', 'Apr-24'],
                'totals': {
                    'Nov-23': {'total_forecast': {'old': 40000, 'new': 40000}, 'total_fte_required': {'old': 80, 'new': 78}, 'total_fte_available': {'old': 100, 'new': 98}, 'total_capacity': {'old': 5000, 'new': 4900}},
                    'Dec-23': {'total_forecast': {'old': 45000, 'new': 45000}, 'total_fte_required': {'old': 90, 'new': 88}, 'total_fte_available': {'old': 110, 'new': 108}, 'total_capacity': {'old': 5500, 'new': 5400}},
                    'Jan-24': {'total_forecast': {'old': 50000, 'new': 50000}, 'total_fte_required': {'old': 100, 'new': 98}, 'total_fte_available': {'old': 120, 'new': 118}, 'total_capacity': {'old': 6000, 'new': 5900}},
                    'Feb-24': {'total_forecast': {'old': 55000, 'new': 55000}, 'total_fte_required': {'old': 110, 'new': 108}, 'total_fte_available': {'old': 130, 'new': 128}, 'total_capacity': {'old': 6500, 'new': 6400}},
                    'Mar-24': {'total_forecast': {'old': 60000, 'new': 60000}, 'total_fte_required': {'old': 120, 'new': 118}, 'total_fte_available': {'old': 140, 'new': 138}, 'total_capacity': {'old': 7000, 'new': 6900}},
                    'Apr-24': {'total_forecast': {'old': 65000, 'new': 65000}, 'total_fte_required': {'old': 130, 'new': 128}, 'total_fte_available': {'old': 150, 'new': 148}, 'total_capacity': {'old': 7500, 'new': 7400}}
                }
            }
        },
        # Entry 19: Gap Analysis - 51 days ago
        {
            'id': 'nn3w6288-w06t-29v2-s594-224433228888',
            'change_type': 'Gap Analysis',
            'report_title': 'Gap Analysis, October 2023',
            'month': 'October',
            'year': 2023,
            'timestamp': (datetime.now() - timedelta(days=51)).isoformat(),
            'user': 'sarah.williams',
            'description': 'Q4 capacity gap analysis and mitigation planning',
            'records_modified': 34,
            'summary_data': {
                'report_month': 'October',
                'report_year': 2023,
                'months': ['Oct-23', 'Nov-23', 'Dec-23', 'Jan-24', 'Feb-24', 'Mar-24'],
                'totals': {
                    'Oct-23': {'total_forecast': {'old': 35000, 'new': 37000}, 'total_fte_required': {'old': 70, 'new': 74}, 'total_fte_available': {'old': 90, 'new': 94}, 'total_capacity': {'old': 4500, 'new': 4700}},
                    'Nov-23': {'total_forecast': {'old': 40000, 'new': 42000}, 'total_fte_required': {'old': 80, 'new': 84}, 'total_fte_available': {'old': 100, 'new': 104}, 'total_capacity': {'old': 5000, 'new': 5200}},
                    'Dec-23': {'total_forecast': {'old': 45000, 'new': 47000}, 'total_fte_required': {'old': 90, 'new': 94}, 'total_fte_available': {'old': 110, 'new': 114}, 'total_capacity': {'old': 5500, 'new': 5700}},
                    'Jan-24': {'total_forecast': {'old': 50000, 'new': 52000}, 'total_fte_required': {'old': 100, 'new': 104}, 'total_fte_available': {'old': 120, 'new': 124}, 'total_capacity': {'old': 6000, 'new': 6200}},
                    'Feb-24': {'total_forecast': {'old': 55000, 'new': 57000}, 'total_fte_required': {'old': 110, 'new': 114}, 'total_fte_available': {'old': 130, 'new': 134}, 'total_capacity': {'old': 6500, 'new': 6700}},
                    'Mar-24': {'total_forecast': {'old': 60000, 'new': 62000}, 'total_fte_required': {'old': 120, 'new': 124}, 'total_fte_available': {'old': 140, 'new': 144}, 'total_capacity': {'old': 7000, 'new': 7200}}
                }
            }
        },
        # Entry 20: Reallocation - 60 days ago
        {
            'id': 'oo4x7399-x17u-30w3-t605-335544339999',
            'change_type': 'Reallocation',
            'report_title': 'Reallocation, September 2023',
            'month': 'September',
            'year': 2023,
            'timestamp': (datetime.now() - timedelta(days=60)).isoformat(),
            'user': 'admin',
            'description': 'End of Q3 resource reallocation',
            'records_modified': 45,
            'summary_data': {
                'report_month': 'September',
                'report_year': 2023,
                'months': ['Sep-23', 'Oct-23', 'Nov-23', 'Dec-23', 'Jan-24', 'Feb-24'],
                'totals': {
                    'Sep-23': {'total_forecast': {'old': 30000, 'new': 30000}, 'total_fte_required': {'old': 60, 'new': 64}, 'total_fte_available': {'old': 80, 'new': 85}, 'total_capacity': {'old': 4000, 'new': 4250}},
                    'Oct-23': {'total_forecast': {'old': 35000, 'new': 35000}, 'total_fte_required': {'old': 70, 'new': 74}, 'total_fte_available': {'old': 90, 'new': 95}, 'total_capacity': {'old': 4500, 'new': 4750}},
                    'Nov-23': {'total_forecast': {'old': 40000, 'new': 40000}, 'total_fte_required': {'old': 80, 'new': 84}, 'total_fte_available': {'old': 100, 'new': 105}, 'total_capacity': {'old': 5000, 'new': 5250}},
                    'Dec-23': {'total_forecast': {'old': 45000, 'new': 45000}, 'total_fte_required': {'old': 90, 'new': 94}, 'total_fte_available': {'old': 110, 'new': 115}, 'total_capacity': {'old': 5500, 'new': 5750}},
                    'Jan-24': {'total_forecast': {'old': 50000, 'new': 50000}, 'total_fte_required': {'old': 100, 'new': 104}, 'total_fte_available': {'old': 120, 'new': 125}, 'total_capacity': {'old': 6000, 'new': 6250}},
                    'Feb-24': {'total_forecast': {'old': 55000, 'new': 55000}, 'total_fte_required': {'old': 110, 'new': 114}, 'total_fte_available': {'old': 130, 'new': 135}, 'total_capacity': {'old': 6500, 'new': 6750}}
                }
            }
        }
    ]

    return entries


# Convenience functions for direct access
def get_report_months() -> List[Dict[str, str]]:
    """Get available report months for dropdown"""
    return ManagerViewMockData.get_available_report_months()


def get_categories() -> List[Dict[str, str]]:
    """Get available categories for dropdown"""
    return ManagerViewMockData.get_available_categories()


def get_manager_data(report_month: str, category: Optional[str] = None) -> Dict:
    """Get manager view data"""
    return ManagerViewMockData.get_manager_view_data(report_month, category)
