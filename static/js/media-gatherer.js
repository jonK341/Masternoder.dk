/**
 * Media Gatherer - Client-side media collection for service worker
 * Collects images and audio from web pages and sends to backend
 */
class MediaGatherer {
    constructor() {
        this.gatheredImages = [];
        this.gatheredAudio = [];
        this.isActive = false;
        this.init();
    }

    init() {
        // Listen for media from service worker
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.addEventListener('message', (event) => {
                if (event.data && event.data.type === 'MEDIA_FOUND') {
                    this.handleMediaFound(event.data);
                }
            });
        }
        
        // Start gathering media from current page
        this.startGathering();
    }

    startGathering() {
        if (this.isActive) return;
        this.isActive = true;
        
        console.log('[MediaGatherer] Starting media gathering...');
        
        // Gather images from current page
        this.gatherImagesFromPage();
        
        // Gather audio from current page
        this.gatherAudioFromPage();
        
        // Listen for new images loaded dynamically
        this.observeNewMedia();
    }

    gatherImagesFromPage() {
        const images = document.querySelectorAll('img');
        images.forEach(img => {
            if (img.src && !img.src.startsWith('data:')) {
                this.collectImage(img.src, {
                    alt: img.alt || '',
                    title: img.title || '',
                    width: img.naturalWidth || img.width,
                    height: img.naturalHeight || img.height
                });
            }
        });
        
        // Also check for background images
        const elements = document.querySelectorAll('*');
        elements.forEach(el => {
            const style = window.getComputedStyle(el);
            const bgImage = style.backgroundImage;
            if (bgImage && bgImage !== 'none') {
                const urlMatch = bgImage.match(/url\(['"]?([^'"]+)['"]?\)/);
                if (urlMatch && urlMatch[1] && !urlMatch[1].startsWith('data:')) {
                    this.collectImage(urlMatch[1], {
                        type: 'background-image',
                        element: el.tagName
                    });
                }
            }
        });
    }

    gatherAudioFromPage() {
        const audioElements = document.querySelectorAll('audio, video');
        audioElements.forEach(el => {
            if (el.src) {
                this.collectAudio(el.src, {
                    type: el.tagName.toLowerCase(),
                    duration: el.duration || 0
                });
            }
            
            // Check for source elements
            const sources = el.querySelectorAll('source');
            sources.forEach(source => {
                if (source.src) {
                    this.collectAudio(source.src, {
                        type: el.tagName.toLowerCase(),
                        codec: source.type || ''
                    });
                }
            });
        });
    }

    observeNewMedia() {
        // Use MutationObserver to detect new media elements
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) { // Element node
                        // Check for images
                        if (node.tagName === 'IMG' && node.src && !node.src.startsWith('data:')) {
                            this.collectImage(node.src, {
                                alt: node.alt || '',
                                title: node.title || ''
                            });
                        }
                        
                        // Check for audio/video
                        if ((node.tagName === 'AUDIO' || node.tagName === 'VIDEO') && node.src) {
                            this.collectAudio(node.src, {
                                type: node.tagName.toLowerCase()
                            });
                        }
                        
                        // Check nested images
                        const nestedImages = node.querySelectorAll && node.querySelectorAll('img');
                        if (nestedImages) {
                            nestedImages.forEach(img => {
                                if (img.src && !img.src.startsWith('data:')) {
                                    this.collectImage(img.src, {
                                        alt: img.alt || '',
                                        title: img.title || ''
                                    });
                                }
                            });
                        }
                    }
                });
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    collectImage(url, metadata = {}) {
        // Avoid duplicates
        if (this.gatheredImages.some(img => img.url === url)) {
            return;
        }
        
        const imageData = {
            url: url,
            metadata: metadata,
            timestamp: Date.now()
        };
        
        this.gatheredImages.push(imageData);
        console.log('[MediaGatherer] Collected image:', url);
        
        // Send to backend
        this.sendMediaToBackend('image', imageData);
    }

    collectAudio(url, metadata = {}) {
        // Avoid duplicates
        if (this.gatheredAudio.some(aud => aud.url === url)) {
            return;
        }
        
        const audioData = {
            url: url,
            metadata: metadata,
            timestamp: Date.now()
        };
        
        this.gatheredAudio.push(audioData);
        console.log('[MediaGatherer] Collected audio:', url);
        
        // Send to backend
        this.sendMediaToBackend('audio', audioData);
    }

    async sendMediaToBackend(type, mediaData) {
        try {
            const endpoint = type === 'image' 
                ? '/api/media/gather-image'
                : '/api/media/gather-audio';
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: mediaData.url,
                    metadata: mediaData.metadata
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log(`[MediaGatherer] ${type} sent to backend:`, result);
            } else {
                console.warn(`[MediaGatherer] Failed to send ${type}:`, response.status);
            }
        } catch (error) {
            console.error(`[MediaGatherer] Error sending ${type}:`, error);
        }
    }

    handleMediaFound(data) {
        if (data.mediaType === 'image') {
            this.collectImage(data.url, data.metadata || {});
        } else if (data.mediaType === 'audio') {
            this.collectAudio(data.url, data.metadata || {});
        }
    }

    getGatheredMedia() {
        return {
            images: this.gatheredImages,
            audio: this.gatheredAudio
        };
    }

    getStatistics() {
        return {
            totalImages: this.gatheredImages.length,
            totalAudio: this.gatheredAudio.length,
            isActive: this.isActive
        };
    }
}

// Initialize media gatherer
let mediaGatherer;
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        mediaGatherer = new MediaGatherer();
        window.mediaGatherer = mediaGatherer;
    });
} else {
    mediaGatherer = new MediaGatherer();
    window.mediaGatherer = mediaGatherer;
}

