/**
 * Chat Widget JavaScript
 * Handles WebSocket communication, message rendering, and UI interactions
 */

(function() {
    'use strict';

    // ========================================================================
    // State Management
    // ========================================================================
    const ChatState = {
        ws: null,
        conversationId: null,
        isConnected: false,
        isOpen: false,
        reconnectAttempts: 0,
        maxReconnectAttempts: 5,
        reconnectDelay: 1000, // Start with 1 second
        messageQueue: [],
        pendingConfirmations: new Map(),
        selectedForecastRow: null, // Currently selected forecast row data
        // ── Ramp modal state ──────────────────────────────────────────────
        pendingRampWeeks: null,      // Raw week data from backend trigger card
        pendingRampMonthKey: null,
        pendingRampForecastId: null,
        // ── Bulk ramp state ───────────────────────────────────────────────
        currentRampListData: null,   // Original API ramp list (never mutated)
        lastBulkRampSubmission: null, // Last submitted bulk payload (for "Edit Again")
        bulkRampForecastId: null,
        bulkRampMonthKey: null,
        // ── Campaign Manager state ────────────────────────────────────────
        campaignModalData: null,      // { months, lobs, monthWeeks, reportLabel }
        campaignStagingRows: [],       // [{forecast_id, main_lob, state, case_type, month_key, month_label, ramp_name, weeks}]
        campaignSubModalWeeks: {},     // { "2025-04": [{...week with rampPercent/rampEmployees}] }
        campaignSubActiveMonth: null,  // active tab month key in sub-modal
        campaignEditingIndex: null,    // staging row index being edited (null = add new)
    };

    // ========================================================================
    // Thinking Bubble State
    // ========================================================================
    let thinkingBubble = null;

    function showThinkingBubble() {
        if (thinkingBubble) return; // already visible
        const div = document.createElement('div');
        div.className = 'chat-message chat-message-assistant chat-thinking-bubble';
        div.innerHTML = `
            <div class="message-content">
                <svg class="thinking-icon" viewBox="0 0 24 24" fill="none" stroke="#4a6cf7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                </svg>
                <div class="thinking-dots-inline">
                    <span class="thinking-dot"></span>
                    <span class="thinking-dot"></span>
                    <span class="thinking-dot"></span>
                </div>
            </div>`;
        elements.messagesArea.appendChild(div);
        thinkingBubble = div;
        scrollToBottom();
    }

    function hideThinkingBubble() {
        if (thinkingBubble) {
            thinkingBubble.remove();
            thinkingBubble = null;
        }
    }

    // ========================================================================
    // DOM Elements
    // ========================================================================
    let elements = {};

    function initElements() {
        elements = {
            toggleBtn: document.getElementById('chat-toggle-btn'),
            container: document.getElementById('chat-container'),
            minimizeBtn: document.getElementById('chat-minimize-btn'),
            newChatBtn: document.getElementById('chat-new-chat-btn'),
            messagesArea: document.getElementById('chat-messages'),
            input: document.getElementById('chat-input'),
            sendBtn: document.getElementById('chat-send-btn'),
            typingIndicator: document.getElementById('chat-typing-indicator'),
            statusBar: document.getElementById('chat-status-bar'),
            statusMessage: document.getElementById('chat-status-message'),
            connectionStatus: document.getElementById('chat-connection-status'),
            modalOverlay: document.getElementById('chat-modal-overlay'),
            modalContainer: document.getElementById('chat-modal-container'),
            modalTitle: document.getElementById('chat-modal-title'),
            modalBody: document.getElementById('chat-modal-body'),
            modalCloseBtn: document.getElementById('chat-modal-close-btn'),
            modalCloseFooterBtn: document.getElementById('chat-modal-close-footer-btn'),
            // Ramp modal
            rampModalOverlay: document.getElementById('ramp-modal-overlay'),
            rampModalTitle: document.getElementById('ramp-modal-title'),
            rampModalBody: document.getElementById('ramp-modal-body'),
            rampModalCloseBtn: document.getElementById('ramp-modal-close-btn'),
            rampModalCancelBtn: document.getElementById('ramp-modal-cancel-btn'),
            rampModalSubmitBtn: document.getElementById('ramp-modal-submit-btn'),
            rampModalError: document.getElementById('ramp-modal-error'),
            // Bulk ramp modal
            bulkRampModal: document.getElementById('ramp-bulk-edit-modal'),
            bulkRampTitle: document.getElementById('ramp-bulk-edit-title'),
            bulkRampBody: document.getElementById('ramp-bulk-edit-body'),
            bulkRampCloseBtn: document.getElementById('ramp-bulk-edit-close-btn'),
            bulkRampCancelBtn: document.getElementById('ramp-bulk-edit-cancel-btn'),
            bulkRampSubmitBtn: document.getElementById('ramp-bulk-edit-submit-btn'),
            bulkRampError: document.getElementById('ramp-bulk-edit-error'),
        };
    }

    // ========================================================================
    // WebSocket Connection
    // ========================================================================
    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/centene_forecasting/ws/chat/`;

        console.log('[Chat] Connecting to WebSocket:', wsUrl);

        ChatState.ws = new WebSocket(wsUrl);

        ChatState.ws.onopen = handleWebSocketOpen;
        ChatState.ws.onmessage = handleWebSocketMessage;
        ChatState.ws.onclose = handleWebSocketClose;
        ChatState.ws.onerror = handleWebSocketError;
    }

    function handleWebSocketOpen(event) {
        console.log('[Chat] WebSocket connected');
        ChatState.isConnected = true;
        ChatState.reconnectAttempts = 0;
        ChatState.reconnectDelay = 1000;

        updateConnectionStatus('connected', 'Connected');
        hideStatusBar();

        // Send queued messages
        while (ChatState.messageQueue.length > 0) {
            const message = ChatState.messageQueue.shift();
            sendWebSocketMessage(message);
        }
    }

    function handleWebSocketMessage(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('[Chat] Received message:', data);

            switch (data.type) {
                case 'system':
                    handleSystemMessage(data);
                    break;
                case 'typing':
                    handleTypingIndicator(data);
                    break;
                case 'assistant_response':
                    handleAssistantResponse(data);
                    break;
                case 'tool_result':
                    handleToolResult(data);
                    break;
                case 'rejection_response':
                    handleRejectionResponse(data);
                    break;
                case 'error':
                    handleErrorMessage(data);
                    break;
                case 'cph_preview':
                    handleCphPreview(data);
                    break;
                case 'cph_update_result':
                    handleCphUpdateResult(data);
                    break;
                case 'fte_details':
                    handleFteDetails(data);
                    break;
                case 'ramp_confirmation':
                    handleRampConfirmation(data);
                    break;
                case 'ramp_preview':
                    handleRampPreview(data);
                    break;
                case 'ramp_apply_result':
                    handleRampApplyResult(data);
                    break;
                case 'bulk_ramp_confirmation':
                    handleBulkRampConfirmation(data);
                    break;
                case 'bulk_ramp_preview':
                    handleBulkRampPreview(data);
                    break;
                case 'bulk_ramp_apply_result':
                    handleBulkRampApplyResult(data);
                    break;
                case 'campaign_preview':
                    handleCampaignPreview(data);
                    break;
                case 'campaign_apply_result':
                    handleCampaignApplyResult(data);
                    break;
                default:
                    console.warn('[Chat] Unknown message type:', data.type);
            }
        } catch (error) {
            console.error('[Chat] Error parsing message:', error);
        }
    }

    function handleWebSocketClose(event) {
        console.log('[Chat] WebSocket closed:', event.code, event.reason);
        ChatState.isConnected = false;

        updateConnectionStatus('disconnected', 'Disconnected');

        // Attempt to reconnect
        if (ChatState.reconnectAttempts < ChatState.maxReconnectAttempts) {
            ChatState.reconnectAttempts++;
            const delay = ChatState.reconnectDelay * Math.pow(2, ChatState.reconnectAttempts - 1);

            showStatusBar(`Disconnected. Reconnecting in ${delay / 1000}s... (${ChatState.reconnectAttempts}/${ChatState.maxReconnectAttempts})`);

            setTimeout(() => {
                console.log('[Chat] Attempting to reconnect...');
                connectWebSocket();
            }, delay);
        } else {
            showStatusBar('Connection lost. Please refresh the page.');
        }
    }

    function handleWebSocketError(event) {
        console.error('[Chat] WebSocket error:', event);
        updateConnectionStatus('disconnected', 'Connection Error');
    }

    function sendWebSocketMessage(data) {
        if (ChatState.isConnected && ChatState.ws.readyState === WebSocket.OPEN) {
            ChatState.ws.send(JSON.stringify(data));
            console.log('[Chat] Sent message:', data);
        } else {
            console.log('[Chat] Queuing message (not connected):', data);
            ChatState.messageQueue.push(data);
        }
    }

    // ========================================================================
    // Message Handlers
    // ========================================================================
    function handleSystemMessage(data) {
        if (data.conversation_id) {
            // Check if this is a NEW conversation (different from current)
            if (ChatState.conversationId && ChatState.conversationId !== data.conversation_id) {
                // Clear UI for new conversation
                clearMessages();
            }

            // Update conversation ID
            ChatState.conversationId = data.conversation_id;
        }

        // Display system message
        addMessage('system', data.message);

        // Re-enable new chat button if it exists
        if (elements.newChatBtn) {
            elements.newChatBtn.disabled = false;
        }
    }

    function handleTypingIndicator(data) {
        if (data.is_typing) {
            showThinkingBubble();
        } else {
            hideThinkingBubble();
        }
    }

    function handleAssistantResponse(data) {
        hideThinkingBubble();
        const hasUI = data.ui_component && data.ui_component.trim() !== '';
        const hasMessage = data.message && data.message.trim() !== '';

        // Show plain text first (LLM summary / clarification)
        if (hasMessage) {
            addMessage('assistant', data.message);
        }

        // Then show the rich HTML component (table, card, etc.)
        if (hasUI) {
            addMessageWithHTML('assistant', data.ui_component);
        }

        // Store pending confirmation data (legacy)
        ChatState.pendingConfirmations.set(data.category, {
            category: data.category,
            parameters: data.metadata || {},
            messageId: data.message_id
        });

        // Attach event listeners to buttons
        attachConfirmationListeners();
        attachViewFullDataListeners();
        attachCphConfirmListeners();
        attachRampOpenListeners();
        attachRampListShowDataListeners();
        attachForecastFetchConfirmListeners();
        attachCampaignOpenListeners();
    }

    function handleToolResult(data) {
        hideThinkingBubble();
        if (data.success) {
            // Inject result UI (table, etc.)
            addMessageWithHTML('assistant', data.ui_component);

            // Attach event listeners
            attachViewFullDataListeners();
            attachRampOpenListeners();
        } else {
            addMessage('assistant', data.message || 'Failed to execute action.');
        }
    }

    function handleRejectionResponse(data) {
        hideThinkingBubble();
        addMessage('assistant', data.message);
    }

    function handleErrorMessage(data) {
        hideThinkingBubble();
        addMessage('system', `Error: ${data.message}`);
    }

    // ========================================================================
    // UI Functions - Messages
    // ========================================================================
    function addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message chat-message-${role}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;

        messageDiv.appendChild(contentDiv);
        elements.messagesArea.appendChild(messageDiv);

        scrollToBottom();
    }

    function addMessageWithHTML(role, htmlContent) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message chat-message-${role}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = htmlContent;

        messageDiv.appendChild(contentDiv);
        elements.messagesArea.appendChild(messageDiv);

        scrollToBottom();
    }

    function scrollToBottom() {
        elements.messagesArea.scrollTop = elements.messagesArea.scrollHeight;
    }

    function clearSystemMessages() {
        const systemMessages = elements.messagesArea.querySelectorAll('.chat-message-system');
        systemMessages.forEach(msg => msg.remove());
    }

    // ========================================================================
    // UI Functions - Status
    // ========================================================================
    function updateConnectionStatus(status, text) {
        const indicator = elements.connectionStatus.querySelector('.status-indicator');
        const statusText = elements.connectionStatus.querySelector('.status-text');

        indicator.className = `status-indicator status-${status}`;
        statusText.textContent = text;
    }

    function showStatusBar(message) {
        elements.statusMessage.textContent = message;
        elements.statusBar.style.display = 'block';
    }

    function hideStatusBar() {
        elements.statusBar.style.display = 'none';
    }

    // ========================================================================
    // UI Functions - Chat Controls
    // ========================================================================
    function toggleChat() {
        ChatState.isOpen = !ChatState.isOpen;

        if (ChatState.isOpen) {
            elements.container.style.display = 'flex';
            elements.input.focus();
            clearSystemMessages();
        } else {
            elements.container.style.display = 'none';
        }
    }

    function sendMessage() {
        const text = elements.input.value.trim();

        if (!text) {
            return;
        }

        // Add user message to UI
        addMessage('user', text);

        // Build message payload with optional row context
        const payload = {
            type: 'user_message',
            message: text
        };

        // Include selected row if available
        if (ChatState.selectedForecastRow) {
            payload.selected_row = ChatState.selectedForecastRow;
        }

        // Send to WebSocket
        sendWebSocketMessage(payload);

        // Show thinking animation while waiting for response
        showThinkingBubble();

        // Clear input
        elements.input.value = '';
        elements.input.style.height = 'auto';
    }

    function startNewChat() {
        // 1. Disable button to prevent double-clicks
        elements.newChatBtn.disabled = true;

        // 2. Send new_conversation message to backend
        sendWebSocketMessage({
            type: 'new_conversation',
            old_conversation_id: ChatState.conversationId
        });

        // Note: Don't clear state here - wait for server confirmation
        // This ensures proper database updates happen first
    }

    function clearMessages() {
        // Remove all messages except system messages
        const messages = elements.messagesArea.querySelectorAll('.chat-message:not(.chat-message-system)');
        messages.forEach(msg => msg.remove());

        // Clear pending confirmations
        ChatState.pendingConfirmations.clear();

        // Reset scroll position
        elements.messagesArea.scrollTop = 0;
    }

    // ========================================================================
    // Confirmation Handling
    // ========================================================================
    function attachConfirmationListeners() {
        // Confirm buttons
        const confirmBtns = elements.messagesArea.querySelectorAll('.chat-confirm-btn');
        confirmBtns.forEach(btn => {
            btn.addEventListener('click', handleConfirmation);
        });

        // Reject buttons
        const rejectBtns = elements.messagesArea.querySelectorAll('.chat-reject-btn');
        rejectBtns.forEach(btn => {
            btn.addEventListener('click', handleRejection);
        });
    }

    function handleConfirmation(event) {
        const btn = event.currentTarget;
        const category = btn.getAttribute('data-category');
        const parametersJson = btn.getAttribute('data-parameters');

        try {
            const parameters = JSON.parse(parametersJson);

            // Send confirmation to WebSocket
            sendWebSocketMessage({
                type: 'confirm_category',
                category: category,
                parameters: parameters,
                message_id: ChatState.pendingConfirmations.get(category)?.messageId
            });

            // Disable buttons
            btn.disabled = true;
            const rejectBtn = btn.parentElement.querySelector('.chat-reject-btn');
            if (rejectBtn) {
                rejectBtn.disabled = true;
            }

        } catch (error) {
            console.error('[Chat] Error parsing parameters:', error);
        }
    }

    function handleRejection(event) {
        const btn = event.currentTarget;
        const category = btn.getAttribute('data-category');

        // Send rejection to WebSocket
        sendWebSocketMessage({
            type: 'reject_category',
            category: category
        });

        // Disable buttons
        btn.disabled = true;
        const confirmBtn = btn.parentElement.querySelector('.chat-confirm-btn');
        if (confirmBtn) {
            confirmBtn.disabled = true;
        }
    }

    // ========================================================================
    // Modal Handling
    // ========================================================================
    function attachViewFullDataListeners() {
        const viewFullBtns = elements.messagesArea.querySelectorAll('.chat-view-full-btn');
        viewFullBtns.forEach(btn => {
            // Only attach if not already attached
            if (!btn.hasAttribute('data-listener-attached')) {
                btn.setAttribute('data-listener-attached', 'true');
                btn.addEventListener('click', handleViewFullData);
            }
        });
    }

    function handleViewFullData(event) {
        const btn = event.currentTarget;
        const container = btn.closest('.forecast-paginated-table');

        if (container) {
            // New paginated forecast table
            openForecastModal(container);
        } else {
            // Legacy handling (fallback)
            const fullDataJson = btn.getAttribute('data-full-data');
            try {
                const data = JSON.parse(fullDataJson);
                openModal('Full Data View', data);
            } catch (error) {
                console.error('[Chat] Error parsing full data:', error);
            }
        }
    }

    function openForecastModal(sourceContainer) {
        const recordsJson = sourceContainer.getAttribute('data-forecast-records');
        const monthsJson = sourceContainer.getAttribute('data-forecast-months');
        const totalRecords = parseInt(sourceContainer.getAttribute('data-total-records'), 10);

        console.log('[Chat] Opening forecast modal, totalRecords:', totalRecords);
        console.log('[Chat] recordsJson length:', recordsJson ? recordsJson.length : 'null');
        console.log('[Chat] monthsJson:', monthsJson);

        if (!recordsJson || !monthsJson) {
            console.error('[Chat] Missing data attributes on source container');
            console.log('[Chat] Source container:', sourceContainer);
            console.log('[Chat] Container HTML:', sourceContainer.outerHTML.substring(0, 500));
            return;
        }

        try {
            const records = JSON.parse(recordsJson);
            const months = JSON.parse(monthsJson);

            console.log('[Chat] Parsed records count:', records.length);
            console.log('[Chat] Parsed months:', months);

            if (!records || records.length === 0) {
                console.warn('[Chat] No records found in parsed data');
                elements.modalBody.innerHTML = '<p class="text-muted p-3">No records available.</p>';
                elements.modalOverlay.style.display = 'flex';
                return;
            }

            elements.modalTitle.textContent = `Forecast Data (${totalRecords} Records)`;

            // Build paginated table in modal
            const tableHTML = buildPaginatedForecastTable(records, months);
            elements.modalBody.innerHTML = tableHTML;

            // Initialize pagination
            initForecastPagination(elements.modalBody, records, months);

            // Show modal
            elements.modalOverlay.style.display = 'flex';
        } catch (error) {
            console.error('[Chat] Error parsing forecast data:', error);
            console.error('[Chat] recordsJson preview:', recordsJson ? recordsJson.substring(0, 200) : 'null');
        }
    }

    function buildPaginatedForecastTable(records, months) {
        const totalRecords = records.length;

        let html = `
        <div class="forecast-modal-container"
             data-current-page="1"
             data-page-size="25"
             data-total-records="${totalRecords}">
            <div class="selection-indicator" style="display: none;">
                <span class="selection-text"></span>
                <div class="selection-actions">
                    <button class="btn btn-sm btn-primary modal-get-fte-btn" title="Get FTE details for this row">
                        <i class="bi bi-info-circle"></i> Get FTE Details
                    </button>
                    <button class="btn btn-sm btn-outline-secondary modal-modify-cph-btn" title="Modify CPH for this row">
                        <i class="bi bi-pencil"></i> Modify CPH
                    </button>
                    <button class="btn btn-sm btn-outline-info modal-use-in-chat-btn" title="Use this row in chat">
                        <i class="bi bi-chat-dots"></i> Use in Chat
                    </button>
                </div>
            </div>
            <div class="forecast-table-wrapper">
                <table class="table table-sm table-bordered table-hover forecast-table">
                    ${buildForecastHeaders(months)}
                    <tbody class="forecast-table-body">
                    </tbody>
                </table>
            </div>
            <div class="forecast-pagination">
                <div class="pagination-info">
                    <span class="showing-info">Showing 1-25 of ${totalRecords} records</span>
                </div>
                <div class="pagination-controls">
                    <button class="btn btn-sm btn-outline-secondary pagination-prev" disabled>
                        &laquo; Prev
                    </button>
                    <span class="pagination-page-info">Page 1 of ${Math.ceil(totalRecords / 25)}</span>
                    <button class="btn btn-sm btn-outline-secondary pagination-next" ${totalRecords <= 25 ? 'disabled' : ''}>
                        Next &raquo;
                    </button>
                </div>
            </div>
        </div>
        `;

        return html;
    }

    function buildForecastHeaders(months) {
        let headerHTML = `
            <thead class="table-light forecast-table-header">
                <tr>
                    <th rowspan="2" class="align-middle forecast-fixed-col forecast-col-lob">Main LOB</th>
                    <th rowspan="2" class="align-middle forecast-fixed-col forecast-col-state">State</th>
                    <th rowspan="2" class="align-middle forecast-fixed-col forecast-col-casetype">Case Type</th>
                    <th rowspan="2" class="align-middle forecast-fixed-col forecast-col-cph">Target CPH</th>
        `;

        // Month headers (colspan=5 for each month)
        months.forEach(month => {
            headerHTML += `<th colspan="5" class="text-center month-header">${month}</th>`;
        });

        headerHTML += '</tr><tr>';

        // Sub-headers for each month
        months.forEach(() => {
            headerHTML += `
                <th class="text-center sub-header">Forecast</th>
                <th class="text-center sub-header">FTE Req</th>
                <th class="text-center sub-header">FTE Avail</th>
                <th class="text-center sub-header">Capacity</th>
                <th class="text-center sub-header">Gap</th>
            `;
        });

        headerHTML += '</tr></thead>';
        return headerHTML;
    }

    function buildForecastRow(record, months, rowIndex) {
        // Escape record data for HTML attribute
        const recordDataJson = JSON.stringify(record).replace(/"/g, '&quot;');

        let rowHTML = `
            <tr data-row-index="${rowIndex}" data-row-record="${recordDataJson}" class="selectable-forecast-row">
                <td class="forecast-fixed-col forecast-col-lob">${record.main_lob || 'N/A'}</td>
                <td class="forecast-fixed-col forecast-col-state">${record.state || 'N/A'}</td>
                <td class="forecast-fixed-col forecast-col-casetype">${record.case_type || 'N/A'}</td>
                <td class="text-end forecast-fixed-col forecast-col-cph">${(record.target_cph || 0).toFixed(1)}</td>
        `;

        months.forEach(month => {
            const monthData = (record.months || {})[month] || {};
            const forecast = monthData.forecast || 0;
            const fteReq = monthData.fte_required || 0;
            const fteAvail = monthData.fte_available || 0;
            const capacity = monthData.capacity || 0;
            const gap = monthData.gap || 0;

            // Determine gap class
            let gapClass = 'text-muted';
            if (gap < 0) gapClass = 'gap-negative';
            else if (gap > 0) gapClass = 'gap-positive';

            rowHTML += `
                <td class="text-end">${forecast.toLocaleString()}</td>
                <td class="text-end">${fteReq}</td>
                <td class="text-end">${fteAvail}</td>
                <td class="text-end">${capacity.toLocaleString()}</td>
                <td class="text-end ${gapClass}"><strong>${gap.toLocaleString()}</strong></td>
            `;
        });

        rowHTML += '</tr>';
        return rowHTML;
    }

    function initForecastPagination(modalBody, records, months) {
        const container = modalBody.querySelector('.forecast-modal-container');
        if (!container) {
            console.error('[Chat] forecast-modal-container not found in modal body');
            return;
        }

        console.log('[Chat] Initializing pagination with', records.length, 'records and', months.length, 'months');

        // Store data on container for pagination
        container._forecastRecords = records;
        container._forecastMonths = months;

        // Render first page
        renderForecastPage(container, 1);

        // Attach pagination listeners
        const prevBtn = container.querySelector('.pagination-prev');
        const nextBtn = container.querySelector('.pagination-next');

        prevBtn.addEventListener('click', () => {
            const currentPage = parseInt(container.getAttribute('data-current-page'), 10);
            if (currentPage > 1) {
                renderForecastPage(container, currentPage - 1);
            }
        });

        nextBtn.addEventListener('click', () => {
            const currentPage = parseInt(container.getAttribute('data-current-page'), 10);
            const pageSize = parseInt(container.getAttribute('data-page-size'), 10);
            const totalRecords = parseInt(container.getAttribute('data-total-records'), 10);
            const totalPages = Math.ceil(totalRecords / pageSize);

            if (currentPage < totalPages) {
                renderForecastPage(container, currentPage + 1);
            }
        });
    }

    function renderForecastPage(container, page) {
        const records = container._forecastRecords;
        const months = container._forecastMonths;
        const pageSize = parseInt(container.getAttribute('data-page-size'), 10);
        const totalRecords = parseInt(container.getAttribute('data-total-records'), 10);
        const totalPages = Math.ceil(totalRecords / pageSize);

        // Calculate slice indices
        const startIdx = (page - 1) * pageSize;
        const endIdx = Math.min(startIdx + pageSize, totalRecords);
        const pageRecords = records.slice(startIdx, endIdx);

        // Update current page
        container.setAttribute('data-current-page', page);

        // Clear selection when changing pages
        ChatState.selectedForecastRow = null;
        const indicator = container.querySelector('.selection-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }

        // Render rows with indices
        const tbody = container.querySelector('.forecast-table-body');
        tbody.innerHTML = pageRecords.map((record, idx) =>
            buildForecastRow(record, months, startIdx + idx)
        ).join('');

        // Attach row click handlers
        attachRowClickHandlers(container);

        // Update pagination info
        const showingInfo = container.querySelector('.showing-info');
        showingInfo.textContent = `Showing ${startIdx + 1}-${endIdx} of ${totalRecords} records`;

        const pageInfo = container.querySelector('.pagination-page-info');
        pageInfo.textContent = `Page ${page} of ${totalPages}`;

        // Update button states
        const prevBtn = container.querySelector('.pagination-prev');
        const nextBtn = container.querySelector('.pagination-next');

        prevBtn.disabled = page === 1;
        nextBtn.disabled = page === totalPages;

        // Scroll table to top
        const tableWrapper = container.querySelector('.forecast-table-wrapper');
        if (tableWrapper) {
            tableWrapper.scrollTop = 0;
        }
    }

    // ========================================================================
    // Row Selection Handlers
    // ========================================================================
    function attachRowClickHandlers(container) {
        const rows = container.querySelectorAll('.selectable-forecast-row');
        rows.forEach(row => {
            if (!row.hasAttribute('data-click-attached')) {
                row.setAttribute('data-click-attached', 'true');
                row.addEventListener('click', function() {
                    handleRowSelection(this, container);
                });
            }
        });
    }

    function handleRowSelection(rowElement, container) {
        // Deselect all rows in this container
        container.querySelectorAll('tr.selected-row').forEach(r => {
            r.classList.remove('selected-row');
        });

        // Select clicked row
        rowElement.classList.add('selected-row');

        // Parse and store row data
        try {
            const recordJson = rowElement.getAttribute('data-row-record');
            const rowData = JSON.parse(recordJson.replace(/&quot;/g, '"'));
            ChatState.selectedForecastRow = rowData;

            // Show selection indicator with action buttons
            const indicator = container.querySelector('.selection-indicator');
            if (indicator) {
                const selectionText = indicator.querySelector('.selection-text');
                if (selectionText) {
                    selectionText.textContent = `Selected: ${rowData.main_lob} | ${rowData.state} | ${rowData.case_type}`;
                }
                indicator.style.display = 'flex';

                // Attach button handlers
                attachModalActionHandlers(container);
            }

            console.log('[Chat] Row selected:', rowData);
        } catch (error) {
            console.error('[Chat] Error parsing row data:', error);
        }
    }

    function attachModalActionHandlers(container) {
        // Get FTE Details button
        const fteBtn = container.querySelector('.modal-get-fte-btn');
        if (fteBtn && !fteBtn.hasAttribute('data-handler-attached')) {
            fteBtn.setAttribute('data-handler-attached', 'true');
            fteBtn.addEventListener('click', () => {
                if (ChatState.selectedForecastRow) {
                    // Close modal
                    closeModal();
                    // Send message to get FTE details
                    sendRowActionMessage('Get FTE details for this row', ChatState.selectedForecastRow);
                }
            });
        }

        // Modify CPH button
        const cphBtn = container.querySelector('.modal-modify-cph-btn');
        if (cphBtn && !cphBtn.hasAttribute('data-handler-attached')) {
            cphBtn.setAttribute('data-handler-attached', 'true');
            cphBtn.addEventListener('click', () => {
                if (ChatState.selectedForecastRow) {
                    // Close modal
                    closeModal();
                    // Prompt user to enter new CPH value
                    const currentCph = ChatState.selectedForecastRow.target_cph || 0;
                    addMessage('assistant', `Selected row: ${ChatState.selectedForecastRow.main_lob} | ${ChatState.selectedForecastRow.state} | ${ChatState.selectedForecastRow.case_type}\nCurrent CPH: ${currentCph}\n\nTo modify the CPH, type something like "change CPH to 3.5" or "increase CPH by 10%"`);
                }
            });
        }

        // Use in Chat button
        const useBtn = container.querySelector('.modal-use-in-chat-btn');
        if (useBtn && !useBtn.hasAttribute('data-handler-attached')) {
            useBtn.setAttribute('data-handler-attached', 'true');
            useBtn.addEventListener('click', () => {
                if (ChatState.selectedForecastRow) {
                    // Close modal
                    closeModal();
                    // Confirm row selection in chat
                    const row = ChatState.selectedForecastRow;
                    addMessage('assistant', `Row selected and ready for interaction:\n• Main LOB: ${row.main_lob}\n• State: ${row.state}\n• Case Type: ${row.case_type}\n• Target CPH: ${row.target_cph}\n\nYou can now ask questions about this row, like "get FTE details" or "change CPH to 4.0"`);
                }
            });
        }
    }

    function sendRowActionMessage(message, rowData) {
        // Add user message to UI
        addMessage('user', message);

        // Send to WebSocket with selected row context
        sendWebSocketMessage({
            type: 'user_message',
            message: message,
            selected_row: rowData
        });
    }

    function clearRowSelection() {
        ChatState.selectedForecastRow = null;
        document.querySelectorAll('tr.selected-row').forEach(r => {
            r.classList.remove('selected-row');
        });
        document.querySelectorAll('.selection-indicator').forEach(ind => {
            ind.style.display = 'none';
        });
    }

    // ========================================================================
    // CPH Preview and Update Handlers
    // ========================================================================
    function handleCphPreview(data) {
        hideThinkingBubble();
        addMessageWithHTML('assistant', data.ui_component);
        attachCphConfirmListeners();
        scrollToBottom();
    }

    function handleCphUpdateResult(data) {
        hideThinkingBubble();
        if (data.success) {
            addMessageWithHTML('assistant', data.ui_component || data.message);
        } else {
            addMessage('assistant', data.message || 'Failed to update CPH.');
        }
        scrollToBottom();
    }

    function handleFteDetails(data) {
        hideThinkingBubble();
        addMessageWithHTML('assistant', data.ui_component);
        scrollToBottom();
    }

    function attachCphConfirmListeners() {
        const confirmBtns = elements.messagesArea.querySelectorAll('.cph-confirm-btn');
        const rejectBtns = elements.messagesArea.querySelectorAll('.cph-reject-btn');

        confirmBtns.forEach(btn => {
            if (!btn.hasAttribute('data-listener-attached')) {
                btn.setAttribute('data-listener-attached', 'true');
                btn.addEventListener('click', handleCphConfirm);
            }
        });

        rejectBtns.forEach(btn => {
            if (!btn.hasAttribute('data-listener-attached')) {
                btn.setAttribute('data-listener-attached', 'true');
                btn.addEventListener('click', handleCphReject);
            }
        });
    }

    function handleCphConfirm(event) {
        const btn = event.currentTarget;

        try {
            const updateDataStr = btn.getAttribute('data-update');
            const updateData = JSON.parse(updateDataStr.replace(/&quot;/g, '"'));

            sendWebSocketMessage({
                type: 'confirm_cph_update',
                update_data: updateData
            });

            // Disable all buttons in this preview
            const actionsDiv = btn.closest('.cph-preview-actions');
            if (actionsDiv) {
                actionsDiv.querySelectorAll('button').forEach(b => b.disabled = true);
            }

            showThinkingBubble();
        } catch (error) {
            console.error('[Chat] Error confirming CPH update:', error);
            addMessage('system', 'Error: Could not process CPH update.');
        }
    }

    function handleCphReject(event) {
        const btn = event.currentTarget;

        // Disable all buttons in this preview
        const actionsDiv = btn.closest('.cph-preview-actions');
        if (actionsDiv) {
            actionsDiv.querySelectorAll('button').forEach(b => b.disabled = true);
        }

        addMessage('assistant', 'CPH change cancelled.');
    }

    // ========================================================================
    // Forecast Fetch Confirmation
    // ========================================================================
    function attachForecastFetchConfirmListeners() {
        const confirmBtns = elements.messagesArea.querySelectorAll('.forecast-fetch-confirm-btn');
        confirmBtns.forEach(btn => {
            if (!btn.hasAttribute('data-listener-attached')) {
                btn.setAttribute('data-listener-attached', 'true');
                btn.addEventListener('click', handleForecastFetchConfirm);
            }
        });

        const cancelBtns = elements.messagesArea.querySelectorAll('.forecast-fetch-cancel-btn');
        cancelBtns.forEach(btn => {
            if (!btn.hasAttribute('data-listener-attached')) {
                btn.setAttribute('data-listener-attached', 'true');
                btn.addEventListener('click', handleForecastFetchCancel);
            }
        });
    }

    function handleForecastFetchConfirm(event) {
        const btn = event.currentTarget;
        const card = btn.closest('.forecast-confirm-card');
        if (card) {
            card.querySelectorAll('button').forEach(b => b.disabled = true);
        }

        // Read params embedded directly in the button — avoids context state dependency
        let fetchParams = null;
        const paramsStr = btn.getAttribute('data-params');
        if (paramsStr) {
            try {
                fetchParams = JSON.parse(paramsStr.replace(/&quot;/g, '"'));
            } catch (e) {
                console.error('[Chat] Error parsing forecast fetch params:', e);
            }
        }

        sendWebSocketMessage({ type: 'confirm_forecast_fetch', fetch_params: fetchParams });
        showThinkingBubble();
    }

    function handleForecastFetchCancel(event) {
        const btn = event.currentTarget;
        const card = btn.closest('.forecast-confirm-card');
        if (card) {
            card.querySelectorAll('button').forEach(b => b.disabled = true);
        }
        addMessage('assistant', 'Fetch cancelled.');
    }

    // ========================================================================
    // Ramp Modal
    // ========================================================================

    function openRampModal(sourceElement) {
        const weeksJson = sourceElement.getAttribute('data-ramp-weeks');
        const monthKey = sourceElement.getAttribute('data-ramp-month-key');
        const forecastId = sourceElement.getAttribute('data-forecast-id');

        if (!weeksJson || !monthKey) {
            console.error('[Chat] Missing ramp data attributes on trigger button');
            return;
        }

        try {
            const weeks = JSON.parse(weeksJson.replace(/&quot;/g, '"'));
            ChatState.pendingRampWeeks = weeks;
            ChatState.pendingRampMonthKey = monthKey;
            ChatState.pendingRampForecastId = forecastId;

            elements.rampModalTitle.textContent = `Configure Ramp — ${monthKey}`;
            elements.rampModalBody.innerHTML = buildWeekCardsHtml(weeks);

            hideRampError();
            elements.rampModalOverlay.style.display = 'flex';
        } catch (err) {
            console.error('[Chat] Error opening ramp modal:', err);
        }
    }

    function buildWeekCardsHtml(weeks) {
        return weeks.map((week, idx) => {
            const label = escapeHtml(week.label || `Week ${idx + 1}`);
            const workingDays = parseInt(week.workingDays, 10) || 0;
            return `
            <div class="ramp-week-card" data-week-index="${idx}">
                <div class="ramp-week-label">${label}</div>
                <div class="ramp-week-fields">
                    <div class="ramp-field-group">
                        <label>Working Days</label>
                        <input type="number" class="form-control ramp-input-working-days"
                               value="${workingDays}" min="1" max="5" step="1">
                        <span class="ramp-field-error" style="display:none;"></span>
                    </div>
                    <div class="ramp-field-group">
                        <label>Ramp %</label>
                        <input type="number" class="form-control ramp-input-ramp-pct"
                               value="100" min="0" max="100" step="0.1">
                        <span class="ramp-field-error" style="display:none;"></span>
                    </div>
                    <div class="ramp-field-group">
                        <label>Ramp Employees</label>
                        <input type="number" class="form-control ramp-input-ramp-emp"
                               value="0" min="0" step="1">
                        <span class="ramp-field-error" style="display:none;"></span>
                    </div>
                </div>
            </div>`;
        }).join('');
    }

    function buildWeekCards(weeks) {
        elements.rampModalBody.innerHTML = buildWeekCardsHtml(weeks);
    }

    function validateRampForm() {
        const cards = elements.rampModalBody.querySelectorAll('.ramp-week-card');
        const errors = [];
        let valid = true;

        cards.forEach((card, idx) => {
            const wdInput = card.querySelector('.ramp-input-working-days');
            const pctInput = card.querySelector('.ramp-input-ramp-pct');
            const empInput = card.querySelector('.ramp-input-ramp-emp');
            const label = card.querySelector('.ramp-week-label').textContent;

            const wd = parseFloat(wdInput.value);
            const pct = parseFloat(pctInput.value);
            const emp = parseFloat(empInput.value);

            // Clear previous errors
            card.querySelectorAll('.ramp-field-error').forEach(el => {
                el.style.display = 'none';
                el.textContent = '';
            });

            if (isNaN(wd) || wd <= 0) {
                showFieldError(wdInput, 'Working days must be > 0');
                errors.push(`${label}: invalid working days`);
                valid = false;
            }
            if (isNaN(pct) || pct < 0 || pct > 100) {
                showFieldError(pctInput, 'Ramp % must be 0–100');
                errors.push(`${label}: invalid ramp %`);
                valid = false;
            }
            if (isNaN(emp) || emp < 0) {
                showFieldError(empInput, 'Must be ≥ 0');
                errors.push(`${label}: invalid ramp employees`);
                valid = false;
            } else if (!Number.isInteger(emp)) {
                showFieldError(empInput, 'Must be a whole number (no decimals)');
                errors.push(`${label}: ramp employees must be a whole number`);
                valid = false;
            }
        });


        return { valid, errors };
    }

    function showFieldError(inputEl, message) {
        const errEl = inputEl.parentElement.querySelector('.ramp-field-error');
        if (errEl) {
            errEl.textContent = message;
            errEl.style.display = 'block';
        }
    }

    function serializeRampForm() {
        const cards = elements.rampModalBody.querySelectorAll('.ramp-week-card');
        const weeks = [];

        cards.forEach((card, idx) => {
            const wdInput = card.querySelector('.ramp-input-working-days');
            const pctInput = card.querySelector('.ramp-input-ramp-pct');
            const empInput = card.querySelector('.ramp-input-ramp-emp');
            const label = card.querySelector('.ramp-week-label').textContent;
            const rawWeek = (ChatState.pendingRampWeeks || [])[idx] || {};

            weeks.push({
                label: label,
                startDate: rawWeek.startDate || '',
                endDate: rawWeek.endDate || '',
                workingDays: parseInt(wdInput.value, 10),
                rampPercent: parseFloat(pctInput.value),
                rampEmployees: parseInt(empInput.value, 10),
            });
        });

        const totalRampEmployees = weeks.reduce((sum, w) => sum + (w.rampEmployees || 0), 0);
        return { weeks, totalRampEmployees };
    }

    function handleRampModalSubmit() {
        const { valid, errors } = validateRampForm();

        if (!valid) {
            showRampError(errors.join('; '));
            return;
        }

        hideRampError();
        const ramp_submission = serializeRampForm();

        // Preserve user's entered values so "No, Edit Again" can reopen with them
        ChatState.pendingRampWeeks = ramp_submission.weeks;

        hideRampModal();

        sendWebSocketMessage({
            type: 'submit_ramp_data',
            ramp_submission: ramp_submission,
        });
    }

    function hideRampModal() {
        elements.rampModalOverlay.style.display = 'none';
        elements.rampModalBody.innerHTML = '';
        hideRampError();
    }

    function closeRampModal() {
        hideRampModal();
        ChatState.pendingRampWeeks = null;
        ChatState.pendingRampMonthKey = null;
        ChatState.pendingRampForecastId = null;
    }

    function showRampError(message) {
        elements.rampModalError.textContent = message;
        elements.rampModalError.style.display = 'block';
    }

    function hideRampError() {
        elements.rampModalError.textContent = '';
        elements.rampModalError.style.display = 'none';
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }

    function populateBreakdownModal(data) {
        const rows = (data.per_ramp || []).map(r => `
            <tr>
                <td>${escapeHtml(r.ramp_name)}</td>
                <td class="text-end ${r.fte_change >= 0 ? 'text-success' : 'text-danger'}">
                    ${r.fte_change >= 0 ? '+' : ''}${r.fte_change.toLocaleString()}
                </td>
                <td class="text-end ${r.cap_change >= 0 ? 'text-success' : 'text-danger'}">
                    ${r.cap_change >= 0 ? '+' : ''}${r.cap_change.toLocaleString(undefined, {maximumFractionDigits: 1})}
                </td>
            </tr>`).join('');

        document.getElementById('ramp-breakdown-body').innerHTML = `
            <div class="mb-3 p-2 bg-light rounded">
                <span class="me-4"><strong>Client Forecast:</strong> ${(data.forecast || 0).toLocaleString()}</span>
                <span><strong>FTE Required:</strong> ${(data.fte_required || 0).toLocaleString()}</span>
            </div>
            <table class="table table-sm table-bordered">
                <thead class="table-light">
                    <tr>
                        <th>Ramp</th>
                        <th class="text-end">FTE Available Change</th>
                        <th class="text-end">Capacity Change</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>`;
    }

    // ── Ramp WS message handlers ─────────────────────────────────────────────

    function handleRampConfirmation(data) {
        hideThinkingBubble();
        if (data.ui_component) {
            addMessageWithHTML('assistant', data.ui_component);
        } else if (data.message) {
            addMessage('assistant', data.message);
        }
        attachRampConfirmListeners();
        scrollToBottom();
    }

    function handleRampPreview(data) {
        hideThinkingBubble();
        if (data.ui_component) {
            addMessageWithHTML('assistant', data.ui_component);
        } else if (data.message) {
            addMessage('assistant', data.message);
        }
        attachRampApplyListeners();
        scrollToBottom();
    }

    function handleRampApplyResult(data) {
        hideThinkingBubble();
        if (data.ui_component) {
            addMessageWithHTML('assistant', data.ui_component);
        } else {
            addMessage('assistant', data.message || (data.success ? 'Ramp applied.' : 'Ramp apply failed.'));
        }

        if (data.success) {
            ChatState.pendingRampWeeks = null;
            ChatState.pendingRampMonthKey = null;
            ChatState.pendingRampForecastId = null;
        }
        scrollToBottom();
    }

    // ── Ramp button listener attachers ───────────────────────────────────────

    function attachRampOpenListeners() {
        const openBtns = elements.messagesArea.querySelectorAll('.ramp-open-modal-btn');
        openBtns.forEach(btn => {
            if (!btn.hasAttribute('data-listener-attached')) {
                btn.setAttribute('data-listener-attached', 'true');
                btn.addEventListener('click', function() {
                    openRampModal(this);
                });
            }
        });
    }

    function attachRampConfirmListeners() {
        const confirmBtns = elements.messagesArea.querySelectorAll('.ramp-confirm-btn');
        confirmBtns.forEach(btn => {
            if (!btn.hasAttribute('data-listener-attached')) {
                btn.setAttribute('data-listener-attached', 'true');
                btn.addEventListener('click', function() {
                    // Disable all buttons in card
                    const card = this.closest('.ramp-confirmation-card');
                    if (card) card.querySelectorAll('button').forEach(b => b.disabled = true);

                    sendWebSocketMessage({ type: 'confirm_ramp_submission' });
                });
            }
        });

        const editBtns = elements.messagesArea.querySelectorAll('.ramp-edit-btn');
        editBtns.forEach(btn => {
            if (!btn.hasAttribute('data-listener-attached')) {
                btn.setAttribute('data-listener-attached', 'true');
                btn.addEventListener('click', function() {
                    const card = this.closest('.ramp-confirmation-card');
                    if (card) card.querySelectorAll('button').forEach(b => b.disabled = true);

                    // Re-open modal with preserved state
                    if (ChatState.pendingRampWeeks) {
                        buildWeekCards(ChatState.pendingRampWeeks);
                        elements.rampModalOverlay.style.display = 'flex';
                    }
                });
            }
        });
    }

    function attachRampApplyListeners() {
        const applyBtns = elements.messagesArea.querySelectorAll('.ramp-apply-btn');
        applyBtns.forEach(btn => {
            if (!btn.hasAttribute('data-listener-attached')) {
                btn.setAttribute('data-listener-attached', 'true');
                btn.addEventListener('click', function() {
                    const card = this.closest('.ramp-preview-card');
                    if (card) card.querySelectorAll('button').forEach(b => b.disabled = true);

                    sendWebSocketMessage({ type: 'apply_ramp_calculation' });
                });
            }
        });

        const cancelBtns = elements.messagesArea.querySelectorAll('.ramp-cancel-btn');
        cancelBtns.forEach(btn => {
            if (!btn.hasAttribute('data-listener-attached')) {
                btn.setAttribute('data-listener-attached', 'true');
                btn.addEventListener('click', function() {
                    const card = this.closest('.ramp-preview-card');
                    if (card) card.querySelectorAll('button').forEach(b => b.disabled = true);

                    // Clear ramp state on cancel
                    ChatState.pendingRampWeeks = null;
                    ChatState.pendingRampMonthKey = null;
                    ChatState.pendingRampForecastId = null;

                    addMessage('assistant', 'Ramp apply cancelled.');
                });
            }
        });
    }

    // ── Bulk ramp WS message handlers ────────────────────────────────────────

    function handleBulkRampConfirmation(data) {
        if (data.ui_component) {
            addMessageWithHTML('assistant', data.ui_component);
        } else if (data.message) {
            addMessage('assistant', data.message);
        }
        attachBulkRampConfirmListeners();
        scrollToBottom();
    }

    function handleBulkRampPreview(data) {
        if (data.ui_component) {
            addMessageWithHTML('assistant', data.ui_component);
        } else if (data.message) {
            addMessage('assistant', data.message);
        }
        attachBulkRampApplyListeners();
        scrollToBottom();
    }

    function handleBulkRampApplyResult(data) {
        if (data.ui_component) {
            addMessageWithHTML('assistant', data.ui_component);
        } else {
            addMessage('assistant', data.message || (data.success ? 'Bulk ramp applied.' : 'Bulk ramp apply failed.'));
        }
        if (data.success) {
            ChatState.currentRampListData = null;
            ChatState.lastBulkRampSubmission = null;
            ChatState.bulkRampForecastId = null;
            ChatState.bulkRampMonthKey = null;
        }
        scrollToBottom();
    }

    // ── Bulk ramp button listener attachers ──────────────────────────────────

    function attachRampListShowDataListeners() {
        const showBtns = elements.messagesArea.querySelectorAll('.ramp-list-show-data-btn');
        showBtns.forEach(btn => {
            if (!btn.hasAttribute('data-listener-attached') && !btn.disabled) {
                btn.setAttribute('data-listener-attached', 'true');
                btn.addEventListener('click', function() {
                    const card = this.closest('.ramp-list-card');
                    if (!card) return;
                    const forecastId = parseInt(card.getAttribute('data-forecast-id'), 10);
                    const monthKey = card.getAttribute('data-month-key') || '';
                    let ramps = [];
                    try {
                        ramps = JSON.parse(card.getAttribute('data-ramp-list') || '[]');
                    } catch (e) {
                        console.error('[Chat] Failed to parse ramp-list data', e);
                    }
                    ChatState.currentRampListData = ramps;
                    ChatState.bulkRampForecastId = forecastId;
                    ChatState.bulkRampMonthKey = monthKey;
                    openBulkRampModal(ramps, forecastId, monthKey);
                });
            }
        });
    }

    function attachBulkRampConfirmListeners() {
        const previewBtns = elements.messagesArea.querySelectorAll('.bulk-ramp-preview-btn');
        previewBtns.forEach(btn => {
            if (!btn.hasAttribute('data-listener-attached')) {
                btn.setAttribute('data-listener-attached', 'true');
                btn.addEventListener('click', function() {
                    const card = this.closest('.bulk-ramp-confirmation-card');
                    if (card) card.querySelectorAll('button').forEach(b => b.disabled = true);
                    sendWebSocketMessage({ type: 'confirm_bulk_ramp_submission' });
                });
            }
        });

        const editBtns = elements.messagesArea.querySelectorAll('.bulk-ramp-edit-btn');
        editBtns.forEach(btn => {
            if (!btn.hasAttribute('data-listener-attached')) {
                btn.setAttribute('data-listener-attached', 'true');
                btn.addEventListener('click', function() {
                    const card = this.closest('.bulk-ramp-confirmation-card');
                    if (card) card.querySelectorAll('button').forEach(b => b.disabled = true);
                    // Reopen with last submitted values
                    const ramps = ChatState.lastBulkRampSubmission || ChatState.currentRampListData || [];
                    openBulkRampModal(ramps, ChatState.bulkRampForecastId, ChatState.bulkRampMonthKey);
                });
            }
        });
    }

    function attachBulkRampApplyListeners() {
        // View Breakdown button
        elements.messagesArea.querySelectorAll('.ramp-view-breakdown-btn').forEach(btn => {
            if (btn.hasAttribute('data-listener-attached')) return;
            btn.setAttribute('data-listener-attached', 'true');
            btn.addEventListener('click', function () {
                const raw = this.getAttribute('data-breakdown').replace(/&amp;quot;/g, '"').replace(/&quot;/g, '"');
                const data = JSON.parse(raw);
                populateBreakdownModal(data);
                document.getElementById('ramp-breakdown-modal').style.display = 'flex';
            });
        });

        const applyBtns = elements.messagesArea.querySelectorAll('.bulk-ramp-apply-btn');
        applyBtns.forEach(btn => {
            if (!btn.hasAttribute('data-listener-attached')) {
                btn.setAttribute('data-listener-attached', 'true');
                btn.addEventListener('click', function() {
                    const card = this.closest('.bulk-ramp-preview-card');
                    if (card) card.querySelectorAll('button').forEach(b => b.disabled = true);
                    sendWebSocketMessage({ type: 'apply_bulk_ramp' });
                });
            }
        });

        const cancelBtns = elements.messagesArea.querySelectorAll('.bulk-ramp-cancel-btn');
        cancelBtns.forEach(btn => {
            if (!btn.hasAttribute('data-listener-attached')) {
                btn.setAttribute('data-listener-attached', 'true');
                btn.addEventListener('click', function() {
                    const card = this.closest('.bulk-ramp-preview-card');
                    if (card) card.querySelectorAll('button').forEach(b => b.disabled = true);
                    ChatState.currentRampListData = null;
                    ChatState.lastBulkRampSubmission = null;
                    addMessage('assistant', 'Bulk ramp apply cancelled.');
                });
            }
        });
    }

    // ── Bulk ramp modal functions ─────────────────────────────────────────────

    function openBulkRampModal(ramps, forecastId, monthKey) {
        if (!elements.bulkRampModal) return;

        elements.bulkRampTitle.textContent = 'Edit Ramps — ' + (monthKey || '');
        buildBulkRampTable(ramps);
        elements.bulkRampModal.style.display = 'flex';
        hideBulkRampError();
    }

    function closeBulkRampModal() {
        if (!elements.bulkRampModal) return;
        elements.bulkRampModal.style.display = 'none';
        elements.bulkRampBody.innerHTML = '';
        hideBulkRampError();
    }

    function buildBulkRampTable(ramps) {
        if (!ramps || ramps.length === 0) {
            elements.bulkRampBody.innerHTML = '<p class="p-3 text-muted">No ramp data available.</p>';
            return;
        }

        // Collect all weeks from first ramp (weeks are the same structure across ramps)
        const allWeeks = ramps[0].weeks || [];

        // Build two-row header
        let headerRow1 = '<th style="position:sticky;left:0;z-index:4;background:#f8f9fa;min-width:120px;">Ramp</th>';
        let headerRow2 = '<th style="position:sticky;left:0;z-index:4;background:#f8f9fa;"></th>';

        allWeeks.forEach((w, idx) => {
            const label = escapeHtml(w.week_label || w.label || ('Week ' + (idx + 1)));
            const days = w.working_days !== undefined ? w.working_days : (w.workingDays || 0);
            headerRow1 += `<th colspan="2" class="text-center" style="z-index:3;">${label} (${days}d)</th>`;
            headerRow2 += '<th style="z-index:3;">Ramp&nbsp;%</th><th style="z-index:3;">Employees</th>';
        });

        // Build ramp rows — use existing values from ramps (support both API snake_case and camelCase keys)
        let bodyRows = '';
        ramps.forEach(ramp => {
            const rampName = escapeHtml(ramp.ramp_name || 'Default');
            let cells = `<td style="position:sticky;left:0;z-index:2;background:white;" class="fw-bold">${rampName}</td>`;

            const weeks = ramp.weeks || [];
            allWeeks.forEach((templateWeek, idx) => {
                const w = weeks[idx] || {};
                // Support both API shape (ramp_percent, employee_count) and form shape (rampPercent, rampEmployees)
                const rampPct = w.ramp_percent !== undefined ? w.ramp_percent : (w.rampPercent !== undefined ? w.rampPercent : 0);
                const empCount = w.employee_count !== undefined ? w.employee_count : (w.rampEmployees !== undefined ? w.rampEmployees : 0);
                cells += `<td><input type="number" class="form-control form-control-sm bulk-ramp-pct" style="min-width:70px;" step="0.1" min="0" max="100" value="${rampPct}" data-ramp="${rampName}" data-week="${idx}"></td>`;
                cells += `<td><input type="number" class="form-control form-control-sm bulk-ramp-emp" style="min-width:70px;" min="0" value="${empCount}" data-ramp="${rampName}" data-week="${idx}"></td>`;
            });

            bodyRows += `<tr data-ramp-name="${rampName}">${cells}</tr>`;
        });

        elements.bulkRampBody.innerHTML = `
            <div style="overflow-x:auto;overflow-y:auto;max-height:60vh;">
                <table class="table table-sm table-bordered ramp-bulk-edit-table mb-0">
                    <thead style="position:sticky;top:0;z-index:3;">
                        <tr>${headerRow1}</tr>
                        <tr>${headerRow2}</tr>
                    </thead>
                    <tbody>${bodyRows}</tbody>
                </table>
            </div>`;
    }

    function submitBulkRampForm() {
        const rows = elements.bulkRampBody.querySelectorAll('tr[data-ramp-name]');
        const allWeekData = [];
        const firstRamp = ChatState.currentRampListData && ChatState.currentRampListData[0];
        const templateWeeks = firstRamp ? (firstRamp.weeks || []) : [];

        const errors = [];
        const rampPayloads = [];

        rows.forEach(row => {
            const rampName = row.getAttribute('data-ramp-name');
            const pctInputs = row.querySelectorAll('.bulk-ramp-pct');
            const empInputs = row.querySelectorAll('.bulk-ramp-emp');

            const weeks = [];
            pctInputs.forEach((pctInput, i) => {
                const tw = templateWeeks[i] || {};
                const rampPct = parseFloat(pctInput.value) || 0;
                const rampEmp = parseInt(empInputs[i] ? empInputs[i].value : 0, 10) || 0;
                const workingDays = tw.working_days !== undefined ? tw.working_days : (tw.workingDays || 0);

                if (rampPct < 0 || rampPct > 100) {
                    errors.push(`Ramp "${rampName}" Week ${i+1}: Ramp % must be 0–100`);
                }
                if (rampEmp < 0) {
                    errors.push(`Ramp "${rampName}" Week ${i+1}: Employees must be >= 0`);
                }
                weeks.push({
                    label: tw.week_label || tw.label || ('Week ' + (i+1)),
                    startDate: tw.start_date || tw.startDate || '',
                    endDate: tw.end_date || tw.endDate || '',
                    workingDays: workingDays,
                    rampPercent: rampPct,
                    rampEmployees: rampEmp,
                });
            });

            const totalRampEmployees = weeks.reduce((s, w) => s + w.rampEmployees, 0);
            rampPayloads.push({ ramp_name: rampName, weeks: weeks, totalRampEmployees: totalRampEmployees });
        });

        if (errors.length > 0) {
            showBulkRampError(errors.join('; '));
            return;
        }

        hideBulkRampError();
        ChatState.lastBulkRampSubmission = rampPayloads;
        closeBulkRampModal();

        sendWebSocketMessage({
            type: 'submit_bulk_ramp_data',
            forecast_id: ChatState.bulkRampForecastId,
            month_key: ChatState.bulkRampMonthKey,
            ramps: rampPayloads,
        });
    }

    function showBulkRampError(message) {
        if (elements.bulkRampError) {
            elements.bulkRampError.textContent = message;
            elements.bulkRampError.style.display = 'block';
        }
    }

    function hideBulkRampError() {
        if (elements.bulkRampError) {
            elements.bulkRampError.textContent = '';
            elements.bulkRampError.style.display = 'none';
        }
    }

    function openModal(title, data) {
        elements.modalTitle.textContent = title;

        // Build full table (legacy)
        const tableHTML = buildFullDataTable(data);
        elements.modalBody.innerHTML = tableHTML;

        // Show modal
        elements.modalOverlay.style.display = 'flex';
    }

    function closeModal() {
        elements.modalOverlay.style.display = 'none';
        elements.modalBody.innerHTML = '';
    }

    function buildFullDataTable(data) {
        if (!data || data.length === 0) {
            return '<p class="text-muted">No data available.</p>';
        }

        // Get column headers from first row
        const headers = Object.keys(data[0]);

        let html = '<div class="table-responsive"><table class="table table-striped table-bordered">';

        // Header
        html += '<thead class="table-light"><tr>';
        headers.forEach(header => {
            html += `<th>${formatHeader(header)}</th>`;
        });
        html += '</tr></thead>';

        // Body
        html += '<tbody>';
        data.forEach(row => {
            html += '<tr>';
            headers.forEach(header => {
                const value = row[header];
                const formattedValue = formatCellValue(header, value);
                const cellClass = getCellClass(header, value);
                html += `<td class="${cellClass}">${formattedValue}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table></div>';

        return html;
    }

    function formatHeader(header) {
        // Convert snake_case or camelCase to Title Case
        return header
            .replace(/_/g, ' ')
            .replace(/([A-Z])/g, ' $1')
            .replace(/^./, str => str.toUpperCase())
            .trim();
    }

    function formatCellValue(header, value) {
        if (value === null || value === undefined) {
            return '-';
        }

        // Format numbers with commas
        if (typeof value === 'number' && !header.includes('gap')) {
            return value.toLocaleString();
        }

        // Format gap values with sign
        if (header.includes('gap') && typeof value === 'number') {
            return value >= 0 ? `+${value}` : value.toString();
        }

        return value.toString();
    }

    function getCellClass(header, value) {
        // Color code gap columns
        if (header.includes('gap') && typeof value === 'number') {
            if (value < 0) return 'text-danger';
            if (value > 0) return 'text-success';
            return 'text-muted';
        }
        return '';
    }

    // ========================================================================
    // Campaign Manager Modal
    // ========================================================================

    // ── Client-side week boundary calculator (mirrors Python calculate_weeks) ──

    function formatDateISO(d) {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
    }

    function calculateWeeksForMonth(monthKey) {
        // monthKey: "YYYY-MM"
        const parts = monthKey.split('-');
        if (parts.length !== 2) return [];
        const year  = parseInt(parts[0], 10);
        const month = parseInt(parts[1], 10);  // 1-based
        if (isNaN(year) || isNaN(month) || month < 1 || month > 12) return [];

        const ABBR = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

        const firstDay = new Date(year, month - 1, 1);
        const lastDay  = new Date(year, month, 0);   // day 0 of next month = last day of this month

        // Find Monday of the week containing firstDay  (JS: Sun=0, Mon=1, ..., Sat=6)
        let monday = new Date(firstDay);
        const dow = firstDay.getDay();
        if (dow === 6) {            // Saturday → skip to next Monday
            monday.setDate(firstDay.getDate() + 2);
        } else if (dow === 0) {     // Sunday → skip to next Monday
            monday.setDate(firstDay.getDate() + 1);
        } else {                    // Mon–Fri → back-track to Monday
            monday.setDate(firstDay.getDate() - (dow - 1));
        }

        const weeks = [];
        while (monday <= lastDay) {
            const sunday   = new Date(monday); sunday.setDate(monday.getDate() + 6);
            const wkStart  = new Date(Math.max(monday.getTime(), firstDay.getTime()));
            const wkEnd    = new Date(Math.min(sunday.getTime(),  lastDay.getTime()));

            // Count Mon–Fri working days in clipped range
            let workingDays = 0;
            const cur = new Date(wkStart);
            while (cur <= wkEnd) {
                const wd = cur.getDay();
                if (wd >= 1 && wd <= 5) workingDays++;
                cur.setDate(cur.getDate() + 1);
            }

            if (workingDays > 0) {
                // First working day of the range (for label)
                const labelDate = new Date(wkStart);
                while (labelDate.getDay() === 0 || labelDate.getDay() === 6) {
                    labelDate.setDate(labelDate.getDate() + 1);
                }
                const label = `${ABBR[month]}-${labelDate.getDate()}-${year}`;
                weeks.push({
                    label:       label,
                    startDate:   formatDateISO(wkStart),
                    endDate:     formatDateISO(wkEnd),
                    workingDays: workingDays,
                    rampPercent:    100,
                    rampEmployees:  0,
                });
            }
            monday.setDate(monday.getDate() + 7);
        }
        return weeks;
    }

    // Convert "Apr-25" → "2025-04"
    function monthLabelToKey(label) {
        const monthMap = { Jan: '01', Feb: '02', Mar: '03', Apr: '04', May: '05', Jun: '06',
                           Jul: '07', Aug: '08', Sep: '09', Oct: '10', Nov: '11', Dec: '12' };
        const parts = label.split('-');
        if (parts.length !== 2) return label;
        const mo = monthMap[parts[0]] || '01';
        return '20' + parts[1] + '-' + mo;
    }

    function attachCampaignOpenListeners() {
        elements.messagesArea.querySelectorAll('.campaign-open-manager-btn').forEach(btn => {
            if (!btn.hasAttribute('data-listener-attached')) {
                btn.setAttribute('data-listener-attached', 'true');
                btn.addEventListener('click', function() { openCampaignModal(this); });
            }
        });
    }

    function openCampaignModal(btn) {
        try {
            const monthsRaw  = JSON.parse(btn.getAttribute('data-campaign-months').replace(/&quot;/g, '"'));
            const lobs       = JSON.parse(btn.getAttribute('data-campaign-lobs').replace(/&quot;/g, '"'));
            const monthWeeks = JSON.parse(btn.getAttribute('data-campaign-month-weeks').replace(/&quot;/g, '"'));
            const reportLabel = btn.getAttribute('data-report-label') || '';

            // Backend sends {"2025-04": "Apr-25", ...}; convert values to ordered label array
            const months = Array.isArray(monthsRaw) ? monthsRaw : Object.values(monthsRaw);

            ChatState.campaignModalData   = { months, lobs, monthWeeks, reportLabel };
            ChatState.campaignStagingRows  = [];
            ChatState.campaignEditingIndex = null;

            document.getElementById('campaign-report-label').textContent = reportLabel;
            updateStagingTable();
            showCampaignView('stage');
            document.getElementById('ramp-campaign-modal').style.display = 'flex';
        } catch (err) {
            console.error('[Campaign] Error opening campaign modal:', err);
        }
    }

    function closeCampaignModal() {
        document.getElementById('ramp-campaign-modal').style.display = 'none';
        ChatState.campaignStagingRows  = [];
        ChatState.campaignModalData    = null;
        ChatState.campaignEditingIndex = null;
    }

    function showCampaignView(view) {
        ['stage', 'preview', 'result'].forEach(v => {
            const el = document.getElementById('campaign-' + v + '-view');
            if (el) el.style.display = (v === view) ? '' : 'none';
        });
    }

    function buildRowSummary(row) {
        const weeks = row.weeks || [];
        if (weeks.length === 0) return '';
        const pcts = weeks.map(w => w.rampPercent !== undefined ? w.rampPercent : (w.ramp_percent || 0));
        const emps = weeks.map(w => w.rampEmployees !== undefined ? w.rampEmployees : (w.employee_count || 0));
        const minPct = Math.min(...pcts);
        const maxPct = Math.max(...pcts);
        const maxEmp = Math.max(...emps);
        return `${weeks.length}wk · ${maxEmp}emp · ${minPct}→${maxPct}%`;
    }

    function updateStagingTable() {
        const tbody     = document.getElementById('campaign-staging-tbody');
        const summaryEl = document.getElementById('campaign-stage-summary');
        const rows      = ChatState.campaignStagingRows;

        if (!rows || rows.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted" style="padding:20px;">No ramps staged yet — click "+ Add New Ramp" to begin.</td></tr>`;
            if (summaryEl) summaryEl.textContent = '';
            return;
        }

        tbody.innerHTML = rows.map((row, idx) => `
            <tr>
                <td>${row.forecast_id}</td>
                <td>${escapeHtml(row.main_lob)}</td>
                <td>${escapeHtml(row.state)}</td>
                <td>${escapeHtml(row.case_type)}</td>
                <td>${escapeHtml(row.month_label)}</td>
                <td>${escapeHtml(row.ramp_name)}</td>
                <td style="font-size:0.85em;">${buildRowSummary(row)}</td>
                <td>
                    <button class="btn btn-sm btn-outline-secondary campaign-edit-row-btn" data-idx="${idx}">Edit</button>
                    <button class="btn btn-sm btn-outline-danger campaign-del-row-btn" data-idx="${idx}" style="margin-left:4px;">Del</button>
                </td>
            </tr>`).join('');

        tbody.querySelectorAll('.campaign-edit-row-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                openEditRampSubModal(parseInt(this.getAttribute('data-idx'), 10));
            });
        });
        tbody.querySelectorAll('.campaign-del-row-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                ChatState.campaignStagingRows.splice(parseInt(this.getAttribute('data-idx'), 10), 1);
                updateStagingTable();
            });
        });

        if (summaryEl) {
            const uniqueLobs = new Set(rows.map(r => r.forecast_id));
            summaryEl.textContent = `Total staged: ${rows.length} ramp${rows.length !== 1 ? 's' : ''} across ${uniqueLobs.size} forecast row${uniqueLobs.size !== 1 ? 's' : ''}`;
        }
    }

    // ── Add / Edit Ramp Sub-Modal ─────────────────────────────────────────────

    function openAddRampSubModal() {
        ChatState.campaignEditingIndex  = null;
        ChatState.campaignSubModalWeeks = {};
        ChatState.campaignSubActiveMonth = null;

        document.getElementById('add-sub-modal-title').textContent = 'Add New Ramp';
        document.getElementById('add-sub-row-selector').style.display  = '';
        document.getElementById('add-sub-month-selector').style.display = '';

        // Populate forecast row dropdown
        const lobs   = (ChatState.campaignModalData || {}).lobs || [];
        const select = document.getElementById('add-sub-row-select');
        select.innerHTML = '<option value="">— Select a forecast row —</option>' +
            lobs.map(lob => `<option value="${lob.forecast_id}">${escapeHtml(lob.main_lob)} | ${escapeHtml(lob.state)} | ${escapeHtml(lob.case_type)}</option>`).join('');

        // Populate month checkboxes
        const months = (ChatState.campaignModalData || {}).months || [];
        document.getElementById('add-sub-month-checks').innerHTML = months.map(m => {
            const mk = monthLabelToKey(m);
            return `<label style="cursor:pointer;user-select:none;">
                <input type="checkbox" class="campaign-month-check" value="${mk}" data-label="${escapeHtml(m)}" style="margin-right:4px;">
                ${escapeHtml(m)}</label>`;
        }).join('');
        document.getElementById('add-sub-month-checks').querySelectorAll('.campaign-month-check').forEach(cb => {
            cb.addEventListener('change', onSubModalMonthChange);
        });

        // Clear tabs & content
        document.getElementById('add-sub-month-tabs').innerHTML = '';
        document.getElementById('add-sub-weeks-content').innerHTML =
            '<p class="text-muted" style="margin-top:8px;font-size:0.9em;">Select month(s) above to configure weeks.</p>';
        document.getElementById('add-sub-ramp-name').value = '';
        document.getElementById('add-sub-confirm-btn').textContent = 'Add to Campaign →';
        clearSubModalError();

        document.getElementById('ramp-add-sub-modal').style.display = 'flex';
    }

    function openEditRampSubModal(idx) {
        const row = ChatState.campaignStagingRows[idx];
        if (!row) return;

        ChatState.campaignEditingIndex   = idx;
        ChatState.campaignSubModalWeeks  = {};
        ChatState.campaignSubModalWeeks[row.month_key] = row.weeks.map(w => ({ ...w }));
        ChatState.campaignSubActiveMonth = row.month_key;

        document.getElementById('add-sub-modal-title').textContent =
            `Edit Ramp — ${escapeHtml(row.main_lob)} | ${escapeHtml(row.state)} | ${escapeHtml(row.case_type)} — ${escapeHtml(row.month_label)}`;

        document.getElementById('add-sub-row-selector').style.display  = 'none';
        document.getElementById('add-sub-month-selector').style.display = 'none';

        // Single tab
        document.getElementById('add-sub-month-tabs').innerHTML =
            `<button class="btn btn-sm btn-primary campaign-month-tab" data-month="${row.month_key}">${escapeHtml(row.month_label)}</button>`;

        renderSubModalWeekTable(row.month_key);
        document.getElementById('add-sub-ramp-name').value = row.ramp_name;
        document.getElementById('add-sub-confirm-btn').textContent = 'Update →';
        clearSubModalError();

        document.getElementById('ramp-add-sub-modal').style.display = 'flex';
    }

    function closeAddRampSubModal() {
        document.getElementById('ramp-add-sub-modal').style.display = 'none';
        ChatState.campaignSubModalWeeks  = {};
        ChatState.campaignSubActiveMonth = null;
        ChatState.campaignEditingIndex   = null;
    }

    function clearSubModalError() {
        const err = document.getElementById('add-sub-error');
        if (err) { err.style.display = 'none'; err.textContent = ''; }
    }

    function showSubModalError(msg) {
        const err = document.getElementById('add-sub-error');
        if (err) { err.textContent = msg; err.style.display = 'block'; }
    }

    function onSubModalMonthChange() {
        // Save current tab data before rebuilding
        if (ChatState.campaignSubActiveMonth) saveSubModalCurrentTab();

        const monthWeeks = (ChatState.campaignModalData || {}).monthWeeks || {};
        const checked = Array.from(document.getElementById('add-sub-month-checks').querySelectorAll('.campaign-month-check:checked'));

        // Initialize week data for newly checked months (use server data; fall back to JS calculation)
        checked.forEach(cb => {
            const mk = cb.value;
            const existing = ChatState.campaignSubModalWeeks[mk];
            if (!existing || existing.length === 0) {
                const template = monthWeeks[mk];
                if (template && template.length > 0) {
                    ChatState.campaignSubModalWeeks[mk] = template.map(w => ({
                        ...w,
                        rampPercent: 100,
                        rampEmployees: 0,
                    }));
                } else {
                    // Fall back to client-side calculation
                    ChatState.campaignSubModalWeeks[mk] = calculateWeeksForMonth(mk);
                }
            }
        });

        // Remove unchecked months
        Object.keys(ChatState.campaignSubModalWeeks).forEach(mk => {
            if (!checked.find(cb => cb.value === mk)) {
                delete ChatState.campaignSubModalWeeks[mk];
            }
        });

        if (checked.length === 0) {
            document.getElementById('add-sub-month-tabs').innerHTML = '';
            document.getElementById('add-sub-weeks-content').innerHTML =
                '<p class="text-muted" style="margin-top:8px;font-size:0.9em;">Select month(s) above to configure weeks.</p>';
            ChatState.campaignSubActiveMonth = null;
            return;
        }

        // Keep active month or default to first
        if (!ChatState.campaignSubModalWeeks[ChatState.campaignSubActiveMonth]) {
            ChatState.campaignSubActiveMonth = checked[0].value;
        }

        rebuildSubModalTabs(checked);
        renderSubModalWeekTable(ChatState.campaignSubActiveMonth);
    }

    function rebuildSubModalTabs(checkedCbs) {
        const tabContainer = document.getElementById('add-sub-month-tabs');
        tabContainer.innerHTML = checkedCbs.map(cb => {
            const isActive = cb.value === ChatState.campaignSubActiveMonth;
            return `<button class="btn btn-sm ${isActive ? 'btn-primary' : 'btn-outline-secondary'} campaign-month-tab"
                            data-month="${cb.value}" data-label="${escapeHtml(cb.getAttribute('data-label'))}">
                ${escapeHtml(cb.getAttribute('data-label'))}</button>`;
        }).join('');

        tabContainer.querySelectorAll('.campaign-month-tab').forEach(btn => {
            btn.addEventListener('click', function() {
                saveSubModalCurrentTab();
                ChatState.campaignSubActiveMonth = this.getAttribute('data-month');
                tabContainer.querySelectorAll('.campaign-month-tab').forEach(b => {
                    b.className = 'btn btn-sm ' + (b.getAttribute('data-month') === ChatState.campaignSubActiveMonth ? 'btn-primary' : 'btn-outline-secondary') + ' campaign-month-tab';
                });
                renderSubModalWeekTable(ChatState.campaignSubActiveMonth);
            });
        });
    }

    function saveSubModalCurrentTab() {
        const mk = ChatState.campaignSubActiveMonth;
        if (!mk || !ChatState.campaignSubModalWeeks[mk]) return;

        document.getElementById('add-sub-weeks-content').querySelectorAll('.sub-week-row').forEach((row, idx) => {
            const pctInput = row.querySelector('.sub-week-pct');
            const empInput = row.querySelector('.sub-week-emp');
            if (ChatState.campaignSubModalWeeks[mk][idx]) {
                ChatState.campaignSubModalWeeks[mk][idx].rampPercent   = parseFloat(pctInput ? pctInput.value : 100) || 0;
                ChatState.campaignSubModalWeeks[mk][idx].rampEmployees = parseInt(empInput ? empInput.value : 0, 10) || 0;
            }
        });
    }

    function renderSubModalWeekTable(monthKey) {
        const weeks   = ChatState.campaignSubModalWeeks[monthKey] || [];
        const content = document.getElementById('add-sub-weeks-content');

        if (weeks.length === 0) {
            content.innerHTML = '<p class="text-muted">No week data for this month.</p>';
            return;
        }

        content.innerHTML = `
            <div style="display:flex;gap:12px;align-items:center;margin-bottom:8px;padding:8px;background:#f8f9fa;border-radius:4px;flex-wrap:wrap;">
                <span style="font-size:0.85em;font-weight:600;">Bulk update:</span>
                Ramp % all weeks <input type="number" id="sub-bulk-pct" class="form-control form-control-sm" style="width:70px;display:inline-block;" min="0" max="100" placeholder="0-100">
                <button class="btn btn-sm btn-outline-secondary" id="sub-bulk-pct-apply">Apply</button>
                &nbsp; Employees all weeks <input type="number" id="sub-bulk-emp" class="form-control form-control-sm" style="width:70px;display:inline-block;" min="0" placeholder="0">
                <button class="btn btn-sm btn-outline-secondary" id="sub-bulk-emp-apply">Apply</button>
            </div>
            <table class="table table-sm table-bordered mb-0">
                <thead class="thead-light">
                    <tr><th>Week</th><th>Date Range</th><th>Working Days</th><th>Ramp %</th><th>Employees</th></tr>
                </thead>
                <tbody>
                    ${weeks.map((w, idx) => {
                        const label     = escapeHtml(w.label || ('Week ' + (idx + 1)));
                        const dateRange = w.startDate ? `${w.startDate} – ${w.endDate}` : '';
                        const days      = w.workingDays !== undefined ? w.workingDays : (w.working_days || 0);
                        const pct       = w.rampPercent !== undefined ? w.rampPercent : (w.ramp_percent || 100);
                        const emp       = w.rampEmployees !== undefined ? w.rampEmployees : (w.employee_count || 0);
                        return `<tr class="sub-week-row">
                            <td>${label}</td>
                            <td style="font-size:0.85em;">${dateRange}</td>
                            <td class="text-center">${days}</td>
                            <td><input type="number" class="form-control form-control-sm sub-week-pct" style="width:80px;" min="0" max="100" step="0.1" value="${pct}" data-idx="${idx}"></td>
                            <td><input type="number" class="form-control form-control-sm sub-week-emp" style="width:80px;" min="0" value="${emp}" data-idx="${idx}"></td>
                        </tr>`;
                    }).join('')}
                </tbody>
            </table>`;

        document.getElementById('sub-bulk-pct-apply').addEventListener('click', function() {
            const val = parseFloat(document.getElementById('sub-bulk-pct').value);
            if (!isNaN(val)) content.querySelectorAll('.sub-week-pct').forEach(inp => inp.value = val);
        });
        document.getElementById('sub-bulk-emp-apply').addEventListener('click', function() {
            const val = parseInt(document.getElementById('sub-bulk-emp').value, 10);
            if (!isNaN(val)) content.querySelectorAll('.sub-week-emp').forEach(inp => inp.value = val);
        });
    }

    function handleAddSubConfirm() {
        clearSubModalError();

        // Save current tab input values
        if (ChatState.campaignSubActiveMonth) saveSubModalCurrentTab();

        const isEdit   = ChatState.campaignEditingIndex !== null;
        const rampName = document.getElementById('add-sub-ramp-name').value.trim() || 'Default';

        if (isEdit) {
            const idx = ChatState.campaignEditingIndex;
            const row = ChatState.campaignStagingRows[idx];
            const weeks = ChatState.campaignSubModalWeeks[row.month_key] || [];
            if (weeks.length === 0) { showSubModalError('No week data found.'); return; }
            ChatState.campaignStagingRows[idx] = { ...row, ramp_name: rampName, weeks: weeks.map(w => ({ ...w })) };
        } else {
            const forecastId = parseInt(document.getElementById('add-sub-row-select').value, 10);
            if (!forecastId) { showSubModalError('Please select a forecast row.'); return; }

            const selectedMonths = Object.keys(ChatState.campaignSubModalWeeks);
            if (selectedMonths.length === 0) { showSubModalError('Please select at least one forecast month.'); return; }

            const lobs    = (ChatState.campaignModalData || {}).lobs || [];
            const lobInfo = lobs.find(l => l.forecast_id === forecastId);
            if (!lobInfo) { showSubModalError('Selected forecast row not found.'); return; }

            // Build month → label map
            const monthLabelMap = {};
            ((ChatState.campaignModalData || {}).months || []).forEach(m => {
                monthLabelMap[monthLabelToKey(m)] = m;
            });

            selectedMonths.forEach(mk => {
                const weeks = ChatState.campaignSubModalWeeks[mk] || [];
                ChatState.campaignStagingRows.push({
                    forecast_id: lobInfo.forecast_id,
                    main_lob:    lobInfo.main_lob,
                    state:       lobInfo.state,
                    case_type:   lobInfo.case_type,
                    month_key:   mk,
                    month_label: monthLabelMap[mk] || mk,
                    ramp_name:   rampName,
                    weeks:       weeks.map(w => ({ ...w })),
                });
            });
        }

        closeAddRampSubModal();
        updateStagingTable();
    }

    // ── Campaign WS flow ──────────────────────────────────────────────────────

    function submitCampaign() {
        const rows = ChatState.campaignStagingRows;
        if (!rows || rows.length === 0) {
            const errEl = document.getElementById('campaign-stage-error');
            errEl.textContent = 'No ramps staged. Add at least one ramp before submitting.';
            errEl.style.display = 'block';
            return;
        }
        document.getElementById('campaign-stage-error').style.display = 'none';
        document.getElementById('campaign-submit-all-btn').disabled = true;
        showThinkingBubble();
        sendWebSocketMessage({ type: 'submit_ramp_campaign', campaign_rows: rows });
    }

    function handleCampaignPreview(data) {
        hideThinkingBubble();
        const submitBtn = document.getElementById('campaign-submit-all-btn');
        if (submitBtn) submitBtn.disabled = false;

        if (!data.success) {
            const errEl = document.getElementById('campaign-stage-error');
            if (errEl) { errEl.textContent = data.message || 'Preview failed.'; errEl.style.display = 'block'; }
            return;
        }

        const previewRows = data.preview_rows || [];
        const totalFte    = data.total_fte_delta || 0;
        const totalCap    = data.total_cap_delta || 0;

        document.getElementById('campaign-preview-tbody').innerHTML = previewRows.map(row => {
            const fteDelta = row.fte_delta;
            const capDelta = row.cap_delta;
            const fteStr = (typeof fteDelta === 'number') ? (fteDelta >= 0 ? '+' + fteDelta : '' + fteDelta) : '—';
            const capStr = (typeof capDelta === 'number') ? (capDelta >= 0 ? '+' + capDelta.toLocaleString() : capDelta.toLocaleString()) : '—';
            const errClass = row.error ? 'text-danger' : '';
            const status   = row.error ? 'Error: ' + escapeHtml(row.error) : 'OK';
            return `<tr class="${errClass}">
                <td>${row.forecast_id}</td>
                <td>${escapeHtml(row.main_lob || '')} / ${escapeHtml(row.case_type || '')}</td>
                <td>${escapeHtml(row.month_label || row.month_key || '')}</td>
                <td class="text-end">${fteStr}</td>
                <td class="text-end">${capStr}</td>
                <td>${status}</td>
            </tr>`;
        }).join('');

        document.getElementById('campaign-preview-summary').textContent = `${previewRows.length} ramp configuration${previewRows.length !== 1 ? 's' : ''} ready to apply`;
        document.getElementById('campaign-preview-totals').innerHTML =
            `Total &Delta; FTE: <span class="${totalFte >= 0 ? 'text-success' : 'text-danger'}">${totalFte >= 0 ? '+' : ''}${totalFte}</span>` +
            `&nbsp;&nbsp; Total &Delta; Capacity: <span class="${totalCap >= 0 ? 'text-success' : 'text-danger'}">${totalCap >= 0 ? '+' : ''}${totalCap.toLocaleString()}</span>`;
        document.getElementById('campaign-preview-error').style.display = 'none';
        document.getElementById('campaign-confirm-apply-btn').disabled = false;
        showCampaignView('preview');
    }

    function applyCampaign() {
        document.getElementById('campaign-confirm-apply-btn').disabled = true;
        showThinkingBubble();
        sendWebSocketMessage({ type: 'apply_ramp_campaign' });
    }

    function handleCampaignApplyResult(data) {
        hideThinkingBubble();
        const applyBtn = document.getElementById('campaign-confirm-apply-btn');
        if (applyBtn) applyBtn.disabled = false;

        const applied = data.applied || [];
        const failed  = data.failed  || [];
        const total   = applied.length + failed.length;

        const allResults = [
            ...applied.map(r => ({ ...r, status: 'applied' })),
            ...failed.map(r => ({ ...r, status:  'failed'  })),
        ];

        document.getElementById('campaign-result-tbody').innerHTML = allResults.map(row => {
            const statusHtml = row.status === 'applied'
                ? '<span class="text-success">&#10003; Applied</span>'
                : `<span class="text-danger">&#10007; ${escapeHtml(row.error || 'Failed')}</span>`;
            return `<tr>
                <td>${row.forecast_id}</td>
                <td>${escapeHtml(row.main_lob || '')} / ${escapeHtml(row.case_type || '')}</td>
                <td>${escapeHtml(row.month_label || row.month_key || '')}</td>
                <td>${statusHtml}</td>
            </tr>`;
        }).join('');

        document.getElementById('campaign-result-summary').textContent =
            `${total} submitted — ✓ Applied: ${applied.length}   ✗ Failed: ${failed.length}`;

        // Clear staging after apply
        ChatState.campaignStagingRows = [];
        showCampaignView('result');
    }

    // ========================================================================
    // Event Listeners
    // ========================================================================
    function attachEventListeners() {
        // Toggle chat
        elements.toggleBtn.addEventListener('click', toggleChat);
        elements.minimizeBtn.addEventListener('click', toggleChat);

        // New chat
        elements.newChatBtn.addEventListener('click', startNewChat);

        // Send message
        elements.sendBtn.addEventListener('click', sendMessage);

        // Enter to send, Shift+Enter for new line
        elements.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Auto-resize textarea
        elements.input.addEventListener('input', () => {
            elements.input.style.height = 'auto';
            elements.input.style.height = elements.input.scrollHeight + 'px';
        });

        // Modal close
        elements.modalCloseBtn.addEventListener('click', closeModal);
        elements.modalCloseFooterBtn.addEventListener('click', closeModal);

        // Close modal on overlay click
        elements.modalOverlay.addEventListener('click', (e) => {
            if (e.target === elements.modalOverlay) {
                closeModal();
            }
        });

        // Ramp modal
        elements.rampModalCloseBtn.addEventListener('click', closeRampModal);
        elements.rampModalCancelBtn.addEventListener('click', closeRampModal);
        elements.rampModalSubmitBtn.addEventListener('click', handleRampModalSubmit);

        elements.rampModalOverlay.addEventListener('click', (e) => {
            if (e.target === elements.rampModalOverlay) {
                closeRampModal();
            }
        });

        // Bulk ramp modal
        if (elements.bulkRampCloseBtn) {
            elements.bulkRampCloseBtn.addEventListener('click', closeBulkRampModal);
        }
        if (elements.bulkRampCancelBtn) {
            elements.bulkRampCancelBtn.addEventListener('click', closeBulkRampModal);
        }
        if (elements.bulkRampSubmitBtn) {
            elements.bulkRampSubmitBtn.addEventListener('click', submitBulkRampForm);
        }
        if (elements.bulkRampModal) {
            elements.bulkRampModal.addEventListener('click', (e) => {
                if (e.target === elements.bulkRampModal) {
                    closeBulkRampModal();
                }
            });
        }

        // Campaign Manager modal
        const campaignModal = document.getElementById('ramp-campaign-modal');
        ['campaign-modal-close-btn', 'campaign-preview-close-btn', 'campaign-result-close-btn', 'campaign-result-done-btn'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('click', closeCampaignModal);
        });
        if (campaignModal) {
            campaignModal.addEventListener('click', e => {
                if (e.target === campaignModal) closeCampaignModal();
            });
        }
        const addRampBtn = document.getElementById('campaign-add-ramp-btn');
        if (addRampBtn) addRampBtn.addEventListener('click', openAddRampSubModal);
        const submitAllBtn = document.getElementById('campaign-submit-all-btn');
        if (submitAllBtn) submitAllBtn.addEventListener('click', submitCampaign);
        const backToStageBtn = document.getElementById('campaign-back-to-stage-btn');
        if (backToStageBtn) backToStageBtn.addEventListener('click', () => showCampaignView('stage'));
        const confirmApplyBtn = document.getElementById('campaign-confirm-apply-btn');
        if (confirmApplyBtn) confirmApplyBtn.addEventListener('click', applyCampaign);

        // Add/Edit Ramp Sub-Modal
        const addSubModal = document.getElementById('ramp-add-sub-modal');
        const addSubCloseBtn  = document.getElementById('add-sub-modal-close-btn');
        const addSubCancelBtn = document.getElementById('add-sub-cancel-btn');
        const addSubConfirmBtn = document.getElementById('add-sub-confirm-btn');
        if (addSubCloseBtn)  addSubCloseBtn.addEventListener('click', closeAddRampSubModal);
        if (addSubCancelBtn) addSubCancelBtn.addEventListener('click', closeAddRampSubModal);
        if (addSubConfirmBtn) addSubConfirmBtn.addEventListener('click', handleAddSubConfirm);
        if (addSubModal) {
            addSubModal.addEventListener('click', e => {
                if (e.target === addSubModal) closeAddRampSubModal();
            });
        }

        // Breakdown modal close
        const breakdownModal = document.getElementById('ramp-breakdown-modal');
        const breakdownCloseBtn = document.getElementById('ramp-breakdown-close-btn');
        if (breakdownCloseBtn) {
            breakdownCloseBtn.addEventListener('click', function () {
                breakdownModal.style.display = 'none';
            });
        }
        if (breakdownModal) {
            breakdownModal.addEventListener('click', (e) => {
                if (e.target === breakdownModal) {
                    breakdownModal.style.display = 'none';
                }
            });
        }
    }

    // ========================================================================
    // Initialization
    // ========================================================================
    function init() {
        console.log('[Chat] Initializing chat widget...');

        initElements();
        attachEventListeners();
        connectWebSocket();

        console.log('[Chat] Chat widget initialized');
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
