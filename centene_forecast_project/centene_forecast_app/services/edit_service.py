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

            # Check if response indicates an error (from backend or from repository error handling)
            if not response.get('success', True):
                error_msg = response.get('error') or response.get('message', 'Unknown error')
                recommendation = response.get('recommendation')

                logger.warning(
                    f"[Edit View Service] Preview calculation failed: {error_msg}"
                    + (f" | Recommendation: {recommendation}" if recommendation else "")
                )
                return response  # Return error response with all details

            total_modified = response.get('total_modified', 0)
            logger.info(
                f"[Edit View Service] Preview calculated - {total_modified} modified records"
            )

            return response

        except Exception as e:
            logger.error(f"[Edit View Service] Preview calculation error: {e}")
            raise

    @staticmethod
    def submit_bench_allocation_update(
        month: str,
        year: int,
        months: dict,
        modified_records: list,
        user_notes: Optional[str] = None
    ) -> dict:
        """
        Submit bench allocation updates to backend.

        This method orchestrates the update process:
        1. Validates that records exist
        2. Calls backend API to save changes
        3. Creates history log entry
        4. Returns success/failure response

        Args:
            month: Month name (e.g., 'April')
            year: Year (e.g., 2025)
            months: Month index mapping (month1-month6 to labels)
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
            >>> months_map = {'month1': 'Jun-25', ...}
            >>> response = service.submit_bench_allocation_update(
            ...     'April', 2025, months_map, [...], 'Updated bench capacity'
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
            client = get_api_client()
            response = client.update_bench_allocation(
                month,
                year,
                months,
                modified_records,
                user_notes or ''
            )

            # Check if response indicates an error (from backend or from repository error handling)
            if not response.get('success', True):
                error_msg = response.get('error') or response.get('message', 'Unknown error')
                recommendation = response.get('recommendation')

                logger.warning(
                    f"[Edit View Service] Update failed: {error_msg}"
                    + (f" | Recommendation: {recommendation}" if recommendation else "")
                )
                return response  # Return error response with all details

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
        limit: int = None,
        change_types: Optional[list] = None
    ) -> dict:
        """
        Get history log entries with optional filtering.

        This method orchestrates history log retrieval:
        1. Applies filters (month, year, change_types)
        2. Handles pagination
        3. Returns formatted history entries

        Args:
            month: Optional month filter (e.g., 'April')
            year: Optional year filter (e.g., 2025)
            page: Page number (default: 1)
            limit: Records per page (default: from config)
            change_types: Optional list of change types to filter by

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
            >>> history = service.get_history_log(month='April', year=2025, page=1, change_types=['Bench Allocation'])
            >>> len(history['data']) > 0
            True
        """
        limit = limit or EditViewConfig.HISTORY_PAGE_SIZE

        logger.info(
            f"[Edit View Service] Fetching history - "
            f"month: {month}, year: {year}, page: {page}, change_types: {change_types}"
        )

        try:
            client = get_api_client()
            response = client.get_history_log(month, year, page, limit, change_types)

            total = response.get('pagination', {}).get('total', 0)
            entries_count = len(response.get('data', []))
            logger.info(
                f"[Edit View Service] Retrieved {entries_count} of {total} history entries"
            )

            return response

        except Exception as e:
            logger.error(f"[Edit View Service] History fetch failed: {e}")
            raise

    @staticmethod
    def get_available_change_types() -> dict:
        """
        Get available change types for filtering.

        This method fetches all available change types from the API
        to populate the filter dropdown dynamically.

        Returns:
            Dict with change types:
            {
                'success': True,
                'data': [
                    {'value': 'Bench Allocation', 'display': 'Bench Allocation'},
                    {'value': 'CPH Update', 'display': 'CPH Update'},
                    ...
                ],
                'total': 6
            }

        Raises:
            Exception: On API failure

        Example:
            >>> service = EditViewService()
            >>> change_types = service.get_available_change_types()
            >>> len(change_types['data']) > 0
            True
        """
        logger.info("[Edit View Service] Fetching available change types")

        try:
            client = get_api_client()
            response = client.get_available_change_types()

            total = response.get('total', 0)
            logger.info(f"[Edit View Service] Retrieved {total} change types")

            return response

        except Exception as e:
            logger.error(f"[Edit View Service] Change types fetch failed: {e}")
            raise

    @staticmethod
    def get_change_type_color(change_type: str, index: int = None) -> str:
        """
        Get color for a change type using predefined colors.

        Args:
            change_type: Type of change (e.g., 'Bench Allocation')
            index: Optional index to use for color selection

        Returns:
            Hex color code

        Example:
            >>> service = EditViewService()
            >>> color = service.get_change_type_color('Bench Allocation')
            >>> color.startswith('#')
            True
        """
        # Predefined colors for common change types (for consistency)
        predefined_colors = {
            'Bench Allocation': '#0d6efd',
            'CPH Update': '#198754',
            'Manual Update': '#ffc107',
            'Capacity Update': '#6f42c1',
            'FTE Update': '#fd7e14',
            'Forecast Update': '#20c997'
        }

        # Return predefined color if exists
        if change_type in predefined_colors:
            return predefined_colors[change_type]

        # Use index if provided, otherwise generate from string hash
        if index is not None:
            color_index = index % len(EditViewConfig.STANDARD_COLORS)
        else:
            # Simple hash function to generate consistent index
            hash_value = 0
            for char in change_type:
                hash_value = ((hash_value << 5) - hash_value) + ord(char)
                hash_value = hash_value & 0xFFFFFFFF  # Convert to 32-bit integer
            color_index = abs(hash_value) % len(EditViewConfig.STANDARD_COLORS)

        return EditViewConfig.STANDARD_COLORS[color_index]


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
    months: dict,
    modified_records: list,
    user_notes: Optional[str] = None
) -> dict:
    """
    Convenience function to submit bench allocation update.

    Args:
        month: Month name
        year: Year
        months: Month index mapping (month1-month6 to labels)
        modified_records: List of modified records
        user_notes: Optional notes

    Returns:
        Dict with update result

    Example:
        >>> from edit_service import submit_bench_allocation_update
        >>> months_map = {'month1': 'Jun-25', 'month2': 'Jul-25', ...}
        >>> response = submit_bench_allocation_update('April', 2025, months_map, [...], 'Notes')
        >>> response['success']
        True
    """
    return EditViewService.submit_bench_allocation_update(
        month, year, months, modified_records, user_notes
    )


def get_history_log(
    month: Optional[str] = None,
    year: Optional[int] = None,
    page: int = 1,
    limit: int = None,
    change_types: Optional[list] = None
) -> dict:
    """
    Convenience function to get history log.

    Args:
        month: Optional month filter
        year: Optional year filter
        page: Page number
        limit: Records per page
        change_types: Optional list of change types to filter by

    Returns:
        Dict with history entries

    Example:
        >>> from edit_service import get_history_log
        >>> history = get_history_log(month='April', year=2025, change_types=['Bench Allocation'])
        >>> len(history['data']) > 0
        True
    """
    return EditViewService.get_history_log(month, year, page, limit, change_types)


def get_available_change_types() -> dict:
    """
    Convenience function to get available change types.

    Returns:
        Dict with change types

    Example:
        >>> from edit_service import get_available_change_types
        >>> change_types = get_available_change_types()
        >>> change_types['success']
        True
    """
    return EditViewService.get_available_change_types()


def get_change_type_color(change_type: str, index: int = None) -> str:
    """
    Convenience function to get change type color.

    Args:
        change_type: Type of change
        index: Optional index for color selection

    Returns:
        Hex color code

    Example:
        >>> from edit_service import get_change_type_color
        >>> color = get_change_type_color('New Change Type')
        >>> color.startswith('#')
        True
    """
    return EditViewService.get_change_type_color(change_type, index)


# ============================================================
# TARGET CPH SERVICE FUNCTIONS
# ============================================================

def get_target_cph_data(month: str, year: int) -> dict:
    """
    Orchestrate CPH data fetching.

    Args:
        month: Month name (e.g., 'April')
        year: Year (e.g., 2025)

    Returns:
        Dict with CPH records

    Example:
        >>> from edit_service import get_target_cph_data
        >>> data = get_target_cph_data('April', 2025)
        >>> data['total']
        12
    """
    logger.info(f"[CPH Service] Fetching CPH data for {month} {year}")

    try:
        client = get_api_client()
        response = client.get_target_cph_data(month, year)

        total = response.get('total', 0)
        logger.info(f"[CPH Service] Retrieved {total} CPH records")

        return response

    except Exception as e:
        logger.error(f"[CPH Service] Failed to fetch CPH data: {e}")
        raise


def calculate_target_cph_preview(
    month: str,
    year: int,
    modified_records: list
) -> dict:
    """
    Orchestrate CPH preview calculation.

    Args:
        month: Month name (e.g., 'April')
        year: Year (e.g., 2025)
        modified_records: List of modified CPH records

    Returns:
        Dict with preview data (forecast impact)

    Example:
        >>> from edit_service import calculate_target_cph_preview
        >>> preview = calculate_target_cph_preview('April', 2025, [...])
        >>> preview['total_modified']
        15
    """
    logger.info(
        f"[CPH Service] Calculating CPH preview for {month} {year} "
        f"({len(modified_records)} CPH changes)"
    )

    try:
        client = get_api_client()
        response = client.get_target_cph_preview(month, year, modified_records)

        # Check if response indicates an error (from backend or from repository error handling)
        if not response.get('success', True):
            error_msg = response.get('error') or response.get('message', 'Unknown error')
            recommendation = response.get('recommendation')

            logger.warning(
                f"[CPH Service] Preview calculation failed: {error_msg}"
                + (f" | Recommendation: {recommendation}" if recommendation else "")
            )
            return response  # Return error response with all details

        total_modified = response.get('total_modified', 0)
        logger.info(
            f"[CPH Service] Preview calculated - {total_modified} forecast rows "
            f"affected by {len(modified_records)} CPH changes"
        )

        return response

    except Exception as e:
        logger.error(f"[CPH Service] Preview calculation error: {e}")
        raise


def submit_target_cph_update(
    month: str,
    year: int,
    months: dict,
    modified_records: list,
    user_notes: Optional[str] = None
) -> dict:
    """
    Orchestrate CPH update submission.

    IMPORTANT: Uses SAME ModifiedForecastRecord format as bench allocation.
    Records include target_cph/target_cph_change fields plus nested months data.

    Args:
        month: Month name (e.g., 'April')
        year: Year (e.g., 2025)
        months: Month index mapping (month1-month6 to labels)
        modified_records: List of ModifiedForecastRecord dicts
        user_notes: Optional user notes

    Returns:
        Dict with update result

    Example:
        >>> from edit_service import submit_target_cph_update
        >>> months_map = {'month1': 'Jun-25', 'month2': 'Jul-25', ...}
        >>> response = submit_target_cph_update('April', 2025, months_map, [...], 'Updated CPH')
        >>> response['success']
        True
    """
    records_count = len(modified_records)
    logger.info(
        f"[CPH Service] Submitting CPH update for {month} {year} "
        f"({records_count} CPH changes)"
    )

    try:
        client = get_api_client()
        response = client.submit_target_cph_update(
            month,
            year,
            months,
            modified_records,
            user_notes or ''
        )

        # Check if response indicates an error (from backend or from repository error handling)
        if not response.get('success', True):
            error_msg = response.get('error') or response.get('message', 'Unknown error')
            recommendation = response.get('recommendation')

            logger.warning(
                f"[CPH Service] Update failed: {error_msg}"
                + (f" | Recommendation: {recommendation}" if recommendation else "")
            )
            return response  # Return error response with all details

        cph_changes = response.get('cph_changes_applied', 0)
        forecast_rows = response.get('forecast_rows_affected', 0)
        logger.info(
            f"[CPH Service] Update successful - {cph_changes} CPH changes applied, "
            f"{forecast_rows} forecast rows affected"
        )

        return response

    except Exception as e:
        logger.error(f"[CPH Service] Update failed: {e}")
        raise


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
