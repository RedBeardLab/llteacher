/**
 * Conversation Detail Page Initialization
 * Coordinates the real-time chat and R execution components
 */
document.addEventListener('DOMContentLoaded', function() {
    // Get conversation ID from the template
    const conversationId = window.conversationConfig?.conversationId;
    
    if (!conversationId) {
        console.error('Conversation ID not found. Make sure conversationConfig is set.');
        return;
    }
    
    // Initialize global instances
    window.webRInstance = null;
    window.rExecutionManager = null;
    window.chatClient = null;
    
    // Initialize R execution manager
    window.rExecutionManager = new RExecutionManager();
    
    // Start WebR initialization in background
    window.rExecutionManager.initialize().catch(error => {
        console.error('Failed to initialize WebR:', error);
    });
    
    // Initialize real-time chat client
    window.chatClient = new RealTimeChatClient(conversationId);
    
    console.log('Conversation detail page initialized successfully');
});
