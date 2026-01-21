"""
Execution Monitoring Service Module

Business logic layer for execution monitoring.
Sits between views and repository to handle data processing and transformations.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime

from centene_forecast_app.repository import get_api_client
from core.config import ExecutionMonitoringConfig

logger = logging.getLogger('django')


class ExecutionMonitoringService:
    """
    Service class for execution monitoring business logic.

    Handles data fetching, processing, and any business rules
    before returning data to views.
    """

    @staticmethod
    def get_executions_list(filters: Dict) -> Dict:
        """
        Get list of executions with business logic applied.

        Args:
            filters: Dictionary of validated filters
                - month: Optional month name
                - year: Optional year
                - status: List of status values
                - uploaded_by: Optional username
                - limit: Records per page
                - offset: Pagination offset

        Returns:
            Dictionary with execution list and pagination

        Raises:
            Exception: If repository call fails

        Example:
            filters = {
                'month': 'January',
                'year': 2025,
                'status': ['SUCCESS'],
                'uploaded_by': None,
                'limit': 50,
                'offset': 0
            }
            result = ExecutionMonitoringService.get_executions_list(filters)
        """
        logger.info(f"[Execution Service] Fetching execution list with filters: {filters}")

        try:
            # Get API client
            client = get_api_client()

            # Fetch data from repository
            response = client.get_executions(
                month=filters.get('month'),
                year=filters.get('year'),
                status=filters.get('status'),
                uploaded_by=filters.get('uploaded_by'),
                limit=filters.get('limit', 50),
                offset=filters.get('offset', 0)
            )

            # Apply any business logic transformations here if needed
            # For now, pass through the response

            logger.info(
                f"[Execution Service] Successfully fetched "
                f"{len(response.get('data', []))} executions"
            )

            return response

        except Exception as e:
            logger.error(f"[Execution Service Error] Failed to fetch executions: {e}", exc_info=True)
            raise

    @staticmethod
    def get_execution_details(execution_id: str) -> Dict:
        """
        Get detailed information about a specific execution.

        Args:
            execution_id: UUID of the execution

        Returns:
            Dictionary with detailed execution information

        Raises:
            Exception: If repository call fails

        Example:
            details = ExecutionMonitoringService.get_execution_details(
                '550e8400-e29b-41d4-a716-446655440000'
            )
        """
        logger.info(f"[Execution Service] Fetching execution details for ID: {execution_id}")

        try:
            # Get API client
            client = get_api_client()

            # Fetch details from repository (with dynamic caching)
            response = client.get_execution_details(execution_id)

            # Apply any business logic transformations here if needed
            # For now, pass through the response

            logger.info(f"[Execution Service] Successfully fetched details for {execution_id}")

            return response

        except Exception as e:
            logger.error(
                f"[Execution Service Error] Failed to fetch execution {execution_id}: {e}",
                exc_info=True
            )
            raise

    @staticmethod
    def get_execution_kpis(filters: Dict) -> Dict:
        """
        Get KPI metrics with optional filters.

        Args:
            filters: Dictionary of validated filters
                - month: Optional month name
                - year: Optional year
                - status: List of status values
                - uploaded_by: Optional username

        Returns:
            Dictionary with KPI metrics

        Raises:
            Exception: If repository call fails

        Example:
            filters = {
                'month': 'January',
                'year': 2025,
                'status': None,
                'uploaded_by': None
            }
            kpis = ExecutionMonitoringService.get_execution_kpis(filters)
        """
        logger.info(f"[Execution Service] Fetching KPIs with filters: {filters}")

        try:
            # Get API client
            client = get_api_client()

            # Fetch KPIs from repository
            response = client.get_execution_kpis(
                month=filters.get('month'),
                year=filters.get('year'),
                status=filters.get('status'),
                uploaded_by=filters.get('uploaded_by')
            )

            # Apply any business logic transformations here if needed
            # For example, you could calculate additional derived metrics

            logger.info(f"[Execution Service] Successfully fetched KPIs")

            return response

        except Exception as e:
            logger.error(f"[Execution Service Error] Failed to fetch KPIs: {e}", exc_info=True)
            raise

    @staticmethod
    def download_execution_report(execution_id: str, report_type: str):
        """
        Get streaming response for Excel report download.

        Args:
            execution_id: UUID of the execution
            report_type: One of 'bucket_summary', 'bucket_after_allocation', 'roster_allotment'

        Returns:
            requests.Response object with streaming content

        Raises:
            ValueError: If report_type is invalid
            Exception: If repository call fails

        Example:
            response = ExecutionMonitoringService.download_execution_report(
                execution_id='550e8400-e29b-41d4-a716-446655440000',
                report_type='bucket_summary'
            )
            # Stream response to Django StreamingHttpResponse
        """
        logger.info(
            f"[Execution Service] Initiating download: {report_type} for {execution_id}"
        )

        try:
            # Check if downloads are enabled
            if not ExecutionMonitoringConfig.ENABLE_DOWNLOADS:
                raise Exception("Downloads are currently disabled")

            # Get API client
            client = get_api_client()

            # Get streaming response from repository
            response = client.download_execution_report(execution_id, report_type)

            logger.info(
                f"[Execution Service] Successfully initiated download: "
                f"{report_type} for {execution_id}"
            )

            return response

        except ValueError as e:
            # Invalid report type - re-raise with context
            logger.error(f"[Execution Service Validation Error] {e}")
            raise
        except Exception as e:
            logger.error(
                f"[Execution Service Error] Download failed: {e}",
                exc_info=True
            )
            raise

    @staticmethod
    def get_latest_execution() -> Optional[Dict]:
        """
        Get the latest (most recent) execution.

        This is a convenience method for fetching just the latest execution
        for the hero card display.

        Returns:
            Dictionary with latest execution data, or None if no executions

        Example:
            latest = ExecutionMonitoringService.get_latest_execution()
            if latest:
                print(f"Latest execution: {latest['execution_id']}")
        """
        logger.info("[Execution Service] Fetching latest execution")

        try:
            # Get API client
            client = get_api_client()

            # Fetch just the first execution (limit=1, offset=0)
            response = client.get_executions(
                month=None,
                year=None,
                status=None,
                uploaded_by=None,
                limit=1,
                offset=0
            )

            data = response.get('data', [])

            if data and len(data) > 0:
                latest = data[0]
                logger.info(
                    f"[Execution Service] Latest execution: {latest.get('execution_id')} "
                    f"(Status: {latest.get('status')})"
                )
                return latest
            else:
                logger.warning("[Execution Service] No executions found")
                return None

        except Exception as e:
            logger.error(
                f"[Execution Service Error] Failed to fetch latest execution: {e}",
                exc_info=True
            )
            raise

    @staticmethod
    def format_duration(seconds: Optional[float]) -> str:
        """
        Format duration in seconds to human-readable string.

        Helper method for formatting duration display.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string (e.g., "5m 30s", "1h 15m 45s")

        Example:
            >>> ExecutionMonitoringService.format_duration(300.5)
            '5m 0s'
            >>> ExecutionMonitoringService.format_duration(3665)
            '1h 1m 5s'
        """
        if seconds is None or seconds < 0:
            return "N/A"

        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    @staticmethod
    def calculate_success_rate(
        total: int,
        successful: int
    ) -> float:
        """
        Calculate success rate as percentage.

        Helper method for calculating success rates.

        Args:
            total: Total number of items
            successful: Number of successful items

        Returns:
            Success rate as float (0.0 to 1.0)

        Example:
            >>> ExecutionMonitoringService.calculate_success_rate(100, 85)
            0.85
            >>> ExecutionMonitoringService.calculate_success_rate(0, 0)
            0.0
        """
        if total == 0:
            return 0.0

        return successful / total

    @staticmethod
    def get_status_display_info(status: str) -> Dict[str, str]:
        """
        Get display information for a status value.

        Returns color class, icon, and display text for a status.

        Args:
            status: Status value (PENDING, IN_PROGRESS, SUCCESS, FAILED, PARTIAL_SUCCESS)

        Returns:
            Dictionary with display info

        Example:
            >>> ExecutionMonitoringService.get_status_display_info('SUCCESS')
            {
                'color': 'success',
                'icon': 'fa-check-circle',
                'text': 'Success'
            }
        """
        status_map = {
            'IN_PROGRESS': {
                'color': 'info',
                'icon': 'fa-spinner',
                'text': 'In Progress'
            },
            'SUCCESS': {
                'color': 'success',
                'icon': 'fa-check-circle',
                'text': 'Success'
            },
            'FAILED': {
                'color': 'danger',
                'icon': 'fa-times-circle',
                'text': 'Failed'
            },
            'PARTIAL_SUCCESS': {
                'color': 'warning',
                'icon': 'fa-exclamation-triangle',
                'text': 'Partial Success'
            },
            'PENDING': {
                'color': 'secondary',
                'icon': 'fa-clock',
                'text': 'Pending'
            }
        }

        return status_map.get(status, {
            'color': 'secondary',
            'icon': 'fa-question-circle',
            'text': status
        })


# ============================================================================
# Convenience Wrapper Functions
# ============================================================================

def get_executions_list(filters: Dict) -> Dict:
    """Convenience function to get execution list."""
    return ExecutionMonitoringService.get_executions_list(filters)


def get_execution_details(execution_id: str) -> Dict:
    """Convenience function to get execution details."""
    return ExecutionMonitoringService.get_execution_details(execution_id)


def get_execution_kpis(filters: Dict) -> Dict:
    """Convenience function to get execution KPIs."""
    return ExecutionMonitoringService.get_execution_kpis(filters)


def download_execution_report(execution_id: str, report_type: str):
    """Convenience function to download execution report."""
    return ExecutionMonitoringService.download_execution_report(execution_id, report_type)


def get_latest_execution() -> Optional[Dict]:
    """Convenience function to get latest execution."""
    return ExecutionMonitoringService.get_latest_execution()


# Example usage in views:
# from execution_service import get_executions_list, get_execution_details
#
# def my_view(request):
#     filters = validate_execution_filters(request.GET)
#     data = get_executions_list(filters)
#     return JsonResponse(data)