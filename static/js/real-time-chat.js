/**
 * Real-time Chat Client for LLTeacher Conversations
 * Handles streaming chat functionality with AI tutors
 */
class RealTimeChatClient {
    constructor(conversationId, csrfToken) {
        this.conversationId = conversationId;
        this.csrfToken = csrfToken;
        this.eventSource = null;
        this.isStreaming = false;
        this.currentStreamingMessage = null;
        
        this.initializeElements();
        this.bindEvents();
    }
    
    initializeElements() {
        this.form = document.getElementById('message-form');
        this.textarea = document.getElementById('content');
        this.sendButton = this.form.querySelector('button[type="submit"]');
        this.messageTypeRadios = this.form.querySelectorAll('input[name="message_type"]');
        this.conversationContainer = document.querySelector('.conversation-container');
        
        // Create typing indicator
        this.typingIndicator = document.createElement('div');
        this.typingIndicator.className = 'typing-indicator';
        this.typingIndicator.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> AI is thinking...';
        this.conversationContainer.appendChild(this.typingIndicator);
    }
    
    bindEvents() {
        // Override form submission
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });
        
        // Handle Enter key for sending messages
        this.textarea.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                if (e.shiftKey) {
                    // Shift+Enter: Allow new line (default behavior)
                    return;
                } else {
                    // Enter: Send message
                    e.preventDefault();
                    this.sendMessage();
                }
            }
        });
        
        // Auto-resize textarea
        this.textarea.addEventListener('input', () => {
            this.textarea.style.height = 'auto';
            this.textarea.style.height = this.textarea.scrollHeight + 'px';
        });
    }
    
    async sendMessage() {
        const content = this.textarea.value.trim();
        const messageType = this.getSelectedMessageType();
        
        if (!content || this.isStreaming) {
            return;
        }
        
        // Disable form and show loading state
        this.setLoadingState(true);
        
        try {
            // Start streaming connection
            await this.startStreaming(content, messageType);
            
            // Clear form
            this.textarea.value = '';
            this.textarea.style.height = 'auto';
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.showError('Failed to send message. Please try again.');
            this.setLoadingState(false);
        }
    }
    
    async startStreaming(content, messageType) {
        return new Promise((resolve, reject) => {
            this.isStreaming = true;
            this.showTypingIndicator(true);
            
            // Create EventSource for streaming
            const streamUrl = `/conversations/api/${this.conversationId}/stream/`;
            
            // Use fetch to POST data and get streaming response
            fetch(streamUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    content: content,
                    message_type: messageType
                })
            }).then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                
                const processStream = () => {
                    reader.read().then(({ done, value }) => {
                        if (done) {
                            this.handleStreamComplete();
                            resolve();
                            return;
                        }
                        
                        const chunk = decoder.decode(value);
                        const lines = chunk.split('\n');
                        
                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                try {
                                    const data = JSON.parse(line.slice(6));
                                    this.handleStreamEvent(data);
                                } catch (e) {
                                    console.error('Error parsing SSE data:', e);
                                }
                            }
                        }
                        
                        processStream();
                    }).catch(reject);
                };
                
                processStream();
            }).catch(reject);
        });
    }
    
    handleStreamEvent(data) {
        switch (data.type) {
            case 'user_message':
                this.addUserMessage(data.content, data.message_id, data.message_type || 'student');
                break;
                
            case 'ai_message_start':
                this.showTypingIndicator(false);
                this.startAIMessage(data.message_id);
                break;
                
            case 'ai_token':
                this.appendAIToken(data.token, data.message_id);
                break;
                
            case 'ai_message_complete':
                this.completeAIMessage(data.message_id, data.final_content);
                break;
                
            case 'error':
                this.showError(data.message);
                this.handleStreamComplete();
                break;
        }
    }
    
    addUserMessage(content, messageId, messageType = 'student') {
        let messageContentHtml;
        
        if (messageType === 'code') {
            // Create R code message with run button
            messageContentHtml = `
                <div class="r-code-container">
                    <div class="r-code-header">
                        <span class="r-code-label">
                            <i class="bi bi-code-slash"></i>
                            R Code
                        </span>
                        <button class="btn btn-sm btn-outline-primary r-run-button" 
                                data-message-id="${messageId}" 
                                ${window.rExecutionManager && window.rExecutionManager.isInitialized ? '' : 'disabled'}>
                            ${window.rExecutionManager && window.rExecutionManager.isInitialized ? 
                              '<i class="bi bi-play-fill"></i> Run Code' : 
                              '<i class="bi bi-hourglass-split"></i> Initializing...'}
                        </button>
                    </div>
                    <pre><code class="language-r">${this.escapeHtml(content)}</code></pre>
                    <div class="r-execution-output" id="r-output-${messageId}"></div>
                </div>
            `;
        } else {
            // Regular message
            messageContentHtml = `<md-block untrusted>${this.escapeHtml(content)}</md-block>`;
        }
        
        const messageHtml = `
            <div class="message-container message-chat mb-3" data-message-id="${messageId}">
                <div class="message-header">
                    <span class="badge bg-primary">Student</span>
                    <small class="text-muted">${this.formatTimestamp(new Date())}</small>
                </div>
                <div class="message-content p-3 rounded">
                    ${messageContentHtml}
                </div>
            </div>
        `;
        
        this.typingIndicator.insertAdjacentHTML('beforebegin', messageHtml);
        
        // If it's R code, bind the run button
        if (messageType === 'code') {
            this.bindRCodeButton(messageId);
        }
        
        this.scrollToBottom();
    }
    
    startAIMessage(messageId) {
        const messageHtml = `
            <div class="message-container message-ai ai-message-streaming mb-3" data-message-id="${messageId}">
                <div class="message-header">
                    <span class="badge bg-success">AI Tutor</span>
                    <small class="text-muted">${this.formatTimestamp(new Date())}</small>
                </div>
                <div class="message-content p-3 rounded">
                    <p><span class="streaming-cursor"></span></p>
                </div>
            </div>
        `;
        
        this.typingIndicator.insertAdjacentHTML('beforebegin', messageHtml);
        this.currentStreamingMessage = document.querySelector(`[data-message-id="${messageId}"]`);
        this.scrollToBottom();
    }
    
    appendAIToken(token, messageId) {
        if (this.currentStreamingMessage) {
            const contentP = this.currentStreamingMessage.querySelector('.message-content p');
            const cursor = contentP.querySelector('.streaming-cursor');
            
            // Insert token before cursor
            const tokenSpan = document.createElement('span');
            tokenSpan.textContent = token;
            cursor.parentNode.insertBefore(tokenSpan, cursor);
            
            this.scrollToBottom();
        }
    }
    
    completeAIMessage(messageId, finalContent) {
        if (this.currentStreamingMessage) {
            // Remove streaming class and cursor
            this.currentStreamingMessage.classList.remove('ai-message-streaming');
            const messageContent = this.currentStreamingMessage.querySelector('.message-content');
            
            // Replace the streaming content with md-block
            messageContent.innerHTML = `<md-block untrusted>${this.escapeHtml(finalContent)}</md-block>`;
            
            this.currentStreamingMessage = null;
        }
    }
    
    handleStreamComplete() {
        this.isStreaming = false;
        this.showTypingIndicator(false);
        this.setLoadingState(false);
        this.currentStreamingMessage = null;
    }
    
    showTypingIndicator(show) {
        if (show) {
            this.typingIndicator.classList.add('show');
        } else {
            this.typingIndicator.classList.remove('show');
        }
        this.scrollToBottom();
    }
    
    getSelectedMessageType() {
        for (const radio of this.messageTypeRadios) {
            if (radio.checked) {
                return radio.value;
            }
        }
        return 'student'; // Default fallback
    }
    
    setLoadingState(loading) {
        this.sendButton.disabled = loading;
        this.textarea.disabled = loading;
        
        // Disable/enable radio buttons
        this.messageTypeRadios.forEach(radio => {
            radio.disabled = loading;
        });
        
        if (loading) {
            this.sendButton.classList.add('send-button-loading');
            this.sendButton.innerHTML = '<i class="bi bi-hourglass-split"></i> Sending...';
        } else {
            this.sendButton.classList.remove('send-button-loading');
            this.sendButton.innerHTML = '<i class="bi bi-send"></i> Send Message';
        }
    }
    
    showError(message) {
        const errorHtml = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="fas fa-exclamation-triangle"></i> ${this.escapeHtml(message)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        this.form.insertAdjacentHTML('beforebegin', errorHtml);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const alert = this.form.previousElementSibling;
            if (alert && alert.classList.contains('alert')) {
                alert.remove();
            }
        }, 5000);
    }
    
    bindRCodeButton(messageId) {
        const button = document.querySelector(`[data-message-id="${messageId}"] .r-run-button`);
        if (button && window.rExecutionManager) {
            // Use the execution manager's binding system for consistency
            if (!button.hasAttribute('data-handler-bound')) {
                window.rExecutionManager.bindButtonClickHandler(button, messageId);
                button.setAttribute('data-handler-bound', 'true');
            }
        }
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.conversationContainer.scrollTop = this.conversationContainer.scrollHeight;
        }, 10);
    }
    
    formatTimestamp(date) {
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
}

// Export for use in other modules
window.RealTimeChatClient = RealTimeChatClient;
