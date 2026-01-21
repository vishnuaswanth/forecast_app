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

    const CONFIG = window.EDIT_VIEW_CONFIG || {
        urls: {
            allocationReports: '/api/edit-view/allocation-reports/',
            benchAllocationPreview: '/api/edit-view/bench-allocation/preview/',
            benchAllocationUpdate: '/api/edit-view/bench-allocation/update/',
            historyLog: '/api/edit-view/history-log/',
            downloadHistoryExcel: '/api/edit-view/history-log/{id}/download/'
        },
        settings: {
            previewPageSize: 25,
            historyPageSize: 5,
            historyInitialLoad: 20,
            historyLazyLoadSize: 10,
            historyShowMoreThreshold: 3,
            maxUserNotesLength: 500,
            enableUserNotes: true
        }
    };

    const STATE = {
        // Preview data
        currentPreviewData: null,
        currentSelectedReport: null, // {month: "April", year: 2025}
        previewCurrentPage: 1,
        previewTotalPages: 0,

        // History data
        currentHistoryData: null,
        historyCurrentPage: 1,
        historyTotalPages: 0,
        historyFilters: {
            month: null,
            year: null,
            changeTypes: []
        },

        // Loading states
        isLoadingPreview: false,
        isLoadingHistory: false,
        isSubmitting: false,

        // Cache (optional - can add later)
        cache: new Map(),
        cacheTTL: 300000  // 5 minutes
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
        console.log('Edit View: Initializing v1.0.0...');

        cacheDOMElements();
        initializeSelect2();
        attachEventListeners();
        loadAllocationReports();

        console.log('Edit View: Initialization complete');
    }

    function cacheDOMElements() {
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
        DOM.historyPagination = $('#history-pagination');

        // Tab buttons
        DOM.benchAllocationTabBtn = $('#bench-allocation-tab-btn');
        DOM.historyLogTabBtn = $('#history-log-tab-btn');
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

        console.log('Edit View: Select2 initialized');
    }

    function attachEventListeners() {
        // Bench Allocation tab
        DOM.runAllocationBtn.on('click', handleRunAllocation);
        DOM.rejectBtn.on('click', handleReject);
        DOM.acceptBtn.on('click', handleAccept);
        DOM.userNotesInput.on('input', handleNotesInput);

        // History Log tab
        DOM.applyHistoryFiltersBtn.on('click', handleApplyHistoryFilters);

        // Tab switching
        DOM.historyLogTabBtn.on('shown.bs.tab', function() {
            // Load history when tab is activated (only first time)
            if (!STATE.currentHistoryData) {
                loadHistoryLog();
            }
        });

        // Event delegation for dynamically created elements
        $(document).on('click', '.preview-pagination .page-link', handlePreviewPageClick);
        $(document).on('click', '.history-pagination .page-link', handleHistoryPageClick);
        $(document).on('click', '.edit-view-show-more-btn', handleShowMoreClick);
        $(document).on('click', '.edit-view-download-excel-btn', handleExcelDownload);

        console.log('Edit View: Event listeners attached');
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
                const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();

            if (!data.success || !data.data || data.data.length === 0) {
                console.warn('Edit View: No allocation reports available');
                return;
            }

            // Populate dropdown
            DOM.allocationReportSelect.empty().append('<option value="">-- Select Report Month --</option>');
            DOM.historyReportSelect.empty().append('<option value="">-- All Reports --</option>');

            data.data.forEach(report => {
                const option = $('<option>').val(report.value).text(report.display);
                DOM.allocationReportSelect.append(option.clone());
                DOM.historyReportSelect.append(option.clone());
            });

            console.log(`Edit View: Loaded ${data.total} allocation reports`);

        } catch (error) {
            console.error('Edit View: Error loading allocation reports', error);
            showErrorAlert('Failed to load allocation reports: ' + error.message);
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
                const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.message || 'Preview calculation failed');
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
            DOM.previewErrorMessage.text(error.message || 'Failed to load preview');
            showElement(DOM.previewError);

        } finally {
            STATE.isLoadingPreview = false;
            hideElement(DOM.previewLoading);
        }
    }

    // ============================================================================
    // PREVIEW TABLE RENDERING
    // ============================================================================

    function renderPreviewTable(data) {
        if (!data || !data.modified_records || data.modified_records.length === 0) {
            console.warn('Edit View: No modified records to display');
            return;
        }

        const records = data.modified_records;
        const totalModified = data.total_modified;

        // Update badge and summary
        DOM.modifiedCountBadge.text(`${totalModified} ${totalModified === 1 ? 'record' : 'records'} modified`);
        DOM.summaryText.text(`${totalModified} ${totalModified === 1 ? 'record' : 'records'} modified`);
        DOM.actionSummaryCount.text(totalModified);

        // Extract unique months from first record
        const firstRecord = records[0];
        const months = extractMonthsFromRecord(firstRecord);

        // Render table headers
        renderPreviewHeaders(months);

        // Paginate records
        const startIndex = (STATE.previewCurrentPage - 1) * CONFIG.settings.previewPageSize;
        const endIndex = startIndex + CONFIG.settings.previewPageSize;
        const pageRecords = records.slice(startIndex, endIndex);

        // Render table rows
        renderPreviewRows(pageRecords, months);

        // Render pagination
        renderPreviewPagination();
    }

    function extractMonthsFromRecord(record) {
        // Assuming structure: record has _modified_fields and month keys
        // Example: record["Jun-25"] = {forecast: 12500, fte_req: 10.5, ...}
        const months = [];
        const monthPattern = /^[A-Z][a-z]{2}-\d{2}$/; // e.g., "Jun-25"

        for (const key in record) {
            if (monthPattern.test(key)) {
                months.push(key);
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

    function renderPreviewHeaders(months) {
        DOM.previewTableHead.empty();

        // Row 1: Main headers
        const headerRow1 = $('<tr>');
        headerRow1.append('<th rowspan="2" class="text-center" style="vertical-align: middle;">Main LOB</th>');
        headerRow1.append('<th rowspan="2" class="text-center" style="vertical-align: middle;">State</th>');
        headerRow1.append('<th rowspan="2" class="text-center" style="vertical-align: middle;">Case Type</th>');
        headerRow1.append('<th rowspan="2" class="text-center" style="vertical-align: middle;">Case Type ID</th>');
        headerRow1.append('<th rowspan="2" class="text-center" style="vertical-align: middle;">Target CPH</th>');

        months.forEach(month => {
            headerRow1.append(`<th colspan="4" class="text-center edit-view-month-header">${month}</th>`);
        });

        // Row 2: Sub-headers
        const headerRow2 = $('<tr>');
        months.forEach(() => {
            headerRow2.append('<th class="text-center">Forecast</th>');
            headerRow2.append('<th class="text-center">FTE Req</th>');
            headerRow2.append('<th class="text-center">FTE Avail</th>');
            headerRow2.append('<th class="text-center">Capacity</th>');
        });

        DOM.previewTableHead.append(headerRow1).append(headerRow2);
    }

    function renderPreviewRows(records, months) {
        DOM.previewTableBody.empty();

        records.forEach(record => {
            const tr = $('<tr>');

            // Static columns
            tr.append(`<td>${escapeHtml(record.main_lob || '-')}</td>`);
            tr.append(`<td>${escapeHtml(record.state || '-')}</td>`);
            tr.append(`<td>${escapeHtml(record.case_type || '-')}</td>`);
            tr.append(`<td>${escapeHtml(record.case_id || '-')}</td>`);

            // Target CPH (check if modified)
            const modifiedFields = record._modified_fields || [];
            const targetCPHModified = modifiedFields.includes('target_cph');
            const cphClass = targetCPHModified ? 'edit-view-modified-cell' : '';
            tr.append(`<td class="${cphClass}">${formatNumber(record.target_cph)}</td>`);

            // Month columns
            months.forEach(month => {
                const monthData = record[month] || {};

                // Forecast
                const forecastModified = modifiedFields.includes(`${month}.forecast`);
                const forecastClass = forecastModified ? 'edit-view-modified-cell' : '';
                tr.append(`<td class="text-end ${forecastClass}">${formatNumber(monthData.forecast)}</td>`);

                // FTE Req
                const fteReqModified = modifiedFields.includes(`${month}.fte_req`);
                const fteReqClass = fteReqModified ? 'edit-view-modified-cell' : '';
                tr.append(`<td class="text-end ${fteReqClass}">${formatNumber(monthData.fte_req)}</td>`);

                // FTE Avail
                const fteAvailModified = modifiedFields.includes(`${month}.fte_avail`);
                const fteAvailClass = fteAvailModified ? 'edit-view-modified-cell' : '';
                tr.append(`<td class="text-end ${fteAvailClass}">${formatNumber(monthData.fte_avail)}</td>`);

                // Capacity
                const capacityModified = modifiedFields.includes(`${month}.capacity`);
                const capacityClass = capacityModified ? 'edit-view-modified-cell' : '';
                tr.append(`<td class="text-end ${capacityClass}">${formatNumber(monthData.capacity)}</td>`);
            });

            DOM.previewTableBody.append(tr);
        });
    }

    function renderPreviewPagination() {
        const paginationUl = DOM.previewPagination.find('ul.pagination');
        paginationUl.empty();

        if (STATE.previewTotalPages <= 1) {
            hideElement(DOM.previewPagination);
            return;
        }

        showElement(DOM.previewPagination);

        // Previous button
        const prevLi = $('<li>').addClass('page-item').addClass(STATE.previewCurrentPage === 1 ? 'disabled' : '');
        prevLi.append($('<a>').addClass('page-link').attr('href', '#').attr('data-page', STATE.previewCurrentPage - 1).text('Previous'));
        paginationUl.append(prevLi);

        // Page numbers
        for (let i = 1; i <= STATE.previewTotalPages; i++) {
            const pageLi = $('<li>').addClass('page-item').addClass(i === STATE.previewCurrentPage ? 'active' : '');
            pageLi.append($('<a>').addClass('page-link').attr('href', '#').attr('data-page', i).text(i));
            paginationUl.append(pageLi);
        }

        // Next button
        const nextLi = $('<li>').addClass('page-item').addClass(STATE.previewCurrentPage === STATE.previewTotalPages ? 'disabled' : '');
        nextLi.append($('<a>').addClass('page-link').attr('href', '#').attr('data-page', STATE.previewCurrentPage + 1).text('Next'));
        paginationUl.append(nextLi);
    }

    function handlePreviewPageClick(e) {
        e.preventDefault();

        const page = parseInt($(this).attr('data-page'));
        if (isNaN(page) || page < 1 || page > STATE.previewTotalPages || page === STATE.previewCurrentPage) {
            return;
        }

        STATE.previewCurrentPage = page;
        renderPreviewTable(STATE.currentPreviewData);

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
        DOM.acceptBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span>Updating...');

        try {
            const payload = {
                month: STATE.currentSelectedReport.month,
                year: STATE.currentSelectedReport.year,
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
                const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
                throw new Error(errorData.error || `HTTP ${response.status}`);
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
            await Swal.fire({
                icon: 'error',
                title: 'Update Failed',
                text: error.message || 'Failed to update allocation. Please try again.',
                confirmButtonColor: '#dc3545'
            });

        } finally {
            STATE.isSubmitting = false;
            DOM.acceptBtn.prop('disabled', false).html('<i class="fas fa-check me-1"></i>Accept & Update');
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

        await loadHistoryLog();
    }

    async function loadHistoryLog(page = 1) {
        console.log(`Edit View: Loading history log (page ${page})...`);

        STATE.isLoadingHistory = true;
        STATE.historyCurrentPage = page;

        showElement(DOM.historyLoading);
        hideElement(DOM.historyError);
        hideElement(DOM.historyNoResults);
        hideElement(DOM.historyCardsContainer);
        hideElement(DOM.historyPagination);

        try {
            const params = new URLSearchParams({
                page: page,
                limit: CONFIG.settings.historyPageSize
            });

            if (STATE.historyFilters.month) {
                params.append('month', STATE.historyFilters.month);
            }
            if (STATE.historyFilters.year) {
                params.append('year', STATE.historyFilters.year);
            }
            // Note: Change type filtering would need backend support - skipping for now

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
                const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error('Failed to fetch history log');
            }

            STATE.currentHistoryData = data;

            // Render history cards
            if (data.data && data.data.length > 0) {
                renderHistoryCards(data.data);
                showElement(DOM.historyCardsContainer);

                // Render pagination
                if (data.pagination && data.pagination.has_more) {
                    STATE.historyTotalPages = Math.ceil(data.pagination.total / CONFIG.settings.historyPageSize);
                    renderHistoryPagination(data.pagination);
                    showElement(DOM.historyPagination);
                }
            } else {
                showElement(DOM.historyNoResults);
            }

            console.log(`Edit View: History log loaded - ${data.data.length} entries`);

        } catch (error) {
            console.error('Edit View: Error loading history log', error);
            DOM.historyErrorMessage.text(error.message || 'Failed to load history log');
            showElement(DOM.historyError);

        } finally {
            STATE.isLoadingHistory = false;
            hideElement(DOM.historyLoading);
        }
    }

    function renderHistoryCards(entries) {
        DOM.historyCardsContainer.empty();

        entries.forEach(entry => {
            const card = createHistoryCard(entry);
            DOM.historyCardsContainer.append(card);
        });
    }

    function createHistoryCard(entry) {
        const card = $('<div>').addClass('card edit-view-history-card mb-3');

        // Determine border color based on change type
        if (entry.change_type === 'Bench Allocation') {
            card.addClass('edit-view-history-bench');
        } else if (entry.change_type === 'CPH Update') {
            card.addClass('edit-view-history-cph');
        } else if (entry.change_type === 'Manual Update') {
            card.addClass('edit-view-history-manual');
        }

        const cardBody = $('<div>').addClass('card-body');

        // Header
        const header = $('<div>').addClass('d-flex justify-content-between align-items-start mb-3');

        const headerLeft = $('<div>');
        headerLeft.append(`<h5 class="mb-1">${escapeHtml(entry.change_type || 'Update')}</h5>`);

        const badge = $('<span>').addClass('badge').text(entry.change_type || 'Update');
        if (entry.change_type === 'Bench Allocation') {
            badge.addClass('bg-primary');
        } else if (entry.change_type === 'CPH Update') {
            badge.addClass('bg-success');
        } else {
            badge.addClass('bg-warning text-dark');
        }
        headerLeft.append(badge);

        const headerRight = $('<div>').addClass('text-muted');
        headerRight.append(`<small>${escapeHtml(entry.timestamp_formatted || entry.timestamp || '-')}</small>`);

        header.append(headerLeft).append(headerRight);
        cardBody.append(header);

        // Details
        const details = $('<div>').addClass('mb-2');
        details.append(`<p class="mb-1"><strong>User:</strong> ${escapeHtml(entry.user || 'System')}</p>`);

        if (entry.user_notes) {
            details.append(`<p class="mb-1"><strong>Description:</strong> "${escapeHtml(entry.user_notes)}"</p>`);
        }

        details.append(`<p class="mb-1"><strong>Records Modified:</strong> ${entry.records_modified || 0}</p>`);

        cardBody.append(details);

        // Changes list
        if (entry.specific_changes && entry.specific_changes.changes && entry.specific_changes.changes.length > 0) {
            const changesList = $('<ul>').addClass('edit-view-history-changes-list mb-2');

            const threshold = CONFIG.settings.historyShowMoreThreshold;
            const changes = entry.specific_changes.changes;
            const showMore = changes.length > threshold;

            // Show first N changes
            changes.slice(0, threshold).forEach(change => {
                changesList.append(`<li>${escapeHtml(change)}</li>`);
            });

            cardBody.append(changesList);

            // Hidden changes (if more than threshold)
            if (showMore) {
                const remainingCount = changes.length - threshold;
                const moreContainer = $('<div>').addClass('edit-view-more-changes-container');
                const moreList = $('<ul>').addClass('edit-view-history-changes-list mt-0 mb-0');
                
                changes.slice(threshold).forEach(change => {
                    moreList.append(`<li>${escapeHtml(change)}</li>`);
                });

                moreContainer.append(moreList);
                cardBody.append(moreContainer);

                // Show More button
                const showMoreBtn = $('<button>')
                    .addClass('btn btn-sm btn-outline-secondary edit-view-show-more-btn')
                    .attr('data-entry-id', entry.id || Math.random())
                    .attr('data-count', remainingCount)
                    .html(`<i class="fas fa-chevron-down me-1"></i>Show More (${remainingCount} more changes)`);
                cardBody.append(showMoreBtn);
            }
        }

        // Download button
        if (entry.id) {
            const downloadBtn = $('<button>')
                .addClass('btn btn-sm btn-outline-primary edit-view-download-excel-btn mt-2')
                .attr('data-history-id', entry.id)
                .html('<i class="fas fa-download me-1"></i>Download Modified Records (Excel)');
            cardBody.append(downloadBtn);
        }

        card.append(cardBody);

        return card;
    }

    function handleShowMoreClick(e) {
        e.preventDefault();
        const btn = $(this);
        const card = btn.closest('.edit-view-history-card');
        const moreContainer = card.find('.edit-view-more-changes-container');
        const count = btn.attr('data-count') || '0';

        if (moreContainer.is(':visible')) {
            // Collapse
            moreContainer.slideUp();
            btn.html(`<i class="fas fa-chevron-down me-1"></i>Show More (${count} more changes)`);
        } else {
            // Expand
            moreContainer.slideDown();
            btn.html('<i class="fas fa-chevron-up me-1"></i>Show Less');
        }
    }

    function renderHistoryPagination(pagination) {
        const paginationUl = DOM.historyPagination.find('ul.pagination');
        paginationUl.empty();

        if (!pagination || !pagination.has_more) {
            hideElement(DOM.historyPagination);
            return;
        }

        const totalPages = Math.ceil(pagination.total / CONFIG.settings.historyPageSize);
        STATE.historyTotalPages = totalPages;

        // Previous button
        const prevLi = $('<li>').addClass('page-item').addClass(STATE.historyCurrentPage === 1 ? 'disabled' : '');
        prevLi.append($('<a>').addClass('page-link').attr('href', '#').attr('data-page', STATE.historyCurrentPage - 1).text('Previous'));
        paginationUl.append(prevLi);

        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            const pageLi = $('<li>').addClass('page-item').addClass(i === STATE.historyCurrentPage ? 'active' : '');
            pageLi.append($('<a>').addClass('page-link').attr('href', '#').attr('data-page', i).text(i));
            paginationUl.append(pageLi);
        }

        // Next button
        const nextLi = $('<li>').addClass('page-item').addClass(STATE.historyCurrentPage === totalPages ? 'disabled' : '');
        nextLi.append($('<a>').addClass('page-link').attr('href', '#').attr('data-page', STATE.historyCurrentPage + 1).text('Next'));
        paginationUl.append(nextLi);
    }

    function handleHistoryPageClick(e) {
        e.preventDefault();

        const page = parseInt($(this).attr('data-page'));
        if (isNaN(page) || page < 1 || page > STATE.historyTotalPages || page === STATE.historyCurrentPage) {
            return;
        }

        loadHistoryLog(page);

        // Scroll to top of history container
        DOM.historyCardsContainer[0].scrollIntoView({ behavior: 'smooth', block: 'start' });
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
        btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-1"></span>Downloading...');

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

    function showErrorAlert(message) {
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: message,
            confirmButtonColor: '#dc3545'
        });
    }

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
    // START APPLICATION
    // ============================================================================

    init();

})();