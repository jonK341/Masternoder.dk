/**
 * Service Worker Gatherer
 * Registers the minimal service worker (no cache, no background sync).
 * Disable: ?sw=0 in URL or localStorage.setItem('sw_disabled','1') then reload.
 */

class ServiceWorkerGatherer {
    constructor() {
        this.swRegistration = null;
        this.isOnline = navigator.onLine;
        this.queue = this.loadQueue();
        this.init();
    }

    init() {
        this.setupOnlineOfflineListeners();
        // Defer SW registration so it never blocks first paint or page load (fixes slow load on all pages)
        const run = () => this.registerServiceWorker();
        if (typeof requestIdleCallback !== 'undefined') {
            requestIdleCallback(run, { timeout: 2000 });
        } else {
            if (document.readyState === 'complete') {
                setTimeout(run, 100);
            } else {
                window.addEventListener('load', () => setTimeout(run, 100));
            }
        }
    }

    setupOnlineOfflineListeners() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            console.log('[SW Gatherer] Online - processing queue');
            this.processQueue();
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            console.log('[SW Gatherer] Offline - queueing requests');
        });
    }

    async registerServiceWorker() {
        if (!('serviceWorker' in navigator)) return;
        if (localStorage.getItem('sw_disabled') === '1') {
            console.log('[SW Gatherer] Disabled via localStorage.sw_disabled');
            return;
        }
        if (new URLSearchParams(location.search).get('sw') === '0') {
            console.log('[SW Gatherer] Disabled via ?sw=0');
            return;
        }
        try {
            const registration = await navigator.serviceWorker.register('/service-worker.js', {
                scope: '/',
                updateViaCache: 'none'  // Never use HTTP cache for SW script - ensures updates deploy immediately
            });
            this.swRegistration = registration;
            console.log('[SW Gatherer] Service Worker registered:', registration.scope);
            registration.update();
            registration.addEventListener('updatefound', () => {
                console.log('[SW Gatherer] New service worker found, updating...');
            });
            navigator.serviceWorker.addEventListener('controllerchange', () => {
                console.log('[SW Gatherer] New service worker active');
                // No reload: minimal SW does not cache, so nothing to refresh
            });
        } catch (error) {
            console.error('[SW Gatherer] Service Worker registration failed:', error);
        }
    }

    loadQueue() {
        try {
            const stored = localStorage.getItem('sw_request_queue');
            return stored ? JSON.parse(stored) : [];
        } catch (e) {
            console.error('[SW Gatherer] Failed to load queue:', e);
            return [];
        }
    }

    saveQueue() {
        try {
            localStorage.setItem('sw_request_queue', JSON.stringify(this.queue));
        } catch (e) {
            console.error('[SW Gatherer] Failed to save queue:', e);
        }
    }

    async queueRequest(url, options) {
        const request = {
            id: Date.now() + Math.random(),
            url,
            options,
            timestamp: Date.now()
        };
        
        this.queue.push(request);
        this.saveQueue();
        console.log('[SW Gatherer] Queued request:', request.id);
        
        if (this.isOnline) {
            await this.processQueue();
        } else {
            this.showOfflineMessage();
        }
    }

    async processQueue() {
        if (!this.isOnline || this.queue.length === 0) {
            return;
        }

        console.log(`[SW Gatherer] Processing ${this.queue.length} queued requests`);
        
        const requests = [...this.queue];
        this.queue = [];
        this.saveQueue();

        for (const request of requests) {
            try {
                const response = await fetch(request.url, request.options);
                console.log('[SW Gatherer] Processed queued request:', request.id, response.status);
                
                // Dispatch custom event for the original caller
                window.dispatchEvent(new CustomEvent('sw-request-complete', {
                    detail: { requestId: request.id, response }
                }));
            } catch (error) {
                console.error('[SW Gatherer] Failed to process queued request:', request.id, error);
                // Re-queue on failure
                this.queue.push(request);
                this.saveQueue();
            }
        }
    }

    showOfflineMessage() {
        // Create or update offline notification
        let notification = document.getElementById('sw-offline-notification');
        if (!notification) {
            notification = document.createElement('div');
            notification.id = 'sw-offline-notification';
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #ffc107;
                color: #000;
                padding: 15px 20px;
                border-radius: 8px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                z-index: 10000;
                font-weight: 600;
            `;
            document.body.appendChild(notification);
        }
        notification.textContent = `📴 Offline - ${this.queue.length} request(s) queued`;
    }

    async fetchWithQueue(url, options = {}) {
        if (this.isOnline) {
            try {
                return await fetch(url, options);
            } catch (error) {
                // Network error - queue it
                if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
                    await this.queueRequest(url, options);
                    throw new Error('Request queued - will retry when online');
                }
                throw error;
            }
        } else {
            // Offline - queue it
            await this.queueRequest(url, options);
            throw new Error('Request queued - will retry when online');
        }
    }

    /** Return status for generator UI: active, online, queueLength, scope. */
    getStatus() {
        return {
            active: !!this.swRegistration && navigator.serviceWorker.controller != null,
            online: this.isOnline,
            queueLength: this.queue ? this.queue.length : 0,
            scope: this.swRegistration ? this.swRegistration.scope : '',
            supportsSW: 'serviceWorker' in navigator
        };
    }
}

// Initialize on page load
let swGatherer;
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        swGatherer = new ServiceWorkerGatherer();
        window.swGatherer = swGatherer;
    });
} else {
    swGatherer = new ServiceWorkerGatherer();
    window.swGatherer = swGatherer;
}

