# edit_serializers.py
"""
Serializers for Edit View API responses.

Follows the serializer pattern from manager_serializers.py.
All serializers transform data for JSON responses with consistent formatting.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger('django')


class EditViewSerializer:
    """Serializers for Edit View API responses"""

    @staticmethod
    def serialize_allocation_reports_response(data: Dict) -> Dict[str, Any]:
        """
        Serialize allocation reports dropdown response.

        Input: {'success': True, 'data': [...], 'total': 15}
        Output: Same structure with timestamp

        Args:
            data: Raw data from repository

        Returns:
            Formatted response dict

        Example:
            >>> data = {'success': True, 'data': [...], 'total': 15}
            >>> response = EditViewSerializer.serialize_allocation_reports_response(data)
            >>> response['timestamp']
            '2024-12-06T...'
        """
        try:
            response = {
                'success': data.get('success', True),
                'data': data.get('data', []),
                'total': data.get('total', len(data.get('data', []))),
                'timestamp': _get_timestamp()
            }

            logger.debug(f"[Serializer] Allocation reports: {response['total']} items")
            return response

        except Exception as e:
            logger.error(f"[Serializer] Error serializing reports: {e}")
            return serialize_error_response("Failed to serialize reports")

    @staticmethod
    def serialize_preview_response(data: Dict) -> Dict[str, Any]:
        """
        Serialize bench allocation preview response.

        Input: {'success': True, 'modified_records': [...], 'total_modified': 15}
        Output: Enhanced with timestamp

        Args:
            data: Raw preview data from repository

        Returns:
            Formatted response dict

        Example:
            >>> data = {'success': True, 'modified_records': [...], 'total_modified': 15}
            >>> response = EditViewSerializer.serialize_preview_response(data)
            >>> response['total_modified']
            15
        """
        try:
            modified_records = data.get('modified_records', [])
            total_modified = data.get('total_modified', len(modified_records))

            response = {
                'success': data.get('success', True),
                'modified_records': modified_records,
                'total_modified': total_modified,
                'message': data.get('message'),
                'timestamp': _get_timestamp()
            }

            logger.debug(f"[Serializer] Preview: {total_modified} modified records")
            return response

        except Exception as e:
            logger.error(f"[Serializer] Error serializing preview: {e}")
            return serialize_error_response("Failed to serialize preview")

    @staticmethod
    def serialize_update_response(data: Dict) -> Dict[str, Any]:
        """
        Serialize bench allocation update response.

        Input: {'success': True, 'message': '...', 'records_updated': 15}
        Output: Standard success response with timestamp

        Args:
            data: Raw update response from repository

        Returns:
            Formatted response dict

        Example:
            >>> data = {'success': True, 'records_updated': 15}
            >>> response = EditViewSerializer.serialize_update_response(data)
            >>> response['success']
            True
        """
        try:
            response = {
                'success': data.get('success', True),
                'message': data.get('message', 'Allocation updated successfully'),
                'records_updated': data.get('records_updated', 0),
                'timestamp': _get_timestamp()
            }

            logger.debug(f"[Serializer] Update: {response['records_updated']} records")
            return response

        except Exception as e:
            logger.error(f"[Serializer] Error serializing update: {e}")
            return serialize_error_response("Failed to serialize update response")

    @staticmethod
    def serialize_history_log_response(data: Dict) -> Dict[str, Any]:
        """
        Serialize history log response.

        Input: {'success': True, 'data': [...], 'pagination': {...}}
        Output: Enhanced with formatted timestamps

        Args:
            data: Raw history data from repository

        Returns:
            Formatted response dict with timestamp formatting

        Example:
            >>> data = {'success': True, 'data': [...], 'pagination': {...}}
            >>> response = EditViewSerializer.serialize_history_log_response(data)
            >>> len(response['data']) > 0
            True
        """
        try:
            entries = data.get('data', [])

            # Format timestamps in each entry
            for entry in entries:
                if 'timestamp' in entry:
                    entry['timestamp_formatted'] = _format_timestamp(entry['timestamp'])

            response = {
                'success': data.get('success', True),
                'data': entries,
                'pagination': data.get('pagination', {}),
                'timestamp': _get_timestamp()
            }

            logger.debug(f"[Serializer] History log: {len(entries)} entries")
            return response

        except Exception as e:
            logger.error(f"[Serializer] Error serializing history: {e}")
            return serialize_error_response("Failed to serialize history log")

    @staticmethod
    def serialize_error_response(error_message: str, status_code: int = 400) -> Dict:
        """
        Standard error response format.

        Args:
            error_message: Error description
            status_code: HTTP status code

        Returns:
            Formatted error response

        Example:
            >>> response = EditViewSerializer.serialize_error_response('Invalid input', 400)
            >>> response['success']
            False
        """
        return {
            'success': False,
            'error': error_message,
            'status_code': status_code,
            'timestamp': _get_timestamp()
        }


# Helper functions
def _get_timestamp() -> str:
    """
    Get current timestamp in ISO format.

    Returns:
        ISO format timestamp string

    Example:
        >>> timestamp = _get_timestamp()
        >>> '2024' in timestamp
        True
    """
    return datetime.now().isoformat()


def _format_timestamp(timestamp_str: str) -> str:
    """
    Format timestamp for display (e.g., 'Dec 5, 2024 2:30 PM').

    Args:
        timestamp_str: ISO format timestamp string

    Returns:
        Formatted timestamp for display

    Example:
        >>> formatted = _format_timestamp('2024-12-05T14:30:00')
        >>> 'Dec' in formatted
        True
    """
    try:
        # Handle both ISO format with/without timezone
        timestamp_str = timestamp_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime('%b %d, %Y %I:%M %p')
    except Exception as e:
        logger.warning(f"Failed to format timestamp '{timestamp_str}': {e}")
        return timestamp_str


# Convenience functions for direct import
def serialize_allocation_reports_response(data: Dict) -> Dict[str, Any]:
    """
    Convenience function to serialize allocation reports response.

    Args:
        data: Raw data from repository

    Returns:
        Formatted response

    Example:
        >>> from edit_serializers import serialize_allocation_reports_response
        >>> response = serialize_allocation_reports_response({'data': [...], 'total': 15})
        >>> response['success']
        True
    """
    return EditViewSerializer.serialize_allocation_reports_response(data)


def serialize_preview_response(data: Dict) -> Dict[str, Any]:
    """
    Convenience function to serialize preview response.

    Args:
        data: Raw preview data

    Returns:
        Formatted response

    Example:
        >>> from edit_serializers import serialize_preview_response
        >>> response = serialize_preview_response({'modified_records': [...], 'total_modified': 15})
        >>> response['total_modified']
        15
    """
    return EditViewSerializer.serialize_preview_response(data)


def serialize_update_response(data: Dict) -> Dict[str, Any]:
    """
    Convenience function to serialize update response.

    Args:
        data: Raw update data

    Returns:
        Formatted response

    Example:
        >>> from edit_serializers import serialize_update_response
        >>> response = serialize_update_response({'success': True, 'records_updated': 15})
        >>> response['records_updated']
        15
    """
    return EditViewSerializer.serialize_update_response(data)


def serialize_history_log_response(data: Dict) -> Dict[str, Any]:
    """
    Convenience function to serialize history log response.

    Args:
        data: Raw history data

    Returns:
        Formatted response

    Example:
        >>> from edit_serializers import serialize_history_log_response
        >>> response = serialize_history_log_response({'data': [...], 'pagination': {...}})
        >>> len(response['data']) >= 0
        True
    """
    return EditViewSerializer.serialize_history_log_response(data)


def serialize_error_response(error_message: str, status_code: int = 400) -> Dict:
    """
    Convenience function to serialize error response.

    Args:
        error_message: Error description
        status_code: HTTP status code

    Returns:
        Formatted error response

    Example:
        >>> from edit_serializers import serialize_error_response
        >>> response = serialize_error_response('Error occurred', 500)
        >>> response['success']
        False
    """
    return EditViewSerializer.serialize_error_response(error_message, status_code)


# Example usage:
# from edit_serializers import (
#     serialize_allocation_reports_response,
#     serialize_preview_response,
#     serialize_update_response,
#     serialize_history_log_response,
#     serialize_error_response
# )
#
# # Serialize allocation reports
# reports_data = {'success': True, 'data': [...], 'total': 15}
# reports_response = serialize_allocation_reports_response(reports_data)
#
# # Serialize preview
# preview_data = {'success': True, 'modified_records': [...], 'total_modified': 15}
# preview_response = serialize_preview_response(preview_data)
#
# # Serialize error
# error_response = serialize_error_response('Validation failed', 400)