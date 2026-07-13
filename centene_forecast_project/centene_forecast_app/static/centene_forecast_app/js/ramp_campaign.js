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
        lobs:             [],     // [{forecast_id, main_lob, state, case_type, target_cph, locality}]
        months:           {},     // {"2025-04": "Apr-25"}
        monthWeeks:       {},     // {"2025-04": [{label, startDate, endDate, workingDays}]}
        shrinkageConfig:  { Domestic: 0.10, Global: 0.15 },
        workHoursConfig:  { Domestic: 9.0,  Global: 9.0  },
        stagingRows:      [],     // [{...ramp, action, target_cph, weeks[{capacity}]}]
        dbRamps:          [],
        dbActiveMonthKey: null,
        stagingLocked:    false,
        editIndex:        null,   // index into stagingRows when editing (staging mode)
        modalMode:        'add',  // 'add' | 'edit-staging' | 'edit-db'
        editDbRampData:   null,   // full ramp object in DB-edit mode
        editDbLobIdx:     null,   // State.lobs index in DB-edit (-1 = not found in current lobs)
        // Multi-month cache (add mode)
        monthWeekCache:      {},   // { "2025-04": [{rampPct, rampEmployees, workingDays}, ...] }
        monthIsFte:          {},   // { "2025-04": true|false } — per-month "Is FTE" toggle
        modalActiveMonthKey: null, // month key currently rendered in the week table
        // Table filters
        filters: { staging: "", db: "" },
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

    // Returns the staged action ("edit" | "delete") for a real DB ramp, or null.
    // "add" rows are excluded — they always carry a freshly-generated unique
    // ramp_name (via buildUniqueRampName) that can never collide with a DB row.
    function findStagedAction(forecastId, monthKey, rampName) {
        const match = State.stagingRows.find(row =>
            row.action !== "add" &&
            row.forecast_id == forecastId &&   // loose equality: matches editStaging/editDbRamp convention
            row.month_key === monthKey &&
            row.ramp_name === rampName
        );
        return match ? match.action : null;
    }

    // Sums the net capacity delta all OTHER staged rows contribute to a given
    // (forecast_id, month_key), mirroring bulk_apply_ramp/bulk_preview_ramp:
    //   add    -> +sum(weeks.capacity)                (nothing to net out yet)
    //   delete -> -total_capacity                      (old capacity being removed)
    //   edit   -> +sum(weeks.capacity) - old_capacity   (base already counts old_capacity)
    // excludeIdx: staging row index to skip (the row currently open live in the
    // modal, so it isn't double-counted once it's actually pushed on save).
    function computeStagedDelta(forecastId, monthKey, excludeIdx) {
        let delta = 0;
        State.stagingRows.forEach((row, idx) => {
            if (idx === excludeIdx) return;
            if (row.forecast_id != forecastId || row.month_key !== monthKey) return;
            if (row.action === "add") {
                delta += (row.weeks || []).reduce((s, w) => s + (w.capacity || 0), 0);
            } else if (row.action === "delete") {
                delta -= (row.total_capacity || 0);
            } else if (row.action === "edit") {
                const newCap = (row.weeks || []).reduce((s, w) => s + (w.capacity || 0), 0);
                delta += newCap - (row.old_capacity || 0);
            }
        });
        return delta;
    }

    function lobLabel(lob) {
        return [lob.main_lob, lob.state, lob.case_type].filter(Boolean).join(" / ");
    }

    function showToast(msg, type = "info") {
        Swal.fire({ toast: true, position: "top-end", icon: type, title: msg, showConfirmButton: false, timer: 3000, timerProgressBar: true });
    }

    function getEffectiveShrinkage(lobOrRamp) {
        const key = (lobOrRamp && lobOrRamp.locality === "Global") ? "Global" : "Domestic";
        return State.shrinkageConfig[key] ?? 0.10;
    }

    function getEffectiveWorkHours(lobOrRamp) {
        const key = (lobOrRamp && lobOrRamp.locality === "Global") ? "Global" : "Domestic";
        return State.workHoursConfig[key] ?? 9.0;
    }

    // ── Filter helpers ───────────────────────────────────────────────────
    function matchesFilter(row, text) {
        if (!text) return true;
        const t = text.toLowerCase();
        return [row.main_lob, row.state, row.case_type, row.ramp_name]
            .some(f => (f || "").toLowerCase().includes(t));
    }

    // ── Unique ramp name generation ─────────────────────────────────────
    // Format: userText_formattedMonth_uuidFragment. Guarantees every newly
    // created ramp gets a globally-unique name that can never collide with
    // an existing DB ramp — FastAPI upserts/deletes by exact ramp_name match,
    // so a collision would silently double-count capacity (see saveStagingRamp).
    function _shortUid() {
        return Math.random().toString(16).slice(2, 10);
    }

    function buildUniqueRampName(rampName, monthKey) {
        const monthLabel = (State.months[monthKey] || monthKey).replace(/[^A-Za-z0-9]+/g, "");
        return `${rampName}_${monthLabel}_${_shortUid()}`;
    }

    // ── Bootstrap modal handles ──────────────────────────────────────────
    let rampModal = null, previewModal = null;
    // Raw (unformatted) live modal capacity total — refreshCapacityBreakdown()
    // reads this directly instead of re-parsing fmtNum()'s locale-formatted
    // DOM text, which silently mis-parses on locales using "." as a thousands
    // separator (e.g. "1.234" would otherwise be read back as 1.234, not 1234).
    let modalLiveTotalCap = 0;

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

            State.lobs             = initData.lobs || [];
            State.months           = initData.months || {};
            State.monthWeeks       = initData.month_weeks || {};
            State.shrinkageConfig  = initData.shrinkage_config  || { Domestic: 0.10, Global: 0.15 };
            State.workHoursConfig  = initData.work_hours_config || { Domestic: 9.0,  Global: 9.0  };
            State.reportLabel      = initData.report_label || `${month} ${year}`;

            State.dbRamps      = rampsData.ramps || [];
            State.stagingRows  = [];
            State.stagingLocked = false;
            State.filters      = { staging: "", db: "" };

            document.getElementById("rc-report-label").textContent = State.reportLabel;
            document.getElementById("rc-main").classList.remove("d-none");

            // Clear any existing filter input values
            const sf = document.getElementById("rc-staging-filter");
            const df = document.getElementById("rc-db-filter");
            if (sf) sf.value = "";
            if (df) df.value = "";

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
        const tbody    = document.getElementById("rc-staging-body");
        const previewBtn = document.getElementById("rc-preview-btn");
        const exportBtn  = document.getElementById("rc-export-staging-btn");

        if (!State.stagingRows.length) {
            tbody.innerHTML = `<tr id="rc-staging-empty"><td colspan="8" class="text-center text-muted py-3">No staged ramps. Click "Add New Ramp" to begin.</td></tr>`;
            previewBtn.disabled = true;
            exportBtn.disabled = true;
            return;
        }

        previewBtn.disabled = State.stagingLocked;
        exportBtn.disabled  = false;

        // Apply filter, preserving real indices for edit/remove
        const indexed = State.stagingRows
            .map((row, idx) => ({ row, idx }))
            .filter(({ row }) => matchesFilter(row, State.filters.staging));

        if (!indexed.length) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted py-3">No rows match the current filter.</td></tr>`;
            return;
        }

        tbody.innerHTML = indexed.map(({ row, idx }) => {
            const peakEmp  = row.action === "delete"
                ? (row.peak_employees || 0)
                : Math.max(...(row.weeks || []).map(w => w.rampEmployees || 0), 0);
            const totalCap = row.action === "delete"
                ? (row.total_capacity || 0)
                : (row.weeks || []).reduce((s, w) => s + (w.capacity || 0), 0);
            const disabled = State.stagingLocked ? "disabled" : "";
            // Delete-staged rows carry no editable week data (weeks: []) — editing
            // one would silently convert the deletion into a zero-value edit
            // instead of actually removing the ramp. Remove-and-re-add instead.
            const editBtn = row.action === "delete" ? "" :
                `<button class="btn btn-xs btn-outline-primary me-1" onclick="RampCampaign.editStaging(${idx})" ${disabled}>Edit</button>`;
            return `<tr>
                <td class="rc-lob-cell">
                    <div class="rc-lob-main">${row.main_lob || "–"}</div>
                    <div class="rc-lob-sub">${[row.state, row.case_type].filter(Boolean).join(" / ")}</div>
                </td>
                <td>${row.month_label || row.month_key || ""}</td>
                <td>${row.ramp_name || ""}</td>
                <td class="text-end">${(row.target_cph || 0).toFixed(1)}</td>
                <td class="text-end">${fmtNum(peakEmp)}</td>
                <td class="text-end">${fmtNum(Math.round(totalCap))}</td>
                <td>${actionBadge(row.action)}</td>
                <td class="text-nowrap">
                    ${editBtn}
                    <button class="btn btn-xs btn-outline-danger" onclick="RampCampaign.removeStaging(${idx})" ${disabled}>Remove</button>
                </td>
            </tr>`;
        }).join("");

        updateBadges();
    }

    // ── DB Ramps tab ─────────────────────────────────────────────────────
    function renderDbTab() {
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
        const allRamps = monthKey ? State.dbRamps.filter(r => r.month_key === monthKey) : [];

        if (!allRamps.length) {
            tbody.innerHTML = `<tr id="rc-db-empty"><td colspan="7" class="text-center text-muted py-3">No ramps found for this month.</td></tr>`;
            return;
        }

        // Apply filter; use real index into allRamps for onclick handlers
        const filtered = allRamps
            .map((r, realIdx) => ({ r, realIdx }))
            .filter(({ r }) => matchesFilter(r, State.filters.db));

        if (!filtered.length) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-3">No rows match the current filter.</td></tr>`;
            return;
        }

        tbody.innerHTML = filtered.map(({ r, realIdx }) => {
            const totalCap = (r.weeks || []).reduce((s, w) => s + (w.capacity || 0), 0);
            const peakEmp  = Math.max(...(r.weeks || []).map(w => w.employee_count || 0), 0);

            const stagedAction = findStagedAction(r.forecast_id, r.month_key, r.ramp_name);
            const rowClass     = stagedAction ? ' class="rc-staged-row"' : '';
            const actionsCell  = stagedAction
                ? `<span class="badge rc-badge-${stagedAction}">Staged for ${stagedAction === "edit" ? "Edit" : "Delete"}</span>`
                : `<button class="btn btn-xs btn-outline-primary me-1" onclick="RampCampaign.editDbRamp(${realIdx}, '${monthKey}')">Edit</button>
                   <button class="btn btn-xs btn-outline-danger" onclick="RampCampaign.deleteDbRamp(${realIdx}, '${monthKey}')">Delete</button>`;

            return `<tr${rowClass}>
                <td class="rc-lob-cell">
                    <div class="rc-lob-main">${r.main_lob || "–"}</div>
                    <div class="rc-lob-sub">${[r.state, r.case_type].filter(Boolean).join(" / ") || "–"}</div>
                </td>
                <td>${r.ramp_name || ""}</td>
                <td class="text-end">${(r.target_cph || 0).toFixed(1)}</td>
                <td class="text-end">${(r.weeks || []).length}</td>
                <td class="text-end">${fmtNum(peakEmp)}</td>
                <td class="text-end">${fmtNum(Math.round(totalCap))}</td>
                <td class="text-nowrap">${actionsCell}</td>
            </tr>`;
        }).join("");
    }

    // ── Modal mode management ────────────────────────────────────────────
    function setModalMode(mode) {
        State.modalMode = mode;
        const isDbEdit = mode === 'edit-db';

        document.getElementById("rc-modal-lob").classList.toggle("d-none", isDbEdit);
        document.getElementById("rc-modal-lob-display").classList.toggle("d-none", !isDbEdit);
        document.getElementById("rc-modal-month").classList.toggle("d-none", isDbEdit);
        document.getElementById("rc-modal-month-display").classList.toggle("d-none", !isDbEdit);

        const rn = document.getElementById("rc-modal-ramp-name");
        rn.toggleAttribute("readonly", isDbEdit);
        rn.classList.toggle("rc-readonly-field", isDbEdit);

        const title   = document.getElementById("rc-ramp-modal-title");
        const saveBtn = document.getElementById("rc-modal-save-btn");
        if (mode === 'add') {
            title.textContent   = "Add Ramp";
            saveBtn.textContent = "Add to Staging";
        } else if (mode === 'edit-staging') {
            title.textContent   = "Edit Ramp";
            saveBtn.textContent = "Update Staging";
        } else {
            title.textContent   = "Edit Ramp";
            saveBtn.textContent = "Save Changes";
        }
    }

    function populateLobDisplay(ramp) {
        const sub = [ramp.state, ramp.case_type].filter(Boolean).join(" / ");
        document.getElementById("rc-modal-lob-display").textContent =
            ramp.main_lob + (sub ? ` — ${sub}` : "");
    }

    function populateMonthDisplay(monthKey) {
        document.getElementById("rc-modal-month-display").textContent =
            State.months[monthKey] || monthKey;
    }

    function updateLobInfoCard(lobOrRamp) {
        const card = document.getElementById("rc-lob-info-card");
        if (!lobOrRamp) {
            card.classList.add("d-none");
            refreshCapacityBreakdown();
            return;
        }
        const locality  = lobOrRamp.locality || "Domestic";
        const shrinkage = getEffectiveShrinkage(lobOrRamp);
        const wh        = getEffectiveWorkHours(lobOrRamp);
        document.getElementById("rc-info-locality").textContent  = locality;
        document.getElementById("rc-info-locality").className    = `rc-locality-badge ${locality.toLowerCase()}`;
        document.getElementById("rc-info-shrinkage").textContent = `${(shrinkage * 100).toFixed(0)}%`;
        document.getElementById("rc-info-cph").textContent       = (lobOrRamp.target_cph || 0).toFixed(1);
        document.getElementById("rc-info-workhours").textContent = `${wh}h`;

        // Forecast / Current Capacity — sourced from month_values (present directly
        // on State.lobs[] entries; DB-ramp objects don't carry it, so in edit-db
        // mode resolve via State.editDbLobIdx instead).
        const mvSource = lobOrRamp.month_values ? lobOrRamp
            : (State.editDbLobIdx >= 0 ? State.lobs[State.editDbLobIdx] : null);
        const monthKey = State.modalActiveMonthKey;
        const mv = (mvSource && monthKey && mvSource.month_values && mvSource.month_values[monthKey]) || {};
        document.getElementById("rc-info-forecast").textContent    = fmtNum(Math.round(mv.forecast || 0));
        document.getElementById("rc-info-current-cap").textContent = fmtNum(Math.round(mv.capacity || 0));

        card.classList.remove("d-none");
        refreshCapacityBreakdown();
    }

    // Live "projected capacity" breakdown for the modal: base DB capacity plus
    // the net capacity delta from every staged row for this (forecast_id,
    // month_key), plus the live in-progress modal row itself. Mirrors
    // bulk_apply_ramp/bulk_preview_ramp's new-minus-old delta math exactly so
    // this can't misrepresent what applying the campaign will actually do.
    function refreshCapacityBreakdown() {
        const el = document.getElementById("rc-cap-breakdown");
        if (!el) return;
        let forecastId, monthKey, mvSource, excludeIdx = null, ownOldCapacity = 0;

        if (State.modalMode === 'edit-db') {
            const ramp = State.editDbRampData;
            if (!ramp) { el.classList.add("d-none"); return; }
            forecastId = ramp.forecast_id;
            monthKey   = State.modalActiveMonthKey;
            mvSource   = (State.editDbLobIdx >= 0) ? State.lobs[State.editDbLobIdx] : null;
            ownOldCapacity = (ramp.weeks || []).reduce((s, w) => s + (w.capacity || 0), 0);
        } else {
            const lobIdx = parseInt(document.getElementById("rc-modal-lob").value);
            if (isNaN(lobIdx)) { el.classList.add("d-none"); return; }
            mvSource   = State.lobs[lobIdx];
            forecastId = mvSource.forecast_id;
            monthKey   = State.modalActiveMonthKey;
            if (State.modalMode === 'edit-staging' && State.editIndex !== null) {
                excludeIdx = State.editIndex;
                const editingRow = State.stagingRows[State.editIndex];
                // Only net out the old DB baseline if the row being replaced IS the
                // active month AND was itself a real edit — otherwise (a different,
                // freshly-added month in a multi-month session) there's no baseline.
                if (editingRow && editingRow.action === 'edit' && editingRow.month_key === monthKey) {
                    ownOldCapacity = editingRow.old_capacity || 0;
                }
            }
        }

        if (!monthKey || !mvSource) { el.classList.add("d-none"); return; }

        const mv      = (mvSource.month_values && mvSource.month_values[monthKey]) || {};
        const baseCap = mv.capacity || 0;

        const otherDelta = computeStagedDelta(forecastId, monthKey, excludeIdx);

        const liveDelta = modalLiveTotalCap - ownOldCapacity;

        const totalDelta = otherDelta + liveDelta;
        const projected  = baseCap + totalDelta;

        document.getElementById("rc-breakdown-projected").textContent = fmtNum(Math.round(projected));
        document.getElementById("rc-breakdown-base").textContent      = fmtNum(Math.round(baseCap));
        const deltaSpan = document.getElementById("rc-breakdown-delta");
        deltaSpan.textContent = `${totalDelta >= 0 ? "+" : ""}${fmtNum(Math.round(totalDelta))}`;
        deltaSpan.className   = totalDelta >= 0 ? "rc-delta-pos" : "rc-delta-neg";

        el.classList.remove("d-none");
    }

    // ── Multi-month cache helpers ─────────────────────────────────────────
    function saveCurrentMonthToCache(monthKey) {
        if (!monthKey) return;
        const rows = [];
        document.querySelectorAll("#rc-week-tbody tr").forEach(row => {
            rows.push({
                rampPct:       row.querySelector(".rc-ramp-pct")?.value ?? "",
                rampEmployees: row.querySelector(".rc-emp")?.value ?? "",
                workingDays:   row.querySelector(".rc-working-days")?.value ?? "",
            });
        });
        if (rows.length) State.monthWeekCache[monthKey] = rows;
        updateMonthDropdownIndicators();
    }

    function restoreCacheToWeekInputs(monthKey) {
        const cached = State.monthWeekCache[monthKey];
        if (!cached) return;
        const trs = document.querySelectorAll("#rc-week-tbody tr");
        cached.forEach((c, i) => {
            if (i >= trs.length) return;
            const tr = trs[i];
            if (c.rampPct       !== "") tr.querySelector(".rc-ramp-pct").value = c.rampPct;
            if (c.rampEmployees !== "") tr.querySelector(".rc-emp").value = c.rampEmployees;
            if (c.workingDays   !== "") tr.querySelector(".rc-working-days").value = c.workingDays;
        });
        recomputeModalCapacity();
        refreshCapacityBreakdown();
    }

    function updateMonthDropdownIndicators() {
        const mSel = document.getElementById("rc-modal-month");
        if (!mSel) return;
        Array.from(mSel.options).forEach(opt => {
            const mk = opt.value;
            const hasData = (State.monthWeekCache[mk] || [])
                .some(r => r.rampPct !== "" || r.rampEmployees !== "");
            const baseLabel = State.months[mk] || mk;
            opt.text = hasData ? `${baseLabel} ✓` : baseLabel;
        });
    }

    // ── Add / Edit modal ─────────────────────────────────────────────────
    function openAddModal() {
        State.editIndex      = null;
        State.editDbRampData = null;
        State.editDbLobIdx   = null;
        State.monthWeekCache = {};
        State.monthIsFte     = {};
        setModalMode('add');

        const lobSel = $("#rc-modal-lob");
        if (lobSel.data("select2")) lobSel.select2("destroy");
        lobSel.empty().append(`<option value="">-- Select LOB --</option>`);
        State.lobs.forEach((lob, i) => {
            lobSel.append(new Option(lobLabel(lob), i));
        });
        lobSel.select2({ dropdownParent: $("#rc-ramp-modal"), theme: "bootstrap-5" });

        // Namespaced event prevents stacking on repeated opens
        lobSel.off("change.lobinfo").on("change.lobinfo", function () {
            const idx = parseInt($(this).val());
            updateLobInfoCard(isNaN(idx) ? null : State.lobs[idx]);
            // Cached week inputs are tied to the previously-selected LOB's
            // context; clear them so a LOB switch can't silently attribute
            // entered ramp %/employee values to the wrong LOB.
            State.monthWeekCache = {};
            State.monthIsFte     = {};
            updateMonthDropdownIndicators();
            recomputeModalCapacity();
        });
        updateLobInfoCard(null);

        const mSel = document.getElementById("rc-modal-month");
        mSel.innerHTML = Object.entries(State.months)
            .map(([k, v]) => `<option value="${k}">${v}</option>`).join("");

        document.getElementById("rc-modal-ramp-name").value = "Default";

        State.modalActiveMonthKey = mSel.value;
        renderWeekInputs(mSel.value, null);
        getRampModal().show();
    }

    function renderWeekInputs(monthKey, existingWeeks) {
        // Defensive fallback: use existingWeeks structure if State.monthWeeks[monthKey] is empty
        let weeks = State.monthWeeks[monthKey] || [];
        if (!weeks.length && existingWeeks && existingWeeks.length) {
            weeks = existingWeeks.map(ew => ({
                label:       ew.label       || ew.week_label  || "",
                startDate:   ew.startDate   || ew.start_date  || "",
                endDate:     ew.endDate     || ew.end_date    || "",
                workingDays: ew.workingDays || ew.working_days || 0,
            }));
        }

        const container = document.getElementById("rc-modal-weeks-container");

        const bulkHtml = `
            <div class="rc-bulk-helpers">
              <span class="rc-bulk-label">Bulk set:</span>
              <div class="rc-bulk-group">
                <span class="text-muted">All Ramp %</span>
                <input type="number" id="rc-bulk-ramp-pct" class="form-control form-control-sm"
                       min="0" max="100" step="1" style="width:65px" placeholder="0">
                <button class="btn btn-xs btn-outline-secondary" id="rc-bulk-ramp-pct-btn"
                        onclick="RampCampaign.applyBulkRampPct()">Apply</button>
              </div>
              <div class="rc-bulk-group">
                <span class="text-muted">All Employees</span>
                <input type="number" id="rc-bulk-employees" class="form-control form-control-sm"
                       min="0" step="1" style="width:65px" placeholder="0">
                <button class="btn btn-xs btn-outline-secondary"
                        onclick="RampCampaign.applyBulkEmployees()">Apply</button>
              </div>
              <div class="rc-bulk-group">
                <input type="checkbox" id="rc-is-fte-check" class="form-check-input">
                <label for="rc-is-fte-check" class="rc-bulk-label mb-0">Is FTE</label>
              </div>
            </div>`;

        container.innerHTML = bulkHtml + `
            <table class="table table-sm table-bordered rc-week-table">
                <thead class="table-light">
                    <tr><th>Week</th><th>Dates</th><th>Working Days</th><th>Ramp %</th><th>Employees</th><th>Capacity</th></tr>
                </thead>
                <tbody id="rc-week-tbody">
                    ${weeks.map((wk, i) => {
                        const ew      = existingWeeks && existingWeeks[i];
                        const rampPct = ew ? (ew.rampPercent  ?? ew.ramp_percent  ?? "") : "";
                        const emp     = ew ? (ew.rampEmployees ?? ew.employee_count ?? "") : "";
                        // Preserve user-edited working days from existing weeks
                        const savedWd = ew ? (ew.workingDays ?? ew.working_days ?? wk.workingDays) : wk.workingDays;
                        return `<tr data-wk-idx="${i}" data-wk-wd="${wk.workingDays}" data-wk-label="${wk.label}" data-wk-start="${wk.startDate}" data-wk-end="${wk.endDate}">
                            <td>${wk.label}</td>
                            <td>${wk.startDate} – ${wk.endDate}</td>
                            <td><input type="number" class="form-control form-control-sm rc-working-days" min="0" max="31" step="1" value="${savedWd}"></td>
                            <td><input type="number" class="form-control form-control-sm rc-ramp-pct" min="0" max="100" step="1" value="${rampPct}" placeholder="0"></td>
                            <td><input type="number" class="form-control form-control-sm rc-emp" min="0" step="1" value="${emp}" placeholder="0"></td>
                            <td class="text-end rc-cap-cell">0</td>
                        </tr>`;
                    }).join("")}
                </tbody>
            </table>`;

        // Default "Is FTE" per month: explicit per-month state wins; otherwise infer
        // from existingWeeks (all ramp% === 100 => default checked); else unchecked.
        let isFteDefault;
        if (Object.prototype.hasOwnProperty.call(State.monthIsFte, monthKey)) {
            isFteDefault = State.monthIsFte[monthKey];
        } else if (existingWeeks && existingWeeks.length) {
            isFteDefault = existingWeeks.every(ew => (ew.rampPercent ?? ew.ramp_percent) === 100);
        } else {
            isFteDefault = false;
        }
        State.monthIsFte[monthKey] = isFteDefault;

        const fteCheck = document.getElementById("rc-is-fte-check");
        fteCheck.checked = isFteDefault;
        applyIsFteState(isFteDefault);

        fteCheck.addEventListener("change", () => {
            State.monthIsFte[monthKey] = fteCheck.checked;
            applyIsFteState(fteCheck.checked);
            recomputeModalCapacity();
            refreshCapacityBreakdown();
        });

        container.querySelectorAll(".rc-emp, .rc-ramp-pct, .rc-working-days").forEach(inp => {
            inp.addEventListener("input", () => { recomputeModalCapacity(); refreshCapacityBreakdown(); });
        });
        recomputeModalCapacity();
        refreshCapacityBreakdown();
    }

    function recomputeModalCapacity() {
        let cph, shrinkage, wh;
        if (State.modalMode === 'edit-db') {
            const ramp = State.editDbRampData || {};
            cph       = ramp.target_cph || 0;
            shrinkage = getEffectiveShrinkage(ramp);
            wh        = getEffectiveWorkHours(ramp);
        } else {
            const lobIdx = parseInt(document.getElementById("rc-modal-lob").value);
            const lob    = isNaN(lobIdx) ? null : State.lobs[lobIdx];
            cph       = lob ? lob.target_cph : 0;
            shrinkage = getEffectiveShrinkage(lob);
            wh        = getEffectiveWorkHours(lob);
        }

        let totalCap = 0, peakEmp = 0;
        document.querySelectorAll("#rc-week-tbody tr").forEach(row => {
            const emp     = parseFloat(row.querySelector(".rc-emp")?.value) || 0;
            const rampPct = (parseFloat(row.querySelector(".rc-ramp-pct")?.value) || 0) / 100;
            const wdInp   = row.querySelector(".rc-working-days");
            const wd      = wdInp ? (parseFloat(wdInp.value) || 0) : (parseFloat(row.dataset.wkWd) || 0);
            const cap     = Math.round(emp * rampPct * cph * wh * (1 - shrinkage) * wd);
            row.querySelector(".rc-cap-cell").textContent = fmtNum(cap);
            totalCap += cap;
            if (emp > peakEmp) peakEmp = emp;
        });

        document.getElementById("rc-modal-total-cap").textContent = fmtNum(totalCap);
        document.getElementById("rc-modal-peak-emp").textContent  = fmtNum(peakEmp);
        modalLiveTotalCap = totalCap;
    }

    function collectModalWeeks(monthKey) {
        let cph, shrinkage, wh;
        if (State.modalMode === 'edit-db') {
            const ramp = State.editDbRampData || {};
            cph       = ramp.target_cph || 0;
            shrinkage = getEffectiveShrinkage(ramp);
            wh        = getEffectiveWorkHours(ramp);
        } else {
            const lobIdx = parseInt(document.getElementById("rc-modal-lob").value);
            const lob    = isNaN(lobIdx) ? null : State.lobs[lobIdx];
            cph       = lob ? lob.target_cph : 0;
            shrinkage = getEffectiveShrinkage(lob);
            wh        = getEffectiveWorkHours(lob);
        }

        const weeks = [];
        document.querySelectorAll("#rc-week-tbody tr").forEach(row => {
            const emp     = parseFloat(row.querySelector(".rc-emp")?.value) || 0;
            const rampPct = parseFloat(row.querySelector(".rc-ramp-pct")?.value) || 0;
            const wdInp   = row.querySelector(".rc-working-days");
            const wd      = wdInp ? (parseFloat(wdInp.value) || 0) : (parseFloat(row.dataset.wkWd) || 0);
            const cap     = Math.round(emp * (rampPct / 100) * cph * wh * (1 - shrinkage) * wd);
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

    // Dispatcher: routes save button to correct handler based on modal mode
    // Guards against duplicate staged rows from a rapid double-click: the save
    // button is disabled synchronously before either handler runs, and only
    // re-enabled if validation rejects the save (on success the modal closes,
    // and the various open* functions/hidden.bs.modal handler re-enable it).
    function saveRampFromModal() {
        const saveBtn = document.getElementById("rc-modal-save-btn");
        if (saveBtn.disabled) return;
        saveBtn.disabled = true;
        const ok = (State.modalMode === 'edit-db') ? saveDbRampEdit() : saveStagingRamp();
        if (!ok) saveBtn.disabled = false;
    }

    // ── Multi-month staging save ─────────────────────────────────────────
    function saveStagingRamp() {
        const lobIdx   = parseInt(document.getElementById("rc-modal-lob").value);
        const rampName = document.getElementById("rc-modal-ramp-name").value.trim();

        if (isNaN(lobIdx) || !rampName) {
            showToast("Please fill in all required fields.", "warning");
            return false;
        }

        // Flush current month's inputs into cache
        saveCurrentMonthToCache(State.modalActiveMonthKey);

        const lob = State.lobs[lobIdx];
        const monthsToStage = Object.keys(State.monthWeekCache);

        if (!monthsToStage.length) {
            showToast("No week data entered.", "warning");
            return false;
        }

        // When editing an already-staged row, its original month/name must be
        // preserved exactly — renaming it would leave the real DB ramp (if any)
        // untouched and double-count capacity, since FastAPI upserts/deletes by
        // exact ramp_name match. Only genuinely new months get a fresh unique name.
        const editingRow       = State.editIndex !== null ? State.stagingRows[State.editIndex] : null;
        const originalMonthKey = editingRow ? editingRow.month_key : null;
        const originalRampName = editingRow ? editingRow.ramp_name : null;

        const newRows = [];

        for (const mk of monthsToStage) {
            const cachedInputs = State.monthWeekCache[mk] || [];
            const wkDefs = State.monthWeeks[mk] || [];
            if (!wkDefs.length) continue;

            // Reconstruct weeks from cache
            const cph = lob.target_cph;
            const sh  = getEffectiveShrinkage(lob);
            const wh  = getEffectiveWorkHours(lob);
            const weeks = wkDefs.map((wk, i) => {
                const ci      = cachedInputs[i] || {};
                const emp     = parseFloat(ci.rampEmployees) || 0;
                const rampPct = parseFloat(ci.rampPct) || 0;
                const wd      = ci.workingDays !== undefined && ci.workingDays !== ""
                    ? parseFloat(ci.workingDays)
                    : wk.workingDays;
                const cap = Math.round(emp * (rampPct / 100) * cph * wh * (1 - sh) * wd);
                return {
                    label:          wk.label,
                    week_label:     wk.label,
                    startDate:      wk.startDate,
                    start_date:     wk.startDate,
                    endDate:        wk.endDate,
                    end_date:       wk.endDate,
                    workingDays:    wd,
                    working_days:   wd,
                    rampPercent:    rampPct,
                    ramp_percent:   rampPct,
                    rampEmployees:  emp,
                    employee_count: emp,
                    capacity:       cap,
                };
            });

            const isOriginalMonth = mk === originalMonthKey;
            const uniqueName = isOriginalMonth ? originalRampName : buildUniqueRampName(rampName, mk);
            // Preserve the row's actual prior action instead of blindly forcing
            // "edit" — re-saving an already-staged "add" (never applied to the
            // DB) must stay "add", or the staging table/preview would show a
            // misleading "edit" badge for a ramp with no real DB baseline.
            const originalAction = (isOriginalMonth && editingRow) ? editingRow.action : null;
            // Carry forward the DB baseline being edited (not recomputed — this
            // row's own weeks already reflect the pending new values, not the
            // true DB baseline) so capacity-breakdown delta math nets correctly.
            const carriedOldCapacity = (originalAction === "edit")
                ? (editingRow.old_capacity || 0)
                : 0;

            newRows.push({
                row: {
                    forecast_id:        lob.forecast_id,
                    main_lob:           lob.main_lob,
                    state:              lob.state,
                    case_type:          lob.case_type,
                    target_cph:         lob.target_cph,
                    work_hours:         wh,
                    shrinkage_pct:      Math.round(sh * 10000) / 100,
                    month_key:          mk,
                    month_label:        State.months[mk] || mk,
                    ramp_name:          uniqueName,
                    weeks,
                    totalRampEmployees: weeks.reduce((s, w) => s + w.rampEmployees, 0),
                    old_capacity:       isOriginalMonth ? carriedOldCapacity : 0,
                    action:             isOriginalMonth ? (originalAction || "add") : "add",
                },
                isOriginalMonth,
            });
        }

        if (!newRows.length) {
            showToast("No valid week definitions found.", "warning");
            return false;
        }

        // Apply: replace the originally-edited row in place, push all other months as new
        newRows.forEach(({ row, isOriginalMonth }) => {
            if (isOriginalMonth && State.editIndex !== null) {
                State.stagingRows[State.editIndex] = row;
            } else {
                State.stagingRows.push(row);
            }
        });

        getRampModal().hide();
        renderStagingTable();
        updateBadges();
        if (State.dbActiveMonthKey) renderDbRampsForMonth(State.dbActiveMonthKey);
        switchTab("staging");
        return true;
    }

    function saveDbRampEdit() {
        const ramp = State.editDbRampData;
        if (!ramp) return false;
        const monthKey = document.getElementById("rc-modal-month").value;
        const weeks    = collectModalWeeks(monthKey);
        if (!weeks.length) {
            showToast("No weeks data available.", "warning");
            return false;
        }
        const totalEmp = weeks.reduce((s, w) => s + (w.rampEmployees || 0), 0);
        const sh = getEffectiveShrinkage(ramp);
        const wh = getEffectiveWorkHours(ramp);
        const oldCapacity = (ramp.weeks || []).reduce((s, w) => s + (w.capacity || 0), 0);
        State.stagingRows.push({
            forecast_id:        ramp.forecast_id,
            main_lob:           ramp.main_lob,
            state:              ramp.state,
            case_type:          ramp.case_type,
            target_cph:         ramp.target_cph || 0,
            work_hours:         wh,
            shrinkage_pct:      Math.round(sh * 10000) / 100,
            month_key:          monthKey,
            month_label:        State.months[monthKey] || monthKey,
            ramp_name:          ramp.ramp_name,
            weeks,
            totalRampEmployees: totalEmp,
            old_capacity:       oldCapacity,
            action:             "edit",
        });
        getRampModal().hide();
        renderStagingTable();
        updateBadges();
        if (State.dbActiveMonthKey) renderDbRampsForMonth(State.dbActiveMonthKey);
        switchTab("staging");
        return true;
    }

    // ── Edit staging row ─────────────────────────────────────────────────
    function editStaging(idx) {
        if (State.stagingLocked) return;
        // Defense-in-depth: the Edit button is hidden for delete-staged rows
        // (renderStagingTable), but guard here too in case this is ever
        // reached another way — editing a delete would silently zero it out
        // instead of removing the ramp.
        if (State.stagingRows[idx] && State.stagingRows[idx].action === "delete") {
            showToast("Delete-staged ramps can't be edited — remove and re-add if needed.", "warning");
            return;
        }
        State.editIndex      = idx;
        State.editDbRampData = null;
        State.editDbLobIdx   = null;
        State.monthWeekCache = {};
        State.monthIsFte     = {};
        setModalMode('edit-staging');

        const row    = State.stagingRows[idx];
        const lobSel = $("#rc-modal-lob");
        if (lobSel.data("select2")) lobSel.select2("destroy");
        lobSel.empty().append(`<option value="">-- Select LOB --</option>`);
        State.lobs.forEach((lob, i) => {
            const opt = new Option(lobLabel(lob), i);
            if (lob.forecast_id == row.forecast_id && lob.main_lob === row.main_lob) opt.selected = true;
            lobSel.append(opt);
        });
        lobSel.select2({ dropdownParent: $("#rc-ramp-modal"), theme: "bootstrap-5" });

        lobSel.off("change.lobinfo").on("change.lobinfo", function () {
            const idx2 = parseInt($(this).val());
            updateLobInfoCard(isNaN(idx2) ? null : State.lobs[idx2]);
            State.monthWeekCache = {};
            State.monthIsFte     = {};
            updateMonthDropdownIndicators();
            recomputeModalCapacity();
        });
        const curLobIdx = State.lobs.findIndex(
            l => l.forecast_id == row.forecast_id && l.main_lob === row.main_lob);
        State.modalActiveMonthKey = row.month_key;
        updateLobInfoCard(curLobIdx >= 0 ? State.lobs[curLobIdx] : null);

        const mSel = document.getElementById("rc-modal-month");
        mSel.innerHTML = Object.entries(State.months)
            .map(([k, v]) => `<option value="${k}" ${k === row.month_key ? "selected" : ""}>${v}</option>`).join("");

        document.getElementById("rc-modal-ramp-name").value = row.ramp_name || "Default";

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
                if (State.dbActiveMonthKey) renderDbRampsForMonth(State.dbActiveMonthKey);
            }
        });
    }

    // ── Edit DB ramp: mode-aware, no onclick override ────────────────────
    function editDbRamp(idx, monthKey) {
        const ramps = State.dbRamps.filter(r => r.month_key === monthKey);
        const ramp  = ramps[idx];
        if (!ramp) return;

        State.editDbRampData = ramp;
        State.editDbLobIdx   = State.lobs.findIndex(
            l => l.forecast_id == ramp.forecast_id && l.main_lob === ramp.main_lob);
        State.editIndex = null;
        State.monthWeekCache = {};
        State.monthIsFte     = {};

        // Destroy Select2 BEFORE setModalMode hides the select
        const lobSel = $("#rc-modal-lob");
        if (lobSel.data("select2")) lobSel.select2("destroy");
        lobSel.empty();   // clear stale value; mode-aware reads use State.editDbRampData

        // Populate hidden month select so collectModalWeeks can read monthKey
        const mSel = document.getElementById("rc-modal-month");
        mSel.innerHTML = Object.entries(State.months)
            .map(([k, v]) => `<option value="${k}" ${k === monthKey ? "selected" : ""}>${v}</option>`)
            .join("");

        document.getElementById("rc-modal-ramp-name").value = ramp.ramp_name || "Default";

        // Switch mode: hides LOB/month selects, shows display divs, sets title/button
        setModalMode('edit-db');
        populateLobDisplay(ramp);
        populateMonthDisplay(monthKey);
        State.modalActiveMonthKey = monthKey;
        // ramp.locality is now present from load_ramps enrichment
        updateLobInfoCard(ramp);

        renderWeekInputs(monthKey, ramp.weeks);
        getRampModal().show();
    }

    // ── Delete DB ramp: staged with peak/capacity for preview estimates ──
    function deleteDbRamp(idx, monthKey) {
        const ramps = State.dbRamps.filter(r => r.month_key === monthKey);
        const ramp  = ramps[idx];
        if (!ramp) return;
        const peakEmp  = Math.max(...(ramp.weeks || []).map(w => w.employee_count || 0), 0);
        const totalCap = (ramp.weeks || []).reduce((s, w) => s + (w.capacity || 0), 0);

        Swal.fire({
            title: `Delete ramp "${ramp.ramp_name}"?`,
            html: `Estimated impact: <strong>−${fmtNum(peakEmp)} FTE</strong>, <strong>−${fmtNum(Math.round(totalCap))} capacity</strong>.<br>
                   <small class="text-muted">Stage for deletion then Preview &amp; Submit to apply.</small>`,
            icon: "warning",
            showCancelButton: true,
            confirmButtonText: "Stage Delete",
            confirmButtonColor: "#dc3545",
        }).then(result => {
            if (result.isConfirmed) {
                State.stagingRows.push({
                    forecast_id:    ramp.forecast_id,
                    main_lob:       ramp.main_lob,
                    state:          ramp.state,
                    case_type:      ramp.case_type,
                    target_cph:     ramp.target_cph || 0,
                    work_hours:     ramp.work_hours,
                    shrinkage_pct:  ramp.shrinkage_pct,
                    month_key:      monthKey,
                    month_label:    State.months[monthKey] || monthKey,
                    ramp_name:      ramp.ramp_name,
                    weeks:          [],
                    peak_employees: peakEmp,
                    total_capacity: Math.round(totalCap),
                    action:         "delete",
                });
                renderStagingTable();
                updateBadges();
                if (State.dbActiveMonthKey) renderDbRampsForMonth(State.dbActiveMonthKey);
                switchTab("staging");
            }
        });
    }

    // ── Bulk helpers ─────────────────────────────────────────────────────
    // Forces/relaxes 100% ramp on all week rows for the "Is FTE" checkbox.
    function applyIsFteState(isFte) {
        document.querySelectorAll("#rc-week-tbody .rc-ramp-pct").forEach(inp => {
            if (isFte) {
                inp.value = "100";
                inp.setAttribute("disabled", "disabled");
            } else {
                inp.removeAttribute("disabled");
            }
        });
        const bulkPctInput = document.getElementById("rc-bulk-ramp-pct");
        const bulkPctBtn   = document.getElementById("rc-bulk-ramp-pct-btn");
        if (bulkPctInput) bulkPctInput.disabled = isFte;
        if (bulkPctBtn)   bulkPctBtn.disabled   = isFte;
    }

    function applyBulkRampPct() {
        if (document.getElementById("rc-is-fte-check")?.checked) return;
        const val = document.getElementById("rc-bulk-ramp-pct")?.value;
        if (val === "" || val == null) return;
        document.querySelectorAll("#rc-week-tbody .rc-ramp-pct").forEach(i => { i.value = val; });
        recomputeModalCapacity();
        refreshCapacityBreakdown();
    }

    function applyBulkEmployees() {
        const val = document.getElementById("rc-bulk-employees")?.value;
        if (val === "" || val == null) return;
        document.querySelectorAll("#rc-week-tbody .rc-emp").forEach(i => { i.value = val; });
        recomputeModalCapacity();
        refreshCapacityBreakdown();
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
                let html = result.message || `${result.applied?.length || 0} ramps applied.`;
                if (result.total_fte_removed || result.total_cap_removed) {
                    html += `<br><br><small class="text-danger">
                        Deleted: <strong>${fmtNum(result.total_fte_removed)} FTE</strong>
                        and <strong>${fmtNum(result.total_cap_removed)} capacity</strong> removed.
                    </small>`;
                }
                await Swal.fire({
                    icon: "success",
                    title: "Applied!",
                    html,
                    timer: 4000,
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
        const ramps = State.dbActiveMonthKey
            ? State.dbRamps.filter(r => r.month_key === State.dbActiveMonthKey)
            : State.dbRamps;
        downloadExcel("db", ramps);
    }

    function downloadExcel(mode, ramps) {
        const data = {
            mode,
            ramps,
            report_month: State.reportMonth,
            report_year:  State.reportYear,
        };

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
        applyBulkRampPct,
        applyBulkEmployees,
        clearStagingFilter() {
            State.filters.staging = "";
            const el = document.getElementById("rc-staging-filter");
            if (el) el.value = "";
            renderStagingTable();
        },
        clearDbFilter() {
            State.filters.db = "";
            const el = document.getElementById("rc-db-filter");
            if (el) el.value = "";
            renderDbRampsForMonth(State.dbActiveMonthKey);
        },
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

        // Select2 for year/month on the main page
        $("#rc-year-select").select2({ theme: "bootstrap-5", placeholder: "-- Select Year --", width: "auto" });
        $("#rc-month-select").select2({ theme: "bootstrap-5", placeholder: "-- Select Month --", width: "auto" });

        $("#rc-year-select").on("change", e => onYearChange(e.target.value));
        $("#rc-month-select").on("change", e => onMonthChange(e.target.value));

        document.getElementById("rc-add-btn").addEventListener("click", openAddModal);
        document.getElementById("rc-preview-btn").addEventListener("click", triggerPreview);
        document.getElementById("rc-export-staging-btn").addEventListener("click", exportStaging);
        document.getElementById("rc-export-db-btn").addEventListener("click", exportDb);

        // Modal month change — save current month to cache, then switch
        document.getElementById("rc-modal-month").addEventListener("change", e => {
            if (State.modalMode === 'edit-db') return;
            saveCurrentMonthToCache(State.modalActiveMonthKey);
            State.modalActiveMonthKey = e.target.value;
            renderWeekInputs(e.target.value, null);
            restoreCacheToWeekInputs(e.target.value);
        });

        // Modal save — dispatcher routes based on State.modalMode
        document.getElementById("rc-modal-save-btn").onclick = saveRampFromModal;

        // Preview modal buttons
        document.getElementById("rc-confirm-apply-btn").addEventListener("click", confirmApply);
        document.getElementById("rc-preview-cancel-btn").addEventListener("click", unlockStaging);

        // Filter inputs
        document.getElementById("rc-staging-filter").addEventListener("input", e => {
            State.filters.staging = e.target.value;
            renderStagingTable();
        });
        document.getElementById("rc-db-filter").addEventListener("input", e => {
            State.filters.db = e.target.value;
            renderDbRampsForMonth(State.dbActiveMonthKey);
        });

        // Full cleanup when ramp modal closes
        document.getElementById("rc-ramp-modal").addEventListener("hidden.bs.modal", () => {
            State.modalMode          = 'add';
            State.editIndex          = null;
            State.editDbRampData     = null;
            State.editDbLobIdx       = null;
            State.monthWeekCache     = {};
            State.monthIsFte         = {};
            State.modalActiveMonthKey = null;

            document.getElementById("rc-modal-lob").classList.remove("d-none");
            document.getElementById("rc-modal-lob-display").classList.add("d-none");
            document.getElementById("rc-modal-month").classList.remove("d-none");
            document.getElementById("rc-modal-month-display").classList.add("d-none");

            const rn = document.getElementById("rc-modal-ramp-name");
            rn.removeAttribute("readonly");
            rn.classList.remove("rc-readonly-field");

            document.getElementById("rc-lob-info-card").classList.add("d-none");
            document.getElementById("rc-cap-breakdown").classList.add("d-none");
            const saveBtn = document.getElementById("rc-modal-save-btn");
            saveBtn.disabled = false;
            saveBtn.onclick  = saveRampFromModal;
        });
    });

})();
