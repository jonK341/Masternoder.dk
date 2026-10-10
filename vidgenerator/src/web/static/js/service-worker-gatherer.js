/**
 * Service Worker as Data Gatherer and AI Generator
 * Enhanced service worker that gathers data and generates clips in background
 */

const APP_VERSION = 'dg-sw-v5-gatherer';
const CACHE_NAME = `documentary-generator-${APP_VERSION}`;

// Data gathering cache
const DATA_CACHE_NAME = 'documentary-data-cache';
const CLIP_CACHE_NAME = 'documentary-clip-cache';

// Max cache sizes
const MAX_DATA_CACHE_SIZE = 50 * 1024 * 1024; // 50MB
const MAX_CLIP_CACHE_SIZE = 100 * 1024 * 1024; // 100MB

// Install event - cache resources
self.addEventListener('install', (event) => {
    console.log('[ServiceWorker] Installing gatherer version:', APP_VERSION);
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[ServiceWorker] Caching app shell');
            return cache.addAll([
                '/vidgenerator/',
                '/vidgenerator/generator',
                '/vidgenerator/static/css/style.css',
                '/vidgenerator/static/js/main.js'
            ]);
        })
    );
    self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[ServiceWorker] Activating gatherer version:', APP_VERSION);
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME && name !== DATA_CACHE_NAME && name !== CLIP_CACHE_NAME)
                    .map((name) => {
                        console.log('[ServiceWorker] Deleting old cache:', name);
                        return caches.delete(name);
                    })
            );
        })
    );
    return self.clients.claim();
});

// Enhanced Data Gathering with Retry Logic and Multiple Sources
async function gatherDataFromSources(prompt, title, retries = 3) {
    console.log('[Gatherer] Starting enhanced data gathering for:', title);
    
    const startTime = performance.now();
    const gatheredData = {
        wikipedia: null,
        images: [],
        news: [],
        videos: [],
        facts: [],
        keywords: [],
        keyword_context: {},
        metadata: {},
        timestamp: new Date().toISOString(),
        gathering_stats: {
            sources_attempted: 0,
            sources_succeeded: 0,
            sources_failed: 0,
            total_time_ms: 0
        }
    };
    
    // Load active keywords from keyword foundation system with retry
    let activeKeywords = [];
    for (let attempt = 0; attempt < retries; attempt++) {
        try {
            const keywordData = await fetch('/vidgenerator/api/keywords/active', {
                signal: AbortSignal.timeout(5000)
            });
            if (keywordData.ok) {
                const keywords = await keywordData.json();
                activeKeywords = keywords.keywords || [];
                console.log('[Gatherer] Loaded active keywords:', activeKeywords.length);
                break;
            }
        } catch (e) {
            console.warn(`[Gatherer] Keyword fetch attempt ${attempt + 1} failed:`, e);
            if (attempt < retries - 1) {
                await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
            }
        }
    }
    
    gatheredData.keywords = activeKeywords;
    gatheredData.keyword_context = {
        categories: [...new Set(activeKeywords.map(k => k.category))],
        total_power: activeKeywords.reduce((sum, k) => sum + (k.power_level || 0), 0),
        active_count: activeKeywords.length
    };
    
    // Parallel data gathering with timeout
    const gatheringPromises = [];
    
    // Wikipedia gathering with retry
    gatheringPromises.push(
        gatherWikipediaData(title || prompt, retries)
            .then(data => {
                if (data) {
                    gatheredData.wikipedia = data;
                    gatheredData.gathering_stats.sources_succeeded++;
                } else {
                    gatheredData.gathering_stats.sources_failed++;
                }
            })
            .catch(err => {
                console.warn('[Gatherer] Wikipedia gathering failed:', err);
                gatheredData.gathering_stats.sources_failed++;
            })
    );
    gatheredData.gathering_stats.sources_attempted++;
    
    // Image gathering (enhanced)
    gatheringPromises.push(
        gatherImageData(prompt, title)
            .then(images => {
                if (images && images.length > 0) {
                    gatheredData.images = images;
                    gatheredData.gathering_stats.sources_succeeded++;
                } else {
                    gatheredData.gathering_stats.sources_failed++;
                }
            })
            .catch(err => {
                console.warn('[Gatherer] Image gathering failed:', err);
                gatheredData.gathering_stats.sources_failed++;
            })
    );
    gatheredData.gathering_stats.sources_attempted++;
    
    // Extract facts from prompt and keywords
    gatheringPromises.push(
        extractFactsFromPrompt(prompt, activeKeywords)
            .then(facts => {
                if (facts && facts.length > 0) {
                    gatheredData.facts = facts;
                    gatheredData.gathering_stats.sources_succeeded++;
                }
            })
            .catch(err => {
                console.warn('[Gatherer] Fact extraction failed:', err);
            })
    );
    
    // Wait for all gathering operations (with timeout)
    try {
        await Promise.race([
            Promise.all(gatheringPromises),
            new Promise((_, reject) => setTimeout(() => reject(new Error('Gathering timeout')), 15000))
        ]);
    } catch (error) {
        console.warn('[Gatherer] Some gathering operations timed out:', error);
    }
    
    // Calculate total time
    gatheredData.gathering_stats.total_time_ms = Math.round(performance.now() - startTime);
    
    // Add metadata
    gatheredData.metadata = {
        prompt_length: prompt.length,
        keyword_count: activeKeywords.length,
        success_rate: gatheredData.gathering_stats.sources_succeeded / gatheredData.gathering_stats.sources_attempted,
        quality_score: calculateQualityScore(gatheredData)
    };
    
    // Store gathered data in cache
    try {
        await storeGatheredData(prompt, gatheredData);
    } catch (error) {
        console.warn('[Gatherer] Failed to store gathered data:', error);
    }
    
    console.log('[Gatherer] Data gathering complete:', {
        sources_succeeded: gatheredData.gathering_stats.sources_succeeded,
        total_time: gatheredData.gathering_stats.total_time_ms + 'ms',
        quality_score: gatheredData.metadata.quality_score
    });
    
    return gatheredData;
}

// Enhanced Wikipedia gathering with retry
async function gatherWikipediaData(query, retries = 3) {
    for (let attempt = 0; attempt < retries; attempt++) {
        try {
            const wikiUrl = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(query)}`;
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);
            
            const wikiResponse = await fetch(wikiUrl, { signal: controller.signal });
            clearTimeout(timeoutId);
            
            if (wikiResponse.ok) {
                const wikiData = await wikiResponse.json();
                return {
                    title: wikiData.title,
                    extract: wikiData.extract,
                    url: wikiData.content_urls?.desktop?.page,
                    thumbnail: wikiData.thumbnail?.source,
                    coordinates: wikiData.coordinates
                };
            }
        } catch (e) {
            if (attempt < retries - 1) {
                await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
            } else {
                console.warn('[Gatherer] Wikipedia fetch failed after retries:', e);
            }
        }
    }
    return null;
}

// Enhanced image gathering
async function gatherImageData(prompt, title) {
    const images = [];
    
    // Try to get images from API if available
    try {
        const imageResponse = await fetch(`/vidgenerator/api/images/search?q=${encodeURIComponent(prompt)}`, {
            signal: AbortSignal.timeout(5000)
        });
        if (imageResponse.ok) {
            const imageData = await imageResponse.json();
            if (imageData.images && imageData.images.length > 0) {
                return imageData.images;
            }
        }
    } catch (e) {
        console.warn('[Gatherer] Image API fetch failed:', e);
    }
    
    // Fallback to placeholder
    images.push({
        url: '/static/img/placeholder.jpg',
        source: 'placeholder',
        alt: title || prompt
    });
    
    return images;
}

// Extract facts from prompt and keywords
async function extractFactsFromPrompt(prompt, keywords) {
    const facts = [];
    
    // Extract key terms from prompt
    const words = prompt.toLowerCase().split(/\s+/);
    const keyTerms = words.filter(w => w.length > 4);
    
    // Add keyword-related facts
    keywords.forEach(keyword => {
        if (keyword.active && keyword.power_level > 5) {
            facts.push({
                type: 'keyword',
                content: keyword.english_translation || keyword.danish_keyword,
                category: keyword.category,
                power_level: keyword.power_level
            });
        }
    });
    
    // Add prompt-based facts
    if (keyTerms.length > 0) {
        facts.push({
            type: 'prompt',
            content: `Topic focuses on: ${keyTerms.slice(0, 5).join(', ')}`,
            relevance: 'high'
        });
    }
    
    return facts;
}

// Calculate quality score for gathered data
function calculateQualityScore(data) {
    let score = 0;
    
    if (data.wikipedia) score += 30;
    if (data.images && data.images.length > 0) score += 20;
    if (data.facts && data.facts.length > 0) score += 20;
    if (data.keywords && data.keywords.length > 0) score += 20;
    if (data.keyword_context.total_power > 50) score += 10;
    
    return Math.min(100, score);
}

// Store gathered data in IndexedDB
async function storeGatheredData(prompt, data) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DATA_CACHE_NAME, 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            if (!db.objectStoreNames.contains('gatheredData')) {
                const upgradeRequest = indexedDB.open(DATA_CACHE_NAME, 2);
                upgradeRequest.onupgradeneeded = (event) => {
                    const db = event.target.result;
                    if (!db.objectStoreNames.contains('gatheredData')) {
                        db.createObjectStore('gatheredData', { keyPath: 'id' });
                    }
                };
                upgradeRequest.onsuccess = () => {
                    storeData(db, prompt, data).then(resolve).catch(reject);
                };
            } else {
                storeData(db, prompt, data).then(resolve).catch(reject);
            }
        };
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('gatheredData')) {
                db.createObjectStore('gatheredData', { keyPath: 'id' });
            }
        };
    });
}

function storeData(db, prompt, data) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['gatheredData'], 'readwrite');
        const store = transaction.objectStore('gatheredData');
        const id = btoa(prompt).substring(0, 50); // Simple ID from prompt
        
        const record = {
            id: id,
            prompt: prompt,
            data: data,
            timestamp: new Date().toISOString()
        };
        
        const request = store.put(record);
        request.onsuccess = () => {
            console.log('[Gatherer] Data stored in cache');
            resolve();
        };
        request.onerror = () => reject(request.error);
    });
}

// Get cached gathered data
async function getCachedData(prompt) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DATA_CACHE_NAME, 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            if (!db.objectStoreNames.contains('gatheredData')) {
                resolve(null);
                return;
            }
            
            const transaction = db.transaction(['gatheredData'], 'readonly');
            const store = transaction.objectStore('gatheredData');
            const id = btoa(prompt).substring(0, 50);
            const getRequest = store.get(id);
            
            getRequest.onsuccess = () => {
                const result = getRequest.result;
                if (result) {
                    // Check if cache is still valid (24 hours)
                    const cacheAge = Date.now() - new Date(result.timestamp).getTime();
                    if (cacheAge < 24 * 60 * 60 * 1000) {
                        console.log('[Gatherer] Using cached data');
                        resolve(result.data);
                    } else {
                        console.log('[Gatherer] Cache expired');
                        resolve(null);
                    }
                } else {
                    resolve(null);
                }
            };
            getRequest.onerror = () => reject(getRequest.error);
        };
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('gatheredData')) {
                db.createObjectStore('gatheredData', { keyPath: 'id' });
            }
        };
    });
}

// Intercept generation requests
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    
    // Intercept generation API requests
    if (url.pathname.includes('/api/documentary/generate')) {
        event.respondWith(handleGenerationRequest(event.request));
    }
    // Intercept clip requests
    else if (url.pathname.includes('/api/clip/') || url.pathname.includes('/vidgenerator/api/clip/')) {
        event.respondWith(handleClipRequest(event.request));
    }
    // Cache-first strategy for static assets
    else if (url.pathname.startsWith('/vidgenerator/static/')) {
        event.respondWith(cacheFirst(event.request));
    }
    // Network-first for API requests
    else if (url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirst(event.request));
    }
    // Default: network first
    else {
        event.respondWith(networkFirst(event.request));
    }
});

// Handle generation request with data gathering
async function handleGenerationRequest(request) {
    try {
        // Clone request to read body
        const clonedRequest = request.clone();
        const requestData = await clonedRequest.json();
        
        const prompt = requestData.prompt || '';
        const title = requestData.title || '';
        
        // Check cache first
        const cachedData = await getCachedData(prompt);
        
        if (cachedData) {
            // Enhance request with cached data
            requestData.gathered_data = cachedData;
            requestData.data_source = 'cache';
        } else {
            // Gather data in background (don't block request)
            gatherDataFromSources(prompt, title).then((data) => {
                // Enhance request with gathered data
                requestData.gathered_data = data;
                requestData.data_source = 'fresh';
            }).catch((error) => {
                console.error('[Gatherer] Background gathering failed:', error);
            });
        }
        
        // Forward enhanced request to server
        const enhancedRequest = new Request(request.url, {
            method: request.method,
            headers: request.headers,
            body: JSON.stringify(requestData)
        });
        
        return fetch(enhancedRequest);
    } catch (error) {
        console.error('[Gatherer] Request handling error:', error);
        return fetch(request); // Fallback to original request
    }
}

// Handle clip requests with caching
async function handleClipRequest(request) {
    const cache = await caches.open(CLIP_CACHE_NAME);
    const cached = await cache.match(request);
    
    if (cached) {
        console.log('[Gatherer] Serving clip from cache');
        return cached;
    }
    
    try {
        const response = await fetch(request);
        if (response.ok) {
            // Check cache size before storing
            const cacheSize = await getCacheSize(CLIP_CACHE_NAME);
            if (cacheSize < MAX_CLIP_CACHE_SIZE) {
                cache.put(request, response.clone());
            } else {
                // Evict oldest entries (FIFO)
                await evictOldestClips(cache);
                cache.put(request, response.clone());
            }
        }
        return response;
    } catch (error) {
        console.error('[Gatherer] Clip fetch error:', error);
        if (cached) {
            return cached; // Return stale cache if network fails
        }
        throw error;
    }
}

// Cache-first strategy
async function cacheFirst(request) {
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(request);
    
    if (cached) {
        return cached;
    }
    
    try {
        const response = await fetch(request);
        if (response.ok) {
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        console.error('[Gatherer] Cache-first error:', error);
        throw error;
    }
}

// Network-first strategy
async function networkFirst(request) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        console.error('[Gatherer] Network-first error, trying cache:', error);
        const cache = await caches.open(CACHE_NAME);
        const cached = await cache.match(request);
        if (cached) {
            return cached;
        }
        throw error;
    }
}

// Get cache size
async function getCacheSize(cacheName) {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    let totalSize = 0;
    
    for (const key of keys) {
        const response = await cache.match(key);
        if (response) {
            const blob = await response.blob();
            totalSize += blob.size;
        }
    }
    
    return totalSize;
}

// Evict oldest clips (FIFO)
async function evictOldestClips(cache) {
    const keys = await cache.keys();
    if (keys.length === 0) return;
    
    // Sort by timestamp if available, otherwise remove first
    const sortedKeys = keys.slice(0, Math.floor(keys.length * 0.2)); // Remove 20%
    for (const key of sortedKeys) {
        await cache.delete(key);
    }
    console.log('[Gatherer] Evicted', sortedKeys.length, 'old clips');
}

// Message handling for communication with main thread
self.addEventListener('message', (event) => {
    if (event.data && event.data.type) {
        switch (event.data.type) {
            case 'GATHER_INTELLIGENCE':
                // Handle intelligence gathering request from generator button
                const messageChannel = event.ports && event.ports[0] ? event.ports[0] : null;
                gatherDataFromSources(event.data.prompt, event.data.title || event.data.prompt)
                    .then((data) => {
                        // Format as intelligence object
                        const intelligence = {
                            research: {
                                wikipedia: data.wikipedia || null,
                                facts: data.facts || [],
                                keywords: data.keywords || []
                            },
                            images: {
                                images: data.images || []
                            },
                            keywords: data.keywords || [],
                            metadata: {
                                sources_count: data.gathering_stats?.sources_succeeded || 0,
                                intelligence_score: calculateQualityScore(data),
                                quality: 'standard',
                                timestamp: data.timestamp
                            }
                        };
                        
                        if (messageChannel) {
                            messageChannel.postMessage({ 
                                success: true, 
                                intelligence: intelligence 
                            });
                        } else {
                            // Fallback: post message back to all clients
                            self.clients.matchAll().then(clients => {
                                clients.forEach(client => {
                                    client.postMessage({
                                        type: 'INTELLIGENCE_GATHERED',
                                        success: true,
                                        intelligence: intelligence,
                                        doc_id: event.data.doc_id
                                    });
                                });
                            });
                        }
                    })
                    .catch((error) => {
                        if (messageChannel) {
                            messageChannel.postMessage({ 
                                success: false, 
                                error: error.message 
                            });
                        }
                    });
                break;
                
            case 'GATHER_DATA':
                gatherDataFromSources(event.data.prompt, event.data.title)
                    .then((data) => {
                        event.ports[0].postMessage({ success: true, data: data });
                    })
                    .catch((error) => {
                        event.ports[0].postMessage({ success: false, error: error.message });
                    });
                break;
                
            case 'GET_CACHED_DATA':
                getCachedData(event.data.prompt)
                    .then((data) => {
                        event.ports[0].postMessage({ success: true, data: data });
                    })
                    .catch((error) => {
                        event.ports[0].postMessage({ success: false, error: error.message });
                    });
                break;
                
            case 'CLEAR_CACHE':
                caches.delete(DATA_CACHE_NAME).then(() => {
                    event.ports[0].postMessage({ success: true });
                });
                break;
                
            default:
                console.log('[Gatherer] Unknown message type:', event.data.type);
        }
    }
});

console.log('[ServiceWorker] Gatherer service worker loaded:', APP_VERSION);

