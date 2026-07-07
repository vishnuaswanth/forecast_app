/**
 * Ramp Campaign Manager – standalone page JS
 * No WebSocket. All server communication via fetch() POST / GET.
 */
(function () {
    "use strict";

    // ── State ────────────────────────────────────────────────────────────
    const State = {
        reportYear:       null,
        reportMonth:      null,   // full month name, e.g. "January"
        reportLabel:      "",
        lobs:             [],     // [{forecast_id, main_lob, state, case_type, target_cph}]
        months:           {},     // {"2025-04": "Apr-25"}
        monthWeeks:       {},     // {"2025-04": [{label, startDate, endDate, workingDays}]}
        workHours:        8.0,
        shrinkage:        0.15,
        stagingRows:      [],     // [{...ramp, action, target_cph, weeks[{capacity}]}]
        dbRamps:          [],
        dbActiveMonthKey: null,
        stagingLocked:    false,
        editIndex:        null,   // index into stagingRows when editing
    };

    // ── Helpers ──────────────────────────────────────────────────────────
    const URLS = window.RAMP_CAMPAIGN_URLS || {};

    function csrfToken() {
        return (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";
    }

    async function apiPost(url, body) {
        const resp = await fetch(url, {
            method:  "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
            body:    JSON.stringify(body),
        });
        return resp.json();
    }

    function fmtNum(n) {
        return n == null ? "–" : Number(n).toLocaleString();
    }

    function fmtDelta(n) {
        if (n == null) return "–";
        const cls = n >= 0 ? "rc-delta-pos" : "rc-delta-neg";
        const sign = n >= 0 ? "+" : "";
        return `<span class="${cls}">${sign}${fmtNum(n)}</span>`;
    }

    function actionBadge(action) {
        const map = { add: ["rc-badge-add", "add"], edit: ["rc-badge-edit", "edit"], delete: ["rc-badge-delete", "delete"] };
        const [cls, label] = map[action] || ["bg-secondary", action || "–"];
        return `<span class="badge ${cls}">${label}</span>`;
    }

    function lobLabel(lob) {
        return [lob.main_lob, lob.state, lob.case_type].filter(Boolean).join(" / ");
    }

    function showToast(msg, type = "info") {
        // Delegate to SweetAlert2 toast (globally available)
        Swal.fire({ toast: true, position: "top-end", icon: type, title: msg, showConfirmButton: false, timer: 3000, timerProgressBar: true });
    }

    // ── Bootstrap modal handles ──────────────────────────────────────────
    let rampModal = null, previewModal = null;

    function getRampModal() {
        if (!rampModal) rampModal = new bootstrap.Modal(document.getElementById("rc-ramp-modal"));
        return rampModal;
    }

    function getPreviewModal() {
        if (!previewModal) previewModal = new bootstrap.Modal(document.getElementById("rc-preview-modal"));
        return previewModal;
    }

    // ── Year / Month selectors ───────────────────────────────────────────
    async function loadYears() {
        try {
            const data = await fetch(URLS.filterYears).then(r => r.json());
            const years = data.years || data.data || [];
            const sel = document.getElementById("rc-year-select");
            sel.innerHTML = `<option value="">-- Select Year --</option>` +
                years.map(y => `<option value="${y.value || y}">${y.display || y}</option>`).join("");
        } catch (e) {
            console.error("[RC] loadYears error", e);
        }
    }

    async function onYearChange(year) {
        State.reportYear = year || null;
        const mSel = document.getElementById("rc-month-select");
        const loadBtn = document.getElementById("rc-load-btn");
        mSel.innerHTML = `<option value="">-- Select Month --</option>`;
        mSel.disabled = !year;
        loadBtn.disabled = true;
        if (!year) return;
        try {
            const data = await fetch(`${URLS.filterMonths}?year=${year}`).then(r => r.json());
            const months = data.options || data.months || [];
            mSel.innerHTML = `<option value="">-- Select Month --</option>` +
                months.map(m => `<option value="${m.display || m}">${m.display || m}</option>`).join("");
            mSel.disabled = false;
        } catch (e) {
            console.error("[RC] onYearChange months error", e);
        }
    }

    function onMonthChange(month) {
        State.reportMonth = month || null;
        document.getElementById("rc-load-btn").disabled = !month;
    }

    // ── Load report ──────────────────────────────────────────────────────
    async function loadReport() {
        const year  = State.reportYear;
        const month = State.reportMonth;
        if (!year || !month) return;

        const loadBtn = document.getElementById("rc-load-btn");
        loadBtn.disabled = true;
        loadBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>Loading…`;

        try {
            const [initData, rampsData] = await Promise.all([
                apiPost(URLS.campaignInit,  { year: parseInt(year), month_name: month }),
                apiPost(URLS.loadRamps,     { year: parseInt(year), month_name: month }),
            ]);

            if (!initData.success) {
                showToast(initData.message || "Failed to load report", "error");
                return;
            }

            State.lobs        = initData.lobs || [];
            State.months      = initData.months || {};
            State.monthWeeks  = initData.month_weeks || {};
            State.workHours   = initData.work_hours || 8.0;
            State.shrinkage   = initData.shrinkage || 0.15;
            State.reportLabel = initData.report_label || `${month} ${year}`;

            State.dbRamps = rampsData.ramps || [];
            State.stagingRows = [];
            State.stagingLocked = false;

            document.getElementById("rc-report-label").textContent = State.reportLabel;
            document.getElementById("rc-main").classList.remove("d-none");

            renderStagingTable();
            renderDbTab();
            updateBadges();

        } catch (e) {
            console.error("[RC] loadReport error", e);
            showToast("Error loading report", "error");
        } finally {
            loadBtn.disabled = false;
            loadBtn.innerHTML = `<i class="fas fa-sync-alt me-1"></i>Load`;
        }
    }

    // ── Tab switching ────────────────────────────────────────────────────
    function switchTab(name) {
        document.getElementById("rc-panel-staging").classList.toggle("d-none", name !== "staging");
        document.getElementById("rc-panel-db").classList.toggle("d-none",      name !== "db");
        document.getElementById("rc-tab-staging").classList.toggle("active",    name === "staging");
        document.getElementById("rc-tab-db").classList.toggle("active",         name === "db");
    }

    function updateBadges() {
        document.getElementById("rc-badge-staging").textContent = State.stagingRows.length;
        document.getElementById("rc-badge-db").textContent = State.dbRamps.length;
    }

    // ── Staging table ────────────────────────────────────────────────────
    function renderStagingTable() {
        const tbody  = document.getElementById("rc-staging-body");
        const emptyRow = document.getElementById("rc-staging-empty");
        const previewBtn = document.getElementById("rc-preview-btn");
        const exportBtn  = document.getElementById("rc-export-staging-btn");

        if (!State.stagingRows.length) {
            tbody.innerHTML = `<tr id="rc-staging-empty"><td colspan="10" class="text-center text-muted py-3">No staged ramps. Click "Add New Ramp" to begin.</td></tr>`;
            previewBtn.disabled = true;
            exportBtn.disabled = true;
            return;
        }

        previewBtn.disabled = State.stagingLocked;
        exportBtn.disabled  = false;

        tbody.innerHTML = State.stagingRows.map((row, idx) => {
            const peakEmp  = Math.max(...(row.weeks || []).map(w => w.rampEmployees || 0), 0);
            const totalCap = (row.weeks || []).reduce((s, w) => s + (w.capacity || 0), 0);
            const disabled = State.stagingLocked ? "disabled" : "";
            return `<tr>
                <td>${row.main_lob || ""}</td>
                <td>${row.state || ""}</td>
                <td>${row.case_type || ""}</td>
                <td>${row.month_label || row.month_key || ""}</td>
                <td>${row.ramp_name || ""}</td>
                <td class="text-end">${(row.target_cph || 0).toFixed(1)}</td>
                <td class="text-end">${fmtNum(peakEmp)}</td>
                <td class="text-end">${fmtNum(totalCap)}</td>
                <td>${actionBadge(row.action)}</td>
                <td class="text-nowrap">
                    <button class="btn btn-xs btn-outline-primary me-1" onclick="RampCampaign.editStaging(${idx})" ${disabled}>Edit</button>
                    <button class="btn btn-xs btn-outline-danger" onclick="RampCampaign.removeStaging(${idx})" ${disabled}>Remove</button>
                </td>
            </tr>`;
        }).join("");

        updateBadges();
    }

    // ── DB Ramps tab ─────────────────────────────────────────────────────
    function renderDbTab() {
        // Build month sub-tabs
        const monthKeys = [...new Set(State.dbRamps.map(r => r.month_key))].sort();
        const tabContainer = document.getElementById("rc-db-month-tabs");
        tabContainer.innerHTML = monthKeys.map(mk => {
            const label = State.months[mk] || mk;
            return `<button class="rc-month-tab" data-mk="${mk}">${label}</button>`;
        }).join("");

        tabContainer.querySelectorAll(".rc-month-tab").forEach(btn => {
            btn.addEventListener("click", () => activateDbMonthTab(btn.dataset.mk));
        });

        if (monthKeys.length) {
            activateDbMonthTab(monthKeys[0]);
        } else {
            renderDbRampsForMonth(null);
        }
        updateBadges();
    }

    function activateDbMonthTab(monthKey) {
        State.dbActiveMonthKey = monthKey;
        document.querySelectorAll(".rc-month-tab").forEach(b => b.classList.toggle("active", b.dataset.mk === monthKey));
        renderDbRampsForMonth(monthKey);
    }

    function renderDbRampsForMonth(monthKey) {
        const tbody = document.getElementById("rc-db-body");
        const ramps = monthKey ? State.dbRamps.filter(r => r.month_key === monthKey) : [];

        if (!ramps.length) {
            tbody.innerHTML = `<tr id="rc-db-empty"><td colspan="10" class="text-center text-muted py-3">No ramps found for this month.</td></tr>`;
            return;
        }

        tbody.innerHTML = ramps.map((r, idx) => {
            const totalCap = (r.weeks || []).reduce((s, w) => s + (w.capacity || 0), 0);
            const peakEmp  = Math.max(...(r.weeks || []).map(w => w.employee_count || 0), 0);
            return `<tr>
                <td>${r.forecast_id}</td>
                <td>${r.main_lob || ""}</td>
                <td>${r.state || ""}</td>
                <td>${r.case_type || ""}</td>
                <td>${r.ramp_name || ""}</td>
                <td class="text-end">${(r.target_cph || 0).toFixed(1)}</td>
                <td class="text-end">${(r.weeks || []).length}</td>
                <td class="text-end">${fmtNum(peakEmp)}</td>
                <td class="text-end">${fmtNum(totalCap)}</td>
                <td class="text-nowrap">
                    <button class="btn btn-xs btn-outline-primary me-1" onclick="RampCampaign.editDbRamp(${JSON.stringify(idx).replace(/"/g,"&quot;")}, '${monthKey}')">Edit</button>
                    <button class="btn btn-xs btn-outline-danger" onclick="RampCampaign.deleteDbRamp(${JSON.stringify(idx).replace(/"/g,"&quot;")}, '${monthKey}')">Delete</button>
                </td>
            </tr>`;
        }).join("");
    }

    // ── Add / Edit modal ─────────────────────────────────────────────────
    function openAddModal() {
        State.editIndex = null;

        // Destroy + reinit Select2 on LOB (pattern from configuration_view.js)
        const lobSel = $("#rc-modal-lob");
        if (lobSel.data("select2")) lobSel.select2("destroy");
        lobSel.empty().append(`<option value="">-- Select LOB --</option>`);
        State.lobs.forEach((lob, i) => {
            lobSel.append(new Option(lobLabel(lob), i));
        });
        lobSel.select2({ dropdownParent: $("#rc-ramp-modal"), theme: "bootstrap-5" });

        // Month select
        const mSel = document.getElementById("rc-modal-month");
        mSel.innerHTML = Object.entries(State.months)
            .map(([k, v]) => `<option value="${k}">${v}</option>`).join("");

        document.getElementById("rc-modal-ramp-name").value = "Default";
        document.getElementById("rc-ramp-modal-title").textContent = "Add Ramp";
        document.getElementById("rc-modal-save-btn").textContent = "Add to Staging";

        renderWeekInputs(mSel.value, null);
        getRampModal().show();
    }

    function renderWeekInputs(monthKey, existingWeeks) {
        const weeks = State.monthWeeks[monthKey] || [];
        const container = document.getElementById("rc-modal-weeks-container");
        container.innerHTML = `
            <table class="table table-sm table-bordered rc-week-table">
                <thead class="table-light">
                    <tr><th>Week</th><th>Dates</th><th>Working Days</th><th>Ramp %</th><th>Employees</th><th>Capacity</th></tr>
                </thead>
                <tbody id="rc-week-tbody">
                    ${weeks.map((wk, i) => {
                        const ew = existingWeeks && existingWeeks[i];
                        const rampPct = ew ? (ew.rampPercent || ew.ramp_percent || "") : "";
                        const emp     = ew ? (ew.rampEmployees || ew.employee_count || "") : "";
                        return `<tr data-wk-idx="${i}" data-wk-wd="${wk.workingDays}" data-wk-label="${wk.label}" data-wk-start="${wk.startDate}" data-wk-end="${wk.endDate}">
                            <td>${wk.label}</td>
                            <td>${wk.startDate} – ${wk.endDate}</td>
                            <td class="text-end">${wk.workingDays}</td>
                            <td><input type="number" class="form-control form-control-sm rc-ramp-pct" min="0" max="100" step="1" value="${rampPct}" placeholder="0"></td>
                            <td><input type="number" class="form-control form-control-sm rc-emp" min="0" step="1" value="${emp}" placeholder="0"></td>
                            <td class="text-end rc-cap-cell">0</td>
                        </tr>`;
                    }).join("")}
                </tbody>
            </table>`;

        // Recompute on input change
        container.querySelectorAll(".rc-emp, .rc-ramp-pct").forEach(inp => {
            inp.addEventListener("input", recomputeModalCapacity);
        });
        recomputeModalCapacity();
    }

    function recomputeModalCapacity() {
        const lobIdx = parseInt(document.getElementById("rc-modal-lob").value);
        const lob    = isNaN(lobIdx) ? null : State.lobs[lobIdx];
        const cph    = lob ? lob.target_cph : 0;
        let totalCap = 0, peakEmp = 0;

        document.querySelectorAll("#rc-week-tbody tr").forEach(row => {
            const emp = parseFloat(row.querySelector(".rc-emp")?.value) || 0;
            const wd  = parseFloat(row.dataset.wkWd) || 0;
            const cap = Math.round(emp * cph * State.workHours * (1 - State.shrinkage) * wd);
            row.querySelector(".rc-cap-cell").textContent = fmtNum(cap);
            totalCap += cap;
            if (emp > peakEmp) peakEmp = emp;
        });

        document.getElementById("rc-modal-total-cap").textContent = fmtNum(totalCap);
        document.getElementById("rc-modal-peak-emp").textContent  = fmtNum(peakEmp);
    }

    function collectModalWeeks(monthKey) {
        const lobIdx = parseInt(document.getElementById("rc-modal-lob").value);
        const lob    = isNaN(lobIdx) ? null : State.lobs[lobIdx];
        const cph    = lob ? lob.target_cph : 0;
        const weeks  = [];

        document.querySelectorAll("#rc-week-tbody tr").forEach(row => {
            const emp     = parseFloat(row.querySelector(".rc-emp")?.value) || 0;
            const rampPct = parseFloat(row.querySelector(".rc-ramp-pct")?.value) || 0;
            const wd      = parseFloat(row.dataset.wkWd) || 0;
            const cap     = Math.round(emp * cph * State.workHours * (1 - State.shrinkage) * wd);
            weeks.push({
                label:          row.dataset.wkLabel,
                week_label:     row.dataset.wkLabel,
                startDate:      row.dataset.wkStart,
                start_date:     row.dataset.wkStart,
                endDate:        row.dataset.wkEnd,
                end_date:       row.dataset.wkEnd,
                workingDays:    wd,
                working_days:   wd,
                rampPercent:    rampPct,
                ramp_percent:   rampPct,
                rampEmployees:  emp,
                employee_count: emp,
                capacity:       cap,
            });
        });
        return weeks;
    }

    function saveRampFromModal() {
        const lobIdx   = parseInt(document.getElementById("rc-modal-lob").value);
        const monthKey = document.getElementById("rc-modal-month").value;
        const rampName = document.getElementById("rc-modal-ramp-name").value.trim();

        if (isNaN(lobIdx) || !monthKey || !rampName) {
            showToast("Please fill in all required fields.", "warning");
            return;
        }

        const lob   = State.lobs[lobIdx];
        const weeks = collectModalWeeks(monthKey);

        if (!weeks.length) {
            showToast("No weeks data available for the selected month.", "warning");
            return;
        }

        const totalEmp = weeks.reduce((s, w) => s + (w.rampEmployees || 0), 0);
        const row = {
            forecast_id:         lob.forecast_id,
            main_lob:            lob.main_lob,
            state:               lob.state,
            case_type:           lob.case_type,
            target_cph:          lob.target_cph,
            month_key:           monthKey,
            month_label:         State.months[monthKey] || monthKey,
            ramp_name:           rampName,
            weeks:               weeks,
            totalRampEmployees:  totalEmp,
            action:              State.editIndex !== null ? "edit" : "add",
        };

        if (State.editIndex !== null) {
            State.stagingRows[State.editIndex] = row;
        } else {
            State.stagingRows.push(row);
        }

        getRampModal().hide();
        renderStagingTable();
        updateBadges();
        switchTab("staging");
    }

    // ── Edit staging row ─────────────────────────────────────────────────
    function editStaging(idx) {
        if (State.stagingLocked) return;
        State.editIndex = idx;
        const row = State.stagingRows[idx];

        const lobSel = $("#rc-modal-lob");
        if (lobSel.data("select2")) lobSel.select2("destroy");
        lobSel.empty().append(`<option value="">-- Select LOB --</option>`);
        let selectedLobIdx = "";
        State.lobs.forEach((lob, i) => {
            const opt = new Option(lobLabel(lob), i);
            if (lob.forecast_id == row.forecast_id && lob.main_lob === row.main_lob) {
                opt.selected = true;
                selectedLobIdx = i;
            }
            lobSel.append(opt);
        });
        lobSel.select2({ dropdownParent: $("#rc-ramp-modal"), theme: "bootstrap-5" });

        const mSel = document.getElementById("rc-modal-month");
        mSel.innerHTML = Object.entries(State.months)
            .map(([k, v]) => `<option value="${k}" ${k === row.month_key ? "selected" : ""}>${v}</option>`).join("");

        document.getElementById("rc-modal-ramp-name").value = row.ramp_name || "Default";
        document.getElementById("rc-ramp-modal-title").textContent = "Edit Ramp";
        document.getElementById("rc-modal-save-btn").textContent = "Update Staging";

        renderWeekInputs(row.month_key, row.weeks);
        getRampModal().show();
    }

    // ── Remove staging row ───────────────────────────────────────────────
    function removeStaging(idx) {
        if (State.stagingLocked) return;
        Swal.fire({
            title: "Remove staged ramp?",
            icon: "warning",
            showCancelButton: true,
            confirmButtonText: "Remove",
            confirmButtonColor: "#dc3545",
        }).then(result => {
            if (result.isConfirmed) {
                State.stagingRows.splice(idx, 1);
                renderStagingTable();
                updateBadges();
            }
        });
    }

    // ── Edit DB ramp → push to staging ──────────────────────────────────
    function editDbRamp(idx, monthKey) {
        const ramps = State.dbRamps.filter(r => r.month_key === monthKey);
        const ramp  = ramps[idx];
        if (!ramp) return;

        // Find matching LOB index
        const lobIdx = State.lobs.findIndex(
            l => l.forecast_id == ramp.forecast_id && l.main_lob === ramp.main_lob
        );

        const lobSel = $("#rc-modal-lob");
        if (lobSel.data("select2")) lobSel.select2("destroy");
        lobSel.empty().append(`<option value="">-- Select LOB --</option>`);
        State.lobs.forEach((lob, i) => {
            const opt = new Option(lobLabel(lob), i);
            if (i === lobIdx) opt.selected = true;
            lobSel.append(opt);
        });
        lobSel.select2({ dropdownParent: $("#rc-ramp-modal"), theme: "bootstrap-5" });

        const mSel = document.getElementById("rc-modal-month");
        mSel.innerHTML = Object.entries(State.months)
            .map(([k, v]) => `<option value="${k}" ${k === monthKey ? "selected" : ""}>${v}</option>`).join("");

        document.getElementById("rc-modal-ramp-name").value = ramp.ramp_name || "Default";
        document.getElementById("rc-ramp-modal-title").textContent = "Edit DB Ramp";
        document.getElementById("rc-modal-save-btn").textContent = "Add Edit to Staging";
        State.editIndex = null;

        // Override save: push with action='edit' (read month live from modal, not closure)
        document.getElementById("rc-modal-save-btn").onclick = () => {
            const selectedMonthKey = document.getElementById("rc-modal-month").value;
            const weeks    = collectModalWeeks(selectedMonthKey);
            const totalEmp = weeks.reduce((s, w) => s + (w.rampEmployees || 0), 0);
            const lob      = State.lobs[lobIdx] || {};
            State.stagingRows.push({
                forecast_id:        ramp.forecast_id,
                main_lob:           ramp.main_lob,
                state:              ramp.state,
                case_type:          ramp.case_type,
                target_cph:         ramp.target_cph || lob.target_cph || 0,
                month_key:          selectedMonthKey,
                month_label:        State.months[selectedMonthKey] || selectedMonthKey,
                ramp_name:          ramp.ramp_name,
                weeks:              weeks,
                totalRampEmployees: totalEmp,
                action:             "edit",
            });
            getRampModal().hide();
            renderStagingTable();
            updateBadges();
            switchTab("staging");
        };

        renderWeekInputs(monthKey, ramp.weeks);
        getRampModal().show();
    }

    // ── Delete DB ramp → push delete row to staging ──────────────────────
    function deleteDbRamp(idx, monthKey) {
        const ramps = State.dbRamps.filter(r => r.month_key === monthKey);
        const ramp  = ramps[idx];
        if (!ramp) return;

        Swal.fire({
            title: `Delete ramp "${ramp.ramp_name}"?`,
            text: "This will be staged for deletion. Click Preview & Submit to apply.",
            icon: "warning",
            showCancelButton: true,
            confirmButtonText: "Stage Delete",
            confirmButtonColor: "#dc3545",
        }).then(result => {
            if (result.isConfirmed) {
                State.stagingRows.push({
                    forecast_id:  ramp.forecast_id,
                    main_lob:     ramp.main_lob,
                    state:        ramp.state,
                    case_type:    ramp.case_type,
                    target_cph:   ramp.target_cph || 0,
                    month_key:    monthKey,
                    month_label:  State.months[monthKey] || monthKey,
                    ramp_name:    ramp.ramp_name,
                    weeks:        [],
                    action:       "delete",
                });
                renderStagingTable();
                updateBadges();
                switchTab("staging");
            }
        });
    }

    // ── Preview flow ──────────────────────────────────────────────────────
    async function triggerPreview() {
        if (!State.stagingRows.length) return;
        State.stagingLocked = true;
        document.getElementById("rc-add-btn").classList.add("rc-locked");
        document.getElementById("rc-preview-btn").disabled = true;

        try {
            const result = await apiPost(URLS.preview, { campaign_rows: State.stagingRows });
            if (!result.success) {
                showToast(result.message || "Preview failed", "error");
                unlockStaging();
                return;
            }
            showPreviewModal(result);
        } catch (e) {
            console.error("[RC] preview error", e);
            showToast("Preview request failed", "error");
            unlockStaging();
        }
    }

    function unlockStaging() {
        State.stagingLocked = false;
        document.getElementById("rc-add-btn").classList.remove("rc-locked");
        document.getElementById("rc-preview-btn").disabled = !State.stagingRows.length;
    }

    function showPreviewModal(result) {
        const rows = result.preview_rows || [];
        document.getElementById("rc-preview-summary").innerHTML =
            `<strong>FTE Δ:</strong> ${fmtNum(result.total_fte_delta)} &nbsp;&nbsp; ` +
            `<strong>Capacity Δ:</strong> ${fmtNum(result.total_cap_delta)} &nbsp;&nbsp; ` +
            `<em>${rows.length} entries</em>`;

        document.getElementById("rc-preview-body").innerHTML = rows.map(r => `
            <tr>
                <td>${r.main_lob || ""}</td>
                <td>${r.state || ""}</td>
                <td>${r.case_type || ""}</td>
                <td>${r.month_label || r.month_key || ""}</td>
                <td>${r.ramp_name || ""}</td>
                <td class="text-end">${fmtDelta(r.fte_delta)}</td>
                <td class="text-end">${fmtDelta(r.cap_delta)}</td>
                <td>${actionBadge(r.action)}</td>
                <td>${r.error ? `<span class="text-danger small">${r.error}</span>` : '<span class="text-success small">OK</span>'}</td>
            </tr>`).join("");

        getPreviewModal().show();
    }

    async function confirmApply() {
        getPreviewModal().hide();
        try {
            const result = await apiPost(URLS.apply, { campaign_rows: State.stagingRows });
            if (result.success) {
                await Swal.fire({
                    icon: "success",
                    title: "Applied!",
                    text: result.message || `${result.applied?.length || 0} ramps applied.`,
                    timer: 3000,
                    showConfirmButton: false,
                });
            } else {
                Swal.fire({
                    icon: "warning",
                    title: "Partially applied",
                    text: result.message || "Some ramps failed.",
                });
            }

            // Reload DB ramps
            const rampsData = await apiPost(URLS.loadRamps, {
                year: parseInt(State.reportYear), month_name: State.reportMonth,
            });
            State.dbRamps = rampsData.ramps || [];

            // Clear staging
            State.stagingRows = [];
            unlockStaging();
            renderStagingTable();
            renderDbTab();
            updateBadges();

        } catch (e) {
            console.error("[RC] apply error", e);
            showToast("Apply request failed", "error");
            unlockStaging();
        }
    }

    // ── Excel export ──────────────────────────────────────────────────────
    function exportStaging() {
        downloadExcel("ui", State.stagingRows);
    }

    function exportDb() {
        // Collect visible month's ramps (or all)
        const ramps = State.dbActiveMonthKey
            ? State.dbRamps.filter(r => r.month_key === State.dbActiveMonthKey)
            : State.dbRamps;
        downloadExcel("db", ramps);
    }

    function downloadExcel(mode, ramps) {
        const form = document.createElement("form");
        form.method = "POST";
        form.action = URLS.downloadExcel;

        const data = {
            mode,
            ramps,
            report_month: State.reportMonth,
            report_year:  State.reportYear,
        };

        const inp = document.createElement("input");
        inp.type  = "hidden";
        inp.name  = "csrfmiddlewaretoken";
        inp.value = csrfToken();
        form.appendChild(inp);

        // Use fetch with blob for binary response
        fetch(URLS.downloadExcel, {
            method:  "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
            body:    JSON.stringify(data),
        }).then(resp => resp.blob()).then(blob => {
            const url  = URL.createObjectURL(blob);
            const a    = document.createElement("a");
            a.href     = url;
            a.download = `ramp_data_${mode}_${State.reportMonth}_${State.reportYear}.xlsx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        }).catch(e => {
            console.error("[RC] Excel export error", e);
            showToast("Excel export failed", "error");
        });
    }

    // ── Public API (called from inline onclick handlers) ─────────────────
    window.RampCampaign = {
        editStaging,
        removeStaging,
        editDbRamp,
        deleteDbRamp,
    };

    // ── Wire up events ────────────────────────────────────────────────────
    document.addEventListener("DOMContentLoaded", () => {
        loadYears();

        document.getElementById("rc-year-select").addEventListener("change", e => onYearChange(e.target.value));
        document.getElementById("rc-month-select").addEventListener("change", e => onMonthChange(e.target.value));
        document.getElementById("rc-load-btn").addEventListener("click", loadReport);

        document.querySelectorAll("#rc-tabs .nav-link").forEach(tab => {
            tab.addEventListener("click", e => {
                e.preventDefault();
                switchTab(tab.dataset.tab);
            });
        });

        // Select2 init for year/month on the main page
        $("#rc-year-select").select2({ theme: "bootstrap-5", placeholder: "-- Select Year --", width: "auto" });
        $("#rc-month-select").select2({ theme: "bootstrap-5", placeholder: "-- Select Month --", width: "auto" });

        $("#rc-year-select").on("change", e => onYearChange(e.target.value));
        $("#rc-month-select").on("change", e => onMonthChange(e.target.value));

        document.getElementById("rc-add-btn").addEventListener("click", openAddModal);
        document.getElementById("rc-preview-btn").addEventListener("click", triggerPreview);
        document.getElementById("rc-export-staging-btn").addEventListener("click", exportStaging);
        document.getElementById("rc-export-db-btn").addEventListener("click", exportDb);

        // Modal month change → re-render week inputs
        document.getElementById("rc-modal-month").addEventListener("change", e => {
            renderWeekInputs(e.target.value, null);
        });

        // LOB change → recompute capacity
        document.getElementById("rc-modal-lob").addEventListener("change", recomputeModalCapacity);

        // Modal save (default — DB-edit flow overrides .onclick; reset on modal close)
        document.getElementById("rc-modal-save-btn").onclick = saveRampFromModal;

        // Preview modal buttons
        document.getElementById("rc-confirm-apply-btn").addEventListener("click", confirmApply);
        document.getElementById("rc-preview-cancel-btn").addEventListener("click", unlockStaging);

        // Restore default save handler whenever ramp modal hides (clears DB-edit override)
        document.getElementById("rc-ramp-modal").addEventListener("hidden.bs.modal", () => {
            document.getElementById("rc-modal-save-btn").onclick = saveRampFromModal;
        });
    });

})();
