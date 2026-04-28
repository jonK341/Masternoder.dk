/**
 * Chatroom Notification Alarm System
 * Includes screen capture and notification logic
 */

class ChatNotificationAlarm {
    constructor() {
        this.notifications = [];
        this.screenCaptureEnabled = false;
        this.notificationPermission = Notification.permission;
        this.mediaStream = null;
        this.initializeNotifications();
    }
    
    initializeNotifications() {
        // Request notification permission
        if (this.notificationPermission === 'default') {
            Notification.requestPermission().then(permission => {
                this.notificationPermission = permission;
            });
        }
        
        // Request screen capture permission
        this.requestScreenCapturePermission();
        
        // Setup notification listeners
        this.setupNotificationListeners();
    }
    
    async requestScreenCapturePermission() {
        try {
            // Check if screen capture API is available
            if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
                // Permission will be requested when needed
                this.screenCaptureEnabled = true;
            }
        } catch (error) {
            console.error('[ChatAlarm] Screen capture not available:', error);
            this.screenCaptureEnabled = false;
        }
    }
    
    setupNotificationListeners() {
        // Listen for new chat messages
        document.addEventListener('chatMessage', (event) => {
            this.handleNewMessage(event.detail);
        });
        
        // Listen for mentions
        document.addEventListener('chatMention', (event) => {
            this.handleMention(event.detail);
        });
        
        // Listen for system alerts
        document.addEventListener('chatAlert', (event) => {
            this.handleAlert(event.detail);
        });
    }
    
    async handleNewMessage(message) {
        // Check if user should be notified
        if (this.shouldNotify(message)) {
            await this.showNotification({
                title: `New Message from ${message.username}`,
                body: message.text.substring(0, 100),
                icon: message.avatar || '/static/images/default-avatar.png',
                tag: `chat-${message.id}`,
                requireInteraction: false,
                data: message
            });
            
            // Capture screen if enabled and important
            if (this.screenCaptureEnabled && message.priority === 'high') {
                await this.captureScreenForMessage(message);
            }
        }
    }
    
    async handleMention(mention) {
        // Always notify on mentions
        await this.showNotification({
            title: `You were mentioned by ${mention.username}`,
            body: mention.text,
            icon: mention.avatar || '/static/images/default-avatar.png',
            tag: `mention-${mention.id}`,
            requireInteraction: true,
            data: mention
        });
        
        // Play sound
        this.playNotificationSound('mention');
        
        // Capture screen
        if (this.screenCaptureEnabled) {
            await this.captureScreenForMessage(mention);
        }
    }
    
    async handleAlert(alert) {
        // System alerts always notify
        await this.showNotification({
            title: alert.title || 'System Alert',
            body: alert.message,
            icon: alert.icon || '/static/images/alert-icon.png',
            tag: `alert-${Date.now()}`,
            requireInteraction: alert.important || false,
            data: alert
        });
        
        // Play alert sound
        this.playNotificationSound('alert');
        
        // Capture screen for important alerts
        if (this.screenCaptureEnabled && alert.important) {
            await this.captureScreenForAlert(alert);
        }
    }
    
    shouldNotify(message) {
        // Don't notify if user is active in chat
        if (document.hasFocus() && this.isChatWindowActive()) {
            return false;
        }
        
        // Notify if message is from admin/moderator
        if (message.role === 'admin' || message.role === 'moderator') {
            return true;
        }
        
        // Notify if message contains keywords
        const keywords = ['urgent', 'important', 'alert', 'warning'];
        const text = message.text.toLowerCase();
        if (keywords.some(keyword => text.includes(keyword))) {
            return true;
        }
        
        // Notify if user is mentioned
        if (message.mentions && message.mentions.includes(this.getCurrentUsername())) {
            return true;
        }
        
        return false;
    }
    
    isChatWindowActive() {
        const chatWindow = document.querySelector('.chat-window, .chat-container');
        return chatWindow && chatWindow.offsetParent !== null;
    }
    
    getCurrentUsername() {
        // Get current username from session or user data
        return localStorage.getItem('username') || 'User';
    }
    
    async showNotification(options) {
        if (this.notificationPermission !== 'granted') {
            console.warn('[ChatAlarm] Notifications not permitted');
            return;
        }
        
        try {
            const notification = new Notification(options.title, {
                body: options.body,
                icon: options.icon,
                tag: options.tag,
                requireInteraction: options.requireInteraction,
                data: options.data,
                badge: '/static/images/badge.png',
                image: options.image,
                vibrate: [200, 100, 200],
                timestamp: Date.now()
            });
            
            // Handle notification click
            notification.onclick = (event) => {
                event.preventDefault();
                window.focus();
                // Navigate to chat or specific message
                if (options.data) {
                    this.navigateToMessage(options.data);
                }
                notification.close();
            };
            
            // Auto-close after 5 seconds
            setTimeout(() => {
                notification.close();
            }, 5000);
            
            this.notifications.push(notification);
            
        } catch (error) {
            console.error('[ChatAlarm] Notification error:', error);
        }
    }
    
    async captureScreenForMessage(message) {
        try {
            if (!this.screenCaptureEnabled) return;
            
            const stream = await navigator.mediaDevices.getDisplayMedia({
                video: { mediaSource: 'screen' },
                audio: false
            });
            
            const video = document.createElement('video');
            video.srcObject = stream;
            video.play();
            
            // Wait for video to be ready
            await new Promise(resolve => {
                video.onloadedmetadata = resolve;
            });
            
            // Capture frame
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0);
            
            // Convert to blob
            const blob = await new Promise(resolve => {
                canvas.toBlob(resolve, 'image/png');
            });
            
            // Stop stream
            stream.getTracks().forEach(track => track.stop());
            
            // Save screenshot with message context
            await this.saveScreenshot(blob, {
                messageId: message.id,
                timestamp: new Date().toISOString(),
                context: 'chat_message',
                messageText: message.text.substring(0, 200)
            });
            
        } catch (error) {
            console.error('[ChatAlarm] Screen capture error:', error);
        }
    }
    
    async captureScreenForAlert(alert) {
        try {
            if (!this.screenCaptureEnabled) return;
            
            const stream = await navigator.mediaDevices.getDisplayMedia({
                video: { mediaSource: 'screen' },
                audio: false
            });
            
            const video = document.createElement('video');
            video.srcObject = stream;
            video.play();
            
            await new Promise(resolve => {
                video.onloadedmetadata = resolve;
            });
            
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0);
            
            const blob = await new Promise(resolve => {
                canvas.toBlob(resolve, 'image/png');
            });
            
            stream.getTracks().forEach(track => track.stop());
            
            await this.saveScreenshot(blob, {
                alertId: alert.id,
                timestamp: new Date().toISOString(),
                context: 'chat_alert',
                alertTitle: alert.title,
                alertMessage: alert.message
            });
            
        } catch (error) {
            console.error('[ChatAlarm] Screen capture error:', error);
        }
    }
    
    async saveScreenshot(blob, metadata) {
        try {
            // Save to IndexedDB
            const db = await this.openDatabase();
            const transaction = db.transaction(['screenshots'], 'readwrite');
            const store = transaction.objectStore('screenshots');
            
            const screenshot = {
                id: `screenshot-${Date.now()}`,
                blob: blob,
                metadata: metadata,
                timestamp: new Date().toISOString()
            };
            
            await store.add(screenshot);
            
            // Also save to server if needed
            await this.uploadScreenshot(blob, metadata);
            
        } catch (error) {
            console.error('[ChatAlarm] Save screenshot error:', error);
        }
    }
    
    async openDatabase() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('ChatScreenshots', 1);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains('screenshots')) {
                    const store = db.createObjectStore('screenshots', { keyPath: 'id' });
                    store.createIndex('timestamp', 'timestamp', { unique: false });
                    store.createIndex('context', 'metadata.context', { unique: false });
                }
            };
        });
    }
    
    async uploadScreenshot(blob, metadata) {
        try {
            const formData = new FormData();
            formData.append('screenshot', blob, `screenshot-${Date.now()}.png`);
            formData.append('metadata', JSON.stringify(metadata));
            
            await fetch('/vidgenerator/api/chat/upload-screenshot', {
                method: 'POST',
                body: formData
            });
        } catch (error) {
            console.error('[ChatAlarm] Upload screenshot error:', error);
        }
    }
    
    playNotificationSound(type) {
        const audio = new Audio();
        
        switch (type) {
            case 'mention':
                audio.src = '/static/sounds/mention.mp3';
                break;
            case 'alert':
                audio.src = '/static/sounds/alert.mp3';
                break;
            case 'message':
                audio.src = '/static/sounds/message.mp3';
                break;
            default:
                audio.src = '/static/sounds/notification.mp3';
        }
        
        audio.volume = 0.5;
        audio.play().catch(error => {
            console.error('[ChatAlarm] Sound play error:', error);
        });
    }
    
    navigateToMessage(message) {
        // Navigate to chat and scroll to message
        if (window.location.pathname !== '/vidgenerator/chat') {
            window.location.href = '/vidgenerator/chat';
        }
        
        // Scroll to message after page loads
        setTimeout(() => {
            const messageElement = document.querySelector(`[data-message-id="${message.id}"]`);
            if (messageElement) {
                messageElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                messageElement.classList.add('highlight');
                setTimeout(() => {
                    messageElement.classList.remove('highlight');
                }, 3000);
            }
        }, 500);
    }
    
    // Public API
    enableScreenCapture() {
        this.screenCaptureEnabled = true;
    }
    
    disableScreenCapture() {
        this.screenCaptureEnabled = false;
    }
    
    clearNotifications() {
        this.notifications.forEach(notification => notification.close());
        this.notifications = [];
    }
}

// Initialize
let chatNotificationAlarm = null;
document.addEventListener('DOMContentLoaded', () => {
    chatNotificationAlarm = new ChatNotificationAlarm();
    window.chatNotificationAlarm = chatNotificationAlarm;
});

