# Ramp Bulk Edit — Implementation Prompt

## Context

This is a Django + Django Channels chat assistant (`chat_app/`). The LLM agent uses LangChain tools in `agent_tools.py`. UI HTML is generated in `ui_tools.py`. WebSocket routing is in `consumers.py`, multi-step flows are coordinated in `chat_service.py`, and the `ConversationContext` Pydantic model lives in `services/tools/validation.py` (fields: `selected_ramp_month_key`, `pending_ramp_data`, `pending_ramp_preview`, `selected_forecast_row`, etc.).

The existing single-ramp flow already works end-to-end:
`setup_ramp_calculation` tool → modal → `submit_ramp_data` WS → `confirm_ramp_submission` WS → `apply_ramp_calculation` WS.

---

## Issue 1 — Fix: Disambiguate "list/view ramps" vs "set up a new ramp"

### Root causes

1. `get_applied_ramp` in `agent_tools.py` requires `selected_ramp_month_key` already in context. When a user says "show me the ramp for January 2026", the month_key is absent, the tool returns an error, and the LLM falls back to calling `setup_ramp_calculation` instead.
2. Tool descriptions and system prompt phrases overlap — both tools respond to messages containing "ramp" and a month name.

### Required changes

#### A. `agent_tools.py` — `GetAppliedRampInput` schema and `_get_applied_ramp`

Add optional `month` and `year` parameters:

```python
class GetAppliedRampInput(BaseModel):
    month: Optional[int] = Field(default=None, description="Forecast month (1-12). Overrides context if provided.")
    year: Optional[int] = Field(default=None, description="Forecast year (e.g. 2026). Overrides context if provided.")
```

Update `_get_applied_ramp(month=None, year=None)`:
- If `month` and `year` are both provided, compute `month_key = f"{year:04d}-{month:02d}"` and store in context via `context_manager.update_entities(conversation_id, selected_ramp_month_key=month_key)`.
- If not provided, fall back to `fresh_ctx.selected_ramp_month_key`.
- If neither is available, return a validation error: `"Please specify a month and year (e.g. 'show ramp for January 2026')."`

Update `get_applied_ramp_tool` description:
```
"Retrieve and display the applied ramps for the currently selected forecast row and a specific month.
Use this to VIEW, LIST, or CHECK existing ramps — never to create or configure new ones.
Accepts optional month and year; falls back to the ramp month already in context.
Trigger phrases: 'show ramp', 'list ramps', 'what ramp is applied', 'view ramp for [month]',
'show ramp for [month] [year]', 'ramps for [month]', 'is there a ramp for [month]?'
Do NOT use this for setting up or configuring a new ramp — use setup_ramp_calculation for that."
```

Update `setup_ramp_calculation` description:
```
"Set up a NEW weekly ramp configuration for the selected forecast row and a specific month.
Use ONLY when the user explicitly wants to CREATE or CONFIGURE a ramp — phrases like:
'set up ramp', 'configure ramp', 'add ramp', 'create ramp for [month]'.
Do NOT call this when the user merely wants to view or list an existing ramp."
```

#### B. `system_prompts.py` — Ramp disambiguation section

Replace the existing ramp section with:

```
**RAMP TOOLS — DISAMBIGUATION IS CRITICAL**

VIEW an existing ramp → get_applied_ramp(month, year)
  Examples: "show ramp for January 2026", "list ramps for Jan", "what ramp is set?",
            "is there a ramp applied?", "show me the current ramp", "ramps for March"

CREATE / CONFIGURE a new ramp → setup_ramp_calculation(month, year)
  Examples: "set up ramp for January 2026", "configure ramp for Jan",
            "add a ramp for March 2026", "I want to create a ramp"

RULE: If the message contains only "ramp" + a month/year with NO explicit setup/create/configure
verb, ALWAYS default to get_applied_ramp (view intent). Only call setup_ramp_calculation when
the user clearly wants to build a new ramp.
```

---

## Issue 2 — New Feature: Multi-Ramp Bulk Edit for One Forecast Record

### Scope

One `selected_forecast_row` (one `forecast_id`) + one `month_key`. The `GET /api/v1/forecasts/{forecast_id}/months/{month_key}/ramp` API returns multiple ramp objects for that record. Each ramp has an `id` field in the database — this `id` **is** the `ramp_id` and is always present (never null, never optional). Use it as-is for all API calls and frontend tracking.

### Assumed API response shape for `get_applied_ramp`

```json
{
  "ramps": [
    {
      "id": 1,
      "ramp_name": "Ramp A",
      "weeks": [
        {"week_label": "Week 1 (Jan 1–5)", "working_days": 3, "ramp_percent": 20.0, "employee_count": 40},
        {"week_label": "Week 2 (Jan 6–12)", "working_days": 5, "ramp_percent": 50.0, "employee_count": 80}
      ]
    },
    {
      "id": 2,
      "ramp_name": "Ramp B",
      "weeks": [...]
    }
  ]
}
```

If the current API still returns `ramp_data` as a flat weeks list (single-ramp legacy format), wrap it:
`ramps = [{"id": data.get("id", 0), "ramp_name": "Ramp", "weeks": data["ramp_data"]}]`

---

### 2a. `_get_applied_ramp` — Enhanced return for multi-ramp listing

After fetching ramp data (already implemented), normalise to the multi-ramp format described above, then:

- Store the normalised ramp list in context under new field `pending_ramp_list_data`.
- Return `generate_ramp_list_ui(ramps, row_label, month_label, forecast_id, month_key)` instead of the current `generate_applied_ramp_ui`.

---

### 2b. `ConversationContext` in `services/tools/validation.py` — New field

Add alongside the existing ramp fields:

```python
pending_ramp_list_data: Optional[List[Dict[str, Any]]] = Field(
    default=None,
    description="Normalised list of ramps (with id, ramp_name, weeks) for the selected row and month. Used for bulk edit."
)
```

Also extend `clear_ramp_state()`:
```python
self.pending_ramp_list_data = None
```

---

### 2c. `ui_tools.py` — `generate_ramp_list_ui`

Add `generate_ramp_list_ui(ramps: list, row_label: str, month_label: str, forecast_id: int, month_key: str) -> str`.

**Summary card layout (shown inline in chat):**

```
┌────────────────────────────────────────────────────┐
│  Ramp Summary                    [Show Data]        │
│  Row:   Amisys Medicaid Dom | CA | Claims           │
│  Month: January 2026                               │
│────────────────────────────────────────────────────│
│  Ramp Name        Total Employees                  │
│  Ramp A           80      (peak across weeks)      │
│  Ramp B           55                               │
│────────────────────────────────────────────────────│
│  Grand Total: 135 employees across 2 ramps         │
└────────────────────────────────────────────────────┘
```

- **Total Employees per ramp** = `max(w['employee_count'] for w in ramp['weeks'])` — peak headcount.
- **Grand Total** = sum of per-ramp peaks.
- If `ramps` is empty: show `alert-info` — "No ramps configured for this row and month."
- **"Show Data" button**: `class="ramp-list-show-data-btn"`.
- On the outer wrapper `<div>`, embed:
  - `data-forecast-id="{forecast_id}"`
  - `data-month-key="{html_module.escape(month_key)}"`
  - `data-ramp-list="{ramps_json_escaped}"` (full normalised ramp list including `id` per ramp)
- All strings (row_label, month_label, ramp names) must be passed through `html_module.escape()`.

---

### 2d. Frontend: Bulk-edit modal (`#ramp-bulk-edit-modal`)

Add a new modal overlay `#ramp-bulk-edit-modal` in the chat template, similar in structure to the existing `#ramp-modal-overlay`.

#### Opening the modal

When `.ramp-list-show-data-btn` is clicked:
- Read `data-ramp-list` (parse JSON), `data-forecast-id`, `data-month-key` from the closest wrapper div.
- Save the parsed ramp list and metadata to a JS variable (`currentRampListData`) for use on submit and "Edit Again".
- Derive weeks structure from `ramps[0].weeks` (all ramps share the same week structure for a given forecast_id + month).
- Dynamically build the table and open the modal.

#### Modal table structure

The table is horizontally and vertically scrollable. All ramps (rows) have the same column count — determined once from `ramps[0].weeks.length`.

```html
<div style="overflow-x: auto; overflow-y: auto; max-height: 60vh;">
  <table class="table table-sm table-bordered ramp-bulk-edit-table">
    <thead class="table-light" style="position: sticky; top: 0; z-index: 3;">
      <tr>
        <th style="position: sticky; left: 0; z-index: 4; background: #f8f9fa;">Ramp</th>
        <!-- Repeated per week (colspan=3): -->
        <th colspan="3" class="text-center">Week 1 (Jan 1–5, 3 days)</th>
        <th colspan="3" class="text-center">Week 2 (Jan 6–12, 5 days)</th>
        ...
      </tr>
      <tr>
        <th style="position: sticky; left: 0; z-index: 4; background: #f8f9fa;"></th>
        <!-- Repeated per week: -->
        <th>Ramp %</th><th>Days</th><th>Employees</th>
        ...
      </tr>
    </thead>
    <tbody>
      <!-- One <tr> per ramp, data-ramp-id uses the ramp's `id` from the database -->
      <tr data-ramp-id="{ramp.id}">
        <td class="fw-bold" style="position: sticky; left: 0; z-index: 2; background: white;">
          {ramp_name}
        </td>
        <!-- Per week: -->
        <td>
          <input type="number" step="0.1" min="0" max="100"
                 class="form-control form-control-sm"
                 data-week-idx="0" data-field="ramp_percent"
                 value="{ramp_percent}">
        </td>
        <td class="text-center text-muted">{working_days}</td>  <!-- read-only -->
        <td>
          <input type="number" min="0"
                 class="form-control form-control-sm"
                 data-week-idx="0" data-field="employee_count"
                 value="{employee_count}">
        </td>
        ...
      </tr>
    </tbody>
  </table>
</div>
<div class="mt-3 d-flex gap-2">
  <button class="btn btn-primary ramp-bulk-submit-btn">Submit</button>
  <button class="btn btn-outline-secondary ramp-bulk-cancel-btn">Cancel</button>
</div>
```

**Details:**
- "Ramp" column (ramp name) and "Days" cells are **read-only**.
- "Ramp %" and "Employees" cells are editable `<input>` fields.
- Two-tier column headers: top row = week label + day count; sub row = `Ramp % | Days | Employees`.
- `overflow-x: auto; overflow-y: auto; max-height: 60vh` on the wrapper ensures the table scrolls both ways.
- The sticky Ramp column (`position: sticky; left: 0`) stays visible during horizontal scroll.
- Sticky header rows (`position: sticky; top: 0`) stay visible during vertical scroll.

#### On "Submit" click

JS collects all rows and sends WS message `submit_bulk_ramp_data`:

```json
{
  "type": "submit_bulk_ramp_data",
  "forecast_id": 123,
  "month_key": "2026-01",
  "ramps": [
    {
      "id": 1,
      "ramp_name": "Ramp A",
      "weeks": [
        {"week_label": "Week 1 (Jan 1–5)", "working_days": 3, "ramp_percent": 25.0, "employee_count": 45},
        ...
      ]
    },
    {
      "id": 2,
      "ramp_name": "Ramp B",
      "weeks": [...]
    }
  ]
}
```

**Important:** Store this collected payload in a JS variable (`lastBulkRampSubmission`) immediately before sending. This is used to restore the modal when "Edit Again" is clicked.

---

### 2e. "Edit Again" — Restore Edited State

When the user clicks the "Edit Again" button on the confirmation card, the modal must re-open with the **user's last edited values**, not the original API values.

**Implementation:**
- The confirmation card's "Edit Again" button carries `class="bulk-ramp-edit-btn"`.
- JS intercepts this click, reads `lastBulkRampSubmission` (the payload that was just submitted), and rebuilds the table using those values — not `currentRampListData` (original API values).
- The rebuild logic is the same table-building function, but called with `lastBulkRampSubmission.ramps` as the data source instead of `currentRampListData`.
- After rebuilding, open the modal.

This ensures the user never loses their edits when iterating.

---

### 2f. `consumers.py` — New WS handlers

Register new message types in the `receive` dispatch switch:

```python
elif message_type == 'submit_bulk_ramp_data':
    await self.handle_submit_bulk_ramp_data(data)
elif message_type == 'confirm_bulk_ramp_submission':
    await self.handle_confirm_bulk_ramp_submission(data)
elif message_type == 'apply_bulk_ramp':
    await self.handle_apply_bulk_ramp(data)
```

**`handle_submit_bulk_ramp_data(data)`:**
- Validate `data` has `forecast_id`, `month_key`, `ramps` (non-empty).
- Route to `chat_service.process_bulk_ramp_submission(data, conversation_id, user)`.
- Respond with `type: 'bulk_ramp_confirmation'`.

**`handle_confirm_bulk_ramp_submission(data)`:**
- Route to `chat_service.execute_bulk_ramp_preview(conversation_id, user)`.
- Respond with `type: 'bulk_ramp_preview'`.

**`handle_apply_bulk_ramp(data)`:**
- Route to `chat_service.execute_bulk_ramp_apply(conversation_id, user)`.
- Respond with `type: 'bulk_ramp_apply_result'`.

---

### 2g. `chat_service.py` — New service methods

#### `process_bulk_ramp_submission(self, submission: dict, conversation_id, user)`

1. Extract `forecast_id`, `month_key`, `ramps` from `submission`.
2. **Validate:**
   - `ramps` must be non-empty.
   - Each ramp must have `id` (int, mandatory — the database model's primary key) and `weeks` (non-empty).
   - Each week: `ramp_percent` in [0, 100], `working_days > 0`, `employee_count >= 0`.
   - At least one week across all ramps must have `employee_count > 0`.
3. Store validated ramps in context: `pending_ramp_list_data = ramps` (preserves `id` per ramp).
4. Store `month_key` in `selected_ramp_month_key` if not already set.
5. Build row_label from `selected_forecast_row`.
6. Return `generate_bulk_ramp_confirmation_ui(ramps, month_label, row_label)`.

#### `execute_bulk_ramp_preview(self, conversation_id, user)`

1. Load `pending_ramp_list_data`, `selected_ramp_month_key`, `selected_forecast_row` from context.
2. Compute `forecast_id` from `selected_forecast_row` (`forecast_id` or `id` field).
3. For each ramp in `pending_ramp_list_data`, call:
   ```python
   await call_preview_ramp(
       forecast_id,
       month_key,
       {
           "ramp_id": ramp['id'],   # database primary key, always present
           "weeks": ramp['weeks'],
           "totalRampEmployees": sum(w['employee_count'] for w in ramp['weeks'])
       }
   )
   ```
   Collect responses as `per_ramp_previews` list (each paired with its `ramp_id` and `ramp_name`).
4. Aggregate diffs: sum `fte_available` Δ, `capacity` Δ, `gap` Δ across all previews.
5. Store in context: `pending_ramp_preview = {"ramps": per_ramp_previews}`.
6. Return `generate_bulk_ramp_preview_ui(per_ramp_previews, aggregated_diff, month_label, row_label)`.

#### `execute_bulk_ramp_apply(self, conversation_id, user)`

1. Load `pending_ramp_preview`, `selected_ramp_month_key`, `pending_ramp_list_data`, `selected_forecast_row` from context.
2. For each ramp in `pending_ramp_list_data`, call:
   ```python
   await call_apply_ramp(
       forecast_id,
       month_key,
       {
           "ramp_id": ramp['id'],   # mandatory database id
           "weeks": ramp['weeks'],
           "totalRampEmployees": sum(w['employee_count'] for w in ramp['weeks'])
       }
   )
   ```
3. Track success/failure count per ramp.
4. If all succeed: call `fresh_ctx.clear_ramp_state()` + `await context_manager.save_context(fresh_ctx)`.
5. Return `generate_bulk_ramp_result_ui(success_count, fail_count, month_label)`.

---

### 2h. `ui_tools.py` — New UI functions

#### `generate_bulk_ramp_confirmation_ui(ramps: list, month_label: str, row_label: str) -> str`

Summary table before preview:

```
┌─────────────────────────────────────────────────────────┐
│  Confirm Bulk Ramp Submission                           │
│  Row:   Amisys Medicaid Dom | CA | Claims               │
│  Month: January 2026                                    │
│─────────────────────────────────────────────────────────│
│  Ramp Name    Weeks    Sum Employees    Peak Employees   │
│  Ramp A       4        245              80               │
│  Ramp B       4        180              55               │
│─────────────────────────────────────────────────────────│
│  [Yes, Preview Changes]   [Edit Again]                  │
└─────────────────────────────────────────────────────────┘
```

- Sum Employees = `sum(w['employee_count'] for w in ramp['weeks'])`.
- Peak Employees = `max(w['employee_count'] for w in ramp['weeks'])`.
- "Yes, Preview Changes" button: `class="bulk-ramp-preview-btn"`.
- "Edit Again" button: `class="bulk-ramp-edit-btn"` — JS uses `lastBulkRampSubmission` to restore the modal with the user's edited values (not the original API values).
- All strings through `html_module.escape()`.

#### `generate_bulk_ramp_preview_ui(per_ramp_previews: list, aggregated_diff: dict, month_label: str, row_label: str) -> str`

Per-ramp diff sections plus aggregated summary:

```
┌─────────────────────────────────────────────────────────────┐
│  Bulk Ramp Impact Preview — January 2026                    │
│  Row: Amisys Medicaid Dom | CA | Claims                     │
│─────────────────────────────────────────────────────────────│
│  Ramp A (id: 1)     Current  →  Projected   (Δ)            │
│  FTE Available      100         110           +10  [green]  │
│  Capacity           5,000       5,500         +500 [green]  │
│  Gap                -200        -150          +50  [green]  │
│─────────────────────────────────────────────────────────────│
│  Ramp B (id: 2)     Current  →  Projected   (Δ)            │
│  ...                                                        │
│─────────────────────────────────────────────────────────────│
│  Overall Change                                             │
│  FTE Available Δ: +15  |  Capacity Δ: +750  |  Gap Δ: +75 │
│─────────────────────────────────────────────────────────────│
│  [Confirm Apply]    [Cancel]                                │
└─────────────────────────────────────────────────────────────┘
```

- Each ramp section uses the preview API's `current`, `projected`, `diff` structure.
- Positive diff: green (`text-success`); negative: red (`text-danger`); zero: muted.
- Aggregated diff row sums all ramp diffs.
- "Confirm Apply" button: `class="bulk-ramp-apply-btn"`.
- "Cancel" button: `class="bulk-ramp-cancel-btn"`.

#### `generate_bulk_ramp_result_ui(success_count: int, fail_count: int, month_label: str) -> str`

- `fail_count == 0`: green success card — `"{success_count} ramp(s) applied successfully for {month_label}."`
- `success_count == 0`: red failure card.
- Mixed: yellow warning card — `"{success_count} ramp(s) applied, {fail_count} failed."`
- Follows same card pattern as existing `generate_ramp_result_ui`.

---

## Implementation Sequence

1. **`services/tools/validation.py`** — Add `pending_ramp_list_data` to `ConversationContext`; extend `clear_ramp_state()`.
2. **`agent_tools.py`** — Patch `GetAppliedRampInput`, `_get_applied_ramp`, and both tool descriptions.
3. **`ui_tools.py`** — Add `generate_ramp_list_ui`, `generate_bulk_ramp_confirmation_ui`, `generate_bulk_ramp_preview_ui`, `generate_bulk_ramp_result_ui`.
4. **`system_prompts.py`** — Rewrite ramp disambiguation section.
5. **`chat_service.py`** — Add `process_bulk_ramp_submission`, `execute_bulk_ramp_preview`, `execute_bulk_ramp_apply`.
6. **`consumers.py`** — Add three WS handlers; register in dispatch switch.
7. **Frontend JS/HTML** — Add `#ramp-bulk-edit-modal`; wire `ramp-list-show-data-btn` → modal open; wire submit → WS; store `lastBulkRampSubmission`; wire `bulk-ramp-edit-btn` → restore modal from `lastBulkRampSubmission`; handle `bulk_ramp_confirmation`, `bulk_ramp_preview`, `bulk_ramp_apply_result` response types.

---

## Constraints

- **`ramp_id` is always the database `id` field** — never null, never optional. Always read from `ramp['id']` and pass as `"ramp_id"` in API payloads. No fallback or default value logic needed.
- **"Edit Again" restores edited state** — JS must store `lastBulkRampSubmission` (the payload just sent) and use it to repopulate the modal, not the original `currentRampListData` from the API. This ensures edits are never lost.
- **Column count is fixed** — derive week structure once from `ramps[0].weeks` to build all column headers. All ramps for the same forecast_id + month have the same number of weeks.
- **XSS** — all strings from API or user data embedded in HTML must go through `html_module.escape()`.
- **Existing single-ramp flow is untouched** — do not modify `handle_submit_ramp_data`, `handle_confirm_ramp_submission`, `handle_apply_ramp_calculation`, `process_ramp_submission`, `execute_ramp_preview`, or `execute_ramp_apply`. The bulk flow is additive only.
- **`call_preview_ramp` / `call_apply_ramp`** — reuse existing async wrappers in `forecast_tools.py`. Pass `ramp_id` in the payload dict.
- **Async** — all new service methods must be `async`; API calls use `loop.run_in_executor` via existing wrappers.
- **Scrollable table** — `overflow-x: auto; overflow-y: auto; max-height: 60vh` on the wrapper div. Sticky header and sticky first column must work together using proper `z-index` layering (header+corner cell = z-index 4, header cells = 3, sticky column cells = 2).
