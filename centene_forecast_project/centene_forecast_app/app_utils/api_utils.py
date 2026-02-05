"""
API Response Utilities

Provides helper functions for handling API responses from repository methods.
"""

import logging
from typing import Any, Dict, Optional, Tuple
from django.http import JsonResponse

logger = logging.getLogger('django')


def is_api_error(response: Any) -> bool:
    """
    Check if an API response is an error response.

    Error responses from _make_request have format:
    {
        'success': False,
        'error': 'error message',
        'status_code': 400
    }

    Args:
        response: Response from repository method

    Returns:
        True if response indicates an error, False otherwise
    """
    if not isinstance(response, dict):
        return False
    return response.get('success') is False and 'error' in response


def get_api_error_response(response: Dict, default_status: int = 500) -> JsonResponse:
    """
    Convert an API error response to a Django JsonResponse.

    Args:
        response: Error response dict from repository
        default_status: Default HTTP status if not in response

    Returns:
        JsonResponse with appropriate status code
    """
    status_code = response.get('status_code', default_status)
    error_message = response.get('error', 'Unknown error')

    return JsonResponse({
        'success': False,
        'error': error_message
    }, status=status_code)


def handle_api_response(response: Any, default_status: int = 500) -> Optional[JsonResponse]:
    """
    Check API response and return JsonResponse if it's an error.

    This is a convenience function that combines is_api_error and get_api_error_response.
    Use in views to handle API errors gracefully:

        data = client.get_manager_view_data(...)
        error_response = handle_api_response(data)
        if error_response:
            return error_response
        # Continue with normal processing...

    Args:
        response: Response from repository method
        default_status: Default HTTP status for errors

    Returns:
        JsonResponse if error, None if response is valid
    """
    if is_api_error(response):
        return get_api_error_response(response, default_status)
    return None


def extract_api_data(response: Any, data_key: str = 'data') -> Tuple[Any, Optional[str]]:
    """
    Extract data from API response, handling both success and error cases.

    Args:
        response: Response from repository method
        data_key: Key to extract data from (default: 'data')

    Returns:
        Tuple of (data, error_message)
        - On success: (data, None)
        - On error: (None, error_message)
    """
    if is_api_error(response):
        return None, response.get('error', 'Unknown error')

    if isinstance(response, dict):
        # Try to extract nested data, or return the whole response
        return response.get(data_key, response), None

    return response, None
