# Centene Forecasting – PowerBI Documentation

## What this system does

This is a **workforce capacity planning system**. It answers the question:
> *Do we have enough case handlers (FTEs) to process the volume of claims/cases our clients forecast each month?*

Key metrics tracked per forecast row:
- **Client Forecast** – How many cases the client expects per month
- **FTE Required** – How many agents are needed to handle that volume (calculated)
- **FTE Available** – How many agents are actually assigned (from roster)
- **Capacity** – How many cases the available agents can actually process (calculated)
- **Gap** = Capacity − Forecast (negative = shortage, positive = surplus)

---

## Database

- **Dev**: SQLite (`db.sqlite3` in the FastAPI project root)
- **Prod**: Microsoft SQL Server (MSSQL)

All business data is stored in the **FastAPI backend** (`manager_view_fastapi/`).
The Django frontend has only two tables: `core_user` and `core_uploadedfile`.

---

## Documents in this folder

| File | Description |
|------|-------------|
| `schema.mmd` | Entity-relationship diagram of all tables |
| `capacity_calculation.mmd` | How FTE Required and Capacity are calculated step by step |
| `tables_reference.md` | Every table with all columns, types, and what each field means |

---

## Quick summary of tables

| Table | Purpose |
|-------|---------|
| `forecastmodel` | **Main data table.** One row = one LOB/State/CaseType combination per upload month. Stores forecast volumes and calculated FTE/Capacity for 6 future months. |
| `target_cph_configuration` | Cases Per Hour target for each LOB + CaseType. Drives FTE and Capacity calculations. |
| `monthconfigurationmodel` | Working days, work hours, and shrinkage rate per month/year/worktype. Also drives calculations. |
| `rostermodel` | Employee list (old format). Used during allocation to count available FTEs. |
| `rostertemplate` | Employee list (new standard format). Primary source for FTE availability. |
| `prodteamrostermodel` | Production team employees only. Subset of roster for production allocation. |
| `skillingmodel` | Employee skills matrix. Used to match employees to LOBs they are certified for. |
| `allocationexecutionmodel` | Tracks every allocation run (who ran it, when, status, source files). |
| `allocationreportsmodel` | Stores the three output reports for each allocation run (as JSON). |
| `fte_allocation_mapping` | Which employee (CN#) was allocated to which forecast row for which month. |
| `history_log` | High-level change log (CPH updates, bench allocation runs, etc.). |
| `history_change` | Field-level detail of every change (old value, new value, delta). |
| `ramp_model` | Week-by-week ramp-up schedule for a forecast row. Adjusts capacity for new hires ramping. |
| `allocation_validity` | Tracks whether the latest allocation is still valid for a month (invalidated when data is manually edited). |
| `forecastmonthsmodel` | Stores the 6 month labels (e.g., Apr-25 through Sep-25) for a forecast upload. |
| `raw_data` | Versioned snapshots of intermediate DataFrames (bucket summaries, etc.). Used internally. |
