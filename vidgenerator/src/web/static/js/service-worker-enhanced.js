/**
 * Enhanced Service Worker with Professional Intelligence Gathering
 * Collects comprehensive data for AI generation
 */

const CACHE_NAME = 'vidgenerator-v1';
const INTELLIGENCE_CACHE = 'intelligence-v1';

// Enhanced data gathering sources
const DATA_SOURCES = {
    DOM: 'dom',
    STORAGE: 'storage',
    NETWORK: 'network',
    PERFORMANCE: 'performance',
    USER_INTERACTION: 'user_interaction',
    CONTEXT: 'context',
    KEYWORDS: 'keywords'
};

class EnhancedServiceWorkerGatherer {
    constructor() {
        this.intelligence = {
            timestamp: new Date().toISOString(),
            sources: {},
            metadata: {},
            errors: []
        };
    }

    /**
     * Gather comprehensive intelligence from all sources
     */
    async gatherComprehensiveIntelligence() {
        try {
            // Gather from all sources in parallel
            const [
                domData,
                storageData,
                networkData,
                performanceData,
                userData,
                contextData,
                keywordData
            ] = await Promise.all([
                this.gatherDOMIntelligence(),
                this.gatherStorageIntelligence(),
                this.gatherNetworkIntelligence(),
                this.gatherPerformanceIntelligence(),
                this.gatherUserInteractionIntelligence(),
                this.gatherContextIntelligence(),
                this.gatherKeywordIntelligence()
            ]);

            this.intelligence.sources = {
                [DATA_SOURCES.DOM]: domData,
                [DATA_SOURCES.STORAGE]: storageData,
                [DATA_SOURCES.NETWORK]: networkData,
                [DATA_SOURCES.PERFORMANCE]: performanceData,
                [DATA_SOURCES.USER_INTERACTION]: userData,
                [DATA_SOURCES.CONTEXT]: contextData,
                [DATA_SOURCES.KEYWORDS]: keywordData
            };

            // Add metadata
            this.intelligence.metadata = {
                userAgent: navigator.userAgent,
                language: navigator.language,
                platform: navigator.platform,
                screenResolution: `${screen.width}x${screen.height}`,
                colorDepth: screen.colorDepth,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                referrer: document.referrer,
                url: window.location.href
            };

            // Cache intelligence
            await this.cacheIntelligence(this.intelligence);

            return this.intelligence;
        } catch (error) {
            console.error('[Service Worker] Intelligence gathering error:', error);
            this.intelligence.errors.push({
                type: 'gathering_error',
                message: error.message,
                stack: error.stack,
                timestamp: new Date().toISOString()
            });
            return this.intelligence;
        }
    }

    /**
     * Gather DOM intelligence
     */
    async gatherDOMIntelligence() {
        try {
            const domData = {
                title: document.title,
                headings: Array.from(document.querySelectorAll('h1, h2, h3')).map(h => ({
                    tag: h.tagName,
                    text: h.textContent.trim().substring(0, 100)
                })),
                links: Array.from(document.querySelectorAll('a')).slice(0, 20).map(a => ({
                    href: a.href,
                    text: a.textContent.trim().substring(0, 50)
                })),
                images: Array.from(document.querySelectorAll('img')).slice(0, 10).map(img => ({
                    src: img.src,
                    alt: img.alt
                })),
                forms: Array.from(document.querySelectorAll('form')).map(form => ({
                    action: form.action,
                    method: form.method,
                    fields: Array.from(form.querySelectorAll('input, textarea, select')).map(f => ({
                        type: f.type || f.tagName.toLowerCase(),
                        name: f.name,
                        value: f.value ? f.value.substring(0, 50) : ''
                    }))
                })),
                metaTags: Array.from(document.querySelectorAll('meta')).map(meta => ({
                    name: meta.name || meta.property,
                    content: meta.content
                }))
            };

            return domData;
        } catch (error) {
            console.error('[Service Worker] DOM gathering error:', error);
            return { error: error.message };
        }
    }

    /**
     * Gather storage intelligence
     */
    async gatherStorageIntelligence() {
        try {
            const storageData = {
                localStorage: {},
                sessionStorage: {},
                indexedDB: null
            };

            // LocalStorage
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                try {
                    const value = localStorage.getItem(key);
                    storageData.localStorage[key] = value ? value.substring(0, 200) : null;
                } catch (e) {
                    // Skip problematic keys
                }
            }

            // SessionStorage
            for (let i = 0; i < sessionStorage.length; i++) {
                const key = sessionStorage.key(i);
                try {
                    const value = sessionStorage.getItem(key);
                    storageData.sessionStorage[key] = value ? value.substring(0, 200) : null;
                } catch (e) {
                    // Skip problematic keys
                }
            }

            // IndexedDB (if available)
            if ('indexedDB' in window) {
                try {
                    const db = await new Promise((resolve, reject) => {
                        const request = indexedDB.open('vidgenerator', 1);
                        request.onsuccess = () => resolve(request.result);
                        request.onerror = () => reject(request.error);
                    });
                    
                    if (db) {
                        storageData.indexedDB = {
                            name: db.name,
                            version: db.version,
                            objectStores: Array.from(db.objectStoreNames)
                        };
                    }
                } catch (e) {
                    storageData.indexedDB = { error: e.message };
                }
            }

            return storageData;
        } catch (error) {
            console.error('[Service Worker] Storage gathering error:', error);
            return { error: error.message };
        }
    }

    /**
     * Gather network intelligence
     */
    async gatherNetworkIntelligence() {
        try {
            const networkData = {
                connection: null,
                resources: []
            };

            // Network Information API
            if ('connection' in navigator) {
                const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
                if (conn) {
                    networkData.connection = {
                        effectiveType: conn.effectiveType,
                        downlink: conn.downlink,
                        rtt: conn.rtt,
                        saveData: conn.saveData
                    };
                }
            }

            // Performance Resource Timing
            if ('performance' in window && 'getEntriesByType' in performance) {
                const resources = performance.getEntriesByType('resource');
                networkData.resources = resources.slice(0, 20).map(resource => ({
                    name: resource.name,
                    type: resource.initiatorType,
                    duration: Math.round(resource.duration),
                    size: resource.transferSize || 0
                }));
            }

            return networkData;
        } catch (error) {
            console.error('[Service Worker] Network gathering error:', error);
            return { error: error.message };
        }
    }

    /**
     * Gather performance intelligence
     */
    async gatherPerformanceIntelligence() {
        try {
            const perfData = {};

            if ('performance' in window) {
                const timing = performance.timing;
                perfData.navigation = {
                    domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                    loadComplete: timing.loadEventEnd - timing.navigationStart,
                    domInteractive: timing.domInteractive - timing.navigationStart
                };

                // Paint Timing
                if ('getEntriesByType' in performance) {
                    const paintEntries = performance.getEntriesByType('paint');
                    perfData.paint = paintEntries.map(entry => ({
                        name: entry.name,
                        startTime: Math.round(entry.startTime)
                    }));
                }

                // Memory (if available)
                if ('memory' in performance) {
                    perfData.memory = {
                        usedJSHeapSize: performance.memory.usedJSHeapSize,
                        totalJSHeapSize: performance.memory.totalJSHeapSize,
                        jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
                    };
                }
            }

            return perfData;
        } catch (error) {
            console.error('[Service Worker] Performance gathering error:', error);
            return { error: error.message };
        }
    }

    /**
     * Gather user interaction intelligence
     */
    async gatherUserInteractionIntelligence() {
        try {
            const interactionData = {
                clicks: [],
                scrolls: [],
                keystrokes: [],
                focus: [],
                mouse: []
            };

            // Track interactions (limited to prevent memory issues)
            const MAX_TRACKED = 50;
            
            // Click tracking
            document.addEventListener('click', (e) => {
                if (interactionData.clicks.length < MAX_TRACKED) {
                    interactionData.clicks.push({
                        target: e.target.tagName,
                        timestamp: Date.now(),
                        x: e.clientX,
                        y: e.clientY
                    });
                }
            }, { passive: true });

            // Scroll tracking
            let scrollTimeout;
            window.addEventListener('scroll', () => {
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(() => {
                    if (interactionData.scrolls.length < MAX_TRACKED) {
                        interactionData.scrolls.push({
                            scrollY: window.scrollY,
                            scrollX: window.scrollX,
                            timestamp: Date.now()
                        });
                    }
                }, 100);
            }, { passive: true });

            return interactionData;
        } catch (error) {
            console.error('[Service Worker] User interaction gathering error:', error);
            return { error: error.message };
        }
    }

    /**
     * Gather context intelligence
     */
    async gatherContextIntelligence() {
        try {
            const contextData = {
                theme: localStorage.getItem('documentaryTheme') || 'matrix',
                userPreferences: {},
                sessionData: {},
                generationHistory: []
            };

            // User preferences
            try {
                const prefs = localStorage.getItem('userPreferences');
                if (prefs) {
                    contextData.userPreferences = JSON.parse(prefs);
                }
            } catch (e) {
                // Ignore parse errors
            }

            // Session data
            try {
                const session = sessionStorage.getItem('sessionData');
                if (session) {
                    contextData.sessionData = JSON.parse(session);
                }
            } catch (e) {
                // Ignore parse errors
            }

            // Generation history (from localStorage)
            try {
                const history = localStorage.getItem('generationHistory');
                if (history) {
                    contextData.generationHistory = JSON.parse(history).slice(-10); // Last 10
                }
            } catch (e) {
                // Ignore parse errors
            }

            return contextData;
        } catch (error) {
            console.error('[Service Worker] Context gathering error:', error);
            return { error: error.message };
        }
    }

    /**
     * Gather keyword intelligence
     */
    async gatherKeywordIntelligence() {
        try {
            const keywordData = {
                activeKeywords: [],
                categories: {},
                powerLevel: 0
            };

            // Fetch from API
            try {
                const response = await fetch('/vidgenerator/api/keywords/active');
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        keywordData.activeKeywords = data.keywords || [];
                        keywordData.categories = data.categories || {};
                        keywordData.powerLevel = data.total_power || 0;
                    }
                }
            } catch (e) {
                console.warn('[Service Worker] Keyword API not available:', e);
            }

            return keywordData;
        } catch (error) {
            console.error('[Service Worker] Keyword gathering error:', error);
            return { error: error.message };
        }
    }

    /**
     * Cache intelligence for offline use
     */
    async cacheIntelligence(intelligence) {
        try {
            if ('caches' in window) {
                const cache = await caches.open(INTELLIGENCE_CACHE);
                await cache.put(
                    new Request('/intelligence/latest'),
                    new Response(JSON.stringify(intelligence), {
                        headers: { 'Content-Type': 'application/json' }
                    })
                );
            }
        } catch (error) {
            console.error('[Service Worker] Cache error:', error);
        }
    }

    /**
     * Send intelligence to server
     */
    async sendIntelligenceToServer(intelligence) {
        try {
            const response = await fetch('/vidgenerator/api/intelligence/collect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(intelligence)
            });

            if (response.ok) {
                const result = await response.json();
                return result;
            } else {
                throw new Error(`Server error: ${response.status}`);
            }
        } catch (error) {
            console.error('[Service Worker] Send intelligence error:', error);
            throw error;
        }
    }
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EnhancedServiceWorkerGatherer;
}

// Auto-initialize if in browser
if (typeof window !== 'undefined') {
    window.EnhancedServiceWorkerGatherer = EnhancedServiceWorkerGatherer;
    
    // Auto-gather on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            const gatherer = new EnhancedServiceWorkerGatherer();
            gatherer.gatherComprehensiveIntelligence().then(intelligence => {
                console.log('[Service Worker] Intelligence gathered:', intelligence);
                // Send to server
                gatherer.sendIntelligenceToServer(intelligence).catch(console.error);
            });
        });
    } else {
        const gatherer = new EnhancedServiceWorkerGatherer();
        gatherer.gatherComprehensiveIntelligence().then(intelligence => {
            console.log('[Service Worker] Intelligence gathered:', intelligence);
            gatherer.sendIntelligenceToServer(intelligence).catch(console.error);
        });
    }
}

