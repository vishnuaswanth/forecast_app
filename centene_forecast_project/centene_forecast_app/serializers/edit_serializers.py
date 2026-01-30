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

        Input: {'success': True, 'months': {...}, 'modified_records': [...], 'total_modified': 15, 'summary': {...}}
        Output: Enhanced with timestamp

        Args:
            data: Raw preview data from repository

        Returns:
            Formatted response dict with summary statistics and months mapping

        Example:
            >>> data = {'success': True, 'months': {...}, 'modified_records': [...], 'total_modified': 15, 'summary': {...}}
            >>> response = EditViewSerializer.serialize_preview_response(data)
            >>> response['total_modified']
            15
        """
        try:
            modified_records = data.get('modified_records', [])
            total_modified = data.get('total_modified', len(modified_records))
            summary = data.get('summary', {
                'total_fte_change': 0,
                'total_capacity_change': 0
            })
            months = data.get('months', {})

            response = {
                'success': data.get('success', True),
                'months': months,
                'modified_records': modified_records,
                'total_modified': total_modified,
                'summary': summary,
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
        Serialize history log response with enhanced structure.

        Input: {'success': True, 'data': [...], 'pagination': {...}}
        Output: Enhanced with formatted timestamps and structured data

        Args:
            data: Raw history data from repository

        Returns:
            Formatted response dict with enhanced structure

        Example:
            >>> data = {'success': True, 'data': [...], 'pagination': {...}}
            >>> response = EditViewSerializer.serialize_history_log_response(data)
            >>> len(response['data']) > 0
            True
        """
        try:
            entries = data.get('data', [])

            # Enhanced formatting for each entry
            for entry in entries:
                # Format timestamps
                if 'timestamp' in entry:
                    entry['timestamp_formatted'] = _format_timestamp(entry['timestamp'])
                
                # Ensure report_title is present
                if not entry.get('report_title') and entry.get('change_type'):
                    month = entry.get('month', '')
                    year = entry.get('year', '')
                    entry['report_title'] = f"{entry['change_type']}, {month} {year}".strip(', ')
                
                # Ensure change_type_color is present
                if not entry.get('change_type_color'):
                    entry['change_type_color'] = _get_default_change_type_color(entry.get('change_type'))
                
                # Validate summary_data structure
                if entry.get('summary_data'):
                    summary = entry['summary_data']
                    # Ensure required fields exist
                    if not summary.get('months'):
                        summary['months'] = []
                    if not summary.get('totals'):
                        summary['totals'] = {}
                
                # Ensure records_modified is an integer
                if 'records_modified' in entry:
                    try:
                        entry['records_modified'] = int(entry['records_modified'])
                    except (ValueError, TypeError):
                        entry['records_modified'] = 0

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
    def serialize_error_response(error_message: str, status_code: int = 400, recommendation: Optional[str] = None) -> Dict:
        """
        Standard error response format.

        Args:
            error_message: Error description
            status_code: HTTP status code
            recommendation: Optional recommendation for user

        Returns:
            Formatted error response

        Example:
            >>> response = EditViewSerializer.serialize_error_response('Invalid input', 400)
            >>> response['success']
            False
            >>> response = EditViewSerializer.serialize_error_response('No data', 400, 'Check configuration')
            >>> response['recommendation']
            'Check configuration'
        """
        response = {
            'success': False,
            'error': error_message,
            'status_code': status_code,
            'timestamp': _get_timestamp()
        }

        # Include recommendation if provided
        if recommendation:
            response['recommendation'] = recommendation

        return response


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


def _get_default_change_type_color(change_type: str) -> str:
    """
    Get color for change type using predefined standard colors.

    Args:
        change_type: Type of change (e.g., 'Bench Allocation')

    Returns:
        Hex color code

    Example:
        >>> color = _get_default_change_type_color('Bench Allocation')
        >>> color
        '#0d6efd'
        >>> color = _get_default_change_type_color('New Change Type')
        >>> color.startswith('#')
        True
    """
    from centene_forecast_app.services.edit_service import get_change_type_color
    return get_change_type_color(change_type)


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


def serialize_error_response(error_message: str, status_code: int = 400, recommendation: Optional[str] = None) -> Dict:
    """
    Convenience function to serialize error response.

    Args:
        error_message: Error description
        status_code: HTTP status code
        recommendation: Optional recommendation for user

    Returns:
        Formatted error response

    Example:
        >>> from edit_serializers import serialize_error_response
        >>> response = serialize_error_response('Error occurred', 500)
        >>> response['success']
        False
        >>> response = serialize_error_response('No data', 400, 'Check settings')
        >>> response['recommendation']
        'Check settings'
    """
    return EditViewSerializer.serialize_error_response(error_message, status_code, recommendation)


# ============================================================
# TARGET CPH SERIALIZERS
# ============================================================

def serialize_target_cph_data_response(data: Dict) -> Dict[str, Any]:
    """
    Serialize CPH data response.

    Args:
        data: Raw CPH data from repository

    Returns:
        Formatted response dict

    Example:
        >>> data = {'success': True, 'data': [...], 'total': 12}
        >>> response = serialize_target_cph_data_response(data)
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

        logger.debug(f"[Serializer] CPH data: {response['total']} records")
        return response

    except Exception as e:
        logger.error(f"[Serializer] Error serializing CPH data: {e}")
        return serialize_error_response("Failed to serialize CPH data")


def serialize_target_cph_preview_response(data: Dict) -> Dict[str, Any]:
    """
    Serialize CPH preview response.

    This reuses the bench allocation preview serializer since
    the data structure is identical.

    Args:
        data: Raw preview data from repository

    Returns:
        Formatted response dict

    Example:
        >>> data = {'success': True, 'modified_records': [...], 'total_modified': 15}
        >>> response = serialize_target_cph_preview_response(data)
        >>> response['total_modified']
        15
    """
    # Reuse bench allocation preview serializer
    return serialize_preview_response(data)


def serialize_target_cph_update_response(data: Dict) -> Dict[str, Any]:
    """
    Serialize CPH update response.

    Args:
        data: Raw update response from repository

    Returns:
        Formatted response dict

    Example:
        >>> data = {'success': True, 'records_updated': 5, 'forecast_rows_affected': 15}
        >>> response = serialize_target_cph_update_response(data)
        >>> response['success']
        True
    """
    try:
        response = {
            'success': data.get('success', True),
            'message': data.get('message', 'CPH updated successfully'),
            'records_updated': data.get('records_updated', 0),
            'cph_changes_applied': data.get('cph_changes_applied', data.get('records_updated', 0)),
            'forecast_rows_affected': data.get('forecast_rows_affected', 0),
            'timestamp': _get_timestamp()
        }

        logger.debug(
            f"[Serializer] CPH update: {response['records_updated']} records, "
            f"{response['forecast_rows_affected']} forecast rows affected"
        )
        return response

    except Exception as e:
        logger.error(f"[Serializer] Error serializing CPH update: {e}")
        return serialize_error_response("Failed to serialize CPH update response")


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
