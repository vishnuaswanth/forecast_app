"""
UI Generation Tools
Functions for generating HTML tables and UI components for forecast data.
"""
import logging
import json
from typing import List, Dict

logger = logging.getLogger(__name__)


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


def generate_error_ui(error_message: str) -> str:
    """
    Generate error alert HTML.

    Args:
        error_message: Error message to display

    Returns:
        HTML string for error alert
    """
    logger.warning(f"[UI Tools] Generated error UI: {error_message}")
    return f'<div class="alert alert-danger">Error: {error_message}</div>'


def generate_clarification_ui(clarification_message: str) -> str:
    """
    Generate clarification request HTML.

    Args:
        clarification_message: Clarification message to display

    Returns:
        HTML string for clarification alert
    """
    logger.info(f"[UI Tools] Generated clarification UI")
    return f'<div class="alert alert-info">{clarification_message}</div>'


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


def generate_combination_diagnostic_ui(
    diagnosis_message: str,
    working_combinations: Dict[str, List[str]],
    total_records: int
) -> str:
    """
    Generate UI for filter combination diagnosis.

    Shows:
    - LLM-generated diagnosis explanation
    - Available filter combinations that would work
    - Suggestions for alternative queries

    Args:
        diagnosis_message: LLM-generated diagnostic message
        working_combinations: Valid filter values for working combinations
        total_records: Total records available

    Returns:
        HTML string for diagnostic UI
    """
    html = '<div class="alert alert-warning" role="alert">'
    html += '<h6 class="alert-heading"><i class="bi bi-search"></i> No Records Found - Diagnosis</h6>'

    # Diagnosis message
    html += f'<p class="mb-2">{diagnosis_message}</p>'

    html += '<hr>'

    # Working combinations
    if working_combinations:
        html += '<div class="mt-2">'
        html += '<strong>Available Options:</strong>'
        html += '<ul class="mb-0 mt-1">'

        for filter_name, valid_values in working_combinations.items():
            display_values = ', '.join(valid_values[:10])
            if len(valid_values) > 10:
                display_values += f' (and {len(valid_values) - 10} more)'

            html += f'<li><strong>{filter_name.replace("_", " ").title()}:</strong> {display_values}</li>'

        html += '</ul></div>'

    # Statistics
    html += '<div class="mt-3">'
    html += '<small class="text-muted">'
    html += f'<strong>Total records available:</strong> {total_records:,}<br>'
    html += '<strong>Suggestion:</strong> Try removing one of the problematic filters or selecting a different value from the available options above.'
    html += '</small>'
    html += '</div>'

    html += '</div>'

    logger.info("[UI Tools] Generated combination diagnostic UI")
    return html
