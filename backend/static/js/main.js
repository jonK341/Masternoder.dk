// Chat Module JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const messagesContainer = document.getElementById('messages-container');
    
    if (!messageInput || !sendButton || !messagesContainer) {
        console.warn('Chat elements not found');
        return;
    }
    
    function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;
        
        // Fire custom event for chat points system
        document.dispatchEvent(new CustomEvent('chatMessageSent', {
            detail: { message: message, text: message }
        }));
        
        // Add message to chat (placeholder - implement real-time chat later)
        addMessage('You', message, true);
        messageInput.value = '';
    }
    
    function addMessage(author, content, own = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${own ? 'own' : ''}`;
        
        const now = new Date();
        const timeString = now.toLocaleTimeString();
        
        messageDiv.innerHTML = `
            <div class="message-header">
                <span class="message-author">${author}</span>
                <span class="message-time">${timeString}</span>
            </div>
            <div class="message-content">${escapeHtml(content)}</div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});

