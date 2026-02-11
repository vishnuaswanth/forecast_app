# Preview Table Data Structure Reference

This document describes the structure of the preview table used in the Edit View feature for Bench Allocation and Target CPH previews.

---

## Table Overview

The preview table displays forecast data with a **two-row header system** that combines:
- **Fixed columns** (leftmost) - Row identifiers that span both header rows
- **Dynamic month columns** - 6 months of forecast data, each with 4 sub-columns

**Total columns**: 4 fixed + (6 months × 4 sub-columns) = **28 columns**

---

## Header Construction

### Visual Structure

```
┌────────────┬────────────┬────────────┬────────────┬─────────────────────────────────┬─────────────────────────────────┬─────┐
│  Main LOB  │   State    │ Case Type  │ Target CPH │            Jun-25               │            Jul-25               │ ... │
│ (rowspan=2)│ (rowspan=2)│ (rowspan=2)│ (rowspan=2)│          (colspan=4)            │          (colspan=4)            │     │
├────────────┼────────────┼────────────┼────────────┼────────┬─────────┬─────────┬────┼────────┬─────────┬─────────┬────┼─────┤
│            │            │            │            │   CF   │ FTE Req │FTE Avail│Cap │   CF   │ FTE Req │FTE Avail│Cap │ ... │
└────────────┴────────────┴────────────┴────────────┴────────┴─────────┴─────────┴────┴────────┴─────────┴─────────┴────┴─────┘
```

### Row 1: Main Headers

| Column Type | Attribute | Value | Description |
|-------------|-----------|-------|-------------|
| Fixed columns | `rowspan` | 2 | Spans both header rows vertically |
| Month headers | `colspan` | 4 | Spans all sub-columns for that month |

### Row 2: Sub-Headers

Contains only the month sub-column labels, repeated for each month:
- **CF** (Case Forecast)
- **FTE Req** (FTE Required)
- **FTE Avail** (FTE Available)
- **Cap** (Capacity)

---

## Column Definitions

### Fixed Columns (4 columns)

These columns identify each forecast record and remain fixed on the left side of the table.

| # | Key | Label | Data Type | Editable | Alignment | Description |
|---|-----|-------|-----------|----------|-----------|-------------|
| 1 | `main_lob` | Main LOB | String | No | Left | Line of Business identifier |
| 2 | `state` | State | String | No | Left | State code (2-letter) |
| 3 | `case_type` | Case Type | String | No | Left | Type of case being processed |
| 4 | `target_cph` | Target CPH | Integer | Yes | Center | Target cases per hour |

**Example Values:**
```json
{
    "main_lob": "Medicaid",
    "state": "MO",
    "case_type": "Appeals",
    "target_cph": 100
}
```

### Month Columns (4 sub-columns per month)

These columns repeat for each of the 6 forecast months.

| # | Key | Label | Data Type | Editable | Alignment | Description |
|---|-----|-------|-----------|----------|-----------|-------------|
| 1 | `forecast` | CF | Integer | No | Right | Case Forecast - predicted case volume |
| 2 | `fte_req` | FTE Req | Integer | Yes | Right | FTE Required - staff needed |
| 3 | `fte_avail` | FTE Avail | Integer | Yes | Right | FTE Available - staff available |
| 4 | `capacity` | Cap | Integer | Yes | Right | Capacity - processing capacity |

**Example Values:**
```json
{
    "Jun-25": {
        "forecast": 12500,
        "fte_req": 11,
        "fte_avail": 8,
        "capacity": 400
    }
}
```

---

## Month Labels

Month labels are dynamically provided by the API in the format `Mon-YY`:

| Index | Key | Example Label |
|-------|-----|---------------|
| 1 | `month1` | Jun-25 |
| 2 | `month2` | Jul-25 |
| 3 | `month3` | Aug-25 |
| 4 | `month4` | Sep-25 |
| 5 | `month5` | Oct-25 |
| 6 | `month6` | Nov-25 |

The months mapping is provided at the top level of the API response:
```json
{
    "months": {
        "month1": "Jun-25",
        "month2": "Jul-25",
        "month3": "Aug-25",
        "month4": "Sep-25",
        "month5": "Oct-25",
        "month6": "Nov-25"
    }
}
```

---

## Complete Record Structure

Each record in `modified_records` follows this structure:

```json
{
    "main_lob": "Medicaid",
    "state": "MO",
    "case_type": "Appeals",
    "target_cph": 100,
    "target_cph_change": 5,
    "modified_fields": ["target_cph", "Jun-25.forecast", "Jun-25.fte_req"],
    "months": {
        "Jun-25": {
            "forecast": 12500,
            "fte_req": 11,
            "fte_avail": 8,
            "capacity": 400,
            "forecast_change": 0,
            "fte_req_change": 2,
            "fte_avail_change": 1,
            "capacity_change": 50
        },
        "Jul-25": {
            "forecast": 13000,
            "fte_req": 12,
            "fte_avail": 9,
            "capacity": 450,
            "forecast_change": 0,
            "fte_req_change": 1,
            "fte_avail_change": 0,
            "capacity_change": 25
        }
    }
}
```

---

## Field Mapping Reference

### JavaScript to API Field Mapping

The frontend uses camelCase keys that map to snake_case API fields:

| JS Key (config) | API Field | Description |
|-----------------|-----------|-------------|
| `forecast` | `forecast` | Case forecast (same) |
| `fteReq` | `fte_req` | FTE required |
| `fteAvail` | `fte_avail` | FTE available |
| `capacity` | `capacity` | Capacity (same) |

### Change Fields

For editable fields, the API provides corresponding `_change` fields:

| Value Field | Change Field | Description |
|-------------|--------------|-------------|
| `target_cph` | `target_cph_change` | Change in target CPH |
| `fte_req` | `fte_req_change` | Change in FTE required |
| `fte_avail` | `fte_avail_change` | Change in FTE available |
| `capacity` | `capacity_change` | Change in capacity |
| `forecast` | `forecast_change` | Change in forecast (always 0 for bench allocation) |

---

## Modified Fields Tracking

The `modified_fields` array tracks which fields have been changed:

- **Fixed column changes**: `"target_cph"`
- **Month column changes**: `"{month}.{field}"` format
  - Example: `"Jun-25.fte_req"`, `"Jul-25.capacity"`

```json
"modified_fields": [
    "target_cph",
    "Jun-25.forecast",
    "Jun-25.fte_req",
    "Jul-25.capacity"
]
```

---

## Summary Statistics

The API response includes summary statistics:

```json
{
    "summary": {
        "total_fte_change": 45,
        "total_capacity_change": 2250
    },
    "total_modified": 15
}
```

| Field | Description |
|-------|-------------|
| `total_fte_change` | Sum of all FTE changes across all records and months |
| `total_capacity_change` | Sum of all capacity changes across all records and months |
| `total_modified` | Count of records with modifications |

---

## Table Features

### Totals Row

When enabled, displays column totals at the bottom of the table:
- Fixed columns show "Total" label in first cell
- Month columns show sum of all values in that column
- Change values are also summed

### Pagination

- Default page size: Configurable via `PREVIEW_PAGE_SIZE`
- Navigation: Previous/Next buttons with page numbers
- Ellipsis shown for large page counts

### Change Highlighting

- Modified cells are visually highlighted
- Positive changes: Green text with `+` prefix
- Negative changes: Red text
- No change: Default styling

---

## Configuration Reference

### JavaScript Configuration Object

```javascript
{
    fixedColumns: [
        { key: 'main_lob', label: 'Main LOB', editable: false },
        { key: 'state', label: 'State', editable: false },
        { key: 'case_type', label: 'Case Type', editable: false },
        { key: 'target_cph', label: 'Target CPH', editable: true, align: 'text-center' }
    ],
    monthColumns: [
        { key: 'forecast', label: 'CF', editable: false },
        { key: 'fteReq', label: 'FTE Req', editable: true },
        { key: 'fteAvail', label: 'FTE Avail', editable: true },
        { key: 'capacity', label: 'Cap', editable: true }
    ],
    features: {
        showTotalsRow: true,
        showMonthwiseSummary: true,
        summaryStyle: 'cards',
        cascadingFilters: true
    }
}
```

---

## Related Files

| File | Purpose |
|------|---------|
| `views/edit_view.py` | API endpoints for preview |
| `services/edit_service.py` | Business logic for preview calculation |
| `serializers/edit_serializers.py` | Response formatting |
| `repository.py` | API client for backend communication |
| `static/.../js/edit_view.js` | Frontend table rendering |

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2025-02 | 1.0 | Initial documentation |
