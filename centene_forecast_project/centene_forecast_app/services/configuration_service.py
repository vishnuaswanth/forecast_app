# configuration_service.py
"""
Business logic for Configuration View operations.

Follows the service pattern from edit_service.py.
All services orchestrate API calls and implement business rules.
"""

import logging
from typing import Dict, Optional, List
from centene_forecast_app.repository import get_api_client
from core.config import ConfigurationViewConfig

logger = logging.getLogger('django')


class MonthConfigService:
    """Business logic for Month Configuration operations"""

    @staticmethod
    def get_configurations(
        month: Optional[str] = None,
        year: Optional[int] = None,
        work_type: Optional[str] = None
    ) -> Dict:
        """
        Get month configurations with optional filtering.

        Args:
            month: Optional month name filter
            year: Optional year filter
            work_type: Optional work type filter

        Returns:
            Dictionary with configurations list

        Example:
            >>> data = MonthConfigService.get_configurations(year=2025)
            >>> len(data['data'])
            24
        """
        logger.info(
            f"[Month Config Service] Fetching configurations - "
            f"month: {month}, year: {year}, work_type: {work_type}"
        )

        try:
            client = get_api_client()
            response = client.get_month_configurations(month, year, work_type)

            # Check for error response
            if not response.get('success', True):
                error_msg = response.get('error', 'Unknown error')
                logger.warning(f"[Month Config Service] Fetch failed: {error_msg}")
                return response

            total = len(response.get('data', []))
            logger.info(f"[Month Config Service] Retrieved {total} configurations")

            return response

        except Exception as e:
            logger.error(f"[Month Config Service] Fetch error: {e}")
            raise

    @staticmethod
    def create_configuration(data: Dict) -> Dict:
        """
        Create a new month configuration.

        Args:
            data: Configuration data dictionary

        Returns:
            Success response with created configuration

        Example:
            >>> data = {'month': 'January', 'year': 2025, 'work_type': 'Domestic', ...}
            >>> response = MonthConfigService.create_configuration(data)
            >>> response['success']
            True
        """
        logger.info(
            f"[Month Config Service] Creating configuration - "
            f"{data.get('month')} {data.get('year')} {data.get('work_type')}"
        )

        try:
            client = get_api_client()
            response = client.create_month_configuration(data)

            if not response.get('success', True):
                error_msg = response.get('error', 'Unknown error')
                logger.warning(f"[Month Config Service] Create failed: {error_msg}")
                return response

            logger.info("[Month Config Service] Configuration created successfully")
            return response

        except Exception as e:
            logger.error(f"[Month Config Service] Create error: {e}")
            raise

    @staticmethod
    def bulk_create_configurations(
        configs: List[Dict],
        created_by: str,
        skip_validation: bool = False
    ) -> Dict:
        """
        Bulk create month configurations.

        Args:
            configs: List of configuration dictionaries
            created_by: Username performing the operation
            skip_validation: Whether to skip duplicate validation

        Returns:
            Success response with created count

        Example:
            >>> configs = [{'month': 'January', 'year': 2025, ...}, ...]
            >>> response = MonthConfigService.bulk_create_configurations(configs, 'admin')
            >>> response['created_count']
            10
        """
        logger.info(
            f"[Month Config Service] Bulk creating {len(configs)} configurations "
            f"by {created_by}"
        )

        try:
            client = get_api_client()
            response = client.bulk_create_month_configurations(
                configs, created_by, skip_validation
            )

            if not response.get('success', True):
                error_msg = response.get('error', 'Unknown error')
                logger.warning(f"[Month Config Service] Bulk create failed: {error_msg}")
                return response

            created = response.get('created_count', 0)
            logger.info(f"[Month Config Service] Bulk created {created} configurations")
            return response

        except Exception as e:
            logger.error(f"[Month Config Service] Bulk create error: {e}")
            raise

    @staticmethod
    def update_configuration(config_id: int, data: Dict) -> Dict:
        """
        Update an existing month configuration.

        Args:
            config_id: ID of configuration to update
            data: Updated configuration data

        Returns:
            Success response with updated configuration

        Example:
            >>> response = MonthConfigService.update_configuration(1, {...})
            >>> response['success']
            True
        """
        logger.info(f"[Month Config Service] Updating configuration ID: {config_id}")

        try:
            client = get_api_client()
            response = client.update_month_configuration(config_id, data)

            if not response.get('success', True):
                error_msg = response.get('error', 'Unknown error')
                logger.warning(f"[Month Config Service] Update failed: {error_msg}")
                return response

            logger.info(f"[Month Config Service] Configuration {config_id} updated")
            return response

        except Exception as e:
            logger.error(f"[Month Config Service] Update error: {e}")
            raise

    @staticmethod
    def delete_configuration(config_id: int, allow_orphan: bool = False) -> Dict:
        """
        Delete a month configuration.

        Args:
            config_id: ID of configuration to delete
            allow_orphan: Whether to allow deletion even if it creates orphan

        Returns:
            Success response or error with orphan warning

        Example:
            >>> response = MonthConfigService.delete_configuration(1)
            >>> response['success']
            True
        """
        logger.info(
            f"[Month Config Service] Deleting configuration ID: {config_id}, "
            f"allow_orphan: {allow_orphan}"
        )

        try:
            client = get_api_client()
            response = client.delete_month_configuration(config_id, allow_orphan)

            if not response.get('success', True):
                error_msg = response.get('error', 'Unknown error')
                logger.warning(f"[Month Config Service] Delete failed: {error_msg}")
                return response

            logger.info(f"[Month Config Service] Configuration {config_id} deleted")
            return response

        except Exception as e:
            logger.error(f"[Month Config Service] Delete error: {e}")
            raise

    @staticmethod
    def validate_configurations() -> Dict:
        """
        Validate month configurations for orphaned records.

        Returns:
            Validation result with orphaned records list

        Example:
            >>> result = MonthConfigService.validate_configurations()
            >>> result['is_valid']
            True
        """
        logger.info("[Month Config Service] Running validation check")

        try:
            client = get_api_client()
            response = client.validate_month_configurations()

            orphan_count = len(response.get('orphaned_records', []))
            is_valid = orphan_count == 0

            logger.info(
                f"[Month Config Service] Validation complete - "
                f"valid: {is_valid}, orphaned: {orphan_count}"
            )

            return response

        except Exception as e:
            logger.error(f"[Month Config Service] Validation error: {e}")
            raise


class TargetCPHService:
    """Business logic for Target CPH Configuration operations"""

    @staticmethod
    def get_configurations(
        main_lob: Optional[str] = None,
        case_type: Optional[str] = None
    ) -> Dict:
        """
        Get Target CPH configurations with optional filtering.

        Args:
            main_lob: Optional Main LOB filter
            case_type: Optional Case Type filter

        Returns:
            Dictionary with configurations list

        Example:
            >>> data = TargetCPHService.get_configurations(main_lob='Amisys')
            >>> len(data['data'])
            15
        """
        logger.info(
            f"[Target CPH Service] Fetching configurations - "
            f"main_lob: {main_lob}, case_type: {case_type}"
        )

        try:
            client = get_api_client()
            response = client.get_target_cph_configurations(main_lob, case_type)

            if not response.get('success', True):
                error_msg = response.get('error', 'Unknown error')
                logger.warning(f"[Target CPH Service] Fetch failed: {error_msg}")
                return response

            total = len(response.get('data', []))
            logger.info(f"[Target CPH Service] Retrieved {total} configurations")

            return response

        except Exception as e:
            logger.error(f"[Target CPH Service] Fetch error: {e}")
            raise

    @staticmethod
    def create_configuration(data: Dict) -> Dict:
        """
        Create a new Target CPH configuration.

        Args:
            data: Configuration data dictionary

        Returns:
            Success response with created configuration

        Example:
            >>> data = {'main_lob': 'Amisys', 'case_type': 'Claims', 'target_cph': 125.5}
            >>> response = TargetCPHService.create_configuration(data)
            >>> response['success']
            True
        """
        logger.info(
            f"[Target CPH Service] Creating configuration - "
            f"{data.get('main_lob')} / {data.get('case_type')}"
        )

        try:
            client = get_api_client()
            response = client.create_target_cph_configuration(data)

            if not response.get('success', True):
                error_msg = response.get('error', 'Unknown error')
                logger.warning(f"[Target CPH Service] Create failed: {error_msg}")
                return response

            logger.info("[Target CPH Service] Configuration created successfully")
            return response

        except Exception as e:
            logger.error(f"[Target CPH Service] Create error: {e}")
            raise

    @staticmethod
    def bulk_create_configurations(configs: List[Dict]) -> Dict:
        """
        Bulk create Target CPH configurations.

        Args:
            configs: List of configuration dictionaries

        Returns:
            Success response with created count

        Example:
            >>> configs = [{'main_lob': 'Amisys', 'case_type': 'Claims', ...}, ...]
            >>> response = TargetCPHService.bulk_create_configurations(configs)
            >>> response['created_count']
            10
        """
        logger.info(f"[Target CPH Service] Bulk creating {len(configs)} configurations")

        try:
            client = get_api_client()
            response = client.bulk_create_target_cph_configurations(configs)

            if not response.get('success', True):
                error_msg = response.get('error', 'Unknown error')
                logger.warning(f"[Target CPH Service] Bulk create failed: {error_msg}")
                return response

            created = response.get('created_count', 0)
            logger.info(f"[Target CPH Service] Bulk created {created} configurations")
            return response

        except Exception as e:
            logger.error(f"[Target CPH Service] Bulk create error: {e}")
            raise

    @staticmethod
    def update_configuration(config_id: int, data: Dict) -> Dict:
        """
        Update an existing Target CPH configuration.

        Args:
            config_id: ID of configuration to update
            data: Updated configuration data

        Returns:
            Success response with updated configuration

        Example:
            >>> response = TargetCPHService.update_configuration(1, {...})
            >>> response['success']
            True
        """
        logger.info(f"[Target CPH Service] Updating configuration ID: {config_id}")

        try:
            client = get_api_client()
            response = client.update_target_cph_configuration(config_id, data)

            if not response.get('success', True):
                error_msg = response.get('error', 'Unknown error')
                logger.warning(f"[Target CPH Service] Update failed: {error_msg}")
                return response

            logger.info(f"[Target CPH Service] Configuration {config_id} updated")
            return response

        except Exception as e:
            logger.error(f"[Target CPH Service] Update error: {e}")
            raise

    @staticmethod
    def delete_configuration(config_id: int) -> Dict:
        """
        Delete a Target CPH configuration.

        Args:
            config_id: ID of configuration to delete

        Returns:
            Success response

        Example:
            >>> response = TargetCPHService.delete_configuration(1)
            >>> response['success']
            True
        """
        logger.info(f"[Target CPH Service] Deleting configuration ID: {config_id}")

        try:
            client = get_api_client()
            response = client.delete_target_cph_configuration(config_id)

            if not response.get('success', True):
                error_msg = response.get('error', 'Unknown error')
                logger.warning(f"[Target CPH Service] Delete failed: {error_msg}")
                return response

            logger.info(f"[Target CPH Service] Configuration {config_id} deleted")
            return response

        except Exception as e:
            logger.error(f"[Target CPH Service] Delete error: {e}")
            raise

    @staticmethod
    def get_distinct_main_lobs() -> Dict:
        """
        Get distinct Main LOB values for dropdown.

        Returns:
            Dictionary with distinct values

        Example:
            >>> data = TargetCPHService.get_distinct_main_lobs()
            >>> len(data['data'])
            10
        """
        logger.info("[Target CPH Service] Fetching distinct Main LOBs")

        try:
            client = get_api_client()
            response = client.get_distinct_main_lobs()

            if not response.get('success', True):
                error_msg = response.get('error', 'Unknown error')
                logger.warning(f"[Target CPH Service] Fetch LOBs failed: {error_msg}")
                return response

            total = len(response.get('data', []))
            logger.info(f"[Target CPH Service] Retrieved {total} distinct LOBs")

            return response

        except Exception as e:
            logger.error(f"[Target CPH Service] Fetch LOBs error: {e}")
            raise

    @staticmethod
    def get_distinct_case_types(main_lob: Optional[str] = None) -> Dict:
        """
        Get distinct Case Type values for dropdown.

        Args:
            main_lob: Optional Main LOB to filter case types

        Returns:
            Dictionary with distinct values

        Example:
            >>> data = TargetCPHService.get_distinct_case_types('Amisys')
            >>> len(data['data'])
            5
        """
        logger.info(f"[Target CPH Service] Fetching distinct Case Types for LOB: {main_lob}")

        try:
            client = get_api_client()
            response = client.get_distinct_case_types(main_lob)

            if not response.get('success', True):
                error_msg = response.get('error', 'Unknown error')
                logger.warning(f"[Target CPH Service] Fetch Case Types failed: {error_msg}")
                return response

            total = len(response.get('data', []))
            logger.info(f"[Target CPH Service] Retrieved {total} distinct Case Types")

            return response

        except Exception as e:
            logger.error(f"[Target CPH Service] Fetch Case Types error: {e}")
            raise


# Convenience functions for direct import

# Month Configuration functions
def get_month_configurations(
    month: Optional[str] = None,
    year: Optional[int] = None,
    work_type: Optional[str] = None
) -> Dict:
    """Get month configurations with optional filtering."""
    return MonthConfigService.get_configurations(month, year, work_type)


def create_month_configuration(data: Dict) -> Dict:
    """Create a new month configuration."""
    return MonthConfigService.create_configuration(data)


def bulk_create_month_configurations(
    configs: List[Dict],
    created_by: str,
    skip_validation: bool = False
) -> Dict:
    """Bulk create month configurations."""
    return MonthConfigService.bulk_create_configurations(configs, created_by, skip_validation)


def update_month_configuration(config_id: int, data: Dict) -> Dict:
    """Update an existing month configuration."""
    return MonthConfigService.update_configuration(config_id, data)


def delete_month_configuration(config_id: int, allow_orphan: bool = False) -> Dict:
    """Delete a month configuration."""
    return MonthConfigService.delete_configuration(config_id, allow_orphan)


def validate_month_configurations() -> Dict:
    """Validate month configurations for orphaned records."""
    return MonthConfigService.validate_configurations()


# Target CPH Configuration functions
def get_target_cph_configurations(
    main_lob: Optional[str] = None,
    case_type: Optional[str] = None
) -> Dict:
    """Get Target CPH configurations with optional filtering."""
    return TargetCPHService.get_configurations(main_lob, case_type)


def create_target_cph_configuration(data: Dict) -> Dict:
    """Create a new Target CPH configuration."""
    return TargetCPHService.create_configuration(data)


def bulk_create_target_cph_configurations(configs: List[Dict]) -> Dict:
    """Bulk create Target CPH configurations."""
    return TargetCPHService.bulk_create_configurations(configs)


def update_target_cph_configuration(config_id: int, data: Dict) -> Dict:
    """Update an existing Target CPH configuration."""
    return TargetCPHService.update_configuration(config_id, data)


def delete_target_cph_configuration(config_id: int) -> Dict:
    """Delete a Target CPH configuration."""
    return TargetCPHService.delete_configuration(config_id)


def get_distinct_main_lobs() -> Dict:
    """Get distinct Main LOB values for dropdown."""
    return TargetCPHService.get_distinct_main_lobs()


def get_distinct_case_types(main_lob: Optional[str] = None) -> Dict:
    """Get distinct Case Type values for dropdown."""
    return TargetCPHService.get_distinct_case_types(main_lob)
