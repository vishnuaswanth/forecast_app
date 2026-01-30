# edit_service.py
"""
Business logic for Edit View operations.

Follows the service pattern from manager_service.py.
All services orchestrate API calls and implement business rules.
"""

import logging
from typing import Dict, Optional
from centene_forecast_app.repository import get_api_client
from core.config import EditViewConfig

logger = logging.getLogger('django')


class EditViewService:
    """Business logic for Edit View operations"""

    @staticmethod
    def get_allocation_reports() -> dict:
        """
        Get available allocation reports for dropdown.

        Returns:
            Dict with report options:
            {
                'success': True,
                'data': [{'value': '2025-04', 'display': 'April 2025'}, ...],
                'total': 15
            }

        Raises:
            Exception: On API failure

        Example:
            >>> service = EditViewService()
            >>> reports = service.get_allocation_reports()
            >>> len(reports['data']) > 0
            True
        """
        logger.info("[Edit View Service] Fetching allocation reports")

        try:
            client = get_api_client()
            response = client.get_allocation_reports()

            total = response.get('total', 0)
            logger.info(f"[Edit View Service] Retrieved {total} allocation reports")

            return response

        except Exception as e:
            logger.error(f"[Edit View Service] Failed to fetch reports: {e}")
            raise

    @staticmethod
    def calculate_bench_allocation_preview(month: str, year: int) -> dict:
        """
        Calculate bench allocation preview (modified records only).

        This method orchestrates the preview calculation:
        1. Calls backend API to calculate allocation
        2. Returns only modified records with metadata

        Args:
            month: Month name (e.g., 'April')
            year: Year (e.g., 2025)

        Returns:
            Dict with modified records and metadata:
            {
                'success': True/False,
                'modified_records': [...] or [],
                'total_modified': 15,
                'message': None or error message
            }

        Raises:
            Exception: On API failure

        Example:
            >>> service = EditViewService()
            >>> preview = service.calculate_bench_allocation_preview('April', 2025)
            >>> preview['success']
            True
        """
        logger.info(f"[Edit View Service] Calculating preview for {month} {year}")

        try:
            client = get_api_client()
            response = client.get_bench_allocation_preview(month, year)

            # Check for success
            if not response.get('success', False):
                error_msg = response.get('message', 'Unknown error')
                logger.warning(
                    f"[Edit View Service] Preview calculation failed: {error_msg}"
                )
                return response

            total_modified = response.get('total_modified', 0)
            logger.info(
                f"[Edit View Service] Preview calculated - {total_modified} modified records"
            )

            return response

        except Exception as e:
            logger.error(f"[Edit View Service] Preview calculation error: {e}")
            raise

    @staticmethod
    def _transform_records_for_api(records: list) -> list:
        """
        Transform records for API submission by wrapping month data in a 'months' object.
        The backend expects month-wise data to be nested under a 'months' key.

        Args:
            records: List of record objects with month keys at top level

        Returns:
            Transformed records with month data wrapped in 'months' object
        """
        import re
        month_pattern = re.compile(r'^[A-Z][a-z]{2}-\d{2}$')  # e.g., "Jun-25"

        transformed = []
        for record in records:
            new_record = {
                'main_lob': record.get('main_lob'),
                'state': record.get('state'),
                'case_type': record.get('case_type'),
                'case_id': record.get('case_id'),
                'target_cph': record.get('target_cph'),
                '_modified_fields': record.get('_modified_fields', []),
                'months': {}
            }

            # Move month keys into months object
            for key, value in record.items():
                if month_pattern.match(key):
                    new_record['months'][key] = value

            transformed.append(new_record)

        return transformed

    @staticmethod
    def submit_bench_allocation_update(
        month: str,
        year: int,
        modified_records: list,
        user_notes: Optional[str] = None
    ) -> dict:
        """
        Submit bench allocation updates to backend.

        This method orchestrates the update process:
        1. Validates that records exist
        2. Transforms records to API format (wraps month data in 'months' object)
        3. Calls backend API to save changes
        4. Creates history log entry
        5. Returns success/failure response

        Args:
            month: Month name (e.g., 'April')
            year: Year (e.g., 2025)
            modified_records: List of modified record dictionaries
            user_notes: Optional user description

        Returns:
            Success response:
            {
                'success': True,
                'message': 'Allocation updated successfully',
                'records_updated': 15
            }

        Raises:
            Exception: On API failure

        Example:
            >>> service = EditViewService()
            >>> response = service.submit_bench_allocation_update(
            ...     'April', 2025, [...], 'Updated bench capacity'
            ... )
            >>> response['success']
            True
        """
        records_count = len(modified_records)
        logger.info(
            f"[Edit View Service] Submitting update for {month} {year} "
            f"({records_count} records)"
        )

        try:
            # Transform records to API format
            transformed_records = EditViewService._transform_records_for_api(
                modified_records
            )

            client = get_api_client()
            response = client.update_bench_allocation(
                month,
                year,
                transformed_records,
                user_notes or ''
            )

            records_updated = response.get('records_updated', 0)
            logger.info(
                f"[Edit View Service] Update successful - {records_updated} records updated"
            )

            return response

        except Exception as e:
            logger.error(f"[Edit View Service] Update failed: {e}")
            raise

    @staticmethod
    def get_history_log(
        month: Optional[str] = None,
        year: Optional[int] = None,
        page: int = 1,
        limit: int = None
    ) -> dict:
        """
        Get history log entries with optional filtering.

        This method orchestrates history log retrieval:
        1. Applies filters (month, year)
        2. Handles pagination
        3. Returns formatted history entries

        Args:
            month: Optional month filter (e.g., 'April')
            year: Optional year filter (e.g., 2025)
            page: Page number (default: 1)
            limit: Records per page (default: from config)

        Returns:
            Dict with history entries and pagination:
            {
                'success': True,
                'data': [...],
                'pagination': {
                    'total': 127,
                    'page': 1,
                    'limit': 25,
                    'has_more': True
                }
            }

        Raises:
            Exception: On API failure

        Example:
            >>> service = EditViewService()
            >>> history = service.get_history_log(month='April', year=2025, page=1)
            >>> len(history['data']) > 0
            True
        """
        limit = limit or EditViewConfig.HISTORY_PAGE_SIZE

        logger.info(
            f"[Edit View Service] Fetching history - "
            f"month: {month}, year: {year}, page: {page}"
        )

        try:
            client = get_api_client()
            response = client.get_history_log(month, year, page, limit)

            total = response.get('pagination', {}).get('total', 0)
            entries_count = len(response.get('data', []))
            logger.info(
                f"[Edit View Service] Retrieved {entries_count} of {total} history entries"
            )

            return response

        except Exception as e:
            logger.error(f"[Edit View Service] History fetch failed: {e}")
            raise


# Convenience functions for direct import
def get_allocation_reports() -> dict:
    """
    Convenience function to get allocation reports.

    Returns:
        Dict with allocation reports

    Example:
        >>> from edit_service import get_allocation_reports
        >>> reports = get_allocation_reports()
        >>> reports['success']
        True
    """
    return EditViewService.get_allocation_reports()


def calculate_bench_allocation_preview(month: str, year: int) -> dict:
    """
    Convenience function to calculate bench allocation preview.

    Args:
        month: Month name
        year: Year

    Returns:
        Dict with preview data

    Example:
        >>> from edit_service import calculate_bench_allocation_preview
        >>> preview = calculate_bench_allocation_preview('April', 2025)
        >>> preview['total_modified']
        15
    """
    return EditViewService.calculate_bench_allocation_preview(month, year)


def submit_bench_allocation_update(
    month: str,
    year: int,
    modified_records: list,
    user_notes: Optional[str] = None
) -> dict:
    """
    Convenience function to submit bench allocation update.

    Args:
        month: Month name
        year: Year
        modified_records: List of modified records
        user_notes: Optional notes

    Returns:
        Dict with update result

    Example:
        >>> from edit_service import submit_bench_allocation_update
        >>> response = submit_bench_allocation_update('April', 2025, [...], 'Notes')
        >>> response['success']
        True
    """
    return EditViewService.submit_bench_allocation_update(
        month, year, modified_records, user_notes
    )


def get_history_log(
    month: Optional[str] = None,
    year: Optional[int] = None,
    page: int = 1,
    limit: int = None
) -> dict:
    """
    Convenience function to get history log.

    Args:
        month: Optional month filter
        year: Optional year filter
        page: Page number
        limit: Records per page

    Returns:
        Dict with history entries

    Example:
        >>> from edit_service import get_history_log
        >>> history = get_history_log(month='April', year=2025)
        >>> len(history['data']) > 0
        True
    """
    return EditViewService.get_history_log(month, year, page, limit)


# Example usage:
# from edit_service import (
#     get_allocation_reports,
#     calculate_bench_allocation_preview,
#     submit_bench_allocation_update,
#     get_history_log
# )
#
# # Get dropdown options
# reports = get_allocation_reports()
#
# # Calculate preview
# preview = calculate_bench_allocation_preview('April', 2025)
#
# # Submit update
# response = submit_bench_allocation_update('April', 2025, preview['modified_records'], 'Notes')
#
# # Get history
# history = get_history_log(month='April', year=2025, page=1)