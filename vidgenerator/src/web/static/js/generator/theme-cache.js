/**
 * Theme File Cache Manager
 * Stores theme video/image files in IndexedDB for offline use and faster loading
 */

class ThemeCacheManager {
    constructor() {
        this.dbName = 'ThemeCacheDB';
        this.dbVersion = 1;
        this.db = null;
        this.init();
    }
    
    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);
            
            request.onerror = () => {
                console.error('[ThemeCache] Failed to open IndexedDB:', request.error);
                reject(request.error);
            };
            
            request.onsuccess = () => {
                this.db = request.result;
                console.log('[ThemeCache] IndexedDB opened successfully');
                resolve(this.db);
            };
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                // Create object store for theme videos
                if (!db.objectStoreNames.contains('themeVideos')) {
                    const videoStore = db.createObjectStore('themeVideos', { keyPath: 'themeName' });
                    videoStore.createIndex('url', 'url', { unique: false });
                    videoStore.createIndex('lastUpdated', 'lastUpdated', { unique: false });
                }
                
                // Create object store for theme images
                if (!db.objectStoreNames.contains('themeImages')) {
                    const imageStore = db.createObjectStore('themeImages', { keyPath: 'themeName' });
                    imageStore.createIndex('url', 'url', { unique: false });
                    imageStore.createIndex('lastUpdated', 'lastUpdated', { unique: false });
                }
                
                console.log('[ThemeCache] IndexedDB schema created');
            };
        });
    }
    
    /**
     * Cache a theme video file
     */
    async cacheThemeVideo(themeName, videoUrl, blob) {
        if (!this.db) {
            await this.init();
        }
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['themeVideos'], 'readwrite');
            const store = transaction.objectStore('themeVideos');
            
            const data = {
                themeName: themeName,
                url: videoUrl,
                blob: blob,
                lastUpdated: Date.now(),
                size: blob.size
            };
            
            const request = store.put(data);
            
            request.onsuccess = () => {
                console.log(`[ThemeCache] Cached video for theme: ${themeName} (${(blob.size / 1024).toFixed(2)} KB)`);
                resolve(data);
            };
            
            request.onerror = () => {
                console.error(`[ThemeCache] Failed to cache video for ${themeName}:`, request.error);
                reject(request.error);
            };
        });
    }
    
    /**
     * Cache a theme image file
     */
    async cacheThemeImage(themeName, imageUrl, blob) {
        if !this.db) {
            await this.init();
        }
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['themeImages'], 'readwrite');
            const store = transaction.objectStore('themeImages');
            
            const data = {
                themeName: themeName,
                url: imageUrl,
                blob: blob,
                lastUpdated: Date.now(),
                size: blob.size
            };
            
            const request = store.put(data);
            
            request.onsuccess = () => {
                console.log(`[ThemeCache] Cached image for theme: ${themeName} (${(blob.size / 1024).toFixed(2)} KB)`);
                resolve(data);
            };
            
            request.onerror = () => {
                console.error(`[ThemeCache] Failed to cache image for ${themeName}:`, request.error);
                reject(request.error);
            };
        });
    }
    
    /**
     * Get cached theme video
     */
    async getCachedVideo(themeName) {
        if (!this.db) {
            await this.init();
        }
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['themeVideos'], 'readonly');
            const store = transaction.objectStore('themeVideos');
            const request = store.get(themeName);
            
            request.onsuccess = () => {
                if (request.result) {
                    // Check if cache is still valid (7 days)
                    const cacheAge = Date.now() - request.result.lastUpdated;
                    const maxAge = 7 * 24 * 60 * 60 * 1000; // 7 days
                    
                    if (cacheAge < maxAge) {
                        console.log(`[ThemeCache] Found cached video for ${themeName}`);
                        const blobUrl = URL.createObjectURL(request.result.blob);
                        resolve({
                            blobUrl: blobUrl,
                            data: request.result
                        });
                    } else {
                        console.log(`[ThemeCache] Cached video for ${themeName} expired, removing...`);
                        this.removeCachedVideo(themeName);
                        resolve(null);
                    }
                } else {
                    resolve(null);
                }
            };
            
            request.onerror = () => {
                console.error(`[ThemeCache] Failed to get cached video for ${themeName}:`, request.error);
                reject(request.error);
            };
        });
    }
    
    /**
     * Get cached theme image
     */
    async getCachedImage(themeName) {
        if (!this.db) {
            await this.init();
        }
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['themeImages'], 'readonly');
            const store = transaction.objectStore('themeImages');
            const request = store.get(themeName);
            
            request.onsuccess = () => {
                if (request.result) {
                    // Check if cache is still valid (7 days)
                    const cacheAge = Date.now() - request.result.lastUpdated;
                    const maxAge = 7 * 24 * 60 * 60 * 1000; // 7 days
                    
                    if (cacheAge < maxAge) {
                        console.log(`[ThemeCache] Found cached image for ${themeName}`);
                        const blobUrl = URL.createObjectURL(request.result.blob);
                        resolve({
                            blobUrl: blobUrl,
                            data: request.result
                        });
                    } else {
                        console.log(`[ThemeCache] Cached image for ${themeName} expired, removing...`);
                        this.removeCachedImage(themeName);
                        resolve(null);
                    }
                } else {
                    resolve(null);
                }
            };
            
            request.onerror = () => {
                console.error(`[ThemeCache] Failed to get cached image for ${themeName}:`, request.error);
                reject(request.error);
            };
        });
    }
    
    /**
     * Download and cache theme video from URL
     */
    async downloadAndCacheVideo(themeName, videoUrl) {
        try {
            console.log(`[ThemeCache] Downloading video for ${themeName} from ${videoUrl}`);
            const response = await fetch(videoUrl);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const blob = await response.blob();
            await this.cacheThemeVideo(themeName, videoUrl, blob);
            
            const blobUrl = URL.createObjectURL(blob);
            return blobUrl;
        } catch (error) {
            console.error(`[ThemeCache] Failed to download video for ${themeName}:`, error);
            throw error;
        }
    }
    
    /**
     * Download and cache theme image from URL
     */
    async downloadAndCacheImage(themeName, imageUrl) {
        try {
            console.log(`[ThemeCache] Downloading image for ${themeName} from ${imageUrl}`);
            const response = await fetch(imageUrl);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const blob = await response.blob();
            await this.cacheThemeImage(themeName, imageUrl, blob);
            
            const blobUrl = URL.createObjectURL(blob);
            return blobUrl;
        } catch (error) {
            console.error(`[ThemeCache] Failed to download image for ${themeName}:`, error);
            throw error;
        }
    }
    
    /**
     * Remove cached video
     */
    async removeCachedVideo(themeName) {
        if (!this.db) return;
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['themeVideos'], 'readwrite');
            const store = transaction.objectStore('themeVideos');
            const request = store.delete(themeName);
            
            request.onsuccess = () => {
                console.log(`[ThemeCache] Removed cached video for ${themeName}`);
                resolve();
            };
            
            request.onerror = () => {
                console.error(`[ThemeCache] Failed to remove cached video for ${themeName}:`, request.error);
                reject(request.error);
            };
        });
    }
    
    /**
     * Remove cached image
     */
    async removeCachedImage(themeName) {
        if (!this.db) return;
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['themeImages'], 'readwrite');
            const store = transaction.objectStore('themeImages');
            const request = store.delete(themeName);
            
            request.onsuccess = () => {
                console.log(`[ThemeCache] Removed cached image for ${themeName}`);
                resolve();
            };
            
            request.onerror = () => {
                console.error(`[ThemeCache] Failed to remove cached image for ${themeName}:`, request.error);
                reject(request.error);
            };
        });
    }
    
    /**
     * Clear all cached themes
     */
    async clearAllCache() {
        if (!this.db) return;
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['themeVideos', 'themeImages'], 'readwrite');
            
            const videoStore = transaction.objectStore('themeVideos');
            const imageStore = transaction.objectStore('themeImages');
            
            const videoRequest = videoStore.clear();
            const imageRequest = imageStore.clear();
            
            let completed = 0;
            const checkComplete = () => {
                completed++;
                if (completed === 2) {
                    console.log('[ThemeCache] All cache cleared');
                    resolve();
                }
            };
            
            videoRequest.onsuccess = checkComplete;
            imageRequest.onsuccess = checkComplete;
            
            videoRequest.onerror = () => reject(videoRequest.error);
            imageRequest.onerror = () => reject(imageRequest.error);
        });
    }
    
    /**
     * Get cache statistics
     */
    async getCacheStats() {
        if (!this.db) {
            await this.init();
        }
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['themeVideos', 'themeImages'], 'readonly');
            const videoStore = transaction.objectStore('themeVideos');
            const imageStore = transaction.objectStore('themeImages');
            
            const videoRequest = videoStore.getAll();
            const imageRequest = imageStore.getAll();
            
            let completed = 0;
            let videos = [];
            let images = [];
            
            const checkComplete = () => {
                completed++;
                if (completed === 2) {
                    const totalSize = [...videos, ...images].reduce((sum, item) => sum + (item.size || 0), 0);
                    resolve({
                        videoCount: videos.length,
                        imageCount: images.length,
                        totalSize: totalSize,
                        totalSizeMB: (totalSize / (1024 * 1024)).toFixed(2),
                        videos: videos.map(v => ({ theme: v.themeName, size: (v.size / 1024).toFixed(2) + ' KB' })),
                        images: images.map(i => ({ theme: i.themeName, size: (i.size / 1024).toFixed(2) + ' KB' }))
                    });
                }
            };
            
            videoRequest.onsuccess = () => {
                videos = videoRequest.result;
                checkComplete();
            };
            
            imageRequest.onsuccess = () => {
                images = imageRequest.result;
                checkComplete();
            };
            
            videoRequest.onerror = () => reject(videoRequest.error);
            imageRequest.onerror = () => reject(imageRequest.error);
        });
    }
}

// Create global instance
window.themeCache = new ThemeCacheManager();

