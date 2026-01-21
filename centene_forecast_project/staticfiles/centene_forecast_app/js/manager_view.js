/**
 * Manager View Dashboard - JavaScript
 *
 * Features:
 * - Select2 searchable dropdowns
 * - AJAX data fetching with proper error handling
 * - Dynamic table rendering with hierarchical expand/collapse
 * - KPI card updates
 * - Loading states and error messages
 * - Missing data handling
 * - Proper filtering functionality
 *
 * Dependencies:
 * - jQuery 3.6.0+
 * - Select2 4.1.0+
 * - Bootstrap 5
 * - Font Awesome
 */

(function() {
    'use strict';

    // ============================================================================
    // CONFIGURATION & GLOBAL STATE
    // ============================================================================

    const CONFIG = window.MANAGER_VIEW_CONFIG || {
        urls: {
            data: 'api/manager-view/data/',
            kpi: 'api/manager-view/kpi/'
        },
        settings: {
            monthsToDisplay: 6,
            kpiMonthIndex: 1,
            defaultCollapsed: true,
            enableExpandAll: true
        }
    };

    const STATE = {
        currentData: null,
        currentKPI: null,
        expandedCategories: new Set(),
        isLoading: false,
        currentFilters: {
            reportMonth: null,
            category: null
        },
        // Enhanced caching with filter keys
        cache: new Map(),        // key: "2024-01|All", value: { data, kpi, timestamp }
        cacheMaxSize: 20,        // Store up to 20 filter combinations
        cacheTTL: 300000,        // 5 minutes in milliseconds
        warmingInProgress: new Set()  // Track which keys are being warmed
    };

    const DOM = {};

    // ============================================================================
    // INITIALIZATION
    // ============================================================================

    function init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initializeApp);
        } else {
            initializeApp();
        }
    }

    function initializeApp() {
        console.log('Manager View: Initializing v3.0.0...');

        cacheDOMElements();
        initializeSelect2();
        attachEventListeners();
        setInitialUIState();

        console.log('Manager View: Initialization complete');
    }

    function cacheDOMElements() {
        DOM.reportMonthSelect = $('#report-month');
        DOM.categorySelect = $('#category');
        DOM.applyFiltersBtn = $('#apply-filters');
        DOM.summaryCards = $('#summary-cards');
        DOM.tableContainer = $('#data-table');
        DOM.tableBody = $('#table-body');
        DOM.tableHead = $('#capacity-table thead');
        DOM.initialMessage = $('#initial-message');
        DOM.loadingSpinner = $('#loading-spinner');
        DOM.errorAlert = $('#error-alert');
        DOM.errorMessage = $('#error-message');
        DOM.selectedCategory = $('#selected-category');
        DOM.selectedReport = $('#selected-report');
        DOM.expandAllBtn = $('#expand-all');
        DOM.collapseAllBtn = $('#collapse-all');
        DOM.lastUpdatedTime = $('#last-updated-time');

        // KPI elements
        DOM.kpi = {
            cf: $('#kpi-cf'),
            cfReport: $('#kpi-cf-report'),
            hc: $('#kpi-hc'),
            hcReport: $('#kpi-hc-report'),
            cap: $('#kpi-cap'),
            capReport: $('#kpi-cap-report'),
            gap: $('#kpi-gap'),
            gapReport: $('#kpi-gap-report')
        };
    }

    function initializeSelect2() {
        if (typeof $.fn.select2 === 'undefined') {
            console.error('Manager View: Select2 not loaded. Dropdowns will not be searchable.');
            return;
        }

        // Initialize Report Month dropdown
        DOM.reportMonthSelect.select2({
            theme: 'bootstrap-5',
            placeholder: '-- Select Report Month --',
            allowClear: false,
            width: '100%',
            minimumResultsForSearch: 5
        });

        // Initialize Category dropdown
        DOM.categorySelect.select2({
            theme: 'bootstrap-5',
            placeholder: '-- All Categories --',
            allowClear: true,
            width: '100%',
            minimumResultsForSearch: 3
        });

        console.log('Manager View: Select2 initialized');
    }

    function attachEventListeners() {
        // Apply filters button
        DOM.applyFiltersBtn.on('click', handleApplyFilters);

        // Expand/Collapse buttons
        if (DOM.expandAllBtn.length) {
            DOM.expandAllBtn.on('click', expandAllCategories);
        }
        if (DOM.collapseAllBtn.length) {
            DOM.collapseAllBtn.on('click', collapseAllCategories);
        }

        // Table click events (using event delegation)
        $(document).on('click', '.expand-icon', handleExpandIconClick);
        $(document).on('click', '.manager-view-category-name', handleCategoryNameClick);

        // Dropdown change events
        DOM.reportMonthSelect.on('change', function() {
            console.log('Report Month changed:', $(this).val());
        });

        DOM.categorySelect.on('change', function() {
            console.log('Category changed:', $(this).val());
        });
    }

    function setInitialUIState() {
        showElement(DOM.initialMessage);
        hideElement(DOM.summaryCards);
        hideElement(DOM.tableContainer);
        hideElement(DOM.loadingSpinner);
        hideElement(DOM.errorAlert);
    }

    // ============================================================================
    // EVENT HANDLERS
    // ============================================================================

    async function handleApplyFilters() {
        console.log('Manager View: Apply filters clicked');

        const reportMonth = DOM.reportMonthSelect.val();
        const category = DOM.categorySelect.val() || '';

        // Validate
        if (!reportMonth) {
            showError('Please select a Report Month');
            return;
        }

        if (STATE.isLoading) {
            console.log('Manager View: Already loading, ignoring click');
            return;
        }

        // Store current filters
        STATE.currentFilters = { reportMonth, category };

        await loadDashboardData(reportMonth, category);
    }

    function handleExpandIconClick(e) {
        e.stopPropagation();
        const row = $(this).closest('tr');
        const categoryId = row.data('id');
        if (categoryId) {
            toggleCategory(categoryId);
        }
    }

    function handleCategoryNameClick(e) {
        const target = $(e.target);
        if (!target.hasClass('expand-icon') && target.closest('.expand-icon').length === 0) {
            const row = target.closest('tr');
            const categoryId = row.data('id');
            const hasChildren = row.data('has-children');
            if (categoryId && hasChildren) {
                toggleCategory(categoryId);
            }
        }
    }

    // ============================================================================
    // CACHING UTILITIES
    // ============================================================================

    function getCacheKey(reportMonth, category) {
        return `${reportMonth}|${category || 'All'}`;
    }

    function isCacheValid(cachedEntry) {
        if (!cachedEntry) return false;
        return (Date.now() - cachedEntry.timestamp) < STATE.cacheTTL;
    }

    function enforceCacheLimit() {
        if (STATE.cache.size > STATE.cacheMaxSize) {
            // LRU Eviction: Find least recently used entry
            let oldestKey = null;
            let oldestAccessTime = Date.now();

            STATE.cache.forEach((value, key) => {
                const accessTime = value.lastAccessed || value.timestamp;
                if (accessTime < oldestAccessTime) {
                    oldestAccessTime = accessTime;
                    oldestKey = key;
                }
            });

            if (oldestKey) {
                STATE.cache.delete(oldestKey);
                const idleTime = Math.round((Date.now() - oldestAccessTime) / 1000);
                console.log(`Manager View: Cache evicted ${oldestKey} (LRU, idle for ${idleTime}s)`);
            }
        }
    }

    function touchCacheEntry(cacheKey) {
        // Update last accessed time for LRU tracking
        const cached = STATE.cache.get(cacheKey);
        if (cached) {
            cached.lastAccessed = Date.now();
        }
    }

    function getAvailableCategories() {
        // Extract all category options from the dropdown
        const categories = [];
        DOM.categorySelect.find('option').each(function() {
            const value = $(this).val();
            categories.push(value || ''); // Empty string for "All Categories"
        });
        return categories;
    }

    function clearCache() {
        STATE.cache.clear();
        STATE.warmingInProgress.clear();
        console.log('Manager View: Cache cleared');
    }

    // ============================================================================
    // DATA FETCHING
    // ============================================================================

    async function loadDashboardData(reportMonth, category, forceRefresh = false) {
        console.log(`Manager View: Loading data for ${reportMonth}, category: ${category || 'All'}`);

        const cacheKey = getCacheKey(reportMonth, category);

        // Check cache first (unless force refresh requested)
        if (!forceRefresh) {
            const cached = STATE.cache.get(cacheKey);
            if (cached && isCacheValid(cached)) {
                console.log(`Manager View: Using cached data for ${cacheKey}`);

                // Update LRU access time
                touchCacheEntry(cacheKey);

                // Use cached data instantly (no loading spinner!)
                STATE.currentData = cached.data;
                STATE.currentKPI = cached.kpi;

                // Reset expanded categories if default collapsed
                if (CONFIG.settings.defaultCollapsed) {
                    STATE.expandedCategories.clear();
                }

                // Update UI
                const hasKPI = cached.kpi && cached.kpi.kpi && Object.keys(cached.kpi.kpi).length > 0;
                const hasCategories = cached.data && cached.data.categories && cached.data.categories.length > 0;

                if (hasKPI) {
                    updateKPICards(cached.kpi.kpi);
                    showElement(DOM.summaryCards);
                } else {
                    hideElement(DOM.summaryCards);
                }

                if (hasCategories) {
                    updateTable(cached.data);
                    updateSelectedLabels(cached.data);
                    updateLastUpdatedTime(cached.timestamp);
                    showElement(DOM.tableContainer);
                } else {
                    hideElement(DOM.tableContainer);
                }

                hideError();
                hideInfo();
                console.log('Manager View: Cache hit - instant load!');
                return;
            }
        }

        // Cache miss or force refresh - fetch from API
        STATE.isLoading = true;
        showLoading();
        hideError();
        hideInfo();

        try {
            // Fetch both data and KPI in parallel
            const [dataResponse, kpiResponse] = await Promise.all([
                fetchData(reportMonth, category),
                fetchKPI(reportMonth, category)
            ]);

            // Check for success
            if (!dataResponse || !dataResponse.success) {
                throw new Error(dataResponse?.error || 'Failed to fetch table data');
            }
            if (!kpiResponse || !kpiResponse.success) {
                throw new Error(kpiResponse?.error || 'Failed to fetch KPI data');
            }

            // Check if we have any data (but it's not an error)
            const hasCategories = dataResponse.categories && dataResponse.categories.length > 0;
            const hasKPI = kpiResponse.kpi && Object.keys(kpiResponse.kpi).length > 0;

            if (!hasCategories && !hasKPI) {
                // No data available - show info message
                showInfo('No data available for the selected report month and category combination.');
                hideElement(DOM.summaryCards);
                hideElement(DOM.tableContainer);
                return;
            }

            // Store in current state
            STATE.currentData = dataResponse;
            STATE.currentKPI = kpiResponse;

            // Store in cache
            const timestamp = Date.now();
            STATE.cache.set(cacheKey, {
                data: dataResponse,
                kpi: kpiResponse,
                timestamp: timestamp
            });
            enforceCacheLimit();

            console.log(`Manager View: Data cached for ${cacheKey}`);

            // Reset expanded categories if default collapsed
            if (CONFIG.settings.defaultCollapsed) {
                STATE.expandedCategories.clear();
            }

            // Update UI
            if (hasKPI) {
                updateKPICards(kpiResponse.kpi);
                showElement(DOM.summaryCards);

                // Fade in animation for KPI cards
                DOM.summaryCards.css('opacity', '0');
                setTimeout(() => {
                    DOM.summaryCards.css({
                        'transition': 'opacity 0.5s',
                        'opacity': '1'
                    });
                }, 50);
            } else {
                hideElement(DOM.summaryCards);
            }

            if (hasCategories) {
                updateTable(dataResponse);
                updateSelectedLabels(dataResponse);
                updateLastUpdatedTime(timestamp);
                showElement(DOM.tableContainer);
            } else {
                hideElement(DOM.tableContainer);
                showInfo('No category data available for the selected filters.');
            }

            console.log('Manager View: Data loaded successfully');

            // Trigger cache warming in the background (all categories for this month)
            warmCache(reportMonth, category);

        } catch (error) {
            console.error('Manager View: Error loading data', error);
            showError(error.message || 'Failed to load data. Please try again.');

            // Hide cards and table on error
            hideElement(DOM.summaryCards);
            hideElement(DOM.tableContainer);

        } finally {
            STATE.isLoading = false;
            hideLoading();
        }
    }

    async function warmCache(reportMonth, currentCategory) {
        // Get all available categories from dropdown
        const allCategories = getAvailableCategories();

        console.log(`Manager View: Cache warming for ${reportMonth} - ${allCategories.length} categories`);

        // Warm cache for all OTHER categories (not the current one)
        const categoriesToWarm = allCategories.filter(cat => cat !== (currentCategory || ''));

        for (const cat of categoriesToWarm) {
            const cacheKey = getCacheKey(reportMonth, cat);

            // Skip if already cached and valid
            const cached = STATE.cache.get(cacheKey);
            if (cached && isCacheValid(cached)) {
                continue;
            }

            // Skip if warming already in progress
            if (STATE.warmingInProgress.has(cacheKey)) {
                continue;
            }

            // Mark as warming
            STATE.warmingInProgress.add(cacheKey);

            // Fetch in background (don't await - fire and forget)
            (async () => {
                try {
                    const [dataResponse, kpiResponse] = await Promise.all([
                        fetchData(reportMonth, cat),
                        fetchKPI(reportMonth, cat)
                    ]);

                    if (dataResponse && dataResponse.success && kpiResponse && kpiResponse.success) {
                        STATE.cache.set(cacheKey, {
                            data: dataResponse,
                            kpi: kpiResponse,
                            timestamp: Date.now()
                        });
                        enforceCacheLimit();
                        console.log(`Manager View: Warmed cache for ${cacheKey}`);
                    }
                } catch (error) {
                    console.warn(`Manager View: Cache warming failed for ${cacheKey}`, error);
                } finally {
                    STATE.warmingInProgress.delete(cacheKey);
                }
            })();
        }
    }

    async function fetchData(reportMonth, category) {
        const params = new URLSearchParams({ report_month: reportMonth });
        if (category) {
            params.append('category', category);
        }

        const url = `${CONFIG.urls.data}?${params.toString()}`;
        console.log(`Manager View: Fetching data from ${url}`);

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    async function fetchKPI(reportMonth, category) {
        const params = new URLSearchParams({ report_month: reportMonth });
        if (category) {
            params.append('category', category);
        }

        const url = `${CONFIG.urls.kpi}?${params.toString()}`;
        console.log(`Manager View: Fetching KPI from ${url}`);

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    // ============================================================================
    // UI UPDATE FUNCTIONS
    // ============================================================================

    function updateKPICards(kpiData) {
        if (!kpiData) {
            console.warn('Manager View: No KPI data provided');
            return;
        }

        console.log('Manager View: Updating KPI cards', kpiData);

        // Update Client Forecast
        if (DOM.kpi.cf && DOM.kpi.cf.length) {
            DOM.kpi.cf.text(kpiData.client_forecast_formatted || formatNumber(kpiData.client_forecast));
        }
        if (DOM.kpi.cfReport && DOM.kpi.cfReport.length) {
            DOM.kpi.cfReport.text(kpiData.kpi_month_display || '');
        }

        // Update Head Count
        if (DOM.kpi.hc && DOM.kpi.hc.length) {
            DOM.kpi.hc.text(kpiData.head_count_formatted || formatNumber(kpiData.head_count));
        }
        if (DOM.kpi.hcReport && DOM.kpi.hcReport.length) {
            DOM.kpi.hcReport.text(kpiData.kpi_month_display || '');
        }

        // Update Capacity
        if (DOM.kpi.cap && DOM.kpi.cap.length) {
            DOM.kpi.cap.text(kpiData.capacity_formatted || formatNumber(kpiData.capacity));
        }
        if (DOM.kpi.capReport && DOM.kpi.capReport.length) {
            DOM.kpi.capReport.text(kpiData.kpi_month_display || '');
        }

        // Update Gap with status
        if (DOM.kpi.gap && DOM.kpi.gap.length) {
            const gapValue = kpiData.capacity_gap;
            DOM.kpi.gap.text(kpiData.capacity_gap_formatted || formatNumber(gapValue));

            if (kpiData.is_shortage) {
                DOM.kpi.gap.removeClass('text-success').addClass('text-danger');
            } else {
                DOM.kpi.gap.removeClass('text-danger').addClass('text-success');
            }
        }
        if (DOM.kpi.gapReport && DOM.kpi.gapReport.length) {
            DOM.kpi.gapReport.text(kpiData.status_message || '');
        }
    }

    function updateTable(data) {
        if (!data) {
            console.warn('Manager View: No table data provided');
            return;
        }

        console.log('Manager View: Updating table', data);

        // Validate months data
        if (!data.months || !Array.isArray(data.months) || data.months.length === 0) {
            console.error('Manager View: Invalid months data structure');
            return;
        }

        // Create combined month objects with both value (for data lookup) and display (for headers)
        const months = data.months.map((monthValue, index) => ({
            value: monthValue,
            display: data.months_display && data.months_display[index] ? data.months_display[index] : monthValue
        }));

        // Update table headers
        updateTableHeaders(months);

        // Clear existing table body
        if (DOM.tableBody && DOM.tableBody.length) {
            DOM.tableBody.empty();
        } else {
            console.error('Manager View: Table body element not found');
            return;
        }

        // Check if we have categories
        if (!data.categories || data.categories.length === 0) {
            const tr = $('<tr>').append(
                $('<td>')
                    .attr('colspan', 1 + (months.length * 4))
                    .addClass('text-center text-muted')
                    .text('No data available for selected filters')
            );
            DOM.tableBody.append(tr);
            return;
        }

        // Render categories
        data.categories.forEach(category => {
            renderCategory(category, 1, months);
        });

        // Always calculate and render total row from first-level categories
        const totals = calculateTotals(data.categories, months);
        renderTotalRow(totals, months);
    }

    function updateTableHeaders(monthDisplays) {
        // Find header rows
        const headerRows = DOM.tableHead.find('tr');
        if (headerRows.length < 2) {
            console.error('Manager View: Table header structure incorrect');
            return;
        }

        const monthRow = $(headerRows[0]);
        const subHeaderRow = $(headerRows[1]);

        // Clear existing month headers (keep Category header)
        monthRow.find('th:not(:first)').remove();
        subHeaderRow.find('th').remove();

        // Add month headers
        monthDisplays.forEach((monthDisplay) => {
            const displayText = typeof monthDisplay === 'object' ? monthDisplay.display : monthDisplay;

            const th = $('<th>')
                .attr('colspan', 4)
                .addClass('text-center manager-view-month-group')
                .text(displayText);
            monthRow.append(th);
        });

        // Add sub-headers (CF, HC, Cap, Gap for each month)
        monthDisplays.forEach(() => {
            ['CF', 'HC', 'Cap', 'Gap'].forEach((label) => {
                const th = $('<th>').addClass('text-center').text(label);
                subHeaderRow.append(th);
            });
        });
    }

    function renderCategory(category, level, months) {
        // Determine if category has actual children to render
        const hasChildren = category.children && category.children.length > 0;

        const tr = $('<tr>')
            .attr('data-id', category.id)
            .attr('data-level', level)
            .attr('data-has-children', hasChildren)
            .data('id', category.id)
            .data('level', level)
            .data('has-children', hasChildren)
            .addClass(`manager-view-level-${level}`);

        // Apply collapsed state
        if (level > 1 && CONFIG.settings.defaultCollapsed && category.parent_id && !STATE.expandedCategories.has(category.parent_id)) {
            tr.addClass('manager-view-hidden-row');
        }

        // Category name cell
        const nameTd = $('<td>').addClass('manager-view-category-name');
        const nameContent = $('<span>').addClass('manager-view-category-content');

        // Add expand icon if has children
        if (category.has_children || (category.children && category.children.length > 0)) {
            const isExpanded = STATE.expandedCategories.has(category.id);
            const icon = $('<i>')
                .addClass('fas expand-icon')
                .addClass(isExpanded ? 'fa-minus-square' : 'fa-plus-square');
            nameContent.append(icon).append(' ');
        }

        nameContent.append(document.createTextNode(category.name));
        nameTd.append(nameContent);
        tr.append(nameTd);

        // Data cells for each month
        months.forEach((month, index) => {
            const monthValue = typeof month === 'object' ? month.value : month;
            const monthData = category.data ? category.data[monthValue] : null;

            if (!monthData) {
                // Missing data - show dashes
                ['CF', 'HC', 'Cap', 'Gap'].forEach((_, colIndex) => {
                    const td = $('<td>')
                        .addClass('manager-view-number-cell text-muted')
                        .text('-');
                    if (colIndex === 0 && index > 0) {
                        td.addClass('manager-view-month-group');
                    }
                    tr.append(td);
                });
                return;
            }

            // CF
            const cfTd = $('<td>')
                .addClass('manager-view-number-cell')
                .text(formatNumber(monthData.cf));
            if (index > 0) cfTd.addClass('manager-view-month-group');
            tr.append(cfTd);

            // HC
            const hcTd = $('<td>')
                .addClass('manager-view-number-cell')
                .text(formatNumber(monthData.hc));
            tr.append(hcTd);

            // Cap
            const capTd = $('<td>')
                .addClass('manager-view-number-cell')
                .text(formatNumber(monthData.cap));
            tr.append(capTd);

            // Gap (with color coding)
            const gapTd = $('<td>')
                .addClass('manager-view-number-cell')
                .text(formatNumber(monthData.gap));

            const gapClass = getGapColorClass(monthData.gap, monthData.cf);
            if (gapClass) {
                gapTd.addClass(gapClass);
            }

            tr.append(gapTd);
        });

        DOM.tableBody.append(tr);

        // Recursively render children
        if (category.children && category.children.length > 0) {
            category.children.forEach(child => {
                child.parent_id = category.id;
                renderCategory(child, level + 1, months);
            });
        }
    }

    function calculateTotals(categories, months) {
        // Calculate totals from first-level categories only
        const totals = {};

        months.forEach(month => {
            const monthValue = typeof month === 'object' ? month.value : month;
            totals[monthValue] = { cf: 0, hc: 0, cap: 0, gap: 0 };
        });

        // Sum only first-level categories (level 1)
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

    function renderTotalRow(totals, months) {
        const tr = $('<tr>').addClass('manager-view-total-row');

        // Total label cell
        const nameTd = $('<td>')
            .addClass('manager-view-category-name')
            .html('<strong>TOTAL</strong>');
        tr.append(nameTd);

        // Data cells for each month
        months.forEach((month, index) => {
            const monthValue = typeof month === 'object' ? month.value : month;
            const monthData = totals[monthValue];

            if (!monthData) {
                // Missing data
                ['CF', 'HC', 'Cap', 'Gap'].forEach((_, colIndex) => {
                    const td = $('<td>')
                        .addClass('manager-view-number-cell text-muted')
                        .html('<strong>-</strong>');
                    if (colIndex === 0 && index > 0) {
                        td.addClass('manager-view-month-group');
                    }
                    tr.append(td);
                });
                return;
            }

            // CF
            const cfTd = $('<td>')
                .addClass('manager-view-number-cell')
                .html(`<strong>${formatNumber(monthData.cf)}</strong>`);
            if (index > 0) cfTd.addClass('manager-view-month-group');
            tr.append(cfTd);

            // HC
            const hcTd = $('<td>')
                .addClass('manager-view-number-cell')
                .html(`<strong>${formatNumber(monthData.hc)}</strong>`);
            tr.append(hcTd);

            // Cap
            const capTd = $('<td>')
                .addClass('manager-view-number-cell')
                .html(`<strong>${formatNumber(monthData.cap)}</strong>`);
            tr.append(capTd);

            // Gap
            const gapTd = $('<td>')
                .addClass('manager-view-number-cell')
                .html(`<strong>${formatNumber(monthData.gap)}</strong>`);

            const gapClass = getGapColorClass(monthData.gap, monthData.cf);
            if (gapClass) {
                gapTd.addClass(gapClass);
            }

            tr.append(gapTd);
        });

        DOM.tableBody.append(tr);
    }

    function updateSelectedLabels(data) {
        if (DOM.selectedCategory.length) {
            DOM.selectedCategory.text(data.category_name || 'All Categories');
        }
        if (DOM.selectedReport.length) {
            DOM.selectedReport.text((data.report_month_display || data.report_month) + ' Report');
        }
    }

    function updateLastUpdatedTime(timestamp) {
        if (DOM.lastUpdatedTime && DOM.lastUpdatedTime.length) {
            const date = timestamp ? new Date(timestamp) : new Date();
            const options = {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                hour12: true
            };
            const formattedTime = date.toLocaleString('en-US', options);

            // Add cache indicator if using cached data
            if (timestamp && timestamp < Date.now() - 1000) {
                DOM.lastUpdatedTime.html(`<i class="fas fa-database me-1"></i>${formattedTime} (cached)`);
            } else {
                DOM.lastUpdatedTime.text(formattedTime);
            }
        }
    }

    // ============================================================================
    // EXPAND/COLLAPSE FUNCTIONALITY
    // ============================================================================

    function toggleCategory(categoryId) {
        console.log(`Manager View: Toggling category ${categoryId}`);

        const isExpanded = STATE.expandedCategories.has(categoryId);

        if (isExpanded) {
            STATE.expandedCategories.delete(categoryId);
            hideChildren(categoryId);
            updateExpandIcon(categoryId, false);
        } else {
            STATE.expandedCategories.add(categoryId);
            showChildren(categoryId);
            updateExpandIcon(categoryId, true);
        }
    }

    function showChildren(categoryId) {
        $(`tr[data-id]`).each(function() {
            const row = $(this);
            const parentId = getParentIdFromRow(row);
            if (parentId === categoryId) {
                row.removeClass('manager-view-hidden-row');
            }
        });
    }

    function hideChildren(categoryId) {
        const childRows = getDescendantRows(categoryId);
        childRows.forEach(row => {
            $(row).addClass('manager-view-hidden-row');
            const childId = $(row).data('id');
            STATE.expandedCategories.delete(childId);
            updateExpandIcon(childId, false);
        });
    }

    function getDescendantRows(categoryId) {
        const descendants = [];
        const rows = DOM.tableBody.find('tr[data-id]').toArray();

        const parentRow = rows.find(r => $(r).data('id') === categoryId);
        if (!parentRow) return descendants;

        const parentLevel = parseInt($(parentRow).data('level'));
        let index = rows.indexOf(parentRow) + 1;

        while (index < rows.length) {
            const row = rows[index];
            const rowLevel = parseInt($(row).data('level'));

            if (rowLevel <= parentLevel) {
                break;
            }

            descendants.push(row);
            index++;
        }

        return descendants;
    }

    function getParentIdFromRow(row) {
        const rows = DOM.tableBody.find('tr[data-id]').toArray();
        const currentIndex = rows.indexOf(row[0]);
        const currentLevel = parseInt(row.data('level'));

        for (let i = currentIndex - 1; i >= 0; i--) {
            const potentialParent = $(rows[i]);
            const potentialParentLevel = parseInt(potentialParent.data('level'));

            if (potentialParentLevel === currentLevel - 1) {
                return potentialParent.data('id');
            }

            if (potentialParentLevel < currentLevel - 1) {
                break;
            }
        }

        return null;
    }

    function updateExpandIcon(categoryId, isExpanded) {
        const row = $(`tr[data-id="${categoryId}"]`);
        if (row.length) {
            const icon = row.find('.expand-icon');
            if (icon.length) {
                icon.removeClass('fa-plus-square fa-minus-square');
                icon.addClass(isExpanded ? 'fa-minus-square' : 'fa-plus-square');
            }
        }
    }

    function expandAllCategories() {
        console.log('Manager View: Expanding all categories');

        const rows = DOM.tableBody.find('tr[data-has-children="true"]');
        rows.each(function() {
            const categoryId = $(this).data('id');
            if (!STATE.expandedCategories.has(categoryId)) {
                STATE.expandedCategories.add(categoryId);
                updateExpandIcon(categoryId, true);
            }
        });

        DOM.tableBody.find('.manager-view-hidden-row').removeClass('manager-view-hidden-row');
    }

    function collapseAllCategories() {
        console.log('Manager View: Collapsing all categories');

        STATE.expandedCategories.clear();

        const rows = DOM.tableBody.find('tr[data-has-children="true"]');
        rows.each(function() {
            const categoryId = $(this).data('id');
            updateExpandIcon(categoryId, false);
        });

        DOM.tableBody.find('tr[data-level]').each(function() {
            const level = parseInt($(this).data('level'));
            if (level > 1) {
                $(this).addClass('manager-view-hidden-row');
            }
        });
    }

    // ============================================================================
    // UTILITY FUNCTIONS
    // ============================================================================

    function formatNumber(num) {
        if (num === null || num === undefined || num === '') {
            return '-';
        }
        if (typeof num === 'string') {
            num = parseFloat(num);
        }
        if (isNaN(num)) {
            return '-';
        }
        return num.toLocaleString('en-US');
    }

    function getGapColorClass(gap, forecast) {
        if (gap === null || gap === undefined || forecast === null || forecast === undefined) {
            return '';
        }

        if (gap >= 0) {
            return 'manager-view-gap-positive';  // Green: surplus capacity
        }

        if (forecast === 0) {
            return 'manager-view-gap-danger';
        }

        // Gap is negative (shortage) - calculate percentage
        const shortagePercent = Math.abs(gap) / forecast * 100;

        if (shortagePercent > 10) {
            return 'manager-view-gap-danger';    // Red: >10% shortage
        } else {
            return 'manager-view-gap-warning';   // Yellow: any shortage up to 10%
        }
    }

    function showElement(element) {
        if (element && element.length) {
            element.show();
        }
    }

    function hideElement(element) {
        if (element && element.length) {
            element.hide();
        }
    }

    function showLoading() {
        hideError();
        hideInfo();
        hideElement(DOM.summaryCards);
        hideElement(DOM.tableContainer);
        showElement(DOM.loadingSpinner);
        if (DOM.applyFiltersBtn.length) {
            DOM.applyFiltersBtn.prop('disabled', true);
        }
    }

    function hideLoading() {
        hideElement(DOM.loadingSpinner);
        if (DOM.applyFiltersBtn.length) {
            DOM.applyFiltersBtn.prop('disabled', false);
        }
    }

    function showError(message) {
        if (DOM.errorMessage && DOM.errorMessage.length) {
            DOM.errorMessage.text(message);
        }
        if (DOM.errorAlert && DOM.errorAlert.length) {
            showElement(DOM.errorAlert);
            setTimeout(() => {
                hideError();
            }, 10000);
        }
    }

    function hideError() {
        if (DOM.errorAlert && DOM.errorAlert.length) {
            hideElement(DOM.errorAlert);
        }
    }

    function showInfo(message) {
        hideError();
        if (DOM.initialMessage && DOM.initialMessage.length) {
            DOM.initialMessage.html(`<i class="fas fa-info-circle me-2"></i>${message}`);
            DOM.initialMessage.removeClass('alert-warning alert-danger').addClass('alert-info');
            showElement(DOM.initialMessage);
        }
    }

    function hideInfo() {
        if (DOM.initialMessage && DOM.initialMessage.length) {
            hideElement(DOM.initialMessage);
        }
    }

    // ============================================================================
    // PUBLIC API (for debugging)
    // ============================================================================

    window.ManagerViewDebug = {
        getState: () => STATE,
        getConfig: () => CONFIG,
        getDOM: () => DOM,
        getCache: () => {
            const cacheEntries = [];
            STATE.cache.forEach((value, key) => {
                cacheEntries.push({
                    key: key,
                    timestamp: value.timestamp,
                    age: Math.round((Date.now() - value.timestamp) / 1000) + 's',
                    isValid: isCacheValid(value)
                });
            });
            return cacheEntries;
        },
        clearCache: clearCache,
        reloadData: (forceRefresh = false) => {
            if (STATE.currentFilters.reportMonth) {
                return loadDashboardData(STATE.currentFilters.reportMonth, STATE.currentFilters.category, forceRefresh);
            }
        },
        expandAll: expandAllCategories,
        collapseAll: collapseAllCategories
    };

    // ============================================================================
    // START APPLICATION
    // ============================================================================

    init();

})();
