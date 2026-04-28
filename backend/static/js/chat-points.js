/**
 * Chat Points System Integration
 * Awards points when users send messages in chat
 */

class ChatPointsManager {
    constructor() {
        this.userId = this.getUserId();
        this.initializeChatPoints();
    }
    
    getUserId() {
        // Get user ID from session or generate
        try {
            const stored = localStorage.getItem('user_id');
            if (stored) return stored;
            
            const userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            localStorage.setItem('user_id', userId);
            return userId;
        } catch (e) {
            return 'user_anonymous';
        }
    }
    
    async initializeChatPoints() {
        // Load chat points on page load
        try {
            const response = await fetch('/vidgenerator/api/points/chat');
            if (response.ok) {
                const data = await response.json();
                this.displayChatPoints(data);
            }
        } catch (error) {
            console.error('[ChatPoints] Error loading chat points:', error);
        }
    }
    
    async awardPointsForMessage(messageText) {
        """Award points when user sends a message"""
        if (!messageText || messageText.trim().length === 0) {
            return;
        }
        
        try {
            const response = await fetch('/vidgenerator/api/points/chat/award', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action_type: 'send_message',
                    message_length: messageText.length,
                    metadata: {
                        timestamp: new Date().toISOString()
                    }
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.points_awarded > 0) {
                    this.showPointsNotification(data);
                    this.updateChatPointsDisplay(data.total_chat_points);
                }
            }
        } catch (error) {
            console.error('[ChatPoints] Error awarding points:', error);
        }
    }
    
    showPointsNotification(data) {
        /** Show notification when points are awarded */
        const notification = document.createElement('div');
        notification.className = 'chat-points-notification';
        notification.innerHTML = `
            <div class="points-badge">
                <span class="points-icon">🎯</span>
                <span class="points-amount">+${data.points_awarded}</span>
                <span class="points-label">Chat Points</span>
            </div>
            ${data.bonuses && data.bonuses.length > 0 ? `
                <div class="points-bonuses">
                    ${data.bonuses.map(b => `<span class="bonus">${b.type}: +${b.points}</span>`).join('')}
                </div>
            ` : ''}
        `;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => notification.classList.add('show'), 10);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    displayChatPoints(data) {
        /** Display chat points in UI */
        const pointsDisplay = document.getElementById('chat-points-display');
        if (pointsDisplay) {
            pointsDisplay.innerHTML = `
                <div class="chat-points-info">
                    <span class="points-total">${data.total_chat_points || 0}</span>
                    <span class="points-label">Chat Points</span>
                    ${data.current_streak > 0 ? `<span class="streak">🔥 ${data.current_streak} day streak</span>` : ''}
                </div>
            `;
        }
    }
    
    updateChatPointsDisplay(totalPoints) {
        /** Update chat points display */
        const pointsDisplay = document.getElementById('chat-points-display');
        if (pointsDisplay) {
            const totalSpan = pointsDisplay.querySelector('.points-total');
            if (totalSpan) {
                totalSpan.textContent = totalPoints;
            }
        }
    }
}

// Initialize chat points manager
let chatPointsManager = null;

document.addEventListener('DOMContentLoaded', () => {
    chatPointsManager = new ChatPointsManager();
    
    // Hook into chat message sending - multiple methods
    const hookIntoChatSending = () => {
        // Method 1: Form submit
        const chatForm = document.getElementById('chat-form') || 
                        document.querySelector('form[action*="chat"]') ||
                        document.querySelector('.chat-form') ||
                        document.querySelector('form');
        
        const messageInput = document.getElementById('message-input') || 
                            document.getElementById('message') ||
                            document.querySelector('input[name="message"]') || 
                            document.querySelector('textarea[name="message"]') ||
                            document.querySelector('.message-input') ||
                            document.querySelector('textarea');
        
        if (chatForm && messageInput) {
            chatForm.addEventListener('submit', (e) => {
                const messageText = messageInput.value;
                if (messageText && messageText.trim() && chatPointsManager) {
                    // Award points after a short delay to ensure message is sent
                    setTimeout(() => {
                        chatPointsManager.awardPointsForMessage(messageText);
                    }, 500);
                }
            });
        }
        
        // Method 2: Send buttons
        const sendButtons = document.querySelectorAll(
            '[data-action="send-message"], ' +
            '.send-message-btn, ' +
            'button[type="submit"], ' +
            '.send-btn, ' +
            '#send-btn'
        );
        
        sendButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const messageText = messageInput?.value;
                if (messageText && messageText.trim() && chatPointsManager) {
                    setTimeout(() => {
                        chatPointsManager.awardPointsForMessage(messageText);
                    }, 500);
                }
            });
        });
        
        // Method 3: Enter key in message input
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    const messageText = messageInput.value;
                    if (messageText && messageText.trim() && chatPointsManager) {
                        setTimeout(() => {
                            chatPointsManager.awardPointsForMessage(messageText);
                        }, 500);
                    }
                }
            });
        }
        
        // Method 4: Listen for custom chat message events
        document.addEventListener('chatMessageSent', (e) => {
            const messageText = e.detail?.message || e.detail?.text;
            if (messageText && chatPointsManager) {
                chatPointsManager.awardPointsForMessage(messageText);
            }
        });
    };
    
    // Try to hook immediately
    hookIntoChatSending();
    
    // Also try after a delay (in case chat.js loads later)
    setTimeout(hookIntoChatSending, 1000);
    setTimeout(hookIntoChatSending, 3000);
});

// Export for use in other scripts
window.ChatPointsManager = ChatPointsManager;
window.chatPointsManager = chatPointsManager;

