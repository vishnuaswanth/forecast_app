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
                "months": [
                "2025-03",
                "2025-04",
                "2025-05",
                "2025-06",
                "2025-07",
                "2025-08"
            ],
            "categories": [
                {
                    "id": "amisys-onshore",
                    "name": "Amisys Onshore",
                    "level": 1,
                    "has_children": True,
                    "data": {
                        "2025-03": {
                            "cf": 82007,
                            "hc": 33,
                            "cap": 56472,
                            "gap": -25535
                        },
                        "2025-04": {
                            "cf": 85402,
                            "hc": 31,
                            "cap": 52391,
                            "gap": -33011
                        },
                        "2025-05": {
                            "cf": 85061,
                            "hc": 31,
                            "cap": 52391,
                            "gap": -32670
                        },
                        "2025-06": {
                            "cf": 85213,
                            "hc": 31,
                            "cap": 52391,
                            "gap": -32822
                        },
                        "2025-07": {
                            "cf": 85282,
                            "hc": 31,
                            "cap": 55596,
                            "gap": -29686
                        },
                        "2025-08": {
                            "cf": 85094,
                            "hc": 31,
                            "cap": 55596,
                            "gap": -29498
                        }
                    },
                    "children": [
                        {
                            "id": "amisys-onshore-manual",
                            "name": "Manual",
                            "level": 2,
                            "has_children": True,
                            "data": {
                                "2025-03": {
                                    "cf": 82007,
                                    "hc": 33,
                                    "cap": 56472,
                                    "gap": -25535
                                },
                                "2025-04": {
                                    "cf": 85402,
                                    "hc": 31,
                                    "cap": 52391,
                                    "gap": -33011
                                },
                                "2025-05": {
                                    "cf": 85061,
                                    "hc": 31,
                                    "cap": 52391,
                                    "gap": -32670
                                },
                                "2025-06": {
                                    "cf": 85213,
                                    "hc": 31,
                                    "cap": 52391,
                                    "gap": -32822
                                },
                                "2025-07": {
                                    "cf": 85282,
                                    "hc": 31,
                                    "cap": 55596,
                                    "gap": -29686
                                },
                                "2025-08": {
                                    "cf": 85094,
                                    "hc": 31,
                                    "cap": 55596,
                                    "gap": -29498
                                }
                            },
                            "children": [
                                {
                                    "id": "amisys-onshore-manual-FL&GA",
                                    "name": "FL & GA",
                                    "level": 3,
                                    "has_children": True,
                                    "data": {
                                        "2025-03": {
                                            "cf": 51411,
                                            "hc": 28,
                                            "cap": 48308,
                                            "gap": -3103
                                        },
                                        "2025-04": {
                                            "cf": 56452,
                                            "hc": 27,
                                            "cap": 45587,
                                            "gap": -10865
                                        },
                                        "2025-05": {
                                            "cf": 56317,
                                            "hc": 27,
                                            "cap": 45587,
                                            "gap": -10730
                                        },
                                        "2025-06": {
                                            "cf": 56569,
                                            "hc": 27,
                                            "cap": 45587,
                                            "gap": -10982
                                        },
                                        "2025-07": {
                                            "cf": 56447,
                                            "hc": 27,
                                            "cap": 48469,
                                            "gap": -7978
                                        },
                                        "2025-08": {
                                            "cf": 56326,
                                            "hc": 27,
                                            "cap": 48469,
                                            "gap": -7857
                                        }
                                    },
                                    "children": [
                                        {
                                            "id": "amisys-onshore-manual-FL&GA-FTC",
                                            "name": "FTC",
                                            "level": 4,
                                            "has_children": False,
                                            "data": {
                                                "2025-03": {
                                                    "cf": 34291,
                                                    "hc": 15,
                                                    "cap": 30618,
                                                    "gap": -3673
                                                },
                                                "2025-04": {
                                                    "cf": 37720,
                                                    "hc": 13,
                                                    "cap": 26535,
                                                    "gap": -11185
                                                },
                                                "2025-05": {
                                                    "cf": 37625,
                                                    "hc": 13,
                                                    "cap": 26535,
                                                    "gap": -11090
                                                },
                                                "2025-06": {
                                                    "cf": 37784,
                                                    "hc": 13,
                                                    "cap": 26535,
                                                    "gap": -11249
                                                },
                                                "2025-07": {
                                                    "cf": 37699,
                                                    "hc": 14,
                                                    "cap": 29937,
                                                    "gap": -7762
                                                },
                                                "2025-08": {
                                                    "cf": 37614,
                                                    "hc": 14,
                                                    "cap": 29937,
                                                    "gap": -7677
                                                }
                                            },
                                            "children": []
                                        },
                                        {
                                            "id": "amisys-onshore-manual-FL&GA-ADJ",
                                            "name": "ADJ",
                                            "level": 4,
                                            "has_children": False,
                                            "data": {
                                                "2025-03": {
                                                    "cf": 17120,
                                                    "hc": 13,
                                                    "cap": 17690,
                                                    "gap": 570
                                                },
                                                "2025-04": {
                                                    "cf": 18732,
                                                    "hc": 14,
                                                    "cap": 19052,
                                                    "gap": 320
                                                },
                                                "2025-05": {
                                                    "cf": 18692,
                                                    "hc": 14,
                                                    "cap": 19052,
                                                    "gap": 360
                                                },
                                                "2025-06": {
                                                    "cf": 18785,
                                                    "hc": 14,
                                                    "cap": 19052,
                                                    "gap": 267
                                                },
                                                "2025-07": {
                                                    "cf": 18748,
                                                    "hc": 13,
                                                    "cap": 18532,
                                                    "gap": -216
                                                },
                                                "2025-08": {
                                                    "cf": 18712,
                                                    "hc": 13,
                                                    "cap": 18532,
                                                    "gap": -180
                                                }
                                            },
                                            "children": []
                                        }
                                    ]
                                },
                                {
                                    "id": "amisys-onshore-manual-MI",
                                    "name": "MI",
                                    "level": 3,
                                    "has_children": True,
                                    "data": {
                                        "2025-03": {
                                            "cf": 30596,
                                            "hc": 5,
                                            "cap": 8164,
                                            "gap": -22432
                                        },
                                        "2025-04": {
                                            "cf": 28950,
                                            "hc": 4,
                                            "cap": 6804,
                                            "gap": -22146
                                        },
                                        "2025-05": {
                                            "cf": 28744,
                                            "hc": 4,
                                            "cap": 6804,
                                            "gap": -21940
                                        },
                                        "2025-06": {
                                            "cf": 28644,
                                            "hc": 4,
                                            "cap": 6804,
                                            "gap": -21840
                                        },
                                        "2025-07": {
                                            "cf": 28835,
                                            "hc": 4,
                                            "cap": 7127,
                                            "gap": -21708
                                        },
                                        "2025-08": {
                                            "cf": 28768,
                                            "hc": 4,
                                            "cap": 7127,
                                            "gap": -21641
                                        }
                                    },
                                    "children": [
                                        {
                                            "id": "amisys-onshore-manual-MI-ADJ",
                                            "name": "ADJ",
                                            "level": 4,
                                            "has_children": False,
                                            "data": {
                                                "2025-03": {
                                                    "cf": 6994,
                                                    "hc": 3,
                                                    "cap": 4082,
                                                    "gap": -2912
                                                },
                                                "2025-04": {
                                                    "cf": 5777,
                                                    "hc": 2,
                                                    "cap": 2722,
                                                    "gap": -3055
                                                },
                                                "2025-05": {
                                                    "cf": 5722,
                                                    "hc": 2,
                                                    "cap": 2722,
                                                    "gap": -3000
                                                },
                                                "2025-06": {
                                                    "cf": 5694,
                                                    "hc": 2,
                                                    "cap": 2722,
                                                    "gap": -2972
                                                },
                                                "2025-07": {
                                                    "cf": 5712,
                                                    "hc": 2,
                                                    "cap": 2851,
                                                    "gap": -2861
                                                },
                                                "2025-08": {
                                                    "cf": 5693,
                                                    "hc": 2,
                                                    "cap": 2851,
                                                    "gap": -2842
                                                }
                                            },
                                            "children": []
                                        },
                                        {
                                            "id": "amisys-onshore-manual-MI-FTC",
                                            "name": "FTC",
                                            "level": 4,
                                            "has_children": False,
                                            "data": {
                                                "2025-03": {
                                                    "cf": 12270,
                                                    "hc": 2,
                                                    "cap": 4082,
                                                    "gap": -8188
                                                },
                                                "2025-04": {
                                                    "cf": 11889,
                                                    "hc": 2,
                                                    "cap": 4082,
                                                    "gap": -7807
                                                },
                                                "2025-05": {
                                                    "cf": 11758,
                                                    "hc": 2,
                                                    "cap": 4082,
                                                    "gap": -7676
                                                },
                                                "2025-06": {
                                                    "cf": 11686,
                                                    "hc": 2,
                                                    "cap": 4082,
                                                    "gap": -7604
                                                },
                                                "2025-07": {
                                                    "cf": 11690,
                                                    "hc": 2,
                                                    "cap": 4276,
                                                    "gap": -7414
                                                },
                                                "2025-08": {
                                                    "cf": 11640,
                                                    "hc": 2,
                                                    "cap": 4276,
                                                    "gap": -7364
                                                }
                                            },
                                            "children": []
                                        },
                                        {
                                            "id": "amisys-onshore-manual-MI-Appeals",
                                            "name": "Appeals",
                                            "level": 4,
                                            "has_children": False,
                                            "data": {
                                                "2025-03": {
                                                    "cf": 3433,
                                                    "hc": 0,
                                                    "cap": 0,
                                                    "gap": -3433
                                                },
                                                "2025-04": {
                                                    "cf": 3424,
                                                    "hc": 0,
                                                    "cap": 0,
                                                    "gap": -3424
                                                },
                                                "2025-05": {
                                                    "cf": 3420,
                                                    "hc": 0,
                                                    "cap": 0,
                                                    "gap": -3420
                                                },
                                                "2025-06": {
                                                    "cf": 3421,
                                                    "hc": 0,
                                                    "cap": 0,
                                                    "gap": -3421
                                                },
                                                "2025-07": {
                                                    "cf": 3476,
                                                    "hc": 0,
                                                    "cap": 0,
                                                    "gap": -3476
                                                },
                                                "2025-08": {
                                                    "cf": 3478,
                                                    "hc": 0,
                                                    "cap": 0,
                                                    "gap": -3478
                                                }
                                            },
                                            "children": []
                                        },
                                        {
                                            "id": "amisys-onshore-manual-MI-CORRES",
                                            "name": "CORRES",
                                            "level": 4,
                                            "has_children": False,
                                            "data": {
                                                "2025-03": {
                                                    "cf": 6956,
                                                    "hc": 0,
                                                    "cap": 0,
                                                    "gap": -6956
                                                },
                                                "2025-04": {
                                                    "cf": 7028,
                                                    "hc": 0,
                                                    "cap": 0,
                                                    "gap": -7028
                                                },
                                                "2025-05": {
                                                    "cf": 7013,
                                                    "hc": 0,
                                                    "cap": 0,
                                                    "gap": -7013
                                                },
                                                "2025-06": {
                                                    "cf": 7012,
                                                    "hc": 0,
                                                    "cap": 0,
                                                    "gap": -7012
                                                },
                                                "2025-07": {
                                                    "cf": 7114,
                                                    "hc": 0,
                                                    "cap": 0,
                                                    "gap": -7114
                                                },
                                                "2025-08": {
                                                    "cf": 7114,
                                                    "hc": 0,
                                                    "cap": 0,
                                                    "gap": -7114
                                                }
                                            },
                                            "children": []
                                        },
                                        {
                                            "id": "amisys-onshore-manual-MI-OMNI",
                                            "name": "OMNI",
                                            "level": 4,
                                            "has_children": False,
                                            "data": {
                                                "2025-03": {
                                                    "cf": 943,
                                                    "hc": 0,
                                                    "cap": 0,
                                                    "gap": -943
                                                },
                                                "2025-04": {
                                                    "cf": 832,
                                                    "hc": 0,
                                                    "cap": 0,
                                                    "gap": -832
                                                },
                                                "2025-05": {
                                                    "cf": 831,
                                                    "hc": 0,
                                                    "cap": 0,
                                                    "gap": -831
                                                },
                                                "2025-06": {
                                                    "cf": 831,
                                                    "hc": 0,
                                                    "cap": 0,
                                                    "gap": -831
                                                },
                                                "2025-07": {
                                                    "cf": 843,
                                                    "hc": 0,
                                                    "cap": 0,
                                                    "gap": -843
                                                },
                                                "2025-08": {
                                                    "cf": 843,
                                                    "hc": 0,
                                                    "cap": 0,
                                                    "gap": -843
                                                }
                                            },
                                            "children": []
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                {
                    "id": "facets",
                    "name": "Facets",
                    "level": 1,
                    "has_children": True,
                    "data": {
                        "2025-03": {
                            "cf": 249200,
                            "hc": 82,
                            "cap": 195275,
                            "gap": -53925
                        },
                        "2025-04": {
                            "cf": 261660,
                            "hc": 82,
                            "cap": 195275,
                            "gap": -66385
                        },
                        "2025-05": {
                            "cf": 261660,
                            "hc": 82,
                            "cap": 195275,
                            "gap": -66385
                        },
                        "2025-06": {
                            "cf": 261660,
                            "hc": 82,
                            "cap": 195275,
                            "gap": -66385
                        },
                        "2025-07": {
                            "cf": 286580,
                            "hc": 85,
                            "cap": 212057,
                            "gap": -74523
                        },
                        "2025-08": {
                            "cf": 236790,
                            "hc": 79,
                            "cap": 197089,
                            "gap": -39701
                        }
                    },
                    "children": [
                        {
                            "id": "facets-medicaid",
                            "name": "Medicaid",
                            "level": 2,
                            "has_children": False,
                            "data": {
                                "2025-03": {
                                    "cf": 249200,
                                    "hc": 82,
                                    "cap": 195275,
                                    "gap": -53925
                                },
                                "2025-04": {
                                    "cf": 261660,
                                    "hc": 82,
                                    "cap": 195275,
                                    "gap": -66385
                                },
                                "2025-05": {
                                    "cf": 261660,
                                    "hc": 82,
                                    "cap": 195275,
                                    "gap": -66385
                                },
                                "2025-06": {
                                    "cf": 261660,
                                    "hc": 82,
                                    "cap": 195275,
                                    "gap": -66385
                                },
                                "2025-07": {
                                    "cf": 286580,
                                    "hc": 85,
                                    "cap": 212057,
                                    "gap": -74523
                                },
                                "2025-08": {
                                    "cf": 236790,
                                    "hc": 79,
                                    "cap": 197089,
                                    "gap": -39701
                                }
                            },
                            "children": []
                        }
                    ]
                }
            ],
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
