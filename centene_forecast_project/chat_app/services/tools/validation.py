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
    """
    month: int = Field(ge=1, le=12, description="Report month (1-12)")
    year: int = Field(ge=2020, le=2100, description="Report year")

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
        """Validate month and year ranges"""
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
    """
    conversation_id: str

    # Stored entities
    current_forecast_month: Optional[int] = None
    current_forecast_year: Optional[int] = None
    current_roster_month: Optional[int] = None
    current_roster_year: Optional[int] = None

    # Active filters (from last query)
    active_platforms: List[str] = Field(default_factory=list)
    active_markets: List[str] = Field(default_factory=list)
    active_localities: List[str] = Field(default_factory=list)
    active_states: List[str] = Field(default_factory=list)

    # Selected records
    selected_forecast_records: List[str] = Field(
        default_factory=list,
        description="Record IDs selected by user"
    )

    # Selected row from forecast modal (for FTE/CPH operations)
    selected_row: Optional[dict] = Field(
        default=None,
        description="Currently selected forecast row data for operations"
    )

    # Cached data
    last_forecast_data: Optional[dict] = Field(
        default=None,
        description="Last fetched forecast data response"
    )
    last_roster_data: Optional[dict] = Field(
        default=None,
        description="Last fetched roster data response"
    )

    # Metadata
    last_updated: datetime = Field(default_factory=datetime.now)
    turn_count: int = Field(default=0, description="Number of conversation turns")

    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


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
