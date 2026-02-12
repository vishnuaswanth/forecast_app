/**
 * configuration_view.js
 * JavaScript for Configuration Management page
 * Follows IIFE module pattern from edit_view.js
 */

(function() {
    'use strict';

    // ============================================================
    // CONFIGURATION
    // ============================================================
    const CONFIG = window.CONFIGURATION_VIEW_CONFIG || {};
    const URLS = CONFIG.urls || {};
    const SETTINGS = CONFIG.settings || {};

    // ============================================================
    // STATE
    // ============================================================
    const STATE = {
        // Month Configuration state
        monthConfig: {
            data: [],
            allData: [],  // Store unfiltered data for client-side filtering
            filters: { year: [], month: [], workType: [] },  // Arrays for multi-select
            currentPage: 1,
            totalPages: 1,
            isLoading: false,
            distinctYears: [],
            distinctMonths: [],
            distinctWorkTypes: []
        },
        // Target CPH state
        targetCph: {
            data: [],
            allData: [],  // Store unfiltered data for client-side filtering
            filters: { mainLob: [], caseType: [] },  // Arrays for multi-select
            currentPage: 1,
            totalPages: 1,
            isLoading: false,
            distinctLobs: [],
            distinctCaseTypes: []
        },
        // Modal state
        modal: {
            mode: 'add', // 'add' or 'edit'
            editingId: null
        },
        // Bulk add state
        bulk: {
            monthConfigRows: 1,
            targetCphRows: 1
        }
    };

    // ============================================================
    // DOM CACHE
    // ============================================================
    const DOM = {
        // Month Config elements
        monthConfig: {
            yearFilter: null,
            monthFilter: null,
            workTypeFilter: null,
            applyBtn: null,
            clearBtn: null,
            addBtn: null,
            bulkAddBtn: null,
            validateBtn: null,
            loading: null,
            error: null,
            errorMsg: null,
            table: null,
            tableBody: null,
            noResults: null,
            pagination: null,
            countBadge: null
        },
        // Target CPH elements
        targetCph: {
            lobFilter: null,
            caseTypeFilter: null,
            applyBtn: null,
            clearBtn: null,
            addBtn: null,
            bulkAddBtn: null,
            loading: null,
            error: null,
            errorMsg: null,
            table: null,
            tableBody: null,
            noResults: null,
            pagination: null,
            countBadge: null
        },
        // Month Config Modal elements
        monthConfigModal: {
            modal: null,
            title: null,
            form: null,
            idField: null,
            monthField: null,
            yearField: null,
            workTypeField: null,
            workDaysField: null,
            occupancyField: null,
            shrinkageField: null,
            workHoursField: null,
            saveBtn: null
        },
        // Month Config Bulk Modal
        monthConfigBulkModal: {
            modal: null,
            rowsContainer: null,
            addRowBtn: null,
            saveBtn: null
        },
        // Validation Modal
        validationModal: {
            modal: null,
            body: null
        },
        // Target CPH Modal elements
        targetCphModal: {
            modal: null,
            title: null,
            form: null,
            idField: null,
            lobField: null,
            caseTypeField: null,
            targetCphField: null,
            saveBtn: null
        },
        // Target CPH Bulk Modal
        targetCphBulkModal: {
            modal: null,
            rowsContainer: null,
            addRowBtn: null,
            saveBtn: null
        }
    };

    // ============================================================
    // INITIALIZATION
    // ============================================================
    function init() {
        cacheDOM();
        populateDropdowns();
        bindEvents();
        initSelect2();

        // Load initial data for Month Config tab (with isInitialLoad=true to populate filters)
        loadMonthConfigurations(true);
    }

    function cacheDOM() {
        // Month Config elements
        DOM.monthConfig = {
            yearFilter: document.getElementById('month-config-year-filter'),
            monthFilter: document.getElementById('month-config-month-filter'),
            workTypeFilter: document.getElementById('month-config-worktype-filter'),
            applyBtn: document.getElementById('month-config-apply-filters-btn'),
            clearBtn: document.getElementById('month-config-clear-filters-btn'),
            addBtn: document.getElementById('month-config-add-btn'),
            bulkAddBtn: document.getElementById('month-config-bulk-add-btn'),
            validateBtn: document.getElementById('month-config-validate-btn'),
            loading: document.getElementById('month-config-loading'),
            error: document.getElementById('month-config-error'),
            errorMsg: document.getElementById('month-config-error-message'),
            tableBody: document.getElementById('month-config-table-body'),
            noResults: document.getElementById('month-config-no-results'),
            pagination: document.getElementById('month-config-pagination'),
            countBadge: document.getElementById('month-config-count-badge')
        };

        // Target CPH elements
        DOM.targetCph = {
            lobFilter: document.getElementById('target-cph-lob-filter'),
            caseTypeFilter: document.getElementById('target-cph-casetype-filter'),
            applyBtn: document.getElementById('target-cph-apply-filters-btn'),
            clearBtn: document.getElementById('target-cph-clear-filters-btn'),
            addBtn: document.getElementById('target-cph-add-btn'),
            bulkAddBtn: document.getElementById('target-cph-bulk-add-btn'),
            loading: document.getElementById('target-cph-loading'),
            error: document.getElementById('target-cph-error'),
            errorMsg: document.getElementById('target-cph-error-message'),
            tableBody: document.getElementById('target-cph-table-body'),
            noResults: document.getElementById('target-cph-no-results'),
            pagination: document.getElementById('target-cph-pagination'),
            countBadge: document.getElementById('target-cph-count-badge')
        };

        // Month Config Modal
        DOM.monthConfigModal = {
            modal: document.getElementById('month-config-modal'),
            title: document.getElementById('month-config-modal-title'),
            form: document.getElementById('month-config-form'),
            idField: document.getElementById('month-config-form-id'),
            monthField: document.getElementById('month-config-form-month'),
            yearField: document.getElementById('month-config-form-year'),
            workTypeField: document.getElementById('month-config-form-worktype'),
            workDaysField: document.getElementById('month-config-form-workdays'),
            occupancyField: document.getElementById('month-config-form-occupancy'),
            shrinkageField: document.getElementById('month-config-form-shrinkage'),
            workHoursField: document.getElementById('month-config-form-workhours'),
            saveBtn: document.getElementById('month-config-save-btn')
        };

        // Month Config Bulk Modal
        DOM.monthConfigBulkModal = {
            modal: document.getElementById('month-config-bulk-modal'),
            rowsContainer: document.getElementById('month-config-bulk-rows'),
            addRowBtn: document.getElementById('month-config-add-row-btn'),
            saveBtn: document.getElementById('month-config-bulk-save-btn')
        };

        // Validation Modal
        DOM.validationModal = {
            modal: document.getElementById('validation-modal'),
            body: document.getElementById('validation-modal-body')
        };

        // Target CPH Modal
        DOM.targetCphModal = {
            modal: document.getElementById('target-cph-modal'),
            title: document.getElementById('target-cph-modal-title'),
            form: document.getElementById('target-cph-form'),
            idField: document.getElementById('target-cph-form-id'),
            lobField: document.getElementById('target-cph-form-lob'),
            caseTypeField: document.getElementById('target-cph-form-casetype'),
            targetCphField: document.getElementById('target-cph-form-targetcph'),
            saveBtn: document.getElementById('target-cph-save-btn')
        };

        // Target CPH Bulk Modal
        DOM.targetCphBulkModal = {
            modal: document.getElementById('target-cph-bulk-modal'),
            rowsContainer: document.getElementById('target-cph-bulk-rows'),
            addRowBtn: document.getElementById('target-cph-add-row-btn'),
            saveBtn: document.getElementById('target-cph-bulk-save-btn')
        };
    }

    function populateDropdowns() {
        // Populate modal dropdowns with static values (filters will be populated from data)
        const currentYear = new Date().getFullYear();

        // Populate month modal dropdown
        const monthNames = SETTINGS.monthNames || [];
        const monthOptions = monthNames.map(m => `<option value="${m}">${m}</option>`).join('');
        if (DOM.monthConfigModal.monthField) {
            DOM.monthConfigModal.monthField.innerHTML = '<option value="">Select Month</option>' + monthOptions;
        }

        // Populate work type modal dropdown
        const workTypes = SETTINGS.workTypes || [];
        const workTypeOptions = workTypes.map(t => `<option value="${t}">${t}</option>`).join('');
        if (DOM.monthConfigModal.workTypeField) {
            DOM.monthConfigModal.workTypeField.innerHTML = '<option value="">Select Type</option>' + workTypeOptions;
        }

        // Set year field limits in modal
        if (DOM.monthConfigModal.yearField) {
            DOM.monthConfigModal.yearField.min = SETTINGS.minYear || 2020;
            DOM.monthConfigModal.yearField.max = SETTINGS.maxYear || 2100;
            DOM.monthConfigModal.yearField.value = currentYear;
        }

        // Initialize filter dropdowns with empty state (will be populated from data)
        // Note: Multi-select filters don't need placeholder options
        if (DOM.monthConfig.yearFilter) {
            DOM.monthConfig.yearFilter.innerHTML = '';
        }
        if (DOM.monthConfig.monthFilter) {
            DOM.monthConfig.monthFilter.innerHTML = '';
        }
        if (DOM.monthConfig.workTypeFilter) {
            DOM.monthConfig.workTypeFilter.innerHTML = '';
        }

        // Initialize Target CPH filters with empty state
        if (DOM.targetCph.lobFilter) {
            DOM.targetCph.lobFilter.innerHTML = '';
        }
        if (DOM.targetCph.caseTypeFilter) {
            DOM.targetCph.caseTypeFilter.innerHTML = '';
        }
    }

    function populateMonthConfigFiltersFromData(cascadeFrom = null) {
        // Extract distinct values from allData (unfiltered data)
        const allData = STATE.monthConfig.allData;

        // Extract distinct years from allData
        const years = [...new Set(allData.map(c => c.year))].sort((a, b) => b - a);
        STATE.monthConfig.distinctYears = years;

        // Extract distinct work types from allData
        const workTypes = SETTINGS.workTypes || [];
        const workTypesInData = [...new Set(allData.map(c => c.work_type))];
        const orderedWorkTypes = workTypes.filter(t => workTypesInData.includes(t));
        STATE.monthConfig.distinctWorkTypes = orderedWorkTypes;

        // Extract distinct months - may be filtered by selected years
        const monthNames = SETTINGS.monthNames || [];
        let dataForMonths = allData;
        let dataForWorkTypes = allData;

        // If years are selected, filter months to only show months from those years
        const selectedYears = STATE.monthConfig.filters.year || [];
        if (selectedYears.length > 0) {
            dataForMonths = allData.filter(c => selectedYears.includes(c.year.toString()) || selectedYears.includes(c.year));
        }

        // If years and months are selected, filter work types
        const selectedMonths = STATE.monthConfig.filters.month || [];
        if (selectedYears.length > 0 || selectedMonths.length > 0) {
            dataForWorkTypes = allData.filter(c => {
                const yearMatch = selectedYears.length === 0 || selectedYears.includes(c.year.toString()) || selectedYears.includes(c.year);
                const monthMatch = selectedMonths.length === 0 || selectedMonths.includes(c.month);
                return yearMatch && monthMatch;
            });
        }

        const monthsInFilteredData = [...new Set(dataForMonths.map(c => c.month))];
        const orderedMonths = monthNames.filter(m => monthsInFilteredData.includes(m));
        STATE.monthConfig.distinctMonths = orderedMonths;

        const workTypesInFilteredData = [...new Set(dataForWorkTypes.map(c => c.work_type))];
        const filteredWorkTypes = workTypes.filter(t => workTypesInFilteredData.includes(t));

        // Populate year filter (always from allData)
        if (DOM.monthConfig.yearFilter && cascadeFrom !== 'year') {
            const yearOptions = years.map(y => `<option value="${y}">${y}</option>`).join('');
            DOM.monthConfig.yearFilter.innerHTML = yearOptions;
        }

        // Populate month filter (filtered by selected years)
        if (DOM.monthConfig.monthFilter) {
            const monthOptions = orderedMonths.map(m => `<option value="${m}">${m}</option>`).join('');
            DOM.monthConfig.monthFilter.innerHTML = monthOptions;

            // If cascading from year, clear month selection if selected months are no longer valid
            if (cascadeFrom === 'year' && selectedMonths.length > 0) {
                const validMonths = selectedMonths.filter(m => orderedMonths.includes(m));
                STATE.monthConfig.filters.month = validMonths;
            }
        }

        // Populate work type filter (filtered by selected years and months)
        if (DOM.monthConfig.workTypeFilter) {
            const workTypeOptions = filteredWorkTypes.map(t => `<option value="${t}">${t}</option>`).join('');
            DOM.monthConfig.workTypeFilter.innerHTML = workTypeOptions;

            // If cascading, clear work type selection if selected types are no longer valid
            if ((cascadeFrom === 'year' || cascadeFrom === 'month') && STATE.monthConfig.filters.workType.length > 0) {
                const validWorkTypes = STATE.monthConfig.filters.workType.filter(t => filteredWorkTypes.includes(t));
                STATE.monthConfig.filters.workType = validWorkTypes;
            }
        }

        // Initialize or refresh Select2 for multi-select dropdowns
        initMonthConfigSelect2();
    }

    function initMonthConfigSelect2() {
        if (!jQuery || !jQuery.fn.select2) return;

        // Year filter
        if (DOM.monthConfig.yearFilter) {
            const $year = jQuery(DOM.monthConfig.yearFilter);
            if ($year.hasClass('select2-hidden-accessible')) {
                $year.select2('destroy');
            }
            $year.select2({
                theme: 'bootstrap-5',
                placeholder: 'Select Years...',
                allowClear: true,
                closeOnSelect: false,
                width: '100%'
            });
            // Restore selected values
            if (STATE.monthConfig.filters.year && STATE.monthConfig.filters.year.length > 0) {
                $year.val(STATE.monthConfig.filters.year).trigger('change.select2');
            }
        }

        // Month filter
        if (DOM.monthConfig.monthFilter) {
            const $month = jQuery(DOM.monthConfig.monthFilter);
            if ($month.hasClass('select2-hidden-accessible')) {
                $month.select2('destroy');
            }
            $month.select2({
                theme: 'bootstrap-5',
                placeholder: 'Select Months...',
                allowClear: true,
                closeOnSelect: false,
                width: '100%'
            });
            // Restore selected values
            if (STATE.monthConfig.filters.month && STATE.monthConfig.filters.month.length > 0) {
                $month.val(STATE.monthConfig.filters.month).trigger('change.select2');
            }
        }

        // Work Type filter
        if (DOM.monthConfig.workTypeFilter) {
            const $workType = jQuery(DOM.monthConfig.workTypeFilter);
            if ($workType.hasClass('select2-hidden-accessible')) {
                $workType.select2('destroy');
            }
            $workType.select2({
                theme: 'bootstrap-5',
                placeholder: 'Select Types...',
                allowClear: true,
                closeOnSelect: false,
                width: '100%'
            });
            // Restore selected values
            if (STATE.monthConfig.filters.workType && STATE.monthConfig.filters.workType.length > 0) {
                $workType.val(STATE.monthConfig.filters.workType).trigger('change.select2');
            }
        }
    }

    function populateTargetCphFiltersFromData(onlyPopulateCaseTypes = false) {
        // Populate Main LOB filter from distinct values (multi-select - no "All" option needed)
        // Skip if we only need to update case types (e.g., after LOB selection change)
        if (!onlyPopulateCaseTypes && DOM.targetCph.lobFilter && STATE.targetCph.distinctLobs.length > 0) {
            // Save current selection before repopulating
            let currentSelection = [];
            if (jQuery && jQuery.fn.select2) {
                currentSelection = jQuery(DOM.targetCph.lobFilter).val() || [];
            }

            const lobOptions = STATE.targetCph.distinctLobs.map(item => {
                const value = typeof item === 'object' ? item.value : item;
                const display = typeof item === 'object' ? item.display : item;
                return `<option value="${escapeHtml(value)}">${escapeHtml(display)}</option>`;
            }).join('');
            DOM.targetCph.lobFilter.innerHTML = lobOptions;

            // Initialize LOB Select2
            initTargetCphLobSelect2(currentSelection);
        }

        // Populate Case Type filter from distinct values (multi-select - no "All" option needed)
        if (DOM.targetCph.caseTypeFilter && STATE.targetCph.distinctCaseTypes.length > 0) {
            const caseTypeOptions = STATE.targetCph.distinctCaseTypes.map(item => {
                const value = typeof item === 'object' ? item.value : item;
                const display = typeof item === 'object' ? item.display : item;
                return `<option value="${escapeHtml(value)}">${escapeHtml(display)}</option>`;
            }).join('');
            DOM.targetCph.caseTypeFilter.innerHTML = caseTypeOptions;

            // Initialize Case Type Select2
            initTargetCphCaseTypeSelect2();
        }
    }

    function initTargetCphLobSelect2(preserveSelection = null) {
        if (!jQuery || !jQuery.fn.select2) return;
        if (!DOM.targetCph.lobFilter) return;

        const $lob = jQuery(DOM.targetCph.lobFilter);

        // Destroy existing Select2 instance if any
        if ($lob.hasClass('select2-hidden-accessible')) {
            $lob.select2('destroy');
        }

        // Initialize Select2
        $lob.select2({
            theme: 'bootstrap-5',
            placeholder: 'Select LOBs...',
            allowClear: true,
            closeOnSelect: false,
            width: '100%'
        });

        // Restore selection - use preserved selection or state
        const valuesToRestore = preserveSelection && preserveSelection.length > 0
            ? preserveSelection
            : (STATE.targetCph.filters.mainLob || []);

        if (valuesToRestore.length > 0) {
            $lob.val(valuesToRestore).trigger('change.select2');
        }
    }

    function initTargetCphCaseTypeSelect2() {
        if (!jQuery || !jQuery.fn.select2) return;
        if (!DOM.targetCph.caseTypeFilter) return;

        const $caseType = jQuery(DOM.targetCph.caseTypeFilter);

        // Destroy existing Select2 instance if any
        if ($caseType.hasClass('select2-hidden-accessible')) {
            $caseType.select2('destroy');
        }

        // Initialize Select2
        $caseType.select2({
            theme: 'bootstrap-5',
            placeholder: 'Select Case Types...',
            allowClear: true,
            closeOnSelect: false,
            width: '100%'
        });

        // Restore selected values AFTER initialization
        if (STATE.targetCph.filters.caseType && STATE.targetCph.filters.caseType.length > 0) {
            $caseType.val(STATE.targetCph.filters.caseType).trigger('change.select2');
        }
    }

    function initSelect2() {
        // Initialize Select2 for filter dropdowns
        // NOTE: Multi-select dropdowns (.config-view-select2-multi) are initialized
        // AFTER their options are populated in populateMonthConfigFiltersFromData()
        // and populateTargetCphFiltersFromData() to ensure Select2 can properly
        // render the options.
        if (jQuery && jQuery.fn.select2) {
            // Single-select dropdowns only
            jQuery('.config-view-select2').select2({
                theme: 'bootstrap-5',
                width: '100%',
                allowClear: true,
                minimumResultsForSearch: 5
            });
        }
    }

    function bindEvents() {
        // Month Config filter events
        if (DOM.monthConfig.applyBtn) {
            DOM.monthConfig.applyBtn.addEventListener('click', handleMonthConfigApplyFilters);
        }
        if (DOM.monthConfig.clearBtn) {
            DOM.monthConfig.clearBtn.addEventListener('click', handleMonthConfigClearFilters);
        }
        if (DOM.monthConfig.addBtn) {
            DOM.monthConfig.addBtn.addEventListener('click', handleMonthConfigAdd);
        }
        if (DOM.monthConfig.bulkAddBtn) {
            DOM.monthConfig.bulkAddBtn.addEventListener('click', handleMonthConfigBulkAdd);
        }
        if (DOM.monthConfig.validateBtn) {
            DOM.monthConfig.validateBtn.addEventListener('click', handleMonthConfigValidate);
        }

        // Month Config cascading filter events (using jQuery for Select2)
        if (jQuery && jQuery.fn.select2) {
            jQuery(DOM.monthConfig.yearFilter).on('change', handleYearFilterChange);
            jQuery(DOM.monthConfig.monthFilter).on('change', handleMonthFilterChange);
        }

        // Month Config Modal events
        if (DOM.monthConfigModal.saveBtn) {
            DOM.monthConfigModal.saveBtn.addEventListener('click', handleMonthConfigSave);
        }
        if (DOM.monthConfigBulkModal.addRowBtn) {
            DOM.monthConfigBulkModal.addRowBtn.addEventListener('click', addMonthConfigBulkRow);
        }
        if (DOM.monthConfigBulkModal.saveBtn) {
            DOM.monthConfigBulkModal.saveBtn.addEventListener('click', handleMonthConfigBulkSave);
        }

        // Target CPH filter events
        if (DOM.targetCph.applyBtn) {
            DOM.targetCph.applyBtn.addEventListener('click', handleTargetCphApplyFilters);
        }
        if (DOM.targetCph.clearBtn) {
            DOM.targetCph.clearBtn.addEventListener('click', handleTargetCphClearFilters);
        }
        if (DOM.targetCph.addBtn) {
            DOM.targetCph.addBtn.addEventListener('click', handleTargetCphAdd);
        }
        if (DOM.targetCph.bulkAddBtn) {
            DOM.targetCph.bulkAddBtn.addEventListener('click', handleTargetCphBulkAdd);
        }

        // LOB filter change event - update case types based on selected LOB
        if (DOM.targetCph.lobFilter) {
            // Use jQuery for Select2 change event only (to avoid double-firing)
            if (jQuery && jQuery.fn.select2) {
                jQuery(DOM.targetCph.lobFilter).on('change', handleLobFilterChange);
            } else {
                DOM.targetCph.lobFilter.addEventListener('change', handleLobFilterChange);
            }
        }

        // Target CPH Modal events
        if (DOM.targetCphModal.saveBtn) {
            DOM.targetCphModal.saveBtn.addEventListener('click', handleTargetCphSave);
        }
        if (DOM.targetCphBulkModal.addRowBtn) {
            DOM.targetCphBulkModal.addRowBtn.addEventListener('click', addTargetCphBulkRow);
        }
        if (DOM.targetCphBulkModal.saveBtn) {
            DOM.targetCphBulkModal.saveBtn.addEventListener('click', handleTargetCphBulkSave);
        }

        // Tab switch event
        const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
        tabButtons.forEach(btn => {
            btn.addEventListener('shown.bs.tab', handleTabSwitch);
        });

        // Table row action delegation
        if (DOM.monthConfig.tableBody) {
            DOM.monthConfig.tableBody.addEventListener('click', handleMonthConfigTableAction);
        }
        if (DOM.targetCph.tableBody) {
            DOM.targetCph.tableBody.addEventListener('click', handleTargetCphTableAction);
        }

        // Pagination event delegation
        document.addEventListener('click', handlePaginationClick);

        // Modal reset on close
        if (DOM.monthConfigModal.modal) {
            DOM.monthConfigModal.modal.addEventListener('hidden.bs.modal', resetMonthConfigModal);
        }
        if (DOM.monthConfigBulkModal.modal) {
            DOM.monthConfigBulkModal.modal.addEventListener('hidden.bs.modal', resetMonthConfigBulkModal);
        }
        if (DOM.targetCphModal.modal) {
            DOM.targetCphModal.modal.addEventListener('hidden.bs.modal', resetTargetCphModal);
        }
        if (DOM.targetCphBulkModal.modal) {
            DOM.targetCphBulkModal.modal.addEventListener('hidden.bs.modal', resetTargetCphBulkModal);
        }
    }

    // ============================================================
    // MONTH CONFIG CASCADING FILTER HANDLERS
    // ============================================================
    function handleYearFilterChange(e) {
        // Get selected years
        let selectedYears = [];
        if (jQuery && jQuery.fn.select2) {
            selectedYears = jQuery(DOM.monthConfig.yearFilter).val() || [];
        } else if (DOM.monthConfig.yearFilter) {
            selectedYears = Array.from(DOM.monthConfig.yearFilter.selectedOptions).map(o => o.value).filter(v => v);
        }

        STATE.monthConfig.filters.year = selectedYears;

        // Repopulate month and work type filters based on selected years
        populateMonthConfigFiltersFromData('year');
    }

    function handleMonthFilterChange(e) {
        // Get selected months
        let selectedMonths = [];
        if (jQuery && jQuery.fn.select2) {
            selectedMonths = jQuery(DOM.monthConfig.monthFilter).val() || [];
        } else if (DOM.monthConfig.monthFilter) {
            selectedMonths = Array.from(DOM.monthConfig.monthFilter.selectedOptions).map(o => o.value).filter(v => v);
        }

        STATE.monthConfig.filters.month = selectedMonths;

        // Repopulate work type filter based on selected years and months
        populateMonthConfigFiltersFromData('month');
    }

    // ============================================================
    // TAB HANDLING
    // ============================================================
    function handleTabSwitch(e) {
        const targetId = e.target.getAttribute('data-bs-target');

        if (targetId === '#target-cph-config-tab') {
            // Load Target CPH data when tab is activated
            if (STATE.targetCph.data.length === 0) {
                // Load filter options and data
                loadDistinctLobs();
                loadDistinctCaseTypes();
                loadTargetCphConfigurations(true); // First load needs to fetch from server
            }
        }
    }

    // ============================================================
    // MONTH CONFIGURATION FUNCTIONS
    // ============================================================
    async function loadMonthConfigurations(isInitialLoad = false) {
        if (STATE.monthConfig.isLoading) return;

        STATE.monthConfig.isLoading = true;
        showLoading(DOM.monthConfig);
        hideError(DOM.monthConfig);

        try {
            // Only fetch from server if we don't have data or isInitialLoad is true
            if (isInitialLoad || STATE.monthConfig.allData.length === 0) {
                // Fetch all data without filters (client-side filtering for multi-select)
                const response = await fetch(URLS.monthConfigList);
                const data = await response.json();

                if (!response.ok || !data.success) {
                    throw new Error(data.error || 'Failed to load configurations');
                }

                STATE.monthConfig.allData = data.data || [];
            }

            // Apply client-side filtering for multi-select
            STATE.monthConfig.data = applyMonthConfigFilters(STATE.monthConfig.allData);

            // On initial load, populate filter dropdowns from data
            if (isInitialLoad || STATE.monthConfig.distinctYears.length === 0) {
                populateMonthConfigFiltersFromData();
            }

            renderMonthConfigTable();
            updateMonthConfigCount();

        } catch (error) {
            console.error('Failed to load month configurations:', error);
            showError(DOM.monthConfig, error.message);
        } finally {
            STATE.monthConfig.isLoading = false;
            hideLoading(DOM.monthConfig);
        }
    }

    function applyMonthConfigFilters(data) {
        const { year, month, workType } = STATE.monthConfig.filters;

        return data.filter(item => {
            // Filter by Year (if any selected)
            if (year && year.length > 0) {
                // year could be number in data, string in filter
                if (!year.includes(item.year.toString()) && !year.includes(item.year)) {
                    return false;
                }
            }

            // Filter by Month (if any selected)
            if (month && month.length > 0) {
                if (!month.includes(item.month)) {
                    return false;
                }
            }

            // Filter by Work Type (if any selected)
            if (workType && workType.length > 0) {
                if (!workType.includes(item.work_type)) {
                    return false;
                }
            }

            return true;
        });
    }

    function renderMonthConfigTable() {
        const tbody = DOM.monthConfig.tableBody;
        if (!tbody) return;

        if (STATE.monthConfig.data.length === 0) {
            tbody.innerHTML = '';
            showElement(DOM.monthConfig.noResults);
            hideElement(DOM.monthConfig.pagination);
            return;
        }

        hideElement(DOM.monthConfig.noResults);

        // Calculate pagination
        const pageSize = SETTINGS.pageSize || 25;
        const startIdx = (STATE.monthConfig.currentPage - 1) * pageSize;
        const endIdx = startIdx + pageSize;
        const pageData = STATE.monthConfig.data.slice(startIdx, endIdx);
        STATE.monthConfig.totalPages = Math.ceil(STATE.monthConfig.data.length / pageSize);

        const rows = pageData.map(config => {
            const workTypeClass = config.work_type === 'Domestic'
                ? 'config-view-worktype-domestic'
                : 'config-view-worktype-global';

            return `
                <tr data-id="${config.id}">
                    <td class="config-view-col-id">${config.id}</td>
                    <td class="config-view-col-month">${escapeHtml(config.month)}</td>
                    <td class="config-view-col-year">${config.year}</td>
                    <td class="config-view-col-worktype">
                        <span class="${workTypeClass}">${escapeHtml(config.work_type)}</span>
                    </td>
                    <td class="config-view-col-workdays config-view-number">${config.working_days}</td>
                    <td class="config-view-col-occupancy config-view-percentage">${formatPercentage(config.occupancy)}</td>
                    <td class="config-view-col-shrinkage config-view-percentage">${formatPercentage(config.shrinkage)}</td>
                    <td class="config-view-col-workhours config-view-number">${config.work_hours}</td>
                    <td class="config-view-col-updatedby">${escapeHtml(config.updated_by || '-')}</td>
                    <td class="config-view-col-updateddate">${formatDate(config.updated_date)}</td>
                    <td class="config-view-col-actions">
                        <div class="config-view-action-btns">
                            <button class="config-view-btn config-view-btn-icon config-view-btn-outline-primary"
                                    data-action="edit" title="Edit">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="config-view-btn config-view-btn-icon config-view-btn-outline-danger"
                                    data-action="delete" title="Delete">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        tbody.innerHTML = rows;

        // Render pagination
        renderMonthConfigPagination();
    }

    function renderMonthConfigPagination() {
        if (!DOM.monthConfig.pagination || STATE.monthConfig.totalPages <= 1) {
            hideElement(DOM.monthConfig.pagination);
            return;
        }

        const currentPage = STATE.monthConfig.currentPage;
        const totalPages = STATE.monthConfig.totalPages;
        const paginationHtml = [];

        // Previous button
        paginationHtml.push(`
            <li class="config-view-page-item ${currentPage === 1 ? 'config-view-page-item-disabled' : ''}">
                <a class="config-view-page-link" href="#" data-page="${currentPage - 1}">Previous</a>
            </li>
        `);

        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
                paginationHtml.push(`
                    <li class="config-view-page-item ${i === currentPage ? 'config-view-page-item-active' : ''}">
                        <a class="config-view-page-link" href="#" data-page="${i}">${i}</a>
                    </li>
                `);
            } else if (i === currentPage - 3 || i === currentPage + 3) {
                paginationHtml.push(`
                    <li class="config-view-page-item config-view-page-item-disabled">
                        <span class="config-view-page-link">...</span>
                    </li>
                `);
            }
        }

        // Next button
        paginationHtml.push(`
            <li class="config-view-page-item ${currentPage === totalPages ? 'config-view-page-item-disabled' : ''}">
                <a class="config-view-page-link" href="#" data-page="${currentPage + 1}">Next</a>
            </li>
        `);

        DOM.monthConfig.pagination.querySelector('ul').innerHTML = paginationHtml.join('');
        showElement(DOM.monthConfig.pagination);
    }

    function updateMonthConfigCount() {
        if (DOM.monthConfig.countBadge) {
            const count = STATE.monthConfig.data.length;
            const startIdx = (STATE.monthConfig.currentPage - 1) * (SETTINGS.pageSize || 25);
            const endIdx = Math.min(startIdx + (SETTINGS.pageSize || 25), count);
            const showing = count > 0 ? `${startIdx + 1}-${endIdx} of ${count}` : '0';
            DOM.monthConfig.countBadge.textContent = `${showing} configuration${count !== 1 ? 's' : ''}`;
        }
    }

    function handleMonthConfigApplyFilters() {
        // Multi-select: use jQuery.val() which returns an array
        if (jQuery && jQuery.fn.select2) {
            STATE.monthConfig.filters.year = jQuery(DOM.monthConfig.yearFilter).val() || [];
            STATE.monthConfig.filters.month = jQuery(DOM.monthConfig.monthFilter).val() || [];
            STATE.monthConfig.filters.workType = jQuery(DOM.monthConfig.workTypeFilter).val() || [];
        } else {
            // Fallback for native multi-select
            STATE.monthConfig.filters.year = DOM.monthConfig.yearFilter
                ? Array.from(DOM.monthConfig.yearFilter.selectedOptions).map(o => o.value).filter(v => v)
                : [];
            STATE.monthConfig.filters.month = DOM.monthConfig.monthFilter
                ? Array.from(DOM.monthConfig.monthFilter.selectedOptions).map(o => o.value).filter(v => v)
                : [];
            STATE.monthConfig.filters.workType = DOM.monthConfig.workTypeFilter
                ? Array.from(DOM.monthConfig.workTypeFilter.selectedOptions).map(o => o.value).filter(v => v)
                : [];
        }
        STATE.monthConfig.currentPage = 1;
        loadMonthConfigurations();
    }

    function handleMonthConfigClearFilters() {
        STATE.monthConfig.filters = { year: [], month: [], workType: [] };

        if (jQuery && jQuery.fn.select2) {
            jQuery(DOM.monthConfig.yearFilter).val(null).trigger('change.select2');
            jQuery(DOM.monthConfig.monthFilter).val(null).trigger('change.select2');
            jQuery(DOM.monthConfig.workTypeFilter).val(null).trigger('change.select2');
        } else {
            if (DOM.monthConfig.yearFilter) {
                Array.from(DOM.monthConfig.yearFilter.options).forEach(o => o.selected = false);
            }
            if (DOM.monthConfig.monthFilter) {
                Array.from(DOM.monthConfig.monthFilter.options).forEach(o => o.selected = false);
            }
            if (DOM.monthConfig.workTypeFilter) {
                Array.from(DOM.monthConfig.workTypeFilter.options).forEach(o => o.selected = false);
            }
        }

        // Repopulate filters from all data (reset cascading)
        populateMonthConfigFiltersFromData();

        STATE.monthConfig.currentPage = 1;
        loadMonthConfigurations();
    }

    function handleMonthConfigAdd() {
        STATE.modal.mode = 'add';
        STATE.modal.editingId = null;

        if (DOM.monthConfigModal.title) {
            DOM.monthConfigModal.title.textContent = 'Add Month Configuration';
        }

        resetMonthConfigForm();
        showModal('month-config-modal');
    }

    function handleMonthConfigEdit(configId) {
        const config = STATE.monthConfig.data.find(c => c.id === configId);
        if (!config) return;

        STATE.modal.mode = 'edit';
        STATE.modal.editingId = configId;

        if (DOM.monthConfigModal.title) {
            DOM.monthConfigModal.title.textContent = 'Edit Month Configuration';
        }

        // Populate form
        if (DOM.monthConfigModal.idField) DOM.monthConfigModal.idField.value = config.id;
        if (DOM.monthConfigModal.monthField) DOM.monthConfigModal.monthField.value = config.month;
        if (DOM.monthConfigModal.yearField) DOM.monthConfigModal.yearField.value = config.year;
        if (DOM.monthConfigModal.workTypeField) DOM.monthConfigModal.workTypeField.value = config.work_type;
        if (DOM.monthConfigModal.workDaysField) DOM.monthConfigModal.workDaysField.value = config.working_days;
        if (DOM.monthConfigModal.occupancyField) DOM.monthConfigModal.occupancyField.value = config.occupancy * 100;
        if (DOM.monthConfigModal.shrinkageField) DOM.monthConfigModal.shrinkageField.value = config.shrinkage * 100;
        if (DOM.monthConfigModal.workHoursField) DOM.monthConfigModal.workHoursField.value = config.work_hours;

        showModal('month-config-modal');
    }

    async function handleMonthConfigSave() {
        const form = DOM.monthConfigModal.form;
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const data = {
            month: DOM.monthConfigModal.monthField.value,
            year: parseInt(DOM.monthConfigModal.yearField.value),
            work_type: DOM.monthConfigModal.workTypeField.value,
            working_days: parseInt(DOM.monthConfigModal.workDaysField.value),
            occupancy: parseFloat(DOM.monthConfigModal.occupancyField.value) / 100,
            shrinkage: parseFloat(DOM.monthConfigModal.shrinkageField.value) / 100,
            work_hours: parseFloat(DOM.monthConfigModal.workHoursField.value)
        };

        try {
            let url, method;
            if (STATE.modal.mode === 'edit') {
                url = URLS.monthConfigUpdate.replace('{id}', STATE.modal.editingId);
                method = 'PUT';
            } else {
                url = URLS.monthConfigCreate;
                method = 'POST';
            }

            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.error || 'Failed to save configuration');
            }

            hideModal('month-config-modal');
            showSuccess(STATE.modal.mode === 'edit' ? 'Configuration updated successfully' : 'Configuration created successfully');
            loadMonthConfigurations();

        } catch (error) {
            console.error('Failed to save configuration:', error);
            showErrorAlert(error.message);
        }
    }

    async function handleMonthConfigDelete(configId) {
        const config = STATE.monthConfig.data.find(c => c.id === configId);
        if (!config) return;

        const confirmed = await Swal.fire({
            title: 'Delete Configuration?',
            html: `Are you sure you want to delete the configuration for<br><strong>${config.month} ${config.year} - ${config.work_type}</strong>?`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#dc3545',
            cancelButtonColor: '#6c757d',
            confirmButtonText: 'Yes, delete it'
        });

        if (!confirmed.isConfirmed) return;

        try {
            const url = URLS.monthConfigDelete.replace('{id}', configId);
            const response = await fetch(url, { method: 'DELETE' });
            const result = await response.json();

            if (!response.ok || !result.success) {
                // Check for orphan warning
                if (result.orphan_warning) {
                    const forceDelete = await Swal.fire({
                        title: 'Orphan Warning',
                        html: result.orphan_warning + '<br><br>Do you still want to delete?',
                        icon: 'warning',
                        showCancelButton: true,
                        confirmButtonColor: '#dc3545',
                        confirmButtonText: 'Yes, delete anyway'
                    });

                    if (forceDelete.isConfirmed) {
                        const forceUrl = url + '?allow_orphan=true';
                        const forceResponse = await fetch(forceUrl, { method: 'DELETE' });
                        const forceResult = await forceResponse.json();

                        if (!forceResponse.ok || !forceResult.success) {
                            throw new Error(forceResult.error || 'Failed to delete');
                        }
                    } else {
                        return;
                    }
                } else {
                    throw new Error(result.error || 'Failed to delete configuration');
                }
            }

            showSuccess('Configuration deleted successfully');
            loadMonthConfigurations();

        } catch (error) {
            console.error('Failed to delete configuration:', error);
            showErrorAlert(error.message);
        }
    }

    function handleMonthConfigTableAction(e) {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;

        const action = btn.dataset.action;
        const row = btn.closest('tr');
        const configId = parseInt(row.dataset.id);

        if (action === 'edit') {
            handleMonthConfigEdit(configId);
        } else if (action === 'delete') {
            handleMonthConfigDelete(configId);
        }
    }

    async function handleMonthConfigValidate() {
        try {
            const response = await fetch(URLS.monthConfigValidate);
            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.error || 'Validation failed');
            }

            renderValidationResults(result);
            showModal('validation-modal');

        } catch (error) {
            console.error('Validation failed:', error);
            showErrorAlert(error.message);
        }
    }

    function renderValidationResults(result) {
        const body = DOM.validationModal.body;
        if (!body) return;

        if (result.is_valid) {
            body.innerHTML = `
                <div class="config-view-alert config-view-validation-valid">
                    <i class="fas fa-check-circle config-view-me-2"></i>
                    <strong>All configurations are valid!</strong>
                    No orphaned records found.
                </div>
            `;
        } else {
            const orphanItems = result.orphaned_records.map(rec => `
                <div class="config-view-orphan-item">
                    <strong>${escapeHtml(rec.month)} ${rec.year}</strong> -
                    ${escapeHtml(rec.work_type)}
                    <span class="config-view-text-muted">(ID: ${rec.id})</span>
                </div>
            `).join('');

            body.innerHTML = `
                <div class="config-view-alert config-view-validation-invalid">
                    <i class="fas fa-exclamation-triangle config-view-me-2"></i>
                    <strong>Validation Issues Found!</strong>
                    <br>${result.orphaned_count} orphaned record(s) detected.
                </div>
                ${result.recommendation ? `
                    <div class="config-view-alert config-view-alert-info config-view-mt-3">
                        <i class="fas fa-info-circle config-view-me-2"></i>
                        <strong>Recommendation:</strong> ${escapeHtml(result.recommendation)}
                    </div>
                ` : ''}
                <div class="config-view-orphan-list">
                    ${orphanItems}
                </div>
            `;
        }
    }

    // Bulk Add functions
    function handleMonthConfigBulkAdd() {
        resetMonthConfigBulkModal();
        addMonthConfigBulkRow();
        showModal('month-config-bulk-modal');
    }

    function addMonthConfigBulkRow() {
        const container = DOM.monthConfigBulkModal.rowsContainer;
        if (!container) return;

        const rowNum = container.children.length + 1;
        const currentYear = new Date().getFullYear();

        const monthOptions = (SETTINGS.monthNames || []).map(m =>
            `<option value="${m}">${m}</option>`
        ).join('');

        const workTypeOptions = (SETTINGS.workTypes || []).map(t =>
            `<option value="${t}">${t}</option>`
        ).join('');

        const rowHtml = `
            <div class="config-view-bulk-row" data-row="${rowNum}">
                <div class="config-view-bulk-row-header">
                    <span class="config-view-bulk-row-number">Row ${rowNum}</span>
                    <span class="config-view-bulk-row-remove" onclick="window.removeMonthConfigBulkRow(this)">
                        <i class="fas fa-times"></i>
                    </span>
                </div>
                <div class="row">
                    <div class="col-md-2 mb-2">
                        <select class="form-select form-select-sm bulk-month" required>
                            <option value="">Month</option>
                            ${monthOptions}
                        </select>
                    </div>
                    <div class="col-md-2 mb-2">
                        <input type="number" class="form-control form-control-sm bulk-year"
                               placeholder="Year" value="${currentYear}"
                               min="${SETTINGS.minYear}" max="${SETTINGS.maxYear}" required>
                    </div>
                    <div class="col-md-2 mb-2">
                        <select class="form-select form-select-sm bulk-worktype" required>
                            <option value="">Work Type</option>
                            ${workTypeOptions}
                        </select>
                    </div>
                    <div class="col-md-1 mb-2">
                        <input type="number" class="form-control form-control-sm bulk-workdays"
                               placeholder="Days" min="1" max="31" required>
                    </div>
                    <div class="col-md-2 mb-2">
                        <input type="number" class="form-control form-control-sm bulk-occupancy"
                               placeholder="Occ %" min="0" max="100" step="0.1" required>
                    </div>
                    <div class="col-md-2 mb-2">
                        <input type="number" class="form-control form-control-sm bulk-shrinkage"
                               placeholder="Shrink %" min="0" max="100" step="0.1" required>
                    </div>
                    <div class="col-md-1 mb-2">
                        <input type="number" class="form-control form-control-sm bulk-workhours"
                               placeholder="Hrs" min="1" max="24" step="0.5" required>
                    </div>
                </div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', rowHtml);
        renumberBulkRows(container);
    }

    window.removeMonthConfigBulkRow = function(element) {
        const row = element.closest('.config-view-bulk-row');
        if (row) {
            row.remove();
            renumberBulkRows(DOM.monthConfigBulkModal.rowsContainer);
        }
    };

    function renumberBulkRows(container) {
        if (!container) return;
        const rows = container.querySelectorAll('.config-view-bulk-row');
        rows.forEach((row, idx) => {
            const numSpan = row.querySelector('.config-view-bulk-row-number');
            if (numSpan) numSpan.textContent = `Row ${idx + 1}`;
        });
    }

    async function handleMonthConfigBulkSave() {
        const container = DOM.monthConfigBulkModal.rowsContainer;
        if (!container) return;

        const rows = container.querySelectorAll('.config-view-bulk-row');
        const configs = [];

        for (const row of rows) {
            const month = row.querySelector('.bulk-month')?.value;
            const year = row.querySelector('.bulk-year')?.value;
            const workType = row.querySelector('.bulk-worktype')?.value;
            const workDays = row.querySelector('.bulk-workdays')?.value;
            const occupancy = row.querySelector('.bulk-occupancy')?.value;
            const shrinkage = row.querySelector('.bulk-shrinkage')?.value;
            const workHours = row.querySelector('.bulk-workhours')?.value;

            if (!month || !year || !workType || !workDays || !occupancy || !shrinkage || !workHours) {
                showErrorAlert('Please fill in all fields for each row');
                return;
            }

            configs.push({
                month: month,
                year: parseInt(year),
                work_type: workType,
                working_days: parseInt(workDays),
                occupancy: parseFloat(occupancy) / 100,
                shrinkage: parseFloat(shrinkage) / 100,
                work_hours: parseFloat(workHours)
            });
        }

        if (configs.length === 0) {
            showErrorAlert('Please add at least one configuration');
            return;
        }

        try {
            const response = await fetch(URLS.monthConfigBulkCreate, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ configurations: configs })
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.error || 'Failed to create configurations');
            }

            hideModal('month-config-bulk-modal');
            showSuccess(`Successfully created ${result.created_count} configuration(s)`);
            loadMonthConfigurations();

        } catch (error) {
            console.error('Bulk create failed:', error);
            showErrorAlert(error.message);
        }
    }

    function resetMonthConfigModal() {
        STATE.modal.mode = 'add';
        STATE.modal.editingId = null;
        resetMonthConfigForm();
    }

    function resetMonthConfigForm() {
        if (DOM.monthConfigModal.form) {
            DOM.monthConfigModal.form.reset();
        }
        if (DOM.monthConfigModal.idField) {
            DOM.monthConfigModal.idField.value = '';
        }
        if (DOM.monthConfigModal.yearField) {
            DOM.monthConfigModal.yearField.value = new Date().getFullYear();
        }
    }

    function resetMonthConfigBulkModal() {
        if (DOM.monthConfigBulkModal.rowsContainer) {
            DOM.monthConfigBulkModal.rowsContainer.innerHTML = '';
        }
        STATE.bulk.monthConfigRows = 0;
    }

    // ============================================================
    // TARGET CPH CONFIGURATION FUNCTIONS
    // ============================================================
    async function loadDistinctLobs() {
        try {
            const response = await fetch(URLS.targetCphDistinctLobs);
            const data = await response.json();

            if (data.success && data.data) {
                STATE.targetCph.distinctLobs = data.data;
                populateTargetCphFiltersFromData();
            }
        } catch (error) {
            console.error('Failed to load distinct LOBs:', error);
        }
    }

    async function loadDistinctCaseTypes(mainLob = null, onlyUpdateCaseTypes = false) {
        try {
            let url = URLS.targetCphDistinctCaseTypes;
            if (mainLob) {
                url += '?main_lob=' + encodeURIComponent(mainLob);
            }

            const response = await fetch(url);
            const data = await response.json();

            if (data.success && data.data) {
                STATE.targetCph.distinctCaseTypes = data.data;
                // Pass flag to only update case types, not LOB (preserves LOB selection)
                populateTargetCphFiltersFromData(onlyUpdateCaseTypes);
            }
        } catch (error) {
            console.error('Failed to load distinct Case Types:', error);
        }
    }

    async function loadTargetCphConfigurations(forceRefresh = false) {
        if (STATE.targetCph.isLoading) return;

        STATE.targetCph.isLoading = true;
        showLoading(DOM.targetCph);
        hideError(DOM.targetCph);

        try {
            // Only fetch from server if we don't have data or forceRefresh is true
            if (forceRefresh || STATE.targetCph.allData.length === 0) {
                // Fetch all data without filters (client-side filtering for multi-select)
                const response = await fetch(URLS.targetCphList);
                const data = await response.json();

                if (!response.ok || !data.success) {
                    throw new Error(data.error || 'Failed to load configurations');
                }

                STATE.targetCph.allData = data.data || [];
            }

            // Apply client-side filtering for multi-select
            STATE.targetCph.data = applyTargetCphFilters(STATE.targetCph.allData);
            renderTargetCphTable();
            updateTargetCphCount();

        } catch (error) {
            console.error('Failed to load Target CPH configurations:', error);
            showError(DOM.targetCph, error.message);
        } finally {
            STATE.targetCph.isLoading = false;
            hideLoading(DOM.targetCph);
        }
    }

    function applyTargetCphFilters(data) {
        const { mainLob, caseType } = STATE.targetCph.filters;

        return data.filter(item => {
            // Filter by Main LOB (if any selected)
            if (mainLob && mainLob.length > 0) {
                if (!mainLob.includes(item.main_lob)) {
                    return false;
                }
            }

            // Filter by Case Type (if any selected)
            if (caseType && caseType.length > 0) {
                if (!caseType.includes(item.case_type)) {
                    return false;
                }
            }

            return true;
        });
    }

    function renderTargetCphTable() {
        const tbody = DOM.targetCph.tableBody;
        if (!tbody) return;

        if (STATE.targetCph.data.length === 0) {
            tbody.innerHTML = '';
            showElement(DOM.targetCph.noResults);
            hideElement(DOM.targetCph.pagination);
            return;
        }

        hideElement(DOM.targetCph.noResults);

        // Calculate pagination
        const pageSize = SETTINGS.pageSize || 25;
        const startIdx = (STATE.targetCph.currentPage - 1) * pageSize;
        const endIdx = startIdx + pageSize;
        const pageData = STATE.targetCph.data.slice(startIdx, endIdx);
        STATE.targetCph.totalPages = Math.ceil(STATE.targetCph.data.length / pageSize);

        const rows = pageData.map(config => `
            <tr data-id="${config.id}">
                <td class="config-view-col-id">${config.id}</td>
                <td class="config-view-col-lob">${escapeHtml(config.main_lob)}</td>
                <td class="config-view-col-casetype">${escapeHtml(config.case_type)}</td>
                <td class="config-view-col-targetcph config-view-number">${config.target_cph}</td>
                <td class="config-view-col-updatedby">${escapeHtml(config.updated_by || '-')}</td>
                <td class="config-view-col-updateddate">${formatDate(config.updated_date)}</td>
                <td class="config-view-col-actions">
                    <div class="config-view-action-btns">
                        <button class="config-view-btn config-view-btn-icon config-view-btn-outline-primary"
                                data-action="edit" title="Edit">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="config-view-btn config-view-btn-icon config-view-btn-outline-danger"
                                data-action="delete" title="Delete">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        tbody.innerHTML = rows;

        // Render pagination
        renderTargetCphPagination();
    }

    function renderTargetCphPagination() {
        if (!DOM.targetCph.pagination || STATE.targetCph.totalPages <= 1) {
            hideElement(DOM.targetCph.pagination);
            return;
        }

        const currentPage = STATE.targetCph.currentPage;
        const totalPages = STATE.targetCph.totalPages;
        const paginationHtml = [];

        // Previous button
        paginationHtml.push(`
            <li class="config-view-page-item ${currentPage === 1 ? 'config-view-page-item-disabled' : ''}">
                <a class="config-view-page-link" href="#" data-page="${currentPage - 1}">Previous</a>
            </li>
        `);

        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
                paginationHtml.push(`
                    <li class="config-view-page-item ${i === currentPage ? 'config-view-page-item-active' : ''}">
                        <a class="config-view-page-link" href="#" data-page="${i}">${i}</a>
                    </li>
                `);
            } else if (i === currentPage - 3 || i === currentPage + 3) {
                paginationHtml.push(`
                    <li class="config-view-page-item config-view-page-item-disabled">
                        <span class="config-view-page-link">...</span>
                    </li>
                `);
            }
        }

        // Next button
        paginationHtml.push(`
            <li class="config-view-page-item ${currentPage === totalPages ? 'config-view-page-item-disabled' : ''}">
                <a class="config-view-page-link" href="#" data-page="${currentPage + 1}">Next</a>
            </li>
        `);

        DOM.targetCph.pagination.querySelector('ul').innerHTML = paginationHtml.join('');
        showElement(DOM.targetCph.pagination);
    }

    function updateTargetCphCount() {
        if (DOM.targetCph.countBadge) {
            const count = STATE.targetCph.data.length;
            const startIdx = (STATE.targetCph.currentPage - 1) * (SETTINGS.pageSize || 25);
            const endIdx = Math.min(startIdx + (SETTINGS.pageSize || 25), count);
            const showing = count > 0 ? `${startIdx + 1}-${endIdx} of ${count}` : '0';
            DOM.targetCph.countBadge.textContent = `${showing} configuration${count !== 1 ? 's' : ''}`;
        }
    }

    function handleTargetCphApplyFilters() {
        // Multi-select: use jQuery.val() which returns an array, or fallback to getting selected options
        if (jQuery && jQuery.fn.select2) {
            STATE.targetCph.filters.mainLob = jQuery(DOM.targetCph.lobFilter).val() || [];
            STATE.targetCph.filters.caseType = jQuery(DOM.targetCph.caseTypeFilter).val() || [];
        } else {
            // Fallback for native multi-select
            STATE.targetCph.filters.mainLob = DOM.targetCph.lobFilter
                ? Array.from(DOM.targetCph.lobFilter.selectedOptions).map(o => o.value).filter(v => v)
                : [];
            STATE.targetCph.filters.caseType = DOM.targetCph.caseTypeFilter
                ? Array.from(DOM.targetCph.caseTypeFilter.selectedOptions).map(o => o.value).filter(v => v)
                : [];
        }
        STATE.targetCph.currentPage = 1;
        loadTargetCphConfigurations();
    }

    function handleTargetCphClearFilters() {
        STATE.targetCph.filters = { mainLob: [], caseType: [] };

        if (jQuery && jQuery.fn.select2) {
            jQuery(DOM.targetCph.lobFilter).val(null).trigger('change.select2');
            jQuery(DOM.targetCph.caseTypeFilter).val(null).trigger('change.select2');
        } else {
            if (DOM.targetCph.lobFilter) {
                Array.from(DOM.targetCph.lobFilter.options).forEach(o => o.selected = false);
            }
            if (DOM.targetCph.caseTypeFilter) {
                Array.from(DOM.targetCph.caseTypeFilter.options).forEach(o => o.selected = false);
            }
        }

        // Reset to all case types when clearing filters
        loadDistinctCaseTypes();

        STATE.targetCph.currentPage = 1;
        loadTargetCphConfigurations();
    }

    function handleLobFilterChange(e) {
        // For multi-select, get all selected values
        let selectedLobs = [];
        if (jQuery && jQuery.fn.select2) {
            selectedLobs = jQuery(DOM.targetCph.lobFilter).val() || [];
        } else if (DOM.targetCph.lobFilter) {
            selectedLobs = Array.from(DOM.targetCph.lobFilter.selectedOptions).map(o => o.value).filter(v => v);
        }

        // Store the selected LOBs in state
        STATE.targetCph.filters.mainLob = selectedLobs;

        // Reset case type filter when LOB changes
        STATE.targetCph.filters.caseType = [];
        if (DOM.targetCph.caseTypeFilter) {
            DOM.targetCph.caseTypeFilter.innerHTML = '<option value="">Loading...</option>';
            if (jQuery && jQuery.fn.select2) {
                jQuery(DOM.targetCph.caseTypeFilter).val(null).trigger('change.select2');
            }
        }

        // Load case types filtered by first selected LOB (or all if none selected)
        // For simplicity, use first LOB or null for all
        const filterLob = selectedLobs.length === 1 ? selectedLobs[0] : null;
        // Pass true to only update case types, preserving LOB selection
        loadDistinctCaseTypes(filterLob, true);
    }

    function handleTargetCphAdd() {
        STATE.modal.mode = 'add';
        STATE.modal.editingId = null;

        if (DOM.targetCphModal.title) {
            DOM.targetCphModal.title.textContent = 'Add Target CPH Configuration';
        }

        resetTargetCphForm();
        showModal('target-cph-modal');
    }

    function handleTargetCphEdit(configId) {
        const config = STATE.targetCph.data.find(c => c.id === configId);
        if (!config) return;

        STATE.modal.mode = 'edit';
        STATE.modal.editingId = configId;

        if (DOM.targetCphModal.title) {
            DOM.targetCphModal.title.textContent = 'Edit Target CPH Configuration';
        }

        // Populate form
        if (DOM.targetCphModal.idField) DOM.targetCphModal.idField.value = config.id;
        if (DOM.targetCphModal.lobField) DOM.targetCphModal.lobField.value = config.main_lob;
        if (DOM.targetCphModal.caseTypeField) DOM.targetCphModal.caseTypeField.value = config.case_type;
        if (DOM.targetCphModal.targetCphField) DOM.targetCphModal.targetCphField.value = config.target_cph;

        showModal('target-cph-modal');
    }

    async function handleTargetCphSave() {
        const form = DOM.targetCphModal.form;
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const data = {
            main_lob: DOM.targetCphModal.lobField.value.trim(),
            case_type: DOM.targetCphModal.caseTypeField.value.trim(),
            target_cph: parseFloat(DOM.targetCphModal.targetCphField.value)
        };

        try {
            let url, method;
            if (STATE.modal.mode === 'edit') {
                url = URLS.targetCphUpdate.replace('{id}', STATE.modal.editingId);
                method = 'PUT';
            } else {
                url = URLS.targetCphCreate;
                method = 'POST';
            }

            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.error || 'Failed to save configuration');
            }

            hideModal('target-cph-modal');
            showSuccess(STATE.modal.mode === 'edit' ? 'Configuration updated successfully' : 'Configuration created successfully');
            loadDistinctLobs(); // Refresh LOB list
            loadTargetCphConfigurations(true); // Force refresh from server

        } catch (error) {
            console.error('Failed to save configuration:', error);
            showErrorAlert(error.message);
        }
    }

    async function handleTargetCphDelete(configId) {
        const config = STATE.targetCph.data.find(c => c.id === configId);
        if (!config) return;

        const confirmed = await Swal.fire({
            title: 'Delete Configuration?',
            html: `Are you sure you want to delete the configuration for<br><strong>${escapeHtml(config.main_lob)} / ${escapeHtml(config.case_type)}</strong>?`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#dc3545',
            cancelButtonColor: '#6c757d',
            confirmButtonText: 'Yes, delete it'
        });

        if (!confirmed.isConfirmed) return;

        try {
            const url = URLS.targetCphDelete.replace('{id}', configId);
            const response = await fetch(url, { method: 'DELETE' });
            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.error || 'Failed to delete configuration');
            }

            showSuccess('Configuration deleted successfully');
            loadDistinctLobs();
            loadTargetCphConfigurations(true); // Force refresh from server

        } catch (error) {
            console.error('Failed to delete configuration:', error);
            showErrorAlert(error.message);
        }
    }

    function handleTargetCphTableAction(e) {
        const btn = e.target.closest('[data-action]');
        if (!btn) return;

        const action = btn.dataset.action;
        const row = btn.closest('tr');
        const configId = parseInt(row.dataset.id);

        if (action === 'edit') {
            handleTargetCphEdit(configId);
        } else if (action === 'delete') {
            handleTargetCphDelete(configId);
        }
    }

    // Target CPH Bulk Add
    function handleTargetCphBulkAdd() {
        resetTargetCphBulkModal();
        addTargetCphBulkRow();
        showModal('target-cph-bulk-modal');
    }

    function addTargetCphBulkRow() {
        const container = DOM.targetCphBulkModal.rowsContainer;
        if (!container) return;

        const rowNum = container.children.length + 1;

        const rowHtml = `
            <div class="config-view-bulk-row" data-row="${rowNum}">
                <div class="config-view-bulk-row-header">
                    <span class="config-view-bulk-row-number">Row ${rowNum}</span>
                    <span class="config-view-bulk-row-remove" onclick="window.removeTargetCphBulkRow(this)">
                        <i class="fas fa-times"></i>
                    </span>
                </div>
                <div class="row">
                    <div class="col-md-5 mb-2">
                        <input type="text" class="form-control form-control-sm bulk-lob"
                               placeholder="Main LOB" maxlength="255" required>
                    </div>
                    <div class="col-md-4 mb-2">
                        <input type="text" class="form-control form-control-sm bulk-casetype"
                               placeholder="Case Type" maxlength="255" required>
                    </div>
                    <div class="col-md-3 mb-2">
                        <input type="number" class="form-control form-control-sm bulk-targetcph"
                               placeholder="Target CPH" min="0" step="0.1" required>
                    </div>
                </div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', rowHtml);
        renumberBulkRows(container);
    }

    window.removeTargetCphBulkRow = function(element) {
        const row = element.closest('.config-view-bulk-row');
        if (row) {
            row.remove();
            renumberBulkRows(DOM.targetCphBulkModal.rowsContainer);
        }
    };

    async function handleTargetCphBulkSave() {
        const container = DOM.targetCphBulkModal.rowsContainer;
        if (!container) return;

        const rows = container.querySelectorAll('.config-view-bulk-row');
        const configs = [];

        for (const row of rows) {
            const lob = row.querySelector('.bulk-lob')?.value?.trim();
            const caseType = row.querySelector('.bulk-casetype')?.value?.trim();
            const targetCph = row.querySelector('.bulk-targetcph')?.value;

            if (!lob || !caseType || !targetCph) {
                showErrorAlert('Please fill in all fields for each row');
                return;
            }

            configs.push({
                main_lob: lob,
                case_type: caseType,
                target_cph: parseFloat(targetCph)
            });
        }

        if (configs.length === 0) {
            showErrorAlert('Please add at least one configuration');
            return;
        }

        try {
            const response = await fetch(URLS.targetCphBulkCreate, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ configurations: configs })
            });

            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.error || 'Failed to create configurations');
            }

            hideModal('target-cph-bulk-modal');
            showSuccess(`Successfully created ${result.created_count} configuration(s)`);
            loadDistinctLobs();
            loadTargetCphConfigurations(true); // Force refresh from server

        } catch (error) {
            console.error('Bulk create failed:', error);
            showErrorAlert(error.message);
        }
    }

    function resetTargetCphModal() {
        STATE.modal.mode = 'add';
        STATE.modal.editingId = null;
        resetTargetCphForm();
    }

    function resetTargetCphForm() {
        if (DOM.targetCphModal.form) {
            DOM.targetCphModal.form.reset();
        }
        if (DOM.targetCphModal.idField) {
            DOM.targetCphModal.idField.value = '';
        }
    }

    function resetTargetCphBulkModal() {
        if (DOM.targetCphBulkModal.rowsContainer) {
            DOM.targetCphBulkModal.rowsContainer.innerHTML = '';
        }
        STATE.bulk.targetCphRows = 0;
    }

    // ============================================================
    // UTILITY FUNCTIONS
    // ============================================================
    function showLoading(elements) {
        if (elements.loading) elements.loading.style.display = 'block';
    }

    function hideLoading(elements) {
        if (elements.loading) elements.loading.style.display = 'none';
    }

    function showError(elements, message) {
        if (elements.error) {
            elements.error.style.display = 'flex';
            if (elements.errorMsg) elements.errorMsg.textContent = message;
        }
    }

    function hideError(elements) {
        if (elements.error) elements.error.style.display = 'none';
    }

    function showElement(el) {
        if (el) el.style.display = 'block';
    }

    function hideElement(el) {
        if (el) el.style.display = 'none';
    }

    function showModal(modalId) {
        const modalEl = document.getElementById(modalId);
        if (modalEl && bootstrap) {
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    }

    function hideModal(modalId) {
        const modalEl = document.getElementById(modalId);
        if (modalEl && bootstrap) {
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
        }
    }

    function showSuccess(message) {
        Swal.fire({
            icon: 'success',
            title: 'Success',
            text: message,
            timer: 2000,
            showConfirmButton: false
        });
    }

    function showErrorAlert(message) {
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: message
        });
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function formatPercentage(value) {
        if (value === null || value === undefined) return '-';
        return (value * 100).toFixed(1) + '%';
    }

    function formatDate(dateStr) {
        if (!dateStr) return '-';
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });
        } catch (e) {
            return dateStr;
        }
    }

    // ============================================================
    // PAGINATION HANDLERS
    // ============================================================
    function handlePaginationClick(e) {
        if (!e.target.matches('.config-view-page-link')) return;
        
        e.preventDefault();
        const page = parseInt(e.target.getAttribute('data-page'));
        if (isNaN(page)) return;

        // Determine which pagination was clicked
        const paginationContainer = e.target.closest('#month-config-pagination, #target-cph-pagination');
        if (!paginationContainer) return;

        if (paginationContainer.id === 'month-config-pagination') {
            if (page >= 1 && page <= STATE.monthConfig.totalPages && page !== STATE.monthConfig.currentPage) {
                STATE.monthConfig.currentPage = page;
                renderMonthConfigTable();
                updateMonthConfigCount();
            }
        } else if (paginationContainer.id === 'target-cph-pagination') {
            if (page >= 1 && page <= STATE.targetCph.totalPages && page !== STATE.targetCph.currentPage) {
                STATE.targetCph.currentPage = page;
                renderTargetCphTable();
                updateTargetCphCount();
            }
        }
    }

    // ============================================================
    // INITIALIZE
    // ============================================================
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
