/**
 * Frame Extractor for Generator Page
 * Only loads on generator page
 */
(function() {
    'use strict';
    
    // Only initialize if we're on the generator page
    if (!window.location.pathname.includes('/generator')) {
        return;
    }
    
    console.log('[GeneratorFrameExtractor] Initializing frame extractor...');
    
    // Wait for frame extractor script to load
    if (typeof frameExtractor === 'undefined') {
        console.warn('[GeneratorFrameExtractor] frameExtractor not available');
        return;
    }
    
    // Get elements with generator-specific IDs
    const videoInput = document.getElementById('generator-video-url-input');
    const loadVideoBtn = document.getElementById('generator-load-video-btn');
    const videoContainer = document.getElementById('generator-video-container');
    const videoElement = document.getElementById('generator-video');
    const extractionControls = document.getElementById('generator-extraction-controls');
    const frameTimeInput = document.getElementById('generator-frame-time-input');
    const extractSingleBtn = document.getElementById('generator-extract-single-frame-btn');
    const frameIntervalInput = document.getElementById('generator-frame-interval-input');
    const maxFramesInput = document.getElementById('generator-max-frames-input');
    const extractMultipleBtn = document.getElementById('generator-extract-multiple-frames-btn');
    const extractedFramesGrid = document.getElementById('generator-extracted-frames-grid');
    const clearFramesBtn = document.getElementById('generator-clear-frames-btn');
    const toolsSection = document.getElementById('generator-tools-section');
    
    if (!toolsSection) {
        console.warn('[GeneratorFrameExtractor] Tools section not found');
        return;
    }
    
    // Toggle tools section visibility
    const toggleToolsBtn = document.getElementById('toggle-tools-btn');
    const toolsCloseBtn = document.getElementById('tools-close-btn');
    const toolsToggleText = toggleToolsBtn ? toggleToolsBtn.querySelector('.tools-toggle-text') : null;
    
    // Toggle button functionality
    if (toggleToolsBtn) {
        toggleToolsBtn.addEventListener('click', () => {
            const isVisible = toolsSection.style.display !== 'none';
            if (isVisible) {
                toolsSection.style.display = 'none';
                if (toolsToggleText) toolsToggleText.textContent = 'Show Tools';
            } else {
                toolsSection.style.display = 'block';
                if (toolsToggleText) toolsToggleText.textContent = 'Hide Tools';
            }
        });
    }
    
    // Close button functionality
    if (toolsCloseBtn) {
        toolsCloseBtn.addEventListener('click', () => {
            toolsSection.style.display = 'none';
            if (toolsToggleText) toolsToggleText.textContent = 'Show Tools';
        });
    }
    
    // Don't auto-show, let user toggle it
    
    // Tab functionality
    const tabButtons = document.querySelectorAll('.tools-tab-btn');
    const tabContents = document.querySelectorAll('.tools-tab-content');
    
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            
            // Remove active class from all buttons and contents
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Add active class to clicked button and corresponding content
            btn.classList.add('active');
            const targetContent = document.getElementById(`tab-${tabName}`);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });
    
    // Load video
    if (loadVideoBtn && videoInput) {
        loadVideoBtn.addEventListener('click', async () => {
            const input = videoInput.value.trim();
            if (!input) {
                alert('Please enter a video URL or documentary ID');
                return;
            }
            
            try {
                loadVideoBtn.disabled = true;
                loadVideoBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
                
                let videoUrl = input;
                
                // If it's a documentary ID, fetch the video URL
                if (!input.startsWith('http') && !input.startsWith('/')) {
                    const response = await fetch(`/vidgenerator/api/documentary/${input}/video`);
                    if (response.ok) {
                        videoUrl = response.url;
                    } else {
                        throw new Error('Documentary not found');
                    }
                }
                
                videoElement.src = videoUrl;
                videoContainer.style.display = 'block';
                extractionControls.style.display = 'block';
                
                videoElement.addEventListener('loadedmetadata', () => {
                    frameExtractor.init(videoElement);
                    frameTimeInput.max = videoElement.duration;
                    loadVideoBtn.disabled = false;
                    loadVideoBtn.innerHTML = '<i class="fas fa-play"></i> Load Video';
                });
                
            } catch (error) {
                console.error('Failed to load video:', error);
                alert('Failed to load video: ' + error.message);
                loadVideoBtn.disabled = false;
                loadVideoBtn.innerHTML = '<i class="fas fa-play"></i> Load Video';
            }
        });
    }
    
    // Extract single frame
    if (extractSingleBtn && frameTimeInput) {
        extractSingleBtn.addEventListener('click', async () => {
            const time = parseFloat(frameTimeInput.value);
            if (isNaN(time) || time < 0) {
                alert('Please enter a valid time');
                return;
            }
            
            try {
                extractSingleBtn.disabled = true;
                extractSingleBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Extracting...';
                
                const frame = await frameExtractor.extractFrameAtTime(time);
                displayFrame(frame);
                
                extractSingleBtn.disabled = false;
                extractSingleBtn.innerHTML = '<i class="fas fa-image"></i> Extract Frame';
            } catch (error) {
                console.error('Frame extraction failed:', error);
                alert('Failed to extract frame: ' + error.message);
                extractSingleBtn.disabled = false;
                extractSingleBtn.innerHTML = '<i class="fas fa-image"></i> Extract Frame';
            }
        });
    }
    
    // Extract multiple frames
    if (extractMultipleBtn && frameIntervalInput && maxFramesInput) {
        extractMultipleBtn.addEventListener('click', async () => {
            const interval = parseFloat(frameIntervalInput.value);
            const maxFrames = parseInt(maxFramesInput.value);
            
            if (isNaN(interval) || interval < 1) {
                alert('Please enter a valid interval');
                return;
            }
            
            try {
                extractMultipleBtn.disabled = true;
                extractMultipleBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Extracting...';
                
                const frames = await frameExtractor.extractFramesAtIntervals(interval, maxFrames);
                
                frames.forEach(frame => displayFrame(frame));
                
                extractMultipleBtn.disabled = false;
                extractMultipleBtn.innerHTML = '<i class="fas fa-layer-group"></i> Extract Frames';
            } catch (error) {
                console.error('Multiple frame extraction failed:', error);
                alert('Failed to extract frames: ' + error.message);
                extractMultipleBtn.disabled = false;
                extractMultipleBtn.innerHTML = '<i class="fas fa-layer-group"></i> Extract Frames';
            }
        });
    }
    
    // Display frame
    function displayFrame(frame) {
        if (!extractedFramesGrid) return;
        
        const frameDiv = document.createElement('div');
        frameDiv.className = 'frame-item';
        frameDiv.innerHTML = `
            <img src="${frame.dataUrl}" alt="Frame at ${frame.time}s">
            <div class="frame-info">
                <span class="frame-time">${frame.time.toFixed(2)}s</span>
                <button class="btn-download-frame" data-time="${frame.time}">
                    <i class="fas fa-download"></i> Download
                </button>
            </div>
        `;
        
        frameDiv.querySelector('.btn-download-frame').addEventListener('click', () => {
            frameExtractor.downloadFrame(frame, `frame_${frame.time.toFixed(2)}s.png`);
        });
        
        extractedFramesGrid.appendChild(frameDiv);
    }
    
    // Clear frames
    if (clearFramesBtn && extractedFramesGrid) {
        clearFramesBtn.addEventListener('click', () => {
            frameExtractor.clearFrames();
            extractedFramesGrid.innerHTML = '';
        });
    }
    
    console.log('[GeneratorFrameExtractor] Frame extractor initialized');
})();

