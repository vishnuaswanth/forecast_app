/**
 * Edit View - JavaScript
 * Version: 1.0.0
 *
 * Features:
 * - Bench Allocation tab with preview/accept/reject workflow
 * - History Log tab with card-based display
 * - Select2 searchable dropdowns (single and multi-select)
 * - AJAX data fetching with proper error handling
 * - Dynamic table rendering with modified field highlighting
 * - Pagination for preview table (25 records/page)
 * - SweetAlert2 for user notifications
 * - Excel download functionality
 *
 * Dependencies:
 * - jQuery 3.6.0+
 * - Select2 4.1.0+
 * - SweetAlert2 11.0+
 * - Bootstrap 5
 * - Font Awesome
 */

(function() {
    'use strict';

    // ============================================================================
    // CONFIGURATION & GLOBAL STATE
    // ============================================================================

    // Configuration is passed from Django template via window.EDIT_VIEW_CONFIG
    // Fallback values provided in case template doesn't set them (for development/testing)
    const CONFIG = window.EDIT_VIEW_CONFIG || {
        urls: {
            allocationReports: '/forecast_app/api/edit-view/allocation-reports/',
            benchAllocationPreview: '/forecast_app/api/edit-view/bench-allocation/preview/',
            benchAllocationUpdate: '/forecast_app/api/edit-view/bench-allocation/update/',
            historyLog: '/forecast_app/api/edit-view/history-log/',
            downloadHistoryExcel: '/forecast_app/api/edit-view/history-log/{id}/download/'
        },
        settings: {
            previewPageSize: 25,
            historyPageSize: 5,
            historyInitialLoad: 20,
            historyLazyLoadSize: 10,
            maxUserNotesLength: 500,
            enableUserNotes: true
        }
    };

    // Validate that CONFIG was properly loaded from Django
    if (!window.EDIT_VIEW_CONFIG) {
        console.warn('Edit View: window.EDIT_VIEW_CONFIG not found. Using fallback configuration. URLs may not work correctly.');
    }

    const STATE = {
        // Preview data
        currentPreviewData: null,
        currentSelectedReport: null, // {month: "April", year: 2025}
        previewCurrentPage: 1,
        previewTotalPages: 0,
        allPreviewRecords: [],        // All fetched records
        filteredPreviewRecords: [],   // After LOB/Case Type filters
        previewFilters: {
            lobs: [],                 // Selected LOB values
            caseTypes: []             // Selected Case Type values
        },

        // History data
        currentHistoryData: null,
        historyCurrentPage: 1,
        historyTotalPages: 0,
        loadedHistoryCount: 0,      // Track loaded entries for lazy loading
        totalHistoryCount: 0,       // Total available entries
        historyFilters: {
            month: null,
            year: null,
            changeTypes: []
        },

        // Change types with colors
        availableChangeTypes: null,  // Populated by loadAvailableChangeTypes()

        // Loading states
        isLoadingPreview: false,
        isLoadingHistory: false,
        isSubmitting: false,

        // Cache (optional - can add later)
        cache: new Map(),
        cacheTTL: 300000,  // 5 minutes

        // Target CPH state
        cph: {
            currentSelectedReport: null,      // {month: "April", year: 2025}
            allCphRecords: [],                // All CPH records from API
            filteredCphRecords: [],           // After LOB/Case Type filters
            modifiedCphRecords: new Map(),    // Map<id, modified_record> - only changed
            currentPage: 1,
            totalPages: 0,
            filters: {
                lobs: [],
                caseTypes: []
            },

            // Preview state
            previewData: null,
            previewCurrentPage: 1,
            previewTotalPages: 0,
            allPreviewRecords: [],
            filteredPreviewRecords: [],
            previewFilters: {
                lobs: [],
                caseTypes: []
            }
        },

        // Forecast Reallocation state
        reallocation: {
            currentSelectedReport: null,      // {month: "April", year: 2025}
            allRecords: [],                   // All records from API
            filteredRecords: [],              // After LOB/State/Case Type filters
            modifiedRecords: new Map(),       // Map<case_id, modified_record> - only changed
            visibleMonths: [],                // Array of visible month keys
            allMonths: [],                    // All available months
            monthsMapping: {},                // {month1: 'Jun-25', month2: 'Jul-25', ...}
            currentPage: 1,
            totalPages: 0,
            filters: {
                mainLobs: [],                 // Selected Main LOBs
                states: [],                   // Selected States
                caseTypes: []                 // Selected Case Types
            },
            filterOptions: {                  // Available filter options from API
                mainLobs: [],
                states: [],
                caseTypes: []
            },

            // Preview state
            previewData: null,
            previewCurrentPage: 1,
            previewTotalPages: 0,
            allPreviewRecords: [],
            filteredPreviewRecords: [],
            previewFilters: {
                lobs: [],
                caseTypes: []
            }
        }
    };

    // ============================================================================
    // PREVIEW CONFIGURATIONS (GENERIC SYSTEM)
    // ============================================================================

    /**
     * Configuration objects for preview systems
     * Enables code reuse between Bench Allocation and Target CPH previews
     */
    const PREVIEW_CONFIGS = {
        benchAllocation: {
            // DOM element references
            dom: {
                loading: 'previewLoading',
                error: 'previewError',
                errorMessage: 'previewErrorMessage',
                container: 'previewContainer',
                tableHead: 'previewTableHead',
                tableBody: 'previewTableBody',
                pagination: 'previewPagination',
                filters: 'previewFilters',
                lobFilter: 'previewLobFilter',
                caseTypeFilter: 'previewCaseTypeFilter',
                clearFiltersBtn: 'clearPreviewFiltersBtn',
                modifiedCountBadge: 'modifiedCountBadge',
                summaryText: 'summaryText',
                actionSummaryCount: 'actionSummaryCount',
                overallChanges: 'overallChanges',
                monthChangesContainer: 'month-changes-container'
            },

            // State path configuration
            state: {
                basePath: 'STATE',
                allRecords: 'allPreviewRecords',
                filteredRecords: 'filteredPreviewRecords',
                currentPage: 'previewCurrentPage',
                totalPages: 'previewTotalPages',
                filters: 'previewFilters'
            },

            // Field name mapping (canonical → actual field names)
            // API spec uses: forecast, fte_req, fte_avail, capacity
            fields: {
                forecast: 'forecast',
                fteReq: 'fte_req',
                fteAvail: 'fte_avail',
                capacity: 'capacity'
            },

            // Fixed columns configuration
            fixedColumns: [
                { key: 'main_lob', label: 'Main LOB', editable: false },
                { key: 'state', label: 'State', editable: false },
                { key: 'case_type', label: 'Case Type', editable: false },
                { key: 'target_cph', label: 'Target CPH', editable: true, align: 'text-center' }
            ],

            // Month columns configuration
            monthColumns: [
                { key: 'forecast', label: 'CF', editable: false },
                { key: 'fteReq', label: 'FTE Req', editable: true },
                { key: 'fteAvail', label: 'FTE Avail', editable: true },
                { key: 'capacity', label: 'Cap', editable: true }
            ],

            // Feature flags
            features: {
                showTotalsRow: true,
                showMonthwiseSummary: true,
                summaryStyle: 'cards',
                cascadingFilters: true
            },

            // Data access pattern
            dataAccess: {
                monthDataPath: 'direct'  // 'direct' = record[month]
            }
        },

        targetCph: {
            // DOM element references
            dom: {
                loading: 'cphPreviewLoading',
                error: 'cphPreviewError',
                errorMessage: 'cphPreviewErrorMessage',
                container: 'cphPreviewContainer',
                tableHead: 'cphPreviewTableHead',
                tableBody: 'cphPreviewTableBody',
                pagination: 'cphPreviewPagination',
                filters: 'cphPreviewFilters',
                lobFilter: 'cphPreviewLobFilter',
                caseTypeFilter: 'cphPreviewCaseTypeFilter',
                clearFiltersBtn: 'clearCphPreviewFiltersBtn',
                modifiedCountBadge: 'cphPreviewModifiedCountBadge',
                summaryText: 'cphSummaryText',
                actionSummaryCount: 'cphActionSummaryCount',
                overallChanges: 'cphOverallChanges',
                monthChangesContainer: 'cph-month-changes-container'
            },

            // State path configuration
            state: {
                basePath: 'STATE.cph',
                allRecords: 'allPreviewRecords',
                filteredRecords: 'filteredPreviewRecords',
                currentPage: 'previewCurrentPage',
                totalPages: 'previewTotalPages',
                filters: 'previewFilters'
            },

            // Field name mapping (canonical → actual field names)
            // API spec uses: forecast, fte_req, fte_avail, capacity (same as bench allocation)
            fields: {
                forecast: 'forecast',
                fteReq: 'fte_req',
                fteAvail: 'fte_avail',
                capacity: 'capacity'
            },

            // Fixed columns configuration - SAME AS BENCH ALLOCATION
            fixedColumns: [
                { key: 'main_lob', label: 'Main LOB', editable: false },
                { key: 'state', label: 'State', editable: false },
                { key: 'case_type', label: 'Case Type', editable: false },
                { key: 'target_cph', label: 'Target CPH', editable: true, align: 'text-center' }
            ],

            // Month columns configuration - SAME AS BENCH ALLOCATION
            monthColumns: [
                { key: 'forecast', label: 'CF', editable: false },
                { key: 'fteReq', label: 'FTE Req', editable: true },
                { key: 'fteAvail', label: 'FTE Avail', editable: true },
                { key: 'capacity', label: 'Cap', editable: true }
            ],

            // Feature flags - SAME AS BENCH ALLOCATION
            features: {
                showTotalsRow: true,           // CHANGED: Enable totals row
                showMonthwiseSummary: true,
                summaryStyle: 'cards',         // CHANGED: Use card-based summary
                cascadingFilters: true
            },

            // Data access pattern
            dataAccess: {
                monthDataPath: 'direct'  // FIX: Changed from 'nested' to 'direct'
            }
        },

        forecastReallocation: {
            // DOM element references
            dom: {
                loading: 'reallocationPreviewLoading',
                error: 'reallocationPreviewError',
                errorMessage: 'reallocationPreviewErrorMessage',
                container: 'reallocationPreviewContainer',
                tableHead: 'reallocationPreviewTableHead',
                tableBody: 'reallocationPreviewTableBody',
                pagination: 'reallocationPreviewPagination',
                filters: 'reallocationPreviewFilters',
                lobFilter: 'reallocationPreviewLobFilter',
                caseTypeFilter: 'reallocationPreviewCaseTypeFilter',
                clearFiltersBtn: 'clearReallocationPreviewFiltersBtn',
                modifiedCountBadge: 'reallocationPreviewModifiedCountBadge',
                summaryText: 'reallocationSummaryText',
                actionSummaryCount: 'reallocationActionSummaryCount',
                overallChanges: 'reallocationOverallChanges',
                monthChangesContainer: 'reallocation-month-changes-container'
            },

            // State path configuration
            state: {
                basePath: 'STATE.reallocation',
                allRecords: 'allPreviewRecords',
                filteredRecords: 'filteredPreviewRecords',
                currentPage: 'previewCurrentPage',
                totalPages: 'previewTotalPages',
                filters: 'previewFilters'
            },

            // Field name mapping (canonical → actual field names)
            fields: {
                forecast: 'forecast',
                fteReq: 'fte_req',
                fteAvail: 'fte_avail',
                capacity: 'capacity'
            },

            // Fixed columns configuration
            fixedColumns: [
                { key: 'main_lob', label: 'Main LOB', editable: false },
                { key: 'state', label: 'State', editable: false },
                { key: 'case_type', label: 'Case Type', editable: false },
                { key: 'target_cph', label: 'Target CPH', editable: true, align: 'text-center' }
            ],

            // Month columns configuration
            monthColumns: [
                { key: 'forecast', label: 'CF', editable: false },
                { key: 'fteReq', label: 'FTE Req', editable: false },
                { key: 'fteAvail', label: 'FTE Avail', editable: true },
                { key: 'capacity', label: 'Cap', editable: false }
            ],

            // Feature flags
            features: {
                showTotalsRow: true,
                showMonthwiseSummary: true,
                summaryStyle: 'cards',
                cascadingFilters: true
            },

            // Data access pattern
            dataAccess: {
                monthDataPath: 'direct'
            }
        }
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

    async function initializeApp() {
        console.log('Edit View: Initializing v1.0.0...');

        cacheDOMElements();
        initializeSelect2();
        attachEventListeners();

        // Show spinner while loading dropdown data
        showElement(DOM.initialDataLoading);

        try {
            // Load dropdown data in parallel
            await Promise.all([
                loadAllocationReports(),
                loadAvailableChangeTypes()
            ]);
        } finally {
            // Hide spinner after all data is loaded (success or failure)
            hideElement(DOM.initialDataLoading);
        }

        console.log('Edit View: Initialization complete');
    }

    function cacheDOMElements() {
        // Initial data loading spinner
        DOM.initialDataLoading = $('#initial-data-loading');

        // Bench Allocation tab elements
        DOM.allocationReportSelect = $('#allocation-report-select');
        DOM.runAllocationBtn = $('#run-allocation-btn');
        DOM.previewLoading = $('#preview-loading');
        DOM.previewError = $('#preview-error');
        DOM.previewErrorMessage = $('#preview-error-message');
        DOM.previewContainer = $('#preview-container');
        DOM.previewTableHead = $('#preview-table-head');
        DOM.previewTableBody = $('#preview-table-body');
        DOM.previewPagination = $('#preview-pagination');
        DOM.modifiedCountBadge = $('#modified-count-badge');
        DOM.previewSummary = $('#preview-summary');
        DOM.summaryText = $('#summary-text');

        // Preview filters
        DOM.previewLobFilter = $('#preview-lob-filter');
        DOM.previewCaseTypeFilter = $('#preview-case-type-filter');
        DOM.clearPreviewFiltersBtn = $('#clear-preview-filters-btn');
        DOM.previewFilters = $('#preview-filters');
        DOM.overallChanges = $('#overall-changes');
        DOM.totalFteChange = $('#total-fte-change');
        DOM.totalCapacityChange = $('#total-capacity-change');

        // Actions section
        DOM.actionsContainer = $('#actions-container');
        DOM.userNotesInput = $('#user-notes-input');
        DOM.notesCharCount = $('#notes-char-count');
        DOM.actionSummaryCount = $('#action-summary-count');
        DOM.rejectBtn = $('#reject-btn');
        DOM.acceptBtn = $('#accept-btn');

        // History Log tab elements
        DOM.historyReportSelect = $('#history-report-select');
        DOM.historyChangeTypeSelect = $('#history-change-type-select');
        DOM.applyHistoryFiltersBtn = $('#apply-history-filters-btn');
        DOM.historyLoading = $('#history-loading');
        DOM.historyError = $('#history-error');
        DOM.historyErrorMessage = $('#history-error-message');
        DOM.historyCardsContainer = $('#history-cards-container');
        DOM.historyNoResults = $('#history-no-results');
        DOM.historyLoadMoreContainer = $('#history-load-more-container');

        // Tab buttons
        DOM.benchAllocationTabBtn = $('#bench-allocation-tab-btn');
        DOM.targetCphTabBtn = $('#target-cph-tab-btn');
        DOM.historyLogTabBtn = $('#history-log-tab-btn');

        // Target CPH tab elements
        DOM.cphReportSelect = $('#cph-report-select');
        DOM.loadCphDataBtn = $('#load-cph-data-btn');
        DOM.cphDataLoading = $('#cph-data-loading');
        DOM.cphDataError = $('#cph-data-error');
        DOM.cphDataErrorMessage = $('#cph-data-error-message');
        DOM.cphDataContainer = $('#cph-data-container');
        DOM.cphTable = $('#cph-table');
        DOM.cphTableBody = $('#cph-table-body');
        DOM.cphPagination = $('#cph-pagination');
        DOM.cphModifiedCountBadge = $('#cph-modified-count-badge');
        DOM.submitCphChangesBtn = $('#submit-cph-changes-btn');

        // CPH filters
        DOM.cphFilters = $('#cph-filters');
        DOM.cphLobFilter = $('#cph-lob-filter');
        DOM.cphCaseTypeFilter = $('#cph-case-type-filter');
        DOM.clearCphFiltersBtn = $('#clear-cph-filters-btn');

        // CPH preview elements
        DOM.cphPreviewLoading = $('#cph-preview-loading');
        DOM.cphPreviewError = $('#cph-preview-error');
        DOM.cphPreviewErrorMessage = $('#cph-preview-error-message');
        DOM.cphPreviewContainer = $('#cph-preview-container');
        DOM.cphPreviewTableHead = $('#cph-preview-table-head');
        DOM.cphPreviewTableBody = $('#cph-preview-table-body');
        DOM.cphPreviewPagination = $('#cph-preview-pagination');
        DOM.cphPreviewModifiedCountBadge = $('#cph-preview-modified-count-badge');
        DOM.cphPreviewSummary = $('#cph-preview-summary');
        DOM.cphSummaryText = $('#cph-summary-text');
        DOM.cphOverallChanges = $('#cph-overall-changes');
        DOM.cphMonthChangesContainer = $('#cph-month-changes-container');

        // CPH preview filters
        DOM.cphPreviewFilters = $('#cph-preview-filters');
        DOM.cphPreviewLobFilter = $('#cph-preview-lob-filter');
        DOM.cphPreviewCaseTypeFilter = $('#cph-preview-case-type-filter');
        DOM.clearCphPreviewFiltersBtn = $('#clear-cph-preview-filters-btn');

        // CPH actions section
        DOM.cphActionsContainer = $('#cph-actions-container');
        DOM.cphUserNotesInput = $('#cph-user-notes-input');
        DOM.cphNotesCharCount = $('#cph-notes-char-count');
        DOM.cphActionSummaryCount = $('#cph-action-summary-count');
        DOM.cphForecastRowsCount = $('#cph-forecast-rows-count');
        DOM.cphRejectBtn = $('#cph-reject-btn');
        DOM.cphAcceptBtn = $('#cph-accept-btn');

        // Forecast Reallocation tab elements
        DOM.reallocationTabBtn = $('#forecast-reallocation-tab-btn');
        DOM.reallocationReportSelect = $('#reallocation-report-select');
        DOM.reallocationLobFilter = $('#reallocation-lob-filter');
        DOM.reallocationCaseTypeFilter = $('#reallocation-case-type-filter');
        DOM.reallocationStateFilter = $('#reallocation-state-filter');
        DOM.loadReallocationDataBtn = $('#load-reallocation-data-btn');
        DOM.reallocationDataLoading = $('#reallocation-data-loading');
        DOM.reallocationDataError = $('#reallocation-data-error');
        DOM.reallocationDataErrorMessage = $('#reallocation-data-error-message');
        DOM.reallocationDataContainer = $('#reallocation-data-container');
        DOM.reallocationTable = $('#reallocation-table');
        DOM.reallocationTableHead = $('#reallocation-table-head');
        DOM.reallocationTableBody = $('#reallocation-table-body');
        DOM.reallocationPagination = $('#reallocation-pagination');
        DOM.reallocationModifiedCountBadge = $('#reallocation-modified-count-badge');
        DOM.showReallocationPreviewBtn = $('#show-reallocation-preview-btn');

        // Reallocation month selector
        DOM.reallocationMonthSelector = $('#reallocation-month-selector');
        DOM.reallocationMonthCheckboxes = $('#reallocation-month-checkboxes');

        // Reallocation preview elements
        DOM.reallocationPreviewLoading = $('#reallocation-preview-loading');
        DOM.reallocationPreviewError = $('#reallocation-preview-error');
        DOM.reallocationPreviewErrorMessage = $('#reallocation-preview-error-message');
        DOM.reallocationPreviewContainer = $('#reallocation-preview-container');
        DOM.reallocationPreviewTableHead = $('#reallocation-preview-table-head');
        DOM.reallocationPreviewTableBody = $('#reallocation-preview-table-body');
        DOM.reallocationPreviewPagination = $('#reallocation-preview-pagination');
        DOM.reallocationPreviewModifiedCountBadge = $('#reallocation-preview-modified-count-badge');
        DOM.reallocationPreviewSummary = $('#reallocation-preview-summary');
        DOM.reallocationSummaryText = $('#reallocation-summary-text');
        DOM.reallocationOverallChanges = $('#reallocation-overall-changes');
        DOM.reallocationMonthChangesContainer = $('#reallocation-month-changes-container');

        // Reallocation preview filters
        DOM.reallocationPreviewFilters = $('#reallocation-preview-filters');
        DOM.reallocationPreviewLobFilter = $('#reallocation-preview-lob-filter');
        DOM.reallocationPreviewCaseTypeFilter = $('#reallocation-preview-case-type-filter');
        DOM.clearReallocationPreviewFiltersBtn = $('#clear-reallocation-preview-filters-btn');

        // Reallocation actions section
        DOM.reallocationActionsContainer = $('#reallocation-actions-container');
        DOM.reallocationUserNotesInput = $('#reallocation-user-notes-input');
        DOM.reallocationNotesCharCount = $('#reallocation-notes-char-count');
        DOM.reallocationActionSummaryCount = $('#reallocation-action-summary-count');
        DOM.reallocationRejectBtn = $('#reallocation-reject-btn');
        DOM.reallocationAcceptBtn = $('#reallocation-accept-btn');
    }

    function initializeSelect2() {
        if (typeof $.fn.select2 === 'undefined') {
            console.error('Edit View: Select2 not loaded. Dropdowns will not be searchable.');
            return;
        }

        // Single-select dropdowns
        $('.edit-view-select2').each(function() {
            $(this).select2({
                theme: 'bootstrap-5',
                placeholder: $(this).attr('data-placeholder') || '-- Select --',
                allowClear: $(this).attr('id') === 'history-report-select', // Only history filter allows clear
                width: '100%',
                minimumResultsForSearch: 5
            });
        });

        // Multi-select dropdowns
        $('.edit-view-select2-multi').each(function() {
            $(this).select2({
                theme: 'bootstrap-5',
                placeholder: $(this).attr('data-placeholder') || 'Select options...',
                allowClear: true,
                closeOnSelect: false,  // Keep dropdown open after selection
                width: '100%'
            });
        });

        // Multi-select with checkboxes
        $('.edit-view-select2-multi-checkbox').each(function() {
            $(this).select2({
                theme: 'bootstrap-5',
                placeholder: $(this).attr('data-placeholder') || 'Select options...',
                allowClear: true,
                closeOnSelect: false,
                width: '100%'
            });
        });

        // Add Select All functionality
        $(document).on('select2:open', '.edit-view-select2-multi-checkbox', function() {
            const container = $('.select2-results__options');

            if (container.find('.select-all-option').length === 0) {
                container.prepend(
                    '<li class="select2-results__option select-all-option" role="option">Select All</li>'
                );
            }
        });

        $(document).on('click', '.select-all-option', function(e) {
            e.stopPropagation();
            const select = $('.select2-hidden-accessible:focus');
            const allValues = select.find('option').map(function() {
                return $(this).val();
            }).get();
            select.val(allValues).trigger('change');
        });

        console.log('Edit View: Select2 initialized');
    }

    function attachEventListeners() {
        // Bench Allocation tab
        DOM.runAllocationBtn.on('click', handleRunAllocation);
        DOM.rejectBtn.on('click', handleReject);
        DOM.acceptBtn.on('click', handleAccept);
        DOM.userNotesInput.on('input', handleNotesInput);

        // Preview filters with cascading behavior
        DOM.previewLobFilter.on('select2:close', function() {
            updateCascadingFilters('lob');
            applyPreviewFilters();
        });

        DOM.previewCaseTypeFilter.on('select2:close', function() {
            updateCascadingFilters('caseType');
            applyPreviewFilters();
        });

        DOM.clearPreviewFiltersBtn.on('click', clearPreviewFilters);

        // Target CPH tab
        DOM.loadCphDataBtn.on('click', handleLoadCphData);
        DOM.submitCphChangesBtn.on('click', handleSubmitCphChanges);
        DOM.cphRejectBtn.on('click', handleCphReject);
        DOM.cphAcceptBtn.on('click', handleCphAccept);
        DOM.cphUserNotesInput.on('input', handleCphNotesInput);

        // CPH filters with cascading behavior
        DOM.cphLobFilter.on('select2:close', function() {
            updateCphCascadingFilters('lob');
            applyCphFilters();
        });

        DOM.cphCaseTypeFilter.on('select2:close', function() {
            updateCphCascadingFilters('caseType');
            applyCphFilters();
        });

        DOM.clearCphFiltersBtn.on('click', clearCphFilters);

        // CPH preview filters
        DOM.cphPreviewLobFilter.on('select2:close', function() {
            updateCphPreviewCascadingFilters('lob');
            applyCphPreviewFilters();
        });

        DOM.cphPreviewCaseTypeFilter.on('select2:close', function() {
            updateCphPreviewCascadingFilters('caseType');
            applyCphPreviewFilters();
        });

        DOM.clearCphPreviewFiltersBtn.on('click', clearCphPreviewFilters);

        // History Log tab
        DOM.applyHistoryFiltersBtn.on('click', handleApplyHistoryFilters);

        // Forecast Reallocation tab
        DOM.loadReallocationDataBtn.on('click', handleLoadReallocationData);
        DOM.showReallocationPreviewBtn.on('click', handleShowReallocationPreview);
        DOM.reallocationRejectBtn.on('click', handleReallocationReject);
        DOM.reallocationAcceptBtn.on('click', handleReallocationAccept);
        DOM.reallocationUserNotesInput.on('input', handleReallocationNotesInput);

        // Reallocation preview filters
        DOM.reallocationPreviewLobFilter.on('select2:close', applyReallocationPreviewFilters);
        DOM.reallocationPreviewCaseTypeFilter.on('select2:close', applyReallocationPreviewFilters);
        DOM.clearReallocationPreviewFiltersBtn.on('click', clearReallocationPreviewFilters);

        // Tab switching
        DOM.historyLogTabBtn.on('shown.bs.tab', function() {
            // Load history when tab is activated (only first time)
            if (!STATE.currentHistoryData) {
                loadHistoryLog();
            }
        });

        // Reallocation tab - load filter options when activated
        DOM.reallocationTabBtn.on('shown.bs.tab', function() {
            // Populate report dropdown if not already done
            if (DOM.reallocationReportSelect.find('option').length <= 1) {
                populateReallocationReportDropdown();
            }
        });

        // Event delegation for dynamically created elements
        $(document).on('click', '.edit-view-preview-pagination .edit-view-page-link', handlePreviewPageClick);
        $(document).on('click', '#history-load-more-btn', handleHistoryLoadMore);
        $(document).on('click', '.edit-view-download-excel-btn', handleExcelDownload);
        $(document).on('click', '.edit-view-cph-pagination .edit-view-page-link', handleCphPageClick);
        $(document).on('click', '.cph-increment-btn', handleCphIncrement);
        $(document).on('click', '.cph-decrement-btn', handleCphDecrement);
        $(document).on('input', '.cph-modified-input', handleCphInputChange);
        $(document).on('click', '.edit-view-cph-preview-pagination .edit-view-page-link', handleCphPreviewPageClick);

        // Reallocation table events
        $(document).on('click', '.edit-view-reallocation-pagination .edit-view-page-link', handleReallocationPageClick);
        $(document).on('click', '.edit-view-reallocation-preview-pagination .edit-view-page-link', handleReallocationPreviewPageClick);
        $(document).on('click', '.reallocation-increment-btn', handleReallocationIncrement);
        $(document).on('click', '.reallocation-decrement-btn', handleReallocationDecrement);
        $(document).on('input', '.reallocation-input', handleReallocationInputChange);
        $(document).on('change', '.reallocation-month-checkbox', handleReallocationMonthVisibility);

        console.log('Edit View: Event listeners attached');
    }

    // ============================================================================
    // ERROR HANDLING UTILITIES
    // ============================================================================

    /**
     * Extract error message from various response formats
     * @param {Response} response - Fetch API response object
     * @returns {Promise<Object|string>} Extracted error message or object with error and recommendation
     */
    async function extractErrorMessage(response) {
        try {
            const data = await response.json();

            // Handle detail object with error and recommendation (bench allocation preview)
            if (data.detail && typeof data.detail === 'object' && !Array.isArray(data.detail)) {
                if (data.detail.error || data.detail.recommendation) {
                    return {
                        error: data.detail.error || 'An error occurred',
                        recommendation: data.detail.recommendation || null
                    };
                }
            }

            // Try different error message fields
            if (data.error) return data.error;
            if (data.message) return data.message;
            if (data.detail && typeof data.detail === 'string') return data.detail;

            // Handle validation errors (array format)
            if (data.errors && Array.isArray(data.errors)) {
                return data.errors.map(e => e.message || e.msg || e).join('; ');
            }

            // Handle FastAPI validation errors (array format)
            if (data.detail && Array.isArray(data.detail)) {
                return data.detail.map(e => {
                    const field = e.loc ? e.loc.join('.') : 'Field';
                    return `${field}: ${e.msg}`;
                }).join('; ');
            }

            return `Request failed with status ${response.status}`;
        } catch (parseError) {
            // If JSON parsing fails, return generic error
            return `Request failed with status ${response.status}`;
        }
    }

    /**
     * Show error in alert element
     * @param {jQuery} errorElement - The error alert element
     * @param {jQuery} messageElement - The error message element
     * @param {string} message - Error message to display
     */
    function showInlineError(errorElement, messageElement, message) {
        messageElement.text(message);
        showElement(errorElement);
    }

    /**
     * Show error using SweetAlert
     * @param {string} title - Alert title
     * @param {string} message - Error message
     * @param {string} context - Additional context (optional)
     */
    function showErrorDialog(title, message, context = null) {
        const htmlContent = context
            ? `<p>${message}</p><p class="text-muted small mt-2">${context}</p>`
            : `<p>${message}</p>`;

        Swal.fire({
            icon: 'error',
            title: title,
            html: htmlContent,
            confirmButtonColor: '#dc3545',
            confirmButtonText: 'OK'
        });
    }

    /**
     * Show warning using SweetAlert
     * @param {string} title - Alert title
     * @param {string} message - Warning message
     */
    function showWarningDialog(title, message) {
        Swal.fire({
            icon: 'warning',
            title: title,
            html: `<p>${message}</p>`,
            confirmButtonColor: '#ffc107',
            confirmButtonText: 'OK'
        });
    }

    // ============================================================================
    // ALLOCATION REPORTS (DROPDOWN)
    // ============================================================================

    async function loadAllocationReports() {
        console.log('Edit View: Loading allocation reports...');

        try {
            const response = await fetch(CONFIG.urls.allocationReports, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                const errorMsg = await extractErrorMessage(response);
                throw new Error(errorMsg);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.message || 'Failed to load allocation reports');
            }

            if (!data.data || data.data.length === 0) {
                console.warn('Edit View: No allocation reports available');
                showWarningDialog(
                    'No Reports Available',
                    'There are no allocation reports available at this time. Please contact your administrator.'
                );
                return;
            }

            // Populate dropdown
            DOM.allocationReportSelect.empty().append('<option value="">-- Select Report Month --</option>');
            DOM.cphReportSelect.empty().append('<option value="">-- Select Report Month --</option>');
            DOM.historyReportSelect.empty().append('<option value="">-- All Reports --</option>');

            data.data.forEach(report => {
                const option = $('<option>').val(report.value).text(report.display);
                DOM.allocationReportSelect.append(option.clone());
                DOM.cphReportSelect.append(option.clone());
                DOM.historyReportSelect.append(option.clone());
            });

            console.log(`Edit View: Loaded ${data.total} allocation reports`);

        } catch (error) {
            console.error('Edit View: Error loading allocation reports', error);
            showErrorDialog(
                'Failed to Load Reports',
                'Unable to load allocation report options. Please refresh the page and try again.',
                `Error: ${error.message}`
            );
        }
    }

    // ============================================================================
    // AVAILABLE CHANGE TYPES (FOR HISTORY LOG FILTER)
    // ============================================================================

    async function loadAvailableChangeTypes() {
        console.log('Edit View: Loading available change types...');

        try {
            const response = await fetch(CONFIG.urls.availableChangeTypes, {
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

            if (!data.success || !data.data || data.data.length === 0) {
                console.warn('Edit View: No change types available');
                return;
            }

            // Store change types in STATE for later use by getDynamicChangeTypeColor
            STATE.availableChangeTypes = data.data;

            // Populate history log change type filter dropdown
            DOM.historyChangeTypeSelect.empty();

            data.data.forEach(changeType => {
                const option = $('<option>')
                    .val(changeType.value)
                    .text(changeType.display)
                    .attr('data-color', changeType.color);
                DOM.historyChangeTypeSelect.append(option);
            });

            console.log(`Edit View: Loaded ${data.total} change types`);

        } catch (error) {
            console.error('Edit View: Error loading change types', error);
            // Non-critical error - just log it, don't show alert
            console.warn('Change type colors will use fallback logic');
        }
    }

    // ============================================================================
    // BENCH ALLOCATION - RUN ALLOCATION
    // ============================================================================

    async function handleRunAllocation() {
        console.log('Edit View: Run Allocation clicked');

        const reportValue = DOM.allocationReportSelect.val();

        // Validate
        if (!reportValue) {
            await Swal.fire({
                icon: 'warning',
                title: 'Selection Required',
                text: 'Please select an allocation report first.',
                confirmButtonColor: '#0d6efd'
            });
            return;
        }

        if (STATE.isLoadingPreview) {
            console.log('Edit View: Already loading preview, ignoring click');
            return;
        }

        // Parse report value (format: "YYYY-MM")
        const [yearStr, monthNum] = reportValue.split('-');
        const year = parseInt(yearStr);
        const monthNames = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December'];
        const month = monthNames[parseInt(monthNum)];

        STATE.currentSelectedReport = { month, year };

        await loadPreviewData(month, year);
    }

    async function loadPreviewData(month, year) {
        console.log(`Edit View: Loading preview for ${month} ${year}`);

        STATE.isLoadingPreview = true;
        showElement(DOM.previewLoading);
        hideElement(DOM.previewError);
        hideElement(DOM.previewContainer);
        hideElement(DOM.actionsContainer);

        try {
            const response = await fetch(CONFIG.urls.benchAllocationPreview, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin',
                body: JSON.stringify({ month, year })
            });

            if (!response.ok) {
                const errorMsg = await extractErrorMessage(response);

                // Check if errorMsg is an object with error and recommendation
                if (typeof errorMsg === 'object' && errorMsg.error) {
                    const errorObj = {
                        message: errorMsg.error,
                        recommendation: errorMsg.recommendation
                    };
                    throw errorObj;
                }

                throw new Error(errorMsg);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.message || 'Preview calculation failed');
            }

            // Check if there are any modified records
            if (!data.modified_records || data.modified_records.length === 0) {
                showInlineError(
                    DOM.previewError,
                    DOM.previewErrorMessage,
                    'No bench allocation changes detected. All resources are already optimally allocated.'
                );
                return;
            }

            // Store preview data
            STATE.currentPreviewData = data;
            STATE.previewCurrentPage = 1;
            STATE.previewTotalPages = Math.ceil(data.total_modified / CONFIG.settings.previewPageSize);

            // Render preview
            renderPreviewTable(data);
            showElement(DOM.previewContainer);
            showElement(DOM.actionsContainer);

            console.log(`Edit View: Preview loaded - ${data.total_modified} records modified`);

        } catch (error) {
            console.error('Edit View: Error loading preview', error);

            // Check if error has recommendation (from API detail object)
            if (error.message && error.recommendation) {
                const errorMessage = `<strong>${error.message}</strong><br><br><em>Recommendation:</em> ${error.recommendation}`;
                DOM.previewErrorMessage.html(errorMessage);
                showElement(DOM.previewError);
            } else {
                showInlineError(
                    DOM.previewError,
                    DOM.previewErrorMessage,
                    error.message || 'Failed to load preview. Please try again.'
                );
            }

        } finally {
            STATE.isLoadingPreview = false;
            hideElement(DOM.previewLoading);
        }
    }

    // ============================================================================
    // PREVIEW FILTERS
    // ============================================================================

    // NOTE: populatePreviewFilters removed - superseded by populateGenericFilters
    // NOTE: initializeFilterSelect2 removed - superseded by generic system

    function updateCascadingFilters(changedFilter) {
        updateGenericCascadingFilters(changedFilter, PREVIEW_CONFIGS.benchAllocation);
    }

    function applyPreviewFilters() {
        const config = PREVIEW_CONFIGS.benchAllocation;
        applyGenericFilters(config);
        renderPreviewTableWithFilteredData();
    }

    function renderPreviewTableWithFilteredData() {
        const config = PREVIEW_CONFIGS.benchAllocation;

        // Create a mock data object for rendering
        const data = {
            modified_records: STATE.allPreviewRecords,
            total_modified: STATE.allPreviewRecords.length
        };

        // Render using generic system
        renderGenericPreviewTable(data, config);

        // Update badges
        const totalOriginal = STATE.allPreviewRecords.length;
        const totalFiltered = STATE.filteredPreviewRecords.length;
        DOM.modifiedCountBadge.text(`${totalOriginal} ${totalOriginal === 1 ? 'record' : 'records'} modified`);
        DOM.summaryText.text(`${totalOriginal} ${totalOriginal === 1 ? 'record' : 'records'} modified (${totalFiltered} shown)`);
        DOM.actionSummaryCount.text(totalOriginal);
    }

    // NOTE: calculateMonthwiseSummaryFromRecords removed - superseded by generic preview system
    // NOTE: updateMonthwiseChanges removed - superseded by generic preview system

    function clearPreviewFilters() {
        const config = PREVIEW_CONFIGS.benchAllocation;

        DOM.previewLobFilter.val(null).trigger('change');
        DOM.previewCaseTypeFilter.val(null).trigger('change');
        STATE.previewFilters = { lobs: [], caseTypes: [] };

        // Repopulate filters with all options
        populateGenericFilters(STATE.allPreviewRecords, config);

        // Apply empty filters
        applyPreviewFilters();

        console.log('Edit View: Filters cleared');
    }

    // ============================================================================
    // GENERIC PREVIEW SYSTEM - UTILITY FUNCTIONS
    // ============================================================================

    /**
     * Get nested state value using dot notation path
     * @param {string} basePath - Base path like 'STATE' or 'STATE.cph'
     * @param {string} property - Property name like 'allPreviewRecords'
     * @returns {*} The value at that path
     */
    function getStateValue(basePath, property) {
        const parts = basePath.split('.');
        let current = STATE;  // Start with STATE object, not window

        // Skip first part if it's 'STATE' since we already start there
        const startIndex = parts[0] === 'STATE' ? 1 : 0;

        for (let i = startIndex; i < parts.length; i++) {
            current = current[parts[i]];
            if (current === undefined) return undefined;
        }

        return current[property];
    }

    /**
     * Set nested state value using dot notation path
     */
    function setStateValue(basePath, property, value) {
        const parts = basePath.split('.');
        let current = STATE;  // Start with STATE object, not window

        // Skip first part if it's 'STATE' since we already start there
        const startIndex = parts[0] === 'STATE' ? 1 : 0;

        for (let i = startIndex; i < parts.length; i++) {
            current = current[parts[i]];
        }

        current[property] = value;
    }

    /**
     * Get month data from record based on access pattern
     * @param {Object} record - Data record
     * @param {string} month - Month key (e.g., "Jun-25")
     * @param {Object} config - Preview configuration
     * @returns {Object} Month data object
     */
    function getMonthData(record, month, config) {
        if (config.dataAccess.monthDataPath === 'nested') {
            return record.data?.[month] || {};
        }
        // API spec: Month data is nested under record.months object
        // Example: record.months = {"Jun-25": {forecast: 12500, fte_req: 10, ...}, ...}
        return (record.months && record.months[month]) || record[month] || {};
    }

    /**
     * Get field value using field mapping
     * @param {Object} monthData - Month data object
     * @param {string} fieldKey - Canonical field key (forecast, fteReq, etc.)
     * @param {Object} config - Preview configuration
     * @returns {number} Field value
     */
    function getFieldValue(monthData, fieldKey, config) {
        const actualFieldName = config.fields[fieldKey];
        return monthData[actualFieldName];
    }

    /**
     * Get field change value using field mapping
     */
    function getFieldChange(monthData, fieldKey, config) {
        const actualFieldName = config.fields[fieldKey];
        return monthData[`${actualFieldName}_change`];
    }

    // ============================================================================
    // GENERIC PREVIEW SYSTEM - RENDERING FUNCTIONS
    // ============================================================================

    /**
     * Render preview table with pagination and filters
     * @param {Object} data - API response data
     * @param {Object} config - Preview configuration
     */
    function renderGenericPreviewTable(data, config) {
        const stateBase = config.state.basePath;

        // Get state values
        const filteredRecords = getStateValue(stateBase, config.state.filteredRecords);
        const currentPage = getStateValue(stateBase, config.state.currentPage);
        const pageSize = CONFIG.settings.previewPageSize;

        // Calculate pagination
        const startIdx = (currentPage - 1) * pageSize;
        const endIdx = startIdx + pageSize;
        const pageRecords = filteredRecords.slice(startIdx, endIdx);

        // Early return if no records
        if (!pageRecords || pageRecords.length === 0) {
            DOM[config.dom.tableBody].html('<tr><td colspan="100" class="text-center">No records match the current filters</td></tr>');
            hideElement(DOM[config.dom.pagination]);
            return;
        }

        // Extract months from first record
        const months = extractMonthsFromRecord(pageRecords[0]);

        // Render all components
        renderGenericHeaders(months, config);
        renderGenericRows(pageRecords, months, config);

        if (config.features.showTotalsRow) {
            renderGenericTotals(filteredRecords, months, config);
        }

        renderGenericPagination(config);

        // Update summary
        const allRecords = getStateValue(stateBase, config.state.allRecords);
        if (config.features.showMonthwiseSummary) {
            const summary = calculateGenericMonthwiseSummary(allRecords, config);
            updateGenericMonthwiseChanges(summary, config);
        }
    }

    /**
     * Render table headers (2 rows: main headers + sub-headers)
     */
    function renderGenericHeaders(months, config) {
        const tableHead = DOM[config.dom.tableHead];
        tableHead.empty();

        // Row 1: Main headers
        const headerRow1 = $('<tr>');

        // Fixed columns
        config.fixedColumns.forEach(col => {
            headerRow1.append(
                `<th rowspan="2" class="text-center" style="vertical-align: middle;">${col.label}</th>`
            );
        });

        // Month headers
        const monthColspan = config.monthColumns.length;
        months.forEach(month => {
            headerRow1.append(
                `<th colspan="${monthColspan}" class="text-center edit-view-month-header">${month}</th>`
            );
        });

        // Row 2: Sub-headers
        const headerRow2 = $('<tr>');
        months.forEach(() => {
            config.monthColumns.forEach(col => {
                headerRow2.append(
                    `<th class="text-center edit-view-month-header">${col.label}</th>`
                );
            });
        });

        tableHead.append(headerRow1).append(headerRow2);
    }

    /**
     * Render data rows with change highlighting
     */
    function renderGenericRows(records, months, config) {
        const tableBody = DOM[config.dom.tableBody];
        tableBody.empty();

        records.forEach(record => {
            const tr = $('<tr>');
            const modifiedFields = record.modified_fields || [];

            // Render fixed columns
            config.fixedColumns.forEach(col => {
                if (col.editable) {
                    // Handle editable fixed columns (e.g., target_cph)
                    const isModified = modifiedFields.includes(col.key);
                    const change = record[`${col.key}_change`] || 0;
                    tr.append(renderCell(record[col.key], change, isModified, col.align || 'text-center'));
                } else {
                    tr.append(`<td>${escapeHtml(record[col.key] || '-')}</td>`);
                }
            });

            // Render month columns
            months.forEach(month => {
                const monthData = getMonthData(record, month, config);

                config.monthColumns.forEach(col => {
                    const value = getFieldValue(monthData, col.key, config);

                    if (col.editable) {
                        const fieldName = config.fields[col.key];
                        const isModified = modifiedFields.includes(`${month}.${fieldName}`);
                        const change = getFieldChange(monthData, col.key, config);
                        tr.append(renderCell(value, change, isModified));
                    } else {
                        tr.append(`<td class="text-end">${formatNumber(value)}</td>`);
                    }
                });
            });

            tableBody.append(tr);
        });
    }

    /**
     * Render totals row (if enabled)
     */
    function renderGenericTotals(records, months, config) {
        const tableBody = DOM[config.dom.tableBody];
        const totals = {};

        // Initialize totals for each month
        months.forEach(month => {
            totals[month] = {};
            config.monthColumns.forEach(col => {
                const fieldName = config.fields[col.key];
                totals[month][fieldName] = 0;
                totals[month][`${fieldName}_change`] = 0;
            });
        });

        // Calculate totals
        records.forEach(record => {
            months.forEach(month => {
                const monthData = getMonthData(record, month, config);

                config.monthColumns.forEach(col => {
                    const fieldName = config.fields[col.key];
                    totals[month][fieldName] += (getFieldValue(monthData, col.key, config) || 0);
                    totals[month][`${fieldName}_change`] += (getFieldChange(monthData, col.key, config) || 0);
                });
            });
        });

        // Render totals row
        const tr = $('<tr class="edit-view-totals-row">');
        tr.append('<td class="edit-view-totals-label"><strong>Total</strong></td>');

        // Empty cells for remaining fixed columns
        for (let i = 1; i < config.fixedColumns.length; i++) {
            tr.append('<td></td>');
        }

        // Month totals
        months.forEach(month => {
            const monthTotals = totals[month];

            config.monthColumns.forEach(col => {
                const fieldName = config.fields[col.key];
                const value = monthTotals[fieldName];
                const change = monthTotals[`${fieldName}_change`];

                if (col.editable) {
                    tr.append(renderTotalCell(value, change));
                } else {
                    tr.append(`<td class="text-end"><strong>${formatNumber(value)}</strong></td>`);
                }
            });
        });

        tableBody.append(tr);
    }

    /**
     * Render pagination controls
     */
    function renderGenericPagination(config) {
        const stateBase = config.state.basePath;
        const currentPage = getStateValue(stateBase, config.state.currentPage);
        const totalPages = getStateValue(stateBase, config.state.totalPages);
        const paginationElement = DOM[config.dom.pagination];

        if (totalPages <= 1) {
            hideElement(paginationElement);
            return;
        }

        showElement(paginationElement);
        const paginationUl = paginationElement.find('ul.edit-view-pagination');
        paginationUl.empty();

        // Previous button
        const prevDisabled = currentPage === 1 ? 'edit-view-page-item-disabled' : '';
        const prevLi = $('<li>').addClass('edit-view-page-item').addClass(prevDisabled);
        prevLi.append($('<a>').addClass('edit-view-page-link').attr('href', '#').attr('data-page', currentPage - 1).text('Previous'));
        paginationUl.append(prevLi);

        // Page numbers (with ellipsis for large page counts)
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
                const activeClass = i === currentPage ? 'edit-view-page-item-active' : '';
                const pageLi = $('<li>').addClass('edit-view-page-item').addClass(activeClass);
                pageLi.append($('<a>').addClass('edit-view-page-link').attr('href', '#').attr('data-page', i).text(i));
                paginationUl.append(pageLi);
            } else if (i === currentPage - 3 || i === currentPage + 3) {
                const ellipsisLi = $('<li>').addClass('edit-view-page-item edit-view-page-item-disabled');
                ellipsisLi.append($('<span>').addClass('edit-view-page-link').text('...'));
                paginationUl.append(ellipsisLi);
            }
        }

        // Next button
        const nextDisabled = currentPage === totalPages ? 'edit-view-page-item-disabled' : '';
        const nextLi = $('<li>').addClass('edit-view-page-item').addClass(nextDisabled);
        nextLi.append($('<a>').addClass('edit-view-page-link').attr('href', '#').attr('data-page', currentPage + 1).text('Next'));
        paginationUl.append(nextLi);
    }

    // ============================================================================
    // GENERIC PREVIEW SYSTEM - FILTER FUNCTIONS
    // ============================================================================

    /**
     * Populate filter dropdowns from records
     */
    function populateGenericFilters(records, config) {
        const uniqueLobs = [...new Set(records.map(r => r.main_lob))].sort();
        const uniqueCaseTypes = [...new Set(records.map(r => r.case_type))].sort();

        const lobFilter = DOM[config.dom.lobFilter];
        const caseTypeFilter = DOM[config.dom.caseTypeFilter];

        // Populate LOB filter
        lobFilter.empty();
        uniqueLobs.forEach(lob => {
            lobFilter.append(`<option value="${escapeHtml(lob)}">${escapeHtml(lob)}</option>`);
        });

        // Populate Case Type filter
        caseTypeFilter.empty();
        uniqueCaseTypes.forEach(caseType => {
            caseTypeFilter.append(`<option value="${escapeHtml(caseType)}">${escapeHtml(caseType)}</option>`);
        });

        // Initialize Select2 on filters
        initializeGenericFilterSelect2(config);

        // Show filters
        showElement(DOM[config.dom.filters]);

        console.log(`Edit View: Filters populated - ${uniqueLobs.length} LOBs, ${uniqueCaseTypes.length} Case Types`);
    }

    /**
     * Initialize Select2 on filter dropdowns
     */
    function initializeGenericFilterSelect2(config) {
        const lobFilter = DOM[config.dom.lobFilter];
        const caseTypeFilter = DOM[config.dom.caseTypeFilter];

        // Destroy existing Select2 instances if present
        if (lobFilter.data('select2')) {
            lobFilter.select2('destroy');
        }
        if (caseTypeFilter.data('select2')) {
            caseTypeFilter.select2('destroy');
        }

        // Initialize LOB filter
        lobFilter.select2({
            theme: 'bootstrap-5',
            placeholder: 'All LOBs',
            allowClear: true,
            closeOnSelect: false,
            width: '100%'
        });

        // Initialize Case Type filter
        caseTypeFilter.select2({
            theme: 'bootstrap-5',
            placeholder: 'All Case Types',
            allowClear: true,
            closeOnSelect: false,
            width: '100%'
        });
    }

    /**
     * Apply filters to records
     */
    function applyGenericFilters(config) {
        const stateBase = config.state.basePath;
        const lobFilter = DOM[config.dom.lobFilter];
        const caseTypeFilter = DOM[config.dom.caseTypeFilter];

        const selectedLobs = lobFilter.val() || [];
        const selectedCaseTypes = caseTypeFilter.val() || [];

        // Update state filters
        const filters = getStateValue(stateBase, config.state.filters);
        filters.lobs = selectedLobs;
        filters.caseTypes = selectedCaseTypes;

        // Filter records
        const allRecords = getStateValue(stateBase, config.state.allRecords);
        const filteredRecords = allRecords.filter(record => {
            const lobMatch = selectedLobs.length === 0 || selectedLobs.includes(record.main_lob);
            const caseTypeMatch = selectedCaseTypes.length === 0 || selectedCaseTypes.includes(record.case_type);
            return lobMatch && caseTypeMatch;
        });

        setStateValue(stateBase, config.state.filteredRecords, filteredRecords);

        // Reset to page 1
        setStateValue(stateBase, config.state.currentPage, 1);
        const totalPages = Math.ceil(filteredRecords.length / CONFIG.settings.previewPageSize);
        setStateValue(stateBase, config.state.totalPages, totalPages);

        console.log(`Edit View: Filters applied - ${filteredRecords.length} records match`);
    }

    /**
     * Update cascading filters (LOB → Case Type or vice versa)
     */
    function updateGenericCascadingFilters(changedFilter, config) {
        const stateBase = config.state.basePath;
        const allRecords = getStateValue(stateBase, config.state.allRecords);
        const lobFilter = DOM[config.dom.lobFilter];
        const caseTypeFilter = DOM[config.dom.caseTypeFilter];

        if (changedFilter === 'lob') {
            const selectedLobs = lobFilter.val() || [];

            if (selectedLobs.length > 0) {
                // Update available case types based on selected LOBs
                const availableCaseTypes = [...new Set(
                    allRecords
                        .filter(r => selectedLobs.includes(r.main_lob))
                        .map(r => r.case_type)
                )].sort();

                const currentSelection = caseTypeFilter.val() || [];
                caseTypeFilter.empty();

                availableCaseTypes.forEach(ct => {
                    caseTypeFilter.append(`<option value="${escapeHtml(ct)}">${escapeHtml(ct)}</option>`);
                });

                // Restore valid selections
                const validSelections = currentSelection.filter(ct => availableCaseTypes.includes(ct));
                caseTypeFilter.val(validSelections).trigger('change');
            } else {
                // No LOB filter - show all case types
                const allCaseTypes = [...new Set(allRecords.map(r => r.case_type))].sort();
                caseTypeFilter.empty();
                allCaseTypes.forEach(ct => {
                    caseTypeFilter.append(`<option value="${escapeHtml(ct)}">${escapeHtml(ct)}</option>`);
                });
            }
        } else if (changedFilter === 'caseType') {
            const selectedCaseTypes = caseTypeFilter.val() || [];

            if (selectedCaseTypes.length > 0) {
                // Update available LOBs based on selected case types
                const availableLobs = [...new Set(
                    allRecords
                        .filter(r => selectedCaseTypes.includes(r.case_type))
                        .map(r => r.main_lob)
                )].sort();

                const currentSelection = lobFilter.val() || [];
                lobFilter.empty();

                availableLobs.forEach(lob => {
                    lobFilter.append(`<option value="${escapeHtml(lob)}">${escapeHtml(lob)}</option>`);
                });

                // Restore valid selections
                const validSelections = currentSelection.filter(lob => availableLobs.includes(lob));
                lobFilter.val(validSelections).trigger('change');
            } else {
                // No case type filter - show all LOBs
                const allLobs = [...new Set(allRecords.map(r => r.main_lob))].sort();
                lobFilter.empty();
                allLobs.forEach(lob => {
                    lobFilter.append(`<option value="${escapeHtml(lob)}">${escapeHtml(lob)}</option>`);
                });
            }
        }
    }

    // ============================================================================
    // GENERIC PREVIEW SYSTEM - SUMMARY FUNCTIONS
    // ============================================================================

    /**
     * Calculate month-wise summary statistics
     */
    function calculateGenericMonthwiseSummary(records, config) {
        const monthwiseSummary = {};

        records.forEach(record => {
            const months = extractMonthsFromRecord(record);

            months.forEach(month => {
                if (!monthwiseSummary[month]) {
                    monthwiseSummary[month] = {};

                    // Initialize all tracked fields
                    config.monthColumns.forEach(col => {
                        const fieldName = config.fields[col.key];
                        monthwiseSummary[month][`${fieldName}_total`] = 0;
                        if (col.editable) {
                            monthwiseSummary[month][`${fieldName}_change`] = 0;
                        }
                    });
                }

                const monthData = getMonthData(record, month, config);

                config.monthColumns.forEach(col => {
                    const fieldName = config.fields[col.key];
                    const value = getFieldValue(monthData, col.key, config);
                    const change = getFieldChange(monthData, col.key, config);

                    monthwiseSummary[month][`${fieldName}_total`] =
                        (monthwiseSummary[month][`${fieldName}_total`] || 0) + (value || 0);

                    if (col.editable) {
                        monthwiseSummary[month][`${fieldName}_change`] =
                            (monthwiseSummary[month][`${fieldName}_change`] || 0) + (change || 0);
                    }
                });
            });
        });

        return monthwiseSummary;
    }

    /**
     * Update month-wise summary display (cards or inline)
     */
    function updateGenericMonthwiseChanges(summary, config) {
        const container = $('#' + config.dom.monthChangesContainer);
        container.empty();

        // Sort months chronologically
        const sortedMonths = Object.keys(summary).sort((a, b) => {
            const [monthA, yearA] = a.split('-');
            const [monthB, yearB] = b.split('-');
            const dateA = new Date(`20${yearA}-${getMonthNumber(monthA)}-01`);
            const dateB = new Date(`20${yearB}-${getMonthNumber(monthB)}-01`);
            return dateA - dateB;
        });

        if (config.features.summaryStyle === 'cards') {
            // Card-based summary (bench allocation style)
            sortedMonths.forEach(month => {
                const monthData = summary[month];
                const card = $('<div>').addClass('edit-view-month-summary-card edit-view-mb-2');

                let cardHtml = `<div class="edit-view-month-summary-header"><strong>${month}</strong></div>`;
                cardHtml += '<div class="edit-view-month-summary-details">';

                config.monthColumns.forEach(col => {
                    if (col.editable) {
                        const fieldName = config.fields[col.key];
                        const change = monthData[`${fieldName}_change`] || 0;
                        const sign = change > 0 ? '+' : '';
                        const className = change > 0 ? 'edit-view-text-success' :
                                        change < 0 ? 'edit-view-text-danger' : '';

                        cardHtml += `
                            <div class="edit-view-change-item">
                                <span class="edit-view-change-label">${col.label}:</span>
                                <span class="edit-view-change-value ${className}">
                                    <strong>${sign}${formatNumber(change)}</strong>
                                </span>
                            </div>
                        `;
                    }
                });

                cardHtml += '</div>';
                card.html(cardHtml);
                container.append(card);
            });
        } else {
            // Inline summary (CPH style)
            sortedMonths.forEach(month => {
                const monthData = summary[month];
                let summaryParts = [`<strong>${month}:</strong>`];

                config.monthColumns.forEach(col => {
                    const fieldName = config.fields[col.key];
                    const total = monthData[`${fieldName}_total`] || 0;
                    summaryParts.push(`<span>${col.label}: ${formatNumber(total)}</span>`);
                });

                const summaryDiv = $('<div>').addClass('edit-view-month-change-item');
                summaryDiv.html(summaryParts.join(' | '));
                container.append(summaryDiv);
            });
        }

        showElement(DOM[config.dom.overallChanges]);
    }

    // ============================================================================
    // PREVIEW TABLE RENDERING
    // ============================================================================

    function renderPreviewTable(data) {
        if (!data || !data.modified_records || data.modified_records.length === 0) {
            console.warn('Edit View: No modified records to display');
            hideElement(DOM.previewFilters);
            hideElement(DOM.overallChanges);
            return;
        }

        const config = PREVIEW_CONFIGS.benchAllocation;

        // Store all records
        STATE.allPreviewRecords = data.modified_records;
        STATE.filteredPreviewRecords = data.modified_records;
        STATE.previewTotalPages = Math.ceil(data.modified_records.length / CONFIG.settings.previewPageSize);

        // Populate filters using generic system
        populateGenericFilters(data.modified_records, config);

        // Render using generic system
        renderGenericPreviewTable(data, config);

        // Update badges - always show total from original data, not filtered
        const totalOriginal = STATE.allPreviewRecords.length;
        const totalFiltered = STATE.filteredPreviewRecords.length;
        DOM.modifiedCountBadge.text(`${totalOriginal} ${totalOriginal === 1 ? 'record' : 'records'} modified`);
        DOM.summaryText.text(`${totalOriginal} ${totalOriginal === 1 ? 'record' : 'records'} modified (${totalFiltered} shown)`);
        DOM.actionSummaryCount.text(totalOriginal);

        // Show containers
        showElement(DOM.previewFilters);
        showElement(DOM.overallChanges);
    }

    function extractMonthsFromRecord(record) {
        // NEW STRUCTURE: Months are nested under record.months object
        // Example: record.months = {"Jun-25": {forecast: 12500, fte_req: 10, ...}, ...}
        const months = [];

        // Check if months is nested (new structure)
        if (record.months && typeof record.months === 'object') {
            // Extract keys from nested months object
            for (const key in record.months) {
                if (record.months.hasOwnProperty(key)) {
                    months.push(key);
                }
            }
        } else {
            // Fallback: Old structure where months are directly on record
            const monthPattern = /^[A-Z][a-z]{2}-\d{2}$/; // e.g., "Jun-25"
            for (const key in record) {
                if (monthPattern.test(key)) {
                    months.push(key);
                }
            }
        }

        // Sort months chronologically (assuming format "MMM-YY")
        months.sort((a, b) => {
            const [monthA, yearA] = a.split('-');
            const [monthB, yearB] = b.split('-');
            const dateA = new Date(`20${yearA}-${getMonthNumber(monthA)}-01`);
            const dateB = new Date(`20${yearB}-${getMonthNumber(monthB)}-01`);
            return dateA - dateB;
        });

        return months;
    }

    function getMonthNumber(monthAbbr) {
        const months = { Jan: '01', Feb: '02', Mar: '03', Apr: '04', May: '05', Jun: '06',
                        Jul: '07', Aug: '08', Sep: '09', Oct: '10', Nov: '11', Dec: '12' };
        return months[monthAbbr] || '01';
    }

    // NOTE: renderPreviewHeaders removed - superseded by renderGenericPreviewTable
    // NOTE: renderPreviewRows removed - superseded by renderGenericPreviewTable
    // NOTE: renderPreviewTotals removed - superseded by renderGenericPreviewTable
    // NOTE: renderPreviewPagination removed - superseded by renderGenericPreviewTable

    function renderCell(value, change, isModified, additionalClass = 'text-end') {
        if (!isModified || change === 0) {
            return `<td class="${additionalClass}">${formatNumber(value)}</td>`;
        }

        const cellClass = change > 0 ? 'edit-view-cell-increased' : 'edit-view-cell-decreased';
        const badgeClass = change > 0 ? 'edit-view-change-badge-positive' : 'edit-view-change-badge-negative';
        const sign = change > 0 ? '+' : '';
        const badge = `<span class="edit-view-change-badge ${badgeClass}">${sign}${formatNumber(change)}</span>`;

        return `<td class="${additionalClass} ${cellClass}">${formatNumber(value)} ${badge}</td>`;
    }

    function renderTotalCell(value, change) {
        if (!change || change === 0) {
            return `<td class="text-end"><strong>${formatNumber(value)}</strong></td>`;
        }

        const badgeClass = change > 0 ? 'edit-view-change-badge-positive' : 'edit-view-change-badge-negative';
        const sign = change > 0 ? '+' : '';
        const badge = `<span class="edit-view-change-badge ${badgeClass}">${sign}${formatNumber(change)}</span>`;

        return `<td class="text-end"><strong>${formatNumber(value)}</strong> ${badge}</td>`;
    }

    function handlePreviewPageClick(e) {
        e.preventDefault();

        const page = parseInt($(this).attr('data-page'));
        if (isNaN(page) || page < 1 || page > STATE.previewTotalPages || page === STATE.previewCurrentPage) {
            return;
        }

        STATE.previewCurrentPage = page;

        // Just re-render the table with the new page, don't reset state
        const config = PREVIEW_CONFIGS.benchAllocation;
        renderGenericPreviewTable(STATE.currentPreviewData, config);

        // Scroll to top of preview table
        DOM.previewContainer[0].scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // ============================================================================
    // ACCEPT & REJECT ACTIONS
    // ============================================================================

    function handleNotesInput() {
        const currentLength = DOM.userNotesInput.val().length;
        DOM.notesCharCount.text(currentLength);

        if (currentLength > CONFIG.settings.maxUserNotesLength) {
            DOM.userNotesInput.val(DOM.userNotesInput.val().substring(0, CONFIG.settings.maxUserNotesLength));
            DOM.notesCharCount.text(CONFIG.settings.maxUserNotesLength);
        }
    }

    function handleReject() {
        console.log('Edit View: Reject clicked');

        // Clear preview and reset state
        STATE.currentPreviewData = null;
        STATE.currentSelectedReport = null;
        STATE.previewCurrentPage = 1;
        STATE.previewTotalPages = 0;

        DOM.userNotesInput.val('');
        DOM.notesCharCount.text('0');

        hideElement(DOM.previewContainer);
        hideElement(DOM.actionsContainer);
        hideElement(DOM.previewError);

        // Show success message
        Swal.fire({
            icon: 'info',
            title: 'Changes Discarded',
            text: 'Preview has been cleared. You can select a different report and run allocation again.',
            timer: 3000,
            showConfirmButton: false
        });
    }

    async function handleAccept() {
        console.log('Edit View: Accept clicked');

        if (STATE.isSubmitting) {
            console.log('Edit View: Already submitting, ignoring click');
            return;
        }

        if (!STATE.currentPreviewData || !STATE.currentSelectedReport) {
            await Swal.fire({
                icon: 'error',
                title: 'No Preview Data',
                text: 'Please run allocation first to preview changes.',
                confirmButtonColor: '#dc3545'
            });
            return;
        }

        // Confirmation dialog
        const result = await Swal.fire({
            icon: 'question',
            title: 'Confirm Update',
            html: `You are about to update <strong>${STATE.currentPreviewData.total_modified} records</strong>.<br>This action cannot be undone.`,
            showCancelButton: true,
            confirmButtonText: 'Yes, Update',
            cancelButtonText: 'Cancel',
            confirmButtonColor: '#198754',
            cancelButtonColor: '#6c757d'
        });

        if (!result.isConfirmed) {
            return;
        }

        await submitBenchAllocationUpdate();
    }

    async function submitBenchAllocationUpdate() {
        console.log('Edit View: Submitting bench allocation update...');

        STATE.isSubmitting = true;
        DOM.acceptBtn.prop('disabled', true).html('<span class="edit-view-spinner edit-view-spinner-sm edit-view-me-1"></span>Updating...');

        try {
            const payload = {
                month: STATE.currentSelectedReport.month,
                year: STATE.currentSelectedReport.year,
                months: STATE.currentPreviewData.months,
                modified_records: STATE.currentPreviewData.modified_records,
                user_notes: DOM.userNotesInput.val().trim()
            };

            const response = await fetch(CONFIG.urls.benchAllocationUpdate, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin',
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorMsg = await extractErrorMessage(response);
                throw new Error(errorMsg);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.message || 'Update failed');
            }

            // Success!
            await Swal.fire({
                icon: 'success',
                title: 'Update Successful',
                html: `<strong>${data.records_updated}</strong> records have been updated successfully.`,
                confirmButtonColor: '#198754',
                timer: 3000
            });

            // Reset state and clear preview
            STATE.currentPreviewData = null;
            STATE.currentSelectedReport = null;
            STATE.previewCurrentPage = 1;
            DOM.userNotesInput.val('');
            DOM.notesCharCount.text('0');
            DOM.allocationReportSelect.val('').trigger('change');

            hideElement(DOM.previewContainer);
            hideElement(DOM.actionsContainer);

            // Refresh history if on history tab (invalidate cache)
            STATE.currentHistoryData = null;

            console.log(`Edit View: Update successful - ${data.records_updated} records updated`);

        } catch (error) {
            console.error('Edit View: Error submitting update', error);

            // Show detailed error message
            showErrorDialog(
                'Update Failed',
                'The allocation update could not be completed. Please review the error details and try again.',
                `Error: ${error.message}`
            );

        } finally {
            STATE.isSubmitting = false;
            DOM.acceptBtn.prop('disabled', false).html('<i class="fas fa-check edit-view-me-1"></i>Accept & Update');
        }
    }

    // ============================================================================
    // HISTORY LOG
    // ============================================================================

    async function handleApplyHistoryFilters() {
        console.log('Edit View: Apply history filters clicked');

        const reportValue = DOM.historyReportSelect.val();
        const changeTypes = DOM.historyChangeTypeSelect.val() || [];

        // Parse report value if selected
        let month = null;
        let year = null;

        if (reportValue) {
            const [yearStr, monthNum] = reportValue.split('-');
            year = parseInt(yearStr);
            const monthNames = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                               'July', 'August', 'September', 'October', 'November', 'December'];
            month = monthNames[parseInt(monthNum)];
        }

        STATE.historyFilters = { month, year, changeTypes };
        STATE.historyCurrentPage = 1;
        STATE.loadedHistoryCount = 0; // Reset lazy loading state

        await loadHistoryLog(false); // append = false (initial load)
    }

    async function loadHistoryLog(append = false) {
        console.log(`Edit View: Loading history log (append: ${append})...`);

        // Prevent duplicate requests
        if (STATE.isLoadingHistory) {
            console.log('Edit View: Already loading history, skipping duplicate request');
            return;
        }

        STATE.isLoadingHistory = true;

        // Determine limit based on whether this is initial load or lazy load
        const limit = append ?
            CONFIG.settings.historyLazyLoadSize :
            CONFIG.settings.historyInitialLoad;

        // If appending, increment page; otherwise reset to page 1
        if (append) {
            STATE.historyCurrentPage++;
        } else {
            STATE.historyCurrentPage = 1;
            STATE.loadedHistoryCount = 0;
        }

        showElement(DOM.historyLoading);
        hideElement(DOM.historyError);

        // Only hide containers on initial load (not when appending)
        if (!append) {
            hideElement(DOM.historyNoResults);
            hideElement(DOM.historyCardsContainer);
            hideElement(DOM.historyLoadMoreContainer);
        }

        try {
            const params = new URLSearchParams({
                page: STATE.historyCurrentPage,
                limit: limit
            });

            if (STATE.historyFilters.month) {
                params.append('month', STATE.historyFilters.month);
            }
            if (STATE.historyFilters.year) {
                params.append('year', STATE.historyFilters.year);
            }
            // Add change type filters (multiple values)
            if (STATE.historyFilters.changeTypes && STATE.historyFilters.changeTypes.length > 0) {
                STATE.historyFilters.changeTypes.forEach(changeType => {
                    params.append('change_types', changeType);
                });
            }

            const url = `${CONFIG.urls.historyLog}?${params.toString()}`;

            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                const errorMsg = await extractErrorMessage(response);
                throw new Error(errorMsg);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.message || 'Failed to fetch history log');
            }

            STATE.currentHistoryData = data;
            STATE.totalHistoryCount = data.pagination.total;

            // Render history cards
            if (data.data && data.data.length > 0) {
                renderHistoryCards(data.data, append);
                STATE.loadedHistoryCount += data.data.length;
                updateHistoryCounters();
                updateLoadMoreButton(data.pagination.has_more);
                showElement(DOM.historyCardsContainer);
                hideElement(DOM.historyNoResults);
            } else {
                if (!append) {
                    // Only show "no results" on initial load with no data
                    showElement(DOM.historyNoResults);
                    hideElement(DOM.historyCardsContainer);
                    updateLoadMoreButton(false);
                }
            }

            console.log(`Edit View: History log loaded - ${data.data.length} entries (total loaded: ${STATE.loadedHistoryCount}/${STATE.totalHistoryCount})`);

        } catch (error) {
            console.error('Edit View: Error loading history log', error);
            showInlineError(
                DOM.historyError,
                DOM.historyErrorMessage,
                error.message || 'Failed to load history log. Please try again.'
            );
            updateLoadMoreButton(false);

        } finally {
            STATE.isLoadingHistory = false;
            hideElement(DOM.historyLoading);
        }
    }

    function renderHistoryCards(entries, append = false) {
        // Clear only on initial load (not when appending)
        if (!append) {
            DOM.historyCardsContainer.empty();
        }

        entries.forEach(entry => {
            const card = createHistoryCard(entry);
            DOM.historyCardsContainer.append(card);
        });
    }

    function createHistoryCard(entry) {
        const card = $('<div>').addClass('edit-view-card edit-view-history-card edit-view-mb-3');

        // Apply dynamic border color based on change type
        const borderColor = getDynamicChangeTypeColor(entry.change_type);
        card.css('border-left-color', borderColor);

        const cardBody = $('<div>').addClass('edit-view-card-body');

        // Header with enhanced title
        const header = $('<div>').addClass('edit-view-flex edit-view-justify-between edit-view-align-start edit-view-mb-3');

        const headerLeft = $('<div>');
        // Use report_title if available, otherwise fallback to change_type
        const title = entry.report_title || `${entry.change_type || 'Update'}, ${entry.month || ''} ${entry.year || ''}`;
        headerLeft.append(`<h5 class="edit-view-mb-1">${escapeHtml(title)}</h5>`);

        // Dynamic badge with matching color
        const badge = $('<span>')
            .addClass('edit-view-badge edit-view-change-type-badge')
            .css('background-color', borderColor)
            .css('color', getContrastColor(borderColor))
            .text(entry.change_type || 'Update');
        headerLeft.append(badge);

        const headerRight = $('<div>').addClass('edit-view-text-muted');
        headerRight.append(`<small>${escapeHtml(entry.timestamp_formatted || entry.timestamp || '-')}</small>`);

        header.append(headerLeft).append(headerRight);
        cardBody.append(header);

        // Enhanced description
        const details = $('<div>').addClass('edit-view-mb-3');
        
        // Description - user provided or system generated
        const description = entry.description || `Updated ${entry.records_modified || 0} rows by ${entry.change_type || 'Update'} operation`;
        details.append(`<p class="edit-view-mb-2"><strong>Description:</strong> ${escapeHtml(description)}</p>`);
        
        details.append(`<p class="edit-view-mb-1"><strong>Records Modified:</strong> ${entry.records_modified || 0}</p>`);

        cardBody.append(details);

        // Summary table with month-wise changes
        if (entry.summary_data) {
            const summarySection = $('<div>').addClass('edit-view-history-summary-section edit-view-mb-3');
            summarySection.append('<h6 class="edit-view-mb-2">Summary:</h6>');
            
            const summaryTable = renderHistorySummaryTable(entry.summary_data);
            const tableContainer = $('<div>').addClass('edit-view-history-summary-container');
            tableContainer.append(summaryTable);
            summarySection.append(tableContainer);
            
            cardBody.append(summarySection);
        }


        // Download button
        if (entry.id) {
            const downloadBtn = $('<button>')
                .addClass('edit-view-btn edit-view-btn-sm edit-view-btn-outline-primary edit-view-download-excel-btn edit-view-mt-2')
                .attr('data-history-id', entry.id)
                .html('<i class="fas fa-download edit-view-me-1"></i>Download Modified Records (Excel)');
            cardBody.append(downloadBtn);
        }

        card.append(cardBody);

        return card;
    }


    // Helper function to update counter display
    function updateHistoryCounters() {
        $('#history-loaded-count').text(STATE.loadedHistoryCount);
        $('#history-total-count').text(STATE.totalHistoryCount);
    }

    // Helper function to show/hide Load More button
    function updateLoadMoreButton(hasMore) {
        const container = DOM.historyLoadMoreContainer;

        if (hasMore && STATE.loadedHistoryCount < STATE.totalHistoryCount) {
            showElement(container);
        } else {
            hideElement(container);
        }
    }

    // Handle Load More button click
    function handleHistoryLoadMore(e) {
        e.preventDefault();
        loadHistoryLog(true); // append = true
    }

    // ============================================================================
    // EXCEL DOWNLOAD
    // ============================================================================

    async function handleExcelDownload(e) {
        e.preventDefault();
        const historyId = $(this).attr('data-history-id');

        if (!historyId) {
            console.error('Edit View: No history ID for download');
            return;
        }

        console.log(`Edit View: Downloading Excel for history ID: ${historyId}`);

        // Disable button during download
        const btn = $(this);
        const originalHtml = btn.html();
        btn.prop('disabled', true).html('<span class="edit-view-spinner edit-view-spinner-sm edit-view-me-1"></span>Downloading...');

        try {
            const url = CONFIG.urls.downloadHistoryExcel.replace('{id}', historyId);

            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            // Download file
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `bench_allocation_${historyId}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(downloadUrl);
            document.body.removeChild(a);

            console.log('Edit View: Excel download successful');

        } catch (error) {
            console.error('Edit View: Error downloading Excel', error);
            await Swal.fire({
                icon: 'error',
                title: 'Download Failed',
                text: 'Failed to download Excel file. Please try again.',
                confirmButtonColor: '#dc3545'
            });

        } finally {
            btn.prop('disabled', false).html(originalHtml);
        }
    }

    // ============================================================================
    // HISTORY SUMMARY TABLE FUNCTIONS
    // ============================================================================

    function renderHistorySummaryTable(summaryData) {
        const table = $('<table>').addClass('edit-view-history-summary-table');
        
        // Create table structure
        const thead = $('<thead>');
        const tbody = $('<tbody>');
        
        // Header row 1 - Main headers
        const headerRow1 = $('<tr>');
        headerRow1.append('<th rowspan="2" class="edit-view-summary-fixed">Month</th>');
        headerRow1.append('<th rowspan="2" class="edit-view-summary-fixed">Year</th>');
        
        summaryData.months.forEach(month => {
            headerRow1.append(`<th colspan="4" class="edit-view-summary-scroll edit-view-month-header">${month}</th>`);
        });
        
        // Header row 2 - Sub headers
        const headerRow2 = $('<tr>');
        summaryData.months.forEach(() => {
            headerRow2.append('<th class="edit-view-summary-scroll">Total Forecast</th>');
            headerRow2.append('<th class="edit-view-summary-scroll">Total FTE Required</th>');
            headerRow2.append('<th class="edit-view-summary-scroll">Total FTE Available</th>');
            headerRow2.append('<th class="edit-view-summary-scroll">Total Capacity</th>');
        });
        
        thead.append(headerRow1).append(headerRow2);
        
        // Data row
        const dataRow = $('<tr>');
        dataRow.append(`<td class="edit-view-summary-fixed"><strong>${summaryData.report_month}</strong></td>`);
        dataRow.append(`<td class="edit-view-summary-fixed"><strong>${summaryData.report_year}</strong></td>`);
        
        summaryData.months.forEach(month => {
            const monthData = summaryData.totals[month];
            
            // Format each value as "old → new" with color coding
            ['total_forecast', 'total_fte_required', 'total_fte_available', 'total_capacity'].forEach(field => {
                const data = monthData[field];
                const cell = formatOldNewCell(data.old, data.new);
                dataRow.append(cell);
            });
        });
        
        tbody.append(dataRow);
        table.append(thead).append(tbody);
        
        return table;
    }

    function formatOldNewCell(oldValue, newValue) {
        const cell = $('<td>').addClass('edit-view-summary-scroll');
        
        if (oldValue === newValue) {
            // No change
            cell.html(`<span class="edit-view-old-new-value">${formatNumber(newValue)}</span>`);
        } else {
            // Changed value
            const changeClass = newValue > oldValue ? 'edit-view-value-increase' : 'edit-view-value-decrease';
            const arrow = '→';
            cell.addClass(changeClass);
            cell.html(`<span class="edit-view-old-new-value">${formatNumber(oldValue)} ${arrow} ${formatNumber(newValue)}</span>`);
        }
        
        return cell;
    }

    function getDynamicChangeTypeColor(changeType) {
        // Check if we have the color from the API response
        if (STATE.availableChangeTypes) {
            const changeTypeData = STATE.availableChangeTypes.find(ct => ct.value === changeType);
            if (changeTypeData && changeTypeData.color) {
                return changeTypeData.color;
            }
        }
        
        // Predefined colors for common change types (fallback)
        const predefinedColors = {
            'Bench Allocation': '#0d6efd',
            'CPH Update': '#198754',
            'Manual Update': '#ffc107',
            'Capacity Update': '#6f42c1',
            'FTE Update': '#fd7e14',
            'Forecast Update': '#20c997'
        };
        
        // Return predefined color if exists
        if (predefinedColors[changeType]) {
            return predefinedColors[changeType];
        }
        
        // Use standard colors with hash-based selection
        return getStandardColorForString(changeType);
    }

    function getStandardColorForString(str) {
        // Standard colors array (matching backend config)
        const standardColors = [
            '#0d6efd', '#198754', '#ffc107', '#dc3545', '#6f42c1', '#fd7e14',
            '#20c997', '#e91e63', '#9c27b0', '#673ab7', '#3f51b5', '#2196f3',
            '#03a9f4', '#00bcd4', '#009688', '#4caf50', '#8bc34a', '#cddc39',
            '#ffeb3b', '#ffc107', '#ff9800', '#ff5722', '#795548', '#9e9e9e',
            '#607d8b', '#f44336', '#e91e63', '#9c27b0', '#673ab7', '#3f51b5',
            '#2196f3', '#03a9f4', '#00bcd4', '#009688', '#4caf50', '#8bc34a',
            '#cddc39', '#ffeb3b', '#ff9800', '#ff5722', '#795548', '#9e9e9e',
            '#607d8b', '#1976d2', '#388e3c', '#f57c00', '#d32f2f', '#7b1fa2',
            '#512da8', '#303f9f'
        ];
        
        // Simple hash function to generate consistent index
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & 0xFFFFFFFF; // Convert to 32-bit integer
        }
        
        const colorIndex = Math.abs(hash) % standardColors.length;
        return standardColors[colorIndex];
    }

    function getContrastColor(backgroundColor) {
        // Determine if text should be white or black based on background color brightness
        let r, g, b;
        
        if (backgroundColor.startsWith('#')) {
            // Hex color
            const color = backgroundColor.replace('#', '');
            if (color.length === 6) {
                r = parseInt(color.substr(0, 2), 16);
                g = parseInt(color.substr(2, 2), 16);
                b = parseInt(color.substr(4, 2), 16);
            } else {
                return '#ffffff'; // Default to white for invalid hex
            }
        } else if (backgroundColor.startsWith('hsl')) {
            // For HSL colors, use white text for better contrast
            return '#ffffff';
        } else {
            return '#ffffff'; // Default to white
        }
        
        // Calculate brightness using relative luminance formula
        const brightness = (r * 299 + g * 587 + b * 114) / 1000;
        return brightness > 128 ? '#000000' : '#ffffff';
    }

    // ============================================================================
    // UTILITY FUNCTIONS
    // ============================================================================

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

    // NOTE: showErrorAlert removed - using Swal.fire directly instead

    function formatNumber(value) {
        if (value === null || value === undefined || value === '') {
            return '-';
        }

        const num = parseFloat(value);
        if (isNaN(num)) {
            return '-';
        }

        return num.toLocaleString('en-US', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        });
    }

    function escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return String(text).replace(/[&<>"']/g, m => map[m]);
    }

    // ============================================================================
    // TARGET CPH FUNCTIONALITY
    // ============================================================================

    async function handleLoadCphData() {
        console.log('Edit View: Load CPH Data clicked');

        const reportValue = DOM.cphReportSelect.val();

        // Validate
        if (!reportValue) {
            await Swal.fire({
                icon: 'warning',
                title: 'Selection Required',
                text: 'Please select an allocation report first.',
                confirmButtonColor: '#0d6efd'
            });
            return;
        }

        // Parse report value (format: "YYYY-MM")
        const [yearStr, monthNum] = reportValue.split('-');
        const year = parseInt(yearStr);
        const monthNames = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December'];
        const month = monthNames[parseInt(monthNum)];

        STATE.cph.currentSelectedReport = { month, year };

        await loadCphData(month, year);
    }

    async function loadCphData(month, year) {
        console.log(`Edit View: Loading CPH data for ${month} ${year}`);

        showElement(DOM.cphDataLoading);
        hideElement(DOM.cphDataError);
        hideElement(DOM.cphDataContainer);
        hideElement(DOM.cphPreviewContainer);
        hideElement(DOM.cphActionsContainer);

        try {
            const url = `${CONFIG.urls.targetCphData}?month=${encodeURIComponent(month)}&year=${year}`;

            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                const errorMsg = await extractErrorMessage(response);
                throw new Error(errorMsg);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.message || 'Failed to load CPH data');
            }

            if (!data.data || data.data.length === 0) {
                showInlineError(
                    DOM.cphDataError,
                    DOM.cphDataErrorMessage,
                    'No CPH data available for the selected report. Please select a different report or contact your administrator.'
                );
                return;
            }

            // Store CPH data
            STATE.cph.allCphRecords = data.data;
            STATE.cph.filteredCphRecords = data.data;
            STATE.cph.modifiedCphRecords.clear();
            STATE.cph.currentPage = 1;
            STATE.cph.totalPages = Math.ceil(data.data.length / 20); // 20 records per page

            // Render CPH table
            renderCphTable();
            populateCphFilters();
            updateCphModifiedCount();
            showElement(DOM.cphDataContainer);

            console.log(`Edit View: CPH data loaded - ${data.total} records`);

        } catch (error) {
            console.error('Edit View: Error loading CPH data', error);
            showInlineError(
                DOM.cphDataError,
                DOM.cphDataErrorMessage,
                error.message || 'Failed to load CPH data. Please try again.'
            );

        } finally {
            hideElement(DOM.cphDataLoading);
        }
    }

    function renderCphTable() {
        const { filteredCphRecords, currentPage } = STATE.cph;
        const recordsPerPage = 20;
        const startIdx = (currentPage - 1) * recordsPerPage;
        const endIdx = startIdx + recordsPerPage;
        const pageRecords = filteredCphRecords.slice(startIdx, endIdx);

        // Clear table body
        DOM.cphTableBody.empty();

        if (pageRecords.length === 0) {
            DOM.cphTableBody.append(`
                <tr>
                    <td colspan="4" class="edit-view-text-center edit-view-text-muted">
                        No CPH records found for the selected filters
                    </td>
                </tr>
            `);
            hideElement(DOM.cphPagination);
            return;
        }

        // Render rows
        pageRecords.forEach(record => {
            DOM.cphTableBody.append(renderCphTableRow(record));
        });

        // Render pagination
        renderCphPagination();

        console.log(`Edit View: Rendered ${pageRecords.length} CPH records (page ${currentPage})`);
    }

    function renderCphTableRow(record) {
        const modifiedRecord = STATE.cph.modifiedCphRecords.get(record.id);
        const currentValue = modifiedRecord ? modifiedRecord.modified_target_cph : record.modified_target_cph;
        const isModified = modifiedRecord !== undefined;

        const rowClass = isModified ? 'edit-view-cph-row-modified' : '';
        const inputClass = isModified ? 'edit-view-input-modified' : '';

        return `
            <tr class="${rowClass}" data-cph-id="${escapeHtml(record.id)}">
                <td>${escapeHtml(record.lob)}</td>
                <td>${escapeHtml(record.case_type)}</td>
                <td class="edit-view-text-end">${formatNumber(record.target_cph)}</td>
                <td class="edit-view-cph-input-cell">
                    <div class="edit-view-cph-btn-group">
                        <button class="edit-view-btn edit-view-btn-sm cph-decrement-btn"
                                data-cph-id="${escapeHtml(record.id)}"
                                title="Decrement by 1.0">
                            <i class="fas fa-minus"></i>
                        </button>
                        <input type="number"
                               class="edit-view-form-input cph-modified-input ${inputClass}"
                               data-cph-id="${escapeHtml(record.id)}"
                               data-original-value="${record.target_cph}"
                               value="${currentValue}"
                               step="1.0"
                               min="0"
                               max="10000"
                               title="Target CPH">
                        <button class="edit-view-btn edit-view-btn-sm cph-increment-btn"
                                data-cph-id="${escapeHtml(record.id)}"
                                title="Increment by 1.0">
                            <i class="fas fa-plus"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }

    function renderCphPagination() {
        const { currentPage, totalPages } = STATE.cph;

        if (totalPages <= 1) {
            hideElement(DOM.cphPagination);
            return;
        }

        const paginationHtml = [];
        paginationHtml.push(`
            <li class="edit-view-page-item ${currentPage === 1 ? 'edit-view-disabled' : ''}">
                <a class="edit-view-page-link" href="#" data-page="${currentPage - 1}">Previous</a>
            </li>
        `);

        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
                paginationHtml.push(`
                    <li class="edit-view-page-item ${i === currentPage ? 'edit-view-active' : ''}">
                        <a class="edit-view-page-link" href="#" data-page="${i}">${i}</a>
                    </li>
                `);
            } else if (i === currentPage - 3 || i === currentPage + 3) {
                paginationHtml.push(`
                    <li class="edit-view-page-item edit-view-disabled">
                        <span class="edit-view-page-link">...</span>
                    </li>
                `);
            }
        }

        paginationHtml.push(`
            <li class="edit-view-page-item ${currentPage === totalPages ? 'edit-view-disabled' : ''}">
                <a class="edit-view-page-link" href="#" data-page="${currentPage + 1}">Next</a>
            </li>
        `);

        DOM.cphPagination.find('ul').html(paginationHtml.join(''));
        showElement(DOM.cphPagination);
    }

    function populateCphFilters() {
        const { allCphRecords } = STATE.cph;

        // Extract unique LOBs and Case Types
        const uniqueLobs = [...new Set(allCphRecords.map(r => r.lob))].sort();
        const uniqueCaseTypes = [...new Set(allCphRecords.map(r => r.case_type))].sort();

        // Populate LOB filter
        DOM.cphLobFilter.empty();
        uniqueLobs.forEach(lob => {
            DOM.cphLobFilter.append(`<option value="${escapeHtml(lob)}">${escapeHtml(lob)}</option>`);
        });

        // Populate Case Type filter
        DOM.cphCaseTypeFilter.empty();
        uniqueCaseTypes.forEach(caseType => {
            DOM.cphCaseTypeFilter.append(`<option value="${escapeHtml(caseType)}">${escapeHtml(caseType)}</option>`);
        });

        // Initialize Select2 on CPH filters
        initializeCphFilterSelect2();

        console.log(`Edit View: CPH filters populated - ${uniqueLobs.length} LOBs, ${uniqueCaseTypes.length} Case Types`);
    }

    function initializeCphFilterSelect2() {
        // Destroy existing Select2 instances if present
        if (DOM.cphLobFilter.data('select2')) {
            DOM.cphLobFilter.select2('destroy');
        }
        if (DOM.cphCaseTypeFilter.data('select2')) {
            DOM.cphCaseTypeFilter.select2('destroy');
        }

        // Initialize CPH LOB filter
        DOM.cphLobFilter.select2({
            theme: 'bootstrap-5',
            placeholder: 'All LOBs',
            allowClear: true,
            closeOnSelect: false,
            width: '100%'
        });

        // Initialize CPH Case Type filter
        DOM.cphCaseTypeFilter.select2({
            theme: 'bootstrap-5',
            placeholder: 'All Case Types',
            allowClear: true,
            closeOnSelect: false,
            width: '100%'
        });
    }

    function applyCphFilters() {
        const selectedLobs = DOM.cphLobFilter.val() || [];
        const selectedCaseTypes = DOM.cphCaseTypeFilter.val() || [];

        STATE.cph.filters.lobs = selectedLobs;
        STATE.cph.filters.caseTypes = selectedCaseTypes;

        // Filter records
        STATE.cph.filteredCphRecords = STATE.cph.allCphRecords.filter(record => {
            const lobMatch = selectedLobs.length === 0 || selectedLobs.includes(record.lob);
            const caseTypeMatch = selectedCaseTypes.length === 0 || selectedCaseTypes.includes(record.case_type);
            return lobMatch && caseTypeMatch;
        });

        // Reset to page 1
        STATE.cph.currentPage = 1;
        STATE.cph.totalPages = Math.ceil(STATE.cph.filteredCphRecords.length / 20);

        // Re-render table
        renderCphTable();

        console.log(`Edit View: CPH filters applied - ${STATE.cph.filteredCphRecords.length} records match`);
    }

    function updateCphCascadingFilters(changedFilter) {
        const { allCphRecords, filters } = STATE.cph;

        if (changedFilter === 'lob') {
            const selectedLobs = DOM.cphLobFilter.val() || [];

            if (selectedLobs.length > 0) {
                // Filter case types based on selected LOBs
                const availableCaseTypes = [...new Set(
                    allCphRecords
                        .filter(r => selectedLobs.includes(r.lob))
                        .map(r => r.case_type)
                )].sort();

                // Update case type filter options
                const selectedCaseTypes = DOM.cphCaseTypeFilter.val() || [];
                DOM.cphCaseTypeFilter.empty();
                availableCaseTypes.forEach(ct => {
                    DOM.cphCaseTypeFilter.append(`<option value="${escapeHtml(ct)}">${escapeHtml(ct)}</option>`);
                });

                // Restore selections that still exist
                const validSelections = selectedCaseTypes.filter(ct => availableCaseTypes.includes(ct));
                DOM.cphCaseTypeFilter.val(validSelections).trigger('change');
            }
        } else if (changedFilter === 'caseType') {
            const selectedCaseTypes = DOM.cphCaseTypeFilter.val() || [];

            if (selectedCaseTypes.length > 0) {
                // Filter LOBs based on selected case types
                const availableLobs = [...new Set(
                    allCphRecords
                        .filter(r => selectedCaseTypes.includes(r.case_type))
                        .map(r => r.lob)
                )].sort();

                // Update LOB filter options
                const selectedLobs = DOM.cphLobFilter.val() || [];
                DOM.cphLobFilter.empty();
                availableLobs.forEach(lob => {
                    DOM.cphLobFilter.append(`<option value="${escapeHtml(lob)}">${escapeHtml(lob)}</option>`);
                });

                // Restore selections that still exist
                const validSelections = selectedLobs.filter(lob => availableLobs.includes(lob));
                DOM.cphLobFilter.val(validSelections).trigger('change');
            }
        }
    }

    function clearCphFilters() {
        DOM.cphLobFilter.val(null).trigger('change');
        DOM.cphCaseTypeFilter.val(null).trigger('change');

        // Repopulate filters with all options
        populateCphFilters();

        // Apply empty filters
        applyCphFilters();
    }

    function handleCphPageClick(e) {
        e.preventDefault();

        const page = parseInt($(e.currentTarget).data('page'));

        if (isNaN(page) || page < 1 || page > STATE.cph.totalPages) {
            return;
        }

        STATE.cph.currentPage = page;
        renderCphTable();

        // Scroll to table top
        DOM.cphTable[0].scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function handleCphInputChange(e) {
        const input = $(e.target);
        const cphId = input.data('cph-id');
        const originalValue = parseFloat(input.data('original-value'));
        const newValue = parseFloat(input.val());

        // Validate
        if (isNaN(newValue) || newValue < 0 || newValue > 10000) {
            input.addClass('edit-view-input-invalid');
            return;
        } else {
            input.removeClass('edit-view-input-invalid');
        }

        trackCphModification(cphId, newValue, originalValue);
    }

    function handleCphIncrement(e) {
        e.preventDefault();

        const cphId = $(e.currentTarget).data('cph-id');
        const input = $(`input.cph-modified-input[data-cph-id="${cphId}"]`);
        const currentValue = parseFloat(input.val()) || 0;
        const originalValue = parseFloat(input.data('original-value'));
        const newValue = Math.min(currentValue + 1.0, 10000);

        input.val(newValue.toFixed(2));
        trackCphModification(cphId, newValue, originalValue);
    }

    function handleCphDecrement(e) {
        e.preventDefault();

        const cphId = $(e.currentTarget).data('cph-id');
        const input = $(`input.cph-modified-input[data-cph-id="${cphId}"]`);
        const currentValue = parseFloat(input.val()) || 0;
        const originalValue = parseFloat(input.data('original-value'));
        const newValue = Math.max(currentValue - 1.0, 0);

        input.val(newValue.toFixed(2));
        trackCphModification(cphId, newValue, originalValue);
    }

    function trackCphModification(cphId, newValue, originalValue) {
        const record = STATE.cph.allCphRecords.find(r => r.id === cphId);
        if (!record) return;

        const roundedNewValue = Math.round(newValue * 100) / 100;
        const roundedOriginalValue = Math.round(originalValue * 100) / 100;

        if (roundedNewValue === roundedOriginalValue) {
            // Reverted to original - remove from modified map
            STATE.cph.modifiedCphRecords.delete(cphId);
        } else {
            // Modified - add/update in map
            STATE.cph.modifiedCphRecords.set(cphId, {
                id: record.id,
                lob: record.lob,
                case_type: record.case_type,
                target_cph: record.target_cph,
                modified_target_cph: roundedNewValue
            });
        }

        // Update UI
        updateCphModifiedCount();
        updateCphRowHighlight(cphId);
    }

    function updateCphRowHighlight(cphId) {
        const row = $(`tr[data-cph-id="${cphId}"]`);
        const input = $(`input.cph-modified-input[data-cph-id="${cphId}"]`);
        const isModified = STATE.cph.modifiedCphRecords.has(cphId);

        if (isModified) {
            row.addClass('edit-view-cph-row-modified');
            input.addClass('edit-view-input-modified');
        } else {
            row.removeClass('edit-view-cph-row-modified');
            input.removeClass('edit-view-input-modified');
        }
    }

    function updateCphModifiedCount() {
        const count = STATE.cph.modifiedCphRecords.size;
        DOM.cphModifiedCountBadge.text(`${count} modified`);

        // Enable/disable submit button
        if (count > 0) {
            DOM.submitCphChangesBtn.prop('disabled', false);
        } else {
            DOM.submitCphChangesBtn.prop('disabled', true);
        }
    }

    async function handleSubmitCphChanges() {
        console.log('Edit View: Submit CPH Changes clicked');

        const modifiedCount = STATE.cph.modifiedCphRecords.size;

        if (modifiedCount === 0) {
            await Swal.fire({
                icon: 'warning',
                title: 'No Changes',
                text: 'Please modify at least one CPH value before generating preview.',
                confirmButtonColor: '#0d6efd'
            });
            return;
        }

        const { month, year } = STATE.cph.currentSelectedReport;
        const modifiedRecords = Array.from(STATE.cph.modifiedCphRecords.values());

        await loadCphPreview(month, year, modifiedRecords);
    }

    async function loadCphPreview(month, year, modifiedRecords) {
        console.log(`Edit View: Loading CPH preview for ${month} ${year} (${modifiedRecords.length} changes)`);

        showElement(DOM.cphPreviewLoading);
        hideElement(DOM.cphPreviewError);
        hideElement(DOM.cphPreviewContainer);
        hideElement(DOM.cphActionsContainer);

        try {
            const response = await fetch(CONFIG.urls.targetCphPreview, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin',
                body: JSON.stringify({ month, year, modified_records: modifiedRecords })
            });

            if (!response.ok) {
                const errorMsg = await extractErrorMessage(response);

                // Check if errorMsg is an object with error and recommendation
                if (typeof errorMsg === 'object' && errorMsg.error) {
                    const errorObj = {
                        message: errorMsg.error,
                        recommendation: errorMsg.recommendation
                    };
                    throw errorObj;
                }

                throw new Error(errorMsg);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.message || 'Preview calculation failed');
            }

            // Check if there are any affected forecast rows
            if (!data.modified_records || data.modified_records.length === 0) {
                showInlineError(
                    DOM.cphPreviewError,
                    DOM.cphPreviewErrorMessage,
                    'No forecast rows were affected by the CPH changes. The selected CPH values may not have any active forecasts.'
                );
                return;
            }

            // Store preview data
            STATE.cph.previewData = data;
            STATE.cph.allPreviewRecords = data.modified_records || [];
            STATE.cph.filteredPreviewRecords = STATE.cph.allPreviewRecords;
            STATE.cph.previewCurrentPage = 1;
            STATE.cph.previewTotalPages = Math.ceil(data.total_modified / CONFIG.settings.previewPageSize);

            // Render preview (reuse bench allocation rendering functions)
            renderCphPreviewTable(data);
            showElement(DOM.cphPreviewContainer);
            showElement(DOM.cphActionsContainer);

            // Update action summary
            DOM.cphActionSummaryCount.text(modifiedRecords.length);
            DOM.cphForecastRowsCount.text(data.total_modified || 0);

            console.log(`Edit View: CPH preview loaded - ${data.total_modified} forecast rows affected`);

        } catch (error) {
            console.error('Edit View: Error loading CPH preview', error);

            // Check if error has recommendation (from API detail object)
            if (error.message && error.recommendation) {
                const errorMessage = `<strong>${error.message}</strong><br><br><em>Recommendation:</em> ${error.recommendation}`;
                DOM.cphPreviewErrorMessage.html(errorMessage);
                showElement(DOM.cphPreviewError);
            } else {
                showInlineError(
                    DOM.cphPreviewError,
                    DOM.cphPreviewErrorMessage,
                    error.message || 'Failed to calculate CPH impact preview. Please try again.'
                );
            }

        } finally {
            hideElement(DOM.cphPreviewLoading);
        }
    }

    function renderCphPreviewTable(data) {
        if (!data || !data.modified_records || data.modified_records.length === 0) {
            console.warn('Edit View: No CPH preview records to display');
            hideElement(DOM.cphPreviewFilters);
            hideElement(DOM.cphOverallChanges);
            return;
        }

        const config = PREVIEW_CONFIGS.targetCph;

        // Store all records (important for pagination and filtering)
        STATE.cph.allPreviewRecords = data.modified_records;
        STATE.cph.filteredPreviewRecords = data.modified_records;
        STATE.cph.previewTotalPages = Math.ceil(data.modified_records.length / CONFIG.settings.previewPageSize);

        // Update CPH-specific summary badges
        DOM.cphSummaryText.text(
            `${data.total_modified} forecast rows affected by ${STATE.cph.modifiedCphRecords.size} CPH changes`
        );
        DOM.cphPreviewModifiedCountBadge.text(`${data.total_modified} forecast rows affected`);

        // Populate filters using generic system
        populateGenericFilters(data.modified_records, config);

        // Render using generic system (THIS FIXES THE BUG - uses getMonthData with 'direct' access)
        renderGenericPreviewTable(data, config);

        // Show containers
        showElement(DOM.cphPreviewFilters);
        showElement(DOM.cphOverallChanges);
    }

    // NOTE: renderCphPreviewHeaders removed - superseded by renderGenericPreviewTable
    // NOTE: renderCphPreviewRows removed - superseded by renderGenericPreviewTable
    // NOTE: populateCphPreviewFilters removed - superseded by populateGenericFilters
    // NOTE: initializeCphPreviewFilterSelect2 removed - superseded by generic system

    function applyCphPreviewFilters() {
        const config = PREVIEW_CONFIGS.targetCph;
        applyGenericFilters(config);
        renderCphPreviewTable(STATE.cph.previewData);
    }

    function updateCphPreviewCascadingFilters(changedFilter) {
        updateGenericCascadingFilters(changedFilter, PREVIEW_CONFIGS.targetCph);
    }

    function clearCphPreviewFilters() {
        const config = PREVIEW_CONFIGS.targetCph;

        DOM.cphPreviewLobFilter.val(null).trigger('change');
        DOM.cphPreviewCaseTypeFilter.val(null).trigger('change');

        // Repopulate filters with all options
        populateGenericFilters(STATE.cph.allPreviewRecords, config);

        // Apply empty filters
        applyCphPreviewFilters();
    }

    // NOTE: updateCphMonthwiseChanges removed - superseded by generic preview system
    // NOTE: renderCphPreviewPagination removed - superseded by generic preview system

    function handleCphPreviewPageClick(e) {
        e.preventDefault();

        const page = parseInt($(e.currentTarget).data('page'));

        if (isNaN(page) || page < 1 || page > STATE.cph.previewTotalPages) {
            return;
        }

        STATE.cph.previewCurrentPage = page;

        // Just re-render the table with the new page, don't reset state
        const config = PREVIEW_CONFIGS.targetCph;
        renderGenericPreviewTable(STATE.cph.previewData, config);

        // Scroll to preview table top
        DOM.cphPreviewContainer[0].scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    async function handleCphReject() {
        console.log('Edit View: CPH Reject clicked');

        const result = await Swal.fire({
            icon: 'question',
            title: 'Reject CPH Preview?',
            text: 'This will clear the preview. CPH changes will remain in the table for further editing.',
            showCancelButton: true,
            confirmButtonColor: '#6c757d',
            cancelButtonColor: '#0d6efd',
            confirmButtonText: 'Yes, Reject',
            cancelButtonText: 'Cancel'
        });

        if (result.isConfirmed) {
            // Clear preview
            STATE.cph.previewData = null;
            STATE.cph.allPreviewRecords = [];
            STATE.cph.filteredPreviewRecords = [];
            DOM.cphUserNotesInput.val('');
            DOM.cphNotesCharCount.text('0');

            hideElement(DOM.cphPreviewContainer);
            hideElement(DOM.cphActionsContainer);

            console.log('Edit View: CPH preview rejected');
        }
    }

    async function handleCphAccept() {
        console.log('Edit View: CPH Accept clicked');

        const modifiedCount = STATE.cph.modifiedCphRecords.size;

        const result = await Swal.fire({
            icon: 'question',
            title: 'Accept CPH Changes?',
            html: `
                <p>This will update <strong>${modifiedCount} CPH values</strong> affecting <strong>${STATE.cph.previewData.total_modified} forecast rows</strong>.</p>
                <p>This action will create a history log entry.</p>
            `,
            showCancelButton: true,
            confirmButtonColor: '#198754',
            cancelButtonColor: '#6c757d',
            confirmButtonText: 'Yes, Accept',
            cancelButtonText: 'Cancel'
        });

        if (result.isConfirmed) {
            await submitCphUpdate();
        }
    }

    async function submitCphUpdate() {
        console.log('Edit View: Submitting CPH update');

        STATE.isSubmitting = true;

        try {
            // Validate preview data exists
            if (!STATE.cph.previewData || !STATE.cph.previewData.modified_records) {
                showErrorDialog(
                    'No CPH Preview Data',
                    'Please run CPH preview before submitting updates.',
                    'CPH Update'
                );
                return;
            }

            const { month, year } = STATE.cph.currentSelectedReport;
            const userNotes = DOM.cphUserNotesInput.val().trim() || '';

            // Build payload with FULL preview structure
            const payload = {
                month,
                year,
                months: STATE.cph.previewData.months,  // Top-level months mapping
                modified_records: STATE.cph.previewData.modified_records,  // Use FULL preview records
                user_notes: userNotes
            };

            console.log('Edit View: Sending CPH update with full preview structure', {
                modifiedRecordsCount: payload.modified_records.length,
                hasMonthsMapping: !!payload.months
            });

            const response = await fetch(CONFIG.urls.targetCphUpdate, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin',
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorMsg = await extractErrorMessage(response);
                throw new Error(errorMsg);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.message || 'Update failed');
            }

            // Show success message
            await Swal.fire({
                icon: 'success',
                title: 'CPH Updated Successfully',
                html: `
                    <p><strong>${data.cph_changes_applied || STATE.cph.modifiedCphRecords.size}</strong> CPH changes applied</p>
                    <p><strong>${data.forecast_rows_affected || 0}</strong> forecast rows affected</p>
                `,
                confirmButtonColor: '#198754'
            });

            // Reset CPH tab
            STATE.cph.modifiedCphRecords.clear();
            STATE.cph.previewData = null;
            STATE.cph.allPreviewRecords = [];
            STATE.cph.filteredPreviewRecords = [];
            DOM.cphUserNotesInput.val('');
            DOM.cphNotesCharCount.text('0');

            hideElement(DOM.cphPreviewContainer);
            hideElement(DOM.cphActionsContainer);

            // Reload CPH data
            await loadCphData(month, year);

            console.log('Edit View: CPH update successful');

        } catch (error) {
            console.error('Edit View: Error submitting CPH update', error);

            // Show detailed error message
            showErrorDialog(
                'CPH Update Failed',
                'The CPH update could not be completed. Please review the error details and try again.',
                `Error: ${error.message}`
            );

        } finally {
            STATE.isSubmitting = false;
        }
    }

    function handleCphNotesInput(e) {
        const input = $(e.target);
        const charCount = input.val().length;
        const maxLength = CONFIG.settings.maxUserNotesLength;

        DOM.cphNotesCharCount.text(charCount);

        if (charCount > maxLength) {
            input.val(input.val().substring(0, maxLength));
            DOM.cphNotesCharCount.text(maxLength);
        }
    }

    // ============================================================================
    // FORECAST REALLOCATION HANDLERS
    // ============================================================================

    /**
     * Populate the reallocation report dropdown with allocation reports
     */
    function populateReallocationReportDropdown() {
        // Copy options from the main allocation report dropdown
        const options = DOM.allocationReportSelect.find('option').clone();
        DOM.reallocationReportSelect.empty().append(options);
        DOM.reallocationReportSelect.trigger('change');
    }

    /**
     * Load filter options for the reallocation tab
     */
    async function loadReallocationFilterOptions(month, year) {
        try {
            const url = `${CONFIG.urls.forecastReallocationFilters}?month=${encodeURIComponent(month)}&year=${year}`;
            const response = await $.ajax({
                url: url,
                method: 'GET',
                dataType: 'json'
            });

            if (response.success) {
                STATE.reallocation.filterOptions = {
                    mainLobs: response.main_lobs || [],
                    states: response.states || [],
                    caseTypes: response.case_types || []
                };

                // Populate filter dropdowns
                populateReallocationFilterDropdowns();
            }
        } catch (error) {
            console.error('Edit View: Failed to load reallocation filter options', error);
        }
    }

    /**
     * Populate the reallocation filter dropdowns
     */
    function populateReallocationFilterDropdowns() {
        const { mainLobs, states, caseTypes } = STATE.reallocation.filterOptions;

        // Main LOB filter
        DOM.reallocationLobFilter.empty();
        mainLobs.forEach(lob => {
            DOM.reallocationLobFilter.append(new Option(lob, lob, false, false));
        });
        DOM.reallocationLobFilter.trigger('change');

        // State filter
        DOM.reallocationStateFilter.empty();
        states.forEach(state => {
            DOM.reallocationStateFilter.append(new Option(state, state, false, false));
        });
        DOM.reallocationStateFilter.trigger('change');

        // Case Type filter
        DOM.reallocationCaseTypeFilter.empty();
        caseTypes.forEach(ct => {
            DOM.reallocationCaseTypeFilter.append(new Option(ct, ct, false, false));
        });
        DOM.reallocationCaseTypeFilter.trigger('change');
    }

    /**
     * Handle Load Data button click for reallocation
     */
    async function handleLoadReallocationData() {
        const selectedValue = DOM.reallocationReportSelect.val();

        if (!selectedValue) {
            showErrorDialog('Selection Required', 'Please select a report month before loading data.');
            return;
        }

        // Parse the selected value (format: "Month YYYY" e.g., "April 2025")
        const parts = selectedValue.split(' ');
        if (parts.length !== 2) {
            showErrorDialog('Invalid Selection', 'Invalid report format. Please select a valid report.');
            return;
        }

        const month = parts[0];
        const year = parseInt(parts[1], 10);

        // Store selected report
        STATE.reallocation.currentSelectedReport = { month, year };

        // Reset state
        STATE.reallocation.allRecords = [];
        STATE.reallocation.filteredRecords = [];
        STATE.reallocation.modifiedRecords.clear();
        STATE.reallocation.currentPage = 1;

        // Load filter options first
        await loadReallocationFilterOptions(month, year);

        // Get selected filters
        const mainLobs = DOM.reallocationLobFilter.val() || [];
        const caseTypes = DOM.reallocationCaseTypeFilter.val() || [];
        const states = DOM.reallocationStateFilter.val() || [];

        // Load data
        await loadReallocationData(month, year, mainLobs, caseTypes, states);
    }

    /**
     * Load reallocation data from API
     */
    async function loadReallocationData(month, year, mainLobs, caseTypes, states) {
        showElement(DOM.reallocationDataLoading);
        hideElement(DOM.reallocationDataError);
        hideElement(DOM.reallocationDataContainer);
        hideElement(DOM.reallocationPreviewContainer);
        hideElement(DOM.reallocationActionsContainer);

        try {
            // Build query params
            let url = `${CONFIG.urls.forecastReallocationData}?month=${encodeURIComponent(month)}&year=${year}`;

            mainLobs.forEach(lob => {
                url += `&main_lobs[]=${encodeURIComponent(lob)}`;
            });
            caseTypes.forEach(ct => {
                url += `&case_types[]=${encodeURIComponent(ct)}`;
            });
            states.forEach(s => {
                url += `&states[]=${encodeURIComponent(s)}`;
            });

            const response = await $.ajax({
                url: url,
                method: 'GET',
                dataType: 'json'
            });

            if (response.success !== false) {
                STATE.reallocation.allRecords = response.data || [];
                STATE.reallocation.filteredRecords = [...STATE.reallocation.allRecords];
                STATE.reallocation.monthsMapping = response.months || {};

                // Get all month keys
                STATE.reallocation.allMonths = Object.keys(response.months || {}).map(key => response.months[key]);
                STATE.reallocation.visibleMonths = [...STATE.reallocation.allMonths].slice(0, 6);

                // Render month checkboxes
                renderReallocationMonthCheckboxes();

                // Render table
                renderReallocationDataTable();

                // Update modified count
                updateReallocationModifiedCount();

                showElement(DOM.reallocationDataContainer);

                console.log(`Edit View: Loaded ${STATE.reallocation.allRecords.length} reallocation records`);
            } else {
                throw new Error(response.message || response.error || 'Failed to load data');
            }

        } catch (error) {
            console.error('Edit View: Failed to load reallocation data', error);
            DOM.reallocationDataErrorMessage.text(error.message || 'Failed to load reallocation data');
            showElement(DOM.reallocationDataError);
        } finally {
            hideElement(DOM.reallocationDataLoading);
        }
    }

    /**
     * Render month visibility checkboxes
     */
    function renderReallocationMonthCheckboxes() {
        DOM.reallocationMonthCheckboxes.empty();

        STATE.reallocation.allMonths.forEach((monthLabel, idx) => {
            const isChecked = STATE.reallocation.visibleMonths.includes(monthLabel);
            const checkbox = $(`
                <div class="edit-view-month-checkbox">
                    <input type="checkbox" id="month-cb-${idx}" class="reallocation-month-checkbox"
                           data-month="${monthLabel}" ${isChecked ? 'checked' : ''}>
                    <label for="month-cb-${idx}">${monthLabel}</label>
                </div>
            `);
            DOM.reallocationMonthCheckboxes.append(checkbox);
        });
    }

    /**
     * Handle month visibility checkbox change
     */
    function handleReallocationMonthVisibility(e) {
        const checkbox = $(e.target);
        const monthLabel = checkbox.data('month');
        const isChecked = checkbox.is(':checked');

        if (isChecked) {
            if (!STATE.reallocation.visibleMonths.includes(monthLabel)) {
                STATE.reallocation.visibleMonths.push(monthLabel);
            }
        } else {
            STATE.reallocation.visibleMonths = STATE.reallocation.visibleMonths.filter(m => m !== monthLabel);
        }

        // Limit to 6 visible months
        if (STATE.reallocation.visibleMonths.length > 6) {
            STATE.reallocation.visibleMonths = STATE.reallocation.visibleMonths.slice(0, 6);
            // Update checkboxes
            renderReallocationMonthCheckboxes();
            showToast('Maximum 6 months can be visible at once', 'warning');
        }

        // Re-render table with updated visibility
        renderReallocationDataTable();
    }

    /**
     * Render the reallocation data table
     */
    function renderReallocationDataTable() {
        const records = STATE.reallocation.filteredRecords;
        const pageSize = CONFIG.settings.previewPageSize;
        const startIdx = (STATE.reallocation.currentPage - 1) * pageSize;
        const endIdx = startIdx + pageSize;
        const pageRecords = records.slice(startIdx, endIdx);

        // Render table header
        renderReallocationTableHeader();

        // Render table body
        const tbody = DOM.reallocationTableBody;
        tbody.empty();

        if (pageRecords.length === 0) {
            tbody.append(`
                <tr>
                    <td colspan="100" class="text-center text-muted py-4">
                        No records found. Try adjusting your filters.
                    </td>
                </tr>
            `);
        } else {
            pageRecords.forEach(record => {
                tbody.append(renderReallocationDataRow(record));
            });
        }

        // Update pagination
        STATE.reallocation.totalPages = Math.ceil(records.length / pageSize);
        renderReallocationPagination();
    }

    /**
     * Render the table header for reallocation
     */
    function renderReallocationTableHeader() {
        const thead = DOM.reallocationTableHead;
        thead.empty();

        // Main header row
        const headerRow = $('<tr></tr>');

        // Fixed columns
        headerRow.append('<th class="edit-view-frozen-col-1">Main LOB</th>');
        headerRow.append('<th class="edit-view-frozen-col-2">State</th>');
        headerRow.append('<th class="edit-view-frozen-col-3">Case Type</th>');
        headerRow.append('<th class="edit-view-frozen-col-4">Target CPH</th>');

        // Month columns (only visible months)
        STATE.reallocation.visibleMonths.forEach(monthLabel => {
            headerRow.append(`
                <th colspan="4" class="edit-view-month-group-header">${monthLabel}</th>
            `);
        });

        thead.append(headerRow);

        // Sub-header row for month columns
        const subHeaderRow = $('<tr></tr>');
        subHeaderRow.append('<th></th><th></th><th></th><th></th>'); // Empty cells for frozen columns

        STATE.reallocation.visibleMonths.forEach(() => {
            subHeaderRow.append(`
                <th class="edit-view-month-subheader">CF</th>
                <th class="edit-view-month-subheader">FTE Req</th>
                <th class="edit-view-month-subheader">FTE Avail</th>
                <th class="edit-view-month-subheader">Cap</th>
            `);
        });

        thead.append(subHeaderRow);
    }

    /**
     * Render a single data row for reallocation table
     */
    function renderReallocationDataRow(record) {
        const caseId = record.case_id;
        const isModified = STATE.reallocation.modifiedRecords.has(caseId);
        const modifiedRecord = isModified ? STATE.reallocation.modifiedRecords.get(caseId) : record;

        const row = $(`<tr data-case-id="${caseId}" class="${isModified ? 'edit-view-reallocation-row-modified' : ''}"></tr>`);

        // Fixed columns
        row.append(`<td class="text-left">${escapeHtml(record.main_lob)}</td>`);
        row.append(`<td class="text-center">${escapeHtml(record.state)}</td>`);
        row.append(`<td class="text-center">${escapeHtml(record.case_type)}</td>`);

        // Target CPH - editable
        const targetCph = modifiedRecord.target_cph || record.target_cph || 0;
        const originalCph = record.target_cph || 0;
        const cphModified = targetCph !== originalCph;
        row.append(`
            <td class="${cphModified ? 'edit-view-cell-modified' : ''}">
                <div class="edit-view-cell-controls">
                    <button class="edit-view-btn-decrement reallocation-decrement-btn"
                            data-case-id="${caseId}" data-field="target_cph" data-step="1">
                        <i class="fas fa-minus"></i>
                    </button>
                    <input type="number" class="edit-view-cell-input reallocation-input ${cphModified ? 'edit-view-cell-modified-input' : ''}"
                           data-case-id="${caseId}" data-field="target_cph"
                           value="${targetCph.toFixed(2)}" min="0" max="200" step="1">
                    <button class="edit-view-btn-increment reallocation-increment-btn"
                            data-case-id="${caseId}" data-field="target_cph" data-step="1">
                        <i class="fas fa-plus"></i>
                    </button>
                </div>
            </td>
        `);

        // Month columns
        const months = modifiedRecord.months || record.months || {};
        STATE.reallocation.visibleMonths.forEach(monthLabel => {
            const monthData = months[monthLabel] || {};
            const originalMonthData = (record.months || {})[monthLabel] || {};

            // CF (not editable)
            row.append(`<td class="text-center">${formatNumber(monthData.forecast || 0)}</td>`);

            // FTE Req (not editable)
            row.append(`<td class="text-center">${formatNumber(monthData.fte_req || 0)}</td>`);

            // FTE Avail (editable)
            const fteAvail = monthData.fte_avail ?? 0;
            const originalFte = originalMonthData.fte_avail ?? 0;
            const fteModified = fteAvail !== originalFte;
            row.append(`
                <td class="${fteModified ? 'edit-view-cell-modified' : ''}">
                    <div class="edit-view-cell-controls">
                        <button class="edit-view-btn-decrement reallocation-decrement-btn"
                                data-case-id="${caseId}" data-field="fte_avail" data-month="${monthLabel}" data-step="1">
                            <i class="fas fa-minus"></i>
                        </button>
                        <input type="number" class="edit-view-cell-input reallocation-input ${fteModified ? 'edit-view-cell-modified-input' : ''}"
                               data-case-id="${caseId}" data-field="fte_avail" data-month="${monthLabel}"
                               value="${fteAvail}" min="0" max="999" step="1">
                        <button class="edit-view-btn-increment reallocation-increment-btn"
                                data-case-id="${caseId}" data-field="fte_avail" data-month="${monthLabel}" data-step="1">
                            <i class="fas fa-plus"></i>
                        </button>
                    </div>
                </td>
            `);

            // Capacity (not editable)
            row.append(`<td class="text-center">${formatNumber(monthData.capacity || 0)}</td>`);
        });

        return row;
    }

    /**
     * Render pagination for reallocation data table
     */
    function renderReallocationPagination() {
        const totalPages = STATE.reallocation.totalPages;
        const currentPage = STATE.reallocation.currentPage;

        if (totalPages <= 1) {
            hideElement(DOM.reallocationPagination);
            return;
        }

        const paginationHtml = renderPaginationHtml(currentPage, totalPages, 'edit-view-reallocation-pagination');
        DOM.reallocationPagination.find('ul').html(paginationHtml);
        showElement(DOM.reallocationPagination);
    }

    /**
     * Handle page click for reallocation data table
     */
    function handleReallocationPageClick(e) {
        e.preventDefault();
        const page = parseInt($(e.currentTarget).data('page'), 10);
        if (page && page !== STATE.reallocation.currentPage) {
            STATE.reallocation.currentPage = page;
            renderReallocationDataTable();
        }
    }

    /**
     * Handle increment button click
     */
    function handleReallocationIncrement(e) {
        const btn = $(e.currentTarget);
        const caseId = btn.data('case-id');
        const field = btn.data('field');
        const month = btn.data('month');
        const step = parseFloat(btn.data('step') || 1);

        updateReallocationValue(caseId, field, month, step);
    }

    /**
     * Handle decrement button click
     */
    function handleReallocationDecrement(e) {
        const btn = $(e.currentTarget);
        const caseId = btn.data('case-id');
        const field = btn.data('field');
        const month = btn.data('month');
        const step = parseFloat(btn.data('step') || 1);

        updateReallocationValue(caseId, field, month, -step);
    }

    /**
     * Handle input change
     */
    function handleReallocationInputChange(e) {
        const input = $(e.target);
        const caseId = input.data('case-id');
        const field = input.data('field');
        const month = input.data('month');
        const newValue = parseFloat(input.val()) || 0;

        setReallocationValue(caseId, field, month, newValue);
    }

    /**
     * Update a reallocation value by delta
     */
    function updateReallocationValue(caseId, field, month, delta) {
        const originalRecord = STATE.reallocation.allRecords.find(r => r.case_id === caseId);
        if (!originalRecord) return;

        let modifiedRecord = STATE.reallocation.modifiedRecords.get(caseId);
        if (!modifiedRecord) {
            modifiedRecord = JSON.parse(JSON.stringify(originalRecord));
            modifiedRecord.modified_fields = [];
        }

        let currentValue, newValue, min, max;

        if (field === 'target_cph') {
            currentValue = modifiedRecord.target_cph || originalRecord.target_cph || 0;
            min = 0;
            max = 200;
            newValue = Math.max(min, Math.min(max, currentValue + delta));
            modifiedRecord.target_cph = parseFloat(newValue.toFixed(2));
            modifiedRecord.target_cph_change = modifiedRecord.target_cph - (originalRecord.target_cph || 0);

            if (!modifiedRecord.modified_fields.includes('target_cph')) {
                modifiedRecord.modified_fields.push('target_cph');
            }
        } else if (field === 'fte_avail' && month) {
            if (!modifiedRecord.months) modifiedRecord.months = {};
            if (!modifiedRecord.months[month]) {
                modifiedRecord.months[month] = JSON.parse(JSON.stringify(originalRecord.months[month] || {}));
            }

            currentValue = modifiedRecord.months[month].fte_avail ?? 0;
            min = 0;
            max = 999;
            newValue = Math.max(min, Math.min(max, Math.round(currentValue + delta)));
            modifiedRecord.months[month].fte_avail = newValue;

            const originalFte = (originalRecord.months[month] || {}).fte_avail ?? 0;
            modifiedRecord.months[month].fte_avail_change = newValue - originalFte;

            const fieldKey = `${month}.fte_avail`;
            if (!modifiedRecord.modified_fields.includes(fieldKey)) {
                modifiedRecord.modified_fields.push(fieldKey);
            }
        }

        // Check if record is actually modified from original
        const isActuallyModified = checkRecordModified(originalRecord, modifiedRecord);

        if (isActuallyModified) {
            STATE.reallocation.modifiedRecords.set(caseId, modifiedRecord);
        } else {
            STATE.reallocation.modifiedRecords.delete(caseId);
        }

        // Update the row
        const row = DOM.reallocationTableBody.find(`tr[data-case-id="${caseId}"]`);
        row.replaceWith(renderReallocationDataRow(
            STATE.reallocation.modifiedRecords.get(caseId) || originalRecord
        ));

        updateReallocationModifiedCount();
    }

    /**
     * Set a reallocation value directly
     */
    function setReallocationValue(caseId, field, month, newValue) {
        const originalRecord = STATE.reallocation.allRecords.find(r => r.case_id === caseId);
        if (!originalRecord) return;

        let modifiedRecord = STATE.reallocation.modifiedRecords.get(caseId);
        if (!modifiedRecord) {
            modifiedRecord = JSON.parse(JSON.stringify(originalRecord));
            modifiedRecord.modified_fields = [];
        }

        if (field === 'target_cph') {
            newValue = Math.max(0, Math.min(200, newValue));
            modifiedRecord.target_cph = parseFloat(newValue.toFixed(2));
            modifiedRecord.target_cph_change = modifiedRecord.target_cph - (originalRecord.target_cph || 0);

            if (!modifiedRecord.modified_fields.includes('target_cph')) {
                modifiedRecord.modified_fields.push('target_cph');
            }
        } else if (field === 'fte_avail' && month) {
            if (!modifiedRecord.months) modifiedRecord.months = {};
            if (!modifiedRecord.months[month]) {
                modifiedRecord.months[month] = JSON.parse(JSON.stringify(originalRecord.months[month] || {}));
            }

            newValue = Math.max(0, Math.min(999, Math.round(newValue)));
            modifiedRecord.months[month].fte_avail = newValue;

            const originalFte = (originalRecord.months[month] || {}).fte_avail ?? 0;
            modifiedRecord.months[month].fte_avail_change = newValue - originalFte;

            const fieldKey = `${month}.fte_avail`;
            if (!modifiedRecord.modified_fields.includes(fieldKey)) {
                modifiedRecord.modified_fields.push(fieldKey);
            }
        }

        const isActuallyModified = checkRecordModified(originalRecord, modifiedRecord);

        if (isActuallyModified) {
            STATE.reallocation.modifiedRecords.set(caseId, modifiedRecord);
        } else {
            STATE.reallocation.modifiedRecords.delete(caseId);
        }

        updateReallocationModifiedCount();
    }

    /**
     * Check if a record is actually modified from the original
     */
    function checkRecordModified(original, modified) {
        // Check target_cph
        if (modified.target_cph !== original.target_cph) {
            return true;
        }

        // Check each month's fte_avail
        if (modified.months) {
            for (const month in modified.months) {
                const origFte = (original.months[month] || {}).fte_avail ?? 0;
                const modFte = modified.months[month].fte_avail ?? 0;
                if (origFte !== modFte) {
                    return true;
                }
            }
        }

        return false;
    }

    /**
     * Update the modified count badge
     */
    function updateReallocationModifiedCount() {
        const count = STATE.reallocation.modifiedRecords.size;
        DOM.reallocationModifiedCountBadge.text(`${count} modified`);

        // Enable/disable preview button
        DOM.showReallocationPreviewBtn.prop('disabled', count === 0);
    }

    /**
     * Handle Show Preview button click
     */
    async function handleShowReallocationPreview() {
        if (STATE.reallocation.modifiedRecords.size === 0) {
            showErrorDialog('No Changes', 'Please make some changes before generating a preview.');
            return;
        }

        const { month, year } = STATE.reallocation.currentSelectedReport;
        const modifiedRecords = Array.from(STATE.reallocation.modifiedRecords.values());

        showElement(DOM.reallocationPreviewLoading);
        hideElement(DOM.reallocationPreviewError);
        hideElement(DOM.reallocationPreviewContainer);
        hideElement(DOM.reallocationActionsContainer);

        try {
            const response = await $.ajax({
                url: CONFIG.urls.forecastReallocationPreview,
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    month: month,
                    year: year,
                    modified_records: modifiedRecords
                })
            });

            if (response.success !== false) {
                STATE.reallocation.previewData = response;
                STATE.reallocation.allPreviewRecords = response.modified_records || [];
                STATE.reallocation.filteredPreviewRecords = [...STATE.reallocation.allPreviewRecords];
                STATE.reallocation.previewCurrentPage = 1;

                // Render preview
                renderReallocationPreview();

                showElement(DOM.reallocationPreviewContainer);
                showElement(DOM.reallocationActionsContainer);

                // Update counts
                DOM.reallocationPreviewModifiedCountBadge.text(`${STATE.reallocation.allPreviewRecords.length} records modified`);
                DOM.reallocationActionSummaryCount.text(STATE.reallocation.allPreviewRecords.length);

                console.log('Edit View: Reallocation preview generated');
            } else {
                throw new Error(response.message || response.error || 'Failed to generate preview');
            }

        } catch (error) {
            console.error('Edit View: Failed to generate reallocation preview', error);
            DOM.reallocationPreviewErrorMessage.text(error.message || 'Failed to generate preview');
            showElement(DOM.reallocationPreviewError);
        } finally {
            hideElement(DOM.reallocationPreviewLoading);
        }
    }

    /**
     * Render the reallocation preview using generic preview system
     */
    function renderReallocationPreview() {
        // Use the generic preview rendering system
        const config = PREVIEW_CONFIGS.forecastReallocation;
        const records = STATE.reallocation.filteredPreviewRecords;
        const pageSize = CONFIG.settings.previewPageSize;
        const currentPage = STATE.reallocation.previewCurrentPage;
        const startIdx = (currentPage - 1) * pageSize;
        const endIdx = startIdx + pageSize;
        const pageRecords = records.slice(startIdx, endIdx);

        // Get months mapping from state
        const monthsMapping = STATE.reallocation.monthsMapping || {};

        // Render using generic preview table
        renderGenericPreviewTable(
            config,
            pageRecords,
            monthsMapping,
            DOM.reallocationPreviewTableHead,
            DOM.reallocationPreviewTableBody
        );

        // Update pagination
        STATE.reallocation.previewTotalPages = Math.ceil(records.length / pageSize);
        renderReallocationPreviewPagination();

        // Update summary
        DOM.reallocationSummaryText.text(`${records.length} records will be modified`);

        // Populate preview filters
        populateReallocationPreviewFilters();
    }

    /**
     * Render preview pagination
     */
    function renderReallocationPreviewPagination() {
        const totalPages = STATE.reallocation.previewTotalPages;
        const currentPage = STATE.reallocation.previewCurrentPage;

        if (totalPages <= 1) {
            hideElement(DOM.reallocationPreviewPagination);
            return;
        }

        const paginationHtml = renderPaginationHtml(currentPage, totalPages, 'edit-view-reallocation-preview-pagination');
        DOM.reallocationPreviewPagination.find('ul').html(paginationHtml);
        showElement(DOM.reallocationPreviewPagination);
    }

    /**
     * Handle preview page click
     */
    function handleReallocationPreviewPageClick(e) {
        e.preventDefault();
        const page = parseInt($(e.currentTarget).data('page'), 10);
        if (page && page !== STATE.reallocation.previewCurrentPage) {
            STATE.reallocation.previewCurrentPage = page;
            renderReallocationPreview();
        }
    }

    /**
     * Populate preview filters with unique values
     */
    function populateReallocationPreviewFilters() {
        const records = STATE.reallocation.allPreviewRecords;

        // Get unique LOBs and Case Types
        const lobs = [...new Set(records.map(r => r.main_lob))].sort();
        const caseTypes = [...new Set(records.map(r => r.case_type))].sort();

        // Populate LOB filter
        DOM.reallocationPreviewLobFilter.empty();
        lobs.forEach(lob => {
            DOM.reallocationPreviewLobFilter.append(new Option(lob, lob, false, false));
        });
        DOM.reallocationPreviewLobFilter.trigger('change');

        // Populate Case Type filter
        DOM.reallocationPreviewCaseTypeFilter.empty();
        caseTypes.forEach(ct => {
            DOM.reallocationPreviewCaseTypeFilter.append(new Option(ct, ct, false, false));
        });
        DOM.reallocationPreviewCaseTypeFilter.trigger('change');

        if (lobs.length > 1 || caseTypes.length > 1) {
            showElement(DOM.reallocationPreviewFilters);
        }
    }

    /**
     * Apply preview filters
     */
    function applyReallocationPreviewFilters() {
        const selectedLobs = DOM.reallocationPreviewLobFilter.val() || [];
        const selectedCaseTypes = DOM.reallocationPreviewCaseTypeFilter.val() || [];

        let filtered = [...STATE.reallocation.allPreviewRecords];

        if (selectedLobs.length > 0) {
            filtered = filtered.filter(r => selectedLobs.includes(r.main_lob));
        }

        if (selectedCaseTypes.length > 0) {
            filtered = filtered.filter(r => selectedCaseTypes.includes(r.case_type));
        }

        STATE.reallocation.filteredPreviewRecords = filtered;
        STATE.reallocation.previewCurrentPage = 1;

        renderReallocationPreview();
    }

    /**
     * Clear preview filters
     */
    function clearReallocationPreviewFilters() {
        DOM.reallocationPreviewLobFilter.val(null).trigger('change');
        DOM.reallocationPreviewCaseTypeFilter.val(null).trigger('change');

        STATE.reallocation.filteredPreviewRecords = [...STATE.reallocation.allPreviewRecords];
        STATE.reallocation.previewCurrentPage = 1;

        renderReallocationPreview();
    }

    /**
     * Handle Reject button click
     */
    function handleReallocationReject() {
        Swal.fire({
            title: 'Reject Changes?',
            text: 'Are you sure you want to discard all changes?',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#dc3545',
            cancelButtonColor: '#6c757d',
            confirmButtonText: 'Yes, discard',
            cancelButtonText: 'Cancel'
        }).then((result) => {
            if (result.isConfirmed) {
                // Clear modified records
                STATE.reallocation.modifiedRecords.clear();

                // Hide preview and actions
                hideElement(DOM.reallocationPreviewContainer);
                hideElement(DOM.reallocationActionsContainer);

                // Clear user notes
                DOM.reallocationUserNotesInput.val('');
                DOM.reallocationNotesCharCount.text('0');

                // Re-render table
                renderReallocationDataTable();
                updateReallocationModifiedCount();

                showToast('Changes discarded', 'info');
            }
        });
    }

    /**
     * Handle Accept button click
     */
    async function handleReallocationAccept() {
        if (STATE.isSubmitting) return;

        const modifiedCount = STATE.reallocation.modifiedRecords.size;
        if (modifiedCount === 0) {
            showErrorDialog('No Changes', 'There are no changes to submit.');
            return;
        }

        const result = await Swal.fire({
            title: 'Confirm Changes',
            html: `
                <p>You are about to update <strong>${modifiedCount}</strong> records.</p>
                <p>This action cannot be undone.</p>
            `,
            icon: 'question',
            showCancelButton: true,
            confirmButtonColor: '#198754',
            cancelButtonColor: '#6c757d',
            confirmButtonText: 'Yes, update',
            cancelButtonText: 'Cancel'
        });

        if (!result.isConfirmed) return;

        STATE.isSubmitting = true;
        const { month, year } = STATE.reallocation.currentSelectedReport;
        const modifiedRecords = Array.from(STATE.reallocation.modifiedRecords.values());
        const userNotes = DOM.reallocationUserNotesInput.val().trim();

        try {
            showSubmittingDialog('Submitting reallocation changes...');

            const response = await $.ajax({
                url: CONFIG.urls.forecastReallocationUpdate,
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    month: month,
                    year: year,
                    months: STATE.reallocation.monthsMapping,
                    modified_records: modifiedRecords,
                    user_notes: userNotes
                })
            });

            Swal.close();

            if (response.success !== false) {
                showSuccessDialog(
                    'Update Successful',
                    `Successfully updated ${response.records_updated || modifiedCount} records.`
                );

                // Clear state
                STATE.reallocation.modifiedRecords.clear();
                STATE.reallocation.previewData = null;

                // Clear user notes
                DOM.reallocationUserNotesInput.val('');
                DOM.reallocationNotesCharCount.text('0');

                // Hide preview and actions
                hideElement(DOM.reallocationPreviewContainer);
                hideElement(DOM.reallocationActionsContainer);

                // Reload data
                await loadReallocationData(month, year, [], [], []);

                console.log('Edit View: Reallocation update successful');
            } else {
                throw new Error(response.message || response.error || 'Update failed');
            }

        } catch (error) {
            console.error('Edit View: Error submitting reallocation update', error);
            showErrorDialog(
                'Update Failed',
                'The reallocation update could not be completed.',
                `Error: ${error.message}`
            );
        } finally {
            STATE.isSubmitting = false;
        }
    }

    /**
     * Handle user notes input
     */
    function handleReallocationNotesInput(e) {
        const input = $(e.target);
        const charCount = input.val().length;
        const maxLength = CONFIG.settings.maxUserNotesLength;

        DOM.reallocationNotesCharCount.text(charCount);

        if (charCount > maxLength) {
            input.val(input.val().substring(0, maxLength));
            DOM.reallocationNotesCharCount.text(maxLength);
        }
    }

    // ============================================================================
    // START APPLICATION
    // ============================================================================

    init();

})();
