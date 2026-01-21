"""
Execution Monitoring Serializers Module

Response formatting and serialization for execution monitoring APIs.
Ensures consistent JSON response structure across all endpoints.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger('django')


class ExecutionMonitoringSerializer:
    """
    Serializer class for execution monitoring API responses.

    Formats data from services/repositories into consistent JSON responses
    that are ready for frontend consumption.
    """

    @staticmethod
    def serialize_executions_list_response(data: Dict) -> Dict[str, Any]:
        """
        Serialize execution list response for frontend.

        Args:
            data: Raw response from repository/service

        Returns:
            Formatted response dictionary

        Example:
            {
                'success': True,
                'data': [...],
                'pagination': {
                    'total': 150,
                    'limit': 50,
                    'offset': 0,
                    'count': 50,
                    'has_more': True
                },
                'timestamp': '2025-01-15T14:30:00'
            }
        """
        try:
            # Extract data and pagination
            executions = data.get('data', [])
            pagination = data.get('pagination', {})

            # Format response
            response = {
                'success': True,
                'data': executions,
                'pagination': {
                    'total': pagination.get('total', 0),
                    'limit': pagination.get('limit', 50),
                    'offset': pagination.get('offset', 0),
                    'count': pagination.get('count', len(executions)),
                    'has_more': pagination.get('has_more', False)
                },
                'timestamp': ExecutionMonitoringSerializer._get_timestamp()
            }

            logger.debug(
                f"[Serializer] Serialized executions list: "
                f"{len(executions)} records, total={pagination.get('total', 0)}"
            )

            return response

        except KeyError as e:
            logger.error(f"[Serializer Error] Missing required field in data: {e}")
            return ExecutionMonitoringSerializer.serialize_error_response(
                f"Invalid data structure: missing field {e}",
                500
            )
        except Exception as e:
            logger.error(f"[Serializer Error] Failed to serialize list response: {e}")
            return ExecutionMonitoringSerializer.serialize_error_response(
                "Failed to serialize response",
                500
            )

    @staticmethod
    def serialize_execution_details_response(data: Dict) -> Dict[str, Any]:
        """
        Serialize execution details response for frontend.

        Args:
            data: Raw response from repository/service

        Returns:
            Formatted response dictionary

        Example:
            {
                'success': True,
                'data': {
                    'execution_id': '550e8400-...',
                    'month': 'January',
                    'year': 2025,
                    'status': 'SUCCESS',
                    ...
                },
                'timestamp': '2025-01-15T14:30:00'
            }
        """
        try:
            # Extract execution details
            execution = data.get('data', {})

            # Format response
            response = {
                'success': True,
                'data': execution,
                'timestamp': ExecutionMonitoringSerializer._get_timestamp()
            }

            logger.debug(
                f"[Serializer] Serialized execution details: "
                f"ID={execution.get('execution_id', 'unknown')}, "
                f"Status={execution.get('status', 'unknown')}"
            )

            return response

        except KeyError as e:
            logger.error(f"[Serializer Error] Missing required field in data: {e}")
            return ExecutionMonitoringSerializer.serialize_error_response(
                f"Invalid data structure: missing field {e}",
                500
            )
        except Exception as e:
            logger.error(f"[Serializer Error] Failed to serialize details response: {e}")
            return ExecutionMonitoringSerializer.serialize_error_response(
                "Failed to serialize response",
                500
            )

    @staticmethod
    def serialize_kpi_response(data: Dict) -> Dict[str, Any]:
        """
        Serialize KPI metrics response for frontend.

        Args:
            data: Raw response from repository/service

        Returns:
            Formatted response dictionary

        Example:
            {
                'success': True,
                'data': {
                    'total_executions': 150,
                    'success_rate': 0.85,
                    'average_duration_seconds': 320.5,
                    ...
                },
                'timestamp': '2025-01-15T14:30:00'
            }
        """
        try:
            # Extract KPI data
            kpi_data = data.get('data', {})

            # Format response
            response = {
                'success': True,
                'data': {
                    'total_executions': kpi_data.get('total_executions', 0),
                    'success_rate': kpi_data.get('success_rate', 0.0),
                    'average_duration_seconds': kpi_data.get('average_duration_seconds', 0.0),
                    'failed_count': kpi_data.get('failed_count', 0),
                    'partial_success_count': kpi_data.get('partial_success_count', 0),
                    'in_progress_count': kpi_data.get('in_progress_count', 0),
                    'pending_count': kpi_data.get('pending_count', 0),
                    'success_count': kpi_data.get('success_count', 0),
                    'total_records_processed': kpi_data.get('total_records_processed', 0),
                    'total_records_failed': kpi_data.get('total_records_failed', 0)
                },
                'timestamp': ExecutionMonitoringSerializer._get_timestamp()
            }

            logger.debug(
                f"[Serializer] Serialized KPI response: "
                f"Total={kpi_data.get('total_executions', 0)}, "
                f"Success Rate={kpi_data.get('success_rate', 0.0):.2%}"
            )

            return response

        except KeyError as e:
            logger.error(f"[Serializer Error] Missing required field in KPI data: {e}")
            return ExecutionMonitoringSerializer.serialize_error_response(
                f"Invalid data structure: missing field {e}",
                500
            )
        except Exception as e:
            logger.error(f"[Serializer Error] Failed to serialize KPI response: {e}")
            return ExecutionMonitoringSerializer.serialize_error_response(
                "Failed to serialize response",
                500
            )

    @staticmethod
    def serialize_error_response(
        error_message: str,
        status_code: int = 400,
        error_type: Optional[str] = None,
        details: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Serialize error response with consistent structure.

        Args:
            error_message: Human-readable error message
            status_code: HTTP status code
            error_type: Optional error type/category
            details: Optional additional error details

        Returns:
            Formatted error response dictionary

        Example:
            {
                'success': False,
                'error': 'Invalid execution ID format',
                'error_type': 'ValidationError',
                'status_code': 400,
                'details': {...},
                'timestamp': '2025-01-15T14:30:00'
            }
        """
        response = {
            'success': False,
            'error': error_message,
            'status_code': status_code,
            'timestamp': ExecutionMonitoringSerializer._get_timestamp()
        }

        if error_type:
            response['error_type'] = error_type

        if details:
            response['details'] = details

        logger.debug(
            f"[Serializer] Serialized error response: "
            f"Code={status_code}, Message={error_message}"
        )

        return response

    @staticmethod
    def serialize_download_error_response(
        error_message: str,
        execution_id: str,
        report_type: str
    ) -> Dict[str, Any]:
        """
        Serialize download-specific error response.

        Args:
            error_message: Error message
            execution_id: Execution ID that failed
            report_type: Report type that was requested

        Returns:
            Formatted error response with download context

        Example:
            {
                'success': False,
                'error': 'Report not available',
                'error_type': 'DownloadError',
                'status_code': 404,
                'details': {
                    'execution_id': '550e8400-...',
                    'report_type': 'bucket_summary'
                },
                'timestamp': '2025-01-15T14:30:00'
            }
        """
        return ExecutionMonitoringSerializer.serialize_error_response(
            error_message=error_message,
            status_code=404,
            error_type='DownloadError',
            details={
                'execution_id': execution_id,
                'report_type': report_type
            }
        )

    @staticmethod
    def _get_timestamp() -> str:
        """
        Get current timestamp in ISO 8601 format.

        Returns:
            ISO formatted timestamp string

        Example:
            '2025-01-15T14:30:00.123456'
        """
        return datetime.now().isoformat()

    @staticmethod
    def serialize_filter_options_response(
        months: List[str],
        years: List[int],
        statuses: List[str],
        users: List[str]
    ) -> Dict[str, Any]:
        """
        Serialize filter dropdown options for frontend.

        Args:
            months: List of available months
            years: List of available years
            statuses: List of available statuses
            users: List of available users

        Returns:
            Formatted response with filter options

        Example:
            {
                'success': True,
                'data': {
                    'months': ['January', 'February', ...],
                    'years': [2025, 2024, ...],
                    'statuses': ['PENDING', 'IN_PROGRESS', ...],
                    'users': ['john.doe', 'jane.smith', ...]
                },
                'timestamp': '2025-01-15T14:30:00'
            }
        """
        try:
            response = {
                'success': True,
                'data': {
                    'months': months,
                    'years': years,
                    'statuses': statuses,
                    'users': users
                },
                'timestamp': ExecutionMonitoringSerializer._get_timestamp()
            }

            logger.debug(
                f"[Serializer] Serialized filter options: "
                f"{len(months)} months, {len(years)} years, "
                f"{len(statuses)} statuses, {len(users)} users"
            )

            return response

        except Exception as e:
            logger.error(f"[Serializer Error] Failed to serialize filter options: {e}")
            return ExecutionMonitoringSerializer.serialize_error_response(
                "Failed to serialize filter options",
                500
            )


# ============================================================================
# Convenience Wrapper Functions
# ============================================================================

def serialize_executions_list_response(data: Dict) -> Dict[str, Any]:
    """Convenience function to serialize executions list."""
    return ExecutionMonitoringSerializer.serialize_executions_list_response(data)


def serialize_execution_details_response(data: Dict) -> Dict[str, Any]:
    """Convenience function to serialize execution details."""
    return ExecutionMonitoringSerializer.serialize_execution_details_response(data)


def serialize_kpi_response(data: Dict) -> Dict[str, Any]:
    """Convenience function to serialize KPI response."""
    return ExecutionMonitoringSerializer.serialize_kpi_response(data)


def serialize_error_response(
    error_message: str,
    status_code: int = 400,
    error_type: Optional[str] = None,
    details: Optional[Dict] = None
) -> Dict[str, Any]:
    """Convenience function to serialize error response."""
    return ExecutionMonitoringSerializer.serialize_error_response(
        error_message, status_code, error_type, details
    )


def serialize_download_error_response(
    error_message: str,
    execution_id: str,
    report_type: str
) -> Dict[str, Any]:
    """Convenience function to serialize download error."""
    return ExecutionMonitoringSerializer.serialize_download_error_response(
        error_message, execution_id, report_type
    )


# Example usage in views:
# from execution_serializers import (
#     serialize_executions_list_response,
#     serialize_error_response
# )
#
# def my_view(request):
#     try:
#         data = get_executions_list(filters)
#         response = serialize_executions_list_response(data)
#         return JsonResponse(response, status=200)
#     except Exception as e:
#         error_response = serialize_error_response(str(e), 500)
#         return JsonResponse(error_response, status=500)