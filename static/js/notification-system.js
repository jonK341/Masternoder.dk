/**
 * Notification System
 * Handles notifications for agent level ups, tech research complete, battle victories, etc.
 */

class NotificationSystem {
    constructor() {
        this.notifications = [];
        this.maxNotifications = 5;
        this.notificationDuration = 5000; // 5 seconds
        this.init();
    }

    init() {
        // Create notification container if it doesn't exist
        if (!document.getElementById('notification-container')) {
            const container = document.createElement('div');
            container.id = 'notification-container';
            container.style.cssText = `
                position: fixed;
                top: 80px;
                right: 20px;
                z-index: 10000;
                display: flex;
                flex-direction: column;
                gap: 10px;
                max-width: 400px;
            `;
            document.body.appendChild(container);
        }
    }

    show(notification) {
        const container = document.getElementById('notification-container');
        if (!container) {
            this.init();
            return;
        }

        const notificationId = `notification-${Date.now()}-${Math.random()}`;
        const notificationEl = document.createElement('div');
        notificationEl.id = notificationId;
        notificationEl.className = 'notification';
        
        const type = notification.type || 'info';
        const icon = this.getIcon(type);
        const color = this.getColor(type);
        
        notificationEl.style.cssText = `
            background: linear-gradient(135deg, rgba(40, 40, 55, 0.95), rgba(30, 30, 45, 0.95));
            border: 2px solid ${color};
            border-radius: 12px;
            padding: 15px 20px;
            color: var(--text-primary);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            animation: slideInRight 0.3s ease;
            backdrop-filter: blur(10px);
            display: flex;
            align-items: start;
            gap: 15px;
            min-width: 300px;
        `;

        notificationEl.innerHTML = `
            <div style="font-size: 2em; color: ${color};">${icon}</div>
            <div style="flex: 1;">
                <div style="font-weight: bold; color: ${color}; margin-bottom: 5px; font-size: 1.1em;">
                    ${notification.title || 'Notification'}
                </div>
                <div style="color: var(--text-secondary); font-size: 0.9em;">
                    ${notification.message || ''}
                </div>
                ${notification.details ? `
                    <div style="margin-top: 8px; font-size: 0.85em; color: var(--text-tertiary);">
                        ${notification.details}
                    </div>
                ` : ''}
            </div>
            <button onclick="notificationSystem.dismiss('${notificationId}')" 
                    style="background: none; border: none; color: var(--text-secondary); 
                           cursor: pointer; font-size: 1.2em; padding: 0; width: 24px; height: 24px;
                           display: flex; align-items: center; justify-content: center;">
                &times;
            </button>
        `;

        // Add animation styles if not already added
        if (!document.getElementById('notification-styles')) {
            const style = document.createElement('style');
            style.id = 'notification-styles';
            style.textContent = `
                @keyframes slideInRight {
                    from {
                        transform: translateX(400px);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                @keyframes slideOutRight {
                    from {
                        transform: translateX(0);
                        opacity: 1;
                    }
                    to {
                        transform: translateX(400px);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }

        container.insertBefore(notificationEl, container.firstChild);

        // Limit number of notifications
        while (container.children.length > this.maxNotifications) {
            container.removeChild(container.lastChild);
        }

        // Auto-dismiss after duration
        if (notification.duration !== false) {
            setTimeout(() => {
                this.dismiss(notificationId);
            }, notification.duration || this.notificationDuration);
        }

        // Store notification
        this.notifications.push({
            id: notificationId,
            element: notificationEl,
            type: type
        });

        return notificationId;
    }

    dismiss(notificationId) {
        const notification = this.notifications.find(n => n.id === notificationId);
        if (notification) {
            notification.element.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (notification.element.parentNode) {
                    notification.element.parentNode.removeChild(notification.element);
                }
                this.notifications = this.notifications.filter(n => n.id !== notificationId);
            }, 300);
        }
    }

    dismissAll() {
        this.notifications.forEach(n => this.dismiss(n.id));
    }

    getIcon(type) {
        const icons = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️',
            'agent_level_up': '🤖',
            'tech_research': '🔬',
            'battle_victory': '🏆',
            'battle_defeat': '💀',
            'achievement': '🎖️'
        };
        return icons[type] || icons['info'];
    }

    getColor(type) {
        const colors = {
            'success': 'var(--primary)',
            'error': '#ff4444',
            'warning': '#ffaa00',
            'info': 'var(--secondary)',
            'agent_level_up': 'var(--primary)',
            'tech_research': 'var(--secondary)',
            'battle_victory': '#ffd700',
            'battle_defeat': '#ff4444',
            'achievement': '#ff00ff'
        };
        return colors[type] || colors['info'];
    }

    // Convenience methods
    agentLevelUp(agentName, newLevel) {
        return this.show({
            type: 'agent_level_up',
            title: 'Agent Level Up!',
            message: `${agentName} reached level ${newLevel}!`,
            details: 'Your agent has gained new abilities and bonuses.',
            duration: 6000
        });
    }

    techResearchComplete(techName) {
        return this.show({
            type: 'tech_research',
            title: 'Research Complete!',
            message: `${techName} research completed!`,
            details: 'New technologies and skills are now available.',
            duration: 6000
        });
    }

    battleVictory(rewards) {
        return this.show({
            type: 'battle_victory',
            title: 'Victory!',
            message: 'You won the battle!',
            details: rewards ? `Rewards: ${rewards} points` : '',
            duration: 5000
        });
    }

    battleDefeat() {
        return this.show({
            type: 'battle_defeat',
            title: 'Defeat',
            message: 'You were defeated in battle.',
            details: 'Better luck next time!',
            duration: 4000
        });
    }

    achievementUnlocked(achievementName, points) {
        return this.show({
            type: 'achievement',
            title: 'Achievement Unlocked!',
            message: achievementName,
            details: points ? `+${points} points` : '',
            duration: 6000
        });
    }
}

// Global instance
const notificationSystem = new NotificationSystem();

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationSystem;
}
