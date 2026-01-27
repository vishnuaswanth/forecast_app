"""
Filter Validation and Combination Diagnosis Tools
Proactive validation and reactive diagnosis for forecast queries.
"""

import logging
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher, get_close_matches
from dataclasses import dataclass, field
from enum import Enum
import calendar

from chat_app.repository import get_chat_api_client
from chat_app.utils.filter_cache import get_filter_cache
from chat_app.services.tools.validation import ForecastQueryParams

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence levels for fuzzy matching."""
    HIGH = "high"        # >90% - auto-correct
    MEDIUM = "medium"    # 60-90% - ask confirmation
    LOW = "low"          # <60% - reject


@dataclass
class ValidationResult:
    """Result of filter validation."""
    is_valid: bool
    field_name: str
    original_value: str
    corrected_value: Optional[str] = None
    confidence: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    suggestions: List[str] = field(default_factory=list)


@dataclass
class CombinationDiagnosticResult:
    """Result of filter combination diagnosis."""
    is_data_issue: bool  # True if no data exists for month/year
    is_combination_issue: bool  # True if filters don't combine
    problematic_filters: List[str] = field(default_factory=list)
    working_combinations: Dict[str, List[str]] = field(default_factory=dict)
    total_records_available: int = 0
    diagnosis_message: str = ""


class FilterValidator:
    """
    Validates filter values against available options using fuzzy matching.

    Confidence Thresholds:
    - >0.90 (HIGH): Auto-correct silently
    - 0.60-0.90 (MEDIUM): Ask user confirmation
    - <0.60 (LOW): Reject and show suggestions
    """

    # Confidence thresholds
    HIGH_CONFIDENCE = 0.90
    MEDIUM_CONFIDENCE = 0.60

    # State name to code mapping
    STATE_NAME_TO_CODE = {
        "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
        "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
        "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
        "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
        "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
        "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
        "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
        "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
        "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
        "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
        "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
        "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
        "wisconsin": "WI", "wyoming": "WY"
    }

    def __init__(self):
        self.cache = get_filter_cache()
        self.client = get_chat_api_client()

    async def get_filter_options(
        self,
        month: int,
        year: int,
        force_refresh: bool = False
    ) -> Optional[dict]:
        """
        Get filter options from API with caching.

        Args:
            month: Report month (1-12)
            year: Report year
            force_refresh: Skip cache and fetch fresh data

        Returns:
            Filter options dict or None if API fails
        """
        # Check cache first
        if not force_refresh:
            cached = self.cache.get(month, year)
            if cached:
                return cached

        # Fetch from API
        try:
            month_name = calendar.month_name[month]
            logger.info(
                f"[Filter Validator] Fetching filter options for "
                f"{month_name} {year}"
            )

            response = self.client.get_filter_options(month_name, year)
            filter_options = response.get('filter_options', {})

            # Cache the result
            self.cache.set(month, year, filter_options)

            logger.info(
                f"[Filter Validator] Retrieved {len(filter_options)} "
                f"filter option types"
            )

            return filter_options

        except Exception as e:
            logger.error(
                f"[Filter Validator] Failed to fetch filter options: {e}",
                exc_info=True
            )
            return None

    def fuzzy_match(
        self,
        user_value: str,
        valid_options: List[str]
    ) -> ValidationResult:
        """
        Perform fuzzy matching on a single value.

        Uses difflib.get_close_matches with cutoff=0.6 (60% similarity).

        Args:
            user_value: User-provided filter value
            valid_options: List of valid options from API

        Returns:
            ValidationResult with match confidence and suggestions
        """
        # Exact match (case-insensitive)
        for option in valid_options:
            if user_value.lower() == option.lower():
                return ValidationResult(
                    is_valid=True,
                    field_name="",  # Set by caller
                    original_value=user_value,
                    corrected_value=option,  # Normalize case
                    confidence=1.0,
                    confidence_level=ConfidenceLevel.HIGH
                )

        # Fuzzy match using difflib
        matches = get_close_matches(
            user_value.lower(),
            [opt.lower() for opt in valid_options],
            n=3,
            cutoff=0.6
        )

        if not matches:
            # No close matches - suggest all options
            return ValidationResult(
                is_valid=False,
                field_name="",
                original_value=user_value,
                confidence=0.0,
                confidence_level=ConfidenceLevel.LOW,
                suggestions=valid_options[:5]  # Top 5 suggestions
            )

        # Find original case version of best match
        best_match_lower = matches[0]
        best_match = next(
            opt for opt in valid_options
            if opt.lower() == best_match_lower
        )

        # Calculate confidence using SequenceMatcher
        confidence = SequenceMatcher(
            None,
            user_value.lower(),
            best_match_lower
        ).ratio()

        # Determine confidence level
        if confidence >= self.HIGH_CONFIDENCE:
            confidence_level = ConfidenceLevel.HIGH
        elif confidence >= self.MEDIUM_CONFIDENCE:
            confidence_level = ConfidenceLevel.MEDIUM
        else:
            confidence_level = ConfidenceLevel.LOW

        # Get original case versions for suggestions
        suggestions = [
            next(opt for opt in valid_options if opt.lower() == m)
            for m in matches
        ]

        return ValidationResult(
            is_valid=(confidence >= self.MEDIUM_CONFIDENCE),
            field_name="",
            original_value=user_value,
            corrected_value=best_match if confidence >= self.MEDIUM_CONFIDENCE else None,
            confidence=confidence,
            confidence_level=confidence_level,
            suggestions=suggestions
        )

    def normalize_state_value(self, user_value: str) -> str:
        """
        Normalize state names to codes (California → CA).

        Args:
            user_value: State name or code

        Returns:
            State code (2 letters) or original value
        """
        user_lower = user_value.lower().strip()

        # Already a code?
        if len(user_value) == 2:
            return user_value.upper()

        # Check state name mapping
        if user_lower in self.STATE_NAME_TO_CODE:
            return self.STATE_NAME_TO_CODE[user_lower]

        return user_value

    async def validate_all(
        self,
        params: ForecastQueryParams
    ) -> Dict[str, List[ValidationResult]]:
        """
        Validate all filter parameters in a ForecastQueryParams object.

        Args:
            params: Forecast query parameters to validate

        Returns:
            Dictionary mapping filter names to validation results
        """
        # Get filter options for the month/year
        filter_options = await self.get_filter_options(params.month, params.year)

        if not filter_options:
            logger.warning(
                "[Filter Validator] Could not fetch filter options - "
                "skipping validation"
            )
            return {}

        results = {}

        # Validate platforms
        if params.platforms:
            results['platforms'] = [
                self._validate_field(
                    'platforms',
                    value,
                    filter_options.get('platforms', [])
                )
                for value in params.platforms
            ]

        # Validate markets
        if params.markets:
            results['markets'] = [
                self._validate_field(
                    'markets',
                    value,
                    filter_options.get('markets', [])
                )
                for value in params.markets
            ]

        # Validate localities
        if params.localities:
            results['localities'] = [
                self._validate_field(
                    'localities',
                    value,
                    filter_options.get('localities', [])
                )
                for value in params.localities
            ]

        # Validate main_lobs
        if params.main_lobs:
            results['main_lobs'] = [
                self._validate_field(
                    'main_lobs',
                    value,
                    filter_options.get('main_lobs', [])
                )
                for value in params.main_lobs
            ]

        # Validate states (with normalization)
        if params.states:
            results['states'] = [
                self._validate_state_field(
                    value,
                    filter_options.get('states', [])
                )
                for value in params.states
            ]

        # Validate case_types
        if params.case_types:
            results['case_types'] = [
                self._validate_field(
                    'case_types',
                    value,
                    filter_options.get('case_types', [])
                )
                for value in params.case_types
            ]

        # Validate forecast_months
        if params.forecast_months:
            results['forecast_months'] = [
                self._validate_field(
                    'forecast_months',
                    value,
                    filter_options.get('forecast_months', [])
                )
                for value in params.forecast_months
            ]

        # Log summary
        total_validated = sum(len(v) for v in results.values())
        failed = sum(
            1 for vals in results.values()
            for val in vals if not val.is_valid
        )

        logger.info(
            f"[Filter Validator] Validated {total_validated} values, "
            f"{failed} failed"
        )

        return results

    def _validate_field(
        self,
        field_name: str,
        user_value: str,
        valid_options: List[str]
    ) -> ValidationResult:
        """Validate a single field value."""
        result = self.fuzzy_match(user_value, valid_options)
        result.field_name = field_name
        return result

    def _validate_state_field(
        self,
        user_value: str,
        valid_options: List[str]
    ) -> ValidationResult:
        """Validate state field with normalization."""
        # Normalize first
        normalized = self.normalize_state_value(user_value)
        result = self.fuzzy_match(normalized, valid_options)
        result.field_name = 'states'
        result.original_value = user_value  # Keep original for display
        return result


class CombinationDiagnostic:
    """
    Diagnoses why a filter combination returns 0 records.

    Uses incremental API testing to isolate problematic filters.
    """

    def __init__(self):
        self.client = get_chat_api_client()
        self.validator = FilterValidator()

    async def diagnose(
        self,
        params: ForecastQueryParams,
        api_response: dict
    ) -> CombinationDiagnosticResult:
        """
        Diagnose why a query returned 0 records.

        Strategy:
        1. Check if data exists for month/year (call filter-options)
        2. Check if ANY records exist (query with no filters)
        3. Remove filters one-by-one to identify problematic filter
        4. Fetch valid options for working combinations

        Args:
            params: Original query parameters
            api_response: API response with 0 records

        Returns:
            CombinationDiagnosticResult with diagnosis
        """
        logger.info(
            f"[Combination Diagnostic] Starting diagnosis for "
            f"{calendar.month_name[params.month]} {params.year}"
        )

        # Step 1: Check if data exists for this month/year
        filter_options = await self.validator.get_filter_options(
            params.month,
            params.year
        )

        if not filter_options:
            # No data uploaded for this month/year
            return CombinationDiagnosticResult(
                is_data_issue=True,
                is_combination_issue=False,
                problematic_filters=[],
                working_combinations={},
                total_records_available=0,
                diagnosis_message=(
                    f"No forecast data has been uploaded for "
                    f"{calendar.month_name[params.month]} {params.year}. "
                    f"Please upload data before querying."
                )
            )

        record_count = filter_options.get('record_count', 0) if isinstance(filter_options, dict) else 0

        # Step 2: Check if ANY records exist (no filters)
        try:
            base_data = await self._query_without_filters(params.month, params.year)
            if base_data.get('total_records', 0) == 0:
                # Data exists in metadata but no actual records
                return CombinationDiagnosticResult(
                    is_data_issue=True,
                    is_combination_issue=False,
                    problematic_filters=[],
                    working_combinations={},
                    total_records_available=0,
                    diagnosis_message=(
                        f"Data metadata exists for "
                        f"{calendar.month_name[params.month]} {params.year}, "
                        f"but no forecast records are available."
                    )
                )
        except Exception as e:
            logger.error(f"[Combination Diagnostic] Base query failed: {e}")
            return CombinationDiagnosticResult(
                is_data_issue=True,
                is_combination_issue=False,
                problematic_filters=[],
                working_combinations={},
                total_records_available=0,
                diagnosis_message=f"Error checking data availability: {str(e)}"
            )

        total_available = base_data.get('total_records', record_count)

        # Step 3: Isolate problematic filter(s)
        problematic_filters = await self._isolate_problematic_filters(params)

        # Step 4: Fetch working combinations
        working_combinations = await self._get_working_combinations(
            params,
            problematic_filters
        )

        # Step 5: Generate diagnosis message
        diagnosis = self._generate_diagnosis_message(
            params,
            problematic_filters,
            working_combinations,
            total_available
        )

        return CombinationDiagnosticResult(
            is_data_issue=False,
            is_combination_issue=True,
            problematic_filters=problematic_filters,
            working_combinations=working_combinations,
            total_records_available=total_available,
            diagnosis_message=diagnosis
        )

    async def _query_without_filters(self, month: int, year: int) -> dict:
        """Query with just month/year to get baseline record count."""
        month_name = calendar.month_name[month]
        return self.client.get_forecast_data(month_name, year)

    async def _isolate_problematic_filters(
        self,
        params: ForecastQueryParams
    ) -> List[str]:
        """
        Remove filters one-by-one to identify which break the combination.

        Returns:
            List of filter names that cause 0 records
        """
        month_name = calendar.month_name[params.month]
        problematic = []

        # Build filter dict
        filters = {}
        if params.platforms:
            filters['platform'] = params.platforms
        if params.markets:
            filters['market'] = params.markets
        if params.localities:
            filters['locality'] = params.localities
        if params.main_lobs:
            filters['main_lob'] = params.main_lobs
        if params.states:
            filters['state'] = params.states
        if params.case_types:
            filters['case_type'] = params.case_types

        # Test each filter by removing it
        for filter_name in filters.keys():
            test_filters = {k: v for k, v in filters.items() if k != filter_name}

            try:
                # Query with this filter removed
                test_data = self.client.get_forecast_data(
                    month_name,
                    params.year,
                    **test_filters
                )

                # If removing this filter yields records, it was problematic
                if test_data.get('total_records', 0) > 0:
                    problematic.append(filter_name)
                    logger.info(
                        f"[Combination Diagnostic] Identified problematic filter: "
                        f"{filter_name}"
                    )

            except Exception as e:
                logger.warning(
                    f"[Combination Diagnostic] Test query failed for "
                    f"{filter_name}: {e}"
                )

        return problematic

    async def _get_working_combinations(
        self,
        params: ForecastQueryParams,
        problematic_filters: List[str]
    ) -> Dict[str, List[str]]:
        """
        Fetch valid filter values for the working combination.

        Returns:
            Dictionary of filter_name → valid_values
        """
        # Query filter options to see what's actually available
        filter_options = await self.validator.get_filter_options(
            params.month,
            params.year
        )

        if not filter_options:
            return {}

        working = {}

        # For each problematic filter, show what values are available
        for filter_name in problematic_filters:
            # Map API parameter names back to filter option keys
            option_key_map = {
                'platform': 'platforms',
                'market': 'markets',
                'locality': 'localities',
                'main_lob': 'main_lobs',
                'state': 'states',
                'case_type': 'case_types'
            }

            option_key = option_key_map.get(filter_name, filter_name + 's')
            available_values = filter_options.get(option_key, [])

            if available_values:
                working[filter_name] = available_values

        return working

    def _generate_diagnosis_message(
        self,
        params: ForecastQueryParams,
        problematic_filters: List[str],
        working_combinations: Dict[str, List[str]],
        total_available: int
    ) -> str:
        """Generate human-readable diagnosis message."""
        month_name = calendar.month_name[params.month]

        if not problematic_filters:
            return (
                f"No records match your filters for {month_name} {params.year}. "
                f"All individual filter values appear valid, but this specific "
                f"combination doesn't exist in the data ({total_available} total records available)."
            )

        # Build message
        msg_parts = [
            f"Found {total_available} records for {month_name} {params.year}, "
            f"but your filter combination returned 0 results."
        ]

        msg_parts.append(f"\nProblematic filter(s): {', '.join(problematic_filters)}")

        for filter_name, valid_values in working_combinations.items():
            msg_parts.append(
                f"\nAvailable {filter_name} values with your other filters: "
                f"{', '.join(valid_values[:10])}"
                + ("..." if len(valid_values) > 10 else "")
            )

        msg_parts.append(
            "\nSuggestion: Try removing one of the problematic filters or "
            "selecting a different value from the available options above."
        )

        return ''.join(msg_parts)
