"""
Entity Extraction Service

Domain-specific entity extraction with validation and context merging.
Extracts entities from preprocessed messages and merges them with conversation context.
"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from chat_app.services.tools.validation import (
    ConversationContext,
    PreprocessedMessage,
    ForecastQueryParams
)

logger = logging.getLogger(__name__)


class ExtractedEntities(BaseModel):
    """
    Structured output from entity extraction.

    Contains all entity types that can be extracted from user messages.
    """
    # Time context
    report_month: Optional[int] = Field(
        default=None,
        ge=1, le=12,
        description="Report month (1-12)"
    )
    report_year: Optional[int] = Field(
        default=None,
        ge=2020, le=2100,
        description="Report year"
    )

    # Report type
    report_type: Optional[str] = Field(
        default=None,
        description="'forecast' or 'roster'"
    )

    # Filters
    platforms: List[str] = Field(default_factory=list)
    markets: List[str] = Field(default_factory=list)
    localities: List[str] = Field(default_factory=list)
    states: List[str] = Field(default_factory=list)
    case_types: List[str] = Field(default_factory=list)
    main_lobs: List[str] = Field(default_factory=list)

    # Forecast month filter
    forecast_months: List[str] = Field(
        default_factory=list,
        description="Specific forecast months to show: ['Apr-25', 'May-25']"
    )

    # Preferences
    show_totals_only: Optional[bool] = None

    # Context references
    uses_previous_context: bool = Field(
        default=False,
        description="Whether message references previous context ('same month', 'that platform')"
    )
    operation: Optional[str] = Field(
        default=None,
        description="Operation type: 'replace', 'extend', 'remove'"
    )
    reset_filter: bool = Field(
        default=False,
        description="Whether to reset filters ('all months', 'full data')"
    )

    def has_time_context(self) -> bool:
        """Check if month and year are present."""
        return self.report_month is not None and self.report_year is not None

    def has_filters(self) -> bool:
        """Check if any filters are present."""
        return bool(
            self.platforms or self.markets or self.localities or
            self.states or self.case_types or self.main_lobs
        )

    def to_dict_for_context_update(self) -> Dict[str, Any]:
        """Convert to dict suitable for context update."""
        update = {}

        if self.report_month is not None:
            update['forecast_report_month'] = self.report_month
            update['current_forecast_month'] = self.report_month  # Legacy

        if self.report_year is not None:
            update['forecast_report_year'] = self.report_year
            update['current_forecast_year'] = self.report_year  # Legacy

        if self.report_type:
            update['active_report_type'] = self.report_type

        if self.platforms:
            update['active_platforms'] = self.platforms

        if self.markets:
            update['active_markets'] = self.markets

        if self.localities:
            update['active_localities'] = self.localities

        if self.states:
            update['active_states'] = self.states

        if self.case_types:
            update['active_case_types'] = self.case_types

        if self.main_lobs:
            update['active_main_lobs'] = self.main_lobs

        if self.forecast_months:
            update['active_forecast_months'] = self.forecast_months

        if self.show_totals_only is not None:
            # Update user preferences dict
            update['_update_preference_show_totals'] = self.show_totals_only

        return update


class EntityExtractionService:
    """
    Service for extracting and managing entities from user messages.

    Handles:
    1. Converting preprocessed messages to structured entities
    2. Merging entities with existing context
    3. Building query params from context
    """

    def extract_from_preprocessed(
        self,
        preprocessed: PreprocessedMessage
    ) -> ExtractedEntities:
        """
        Extract structured entities from preprocessed message.

        Args:
            preprocessed: PreprocessedMessage with extracted_entities dict

        Returns:
            ExtractedEntities model
        """
        entities = preprocessed.extracted_entities
        implicit = preprocessed.implicit_info

        # Parse month
        report_month = None
        if 'month' in entities and entities['month']:
            try:
                report_month = int(entities['month'][0])
            except (ValueError, IndexError):
                pass

        # Parse year
        report_year = None
        if 'year' in entities and entities['year']:
            try:
                report_year = int(entities['year'][0])
            except (ValueError, IndexError):
                pass

        # Parse show_totals_only
        show_totals_only = None
        if 'show_totals_only' in entities and entities['show_totals_only']:
            show_totals_only = entities['show_totals_only'][0]

        return ExtractedEntities(
            report_month=report_month,
            report_year=report_year,
            report_type=entities.get('report_type', [None])[0] if 'report_type' in entities else None,
            platforms=entities.get('platforms', []),
            markets=entities.get('markets', []),
            localities=entities.get('localities', []),
            states=entities.get('states', []),
            case_types=entities.get('case_types', []),
            main_lobs=entities.get('main_lobs', []),
            forecast_months=entities.get('active_forecast_months', []),
            show_totals_only=show_totals_only,
            uses_previous_context=implicit.get('uses_previous_context', False),
            operation=implicit.get('operation'),
            reset_filter=implicit.get('reset_filter', False)
        )

    def merge_with_context(
        self,
        entities: ExtractedEntities,
        context: ConversationContext
    ) -> ConversationContext:
        """
        Merge extracted entities with existing context.

        Follows operation rules:
        - 'replace': Replace context values with new values
        - 'extend': Add new values to existing (for lists)
        - 'remove': Remove specified values from context
        - None/default: Replace if new values provided

        Args:
            entities: Newly extracted entities
            context: Existing conversation context

        Returns:
            Updated ConversationContext
        """
        operation = entities.operation or 'replace'

        # Handle time context
        if entities.report_month is not None:
            context.forecast_report_month = entities.report_month
            context.current_forecast_month = entities.report_month  # Legacy sync
        elif entities.uses_previous_context:
            # Keep existing values
            pass

        if entities.report_year is not None:
            context.forecast_report_year = entities.report_year
            context.current_forecast_year = entities.report_year  # Legacy sync
        elif entities.uses_previous_context:
            # Keep existing values
            pass

        # Handle report type
        if entities.report_type:
            # Check if we need to clear selected row on type change
            if context.should_clear_selected_row(new_report_type=entities.report_type):
                context.clear_selected_row()
            context.active_report_type = entities.report_type

        # Handle main_lobs (takes precedence)
        if entities.main_lobs:
            if operation == 'extend':
                context.active_main_lobs = list(set(
                    (context.active_main_lobs or []) + entities.main_lobs
                ))
            elif operation == 'remove':
                context.active_main_lobs = [
                    lob for lob in (context.active_main_lobs or [])
                    if lob not in entities.main_lobs
                ] or None
            else:
                context.active_main_lobs = entities.main_lobs
                # Clear granular filters when main_lobs is set
                if not entities.platforms:
                    context.active_platforms = []
                if not entities.markets:
                    context.active_markets = []
                if not entities.localities:
                    context.active_localities = []

        # Handle filter lists
        filter_mappings = [
            ('platforms', 'active_platforms'),
            ('markets', 'active_markets'),
            ('localities', 'active_localities'),
            ('states', 'active_states'),
            ('case_types', 'active_case_types'),
        ]

        for entity_key, context_key in filter_mappings:
            new_values = getattr(entities, entity_key)
            if new_values:
                current = getattr(context, context_key) or []
                if operation == 'extend':
                    setattr(context, context_key, list(set(current + new_values)))
                elif operation == 'remove':
                    setattr(context, context_key, [v for v in current if v not in new_values])
                else:
                    setattr(context, context_key, new_values)

        # Handle forecast month filter
        if entities.reset_filter:
            # Reset to show all months
            context.active_forecast_months = None
        elif entities.forecast_months:
            if operation == 'extend':
                context.active_forecast_months = list(set(
                    (context.active_forecast_months or []) + entities.forecast_months
                ))
            elif operation == 'remove':
                context.active_forecast_months = [
                    m for m in (context.active_forecast_months or [])
                    if m not in entities.forecast_months
                ] or None
            else:
                context.active_forecast_months = entities.forecast_months

        # Handle preferences
        if entities.show_totals_only is not None:
            context.user_preferences['show_totals_only'] = entities.show_totals_only

        # Sync legacy fields
        context.sync_legacy_fields()

        return context

    def build_params_from_context(
        self,
        context: ConversationContext
    ) -> ForecastQueryParams:
        """
        Build query params from context store.

        Ensures all stored entities are properly mapped to query params.
        """
        # Determine which filters to apply based on active_forecast_months
        forecast_month_filter = None
        if context.should_apply_forecast_month_filter():
            forecast_month_filter = context.active_forecast_months

        # Handle main_lobs precedence: if set, platforms/markets/localities are ignored
        platforms = None
        markets = None
        localities = None
        main_lobs = None

        if context.active_main_lobs:
            # main_lobs takes precedence - ignore granular filters
            main_lobs = context.active_main_lobs
        else:
            # Use granular filters
            platforms = context.active_platforms or None
            markets = context.active_markets or None
            localities = context.active_localities or None

        # Get month/year (prefer new fields, fall back to legacy)
        month = context.forecast_report_month or context.current_forecast_month
        year = context.forecast_report_year or context.current_forecast_year

        return ForecastQueryParams(
            # Time context
            month=month,
            year=year,

            # Filters (with main_lobs precedence)
            main_lobs=main_lobs,
            platforms=platforms,
            markets=markets,
            localities=localities,
            states=context.active_states or None,
            case_types=context.active_case_types or None,

            # Forecast month column filter (only if not all 6)
            forecast_months=forecast_month_filter,

            # Preferences
            show_totals_only=context.user_preferences.get('show_totals_only', False),
            max_records=context.user_preferences.get('max_preview_records', 5),
        )

    def validate_params_for_ui(
        self,
        params: ForecastQueryParams
    ) -> tuple[bool, List[str]]:
        """
        Validate params before sending to UI tools.

        Returns (is_valid, list_of_issues)
        """
        issues = []

        # Required: month and year
        if params.month is None:
            issues.append("Missing report month")
        if params.year is None:
            issues.append("Missing report year")

        # Validate month range
        if params.month is not None and not (1 <= params.month <= 12):
            issues.append(f"Invalid month: {params.month}")

        # Validate year range
        if params.year is not None and not (2020 <= params.year <= 2100):
            issues.append(f"Invalid year: {params.year}")

        # Validate known platform values (these are fixed)
        valid_platforms = {'Amisys', 'Facets', 'Xcelys'}
        if params.platforms:
            invalid = set(params.platforms) - valid_platforms
            if invalid:
                issues.append(f"Unknown platforms: {invalid}")

        # NOTE: Markets are NOT validated - there are many market types
        # Allow any market value from user input

        return len(issues) == 0, issues


# Singleton instance
_extraction_service: Optional[EntityExtractionService] = None


def get_extraction_service() -> EntityExtractionService:
    """Get or create extraction service instance."""
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = EntityExtractionService()
    return _extraction_service
