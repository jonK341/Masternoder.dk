/**
 * Frame Extractor for Stats Page
 * Moved from generator page to reduce CPU load
 * Extracts frames from videos for analysis
 */

class FrameExtractor {
    constructor() {
        this.canvas = null;
        this.video = null;
        this.isExtracting = false;
        this.extractedFrames = [];
    }
    
    /**
     * Initialize frame extractor with video element
     */
    init(videoElement) {
        this.video = videoElement;
        this.canvas = document.createElement('canvas');
        this.canvas.width = videoElement.videoWidth || 1920;
        this.canvas.height = videoElement.videoHeight || 1080;
    }
    
    /**
     * Extract frame at specific time
     */
    async extractFrameAtTime(timeInSeconds) {
        if (!this.video || !this.canvas) {
            throw new Error('Frame extractor not initialized');
        }
        
        if (this.isExtracting) {
            throw new Error('Frame extraction already in progress');
        }
        
        this.isExtracting = true;
        
        try {
            // Seek to time
            this.video.currentTime = timeInSeconds;
            
            // Wait for seek to complete
            await new Promise((resolve) => {
                const onSeeked = () => {
                    this.video.removeEventListener('seeked', onSeeked);
                    resolve();
                };
                this.video.addEventListener('seeked', onSeeked);
            });
            
            // Draw frame to canvas
            const ctx = this.canvas.getContext('2d');
            ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
            
            // Convert to blob
            const blob = await new Promise((resolve) => {
                this.canvas.toBlob(resolve, 'image/png');
            });
            
            const frame = {
                time: timeInSeconds,
                blob: blob,
                dataUrl: this.canvas.toDataURL('image/png'),
                timestamp: new Date().toISOString()
            };
            
            this.extractedFrames.push(frame);
            this.isExtracting = false;
            
            return frame;
        } catch (error) {
            this.isExtracting = false;
            throw error;
        }
    }
    
    /**
     * Extract multiple frames at intervals
     */
    async extractFramesAtIntervals(intervalSeconds = 5, maxFrames = 10) {
        if (!this.video) {
            throw new Error('Video not initialized');
        }
        
        const duration = this.video.duration;
        const frames = [];
        const times = [];
        
        // Calculate frame times
        for (let i = 0; i < maxFrames && i * intervalSeconds < duration; i++) {
            times.push(i * intervalSeconds);
        }
        
        // Extract frames sequentially to avoid CPU overload
        for (const time of times) {
            try {
                const frame = await this.extractFrameAtTime(time);
                frames.push(frame);
                
                // Small delay between extractions
                await new Promise(resolve => setTimeout(resolve, 100));
            } catch (error) {
                console.error(`Failed to extract frame at ${time}s:`, error);
            }
        }
        
        return frames;
    }
    
    /**
     * Get extracted frames
     */
    getExtractedFrames() {
        return this.extractedFrames;
    }
    
    /**
     * Clear extracted frames
     */
    clearFrames() {
        this.extractedFrames = [];
    }
    
    /**
     * Download frame as image
     */
    downloadFrame(frame, filename = null) {
        const link = document.createElement('a');
        link.href = frame.dataUrl;
        link.download = filename || `frame_${frame.time.toFixed(2)}s.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// Global instance
const frameExtractor = new FrameExtractor();

// Export for use in stats page
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FrameExtractor;
}

