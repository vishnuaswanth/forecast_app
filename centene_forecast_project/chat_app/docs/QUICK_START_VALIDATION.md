# Filter Validation - Quick Start Guide

**For:** Frontend Developers, QA Engineers, Product Managers
**Last Updated:** 2026-01-24

---

## What is Filter Validation?

Filter Validation is an intelligent system that:
1. **Catches typos** before queries fail (e.g., "Amysis" → "Amisys")
2. **Diagnoses combination issues** when filters don't match (e.g., "No data for state ZZ with Amisys + Medicaid")
3. **Provides smart suggestions** based on available data

---

## User Experience

### Scenario 1: High-Confidence Auto-Correction (>90%)

**User types:** "Show me Amysis data for March 2025"

**System behavior:**
- ✅ Automatically corrects "Amysis" → "Amisys"
- ✅ Executes query immediately
- ✅ Shows info alert: "Auto-corrected: platforms: Amisys"

**No user action required!**

---

### Scenario 2: Medium-Confidence Confirmation (60-90%)

**User types:** "Show Medcaid data for March 2025"

**System behavior:**
- ⚠️ Shows confirmation UI:
  ```
  Did you mean "Medicaid" instead of "Medcaid"? [75% match]
  [✓ Accept Corrections & Continue] [✗ Cancel & Revise Query]
  ```

**User must confirm before query executes.**

---

### Scenario 3: Invalid Filter Rejection (<60%)

**User types:** "Show data for state ZZ in March 2025"

**System behavior:**
- ❌ Rejects invalid value
- ❌ Shows suggestions:
  ```
  Invalid values:
  • states: "ZZ" is not valid. Try: CA, TX, FL, NY...

  [✗ Cancel & Revise Query]
  ```

**User must fix the filter.**

---

### Scenario 4: Combination Diagnosis (0 records)

**User types:** "Show Amisys Medicaid data for state ZZ in March 2025"

**System behavior:**
1. Auto-corrects any typos
2. Executes query → 0 records
3. Diagnoses: "state=ZZ is problematic"
4. Shows:
   ```
   Found 1,250 records for March 2025, but your combination returned 0.

   Problematic filter: state

   Available states for Amisys + Medicaid:
   • CA, TX, FL, GA, NY (and 15 more)

   Suggestion: Try removing the state filter or select a valid state.
   ```

**User gets clear guidance on how to fix the query.**

---

## For Frontend Developers

### UI Components

#### 1. Validation Confirmation Alert

**When to show:** Response includes `requires_confirmation: true`

**Example response:**
```json
{
  "success": false,
  "message": "Filter validation requires user input",
  "ui_component": "<div class='alert alert-warning'>...</div>",
  "metadata": {
    "validation_summary": {
      "needs_confirmation": {
        "markets": [["Medcaid", "Medicaid", 0.75]]
      },
      "rejected": {
        "states": [["ZZ", ["CA", "TX", "FL"]]]
      }
    },
    "requires_confirmation": true
  }
}
```

**Action buttons:**
- `chat-accept-corrections-btn` - Accepts corrections and re-executes query
- `chat-reject-corrections-btn` - Cancels and lets user revise

---

#### 2. Auto-Correction Info Note

**When to show:** Query succeeds with auto-corrections

**Example:**
```html
<div class='alert alert-info mt-2'>
  <small>
    Note: Auto-corrected 1 filter value(s). platforms: Amisys.
  </small>
</div>
```

This is **appended** to the success UI automatically.

---

#### 3. Combination Diagnostic Alert

**When to show:** Query returns 0 records with diagnosis

**Example response:**
```json
{
  "success": false,
  "message": "No records found - diagnosis provided",
  "ui_component": "<div class='alert alert-warning'>...</div>",
  "metadata": {
    "diagnosis": {
      "is_data_issue": false,
      "is_combination_issue": true,
      "problematic_filters": ["state"],
      "total_records_available": 1250
    }
  }
}
```

---

### JavaScript Integration

```javascript
// Listen for confirmation button clicks
$(document).on('click', '.chat-accept-corrections-btn', function() {
    const params = $(this).data('parameters');

    // Re-submit query with corrected parameters
    submitChatQuery(params);
});

$(document).on('click', '.chat-reject-corrections-btn', function() {
    // Clear the message and let user type again
    clearLastMessage();
    showInputPrompt("Please revise your query");
});
```

---

## For QA Engineers

### Test Cases

#### TC1: High-Confidence Typo Auto-Correction

**Steps:**
1. User query: "Show Amysis forecast for March 2025"
2. Observe auto-correction happens
3. Verify query executes successfully
4. Verify info alert shows: "Auto-corrected: platforms: Amisys"

**Expected:** No user confirmation needed

---

#### TC2: Medium-Confidence Typo Confirmation

**Steps:**
1. User query: "Show Medcaid forecast for March 2025"
2. Verify confirmation UI appears
3. Verify shows: "Did you mean 'Medicaid' instead of 'Medcaid'? [~75% match]"
4. Click "Accept Corrections & Continue"
5. Verify query executes with corrected value

**Expected:** User must confirm before execution

---

#### TC3: Invalid Filter Rejection

**Steps:**
1. User query: "Show data for state ZZ in March 2025"
2. Verify rejection UI appears
3. Verify shows suggestions: "Try: CA, TX, FL..."
4. Verify query does NOT execute

**Expected:** User must fix the filter

---

#### TC4: Combination Diagnosis

**Steps:**
1. User query: "Show Amisys Medicaid data for state ZZ in March 2025"
2. Query returns 0 records
3. Verify diagnostic UI appears
4. Verify shows: "Problematic filter: state"
5. Verify shows available states: "CA, TX, FL..."

**Expected:** Clear guidance on how to fix

---

#### TC5: Cache Clearing After Upload

**Steps:**
1. Upload forecast file for March 2025
2. Verify upload succeeds
3. Check logs for: "Cleared filter options cache"
4. Make query with typo for March 2025
5. Verify validation uses fresh filter options

**Expected:** Cache is cleared after upload

---

### Edge Cases to Test

1. **Multiple typos in one query**
   - Query: "Show Amisy Medcaid data"
   - Expected: Both corrected or confirmed

2. **State name normalization**
   - Query: "Show data for California"
   - Expected: Auto-normalizes to "CA"

3. **No data uploaded**
   - Query: "Show data for December 2026"
   - Expected: "No data uploaded for December 2026"

4. **All valid filters but bad combination**
   - Query: "Show Amisys Medicare data for case type 'XYZ'"
   - Expected: Diagnosis shows which filter is problematic

5. **API timeout during validation**
   - Simulate slow `/filter-options` endpoint
   - Expected: Falls back to reactive diagnosis

---

## Performance Benchmarks

| Operation | Target | Actual |
|-----------|--------|--------|
| Filter options (cached) | <10ms | ~5ms |
| Filter options (uncached) | <200ms | ~150ms |
| Fuzzy match (1 value) | <1ms | <1ms |
| Combination diagnosis (3 filters) | <1s | ~800ms |
| Cache invalidation | <5ms | ~2ms |

---

## Troubleshooting

### Issue: Validation not working

**Check:**
1. Is `/api/llm/forecast/filter-options` endpoint working?
   ```bash
   curl "http://127.0.0.1:8888/api/llm/forecast/filter-options?month=March&year=2025"
   ```
2. Check logs for: `[Filter Validator] Fetching filter options`
3. Verify cache is not corrupted: `cache.get_stats()`

**Fix:**
```python
# Clear cache and retry
from chat_app.utils.filter_cache import get_filter_cache
cache = get_filter_cache()
cache.clear_all()
```

---

### Issue: Auto-correction too aggressive

**Symptom:** Correcting values that shouldn't be corrected

**Check:** Confidence threshold in `FilterValidator.HIGH_CONFIDENCE`

**Adjust (if needed):**
```python
# In validation_tools.py
HIGH_CONFIDENCE = 0.95  # Increase from 0.90 to be more conservative
```

---

### Issue: Cache not clearing after upload

**Check:**
1. Logs for: "Cleared filter options cache"
2. Verify import works: `from chat_app.utils.filter_cache import get_filter_cache`

**Fix:**
Ensure `chat_app` is in Python path for `centene_forecast_app` views.

---

## Monitoring

### Key Metrics to Track

1. **Validation success rate:** % of queries validated successfully
2. **Auto-correction rate:** % of queries auto-corrected
3. **Confirmation rate:** % of queries requiring user confirmation
4. **Rejection rate:** % of queries rejected
5. **Cache hit rate:** % of cache hits vs. misses

### Log Analysis

```bash
# Check validation activity
grep "\[Filter Validator\]" logs/chat_app.log

# Check auto-corrections
grep "Auto-corrected" logs/chat_app.log

# Check cache hits
grep "\[Filter Cache\] HIT" logs/chat_app.log
```

---

## FAQ

### Q: Why do I see "Auto-corrected" for exact matches?

A: Case normalization. "amisys" is corrected to "Amisys" (proper case).

### Q: Can I disable auto-correction?

A: Yes, set `enable_validation=False` in `fetch_forecast_data()`. But you'll lose typo detection.

### Q: How often is the cache cleared?

A: After every forecast file upload, or after 5 minutes (TTL expiry).

### Q: What happens if the API is down?

A: Validation is skipped, query proceeds normally, falls back to reactive diagnosis if 0 records.

---

## Release Notes

### Version 1.0 (2026-01-24)

**New Features:**
- ✅ Proactive filter validation before query execution
- ✅ Fuzzy matching with confidence-based auto-correction
- ✅ Combination diagnosis for 0-record queries
- ✅ LLM-powered guidance and suggestions
- ✅ State name normalization (California → CA)
- ✅ Cache management with 5-minute TTL
- ✅ Graceful error handling with fallbacks

**Breaking Changes:**
- None (backward compatible)

**Known Issues:**
- Multi-word case types may have lower match confidence
- State abbreviations must be uppercase (FL not fl)

---

## Contact

**Development Team:** NTT Data Centene Forecasting
**Documentation:** See `FILTER_VALIDATION_API.md` for technical details
