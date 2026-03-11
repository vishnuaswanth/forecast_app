# Tables Reference

This document describes every table, its columns, and how it connects to other tables.

---

## forecastmodel

**Purpose**: The central data table. Each row represents one unique combination of
Line of Business + State + Case Type for a specific upload month/year.
It stores 6 months of forecast data and the calculated FTE/Capacity values.

**How rows get here**: An analyst uploads a forecast CSV/Excel file. The system processes
it, calculates FTE Required and Capacity for each row, and stores all 6 months in this table.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int (PK) | Auto-increment row ID |
| `Centene_Capacity_Plan_Main_LOB` | string | Line of Business. Contains worktype embedded in name, e.g., `"Amisys Medicaid DOMESTIC"` or `"Facets Medicare GLOBAL"`. Used to determine Domestic vs Global worktype. |
| `Centene_Capacity_Plan_State` | string | State code, e.g., `"CA"`, `"TX"`, `"N/A"` (for global rows) |
| `Centene_Capacity_Plan_Case_Type` | string | Type of work, e.g., `"FTC MCARE"`, `"Marketplace"` |
| `Centene_Capacity_Plan_Call_Type_ID` | string | Business identifier for the case type within the LOB |
| `Centene_Capacity_Plan_Target_CPH` | int | Cases Per Hour target **at time of upload** (snapshot). For the live/editable CPH, see `target_cph_configuration`. |
| `Client_Forecast_Month1` | int | Client's expected case volume for the 1st forecast month |
| `Client_Forecast_Month2` | int | … 2nd forecast month |
| `Client_Forecast_Month3` | int | … 3rd forecast month |
| `Client_Forecast_Month4` | int | … 4th forecast month |
| `Client_Forecast_Month5` | int | … 5th forecast month |
| `Client_Forecast_Month6` | int | … 6th forecast month |
| `FTE_Required_Month1` | int | How many roster agents are needed to handle Month1 forecast volume (calculated: CEIL) |
| `FTE_Required_Month2` | int | … Month2 |
| `FTE_Required_Month3` | int | … Month3 |
| `FTE_Required_Month4` | int | … Month4 |
| `FTE_Required_Month5` | int | … Month5 |
| `FTE_Required_Month6` | int | … Month6 |
| `FTE_Avail_Month1` | int | Actual roster agents assigned to this row for Month1 (from allocation run) |
| `FTE_Avail_Month2` | int | … Month2 |
| `FTE_Avail_Month3` | int | … Month3 |
| `FTE_Avail_Month4` | int | … Month4 |
| `FTE_Avail_Month5` | int | … Month5 |
| `FTE_Avail_Month6` | int | … Month6 |
| `Capacity_Month1` | int | How many cases the available roster agents can handle in Month1 (calculated: FLOOR) |
| `Capacity_Month2` | int | … Month2 |
| `Capacity_Month3` | int | … Month3 |
| `Capacity_Month4` | int | … Month4 |
| `Capacity_Month5` | int | … Month5 |
| `Capacity_Month6` | int | … Month6 |
| `Month` | string | The **upload month** or report month (e.g., `"April"`). This is the month the data was uploaded for, NOT the 6 forecast months. |
| `Year` | int | The **upload year** or report year (e.g., `2025`) |
| `UploadedFile` | string | Filename of the source upload (audit trail) |
| `CreatedBy` | string | Username who uploaded |
| `CreatedDateTime` | datetime | When row was created |
| `UpdatedDateTime` | datetime | When row was last modified |
| `UpdatedBy` | string | Username who last modified |

**What Month1–Month6 refer to**: The actual month names are stored in `forecastmonthsmodel`.
For example, if Month=April and Year=2025, then Month1 might be April 2025, Month2 = May 2025, etc.

**Derived field (calculate in PowerBI)**:
```
Gap_MonthN = Capacity_MonthN - Client_Forecast_MonthN
```

---

## forecastmonthsmodel

**Purpose**: Maps Month1–Month6 column numbers to actual month names for a given upload batch.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int (PK) | Auto-increment |
| `Month1` | string | Actual name of the 1st forecast month, e.g., `"April"` |
| `Month2` | string | e.g., `"May"` |
| `Month3` | string | e.g., `"June"` |
| `Month4` | string | e.g., `"July"` |
| `Month5` | string | e.g., `"August"` |
| `Month6` | string | e.g., `"September"` |
| `UploadedFile` | string | Links to the same upload batch as `forecastmodel.UploadedFile` |
| `CreatedBy` | string | Username who uploaded |
| `CreatedDateTime` | datetime | When created |

**Join**: `forecastmonthsmodel.UploadedFile = forecastmodel.UploadedFile`

---

## target_cph_configuration

**Purpose**: Defines how many cases per hour an roster agent is expected to process for each
LOB + CaseType combination. This is the primary driver of FTE and Capacity calculations.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int (PK) | Auto-increment |
| `MainLOB` | string | Line of Business, e.g., `"Amisys Medicaid GLOBAL"` |
| `CaseType` | string | Case type, e.g., `"FTC-Basic/Non MMP"` |
| `TargetCPH` | float | Cases per hour. Typical range: 3.0 – 17.0 |
| `CreatedBy` | string | Who created this config |
| `CreatedDateTime` | datetime | When created |
| `UpdatedBy` | string | Who last updated |
| `UpdatedDateTime` | datetime | When last updated |

**Unique constraint**: One row per `(MainLOB, CaseType)` combination.

**Join to forecastmodel**:
```sql
target_cph_configuration.MainLOB = forecastmodel.Centene_Capacity_Plan_Main_LOB
AND target_cph_configuration.CaseType = forecastmodel.Centene_Capacity_Plan_Case_Type
```
Note: `forecastmodel.Centene_Capacity_Plan_Target_CPH` is a snapshot at upload time.
`target_cph_configuration.TargetCPH` is the live/editable value used in new calculations.

---

## monthconfigurationmodel

**Purpose**: Defines working parameters for each month/year and worktype.
These parameters directly feed the FTE Required and Capacity formulas.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int (PK) | Auto-increment |
| `Month` | string | Full month name, e.g., `"April"` |
| `Year` | int | e.g., `2025` |
| `WorkType` | string | Either `"Domestic"` or `"Global"` |
| `WorkingDays` | int | Number of business days in that month, e.g., `22` |
| `Occupancy` | float | Stored but **not used in formulas**. Present for reference only. |
| `Shrinkage` | float | Fraction of time roster agents are unavailable (breaks, training, etc.), e.g., `0.10` = 10% |
| `WorkHours` | float | Hours roster agents work per day, e.g., `9.0` |
| `CreatedBy` | string | Who created |
| `CreatedDateTime` | datetime | When created |
| `UpdatedBy` | string | Who last updated |
| `UpdatedDateTime` | datetime | When last updated |

**Unique constraint**: One row per `(Month, Year, WorkType)`.

**Join to forecastmodel**:
```sql
monthconfigurationmodel.Month = forecastmodel.Month
AND monthconfigurationmodel.Year = forecastmodel.Year
AND monthconfigurationmodel.WorkType = (
    CASE WHEN forecastmodel.Centene_Capacity_Plan_Main_LOB LIKE '%GLOBAL%'
    THEN 'Global' ELSE 'Domestic' END
)
```

---

## rostertemplate

**Purpose**: The standard employee roster. Each row is one employee.
This is the primary source for counting FTE availability during allocation.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int (PK) | Auto-increment |
| `FirstName` | string | Employee first name |
| `LastName` | string | Employee last name |
| `CN` | string | **Employee's unique CN number** (primary identifier across the system) |
| `OPID` | string | Operations ID |
| `Location` | string | Physical location |
| `ZIPCode` | string | ZIP code |
| `City` | string | City |
| `BeelineTitle` | string | Job title in Beeline system |
| `Status` | string | Employment status |
| `PrimaryPlatform` | string | Main platform the employee works on (e.g., `"Amisys"`, `"Facets"`) |
| `PrimaryMarket` | string | Market the employee primarily serves |
| `Worktype` | string | Type of work (Domestic/Global/etc.) |
| `LOB` | string | Line of Business assigned to |
| `SupervisorFullName` | string | Supervisor name |
| `SupervisorCNNo` | string | Supervisor's CN number |
| `UserStatus` | string | Active/Inactive/etc. |
| `PartofProduction` | string | Whether employee is part of production (`"Yes"` / `"No"`) |
| `ProductionPercentage` | string | What % of their time is production |
| `NewWorkType` | string | Updated/reclassified work type |
| `State` | string | State the employee supports |
| `CenteneMailId` | string | Centene corporate email |
| `NTTMailID` | string | NTT Data email |
| `Month` | string | Upload month |
| `Year` | int | Upload year |
| `UploadedFile` | string | Source filename |
| `CreatedBy` | string | Who uploaded |
| `CreatedDateTime` | datetime | When created |
| `UpdatedBy` | string | Who updated |
| `UpdatedDateTime` | datetime | When updated |

**Join to fte_allocation_mapping**:
```sql
rostertemplate.CN = fte_allocation_mapping.cn
```

---

## rostermodel

**Purpose**: Older-format employee roster. Contains additional training and skills fields.
Used alongside `rostertemplate` depending on upload format.

Key additional columns compared to `rostertemplate`:
| Column | Type | Description |
|--------|------|-------------|
| `Platform` | string | Platform (maps to PrimaryPlatform in new format) |
| `PrimarySkills` | string | Primary skills list |
| `SecondarySkills` | string | Secondary skills list |
| `HireDate_AmisysStartDate` | string | Hire/start date |
| `TL` | string | Team leader name |
| `Supervisor` | string | Supervisor name |
| `FTC_START_TRAINING` | string | FTC training start date |
| `FTC_END_TRAINING` | string | FTC training end date |
| `RampStartDate` | string | When ramp period begins |
| `RampEndDate` | string | When ramp period ends |
| `Ramp` | string | Ramp flag |
| `CPH` | string | Individual employee's actual CPH (not the target) |
| `ProductionStartDate` | string | When employee started in production |

---

## prodteamrostermodel

**Purpose**: A filtered subset of the roster containing only production team employees.
Same structure as `rostertemplate`. Used when allocating specifically to production buckets.

---

## skillingmodel

**Purpose**: Employee skills matrix. Used to match employees to the LOBs they are certified for.
An employee may have multiple skill rows (one per skill they hold).

| Column | Type | Description |
|--------|------|-------------|
| `id` | int (PK) | Auto-increment |
| `FirstName`, `LastName` | string | Employee name |
| `PortalId` | string | Login ID |
| `LOB_1` | string | Line of Business this skill applies to |
| `Sub_LOB` | string | Sub-level LOB |
| `Site` | string | Physical site |
| `Skills` | string | Skill description |
| `State` | string | State |
| `Skill_Name` | string | Name of the specific skill |
| `Skill_Split` | float | What fraction of time allocated to this skill (e.g., `0.5` = 50%) |
| `Month`, `Year` | string, int | Upload period |

---

## allocationexecutionmodel

**Purpose**: Tracks every time an analyst runs the allocation process. Think of it as a job log.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int (PK) | Auto-increment |
| `execution_id` | string (UUID) | Unique ID for this run. Referenced by reports and FTE mapping. |
| `Month`, `Year` | string, int | Which month/year this allocation was run for |
| `Status` | string | `PENDING`, `IN_PROGRESS`, `SUCCESS`, `FAILED`, `PARTIAL_SUCCESS` |
| `StartTime`, `EndTime` | datetime | When the run started and finished |
| `DurationSeconds` | float | How long it took |
| `ForecastFilename` | string | Which forecast file was used |
| `RosterFilename` | string | Which roster file was used |
| `RosterMonthUsed` | string | Roster month used (may differ from requested if fallback) |
| `RosterYearUsed` | int | Roster year used |
| `RosterWasFallback` | bool | `true` if the system fell back to the latest available roster |
| `UploadedBy` | string | Who triggered the run |
| `RecordsProcessed` | int | How many forecast rows were processed |
| `RecordsFailed` | int | How many rows failed |
| `AllocationSuccessRate` | float | `RecordsProcessed / (RecordsProcessed + RecordsFailed)` |
| `ErrorMessage` | string | Error detail if failed |
| `ErrorType` | string | `MISSING_MONTH_CONFIG`, `VALIDATION_ERROR`, `DATABASE_ERROR`, `UNEXPECTED_ERROR` |
| `BenchAllocationCompleted` | bool | Whether bench allocation was also done for this run |
| `BenchAllocationCompletedAt` | datetime | When bench allocation completed |
| `CreatedDateTime` | datetime | Row creation time |

---

## allocationreportsmodel

**Purpose**: Stores the output reports from each allocation run as JSON.
Each run produces up to 3 report types.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int (PK) | Auto-increment |
| `execution_id` | string (FK) | Links to `allocationexecutionmodel.execution_id` |
| `Month`, `Year` | string, int | Period this report covers |
| `ReportType` | string | One of: `bucket_summary`, `bucket_after_allocation`, `roster_allotment` |
| `ReportData` | text | The full report as a JSON string (serialized DataFrame) |
| `CreatedBy`, `UpdatedBy` | string | Audit |
| `CreatedDateTime`, `UpdatedDateTime` | datetime | Audit |

**Report types explained**:
- `bucket_summary` – Total FTE Required vs Available per LOB/CaseType bucket, before allocation
- `bucket_after_allocation` – Same buckets but shows allocation status (filled / short)
- `roster_allotment` – Which employee is assigned to which bucket

**Join**: `allocationreportsmodel.execution_id = allocationexecutionmodel.execution_id`

---

## fte_allocation_mapping

**Purpose**: The most granular allocation table. One row per employee-per-forecast-month.
Answers the question: *"For execution X, which employees were assigned to which LOB/Case Type?"*

| Column | Type | Description |
|--------|------|-------------|
| `id` | int (PK) | Auto-increment |
| `allocation_execution_id` | string (FK) | Links to `allocationexecutionmodel.execution_id` |
| `report_month`, `report_year` | string, int | The allocation run's month/year |
| `main_lob` | string | Which LOB this employee was allocated to |
| `state` | string | Which state |
| `case_type` | string | Which case type |
| `call_type_id` | string | Business ID of the case type |
| `forecast_month` | string | Full name of the forecast month (e.g., `"June"`) |
| `forecast_year` | int | Year of the forecast month |
| `forecast_month_label` | string | Short label, e.g., `"Jun-25"` |
| `forecast_month_index` | int | 1–6: which MonthN column in `forecastmodel` |
| `cn` | string | **Employee's CN number** (links to roster) |
| `first_name`, `last_name` | string | Employee name (denormalized from roster) |
| `opid` | string | Operations ID |
| `primary_platform` | string | Employee's primary platform |
| `primary_market` | string | Employee's primary market |
| `location` | string | Domestic/Global indicator for this employee |
| `original_state` | string | Employee's original state assignment |
| `worktype` | string | Employee's work type |
| `skills` | string | Comma-separated skills |
| `allocation_type` | string | `"primary"` (directly assigned) or `"bench"` (backup pool) |
| `created_datetime` | datetime | When this mapping row was created |

**Key joins**:
- To execution: `fte_allocation_mapping.allocation_execution_id = allocationexecutionmodel.execution_id`
- To roster: `fte_allocation_mapping.cn = rostertemplate.CN`
- To forecast: match on `main_lob + state + case_type + forecast_month_index`

---

## history_log

**Purpose**: High-level audit log. One row per change operation (not per field changed).
Captures WHO changed WHAT type of data, WHEN, and a summary.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int (PK) | Auto-increment |
| `history_log_id` | string (UUID) | Unique ID, referenced by `history_change` rows |
| `Month`, `Year` | string, int | Period the change applies to |
| `ChangeType` | string | Type of operation, e.g., `bench_allocation`, `cph_update`, `forecast_reallocation` |
| `Timestamp` | datetime | When the change was made |
| `User` | string | Who made the change |
| `Description` | string | Optional user notes |
| `RecordsModified` | int | How many forecast rows were affected |
| `SummaryData` | text | JSON with before/after totals aggregated by month |
| `CreatedBy` | string | System user who wrote this row |
| `CreatedDateTime` | datetime | When created |

---

## history_change

**Purpose**: Field-level change detail. One row per field that changed in a forecast row.
Links back to `history_log` for context.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int (PK) | Auto-increment |
| `history_log_id` | string (FK) | Links to `history_log.history_log_id` |
| `MainLOB` | string | Which LOB was changed |
| `State` | string | Which state |
| `CaseType` | string | Which case type |
| `CaseID` | string | Business case identifier |
| `FieldName` | string | Dot notation: `"Jun-25.fte_avail"` or `"target_cph"` |
| `OldValue` | string | Previous value (stored as string) |
| `NewValue` | string | New value (stored as string) |
| `Delta` | float | `NewValue - OldValue` (null for non-numeric fields) |
| `MonthLabel` | string | Extracted month label if field is month-specific, e.g., `"Jun-25"` |
| `CreatedDateTime` | datetime | When this row was created |

**Join**: `history_change.history_log_id = history_log.history_log_id`

---

## ramp_model

**Purpose**: Stores week-by-week ramp schedules for new hires who are not yet at full productivity.
A ramp adjusts the capacity calculation for a specific forecast row and month.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int (PK) | Auto-increment |
| `forecast_id` | int (FK) | Links to `forecastmodel.id` |
| `month_key` | string | Format `"YYYY-MM"`, e.g., `"2026-01"` — which month the ramp applies to |
| `ramp_name` | string | Groups weeks into a named ramp (default: `"Default"`). Multiple ramps can exist for the same month. |
| `week_label` | string | Human-readable week label, e.g., `"Jan-1-2026"` |
| `start_date` | string | Week start date, e.g., `"2026-01-01"` |
| `end_date` | string | Week end date, e.g., `"2026-01-04"` |
| `working_days` | int | Working days in this specific week |
| `ramp_percent` | float | How productive the ramping employees are, e.g., `50.0` = 50% |
| `employee_count` | int | How many employees are on this ramp this week |
| `applied_at` | datetime | When the ramp was applied |
| `applied_by` | string | Who applied the ramp |

**Join**: `ramp_model.forecast_id = forecastmodel.id`

**Ramp capacity formula**:
```
ramp_capacity_this_week =
    employee_count × (ramp_percent / 100)
    × TargetCPH × WorkHours × (1 − Shrinkage) × working_days
```
Sum across all weeks within a `(forecast_id, month_key)` group to get total ramp contribution.

---

## allocation_validity

**Purpose**: Tracks whether the current allocation for a month is still valid.
When an analyst manually edits forecast data (CPH, FTE counts, etc.), this gets set to invalid,
signaling that a re-run is needed.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int (PK) | Auto-increment |
| `month` | string | Month (e.g., `"April"`) |
| `year` | int | Year (e.g., `2025`) |
| `allocation_execution_id` | string | The execution ID this validity record tracks |
| `is_valid` | bool | `true` = allocation is still current; `false` = stale |
| `created_datetime` | datetime | When this validity record was created |
| `invalidated_datetime` | datetime | When it was marked invalid (null if still valid) |
| `invalidated_reason` | string | Why it was invalidated |

**Unique constraint**: One row per `(month, year)`.

---

## raw_data

**Purpose**: Internal versioned snapshots of intermediate DataFrames used during allocation.
Not intended for direct PowerBI use. Stores serialized tabular data as JSON.

| Column | Type | Description |
|--------|------|-------------|
| `id` | int (PK) | Auto-increment |
| `data_model` | string | Type of data, e.g., `"bucket_summary"` |
| `data_model_type` | string | Sub-type |
| `month`, `year` | string, int | Period |
| `version` | int | Version number (increments on each save) |
| `is_current` | bool | Whether this is the latest version |
| `dataframe_json` | text | The DataFrame serialized as JSON |
| `created_by`, `updated_by` | string | Audit |
| `created_on`, `updated_on` | datetime | Audit |

---

## Django tables (not in FastAPI)

These two tables are in the Django application database
They do **not** contain business data.

### core_user

| Column | Type | Description |
|--------|------|-------------|
| `id` | int (PK) | Auto-increment |
| `portal_id` | string | NTT Data username (used for login) |
| `email` | string | Optional email |
| Standard Django AbstractUser fields (is_staff, is_active, groups, etc.) | | |


---

## Key formula reference

```
FTE_Required = CEIL(
    Client_Forecast
    ÷ (WorkingDays × WorkHours × (1 − Shrinkage) × TargetCPH)
)

Capacity = FLOOR(
    FTE_Available × WorkingDays × WorkHours × (1 − Shrinkage) × TargetCPH
)

Gap = Capacity − Client_Forecast
(negative = shortage, positive = surplus)

Ramp_Capacity_per_week =
    employee_count × (ramp_percent / 100)
    × TargetCPH × WorkHours × (1 − Shrinkage) × working_days
```

**Note**: `Occupancy` is stored in `monthconfigurationmodel` but is **not used** in any formula.
All calculations use only `WorkingDays`, `WorkHours`, `Shrinkage`, and `TargetCPH`.
