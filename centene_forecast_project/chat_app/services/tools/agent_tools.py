"""
Agent Tools Factory

Builds the list of LangChain tools for one agent invocation.
Each tool is an async closure that captures conversation_id and context_manager
so they don't need to be passed as tool arguments.

Tools:
    get_forecast_data       - Fetch forecast records and generate table HTML
    get_available_reports   - List available forecast report periods
    get_fte_details         - Show FTE breakdown for the selected row
    preview_cph_change      - Preview impact of a CPH value change
    update_filters          - Merge / replace / remove context filters
    clear_context           - Wipe all filters and cached state
"""
import logging
from typing import List, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from chat_app.services.tools.forecast_tools import (
    fetch_forecast_data,
    fetch_available_reports,
    call_get_applied_ramp,
)
from chat_app.services.tools.validation import ForecastQueryParams, ConversationContext
from chat_app.services.tools.ui_tools import (
    generate_forecast_table_html,
    generate_totals_table_html,
    generate_available_reports_ui,
    generate_fte_details_ui,
    generate_cph_preview_ui,
    generate_clear_context_ui,
    generate_context_update_ui,
    generate_error_ui,
    generate_ramp_trigger_ui,
    generate_applied_ramp_ui,
)
from chat_app.services.tools.calculation_tools import (
    calculate_cph_impact,
    determine_locality,
    validate_cph_value,
)
from chat_app.exceptions import APIError, APIClientError, ValidationError

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Input schemas
# ─────────────────────────────────────────────────────────────────────────────

class ForecastInput(BaseModel):
    month: int = Field(description="Report month (1-12)")
    year: int = Field(description="Report year (e.g. 2025)")
    platforms: List[str] = Field(default=[], description="Platform filters: Amisys, Facets, Xcelys")
    markets: List[str] = Field(default=[], description="Market filters: Medicaid, Medicare")
    localities: List[str] = Field(default=[], description="Locality filters: Domestic, Global")
    main_lobs: List[str] = Field(default=[], description="Full LOB strings like 'Amisys Medicaid Domestic'. Overrides platform/market/locality.")
    states: List[str] = Field(default=[], description="State filters: CA, TX, or N/A")
    case_types: List[str] = Field(default=[], description="Case type filters: Claims Processing, Enrollment, etc.")
    forecast_months: List[str] = Field(default=[], description="Month column filters: Apr-25, May-25 …")
    show_totals_only: bool = Field(default=False, description="Show totals table instead of individual records")


class FteDetailsInput(BaseModel):
    row_key: Optional[str] = Field(
        default=None,
        description="Row identifier 'main_lob|state|case_type'. Leave empty to use currently selected row."
    )


class CphChangeInput(BaseModel):
    new_cph: float = Field(description="The numeric CPH value to apply (always pass the absolute target value after applying the operation)")
    operation: str = Field(
        default="set_to",
        description=(
            "How to interpret new_cph: "
            "'set_to' (default) – use new_cph as the final value; "
            "'increase_by_pct' – increase current CPH by new_cph percent; "
            "'decrease_by_pct' – decrease current CPH by new_cph percent; "
            "'add_to' – add new_cph to current CPH; "
            "'subtract_from' – subtract new_cph from current CPH"
        )
    )


class UpdateFiltersInput(BaseModel):
    operation: str = Field(
        description=(
            "How to apply the new filter values: "
            "'extend' – merge into existing; "
            "'replace' – overwrite existing; "
            "'remove' – subtract from existing; "
            "'reset' – clear all filters (keep month/year)"
        )
    )
    platforms: List[str] = Field(default=[], description="Platform values")
    localities: List[str] = Field(default=[], description="Locality values")
    states: List[str] = Field(default=[], description="State values")
    case_types: List[str] = Field(default=[], description="Case type values")


class NoInput(BaseModel):
    """Tool that requires no parameters."""
    pass


class SetupRampInput(BaseModel):
    month: int = Field(description="Forecast month to configure ramp for (1-12)")
    year: int = Field(description="Forecast year (e.g. 2026)")


# ─────────────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────────────

def make_agent_tools(
    conversation_id: str,
    context: ConversationContext,
    context_manager,
) -> list:
    """
    Build the tool list for one agent invocation.

    Args:
        conversation_id: Active conversation ID (captured in closures)
        context: Current ConversationContext snapshot (captured in closures)
        context_manager: ConversationContextManager singleton

    Returns:
        List of LangChain StructuredTool instances ready for llm.bind_tools()
    """

    # ── get_forecast_data ────────────────────────────────────────────────────

    async def _get_forecast_data(
        month: int,
        year: int,
        platforms: List[str] = None,
        markets: List[str] = None,
        localities: List[str] = None,
        main_lobs: List[str] = None,
        states: List[str] = None,
        case_types: List[str] = None,
        forecast_months: List[str] = None,
        show_totals_only: bool = False,
    ) -> dict:
        """Fetch forecast data and return a rendered HTML table."""
        params = ForecastQueryParams(
            month=month,
            year=year,
            platforms=platforms or [],
            markets=markets or [],
            localities=localities or [],
            main_lobs=main_lobs or [],
            states=states or [],
            case_types=case_types or [],
            forecast_months=forecast_months or [],
            show_totals_only=show_totals_only,
        )

        try:
            data = await fetch_forecast_data(params, enable_validation=False)
        except APIClientError as e:
            return {
                "message": e.user_message,
                "ui_component": generate_error_ui(
                    e.user_message, error_type="validation",
                    admin_contact=False, error_code=e.error_code
                ),
                "data": {},
            }
        except APIError as e:
            return {
                "message": str(e),
                "ui_component": generate_error_ui(
                    "Data service temporarily unavailable.",
                    error_type="api", admin_contact=True
                ),
                "data": {},
            }
        except Exception as e:
            return {
                "message": f"Failed to fetch forecast data: {str(e)}",
                "ui_component": generate_error_ui(str(e), error_type="api", admin_contact=True),
                "data": {},
            }

        # Update context
        months_from_api = data.get('months', {})
        report_config = data.get('configuration')
        await context_manager.update_entities(
            conversation_id,
            active_report_type='forecast',
            last_forecast_data=data,
            forecast_report_month=month,
            forecast_report_year=year,
            current_forecast_month=month,
            current_forecast_year=year,
            active_main_lobs=params.main_lobs or None,
            active_platforms=params.platforms or [],
            active_markets=params.markets or [],
            active_localities=params.localities or [],
            active_states=params.states or [],
            active_case_types=params.case_types or [],
            forecast_months=months_from_api,
            report_configuration=report_config,
            last_successful_query=params.model_dump(),
        )

        # Generate UI
        records = data.get('records', [])
        months = data.get('months', {})

        if show_totals_only:
            ui = generate_totals_table_html(data.get('totals', {}), months)
            import calendar
            message = f"Forecast totals for {calendar.month_name[month]} {year}"
        else:
            if records:
                ui = generate_forecast_table_html(
                    records, months,
                    show_full=(len(records) <= 5),
                    max_preview=5,
                )
                message = (
                    f"Found {len(records)} forecast records"
                    if len(records) <= 5
                    else f"Showing 5 of {len(records)} records. Click 'View All' to see more."
                )
            else:
                import calendar
                ui = generate_error_ui(
                    f"No records found for {calendar.month_name[month]} {year} with the applied filters.",
                    error_type="validation", admin_contact=False
                )
                message = "No records found for the given filters."

        return {"message": message, "ui_component": ui, "data": data}

    # ── get_available_reports ────────────────────────────────────────────────

    async def _get_available_reports() -> dict:
        """List all available forecast report periods."""
        try:
            data = await fetch_available_reports()
        except Exception as e:
            return {
                "message": f"Failed to fetch reports: {str(e)}",
                "ui_component": generate_error_ui(
                    "Could not retrieve available reports.",
                    error_type="api", admin_contact=True
                ),
                "data": {},
            }

        ui = generate_available_reports_ui(data)
        reports = data.get('reports', [])
        total = len(reports)
        current = sum(1 for r in reports if r.get('is_valid', False))

        if total == 0:
            message = "No forecast reports are currently available. Please upload forecast data."
        else:
            periods = ", ".join(
                f"{r.get('month', '?')} {r.get('year', '?')}" for r in reports[:5]
            )
            if total > 5:
                periods += f", and {total - 5} more"
            message = (
                f"Found {total} forecast report{'s' if total != 1 else ''}"
                f" ({current} current). Available periods: {periods}."
            )

        return {"message": message, "ui_component": ui, "data": data}

    # ── get_fte_details ──────────────────────────────────────────────────────

    async def _get_fte_details(row_key: str = None) -> dict:
        """Show FTE breakdown for the currently selected forecast row."""
        # Refresh context to get selected row
        fresh_ctx = await context_manager.get_context(conversation_id)
        row_data = fresh_ctx.selected_forecast_row

        if not row_data:
            return {
                "message": "No row selected. Please select a row from the forecast table first.",
                "ui_component": generate_error_ui(
                    "Please select a row from the forecast table first.",
                    error_type="validation", admin_contact=False
                ),
                "data": {},
            }

        ui = generate_fte_details_ui(row_data)
        main_lob = row_data.get('main_lob', '')
        message = f"FTE details for {main_lob} | {row_data.get('state')} | {row_data.get('case_type')}"
        return {
            "message": message,
            "ui_component": ui,
            "data": {"row_key": row_key or fresh_ctx.selected_row_key},
        }

    # ── preview_cph_change ───────────────────────────────────────────────────

    async def _preview_cph_change(new_cph: float, operation: str = "set_to") -> dict:
        """Calculate and preview the impact of a CPH change on the selected row."""
        fresh_ctx = await context_manager.get_context(conversation_id)
        row_data = fresh_ctx.selected_forecast_row

        if not row_data:
            return {
                "message": "No row selected. Please select a row from the forecast table first.",
                "ui_component": generate_error_ui(
                    "Please select a row from the forecast table first.",
                    error_type="validation", admin_contact=False
                ),
                "data": {},
            }

        current_cph = float(row_data.get('target_cph', 0))

        # Resolve the final CPH from the operation
        if operation == "set_to":
            final_cph = new_cph
        elif operation == "increase_by_pct":
            final_cph = round(current_cph * (1 + new_cph / 100), 2)
        elif operation == "decrease_by_pct":
            final_cph = round(current_cph * (1 - new_cph / 100), 2)
        elif operation == "add_to":
            final_cph = round(current_cph + new_cph, 2)
        elif operation == "subtract_from":
            final_cph = round(current_cph - new_cph, 2)
        else:
            final_cph = new_cph

        is_valid, error_msg = validate_cph_value(final_cph)
        if not is_valid:
            return {
                "message": error_msg,
                "ui_component": generate_error_ui(error_msg, error_type="validation", admin_contact=False),
                "data": {},
            }

        locality = determine_locality(
            row_data.get('main_lob', ''),
            row_data.get('case_type', '')
        )
        impact_data = calculate_cph_impact(row_data, final_cph, fresh_ctx.report_configuration)
        ui = generate_cph_preview_ui(row_data, final_cph, impact_data, locality)

        return {
            "message": f"Preview: CPH {current_cph} → {final_cph} for {row_data.get('main_lob')}",
            "ui_component": ui,
            "data": {"old_cph": current_cph, "new_cph": final_cph, "impact": impact_data},
        }

    # ── update_filters ───────────────────────────────────────────────────────

    async def _update_filters(
        operation: str,
        platforms: List[str] = None,
        localities: List[str] = None,
        states: List[str] = None,
        case_types: List[str] = None,
    ) -> dict:
        """Merge, replace, remove, or reset conversation context filters."""
        fresh_ctx = await context_manager.get_context(conversation_id)

        new_platforms = [p.strip().title() for p in (platforms or [])]
        new_localities = [l.strip().title() for l in (localities or [])]
        new_states = [s.strip() for s in (states or [])]
        new_case_types = [c.strip().title() for c in (case_types or [])]

        if operation == "reset":
            updated = await context_manager.reset_filters(conversation_id, keep_month_year=True)
            message = "All filters have been reset."
            preserved = []
            if updated.forecast_report_month and updated.forecast_report_year:
                import calendar
                preserved.append(
                    f"Period: {calendar.month_name[updated.forecast_report_month]} {updated.forecast_report_year}"
                )
            return {
                "message": message,
                "ui_component": generate_context_update_ui(message, preserved),
                "data": {"operation": "reset"},
            }

        if operation == "extend":
            final_platforms = list(set(fresh_ctx.active_platforms + new_platforms))
            final_localities = list(set(fresh_ctx.active_localities + new_localities))
            final_states = list(set(fresh_ctx.active_states + new_states))
            final_case_types = list(set(fresh_ctx.active_case_types + new_case_types))
        elif operation == "replace":
            final_platforms = new_platforms if new_platforms else fresh_ctx.active_platforms
            final_localities = new_localities if new_localities else fresh_ctx.active_localities
            final_states = new_states if new_states else fresh_ctx.active_states
            final_case_types = new_case_types if new_case_types else fresh_ctx.active_case_types
        elif operation == "remove":
            final_platforms = [p for p in fresh_ctx.active_platforms if p not in new_platforms]
            final_localities = [l for l in fresh_ctx.active_localities if l not in new_localities]
            final_states = [s for s in fresh_ctx.active_states if s not in new_states]
            final_case_types = [c for c in fresh_ctx.active_case_types if c not in new_case_types]
        else:
            # Unknown operation – treat as extend
            logger.warning(f"[Agent Tools] Unknown update_filters operation: {operation}, defaulting to extend")
            final_platforms = list(set(fresh_ctx.active_platforms + new_platforms))
            final_localities = list(set(fresh_ctx.active_localities + new_localities))
            final_states = list(set(fresh_ctx.active_states + new_states))
            final_case_types = list(set(fresh_ctx.active_case_types + new_case_types))

        await context_manager.update_entities(
            conversation_id,
            active_platforms=final_platforms,
            active_localities=final_localities,
            active_states=final_states,
            active_case_types=final_case_types,
        )

        # Build human-readable summary
        changes = []
        if new_platforms:
            changes.append(f"Platforms: {', '.join(new_platforms)}")
        if new_localities:
            changes.append(f"Localities: {', '.join(new_localities)}")
        if new_states:
            changes.append(f"States: {', '.join(new_states)}")
        if new_case_types:
            changes.append(f"Case Types: {', '.join(new_case_types)}")

        verb = {"extend": "Added", "replace": "Replaced", "remove": "Removed"}.get(operation, "Updated")
        message = f"{verb}: {', '.join(changes)}" if changes else "Filters updated."

        return {
            "message": message,
            "ui_component": generate_context_update_ui(message),
            "data": {
                "operation": operation,
                "platforms": final_platforms,
                "localities": final_localities,
                "states": final_states,
                "case_types": final_case_types,
            },
        }

    # ── clear_context ────────────────────────────────────────────────────────

    async def _clear_context() -> dict:
        """Clear all conversation context – filters, selected row, cached data."""
        await context_manager.clear_context(conversation_id)
        return {
            "message": "All filters and previous selections have been reset. You can start fresh!",
            "ui_component": generate_clear_context_ui(),
            "data": {"cleared": True},
        }

    # ── setup_ramp_calculation ───────────────────────────────────────────────

    async def _setup_ramp_calculation(month: int, year: int) -> dict:
        """Set up the ramp configuration modal for the selected forecast row and month."""
        from chat_app.utils.week_calculator import calculate_weeks
        import calendar as cal

        fresh_ctx = await context_manager.get_context(conversation_id)
        row_data = fresh_ctx.selected_forecast_row

        if not row_data:
            return {
                "message": "No row selected. Please select a forecast row first.",
                "ui_component": generate_error_ui(
                    "Please select a forecast row before setting up a ramp.",
                    error_type="validation", admin_contact=False
                ),
                "data": {},
            }

        month_key = f"{year:04d}-{month:02d}"

        # Verify month_key is one of the 6 available forecast months in context
        if fresh_ctx.forecast_months:
            available_month_labels = set(fresh_ctx.forecast_months.values())
            # Build month label from month_key to match (e.g. "Jan-26")
            month_label_short = f"{cal.month_abbr[month]}-{str(year)[2:]}"
            if available_month_labels and month_label_short not in available_month_labels:
                avail_str = ", ".join(sorted(available_month_labels))
                return {
                    "message": f"{month_label_short} is not among the available forecast months ({avail_str}).",
                    "ui_component": generate_error_ui(
                        f"{month_label_short} is not in the available forecast months. Available: {avail_str}",
                        error_type="validation", admin_contact=False
                    ),
                    "data": {},
                }

        weeks = calculate_weeks(year, month)

        await context_manager.update_entities(
            conversation_id,
            selected_ramp_month_key=month_key,
        )

        month_label = f"{cal.month_name[month]} {year}"
        main_lob = row_data.get('main_lob', '')
        state = row_data.get('state', '')
        case_type = row_data.get('case_type', '')
        row_label = f"{main_lob} | {state} | {case_type}"

        ui = generate_ramp_trigger_ui(row_data, month_key, weeks)
        return {
            "message": f"Ramp input modal ready for {row_label} — {month_label}",
            "ui_component": ui,
            "data": {"month_key": month_key, "weeks": weeks},
        }

    # ── get_applied_ramp ─────────────────────────────────────────────────────

    async def _get_applied_ramp() -> dict:
        """Show the currently applied ramp for the selected forecast row and month."""
        fresh_ctx = await context_manager.get_context(conversation_id)
        row_data = fresh_ctx.selected_forecast_row
        month_key = fresh_ctx.selected_ramp_month_key

        if not row_data:
            return {
                "message": "No row selected. Please select a forecast row first.",
                "ui_component": generate_error_ui(
                    "Please select a forecast row first, then specify a month to view its ramp.",
                    error_type="validation", admin_contact=False
                ),
                "data": {},
            }

        if not month_key:
            return {
                "message": "No ramp month selected. Please set up a ramp for a specific month first.",
                "ui_component": generate_error_ui(
                    "No ramp month is set. Ask me to 'set up ramp for [month] [year]' first.",
                    error_type="validation", admin_contact=False
                ),
                "data": {},
            }

        forecast_id = int(row_data.get('forecast_id', row_data.get('id', 0)))
        main_lob = row_data.get('main_lob', '')
        state = row_data.get('state', '')
        case_type = row_data.get('case_type', '')
        row_label = f"{main_lob} | {state} | {case_type}"

        try:
            import calendar as cal
            year, month = int(month_key[:4]), int(month_key[5:7])
            month_label = f"{cal.month_name[month]} {year}"
        except (ValueError, IndexError):
            month_label = month_key

        try:
            data = await call_get_applied_ramp(forecast_id, month_key)
        except Exception as e:
            return {
                "message": f"Failed to retrieve applied ramp: {str(e)}",
                "ui_component": generate_error_ui(
                    "Could not retrieve the applied ramp from the server.",
                    error_type="api", admin_contact=True
                ),
                "data": {},
            }

        ui = generate_applied_ramp_ui(data, row_label, month_label)
        return {
            "message": f"Applied ramp for {row_label} — {month_label}",
            "ui_component": ui,
            "data": data,
        }

    # ── Assemble tool list ───────────────────────────────────────────────────

    get_forecast_tool = StructuredTool.from_function(
        coroutine=_get_forecast_data,
        name="get_forecast_data",
        description=(
            "Fetch forecast data for a given month and year with optional filters. "
            "Returns an HTML table of records or totals."
        ),
        args_schema=ForecastInput,
    )

    get_reports_tool = StructuredTool.from_function(
        coroutine=_get_available_reports,
        name="get_available_reports",
        description="List all available forecast report periods with their status and record counts.",
        args_schema=NoInput,
    )

    get_fte_tool = StructuredTool.from_function(
        coroutine=_get_fte_details,
        name="get_fte_details",
        description=(
            "Show FTE required, FTE available, capacity and gap breakdown for the currently "
            "selected forecast row. Optionally pass row_key to identify the row."
        ),
        args_schema=FteDetailsInput,
    )

    preview_cph_tool = StructuredTool.from_function(
        coroutine=_preview_cph_change,
        name="preview_cph_change",
        description=(
            "Preview the impact of changing the target CPH for the selected forecast row. "
            "Shows old → new FTE required, capacity, and gap for each forecast month. "
            "Generates a confirmation card with Confirm/Cancel buttons."
        ),
        args_schema=CphChangeInput,
    )

    update_filters_tool = StructuredTool.from_function(
        coroutine=_update_filters,
        name="update_filters",
        description=(
            "Update conversation context filters. "
            "operation='extend' adds to existing filters; "
            "'replace' overwrites them; "
            "'remove' subtracts values; "
            "'reset' clears all filters (but keeps the report period)."
        ),
        args_schema=UpdateFiltersInput,
    )

    clear_context_tool = StructuredTool.from_function(
        coroutine=_clear_context,
        name="clear_context",
        description=(
            "Completely clear the conversation context: all filters, selected row, "
            "report period, and cached data. Use when the user says 'start over', "
            "'clear everything', 'reset all', etc."
        ),
        args_schema=NoInput,
    )

    setup_ramp_tool = StructuredTool.from_function(
        coroutine=_setup_ramp_calculation,
        name="setup_ramp_calculation",
        description=(
            "Set up a weekly ramp configuration for the selected forecast row and a specific month. "
            "Calculates weeks for the month and opens the ramp input modal. "
            "REQUIRES a selected_forecast_row in context. "
            "Use when user says 'set up ramp', 'configure ramp', 'ramp calculation for [month]'."
        ),
        args_schema=SetupRampInput,
    )

    get_applied_ramp_tool = StructuredTool.from_function(
        coroutine=_get_applied_ramp,
        name="get_applied_ramp",
        description=(
            "Show the currently applied ramp for the selected forecast row and ramp month. "
            "REQUIRES both selected_forecast_row and selected_ramp_month_key in context. "
            "Use when user says 'show applied ramp', 'what ramp is set', 'view ramp'."
        ),
        args_schema=NoInput,
    )

    return [
        get_forecast_tool,
        get_reports_tool,
        get_fte_tool,
        preview_cph_tool,
        update_filters_tool,
        clear_context_tool,
        setup_ramp_tool,
        get_applied_ramp_tool,
    ]
