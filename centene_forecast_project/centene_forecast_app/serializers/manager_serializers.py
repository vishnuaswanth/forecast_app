"""
Manager View Serializers

Handles JSON serialization for manager view API responses.
Formats data structures for frontend consumption.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger('django')


class ManagerViewSerializer:
    """
    Serializer for Manager View API responses.
    
    Converts internal data structures to JSON-ready formats
    that match frontend expectations.
    """
    
    @staticmethod
    def serialize_data_response(data: Dict) -> Dict[str, Any]:
        """
        Serialize table data for frontend consumption.
        
        Args:
            data: Raw data from repository containing:
                - report_month: str
                - months: List[str]
                - categories: List[Dict]
                - category_name: str
                
        Returns:
            JSON-ready dictionary with formatted data
            
        Example:
            {
                'success': True,
                'report_month': '2025-02',
                'report_month_display': 'February 2025',
                'category_name': 'Amisys Onshore',
                'months': ['2025-02', '2025-03', ...],
                'months_display': ['Feb 2025', 'Mar 2025', ...],
                'categories': [...],
                'total_categories': 3
            }
        """
        try:
            # Format month displays
            months_display = [
                ManagerViewSerializer._format_short_month(m) 
                for m in data['months']
            ]
            
            # Format report month display
            report_month_display = ManagerViewSerializer._format_long_month(
                data['report_month']
            )
            
            response = {
                'success': True,
                'report_month': data['report_month'],
                'report_month_display': report_month_display,
                'category_name': data.get('category_name', 'All Categories'),
                'months': data['months'],
                'months_display': months_display,
                'categories': data['categories'],
                'total_categories': len(data['categories']),
                'timestamp': ManagerViewSerializer._get_timestamp()
            }
            
            logger.debug(
                f"Serialized data response - {response['total_categories']} categories, "
                f"{len(response['months'])} months"
            )
            
            return response
            
        except KeyError as e:
            logger.error(f"Missing required field in data: {str(e)}")
            return ManagerViewSerializer.serialize_error_response(
                f"Invalid data structure: missing {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error serializing data response: {str(e)}")
            return ManagerViewSerializer.serialize_error_response(
                "Failed to serialize data"
            )
    
    @staticmethod
    def serialize_kpi_response(kpi_data: Dict) -> Dict[str, Any]:
        """
        Serialize KPI summary card data for frontend.
        
        Args:
            kpi_data: KPI data from service containing:
                - client_forecast: int
                - head_count: int
                - capacity: int
                - capacity_gap: int
                - kpi_month: str
                - kpi_month_display: str
                - is_shortage: bool
                
        Returns:
            JSON-ready dictionary with formatted KPI data
            
        Example:
            {
                'success': True,
                'kpi': {
                    'client_forecast': 10750,
                    'client_forecast_formatted': '10,750',
                    'head_count': 108,
                    'capacity': 10260,
                    'capacity_gap': -490,
                    'capacity_gap_formatted': '-490',
                    'kpi_month_display': 'March 2025',
                    'is_shortage': True,
                    'status_message': '⚠️ Shortage in March 2025',
                    'gap_percentage': 4.56
                }
            }
        """
        try:
            # Format numbers with commas
            formatted_kpi = {
                'client_forecast': kpi_data['client_forecast'],
                'client_forecast_formatted': f"{kpi_data['client_forecast']:,}",
                'head_count': kpi_data['head_count'],
                'head_count_formatted': f"{kpi_data['head_count']:,}",
                'capacity': kpi_data['capacity'],
                'capacity_formatted': f"{kpi_data['capacity']:,}",
                'capacity_gap': kpi_data['capacity_gap'],
                'capacity_gap_formatted': f"{kpi_data['capacity_gap']:,}",
                'kpi_month': kpi_data['kpi_month'],
                'kpi_month_display': kpi_data['kpi_month_display'],
                'is_shortage': kpi_data['is_shortage'],
                'gap_percentage': kpi_data.get('gap_percentage', 0)
            }
            
            # Add status message
            if kpi_data['is_shortage']:
                formatted_kpi['status_message'] = (
                    f"[WARNING] Shortage in {kpi_data['kpi_month_display']}"
                )
                formatted_kpi['status_class'] = 'text-danger'
            else:
                formatted_kpi['status_message'] = (
                    f"Surplus in {kpi_data['kpi_month_display']}"
                )
                formatted_kpi['status_class'] = 'text-success'
            
            response = {
                'success': True,
                'kpi': formatted_kpi,
                'timestamp': ManagerViewSerializer._get_timestamp()
            }
            
            logger.debug(
                f"Serialized KPI response - Gap: {formatted_kpi['capacity_gap_formatted']}, "
                f"Month: {formatted_kpi['kpi_month_display']}"
            )
            
            return response
            
        except KeyError as e:
            logger.error(f"Missing required field in KPI data: {str(e)}")
            return ManagerViewSerializer.serialize_error_response(
                f"Invalid KPI data structure: missing {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error serializing KPI response: {str(e)}")
            return ManagerViewSerializer.serialize_error_response(
                "Failed to serialize KPI data"
            )
    
    @staticmethod
    def serialize_error_response(error_message: str, status_code: int = 400) -> Dict[str, Any]:
        """
        Serialize error response for API endpoints.
        
        Args:
            error_message: Human-readable error message
            status_code: HTTP status code (default: 400)
            
        Returns:
            JSON-ready error response
            
        Example:
            {
                'success': False,
                'error': 'Invalid report month format',
                'status_code': 400,
                'timestamp': '2025-10-16T15:30:00'
            }
        """
        response = {
            'success': False,
            'error': error_message,
            'status_code': status_code,
            'timestamp': ManagerViewSerializer._get_timestamp()
        }
        
        logger.warning(f"Error response: {error_message} (status: {status_code})")
        
        return response
    
    @staticmethod
    def _format_short_month(month_str: str) -> str:
        """
        Format month as 'MMM YYYY' (e.g., 'Feb 2025').
        
        Args:
            month_str: Month in YYYY-MM format
            
        Returns:
            Short formatted month string
        """
        months = {
            '01': 'Jan', '02': 'Feb', '03': 'Mar', '04': 'Apr',
            '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Aug',
            '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec'
        }
        
        try:
            year, month = month_str.split('-')
            return f"{months[month]} {year}"
        except (ValueError, KeyError):
            return month_str
    
    @staticmethod
    def _format_long_month(month_str: str) -> str:
        """
        Format month as 'Month YYYY' (e.g., 'February 2025').
        
        Args:
            month_str: Month in YYYY-MM format
            
        Returns:
            Long formatted month string
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
            return month_str
    
    @staticmethod
    def _get_timestamp() -> str:
        """
        Get current timestamp in ISO format.
        
        Returns:
            ISO formatted timestamp string
        """
        from datetime import datetime
        return datetime.now().isoformat()


# Convenience functions for direct use
def serialize_data_response(data: Dict) -> Dict[str, Any]:
    """Serialize table data response"""
    return ManagerViewSerializer.serialize_data_response(data)


def serialize_kpi_response(kpi_data: Dict) -> Dict[str, Any]:
    """Serialize KPI response"""
    return ManagerViewSerializer.serialize_kpi_response(kpi_data)


def serialize_error_response(error_message: str, status_code: int = 400) -> Dict[str, Any]:
    """Serialize error response"""
    return ManagerViewSerializer.serialize_error_response(error_message, status_code)
