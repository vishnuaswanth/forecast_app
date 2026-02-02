"""
Pydantic Models for Chat App LLM Service
Validation models for intent classification, forecast queries, and conversation context.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Tuple
from datetime import datetime
from enum import Enum
import re


class IntentCategory(str, Enum):
    """
    Enumeration of supported intent categories for user requests.
    """
    GET_FORECAST_DATA = "get_forecast_data"
    LIST_AVAILABLE_REPORTS = "list_available_reports"
    REALLOCATE_FORECAST = "reallocate_forecast_data"
    ALLOCATE_RAMP_FTES = "allocate_ramp_ftes"
    GET_ROSTER_DATA = "get_roster_data"
    MODIFY_ROSTER_DATA = "modify_roster_data"
    SHOW_ALLOCATED_RESOURCES = "show_allocated_resources"
    GET_FTE_DETAILS = "get_fte_details"  # Get FTE mapping info for selected row
    MODIFY_CPH = "modify_cph"  # Modify target CPH for selected row
    UNKNOWN = "unknown"


class IntentClassification(BaseModel):
    """
    Structured output from LLM intent classification.

    Contains the classified intent, confidence score, and extracted parameters.
    """
    category: IntentCategory
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")
    reasoning: str = Field(description="Explanation of why this intent was chosen")
    requires_clarification: bool = Field(default=False, description="Whether user input needs clarification")
    missing_parameters: List[str] = Field(default_factory=list, description="List of required missing parameters")


class ForecastQueryParams(BaseModel):
    """
    Parameters for forecast data queries - maps to /api/llm/forecast endpoint.

    All filter parameters are optional and support multiple values (arrays).
    Month and year are optional to allow the LLM to leave them unset when
    the user doesn't specify them - triggering a clarification request.
    """
    month: Optional[int] = Field(default=None, ge=1, le=12, description="Report month (1-12). Set to null if user did not specify.")
    year: Optional[int] = Field(default=None, ge=2020, le=2100, description="Report year. Set to null if user did not specify.")

    def is_missing_required(self) -> bool:
        """Check if required month/year parameters are missing."""
        return self.month is None or self.year is None

    def get_missing_fields(self) -> List[str]:
        """Get list of missing required fields."""
        missing = []
        if self.month is None:
            missing.append('month')
        if self.year is None:
            missing.append('year')
        return missing

    # Filter parameters (all optional, multi-value arrays)
    # Note: If main_lobs is provided, platforms/markets/localities are IGNORED per API precedence rules
    platforms: Optional[List[str]] = Field(
        default=None,
        description="Technology platforms: Amisys, Facets, Xcelys"
    )
    markets: Optional[List[str]] = Field(
        default=None,
        description="Insurance markets: Medicaid, Medicare"
    )
    localities: Optional[List[str]] = Field(
        default=None,
        description="Workforce locations: Domestic, Global"
    )
    main_lobs: Optional[List[str]] = Field(
        default=None,
        description="Full LOB strings like 'Amisys Medicaid Domestic'"
    )
    states: Optional[List[str]] = Field(
        default=None,
        description="US state codes (CA, TX) or N/A for non-state work"
    )
    case_types: Optional[List[str]] = Field(
        default=None,
        description="Work types: Claims Processing, Enrollment, etc"
    )
    forecast_months: Optional[List[str]] = Field(
        default=None,
        description="Month labels to include: Apr-25, May-25, Jun-25, etc"
    )

    # Output preferences (not sent to API, used for UI generation)
    show_totals_only: bool = Field(
        default=False,
        description="Show only totals table, not individual records"
    )
    max_records: int = Field(
        default=5,
        description="Max records to show in chat preview before modal"
    )

    @field_validator('month', 'year')
    @classmethod
    def validate_date(cls, v, info):
        """Validate month and year ranges (allow None for clarification flow)"""
        if v is None:
            return v
        field_name = info.field_name
        if field_name == 'month' and not (1 <= v <= 12):
            raise ValueError("Month must be between 1 and 12")
        if field_name == 'year' and not (2020 <= v <= 2100):
            raise ValueError("Year must be reasonable (2020-2100)")
        return v

    @field_validator('platforms', 'markets', 'localities', 'main_lobs', 'states', 'case_types')
    @classmethod
    def normalize_values(cls, v):
        """Normalize filter values - trim whitespace and title case"""
        if v is None:
            return v
        return [item.strip().title() if item else item for item in v]

    @field_validator('forecast_months')
    @classmethod
    def validate_month_format(cls, v):
        """Validate forecast month format (e.g., 'Apr-25', 'May-25')"""
        if v is None:
            return v

        for month_str in v:
            if not re.match(r'^[A-Z][a-z]{2}-\d{2}$', month_str):
                raise ValueError(
                    f"Invalid month format: {month_str}. "
                    "Expected format like 'Apr-25'"
                )
        return v


class RosterQueryParams(BaseModel):
    """Parameters for roster data queries"""
    month: int = Field(ge=1, le=12, description="Roster month (1-12)")
    year: int = Field(ge=2020, le=2100, description="Roster year")
    team_name: Optional[str] = Field(default=None, description="Team name filter")
    role: Optional[str] = Field(default=None, description="Role filter")

    @field_validator('month', 'year')
    @classmethod
    def validate_date(cls, v, info):
        """Validate month and year ranges"""
        field_name = info.field_name
        if field_name == 'month' and not (1 <= v <= 12):
            raise ValueError("Month must be between 1 and 12")
        if field_name == 'year' and not (2020 <= v <= 2100):
            raise ValueError("Year must be reasonable (2020-2100)")
        return v


class ConversationContext(BaseModel):
    """
    Tracks conversation state across turns.

    Stores entities, filters, and cached data to enable context-aware responses.
    Enhanced with comprehensive entity tracking for memory management.
    """
    conversation_id: str

    # ===== REPORT TYPE TRACKING =====
    active_report_type: Optional[str] = Field(
        default=None,
        description="Current report type: 'forecast' or 'roster'"
    )

    # ===== TIME PERIOD (Report month/year, not calendar) =====
    # Renamed from current_forecast_month/year for clarity
    forecast_report_month: Optional[int] = Field(
        default=None,
        ge=1, le=12,
        description="The report's period month (e.g., 3 for March report)"
    )
    forecast_report_year: Optional[int] = Field(
        default=None,
        ge=2020, le=2100,
        description="The report's year (e.g., 2025)"
    )

    # Legacy field names for backward compatibility
    current_forecast_month: Optional[int] = Field(default=None, description="Deprecated: use forecast_report_month")
    current_forecast_year: Optional[int] = Field(default=None, description="Deprecated: use forecast_report_year")
    current_roster_month: Optional[int] = None
    current_roster_year: Optional[int] = None

    # ===== ALL FORECAST FILTERS =====
    # Note: main_lobs overrides platforms/markets/localities per API precedence
    active_main_lobs: Optional[List[str]] = Field(
        default=None,
        description="Full LOB strings like 'Amisys Medicaid Domestic'. Overrides platform/market/locality."
    )
    active_platforms: List[str] = Field(default_factory=list)
    active_markets: List[str] = Field(default_factory=list)
    active_localities: List[str] = Field(default_factory=list)
    active_states: List[str] = Field(default_factory=list)
    active_case_types: List[str] = Field(
        default_factory=list,
        description="Work types: Claims Processing, Enrollment, etc."
    )

    # ===== FORECAST MONTH COLUMNS (6-month rolling forecast) =====
    forecast_months: Optional[Dict[int, str]] = Field(
        default=None,
        description="Available forecast month columns from report. Populated after data fetch. Format: {0: 'Apr-25', 1: 'May-25', ...}"
    )
    active_forecast_months: Optional[List[str]] = Field(
        default=None,
        description="Which forecast months to filter. None = show all 6 months. Format: ['Apr-25', 'May-25']"
    )

    # ===== USER PREFERENCES =====
    user_preferences: Dict[str, any] = Field(
        default_factory=lambda: {
            'show_totals_only': False,
            'max_preview_records': 5,
            'auto_apply_last_filters': True,
        },
        description="User display preferences"
    )

    # ===== QUERY HISTORY =====
    last_successful_query: Optional[Dict[str, any]] = Field(
        default=None,
        description="Last successful query parameters for repeat functionality"
    )
    pending_clarification: Optional[Dict[str, any]] = Field(
        default=None,
        description="Pending clarification details when waiting for user input"
    )

    # ===== SELECTED ROW PERSISTENCE =====
    # The currently selected forecast row for FTE/CPH operations
    # PERSISTENCE RULES:
    # - Keep until: report_type changes, OR different record is selected, OR CPH change on different record
    # - Clear when: switching from forecast to roster (or vice versa)
    selected_forecast_row: Optional[Dict[str, any]] = Field(
        default=None,
        description="Currently selected forecast row. Persists until report type changes or different row selected."
    )
    selected_row_key: Optional[str] = Field(
        default=None,
        description="Unique key for selected row: 'main_lob|state|case_type'"
    )

    # Legacy field for backward compatibility
    selected_row: Optional[dict] = Field(
        default=None,
        description="Deprecated: use selected_forecast_row"
    )

    # ===== SELECTED RECORDS =====
    selected_forecast_records: List[str] = Field(
        default_factory=list,
        description="Record IDs selected by user"
    )

    # ===== CACHED DATA =====
    last_forecast_data: Optional[dict] = Field(
        default=None,
        description="Last fetched forecast data response"
    )
    last_roster_data: Optional[dict] = Field(
        default=None,
        description="Last fetched roster data response"
    )

    # Report configuration (working_days, work_hours, shrinkage per month/locality)
    report_configuration: Optional[dict] = Field(
        default=None,
        description="Configuration for current report (working_days, work_hours, shrinkage by month and locality)"
    )

    # ===== METADATA =====
    last_updated: datetime = Field(default_factory=datetime.now)
    turn_count: int = Field(default=0, description="Number of conversation turns")

    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    # ===== HELPER METHODS =====

    def should_clear_selected_row(
        self,
        new_report_type: Optional[str] = None,
        new_row_key: Optional[str] = None
    ) -> bool:
        """
        Determine if selected_forecast_row should be cleared.

        Clear when:
        1. Report type changes (forecast → roster or vice versa)
        2. A different row is being selected (new_row_key != current)
        3. CPH change is for a different row

        Keep when:
        1. Same report type, no new selection
        2. Follow-up questions about the same row
        3. FTE details for same row
        """
        # Rule 1: Report type change
        if new_report_type and new_report_type != self.active_report_type:
            return True

        # Rule 2: Different row selected
        if new_row_key and new_row_key != self.selected_row_key:
            return True

        return False

    def update_selected_row(self, row_data: dict):
        """
        Update selected row with proper key generation.
        """
        self.selected_forecast_row = row_data
        self.selected_row_key = f"{row_data.get('main_lob')}|{row_data.get('state')}|{row_data.get('case_type')}"
        # Also update legacy field
        self.selected_row = row_data

    def clear_selected_row(self):
        """Clear selected row when appropriate."""
        self.selected_forecast_row = None
        self.selected_row_key = None
        self.selected_row = None

    def should_apply_forecast_month_filter(self) -> bool:
        """
        Determine if forecast month filter should be applied.

        Returns False (no filter) if:
        - active_forecast_months is None (initial state)
        - All 6 months are in active_forecast_months

        Returns True (apply filter) if:
        - active_forecast_months has fewer than 6 months
        """
        if self.active_forecast_months is None:
            return False  # No filter - show all months

        if self.forecast_months is None:
            return False  # Can't filter without knowing available months

        # If all 6 months are active, no need to filter
        all_months = set(self.forecast_months.values())
        active_months = set(self.active_forecast_months)

        return active_months != all_months and len(active_months) < len(all_months)

    def get_forecast_month_filter(self) -> Optional[List[str]]:
        """
        Get the filter to apply for forecast months.

        Returns None if no filter should be applied.
        Returns list of month names to include if filter should be applied.
        """
        if not self.should_apply_forecast_month_filter():
            return None
        return self.active_forecast_months

    def get_context_summary_for_llm(self) -> str:
        """
        Generate compact context string for LLM prompts.

        Returns a readable summary of current context state.
        """
        parts = []

        # Report type
        if self.active_report_type:
            parts.append(f"Report: {self.active_report_type.title()}")

        # Period
        if self.forecast_report_month and self.forecast_report_year:
            import calendar
            month_name = calendar.month_name[self.forecast_report_month]
            parts.append(f"Period: {month_name} {self.forecast_report_year}")
        elif self.current_forecast_month and self.current_forecast_year:
            # Fallback to legacy fields
            import calendar
            month_name = calendar.month_name[self.current_forecast_month]
            parts.append(f"Period: {month_name} {self.current_forecast_year}")

        # Filters (with main_lobs precedence)
        if self.active_main_lobs:
            parts.append(f"LOBs: {', '.join(self.active_main_lobs[:3])}")
        else:
            if self.active_platforms:
                parts.append(f"Platforms: {', '.join(self.active_platforms[:3])}")
            if self.active_markets:
                parts.append(f"Markets: {', '.join(self.active_markets[:3])}")
            if self.active_localities:
                parts.append(f"Localities: {', '.join(self.active_localities[:3])}")

        if self.active_states:
            parts.append(f"States: {', '.join(self.active_states[:5])}")

        if self.active_case_types:
            parts.append(f"Case Types: {', '.join(self.active_case_types[:3])}")

        # Forecast month filter
        if self.should_apply_forecast_month_filter():
            parts.append(f"Month Filter: {', '.join(self.active_forecast_months)}")

        # Preferences
        if self.user_preferences.get('show_totals_only'):
            parts.append("Display: Totals Only")

        # Selected row
        if self.selected_row_key:
            parts.append(f"Selected: {self.selected_row_key}")

        return " | ".join(parts) if parts else "No context set"

    def sync_legacy_fields(self):
        """
        Sync new fields with legacy fields for backward compatibility.
        Call this after updating either set of fields.
        """
        # Sync forecast month/year
        if self.forecast_report_month and not self.current_forecast_month:
            self.current_forecast_month = self.forecast_report_month
        elif self.current_forecast_month and not self.forecast_report_month:
            self.forecast_report_month = self.current_forecast_month

        if self.forecast_report_year and not self.current_forecast_year:
            self.current_forecast_year = self.forecast_report_year
        elif self.current_forecast_year and not self.forecast_report_year:
            self.forecast_report_year = self.current_forecast_year

        # Sync selected row
        if self.selected_forecast_row and not self.selected_row:
            self.selected_row = self.selected_forecast_row
        elif self.selected_row and not self.selected_forecast_row:
            self.selected_forecast_row = self.selected_row


class PreprocessedMessage(BaseModel):
    """
    Result of message preprocessing pipeline.

    Contains normalized text, XML-tagged text, and extracted entities.
    """
    original: str = Field(description="Original user input")
    normalized_text: str = Field(description="Clean, corrected text")
    tagged_text: str = Field(description="Text with XML entity tags")
    extracted_entities: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Extracted entities by type: {entity_type: [values]}"
    )
    corrections_made: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of corrections: [{original: ..., corrected: ...}]"
    )
    parsing_confidence: float = Field(
        default=0.5,
        ge=0.0, le=1.0,
        description="Confidence in parsing quality"
    )
    implicit_info: Dict[str, any] = Field(
        default_factory=dict,
        description="Implicit information detected (uses_previous_context, operation, reset_filter)"
    )

    def has_time_context(self) -> bool:
        """Check if month and year were extracted."""
        return bool(
            self.extracted_entities.get('month') and
            self.extracted_entities.get('year')
        )

    def has_filters(self) -> bool:
        """Check if any filter entities were extracted."""
        filter_types = ['platforms', 'markets', 'localities', 'states', 'case_types', 'main_lobs']
        return any(self.extracted_entities.get(ft) for ft in filter_types)

    def uses_previous_context(self) -> bool:
        """Check if message references previous context."""
        return self.implicit_info.get('uses_previous_context', False)


class FilterValidationSummary(BaseModel):
    """
    Summary of filter validation results.

    Tracks auto-corrections, confirmations needed, and rejections
    from pre-flight filter validation.

    Attributes:
        all_valid: Whether all filters passed validation
        auto_corrected: Filters auto-corrected (>90% confidence)
        needs_confirmation: Filters needing confirmation (60-90% confidence)
        rejected: Rejected filters (<60% confidence)

    Example:
        >>> summary = FilterValidationSummary()
        >>> summary.auto_corrected['platforms'] = ['Amisys']
        >>> summary.needs_confirmation['markets'] = [('Medcaid', 'Medicaid', 0.75)]
        >>> summary.has_issues()
        True
    """

    all_valid: bool = Field(
        default=True,
        description="Whether all filters passed validation"
    )
    auto_corrected: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Filters auto-corrected (>90% confidence): {field_name: [corrected_values]}"
    )
    needs_confirmation: Dict[str, List[Tuple[str, str, float]]] = Field(
        default_factory=dict,
        description="Filters needing confirmation (60-90% confidence): {field_name: [(original, suggested, confidence)]}"
    )
    rejected: Dict[str, List[Tuple[str, List[str]]]] = Field(
        default_factory=dict,
        description="Rejected filters (<60% confidence): {field_name: [(value, suggestions)]}"
    )

    def has_issues(self) -> bool:
        """
        Check if there are any validation issues requiring user action.

        Returns:
            True if confirmations or rejections exist, False otherwise

        Example:
            >>> summary = FilterValidationSummary()
            >>> summary.needs_confirmation['platforms'] = [('Amysis', 'Amisys', 0.85)]
            >>> summary.has_issues()
            True
        """
        return bool(self.needs_confirmation or self.rejected)

    def get_correction_count(self) -> int:
        """
        Get total number of auto-corrections made.

        Returns:
            Count of auto-corrected filter values

        Example:
            >>> summary = FilterValidationSummary()
            >>> summary.auto_corrected = {'platforms': ['Amisys'], 'markets': ['Medicaid']}
            >>> summary.get_correction_count()
            2
        """
        return sum(len(v) for v in self.auto_corrected.values())

    def get_confirmation_count(self) -> int:
        """
        Get total number of confirmations needed.

        Returns:
            Count of filter values needing user confirmation

        Example:
            >>> summary = FilterValidationSummary()
            >>> summary.needs_confirmation = {'platforms': [('Amysis', 'Amisys', 0.85)]}
            >>> summary.get_confirmation_count()
            1
        """
        return sum(len(v) for v in self.needs_confirmation.values())

    def get_rejection_count(self) -> int:
        """
        Get total number of rejections.

        Returns:
            Count of rejected filter values

        Example:
            >>> summary = FilterValidationSummary()
            >>> summary.rejected = {'states': [('ZZ', ['CA', 'TX', 'FL'])]}
            >>> summary.get_rejection_count()
            1
        """
        return sum(len(v) for v in self.rejected.values())
