"""
Calculation Tools for FTE and CPH Operations

Provides functions to calculate FTE requirements, capacity, and gap
using the correct business formulas with configuration parameters.

Formulas:
- FTE Required = ceil(forecast / (working_days * work_hours * (1 - shrinkage) * target_cph))
- Capacity = fte_available * working_days * work_hours * (1 - shrinkage) * target_cph
- Gap = capacity - forecast
"""
import logging
import math
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MonthConfiguration:
    """Configuration for a specific month and locality."""
    working_days: float
    work_hours: float
    shrinkage: float  # As decimal, e.g., 0.15 for 15%

    @property
    def effective_hours_factor(self) -> float:
        """Calculate working_days * work_hours * (1 - shrinkage)"""
        return self.working_days * self.work_hours * (1 - self.shrinkage)


@dataclass
class CalculationResult:
    """Result of FTE/Capacity calculation for a month."""
    month: str
    forecast: float
    fte_required: float
    fte_available: float
    capacity: float
    gap: float
    config_used: MonthConfiguration


def determine_locality(main_lob: str, case_type: str) -> str:
    """
    Determine locality (Domestic/Global) from main_lob and case_type.

    Rules:
    - If main_lob contains "domestic" (case-insensitive) -> "Domestic"
    - If case_type contains "domestic" (case-insensitive) -> "Domestic"
    - Otherwise -> "Global"

    Args:
        main_lob: Main LOB value (e.g., "Amisys Medicaid Domestic")
        case_type: Case type value (e.g., "Claims Processing")

    Returns:
        "Domestic" or "Global"
    """
    main_lob_lower = (main_lob or '').lower()
    case_type_lower = (case_type or '').lower()

    if 'domestic' in main_lob_lower or 'domestic' in case_type_lower:
        return 'Domestic'
    return 'Global'


def get_month_config(
    configuration: dict,
    month_label: str,
    locality: str
) -> Optional[MonthConfiguration]:
    """
    Extract configuration for a specific month and locality.

    Args:
        configuration: Report configuration dict from API
        month_label: Month label (e.g., "Apr-25", "May-25")
        locality: "Domestic" or "Global"

    Returns:
        MonthConfiguration or None if not found
    """
    if not configuration:
        logger.warning("[Calculation Tools] No configuration provided")
        return None

    try:
        # Expected structure:
        # configuration = {
        #     "Domestic": {
        #         "Apr-25": {"working_days": 22, "work_hours": 8, "shrinkage": 0.15},
        #         "May-25": {...}
        #     },
        #     "Global": {...}
        # }
        locality_config = configuration.get(locality, {})
        month_config = locality_config.get(month_label, {})

        if not month_config:
            # Try alternative structure where config is flat per month
            month_config = configuration.get(month_label, {})
            if locality in month_config:
                month_config = month_config[locality]

        if not month_config:
            logger.warning(
                f"[Calculation Tools] No config found for {locality}/{month_label}"
            )
            return None

        return MonthConfiguration(
            working_days=float(month_config.get('working_days', 22)),
            work_hours=float(month_config.get('work_hours', 8)),
            shrinkage=float(month_config.get('shrinkage', 0.15))
        )

    except Exception as e:
        logger.error(f"[Calculation Tools] Error parsing config: {e}")
        return None


def get_default_config() -> MonthConfiguration:
    """
    Get default configuration when no config is available.

    Returns:
        Default MonthConfiguration (22 days, 8 hours, 15% shrinkage)
    """
    return MonthConfiguration(
        working_days=22,
        work_hours=8,
        shrinkage=0.15
    )


def calculate_fte_required(
    forecast: float,
    target_cph: float,
    config: MonthConfiguration
) -> float:
    """
    Calculate FTE required using the business formula.

    Formula: ceil(forecast / (working_days * work_hours * (1 - shrinkage) * target_cph))

    Args:
        forecast: Forecast volume for the month
        target_cph: Target cases per hour
        config: Month configuration

    Returns:
        FTE required (rounded up)
    """
    if target_cph <= 0 or config.effective_hours_factor <= 0:
        logger.warning("[Calculation Tools] Invalid CPH or config, returning 0")
        return 0

    denominator = config.effective_hours_factor * target_cph
    fte_required = math.ceil(forecast / denominator)

    logger.debug(
        f"[Calculation Tools] FTE Req: ceil({forecast} / "
        f"({config.working_days} * {config.work_hours} * (1 - {config.shrinkage}) * {target_cph})) = {fte_required}"
    )

    return fte_required


def calculate_capacity(
    fte_available: float,
    target_cph: float,
    config: MonthConfiguration
) -> float:
    """
    Calculate capacity using the business formula.

    Formula: fte_available * working_days * work_hours * (1 - shrinkage) * target_cph

    Args:
        fte_available: Available FTE count
        target_cph: Target cases per hour
        config: Month configuration

    Returns:
        Capacity (total cases that can be processed)
    """
    capacity = fte_available * config.effective_hours_factor * target_cph

    logger.debug(
        f"[Calculation Tools] Capacity: {fte_available} * "
        f"({config.working_days} * {config.work_hours} * (1 - {config.shrinkage})) * {target_cph} = {capacity}"
    )

    return round(capacity)


def calculate_gap(capacity: float, forecast: float) -> float:
    """
    Calculate gap between capacity and forecast.

    Formula: capacity - forecast

    Args:
        capacity: Total capacity
        forecast: Forecast volume

    Returns:
        Gap (positive = surplus, negative = shortfall)
    """
    return capacity - forecast


def calculate_month_metrics(
    forecast: float,
    fte_available: float,
    target_cph: float,
    config: MonthConfiguration,
    month_label: str
) -> CalculationResult:
    """
    Calculate all metrics for a single month.

    Args:
        forecast: Forecast volume
        fte_available: Available FTEs
        target_cph: Target CPH
        config: Month configuration
        month_label: Month identifier

    Returns:
        CalculationResult with all calculated values
    """
    fte_required = calculate_fte_required(forecast, target_cph, config)
    capacity = calculate_capacity(fte_available, target_cph, config)
    gap = calculate_gap(capacity, forecast)

    return CalculationResult(
        month=month_label,
        forecast=forecast,
        fte_required=fte_required,
        fte_available=fte_available,
        capacity=capacity,
        gap=gap,
        config_used=config
    )


def calculate_cph_impact(
    row_data: dict,
    new_cph: float,
    configuration: dict
) -> Dict[str, dict]:
    """
    Calculate the impact of changing CPH for a forecast row.

    Args:
        row_data: Forecast row data with months dict
        new_cph: New target CPH value
        configuration: Report configuration from context

    Returns:
        Dictionary with old and new values for each month:
        {
            "Apr-25": {
                "forecast": 1000,
                "fte_available": 10,
                "old": {"fte_required": 5, "capacity": 1200, "gap": 200},
                "new": {"fte_required": 4, "capacity": 1500, "gap": 500},
                "config": {"working_days": 22, "work_hours": 8, "shrinkage": 0.15}
            },
            ...
        }
    """
    # Determine locality
    main_lob = row_data.get('main_lob', '')
    case_type = row_data.get('case_type', '')
    locality = determine_locality(main_lob, case_type)

    old_cph = row_data.get('target_cph', 0)
    months_data = row_data.get('months', {})

    result = {}

    for month_label, month_data in months_data.items():
        forecast = month_data.get('forecast', 0)
        fte_available = month_data.get('fte_available', 0)

        # Get configuration for this month
        config = get_month_config(configuration, month_label, locality)
        if not config:
            config = get_default_config()
            logger.warning(
                f"[Calculation Tools] Using default config for {month_label}/{locality}"
            )

        # Old values (from existing data or recalculate)
        old_fte_req = month_data.get('fte_required', 0)
        old_capacity = month_data.get('capacity', 0)
        old_gap = month_data.get('gap', 0)

        # If old values are 0 or missing, recalculate with old CPH
        if old_capacity == 0 and old_cph > 0:
            old_fte_req = calculate_fte_required(forecast, old_cph, config)
            old_capacity = calculate_capacity(fte_available, old_cph, config)
            old_gap = calculate_gap(old_capacity, forecast)

        # Calculate new values with new CPH
        new_fte_req = calculate_fte_required(forecast, new_cph, config)
        new_capacity = calculate_capacity(fte_available, new_cph, config)
        new_gap = calculate_gap(new_capacity, forecast)

        result[month_label] = {
            'forecast': forecast,
            'fte_available': fte_available,
            'old': {
                'fte_required': old_fte_req,
                'capacity': old_capacity,
                'gap': old_gap
            },
            'new': {
                'fte_required': new_fte_req,
                'capacity': new_capacity,
                'gap': new_gap
            },
            'config': {
                'working_days': config.working_days,
                'work_hours': config.work_hours,
                'shrinkage': config.shrinkage,
                'locality': locality
            }
        }

        logger.info(
            f"[Calculation Tools] {month_label}: CPH {old_cph} → {new_cph}, "
            f"Gap {old_gap:+d} → {new_gap:+d}"
        )

    return result


def validate_cph_value(new_cph: float, min_cph: float = 0.1, max_cph: float = 100.0) -> Tuple[bool, str]:
    """
    Validate that a CPH value is within acceptable range.

    Args:
        new_cph: CPH value to validate
        min_cph: Minimum allowed CPH
        max_cph: Maximum allowed CPH

    Returns:
        Tuple of (is_valid, error_message)
    """
    if new_cph <= 0:
        return False, "CPH must be greater than 0"

    if new_cph < min_cph:
        return False, f"CPH {new_cph} is below minimum ({min_cph})"

    if new_cph > max_cph:
        return False, f"CPH {new_cph} is above maximum ({max_cph})"

    return True, ""
