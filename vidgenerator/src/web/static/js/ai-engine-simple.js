/**
 * Simple AI Engine
 * Runs AI generation with Service Worker data gathering
 */
(function() {
    'use strict';
    
    console.log('[AI-Engine] Initializing simple AI engine...');
    
    class SimpleAIEngine {
        constructor() {
            this.serviceWorker = null;
            this.isReady = false;
        }
        
        async initialize() {
            """Initialize AI engine and service worker"""
            try {
                // Wait for service worker
                if ('serviceWorker' in navigator) {
                    const registration = await navigator.serviceWorker.ready;
                    this.serviceWorker = registration.active;
                    console.log('[AI-Engine] Service Worker ready');
                }
                
                // Setup message listener
                if (this.serviceWorker) {
                    navigator.serviceWorker.addEventListener('message', (event) => {
                        this.handleServiceWorkerMessage(event.data);
                    });
                }
                
                this.isReady = true;
                console.log('[AI-Engine] ✓ AI Engine ready');
                return true;
            } catch (error) {
                console.error('[AI-Engine] Initialization failed:', error);
                return false;
            }
        }
        
        async gatherData(prompt, title) {
            """Gather all data via service worker"""
            if (!this.serviceWorker) {
                throw new Error('Service Worker not available');
            }
            
            return new Promise((resolve, reject) => {
                const messageChannel = new MessageChannel();
                const timeout = setTimeout(() => {
                    reject(new Error('Data gathering timeout'));
                }, 30000);
                
                messageChannel.port1.onmessage = (event) => {
                    clearTimeout(timeout);
                    if (event.data.success) {
                        console.log('[AI-Engine] Data gathered:', event.data);
                        resolve(event.data.data || event.data.intelligence);
                    } else {
                        reject(new Error(event.data.error || 'Data gathering failed'));
                    }
                };
                
                this.serviceWorker.postMessage({
                    type: 'GATHER_INTELLIGENCE',
                    prompt: prompt,
                    title: title || prompt
                }, [messageChannel.port2]);
            });
        }
        
        async generate(prompt, title, provider = 'openai') {
            """Generate video using AI with gathered data"""
            try {
                console.log('[AI-Engine] Starting generation...');
                
                // Step 1: Gather data via service worker
                console.log('[AI-Engine] Step 1: Gathering data...');
                const data = await this.gatherData(prompt, title);
                console.log('[AI-Engine] Data gathered:', data);
                
                // Step 2: Create enhanced prompt
                const enhancedPrompt = this.createEnhancedPrompt(prompt, data);
                console.log('[AI-Engine] Enhanced prompt created');
                
                // Step 3: Generate with AI
                console.log('[AI-Engine] Step 2: Generating with AI...');
                const result = await this.callAIProvider(enhancedPrompt, provider, data);
                console.log('[AI-Engine] Generation complete:', result);
                
                return {
                    success: true,
                    data: data,
                    enhanced_prompt: enhancedPrompt,
                    result: result
                };
            } catch (error) {
                console.error('[AI-Engine] Generation failed:', error);
                throw error;
            }
        }
        
        createEnhancedPrompt(originalPrompt, data) {
            """Create enhanced prompt from gathered data"""
            let enhanced = originalPrompt;
            
            if (data) {
                // Add Wikipedia context
                if (data.research?.wikipedia?.extract) {
                    enhanced += `\n\nContext: ${data.research.wikipedia.extract.substring(0, 200)}`;
                }
                
                // Add facts
                if (data.research?.facts && data.research.facts.length > 0) {
                    const facts = data.research.facts.slice(0, 3).map(f => f.content).join(', ');
                    enhanced += `\n\nKey facts: ${facts}`;
                }
                
                // Add keywords
                if (data.keywords && data.keywords.length > 0) {
                    const keywords = data.keywords.slice(0, 5)
                        .map(k => k.english_translation || k.danish_keyword || k)
                        .join(', ');
                    enhanced += `\n\nKeywords: ${keywords}`;
                }
            }
            
            return enhanced;
        }
        
        async callAIProvider(prompt, provider, data) {
            """Call AI provider API"""
            const apiPath = `/vidgenerator/api/documentary/generate`;
            
            const response = await fetch(apiPath, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt: prompt,
                    original_prompt: prompt.split('\n\n')[0], // Get original
                    ai_provider: provider,
                    intelligence: data,
                    settings: {
                        quality: 'high',
                        duration: 10
                    }
                })
            });
            
            if (!response.ok) {
                throw new Error(`AI provider returned ${response.status}`);
            }
            
            return await response.json();
        }
        
        handleServiceWorkerMessage(data) {
            """Handle messages from service worker"""
            if (data.type === 'INTELLIGENCE_GATHERED') {
                console.log('[AI-Engine] Intelligence gathered:', data);
                // Dispatch event
                window.dispatchEvent(new CustomEvent('aiIntelligenceReady', {
                    detail: data
                }));
            }
        }
    }
    
    // Initialize global instance
    window.simpleAIEngine = new SimpleAIEngine();
    
    // Auto-initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.simpleAIEngine.initialize();
        });
    } else {
        window.simpleAIEngine.initialize();
    }
    
    console.log('[AI-Engine] Simple AI Engine loaded');
})();

