"""
UI Generation Tools
Functions for generating HTML tables and UI components for forecast data.

All user-facing content is HTML-escaped to prevent XSS vulnerabilities.
"""
import html as html_module
import logging
import json
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def generate_forecast_confirmation_card(month: int, year: int, filters: dict) -> str:
    """
    Generate a confirmation card for a proposed forecast data fetch.

    Args:
        month: Report month (1-12)
        year: Report year
        filters: Dict with optional filter keys (platforms, markets, localities,
                 main_lobs, states, case_types, show_totals_only)

    Returns:
        HTML string for the confirmation card with confirm/cancel buttons
    """
    import calendar

    month_name = calendar.month_name[month]

    parts = []
    if filters.get('main_lobs'):
        parts.append(f"LOBs: {', '.join(filters['main_lobs'])}")
    else:
        if filters.get('platforms'):
            parts.append(f"Platforms: {', '.join(filters['platforms'])}")
        if filters.get('markets'):
            parts.append(f"Markets: {', '.join(filters['markets'])}")
        if filters.get('localities'):
            parts.append(f"Localities: {', '.join(filters['localities'])}")
    if filters.get('states'):
        parts.append(f"States: {', '.join(filters['states'])}")
    if filters.get('case_types'):
        parts.append(f"Case Types: {', '.join(filters['case_types'])}")

    filter_summary = html_module.escape(', '.join(parts)) if parts else 'None — all data'
    display_mode = 'Totals only' if filters.get('show_totals_only') else 'Full records'

    logger.info(f"[UI Tools] Generated forecast confirmation card for {month_name} {year}")

    return f"""
<div class="forecast-confirm-card">
    <div class="forecast-confirm-header">
        <span class="forecast-confirm-icon">&#128202;</span>
        <span class="forecast-confirm-title">Fetch Forecast Data</span>
    </div>
    <div class="forecast-confirm-body">
        <div class="forecast-confirm-row">
            <span class="forecast-confirm-label">Period</span>
            <span class="forecast-confirm-value"><strong>{html_module.escape(month_name)} {year}</strong></span>
        </div>
        <div class="forecast-confirm-row">
            <span class="forecast-confirm-label">Filters</span>
            <span class="forecast-confirm-value">{filter_summary}</span>
        </div>
        <div class="forecast-confirm-row">
            <span class="forecast-confirm-label">Display</span>
            <span class="forecast-confirm-value">{display_mode}</span>
        </div>
    </div>
    <div class="forecast-confirm-actions">
        <button class="btn btn-primary btn-sm forecast-fetch-confirm-btn">
            &#10003; Yes, Fetch Data
        </button>
        <button class="btn btn-outline-secondary btn-sm forecast-fetch-cancel-btn">
            Cancel
        </button>
    </div>
</div>
"""


def generate_clear_context_ui() -> str:
    """
    Generate confirmation UI for context cleared.

    Returns:
        HTML string for context cleared confirmation card
    """
    logger.info("[UI Tools] Generated clear context confirmation UI")
    return '''
    <div class="chat-success-card">
        <div class="d-flex align-items-start">
            <div class="success-icon me-2" style="font-size: 24px; color: #28a745;">&#10003;</div>
            <div class="success-content flex-grow-1">
                <strong class="success-title">Context Cleared</strong>
                <p class="success-message mb-0">
                    All filters and previous selections have been reset. You can start fresh!
                </p>
            </div>
        </div>
    </div>
    '''


def generate_context_update_ui(message: str, preserved_items: list = None) -> str:
    """
    Generate confirmation UI for context update (selective filter reset).

    Args:
        message: What was updated (will be HTML-escaped)
        preserved_items: List of items that were preserved

    Returns:
        HTML string for context update confirmation card
    """
    # HTML-escape the message to prevent XSS
    safe_message = html_module.escape(str(message))

    preserved_html = ""
    if preserved_items:
        # HTML-escape each item
        safe_items = [html_module.escape(str(item)) for item in preserved_items]
        items = "".join(f"<li>{item}</li>" for item in safe_items)
        preserved_html = f'''
        <div class="preserved-items mt-2">
            <small class="text-muted">Preserved:</small>
            <ul class="mb-0 ps-3">{items}</ul>
        </div>
        '''

    logger.info("[UI Tools] Generated context update confirmation UI")
    return f'''
    <div class="chat-success-card">
        <div class="d-flex align-items-start">
            <div class="success-icon me-2" style="font-size: 24px; color: #28a745;">&#10003;</div>
            <div class="success-content flex-grow-1">
                <strong class="success-title">Filters Reset</strong>
                <p class="success-message mb-0">{safe_message}</p>
                {preserved_html}
            </div>
        </div>
    </div>
    '''


def generate_available_reports_ui(reports_data: dict) -> str:
    """
    Generate HTML card listing available forecast reports.

    Displays a summary line and table with columns:
    Report Period | Status | Records | Data Freshness

    Current reports are highlighted; outdated reports are dimmed.

    Args:
        reports_data: Dictionary from /api/llm/forecast/available-reports with:
            - reports: List of report dicts (month, year, is_valid, record_count, etc.)
            - total_reports: int

    Returns:
        HTML string for available reports card
    """
    reports = reports_data.get('reports', [])
    total_reports = reports_data.get('total_reports', len(reports))

    current_count = sum(1 for r in reports if r.get('is_valid', False))
    outdated_count = total_reports - current_count

    logger.info(
        f"[UI Tools] Generating available reports UI - "
        f"{total_reports} reports ({current_count} current, {outdated_count} outdated)"
    )

    # Summary header
    html = f'''
    <div class="available-reports-card">
        <div class="card">
            <div class="card-header bg-primary text-white">
                <h6 class="mb-0">
                    <i class="bi bi-file-earmark-bar-graph"></i>
                    Available Forecast Reports
                </h6>
            </div>
            <div class="card-body">
                <p class="mb-3">
                    <strong>{total_reports}</strong> report{"s" if total_reports != 1 else ""} available
                    (<span class="text-success">{current_count} current</span>,
                     <span class="text-muted">{outdated_count} outdated</span>)
                </p>
    '''

    if reports:
        html += '''
                <div class="table-responsive">
                    <table class="table table-sm table-bordered table-hover mb-0">
                        <thead class="table-light">
                            <tr>
                                <th>Report Period</th>
                                <th class="text-center">Status</th>
                                <th class="text-end">Records</th>
                                <th>Data Freshness</th>
                            </tr>
                        </thead>
                        <tbody>
        '''

        for report in reports:
            month = report.get('month', 'Unknown')
            year = report.get('year', '')
            is_valid = report.get('is_valid', False)
            record_count = report.get('records_count', 0)
            freshness = report.get('data_freshness', 'Unknown')

            # Status badge
            if is_valid:
                status_badge = '<span class="badge bg-success">Current</span>'
                row_class = ''
            else:
                status_badge = '<span class="badge bg-secondary">Outdated</span>'
                row_class = ' class="text-muted"'

            html += f'''
                            <tr{row_class}>
                                <td><strong>{month} {year}</strong></td>
                                <td class="text-center">{status_badge}</td>
                                <td class="text-end">{record_count:,} records</td>
                                <td><small>{freshness}</small></td>
                            </tr>
            '''

        html += '''
                        </tbody>
                    </table>
                </div>
        '''
    else:
        html += '''
                <div class="alert alert-info mb-0">
                    No forecast reports are currently available.
                    Please upload forecast data to get started.
                </div>
        '''

    html += '''
            </div>
        </div>
    </div>
    '''

    return html


def generate_forecast_table_html(
    records: List[dict],
    months: dict,
    show_full: bool = False,
    max_preview: int = 5
) -> str:
    """
    Generate responsive, scrollable HTML table for forecast data with pagination support.

    Format:
    - Two-tier headers: Fixed columns (Main LOB, State, Case Type, Target CPH) +
      Dynamic month columns with sub-headers (Forecast, FTE Req, FTE Avail, Capacity, Gap)
    - Color-coded gaps: Red (negative), Green (positive)
    - Scrollable horizontally and vertically
    - Client-side pagination for full data view

    Args:
        records: List of forecast records
        months: Dictionary mapping Month1, Month2, etc to Apr-25, May-25, etc
        show_full: Whether to show all records or preview (preview = max_preview rows)
        max_preview: Maximum records to show in preview mode

    Returns:
        HTML string for table with embedded data for JS pagination
    """
    total_records = len(records)
    month_labels = list(months.values())  # ["Apr-25", "May-25", ...]

    logger.info(
        f"[UI Tools] Generating forecast table (total: {total_records}, months: {len(month_labels)})"
    )

    # Build the two-tier header HTML
    def build_table_header():
        header_html = '''
            <thead class="table-light forecast-table-header">
                <tr>
                    <th rowspan="2" class="align-middle forecast-fixed-col forecast-col-lob">Main LOB</th>
                    <th rowspan="2" class="align-middle forecast-fixed-col forecast-col-state">State</th>
                    <th rowspan="2" class="align-middle forecast-fixed-col forecast-col-casetype">Case Type</th>
                    <th rowspan="2" class="align-middle forecast-fixed-col forecast-col-cph">Target CPH</th>
        '''
        # Month headers (colspan=5 for each month)
        for month_label in month_labels:
            header_html += f'<th colspan="5" class="text-center month-header">{month_label}</th>'

        header_html += '</tr><tr>'

        # Sub-headers for each month
        for _ in month_labels:
            header_html += '''
                <th class="text-center sub-header">Forecast</th>
                <th class="text-center sub-header">FTE Req</th>
                <th class="text-center sub-header">FTE Avail</th>
                <th class="text-center sub-header">Capacity</th>
                <th class="text-center sub-header">Gap</th>
            '''

        header_html += '</tr></thead>'
        return header_html

    # Build a single data row
    def build_data_row(record):
        row_html = f'''
            <tr>
                <td class="forecast-fixed-col forecast-col-lob">{record.get('main_lob', 'N/A')}</td>
                <td class="forecast-fixed-col forecast-col-state">{record.get('state', 'N/A')}</td>
                <td class="forecast-fixed-col forecast-col-casetype">{record.get('case_type', 'N/A')}</td>
                <td class="text-end forecast-fixed-col forecast-col-cph">{record.get('target_cph', 0):.1f}</td>
        '''

        # Month data
        for month_label in month_labels:
            month_data = record.get('months', {}).get(month_label, {})

            forecast = month_data.get('forecast', 0)
            fte_req = month_data.get('fte_required', 0)
            fte_avail = month_data.get('fte_available', 0)
            capacity = month_data.get('capacity', 0)
            gap = month_data.get('gap', 0)

            # Determine gap color class
            if gap < 0:
                gap_class = "gap-negative"
            elif gap > 0:
                gap_class = "gap-positive"
            else:
                gap_class = "text-muted"

            row_html += f'''
                <td class="text-end">{forecast:,.0f}</td>
                <td class="text-end">{fte_req}</td>
                <td class="text-end">{fte_avail}</td>
                <td class="text-end">{capacity:,.0f}</td>
                <td class="text-end {gap_class}"><strong>{gap:,.0f}</strong></td>
            '''

        row_html += '</tr>'
        return row_html

    # Determine preview records
    preview_records = records[:max_preview]

    # JSON encode data for client-side pagination
    # Use HTML entity encoding for safe embedding in HTML attributes
    import html as html_module
    records_json = html_module.escape(json.dumps(records))
    months_json = html_module.escape(json.dumps(month_labels))

    # Build the preview table (always shown inline)
    html = f'''
    <div class="forecast-paginated-table"
         data-forecast-records="{records_json}"
         data-forecast-months="{months_json}"
         data-total-records="{total_records}">
        <div class="forecast-table-wrapper">
            <table class="table table-sm table-bordered table-hover forecast-table">
                {build_table_header()}
                <tbody>
    '''

    # Add preview rows
    for record in preview_records:
        html += build_data_row(record)

    html += '''
                </tbody>
            </table>
        </div>
    '''

    # Add "View Full Data" button if more records than preview
    if total_records > max_preview:
        html += f'''
        <div class="mt-2 text-center">
            <button class="btn btn-sm btn-primary chat-view-full-btn"
                    data-record-count="{total_records}">
                View All {total_records} Records
            </button>
        </div>
        '''

    html += '</div>'

    return html


def generate_totals_table_html(totals: dict, months: dict) -> str:
    """
    Generate totals-only table.

    Args:
        totals: Dictionary of totals per month
        months: Dictionary mapping Month1, Month2, etc to Apr-25, May-25, etc

    Returns:
        HTML string for totals table
    """
    month_labels = list(months.values())

    logger.info(f"[UI Tools] Generating totals table for {len(month_labels)} months")

    html = '''
    <div class="totals-table-container">
        <h6 class="mb-2">Forecast Totals</h6>
        <table class="table table-sm table-bordered">
            <thead class="table-light">
                <tr>
                    <th>Month</th>
                    <th class="text-end">Forecast</th>
                    <th class="text-end">FTE Required</th>
                    <th class="text-end">FTE Available</th>
                    <th class="text-end">Capacity</th>
                    <th class="text-end">Gap</th>
                </tr>
            </thead>
            <tbody>
    '''

    for month_label in month_labels:
        if month_label in totals:
            month_totals = totals[month_label]
            gap = month_totals.get('gap_total', 0)

            # Determine gap color
            if gap < 0:
                gap_class = "text-danger"
            elif gap > 0:
                gap_class = "text-success"
            else:
                gap_class = "text-muted"

            html += f'''
            <tr>
                <td>{month_label}</td>
                <td class="text-end">{month_totals.get('forecast_total', 0):,.0f}</td>
                <td class="text-end">{month_totals.get('fte_required_total', 0)}</td>
                <td class="text-end">{month_totals.get('fte_available_total', 0)}</td>
                <td class="text-end">{month_totals.get('capacity_total', 0):,.0f}</td>
                <td class="text-end {gap_class}"><strong>{gap:,.0f}</strong></td>
            </tr>
            '''

    html += '''
            </tbody>
        </table>
    </div>
    '''

    return html


def generate_confirmation_ui(category: str, params: dict) -> str:
    """
    Build confirmation card HTML.

    Args:
        category: Intent category
        params: Extracted parameters

    Returns:
        HTML string for confirmation card
    """
    import calendar

    # Handle list_available_reports category (no parameters needed)
    if category == 'list_available_reports':
        params_json = json.dumps(params)
        logger.info(f"[UI Tools] Generated confirmation UI for category: {category}")
        return f'''
        <div class="chat-confirmation-card">
            <div class="confirmation-header">
                <strong>List Available Reports</strong>
            </div>
            <div class="confirmation-body">
                I'll retrieve a list of all available forecast reports.
            </div>
            <div class="confirmation-actions">
                <button class="btn btn-success btn-sm chat-confirm-btn"
                        data-category="{category}"
                        data-parameters='{params_json}'>
                    ✓ Yes, Show Reports
                </button>
                <button class="btn btn-secondary btn-sm chat-reject-btn"
                        data-category="{category}">
                    ✗ No, Let me clarify
                </button>
            </div>
        </div>
        '''

    # Format parameters for display
    param_display = []

    if 'month' in params and 'year' in params:
        month_name = calendar.month_name[params['month']]
        param_display.append(f"Report Period: {month_name} {params['year']}")

    # Show all applied filters
    if params.get('main_lobs'):
        param_display.append(f"LOB: {', '.join(params['main_lobs'])}")

    if params.get('platforms'):
        param_display.append(f"Platforms: {', '.join(params['platforms'])}")

    if params.get('markets'):
        param_display.append(f"Markets: {', '.join(params['markets'])}")

    if params.get('localities'):
        param_display.append(f"Localities: {', '.join(params['localities'])}")

    if params.get('states'):
        param_display.append(f"States: {', '.join(params['states'])}")

    if params.get('case_types'):
        param_display.append(f"Case Types: {', '.join(params['case_types'])}")

    if params.get('forecast_months'):
        param_display.append(f"Months: {', '.join(params['forecast_months'])}")

    if params.get('show_totals_only'):
        param_display.append("Display: Totals Only")

    params_html = '<br>'.join(param_display) if param_display else "No filters applied"

    # Encode parameters as JSON for the button
    params_json = json.dumps(params)

    logger.info(f"[UI Tools] Generated confirmation UI for category: {category}")

    return f'''
    <div class="chat-confirmation-card">
        <div class="confirmation-header">
            <strong>Confirm Forecast Query</strong>
        </div>
        <div class="confirmation-body">
            I'll fetch forecast data with these parameters:<br><br>
            {params_html}
        </div>
        <div class="confirmation-actions">
            <button class="btn btn-success btn-sm chat-confirm-btn"
                    data-category="{category}"
                    data-parameters='{params_json}'>
                ✓ Yes, Show Data
            </button>
            <button class="btn btn-secondary btn-sm chat-reject-btn"
                    data-category="{category}">
                ✗ No, Let me clarify
            </button>
        </div>
    </div>
    '''


def generate_error_ui(
    error_message: str,
    error_type: str = "unknown",
    admin_contact: bool = False,
    error_code: str = None
) -> str:
    """
    Generate error alert HTML with proper XSS protection.

    Supports both simple error messages and structured error cards.

    Args:
        error_message: Error message to display (will be HTML-escaped)
        error_type: Type of error ('llm', 'api', 'validation', 'context', 'unknown')
        admin_contact: Whether to show "contact admin" guidance
        error_code: Optional error code to display

    Returns:
        HTML string for error alert/card
    """
    # HTML-escape the message to prevent XSS
    safe_message = html_module.escape(str(error_message))

    logger.warning(f"[UI Tools] Generated error UI: {error_message[:100]}...")

    # For simple errors (backward compatibility), use simple alert
    if error_type == "unknown" and not admin_contact and not error_code:
        return f'<div class="alert alert-danger" role="alert"><strong>Error:</strong> {safe_message}</div>'

    # For structured errors, use error card format
    error_config = _get_error_ui_config(error_type)

    # Build footer elements
    footer_parts = []
    if error_code:
        safe_code = html_module.escape(str(error_code))
        footer_parts.append(f'<span class="error-code">Error: {safe_code}</span>')
    if admin_contact:
        footer_parts.append('<span class="admin-contact">Please contact admin if this persists.</span>')

    footer_html = ""
    if footer_parts:
        footer_html = f'''
            <div class="error-footer mt-2">
                <small class="text-muted">{" ".join(footer_parts)}</small>
            </div>
        '''

    safe_error_type = html_module.escape(error_type)
    return f'''
    <div class="chat-error-card error-{safe_error_type}" role="alert">
        <div class="d-flex align-items-start">
            <div class="error-icon me-2">{error_config["icon"]}</div>
            <div class="error-content flex-grow-1">
                <strong class="error-title">{error_config["title"]}</strong>
                <p class="error-message mb-1">{safe_message}</p>
                {footer_html}
            </div>
        </div>
    </div>
    '''


def _get_error_ui_config(error_type: str) -> Dict[str, str]:
    """Get icon and title configuration for error type."""
    configs = {
        "llm": {
            "icon": "\u26a0\ufe0f",  # Warning sign emoji
            "title": "AI Service Issue",
        },
        "api": {
            "icon": "\u26a0\ufe0f",  # Warning sign emoji
            "title": "Data Service Issue",
        },
        "validation": {
            "icon": "\u2139\ufe0f",  # Info sign emoji
            "title": "Invalid Input",
        },
        "context": {
            "icon": "\u2139\ufe0f",  # Info sign emoji
            "title": "Session Issue",
        },
        "unknown": {
            "icon": "\u26a0\ufe0f",  # Warning sign emoji
            "title": "Error",
        },
    }
    return configs.get(error_type, configs["unknown"])


def generate_clarification_ui(clarification_message: str) -> str:
    """
    Generate clarification request HTML with XSS protection.

    Args:
        clarification_message: Clarification message to display (will be HTML-escaped)

    Returns:
        HTML string for clarification alert
    """
    # HTML-escape the message to prevent XSS
    safe_message = html_module.escape(str(clarification_message))

    logger.info(f"[UI Tools] Generated clarification UI")
    return f'<div class="alert alert-info" role="alert">{safe_message}</div>'


def generate_validation_confirmation_ui(
    validation_summary,
    params
) -> str:
    """
    Generate UI for filter validation confirmation.

    Shows:
    - Auto-corrected filters (informational)
    - Filters needing confirmation (user action required)
    - Rejected filters with suggestions

    Args:
        validation_summary: FilterValidationSummary object with validation results
        params: ForecastQueryParams with original query parameters

    Returns:
        HTML string for validation confirmation UI
    """
    import json
    import calendar

    html = '<div class="alert alert-warning" role="alert">'
    html += '<h6 class="alert-heading"><i class="bi bi-exclamation-triangle"></i> Filter Validation</h6>'

    # Auto-corrections (informational)
    if validation_summary.auto_corrected:
        html += '<div class="mb-3">'
        html += '<strong>Auto-corrected:</strong><ul class="mb-0 mt-1">'
        for field_name, corrections in validation_summary.auto_corrected.items():
            html += f'<li>{field_name}: {", ".join(corrections)}</li>'
        html += '</ul></div>'

    # Confirmations needed
    if validation_summary.needs_confirmation:
        html += '<div class="mb-3">'
        html += '<strong>Please confirm these corrections:</strong>'
        html += '<ul class="mb-0 mt-1">'
        for field_name, confirmations in validation_summary.needs_confirmation.items():
            for original, suggested, confidence in confirmations:
                html += f'<li>{field_name}: Did you mean <strong>"{suggested}"</strong> instead of "{original}"? '
                html += f'<span class="badge bg-info">{confidence*100:.0f}% match</span></li>'
        html += '</ul></div>'

    # Rejections
    if validation_summary.rejected:
        html += '<div class="mb-3">'
        html += '<strong>Invalid values:</strong>'
        html += '<ul class="mb-0 mt-1">'
        for field_name, rejections in validation_summary.rejected.items():
            for value, suggestions in rejections:
                html += f'<li>{field_name}: "{value}" is not valid. '
                if suggestions:
                    html += f'Try: {", ".join(suggestions[:3])}'
                html += '</li>'
        html += '</ul></div>'

    html += '<hr>'
    html += '<div class="mt-3">'

    # Show original query
    month_name = calendar.month_name[params.month]
    html += f'<strong>Your Query:</strong> {month_name} {params.year}'

    applied_filters = []
    if params.platforms:
        applied_filters.append(f"Platforms: {', '.join(params.platforms)}")
    if params.markets:
        applied_filters.append(f"Markets: {', '.join(params.markets)}")
    if params.localities:
        applied_filters.append(f"Localities: {', '.join(params.localities)}")
    if params.states:
        applied_filters.append(f"States: {', '.join(params.states)}")
    if params.case_types:
        applied_filters.append(f"Case Types: {', '.join(params.case_types)}")

    if applied_filters:
        html += f'<br><small>{" | ".join(applied_filters)}</small>'

    html += '</div>'

    # Action buttons
    params_json = json.dumps(params.dict())

    html += '<div class="mt-3">'
    if validation_summary.needs_confirmation and not validation_summary.rejected:
        # Can proceed with confirmations
        html += f'''
        <button class="btn btn-success btn-sm chat-accept-corrections-btn"
                data-parameters='{params_json}'>
            ✓ Accept Corrections & Continue
        </button>
        '''

    html += '''
    <button class="btn btn-secondary btn-sm chat-reject-corrections-btn">
        ✗ Cancel & Revise Query
    </button>
    '''

    html += '</div></div>'

    logger.info("[UI Tools] Generated validation confirmation UI")
    return html


def generate_fte_details_ui(row_data: dict) -> str:
    """
    Generate FTE details card for a selected forecast row.

    Args:
        row_data: Selected forecast row with months dict

    Returns:
        HTML string for FTE details card
    """
    main_lob = row_data.get('main_lob', '')
    case_type = row_data.get('case_type', '')
    is_domestic = 'domestic' in main_lob.lower() or 'domestic' in case_type.lower()
    config_type = 'DOMESTIC' if is_domestic else 'GLOBAL'
    badge_class = 'bg-primary' if is_domestic else 'bg-secondary'

    months_html = ""
    for month_name, month_data in row_data.get('months', {}).items():
        gap = month_data.get('gap', 0)
        gap_class = 'gap-negative' if gap < 0 else 'gap-positive' if gap > 0 else ''
        fte_req = month_data.get('fte_required', 0)
        fte_avail = month_data.get('fte_available', 0)

        months_html += f'''
        <div class="fte-detail-item">
            <div class="fte-detail-label">{month_name}</div>
            <div class="fte-detail-value">
                FTE Req: {fte_req} |
                FTE Avail: {fte_avail} |
                <span class="{gap_class}">Gap: {gap:+d}</span>
            </div>
        </div>
        '''

    logger.info(f"[UI Tools] Generated FTE details UI for {main_lob}")
    return f'''
    <div class="fte-details-card">
        <div class="fte-details-header">
            FTE Details: {main_lob} | {row_data.get('state')} | {case_type}
        </div>
        <div class="fte-config-badge" style="margin-bottom: 12px;">
            <span class="badge {badge_class}">
                {config_type} Configuration
            </span>
            <span style="margin-left: 8px;">Target CPH: {row_data.get('target_cph', 'N/A')}</span>
        </div>
        <div class="fte-details-grid">
            {months_html}
        </div>
    </div>
    '''


def generate_cph_preview_ui(row_data: dict, new_cph: float, impact_data: dict, locality: str) -> str:
    """
    Generate CPH change preview card.

    Args:
        row_data: Selected forecast row data
        new_cph: New CPH value
        impact_data: Output of calculate_cph_impact() - monthly old/new values
        locality: 'Domestic' or 'Global'

    Returns:
        HTML string for CPH preview card with confirm/cancel buttons
    """
    import json as _json

    old_cph = row_data.get('target_cph', 0)
    main_lob = row_data.get('main_lob', '')
    case_type = row_data.get('case_type', '')
    config_type = locality.upper()
    is_domestic = locality == 'Domestic'
    badge_class = 'bg-primary' if is_domestic else 'bg-secondary'

    preview_data = {
        'main_lob': main_lob,
        'state': row_data.get('state'),
        'case_type': case_type,
        'old_cph': old_cph,
        'new_cph': new_cph,
        'config_type': config_type,
        'locality': locality,
        'months': impact_data,
    }

    months_preview_html = ""
    for month_name, month_impact in impact_data.items():
        old_values = month_impact['old']
        new_values = month_impact['new']
        config_used = month_impact.get('config', {})

        old_gap = old_values['gap']
        new_gap = new_values['gap']
        new_gap_class = 'gap-positive' if new_gap >= 0 else 'gap-negative'

        config_info = ""
        if config_used:
            config_info = f'''
            <div class="cph-config-info" style="font-size: 10px; color: #888; margin-top: 4px;">
                {config_used.get('working_days', 22)}d &times; {config_used.get('work_hours', 8)}h &times;
                {100 - int(config_used.get('shrinkage', 0.15) * 100)}% productivity
            </div>
            '''

        months_preview_html += f'''
        <div class="cph-month-preview">
            <strong>{month_name}</strong>
            <div class="cph-preview-row">
                <span class="cph-preview-label">FTE Required:</span>
                <span class="cph-preview-old">{old_values['fte_required']}</span>
                <span class="cph-preview-arrow">&rarr;</span>
                <span class="cph-preview-new">{new_values['fte_required']}</span>
            </div>
            <div class="cph-preview-row">
                <span class="cph-preview-label">Capacity:</span>
                <span class="cph-preview-old">{old_values['capacity']:,}</span>
                <span class="cph-preview-arrow">&rarr;</span>
                <span class="cph-preview-new">{new_values['capacity']:,}</span>
            </div>
            <div class="cph-preview-row">
                <span class="cph-preview-label">Gap:</span>
                <span class="cph-preview-old">{old_gap:+d}</span>
                <span class="cph-preview-arrow">&rarr;</span>
                <span class="cph-preview-new {new_gap_class}">{new_gap:+d}</span>
            </div>
            {config_info}
        </div>
        '''

    preview_data_json = _json.dumps(preview_data).replace('"', '&quot;')

    logger.info(f"[UI Tools] Generated CPH preview UI: {old_cph} -> {new_cph}")
    return f'''
    <div class="cph-preview-card">
        <div class="cph-preview-header">
            CPH Change Preview
            <span class="badge {badge_class} ms-2">{config_type}</span>
        </div>
        <div class="cph-preview-row" style="margin-bottom: 16px;">
            <span class="cph-preview-label">Target CPH:</span>
            <span class="cph-preview-old">{old_cph}</span>
            <span class="cph-preview-arrow">&rarr;</span>
            <span class="cph-preview-new">{new_cph}</span>
        </div>
        <div class="cph-preview-subtitle">
            <strong>{main_lob}</strong> | {row_data.get('state')} | {case_type}
        </div>
        <div class="cph-months-preview">
            {months_preview_html}
        </div>
        <div class="cph-preview-actions">
            <button class="cph-confirm-btn" data-update="{preview_data_json}">
                Confirm Change
            </button>
            <button class="cph-reject-btn">Cancel</button>
        </div>
    </div>
    '''


def generate_combination_diagnostic_ui(
    diagnosis_message: str,
    working_combinations: Dict[str, List[str]],
    total_records: int
) -> str:
    """
    Generate UI for filter combination diagnosis with XSS protection.

    Shows:
    - LLM-generated diagnosis explanation
    - Available filter combinations that would work
    - Suggestions for alternative queries

    Args:
        diagnosis_message: LLM-generated diagnostic message (will be HTML-escaped)
        working_combinations: Valid filter values for working combinations
        total_records: Total records available

    Returns:
        HTML string for diagnostic UI
    """
    # HTML-escape the diagnosis message
    safe_message = html_module.escape(str(diagnosis_message))

    result = '<div class="alert alert-warning" role="alert">'
    result += '<h6 class="alert-heading"><i class="bi bi-search"></i> No Records Found - Diagnosis</h6>'

    # Diagnosis message (escaped)
    result += f'<p class="mb-2">{safe_message}</p>'

    result += '<hr>'

    # Working combinations (escape all values)
    if working_combinations:
        result += '<div class="mt-2">'
        result += '<strong>Available Options:</strong>'
        result += '<ul class="mb-0 mt-1">'

        for filter_name, valid_values in working_combinations.items():
            # Escape filter name and values
            safe_filter_name = html_module.escape(filter_name.replace("_", " ").title())
            safe_values = [html_module.escape(str(v)) for v in valid_values[:10]]
            display_values = ', '.join(safe_values)
            if len(valid_values) > 10:
                display_values += f' (and {len(valid_values) - 10} more)'

            result += f'<li><strong>{safe_filter_name}:</strong> {display_values}</li>'

        result += '</ul></div>'

    # Statistics (total_records is an int, safe to use directly)
    result += '<div class="mt-3">'
    result += '<small class="text-muted">'
    result += f'<strong>Total records available:</strong> {total_records:,}<br>'
    result += '<strong>Suggestion:</strong> Try removing one of the problematic filters or selecting a different value from the available options above.'
    result += '</small>'
    result += '</div>'

    result += '</div>'

    logger.info("[UI Tools] Generated combination diagnostic UI")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Ramp Calculation UI Generators
# ─────────────────────────────────────────────────────────────────────────────

def generate_ramp_trigger_ui(
    row_data: dict,
    month_key: str,
    weeks: list,
) -> str:
    """
    Generate a chat card with a "Configure Ramp" button.

    Embeds the pre-calculated weeks JSON as a data attribute so the JS
    modal never needs to re-derive weeks from scratch.

    Args:
        row_data: Selected forecast row (main_lob, state, case_type, forecast_id)
        month_key: Target month in 'YYYY-MM' format
        weeks: Output of calculate_weeks() for the given month

    Returns:
        HTML string for ramp trigger card
    """
    import calendar as cal
    main_lob = html_module.escape(str(row_data.get('main_lob', 'N/A')))
    state = html_module.escape(str(row_data.get('state', 'N/A')))
    case_type = html_module.escape(str(row_data.get('case_type', 'N/A')))
    forecast_id = int(row_data.get('forecast_id', row_data.get('id', 0)))

    try:
        year, month = int(month_key[:4]), int(month_key[5:7])
        month_label = f"{cal.month_name[month]} {year}"
    except (ValueError, IndexError):
        month_label = month_key

    weeks_json = html_module.escape(json.dumps(weeks))

    logger.info(f"[UI Tools] Generated ramp trigger UI for {main_lob} | {month_key}")
    return f'''
    <div class="ramp-trigger-card card border-info">
        <div class="card-header bg-info text-white d-flex align-items-center justify-content-between">
            <span><i class="bi bi-graph-up-arrow"></i> Ramp Configuration</span>
            <span class="badge bg-white text-info">{month_label}</span>
        </div>
        <div class="card-body">
            <p class="mb-1"><strong>Row:</strong> {main_lob} &bull; {state} &bull; {case_type}</p>
            <p class="mb-3 text-muted"><small>{len(weeks)} week{'' if len(weeks) == 1 else 's'} in {month_label}</small></p>
            <button class="btn btn-info ramp-open-modal-btn"
                    data-ramp-weeks="{weeks_json}"
                    data-ramp-month-key="{html_module.escape(month_key)}"
                    data-forecast-id="{forecast_id}">
                Configure Ramp
            </button>
        </div>
    </div>
    '''


def generate_ramp_confirmation_ui(
    row_label: str,
    month_label: str,
    weeks: list,
) -> str:
    """
    Generate a confirmation card summarising the per-week ramp data the user submitted.

    Two action buttons:
      - "Yes, Proceed"   → class="ramp-confirm-btn"
      - "No, Edit Again" → class="ramp-edit-btn"

    Args:
        row_label: Human-readable row identifier (e.g. "Amisys | CA | Claims Processing")
        month_label: Human-readable month label (e.g. "January 2026")
        weeks: List of submitted week dicts (label, workingDays, rampPercent, rampEmployees)

    Returns:
        HTML string for ramp confirmation card
    """
    safe_row = html_module.escape(str(row_label))
    safe_month = html_module.escape(str(month_label))
    submission_json = html_module.escape(json.dumps({"weeks": weeks}))

    rows_html = ""
    total_employees = sum(w.get('rampEmployees', 0) for w in weeks)
    for w in weeks:
        label = html_module.escape(str(w.get('label', '')))
        working_days = int(w.get('workingDays', 0))
        ramp_pct = float(w.get('rampPercent', 0))
        ramp_emp = int(w.get('rampEmployees', 0))
        rows_html += f'''
            <tr>
                <td>{label}</td>
                <td class="text-center">{working_days}</td>
                <td class="text-center">{ramp_pct:.1f}%</td>
                <td class="text-center">{ramp_emp:,}</td>
            </tr>
        '''

    logger.info(f"[UI Tools] Generated ramp confirmation UI for {row_label} | {month_label}")
    return f'''
    <div class="ramp-confirmation-card card border-warning">
        <div class="card-header bg-warning text-dark">
            <strong>Confirm Ramp Submission</strong>
        </div>
        <div class="card-body">
            <p class="mb-1"><strong>Row:</strong> {safe_row}</p>
            <p class="mb-3"><strong>Month:</strong> {safe_month}</p>
            <div class="table-responsive">
                <table class="table table-sm table-bordered ramp-confirmation-table mb-2">
                    <thead class="table-light">
                        <tr>
                            <th>Week</th>
                            <th class="text-center">Working Days</th>
                            <th class="text-center">Ramp %</th>
                            <th class="text-center">Ramp Employees</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                    <tfoot class="table-light fw-bold">
                        <tr>
                            <td colspan="3" class="text-end">Total Ramp Employees</td>
                            <td class="text-center">{total_employees:,}</td>
                        </tr>
                    </tfoot>
                </table>
            </div>
            <div class="d-flex gap-2">
                <button class="btn btn-success ramp-confirm-btn"
                        data-ramp-submission="{submission_json}">
                    Yes, Proceed
                </button>
                <button class="btn btn-secondary ramp-edit-btn">
                    No, Edit Again
                </button>
            </div>
        </div>
    </div>
    '''


def generate_ramp_preview_ui(preview_response: dict) -> str:
    """
    Generate a diff preview card showing current vs projected values.

    Expected preview_response structure:
        {
            "preview": {
                "current":   {"forecast": …, "fte_required": …, "fte_available": …, "capacity": …, "gap": …},
                "projected": { same fields },
                "diff":      { same fields (projected - current) }
            }
        }

    Two action buttons:
      - "Confirm Apply"  → class="ramp-apply-btn"
      - "Cancel"         → class="ramp-cancel-btn"

    Args:
        preview_response: Response dict from preview API call

    Returns:
        HTML string for ramp preview card
    """
    preview = preview_response.get('preview', preview_response)
    current = preview.get('current', {})
    projected = preview.get('projected', {})
    diff = preview.get('diff', {})

    preview_json = html_module.escape(json.dumps(preview_response))

    fields = [
        ('forecast',      'Forecast'),
        ('fte_required',  'FTE Required'),
        ('fte_available', 'FTE Available'),
        ('capacity',      'Capacity'),
        ('gap',           'Gap'),
    ]

    rows_html = ""
    for field_key, field_label in fields:
        cur_val = current.get(field_key, 0)
        proj_val = projected.get(field_key, 0)
        diff_val = diff.get(field_key, proj_val - cur_val if isinstance(proj_val, (int, float)) and isinstance(cur_val, (int, float)) else 0)

        if isinstance(diff_val, (int, float)):
            if diff_val > 0:
                diff_class = "text-success"
                diff_fmt = f"+{diff_val:,.1f}" if isinstance(diff_val, float) else f"+{int(diff_val):,}"
            elif diff_val < 0:
                diff_class = "text-danger"
                diff_fmt = f"{diff_val:,.1f}" if isinstance(diff_val, float) else f"{int(diff_val):,}"
            else:
                diff_class = "text-muted"
                diff_fmt = "0"
        else:
            diff_class = "text-muted"
            diff_fmt = str(diff_val)

        cur_fmt = f"{cur_val:,.1f}" if isinstance(cur_val, float) else (f"{int(cur_val):,}" if isinstance(cur_val, (int, float)) else str(cur_val))
        proj_fmt = f"{proj_val:,.1f}" if isinstance(proj_val, float) else (f"{int(proj_val):,}" if isinstance(proj_val, (int, float)) else str(proj_val))

        rows_html += f'''
            <tr>
                <td>{html_module.escape(field_label)}</td>
                <td class="text-end">{cur_fmt}</td>
                <td class="text-end">{proj_fmt}</td>
                <td class="text-end {diff_class}"><strong>{diff_fmt}</strong></td>
            </tr>
        '''

    logger.info("[UI Tools] Generated ramp preview UI")
    return f'''
    <div class="ramp-preview-card card border-primary">
        <div class="card-header bg-primary text-white">
            <strong>Ramp Impact Preview</strong>
        </div>
        <div class="card-body">
            <p class="text-muted mb-3"><small>Review the projected changes before applying.</small></p>
            <div class="table-responsive">
                <table class="table table-sm table-bordered ramp-preview-table mb-3">
                    <thead class="table-light">
                        <tr>
                            <th>Field</th>
                            <th class="text-end">Current</th>
                            <th class="text-end">Projected</th>
                            <th class="text-end">Change</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
            <div class="d-flex gap-2">
                <button class="btn btn-primary ramp-apply-btn"
                        data-ramp-preview="{preview_json}">
                    Confirm Apply
                </button>
                <button class="btn btn-outline-secondary ramp-cancel-btn">
                    Cancel
                </button>
            </div>
        </div>
    </div>
    '''


def generate_ramp_result_ui(success: bool, message: str) -> str:
    """
    Generate a result card after a ramp apply attempt.

    Args:
        success: Whether the apply succeeded
        message: Result message to display

    Returns:
        HTML string for ramp result card (green on success, red on failure)
    """
    safe_message = html_module.escape(str(message))

    if success:
        logger.info("[UI Tools] Generated ramp apply success UI")
        return f'''
        <div class="ramp-result-card card border-success">
            <div class="card-body d-flex align-items-start gap-2">
                <div style="font-size:24px;color:#28a745;">&#10003;</div>
                <div>
                    <strong class="text-success">Ramp Applied Successfully</strong>
                    <p class="mb-0 mt-1">{safe_message}</p>
                </div>
            </div>
        </div>
        '''
    else:
        logger.info("[UI Tools] Generated ramp apply failure UI")
        return f'''
        <div class="ramp-result-card card border-danger">
            <div class="card-body d-flex align-items-start gap-2">
                <div style="font-size:24px;color:#dc3545;">&#10007;</div>
                <div>
                    <strong class="text-danger">Ramp Apply Failed</strong>
                    <p class="mb-0 mt-1">{safe_message}</p>
                </div>
            </div>
        </div>
        '''


def generate_applied_ramp_ui(
    applied_ramp_data: dict,
    row_label: str,
    month_label: str,
) -> str:
    """
    Generate a card showing the currently applied ramp for a row/month.

    Args:
        applied_ramp_data: Response dict from get_applied_ramp API call
        row_label: Human-readable row identifier
        month_label: Human-readable month label

    Returns:
        HTML string for applied ramp display card
    """
    safe_row = html_module.escape(str(row_label))
    safe_month = html_module.escape(str(month_label))

    weeks = applied_ramp_data.get('weeks', [])
    total_ramp_employees = applied_ramp_data.get('totalRampEmployees', 0)

    if not weeks:
        logger.info("[UI Tools] Generated applied ramp UI (none applied)")
        return f'''
        <div class="applied-ramp-card card border-secondary">
            <div class="card-header bg-secondary text-white">
                <strong>Applied Ramp</strong>
            </div>
            <div class="card-body">
                <p class="mb-1"><strong>Row:</strong> {safe_row}</p>
                <p class="mb-3"><strong>Month:</strong> {safe_month}</p>
                <div class="alert alert-info mb-0">
                    No ramp has been applied for this row and month.
                </div>
            </div>
        </div>
        '''

    rows_html = ""
    for w in weeks:
        label = html_module.escape(str(w.get('label', '')))
        working_days = int(w.get('workingDays', 0))
        ramp_pct = float(w.get('rampPercent', 0))
        rows_html += f'''
            <tr>
                <td>{label}</td>
                <td class="text-center">{working_days}</td>
                <td class="text-center">{ramp_pct:.1f}%</td>
            </tr>
        '''

    logger.info(f"[UI Tools] Generated applied ramp UI for {row_label} | {month_label}")
    return f'''
    <div class="applied-ramp-card card border-secondary">
        <div class="card-header bg-secondary text-white">
            <strong>Applied Ramp</strong>
        </div>
        <div class="card-body">
            <p class="mb-1"><strong>Row:</strong> {safe_row}</p>
            <p class="mb-3"><strong>Month:</strong> {safe_month}</p>
            <p class="mb-2"><strong>Total Ramp Employees:</strong> {total_ramp_employees:,}</p>
            <div class="table-responsive">
                <table class="table table-sm table-bordered mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Week</th>
                            <th class="text-center">Working Days</th>
                            <th class="text-center">Ramp %</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    '''
