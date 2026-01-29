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
    };

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
        };
    }

    // ========================================================================
    // WebSocket Connection
    // ========================================================================
    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat/`;

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
            elements.typingIndicator.style.display = 'flex';
        } else {
            elements.typingIndicator.style.display = 'none';
        }
    }

    function handleAssistantResponse(data) {
        // Inject UI component with confirmation
        addMessageWithHTML('assistant', data.ui_component);

        // Store pending confirmation data
        ChatState.pendingConfirmations.set(data.category, {
            category: data.category,
            parameters: data.metadata || {},
            messageId: data.message_id
        });

        // Attach event listeners to buttons
        attachConfirmationListeners();
    }

    function handleToolResult(data) {
        if (data.success) {
            // Inject result UI (table, etc.)
            addMessageWithHTML('assistant', data.ui_component);

            // Attach event listeners for "View Full Data" buttons
            attachViewFullDataListeners();
        } else {
            addMessage('assistant', data.message || 'Failed to execute action.');
        }
    }

    function handleRejectionResponse(data) {
        addMessage('assistant', data.message);
    }

    function handleErrorMessage(data) {
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
        // Display preview card with confirm/reject buttons
        addMessageWithHTML('assistant', data.ui_component);
        attachCphConfirmListeners();
        scrollToBottom();
    }

    function handleCphUpdateResult(data) {
        if (data.success) {
            addMessageWithHTML('assistant', data.ui_component || data.message);
        } else {
            addMessage('assistant', data.message || 'Failed to update CPH.');
        }
        scrollToBottom();
    }

    function handleFteDetails(data) {
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

            // Show processing message
            addMessage('assistant', 'Processing CPH update...');
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
