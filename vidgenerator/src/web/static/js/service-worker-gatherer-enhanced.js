/**
 * Enhanced Service Worker Data Gatherer
 * Improved data collection with better organization and structure
 * Reduces data chaos through intelligent categorization
 */

const DATA_COLLECTOR_VERSION = '2.0.0-enhanced';

class EnhancedDataGatherer {
    constructor() {
        this.dataStore = {
            version: DATA_COLLECTOR_VERSION,
            timestamp: new Date().toISOString(),
            categories: {
                wikipedia: [],
                images: [],
                news: [],
                videos: [],
                metadata: {},
                context: {}
            },
            statistics: {
                total_items: 0,
                sources: {},
                quality_scores: {}
            }
        };
        
        this.collectionStrategies = {
            'wikipedia': this.collectWikipedia.bind(this),
            'images': this.collectImages.bind(this),
            'news': this.collectNews.bind(this),
            'videos': this.collectVideos.bind(this)
        };
        
        this.qualityFilters = {
            min_relevance: 0.5,
            max_items_per_source: 50,
            deduplication: true
        };
    }
    
    /**
     * Main collection method - organized and structured
     */
    async collectData(topic, options = {}) {
        const {
            sources = ['wikipedia', 'images', 'news'],
            maxItems = 100,
            qualityThreshold = 0.5
        } = options;
        
        console.log(`[DataGatherer] Starting organized data collection for: ${topic}`);
        
        // Initialize structured data store
        const collectionResult = {
            topic: topic,
            timestamp: new Date().toISOString(),
            sources: {},
            summary: {
                total_items: 0,
                quality_score: 0,
                coverage: {}
            }
        };
        
        // Collect from each source systematically
        for (const source of sources) {
            if (this.collectionStrategies[source]) {
                try {
                    const sourceData = await this.collectionStrategies[source](topic, {
                        maxItems: Math.floor(maxItems / sources.length),
                        qualityThreshold
                    });
                    
                    // Organize and categorize
                    const organized = this.organizeData(sourceData, source);
                    collectionResult.sources[source] = organized;
                    collectionResult.summary.total_items += organized.items.length;
                    collectionResult.summary.coverage[source] = organized.items.length;
                    
                    console.log(`[DataGatherer] Collected ${organized.items.length} items from ${source}`);
                } catch (error) {
                    console.error(`[DataGatherer] Error collecting from ${source}:`, error);
                    collectionResult.sources[source] = { error: error.message, items: [] };
                }
            }
        }
        
        // Calculate overall quality score
        collectionResult.summary.quality_score = this.calculateQualityScore(collectionResult);
        
        // Store in IndexedDB with structure
        await this.storeData(topic, collectionResult);
        
        return collectionResult;
    }
    
    /**
     * Organize data by category and relevance
     */
    organizeData(rawData, source) {
        const organized = {
            source: source,
            items: [],
            categories: {},
            metadata: {
                collection_time: new Date().toISOString(),
                item_count: 0
            }
        };
        
        if (Array.isArray(rawData)) {
            // Deduplicate and filter
            const unique = this.deduplicate(rawData);
            const filtered = this.filterByQuality(unique);
            
            // Categorize
            for (const item of filtered) {
                const category = this.categorizeItem(item, source);
                
                if (!organized.categories[category]) {
                    organized.categories[category] = [];
                }
                
                organized.categories[category].push(item);
                organized.items.push({
                    ...item,
                    category: category,
                    relevance_score: this.calculateRelevance(item)
                });
            }
        } else if (rawData && typeof rawData === 'object') {
            // Handle object data
            organized.items = [rawData];
            organized.categories['general'] = [rawData];
        }
        
        organized.metadata.item_count = organized.items.length;
        
        return organized;
    }
    
    /**
     * Categorize items intelligently
     */
    categorizeItem(item, source) {
        if (source === 'wikipedia') {
            // Categorize by Wikipedia sections
            return item.section || 'general';
        } else if (source === 'images') {
            // Categorize by image type/theme
            return item.category || item.tags?.[0] || 'general';
        } else if (source === 'news') {
            // Categorize by news category
            return item.category || 'general';
        }
        return 'general';
    }
    
    /**
     * Calculate relevance score for item
     */
    calculateRelevance(item) {
        let score = 0.5; // Base score
        
        // Boost score based on quality indicators
        if (item.title && item.title.length > 10) score += 0.1;
        if (item.description && item.description.length > 50) score += 0.1;
        if (item.url) score += 0.1;
        if (item.quality_score) score += item.quality_score * 0.2;
        
        return Math.min(1.0, score);
    }
    
    /**
     * Deduplicate items
     */
    deduplicate(items) {
        if (!this.qualityFilters.deduplication) return items;
        
        const seen = new Set();
        const unique = [];
        
        for (const item of items) {
            const key = item.url || item.id || JSON.stringify(item);
            if (!seen.has(key)) {
                seen.add(key);
                unique.push(item);
            }
        }
        
        return unique;
    }
    
    /**
     * Filter items by quality
     */
    filterByQuality(items) {
        return items.filter(item => {
            const relevance = this.calculateRelevance(item);
            return relevance >= this.qualityFilters.min_relevance;
        }).slice(0, this.qualityFilters.max_items_per_source);
    }
    
    /**
     * Calculate overall quality score
     */
    calculateQualityScore(collectionResult) {
        let totalScore = 0;
        let count = 0;
        
        for (const source in collectionResult.sources) {
            const sourceData = collectionResult.sources[source];
            if (sourceData.items) {
                for (const item of sourceData.items) {
                    if (item.relevance_score) {
                        totalScore += item.relevance_score;
                        count++;
                    }
                }
            }
        }
        
        return count > 0 ? totalScore / count : 0;
    }
    
    /**
     * Collect Wikipedia data
     */
    async collectWikipedia(topic, options = {}) {
        try {
            const url = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(topic)}`;
            const response = await fetch(url);
            
            if (response.ok) {
                const data = await response.json();
                return {
                    title: data.title,
                    extract: data.extract,
                    url: data.content_urls?.desktop?.page,
                    thumbnail: data.thumbnail?.source,
                    relevance_score: 0.9
                };
            }
        } catch (error) {
            console.error('[DataGatherer] Wikipedia error:', error);
        }
        
        return null;
    }
    
    /**
     * Collect images
     */
    async collectImages(topic, options = {}) {
        // Placeholder - would integrate with image APIs
        return [];
    }
    
    /**
     * Collect news
     */
    async collectNews(topic, options = {}) {
        // Placeholder - would integrate with news APIs
        return [];
    }
    
    /**
     * Collect videos
     */
    async collectVideos(topic, options = {}) {
        // Placeholder - would integrate with video APIs
        return [];
    }
    
    /**
     * Store data in IndexedDB with structure
     */
    async storeData(topic, data) {
        try {
            const db = await this.openDatabase();
            const transaction = db.transaction(['collected_data'], 'readwrite');
            const store = transaction.objectStore('collected_data');
            
            const record = {
                topic: topic,
                data: data,
                timestamp: new Date().toISOString(),
                version: DATA_COLLECTOR_VERSION
            };
            
            await store.put(record);
            console.log(`[DataGatherer] Stored organized data for: ${topic}`);
        } catch (error) {
            console.error('[DataGatherer] Storage error:', error);
        }
    }
    
    /**
     * Open IndexedDB database
     */
    async openDatabase() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('DataGathererDB', 2);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains('collected_data')) {
                    const store = db.createObjectStore('collected_data', { keyPath: 'topic' });
                    store.createIndex('timestamp', 'timestamp', { unique: false });
                }
            };
        });
    }
    
    /**
     * Get organized data for topic
     */
    async getData(topic) {
        try {
            const db = await this.openDatabase();
            const transaction = db.transaction(['collected_data'], 'readonly');
            const store = transaction.objectStore('collected_data');
            const request = store.get(topic);
            
            return new Promise((resolve, reject) => {
                request.onsuccess = () => resolve(request.result?.data);
                request.onerror = () => reject(request.error);
            });
        } catch (error) {
            console.error('[DataGatherer] Get data error:', error);
            return null;
        }
    }
}

// Export for use in service worker
if (typeof self !== 'undefined') {
    self.enhancedDataGatherer = new EnhancedDataGatherer();
}

