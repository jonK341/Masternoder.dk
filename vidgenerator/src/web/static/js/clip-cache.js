/**
 * Clip Cache Manager
 * Handles caching of video clips in browser cache
 */

class ClipCacheManager {
    constructor() {
        this.cacheName = 'dg-clips-v1';
        this.maxCacheSize = 100 * 1024 * 1024; // 100MB
    }
    
    /**
     * Check if a clip is cached
     * @param {string} clipId - Clip ID
     * @returns {Promise<boolean>}
     */
    async isCached(clipId) {
        try {
            const cache = await caches.open(this.cacheName);
            const cacheKey = `/vidgenerator/api/clip/${clipId}`;
            const cached = await cache.match(cacheKey);
            return cached !== undefined;
        } catch (error) {
            console.error('[ClipCache] Error checking cache:', error);
            return false;
        }
    }
    
    /**
     * Get cached clip
     * @param {string} clipId - Clip ID
     * @returns {Promise<Response|null>}
     */
    async getCachedClip(clipId) {
        try {
            const cache = await caches.open(this.cacheName);
            const cacheKey = `/vidgenerator/api/clip/${clipId}`;
            return await cache.match(cacheKey);
        } catch (error) {
            console.error('[ClipCache] Error getting cached clip:', error);
            return null;
        }
    }
    
    /**
     * Cache a clip from URL
     * @param {string} clipId - Clip ID
     * @param {string} clipUrl - Clip URL
     * @returns {Promise<boolean>}
     */
    async cacheClip(clipId, clipUrl) {
        try {
            const cache = await caches.open(this.cacheName);
            const cacheKey = `/vidgenerator/api/clip/${clipId}`;
            
            // Check if already cached
            const existing = await cache.match(cacheKey);
            if (existing) {
                console.log('[ClipCache] Clip already cached:', clipId);
                return true;
            }
            
            // Check cache size and clean up if needed
            await this.cleanupCache();
            
            // Fetch and cache
            const response = await fetch(clipUrl);
            if (response.ok) {
                await cache.put(cacheKey, response.clone());
                console.log('[ClipCache] Cached clip:', clipId);
                return true;
            }
            return false;
        } catch (error) {
            console.error('[ClipCache] Error caching clip:', error);
            return false;
        }
    }
    
    /**
     * Clean up cache if too large (FIFO)
     * @returns {Promise<void>}
     */
    async cleanupCache() {
        try {
            const cache = await caches.open(this.cacheName);
            const keys = await cache.keys();
            
            // Calculate total size
            let totalSize = 0;
            const sizes = [];
            for (const key of keys) {
                const response = await cache.match(key);
                if (response) {
                    const blob = await response.blob();
                    const size = blob.size;
                    totalSize += size;
                    sizes.push({ key, size });
                }
            }
            
            // If cache is too large, remove oldest 20%
            if (totalSize > this.maxCacheSize) {
                const sortedKeys = keys.sort((a, b) => {
                    return a.url.localeCompare(b.url); // FIFO order
                });
                const removeCount = Math.max(1, Math.floor(sortedKeys.length * 0.2));
                
                for (let i = 0; i < removeCount; i++) {
                    await cache.delete(sortedKeys[i]);
                    console.log('[ClipCache] Removed old clip from cache:', sortedKeys[i].url);
                }
            }
        } catch (error) {
            console.error('[ClipCache] Error cleaning up cache:', error);
        }
    }
    
    /**
     * Get cache stats
     * @returns {Promise<{count: number, size: number, maxSize: number}>}
     */
    async getCacheStats() {
        try {
            const cache = await caches.open(this.cacheName);
            const keys = await cache.keys();
            let totalSize = 0;
            
            for (const key of keys) {
                const response = await cache.match(key);
                if (response) {
                    const blob = await response.blob();
                    totalSize += blob.size;
                }
            }
            
            return {
                count: keys.length,
                size: totalSize,
                maxSize: this.maxCacheSize,
                sizeMB: (totalSize / (1024 * 1024)).toFixed(2)
            };
        } catch (error) {
            console.error('[ClipCache] Error getting cache stats:', error);
            return { count: 0, size: 0, maxSize: this.maxCacheSize, sizeMB: '0.00' };
        }
    }
    
    /**
     * Clear all cached clips
     * @returns {Promise<void>}
     */
    async clearCache() {
        try {
            await caches.delete(this.cacheName);
            console.log('[ClipCache] Cache cleared');
        } catch (error) {
            console.error('[ClipCache] Error clearing cache:', error);
        }
    }
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
    window.ClipCacheManager = ClipCacheManager;
    window.clipCache = new ClipCacheManager();
}

// Auto-cache clips when they're loaded
if (typeof window !== 'undefined') {
    document.addEventListener('DOMContentLoaded', function() {
        // Listen for clip loading events
        document.addEventListener('clipLoaded', async function(event) {
            const { clipId, clipUrl } = event.detail;
            if (clipId && clipUrl && window.clipCache) {
                await window.clipCache.cacheClip(clipId, clipUrl);
            }
        });
    });
}

