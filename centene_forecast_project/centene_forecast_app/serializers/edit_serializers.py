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

        Input: {'success': True, 'months': {...}, 'month': '...', 'year': ..., 'modified_records': [...], 'total_modified': 15, 'summary': {...}}
        Output: Enhanced with timestamp, passing through all API spec fields

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
                'months': data.get('months'),
                'month': data.get('month'),
                'year': data.get('year'),
                'modified_records': modified_records,
                'total_modified': total_modified,
                'summary': data.get('summary'),
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

        Input: {'success': True, 'message': '...', 'records_updated': 15, 'history_log_id': '...'}
        Output: Standard success response with timestamp and history_log_id

        Args:
            data: Raw update response from repository

        Returns:
            Formatted response dict

        Example:
            >>> data = {'success': True, 'records_updated': 15, 'history_log_id': 'uuid-123'}
            >>> response = EditViewSerializer.serialize_update_response(data)
            >>> response['success']
            True
        """
        try:
            response = {
                'success': data.get('success', True),
                'message': data.get('message', 'Allocation updated successfully'),
                'records_updated': data.get('records_updated', 0),
                'history_log_id': data.get('history_log_id'),
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

        Input: {'success': True, 'data': [...], 'total': 127, 'page': 1, 'limit': 25, 'has_more': True}
        Output: Flat pagination structure with formatted timestamps

        Args:
            data: Raw history data from repository

        Returns:
            Formatted response dict with flat pagination

        Example:
            >>> data = {'success': True, 'data': [...], 'total': 127, 'page': 1, 'limit': 25, 'has_more': True}
            >>> response = EditViewSerializer.serialize_history_log_response(data)
            >>> len(response['data']) > 0
            True
        """
        try:
            entries = data.get('data', [])

            # Format timestamps in each entry (created_at field per API spec)
            for entry in entries:
                if 'created_at' in entry:
                    entry['created_at_formatted'] = _format_timestamp(entry['created_at'])
                # Support legacy timestamp field as well
                elif 'timestamp' in entry:
                    entry['timestamp_formatted'] = _format_timestamp(entry['timestamp'])

            # Extract pagination - support both flat and nested formats
            pagination = data.get('pagination', {})
            response = {
                'success': data.get('success', True),
                'data': entries,
                'total': data.get('total') or pagination.get('total', 0),
                'page': data.get('page') or pagination.get('page', 1),
                'limit': data.get('limit') or pagination.get('limit', 25),
                'has_more': data.get('has_more') if 'has_more' in data else pagination.get('has_more', False),
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