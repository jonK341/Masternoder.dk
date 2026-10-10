/**
 * Service Worker Clip Generator
 * Handles clip generation orchestration, logging, and debugging
 */

const CLIP_GENERATOR_VERSION = '1.0.0';

class ClipGeneratorServiceWorker {
    constructor() {
        this.version = CLIP_GENERATOR_VERSION;
        this.activeGenerations = new Map();
        this.logBuffer = [];
        this.maxLogEntries = 1000;
    }
    
    /**
     * Main entry point for clip generation
     */
    async generateClips(documentaryData) {
        const generationId = `gen_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        this.log(`[ClipGenerator] Starting generation: ${generationId}`);
        this.log(`[ClipGenerator] Topic: ${documentaryData.topic || documentaryData.prompt}`);
        
        try {
            // Step 1: Gather all information
            const gatheredData = await this.gatherInformation(documentaryData);
            this.log(`[ClipGenerator] Information gathered: ${Object.keys(gatheredData).length} sources`);
            
            // Step 2: Process and structure data
            const processedData = await this.processData(gatheredData);
            this.log(`[ClipGenerator] Data processed: ${processedData.clips.length} clips planned`);
            
            // Step 3: Create clip requests
            const clipRequests = this.createClipRequests(processedData);
            this.log(`[ClipGenerator] Created ${clipRequests.length} clip requests`);
            
            // Step 4: Generate clips
            const clipResults = await this.generateAllClips(clipRequests, generationId);
            this.log(`[ClipGenerator] Generated ${clipResults.filter(r => r.success).length}/${clipResults.length} clips`);
            
            // Step 5: Compile final documentary if needed
            if (documentaryData.targetDuration && documentaryData.targetDuration >= 1500) { // 25 minutes
                const finalVideo = await this.compileFinalDocumentary(clipResults, generationId);
                this.log(`[ClipGenerator] Final documentary compiled: ${finalVideo ? 'success' : 'failed'}`);
                return {
                    success: true,
                    generationId,
                    clips: clipResults,
                    finalVideo
                };
            }
            
            return {
                success: true,
                generationId,
                clips: clipResults
            };
            
        } catch (error) {
            this.log(`[ClipGenerator] ERROR: ${error.message}`, 'error');
            this.log(`[ClipGenerator] Stack: ${error.stack}`, 'error');
            return {
                success: false,
                generationId,
                error: error.message
            };
        }
    }
    
    /**
     * Step 1: Gather all information
     */
    async gatherInformation(documentaryData) {
        this.log(`[Gather] Starting information gathering...`);
        
        const topic = documentaryData.topic || documentaryData.prompt;
        const sources = {
            wikipedia: null,
            images: null,
            news: null,
            videos: null,
            metadata: {}
        };
        
        try {
            // Gather from multiple sources in parallel
            const [wikiData, imageData, newsData, videoData] = await Promise.allSettled([
                this.gatherWikipedia(topic),
                this.gatherImages(topic),
                this.gatherNews(topic),
                this.gatherVideos(topic)
            ]);
            
            sources.wikipedia = wikiData.status === 'fulfilled' ? wikiData.value : null;
            sources.images = imageData.status === 'fulfilled' ? imageData.value : null;
            sources.news = newsData.status === 'fulfilled' ? newsData.value : null;
            sources.videos = videoData.status === 'fulfilled' ? videoData.value : null;
            
            sources.metadata = {
                topic,
                timestamp: new Date().toISOString(),
                sources_available: Object.values(sources).filter(v => v !== null).length
            };
            
            this.log(`[Gather] Completed: ${sources.metadata.sources_available} sources available`);
            
        } catch (error) {
            this.log(`[Gather] Error: ${error.message}`, 'error');
        }
        
        return sources;
    }
    
    /**
     * Step 2: Process and structure data
     */
    async processData(gatheredData) {
        this.log(`[Process] Processing gathered data...`);
        
        const clips = [];
        let clipIndex = 0;
        
        // Process Wikipedia data into clips
        if (gatheredData.wikipedia) {
            const sections = this.extractSections(gatheredData.wikipedia);
            for (const section of sections) {
                clips.push({
                    index: clipIndex++,
                    type: 'short', // 5-12 seconds
                    prompt: section.title,
                    description: section.content.substring(0, 200),
                    duration: this.calculateDuration(section.content, 'short'),
                    source: 'wikipedia'
                });
            }
        }
        
        // Process images into visual clips
        if (gatheredData.images && gatheredData.images.length > 0) {
            for (let i = 0; i < Math.min(gatheredData.images.length, 10); i++) {
                clips.push({
                    index: clipIndex++,
                    type: 'short',
                    prompt: `Visual representation: ${gatheredData.images[i].title || 'Image'}`,
                    imageUrl: gatheredData.images[i].url,
                    duration: 8, // 8 seconds for image-based clips
                    source: 'images'
                });
            }
        }
        
        // Process news into medium clips
        if (gatheredData.news && gatheredData.news.length > 0) {
            for (const newsItem of gatheredData.news.slice(0, 5)) {
                clips.push({
                    index: clipIndex++,
                    type: 'medium', // 1-3 minutes
                    prompt: newsItem.title,
                    description: newsItem.description,
                    duration: this.calculateDuration(newsItem.description, 'medium'),
                    source: 'news'
                });
            }
        }
        
        this.log(`[Process] Created ${clips.length} clip plans`);
        
        return {
            clips,
            metadata: gatheredData.metadata
        };
    }
    
    /**
     * Step 3: Create clip requests for API
     */
    createClipRequests(processedData) {
        const requests = [];
        
        for (const clip of processedData.clips) {
            requests.push({
                prompt: clip.prompt,
                duration: clip.type, // 'short', 'medium', 'long'
                duration_seconds: clip.duration,
                style: clip.source,
                metadata: {
                    index: clip.index,
                    source: clip.source,
                    description: clip.description
                }
            });
        }
        
        return requests;
    }
    
    /**
     * Step 4: Generate all clips
     */
    async generateAllClips(clipRequests, generationId) {
        this.log(`[Generate] Starting generation of ${clipRequests.length} clips...`);
        
        const results = [];
        const batchSize = 3; // Generate 3 clips at a time
        
        for (let i = 0; i < clipRequests.length; i += batchSize) {
            const batch = clipRequests.slice(i, i + batchSize);
            this.log(`[Generate] Processing batch ${Math.floor(i / batchSize) + 1}/${Math.ceil(clipRequests.length / batchSize)}`);
            
            const batchPromises = batch.map((request, idx) => 
                this.generateSingleClip(request, generationId, i + idx)
            );
            
            const batchResults = await Promise.allSettled(batchPromises);
            
            for (const result of batchResults) {
                if (result.status === 'fulfilled') {
                    results.push(result.value);
                } else {
                    results.push({
                        success: false,
                        error: result.reason?.message || 'Unknown error'
                    });
                }
            }
            
            // Update progress
            const successCount = results.filter(r => r.success).length;
            this.log(`[Generate] Progress: ${successCount}/${results.length} clips generated`);
        }
        
        return results;
    }
    
    /**
     * Generate a single clip via API
     */
    async generateSingleClip(request, generationId, clipIndex) {
        this.log(`[Generate] Clip ${clipIndex + 1}: ${request.prompt.substring(0, 50)}...`);
        
        try {
            const response = await fetch('/vidgenerator/api/clip/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    prompt: request.prompt,
                    duration: request.duration,
                    duration_seconds: request.duration_seconds,
                    style: request.style,
                    metadata: {
                        ...request.metadata,
                        generationId,
                        clipIndex
                    }
                })
            });
            
            if (!response.ok) {
                throw new Error(`API returned ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.log(`[Generate] Clip ${clipIndex + 1} generated: ${data.clip_path}`);
                return {
                    success: true,
                    clip_path: data.clip_path,
                    duration: data.duration,
                    metadata: request.metadata
                };
            } else {
                throw new Error(data.error || 'Generation failed');
            }
            
        } catch (error) {
            this.log(`[Generate] Clip ${clipIndex + 1} failed: ${error.message}`, 'error');
            return {
                success: false,
                error: error.message,
                metadata: request.metadata
            };
        }
    }
    
    /**
     * Step 5: Compile final documentary
     */
    async compileFinalDocumentary(clipResults, generationId) {
        this.log(`[Compile] Compiling final documentary from ${clipResults.length} clips...`);
        
        try {
            const successfulClips = clipResults.filter(r => r.success && r.clip_path);
            
            if (successfulClips.length === 0) {
                throw new Error('No successful clips to compile');
            }
            
            const response = await fetch('/vidgenerator/api/documentary/compile', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    clips: successfulClips.map(c => ({
                        path: c.clip_path,
                        duration: c.duration,
                        metadata: c.metadata
                    })),
                    generationId
                })
            });
            
            if (!response.ok) {
                throw new Error(`Compilation API returned ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.log(`[Compile] Final documentary compiled: ${data.final_path}`);
                return data.final_path;
            } else {
                throw new Error(data.error || 'Compilation failed');
            }
            
        } catch (error) {
            this.log(`[Compile] ERROR: ${error.message}`, 'error');
            return null;
        }
    }
    
    /**
     * Helper methods
     */
    async gatherWikipedia(topic) {
        this.log(`[Gather] Fetching Wikipedia data for: ${topic}`);
        try {
            const response = await fetch(`https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(topic)}`);
            if (response.ok) {
                const data = await response.json();
                this.log(`[Gather] Wikipedia: Found "${data.title}"`);
                return {
                    title: data.title,
                    content: data.extract || data.description || '',
                    url: data.content_urls?.desktop?.page || ''
                };
            }
        } catch (error) {
            this.log(`[Gather] Wikipedia error: ${error.message}`, 'error');
        }
        return { title: topic, content: `Information about ${topic}` };
    }
    
    async gatherImages(topic) {
        this.log(`[Gather] Fetching images for: ${topic}`);
        try {
            // Use Unsplash API (free tier)
            const response = await fetch(`https://api.unsplash.com/search/photos?query=${encodeURIComponent(topic)}&per_page=10&client_id=YOUR_UNSPLASH_KEY`);
            if (response.ok) {
                const data = await response.json();
                const images = data.results?.map(img => ({
                    url: img.urls?.regular || img.urls?.small,
                    title: img.description || img.alt_description || topic,
                    thumbnail: img.urls?.thumb
                })) || [];
                this.log(`[Gather] Images: Found ${images.length} images`);
                return images;
            }
        } catch (error) {
            this.log(`[Gather] Images error: ${error.message}`, 'error');
        }
        return [];
    }
    
    async gatherNews(topic) {
        this.log(`[Gather] Fetching news for: ${topic}`);
        try {
            // Use NewsAPI (requires API key)
            const response = await fetch(`https://newsapi.org/v2/everything?q=${encodeURIComponent(topic)}&sortBy=relevancy&pageSize=5&apiKey=YOUR_NEWS_API_KEY`);
            if (response.ok) {
                const data = await response.json();
                const articles = data.articles?.map(article => ({
                    title: article.title,
                    description: article.description,
                    url: article.url,
                    publishedAt: article.publishedAt
                })) || [];
                this.log(`[Gather] News: Found ${articles.length} articles`);
                return articles;
            }
        } catch (error) {
            this.log(`[Gather] News error: ${error.message}`, 'error');
        }
        return [];
    }
    
    async gatherVideos(topic) {
        this.log(`[Gather] Fetching video references for: ${topic}`);
        // YouTube API would go here
        return [];
    }
    
    extractSections(wikiData) {
        // Placeholder - extract sections from Wikipedia data
        return [{
            title: wikiData.title,
            content: wikiData.content
        }];
    }
    
    calculateDuration(content, type) {
        if (type === 'short') {
            // 5-12 seconds based on content length
            const words = content.split(' ').length;
            return Math.max(5, Math.min(12, Math.floor(words / 10)));
        } else if (type === 'medium') {
            // 60-180 seconds (1-3 minutes)
            const words = content.split(' ').length;
            return Math.max(60, Math.min(180, Math.floor(words / 2)));
        }
        return 10; // Default
    }
    
    /**
     * Logging and debugging
     */
    log(message, level = 'info') {
        const timestamp = new Date().toISOString();
        const logEntry = {
            timestamp,
            level,
            message
        };
        
        this.logBuffer.push(logEntry);
        
        // Keep buffer size manageable
        if (this.logBuffer.length > this.maxLogEntries) {
            this.logBuffer = this.logBuffer.slice(-this.maxLogEntries);
        }
        
        // Also log to console
        const prefix = level === 'error' ? '❌' : level === 'warning' ? '⚠️' : 'ℹ️';
        console.log(`${prefix} [SW-ClipGen] ${message}`);
        
        // Send to API to store logs
        this._storeLog(logEntry);
        
        // Send to main thread if available
        if (self.clients) {
            self.clients.matchAll().then(clients => {
                clients.forEach(client => {
                    client.postMessage({
                        type: 'clip_generation_log',
                        data: logEntry
                    });
                });
            });
        }
    }
    
    /**
     * Store log entry in API
     */
    async _storeLog(logEntry) {
        try {
            const generationId = this.activeGenerations.keys().next().value || 'default';
            await fetch('/vidgenerator/api/service-worker/logs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    generation_id: generationId,
                    level: logEntry.level,
                    message: logEntry.message,
                    metadata: {
                        timestamp: logEntry.timestamp
                    }
                })
            });
        } catch (error) {
            // Silently fail - logging shouldn't break the process
            console.warn('[SW-ClipGen] Failed to store log:', error);
        }
    }
    
    getLogs() {
        return this.logBuffer;
    }
    
    clearLogs() {
        this.logBuffer = [];
    }
}

// Export for service worker
if (typeof self !== 'undefined') {
    self.clipGenerator = new ClipGeneratorServiceWorker();
}

