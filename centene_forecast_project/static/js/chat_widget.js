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

        // Send to WebSocket
        sendWebSocketMessage({
            type: 'user_message',
            message: text
        });

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
            btn.addEventListener('click', handleViewFullData);
        });
    }

    function handleViewFullData(event) {
        const btn = event.currentTarget;
        const fullDataJson = btn.getAttribute('data-full-data');

        try {
            const data = JSON.parse(fullDataJson);
            openModal('Full Data View', data);
        } catch (error) {
            console.error('[Chat] Error parsing full data:', error);
        }
    }

    function openModal(title, data) {
        elements.modalTitle.textContent = title;

        // Build full table
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
