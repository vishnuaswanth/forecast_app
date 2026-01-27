# Classification Prompt Update - Summary

**Date:** 2026-01-27
**Status:** ✅ Complete

---

## What Changed

Updated the `CLASSIFICATION_SYSTEM_PROMPT` to **simplify intent categorization** for forecast-related queries.

**Golden Rule:** ALL forecast data queries → `get_forecast_data` category

---

## Previous Approach (Too Complex)

Before, the prompt wasn't explicit enough, which could lead to confusion about whether different types of forecast queries should be categorized the same way.

**Problems:**
- Unclear if "show totals" vs "list data" vs "check available reports" should be the same category
- LLM might create sub-categories unnecessarily
- Not explicit about handling all variations

---

## New Approach (Simplified)

### ✅ Single Category for ALL Forecast Queries

**get_forecast_data** now explicitly includes:

1. **List forecast data** for month and year
   - "Show forecast for March 2025"
   - "Display data for April 2025"

2. **Filter forecast data** by any combination:
   - Platform/LOB (Amisys, Facets, Xcelys)
   - Market (Medicaid, Medicare, Marketplace)
   - Location (Domestic, Global)
   - State (CA, TX, FL, etc.)
   - Worktype/Case Type (Claims Processing, Enrollment)
   - Forecast Months (Apr-25, May-25, etc.)

3. **Check available forecast reports**
   - "What forecast data is available?"
   - "Do we have forecast for March?"

4. **Get totals** (complete or filtered)
   - "Show totals for March 2025"
   - "What are total FTEs for Amisys?"

5. **ANY variation** of forecast requests
   - "How many agents do we need?"
   - "What's the staffing requirement?"
   - "Show gaps for Texas"

---

## Updated Prompt Structure

### Primary Section (Forecast Data)

```
## PRIMARY CATEGORY - Forecast Data Queries

**get_forecast_data**: ALL queries related to forecast data, including:

   ✅ List forecast data for a month and year
   ✅ Filter forecast data by any combination
   ✅ Check available forecast reports
   ✅ Get totals (complete or filtered)
   ✅ ANY variation of forecast data requests

   **IMPORTANT**: Categorize ALL the above as `get_forecast_data`.
   The LLM will handle the specifics through tool calls and parameter extraction.
```

### Golden Rule Added

```
**Golden Rule**: When in doubt, if the query is about forecast data in ANY form
(list, filter, total, check, etc.), categorize as `get_forecast_data`.
```

---

## Updated Examples (21 Examples)

### Forecast Data Examples (18 examples) ✅

All categorized as `get_forecast_data`:

1. List forecast data
2. List with platform filter
3. Check available reports
4. Get totals (complete)
5. Get totals (filtered)
6. Filter by LOB/platform
7. Filter by market
8. Filter by location/locality
9. Filter by state
10. Filter by multiple states
11. Filter by worktype/case type
12. Filter by forecast months
13. Multiple filters combined
14. Specific LOB filter
15. Natural language staffing query ("How many agents do we need?")
16. Gaps query
17. Missing required parameters
18. Context-dependent query

### Non-Forecast Examples (3 examples) ❌

**NOT** categorized as `get_forecast_data`:

19. Reallocation request → `reallocate_forecast_data`
20. Ramp allocation → `allocate_ramp_ftes`
21. Roster query → `get_roster_data`

---

## How LLM Handles Different Requests

Once categorized as `get_forecast_data`, the LLM uses **parameter extraction** and **tool calls** to handle specifics:

### Example 1: List All Data

**User:** "Show forecast for March 2025"

**LLM Processing:**
1. Category: `get_forecast_data` ✓
2. Extract parameters: `{month: 3, year: 2025}`
3. Tool call: `fetch_forecast_data(month=3, year=2025)`
4. Response: Display all forecast data

---

### Example 2: Filter by Platform

**User:** "Show Amisys data for March 2025"

**LLM Processing:**
1. Category: `get_forecast_data` ✓
2. Extract parameters: `{month: 3, year: 2025, platforms: ["Amisys"]}`
3. Tool call: `fetch_forecast_data(month=3, year=2025, platforms=["Amisys"])`
4. Response: Display filtered data

---

### Example 3: Get Totals

**User:** "What are the total FTEs for March 2025?"

**LLM Processing:**
1. Category: `get_forecast_data` ✓
2. Extract parameters: `{month: 3, year: 2025, show_totals_only: True}`
3. Tool call: `fetch_forecast_data(month=3, year=2025, show_totals_only=True)`
4. Response: Display totals table instead of detail table

---

### Example 4: Check Available Reports

**User:** "What forecast data is available for March 2025?"

**LLM Processing:**
1. Category: `get_forecast_data` ✓
2. Extract parameters: `{month: 3, year: 2025}`
3. Tool call: `fetch_forecast_data(month=3, year=2025)`
4. Check if data exists (0 records vs data exists)
5. Response: "Yes, we have 1,250 records available for March 2025" or "No data uploaded yet"

---

### Example 5: Multiple Filters

**User:** "Show Amisys Medicaid data for CA and TX in March 2025 for Claims Processing"

**LLM Processing:**
1. Category: `get_forecast_data` ✓
2. Extract parameters:
   ```python
   {
       month: 3,
       year: 2025,
       platforms: ["Amisys"],
       markets: ["Medicaid"],
       states: ["CA", "TX"],
       case_types: ["Claims Processing"]
   }
   ```
3. Tool call: `fetch_forecast_data(...)` with all filters
4. Response: Display heavily filtered data

---

## Benefits of This Approach

### 1. **Simplicity**
- One category for all forecast queries
- No ambiguity about classification
- Clear golden rule: "If it's about forecast data, it's `get_forecast_data`"

### 2. **Flexibility**
- LLM handles nuances through parameter extraction
- Tool calls adapt to the specific request
- Can combine filters dynamically

### 3. **Consistency**
- All forecast queries follow same path
- Easier to maintain and debug
- Predictable user experience

### 4. **Extensibility**
- New filter types? Just add to parameters
- New variations? Already covered by "ANY variation"
- No prompt rewrite needed

---

## Files Updated

### 1. `chat_app/prompts/system_prompts.py`

**Changes:**
- Updated `CLASSIFICATION_SYSTEM_PROMPT` (lines 6-68)
  - Added "PRIMARY CATEGORY" section
  - Listed all forecast query variations explicitly
  - Added "Golden Rule"
  - Made it clear all variations → `get_forecast_data`

- Updated `FEW_SHOT_EXAMPLES` (lines 70-188)
  - Expanded from 15 to 21 examples
  - Added 18 forecast data examples (all → `get_forecast_data`)
  - Organized by query type (list, filter, totals, check, etc.)
  - Clear separation: ✅ Forecast vs ❌ Non-Forecast

---

## Testing the New Prompt

### Test Queries (All should → get_forecast_data)

1. ✅ "Show forecast for March 2025"
2. ✅ "List Amisys data for April 2025"
3. ✅ "What forecast is available?"
4. ✅ "Show totals for May 2025"
5. ✅ "Get Medicaid totals for June 2025"
6. ✅ "Display California forecast for March 2025"
7. ✅ "How many agents do we need for April 2025?"
8. ✅ "What are the gaps for Texas in May 2025?"
9. ✅ "Show Claims Processing data for March 2025"
10. ✅ "Get Amisys Medicaid data for CA and TX in March 2025"

### Non-Forecast Queries (Should NOT be get_forecast_data)

1. ❌ "Move 5 FTEs from Amisys to Facets" → `reallocate_forecast_data`
2. ❌ "Allocate ramp employees to Claims" → `allocate_ramp_ftes`
3. ❌ "Show me the roster" → `get_roster_data`

---

## Verification

You can verify the prompt works correctly by:

1. **Starting the chat service**
2. **Sending test queries** from above
3. **Checking logs** for classification results:
   ```
   [LLM Service] Classification: get_forecast_data (confidence: 0.92)
   ```

4. **Verifying parameters** are extracted correctly:
   ```
   [LLM Service] Extracted parameters: {month: 3, year: 2025, platforms: ['Amisys']}
   ```

---

## Next Steps

1. ✅ **Prompt updated** (Complete)
2. ✅ **Examples added** (Complete)
3. ✅ **Documentation created** (Complete)
4. 🔄 **Test in dev environment** (Next)
5. 🔄 **Monitor classification accuracy** (Next)
6. 🔄 **Adjust confidence thresholds if needed** (Next)

---

## Summary

**Before:** Unclear if different forecast query types should be same category

**After:** **Golden Rule** - ALL forecast data queries (list, filter, totals, check, etc.) → `get_forecast_data`

**Impact:**
- Simpler classification
- More predictable behavior
- Easier to maintain
- Better user experience

---

**Updated by:** Claude (Anthropic)
**Date:** 2026-01-27
**Status:** ✅ Ready for Testing
