/**
 * Data View - JavaScript with Persistent Caching & Cascading Dropdowns
 *
 * Features:
 * - Cascading filters for forecast (Year → Month → Platform → Market → Locality → Worktype)
 * - Dual-layer caching system:
 *   1. In-memory cache (fast, cleared on page refresh)
 *   2. SessionStorage cache (persists across page refreshes until browser session ends)
 * - Dynamic dropdown population via AJAX with loading indicators
 * - URL parameter synchronization and auto-restoration
 * - Smart cascade restoration: when switching data types or reloading page,
 *   previously fetched dropdown options are restored from sessionStorage
 *
 * Performance benefits:
 * - No re-fetching when checking multiple worktypes with same filters
 * - Instant dropdown population on page refresh from sessionStorage
 * - Reduced server load through persistent client-side caching
 */

(function() {
    'use strict';

    // ============================================================================
    // CONFIGURATION & STATE
    // ============================================================================

    const STATE = {
        cache: new Map(),
        cacheMaxSize: 50,
        cacheTTL: 300000,  // 5 minutes
        sessionStoragePrefix: 'dataview_dropdown_',
        currentFilters: {
            year: null,
            month: null,
            platform: null,
            market: null,
            locality: null,
            worktype: null
        }
    };

    // Map data_type to visible containers and cascade requirements
    const dataTypeDropdownMap = {
        roster:              { show: ['year', 'month'], hide: ['platform', 'market', 'locality', 'worktype', 'summary_type'], cascade: true, cascadeLevel: 'month' },
        prod_team_roster:    { show: ['year', 'month'], hide: ['platform', 'market', 'locality', 'worktype', 'summary_type'], cascade: true, cascadeLevel: 'month' },
        summary:             { show: ['year', 'month', 'summary_type'], hide: ['platform', 'market', 'locality', 'worktype'], cascade: true, cascadeLevel: 'month' },
        forecast:            { show: ['year', 'month', 'platform', 'market', 'locality', 'worktype'], hide: ['summary_type'], cascade: true },
        actuals:             { show: ['year', 'month', 'platform', 'market', 'locality', 'worktype'], hide: ['summary_type'] }
    };

    // ============================================================================
    // CACHING UTILITIES
    // ============================================================================

    function getCacheKey(endpoint, params) {
        const sortedParams = Object.keys(params).sort().map(k => `${k}=${params[k]}`).join('&');
        return `${endpoint}?${sortedParams}`;
    }

    function isCacheValid(cachedEntry) {
        if (!cachedEntry) return false;
        return (Date.now() - cachedEntry.timestamp) < STATE.cacheTTL;
    }

    function enforceCacheLimit() {
        if (STATE.cache.size > STATE.cacheMaxSize) {
            let oldestKey = null;
            let oldestTime = Date.now();

            STATE.cache.forEach((value, key) => {
                if (value.timestamp < oldestTime) {
                    oldestTime = value.timestamp;
                    oldestKey = key;
                }
            });

            if (oldestKey) {
                STATE.cache.delete(oldestKey);
                console.log(`Cache evicted: ${oldestKey}`);
            }
        }
    }

    // ============================================================================
    // SESSION STORAGE PERSISTENCE
    // ============================================================================

    function getFromSessionStorage(cacheKey) {
        try {
            const storageKey = STATE.sessionStoragePrefix + cacheKey;
            const stored = sessionStorage.getItem(storageKey);

            if (!stored) return null;

            const parsed = JSON.parse(stored);

            // Session storage doesn't expire like in-memory cache
            // Data persists until browser session ends or server restart
            return parsed.data;
        } catch (error) {
            console.warn('Error reading from sessionStorage:', error);
            return null;
        }
    }

    function saveToSessionStorage(cacheKey, data) {
        try {
            const storageKey = STATE.sessionStoragePrefix + cacheKey;
            const toStore = {
                data: data,
                timestamp: Date.now()
            };
            sessionStorage.setItem(storageKey, JSON.stringify(toStore));
            console.log(`Saved to sessionStorage: ${cacheKey}`);
        } catch (error) {
            // Handle quota exceeded errors gracefully
            if (error.name === 'QuotaExceededError') {
                console.warn('SessionStorage quota exceeded, clearing old entries');
                clearOldestSessionStorageEntries();
                // Retry once after cleanup
                try {
                    const storageKey = STATE.sessionStoragePrefix + cacheKey;
                    const toStore = {
                        data: data,
                        timestamp: Date.now()
                    };
                    sessionStorage.setItem(storageKey, JSON.stringify(toStore));
                } catch (retryError) {
                    console.error('Failed to save to sessionStorage after cleanup:', retryError);
                }
            } else {
                console.error('Error saving to sessionStorage:', error);
            }
        }
    }

    function clearOldestSessionStorageEntries() {
        try {
            const entries = [];
            const prefix = STATE.sessionStoragePrefix;

            // Collect all our entries
            for (let i = 0; i < sessionStorage.length; i++) {
                const key = sessionStorage.key(i);
                if (key && key.startsWith(prefix)) {
                    try {
                        const value = JSON.parse(sessionStorage.getItem(key));
                        entries.push({ key, timestamp: value.timestamp || 0 });
                    } catch (e) {
                        // Invalid JSON, safe to remove
                        entries.push({ key, timestamp: 0 });
                    }
                }
            }

            // Sort by timestamp (oldest first)
            entries.sort((a, b) => a.timestamp - b.timestamp);

            // Remove oldest 25% of entries
            const toRemove = Math.max(1, Math.floor(entries.length * 0.25));
            for (let i = 0; i < toRemove; i++) {
                sessionStorage.removeItem(entries[i].key);
                console.log(`Removed old entry: ${entries[i].key}`);
            }
        } catch (error) {
            console.error('Error clearing sessionStorage entries:', error);
        }
    }

    // ============================================================================
    // AJAX DATA FETCHING
    // ============================================================================

    async function fetchCascadeData(endpoint, params = {}) {
        const cacheKey = getCacheKey(endpoint, params);

        // 1. Check in-memory cache first (fastest)
        const cached = STATE.cache.get(cacheKey);
        if (cached && isCacheValid(cached)) {
            console.log(`Memory cache hit: ${cacheKey}`);
            return cached.data;
        }

        // 2. Check sessionStorage (persists across page refreshes)
        const sessionData = getFromSessionStorage(cacheKey);
        if (sessionData) {
            console.log(`SessionStorage hit: ${cacheKey}`);
            // Also store in memory cache for faster subsequent access
            STATE.cache.set(cacheKey, {
                data: sessionData,
                timestamp: Date.now()
            });
            enforceCacheLimit();
            return sessionData;
        }

        // 3. Fetch from API (no cache available)
        try {
            const queryString = new URLSearchParams(params).toString();
            const url = `${endpoint}?${queryString}`;

            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error || 'API returned error');
            }

            // Store in both memory cache and sessionStorage
            STATE.cache.set(cacheKey, {
                data: data,
                timestamp: Date.now()
            });
            enforceCacheLimit();

            // Persist to sessionStorage for cross-page-load persistence
            saveToSessionStorage(cacheKey, data);

            console.log(`Fetched and cached: ${cacheKey}`);
            return data;

        } catch (error) {
            console.error(`Error fetching ${endpoint}:`, error);
            throw error;
        }
    }

    // ============================================================================
    // DROPDOWN POPULATION
    // ============================================================================

    function populateDropdown(selectElement, options, placeholder = 'Select') {
        selectElement.empty();
        selectElement.append(`<option value="select">${placeholder}</option>`);

        options.forEach(option => {
            selectElement.append(`<option value="${option.value}">${option.display}</option>`);
        });
    }

    function disableDropdown(selectElement, reset = true) {
        if (reset) {
            selectElement.val('select');
        }
        selectElement.prop('disabled', true);
    }

    function enableDropdown(selectElement) {
        selectElement.prop('disabled', false);
    }

    function showLoadingState(wrapperId) {
        const wrapper = document.getElementById(wrapperId);
        if (wrapper) {
            wrapper.classList.add('loading');
        }
    }

    function hideLoadingState(wrapperId) {
        const wrapper = document.getElementById(wrapperId);
        if (wrapper) {
            wrapper.classList.remove('loading');
        }
    }

    // ============================================================================
    // CASCADING LOGIC FOR FORECAST
    // ============================================================================

    async function handleYearChange(yearValue, autoTriggerNext = false) {
        const monthSelect = $('select[name="month"]');
        const platformSelect = $('select[name="platform"]');
        const marketSelect = $('select[name="market"]');
        const localitySelect = $('select[name="locality"]');
        const worktypeSelect = $('select[name="worktype"]');

        if (!yearValue || yearValue === 'select') {
            disableDropdown(monthSelect);
            disableDropdown(platformSelect);
            disableDropdown(marketSelect);
            disableDropdown(localitySelect);
            disableDropdown(worktypeSelect);
            STATE.currentFilters.year = null;
            return;
        }

        STATE.currentFilters.year = yearValue;

        // Show loading state
        showLoadingState('month-wrapper');

        // Disable dependent dropdowns
        disableDropdown(platformSelect);
        disableDropdown(marketSelect);
        disableDropdown(localitySelect);
        disableDropdown(worktypeSelect);

        try {
            // Fetch months for selected year
            const data = await fetchCascadeData(window.DATA_VIEW_URLS.forecastMonths, { year: yearValue });

            populateDropdown(monthSelect, data.options, 'Select Month');
            enableDropdown(monthSelect);
            hideLoadingState('month-wrapper');

            // Auto-restore from URL if requested
            if (autoTriggerNext) {
                const urlParams = new URLSearchParams(window.location.search);
                const monthValue = urlParams.get('month');
                if (monthValue && monthValue !== 'select') {
                    monthSelect.val(monthValue);
                    // Trigger next cascade step
                    await handleMonthChange(monthValue, true);
                }
            }

        } catch (error) {
            console.error('Error loading months:', error);
            populateDropdown(monthSelect, [], 'Error loading months');
            disableDropdown(monthSelect);
            hideLoadingState('month-wrapper');
        }
    }

    async function handleYearChangeForRosterSummary(yearValue, autoTriggerNext = false) {
        const monthSelect = $('select[name="month"]');

        if (!yearValue || yearValue === 'select') {
            disableDropdown(monthSelect);
            return;
        }

        // Show loading state
        showLoadingState('month-wrapper');

        try {
            // Fetch months using same endpoint as forecast
            const data = await fetchCascadeData(window.DATA_VIEW_URLS.forecastMonths, { year: yearValue });

            if (data.options && data.options.length > 0) {
                populateDropdown(monthSelect, data.options, 'Select Month');
                enableDropdown(monthSelect);
            } else {
                // Empty state: no months available
                populateDropdown(monthSelect, [], 'No months available');
                disableDropdown(monthSelect, false);
            }

            hideLoadingState('month-wrapper');

            // Auto-restore from URL if requested
            if (autoTriggerNext) {
                const urlParams = new URLSearchParams(window.location.search);
                const monthValue = urlParams.get('month');
                if (monthValue && monthValue !== 'select') {
                    monthSelect.val(monthValue);
                }
            }

        } catch (error) {
            console.error('Error loading months for roster/summary:', error);
            populateDropdown(monthSelect, [], 'Error loading months');
            disableDropdown(monthSelect);
            hideLoadingState('month-wrapper');
        }
    }

    async function handleMonthChange(monthValue, autoTriggerNext = false) {
        const platformSelect = $('select[name="platform"]');
        const marketSelect = $('select[name="market"]');
        const localitySelect = $('select[name="locality"]');
        const worktypeSelect = $('select[name="worktype"]');

        if (!monthValue || monthValue === 'select' || !STATE.currentFilters.year) {
            disableDropdown(platformSelect);
            disableDropdown(marketSelect);
            disableDropdown(localitySelect);
            disableDropdown(worktypeSelect);
            STATE.currentFilters.month = null;
            return;
        }

        STATE.currentFilters.month = monthValue;

        // Show loading state
        showLoadingState('platform-wrapper');

        // Disable dependent dropdowns
        disableDropdown(marketSelect);
        disableDropdown(localitySelect);
        disableDropdown(worktypeSelect);

        try {
            // Fetch platforms for selected year/month
            const data = await fetchCascadeData(window.DATA_VIEW_URLS.forecastPlatforms, {
                year: STATE.currentFilters.year,
                month: monthValue
            });

            populateDropdown(platformSelect, data.options, 'Select Platform');
            enableDropdown(platformSelect);
            hideLoadingState('platform-wrapper');

            // Auto-restore from URL if requested
            if (autoTriggerNext) {
                const urlParams = new URLSearchParams(window.location.search);
                const platformValue = urlParams.get('platform');
                if (platformValue && platformValue !== 'select') {
                    platformSelect.val(platformValue);
                    await handlePlatformChange(platformValue, true);
                }
            }

        } catch (error) {
            console.error('Error loading platforms:', error);
            populateDropdown(platformSelect, [], 'Error loading platforms');
            disableDropdown(platformSelect);
            hideLoadingState('platform-wrapper');
        }
    }

    async function handlePlatformChange(platformValue, autoTriggerNext = false) {
        const marketSelect = $('select[name="market"]');
        const localitySelect = $('select[name="locality"]');
        const worktypeSelect = $('select[name="worktype"]');

        if (!platformValue || platformValue === 'select' || !STATE.currentFilters.month) {
            disableDropdown(marketSelect);
            disableDropdown(localitySelect);
            disableDropdown(worktypeSelect);
            STATE.currentFilters.platform = null;
            return;
        }

        STATE.currentFilters.platform = platformValue;

        // Show loading state
        showLoadingState('market-wrapper');

        // Disable dependent dropdowns
        disableDropdown(localitySelect);
        disableDropdown(worktypeSelect);

        try {
            // Fetch markets for selected platform
            const data = await fetchCascadeData(window.DATA_VIEW_URLS.forecastMarkets, {
                year: STATE.currentFilters.year,
                month: STATE.currentFilters.month,
                platform: platformValue
            });

            populateDropdown(marketSelect, data.options, 'Select Market');
            enableDropdown(marketSelect);
            hideLoadingState('market-wrapper');

            // Auto-restore from URL if requested
            if (autoTriggerNext) {
                const urlParams = new URLSearchParams(window.location.search);
                const marketValue = urlParams.get('market');
                if (marketValue && marketValue !== 'select') {
                    marketSelect.val(marketValue);
                    await handleMarketChange(marketValue, true);
                }
            }

        } catch (error) {
            console.error('Error loading markets:', error);
            populateDropdown(marketSelect, [], 'Error loading markets');
            disableDropdown(marketSelect);
            hideLoadingState('market-wrapper');
        }
    }

    async function handleMarketChange(marketValue, autoTriggerNext = false) {
        const localitySelect = $('select[name="locality"]');
        const worktypeSelect = $('select[name="worktype"]');

        if (!marketValue || marketValue === 'select' || !STATE.currentFilters.platform) {
            disableDropdown(localitySelect);
            disableDropdown(worktypeSelect);
            STATE.currentFilters.market = null;
            return;
        }

        STATE.currentFilters.market = marketValue;

        // Show loading state
        showLoadingState('locality-wrapper');
        disableDropdown(worktypeSelect);

        try {
            // Fetch localities for selected platform/market (optional field)
            const data = await fetchCascadeData(window.DATA_VIEW_URLS.forecastLocalities, {
                year: STATE.currentFilters.year,
                month: STATE.currentFilters.month,
                platform: STATE.currentFilters.platform,
                market: marketValue
            });

            populateDropdown(localitySelect, data.options);
            enableDropdown(localitySelect);
            hideLoadingState('locality-wrapper');

            // Auto-restore from URL if requested
            if (autoTriggerNext) {
                const urlParams = new URLSearchParams(window.location.search);
                const localityValue = urlParams.get('locality');
                // Locality is optional, so trigger worktype fetch either way
                if (localityValue && localityValue !== 'select') {
                    localitySelect.val(localityValue);
                    await handleLocalityChange(localityValue, true);
                } else {
                    // No locality in URL, fetch worktypes for "All Localities"
                    await handleLocalityChange('', true);
                }
            } else {
                // Auto-fetch worktypes for "All Localities" (original behavior)
                handleLocalityChange('');
            }

        } catch (error) {
            console.error('Error loading localities:', error);
            populateDropdown(localitySelect, [], 'Error loading localities');
            disableDropdown(localitySelect);
            disableDropdown(worktypeSelect);
            hideLoadingState('locality-wrapper');
        }
    }

    async function handleLocalityChange(localityValue, autoTriggerNext = false) {
        const worktypeSelect = $('select[name="worktype"]');

        if (!STATE.currentFilters.market) {
            disableDropdown(worktypeSelect);
            STATE.currentFilters.locality = null;
            return;
        }

        // Locality is optional - empty string is valid
        STATE.currentFilters.locality = localityValue || '';

        // Show loading state
        showLoadingState('worktype-wrapper');

        try {
            // Fetch worktypes for selected filters
            const params = {
                year: STATE.currentFilters.year,
                month: STATE.currentFilters.month,
                platform: STATE.currentFilters.platform,
                market: STATE.currentFilters.market
            };

            if (localityValue && localityValue !== 'select') {
                params.locality = localityValue;
            }

            const data = await fetchCascadeData(window.DATA_VIEW_URLS.forecastWorktypes, params);

            populateDropdown(worktypeSelect, data.options, 'Select Worktype');
            enableDropdown(worktypeSelect);
            hideLoadingState('worktype-wrapper');

            // Auto-restore from URL if requested
            if (autoTriggerNext) {
                const urlParams = new URLSearchParams(window.location.search);
                const worktypeValue = urlParams.get('worktype');
                if (worktypeValue && worktypeValue !== 'select') {
                    worktypeSelect.val(worktypeValue);
                    // Worktype is the final dropdown, no more cascade
                }
            }

        } catch (error) {
            console.error('Error loading worktypes:', error);
            populateDropdown(worktypeSelect, [], 'Error loading worktypes');
            disableDropdown(worktypeSelect);
            hideLoadingState('worktype-wrapper');
        }
    }

    // ============================================================================
    // DROPDOWN VISIBILITY MANAGEMENT
    // ============================================================================

    function updateDropdownVisibilityByType(dataType) {
        const containers = {
            year: document.getElementById("year-container"),
            month: document.getElementById("month-container"),
            platform: document.getElementById("platform-container"),
            market: document.getElementById("market-container"),
            locality: document.getElementById("locality-container"),
            worktype: document.getElementById("worktype-container"),
            summary_type: document.getElementById("summary-type-container"),
        };

        // Hide all containers first
        Object.values(containers).forEach(c => c.style.display = "none");

        // Show containers for selected data type
        if (dataTypeDropdownMap[dataType]) {
            dataTypeDropdownMap[dataType].show.forEach(key => {
                if (containers[key]) {
                    containers[key].style.display = "";
                }
            });

            // Restore values from URL for visible dropdowns
            restoreVisibleDropdownsFromURL(dataType);

            // Initialize cascade based on data type
            if (dataType === 'forecast' && dataTypeDropdownMap[dataType].cascade) {
                initializeForecastCascade();
            } else if ((dataType === 'roster' || dataType === 'prod_team_roster' || dataType === 'summary') && dataTypeDropdownMap[dataType].cascade) {
                // Initialize roster/summary cascade (year→month only)
                initializeRosterSummaryCascade();
            } else {
                // For non-cascade types (actuals), enable all visible dropdowns
                enableNonCascadeDropdowns(dataType);
            }
        }
    }

    function restoreVisibleDropdownsFromURL(dataType) {
        const urlParams = new URLSearchParams(window.location.search);
        const visibleDropdowns = dataTypeDropdownMap[dataType].show;

        visibleDropdowns.forEach(dropdownName => {
            const select = document.querySelector(`select[name="${dropdownName}"]`);
            if (select) {
                const value = urlParams.get(dropdownName);
                if (value && value !== 'select') {
                    select.value = value;
                } else {
                    select.value = 'select';
                }
            }
        });
    }

    function enableNonCascadeDropdowns(dataType) {
        // Only for truly non-cascade types (actuals)
        // Roster, prod_team_roster, and summary now have cascade (year→month), so exclude them
        if (dataType !== 'forecast' && dataType !== 'roster' && dataType !== 'prod_team_roster' && dataType !== 'summary') {
            const visibleDropdowns = dataTypeDropdownMap[dataType].show;
            visibleDropdowns.forEach(dropdownName => {
                const select = $(`select[name="${dropdownName}"]`);
                if (select.length) {
                    enableDropdown(select);
                }
            });
        }
    }

    function initializeForecastCascade() {
        // Disable all dependent dropdowns initially
        const yearValue = $('select[name="year"]').val();
        if (yearValue && yearValue !== 'select') {
            // Trigger cascade with auto-restoration enabled
            handleYearChange(yearValue, true);
        } else {
            disableDropdown($('select[name="month"]'));
            disableDropdown($('select[name="platform"]'));
            disableDropdown($('select[name="market"]'));
            disableDropdown($('select[name="locality"]'));
            disableDropdown($('select[name="worktype"]'));
        }
    }

    function initializeRosterSummaryCascade() {
        // Disable month initially until year is selected
        const monthSelect = $('select[name="month"]');
        const yearValue = $('select[name="year"]').val();

        if (yearValue && yearValue !== 'select') {
            // Trigger cascade with auto-restoration enabled
            handleYearChangeForRosterSummary(yearValue, true);
        } else {
            disableDropdown(monthSelect);
        }
    }

    // ============================================================================
    // FORM VALIDATION
    // ============================================================================

    function validateForm(dataType) {
        const validationAlert = document.getElementById("validationAlert");
        let valid = true;
        let errorMsg = "";

        if (dataType === "roster" || dataType === "prod_team_roster") {
            const year = $('select[name="year"]').val();
            const month = $('select[name="month"]').val();

            if (!year || year === 'select' || !month || month === 'select') {
                valid = false;
                errorMsg = "Please select Year and Month.";
            }
        } else if (dataType === "forecast") {
            const year = $('select[name="year"]').val();
            const month = $('select[name="month"]').val();
            const platform = $('select[name="platform"]').val();
            const market = $('select[name="market"]').val();
            const worktype = $('select[name="worktype"]').val();
            // Locality is optional

            if (!year || year === 'select' || !month || month === 'select' ||
                !platform || platform === 'select' || !market || market === 'select' ||
                !worktype || worktype === 'select') {
                valid = false;
                errorMsg = "Please select all required filters: Year, Month, Platform, Market, and Worktype.";
            }
        } else if (dataType === "summary") {
            const year = $('select[name="year"]').val();
            const month = $('select[name="month"]').val();
            const summaryType = $('select[name="summary_type"]').val();

            if (!year || year === 'select' || !month || month === 'select' ||
                !summaryType || summaryType === 'select') {
                valid = false;
                errorMsg = "Please select Year, Month, and Summary Type.";
            }
        }

        if (!valid) {
            validationAlert.innerHTML = errorMsg;
            validationAlert.style.display = "block";
        } else {
            validationAlert.style.display = "none";
        }

        return valid;
    }

    // ============================================================================
    // URL MANAGEMENT
    // ============================================================================

    function updateUrl(paramUpdates = {}) {
        // Start with current URL parameters
        const urlParams = new URLSearchParams(window.location.search);

        // Apply updates to the params
        for (const [key, value] of Object.entries(paramUpdates)) {
            if (value === null || value === undefined || value === '') {
                urlParams.delete(key);
            } else {
                urlParams.set(key, value);
            }
        }

        // Update browser URL
        const url = new URL(window.location.href);
        url.search = urlParams.toString();
        window.history.replaceState({}, '', url.toString());
    }

    function setDropdownValuesFromParams() {
        const urlParams = new URLSearchParams(window.location.search);
        document.querySelectorAll('select').forEach(function(select) {
            const name = select.name;
            const value = urlParams.get(name);
            if (value) {
                select.value = value;
            } else {
                select.value = 'select';
            }
        });
    }

    // ============================================================================
    // DOWNLOAD FUNCTIONALITY
    // ============================================================================

    function setupDownloadLink() {
        $('#download-link').on('click', function (e) {
            e.preventDefault();

            const params = new URLSearchParams(window.location.search);
            const url = window.DATA_VIEW_URLS.fileDownload + '?' + params.toString();

            $.ajax({
                url: url,
                method: "GET",
                xhrFields: {
                    responseType: 'blob'
                },
                success: function (data, _status, xhr) {
                    const disposition = xhr.getResponseHeader('Content-Disposition');

                    if (disposition && disposition.includes('attachment')) {
                        const blob = new Blob([data]);
                        const link = document.createElement('a');
                        link.href = window.URL.createObjectURL(blob);
                        link.download = getFilenameFromDisposition(disposition);
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        $('#error-message').text('').hide();
                    } else {
                        const reader = new FileReader();
                        reader.onload = function () {
                            try {
                                const errorJson = JSON.parse(reader.result);
                                $('#error-message').text(errorJson.detail || 'An error occurred').show();
                            } catch {
                                $('#error-message').text('An unknown error occurred.').show();
                            }
                        };
                        reader.readAsText(data);
                    }
                },
                error: function (xhr) {
                    let errorMsg = 'Error downloading file';
                    if (xhr.status === 404) {
                        errorMsg = 'File not found for the selected filters.';
                    }
                    $('#error-message').text(errorMsg).show();
                    setTimeout(function() {
                        $('#error-message').hide();
                    }, 10000);
                }
            });

            function getFilenameFromDisposition(disposition) {
                const match = /filename[^;=\\n]*=((['\"]).*?\\2|[^;\\n]*)/.exec(disposition);
                return match && match[1] ? match[1].replace(/['\\"]/g, '') : 'downloaded_file';
            }
        });
    }

    // ============================================================================
    // EVENT HANDLERS
    // ============================================================================

    function attachEventListeners() {
        const dataTypeSelect = $('select[name="data_type"]');
        const yearSelect = $('select[name="year"]');
        const monthSelect = $('select[name="month"]');
        const platformSelect = $('select[name="platform"]');
        const marketSelect = $('select[name="market"]');
        const localitySelect = $('select[name="locality"]');
        const form = document.getElementById("filterForm");

        // Data type change
        dataTypeSelect.on("change", function(event) {
            const dataType = event.target.value;
            updateUrl({ data_type: dataType });
            updateDropdownVisibilityByType(dataType);
        });

        // Cascade event listeners for forecast, roster, and summary
        yearSelect.on("change", function(event) {
            const yearValue = event.target.value;
            const dataType = dataTypeSelect.val();

            // Handle cascade based on data type
            if (dataType === 'forecast') {
                handleYearChange(yearValue);
            } else if (dataType === 'roster' || dataType === 'prod_team_roster' || dataType === 'summary') {
                handleYearChangeForRosterSummary(yearValue);
            }

            updateUrl({ year: yearValue });
        });

        monthSelect.on("change", function(event) {
            const monthValue = event.target.value;
            const dataType = dataTypeSelect.val();

            if (dataType === 'forecast') {
                handleMonthChange(monthValue);
            }

            updateUrl({ month: monthValue });
        });

        platformSelect.on("change", function(event) {
            const platformValue = event.target.value;
            const dataType = dataTypeSelect.val();

            if (dataType === 'forecast') {
                handlePlatformChange(platformValue);
            }

            updateUrl({ platform: platformValue });
        });

        marketSelect.on("change", function(event) {
            const marketValue = event.target.value;
            const dataType = dataTypeSelect.val();

            if (dataType === 'forecast') {
                handleMarketChange(marketValue);
            }

            updateUrl({ market: marketValue });
        });

        localitySelect.on("change", function(event) {
            const localityValue = event.target.value;
            const dataType = dataTypeSelect.val();

            if (dataType === 'forecast') {
                handleLocalityChange(localityValue);
            }

            updateUrl({ locality: localityValue });
        });

        // Form submission validation
        form.addEventListener("submit", function(e) {
            const dataType = dataTypeSelect.val();
            if (!validateForm(dataType)) {
                e.preventDefault();
            }
        });

        // All other dropdowns update URL
        document.querySelectorAll('select').forEach(function(select) {
            if (!['data_type', 'year', 'month', 'platform', 'market', 'locality'].includes(select.name)) {
                select.addEventListener("change", function(event) {
                    updateUrl({ [event.target.name]: event.target.value });
                });
            }
        });
    }

    // ============================================================================
    // INITIALIZATION
    // ============================================================================

    document.addEventListener("DOMContentLoaded", function() {
        console.log('Data View: Initializing...');

        // Set initial dropdown values from URL
        setDropdownValuesFromParams();

        // Setup initial visibility
        const urlParams = new URLSearchParams(window.location.search);
        const initialDataType = urlParams.get('data_type') || $('select[name="data_type"]').val();
        updateDropdownVisibilityByType(initialDataType);

        // Attach all event listeners
        attachEventListeners();

        // Setup download link
        setupDownloadLink();

        console.log('Data View: Initialization complete');
    });

})();


// ============================================================================
// EXISTING EDITABLE TABLE FUNCTIONALITY (unchanged)
// ============================================================================

$(document).ready(function() {
    // Initialize validation and first calculation
    initializeval();
    updateSummary();

    function initializeval(){
        $('.editable-field').each(function() {
            validateInput($(this));
        });
    }

    function validateInput($input) {
        const value = parseFloat($input.val());
        if (isNaN(value)) {
            $input.addClass('is-invalid');
            return false;
        }
        $input.removeClass('is-invalid');

        // Special handling for Ramp
        if ($input.data('field') === 'Ramp') {
            const clamped = Math.min(100, Math.max(0, value));
            $input.val(clamped);
        }
        return true;
    }

    function updateSummary() {
        let totalCPH = 0, totalCDP = 0, rampValues = [];

        $('#editableTable tbody tr:not(.summary-row)').each(function() {
            const cph = parseFloat($(this).find('[data-field="CPH"]').val()) || 0;
            const cdp = parseFloat($(this).find('[data-field="CDP"]').val()) || 0;
            const ramp = parseFloat($(this).find('[data-field="Ramp"]').val()) || 0;

            totalCPH += cph;
            totalCDP += cdp;
            rampValues.push(ramp);
        });

        $('.summary-cph').text(totalCPH);
        $('.summary-cdp').text(totalCDP);
    }

    $(document).on('input', '.editable-field', function() {
        if (validateInput($(this))) {
            updateSummary();
        }
    });

    $('#saveBtn').click(function() {
        const tableData = [];
        $('#editableTable tbody tr:not(.summary-row)').each(function() {
            const row = {};
            $(this).find('td').each(function(index) {
                const header = $('th').eq(index).text().trim();
                const input = $(this).find('.editable-field');

                if (input.length) {
                    if (header === 'Ramp') {
                        let rampValue = input.val();
                        rampValue = Math.min(100, Math.max(0, parseInt(rampValue) || 0));
                        row[header] = rampValue + '%';
                    } else {
                        row[header] = input.val();

                        if (header === 'CPH' || header === 'CDP') {
                            row[header] = parseInt(row[header]) || 0;
                        }
                    }
                } else {
                    row[header] = $(this).text().trim();
                }
            });
            tableData.push(row);
        });
        console.log(tableData);
        // AJAX save implementation
    });
});