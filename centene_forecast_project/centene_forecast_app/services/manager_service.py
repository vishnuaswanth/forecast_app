"""
Manager View Service Layer

Business logic for manager view dashboard.
Handles KPI calculations using ManagerViewConfig settings.
"""

import logging
from typing import Dict, List, Optional
from core.config import ManagerViewConfig
from centene_forecast_app.repository import get_api_client

logger = logging.getLogger('django')


class ManagerViewService:
    """
    Service class for Manager View business logic.
    
    Encapsulates KPI calculations and data transformations.
    """
    
    @staticmethod
    def calculate_kpi_data(report_month: str, category: Optional[str] = None) -> Dict:
        """
        Calculate KPI summary card data for the specified report month.
        
        Uses ManagerViewConfig.KPI_MONTH_INDEX to determine which month's data
        to display in the summary cards (default: index 1 = second displayed month).
        
        Args:
            report_month: Report month in YYYY-MM format (e.g., '2025-02')
            category: Optional category filter (e.g., 'amisys-onshore')
            
        Returns:
            Dictionary containing KPI data:
            {
                'client_forecast': 10750,
                'head_count': 108,
                'capacity': 10260,
                'capacity_gap': -490,
                'kpi_month': '2025-03',
                'kpi_month_display': 'March 2025',
                'is_shortage': True  # True if gap < 0
            }
            
        Raises:
            ValueError: If data not found or invalid parameters
            
        Example:
            >>> service = ManagerViewService()
            >>> kpi = service.calculate_kpi_data('2025-02', 'amisys-onshore')
            >>> print(kpi['capacity_gap'])
            -490
        """
        logger.info(
            f"Calculating KPI data - report_month: {report_month}, category: {category or 'all'}"
        )
        
        # Get data from API client (currently using mock data)
        try:
            client = get_api_client()
            data = client.get_manager_view_data(report_month, category)
        except ValueError as e:
            logger.error(f"Failed to get manager view data: {str(e)}")
            raise
        
        # Get KPI month index from config (default: 1 = second month)
        kpi_index = ManagerViewConfig.KPI_MONTH_INDEX
        
        # Validate index is within range
        if kpi_index >= len(data['months']):
            logger.warning(
                f"KPI_MONTH_INDEX ({kpi_index}) exceeds available months "
                f"({len(data['months'])}). Using first month instead."
            )
            kpi_index = 0
        
        # Get the KPI month
        kpi_month = data['months'][kpi_index]
        logger.debug(f"Using KPI month: {kpi_month} (index {kpi_index})")
        
        # Calculate totals across all TOP-LEVEL categories for the KPI month
        # Note: Each top-level category's data already includes the sum of its children,
        # so we don't need to recursively sum children (that would be double-counting)
        total_cf = 0
        total_hc = 0
        total_cap = 0
        total_gap = 0
        
        # Only sum level-1 (top-level) categories
        # Their data already contains aggregated values from all descendants
        for cat in data['categories']:
            if kpi_month in cat['data']:
                month_data = cat['data'][kpi_month]
                total_cf += month_data['cf']
                total_hc += month_data['hc']
                total_cap += month_data['cap']
                total_gap += month_data['gap']
        
        # Format KPI month display name
        kpi_month_display = ManagerViewService._format_month_display(kpi_month)
        
        # Determine if there's a shortage
        is_shortage = total_gap < 0
        
        kpi_data = {
            'client_forecast': total_cf,
            'head_count': total_hc,
            'capacity': total_cap,
            'capacity_gap': total_gap,
            'kpi_month': kpi_month,
            'kpi_month_display': kpi_month_display,
            'is_shortage': is_shortage,
            'gap_percentage': round((abs(total_gap) / total_cf * 100), 2) if total_cf > 0 else 0
        }
        
        logger.info(
            f"KPI calculated - CF: {total_cf}, HC: {total_hc}, "
            f"Cap: {total_cap}, Gap: {total_gap} ({kpi_month_display})"
        )
        
        return kpi_data
    
    @staticmethod
    def _format_month_display(month_str: str) -> str:
        """
        Format month string from YYYY-MM to 'Month YYYY'.
        
        Args:
            month_str: Month in YYYY-MM format (e.g., '2025-03')
            
        Returns:
            Formatted month string (e.g., 'March 2025')
            
        Example:
            >>> ManagerViewService._format_month_display('2025-03')
            'March 2025'
        """
        months = {
            '01': 'January', '02': 'February', '03': 'March', '04': 'April',
            '05': 'May', '06': 'June', '07': 'July', '08': 'August',
            '09': 'September', '10': 'October', '11': 'November', '12': 'December'
        }
        
        try:
            year, month = month_str.split('-')
            return f"{months[month]} {year}"
        except (ValueError, KeyError):
            logger.warning(f"Invalid month format: {month_str}")
            return month_str
    
    @staticmethod
    def get_filter_options() -> Dict[str, List[Dict[str, str]]]:
        """
        Get available filter options for the manager view dropdowns.
        
        Returns:
            Dictionary containing filter options:
            {
                'report_months': [
                    {'value': '2025-02', 'display': 'February 2025'},
                    ...
                ],
                'categories': [
                    {'value': '', 'display': '-- All Categories --'},
                    {'value': 'amisys-onshore', 'display': 'Amisys Onshore'},
                    ...
                ]
            }
        """
        logger.info("Fetching filter options")
        
        try:
            client = get_api_client()
            filters = client.get_manager_view_filters()
            
            logger.debug(
                f"Retrieved {len(filters['report_months'])} report months, "
                f"{len(filters['categories'])} categories"
            )
            
            return filters
        
        except Exception as e:
            logger.error(f"Failed to get filter options: {str(e)}")
            # Return empty filters on error
            return {
                'report_months': [],
                'categories': [{'value': '', 'display': '-- All Categories --'}]
            }


# Convenience function for backward compatibility
def calculate_kpi_data(report_month: str, category: Optional[str] = None) -> Dict:
    """Convenience function to calculate KPI data"""
    service = ManagerViewService()
    return service.calculate_kpi_data(report_month, category)


def get_filter_options() -> Dict[str, List[Dict[str, str]]]:
    """Convenience function to get filter options"""
    service = ManagerViewService()
    return service.get_filter_options()
