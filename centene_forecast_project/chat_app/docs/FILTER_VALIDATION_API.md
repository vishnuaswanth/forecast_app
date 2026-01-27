# Filter Validation API Documentation

**Version:** 1.0
**Last Updated:** 2026-01-24
**Module:** `chat_app.services.tools.validation_tools`

---

## Overview

The Filter Validation API provides intelligent typo detection, auto-correction, and combination diagnosis for forecast queries. It uses fuzzy matching to detect misspellings and incremental API testing to identify problematic filter combinations.

### Key Features

- **Proactive Validation:** Validates filters before query execution
- **Confidence-Based Auto-Correction:** >90% confidence = auto-fix, 60-90% = confirm, <60% = reject
- **Combination Diagnosis:** Identifies which specific filter breaks a combination
- **LLM-Powered Guidance:** Natural language explanations and suggestions
- **Efficient Caching:** 5-minute TTL to minimize API calls
- **Graceful Error Handling:** Falls back to reactive diagnosis if validation fails

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│           LLM Service Layer                     │
│  (execute_forecast_query)                       │
└─────────────┬───────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────┐
│       FilterValidator                           │
│  - Pre-flight validation                        │
│  - Fuzzy matching (difflib)                     │
│  - Confidence thresholds                        │
└─────────────┬───────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────┐
│       FilterOptionsCache                        │
│  - 5-minute TTL                                 │
│  - In-memory storage                            │
└─────────────┬───────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────┐
│       API: /api/llm/forecast/filter-options     │
│  - Returns valid filter values                  │
└─────────────────────────────────────────────────┘
```

---

## Core Classes

### 1. FilterValidator

**Location:** `chat_app/services/tools/validation_tools.py`

**Purpose:** Validates filter values against available options using fuzzy matching.

#### Confidence Thresholds

```python
HIGH_CONFIDENCE = 0.90   # >90% - Auto-correct silently
MEDIUM_CONFIDENCE = 0.60 # 60-90% - Ask user confirmation
# <60% - Reject and show suggestions
```

#### Methods

##### `async get_filter_options(month: int, year: int, force_refresh: bool = False) -> Optional[dict]`

Fetches valid filter values from the API with caching.

**Parameters:**
- `month` (int): Report month (1-12)
- `year` (int): Report year
- `force_refresh` (bool): Skip cache and fetch fresh data

**Returns:**
- Dictionary with filter options or None if API fails

**Example:**
```python
validator = FilterValidator()
options = await validator.get_filter_options(3, 2025)
print(options['platforms'])  # ['Amisys', 'Facets', 'Xcelys']
```

---

##### `fuzzy_match(user_value: str, valid_options: List[str]) -> ValidationResult`

Performs fuzzy matching on a single filter value.

**Algorithm:**
1. Try exact match (case-insensitive) → 1.0 confidence
2. Use `difflib.get_close_matches(cutoff=0.6, n=3)` → Top 3 matches
3. Calculate precise confidence with `SequenceMatcher.ratio()`
4. Apply confidence thresholds

**Parameters:**
- `user_value` (str): User-provided filter value (e.g., "Amysis")
- `valid_options` (List[str]): Valid values from API (e.g., ["Amisys", "Facets", "Xcelys"])

**Returns:**
- `ValidationResult` dataclass with:
  - `is_valid` (bool): Whether value passes validation
  - `field_name` (str): Filter field name
  - `original_value` (str): User's input
  - `corrected_value` (Optional[str]): Suggested correction
  - `confidence` (float): Similarity score (0.0-1.0)
  - `confidence_level` (ConfidenceLevel): HIGH, MEDIUM, or LOW
  - `suggestions` (List[str]): Alternative values

**Example:**
```python
validator = FilterValidator()
result = validator.fuzzy_match("Amysis", ["Amisys", "Facets", "Xcelys"])

print(result.confidence)        # 0.95
print(result.confidence_level)  # ConfidenceLevel.HIGH
print(result.corrected_value)   # "Amisys"
```

---

##### `normalize_state_value(user_value: str) -> str`

Normalizes state names to 2-letter codes.

**Mapping:**
- "California" → "CA"
- "texas" → "TX" (case-insensitive)
- "FL" → "FL" (already a code)

**Example:**
```python
validator = FilterValidator()
normalized = validator.normalize_state_value("California")
print(normalized)  # "CA"
```

---

##### `async validate_all(params: ForecastQueryParams) -> Dict[str, List[ValidationResult]]`

Validates all filter parameters in a query.

**Parameters:**
- `params` (ForecastQueryParams): Query parameters to validate

**Returns:**
- Dictionary mapping filter names to validation results:
  ```python
  {
      'platforms': [ValidationResult(...)],
      'markets': [ValidationResult(...)],
      'states': [ValidationResult(...)]
  }
  ```

**Example:**
```python
from chat_app.services.tools.validation import ForecastQueryParams

params = ForecastQueryParams(
    month=3,
    year=2025,
    platforms=['Amysis'],  # Typo
    markets=['Medicaid'],
    states=['California']  # Will normalize to CA
)

validator = FilterValidator()
results = await validator.validate_all(params)

# Check platforms
platform_result = results['platforms'][0]
if platform_result.confidence >= FilterValidator.HIGH_CONFIDENCE:
    print(f"Auto-correcting: {platform_result.original_value} → {platform_result.corrected_value}")
```

---

### 2. CombinationDiagnostic

**Location:** `chat_app/services/tools/validation_tools.py`

**Purpose:** Diagnoses why a filter combination returns 0 records through incremental API testing.

#### Methods

##### `async diagnose(params: ForecastQueryParams, api_response: dict) -> CombinationDiagnosticResult`

Diagnoses why a query returned 0 records.

**Strategy:**
1. Check if data exists for month/year (call `/filter-options`)
2. Check if ANY records exist (query with no filters)
3. Remove filters one-by-one to identify problematic filter
4. Fetch valid options for working combinations

**Parameters:**
- `params` (ForecastQueryParams): Original query parameters
- `api_response` (dict): API response with 0 records

**Returns:**
- `CombinationDiagnosticResult` dataclass with:
  - `is_data_issue` (bool): True if no data exists for month/year
  - `is_combination_issue` (bool): True if filters don't combine
  - `problematic_filters` (List[str]): Which filters break the combination
  - `working_combinations` (Dict[str, List[str]]): Valid values for each filter
  - `total_records_available` (int): Total records for month/year
  - `diagnosis_message` (str): Human-readable explanation

**Example:**
```python
params = ForecastQueryParams(
    month=3,
    year=2025,
    platforms=['Amisys'],
    markets=['Medicaid'],
    states=['ZZ']  # Invalid state
)

diagnostic = CombinationDiagnostic()
result = await diagnostic.diagnose(params, {'records': [], 'total_records': 0})

print(result.problematic_filters)  # ['state']
print(result.working_combinations)  # {'state': ['CA', 'TX', 'FL', ...]}
print(result.diagnosis_message)
# "Found 1250 records for March 2025, but your filter combination returned 0 results.
#  Problematic filter(s): state
#  Available state values with your other filters: CA, TX, FL, NY, GA..."
```

---

### 3. FilterOptionsCache

**Location:** `chat_app/utils/filter_cache.py`

**Purpose:** In-memory cache for filter options with 5-minute TTL.

#### Methods

##### `get(month: int, year: int) -> Optional[dict]`

Retrieves cached filter options if not expired.

**Example:**
```python
from chat_app.utils.filter_cache import get_filter_cache

cache = get_filter_cache()
options = cache.get(3, 2025)  # Returns cached data or None
```

##### `set(month: int, year: int, filter_options: dict)`

Caches filter options with current timestamp.

##### `invalidate(month: int, year: int)`

Invalidates cache for specific month/year.

##### `clear_all()`

Clears entire cache (called after file uploads).

**Example:**
```python
# After forecast file upload
cache = get_filter_cache()
cache.clear_all()
logger.info("Cleared filter options cache")
```

---

## Integration with LLM Service

### Validation Flow

```python
# In llm_service.py execute_forecast_query()

# 1. Pre-flight validation
validator = FilterValidator()
validation_results = await validator.validate_all(params)

# 2. Process results
validation_summary = FilterValidationSummary()

for field_name, results in validation_results.items():
    for result in results:
        if result.confidence_level == ConfidenceLevel.HIGH:
            # Auto-correct (>90% confidence)
            validation_summary.auto_corrected.setdefault(field_name, []).append(
                result.corrected_value
            )
            # Apply correction to params
            params.platforms[0] = result.corrected_value

        elif result.confidence_level == ConfidenceLevel.MEDIUM:
            # Needs confirmation (60-90% confidence)
            validation_summary.needs_confirmation.setdefault(field_name, []).append(
                (result.original_value, result.corrected_value, result.confidence)
            )

        elif not result.is_valid:
            # Rejected (<60% confidence)
            validation_summary.rejected.setdefault(field_name, []).append(
                (result.original_value, result.suggestions)
            )

# 3. Return confirmation UI if issues
if validation_summary.has_issues():
    return {
        'success': False,
        'message': 'Filter validation requires user input',
        'ui_component': generate_validation_confirmation_ui(validation_summary, params)
    }

# 4. Execute query with corrected params
data = await fetch_forecast_data(params, enable_validation=False)

# 5. If 0 records, diagnose combination
if len(data.get('records', [])) == 0:
    diagnostic = CombinationDiagnostic()
    diagnosis = await diagnostic.diagnose(params, data)
    ui_html = await self._generate_diagnostic_guidance(params, diagnosis)
```

---

## UI Components

### 1. Validation Confirmation UI

**Function:** `generate_validation_confirmation_ui(validation_summary, params)`
**Location:** `chat_app/services/tools/ui_tools.py`

**Displays:**
- Auto-corrected filters (informational)
- Filters needing confirmation (with confidence %)
- Rejected filters with suggestions
- Action buttons: "Accept Corrections" and "Cancel"

**Example Output:**
```html
┌─────────────────────────────────────────────────┐
│ ⚠ Filter Validation                            │
├─────────────────────────────────────────────────┤
│                                                 │
│ Auto-corrected:                                 │
│  • platforms: Amisys                            │
│                                                 │
│ Please confirm these corrections:              │
│  • markets: Did you mean "Medicaid" instead of │
│    "Medcaid"? [75% match]                      │
│                                                 │
│ Invalid values:                                 │
│  • states: "ZZ" is not valid.                  │
│    Try: CA, TX, FL                             │
│                                                 │
│ ─────────────────────────────────────────────── │
│                                                 │
│ Your Query: March 2025                         │
│ Platforms: Amysis | Markets: Medcaid           │
│                                                 │
│ [✓ Accept Corrections & Continue]              │
│ [✗ Cancel & Revise Query]                      │
└─────────────────────────────────────────────────┘
```

---

### 2. Combination Diagnostic UI

**Function:** `generate_combination_diagnostic_ui(diagnosis_message, working_combinations, total_records)`
**Location:** `chat_app/services/tools/ui_tools.py`

**Displays:**
- LLM-generated diagnosis explanation
- Available filter combinations that would work
- Statistics (total records available)

**Example Output:**
```html
┌─────────────────────────────────────────────────┐
│ 🔍 No Records Found - Diagnosis                │
├─────────────────────────────────────────────────┤
│                                                 │
│ Found 1,250 records for March 2025, but your   │
│ filter combination returned 0 results. The     │
│ issue is with your "state" filter.             │
│                                                 │
│ ─────────────────────────────────────────────── │
│                                                 │
│ Available Options:                             │
│  • States: CA, TX, FL, GA, NY (and 15 more)   │
│                                                 │
│ ─────────────────────────────────────────────── │
│                                                 │
│ Total records available: 1,250                 │
│ Suggestion: Try removing the state filter or   │
│ selecting a different state from the list.     │
└─────────────────────────────────────────────────┘
```

---

## Error Handling

### Graceful Degradation

| Scenario | Fallback Mechanism |
|----------|-------------------|
| Filter options API 404 | Show "no data uploaded" message |
| Filter options API 500 | Skip validation, proceed with query |
| Validation timeout | Skip validation, use reactive diagnosis |
| Diagnosis API failure | Use existing `_generate_no_data_guidance()` |
| Cache corruption | Clear cache, refetch from API |

### Example

```python
# Pre-flight validation with fallback
try:
    validation_results = await validator.validate_all(params)
except Exception as e:
    logger.warning(f"Validation failed: {e} - proceeding without validation")
    validation_results = {}
    # Query will still execute
    # If 0 records, combination diagnosis will catch it
```

---

## Cache Management

### Cache Invalidation

**Trigger:** After forecast file upload

**Implementation:**
```python
# In centene_forecast_app/views/views.py upload_view()

elif file_type == 'forecast' or file_type == 'altered_forecast':
    # Clear all forecast-related caches
    clear_all_caches()

    # NEW: Clear filter options cache
    from chat_app.utils.filter_cache import get_filter_cache
    filter_cache = get_filter_cache()
    filter_cache.clear_all()
    logger.info("Cleared filter options cache")
```

### Cache Statistics

```python
from chat_app.utils.filter_cache import get_filter_cache

cache = get_filter_cache()
stats = cache.get_stats()
print(stats)
# {
#     'entry_count': 5,
#     'ttl_seconds': 300,
#     'entries': ['filter_options:2025:3', 'filter_options:2025:4', ...]
# }
```

---

## Testing

### Running Tests

```bash
cd centene_forecast_project
pytest chat_app/tests/test_filter_validation.py -v -s
```

### Test Coverage

1. **Fuzzy Matching Tests**
   - Exact match (100% confidence)
   - High-confidence typo (>90%)
   - Medium-confidence typo (60-90%)
   - Low-confidence rejection (<60%)
   - State normalization

2. **Filter Validation Tests**
   - validate_all() with multiple typos
   - Invalid filter rejection
   - Auto-correction flow
   - Confirmation required flow

3. **Combination Diagnosis Tests**
   - No data uploaded scenario
   - Filter combination issue
   - Incremental filter isolation

### Example Test

```python
@pytest.mark.asyncio
async def test_high_confidence_typo():
    validator = FilterValidator()
    result = validator.fuzzy_match("Amysis", ["Amisys", "Facets", "Xcelys"])

    assert result.confidence >= 0.90
    assert result.confidence_level == ConfidenceLevel.HIGH
    assert result.corrected_value == "Amisys"
    print(f"✅ High confidence match: 'Amysis' → 'Amisys' ({result.confidence:.2%})")
```

---

## Performance Considerations

### API Call Optimization

**Maximum API Calls for Combination Diagnosis:** `1 + N` (N = number of filters)

**Example:**
- Filter options: 1 call (cached 5 min)
- Base query: 1 call
- Test 3 filters: 3 calls max
- **Total:** 5 calls (first call cached)

**Early Termination:**
```python
# Stop as soon as problematic filter is found
if records_without_filter_A > 0:
    problematic = ['filter_A']
    break  # No need to test B and C
```

### Caching Efficiency

- **First query:** ~150-600ms (uncached)
- **Subsequent queries:** <10ms (cached)
- **Cache TTL:** 5 minutes
- **Cache invalidation:** After file uploads only

---

## Changelog

### Version 1.0 (2026-01-24)

**Added:**
- FilterValidator class with fuzzy matching
- CombinationDiagnostic class with incremental isolation
- FilterOptionsCache with 5-minute TTL
- Pre-flight validation in forecast_tools.py
- Integration with llm_service.py
- Validation confirmation UI
- Combination diagnostic UI
- State normalization (California → CA)
- Auto-correction for high-confidence typos
- User confirmation for medium-confidence matches
- Graceful error handling with fallbacks

---

## Support

For questions or issues:
- **Internal Documentation:** `/Users/aswanthvishnu/Projects/Centene_Forecasting/CLAUDE.md`
- **API Spec:** `centene_forecast_project/api_specs/LLM_FORECAST_API_SPEC.md`
- **Tests:** `chat_app/tests/test_filter_validation.py`

---

## License

Internal use only - NTT Data Centene Forecasting Project
