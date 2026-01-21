/**
 * Execution Monitoring JavaScript
 *
 * Features:
 * - Bootstrap 5 toast notifications
 * - Lazy loading with pagination (100 records per batch)
 * - Hero card auto-refresh polling (5s when IN_PROGRESS)
 * - Real AJAX calls to Django APIs
 * - Proper error handling
 */

(function() {
    'use strict';

    // ========================================================================
    // Configuration
    // ========================================================================

    const CONFIG = window.EXECUTION_MONITORING_CONFIG || {
        urls: {},
        settings: {}
    };

    // ========================================================================
    // Global State
    // ========================================================================

    const STATE = {
        // Pagination
        currentPage: 1,
        itemsPerPage: CONFIG.settings.items_per_page || 10,
        totalLoaded: 0,
        allData: [],
        hasMoreData: true,
        isLoading: false,

        // Filters
        filters: {
            month: null,
            year: null,
            status: [],
            uploaded_by: null
        },

        // Polling
        pollingInterval: null,
        pollingEnabled: false,

        // Current execution
        latestExecution: null,
        selectedExecution: null,

        // Toast
        toastInstance: null,

        // Caching
        cache: new Map(),           // key: "month|year|status|user|limit|offset", value: { data, timestamp }
        cacheMaxSize: 50,            // Store up to 50 filter combinations
        cacheTTL: 30000,             // 30 seconds (matches backend cache)
        kpiCache: new Map(),         // Separate cache for KPI data
        kpiCacheTTL: 60000,          // 60 seconds (matches backend cache)
        detailsCache: new Map(),     // Cache for execution details
        detailsCacheTTL: 5000        // 5 seconds for IN_PROGRESS, handled dynamically
    };

    // ========================================================================
    // DOM Elements Cache
    // ========================================================================

    const DOM = {};

    function cacheDOMElements() {
        // Hero card elements
        DOM.heroCard = document.getElementById('layout-hero');
        DOM.heroIcon = document.getElementById('hero-icon');
        DOM.heroExecId = document.getElementById('hero-exec-id');
        DOM.heroStatus = document.getElementById('hero-status');
        DOM.heroStart = document.getElementById('hero-start');
        DOM.heroDuration = document.getElementById('hero-duration');
        DOM.heroRecords = document.getElementById('hero-records');
        DOM.heroSuccessRate = document.getElementById('hero-success-rate');
        DOM.heroError = document.getElementById('hero-error');
        DOM.heroErrorType = document.getElementById('hero-error-type');

        // Filter elements
        DOM.monthFilter = document.getElementById('month-filter');
        DOM.yearFilter = document.getElementById('year-filter');
        DOM.userFilter = document.getElementById('user-filter');
        DOM.statusCheckboxes = document.querySelectorAll('.status-checkboxes input[type="checkbox"]');

        // KPI elements
        DOM.kpiTotal = document.getElementById('kpi-total');
        DOM.kpiSuccessRate = document.getElementById('kpi-success-rate');
        DOM.kpiAvgDuration = document.getElementById('kpi-avg-duration');
        DOM.kpiFailed = document.getElementById('kpi-failed');

        // Table elements
        DOM.tableBody = document.getElementById('execution-table-body');
        DOM.paginationInfo = document.getElementById('pagination-info');
        DOM.prevBtn = document.getElementById('prev-btn');
        DOM.nextBtn = document.getElementById('next-btn');

        // Drawer elements
        DOM.drawerOverlay = document.getElementById('drawer-overlay');
        DOM.sideDrawer = document.getElementById('side-drawer');
        DOM.drawerExecId = document.getElementById('drawer-exec-id');

        // Loading spinner
        DOM.loadingSpinner = document.getElementById('loading-spinner');

        // Toast
        DOM.toastElement = document.getElementById('notification-toast');
        DOM.toastMessage = document.getElementById('toast-message');
    }

    // ========================================================================
    // Toast Notifications
    // ========================================================================

    function showToast(message, type = 'success') {
        if (!DOM.toastElement || !DOM.toastMessage) return;

        // Remove previous type classes
        DOM.toastElement.classList.remove('bg-success', 'bg-danger', 'bg-info', 'bg-warning');

        // Add new type class
        const bgClass = {
            'success': 'bg-success',
            'error': 'bg-danger',
            'info': 'bg-info',
            'warning': 'bg-warning'
        }[type] || 'bg-info';

        DOM.toastElement.classList.add(bgClass);
        DOM.toastMessage.textContent = message;

        // Create and show Bootstrap toast
        if (!STATE.toastInstance) {
            STATE.toastInstance = new bootstrap.Toast(DOM.toastElement, {
                autohide: true,
                delay: CONFIG.settings.toast_duration || 3000
            });
        }

        STATE.toastInstance.show();
    }

    // ========================================================================
    // Loading Spinner
    // ========================================================================

    function showLoading() {
        if (DOM.loadingSpinner) {
            DOM.loadingSpinner.style.display = 'flex';
        }
    }

    function hideLoading() {
        if (DOM.loadingSpinner) {
            DOM.loadingSpinner.style.display = 'none';
        }
    }

    // ========================================================================
    // Caching Utilities
    // ========================================================================

    function getCacheKey(limit, offset, filters) {
        const statusKey = (filters.status || []).sort().join(',') || 'all';
        return `${filters.month || 'all'}|${filters.year || 'all'}|${statusKey}|${filters.uploaded_by || 'all'}|${limit}|${offset}`;
    }

    function getKPICacheKey(filters) {
        const statusKey = (filters.status || []).sort().join(',') || 'all';
        return `${filters.month || 'all'}|${filters.year || 'all'}|${statusKey}|${filters.uploaded_by || 'all'}`;
    }

    function isCacheValid(cachedEntry, ttl) {
        if (!cachedEntry) return false;
        return (Date.now() - cachedEntry.timestamp) < ttl;
    }

    function touchCacheEntry(cache, cacheKey) {
        const cached = cache.get(cacheKey);
        if (cached) {
            cached.lastAccessed = Date.now();
        }
    }

    function enforceCacheLimit(cache, maxSize) {
        if (cache.size > maxSize) {
            // LRU Eviction
            let oldestKey = null;
            let oldestAccessTime = Date.now();

            cache.forEach((value, key) => {
                const accessTime = value.lastAccessed || value.timestamp;
                if (accessTime < oldestAccessTime) {
                    oldestAccessTime = accessTime;
                    oldestKey = key;
                }
            });

            if (oldestKey) {
                cache.delete(oldestKey);
                console.log(`[Cache] Evicted ${oldestKey} (LRU)`);
            }
        }
    }

    function clearAllCaches() {
        STATE.cache.clear();
        STATE.kpiCache.clear();
        STATE.detailsCache.clear();
        console.log('[Cache] All caches cleared');
    }

    function clearListAndKpiCaches() {
        STATE.cache.clear();
        STATE.kpiCache.clear();
        console.log('[Cache] List and KPI caches cleared (details cache preserved)');
    }

    // ========================================================================
    // API Calls
    // ========================================================================

    async function fetchExecutions(limit, offset, forceRefresh = false, ignoreFilters = false) {
        // Create filters object (empty if ignoreFilters is true)
        const filtersToUse = ignoreFilters ? { month: null, year: null, status: [], uploaded_by: null } : STATE.filters;
        const cacheKey = getCacheKey(limit, offset, filtersToUse);

        // Check cache first (unless force refresh)
        if (!forceRefresh) {
            const cached = STATE.cache.get(cacheKey);
            if (cached && isCacheValid(cached, STATE.cacheTTL)) {
                console.log(`[API] Using cached executions for ${cacheKey}`);
                touchCacheEntry(STATE.cache, cacheKey);
                return cached.data;
            }
        }

        try {
            const params = new URLSearchParams({
                limit: limit,
                offset: offset
            });

            // Add filters (only if not ignoring filters)
            if (!ignoreFilters) {
                if (STATE.filters.month) params.append('month', STATE.filters.month);
                if (STATE.filters.year) params.append('year', STATE.filters.year);
                if (STATE.filters.uploaded_by) params.append('uploaded_by', STATE.filters.uploaded_by);

                // Add status filters (multiple)
                STATE.filters.status.forEach(status => {
                    params.append('status', status);
                });
            }

            const url = `${CONFIG.urls.list}?${params.toString()}`;
            console.log(`[API] Fetching executions${ignoreFilters ? ' (ignoring filters)' : ''}:`, url);

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
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error || 'Failed to fetch executions');
            }

            // Store in cache
            STATE.cache.set(cacheKey, {
                data: data,
                timestamp: Date.now()
            });
            enforceCacheLimit(STATE.cache, STATE.cacheMaxSize);

            console.log('[API] Fetched executions:', data.data.length, '- cached');
            return data;

        } catch (error) {
            console.error('[API Error] fetchExecutions:', error);
            throw error;
        }
    }

    async function fetchExecutionDetails(executionId, forceRefresh = false) {
        // Check cache first (unless force refresh)
        if (!forceRefresh) {
            const cached = STATE.detailsCache.get(executionId);
            if (cached) {
                // Dynamic TTL: 5s for IN_PROGRESS, 1hr for others
                const ttl = cached.data.status === 'IN_PROGRESS' ? 5000 : 3600000;
                if (isCacheValid(cached, ttl)) {
                    console.log(`[API] Using cached details for ${executionId}`);
                    touchCacheEntry(STATE.detailsCache, executionId);
                    return cached.data;
                }
            }
        }

        try {
            const url = CONFIG.urls.details.replace('{execution_id}', executionId);
            console.log('[API] Fetching execution details:', url);

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
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error || 'Failed to fetch execution details');
            }

            // Store in cache
            STATE.detailsCache.set(executionId, {
                data: data.data,
                timestamp: Date.now()
            });
            enforceCacheLimit(STATE.detailsCache, 100); // Keep up to 100 execution details

            console.log('[API] Fetched execution details - cached');
            return data.data;

        } catch (error) {
            console.error('[API Error] fetchExecutionDetails:', error);
            throw error;
        }
    }

    async function fetchKPIs(forceRefresh = false) {
        const cacheKey = getKPICacheKey(STATE.filters);

        // Check cache first (unless force refresh)
        if (!forceRefresh) {
            const cached = STATE.kpiCache.get(cacheKey);
            if (cached && isCacheValid(cached, STATE.kpiCacheTTL)) {
                console.log(`[API] Using cached KPIs for ${cacheKey}`);
                touchCacheEntry(STATE.kpiCache, cacheKey);
                return cached.data;
            }
        }

        try {
            const params = new URLSearchParams();

            // Add filters
            if (STATE.filters.month) params.append('month', STATE.filters.month);
            if (STATE.filters.year) params.append('year', STATE.filters.year);
            if (STATE.filters.uploaded_by) params.append('uploaded_by', STATE.filters.uploaded_by);

            // Add status filters
            STATE.filters.status.forEach(status => {
                params.append('status', status);
            });

            const url = `${CONFIG.urls.kpis}?${params.toString()}`;
            console.log('[API] Fetching KPIs:', url);

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
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error || 'Failed to fetch KPIs');
            }

            // Store in cache
            STATE.kpiCache.set(cacheKey, {
                data: data.data,
                timestamp: Date.now()
            });
            enforceCacheLimit(STATE.kpiCache, 20); // Keep up to 20 KPI combinations

            console.log('[API] Fetched KPIs - cached');
            return data.data;

        } catch (error) {
            console.error('[API Error] fetchKPIs:', error);
            throw error;
        }
    }

    // ========================================================================
    // Hero Card Management
    // ========================================================================

    async function loadLatestExecution() {
        try {
            // Store previous execution ID to detect changes
            const previousExecutionId = STATE.latestExecution?.execution_id;

            // Force refresh to bypass cache and get latest execution
            // Always ignore filters for hero card (show global latest)
            const listResponse = await fetchExecutions(1, 0, true, true);

            if (listResponse.data && listResponse.data.length > 0) {
                let latest = listResponse.data[0];

                // Detect new execution and clear caches
                if (previousExecutionId && latest.execution_id !== previousExecutionId) {
                    console.log(`[Hero] New execution detected: ${previousExecutionId} → ${latest.execution_id}`);
                    clearListAndKpiCaches();
                }

                // If the latest execution is in progress, fetch its full details for real-time updates
                const pollingStatuses = CONFIG.settings.polling_enabled_statuses || ['IN_PROGRESS'];
                if (pollingStatuses.includes(latest.status)) {
                    console.log(`[Hero] Latest execution ${latest.execution_id} is IN_PROGRESS, fetching full details.`);
                    const detailedExecution = await fetchExecutionDetails(latest.execution_id, true); // Force refresh for latest data
                    STATE.latestExecution = detailedExecution;
                } else {
                    STATE.latestExecution = latest;
                }

                updateHeroCard();

                // Start or stop polling based on status
                if (pollingStatuses.includes(STATE.latestExecution.status)) {
                    startPolling();
                } else {
                    stopPolling();
                }
            } else {
                console.warn('[Hero] No executions found');
                STATE.latestExecution = null;
                updateHeroCard();
            }

        } catch (error) {
            console.error('[Hero Error] loadLatestExecution:', error);
            showToast('Failed to load latest execution', 'error');
        }
    }

    function updateHeroCard() {
        const latest = STATE.latestExecution;

        if (!latest) {
            DOM.heroExecId.textContent = 'No executions found';
            DOM.heroStatus.textContent = '-';
            DOM.heroStart.textContent = '-';
            DOM.heroDuration.textContent = '-';
            DOM.heroRecords.textContent = '0';
            DOM.heroSuccessRate.textContent = '0%';
            return;
        }

        // Update content
        DOM.heroExecId.textContent = latest.execution_id;
        DOM.heroStatus.textContent = latest.status.replace('_', ' ');
        DOM.heroStart.textContent = formatRelativeTime(latest.start_time);
        DOM.heroRecords.textContent = formatNumber(latest.records_processed || 0);
        DOM.heroSuccessRate.textContent = Math.round((latest.allocation_success_rate || 0) * 100) + '%';

        // Calculate duration
        let duration = '';
        if (latest.status === 'IN_PROGRESS') {
            const elapsed = Math.floor((Date.now() - new Date(latest.start_time).getTime()) / 1000);
            duration = formatDuration(elapsed);
        } else if (latest.duration_seconds) {
            duration = formatDuration(latest.duration_seconds);
        }
        DOM.heroDuration.textContent = duration || 'N/A';

        // Update styling and animations
        DOM.heroCard.classList.remove('status-success', 'status-failed', 'status-partial', 'status-pending', 'status-in-progress');
        DOM.heroCard.classList.add('transitioning');

        DOM.heroIcon.classList.remove('fa-spinner', 'fa-check-circle', 'fa-times-circle', 'fa-exclamation-triangle', 'fa-clock');
        DOM.heroIcon.classList.remove('status-in-progress', 'status-success', 'status-failed', 'status-partial', 'status-pending');

        const statusMap = {
            'IN_PROGRESS': { card: 'status-in-progress', icon: 'fa-spinner status-in-progress' },
            'SUCCESS': { card: 'status-success', icon: 'fa-check-circle status-success' },
            'FAILED': { card: 'status-failed', icon: 'fa-times-circle status-failed' },
            'PARTIAL_SUCCESS': { card: 'status-partial', icon: 'fa-exclamation-triangle status-partial' },
            'PENDING': { card: 'status-pending', icon: 'fa-clock status-pending' }
        };

        const statusConfig = statusMap[latest.status] || statusMap['PENDING'];
        DOM.heroCard.classList.add(statusConfig.card);
        DOM.heroIcon.className = `fas ${statusConfig.icon}`;

        // Show/hide error
        if (latest.status === 'FAILED' || latest.status === 'PARTIAL_SUCCESS') {
            DOM.heroErrorType.textContent = latest.error_type || 'Unknown error';
            DOM.heroError.classList.remove('hidden');
        } else {
            DOM.heroError.classList.add('hidden');
        }

        // Remove transition class
        setTimeout(() => {
            DOM.heroCard.classList.remove('transitioning');
        }, 600);
    }

    // ========================================================================
    // Polling
    // ========================================================================

    function startPolling() {
        if (STATE.pollingInterval) return; // Already polling

        const interval = CONFIG.settings.hero_refresh_interval || 5000;
        console.log(`[Polling] Started (${interval}ms)`);

        STATE.pollingEnabled = true;
        STATE.pollingInterval = setInterval(async () => {
            if (STATE.pollingEnabled) {
                // loadLatestExecution() forces cache refresh and detects new executions
                await loadLatestExecution();
            }
        }, interval);
    }

    function stopPolling() {
        if (STATE.pollingInterval) {
            console.log('[Polling] Stopped');
            clearInterval(STATE.pollingInterval);
            STATE.pollingInterval = null;
        }
        STATE.pollingEnabled = false;
    }

    // ========================================================================
    // Lazy Loading
    // ========================================================================

    async function loadInitialData() {
        if (STATE.isLoading) return;

        STATE.isLoading = true;
        showLoading();

        try {
            const pageSize = CONFIG.settings.initial_page_size || 100;
            console.log(`[LazyLoad] Loading initial ${pageSize} records`);

            const response = await fetchExecutions(pageSize, 0);

            STATE.allData = response.data || [];
            STATE.totalLoaded = response.data.length;
            STATE.hasMoreData = response.pagination.has_more;
            STATE.currentPage = 1;

            console.log(`[LazyLoad] Loaded ${STATE.totalLoaded} records, hasMore: ${STATE.hasMoreData}`);

            renderTable();
            showToast(`Loaded ${STATE.totalLoaded} executions`, 'success');

        } catch (error) {
            console.error('[LazyLoad Error] loadInitialData:', error);
            showToast('Failed to load executions: ' + error.message, 'error');

            // Show empty state
            DOM.tableBody.innerHTML = '<tr><td colspan="8" class="text-center py-4">Failed to load data</td></tr>';

        } finally {
            STATE.isLoading = false;
            hideLoading();
        }
    }

    async function loadMoreData() {
        if (STATE.isLoading || !STATE.hasMoreData) return;

        STATE.isLoading = true;
        showLoading();

        try {
            const pageSize = CONFIG.settings.lazy_load_page_size || 100;
            const offset = STATE.totalLoaded;

            console.log(`[LazyLoad] Loading next ${pageSize} records from offset ${offset}`);

            const response = await fetchExecutions(pageSize, offset);

            STATE.allData = [...STATE.allData, ...response.data];
            STATE.totalLoaded += response.data.length;
            STATE.hasMoreData = response.pagination.has_more;

            console.log(`[LazyLoad] Total loaded: ${STATE.totalLoaded}, hasMore: ${STATE.hasMoreData}`);

            renderTable();
            showToast(`Loaded ${response.data.length} more executions`, 'info');

        } catch (error) {
            console.error('[LazyLoad Error] loadMoreData:', error);
            showToast('Failed to load more data: ' + error.message, 'error');

        } finally {
            STATE.isLoading = false;
            hideLoading();
        }
    }

    function checkLazyLoad() {
        const triggerPage = CONFIG.settings.lazy_load_trigger_page || 9;
        const requiredRecords = STATE.currentPage * STATE.itemsPerPage;

        // Check if we're at the trigger page and need more data
        if (STATE.currentPage >= triggerPage && requiredRecords > STATE.totalLoaded && STATE.hasMoreData) {
            console.log(`[LazyLoad] Trigger at page ${STATE.currentPage}`);
            loadMoreData();
        }
    }

    // ========================================================================
    // Table Rendering
    // ========================================================================

    function renderTable() {
        const start = (STATE.currentPage - 1) * STATE.itemsPerPage;
        const end = start + STATE.itemsPerPage;
        const pageData = STATE.allData.slice(start, end);

        if (pageData.length === 0) {
            DOM.tableBody.innerHTML = '<tr><td colspan="8" class="text-center py-4">No executions found</td></tr>';
            updatePaginationControls();
            return;
        }

        let html = '';
        pageData.forEach(exec => {
            const statusClass = exec.status.toLowerCase().replace('_', '-');
            const statusText = exec.status.replace('_', ' ');
            const duration = exec.duration_seconds ? formatDuration(exec.duration_seconds) : 'N/A';
            const successRate = Math.round((exec.allocation_success_rate || 0) * 100) + '%';

            html += `
                <tr onclick="openDrawer('${exec.execution_id}')">
                    <td><span class="execution-id">${exec.execution_id.substring(0, 16)}...</span></td>
                    <td>${exec.month}</td>
                    <td>${exec.year}</td>
                    <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                    <td>${exec.uploaded_by}</td>
                    <td>${formatDateTime(exec.start_time)}</td>
                    <td>${duration}</td>
                    <td>${successRate}</td>
                </tr>
            `;
        });

        DOM.tableBody.innerHTML = html;
        updatePaginationControls();
    }

    function updatePaginationControls() {
        const start = (STATE.currentPage - 1) * STATE.itemsPerPage + 1;
        const end = Math.min(STATE.currentPage * STATE.itemsPerPage, STATE.allData.length);
        const total = STATE.allData.length;

        DOM.paginationInfo.textContent = `Showing ${start}-${end} of ${total} executions`;

        const totalPages = Math.ceil(total / STATE.itemsPerPage);
        DOM.prevBtn.disabled = STATE.currentPage === 1;
        DOM.nextBtn.disabled = STATE.currentPage >= totalPages;
    }

    // ========================================================================
    // KPI Updates
    // ========================================================================

    async function updateKPIs() {
        try {
            const kpis = await fetchKPIs();

            DOM.kpiTotal.textContent = kpis.total_executions || 0;
            DOM.kpiSuccessRate.textContent = Math.round((kpis.success_rate || 0) * 100) + '%';
            DOM.kpiAvgDuration.textContent = formatDuration(kpis.average_duration_seconds || 0);
            DOM.kpiFailed.textContent = kpis.failed_count || 0;

        } catch (error) {
            console.error('[KPI Error] updateKPIs:', error);
            showToast('Failed to load KPIs', 'error');
        }
    }

    // ========================================================================
    // Filters
    // ========================================================================

    function applyFilters() {
        // Gather filter values
        STATE.filters.month = DOM.monthFilter.value || null;
        STATE.filters.year = DOM.yearFilter.value || null;
        STATE.filters.uploaded_by = DOM.userFilter.value.trim() || null;

        // Gather checked statuses
        STATE.filters.status = [];
        DOM.statusCheckboxes.forEach(checkbox => {
            if (checkbox.checked) {
                STATE.filters.status.push(checkbox.value);
            }
        });

        console.log('[Filters] Applied:', STATE.filters);

        // Clear list and KPI caches (preserve details cache)
        clearListAndKpiCaches();

        // Reset pagination state
        STATE.allData = [];
        STATE.totalLoaded = 0;
        STATE.hasMoreData = true;
        STATE.currentPage = 1;

        // Reload all data (hero card always shows global latest, ignoring filters)
        loadLatestExecution();  // Hero card (global, no filters)
        loadInitialData();      // Table (respects filters)
        updateKPIs();          // KPIs (respects filters)

        showToast('Filters applied', 'info');
    }

    // Make applyFilters global
    window.applyFilters = applyFilters;

    // ========================================================================
    // Pagination
    // ========================================================================

    function previousPage() {
        if (STATE.currentPage > 1) {
            STATE.currentPage--;
            renderTable();
            checkLazyLoad();
        }
    }

    function nextPage() {
        const totalPages = Math.ceil(STATE.allData.length / STATE.itemsPerPage);
        if (STATE.currentPage < totalPages) {
            STATE.currentPage++;
            renderTable();
            checkLazyLoad();
        }
    }

    // Make pagination functions global
    window.previousPage = previousPage;
    window.nextPage = nextPage;

    // ========================================================================
    // Drawer Management
    // ========================================================================

    async function openDrawer(executionId) {
        console.log('[Drawer] Opening for:', executionId);

        try {
            showLoading();
            const execution = await fetchExecutionDetails(executionId);
            STATE.selectedExecution = execution;

            populateDrawer(execution);

            // Show drawer
            document.body.classList.add('drawer-open');
            DOM.drawerOverlay.classList.add('show');
            DOM.sideDrawer.classList.add('show');

        } catch (error) {
            console.error('[Drawer Error] openDrawer:', error);
            showToast('Failed to load execution details', 'error');
        } finally {
            hideLoading();
        }
    }

    function populateDrawer(exec) {
        // Header
        DOM.drawerExecId.textContent = `ID: ${exec.execution_id}`;

        // Overview
        document.getElementById('detail-status').textContent = exec.status.replace('_', ' ');
        document.getElementById('detail-month-year').textContent = `${exec.month} ${exec.year}`;
        document.getElementById('detail-start').textContent = formatDateTime(exec.start_time);
        document.getElementById('detail-end').textContent = exec.end_time ? formatDateTime(exec.end_time) : 'In Progress';
        document.getElementById('detail-duration').textContent = exec.duration_seconds ? formatDuration(exec.duration_seconds) : 'N/A';
        document.getElementById('detail-user').textContent = exec.uploaded_by;

        // Error section
        const errorSection = document.getElementById('detail-error-section');
        if (exec.status === 'FAILED' || exec.status === 'PARTIAL_SUCCESS') {
            const errorHTML = `
                <div class="error-box">
                    <h6><i class="fas fa-exclamation-circle me-2"></i>Error Details</h6>
                    <div class="error-message"><strong>Type:</strong> ${exec.error_type || 'N/A'}</div>
                    ${exec.error_message ? `<div class="error-message"><strong>Message:</strong> ${exec.error_message}</div>` : ''}
                    ${exec.stack_trace ? `
                        <details>
                            <summary style="cursor: pointer; font-weight: 600; margin-top: 10px;">Stack Trace</summary>
                            <div class="stack-trace">${exec.stack_trace}</div>
                        </details>
                    ` : ''}
                </div>
            `;
            errorSection.innerHTML = errorHTML;
            errorSection.classList.remove('hidden');
        } else {
            errorSection.classList.add('hidden');
        }

        // Files section
        const filesHTML = `
            <div class="file-tag">
                <i class="fas fa-file-excel"></i>
                <div>
                    <div><strong>Forecast File:</strong></div>
                    <div>${exec.forecast_filename || 'N/A'}</div>
                </div>
            </div>
            <div class="file-tag">
                <i class="fas fa-file-excel"></i>
                <div>
                    <div><strong>Roster File:</strong></div>
                    <div>${exec.roster_filename || 'N/A'}</div>
                </div>
            </div>
            ${exec.roster_was_fallback ? `
                <div class="alert alert-warning" style="margin-top: 10px;">
                    <i class="fas fa-info-circle me-2"></i>
                    <strong>Fallback Used:</strong> Roster for ${exec.roster_month_used} ${exec.roster_year_used} was used
                </div>
            ` : ''}
        `;
        document.getElementById('files-content').innerHTML = filesHTML;

        // Config section
        const configHTML = renderConfigAccordion(exec.config_snapshot);
        document.getElementById('config-content').innerHTML = configHTML;

        // Stats section
        const statsHTML = `
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">Records Processed</span>
                    <span class="info-value">${formatNumber(exec.records_processed || 0)}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Records Failed</span>
                    <span class="info-value">${formatNumber(exec.records_failed || 0)}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Success Rate</span>
                    <span class="info-value">${Math.round((exec.allocation_success_rate || 0) * 100)}%</span>
                </div>
            </div>
            <div style="margin-top: 15px;">
                <div class="progress" style="height: 25px;">
                    <div class="progress-bar bg-success" style="width: ${(exec.allocation_success_rate || 0) * 100}%">
                        ${Math.round((exec.allocation_success_rate || 0) * 100)}%
                    </div>
                </div>
            </div>
        `;
        document.getElementById('stats-content').innerHTML = statsHTML;

        // Download section visibility
        const downloadSection = document.getElementById('drawer-section-downloads');
        if (exec.status === 'SUCCESS') {
            downloadSection.classList.remove('download-disabled');
        } else {
            downloadSection.classList.add('download-disabled');
        }
    }

    function renderConfigAccordion(configSnapshot) {
        if (!configSnapshot || !configSnapshot.month_config) return '<p class="text-muted">No configuration data available</p>';

        let html = '<div class="config-accordion">';
        let index = 0;

        for (const [monthYear, configs] of Object.entries(configSnapshot.month_config)) {
            const isFirst = index === 0;
            const accordionId = `config-accordion-${index}`;

            html += `
                <div class="drawer-section" style="margin-bottom: 10px;">
                    <div class="section-header" onclick="toggleConfigMonth('${accordionId}')">
                        <h6 style="margin: 0;">${monthYear}</h6>
                        <i class="fas fa-chevron-down section-toggle ${isFirst ? 'expanded' : ''}" id="toggle-${accordionId}"></i>
                    </div>
                    <div class="section-body ${isFirst ? 'expanded' : ''}" id="section-${accordionId}">
                        <table class="config-table">
                            <thead>
                                <tr>
                                    <th>Work Type</th>
                                    <th>Working Days</th>
                                    <th>Occupancy</th>
                                    <th>Shrinkage</th>
                                    <th>Work Hours</th>
                                </tr>
                            </thead>
                            <tbody>
            `;

            for (const [workType, config] of Object.entries(configs)) {
                html += `
                    <tr>
                        <td><strong>${workType}</strong></td>
                        <td>${config.working_days}</td>
                        <td>${(config.occupancy * 100).toFixed(0)}%</td>
                        <td>${(config.shrinkage * 100).toFixed(0)}%</td>
                        <td>${config.work_hours}</td>
                    </tr>
                `;
            }

            html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
            index++;
        }

        html += '</div>';
        return html;
    }

    function closeDrawer() {
        document.body.classList.remove('drawer-open');
        DOM.drawerOverlay.classList.remove('show');
        DOM.sideDrawer.classList.remove('show');
    }

    function toggleSection(sectionId) {
        const section = document.getElementById(`section-${sectionId}`);
        const toggle = document.getElementById(`toggle-${sectionId}`);

        section.classList.toggle('expanded');
        toggle.classList.toggle('expanded');
    }

    function toggleConfigMonth(monthId) {
        const section = document.getElementById(`section-${monthId}`);
        const toggle = document.getElementById(`toggle-${monthId}`);
        section.classList.toggle('expanded');
        toggle.classList.toggle('expanded');
    }

    // Make drawer functions global
    window.openDrawer = openDrawer;
    window.closeDrawer = closeDrawer;
    window.toggleSection = toggleSection;
    window.toggleConfigMonth = toggleConfigMonth;

    // ========================================================================
    // Download Management
    // ========================================================================

    function toggleDownloadItem(itemId) {
        const item = document.getElementById(`download-${itemId}`);
        if (!item) return;

        // Close other items
        document.querySelectorAll('.download-item').forEach(el => {
            if (el !== item) {
                el.classList.remove('expanded');
            }
        });

        // Toggle current item
        item.classList.toggle('expanded');
    }

    function downloadReport(reportType, event) {
        if (event) event.stopPropagation();

        if (!STATE.selectedExecution) {
            showToast('No execution selected', 'error');
            return;
        }

        try {
            const url = CONFIG.urls.download
                .replace('{execution_id}', STATE.selectedExecution.execution_id)
                .replace('{report_type}', reportType);

            console.log('[Download] Starting:', reportType, url);

            // Trigger download
            window.location.href = url;

            showToast('Download started!', 'success');

        } catch (error) {
            console.error('[Download Error]:', error);
            showToast('Download failed: ' + error.message, 'error');
        }
    }

    // Make download functions global
    window.toggleDownloadItem = toggleDownloadItem;
    window.downloadReport = downloadReport;

    // ========================================================================
    // Copy to Clipboard
    // ========================================================================

    function copyExecutionId(elementId) {
        const element = document.getElementById(elementId);
        if (!element) return;

        const text = element.textContent;

        navigator.clipboard.writeText(text).then(() => {
            showToast('Execution ID copied to clipboard!', 'success');
        }).catch(() => {
            showToast('Failed to copy to clipboard', 'error');
        });
    }

    // Make copy function global
    window.copyExecutionId = copyExecutionId;

    // ========================================================================
    // Utility Functions
    // ========================================================================

    function formatNumber(num) {
        if (num === null || num === undefined) return '0';
        return num.toLocaleString();
    }

    function formatDuration(seconds) {
        if (!seconds || seconds < 0) return 'N/A';

        seconds = Math.floor(seconds);
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

        if (hours > 0) {
            return `${hours}h ${minutes}m ${secs}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    }

    function formatDateTime(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function formatRelativeTime(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000);

        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)} minutes ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
        if (diff < 604800) return `${Math.floor(diff / 86400)} days ago`;
        return formatDateTime(dateString);
    }

    // ========================================================================
    // Initialization
    // ========================================================================

    function init() {
        console.log('[Init] Execution Monitoring starting...');
        console.log('[Init] Config:', CONFIG);

        // Clear list and KPI caches on page load (preserve details cache)
        clearListAndKpiCaches();

        // Cache DOM elements
        cacheDOMElements();

        // Load initial data
        loadLatestExecution();
        loadInitialData();
        updateKPIs();

        console.log('[Init] Execution Monitoring initialized successfully');
    }

    // ========================================================================
    // Debug API (for console debugging)
    // ========================================================================

    window.ExecutionMonitoringDebug = {
        getState: () => STATE,
        getConfig: () => CONFIG,
        getDOM: () => DOM,
        getCache: () => {
            const cacheEntries = [];
            STATE.cache.forEach((value, key) => {
                cacheEntries.push({
                    type: 'executions',
                    key: key,
                    timestamp: value.timestamp,
                    age: Math.round((Date.now() - value.timestamp) / 1000) + 's',
                    isValid: isCacheValid(value, STATE.cacheTTL)
                });
            });
            STATE.kpiCache.forEach((value, key) => {
                cacheEntries.push({
                    type: 'kpi',
                    key: key,
                    timestamp: value.timestamp,
                    age: Math.round((Date.now() - value.timestamp) / 1000) + 's',
                    isValid: isCacheValid(value, STATE.kpiCacheTTL)
                });
            });
            STATE.detailsCache.forEach((value, key) => {
                const ttl = value.data.status === 'IN_PROGRESS' ? 5000 : 3600000;
                cacheEntries.push({
                    type: 'details',
                    key: key,
                    status: value.data.status,
                    timestamp: value.timestamp,
                    age: Math.round((Date.now() - value.timestamp) / 1000) + 's',
                    isValid: isCacheValid(value, ttl)
                });
            });
            return cacheEntries;
        },
        getCacheStats: () => ({
            executions: STATE.cache.size,
            kpi: STATE.kpiCache.size,
            details: STATE.detailsCache.size,
            total: STATE.cache.size + STATE.kpiCache.size + STATE.detailsCache.size
        }),
        clearCache: clearAllCaches,
        reloadData: () => {
            clearAllCaches();
            loadLatestExecution();
            loadInitialData();
            updateKPIs();
        },
        stopPolling: stopPolling,
        startPolling: startPolling
    };

    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();