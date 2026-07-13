"""
Ramp Campaign Service

Standalone service for the Ramp Campaign Manager page.
No imports from chat_app — uses centene_forecast_app.repository exclusively.
"""
import calendar
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from typing import List, Dict

from centene_forecast_app.repository import get_api_client

logger = logging.getLogger("django")

# Fields accepted by FastAPI's RampWeek model (extra="forbid").
# collectModalWeeks() emits both camelCase and snake_case — strip extras before sending.
_RAMP_WEEK_FIELDS = {"label", "startDate", "endDate", "workingDays", "rampPercent", "rampEmployees"}


def _clean_week(w: dict) -> dict:
    return {k: w[k] for k in _RAMP_WEEK_FIELDS if k in w}


# ------------------------------------------------------------------ #
# Local copy of week calculator (no chat_app dependency)              #
# ------------------------------------------------------------------ #

def _month_abbr(month: int) -> str:
    return calendar.month_abbr[month]


def calculate_weeks(year: int, month: int) -> List[Dict]:
    """Calculate per-week breakdowns for a calendar month (Mon–Sun, clipped to month)."""
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    days_since_monday = first_day.weekday()
    if days_since_monday == 5:
        initial_monday = first_day + timedelta(days=2)
    elif days_since_monday == 6:
        initial_monday = first_day + timedelta(days=1)
    else:
        initial_monday = first_day - timedelta(days=days_since_monday)

    weeks = []
    monday = initial_monday
    while monday <= last_day:
        sunday = monday + timedelta(days=6)
        week_start = max(monday, first_day)
        week_end = min(sunday, last_day)
        working_days = sum(
            1 for offset in range((week_end - week_start).days + 1)
            if (week_start + timedelta(days=offset)).weekday() < 5
        )
        if working_days > 0:
            label_date = week_start
            while label_date.weekday() >= 5 and label_date <= week_end:
                label_date += timedelta(days=1)
            label = f"{_month_abbr(month)}-{label_date.day}-{year}"
            weeks.append({
                "label": label,
                "startDate": week_start.isoformat(),
                "endDate": week_end.isoformat(),
                "workingDays": working_days,
            })
        monday += timedelta(days=7)
    return weeks


# ------------------------------------------------------------------ #
# Service functions                                                    #
# ------------------------------------------------------------------ #


def _find_cfg(d, key):
    """Case-insensitive lookup into WorkType config dict (e.g. 'Domestic', 'Global')."""
    for k in d:
        if k.lower() == key.lower():
            return d[k]
    return {}

def load_ramps(year: int, month_name: str) -> dict:
    """
    Load all existing ramps for a report period, enriched with CPH and per-week capacity.

    Args:
        year: Report year
        month_name: Full month name, e.g. "January"

    Returns:
        {"success": True, "ramps": [...]} or {"success": False, "message": "..."}
    """
    client = get_api_client()

    try:
        month_int = datetime.strptime(month_name, "%B").month
    except ValueError:
        return {"success": False, "message": f"Invalid month name: {month_name}"}

    # Fetch ramps
    ramps_data = client.get_ramps_for_report(year, month_name)
    if not ramps_data.get("success", True) is not False and ramps_data.get("error"):
        return {"success": False, "message": ramps_data.get("error", "Failed to fetch ramps")}

    ramps = ramps_data.get("ramps", [])

    # Fetch forecast records for CPH + configuration
    fd = client.get_forecast_records_with_cph(year, month_int)
    records      = fd.get("records", []) if not fd.get("error") else []
    cph_map      = {str(rec["id"]): float(rec.get("target_cph", 0)) for rec in records}
    locality_map = {str(rec["id"]): rec.get("locality", "Domestic") for rec in records}

    config          = fd.get("configuration", {}) if not fd.get("error") else {}
    first_month_cfg = next(iter(config.values()), {}) if config else {}
    shrinkage_cfg   = {
        "Domestic": float(_find_cfg(first_month_cfg, "Domestic").get("shrinkage",  0.10)),
        "Global":   float(_find_cfg(first_month_cfg, "Global").get("shrinkage",  0.15)),
    }
    work_hours_cfg  = {
        "Domestic": float(_find_cfg(first_month_cfg, "Domestic").get("work_hours", 9.0)),
        "Global":   float(_find_cfg(first_month_cfg, "Global").get("work_hours",  9.0)),
    }

    # Enrich ramps with locality + corrected capacity formula (includes ramp_percent)
    for r in ramps:
        fid        = str(r.get("forecast_id", ""))
        target_cph = cph_map.get(fid, 0.0)
        locality   = locality_map.get(fid, "Domestic")
        sh         = shrinkage_cfg[locality]
        wh         = work_hours_cfg[locality]
        r["target_cph"]    = target_cph
        r["locality"]      = locality
        r["work_hours"]    = wh
        r["shrinkage_pct"] = round(sh * 100, 2)
        for w in r.get("weeks", []):
            emp      = w.get("employee_count", 0) or 0
            wd       = w.get("working_days",   0) or 0
            _rp      = w.get("ramp_percent")
            ramp_pct = (_rp if _rp is not None else 100) / 100
            w["capacity"] = round(emp * ramp_pct * target_cph * wh * (1 - sh) * wd)

    logger.info(f"[RampCampaignService] Loaded {len(ramps)} ramps for {month_name} {year}")
    return {"success": True, "ramps": ramps}


def get_campaign_init_data(year: int, month_name: str) -> dict:
    """
    Return all data needed to initialise the Ramp Campaign page for a given report.

    Returns:
        {
            "success": True,
            "lobs": [{forecast_id, main_lob, state, case_type, target_cph}],
            "months": {"2025-04": "Apr-25"},
            "months_full": {"2025-04": "April 2025"},
            "month_weeks": {"2025-04": [...]},
            "report_label": "January 2025",
            "work_hours": 8.0,
            "shrinkage": 0.15,
        }
    """
    client = get_api_client()

    try:
        month_int = datetime.strptime(month_name, "%B").month
    except ValueError:
        return {"success": False, "message": f"Invalid month name: {month_name}"}

    fd = client.get_forecast_records_with_cph(year, month_int)
    if fd.get("error"):
        return {"success": False, "message": fd.get("error", "Failed to fetch forecast data")}

    records = fd.get("records", [])
    if not records:
        return {"success": False, "message": "No forecast data found for the selected report."}

    # Build months dict from the response (needed first: lobs' month_values below re-keys
    # each record's per-month forecast/capacity from label-keyed to "YYYY-MM"-keyed)
    months_raw = fd.get("months", {})
    months: dict = {}
    months_full: dict = {}
    for _key, label in months_raw.items():
        try:
            abbr, yr_short = label.split("-")
            mo = list(calendar.month_abbr).index(abbr)
            yr = 2000 + int(yr_short)
            month_key = f"{yr:04d}-{mo:02d}"
            months[month_key] = label
            months_full[month_key] = f"{calendar.month_name[mo]} {yr}"
        except Exception:
            pass

    # Build LOB list (includes locality for per-locality shrinkage/work_hours,
    # and month_values for the modal's forecast/current-capacity display).
    lobs = [
        {
            "forecast_id": rec["id"],
            "main_lob":    rec.get("main_lob", ""),
            "state":       rec.get("state", ""),
            "case_type":   rec.get("case_type", ""),
            "target_cph":  float(rec.get("target_cph", 0)),
            "locality":    rec.get("locality", "Domestic"),
            "month_values": {
                month_key: {
                    "forecast": float(rec.get("months", {}).get(label, {}).get("forecast", 0) or 0),
                    "capacity": float(rec.get("months", {}).get(label, {}).get("capacity", 0) or 0),
                }
                for month_key, label in months.items()
            },
        }
        for rec in records
    ]

    # Calculate weeks per month
    month_weeks: dict = {}
    for month_key in months:
        try:
            yr, mo = int(month_key[:4]), int(month_key[5:7])
            month_weeks[month_key] = calculate_weeks(yr, mo)
        except Exception:
            month_weeks[month_key] = []

    # Shrinkage and work_hours from configuration, per WorkType (Domestic/Global)
    # configuration: {month_label: {WorkType: {work_hours, shrinkage, ...}}}
    config          = fd.get("configuration", {})
    first_month_cfg = next(iter(config.values()), {}) if config else {}
    shrinkage_config  = {
        "Domestic": float(_find_cfg(first_month_cfg, "Domestic").get("shrinkage",  0.10)),
        "Global":   float(_find_cfg(first_month_cfg, "Global").get("shrinkage",  0.15)),
    }
    work_hours_config = {
        "Domestic": float(_find_cfg(first_month_cfg, "Domestic").get("work_hours", 9.0)),
        "Global":   float(_find_cfg(first_month_cfg, "Global").get("work_hours",  9.0)),
    }

    logger.info(
        f"[RampCampaignService] Init data: {len(lobs)} LOBs, {len(months)} months for {month_name} {year}"
    )
    return {
        "success":           True,
        "lobs":              lobs,
        "months":            months,
        "months_full":       months_full,
        "month_weeks":       month_weeks,
        "report_label":      f"{month_name} {year}",
        "shrinkage_config":  shrinkage_config,
        "work_hours_config": work_hours_config,
    }


def preview_campaign(campaign_rows: list, user=None) -> dict:
    """
    Stateless campaign preview. Calls bulk-preview for each (forecast_id, month_key)
    group in parallel via ThreadPoolExecutor.

    Args:
        campaign_rows: List of staged rows from the UI
        user: Django user (for logging only)

    Returns:
        {"success", "preview_rows", "total_fte_delta", "total_cap_delta", "message"}
    """
    client = get_api_client()

    if not campaign_rows:
        return {
            "success": False,
            "message": "No campaign rows provided.",
            "preview_rows": [],
            "total_fte_delta": 0,
            "total_cap_delta": 0,
        }

    delete_rows = [r for r in campaign_rows if r.get("action") == "delete"]
    upsert_rows = [r for r in campaign_rows if r.get("action") != "delete"]

    errors = []
    for i, row in enumerate(upsert_rows):
        if not row.get("forecast_id"):
            errors.append(f"Row {i+1}: missing forecast_id")
        if not row.get("month_key"):
            errors.append(f"Row {i+1}: missing month_key")
        if not row.get("weeks"):
            errors.append(f"Row {i+1}: missing weeks data")
    if errors:
        return {
            "success": False,
            "message": "Validation failed: " + "; ".join(errors),
            "preview_rows": [],
            "total_fte_delta": 0,
            "total_cap_delta": 0,
        }

    # Build flat preview for delete rows (use stored peak/capacity as estimated impact)
    preview_rows = []
    for row in delete_rows:
        peak_emp  = row.get("peak_employees") or 0
        total_cap = row.get("total_capacity") or 0
        preview_rows.append({
            "forecast_id": int(row.get("forecast_id", 0)),
            "main_lob":    row.get("main_lob", ""),
            "state":       row.get("state", ""),
            "case_type":   row.get("case_type", ""),
            "month_key":   row.get("month_key", ""),
            "month_label": row.get("month_label", row.get("month_key", "")),
            "ramp_name":   row.get("ramp_name", ""),
            "fte_delta":   -peak_emp,
            "cap_delta":   -total_cap,
            "action":      "delete",
            "error":       None,
        })

    # Group upsert rows by (forecast_id, month_key)
    groups: dict = defaultdict(list)
    for row in upsert_rows:
        key = (int(row["forecast_id"]), row["month_key"])
        weeks = row["weeks"]
        total = row.get("totalRampEmployees") or sum(w.get("rampEmployees", 0) for w in weeks)
        groups[key].append({
            "ramp_name": row.get("ramp_name", f"Ramp-{row['month_key']}"),
            "weeks": [_clean_week(w) for w in weeks],
            "totalRampEmployees": int(total),
        })

    group_items = list(groups.items())

    def _safe_preview(forecast_id, month_key, ramps):
        try:
            return client.bulk_preview_ramp(forecast_id, month_key, {"ramps": ramps})
        except Exception as e:
            return e

    results = [None] * len(group_items)
    with ThreadPoolExecutor(max_workers=min(8, len(group_items) or 1)) as ex:
        futures = {
            ex.submit(_safe_preview, fid, mk, ramps): idx
            for idx, ((fid, mk), ramps) in enumerate(group_items)
        }
        for future in as_completed(futures):
            results[futures[future]] = future.result()

    for idx, ((forecast_id, month_key), ramps) in enumerate(group_items):
        result = results[idx]
        for ramp in ramps:
            orig = next(
                (r for r in upsert_rows
                 if int(r["forecast_id"]) == forecast_id
                 and r["month_key"] == month_key
                 and r.get("ramp_name") == ramp["ramp_name"]),
                {},
            )
            if isinstance(result, Exception):
                preview_rows.append({
                    "forecast_id": forecast_id,
                    "main_lob": orig.get("main_lob", ""),
                    "state": orig.get("state", ""),
                    "case_type": orig.get("case_type", ""),
                    "month_key": month_key,
                    "month_label": orig.get("month_label", month_key),
                    "ramp_name": ramp["ramp_name"],
                    "fte_delta": None,
                    "cap_delta": None,
                    "action": orig.get("action", "edit"),
                    "error": str(result),
                })
            else:
                per_ramp = result.get("per_ramp_previews", []) if result else []
                ramp_preview = next(
                    (p for p in per_ramp if p.get("ramp_name") == ramp["ramp_name"]),
                    per_ramp[0] if per_ramp else {},
                )
                diff = ramp_preview.get("diff", {})
                preview_rows.append({
                    "forecast_id": forecast_id,
                    "main_lob": orig.get("main_lob", ""),
                    "state": orig.get("state", ""),
                    "case_type": orig.get("case_type", ""),
                    "month_key": month_key,
                    "month_label": orig.get("month_label", month_key),
                    "ramp_name": ramp["ramp_name"],
                    "fte_delta": diff.get("fte_available", 0),
                    "cap_delta": diff.get("capacity", 0),
                    "action": orig.get("action", "edit"),
                    "error": None,
                })

    total_fte = sum((r["fte_delta"] or 0) for r in preview_rows if r["fte_delta"] is not None)
    total_cap = sum((r["cap_delta"] or 0) for r in preview_rows if r["cap_delta"] is not None)
    error_count = sum(1 for r in preview_rows if r.get("error"))

    logger.info(
        f"[RampCampaignService] Preview: {len(preview_rows)} rows, {error_count} errors"
    )
    return {
        "success": True,
        "message": f"Preview ready: {len(preview_rows)} entries"
                   + (f" ({error_count} failed)" if error_count else ""),
        "preview_rows": preview_rows,
        "total_fte_delta": total_fte,
        "total_cap_delta": total_cap,
    }


def apply_campaign(campaign_rows: list, user=None) -> dict:
    """
    Stateless campaign apply. Groups by (forecast_id, month_key), runs deletes
    then upserts per group, all groups in parallel via ThreadPoolExecutor.

    Args:
        campaign_rows: List of staged rows (same structure as preview input)
        user: Django user (for logging only)

    Returns:
        {"success", "message", "applied": [...], "failed": [...]}
    """
    client = get_api_client()

    if not campaign_rows:
        return {
            "success": False,
            "message": "No campaign rows provided.",
            "applied": [],
            "failed": [],
        }

    delete_rows = [r for r in campaign_rows if r.get("action") == "delete"]
    upsert_rows = [r for r in campaign_rows if r.get("action") != "delete"]

    upsert_groups: dict = defaultdict(list)
    for row in upsert_rows:
        key = (int(row["forecast_id"]), row["month_key"])
        weeks = row["weeks"]
        total = row.get("totalRampEmployees") or sum(w.get("rampEmployees", 0) for w in weeks)
        upsert_groups[key].append({
            "ramp_name": row.get("ramp_name", f"Ramp-{row['month_key']}"),
            "weeks": [_clean_week(w) for w in weeks],
            "totalRampEmployees": int(total),
        })

    delete_groups: dict = defaultdict(list)
    for row in delete_rows:
        key = (int(row["forecast_id"]), row["month_key"])
        delete_groups[key].append(row.get("ramp_name", ""))

    all_keys = set(upsert_groups.keys()) | set(delete_groups.keys())

    def _apply_group(forecast_id, month_key):
        results_list = []
        for ramp_name in delete_groups.get((forecast_id, month_key), []):
            try:
                result = client.delete_ramp(forecast_id, month_key, ramp_name)
                results_list.append(("delete", ramp_name, result, None))
            except Exception as e:
                results_list.append(("delete", ramp_name, None, e))
        ramps = upsert_groups.get((forecast_id, month_key), [])
        if ramps:
            try:
                result = client.bulk_apply_ramp(forecast_id, month_key, {"ramps": ramps})
                results_list.append(("upsert", None, result, None))
            except Exception as e:
                results_list.append(("upsert", None, None, e))
        return forecast_id, month_key, results_list

    group_results = []
    with ThreadPoolExecutor(max_workers=min(8, len(all_keys) or 1)) as ex:
        futures = {ex.submit(_apply_group, fid, mk): (fid, mk) for fid, mk in all_keys}
        for future in as_completed(futures):
            group_results.append(future.result())

    applied = []
    failed = []

    for forecast_id, month_key, results_list in group_results:
        for action_type, ramp_name, result, exc in results_list:
            if action_type == "delete":
                orig = next(
                    (r for r in delete_rows
                     if int(r["forecast_id"]) == forecast_id
                     and r["month_key"] == month_key
                     and r.get("ramp_name") == ramp_name),
                    {},
                )
                entry = {
                    "forecast_id": forecast_id,
                    "main_lob": orig.get("main_lob", ""),
                    "state": orig.get("state", ""),
                    "case_type": orig.get("case_type", ""),
                    "month_key": month_key,
                    "month_label": orig.get("month_label", month_key),
                    "ramp_name": ramp_name,
                    "action": "delete",
                }
                if exc:
                    entry["error"] = str(exc)
                    failed.append(entry)
                elif result and result.get("error"):
                    entry["error"] = result["error"]
                    failed.append(entry)
                else:
                    entry["fte_removed"]      = result.get("fte_removed", 0) if result else 0
                    entry["capacity_removed"] = result.get("capacity_removed", 0) if result else 0
                    applied.append(entry)
            else:
                ramps = upsert_groups.get((forecast_id, month_key), [])
                ramps_failed_names: set = set()
                if result and not exc:
                    ramps_failed_names = set(result.get("ramps_failed", []))
                for ramp in ramps:
                    orig = next(
                        (r for r in upsert_rows
                         if int(r["forecast_id"]) == forecast_id
                         and r["month_key"] == month_key
                         and r.get("ramp_name") == ramp["ramp_name"]),
                        {},
                    )
                    entry = {
                        "forecast_id": forecast_id,
                        "main_lob": orig.get("main_lob", ""),
                        "state": orig.get("state", ""),
                        "case_type": orig.get("case_type", ""),
                        "month_key": month_key,
                        "month_label": orig.get("month_label", month_key),
                        "ramp_name": ramp["ramp_name"],
                        "action": orig.get("action", "edit"),
                    }
                    if exc:
                        entry["error"] = str(exc)
                        failed.append(entry)
                    elif ramp["ramp_name"] in ramps_failed_names:
                        entry["error"] = "Apply failed on server"
                        failed.append(entry)
                    else:
                        applied.append(entry)

    total_fte_removed = sum(e.get("fte_removed", 0) for e in applied if e.get("action") == "delete")
    total_cap_removed = sum(e.get("capacity_removed", 0) for e in applied if e.get("action") == "delete")
    logger.info(
        f"[RampCampaignService] Apply complete: {len(applied)} applied, {len(failed)} failed"
    )
    return {
        "success":           len(failed) == 0,
        "message":           f"Applied {len(applied)} ramps."
                             + (f" {len(failed)} failed." if failed else ""),
        "applied":           applied,
        "failed":            failed,
        "total_fte_removed": total_fte_removed,
        "total_cap_removed": round(total_cap_removed, 2),
    }
