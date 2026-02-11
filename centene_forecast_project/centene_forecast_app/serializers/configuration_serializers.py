# configuration_serializers.py
"""
Serializers for Configuration View API responses.

Follows the serializer pattern from edit_serializers.py.
All serializers transform data for JSON responses with consistent formatting.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger('django')


def _get_timestamp() -> str:
    """
    Get current timestamp in ISO format.

    Returns:
        ISO format timestamp string
    """
    return datetime.now().isoformat()


def _format_datetime(dt_str: str) -> str:
    """
    Format datetime string for display.

    Args:
        dt_str: ISO format datetime string

    Returns:
        Formatted datetime for display (e.g., 'Jan 15, 2025 2:30 PM')
    """
    try:
        if not dt_str:
            return ''
        dt_str = dt_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime('%b %d, %Y %I:%M %p')
    except Exception as e:
        logger.warning(f"Failed to format datetime '{dt_str}': {e}")
        return dt_str or ''


class ConfigurationSerializer:
    """Serializers for Configuration View API responses"""

    @staticmethod
    def serialize_month_config_list(data: Dict) -> Dict[str, Any]:
        """
        Serialize month configuration list response.

        Args:
            data: Raw data from repository (API spec format: {success, data: {count, configurations: [...]}})

        Returns:
            Formatted response dict with configurations and metadata

        Example:
            >>> data = {'success': True, 'data': {'count': 50, 'configurations': [...]}}
            >>> response = ConfigurationSerializer.serialize_month_config_list(data)
        """
        try:
            # Handle API spec format: data.data.configurations
            raw_data = data.get('data', {})
            if isinstance(raw_data, dict):
                configs = raw_data.get('configurations', [])
                count = raw_data.get('count', len(configs))
            else:
                # Fallback for flat array format
                configs = raw_data if isinstance(raw_data, list) else []
                count = len(configs)

            # Format each configuration
            for config in configs:
                # Map API field names to display names
                # API uses: created_datetime, updated_datetime
                # We normalize to: updated_date for display
                if config.get('updated_datetime'):
                    config['updated_date'] = config['updated_datetime']
                    config['updated_date_formatted'] = _format_datetime(config['updated_datetime'])
                elif config.get('updated_date'):
                    config['updated_date_formatted'] = _format_datetime(config['updated_date'])

                # Ensure numeric fields are properly typed
                if 'occupancy' in config:
                    config['occupancy'] = float(config['occupancy']) if config['occupancy'] is not None else None
                if 'shrinkage' in config:
                    config['shrinkage'] = float(config['shrinkage']) if config['shrinkage'] is not None else None
                if 'work_hours' in config:
                    config['work_hours'] = float(config['work_hours']) if config['work_hours'] is not None else None

            response = {
                'success': data.get('success', True),
                'data': configs,
                'total': count,
                'timestamp': _get_timestamp()
            }

            logger.debug(f"[Serializer] Month config list: {response['total']} items")
            return response

        except Exception as e:
            logger.error(f"[Serializer] Error serializing month config list: {e}")
            return serialize_error_response("Failed to serialize month configurations")

    @staticmethod
    def serialize_month_config_response(data: Dict) -> Dict[str, Any]:
        """
        Serialize single month configuration response (create/update).

        Args:
            data: Raw response from repository

        Returns:
            Formatted response dict

        Example:
            >>> data = {'success': True, 'data': {...}, 'message': 'Created'}
            >>> response = ConfigurationSerializer.serialize_month_config_response(data)
        """
        try:
            config = data.get('data', {})

            # Format updated_date for display
            if config.get('updated_date'):
                config['updated_date_formatted'] = _format_datetime(config['updated_date'])

            response = {
                'success': data.get('success', True),
                'data': config,
                'message': data.get('message', 'Operation successful'),
                'timestamp': _get_timestamp()
            }

            logger.debug(f"[Serializer] Month config response: {response['message']}")
            return response

        except Exception as e:
            logger.error(f"[Serializer] Error serializing month config response: {e}")
            return serialize_error_response("Failed to serialize month configuration")

    @staticmethod
    def serialize_validation_response(data: Dict) -> Dict[str, Any]:
        """
        Serialize month configuration validation response.

        Args:
            data: Validation result from repository (API spec format: {success, data: {...}})

        Returns:
            Formatted response with validation results

        Example:
            >>> data = {'success': True, 'data': {'is_valid': False, 'orphaned_records': [...]}}
            >>> response = ConfigurationSerializer.serialize_validation_response(data)
        """
        try:
            # Handle API spec format: data.data contains the validation results
            raw_data = data.get('data', data)
            if isinstance(raw_data, dict) and 'is_valid' in raw_data:
                validation_data = raw_data
            else:
                validation_data = data

            orphaned = validation_data.get('orphaned_records', [])

            # Format orphaned records for display
            for record in orphaned:
                if record.get('updated_datetime'):
                    record['updated_date'] = record['updated_datetime']
                    record['updated_date_formatted'] = _format_datetime(record['updated_datetime'])
                elif record.get('updated_date'):
                    record['updated_date_formatted'] = _format_datetime(record['updated_date'])

            # Get recommendations from API response
            recommendations = validation_data.get('recommendations', [])
            recommendation_text = '; '.join(recommendations) if recommendations else validation_data.get('recommendation')

            response = {
                'success': data.get('success', True),
                'is_valid': validation_data.get('is_valid', len(orphaned) == 0),
                'orphaned_count': validation_data.get('orphaned_count', len(orphaned)),
                'orphaned_records': orphaned,
                'total_configs': validation_data.get('total_configs', 0),
                'paired_count': validation_data.get('paired_count', 0),
                'message': validation_data.get('message'),
                'recommendation': recommendation_text,
                'timestamp': _get_timestamp()
            }

            logger.debug(f"[Serializer] Validation response: {response['orphaned_count']} orphaned records")
            return response

        except Exception as e:
            logger.error(f"[Serializer] Error serializing validation response: {e}")
            return serialize_error_response("Failed to serialize validation response")

    @staticmethod
    def serialize_target_cph_list(data: Dict) -> Dict[str, Any]:
        """
        Serialize Target CPH configuration list response.

        Args:
            data: Raw data from repository (API spec format: {success, data: {count, configurations: [...]}})

        Returns:
            Formatted response dict with configurations and metadata

        Example:
            >>> data = {'success': True, 'data': {'count': 50, 'configurations': [...]}}
            >>> response = ConfigurationSerializer.serialize_target_cph_list(data)
        """
        try:
            # Handle API spec format: data.data.configurations
            raw_data = data.get('data', {})
            if isinstance(raw_data, dict):
                configs = raw_data.get('configurations', [])
                count = raw_data.get('count', len(configs))
            else:
                # Fallback for flat array format
                configs = raw_data if isinstance(raw_data, list) else []
                count = len(configs)

            # Format each configuration
            for config in configs:
                # Map API field names to display names
                # API uses: created_datetime, updated_datetime
                if config.get('updated_datetime'):
                    config['updated_date'] = config['updated_datetime']
                    config['updated_date_formatted'] = _format_datetime(config['updated_datetime'])
                elif config.get('updated_date'):
                    config['updated_date_formatted'] = _format_datetime(config['updated_date'])

                # Ensure target_cph is properly typed
                if 'target_cph' in config:
                    config['target_cph'] = float(config['target_cph']) if config['target_cph'] is not None else None

            response = {
                'success': data.get('success', True),
                'data': configs,
                'total': count,
                'timestamp': _get_timestamp()
            }

            logger.debug(f"[Serializer] Target CPH list: {response['total']} items")
            return response

        except Exception as e:
            logger.error(f"[Serializer] Error serializing Target CPH list: {e}")
            return serialize_error_response("Failed to serialize Target CPH configurations")

    @staticmethod
    def serialize_target_cph_response(data: Dict) -> Dict[str, Any]:
        """
        Serialize single Target CPH configuration response (create/update).

        Args:
            data: Raw response from repository

        Returns:
            Formatted response dict

        Example:
            >>> data = {'success': True, 'data': {...}, 'message': 'Created'}
            >>> response = ConfigurationSerializer.serialize_target_cph_response(data)
        """
        try:
            config = data.get('data', {})

            # Format updated_date for display
            if config.get('updated_date'):
                config['updated_date_formatted'] = _format_datetime(config['updated_date'])

            response = {
                'success': data.get('success', True),
                'data': config,
                'message': data.get('message', 'Operation successful'),
                'timestamp': _get_timestamp()
            }

            logger.debug(f"[Serializer] Target CPH response: {response['message']}")
            return response

        except Exception as e:
            logger.error(f"[Serializer] Error serializing Target CPH response: {e}")
            return serialize_error_response("Failed to serialize Target CPH configuration")

    @staticmethod
    def serialize_distinct_values(data: Dict, value_key: str = 'values') -> Dict[str, Any]:
        """
        Serialize distinct values response for dropdowns.

        Args:
            data: Raw distinct values from repository
                  (API spec format: {success, data: {count, main_lobs: [...]}} or {count, case_types: [...]})
            value_key: Key to use for extracting values ('main_lobs' or 'case_types')

        Returns:
            Formatted response with value/display pairs

        Example:
            >>> data = {'success': True, 'data': {'count': 10, 'main_lobs': [...]}}
            >>> response = ConfigurationSerializer.serialize_distinct_values(data, 'main_lobs')
        """
        try:
            raw_data = data.get('data', {})

            # Handle API spec format: data.data.main_lobs or data.data.case_types
            if isinstance(raw_data, dict):
                # Try to find the values array in the nested data
                values = raw_data.get('main_lobs') or raw_data.get('case_types') or raw_data.get(value_key, [])
                count = raw_data.get('count', len(values))
            else:
                # Fallback for flat array format
                values = raw_data if isinstance(raw_data, list) else []
                count = len(values)

            # Ensure consistent format - convert strings to value/display pairs
            formatted_values = []
            for value in values:
                if isinstance(value, dict):
                    formatted_values.append(value)
                else:
                    # Convert string to value/display pair
                    formatted_values.append({
                        'value': value,
                        'display': value
                    })

            response = {
                'success': data.get('success', True),
                'data': formatted_values,
                'total': count,
                'timestamp': _get_timestamp()
            }

            logger.debug(f"[Serializer] Distinct values: {response['total']} items")
            return response

        except Exception as e:
            logger.error(f"[Serializer] Error serializing distinct values: {e}")
            return serialize_error_response("Failed to serialize distinct values")

    @staticmethod
    def serialize_bulk_response(data: Dict) -> Dict[str, Any]:
        """
        Serialize bulk create response.

        Args:
            data: Bulk operation result from repository
                  (API spec format: {success, data: {total, succeeded, failed, errors}, message})

        Returns:
            Formatted response with created count and any errors

        Example:
            >>> data = {'success': True, 'data': {'total': 10, 'succeeded': 10, 'failed': 0}}
            >>> response = ConfigurationSerializer.serialize_bulk_response(data)
        """
        try:
            # Handle API spec format: data.data contains the bulk operation stats
            raw_data = data.get('data', {})
            if isinstance(raw_data, dict):
                created_count = raw_data.get('succeeded', raw_data.get('created_count', 0))
                skipped_count = raw_data.get('duplicates_skipped', raw_data.get('skipped_count', 0))
                failed_count = raw_data.get('failed', 0)
                errors = raw_data.get('errors', []) + raw_data.get('validation_errors', [])
            else:
                created_count = data.get('created_count', 0)
                skipped_count = data.get('skipped_count', 0)
                failed_count = data.get('failed', 0)
                errors = data.get('errors', [])

            response = {
                'success': data.get('success', True),
                'created_count': created_count,
                'skipped_count': skipped_count,
                'failed_count': failed_count,
                'errors': errors,
                'message': data.get('message', 'Bulk operation completed'),
                'timestamp': _get_timestamp()
            }

            logger.debug(
                f"[Serializer] Bulk response: {response['created_count']} created, "
                f"{response['skipped_count']} skipped, {response['failed_count']} failed"
            )
            return response

        except Exception as e:
            logger.error(f"[Serializer] Error serializing bulk response: {e}")
            return serialize_error_response("Failed to serialize bulk response")

    @staticmethod
    def serialize_delete_response(data: Dict) -> Dict[str, Any]:
        """
        Serialize delete response.

        Args:
            data: Delete operation result from repository

        Returns:
            Formatted response

        Example:
            >>> data = {'success': True, 'message': 'Deleted successfully'}
            >>> response = ConfigurationSerializer.serialize_delete_response(data)
        """
        try:
            response = {
                'success': data.get('success', True),
                'message': data.get('message', 'Deleted successfully'),
                'timestamp': _get_timestamp()
            }

            # Include orphan warning if present
            if data.get('orphan_warning'):
                response['orphan_warning'] = data['orphan_warning']

            logger.debug(f"[Serializer] Delete response: {response['message']}")
            return response

        except Exception as e:
            logger.error(f"[Serializer] Error serializing delete response: {e}")
            return serialize_error_response("Failed to serialize delete response")

    @staticmethod
    def serialize_error_response(
        message: str,
        status_code: int = 400,
        recommendation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Serialize error response.

        Args:
            message: Error message
            status_code: HTTP status code
            recommendation: Optional recommendation for user

        Returns:
            Formatted error response

        Example:
            >>> response = ConfigurationSerializer.serialize_error_response('Invalid data', 400)
            >>> response['success']
            False
        """
        response = {
            'success': False,
            'error': message,
            'status_code': status_code,
            'timestamp': _get_timestamp()
        }

        if recommendation:
            response['recommendation'] = recommendation

        return response


# Convenience functions for direct import

def serialize_month_config_list(data: Dict) -> Dict[str, Any]:
    """Serialize month configuration list response."""
    return ConfigurationSerializer.serialize_month_config_list(data)


def serialize_month_config_response(data: Dict) -> Dict[str, Any]:
    """Serialize single month configuration response."""
    return ConfigurationSerializer.serialize_month_config_response(data)


def serialize_validation_response(data: Dict) -> Dict[str, Any]:
    """Serialize validation response."""
    return ConfigurationSerializer.serialize_validation_response(data)


def serialize_target_cph_list(data: Dict) -> Dict[str, Any]:
    """Serialize Target CPH configuration list response."""
    return ConfigurationSerializer.serialize_target_cph_list(data)


def serialize_target_cph_response(data: Dict) -> Dict[str, Any]:
    """Serialize single Target CPH configuration response."""
    return ConfigurationSerializer.serialize_target_cph_response(data)


def serialize_distinct_values(data: Dict) -> Dict[str, Any]:
    """Serialize distinct values response."""
    return ConfigurationSerializer.serialize_distinct_values(data)


def serialize_bulk_response(data: Dict) -> Dict[str, Any]:
    """Serialize bulk operation response."""
    return ConfigurationSerializer.serialize_bulk_response(data)


def serialize_delete_response(data: Dict) -> Dict[str, Any]:
    """Serialize delete response."""
    return ConfigurationSerializer.serialize_delete_response(data)


def serialize_error_response(
    message: str,
    status_code: int = 400,
    recommendation: Optional[str] = None
) -> Dict[str, Any]:
    """Serialize error response."""
    return ConfigurationSerializer.serialize_error_response(message, status_code, recommendation)
