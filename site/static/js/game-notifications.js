/**
 * Game Notifications System
 * Real-time notifications for achievements, level ups, and game events
 */

class GameNotifications {
    constructor() {
        this.notifications = [];
        this.container = null;
        this.init();
    }
    
    init() {
        // Create notification container
        this.container = document.createElement('div');
        this.container.id = 'game-notifications-container';
        this.container.className = 'game-notifications-container';
        document.body.appendChild(this.container);
    }
    
    show(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `game-notification game-notification-${type}`;
        
        const icon = this.getIcon(type);
        notification.innerHTML = `
            <div class="notification-icon">${icon}</div>
            <div class="notification-content">
                <div class="notification-message">${message}</div>
            </div>
            <button class="notification-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        this.container.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        // Auto remove
        if (duration > 0) {
            setTimeout(() => {
                this.remove(notification);
            }, duration);
        }
        
        return notification;
    }
    
    remove(notification) {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 300);
    }
    
    getIcon(type) {
        const icons = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️',
            'achievement': '🏆',
            'levelup': '🎉',
            'milestone': '🎯',
            'xp': '⭐',
            'reward': '🎁'
        };
        return icons[type] || icons.info;
    }
    
    achievement(name) {
        return this.show(`Achievement Unlocked: ${name}!`, 'achievement', 5000);
    }
    
    levelUp(level) {
        return this.show(`Level Up! You reached Level ${level}!`, 'levelup', 5000);
    }
    
    milestone(name) {
        return this.show(`Milestone Reached: ${name}!`, 'milestone', 5000);
    }
    
    xpGained(amount) {
        return this.show(`+${amount} XP Gained!`, 'xp', 3000);
    }
    
    reward(name) {
        return this.show(`Reward Unlocked: ${name}!`, 'reward', 4000);
    }
    
    success(message) {
        return this.show(message, 'success', 3000);
    }
    
    error(message) {
        return this.show(message, 'error', 4000);
    }
    
    info(message) {
        return this.show(message, 'info', 3000);
    }
}

// Global instance
window.gameNotifications = new GameNotifications();




