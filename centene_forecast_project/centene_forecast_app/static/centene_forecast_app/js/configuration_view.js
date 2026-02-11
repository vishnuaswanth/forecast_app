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
            filters: { year: '', month: '', workType: '' },
            currentPage: 1,
            totalPages: 1,
            isLoading: false
        },
        // Target CPH state
        targetCph: {
            data: [],
            filters: { mainLob: '', caseType: '' },
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

        // Load initial data for Month Config tab
        loadMonthConfigurations();
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
        // Populate year filter (current year +/- 5 years)
        const currentYear = new Date().getFullYear();
        const yearOptions = [];
        for (let y = currentYear - 5; y <= currentYear + 5; y++) {
            yearOptions.push(`<option value="${y}">${y}</option>`);
        }
        if (DOM.monthConfig.yearFilter) {
            DOM.monthConfig.yearFilter.innerHTML = '<option value="">All Years</option>' + yearOptions.join('');
        }

        // Populate month filter
        const monthNames = SETTINGS.monthNames || [];
        const monthOptions = monthNames.map(m => `<option value="${m}">${m}</option>`).join('');
        if (DOM.monthConfig.monthFilter) {
            DOM.monthConfig.monthFilter.innerHTML = '<option value="">All Months</option>' + monthOptions;
        }
        if (DOM.monthConfigModal.monthField) {
            DOM.monthConfigModal.monthField.innerHTML = '<option value="">Select Month</option>' + monthOptions;
        }

        // Populate work type filter
        const workTypes = SETTINGS.workTypes || [];
        const workTypeOptions = workTypes.map(t => `<option value="${t}">${t}</option>`).join('');
        if (DOM.monthConfig.workTypeFilter) {
            DOM.monthConfig.workTypeFilter.innerHTML = '<option value="">All Types</option>' + workTypeOptions;
        }
        if (DOM.monthConfigModal.workTypeField) {
            DOM.monthConfigModal.workTypeField.innerHTML = '<option value="">Select Type</option>' + workTypeOptions;
        }

        // Set year field limits
        if (DOM.monthConfigModal.yearField) {
            DOM.monthConfigModal.yearField.min = SETTINGS.minYear || 2020;
            DOM.monthConfigModal.yearField.max = SETTINGS.maxYear || 2100;
            DOM.monthConfigModal.yearField.value = currentYear;
        }
    }

    function initSelect2() {
        // Initialize Select2 for filter dropdowns
        if (jQuery && jQuery.fn.select2) {
            jQuery('.config-view-select2').select2({
                theme: 'bootstrap-5',
                width: '100%',
                allowClear: true
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
    // TAB HANDLING
    // ============================================================
    function handleTabSwitch(e) {
        const targetId = e.target.getAttribute('data-bs-target');

        if (targetId === '#target-cph-config-tab') {
            // Load Target CPH data when tab is activated
            if (STATE.targetCph.data.length === 0) {
                loadDistinctLobs();
                loadTargetCphConfigurations();
            }
        }
    }

    // ============================================================
    // MONTH CONFIGURATION FUNCTIONS
    // ============================================================
    async function loadMonthConfigurations() {
        if (STATE.monthConfig.isLoading) return;

        STATE.monthConfig.isLoading = true;
        showLoading(DOM.monthConfig);
        hideError(DOM.monthConfig);

        try {
            const params = new URLSearchParams();
            if (STATE.monthConfig.filters.year) params.append('year', STATE.monthConfig.filters.year);
            if (STATE.monthConfig.filters.month) params.append('month', STATE.monthConfig.filters.month);
            if (STATE.monthConfig.filters.workType) params.append('work_type', STATE.monthConfig.filters.workType);

            const url = URLS.monthConfigList + (params.toString() ? '?' + params.toString() : '');
            const response = await fetch(url);
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Failed to load configurations');
            }

            STATE.monthConfig.data = data.data || [];
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

        const rows = STATE.monthConfig.data.map(config => {
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
    }

    function updateMonthConfigCount() {
        if (DOM.monthConfig.countBadge) {
            const count = STATE.monthConfig.data.length;
            DOM.monthConfig.countBadge.textContent = `${count} configuration${count !== 1 ? 's' : ''}`;
        }
    }

    function handleMonthConfigApplyFilters() {
        STATE.monthConfig.filters.year = DOM.monthConfig.yearFilter?.value || '';
        STATE.monthConfig.filters.month = DOM.monthConfig.monthFilter?.value || '';
        STATE.monthConfig.filters.workType = DOM.monthConfig.workTypeFilter?.value || '';
        STATE.monthConfig.currentPage = 1;
        loadMonthConfigurations();
    }

    function handleMonthConfigClearFilters() {
        STATE.monthConfig.filters = { year: '', month: '', workType: '' };

        if (jQuery && jQuery.fn.select2) {
            jQuery(DOM.monthConfig.yearFilter).val('').trigger('change');
            jQuery(DOM.monthConfig.monthFilter).val('').trigger('change');
            jQuery(DOM.monthConfig.workTypeFilter).val('').trigger('change');
        } else {
            if (DOM.monthConfig.yearFilter) DOM.monthConfig.yearFilter.value = '';
            if (DOM.monthConfig.monthFilter) DOM.monthConfig.monthFilter.value = '';
            if (DOM.monthConfig.workTypeFilter) DOM.monthConfig.workTypeFilter.value = '';
        }

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
                populateLobFilter();
            }
        } catch (error) {
            console.error('Failed to load distinct LOBs:', error);
        }
    }

    function populateLobFilter() {
        if (!DOM.targetCph.lobFilter) return;

        const options = STATE.targetCph.distinctLobs.map(lob =>
            `<option value="${escapeHtml(lob.value)}">${escapeHtml(lob.display)}</option>`
        ).join('');

        DOM.targetCph.lobFilter.innerHTML = '<option value="">All LOBs</option>' + options;

        if (jQuery && jQuery.fn.select2) {
            jQuery(DOM.targetCph.lobFilter).trigger('change');
        }
    }

    async function loadTargetCphConfigurations() {
        if (STATE.targetCph.isLoading) return;

        STATE.targetCph.isLoading = true;
        showLoading(DOM.targetCph);
        hideError(DOM.targetCph);

        try {
            const params = new URLSearchParams();
            if (STATE.targetCph.filters.mainLob) params.append('main_lob', STATE.targetCph.filters.mainLob);
            if (STATE.targetCph.filters.caseType) params.append('case_type', STATE.targetCph.filters.caseType);

            const url = URLS.targetCphList + (params.toString() ? '?' + params.toString() : '');
            const response = await fetch(url);
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Failed to load configurations');
            }

            STATE.targetCph.data = data.data || [];
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

        const rows = STATE.targetCph.data.map(config => `
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
    }

    function updateTargetCphCount() {
        if (DOM.targetCph.countBadge) {
            const count = STATE.targetCph.data.length;
            DOM.targetCph.countBadge.textContent = `${count} configuration${count !== 1 ? 's' : ''}`;
        }
    }

    function handleTargetCphApplyFilters() {
        STATE.targetCph.filters.mainLob = DOM.targetCph.lobFilter?.value || '';
        STATE.targetCph.filters.caseType = DOM.targetCph.caseTypeFilter?.value || '';
        STATE.targetCph.currentPage = 1;
        loadTargetCphConfigurations();
    }

    function handleTargetCphClearFilters() {
        STATE.targetCph.filters = { mainLob: '', caseType: '' };

        if (jQuery && jQuery.fn.select2) {
            jQuery(DOM.targetCph.lobFilter).val('').trigger('change');
            jQuery(DOM.targetCph.caseTypeFilter).val('').trigger('change');
        } else {
            if (DOM.targetCph.lobFilter) DOM.targetCph.lobFilter.value = '';
            if (DOM.targetCph.caseTypeFilter) DOM.targetCph.caseTypeFilter.value = '';
        }

        STATE.targetCph.currentPage = 1;
        loadTargetCphConfigurations();
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
            loadTargetCphConfigurations();

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
            loadTargetCphConfigurations();

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
            loadTargetCphConfigurations();

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
    // INITIALIZE
    // ============================================================
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
