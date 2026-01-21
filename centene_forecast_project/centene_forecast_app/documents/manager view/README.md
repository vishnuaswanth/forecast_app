# Manager View Dashboard

A Django-based capacity planning dashboard that displays hierarchical category data with expand/collapse functionality, KPI summary cards, and intelligent client-side caching.

## Overview

The Manager View dashboard provides managers with a comprehensive view of Client Forecast (CF), Head Count (HC), Capacity (Cap), and Capacity Gap metrics across multiple months and organizational categories. The interface features:

- **Hierarchical Data Display**: Multi-level category structure with expand/collapse navigation
- **KPI Summary Cards**: Quick overview of key metrics for the selected month
- **Searchable Filters**: Select2-powered dropdowns for report month and category selection
- **Intelligent Caching**: LRU cache with automatic cache warming for improved performance
- **Client-Side Totals**: Automatic calculation of total row from first-level categories
- **Responsive Design**: Optimized for desktop/laptop displays (1400px+ focus)

## Features

### Core Functionality

1. **Report Month Selection**
   - Searchable dropdown with Select2 integration
   - Displays data for selected month plus 5 subsequent months (configurable)
   - Mandatory selection before data loads

2. **Category Filtering**
   - Optional category filter to drill down into specific organizational units
   - "All Categories" option to view complete hierarchy
   - Searchable dropdown interface

3. **KPI Cards**
   - Client Forecast: Total client demand for the KPI month
   - Head Count: Current staffing levels
   - Capacity: Available workforce capacity
   - Capacity Gap: Difference between forecast and capacity (color-coded)

4. **Hierarchical Table**
   - Multi-level category structure (up to 4 levels supported)
   - Expand/collapse individual categories with + / - icons
   - "Expand All" and "Collapse All" buttons
   - Sticky first column for easy navigation during horizontal scroll
   - Color-coded gap values (green: positive, yellow: warning, red: danger)

5. **Mandatory Total Row**
   - Always displayed at the bottom of the table
   - Calculated client-side from first-level categories only
   - Prevents double-counting of nested category data
   - Visually distinct with blue background

### Performance Features

1. **LRU (Least Recently Used) Caching**
   - Stores API responses in browser memory
   - Maximum 50 cache entries with automatic eviction
   - Composite cache keys: "YYYY-MM|Category"
   - Tracks `lastAccessed` timestamp for intelligent eviction

2. **Cache Warming**
   - Background prefetching of all categories for a selected month
   - Fire-and-forget async pattern doesn't block UI
   - Improves subsequent filter changes

3. **Instant Cache Hits**
   - No loading spinner when serving cached data
   - Immediate UI updates for better UX

## Technical Stack

### Frontend
- **jQuery 3.6.0+**: DOM manipulation, AJAX, event delegation
- **Select2 4.1.0+**: Searchable dropdowns with Bootstrap 5 theme
- **Bootstrap 5**: UI framework (cards, tables, alerts, spinners)
- **Font Awesome**: Icon library for UI elements

### Backend
- **Django**: Template rendering, URL routing, API endpoints
- **Django Templates**: Template inheritance, static file management

### CSS Architecture
- **Namespaced CSS**: All classes prefixed with `.manager-view-*` to avoid conflicts
- **Sticky Positioning**: Fixed table headers and first column
- **Responsive Design**: Media queries for smaller desktops (1200px - 1400px)

## File Structure

```
centene_forecast_app/
├── templates/
│   └── centene_forecast_app/
│       └── manager_view.html              # Django template (203 lines)
├── static/
│   └── centene_forecast_app/
│       ├── css/
│       │   └── manager_view.css           # Namespaced styles (610 lines)
│       └── js/
│           └── manager_view.js            # Main application logic (1,165 lines)
├── views/
│   └── manager_view.py                    # Django views (manager_view, manager_view_data, manager_view_kpi)
├── serializers/
│   └── manager_view_serializers.py        # Data serialization for API responses
├── validators/
│   └── manager_view_validators.py         # Input validation logic
├── services/
│   └── manager_view_services.py           # Business logic and data processing
├── documents/
│   └── manager_view/
│       └── README.md                      # This documentation
└── urls.py                                # URL routing
```

### manager_view.html
Django template extending `index.html` with:
- Filter section (lines 25-59): Report month and category selectors
- Summary KPI cards (lines 62-107): Four metric cards (initially hidden)
- Main data table (lines 110-151): Hierarchical table structure
- Loading/error states (lines 154-171): Spinner and error messages
- Script configuration (lines 183-198): Django context → JavaScript bridge

### manager_view.js
Main application logic organized into sections:
- **Configuration & Constants** (lines 1-67): DOM references, settings
- **Cache Management** (lines 69-166): LRU cache, warming, eviction
- **API Functions** (lines 168-315): Data fetching with error handling
- **Event Handlers** (lines 317-457): User interactions, expand/collapse
- **Rendering Functions** (lines 459-798): Table, headers, totals, KPIs
- **Initialization** (lines 800-1165): Select2 setup, event binding

### manager_view.css
Namespaced styles with sections:
- **Container & Cards** (lines 12-28): Base layout
- **Select2 Customization** (lines 43-233): Searchable dropdown styling
- **Summary Cards** (lines 236-271): KPI card styles
- **Table Styles** (lines 273-430): Hierarchical table, sticky columns
- **Gap Color Coding** (lines 433-449): Conditional formatting
- **Responsive Design** (lines 498-550): Media queries
- **Accessibility** (lines 578-612): Focus states, transitions

## Django Configuration

### URL Configuration
```python
# urls.py
path('manager-view/', views.manager_view, name='manager_view'),
path('manager-view/data/', views.manager_view_data, name='manager_view_data'),
path('manager-view/kpi/', views.manager_view_kpi, name='manager_view_kpi'),
```

### View Context
```python
# views.py
def manager_view(request):
    context = {
        'page_title': 'Manager View Dashboard',
        'report_months': [
            {'value': '2025-01', 'display': 'Jan 2025'},
            {'value': '2025-02', 'display': 'Feb 2025'},
            # ... more months
        ],
        'categories': [
            {'value': '', 'display': '-- All Categories --'},
            {'value': 'Commercial', 'display': 'Commercial'},
            # ... more categories
        ],
        'config': {
            'months_to_display': 6,
            'kpi_month_index': 1,
            'default_table_collapsed': True,
            'enable_expand_all': True,
        }
    }
    return render(request, 'manager_view.html', context)
```

### Prerequisites
- Django project with template rendering configured
- Static files properly configured in Django settings
- CDN access for jQuery, Select2, Bootstrap 5, and Font Awesome

### API Endpoint Requirements

#### Data Endpoint: `/manager-view/data/`
**Request Parameters**:
- `report_month` (required): YYYY-MM format (e.g., "2025-03")
- `category` (optional): Category name or empty for all

**Response Format**:
```json
{
    "report_month": "2025-03",
    "report_month_display": "February 2025",
    "success": true,
    "timestamp": "2025-10-18T17:10:55.867517",
    "total_categories":5,
    "category_name": "All Categories",
    "months": ["2025-03", "2025-04", "2025-05", "2025-06", "2025-07", "2025-08"],
    "months_display": ["Mar 2025", "Apr 2025", "May 2025", "Jun 2025", "Jul 2025", "Aug 2025"],
    "categories": [
        {
            "id": "cat_1",
            "name": "Amysis Onshore",
            "level": 1,
            "parent_id": null,
            "has_children": true,
            "data": {
                "2025-03": {"cf": 1000, "hc": 950, "cap": 1200, "gap": 200},
                "2025-04": {"cf": 1050, "hc": 960, "cap": 1220, "gap": 170}
            },
            "children": [
                {
                    "id": "cat_2",
                    "name": "Sub type 1",
                    "level": 2,
                    "parent_id": "cat_1",
                    "data": {
                        "2025-03": {"cf": 500, "hc": 480, "cap": 600, "gap": 100}
                    },
                    "children": []
                }
            ]
        }
    ]
}
```

#### KPI Endpoint: `/manager-view/kpi/`
**Request Parameters**:
- `report_month` (required): YYYY-MM format
- `category` (optional): Category name or empty for all

**Response Format**:
```json
{
    "client_forecast": 212984,
    "client_forecast_formatted": "212,984",
    "head_count": 482,
    "head_count_formatted": "482",
    "capacity": 310232,
    "capacity_formatted": "310,232",
    "capacity_gap": -1925,
    "capacity_gap_formatted": "-1,925",
    "gap_percentage": 0.9,
    "is_shortage": true,
    "kpi_month": "2025-04",
    "kpi_month_display": "April 2025",
    "status_class": "text-danger",
    "status_message": "⚠️ Shortage in April 2025"
}
```

**Field Descriptions**:
- `client_forecast` / `client_forecast_formatted`: Total client demand (raw number and formatted string)
- `head_count` / `head_count_formatted`: Total headcount (raw number and formatted string)
- `capacity` / `capacity_formatted`: Total capacity (raw number and formatted string)
- `capacity_gap` / `capacity_gap_formatted`: Difference between capacity and forecast (raw number and formatted string)
- `gap_percentage`: Gap as percentage of client forecast
- `is_shortage`: Boolean indicating if there's a capacity shortage
- `kpi_month`: Month value for KPI data (YYYY-MM format)
- `kpi_month_display`: Human-readable month label
- `status_class`: CSS class for styling (e.g., "text-danger", "text-success")
- `status_message`: User-friendly status message with icon

## Architecture Overview

### Data Flow

```
User Action (Select Filters)
    ↓
Event Handler (handleApplyFilters)
    ↓
Check Cache (getCache)
    ↓
├─ Cache Hit → Render Immediately (No Spinner)
│
└─ Cache Miss → Show Loading Spinner
       ↓
   Parallel API Calls (Promise.all)
       ↓
   ├─ fetchData()
   └─ fetchKPI()
       ↓
   Store in Cache (setCache)
       ↓
   Trigger Cache Warming (warmCacheInBackground)
       ↓
   Render UI (renderData + renderKPI)
       ↓
   Hide Loading Spinner
```

### Caching Strategy

1. **Cache Key Format**: `"YYYY-MM|CategoryName"` or `"YYYY-MM|All"` for all categories
2. **Cache Size Limit**: Maximum 20 filter combinations stored in memory (Map)
3. **Cache TTL**: 5 minutes (300,000 milliseconds)
4. **LRU Eviction**: When cache exceeds 20 entries, removes least recently accessed entry
5. **Cache Warming**: After successful data load, prefetches all categories for the same month in background

**Cache Structure**:
```javascript
STATE.cache = new Map();  // ES6 Map for efficient key-value storage

// Example cache entry
{
    "2025-03|Commercial": {
        data: { /* Full data API response */ },
        kpi: { /* Full KPI API response */ },
        timestamp: 1729270255867,      // When cache entry was created (Date.now())
        lastAccessed: 1729270300000    // Last time this entry was used (for LRU)
    },
    "2025-03|All": {
        data: { /* API response */ },
        kpi: { /* KPI response */ },
        timestamp: 1729270260000,
        lastAccessed: 1729270260000
    }
}
```

**Cache Metadata**:
- `timestamp`: Unix timestamp (milliseconds) when the cache entry was created
- `lastAccessed`: Unix timestamp (milliseconds) when the cache entry was last accessed
- Both used for LRU eviction and TTL validation
- `lastAccessed` updated on cache hits via `touchCacheEntry()`

### Total Row Calculation

**Critical Design Decision**: Totals are calculated client-side from **first-level categories only** to prevent double-counting.

```javascript
function calculateTotals(categories, months) {
    const totals = {};

    // Initialize totals for each month
    months.forEach(month => {
        const monthValue = typeof month === 'object' ? month.value : month;
        totals[monthValue] = { cf: 0, hc: 0, cap: 0, gap: 0 };
    });

    // Sum only level 1 categories (NOT children)
    categories.forEach(category => {
        months.forEach(month => {
            const monthValue = typeof month === 'object' ? month.value : month;
            if (category.data && category.data[monthValue]) {
                totals[monthValue].cf += category.data[monthValue].cf || 0;
                totals[monthValue].hc += category.data[monthValue].hc || 0;
                totals[monthValue].cap += category.data[monthValue].cap || 0;
                totals[monthValue].gap += category.data[monthValue].gap || 0;
            }
        });
    });

    return totals;
}
```

**Why First-Level Only?**
- First-level categories already contain aggregated data from their children
- Including children would count the same data multiple times
- Example: If "Commercial" = 1000 and "Sales Team" (child) = 500, total should be 1000, not 1500

### Expand/Collapse Mechanism

**HTML Attributes vs jQuery Data**:
```javascript
const tr = $('<tr>')
    .attr('data-id', category.id)              // HTML attribute for CSS selectors
    .attr('data-level', level)                 // HTML attribute for CSS selectors
    .attr('data-has-children', hasChildren)    // HTML attribute for CSS selectors
    .data('id', category.id)                   // jQuery cache for performance
    .data('level', level)                      // jQuery cache for performance
    .data('has-children', hasChildren);        // jQuery cache for performance
```

**Why Both?**
- `.attr()` creates actual HTML attributes readable by CSS selectors: `tr[data-has-children="true"]`
- `.data()` stores values in jQuery's internal cache for faster JavaScript access
- CSS rules like `.manager-view-hidden-row` require HTML attributes to work

### Event Delegation Pattern

All click events use event delegation for dynamic content:
```javascript
$(document).on('click', '.manager-view-category-name', handleCategoryNameClick);
$(document).on('click', '#expand-all', handleExpandAll);
$(document).on('click', '#collapse-all', handleCollapseAll);
```

This ensures events work even after table is re-rendered.

## Key Implementation Details

### CSS Namespacing
All CSS classes use the `manager-view-*` prefix to avoid conflicts with global styles:
- ✅ `.manager-view-category-name`
- ✅ `.manager-view-number-cell`
- ✅ `.manager-view-gap-danger`
- ❌ `.category-name` (would conflict with global styles)

### Month Value vs Display
API returns two arrays for month handling:
- `months`: Machine-readable values for data lookup (`"2025-03"`)
- `months_display`: Human-readable labels for headers (`"Mar 2025"`)

Combined into objects:
```javascript
const months = data.months.map((monthValue, index) => ({
    value: monthValue,              // For data lookup
    display: data.months_display[index]  // For headers
}));
```

### Gap Color Coding
Capacity gaps are color-coded based on value and severity:

```javascript
function getGapColorClass(gap, forecast) {
    // Null/undefined check
    if (gap === null || gap === undefined || forecast === null || forecast === undefined) {
        return '';
    }

    // Green: Surplus capacity (gap is positive or zero)
    if (gap >= 0) {
        return 'manager-view-gap-positive';
    }

    // Handle division by zero
    if (forecast === 0) {
        return 'manager-view-gap-danger';
    }

    // Calculate shortage percentage
    const shortagePercent = Math.abs(gap) / forecast * 100;

    // Red: Severe shortage (>10% of client forecast)
    if (shortagePercent > 10) {
        return 'manager-view-gap-danger';
    }
    // Yellow: Moderate shortage (0-10% of client forecast)
    else {
        return 'manager-view-gap-warning';
    }
}
```

**Color Rules**:
- 🟢 **Green** (`manager-view-gap-positive`): Surplus capacity (gap ≥ 0)
- 🟡 **Yellow** (`manager-view-gap-warning`): Shortage up to 10% of forecast
- 🔴 **Red** (`manager-view-gap-danger`): Shortage greater than 10% of forecast

**Examples**:
- Gap = 50, Forecast = 1000 → **Green** (surplus)
- Gap = 0, Forecast = 1000 → **Green** (exactly at capacity)
- Gap = -30, Forecast = 1000 → **Yellow** (3% shortage)
- Gap = -80, Forecast = 1000 → **Yellow** (8% shortage)
- Gap = -150, Forecast = 1000 → **Red** (15% shortage)

### Sticky Column Implementation
First column (Category) remains visible during horizontal scroll:
```css
.manager-view-category-name {
    position: sticky;
    left: 0;
    background: white;
    z-index: 5;
}

.manager-view-category-header {
    position: sticky;
    left: 0;
    z-index: 11 !important;  /* Above table header */
}
```

### Select2 Integration
Searchable dropdowns initialized with Bootstrap 5 theme:
```javascript
$('.manager-view-select2').select2({
    theme: 'bootstrap-5',
    width: '100%',
    placeholder: function() {
        return $(this).data('placeholder');
    },
    allowClear: true,
    minimumResultsForSearch: 0
});
```

## Configuration Options

Configured via Django context in `manager_view.html`:
```javascript
window.MANAGER_VIEW_CONFIG = {
    urls: {
        data: '{% url "forecast_app:manager_view_data" %}',
        kpi: '{% url "forecast_app:manager_view_kpi" %}',
    },
    settings: {
        monthsToDisplay: 6,              // Number of months to display
        kpiMonthIndex: 1,                // Index of month for KPI cards (0-based)
        defaultCollapsed: true,          // Start with collapsed rows
        enableExpandAll: true,           // Show expand/collapse buttons
    }
};
```
### 🧰 Developer Utilities (ManagerViewDebug API)

The following helper methods are exposed under the global object  
`window.ManagerViewDebug` for debugging and testing:

```js
// Inspect current app state (data, cache, filters, etc.)
ManagerViewDebug.getState()

// Inspect configuration loaded from Django (URLs, settings)
ManagerViewDebug.getConfig()

// Access cached DOM references (Select2, table, KPI cards)
ManagerViewDebug.getDOM()

// List all cached filter combinations with timestamps and TTL status
ManagerViewDebug.getCache()

// Clear all cached dashboard data (force fresh API calls)
ManagerViewDebug.clearCache()

// Reload data for the current filters
// Pass true to force-refresh and bypass cache
ManagerViewDebug.reloadData(true)

// Expand all hierarchical rows in the data table
ManagerViewDebug.expandAll()

// Collapse all hierarchical rows in the data table
ManagerViewDebug.collapseAll()
```

## Troubleshooting

### Issue: Table Shows "-" Instead of Data
**Cause**: Mismatch between month values used for data lookup
**Solution**: Ensure API returns both `months` and `months_display` arrays in same order

### Issue: Row Expansion Not Working
**Cause**: Missing HTML `data-*` attributes on table rows
**Solution**: Verify `renderCategoryRow()` uses both `.attr()` and `.data()` for row attributes

### Issue: Total Row Missing or Incorrect
**Cause**: Total calculation including nested categories
**Solution**: Ensure `calculateTotals()` only sums `level: 1` categories

### Issue: CSS Styles Not Applying
**Cause**: Missing `manager-view-*` prefix in JavaScript class additions
**Solution**: Search for `.addClass()` calls and ensure all use prefixed class names

### Issue: Click Events Not Firing After Re-render
**Cause**: Direct event binding instead of event delegation
**Solution**: Use `$(document).on('click', '.selector', handler)` pattern

### Issue: Cache Not Clearing Between Sessions
**Cause**: Cache stored in global variable persists during page session
**Solution**: This is intended behavior. Refresh page to clear cache, or implement manual "Clear Cache" button

## Development Notes

### Critical Code Sections

1. **manager_view.js:683-689** - Row attribute setting (both `.attr()` and `.data()`)
2. **manager_view.js:775-798** - Total calculation (first-level only)
3. **manager_view.js:605-608** - Month object creation (value + display)
4. **manager_view.css:328-335** - Category header sticky positioning
5. **manager_view.html:134** - Category header with proper class name

### Design Decisions

1. **Why Client-Side Totals?**
   - Backend may not know which categories are first-level in filtered view
   - Prevents over-fetching data just for totals
   - Allows flexibility in total calculation logic

2. **Why LRU Cache Instead of Browser Storage?**
   - Faster access (memory vs localStorage)
   - Automatic eviction prevents unbounded growth
   - No serialization overhead
   - Cleared on page refresh (desirable for financial data)

3. **Why Both HTML Attributes and jQuery Data?**
   - HTML attributes needed for CSS selectors to work
   - jQuery data cache provides performance benefit for JavaScript access
   - Small memory overhead worth the reliability

4. **Why Fire-and-Forget Cache Warming?**
   - Doesn't block UI or slow down initial data display
   - Improves subsequent user interactions
   - Graceful degradation if warming fails

### Testing Checklist

- [ ] Select report month, verify data loads
- [ ] Select category filter, verify filtered data loads
- [ ] Click individual category rows to expand/collapse
- [ ] Click "Expand All" button, verify all rows expand
- [ ] Click "Collapse All" button, verify all rows collapse
- [ ] Verify total row always displays at bottom
- [ ] Verify total row values match sum of first-level categories
- [ ] Change month, verify cache hit (instant load, no spinner)
- [ ] Change category, verify data updates correctly
- [ ] Verify KPI cards show correct values for KPI month
- [ ] Verify gap color coding (green/yellow/red)
- [ ] Test horizontal scroll, verify first column stays sticky
- [ ] Test on different screen sizes (1200px, 1400px, 1920px)
- [ ] Verify Select2 dropdowns are searchable
- [ ] Test error handling (disconnect network, verify error message)

## Browser Support

- **Minimum**: Modern browsers with ES6 support
- **Tested**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Not Supported**: Internet Explorer

## Performance Considerations

- **Initial Load**: ~2-3 API calls (data + KPI + potential cache warming)
- **Cached Load**: Instant (0 API calls, no spinner)
- **Table Rendering**: Optimized for up to 100 categories across 6 months
- **Memory Usage**: ~50 cache entries × ~50KB each = ~2.5MB max

## Future Enhancements

- [ ] Export table to Excel/CSV
- [ ] Chart visualizations for trend analysis
- [ ] User preference persistence (collapsed state, selected filters)
- [ ] Drill-down to individual employee details
- [ ] Real-time data updates with WebSockets
- [ ] Mobile-responsive design
- [ ] Dark mode support
- [ ] Keyboard navigation shortcuts
- [ ] Undo/redo for filter changes
- [ ] Bookmark/share specific views with URL parameters

## License

[Your License Here]

## Contributors

[Your Team/Developer Names Here]

## Support

For issues or questions, please contact [Your Support Contact Here]

---

**Last Updated**: 2025-01-XX
**Version**: 1.0.0