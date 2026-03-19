"""
Data View Serializers

Handles JSON serialization for Data view API responses.
Formats cascading dropdown data structures for frontend consumption.
"""

import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger('django')


class ForecastSerializer:
    """
    Serializer for Forecast View API responses.

    Converts internal data structures to JSON-ready formats
    for cascading dropdown functionality.
    """

    @staticmethod
    def serialize_filter_options_response(
        options: Dict[str, List[Dict[str, str]]]
    ) -> Dict[str, Any]:
        """
        Serialize initial filter options (years) for frontend.

        Args:
            options: Dictionary with filter options from repository

        Returns:
            JSON-ready dictionary with formatted options

        Example:
            {
                'success': True,
                'years': [
                    {'value': '2025', 'display': '2025'},
                    {'value': '2024', 'display': '2024'}
                ],
                'timestamp': '2025-10-22T15:30:00'
            }
        """
        try:
            response = {
                'success': True,
                'years': options.get('years', []),
                'timestamp': ForecastSerializer._get_timestamp()
            }

            logger.debug(f"Serialized filter options - {len(response['years'])} years")

            return response

        except Exception as e:
            logger.error(f"Error serializing filter options: {str(e)}")
            return ForecastSerializer.serialize_error_response(
                "Failed to serialize filter options"
            )

    @staticmethod
    def serialize_cascade_response(
        options: List[Dict[str, str]],
        option_type: str
    ) -> Dict[str, Any]:
        """
        Serialize cascading dropdown options for frontend.

        Args:
            options: List of option dictionaries with 'value' and 'display' keys
            option_type: Type of options (e.g., 'months', 'platforms', 'markets')

        Returns:
            JSON-ready dictionary with formatted cascade data

        Example:
            {
                'success': True,
                'type': 'months',
                'options': [
                    {'value': '1', 'display': 'January'},
                    {'value': '2', 'display': 'February'}
                ],
                'count': 2,
                'timestamp': '2025-10-22T15:30:00'
            }
        """
        try:
            response = {
                'success': True,
                'type': option_type,
                'options': options,
                'count': len(options),
                'timestamp': ForecastSerializer._get_timestamp()
            }

            logger.debug(
                f"Serialized cascade response - "
                f"{option_type}: {len(options)} options"
            )

            return response

        except Exception as e:
            logger.error(f"Error serializing cascade response: {str(e)}")
            return ForecastSerializer.serialize_error_response(
                f"Failed to serialize {option_type} options"
            )

    @staticmethod
    def serialize_error_response(
        error_message: str,
        status_code: int = 400
    ) -> Dict[str, Any]:
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
                'error': 'Invalid year parameter',
                'status_code': 400,
                'timestamp': '2025-10-22T15:30:00'
            }
        """
        response = {
            'success': False,
            'error': error_message,
            'status_code': status_code,
            'timestamp': ForecastSerializer._get_timestamp()
        }

        logger.warning(f"Error response: {error_message} (status: {status_code})")

        return response

    @staticmethod
    def _get_timestamp() -> str:
        """
        Get current timestamp in ISO format.

        Returns:
            ISO formatted timestamp string
        """
        return datetime.now().isoformat()


# Convenience functions for direct use
def serialize_filter_options_response(
    options: Dict[str, List[Dict[str, str]]]
) -> Dict[str, Any]:
    """Serialize initial filter options response"""
    return ForecastSerializer.serialize_filter_options_response(options)


def serialize_cascade_response(
    options: List[Dict[str, str]],
    option_type: str
) -> Dict[str, Any]:
    """Serialize cascading dropdown response"""
    return ForecastSerializer.serialize_cascade_response(options, option_type)


def serialize_error_response(
    error_message: str,
    status_code: int = 400
) -> Dict[str, Any]:
    """Serialize error response"""
    return ForecastSerializer.serialize_error_response(error_message, status_code)