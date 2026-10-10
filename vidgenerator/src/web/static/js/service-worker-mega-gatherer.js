/**
 * Service Worker Mega Data Gatherer
 * Gathers ALL data: stats, behavior, scrapes, searches, XP, psychological profile
 * Compiles into mega prompt/dataset for AI clip generation
 */

const MEGA_GATHERER_VERSION = '2.0.0';

class MegaDataGatherer {
    constructor() {
        this.version = MEGA_GATHERER_VERSION;
        this.gatheredData = {};
        this.logBuffer = [];
    }
    
    /**
     * Main entry: Gather ALL data and create mega prompt
     */
    async gatherMegaData(documentaryData, userContext = {}) {
        this.log(`[MegaGatherer] Starting comprehensive data gathering...`);
        
        const topic = documentaryData.topic || documentaryData.prompt;
        const docId = documentaryData.doc_id || documentaryData.id;
        
        try {
            // Gather from ALL sources in parallel
            const [
                webData,
                statsData,
                behaviorData,
                xpData,
                psychologicalData,
                searchData,
                matrixData,
                emotionData
            ] = await Promise.allSettled([
                this.gatherWebData(topic),
                this.gatherStatsData(docId, userContext),
                this.gatherBehaviorData(userContext),
                this.gatherXPData(userContext),
                this.gatherPsychologicalData(userContext),
                this.gatherSearchData(topic),
                this.gatherMatrixData(topic),
                this.gatherEmotionData(documentaryData)
            ]);
            
            // Compile all data
            this.gatheredData = {
                // Web scraping data
                web: webData.status === 'fulfilled' ? webData.value : {},
                // Stats and analytics
                stats: statsData.status === 'fulfilled' ? statsData.value : {},
                // Behavioral tracking
                behavior: behaviorData.status === 'fulfilled' ? behaviorData.value : {},
                // XP system data
                xp: xpData.status === 'fulfilled' ? xpData.value : {},
                // Psychological profile
                psychological: psychologicalData.status === 'fulfilled' ? psychologicalData.value : {},
                // Search results
                search: searchData.status === 'fulfilled' ? searchData.value : {},
                // Matrix system data
                matrix: matrixData.status === 'fulfilled' ? matrixData.value : {},
                // Emotion system data
                emotion: emotionData.status === 'fulfilled' ? emotionData.value : {},
                // Metadata
                metadata: {
                    topic,
                    doc_id: docId,
                    timestamp: new Date().toISOString(),
                    version: this.version,
                    sources_count: 8
                }
            };
            
            this.log(`[MegaGatherer] Gathered data from ${this.gatheredData.metadata.sources_count} sources`);
            
            // Create mega prompt
            const megaPrompt = this.createMegaPrompt(this.gatheredData, documentaryData);
            
            return {
                success: true,
                gathered_data: this.gatheredData,
                mega_prompt: megaPrompt,
                prompt_length: megaPrompt.length,
                data_summary: this.createDataSummary()
            };
            
        } catch (error) {
            this.log(`[MegaGatherer] ERROR: ${error.message}`, 'error');
            return {
                success: false,
                error: error.message,
                gathered_data: this.gatheredData
            };
        }
    }
    
    /**
     * Gather web data (Wikipedia, images, news, videos)
     */
    async gatherWebData(topic) {
        this.log(`[WebData] Gathering web data for: ${topic}`);
        
        const [wiki, images, news, videos] = await Promise.allSettled([
            this.fetchWikipedia(topic),
            this.fetchImages(topic),
            this.fetchNews(topic),
            this.fetchVideos(topic)
        ]);
        
        return {
            wikipedia: wiki.status === 'fulfilled' ? wiki.value : null,
            images: images.status === 'fulfilled' ? images.value : [],
            news: news.status === 'fulfilled' ? news.value : [],
            videos: videos.status === 'fulfilled' ? videos.value : [],
            timestamp: new Date().toISOString()
        };
    }
    
    /**
     * Gather stats data (generation stats, performance metrics)
     */
    async gatherStatsData(docId, userContext) {
        this.log(`[StatsData] Gathering stats data...`);
        
        try {
            const response = await fetch(`/vidgenerator/api/stats/documentary/${docId}`);
            if (response.ok) {
                const stats = await response.json();
                return {
                    generation_stats: stats.generation_stats || {},
                    performance_metrics: stats.performance_metrics || {},
                    quality_scores: stats.quality_scores || {},
                    timestamp: new Date().toISOString()
                };
            }
        } catch (error) {
            this.log(`[StatsData] Error: ${error.message}`, 'warning');
        }
        
        return {
            generation_stats: {},
            performance_metrics: {},
            quality_scores: {},
            timestamp: new Date().toISOString()
        };
    }
    
    /**
     * Gather behavioral data (user behavior patterns)
     */
    async gatherBehaviorData(userContext) {
        this.log(`[BehaviorData] Gathering behavioral data...`);
        
        try {
            const userId = userContext.user_id || 'anonymous';
            const response = await fetch(`/vidgenerator/api/behavior/${userId}`);
            if (response.ok) {
                const behavior = await response.json();
                return {
                    patterns: behavior.patterns || {},
                    preferences: behavior.preferences || {},
                    history: behavior.history || [],
                    timestamp: new Date().toISOString()
                };
            }
        } catch (error) {
            this.log(`[BehaviorData] Error: ${error.message}`, 'warning');
        }
        
        return {
            patterns: {},
            preferences: {},
            history: [],
            timestamp: new Date().toISOString()
        };
    }
    
    /**
     * Gather XP system data
     */
    async gatherXPData(userContext) {
        this.log(`[XPData] Gathering XP system data...`);
        
        try {
            const userId = userContext.user_id || 'anonymous';
            const response = await fetch(`/vidgenerator/api/xp/${userId}`);
            if (response.ok) {
                const xp = await response.json();
                return {
                    level: xp.level || 1,
                    total_xp: xp.total_xp || 0,
                    achievements: xp.achievements || [],
                    trophies: xp.trophies || [],
                    timestamp: new Date().toISOString()
                };
            }
        } catch (error) {
            this.log(`[XPData] Error: ${error.message}`, 'warning');
        }
        
        return {
            level: 1,
            total_xp: 0,
            achievements: [],
            trophies: [],
            timestamp: new Date().toISOString()
        };
    }
    
    /**
     * Gather psychological profile data
     */
    async gatherPsychologicalData(userContext) {
        this.log(`[PsychologicalData] Gathering psychological profile...`);
        
        try {
            const userId = userContext.user_id || 'anonymous';
            const response = await fetch(`/vidgenerator/api/psychological/${userId}`);
            if (response.ok) {
                const profile = await response.json();
                return {
                    profile: profile.profile || {},
                    traits: profile.traits || {},
                    preferences: profile.preferences || {},
                    timestamp: new Date().toISOString()
                };
            }
        } catch (error) {
            this.log(`[PsychologicalData] Error: ${error.message}`, 'warning');
        }
        
        return {
            profile: {},
            traits: {},
            preferences: {},
            timestamp: new Date().toISOString()
        };
    }
    
    /**
     * Gather search data (enhanced searches)
     */
    async gatherSearchData(topic) {
        this.log(`[SearchData] Gathering search data for: ${topic}`);
        
        const searches = [];
        
        // Multiple search variations
        const searchTerms = [
            topic,
            `${topic} history`,
            `${topic} documentary`,
            `${topic} facts`,
            `${topic} overview`
        ];
        
        for (const term of searchTerms) {
            try {
                const results = await this.performSearch(term);
                searches.push({
                    term,
                    results: results.slice(0, 5), // Top 5 results
                    count: results.length
                });
            } catch (error) {
                this.log(`[SearchData] Search error for "${term}": ${error.message}`, 'warning');
            }
        }
        
        return {
            searches,
            total_results: searches.reduce((sum, s) => sum + s.count, 0),
            timestamp: new Date().toISOString()
        };
    }
    
    /**
     * Gather matrix system data
     */
    async gatherMatrixData(topic) {
        this.log(`[MatrixData] Gathering matrix system data...`);
        
        try {
            const response = await fetch(`/vidgenerator/api/matrix/data?topic=${encodeURIComponent(topic)}`);
            if (response.ok) {
                const matrix = await response.json();
                return {
                    nodes: matrix.nodes || [],
                    connections: matrix.connections || [],
                    optimal_path: matrix.optimal_path || [],
                    timestamp: new Date().toISOString()
                };
            }
        } catch (error) {
            this.log(`[MatrixData] Error: ${error.message}`, 'warning');
        }
        
        return {
            nodes: [],
            connections: [],
            optimal_path: [],
            timestamp: new Date().toISOString()
        };
    }
    
    /**
     * Gather emotion system data
     */
    async gatherEmotionData(documentaryData) {
        this.log(`[EmotionData] Gathering emotion system data...`);
        
        try {
            const docId = documentaryData.doc_id || documentaryData.id;
            const response = await fetch(`/vidgenerator/api/emotion/${docId}`);
            if (response.ok) {
                const emotion = await response.json();
                return {
                    profile: emotion.profile || {},
                    triggers: emotion.triggers || [],
                    relations: emotion.relations || [],
                    timestamp: new Date().toISOString()
                };
            }
        } catch (error) {
            this.log(`[EmotionData] Error: ${error.message}`, 'warning');
        }
        
        return {
            profile: {},
            triggers: [],
            relations: [],
            timestamp: new Date().toISOString()
        };
    }
    
    /**
     * Create mega prompt from all gathered data
     */
    createMegaPrompt(gatheredData, documentaryData) {
        this.log(`[MegaPrompt] Creating comprehensive mega prompt...`);
        
        const parts = [];
        
        // 1. Original prompt/topic
        parts.push(`TOPIC: ${documentaryData.topic || documentaryData.prompt}`);
        parts.push('');
        
        // 2. Wikipedia content
        if (gatheredData.web?.wikipedia) {
            parts.push(`WIKIPEDIA CONTENT:`);
            parts.push(`Title: ${gatheredData.web.wikipedia.title || ''}`);
            parts.push(`Content: ${gatheredData.web.wikipedia.content || ''}`);
            parts.push('');
        }
        
        // 3. Images context
        if (gatheredData.web?.images && gatheredData.web.images.length > 0) {
            parts.push(`VISUAL CONTEXT (${gatheredData.web.images.length} images):`);
            gatheredData.web.images.slice(0, 10).forEach((img, idx) => {
                parts.push(`  Image ${idx + 1}: ${img.title || img.description || 'Visual element'}`);
            });
            parts.push('');
        }
        
        // 4. News context
        if (gatheredData.web?.news && gatheredData.web.news.length > 0) {
            parts.push(`NEWS CONTEXT (${gatheredData.web.news.length} articles):`);
            gatheredData.web.news.slice(0, 5).forEach((article, idx) => {
                parts.push(`  Article ${idx + 1}: ${article.title || ''}`);
                parts.push(`    ${article.description || ''}`);
            });
            parts.push('');
        }
        
        // 5. Search results
        if (gatheredData.search?.searches && gatheredData.search.searches.length > 0) {
            parts.push(`SEARCH RESULTS:`);
            gatheredData.search.searches.forEach(search => {
                parts.push(`  Search: "${search.term}" - ${search.count} results`);
            });
            parts.push('');
        }
        
        // 6. Behavioral preferences
        if (gatheredData.behavior?.preferences && Object.keys(gatheredData.behavior.preferences).length > 0) {
            parts.push(`USER PREFERENCES:`);
            parts.push(JSON.stringify(gatheredData.behavior.preferences, null, 2));
            parts.push('');
        }
        
        // 7. XP and achievements
        if (gatheredData.xp) {
            parts.push(`USER LEVEL & ACHIEVEMENTS:`);
            parts.push(`  Level: ${gatheredData.xp.level || 1}`);
            parts.push(`  Total XP: ${gatheredData.xp.total_xp || 0}`);
            if (gatheredData.xp.achievements && gatheredData.xp.achievements.length > 0) {
                parts.push(`  Achievements: ${gatheredData.xp.achievements.join(', ')}`);
            }
            parts.push('');
        }
        
        // 8. Psychological profile
        if (gatheredData.psychological?.traits && Object.keys(gatheredData.psychological.traits).length > 0) {
            parts.push(`PSYCHOLOGICAL PROFILE:`);
            parts.push(JSON.stringify(gatheredData.psychological.traits, null, 2));
            parts.push('');
        }
        
        // 9. Emotion context
        if (gatheredData.emotion?.profile) {
            parts.push(`EMOTION CONTEXT:`);
            parts.push(JSON.stringify(gatheredData.emotion.profile, null, 2));
            if (gatheredData.emotion.triggers && gatheredData.emotion.triggers.length > 0) {
                parts.push(`  Active Triggers: ${gatheredData.emotion.triggers.length}`);
            }
            parts.push('');
        }
        
        // 10. Matrix system path
        if (gatheredData.matrix?.optimal_path && gatheredData.matrix.optimal_path.length > 0) {
            parts.push(`OPTIMAL GENERATION PATH:`);
            parts.push(JSON.stringify(gatheredData.matrix.optimal_path, null, 2));
            parts.push('');
        }
        
        // 11. Stats and quality metrics
        if (gatheredData.stats?.quality_scores && Object.keys(gatheredData.stats.quality_scores).length > 0) {
            parts.push(`QUALITY METRICS:`);
            parts.push(JSON.stringify(gatheredData.stats.quality_scores, null, 2));
            parts.push('');
        }
        
        // 12. Generation instructions
        parts.push(`GENERATION INSTRUCTIONS:`);
        parts.push(`Create engaging video clips that:`);
        parts.push(`- Tell a compelling story about the topic`);
        parts.push(`- Use visual elements from gathered images`);
        parts.push(`- Incorporate recent news and developments`);
        parts.push(`- Match user preferences and psychological profile`);
        parts.push(`- Follow optimal generation path from matrix system`);
        parts.push(`- Apply emotion triggers for enhanced engagement`);
        parts.push(`- Maintain quality standards from previous generations`);
        
        const megaPrompt = parts.join('\n');
        
        this.log(`[MegaPrompt] Created mega prompt: ${megaPrompt.length} characters`);
        
        return megaPrompt;
    }
    
    /**
     * Create data summary
     */
    createDataSummary() {
        return {
            web_sources: {
                wikipedia: this.gatheredData.web?.wikipedia ? 1 : 0,
                images: this.gatheredData.web?.images?.length || 0,
                news: this.gatheredData.web?.news?.length || 0,
                videos: this.gatheredData.web?.videos?.length || 0
            },
            user_data: {
                stats: Object.keys(this.gatheredData.stats || {}).length,
                behavior: Object.keys(this.gatheredData.behavior || {}).length,
                xp: this.gatheredData.xp ? 1 : 0,
                psychological: Object.keys(this.gatheredData.psychological || {}).length
            },
            system_data: {
                search: this.gatheredData.search?.searches?.length || 0,
                matrix: this.gatheredData.matrix ? 1 : 0,
                emotion: this.gatheredData.emotion ? 1 : 0
            },
            total_sources: 8
        };
    }
    
    /**
     * Helper: Fetch Wikipedia
     */
    async fetchWikipedia(topic) {
        try {
            const response = await fetch(`https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(topic)}`);
            if (response.ok) {
                const data = await response.json();
                return {
                    title: data.title,
                    content: data.extract || data.description || '',
                    url: data.content_urls?.desktop?.page || ''
                };
            }
        } catch (error) {
            this.log(`[Wikipedia] Error: ${error.message}`, 'warning');
        }
        return { title: topic, content: `Information about ${topic}` };
    }
    
    /**
     * Helper: Fetch images
     */
    async fetchImages(topic) {
        try {
            // Use Unsplash or similar
            const response = await fetch(`https://api.unsplash.com/search/photos?query=${encodeURIComponent(topic)}&per_page=10&client_id=YOUR_UNSPLASH_KEY`);
            if (response.ok) {
                const data = await response.json();
                return data.results?.map(img => ({
                    url: img.urls?.regular || img.urls?.small,
                    title: img.description || img.alt_description || topic,
                    thumbnail: img.urls?.thumb
                })) || [];
            }
        } catch (error) {
            this.log(`[Images] Error: ${error.message}`, 'warning');
        }
        return [];
    }
    
    /**
     * Helper: Fetch news
     */
    async fetchNews(topic) {
        try {
            const response = await fetch(`https://newsapi.org/v2/everything?q=${encodeURIComponent(topic)}&sortBy=relevancy&pageSize=5&apiKey=YOUR_NEWS_API_KEY`);
            if (response.ok) {
                const data = await response.json();
                return data.articles?.map(article => ({
                    title: article.title,
                    description: article.description,
                    url: article.url,
                    publishedAt: article.publishedAt
                })) || [];
            }
        } catch (error) {
            this.log(`[News] Error: ${error.message}`, 'warning');
        }
        return [];
    }
    
    /**
     * Helper: Fetch videos
     */
    async fetchVideos(topic) {
        // YouTube API would go here
        return [];
    }
    
    /**
     * Helper: Perform search
     */
    async performSearch(term) {
        // Placeholder for search API
        return [];
    }
    
    /**
     * Logging
     */
    log(message, level = 'info') {
        const timestamp = new Date().toISOString();
        const logEntry = { timestamp, level, message };
        this.logBuffer.push(logEntry);
        
        if (this.logBuffer.length > 1000) {
            this.logBuffer = this.logBuffer.slice(-1000);
        }
        
        const prefix = level === 'error' ? '❌' : level === 'warning' ? '⚠️' : 'ℹ️';
        console.log(`${prefix} [MegaGatherer] ${message}`);
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
    self.megaGatherer = new MegaDataGatherer();
}

