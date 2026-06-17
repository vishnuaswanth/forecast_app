import io
import json
import logging

import openpyxl
from openpyxl.styles import Font
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

_ACTION_LABEL = {"add": "added", "edit": "edit", "delete": "delete"}

_DB_HEADERS = [
    "Forecast ID", "Main LOB", "State", "Case Type",
    "Forecast Month", "Ramp Name",
    "Week Label", "Start Date", "End Date",
    "Working Days", "Ramp %", "Employees",
]

_UI_HEADERS = [
    "Forecast ID", "Main LOB", "State", "Case Type",
    "Forecast Month", "Ramp Name", "Actions Taken",
    "Week Label", "Start Date", "End Date",
    "Working Days", "Ramp %", "Employees",
]


@login_required
@require_http_methods(["POST"])
def download_ramp_excel(request):
    """
    Generate and return an Excel file of ramp data.

    Request body (JSON):
        mode        : "db" (clean DB data) or "ui" (staging rows with actions)
        ramps       : list of ramp dicts
        report_month: full month name, e.g. "January"
        report_year : year string, e.g. "2026"

    DB export  → 12 columns, no Actions Taken column.
    UI export  → 13 columns with "Actions Taken" (added/edit/delete/"").
                 Delete rows appear as one header-only row (no week detail).

    Filenames:
        ramp_data_db_January_2026.xlsx
        ramp_data_ui_January_2026.xlsx
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    mode      = body.get("mode", "db")
    ramps     = body.get("ramps", [])
    rep_month = body.get("report_month", "")
    rep_year  = body.get("report_year", "")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ramp Data"

    is_ui = (mode == "ui")
    headers = _UI_HEADERS if is_ui else _DB_HEADERS
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for r in ramps:
        action     = r.get("action", "")
        is_delete  = (action == "delete")
        base_db    = [
            r.get("forecast_id", ""),
            r.get("main_lob", ""),
            r.get("state", ""),
            r.get("case_type", ""),
            r.get("month_label", ""),
            r.get("ramp_name", ""),
        ]

        if is_ui:
            actions_taken = _ACTION_LABEL.get(action, "")
            base = base_db + [actions_taken]
        else:
            base = base_db

        if is_delete:
            # One summary row with no week detail (weeks is empty for delete rows)
            ws.append(base + [""] * (len(headers) - len(base)))
        else:
            for w in r.get("weeks", []):
                ws.append(base + [
                    w.get("week_label")    or w.get("label", ""),
                    w.get("start_date")    or w.get("startDate", ""),
                    w.get("end_date")      or w.get("endDate", ""),
                    w.get("working_days")  or w.get("workingDays", ""),
                    w.get("ramp_percent")  or w.get("rampPercent", ""),
                    w.get("employee_count") or w.get("rampEmployees", ""),
                ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    label    = "db" if not is_ui else "ui"
    filename = f"ramp_data_{label}_{rep_month}_{rep_year}.xlsx"

    logger.info(
        f"[Chat Views] Ramp Excel download: mode={mode}, ramps={len(ramps)}, file={filename}"
    )

    response = HttpResponse(
        buf.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
