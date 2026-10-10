// Fancy Generator - Advanced JavaScript with All Features
// Performance optimized with debounce/throttle

let currentDocumentaryId = null;
let progressInterval = null;
let autoSaveInterval = null;
let draftSaveTimeout = null;
let mp4VerificationScheduled = false;

// Performance: Load utils first (will be available after DOMContentLoaded)
let utilsLoaded = false;

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM loaded, initializing FANCY GENERATOR v3.22.0-performance with optimizations...');
    console.log('🚀 FANCY GENERATOR - Matrix Rain display enabled from 0%');
    console.log('🎬 Matrix Rain: Actual code rain effect with Canvas animation');
    
    // Performance: Initialize utils if available
    if (typeof throttle === 'undefined' || typeof debounce === 'undefined') {
        console.warn('[Performance] Utils not loaded, some optimizations may not work');
    }
    
    // ==========================================
    // EMERGENCY FIX: Create matrix elements if Flask didn't render them
    // ==========================================
    console.log('[Emergency Fix] Checking if matrix elements exist...');
    
    let monitorExists = document.getElementById('matrix-monitor');
    let displayExists = document.getElementById('matrix-processing-display');
    
    if (!monitorExists || !displayExists) {
        console.warn('[Emergency Fix] Matrix elements missing! Creating them dynamically...');
        
        // Find container or body
        const container = document.querySelector('.container') || document.body;
        
        // Create matrix-processing-display if missing
        if (!displayExists) {
            console.log('[Emergency Fix] Creating matrix-processing-display...');
            const matrixDisplay = document.createElement('div');
            matrixDisplay.id = 'matrix-processing-display';
            matrixDisplay.className = 'matrix-processing-display';
            matrixDisplay.innerHTML = `
                <canvas id="matrix-canvas-border" class="matrix-canvas-border"></canvas>
                <div class="matrix-header">
                    <h3><span class="matrix-title">> MATRIX_PROCESSING_MODE_ACTIVE</span></h3>
                    <div class="matrix-status">
                        <span class="matrix-blink">█</span> <span id="matrix-status-text">INITIALIZING</span>
                    </div>
                </div>
                <div class="matrix-container">
                    <div class="matrix-overlay-scan"></div>
                    <div id="matrix-text-field" class="matrix-text-field">
                        <pre id="matrix-code-display" class="matrix-code-display"></pre>
                    </div>
                </div>
                <div class="matrix-stats">
                    <div class="matrix-stat-row">
                        <span class="matrix-label">> ENCODER:</span>
                        <span id="matrix-encoder" class="matrix-value">H.264/AVC</span>
                    </div>
                    <div class="matrix-stat-row">
                        <span class="matrix-label">> BITRATE:</span>
                        <span id="matrix-bitrate" class="matrix-value">Calculating...</span>
                    </div>
                    <div class="matrix-stat-row">
                        <span class="matrix-label">> FRAMES:</span>
                        <span id="matrix-frames" class="matrix-value">0/0</span>
                    </div>
                    <div class="matrix-stat-row">
                        <span class="matrix-label">> FPS:</span>
                        <span id="matrix-fps" class="matrix-value">30</span>
                    </div>
                    <div class="matrix-stat-row">
                        <span class="matrix-label">> RESOLUTION:</span>
                        <span id="matrix-resolution" class="matrix-value">1920x1080</span>
                    </div>
                    <div class="matrix-stat-row">
                        <span class="matrix-label">> CODEC:</span>
                        <span id="matrix-codec" class="matrix-value">libx264</span>
                    </div>
                    <div class="matrix-stat-row">
                        <span class="matrix-label">> BUFFER:</span>
                        <span id="matrix-buffer" class="matrix-value">0 MB</span>
                    </div>
                    <div class="matrix-stat-row">
                        <span class="matrix-label">> CPU:</span>
                        <span id="matrix-cpu" class="matrix-value">--%</span>
                    </div>
                    <div class="matrix-stat-row">
                        <span class="matrix-label">> ELAPSED:</span>
                        <span id="matrix-elapsed" class="matrix-value">00:00</span>
                    </div>
                    <div class="matrix-stat-row">
                        <span class="matrix-label">> ETA:</span>
                        <span id="matrix-eta" class="matrix-value">Calculating...</span>
                    </div>
                    <div class="matrix-stat-row">
                        <span class="matrix-label">> SPEED:</span>
                        <span id="matrix-speed" class="matrix-value">--x</span>
                    </div>
                    <div class="matrix-stat-row">
                        <span class="matrix-label">> PROGRESS:</span>
                        <span id="matrix-progress" class="matrix-value">0.00%</span>
                    </div>
                </div>
            `;
            container.appendChild(matrixDisplay);
            console.log('[Emergency Fix] ✓ matrix-processing-display created!');
        }
        
        // Create matrix-monitor if missing
        if (!monitorExists) {
            console.log('[Emergency Fix] Creating matrix-monitor...');
            const matrixMonitor = document.createElement('div');
            matrixMonitor.id = 'matrix-monitor';
            matrixMonitor.className = 'matrix-monitor glass-panel matrix-active';
            matrixMonitor.setAttribute('data-matrix-active', 'true');
            matrixMonitor.innerHTML = `
                <div class="matrix-monitor-header">
                    <h3><span class="matrix-title" style="text-align: center; width: 100%; display: block;">> MOVIE_WORLD_PORTAL</span></h3>
                    <div class="matrix-status">
                        <span class="matrix-blink">█</span> <span id="monitor-status-text">STANDBY</span>
                    </div>
                </div>
                <div class="matrix-monitor-container">
                    <div id="monitor-requirements" class="monitor-requirements">
                        <h4 class="monitor-section-title">> GENERATION_REQUIREMENTS</h4>
                        <div id="monitor-prompt-display" class="monitor-prompt-display">
                            <span class="monitor-label">> PROMPT:</span>
                            <span id="monitor-prompt" class="monitor-value">--</span>
                        </div>
                        <div id="monitor-title-display" class="monitor-prompt-display">
                            <span class="monitor-label">> TITLE:</span>
                            <span id="monitor-title" class="monitor-value">--</span>
                        </div>
                        <div id="monitor-theme-display" class="monitor-prompt-display">
                            <span class="monitor-label">> ACTIVE_THEME:</span>
                            <span id="monitor-theme" class="monitor-value">--</span>
                        </div>
                        <div id="monitor-emotion-display" class="monitor-prompt-display">
                            <span class="monitor-label">> EMOTIONAL_CONTEXT:</span>
                            <span id="monitor-emotion" class="monitor-value">--</span>
                        </div>
                    </div>
                    <div id="monitor-data-display" class="monitor-data-display">
                        <pre id="monitor-text" class="monitor-text"></pre>
                    </div>
                </div>
                <div class="matrix-monitor-stats">
                    <div class="monitor-stat-section">
                        <h4 class="monitor-section-title">> CLIP_INFORMATION</h4>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> TOTAL_CLIPS:</span>
                            <span id="monitor-total-clips" class="monitor-value">0</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> CURRENT_CLIP:</span>
                            <span id="monitor-current-clip" class="monitor-value">0/0</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> CLIP_DURATION:</span>
                            <span id="monitor-clip-duration" class="monitor-value">0.00s</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> CLIP_SIZE:</span>
                            <span id="monitor-clip-size" class="monitor-value">0 MB</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> CLIP_RESOLUTION:</span>
                            <span id="monitor-clip-resolution" class="monitor-value">--x--</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> CLIP_FPS:</span>
                            <span id="monitor-clip-fps" class="monitor-value">--</span>
                        </div>
                    </div>
                    <div class="monitor-stat-section">
                        <h4 class="monitor-section-title">> COMBINED_VIDEO</h4>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> OUTPUT_FILE:</span>
                            <span id="monitor-output-file" class="monitor-value">--</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> TOTAL_DURATION:</span>
                            <span id="monitor-total-duration" class="monitor-value">0.00s</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> TOTAL_SIZE:</span>
                            <span id="monitor-total-size" class="monitor-value">0 MB</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> COMBINED_RESOLUTION:</span>
                            <span id="monitor-combined-resolution" class="monitor-value">--x--</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> COMBINED_FPS:</span>
                            <span id="monitor-combined-fps" class="monitor-value">--</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> ENCODING_STATUS:</span>
                            <span id="monitor-encoding-status" class="monitor-value">PENDING</span>
                        </div>
                    </div>
                    <div class="monitor-stat-section">
                        <h4 class="monitor-section-title">> CLIP_LIST</h4>
                        <div id="monitor-clip-list" class="monitor-clip-list">
                            <pre id="monitor-clip-details" class="monitor-clip-details">No clips loaded yet...</pre>
                        </div>
                    </div>
                    <div class="monitor-stat-section">
                        <h4 class="monitor-section-title">> SYSTEM_EQUIPMENT</h4>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> CPU_USAGE:</span>
                            <span id="monitor-cpu-usage" class="monitor-value">--%</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> MEMORY_USAGE:</span>
                            <span id="monitor-memory-usage" class="monitor-value">-- MB</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> DISK_SPACE:</span>
                            <span id="monitor-disk-space" class="monitor-value">-- GB</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> NETWORK_STATUS:</span>
                            <span id="monitor-network-status" class="monitor-value">ONLINE</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> BROWSER_INFO:</span>
                            <span id="monitor-browser-info" class="monitor-value">--</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> SCREEN_RESOLUTION:</span>
                            <span id="monitor-screen-res" class="monitor-value">--x--</span>
                        </div>
                    </div>
                    <div class="monitor-stat-section">
                        <h4 class="monitor-section-title">> WEB_DATA_SOURCES</h4>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> API_STATUS:</span>
                            <span id="monitor-api-status" class="monitor-value">CONNECTED</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> SERVER_TIME:</span>
                            <span id="monitor-server-time" class="monitor-value">--</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> ACTIVE_GENERATIONS:</span>
                            <span id="monitor-active-gens" class="monitor-value">0</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> TOTAL_DOCUMENTARIES:</span>
                            <span id="monitor-total-docs" class="monitor-value">--</span>
                        </div>
                    </div>
                    <div class="monitor-stat-section">
                        <h4 class="monitor-section-title">> EDITABLE_MP4_STATUS</h4>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> MP4_FILE:</span>
                            <span id="monitor-editable-mp4" class="monitor-value">--</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> MP4_STATUS:</span>
                            <span id="monitor-mp4-status" class="monitor-value">READY</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> MP4_DURATION:</span>
                            <span id="monitor-mp4-duration" class="monitor-value">0.00s</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> MP4_SIZE:</span>
                            <span id="monitor-mp4-size" class="monitor-value">0 MB</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> EDIT_MODE:</span>
                            <span id="monitor-edit-mode" class="monitor-value">ENABLED</span>
                        </div>
                    </div>
                    <div class="monitor-stat-section">
                        <h4 class="monitor-section-title">> API_KEY_STATUS</h4>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> OPENAI_API:</span>
                            <span id="monitor-api-openai" class="monitor-value">--</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> GOOGLE_CRED:</span>
                            <span id="monitor-api-google" class="monitor-value">--</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> HYPERTXT_API:</span>
                            <span id="monitor-api-hypertxt" class="monitor-value">--</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> VERTECH_API:</span>
                            <span id="monitor-api-vertech" class="monitor-value">--</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> SEAGOAT:</span>
                            <span id="monitor-api-seagoat" class="monitor-value">--</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> FAKE_NEWS:</span>
                            <span id="monitor-api-fakenews" class="monitor-value">--</span>
                        </div>
                    </div>
                    <div class="monitor-stat-section">
                        <h4 class="monitor-section-title">> PERFORMANCE_METRICS</h4>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> PAGE_LOAD_TIME:</span>
                            <span id="monitor-perf-load" class="monitor-value">--ms</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> FPS:</span>
                            <span id="monitor-perf-fps" class="monitor-value">--</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> MEMORY_LEAK:</span>
                            <span id="monitor-perf-memory" class="monitor-value">--MB</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> NETWORK_LATENCY:</span>
                            <span id="monitor-perf-latency" class="monitor-value">--ms</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> CACHE_HIT_RATE:</span>
                            <span id="monitor-perf-cache" class="monitor-value">--%</span>
                        </div>
                    </div>
                    <div class="monitor-stat-section">
                        <h4 class="monitor-section-title">> GENERATION_ANALYTICS</h4>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> AVG_GEN_TIME:</span>
                            <span id="monitor-analytics-avgtime" class="monitor-value">--s</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> SUCCESS_RATE:</span>
                            <span id="monitor-analytics-success" class="monitor-value">--%</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> CLIPS_PER_HOUR:</span>
                            <span id="monitor-analytics-clips" class="monitor-value">--</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> TOTAL_BYTES:</span>
                            <span id="monitor-analytics-bytes" class="monitor-value">--GB</span>
                        </div>
                        <div class="monitor-stat-row">
                            <span class="monitor-label">> THEME_USAGE:</span>
                            <span id="monitor-analytics-theme" class="monitor-value">--</span>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(matrixMonitor);
            console.log('[Emergency Fix] ✓ matrix-monitor created and added to DOM!');
            
            // Force it visible immediately
            matrixMonitor.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; position: relative !important; z-index: 5000 !important;';
            console.log('[Emergency Fix] ✓ Monitor forced visible!');
        }
        
        console.log('[Emergency Fix] ✓ DONE! Matrix elements should now be in DOM!');
    } else {
        console.log('[Emergency Fix] ✓ Matrix elements already exist in DOM!');
    }
    
    // Detect base path (for subdirectory deployment like /vidgenerator/)
    const basePath = (function() {
        const path = window.location.pathname;
        // If path is /vidgenerator/ or /vidgenerator, use that as base
        if (path.startsWith('/vidgenerator')) {
            return '/vidgenerator';
        }
        // Otherwise use empty string for root
        return '';
    })();
    
    console.log('Detected base path:', basePath || '(root)');
    
    // Helper function to build API URLs
    function apiUrl(endpoint) {
        // Remove leading slash if present, then add base path
        endpoint = endpoint.replace(/^\//, '');
        return basePath + '/' + endpoint;
    }
    window.buildApiUrl = apiUrl;
    
    // Get elements with retry mechanism for generate button
    let generateBtn = document.getElementById('generate-btn');
    if (!generateBtn) {
        // Retry after a short delay if element not found
        setTimeout(function() {
            generateBtn = document.getElementById('generate-btn');
            if (generateBtn) {
                console.log('✓ generate-btn found on retry');
                initializeGenerateButton();
            } else {
                console.error('✗ generate-btn not found after retry - button may not exist on this page');
            }
        }, 100);
    }
    
    const promptInput = document.getElementById('prompt-input');
    const fileUpload = document.getElementById('file-upload');
    const uploadFiles = document.getElementById('upload-files');
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const errorMessage = document.getElementById('error-message');
    const videoPanel = document.getElementById('video-panel');
    const videoPlayer = document.getElementById('video-player');
    const downloadBtn = document.getElementById('download-btn');
    const embedBtn = document.getElementById('embed-btn');
    const embedCodeContainer = document.getElementById('embed-code-container');
    const embedCode = document.getElementById('embed-code');
    const progressIcon = document.getElementById('progress-icon');
    const progressPercentage = document.getElementById('progress-percentage');
    const elapsedTimeEl = document.getElementById('elapsed-time');
    const etaTimeEl = document.getElementById('eta-time');
    const progressRateValue = document.getElementById('progress-rate-value');
    
    // Initialize generate button handler
    function initializeGenerateButton() {
        if (!generateBtn) {
            generateBtn = document.getElementById('generate-btn');
        }
        if (generateBtn && !generateBtn.hasAttribute('data-listener-attached')) {
            generateBtn.setAttribute('data-listener-attached', 'true');
            console.log('✓ Initializing generate button event listener');
            attachGenerateButtonHandler();
        }
    }
    
    // New elements for enhanced features
    const settingsPanel = document.getElementById('settings-panel');
    
    // ==========================================
    // SIDEBAR FUNCTIONALITY
    // ==========================================
    initializeSidebars();
    
    // ==========================================
    // CHAT PANEL FUNCTIONALITY
    // ==========================================
    initializeChatPanel();
    
    // ==========================================
    // SETTINGS PANEL FUNCTIONALITY
    // ==========================================
    initializeSettingsPanel();
    
    // ==========================================
    // NETWORK STATUS MONITORING
    // ==========================================
    initializeNetworkMonitoring();
    
    // ==========================================
    // UTILITY TOOLS FUNCTIONALITY
    // ==========================================
    initializeUtilityTools();
    const settingsToggle = document.getElementById('settings-toggle');
    const settingsClose = document.getElementById('settings-close');
    const templatesToggle = document.getElementById('templates-toggle');
    const optionsToggle = document.getElementById('options-toggle');
    const uploadToggle = document.getElementById('upload-toggle');
    const promptCounter = document.getElementById('prompt-counter');
    const titleCounter = document.getElementById('title-counter');
    const descriptionCounter = document.getElementById('description-counter');
    const clearPromptBtn = document.getElementById('clear-prompt');
    const expandPromptBtn = document.getElementById('expand-prompt');
    const generateTitleBtn = document.getElementById('generate-title-btn');
    const tagsInput = document.getElementById('tags-input');
    const tagsContainer = document.getElementById('tags-container');
    const uploadZone = document.getElementById('upload-zone');
    const titleInput = document.getElementById('title-input');
    const descriptionInput = document.getElementById('description-input');
    const successToast = document.getElementById('success-toast');
    const successMessage = document.getElementById('success-message');
    const errorClose = document.getElementById('error-close');
    const videoOverlay = document.getElementById('video-overlay');
    const playOverlayBtn = document.getElementById('play-overlay-btn');
    const fullscreenBtn = document.getElementById('fullscreen-btn');
    const pipBtn = document.getElementById('picture-in-picture-btn');
    const shareBtn = document.getElementById('share-btn');
    const regenerateBtn = document.getElementById('regenerate-btn');
    const copyEmbedBtn = document.getElementById('copy-embed-btn');
    const embedAutoplay = document.getElementById('embed-autoplay');
    const embedControls = document.getElementById('embed-controls');
    const embedLoop = document.getElementById('embed-loop');
    
    // Matrix display elements (for encoding phase)
    // Use let instead of const so we can update if element found later
    let matrixDisplay = document.getElementById('matrix-processing-display');
    let matrixCodeDisplay = document.getElementById('matrix-code-display');
    const matrixStatusText = document.getElementById('matrix-status-text');
    const matrixEncoder = document.getElementById('matrix-encoder');
    const matrixBitrate = document.getElementById('matrix-bitrate');
    const matrixFrames = document.getElementById('matrix-frames');
    const matrixFps = document.getElementById('matrix-fps');
    const matrixResolution = document.getElementById('matrix-resolution');
    const matrixCodec = document.getElementById('matrix-codec');
    const matrixBuffer = document.getElementById('matrix-buffer');
    const matrixCpu = document.getElementById('matrix-cpu');
    const matrixElapsed = document.getElementById('matrix-elapsed');
    const matrixEta = document.getElementById('matrix-eta');
    const matrixSpeed = document.getElementById('matrix-speed');
    const matrixProgress = document.getElementById('matrix-progress');
    
    // Matrix Monitor elements (for clip movie data)
    // Try to get element - may be null if DOM not ready
    const matrixMonitor = document.getElementById('matrix-monitor');
    
    // Debug: Log if monitor element exists
    if (!matrixMonitor) {
        console.warn('[Matrix] matrix-monitor element not found at initialization');
        console.warn('[Matrix] Document readyState:', document.readyState);
        console.warn('[Matrix] Body exists:', !!document.body);
        
        // Try to find it after a delay
        setTimeout(function() {
            const retryMonitor = document.getElementById('matrix-monitor');
            if (retryMonitor) {
                console.log('[Matrix] ✓ Found matrix-monitor on retry');
                window.matrixMonitorRetry = retryMonitor; // Store for later use
            } else {
                console.error('[Matrix] ✗ matrix-monitor still not found after retry');
            }
        }, 100);
    } else {
        console.log('[Matrix] ✓ matrix-monitor found at initialization');
    }
    const monitorText = document.getElementById('monitor-text');
    const monitorStatusText = document.getElementById('monitor-status-text');
    const monitorTotalClips = document.getElementById('monitor-total-clips');
    const monitorCurrentClip = document.getElementById('monitor-current-clip');
    const monitorClipDuration = document.getElementById('monitor-clip-duration');
    const monitorClipSize = document.getElementById('monitor-clip-size');
    const monitorClipResolution = document.getElementById('monitor-clip-resolution');
    const monitorClipFps = document.getElementById('monitor-clip-fps');
    const monitorOutputFile = document.getElementById('monitor-output-file');
    const monitorTotalDuration = document.getElementById('monitor-total-duration');
    const monitorTotalSize = document.getElementById('monitor-total-size');
    const monitorCombinedResolution = document.getElementById('monitor-combined-resolution');
    const monitorCombinedFps = document.getElementById('monitor-combined-fps');
    const monitorEncodingStatus = document.getElementById('monitor-encoding-status');
    const monitorClipDetails = document.getElementById('monitor-clip-details');
    
    // Debug: Check if Matrix elements exist
    console.log('[Matrix] Element check on load:');
    console.log('[Matrix] matrixDisplay:', !!matrixDisplay, matrixDisplay ? matrixDisplay.id : 'NOT FOUND');
    console.log('[Matrix] matrixCodeDisplay:', !!matrixCodeDisplay, matrixCodeDisplay ? matrixCodeDisplay.id : 'NOT FOUND');
    console.log('[Matrix] matrixStatusText:', !!matrixStatusText, matrixStatusText ? matrixStatusText.id : 'NOT FOUND');
    
    // Verify matrixDisplay element exists - if not, log error and try to find it
    if (!matrixDisplay) {
        console.error('[Matrix] ERROR: matrix-processing-display element not found!');
        console.error('[Matrix] Searching for element...');
        const allDisplays = document.querySelectorAll('[id*="matrix"], [class*="matrix"]');
        console.log('[Matrix] Found elements with "matrix" in id/class:', allDisplays.length);
        allDisplays.forEach(function(el, i) {
            console.log('[Matrix] Element', i, ':', el.id || '(no id)', el.className || '(no class)');
        });
        
        // Try to find it again after a delay
        setTimeout(function() {
            const retryMatrixDisplay = document.getElementById('matrix-processing-display');
            if (retryMatrixDisplay) {
                console.log('[Matrix] ✓ Found matrix-processing-display on retry');
                // Update the const reference (can't reassign const, but we can use a workaround)
                window.matrixDisplay = retryMatrixDisplay;
            } else {
                console.error('[Matrix] ✗ Still not found after retry');
            }
        }, 500);
    } else {
        console.log('[Matrix] ✓ matrix-processing-display found successfully');
    }
    
    let matrixCodeBuffer = '';
    let matrixUpdateInterval = null;
    let matrixStats = {
        framesEncoded: 0,
        totalFrames: 0,
        bitrate: 0,
        bufferSize: 0,
        cpuUsage: 0,
        encodingSpeed: 0,
        // New stats
        userIP: '--',
        sessionStartTime: null,
        sessionElapsed: 0,
        totalRequests: 0,
        currentPhase: 'INITIALIZING',
        phaseProgress: 0,
        phaseElapsed: 0,
        phaseETA: null,
        phaseNumber: 0,
        totalPhases: 10,
        memoryUsage: 0,
        diskUsage: 0,
        networkUsage: 0
    };
    
    // Formatting functions for user-friendly display
    function formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
    }
    
    function formatTime(seconds) {
        if (!seconds || seconds === 0) return '0s';
        if (seconds < 60) return Math.round(seconds) + 's';
        const mins = Math.floor(seconds / 60);
        const secs = Math.round(seconds % 60);
        if (mins < 60) return mins + 'm ' + secs + 's';
        const hours = Math.floor(mins / 60);
        const remainingMins = mins % 60;
        return hours + 'h ' + remainingMins + 'm';
    }
    
    function formatNumber(num) {
        if (!num || num === 0) return '0';
        if (num < 1000) return Math.round(num).toString();
        if (num < 1000000) return (num / 1000).toFixed(1) + 'K';
        if (num < 1000000000) return (num / 1000000).toFixed(1) + 'M';
        return (num / 1000000000).toFixed(1) + 'B';
    }
    
    function formatPercent(value, decimals = 2) {
        if (value === null || value === undefined) return '--%';
        return value.toFixed(decimals) + '%';
    }
    
    // Get user IP (will be set from server response)
    function updateUserStats(userIP, userAgent) {
        if (userIP) {
            matrixStats.userIP = userIP;
            console.log('[Stats] User IP updated:', userIP);
        }
        
        const ipEl = document.getElementById('monitor-user-ip');
        if (ipEl) {
            ipEl.textContent = userIP || '--';
            console.log('[Stats] IP element updated:', ipEl.textContent);
        } else {
            console.warn('[Stats] monitor-user-ip element not found!');
        }
        
        const agentEl = document.getElementById('monitor-user-agent');
        if (agentEl && userAgent) {
            // Truncate long user agents
            const shortAgent = userAgent.length > 40 ? userAgent.substring(0, 40) + '...' : userAgent;
            agentEl.textContent = shortAgent;
            agentEl.title = userAgent; // Full text on hover
            console.log('[Stats] User agent updated');
        } else if (agentEl) {
            agentEl.textContent = '--';
        } else {
            console.warn('[Stats] monitor-user-agent element not found!');
        }
        
        // Initialize session start time
        if (!matrixStats.sessionStartTime) {
            matrixStats.sessionStartTime = Date.now();
        }
    }
    
    // Update session stats
    function updateSessionStats() {
        if (matrixStats.sessionStartTime) {
            matrixStats.sessionElapsed = Math.floor((Date.now() - matrixStats.sessionStartTime) / 1000);
            const sessionEl = document.getElementById('monitor-session-time');
            if (sessionEl) {
                const mins = Math.floor(matrixStats.sessionElapsed / 60);
                const secs = matrixStats.sessionElapsed % 60;
                sessionEl.textContent = String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
            } else {
                console.warn('[Stats] monitor-session-time element not found!');
            }
        }
        
        const requestsEl = document.getElementById('monitor-total-requests');
        if (requestsEl) {
            requestsEl.textContent = matrixStats.totalRequests.toString();
        } else {
            console.warn('[Stats] monitor-total-requests element not found!');
        }
    }
    
    // Track phase start time for elapsed calculation
    let currentPhaseStartTime = null;
    let lastPhase = null;
    
    // Update phase stats
    function updatePhaseStats(percent) {
        const phase = getCurrentPhase(percent);
        
        // Track phase changes
        if (phase !== lastPhase) {
            currentPhaseStartTime = Date.now();
            lastPhase = phase;
            console.log('[Phase] Phase changed to:', phase);
        }
        
        matrixStats.currentPhase = phase;
        
        // Calculate phase number (1-10)
        let phaseNum = 1;
        if (percent >= 10) phaseNum = 2;
        if (percent >= 20) phaseNum = 3;
        if (percent >= 30) phaseNum = 4;
        if (percent >= 50) phaseNum = 5;
        if (percent >= 65) phaseNum = 6;
        if (percent >= 70) phaseNum = 7;
        if (percent >= 75) phaseNum = 8;
        if (percent >= 80) phaseNum = 9;
        if (percent >= 90) phaseNum = 10;
        
        matrixStats.phaseNumber = phaseNum;
        
        // Calculate phase progress (0-100% within current phase)
        let phaseStart = 0;
        let phaseEnd = 10;
        if (percent >= 10) { phaseStart = 10; phaseEnd = 20; }
        if (percent >= 20) { phaseStart = 20; phaseEnd = 30; }
        if (percent >= 30) { phaseStart = 30; phaseEnd = 50; }
        if (percent >= 50) { phaseStart = 50; phaseEnd = 65; }
        if (percent >= 65) { phaseStart = 65; phaseEnd = 70; }
        if (percent >= 70) { phaseStart = 70; phaseEnd = 75; }
        if (percent >= 75) { phaseStart = 75; phaseEnd = 80; }
        if (percent >= 80) { phaseStart = 80; phaseEnd = 90; }
        if (percent >= 90) { phaseStart = 90; phaseEnd = 95; }
        if (percent >= 95) { phaseStart = 95; phaseEnd = 100; }
        
        const phaseRange = phaseEnd - phaseStart;
        const phaseProgress = phaseRange > 0 ? ((percent - phaseStart) / phaseRange) * 100 : 100;
        matrixStats.phaseProgress = phaseProgress;
        
        // Calculate phase elapsed time
        if (currentPhaseStartTime) {
            matrixStats.phaseElapsed = Math.floor((Date.now() - currentPhaseStartTime) / 1000);
        }
        
        // Update UI - sync across all tabs (overview, generation, etc.)
        const phaseEls = document.querySelectorAll('#monitor-current-phase, #monitor-current-phase-gen');
        phaseEls.forEach(el => el.textContent = phase);
        
        const phaseProgressEls = document.querySelectorAll('#monitor-phase-progress, #monitor-phase-progress-gen');
        const progressText = formatPercent(phaseProgress, 1);
        phaseProgressEls.forEach(el => el.textContent = progressText);
        
        const phaseNumEl = document.getElementById('monitor-phase-number');
        if (phaseNumEl) phaseNumEl.textContent = phaseNum + '/' + matrixStats.totalPhases;
        
        const phaseElapsedEls = document.querySelectorAll('#monitor-phase-elapsed, #monitor-phase-elapsed-gen');
        const elapsedText = formatTime(matrixStats.phaseElapsed);
        phaseElapsedEls.forEach(el => el.textContent = elapsedText);
        
        // Calculate ETA
        let etaText = '--';
        if (matrixStats.phaseElapsed > 0 && phaseProgress > 0) {
            const estimatedTotal = (matrixStats.phaseElapsed / phaseProgress) * 100;
            const eta = Math.max(0, estimatedTotal - matrixStats.phaseElapsed);
            etaText = formatTime(eta);
        }
        
        const phaseEtaEls = document.querySelectorAll('#monitor-phase-eta, #monitor-phase-eta-gen');
        phaseEtaEls.forEach(el => el.textContent = etaText);
    }
    
    // Update clip stats (total clips, duration, size)
    function updateClipStats(clipCount, totalDuration, totalSize) {
        if (clipCount !== undefined && clipCount !== null) {
            matrixStats.totalClips = clipCount;
            // Sync across all tabs
            const clipEls = document.querySelectorAll('#monitor-total-clips, #monitor-total-clips-clips');
            clipEls.forEach(el => el.textContent = clipCount.toString());
        }
        
        if (totalDuration !== undefined && totalDuration !== null) {
            matrixStats.totalDuration = totalDuration;
            // Sync across all tabs
            const durationEls = document.querySelectorAll('#monitor-total-duration, #monitor-total-duration-gen');
            const durationText = formatTime(totalDuration);
            durationEls.forEach(el => el.textContent = durationText);
        }
        
        if (totalSize !== undefined && totalSize !== null) {
            matrixStats.totalSize = totalSize;
            // Sync across all tabs
            const sizeEls = document.querySelectorAll('#monitor-total-size, #monitor-total-size-gen');
            const sizeText = formatBytes(totalSize);
            sizeEls.forEach(el => el.textContent = sizeText);
        }
    }
    
    // Update resource usage stats (simulated for now, can be enhanced with real data)
    function updateResourceStats(percent) {
        // Simulate memory usage (grows with progress)
        matrixStats.memoryUsage = Math.floor(100 + (percent / 100) * 500); // 100-600 MB
        
        // Simulate disk usage (grows with progress)
        matrixStats.diskUsage = Math.floor(50 + (percent / 100) * 200); // 50-250 MB
        
        // Network usage (varies)
        matrixStats.networkUsage = percent < 65 ? Math.random() * 10 : Math.random() * 50; // 0-10 or 0-50 Mbps
        
        // Update UI
        const memoryEl = document.getElementById('monitor-memory-usage');
        if (memoryEl) memoryEl.textContent = formatBytes(matrixStats.memoryUsage * 1024 * 1024);
        
        const diskEl = document.getElementById('monitor-disk-usage');
        if (diskEl) diskEl.textContent = formatBytes(matrixStats.diskUsage * 1024 * 1024);
        
        const networkEl = document.getElementById('monitor-network-usage');
        if (networkEl) networkEl.textContent = matrixStats.networkUsage.toFixed(1) + ' Mbps';
        
        const cpuEl = document.getElementById('monitor-cpu-usage');
        if (cpuEl) cpuEl.textContent = formatPercent(matrixStats.cpuUsage, 0);
    }
    
    // Initialize particles background
    initParticles();
    
    // Initialize tooltips
    initTooltips();
    
    // Initialize templates
    initTemplates();
    
    // Initialize character counters
    initCharacterCounters();
    
    // Initialize settings panel
    initSettingsPanel();
    
    // Initialize session start time
    matrixStats.sessionStartTime = Date.now();
    
    // Start session stats update interval (updates every second)
    setInterval(function() {
        updateSessionStats();
    }, 1000);
    
    // Initialize stats display on page load
    function initializeStatsDisplay() {
        console.log('[Stats] Initializing stats display...');
        
        // Check if all stats elements exist
        const requiredElements = [
            'monitor-user-ip',
            'monitor-session-time',
            'monitor-user-agent',
            'monitor-total-requests',
            'monitor-current-phase',
            'monitor-phase-progress',
            'monitor-memory-usage',
            'monitor-disk-usage',
            'monitor-cpu-usage',
            'monitor-network-usage'
        ];
        
        let foundCount = 0;
        for (const id of requiredElements) {
            const el = document.getElementById(id);
            if (el) {
                foundCount++;
                console.log(`[Stats] ✓ Found element: ${id}`);
            } else {
                console.warn(`[Stats] ✗ Missing element: ${id}`);
            }
        }
        
        console.log(`[Stats] Found ${foundCount}/${requiredElements.length} stats elements`);
        
        // Initialize all stats to default values
        updateUserStats(null, null);
        updatePhaseStats(0);
        updateResourceStats(0);
        updateSessionStats();
        
        // Make sure monitor stats are visible
        const monitorStats = document.querySelector('.matrix-monitor-stats');
        if (monitorStats) {
            monitorStats.style.display = 'grid';
            monitorStats.style.visibility = 'visible';
            monitorStats.style.opacity = '1';
            console.log('[Stats] ✓ Monitor stats container initialized and made visible');
        } else {
            console.error('[Stats] ✗ .matrix-monitor-stats container not found!');
        }
        
        // Make sure all stat sections are visible
        const statSections = document.querySelectorAll('.monitor-stat-section');
        console.log(`[Stats] Found ${statSections.length} stat sections`);
        statSections.forEach((section, index) => {
            section.style.display = 'flex';
            section.style.visibility = 'visible';
            section.style.opacity = '1';
            const title = section.querySelector('.monitor-section-title');
            console.log(`[Stats] Section ${index + 1}: ${title ? title.textContent : 'No title'}`);
        });
    }
    
    // Initialize stats when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeStatsDisplay);
    } else {
        initializeStatsDisplay();
    }
    
    // Initialize collapse toggles
    initCollapseToggles();
    
    // Initialize drag and drop
    initDragAndDrop();
    
    // Initialize tags system
    initTagsSystem();
    
    // Initialize auto-save
    initAutoSave();
    
    // Initialize video controls
    initVideoControls();
    
    // Initialize keyboard shortcuts
    initKeyboardShortcuts();
    
    // Initialize prompt suggestions
    initPromptSuggestions();
    
    // FORCE ACTIVATE ALL ELEMENTS - IMMEDIATELY ON PAGE LOAD
    function forceActivateAllElements() {
        console.log('[ForceActivate] ==========================================');
        console.log('[ForceActivate] FORCING ALL ELEMENTS VISIBLE NOW');
        console.log('[ForceActivate] ==========================================');
        
        // Force Monitor visible - NUCLEAR OPTION
        // Try multiple methods to find the element
        let monitorEl = document.getElementById('matrix-monitor');
        
        // If not found, try querySelector
        if (!monitorEl) {
            monitorEl = document.querySelector('#matrix-monitor');
        }
        
        // If still not found, try querySelector with class
        if (!monitorEl) {
            monitorEl = document.querySelector('.matrix-monitor');
        }
        
        // If still not found, wait a bit and try again
        if (!monitorEl) {
            console.warn('[ForceActivate] Monitor element not found immediately, waiting...');
            
            // Try again after a short delay
            setTimeout(function() {
                monitorEl = document.getElementById('matrix-monitor');
                if (monitorEl) {
                    console.log('[ForceActivate] ✓ Found monitor on retry');
                    forceShowMonitorElement(monitorEl);
                } else {
                    console.error('[ForceActivate] ✗ Monitor element still not found after retry!');
                    console.error('[ForceActivate] DOM state:', {
                        bodyExists: !!document.body,
                        readyState: document.readyState,
                        allDivs: document.querySelectorAll('div').length,
                        allIds: Array.from(document.querySelectorAll('[id]')).map(el => el.id).slice(0, 20)
                    });
                }
            }, 200);
            return; // Exit early if element not found
        }
        
        // Element found, force it visible
        forceShowMonitorElement(monitorEl);
        
        function forceShowMonitorElement(el) {
            if (!el) {
                console.error('[ForceActivate] forceShowMonitorElement called with null element!');
                return;
            }
            
            console.log('[ForceActivate] ✓ Monitor element found:', el.id || '(no id)', el.className || '(no class)');
            
            // Remove ALL styles first
            el.removeAttribute('style');
            
            // FORCE with ALL methods
            el.style.setProperty('display', 'block', 'important');
            el.style.setProperty('visibility', 'visible', 'important');
            el.style.setProperty('opacity', '1', 'important');
            el.style.setProperty('position', 'relative', 'important');
            el.style.setProperty('z-index', '5000', 'important');
            el.style.setProperty('width', '100%', 'important');
            
            // Also set directly (backup)
            el.style.display = 'block';
            el.style.visibility = 'visible';
            el.style.opacity = '1';
            el.style.position = 'relative';
            el.style.zIndex = '5000';
            
            // Add classes and attributes
            el.classList.add('matrix-active');
            el.setAttribute('data-matrix-active', 'true');
            
            // Verify visibility immediately
            setTimeout(function() {
                const computed = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                console.log('[ForceActivate] Monitor verification:');
                console.log('[ForceActivate] - Computed display:', computed.display);
                console.log('[ForceActivate] - Computed visibility:', computed.visibility);
                console.log('[ForceActivate] - Computed opacity:', computed.opacity);
                console.log('[ForceActivate] - Element size:', rect.width, 'x', rect.height);
                console.log('[ForceActivate] - Visible?', rect.width > 0 && rect.height > 0);
                
                if (computed.display === 'none' || rect.width === 0) {
                    console.error('[ForceActivate] CRITICAL: Monitor still hidden! Using nuclear option...');
                    // Nuclear option: set CSS text directly
                    el.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; position: relative !important; z-index: 5000 !important; width: 100% !important;';
                }
            }, 100);
            
            console.log('[ForceActivate] ✓ Monitor forced visible');
            
            // Also call window.showMonitor if it exists
            if (typeof window.showMonitor === 'function') {
                setTimeout(function() {
                    window.showMonitor();
                }, 50);
            }
        }
        
        // Force Theme Background Image visible
        const bgImage = document.getElementById('theme-background-image');
        if (bgImage) {
            bgImage.style.setProperty('display', 'block', 'important');
            bgImage.style.setProperty('visibility', 'visible', 'important');
            bgImage.style.setProperty('opacity', '0.15', 'important');
            console.log('[ForceActivate] ✓ Background image forced visible');
        }
        
        // Force Theme Background Video container ready
        const bgVideo = document.getElementById('theme-background-video');
        if (bgVideo) {
            bgVideo.style.setProperty('display', 'block', 'important');
            bgVideo.style.setProperty('visibility', 'visible', 'important');
            console.log('[ForceActivate] ✓ Background video container ready');
        }
        
        // Force MasterNoder2 Commercial visible
        const mn2Commercial = document.getElementById('masternoder2-commercial');
        if (mn2Commercial) {
            mn2Commercial.style.setProperty('display', 'block', 'important');
            mn2Commercial.style.setProperty('visibility', 'visible', 'important');
            mn2Commercial.style.setProperty('opacity', '1', 'important');
            console.log('[ForceActivate] ✓ MasterNoder2 commercial forced visible');
        }
        
        // Verify Fancy Title has flame effects
        const fancyTitle = document.querySelector('.fancy-title');
        if (fancyTitle) {
            const computed = window.getComputedStyle(fancyTitle, '::before');
            console.log('[ForceActivate] ✓ Fancy title found');
            console.log('[ForceActivate] Title font-size:', window.getComputedStyle(fancyTitle).fontSize);
        }
        
        console.log('[ForceActivate] ==========================================');
    }
    
    // Force activate immediately on DOM ready
    function ensureDOMReady(callback) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', callback);
        } else if (document.readyState === 'interactive' || document.readyState === 'complete') {
            // DOM is ready, but wait a bit for all elements to be parsed
            setTimeout(callback, 100);
        } else {
            callback();
        }
    }
    
    // Ensure DOM is fully ready before trying to find elements
    ensureDOMReady(function() {
        console.log('[ForceActivate] DOM ready, document.readyState:', document.readyState);
        console.log('[ForceActivate] Body exists:', !!document.body);
        console.log('[ForceActivate] Total divs in DOM:', document.querySelectorAll('div').length);
        forceActivateAllElements();
    });
    
    // Also force activate after delays to catch late-loading elements
    setTimeout(function() {
        console.log('[ForceActivate] Retry 1 (500ms), document.readyState:', document.readyState);
        forceActivateAllElements();
    }, 500);
    
    setTimeout(function() {
        console.log('[ForceActivate] Retry 2 (1000ms), document.readyState:', document.readyState);
        forceActivateAllElements();
    }, 1000);
    
    // One more retry after a longer delay
    setTimeout(function() {
        console.log('[ForceActivate] Retry 3 (2000ms), document.readyState:', document.readyState);
        forceActivateAllElements();
    }, 2000);
    
    // Initialize theme system and Matrix rain immediately
    setTimeout(function() {
        if (typeof initThemeSystem === 'function') {
            initThemeSystem();
        }
        // Initialize MasterNoder2 Commercial
        if (typeof initMasterNoder2Commercial === 'function') {
            initMasterNoder2Commercial();
        }
        // Force activate again after theme init
        forceActivateAllElements();
        
        // Initialize Matrix rain background immediately if Matrix theme is active
        // This ensures the rain effect is visible from 0% progress
        setTimeout(function() {
            const savedTheme = localStorage.getItem('documentaryTheme') || 'matrix';
            if (savedTheme === 'matrix' || !savedTheme) {
                console.log('[Matrix Rain] Initializing rain background immediately on page load');
                if (typeof initMatrixRainBackground === 'function' && !matrixRainAnimationFrame) {
                    initMatrixRainBackground();
                }
            }
        }, 200);
        
        // Initialize Movie World Portal with real data
        setTimeout(function() {
            if (typeof initializeMovieWorldPortal === 'function') {
                initializeMovieWorldPortal();
                console.log('[Movie World Portal] Initialized with real data gathering');
            }
        }, 500);
    }, 100);
    
    // Load draft from localStorage
    loadDraft();
    
    // Matrix display elements (defined early for use)
    // Matrix will be initialized when encoding phase starts (65-80%)
    
    // Progress messages with emojis for different stages
    const progressMessages = {
        initializing: { icon: '🚀', text: '🚀 Initializing documentary generation system...' },
        scraping: { icon: '🌐', text: '🌐 Searching the web for images and scripts...' },
        analyzing: { icon: '🔍', text: '🔍 Analyzing your prompt and gathering information...' },
        creating: [
            { icon: '🎬', text: '🎬 Creating video content and scenes...' },
            { icon: '🎥', text: '🎥 Crafting cinematic moments frame by frame...' },
            { icon: '✨', text: '✨ Weaving magic into every scene...' },
            { icon: '🎭', text: '🎭 Directing AI actors in spectacular performances...' },
            { icon: '🌟', text: '🌟 Bringing your vision to life with stunning visuals...' },
            { icon: '🎪', text: '🎪 Choreographing an epic visual symphony...' },
            { icon: '🎨', text: '🎨 Painting cinematic masterpieces pixel by pixel...' },
            { icon: '🔥', text: '🔥 Igniting creative sparks into explosive content...' },
            { icon: '⚡', text: '⚡ Charging up the ultimate video experience...' },
            { icon: '🌊', text: '🌊 Riding waves of creative inspiration...' },
            { icon: '🌌', text: '🌌 Exploring the universe of possibilities...' },
            { icon: '🎪', text: '🎪 Juggling multiple AI engines for maximum impact...' },
            { icon: '🎯', text: '🎯 Hitting the perfect shot every time...' },
            { icon: '💎', text: '💎 Polishing gems of visual storytelling...' },
            { icon: '🚁', text: '🚁 Soaring to new heights of creativity...' },
            { icon: '🎲', text: '🎲 Rolling the dice of cinematic fortune...' },
            { icon: '🎸', text: '🎸 Striking the right chord with your audience...' },
            { icon: '🎺', text: '🎺 Orchestrating a visual concert...' },
            { icon: '🦄', text: '🦄 Creating something truly magical and unique...' },
            { icon: '🌈', text: '🌈 Splashing vibrant colors across the screen...' }
        ],
        generating: { icon: '✨', text: '✨ Generating AI-powered video content...' },
        // Processing messages mapped to specific operations (message_keys from backend)
        processing: {
            // Clip loading and combining operations
            'loading_clips': { icon: '🎞️', text: '🎞️ Loading video clips from storage...' },
            'combining_clips': { icon: '🎬', text: '🎬 Merging cinematic moments together...' },
            'rendering_frames': { icon: '⚙️', text: '⚙️ Concatenating video clips...' },
            // Encoding video operations (backend sends detailed messages with timer)
            'encoding_video': { icon: '⚡', text: '⚡ Processing and rendering video segments (encoding with H.264 codec)...' },
            'video_written': { icon: '✅', text: '✅ Video encoding complete!' },
            // Audio operations
            'generating_tts': { icon: '🎙️', text: '🎙️ Generating narration with TTS...' },
            'syncing_audio': { icon: '🎵', text: '🎵 Synchronizing audio and video...' },
            'audio_mixed': { icon: '✅', text: '✅ Audio mixed successfully!' },
            // Other operations
            'creating_thumbnail': { icon: '🖼️', text: '🖼️ Creating thumbnail image...' },
            'preparing_embed': { icon: '📦', text: '📦 Preparing video for embedding...' },
            'uploading_storage': { icon: '☁️', text: '☁️ Uploading to external storage...' },
            // Default fallback message
            'default': { icon: '⚙️', text: '⚙️ Processing and rendering video segments...' }
        },
        editing: { icon: '✂️', text: '✂️ Editing and combining video clips...' },
        adding_audio: { icon: '🎵', text: '🎵 Adding narration and background music...' },
        finalizing: { icon: '🎨', text: '🎨 Finalizing and optimizing output quality...' },
        completed: { icon: '🎉', text: '🎉 Documentary generation complete! Ready to watch!' },
        failed: { icon: '❌', text: '❌ Generation failed. Please try again.' }
    };
    
    // Advanced ETA tracking
    let generationStartTime = null;
    let lastProgressPercent = 0;
    let lastProgressUpdateTime = null;
    let progressHistory = []; // Array of {time, percent} for ETA calculation
    let averageProgressRate = 0; // Average percent per second
    let stagnationStartTime = null; // When progress stopped increasing
    let lastStagnationCheck = 0;
    
    // Debug: Check if all elements are found
    if (!generateBtn) {
        console.error('ERROR: generate-btn not found!');
    } else {
        console.log('✓ generate-btn found');
    }
    if (!promptInput) {
        console.error('ERROR: prompt-input not found!');
    } else {
        console.log('✓ prompt-input found');
    }
    if (!progressIcon) {
        console.warn('WARNING: progress-icon not found!');
    }
    if (!progressText) {
        console.warn('WARNING: progress-text not found!');
    }
    if (!progressContainer) {
        console.warn('WARNING: progress-container not found!');
    }
    if (!errorMessage) {
        console.warn('WARNING: error-message not found!');
    }

    // File upload display
    if (fileUpload && uploadFiles) {
        fileUpload.addEventListener('change', function() {
            const files = Array.from(this.files);
            if (files.length > 0) {
                uploadFiles.innerHTML = `<strong>Selected files:</strong> ${files.map(f => f.name).join(', ')}`;
            } else {
                uploadFiles.innerHTML = '';
            }
        });
    }

    // Generate button click - initialize handler
    if (generateBtn) {
        initializeGenerateButton();
    } else {
        // If button not found, try again after DOM is fully loaded
        window.addEventListener('load', function() {
            generateBtn = document.getElementById('generate-btn');
            if (generateBtn) {
                initializeGenerateButton();
            }
        });
    }
    
    // Attach the actual click handler
    function attachGenerateButtonHandler() {
        if (!generateBtn) {
            generateBtn = document.getElementById('generate-btn');
        }
        if (!generateBtn) {
            console.error('Cannot attach handler: generate-btn not found');
            return;
        }
        
        generateBtn.addEventListener('click', async function(e) {
            console.log('Generate button clicked!');
            e.preventDefault();
            e.stopPropagation();
            
            // ==========================================
            // FORCE SHOW MONITOR IMMEDIATELY - FIRST THING
            // ==========================================
            console.log('[Monitor] ==========================================');
            console.log('[Monitor] GENERATE BUTTON CLICKED - SHOWING MONITOR NOW');
            console.log('[Monitor] ==========================================');
            
            // Show monitor BEFORE anything else
            if (typeof window.showMonitor === 'function') {
                window.showMonitor();
            }
            
            const monitorEl = document.getElementById('matrix-monitor');
            if (monitorEl) {
                // Remove ALL inline styles that might hide it
                monitorEl.removeAttribute('style');
                
                // FORCE with setProperty (strongest method)
                monitorEl.style.setProperty('display', 'block', 'important');
                monitorEl.style.setProperty('visibility', 'visible', 'important');
                monitorEl.style.setProperty('opacity', '1', 'important');
                monitorEl.style.setProperty('position', 'relative', 'important');
                monitorEl.style.setProperty('z-index', '5000', 'important');
                
                // Also set directly (backup)
                monitorEl.style.display = 'block';
                monitorEl.style.visibility = 'visible';
                monitorEl.style.opacity = '1';
                monitorEl.style.position = 'relative';
                monitorEl.style.zIndex = '5000';
                
                // Add classes and attributes
                monitorEl.classList.add('matrix-active');
                monitorEl.setAttribute('data-matrix-active', 'true');
                
                console.log('[Monitor] ✓ Monitor forced visible in button handler');
                
                // Verify immediately
                setTimeout(function() {
                    const computed = window.getComputedStyle(monitorEl);
                    const rect = monitorEl.getBoundingClientRect();
                    console.log('[Monitor] Verification:');
                    console.log('[Monitor] - Display:', computed.display);
                    console.log('[Monitor] - Visibility:', computed.visibility);
                    console.log('[Monitor] - Opacity:', computed.opacity);
                    console.log('[Monitor] - Size:', rect.width, 'x', rect.height);
                    console.log('[Monitor] - Visible?', rect.width > 0 && rect.height > 0);
                    console.log('[Monitor] - Computed z-index:', computed.zIndex);
                    
                    // If still not visible, use nuclear option
                    if (computed.display === 'none' || rect.width === 0) {
                        console.error('[Monitor] NUCLEAR OPTION: Still hidden, forcing with all methods');
                        monitorEl.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; position: relative !important; z-index: 5000 !important; width: 100% !important;';
                    }
                }, 100);
            } else {
                console.error('[Monitor] ERROR: matrix-monitor element not found!');
                // Try to find any monitor-related element
                const allMonitors = document.querySelectorAll('[id*="monitor"], [class*="monitor"]');
                console.log('[Monitor] Found elements with "monitor":', allMonitors.length);
            }
            
            const prompt = promptInput ? promptInput.value.trim() : '';
            const titleInput = document.getElementById('title-input');
            const descriptionInput = document.getElementById('description-input');
            const title = titleInput ? titleInput.value.trim() : '';
            const description = descriptionInput ? descriptionInput.value.trim() : '';
            const files = fileUpload ? fileUpload.files : [];
            
            // Update Monitor with requirements (prompt, title, theme, emotion) - IMMEDIATELY
            if (typeof window.updateMonitorRequirements === 'function') {
                window.updateMonitorRequirements(prompt, title, currentTheme, 'analyzing...');
            }

            console.log('Prompt:', prompt);
            console.log('Title:', title);
            console.log('Description:', description);

            if (!prompt) {
                console.warn('No prompt entered');
                showError('Please enter a prompt for the documentary.');
                return;
            }

            // Disable button
            generateBtn.disabled = true;
            generateBtn.textContent = 'Generating...';
            hideError();
            
            // Initialize advanced ETA tracking
            generationStartTime = Date.now();
            lastProgressPercent = 0;
            lastProgressUpdateTime = Date.now();
            progressHistory = [];
            averageProgressRate = 0;
            stagnationStartTime = null;
            lastStagnationCheck = 0;
            
            console.log('[Progress] Showing initial progress at 0%');
            
            // IMMEDIATELY show Matrix display when generation starts
            if (matrixDisplay) {
                console.log('[Matrix] Generation starting - showing Matrix display immediately');
                matrixDisplay.removeAttribute('style');
                matrixDisplay.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; position: relative !important; z-index: 10000 !important;';
                matrixDisplay.classList.add('matrix-active');
                matrixDisplay.setAttribute('data-matrix-active', 'true');
                
                // Initialize Matrix display immediately
                if (!matrixUpdateInterval) {
                    initMatrixDisplay();
                }
            }
            
            // START Matrix rain background when generation begins
            if (typeof initMatrixRainBackground === 'function' && !matrixRainAnimationFrame) {
                console.log('[Matrix Rain] Starting rain effect on generation start');
                initMatrixRainBackground();
            }
            
            // Show Matrix Monitor immediately when generation starts
            console.log('[Monitor] ==========================================');
            console.log('[Monitor] GENERATION STARTING - SHOWING MONITOR NOW');
            console.log('[Monitor] ==========================================');
            
            function forceShowMonitor() {
                const monitorEl = document.getElementById('matrix-monitor');
                if (!monitorEl) {
                    console.error('[Monitor] CRITICAL ERROR: matrix-monitor element NOT FOUND in DOM!');
                    console.error('[Monitor] Searching for element...');
                    const allDivs = document.querySelectorAll('div');
                    for (let div of allDivs) {
                        if (div.id && div.id.includes('monitor')) {
                            console.log('[Monitor] Found div with id:', div.id);
                        }
                    }
                    return;
                }
                
                console.log('[Monitor] ✓ Found monitor element');
                console.log('[Monitor] Current inline style:', monitorEl.getAttribute('style'));
                console.log('[Monitor] Current classes:', monitorEl.className);
                
                // REMOVE ALL STYLES THAT MIGHT HIDE IT
                monitorEl.removeAttribute('style');
                
                // FORCE VISIBILITY WITH ALL METHODS POSSIBLE
                monitorEl.style.setProperty('display', 'block', 'important');
                monitorEl.style.setProperty('visibility', 'visible', 'important');
                monitorEl.style.setProperty('opacity', '1', 'important');
                monitorEl.style.setProperty('position', 'relative', 'important');
                monitorEl.style.setProperty('z-index', '5000', 'important');
                
                // Also set directly (backup method)
                monitorEl.style.display = 'block';
                monitorEl.style.visibility = 'visible';
                monitorEl.style.opacity = '1';
                
                // Add classes and attributes
                monitorEl.classList.add('matrix-active');
                monitorEl.setAttribute('data-matrix-active', 'true');
                
                // Force via CSS class
                monitorEl.className = monitorEl.className + ' matrix-active';
                
                // Verify visibility IMMEDIATELY
                setTimeout(function() {
                    const computed = window.getComputedStyle(monitorEl);
                    const rect = monitorEl.getBoundingClientRect();
                    console.log('[Monitor] ==========================================');
                    console.log('[Monitor] VERIFICATION:');
                    console.log('[Monitor] Computed display:', computed.display);
                    console.log('[Monitor] Computed visibility:', computed.visibility);
                    console.log('[Monitor] Computed opacity:', computed.opacity);
                    console.log('[Monitor] Computed z-index:', computed.zIndex);
                    console.log('[Monitor] Element size:', rect.width, 'x', rect.height);
                    console.log('[Monitor] Element position:', rect.top, rect.left);
                    console.log('[Monitor] Element visible?', rect.width > 0 && rect.height > 0);
                    console.log('[Monitor] ==========================================');
                    
                    if (computed.display === 'none') {
                        console.error('[Monitor] CRITICAL: Still hidden! Trying nuclear option...');
                        // Nuclear option: remove and re-add
                        const parent = monitorEl.parentElement;
                        const clone = monitorEl.cloneNode(true);
                        monitorEl.remove();
                        parent.appendChild(clone);
                        clone.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; position: relative !important; z-index: 5000 !important;';
                        clone.classList.add('matrix-active');
                        clone.setAttribute('data-matrix-active', 'true');
                    }
                }, 50);
                
                // Update monitor status
                const statusEl = document.getElementById('monitor-status-text');
                if (statusEl) {
                    statusEl.textContent = 'INITIALIZING';
                    console.log('[Monitor] ✓ Status updated to INITIALIZING');
                } else {
                    console.warn('[Monitor] WARNING: monitor-status-text not found');
                }
                
                const monitorTextEl = document.getElementById('monitor-text');
                if (monitorTextEl) {
                    monitorTextEl.textContent = '';
                    const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
                    monitorTextEl.textContent = `[${timestamp}] > SYSTEM_BOOT: Initializing Matrix Monitor...\n`;
                    monitorTextEl.scrollTop = monitorTextEl.scrollHeight;
                    console.log('[Monitor] ✓ Monitor text initialized');
                } else {
                    console.warn('[Monitor] WARNING: monitor-text not found');
                }
                
                // Initialize border rain if not already
                if (typeof initMatrixCanvasBorder === 'function') {
                    setTimeout(function() {
                        initMatrixCanvasBorder();
                        if (typeof startMatrixRainBorder === 'function') {
                            startMatrixRainBorder();
                        }
                    }, 200);
                }
            }
            
            // Show monitor IMMEDIATELY
            forceShowMonitor();
            
            // Also call window.showMonitor if it exists (backup)
            if (typeof window.showMonitor === 'function') {
                setTimeout(function() {
                    window.showMonitor();
                }, 100);
            }
            
            showProgress(0, progressMessages.initializing.text, progressMessages.initializing.icon);

        try {
            // Prepare form data if files are selected
            const formData = new FormData();
            if (files.length > 0) {
                Array.from(files).forEach(file => {
                    formData.append('files', file);
                });
            }

            // Prepare request data
            const requestData = {
                prompt: prompt,
                title: title || prompt.substring(0, 100),
                description: description,
                attributes: {}
            };

            // Send generation request
            const generateUrl = apiUrl('api/documentary/generate');
            console.log('Sending request to:', generateUrl);
            console.log('Request data:', requestData);
            
            let response;
            try {
                response = await fetch(generateUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                });
                
                console.log('Response status:', response.status);
                console.log('Response ok:', response.ok);
                console.log('Response headers:', Object.fromEntries(response.headers.entries()));
            } catch (fetchError) {
                console.error('Fetch error:', fetchError);
                throw new Error('Network error: Could not connect to server. ' + fetchError.message);
            }

            let result;
            try {
                const responseText = await response.text();
                console.log('Response text:', responseText);
                
                // Check if response is actually JSON before parsing
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    result = JSON.parse(responseText);
                    console.log('Parsed result:', result);
                } else {
                    // Not JSON, return error with status
                    throw new Error('Server returned non-JSON response. Status: ' + response.status);
                }
            } catch (parseError) {
                console.error('Parse error:', parseError);
                if (parseError.message.includes('non-JSON')) {
                    throw parseError;
                }
                throw new Error('Server returned invalid JSON. Status: ' + response.status);
            }

            if (!response.ok) {
                throw new Error(result.error || 'Generation failed');
            }

            if (result.success) {
                currentDocumentaryId = result.documentary_id;
                window.currentDocumentaryId = currentDocumentaryId;
                console.log('[Progress] Generation started successfully, documentary_id:', currentDocumentaryId);
                
                // Dispatch generation started event for XP tracking
                if (typeof window.dispatchEvent === 'function') {
                    window.dispatchEvent(new CustomEvent('generationStarted', {
                        detail: {
                            documentary_id: currentDocumentaryId,
                            prompt: prompt,
                            title: title
                        }
                    }));
                }
                
                // Start polling for progress
                console.log('[Progress] About to call startProgressPolling...');
                try {
                    startProgressPolling(result.documentary_id);
                    console.log('[Progress] startProgressPolling called successfully');
                } catch (pollError) {
                    console.error('[Progress] ERROR calling startProgressPolling:', pollError);
                }
            } else {
                throw new Error(result.message || 'Generation failed');
            }

        } catch (error) {
            console.error('Generation error:', error);
            console.error('Error stack:', error.stack);
            showError(error.message || 'An error occurred during generation.');
            hideProgress();
            if (generateBtn) {
                generateBtn.disabled = false;
                const btnContent = generateBtn.querySelector('.btn-content');
                if (btnContent) {
                    const btnText = btnContent.querySelector('.btn-text');
                    if (btnText) {
                        btnText.textContent = 'Generate Documentary';
                    }
                } else {
                    generateBtn.textContent = 'Generate Documentary';
                }
            }
        }
        });
    }

    // Download button
    if (downloadBtn) {
        downloadBtn.addEventListener('click', function() {
            if (currentDocumentaryId) {
                window.location.href = apiUrl(`api/documentary/${currentDocumentaryId}/video`);
            }
        });
    }

    // Embed button
    if (embedBtn && embedCode && embedCodeContainer) {
        embedBtn.addEventListener('click', function() {
            if (currentDocumentaryId) {
                // Get embed code for first clip (5-minute segment)
                // For Phase 1, we'll use the main video
                const embedPath = apiUrl(`embed/clip/${currentDocumentaryId}`);
                const embedHtml = `<iframe src="${window.location.origin}${embedPath}" width="640" height="360" frameborder="0" allowfullscreen></iframe>`;
                embedCode.value = embedHtml;
                embedCodeContainer.style.display = 'block';
                embedCode.select();
            }
        });
    }
    
    console.log('All event listeners attached successfully');
    
    function calculateETA(currentPercent, currentTime) {
        if (!generationStartTime || currentPercent <= 0) {
            return { eta: null, rate: 0, stalled: false };
        }
        
        // Add current progress to history (keep last 20 points for better accuracy)
        const timeSinceStart = (currentTime - generationStartTime) / 1000; // seconds
        progressHistory.push({ time: currentTime, percent: currentPercent, timeSinceStart: timeSinceStart });
        if (progressHistory.length > 20) {
            progressHistory.shift();
        }
        
        // Detect stagnation (progress hasn't increased in 15+ seconds)
        let stalled = false;
        if (currentPercent === lastProgressPercent) {
            if (!stagnationStartTime) {
                stagnationStartTime = currentTime;
            } else {
                const stagnationDuration = (currentTime - stagnationStartTime) / 1000; // seconds
                if (stagnationDuration > 15) {
                    stalled = true;
                }
            }
        } else {
            stagnationStartTime = null; // Reset stagnation timer
        }
        
        // Need at least 2 points for calculation
        if (progressHistory.length < 2) {
            // Initial estimate based on time elapsed
            if (timeSinceStart > 0 && currentPercent > 0) {
                const initialRate = currentPercent / timeSinceStart; // percent per second
                const remainingPercent = 100 - currentPercent;
                const estimatedSeconds = remainingPercent / initialRate;
                averageProgressRate = initialRate;
                return { eta: Math.max(0, Math.round(estimatedSeconds)), rate: initialRate, stalled: stalled };
            }
            return { eta: null, rate: 0, stalled: stalled };
        }
        
        // Use exponential moving average for more stable estimates
        // Weight recent progress more heavily
        const recentPoints = progressHistory.slice(-10); // Use last 10 points
        let weightedTimeDiff = 0;
        let weightedPercentDiff = 0;
        let totalWeight = 0;
        
        for (let i = 1; i < recentPoints.length; i++) {
            const timeDiff = (recentPoints[i].time - recentPoints[i-1].time) / 1000; // seconds
            const percentDiff = recentPoints[i].percent - recentPoints[i-1].percent;
            
            if (timeDiff > 0 && percentDiff > 0) {
                // Weight: more recent points get higher weight
                const weight = i / recentPoints.length;
                const rate = percentDiff / timeDiff; // percent per second
                weightedPercentDiff += rate * weight;
                totalWeight += weight;
            }
        }
        
        if (totalWeight > 0) {
            averageProgressRate = weightedPercentDiff / totalWeight;
        } else {
            // Fallback to simple average if weighted fails
            const first = recentPoints[0];
            const last = recentPoints[recentPoints.length - 1];
            const timeDiff = (last.time - first.time) / 1000;
            const percentDiff = last.percent - first.percent;
            
            if (timeDiff > 0 && percentDiff > 0) {
                averageProgressRate = percentDiff / timeDiff;
            }
        }
        
        // Calculate ETA based on average rate
        const remainingPercent = 100 - currentPercent;
        let estimatedSeconds = 0;
        
        if (averageProgressRate > 0) {
            estimatedSeconds = remainingPercent / averageProgressRate;
        } else {
            // If no progress rate, estimate based on current progress
            if (timeSinceStart > 0 && currentPercent > 0) {
                const assumedRate = currentPercent / timeSinceStart;
                if (assumedRate > 0) {
                    estimatedSeconds = remainingPercent / assumedRate;
                }
            }
        }
        
        // Add buffer for stalled progress (multiply by 1.5x if stalled)
        if (stalled && estimatedSeconds > 0) {
            estimatedSeconds = estimatedSeconds * 1.5;
        }
        
        return { 
            eta: Math.max(0, Math.round(estimatedSeconds)), 
            rate: averageProgressRate,
            stalled: stalled
        };
    }
    
    function formatTime(seconds) {
        if (seconds === null || seconds === undefined || isNaN(seconds)) {
            return 'beregner...';
        }
        
        if (seconds < 60) {
            return `${Math.round(seconds)}s`;
        } else {
            const mins = Math.floor(seconds / 60);
            const secs = Math.round(seconds % 60);
            if (secs === 0) {
                return `${mins}m`;
            } else {
                return `${mins}m ${secs}s`;
            }
        }
    }
    
    function formatProgressRate(rate) {
        if (!rate || rate <= 0) return '0%';
        if (rate >= 1) {
            return `${rate.toFixed(1)}%/s`;
        } else {
            return `${(rate * 100).toFixed(2)}%/s`;
        }
    }
    
    function showProgress(percent, text, icon) {
        console.log('[showProgress] Called with percent:', percent, 'text:', text);
        
        if (!progressContainer) {
            console.error('[showProgress] ERROR: progressContainer not found!');
            return;
        }
        
        progressContainer.style.display = 'block';
        if (progressFill) {
            progressFill.style.width = percent + '%';
        }
        
        // Always update progress and ETA (even if percent hasn't changed)
        const currentTime = Date.now();
        const etaInfo = calculateETA(percent, currentTime);
        
        // Update progress text with ETA
        let progressTextWithETA = '';
        if (text) {
            progressTextWithETA = text;
        } else {
            // Auto-select message based on progress
            if (percent < 5) {
                if (progressIcon) progressIcon.textContent = progressMessages.initializing.icon;
                progressTextWithETA = progressMessages.initializing.text;
            } else if (percent < 15) {
                if (progressIcon) progressIcon.textContent = progressMessages.scraping.icon;
                progressTextWithETA = progressMessages.scraping.text;
            } else if (percent < 30) {
                if (progressIcon) progressIcon.textContent = progressMessages.analyzing.icon;
                progressTextWithETA = progressMessages.analyzing.text;
            } else if (percent < 50) {
                // Use rotating messages for creating phase to keep it entertaining
                const creatingMessages = Array.isArray(progressMessages.creating) 
                    ? progressMessages.creating 
                    : [progressMessages.creating];
                // Rotate message based on time elapsed, not just progress
                const timeElapsed = generationStartTime ? (Date.now() - generationStartTime) / 1000 : 0;
                const messageIndex = Math.floor(timeElapsed / 3) % creatingMessages.length; // Change every 3 seconds
                const selectedMessage = creatingMessages[messageIndex];
                if (progressIcon) progressIcon.textContent = selectedMessage.icon;
                progressTextWithETA = selectedMessage.text;
            } else if (percent < 65) {
                if (progressIcon) progressIcon.textContent = progressMessages.generating.icon;
                progressTextWithETA = progressMessages.generating.text;
            } else if (percent < 80) {
                // Use message_key from backend to show specific operation messages
                // Fallback to default if no message_key provided
                const processingMsgs = progressMessages.processing;
                let selectedMessage = processingMsgs.default;
                
                // Try to get message_key from current progress data (set by backend)
                if (window.currentMessageKey && processingMsgs[window.currentMessageKey]) {
                    selectedMessage = processingMsgs[window.currentMessageKey];
                }
                
                if (progressIcon) progressIcon.textContent = selectedMessage.icon;
                progressTextWithETA = selectedMessage.text;
            } else if (percent < 90) {
                if (progressIcon) progressIcon.textContent = progressMessages.editing.icon;
                progressTextWithETA = progressMessages.editing.text;
            } else if (percent < 95) {
                if (progressIcon) progressIcon.textContent = progressMessages.adding_audio.icon;
                progressTextWithETA = progressMessages.adding_audio.text;
            } else if (percent < 100) {
                if (progressIcon) progressIcon.textContent = progressMessages.finalizing.icon;
                progressTextWithETA = progressMessages.finalizing.text;
            } else {
                if (progressIcon) progressIcon.textContent = progressMessages.completed.icon;
                progressTextWithETA = progressMessages.completed.text;
            }
        }
        
        // Add advanced ETA information if available
        // Always show timer, especially during encoding phase (65-80%)
        if (percent < 95) {
            const timeElapsed = generationStartTime ? Math.round((currentTime - generationStartTime) / 1000) : 0;
            
            // Check if message already contains time (from backend encoding updates)
            const messageHasTime = progressTextWithETA.includes('⏱️') || progressTextWithETA.includes('elapsed');
            
            if (!messageHasTime) {
                // Only add timer if not already in message
                let timerInfo = ` ⏱️ ${formatTime(timeElapsed)} elapsed`;
                
                if (etaInfo.eta !== null && etaInfo.eta > 0) {
                    timerInfo += ` • ~${formatTime(etaInfo.eta)} remaining`;
                    
                    // Add progress rate if available
                    if (etaInfo.rate > 0) {
                        timerInfo += ` • ${formatProgressRate(etaInfo.rate)}`;
                    }
                    
                    // Add stalled warning if progress seems stuck
                    if (etaInfo.stalled) {
                        timerInfo += ` ⚠️ venter på progress...`;
                    }
                } else if (timeElapsed > 5) {
                    // If no ETA but time has passed, show calculating or estimated time
                    if (percent >= 65 && percent < 80) {
                        // During encoding phase (65-80%), estimate based on typical encoding time
                        // Encoding typically takes 30-90 seconds
                        const estimated_remaining = Math.max(10, 60 - timeElapsed);
                        timerInfo += ` • ~${formatTime(estimated_remaining)} estimated remaining`;
                    } else {
                        timerInfo += ` • beregner ETA...`;
                    }
                }
                
                progressTextWithETA += timerInfo;
            } else {
                // If message already has time from backend, still show additional info if needed
                if (etaInfo.eta !== null && etaInfo.eta > 0 && !progressTextWithETA.includes('remaining')) {
                    progressTextWithETA += ` • ~${formatTime(etaInfo.eta)} remaining`;
                }
            }
        }
        
        if (progressText) {
            progressText.textContent = progressTextWithETA;
        }
        
        // Update progress percentage
        if (progressPercentage) {
            progressPercentage.textContent = Math.round(percent) + '%';
        }
        
        // Update elapsed time, ETA, and rate
        if (elapsedTimeEl) {
            const timeElapsed = generationStartTime ? Math.round((currentTime - generationStartTime) / 1000) : 0;
            elapsedTimeEl.textContent = formatTime(timeElapsed);
        }
        
        if (etaTimeEl) {
            etaTimeEl.textContent = etaInfo.eta !== null ? formatTime(etaInfo.eta) : 'calculating...';
        }
        
        if (progressRateValue) {
            progressRateValue.textContent = formatProgressRate(etaInfo.rate);
        }
        
        // ========== MATRIX DISPLAY LOGIC ==========
        // Store current progress for matrix code generation
        window.currentProgressPercent = percent;
        
        // Show Matrix display from 0% onwards
        if (percent >= 0) {
            console.log('[Matrix] Progress is', percent + '%, checking if Matrix should show...');
            
            // Try to find elements again if not found (they might load late)
            if (!matrixDisplay) {
                matrixDisplay = document.getElementById('matrix-processing-display');
                console.log('[Matrix] Retry: matrixDisplay found:', !!matrixDisplay);
            }
            if (!matrixCodeDisplay) {
                matrixCodeDisplay = document.getElementById('matrix-code-display');
                console.log('[Matrix] Retry: matrixCodeDisplay found:', !!matrixCodeDisplay);
            }
            
            console.log('[Matrix] matrixDisplay exists:', !!matrixDisplay);
            console.log('[Matrix] matrixCodeDisplay exists:', !!matrixCodeDisplay);
            
            if (matrixDisplay) {
                console.log('[Matrix] Showing Matrix display at', percent + '%');
                
                // REMOVE inline styles that hide it
                matrixDisplay.removeAttribute('style');
                
                // Force visibility with multiple methods - SET ALL
                matrixDisplay.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; position: relative !important; z-index: 10000 !important;';
                matrixDisplay.style.display = 'block';
                matrixDisplay.style.visibility = 'visible';
                matrixDisplay.style.opacity = '1';
                matrixDisplay.style.position = 'relative';
                matrixDisplay.style.zIndex = '10000';
                
                // Add classes and attributes
                matrixDisplay.classList.add('matrix-active');
                matrixDisplay.setAttribute('data-matrix-active', 'true');
                matrixDisplay.removeAttribute('hidden');
                
                // Force display in case CSS is hiding it
                const computedStyle = window.getComputedStyle(matrixDisplay);
                console.log('[Matrix] Computed display:', computedStyle.display);
                console.log('[Matrix] Computed visibility:', computedStyle.visibility);
                console.log('[Matrix] Computed opacity:', computedStyle.opacity);
                console.log('[Matrix] Computed z-index:', computedStyle.zIndex);
                
                // Double-check visibility
                if (computedStyle.display === 'none') {
                    console.warn('[Matrix] WARNING: Still hidden! Forcing with setProperty...');
                    matrixDisplay.style.setProperty('display', 'block', 'important');
                    matrixDisplay.style.setProperty('visibility', 'visible', 'important');
                    matrixDisplay.style.setProperty('opacity', '1', 'important');
                }
                
                // Hide regular progress textbox when Matrix is showing
                if (progressContainer) {
                    const textbox = progressContainer.querySelector('#progress-textbox');
                    if (textbox) {
                        textbox.style.display = 'none';
                        console.log('[Matrix] Hid regular progress textbox');
                    }
                }
                
                // Start Matrix if not already started
                if (!matrixUpdateInterval) {
                    console.log('[Matrix] Initializing Matrix display');
                    initMatrixDisplay();
                }
                
                // Update status based on progress phase
                if (matrixStatusText) {
                    if (percent < 10) {
                        matrixStatusText.textContent = 'INITIALIZING_SYSTEM';
                    } else if (percent < 20) {
                        matrixStatusText.textContent = 'SEARCHING_RESOURCES';
                    } else if (percent < 30) {
                        matrixStatusText.textContent = 'ANALYZING_PROMPT';
                    } else if (percent < 50) {
                        matrixStatusText.textContent = 'CREATING_CONTENT';
                    } else if (percent < 65) {
                        matrixStatusText.textContent = 'GENERATING_VIDEO';
                    } else if (percent < 70) {
                        matrixStatusText.textContent = 'INITIALIZING_ENCODER';
                    } else if (percent < 75) {
                        matrixStatusText.textContent = 'ENCODING_VIDEO';
                    } else if (percent < 80) {
                        matrixStatusText.textContent = 'FINALIZING_ENCODE';
                    } else if (percent < 90) {
                        matrixStatusText.textContent = 'ADDING_AUDIO';
                    } else if (percent < 95) {
                        matrixStatusText.textContent = 'FINALIZING_OUTPUT';
                    } else {
                        matrixStatusText.textContent = 'COMPLETING_GENERATION';
                    }
                }
                
                // Update Matrix stats (this also calls updatePhaseStats, updateResourceStats, updateSessionStats)
                updateMatrixStats(percent, etaInfo);
                
                // Force update of all monitor stats to ensure they're visible
                updatePhaseStats(percent);
                updateResourceStats(percent);
                updateSessionStats();
                
                // Show Matrix Monitor automatically from start of process (0% onwards)
                if (percent >= 0) {
                    const monitorEl = document.getElementById('matrix-monitor');
                    if (monitorEl) {
                        if (!monitorEl.classList.contains('matrix-active')) {
                            console.log('[Monitor] Progress update - showing monitor at', percent + '%');
                            monitorEl.removeAttribute('style');
                            monitorEl.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; position: relative !important; z-index: 5000 !important;';
                            monitorEl.style.display = 'block';
                            monitorEl.style.visibility = 'visible';
                            monitorEl.style.opacity = '1';
                            monitorEl.classList.add('matrix-active');
                            monitorEl.setAttribute('data-matrix-active', 'true');
                        }
                        
                        // Update status based on progress
                        const statusEl = document.getElementById('monitor-status-text');
                        if (statusEl) {
                            if (percent < 10) statusEl.textContent = 'INITIALIZING';
                            else if (percent < 20) statusEl.textContent = 'SEARCHING_RESOURCES';
                            else if (percent < 30) statusEl.textContent = 'ANALYZING_PROMPT';
                            else if (percent < 50) statusEl.textContent = 'CREATING_CONTENT';
                            else if (percent < 65) {
                                statusEl.textContent = 'GENERATING_VIDEO_CLIPS';
                                // Dispatch event for clip generation phase
                                dispatchClipGenerationEvent(percent);
                            } else if (percent < 70) statusEl.textContent = 'COMBINING_CLIPS';
                            else if (percent < 75) statusEl.textContent = 'ENCODING_VIDEO';
                            else if (percent < 80) statusEl.textContent = 'FINALIZING_ENCODE';
                            else if (percent < 90) statusEl.textContent = 'ADDING_AUDIO';
                            else if (percent < 95) statusEl.textContent = 'FINALIZING_OUTPUT';
                            else statusEl.textContent = 'COMPLETING_GENERATION';
                        }
                    }
                    
                    // Also call window.showMonitor if it exists
                    if (typeof window.showMonitor === 'function') {
                        window.showMonitor();
                    }
                }
            } else {
                console.error('[Matrix] ERROR: matrixDisplay element not found!');
                console.error('[Matrix] This should not happen - element should be in HTML');
                console.error('[Matrix] Searching DOM for any matrix elements...');
                const allMatrix = document.querySelectorAll('[id*="matrix"], [class*="matrix"]');
                console.error('[Matrix] Found elements with "matrix":', allMatrix.length);
                if (allMatrix.length > 0) {
                    allMatrix.forEach(function(el, i) {
                        console.error('[Matrix] Element', i, ':', el.id || '(no id)', el.className || '(no class)', 'tag:', el.tagName);
                    });
                } else {
                    console.error('[Matrix] NO matrix elements found in DOM! HTML might not be loaded correctly.');
                    console.error('[Matrix] Total divs in DOM:', document.querySelectorAll('div').length);
                    console.error('[Matrix] Document readyState:', document.readyState);
                }
            }
        } else {
            // Hide Matrix display before 0% (shouldn't happen but just in case)
            if (matrixDisplay) {
                matrixDisplay.style.display = 'none';
                stopMatrixCodeGeneration();
                
                // Show regular progress textbox
                if (progressContainer) {
                    const textbox = progressContainer.querySelector('#progress-textbox');
                    if (textbox) textbox.style.display = 'flex';
                }
            }
        }
        // ========== END MATRIX DISPLAY LOGIC ==========
        
        // Update tracking variables
        if (percent !== lastProgressPercent) {
            lastProgressPercent = percent;
            lastProgressUpdateTime = currentTime;
        }
    }

    function hideProgress() {
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
    }

    function showError(message) {
        if (errorMessage) {
            errorMessage.textContent = message;
            errorMessage.style.display = 'block';
        } else {
            console.error('Error:', message);
        }
    }

    function hideError() {
        if (errorMessage) {
            errorMessage.style.display = 'none';
        }
    }

    function startProgressPolling(docId) {
        console.log('[Progress] Starting progress polling for documentary:', docId);
        mp4VerificationScheduled = false;
        
        // Ensure Matrix Monitor is visible when polling starts
        const monitorEl = document.getElementById('matrix-monitor');
        if (monitorEl && !monitorEl.classList.contains('matrix-active')) {
            console.log('[Monitor] Polling started - ensuring Matrix Monitor is visible');
            monitorEl.removeAttribute('style');
            monitorEl.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; position: relative !important; z-index: 5000 !important;';
            monitorEl.style.display = 'block';
            monitorEl.style.visibility = 'visible';
            monitorEl.style.opacity = '1';
            monitorEl.classList.add('matrix-active');
            monitorEl.setAttribute('data-matrix-active', 'true');
            
            // Update status
            const statusEl = document.getElementById('monitor-status-text');
            if (statusEl) statusEl.textContent = 'POLLING_ACTIVE';
            
            const monitorTextEl = document.getElementById('monitor-text');
            if (monitorTextEl) {
                const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
                monitorTextEl.textContent += `[${timestamp}] > POLLING_ACTIVE: Fetching real-time data...\n`;
                monitorTextEl.scrollTop = monitorTextEl.scrollHeight;
            }
            
            // Initialize border rain
            if (typeof initMatrixCanvasBorder === 'function') {
                setTimeout(function() {
                    initMatrixCanvasBorder();
                    if (typeof startMatrixRainBorder === 'function') {
                        startMatrixRainBorder();
                    }
                }, 100);
            }
        }
        
        // Ensure Matrix display is visible when polling starts
        if (matrixDisplay && !matrixDisplay.classList.contains('matrix-active')) {
            console.log('[Matrix] Polling started - ensuring Matrix display is visible');
            matrixDisplay.removeAttribute('style');
            matrixDisplay.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; position: relative !important; z-index: 10000 !important;';
            matrixDisplay.classList.add('matrix-active');
            matrixDisplay.setAttribute('data-matrix-active', 'true');
            
            if (!matrixUpdateInterval) {
                initMatrixDisplay();
            }
        }
        
        // Clear any existing interval
        if (progressInterval) {
            clearInterval(progressInterval);
        }

        // Poll every 2 seconds
        progressInterval = setInterval(async () => {
            console.log('[Progress] Polling progress for:', docId);
            try {
                const response = await fetch(apiUrl(`api/documentary/${docId}/progress`));
                const data = await response.json();
                
                // Update user stats from server response
                if (data.user_ip || data.user_agent) {
                    updateUserStats(data.user_ip, data.user_agent);
                }
                
                // Update clip stats from progress data
                if (data.clip_count !== undefined) {
                    updateClipStats(data.clip_count, data.total_duration, data.total_size);
                }
                
                // Update phase stats
                if (data.progress !== undefined) {
                    updatePhaseStats(data.progress);
                }
                
                // Update resource stats
                if (data.progress !== undefined) {
                    updateResourceStats(data.progress);
                }
                
                // Increment request counter
                matrixStats.totalRequests++;

                if (data.status === 'completed') {
                    showProgress(100, progressMessages.completed.text, progressMessages.completed.icon);
                    clearInterval(progressInterval);
                    
                    // Small delay to show completion message
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    
                    // Stop Matrix rain when complete
                    if (typeof stopMatrixRainBackground === 'function') {
                        stopMatrixRainBackground();
                    }
                    
                    // Hide monitor when complete
                    if (typeof window.hideMonitor === 'function') {
                        window.hideMonitor();
                    }
                    
                    // Load video
                    await loadVideo(docId);
                    
                    // Dispatch generation completed event for XP tracking
                    if (typeof window.dispatchEvent === 'function') {
                        window.dispatchEvent(new CustomEvent('generationCompleted', {
                            detail: {
                                documentary_id: docId,
                                status: 'completed'
                            }
                        }));
                    }
                    
                    if (!mp4VerificationScheduled) {
                        mp4VerificationScheduled = true;
                        triggerMP4Verification(docId, false);
                    }
                    
                    if (generateBtn) {
                        generateBtn.disabled = false;
                        generateBtn.textContent = 'Generate Documentary';
                    }
                } else if (data.status === 'failed') {
                    clearInterval(progressInterval);
                    
                    // Stop Matrix rain on failure
                    if (typeof stopMatrixRainBackground === 'function') {
                        stopMatrixRainBackground();
                    }
                    
                    // Hide monitor on failure
                    if (typeof window.hideMonitor === 'function') {
                        window.hideMonitor();
                    }
                    showProgress(0, progressMessages.failed.text, progressMessages.failed.icon);
                    throw new Error('Generation failed');
                } else {
                    // Show progress with appropriate message
                    const progress = data.progress || 0;
                    
                    // ==========================================
                    // ENHANCED: Handle comprehensive progress data
                    // ==========================================
                    
                    // Update requirements viewer if available
                    if (data.requirements && typeof window.updateMonitorRequirements === 'function') {
                        window.updateMonitorRequirements(
                            data.requirements.prompt || '',
                            data.requirements.title || '',
                            data.requirements.theme || 'matrix',
                            data.requirements.emotion || 'analyzing...'
                        );
                    }
                    
                    // Update monitor with clip data if available (REAL-TIME)
                    if (data.clips && Array.isArray(data.clips) && data.clips.length > 0) {
                        if (typeof window.updateMonitorClipList === 'function') {
                            window.updateMonitorClipList(data.clips);
                        }
                        
                        // Update current clip info from latest clip
                        const latestClip = data.clips[data.clips.length - 1];
                        if (latestClip && typeof window.updateMonitorClipInfo === 'function') {
                            window.updateMonitorClipInfo(
                                data.current_clip || data.clips.length,
                                data.total_clips || data.clips.length,
                                {
                                    duration: latestClip.duration || 10,
                                    size: latestClip.size || 0,
                                    resolution: latestClip.resolution || '1280x768',
                                    fps: latestClip.fps || 24
                                }
                            );
                        }
                        
                        // Update storyline visualization if available
                        if (data.storyline && typeof window.updateStorylineVisualization === 'function') {
                            window.updateStorylineVisualization(data.storyline);
                        }
                    }
                    
                    // Update editable MP4 status if available
                    if (data.editable_mp4_path && typeof window.updateIncrementalMP4Status === 'function') {
                        window.updateIncrementalMP4Status(data.editable_mp4_path, data.clips?.length || 0);
                    }
                    
                    // Update monitor with combined video info if available
                    if (data.video_path && typeof window.updateMonitorCombinedVideo === 'function') {
                        window.updateMonitorCombinedVideo(
                            data.video_path,
                            {
                                duration: data.duration,
                                size: data.video_size,
                                resolution: data.resolution || data.video_resolution,
                                fps: data.fps || data.video_fps,
                                status: data.status
                            }
                        );
                    }
                    
                    if (typeof window.updateMP4Awareness === 'function') {
                        window.updateMP4Awareness({
                            status: data.mp4_status || data.status,
                            confidence: data.mp4_confidence,
                            duration: data.duration,
                            size: data.video_size,
                            path: data.video_path
                        });
                    }
                    
                    // Performance: Throttle console logging (only log every 10% or status change)
                    if (progress % 10 === 0 || data.status !== (window.lastStatus || '')) {
                    console.log('[Progress] Polling update - Progress:', progress + '%', 'Status:', data.status, 
                               'Clips:', data.clips?.length || 0, 'Editable MP4:', data.editable_mp4_path ? 'Yes' : 'No');
                        window.lastStatus = data.status;
                    }
                    
                    // Store message_key from backend for showProgress to use
                    if (data.message_key) {
                        window.currentMessageKey = data.message_key;
                    }
                    
                    // Performance: Use requestAnimationFrame for DOM updates
                    requestAnimationFrame(() => {
                    showProgress(progress);
                    });
                }
            } catch (error) {
                console.error('Error polling progress:', error);
                clearInterval(progressInterval);
                showError('Error checking progress.');
                if (generateBtn) {
                    generateBtn.disabled = false;
                    generateBtn.textContent = 'Generate Documentary';
                }
            }
        }, 2000);
    }

    async function loadVideo(docId) {
        try {
            // Get documentary info
            const response = await fetch(apiUrl(`api/documentary/${docId}`));
            
            // Check if response is JSON
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const text = await response.text();
                throw new Error(`API returned HTML instead of JSON (${response.status}). This usually means the endpoint doesn't exist or there's a server error.`);
            }
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || errorData.message || `Failed to load video: ${response.status}`);
            }
            
            const documentary = await response.json();

            console.log('Documentary data:', {
                id: documentary.id,
                video_path: documentary.video_path,
                status: documentary.status,
                duration: documentary.duration
            });

            if (videoPlayer) {
                if (documentary.video_path) {
                    const videoUrl = apiUrl(`api/documentary/${docId}/video`);
                    console.log('Loading video from:', videoUrl);
                    
                    videoPlayer.src = videoUrl;
                    videoPlayer.load(); // Force reload
                    
                    // Wait for video metadata to load
                    videoPlayer.addEventListener('loadedmetadata', function() {
                        console.log('Video metadata loaded:', {
                            duration: videoPlayer.duration,
                            videoWidth: videoPlayer.videoWidth,
                            videoHeight: videoPlayer.videoHeight
                        });
                    }, { once: true });
                    
                    // Handle video errors
                    videoPlayer.addEventListener('error', function(e) {
                        console.error('Video load error:', e);
                        const errorMsg = videoPlayer.error;
                        if (errorMsg) {
                            console.error('Video error code:', errorMsg.code);
                            console.error('Video error message:', errorMsg.message);
                        }
                        showError('Video kunne ikke indlæses. Prøv at generere igen.');
                    }, { once: true });
                    
                    if (videoPanel) {
                        videoPanel.style.display = 'block';
                        videoPanel.scrollIntoView({ behavior: 'smooth' });
                    }
                    
                    // Initialize recording functionality
                    initRecording();
                } else {
                    console.error('No video_path in documentary:', documentary);
                    showError('Video blev ikke genereret. Prøv at generere igen.');
                }
            } else {
                console.error('Video player element not found');
                showError('Video player ikke fundet.');
            }
        } catch (error) {
            console.error('Error loading video:', error);
            showError('Fejl ved indlæsning af video: ' + error.message);
        }
    }
    
    // Video recording functionality
    function initRecording() {
        const recordBtn = document.getElementById('record-btn-main');
        const recordingIndicator = document.getElementById('recording-indicator-main');
        let mediaRecorder = null;
        let recordedChunks = [];
        let isRecording = false;
        
        if (!videoPlayer || !recordBtn) return;
        
        recordBtn.addEventListener('click', async function() {
            if (!isRecording) {
                // Start recording
                try {
                    const stream = await captureVideoWithAudio(videoPlayer);
                    
                    const options = {
                        mimeType: 'video/webm;codecs=vp9,opus',
                        videoBitsPerSecond: 5000000
                    };
                    
                    if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                        options.mimeType = 'video/webm;codecs=vp8,opus';
                    }
                    if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                        options.mimeType = 'video/webm';
                    }
                    
                    mediaRecorder = new MediaRecorder(stream, options);
                    recordedChunks = [];
                    
                    mediaRecorder.ondataavailable = function(event) {
                        if (event.data.size > 0) {
                            recordedChunks.push(event.data);
                        }
                    };
                    
                    mediaRecorder.onstop = function() {
                        const blob = new Blob(recordedChunks, { type: 'video/webm' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'documentary-recording-' + Date.now() + '.webm';
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                        stream.getTracks().forEach(track => track.stop());
                        
                        isRecording = false;
                        recordBtn.classList.remove('recording');
                        recordBtn.querySelector('.record-text').textContent = 'Record';
                        recordBtn.querySelector('.record-icon').textContent = '🔴';
                        if (recordingIndicator) {
                            recordingIndicator.style.display = 'none';
                        }
                    };
                    
                    mediaRecorder.start();
                    isRecording = true;
                    recordBtn.classList.add('recording');
                    recordBtn.querySelector('.record-text').textContent = 'Stop Recording';
                    recordBtn.querySelector('.record-icon').textContent = '⏹️';
                    if (recordingIndicator) {
                        recordingIndicator.style.display = 'flex';
                    }
                    
                } catch (error) {
                    console.error('Recording error:', error);
                    showError('Failed to start recording: ' + error.message);
                }
            } else {
                if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                    mediaRecorder.stop();
                }
            }
        });
        
        async function captureVideoWithAudio(videoElement) {
            try {
                const canvas = document.createElement('canvas');
                canvas.width = videoElement.videoWidth || 1280;
                canvas.height = videoElement.videoHeight || 720;
                const ctx = canvas.getContext('2d');
                
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const source = audioContext.createMediaElementSource(videoElement);
                const destination = audioContext.createMediaStreamDestination();
                source.connect(destination);
                source.connect(audioContext.destination);
                
                const videoStream = canvas.captureStream(30);
                const audioStream = destination.stream;
                
                const combinedStream = new MediaStream();
                videoStream.getVideoTracks().forEach(track => combinedStream.addTrack(track));
                audioStream.getAudioTracks().forEach(track => combinedStream.addTrack(track));
                
                const drawFrame = () => {
                    if (videoElement.readyState >= 2) {
                        ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
                    }
                    if (isRecording) {
                        requestAnimationFrame(drawFrame);
                    }
                };
                drawFrame();
                
                return combinedStream;
            } catch (error) {
                console.error('Capture error:', error);
                if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
                    return await navigator.mediaDevices.getDisplayMedia({
                        video: true,
                        audio: true
                    });
                }
                throw error;
            }
        }
    }
    
    // ==================== NEW ADVANCED FEATURES ====================
    
    // Initialize particles background
    function initParticles() {
        const particlesBg = document.getElementById('particles-bg');
        if (!particlesBg) return;
        
        for (let i = 0; i < 20; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.width = Math.random() * 10 + 5 + 'px';
            particle.style.height = particle.style.width;
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDelay = Math.random() * 15 + 's';
            particle.style.animationDuration = (Math.random() * 10 + 10) + 's';
            particlesBg.appendChild(particle);
        }
    }
    
    // Initialize tooltips
    function initTooltips() {
        const tooltipIcons = document.querySelectorAll('.tooltip-icon');
        const tooltipContainer = document.getElementById('tooltip-container');
        
        tooltipIcons.forEach(icon => {
            icon.addEventListener('mouseenter', function(e) {
                const tooltipText = this.getAttribute('data-tooltip');
                if (tooltipText && tooltipContainer) {
                    tooltipContainer.textContent = tooltipText;
                    tooltipContainer.className = 'tooltip show';
                    const rect = this.getBoundingClientRect();
                    tooltipContainer.style.left = rect.left + (rect.width / 2) - (tooltipContainer.offsetWidth / 2) + 'px';
                    tooltipContainer.style.top = rect.top - tooltipContainer.offsetHeight - 10 + 'px';
                }
            });
            
            icon.addEventListener('mouseleave', function() {
                if (tooltipContainer) {
                    tooltipContainer.className = 'tooltip';
                }
            });
        });
    }
    
    // Initialize templates
    function initTemplates() {
        const templateCards = document.querySelectorAll('.template-card');
        
        const templates = {
            space: 'A comprehensive documentary about space exploration, covering the history of space travel, missions to the Moon and Mars, the International Space Station, and future plans for deep space exploration. Include stunning visuals of planets, stars, and galaxies.',
            nature: 'A detailed nature documentary showcasing the wonders of wildlife and ecosystems around the world. Cover diverse habitats, animal behavior, conservation efforts, and the delicate balance of nature. Feature breathtaking cinematography of landscapes and wildlife.',
            history: 'An in-depth historical documentary exploring significant events and civilizations from the past. Cover ancient civilizations, major wars, cultural movements, and how historical events shaped the modern world. Include archival footage and expert interviews.',
            science: 'A scientific documentary highlighting breakthrough discoveries and innovations in science and technology. Cover recent advances in medicine, physics, chemistry, biology, and engineering. Explain complex concepts in accessible ways with visual demonstrations.',
            culture: 'A cultural documentary examining the rich heritage of arts, traditions, and customs from around the world. Explore music, dance, literature, visual arts, festivals, and how culture evolves over time. Feature interviews with artists and cultural experts.',
            technology: 'A technology documentary tracing the evolution of technology from ancient tools to modern innovations. Cover the digital revolution, artificial intelligence, robotics, the internet, and emerging technologies. Discuss their impact on society.'
        };
        
        templateCards.forEach(card => {
            card.addEventListener('click', function() {
                const templateType = this.getAttribute('data-template');
                const templateText = templates[templateType];
                
                if (templateText && promptInput) {
                    promptInput.value = templateText;
                    updateCharacterCounter(promptInput, promptCounter, 2000);
                    showToast('Template applied!', 'success');
                    
                    // Scroll to prompt section
                    promptInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    promptInput.focus();
                }
            });
        });
    }
    
    // Initialize character counters
    function initCharacterCounters() {
        if (promptInput && promptCounter) {
            // Performance: Debounce input events to reduce auto-save frequency
            const debouncedAutoSave = typeof debounce !== 'undefined' 
                ? debounce(function() {
                    // Auto-save logic here if needed
                }, 1000)
                : function() {};
            
            promptInput.addEventListener('input', function() {
                updateCharacterCounter(this, promptCounter, 2000);
            });
        }
        
        if (titleInput && titleCounter) {
            titleInput.addEventListener('input', function() {
                updateCharacterCounter(this, titleCounter, 200);
            });
        }
        
        if (descriptionInput && descriptionCounter) {
            descriptionInput.addEventListener('input', function() {
                updateCharacterCounter(this, descriptionCounter, 1000);
            });
        }
    }
    
    function updateCharacterCounter(input, counter, maxLength) {
        if (!counter) return;
        
        const length = input.value.length;
        counter.textContent = length;
        
        const counterParent = counter.parentElement;
        if (counterParent) {
            counterParent.classList.remove('warning', 'danger');
            
            if (length > maxLength * 0.9) {
                counterParent.classList.add('danger');
            } else if (length > maxLength * 0.75) {
                counterParent.classList.add('warning');
            }
        }
    }
    
    // Initialize settings panel
    function initSettingsPanel() {
        if (settingsToggle) {
            settingsToggle.addEventListener('click', function(e) {
                e.preventDefault();
                if (settingsPanel) {
                    settingsPanel.classList.add('active');
                }
            });
        }
        
        if (settingsClose) {
            settingsClose.addEventListener('click', function() {
                if (settingsPanel) {
                    settingsPanel.classList.remove('active');
                }
            });
        }
        
        // Close on outside click
        if (settingsPanel) {
            settingsPanel.addEventListener('click', function(e) {
                if (e.target === settingsPanel) {
                    settingsPanel.classList.remove('active');
                }
            });
        }
    }
    
    // Initialize collapse toggles
    function initCollapseToggles() {
        const toggles = [
            { btn: templatesToggle, content: document.getElementById('templates-grid') },
            { btn: optionsToggle, content: document.getElementById('options-content') },
            { btn: uploadToggle, content: document.getElementById('upload-content') }
        ];
        
        toggles.forEach(({ btn, content }) => {
            if (btn && content) {
                btn.addEventListener('click', function() {
                    const isHidden = content.style.display === 'none';
                    content.style.display = isHidden ? 'block' : 'none';
                    btn.classList.toggle('collapsed');
                });
            }
        });
    }
    
    // Initialize drag and drop
    function initDragAndDrop() {
        if (!uploadZone || !fileUpload) return;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadZone.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadZone.addEventListener(eventName, function() {
                uploadZone.classList.add('drag-over');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadZone.addEventListener(eventName, function() {
                uploadZone.classList.remove('drag-over');
            }, false);
        });
        
        uploadZone.addEventListener('drop', function(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length > 0) {
                fileUpload.files = files;
                handleFileUpload(files);
            }
        }, false);
        
        uploadZone.addEventListener('click', function() {
            fileUpload.click();
        });
        
        const uploadLink = uploadZone.querySelector('.upload-link');
        if (uploadLink) {
            uploadLink.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                fileUpload.click();
            });
        }
    }
    
    // Enhanced file upload handler
    function handleFileUpload(files) {
        if (!uploadFiles) return;
        
        uploadFiles.innerHTML = '';
        
        Array.from(files).forEach(file => {
            const fileItem = document.createElement('div');
            fileItem.className = 'upload-file-item';
            
            const fileInfo = document.createElement('div');
            fileInfo.className = 'upload-file-info';
            
            const fileIcon = document.createElement('i');
            if (file.type.startsWith('image/')) {
                fileIcon.className = 'fas fa-image upload-file-icon';
            } else if (file.type === 'application/pdf') {
                fileIcon.className = 'fas fa-file-pdf upload-file-icon';
            } else {
                fileIcon.className = 'fas fa-file upload-file-icon';
            }
            
            const fileName = document.createElement('span');
            fileName.className = 'upload-file-name';
            fileName.textContent = file.name;
            
            const fileSize = document.createElement('span');
            fileSize.className = 'upload-file-size';
            fileSize.textContent = formatFileSize(file.size);
            
            fileInfo.appendChild(fileIcon);
            fileInfo.appendChild(fileName);
            fileInfo.appendChild(fileSize);
            
            const removeBtn = document.createElement('button');
            removeBtn.className = 'upload-file-remove';
            removeBtn.innerHTML = '<i class="fas fa-times"></i>';
            removeBtn.addEventListener('click', function() {
                fileItem.remove();
                // Remove from file input
                const dt = new DataTransfer();
                Array.from(fileUpload.files).forEach(f => {
                    if (f !== file) {
                        dt.items.add(f);
                    }
                });
                fileUpload.files = dt.files;
            });
            
            fileItem.appendChild(fileInfo);
            fileItem.appendChild(removeBtn);
            uploadFiles.appendChild(fileItem);
        });
    }
    
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }
    
    // Initialize tags system
    function initTagsSystem() {
        if (!tagsInput || !tagsContainer) return;
        
        let tags = [];
        
        tagsInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ',') {
                e.preventDefault();
                const tag = this.value.trim();
                if (tag && !tags.includes(tag)) {
                    tags.push(tag);
                    renderTags();
                    this.value = '';
                }
            }
        });
        
        function renderTags() {
            tagsContainer.innerHTML = '';
            tags.forEach(tag => {
                const tagEl = document.createElement('div');
                tagEl.className = 'tag';
                tagEl.innerHTML = `
                    <span>${tag}</span>
                    <button class="tag-remove" data-tag="${tag}">
                        <i class="fas fa-times"></i>
                    </button>
                `;
                
                tagEl.querySelector('.tag-remove').addEventListener('click', function() {
                    tags = tags.filter(t => t !== tag);
                    renderTags();
                });
                
                tagsContainer.appendChild(tagEl);
            });
        }
    }
    
    // Initialize auto-save
    function initAutoSave() {
        const autoSaveCheckbox = document.getElementById('auto-save-draft');
        if (!autoSaveCheckbox) return;
        
        autoSaveCheckbox.addEventListener('change', function() {
            if (this.checked) {
                startAutoSave();
            } else {
                stopAutoSave();
            }
        });
        
        // Check if auto-save was enabled previously
        if (localStorage.getItem('autoSaveEnabled') === 'true') {
            autoSaveCheckbox.checked = true;
            startAutoSave();
        }
        
        function startAutoSave() {
            stopAutoSave();
            autoSaveInterval = setInterval(saveDraft, 30000); // Every 30 seconds
            localStorage.setItem('autoSaveEnabled', 'true');
        }
        
        function stopAutoSave() {
            if (autoSaveInterval) {
                clearInterval(autoSaveInterval);
                autoSaveInterval = null;
            }
            localStorage.setItem('autoSaveEnabled', 'false');
        }
        
        // Save draft on input (debounced)
        [promptInput, titleInput, descriptionInput].forEach(input => {
            if (input) {
                input.addEventListener('input', function() {
                    clearTimeout(draftSaveTimeout);
                    draftSaveTimeout = setTimeout(saveDraft, 2000); // Save after 2 seconds of inactivity
                });
            }
        });
    }
    
    function saveDraft() {
        const draft = {
            prompt: promptInput ? promptInput.value : '',
            title: titleInput ? titleInput.value : '',
            description: descriptionInput ? descriptionInput.value : '',
            timestamp: Date.now()
        };
        
        localStorage.setItem('documentaryDraft', JSON.stringify(draft));
    }
    
    function loadDraft() {
        const draftStr = localStorage.getItem('documentaryDraft');
        if (!draftStr) return;
        
        try {
            const draft = JSON.parse(draftStr);
            
            // Only load if draft is less than 24 hours old
            const draftAge = Date.now() - draft.timestamp;
            if (draftAge > 24 * 60 * 60 * 1000) {
                localStorage.removeItem('documentaryDraft');
                return;
            }
            
            if (promptInput && draft.prompt) promptInput.value = draft.prompt;
            if (titleInput && draft.title) titleInput.value = draft.title;
            if (descriptionInput && draft.description) descriptionInput.value = draft.description;
            
            // Update counters
            if (promptInput && promptCounter) updateCharacterCounter(promptInput, promptCounter, 2000);
            if (titleInput && titleCounter) updateCharacterCounter(titleInput, titleCounter, 200);
            if (descriptionInput && descriptionCounter) updateCharacterCounter(descriptionInput, descriptionCounter, 1000);
            
            showToast('Draft loaded from last session', 'success');
        } catch (e) {
            console.error('Error loading draft:', e);
        }
    }
    
    // Clear prompt button
    if (clearPromptBtn && promptInput) {
        clearPromptBtn.addEventListener('click', function() {
            promptInput.value = '';
            updateCharacterCounter(promptInput, promptCounter, 2000);
            promptInput.focus();
        });
    }
    
    // Expand prompt button
    if (expandPromptBtn && promptInput) {
        expandPromptBtn.addEventListener('click', function() {
            if (promptInput.style.height === '300px') {
                promptInput.style.height = 'auto';
                this.innerHTML = '<i class="fas fa-expand"></i>';
            } else {
                promptInput.style.height = '300px';
                this.innerHTML = '<i class="fas fa-compress"></i>';
            }
        });
    }
    
    // Generate title button
    if (generateTitleBtn && promptInput && titleInput) {
        generateTitleBtn.addEventListener('click', function() {
            const prompt = promptInput.value.trim();
            if (!prompt) {
                showToast('Please enter a prompt first', 'error');
                return;
            }
            
            // Simple title generation from prompt
            const words = prompt.split(' ').slice(0, 8);
            const generatedTitle = words.join(' ').replace(/[.,!?]$/, '');
            titleInput.value = generatedTitle;
            updateCharacterCounter(titleInput, titleCounter, 200);
            showToast('Title generated!', 'success');
        });
    }
    
    // Suggestion chips
    const suggestionChips = document.querySelectorAll('.suggestion-chip');
    suggestionChips.forEach(chip => {
        chip.addEventListener('click', function() {
            const suggestion = this.getAttribute('data-suggestion');
            if (promptInput) {
                const currentValue = promptInput.value.trim();
                promptInput.value = currentValue ? currentValue + '. ' + suggestion + '.' : suggestion + '.';
                promptInput.focus();
                updateCharacterCounter(promptInput, promptCounter, 2000);
            }
        });
    });
    
    // Initialize video controls
    function initVideoControls() {
        // Play overlay
        if (playOverlayBtn && videoPlayer) {
            playOverlayBtn.addEventListener('click', function() {
                videoPlayer.play();
                if (videoOverlay) {
                    videoOverlay.classList.add('hidden');
                }
            });
        }
        
        // Hide overlay when video starts playing
        if (videoPlayer) {
            videoPlayer.addEventListener('play', function() {
                if (videoOverlay) {
                    videoOverlay.classList.add('hidden');
                }
            });
            
            videoPlayer.addEventListener('pause', function() {
                if (videoOverlay) {
                    videoOverlay.classList.remove('hidden');
                }
            });
        }
        
        // Fullscreen button
        if (fullscreenBtn && videoPlayer) {
            fullscreenBtn.addEventListener('click', function() {
                if (videoPlayer.requestFullscreen) {
                    videoPlayer.requestFullscreen();
                } else if (videoPlayer.webkitRequestFullscreen) {
                    videoPlayer.webkitRequestFullscreen();
                } else if (videoPlayer.mozRequestFullScreen) {
                    videoPlayer.mozRequestFullScreen();
                } else if (videoPlayer.msRequestFullscreen) {
                    videoPlayer.msRequestFullscreen();
                }
            });
        }
        
        // Picture-in-Picture button
        if (pipBtn && videoPlayer) {
            pipBtn.addEventListener('click', async function() {
                if (document.pictureInPictureElement) {
                    await document.exitPictureInPicture();
                } else if (videoPlayer.requestPictureInPicture) {
                    await videoPlayer.requestPictureInPicture();
                }
            });
        }
        
        // Share button
        if (shareBtn && currentDocumentaryId) {
            shareBtn.addEventListener('click', async function() {
                if (navigator.share) {
                    try {
                        await navigator.share({
                            title: titleInput ? titleInput.value : 'Generated Documentary',
                            text: descriptionInput ? descriptionInput.value : '',
                            url: window.location.href
                        });
                    } catch (e) {
                        console.log('Share cancelled');
                    }
                } else {
                    // Fallback: copy to clipboard
                    navigator.clipboard.writeText(window.location.href);
                    showToast('Link copied to clipboard!', 'success');
                }
            });
        }
        
        // Regenerate button
        if (regenerateBtn) {
            regenerateBtn.addEventListener('click', function() {
                if (confirm('Are you sure you want to regenerate this documentary?')) {
                    // Scroll to top and trigger generation again
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                    if (generateBtn && !generateBtn.disabled) {
                        generateBtn.click();
                    }
                }
            });
        }
        
        // Copy embed code button
        if (copyEmbedBtn && embedCode) {
            copyEmbedBtn.addEventListener('click', function() {
                embedCode.select();
                document.execCommand('copy');
                showToast('Embed code copied to clipboard!', 'success');
            });
        }
        
        // Update embed code when options change
        [embedAutoplay, embedControls, embedLoop].forEach(input => {
            if (input) {
                input.addEventListener('change', updateEmbedCode);
            }
        });
        
        function updateEmbedCode() {
            if (!embedCode || !embedBtn) return;
            embedBtn.click(); // Re-generate embed code with new options
        }
    }
    
    // Initialize keyboard shortcuts
    function initKeyboardShortcuts() {
        document.addEventListener('keydown', function(e) {
            // Ctrl+Enter to generate
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                if (generateBtn && !generateBtn.disabled) {
                    e.preventDefault();
                    generateBtn.click();
                }
            }
            
            // Escape to close modals
            if (e.key === 'Escape') {
                if (settingsPanel && settingsPanel.classList.contains('active')) {
                    settingsPanel.classList.remove('active');
                }
                if (errorMessage && errorMessage.style.display !== 'none') {
                    hideError();
                }
            }
        });
    }
    
    // Initialize prompt suggestions from previous searches - ENHANCED
    function initPromptSuggestions() {
        const suggestionsContainer = document.getElementById('suggestions-buttons');
        const suggestionsLoading = document.getElementById('suggestions-loading');
        
        if (!suggestionsContainer) {
            console.warn('[Suggestions] Container not found');
            return;
        }
        
        // Show loading
        if (suggestionsLoading) {
            suggestionsLoading.style.display = 'block';
        }
        suggestionsContainer.innerHTML = '';
        
        // Default suggestions (fallback)
        const defaultSuggestions = [
            'A comprehensive documentary about the history of space exploration, from the first satellites to Mars missions',
            'An in-depth look at ancient civilizations and their architectural marvels',
            'The evolution of artificial intelligence and its impact on modern society',
            'A journey through the world\'s most beautiful natural landscapes and ecosystems',
            'The history and culture of medieval Europe, featuring castles, knights, and battles',
            'Exploring the depths of the ocean and its mysterious creatures',
            'The rise of renewable energy and sustainable technologies',
            'A documentary about the world\'s greatest artists and their masterpieces'
        ];
        
        // Fetch suggestions from API
        fetch(apiUrl('api/prompt/suggestions'))
            .then(response => response.json())
            .then(data => {
                // Hide loading
                if (suggestionsLoading) {
                    suggestionsLoading.style.display = 'none';
                }
                
                let suggestions = [];
                if (data.success && data.suggestions && data.suggestions.length > 0) {
                    suggestions = data.suggestions;
                } else {
                    // Use default suggestions if API returns none
                    suggestions = defaultSuggestions;
                }
                
                // Also add default suggestions if we have less than 5
                if (suggestions.length < 5) {
                    suggestions = [...suggestions, ...defaultSuggestions.slice(0, 5 - suggestions.length)];
                }
                
                // Create suggestion buttons
                suggestions.forEach((prompt, index) => {
                    const button = document.createElement('button');
                    button.className = 'suggestion-chip';
                    button.innerHTML = `<i class="fas fa-lightbulb"></i> ${prompt.length > 50 ? prompt.substring(0, 50) + '...' : prompt}`;
                    button.title = prompt; // Full prompt on hover
                    button.setAttribute('data-prompt', prompt);
                    
                    // Click handler - enhanced
                    button.addEventListener('click', function() {
                        if (promptInput) {
                            const currentValue = promptInput.value.trim();
                            // If there's existing text, append with proper formatting
                            if (currentValue && !currentValue.endsWith('.') && !currentValue.endsWith('!') && !currentValue.endsWith('?')) {
                                promptInput.value = currentValue + '. ' + prompt;
                            } else if (currentValue) {
                                promptInput.value = currentValue + ' ' + prompt;
                            } else {
                                promptInput.value = prompt;
                            }
                            
                            promptInput.dispatchEvent(new Event('input', { bubbles: true }));
                            
                            // Update character counter
                            if (promptCounter) {
                                promptCounter.textContent = promptInput.value.length;
                            }
                            
                            // Focus on input
                            promptInput.focus();
                            
                            // Scroll to input
                            promptInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            
                            // Show success message
                            showToast('Prompt suggestion added!', 'success');
                            
                            // Highlight the button briefly
                            button.style.transform = 'scale(0.95)';
                            setTimeout(() => {
                                button.style.transform = '';
                            }, 200);
                        }
                    });
                    
                    suggestionsContainer.appendChild(button);
                });
                
                console.log(`[Suggestions] Loaded ${suggestions.length} suggestions`);
            })
            .catch(error => {
                console.error('[Suggestions] Error loading suggestions:', error);
                
                // Hide loading
                if (suggestionsLoading) {
                    suggestionsLoading.style.display = 'none';
                }
                
                // Show default suggestions even on error
                defaultSuggestions.slice(0, 5).forEach((prompt, index) => {
                    const button = document.createElement('button');
                    button.className = 'suggestion-chip';
                    button.innerHTML = `<i class="fas fa-lightbulb"></i> ${prompt.length > 50 ? prompt.substring(0, 50) + '...' : prompt}`;
                    button.title = prompt;
                    button.setAttribute('data-prompt', prompt);
                    
                    button.addEventListener('click', function() {
                        if (promptInput) {
                            const currentValue = promptInput.value.trim();
                            if (currentValue && !currentValue.endsWith('.') && !currentValue.endsWith('!') && !currentValue.endsWith('?')) {
                                promptInput.value = currentValue + '. ' + prompt;
                            } else if (currentValue) {
                                promptInput.value = currentValue + ' ' + prompt;
                            } else {
                                promptInput.value = prompt;
                            }
                            promptInput.dispatchEvent(new Event('input', { bubbles: true }));
                            if (promptCounter) {
                                promptCounter.textContent = promptInput.value.length;
                            }
                            promptInput.focus();
                            showToast('Prompt suggestion added!', 'success');
                        }
                    });
                    
                    suggestionsContainer.appendChild(button);
                });
            });
        
        // Refresh suggestions every 30 seconds
        setInterval(initPromptSuggestions, 30000);
    }
    
    // Matrix canvas rain effect
    let matrixCanvas = null;
    let matrixCtx = null;
    let matrixDrops = [];
    let matrixAnimationFrame = null;
    
    // Matrix canvas initialization - MORE VISIBLE
    function initMatrixCanvas() {
        matrixCanvas = document.getElementById('matrix-canvas');
        if (!matrixCanvas) {
            console.error('[Matrix] Canvas not found');
            return;
        }
        
        console.log('[Matrix] Initializing canvas...');
        const container = matrixCanvas.parentElement;
        if (!container) {
            console.error('[Matrix] Container not found');
            return;
        }
        
        // Set canvas size to match container
        const width = container.clientWidth || 800;
        const height = container.clientHeight || 500;
        
        matrixCanvas.width = width;
        matrixCanvas.height = height;
        matrixCanvas.style.width = width + 'px';
        matrixCanvas.style.height = height + 'px';
        
        matrixCtx = matrixCanvas.getContext('2d');
        matrixCtx.fillStyle = '#00ff00';
        matrixCtx.font = 'bold 16px monospace';
        matrixCtx.textBaseline = 'top';
        
        // Create drops
        const fontSize = 16;
        const columns = Math.ceil(width / fontSize);
        matrixDrops = [];
        
        for (let i = 0; i < columns; i++) {
            matrixDrops[i] = Math.random() * -100;
        }
        
        console.log('[Matrix] Canvas initialized:', matrixCanvas.width, 'x', matrixCanvas.height, 'columns:', columns);
        startMatrixRain();
        
        // Handle window resize
        let resizeTimeout;
        window.addEventListener('resize', function() {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(function() {
                if (matrixCanvas && matrixCanvas.parentElement) {
                    const container = matrixCanvas.parentElement;
                    const newWidth = container.clientWidth || 800;
                    const newHeight = container.clientHeight || 500;
                    
                    matrixCanvas.width = newWidth;
                    matrixCanvas.height = newHeight;
                    matrixCanvas.style.width = newWidth + 'px';
                    matrixCanvas.style.height = newHeight + 'px';
                    
                    // Recalculate drops
                    const fontSize = 16;
                    const columns = Math.ceil(newWidth / fontSize);
                    const oldLength = matrixDrops.length;
                    matrixDrops.length = columns;
                    
                    // Initialize new columns
                    for (let i = oldLength; i < columns; i++) {
                        matrixDrops[i] = Math.random() * -100;
                    }
                    
                    console.log('[Matrix] Canvas resized to:', newWidth, 'x', newHeight);
                }
            }, 250);
        });
    }
    
    // Matrix rain animation - MORE VISIBLE
    function startMatrixRain() {
        if (!matrixCanvas || !matrixCtx) return;
        
        // More transparent fade for better visibility
        matrixCtx.fillStyle = 'rgba(0, 0, 0, 0.08)';
        matrixCtx.fillRect(0, 0, matrixCanvas.width, matrixCanvas.height);
        
        matrixCtx.fillStyle = '#00ff00';
        matrixCtx.font = 'bold 16px monospace';
        matrixCtx.textBaseline = 'top';
        
        const chars = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!@#$%^&*()[]{}|;:<>?/';
        const fontSize = 16;
        const columns = Math.ceil(matrixCanvas.width / fontSize);
        
        // Ensure drops array matches columns
        while (matrixDrops.length < columns) {
            matrixDrops.push(Math.random() * -100);
        }
        
        for (let i = 0; i < Math.min(matrixDrops.length, columns); i++) {
            const text = chars[Math.floor(Math.random() * chars.length)];
            const x = i * fontSize;
            const y = matrixDrops[i] * fontSize;
            
            // More visible fade effect
            const opacity = Math.min(1, Math.max(0.3, (matrixCanvas.height - y) / fontSize / 8));
            
            // Brighter green for better visibility
            const greenIntensity = Math.min(255, 100 + (opacity * 155));
            matrixCtx.fillStyle = `rgba(0, ${greenIntensity}, 0, ${opacity})`;
            
            matrixCtx.fillText(text, x, y);
            
            // Occasionally highlight first character
            if (i === 0 && Math.random() > 0.95) {
                matrixCtx.fillStyle = 'rgba(255, 255, 255, 0.9)';
                matrixCtx.fillText(text, x, y - fontSize);
            }
            
            if (y > matrixCanvas.height && Math.random() > 0.975) {
                matrixDrops[i] = 0;
            } else {
                matrixDrops[i]++;
            }
        }
        
        matrixAnimationFrame = requestAnimationFrame(startMatrixRain);
    }
    
    function stopMatrixRain() {
        if (matrixAnimationFrame) {
            cancelAnimationFrame(matrixAnimationFrame);
            matrixAnimationFrame = null;
        }
        if (matrixCtx) {
            matrixCtx.clearRect(0, 0, matrixCanvas?.width || 0, matrixCanvas?.height || 0);
        }
    }
    
    // Initialize Matrix display
    function initMatrixDisplay() {
        console.log('[Matrix] initMatrixDisplay called');
        console.log('[Matrix] matrixDisplay exists:', !!matrixDisplay);
        console.log('[Matrix] matrixCodeDisplay exists:', !!matrixCodeDisplay);
        
        if (!matrixDisplay || !matrixCodeDisplay) {
            console.error('[Matrix] ERROR: matrixDisplay or matrixCodeDisplay not found!');
            return;
        }
        
        // Initialize canvas rain effect
        initMatrixCanvas();
        
        console.log('[Matrix] Starting matrix code generation');
        // Start matrix code generation
        startMatrixCodeGeneration();
    }
    
    // Generate Matrix-style code with real data
    function startMatrixCodeGeneration() {
        console.log('[Matrix] startMatrixCodeGeneration called');
        if (!matrixCodeDisplay) {
            console.error('[Matrix] ERROR: matrixCodeDisplay not found!');
            return;
        }
        
        console.log('[Matrix] Starting code generation interval');
        
        const chars = '01ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!@#$%^&*()[]{}|;:<>?/';
        const commands = [
            // Initialization phase commands
            '> INITIALIZING DOCUMENTARY GENERATOR...',
            '> Loading AI models and resources...',
            '> Connecting to video generation API...',
            '> Preparing content pipeline...',
            '> Analyzing prompt structure...',
            '> Initializing neural networks...',
            '> Loading emotion trigger system...',
            '> Preparing video generator modules...',
            '> Connecting to ElevenLabs TTS API...',
            '> System check: All modules OK',
            
            // Search/Analysis phase commands
            '> Searching web for images and scripts...',
            '> Fetching relevant content from web...',
            '> Processing image metadata...',
            '> Analyzing visual requirements...',
            '> Building content library...',
            '> Scraping web data: 45% complete...',
            '> Found 12 relevant images',
            '> Found 8 script snippets',
            '> Processing scraped data...',
            '> Content library built: 100%',
            
            // Content creation phase commands
            '> Generating video clips...',
            '> Creating scene compositions...',
            '> Processing visual effects...',
            '> Applying color grading...',
            '> Optimizing frame sequences...',
            '> Downloading clip 1/8 from API...',
            '> Clip 1/8 downloaded: 10.5s @ 30fps',
            '> Processing clip 2/8...',
            '> Clip 2/8 complete: 120 seconds total',
            '> Generating clip 3/8 with emotion effects...',
            '> Clips generated: 3/8 | Duration: 120s/180s',
            '> Target duration reached: 180s',
            '> All clips generated successfully',
            
            // Combining clips phase
            '> COMBINING VIDEO CLIPS INTO SINGLE MP4',
            '> Total clips to combine: 8',
            '> Loading clip 1/8: 10.5s, 2.3MB',
            '> Loading clip 2/8: 10.5s, 2.1MB',
            '> All clips loaded successfully',
            '> Concatenating 8 clips using MoviePy...',
            '> Method: compose (handles different resolutions)',
            '> Concatenation complete!',
            '> Final video: 84.0s @ 30fps, 1920x1080',
            
            // Encoding phase commands
            'ffmpeg -i input.mp4 -c:v libx264 -preset medium -crf 23',
            'frame=  1234 fps= 45 q=23.0 size=   12345kB time=00:00:41.23',
            '[libx264 @ 0x7f8a2c004b00] frame I:234  P:5678  B:12345',
            '[libx264 @ 0x7f8a2c004b00] kb/s:1234.56 frame=5678 fps=45',
            'bitrate=1234.56kbits/s speed=1.5x',
            'frame=12345 fps=30 q=23.0 Lsize=123456kB time=00:03:21.45',
            '[h264 @ 0x7f8a2c004b00] Reinit context to 1920x1080',
            '[libx264 @ 0x7f8a2c004b00] using cpu capabilities: MMX2 SSE2Fast SSSE3',
            'Encoding: frame 5678/18000 [31.5%]',
            'Buffer status: 85% |████████████████░░░░░░|',
            'Video codec: H.264/AVC | Audio codec: AAC',
            'Stream mapping: Video -> Stream #0:0, Audio -> Stream #0:1',
            '[out#0/mp4 @ 0x7f8a2c004b00] video:123456kB audio:12345kB',
            'Total time: 00:03:21.45 | Encoding time: 00:01:23.45',
            'FPS: 30.00 | Bitrate: 1234.56 kbps | Size: 123.45 MB',
            '[Pipeline] Writing video file to disk...',
            '[Pipeline] Encoding video frames (H.264 compression)...',
            '[Pipeline] Compressing video data (reducing file size)...',
            '[Pipeline] Processing video segments (combining clips)...',
            '[Pipeline] Rendering final output (optimizing quality)...',
            '[Pipeline] Video encoding complete and verified!',
            '[Pipeline] SUCCESS: SINGLE MP4 FILE CREATED',
            '[Pipeline] File: output/abc123.mp4 | Size: 45.2MB',
            
            // Audio phase commands
            '> Generating TTS narration...',
            '> Synchronizing audio tracks...',
            '> Mixing background music...',
            '> Applying audio filters...',
            '> Normalizing audio levels...',
            '> Connecting to ElevenLabs API...',
            '> Generating speech from script...',
            '> Audio generated: 84.0s duration',
            '> Adding audio to video...',
            '> Audio sync complete',
            
            // Finalization commands
            '> Finalizing video output...',
            '> Creating thumbnail image...',
            '> Generating metadata...',
            '> Preparing for upload...',
            '> Verification: MP4 header check OK',
            '> File integrity verified',
            '> COMPLETION: 100%',
            '> ALL OPERATIONS COMPLETE'
        ];
        
        let lineIndex = 0;
        
        // Matrix Trilogy timestamp format: YYYYMMDD-HHMMSS.mmm
        function getMatrixTimestamp() {
            const now = new Date();
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            const milliseconds = String(now.getMilliseconds()).padStart(3, '0');
            
            return `${year}${month}${day}-${hours}${minutes}${seconds}.${milliseconds}`;
        }
        
        function addMatrixLine() {
            if (!matrixCodeDisplay) return;
            
            // Matrix Trilogy style timestamp
            const timestamp = getMatrixTimestamp();
            const randomCommand = commands[Math.floor(Math.random() * commands.length)];
            const randomChars = Array.from({length: 50}, () => chars[Math.floor(Math.random() * chars.length)]).join('');
            
            // Mix real data with matrix code
            const currentPercent = window.currentProgressPercent || 0;
            
            // Create line with Matrix trilogy styling
            let line = `<span class="matrix-timestamp">[${timestamp}]</span> <span class="matrix-command">${randomCommand}</span>\n`;
            
            // Add phase-specific details with styling
            if (currentPercent >= 65 && matrixStats.totalFrames > 0) {
                // Encoding phase - show frame progress
                const frameProgress = ((matrixStats.framesEncoded / matrixStats.totalFrames) * 100).toFixed(2);
                line += `         <span class="matrix-data">frame=${matrixStats.framesEncoded}/${matrixStats.totalFrames} [${frameProgress}%]</span>\n`;
                line += `         <span class="matrix-data">bitrate=${matrixStats.bitrate.toFixed(2)}kbits/s speed=${matrixStats.encodingSpeed.toFixed(2)}x</span>\n`;
                line += `         <span class="matrix-data">buffer=${matrixStats.bufferSize}MB cpu=${Math.round(matrixStats.cpuUsage)}%</span>\n`;
            } else if (currentPercent >= 70 && currentPercent < 80) {
                // Combining clips phase
                const clipsPhase = currentPercent >= 72 && currentPercent < 74 ? 'LOADING' : 'CONCATENATING';
                line += `         <span class="matrix-data">phase=${clipsPhase}_CLIPS</span>\n`;
                line += `         <span class="matrix-data">progress=${currentPercent.toFixed(2)}% | buffer=${matrixStats.bufferSize}MB</span>\n`;
            } else if (currentPercent >= 30 && currentPercent < 70) {
                // Generating clips phase
                const estimatedClips = Math.ceil((currentPercent - 30) / 5);
                line += `         <span class="matrix-data">phase=GENERATING_CLIPS</span>\n`;
                line += `         <span class="matrix-data">clip=${estimatedClips}/8 | progress=${currentPercent.toFixed(2)}%</span>\n`;
            } else if (currentPercent >= 5) {
                // Other phases
                line += `         <span class="matrix-data">phase=${getCurrentPhase(currentPercent)}</span>\n`;
                line += `         <span class="matrix-data">progress=${currentPercent.toFixed(2)}% | cpu=${Math.round(matrixStats.cpuUsage)}%</span>\n`;
            }
            
            // Add random chars for Matrix effect (less frequent, more meaningful)
            if (Math.random() > 0.3) {
                line += `         <span class="matrix-data">${randomChars.substring(0, 50)}</span>\n`;
            }
            
            // Add system info line occasionally
            if (Math.random() > 0.75) {
                const memory = (matrixStats.bufferSize * 2.5).toFixed(0);
                line += `         <span class="matrix-data">[SYSTEM] Memory: ${memory}MB | Process: python3 run.py | PID: ${Math.floor(Math.random() * 9999) + 1000}</span>\n`;
            }
            
            line += `\n`;
            
            matrixCodeBuffer += line;
            
            // Keep only last 60 lines (more for better Matrix effect)
            const lines = matrixCodeBuffer.split('\n');
            if (lines.length > 60) {
                matrixCodeBuffer = lines.slice(-60).join('\n');
            }
            
            // Use innerHTML for styled content with Matrix Trilogy styling
            matrixCodeDisplay.innerHTML = matrixCodeBuffer;
            
            // Auto-scroll to bottom
            matrixCodeDisplay.scrollTop = matrixCodeDisplay.scrollHeight;
        }
        
        // Add new line every 500ms
        matrixUpdateInterval = setInterval(addMatrixLine, 500);
        
        // Initial line
        addMatrixLine();
    }
    
    function stopMatrixCodeGeneration() {
        if (matrixUpdateInterval) {
            clearInterval(matrixUpdateInterval);
            matrixUpdateInterval = null;
        }
        stopMatrixRain();
    }
    
    function getCurrentPhase(percent) {
        if (percent < 10) return 'INITIALIZING';
        if (percent < 20) return 'SEARCHING';
        if (percent < 30) return 'ANALYZING';
        if (percent < 50) return 'CREATING';
        if (percent < 65) return 'GENERATING';
        if (percent < 70) return 'INIT_ENCODER';
        if (percent < 75) return 'ENCODING';
        if (percent < 80) return 'FINAL_ENCODE';
        if (percent < 90) return 'ADDING_AUDIO';
        if (percent < 95) return 'FINALIZING';
        return 'COMPLETING';
    }
    
    // Update Matrix stats
    function updateMatrixStats(percent, etaInfo) {
        if (!matrixDisplay) {
            console.log('[Matrix] updateMatrixStats: matrixDisplay not found');
            return;
        }
        
        const currentTime = Date.now();
        const timeElapsed = generationStartTime ? Math.round((currentTime - generationStartTime) / 1000) : 0;
        
        // Update new stats
        updatePhaseStats(percent);
        updateResourceStats(percent);
        updateSessionStats();
        
        // Update stats for all phases (from 0% onwards)
        if (percent >= 0) {
            // Different phases have different stats
            if (percent < 65) {
                // Pre-encoding phases (5-65%)
                // Estimate frames based on 30fps and 3-minute video (180 seconds = 5400 frames)
                const estimatedTotalFrames = 5400;
                matrixStats.totalFrames = estimatedTotalFrames;
                // Before encoding, frames are 0 but we show progress
                const preEncodingProgress = percent / 65; // 0 to 1
                matrixStats.framesEncoded = Math.floor(estimatedTotalFrames * preEncodingProgress * 0.1); // Small progress before encoding
                
                // Simulate bitrate building up
                matrixStats.bitrate = Math.max(100, (percent / 65) * 800); // 100-800 kbps
                
                // Buffer size grows slowly
                matrixStats.bufferSize = Math.floor((percent / 65) * 50); // Up to 50 MB before encoding
                
                // CPU usage varies by phase
                if (percent < 30) {
                    matrixStats.cpuUsage = 20 + (Math.sin(timeElapsed / 3) * 10); // 10-30%
                } else {
                    matrixStats.cpuUsage = 30 + (Math.sin(timeElapsed / 4) * 15); // 15-45%
                }
                
                // No encoding speed before encoding phase
                matrixStats.encodingSpeed = 0;
            } else {
                // Encoding phase (65%+)
                const encodingProgress = (percent - 65) / 35; // 0 to 1 in encoding phase (65-100%)
                
                // Estimate frames based on 30fps and 3-minute video (180 seconds = 5400 frames)
                const estimatedTotalFrames = 5400;
                matrixStats.totalFrames = estimatedTotalFrames;
                const encodingFrameProgress = encodingProgress * 0.9; // Most frames encoded in this phase
                matrixStats.framesEncoded = Math.floor(estimatedTotalFrames * (0.1 + encodingFrameProgress));
                
                // Estimate bitrate (increases with encoding)
                matrixStats.bitrate = 800 + (encodingProgress * 600); // 800-1400 kbps
                
                // Estimate buffer size (MB)
                matrixStats.bufferSize = Math.floor(50 + ((percent - 65) / 35) * 100); // 50-150 MB
                
                // Simulate CPU usage (varies during encoding)
                matrixStats.cpuUsage = 60 + (Math.sin(timeElapsed / 5) * 20); // 40-80%
                
                // Encoding speed varies
                matrixStats.encodingSpeed = 1.2 + (Math.sin(timeElapsed / 3) * 0.5); // 0.7-1.7x
            }
            
            // Update UI elements
            if (matrixFrames) {
                if (percent < 65) {
                    matrixFrames.textContent = `Preparing.../${matrixStats.totalFrames}`;
                } else {
                    matrixFrames.textContent = `${matrixStats.framesEncoded}/${matrixStats.totalFrames}`;
                }
            }
            
            if (matrixBitrate) {
                if (percent < 65) {
                    matrixBitrate.textContent = `Calculating...`;
                } else {
                    matrixBitrate.textContent = `${matrixStats.bitrate.toFixed(2)} kbps`;
                }
            }
            
            if (matrixBuffer) {
                matrixBuffer.textContent = `${matrixStats.bufferSize} MB`;
            }
            
            if (matrixCpu) {
                matrixCpu.textContent = `${Math.round(matrixStats.cpuUsage)}%`;
            }
            
            if (matrixSpeed) {
                if (percent < 65) {
                    matrixSpeed.textContent = `--x`;
                } else {
                    matrixSpeed.textContent = `${matrixStats.encodingSpeed.toFixed(2)}x`;
                }
            }
            
            if (matrixElapsed) {
                const mins = Math.floor(timeElapsed / 60);
                const secs = timeElapsed % 60;
                matrixElapsed.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
            }
            
            if (matrixEta && etaInfo.eta !== null) {
                matrixEta.textContent = formatTime(etaInfo.eta);
            } else if (matrixEta) {
                matrixEta.textContent = 'Calculating...';
            }
            
            if (matrixProgress) {
                matrixProgress.textContent = `${percent.toFixed(2)}%`;
            }
            
            // Update encoder/codec based on phase
            if (matrixEncoder) {
                if (percent < 65) {
                    matrixEncoder.textContent = 'Preparing...';
                } else {
                    matrixEncoder.textContent = 'H.264/AVC';
                }
            }
            
            if (matrixCodec) {
                if (percent < 65) {
                    matrixCodec.textContent = 'Initializing...';
                } else {
                    matrixCodec.textContent = 'libx264';
                }
            }
        }
    }
    
    // Matrix logic is now integrated directly into showProgress function above
    
    // ========== MATRIX MONITOR FUNCTIONS ==========
    // Global functions for monitor visibility (must be on window object)
    window.showMonitor = function() {
        console.log('[Monitor] showMonitor() called');
        const monitorEl = document.getElementById('matrix-monitor');
        if (monitorEl) {
            console.log('[Monitor] ✓ Element found, forcing visibility...');
            
            // REMOVE ALL INLINE STYLES
            monitorEl.removeAttribute('style');
            
            // FORCE WITH setProperty (stronger than style.xxx)
            monitorEl.style.setProperty('display', 'block', 'important');
            monitorEl.style.setProperty('visibility', 'visible', 'important');
            monitorEl.style.setProperty('opacity', '1', 'important');
            monitorEl.style.setProperty('position', 'relative', 'important');
            monitorEl.style.setProperty('z-index', '5000', 'important');
            
            // ALSO SET DIRECTLY (backup)
            monitorEl.style.display = 'block';
            monitorEl.style.visibility = 'visible';
            monitorEl.style.opacity = '1';
            monitorEl.style.position = 'relative';
            monitorEl.style.zIndex = '5000';
            
            // ADD CLASSES AND ATTRIBUTES
            monitorEl.classList.add('matrix-active');
            monitorEl.setAttribute('data-matrix-active', 'true');
            
            // Verify visibility
            const computed = window.getComputedStyle(monitorEl);
            const rect = monitorEl.getBoundingClientRect();
            console.log('[Monitor] Verification:');
            console.log('[Monitor] - Computed display:', computed.display);
            console.log('[Monitor] - Computed visibility:', computed.visibility);
            console.log('[Monitor] - Computed opacity:', computed.opacity);
            console.log('[Monitor] - Element size:', rect.width, 'x', rect.height);
            console.log('[Monitor] - Visible?', rect.width > 0 && rect.height > 0);
            
            // Initialize border rain if not already
            if (typeof initMatrixCanvasBorder === 'function') {
                setTimeout(function() {
                    initMatrixCanvasBorder();
                    if (typeof startMatrixRainBorder === 'function') {
                        startMatrixRainBorder();
                    }
                }, 100);
            }
        } else {
            console.error('[Monitor] ERROR: matrix-monitor element not found!');
            // Try to find it
            const allMonitors = document.querySelectorAll('[id*="monitor"], [class*="monitor"]');
            console.log('[Monitor] Found elements with "monitor" in id/class:', allMonitors.length);
            allMonitors.forEach(function(el, i) {
                console.log('[Monitor] Element', i, ':', el.id, el.className);
            });
        }
    };
    
    window.hideMonitor = function() {
        console.log('[Monitor] hideMonitor called');
        const monitor = document.getElementById('matrix-monitor');
        if (monitor) {
            monitor.style.display = 'none';
            monitor.classList.remove('matrix-active');
            monitor.removeAttribute('data-matrix-active');
            if (typeof stopMatrixRainBorder === 'function') {
                stopMatrixRainBorder();
            }
        }
    };
    
    // Update monitor clip information
    window.updateMonitorClipInfo = function(currentClip, totalClips, clipDetails) {
        if (monitorTotalClips) monitorTotalClips.textContent = totalClips || 0;
        if (monitorCurrentClip) monitorCurrentClip.textContent = `${currentClip || 0}/${totalClips || 0}`;
        if (monitorClipDuration) monitorClipDuration.textContent = clipDetails?.duration ? `${clipDetails.duration.toFixed(2)}s` : '0.00s';
        if (monitorClipSize) monitorClipSize.textContent = clipDetails?.size ? `${clipDetails.size.toFixed(2)} MB` : '0 MB';
        if (monitorClipResolution) monitorClipResolution.textContent = clipDetails?.resolution || '--x--';
        if (monitorClipFps) monitorClipFps.textContent = clipDetails?.fps || '--';
        if (monitorText) {
            const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
            // Slow down text speed - add delay before scrolling
            const textSpeed = parseFloat(localStorage.getItem('monitor-text-speed') || '1.0');
            const delay = (1000 / textSpeed); // Delay in ms based on speed (lower speed = longer delay)
            
            // Use limited lines function
            addMonitorTextLine(`[${timestamp}] > CLIP: ${currentClip}/${totalClips} | ${clipDetails?.duration?.toFixed(2) || '0.00'}s | ${clipDetails?.size?.toFixed(2) || '0'}MB`);
            
            // Auto-scroll only if enabled, and with delay for readability
            const autoScroll = localStorage.getItem('monitor-auto-scroll') !== 'false';
            if (autoScroll) {
                setTimeout(function() {
                    monitorText.scrollTop = monitorText.scrollHeight;
                }, delay);
            }
        }
    };
    
    // Update monitor combined video information
    window.updateMonitorCombinedVideo = function(outputPath, videoDetails) {
        if (monitorOutputFile) monitorOutputFile.textContent = outputPath ? outputPath.split('/').pop().split('\\').pop() : '--';
        if (monitorTotalDuration) monitorTotalDuration.textContent = videoDetails?.duration ? `${videoDetails.duration.toFixed(2)}s` : '0.00s';
        if (monitorTotalSize) monitorTotalSize.textContent = videoDetails?.size ? `${videoDetails.size.toFixed(2)} MB` : '0 MB';
        if (monitorCombinedResolution) monitorCombinedResolution.textContent = videoDetails?.resolution || '--x--';
        if (monitorCombinedFps) monitorCombinedFps.textContent = videoDetails?.fps || '--';
        if (monitorEncodingStatus) monitorEncodingStatus.textContent = videoDetails?.status ? videoDetails.status.toUpperCase() : 'UNKNOWN';
        if (monitorText) {
            const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
            // Slow down text speed
            const textSpeed = parseFloat(localStorage.getItem('monitor-text-speed') || '1.0');
            const delay = (1000 / textSpeed);
            
            // Use limited lines function
            const fileName = outputPath ? outputPath.split('/').pop().split('\\').pop() : '--';
            addMonitorTextLine(`[${timestamp}] > VIDEO: ${fileName.substring(0, 30)} | ${videoDetails?.status?.toUpperCase() || 'UNKNOWN'}`);
            
            const autoScroll = localStorage.getItem('monitor-auto-scroll') !== 'false';
            if (autoScroll) {
                setTimeout(function() {
                    monitorText.scrollTop = monitorText.scrollHeight;
                }, delay);
            }
        }
    };
    
    // Update monitor clip list
    window.updateMonitorClipList = function(clips) {
        if (monitorClipDetails && clips && Array.isArray(clips)) {
            let clipListText = '';
            let cumulativeDuration = 0;
            clips.forEach((clip, index) => {
                cumulativeDuration += clip.duration || 0;
                const clipPath = clip.path || clip.file || '';
                const fileName = clipPath.split('/').pop().split('\\').pop() || `clip_${index + 1}`;
                clipListText += `[${String(index + 1).padStart(2, '0')}] ${fileName} | Dur: ${(clip.duration || 0).toFixed(2)}s | Cum.Dur: ${cumulativeDuration.toFixed(2)}s\n`;
            });
            monitorClipDetails.textContent = clipListText || 'No clips loaded yet...';
            const clipList = document.getElementById('monitor-clip-list');
            if (clipList) clipList.scrollTop = clipList.scrollHeight;
        }
    };
    
    // Helper function to limit monitor text lines (optimized for fixed height, no blinking)
    function addMonitorTextLine(text) {
        if (!monitorText) return;
        
        // Calculate max lines based on fixed height (300px) and line-height (1.5)
        // With padding (1rem top + 1rem bottom = ~32px) and font-size (0.9rem = ~14.4px)
        // Available height: ~268px, each line: ~21.6px (14.4 * 1.5)
        // Max lines: ~12-13 lines
        const maxLines = 13; // Optimized for 300px fixed height
        
        // Get current lines (filter empty lines but keep structure)
        const currentContent = monitorText.textContent || '';
        const lines = currentContent.split('\n').filter(line => line.trim() !== '' || line === '');
        
        // Add new line
        if (text && text.trim()) {
            lines.push(text.trim());
        }
        
        // Keep only last maxLines (remove oldest lines)
        while (lines.length > maxLines) {
            lines.shift();
        }
        
        // Use requestAnimationFrame for smooth, non-blinking updates
        requestAnimationFrame(() => {
            if (!monitorText) return;
            
            // Store current scroll position if needed (though we're hiding scrollbar)
            const wasAtBottom = monitorText.scrollHeight - monitorText.scrollTop <= monitorText.clientHeight + 5;
            
            // Update text content smoothly
            monitorText.textContent = lines.join('\n');
            
            // Ensure we stay at bottom if we were there (for smooth scrolling)
            if (wasAtBottom) {
                requestAnimationFrame(() => {
                    if (monitorText) {
                        monitorText.scrollTop = monitorText.scrollHeight;
                    }
                });
            }
        });
    }
    
    // Update Monitor with generation requirements (ENHANCED)
    window.updateMonitorRequirements = function(prompt, title, themeName, emotion) {
        const monitorPrompt = document.getElementById('monitor-prompt');
        const monitorTitle = document.getElementById('monitor-title');
        const monitorTheme = document.getElementById('monitor-theme');
        const monitorEmotion = document.getElementById('monitor-emotion');
        
        if (monitorPrompt) monitorPrompt.textContent = prompt || '--';
        if (monitorTitle) monitorTitle.textContent = title || prompt || '--';
        if (monitorTheme) {
            const theme = themes[themeName || currentTheme];
            monitorTheme.textContent = theme ? theme.name.toUpperCase() : (themeName || 'MATRIX').toUpperCase();
        }
        if (monitorEmotion) {
            monitorEmotion.textContent = emotion || 'ANALYZING...';
        }
        
        // Also log to monitor text (if not already logged) - using limited lines
        if (monitorText && (!monitorText.textContent || !monitorText.textContent.includes('REQUIREMENTS_LOADED'))) {
            const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
            const theme = themes[themeName || currentTheme];
            
            // Use addMonitorTextLine to limit lines
            addMonitorTextLine(`[${timestamp}] > REQUIREMENTS_LOADED`);
            addMonitorTextLine(`  PROMPT: ${(prompt || '--').substring(0, 50)}${(prompt && prompt.length > 50) ? '...' : ''}`);
            addMonitorTextLine(`  THEME: ${theme ? theme.name : (themeName || 'MATRIX')}`);
            addMonitorTextLine(`  STATUS: INITIALIZING`);
        }
    };
    
    // Update Storyline Visualization
    window.updateStorylineVisualization = function(storyline) {
        if (!storyline || !storyline.segments) return;
        
        const monitorTextEl = document.getElementById('monitor-text');
        if (monitorTextEl) {
            const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
            // Use limited lines function
            if (typeof addMonitorTextLine === 'function') {
                addMonitorTextLine(`[${timestamp}] > STORYLINE: ${storyline.segments.length} segments | ${storyline.total_duration?.toFixed(2) || 0}s`);
            } else {
                monitorTextEl.textContent += `[${timestamp}] > STORYLINE: ${storyline.segments.length} segments | ${storyline.total_duration?.toFixed(2) || 0}s\n`;
            monitorTextEl.scrollTop = monitorTextEl.scrollHeight;
            }
        }
        
        // Update clip list with storyline info
        const monitorClipDetails = document.getElementById('monitor-clip-details');
        if (monitorClipDetails && storyline.segments) {
            let clipListText = '';
            storyline.segments.forEach((segment) => {
                clipListText += `[${String(segment.index).padStart(2, '0')}] ${segment.story_position} | `;
                clipListText += `Start: ${segment.start_time?.toFixed(2) || '0.00'}s | `;
                clipListText += `Dur: ${segment.duration?.toFixed(2) || '0.00'}s\n`;
            });
            monitorClipDetails.textContent = clipListText || 'No clips in storyline yet...';
        }
    };
    
    // Initialize Movie World Portal with real data
    function initializeMovieWorldPortal() {
        // Update system equipment data
        updateSystemEquipment();
        
        // Update web data sources
        updateWebDataSources();
        
        // Update editable MP4 status
        updateEditableMP4Display();
        
        // Set up periodic updates
        setInterval(updateSystemEquipment, 5000); // Update every 5 seconds
        setInterval(updateWebDataSources, 10000); // Update every 10 seconds
        setInterval(updateServerTime, 1000); // Update server time every second
        setInterval(updateAPIKeyStatus, 30000); // Update API keys every 30 seconds
        setInterval(updatePerformanceMetrics, 5000); // Update performance every 5 seconds
        setInterval(updateGenerationAnalytics, 15000); // Update analytics every 15 seconds
    }
    
    // Update system equipment data from user's unit
    function updateSystemEquipment() {
        // CPU Usage (estimated based on performance)
        const cpuUsage = Math.min(100, Math.max(0, Math.random() * 30 + 10)); // Simulated 10-40%
        const cpuEl = document.getElementById('monitor-cpu-usage');
        if (cpuEl) cpuEl.textContent = cpuUsage.toFixed(1) + '%';
        
        // Memory Usage
        if (navigator.deviceMemory) {
            const memoryEl = document.getElementById('monitor-memory-usage');
            if (memoryEl) {
                const used = (navigator.deviceMemory * 0.3).toFixed(1);
                const total = navigator.deviceMemory.toFixed(1);
                memoryEl.textContent = used + ' / ' + total + ' GB';
            }
        } else {
            const memoryEl = document.getElementById('monitor-memory-usage');
            if (memoryEl) memoryEl.textContent = 'N/A';
        }
        
        // Disk Space (estimated)
        const diskEl = document.getElementById('monitor-disk-space');
        if (diskEl) {
            // This would need backend API to get real disk space
            diskEl.textContent = '-- GB';
        }
        
        // Network Status
        const networkEl = document.getElementById('monitor-network-status');
        if (networkEl) {
            networkEl.textContent = navigator.onLine ? 'ONLINE' : 'OFFLINE';
        }
        
        // Browser Info
        const browserEl = document.getElementById('monitor-browser-info');
        if (browserEl) {
            const browser = navigator.userAgent.includes('Chrome') ? 'Chrome' :
                           navigator.userAgent.includes('Firefox') ? 'Firefox' :
                           navigator.userAgent.includes('Safari') ? 'Safari' : 'Unknown';
            browserEl.textContent = browser;
        }
        
        // Screen Resolution
        const screenEl = document.getElementById('monitor-screen-res');
        if (screenEl) {
            screenEl.textContent = window.screen.width + 'x' + window.screen.height;
        }
    }
    
    // Update web data sources
    function updateWebDataSources() {
        // API Status
        const apiEl = document.getElementById('monitor-api-status');
        if (apiEl) {
            // Check if we can reach the API (try both /health and /api/health)
            Promise.race([
                fetch(apiUrl('health'), { method: 'GET', cache: 'no-cache' }).catch(() => null),
                fetch(apiUrl('api/health'), { method: 'GET', cache: 'no-cache' }).catch(() => null).catch(() => null) // Ignore 404
            ])
                .then((response) => {
                    if (response && response.ok) {
                        if (apiEl) apiEl.textContent = 'CONNECTED';
                    } else {
                        if (apiEl) apiEl.textContent = 'CHECKING...';
                    }
                })
                .catch(() => {
                    if (apiEl) apiEl.textContent = 'DISCONNECTED';
                });
        }
        
        // Active Generations (would need backend API)
        const activeGensEl = document.getElementById('monitor-active-gens');
        if (activeGensEl) {
            // This would need backend API call
            activeGensEl.textContent = currentDocumentaryId ? '1' : '0';
        }
        
        // Total Documentaries (would need backend API)
        const totalDocsEl = document.getElementById('monitor-total-docs');
        if (totalDocsEl) {
            // This would need backend API call
            totalDocsEl.textContent = '--';
        }
        
        // Update API Key Status
        updateAPIKeyStatus();
        
        // Update Performance Metrics
        updatePerformanceMetrics();
        
        // Update Generation Analytics
        updateGenerationAnalytics();
    }
    
    // Update API Key Status
    function updateAPIKeyStatus() {
        // Fetch API status from backend
        fetch(apiUrl('api/external-apis/status'), { method: 'GET', cache: 'no-cache' })
            .then(res => {
                if (!res.ok) {
                    return Promise.reject(new Error(`HTTP ${res.status}`));
                }
                return res.json();
            })
            .catch(err => {
                console.warn('External APIs status endpoint not available:', err);
                return null;
            })
            .then(data => {
                const openaiEl = document.getElementById('monitor-api-openai');
                const googleEl = document.getElementById('monitor-api-google');
                const hypertxtEl = document.getElementById('monitor-api-hypertxt');
                const vertechEl = document.getElementById('monitor-api-vertech');
                const seagoatEl = document.getElementById('monitor-api-seagoat');
                const fakenewsEl = document.getElementById('monitor-api-fakenews');
                
                // OpenAI (check localStorage or env)
                if (openaiEl) {
                    openaiEl.textContent = 'CHECKING...';
                    openaiEl.className = 'monitor-value status-warning';
                }
                
                // Google Credentials
                if (googleEl) {
                    const hasGoogle = localStorage.getItem('google_credentials_set') === 'true' || 
                                     document.cookie.includes('google_credentials');
                    googleEl.textContent = hasGoogle ? 'ACTIVE' : 'INACTIVE';
                    googleEl.className = 'monitor-value ' + (hasGoogle ? 'status-online' : 'status-offline');
                }
                
                // Hypertxt
                if (hypertxtEl && data.hypertxt) {
                    hypertxtEl.textContent = data.hypertxt.api_key ? 'ACTIVE' : 'INACTIVE';
                    hypertxtEl.className = 'monitor-value ' + (data.hypertxt.api_key ? 'status-online' : 'status-offline');
                } else if (hypertxtEl) {
                    hypertxtEl.textContent = 'UNKNOWN';
                    hypertxtEl.className = 'monitor-value status-warning';
                }
                
                // Vertech Academy
                if (vertechEl && data.vertech_academy) {
                    vertechEl.textContent = data.vertech_academy.api_key ? 'ACTIVE' : 'INACTIVE';
                    vertechEl.className = 'monitor-value ' + (data.vertech_academy.api_key ? 'status-online' : 'status-offline');
                } else if (vertechEl) {
                    vertechEl.textContent = 'UNKNOWN';
                    vertechEl.className = 'monitor-value status-warning';
                }
                
                // SeaGOAT
                if (seagoatEl && data.seagoat) {
                    seagoatEl.textContent = data.seagoat.installed ? 'INSTALLED' : 'NOT_INSTALLED';
                    seagoatEl.className = 'monitor-value ' + (data.seagoat.installed ? 'status-online' : 'status-offline');
                } else if (seagoatEl) {
                    seagoatEl.textContent = 'UNKNOWN';
                    seagoatEl.className = 'monitor-value status-warning';
                }
                
                // Fake News Detector
                if (fakenewsEl && data.fake_news_detector) {
                    fakenewsEl.textContent = data.fake_news_detector.status === 'ready' ? 'READY' : 'LOADING';
                    fakenewsEl.className = 'monitor-value ' + (data.fake_news_detector.status === 'ready' ? 'status-online' : 'status-warning');
                } else if (fakenewsEl) {
                    fakenewsEl.textContent = 'UNKNOWN';
                    fakenewsEl.className = 'monitor-value status-warning';
                }
            })
            .catch(() => {
                // Set all to UNKNOWN on error
                ['monitor-api-openai', 'monitor-api-google', 'monitor-api-hypertxt', 
                 'monitor-api-vertech', 'monitor-api-seagoat', 'monitor-api-fakenews'].forEach(id => {
                    const el = document.getElementById(id);
                    if (el) {
                        el.textContent = 'UNKNOWN';
                        el.className = 'monitor-value status-warning';
                    }
                });
            });
    }
    
    // Update Performance Metrics
    function updatePerformanceMetrics() {
        // Page Load Time
        const loadTimeEl = document.getElementById('monitor-perf-load');
        if (loadTimeEl && window.performance && window.performance.timing) {
            const loadTime = window.performance.timing.loadEventEnd - window.performance.timing.navigationStart;
            loadTimeEl.textContent = loadTime + 'ms';
            loadTimeEl.className = 'monitor-value ' + (loadTime < 2000 ? 'status-online' : loadTime < 5000 ? 'status-warning' : 'status-offline');
        }
        
        // FPS (Frame Rate)
        let lastTime = performance.now();
        let frameCount = 0;
        let fps = 0;
        function measureFPS() {
            frameCount++;
            const currentTime = performance.now();
            if (currentTime >= lastTime + 1000) {
                fps = Math.round((frameCount * 1000) / (currentTime - lastTime));
                frameCount = 0;
                lastTime = currentTime;
                
                const fpsEl = document.getElementById('monitor-perf-fps');
                if (fpsEl) {
                    fpsEl.textContent = fps;
                    fpsEl.className = 'monitor-value ' + (fps >= 55 ? 'status-online' : fps >= 30 ? 'status-warning' : 'status-offline');
                }
            }
            requestAnimationFrame(measureFPS);
        }
        if (document.getElementById('monitor-perf-fps')) {
            requestAnimationFrame(measureFPS);
        }
        
        // Memory Usage (if available)
        const memoryEl = document.getElementById('monitor-perf-memory');
        if (memoryEl && performance.memory) {
            const usedMB = (performance.memory.usedJSHeapSize / 1048576).toFixed(1);
            memoryEl.textContent = usedMB + 'MB';
            memoryEl.className = 'monitor-value ' + (usedMB < 50 ? 'status-online' : usedMB < 100 ? 'status-warning' : 'status-offline');
        } else if (memoryEl) {
            memoryEl.textContent = 'N/A';
        }
        
        // Network Latency
        const latencyEl = document.getElementById('monitor-perf-latency');
        if (latencyEl) {
            const startTime = performance.now();
            fetch(apiUrl('api/health'), { method: 'GET', cache: 'no-cache' })
                .then(() => {
                    const latency = Math.round(performance.now() - startTime);
                    latencyEl.textContent = latency + 'ms';
                    latencyEl.className = 'monitor-value ' + (latency < 100 ? 'status-online' : latency < 300 ? 'status-warning' : 'status-offline');
                })
                .catch(() => {
                    latencyEl.textContent = 'N/A';
                    latencyEl.className = 'monitor-value status-offline';
                });
        }
        
        // Cache Hit Rate (simulated)
        const cacheEl = document.getElementById('monitor-perf-cache');
        if (cacheEl) {
            const cacheRate = Math.min(100, Math.max(0, 75 + Math.random() * 20)); // 75-95%
            cacheEl.textContent = cacheRate.toFixed(1) + '%';
            cacheEl.className = 'monitor-value ' + (cacheRate > 80 ? 'status-online' : cacheRate > 60 ? 'status-warning' : 'status-offline');
        }
    }
    
    // Update Generation Analytics
    function updateGenerationAnalytics() {
        // Average Generation Time (from localStorage or API)
        const avgTimeEl = document.getElementById('monitor-analytics-avgtime');
        if (avgTimeEl) {
            const stats = JSON.parse(localStorage.getItem('generationStats') || '{"avgTime":0,"successCount":0,"totalCount":0,"totalBytes":0}');
            avgTimeEl.textContent = stats.avgTime > 0 ? stats.avgTime.toFixed(1) + 's' : '--s';
        }
        
        // Success Rate
        const successEl = document.getElementById('monitor-analytics-success');
        if (successEl) {
            const stats = JSON.parse(localStorage.getItem('generationStats') || '{"avgTime":0,"successCount":0,"totalCount":0,"totalBytes":0}');
            const successRate = stats.totalCount > 0 ? (stats.successCount / stats.totalCount * 100) : 0;
            successEl.textContent = successRate.toFixed(1) + '%';
            successEl.className = 'monitor-value ' + (successRate > 90 ? 'status-online' : successRate > 70 ? 'status-warning' : 'status-offline');
        }
        
        // Clips Per Hour (simulated)
        const clipsEl = document.getElementById('monitor-analytics-clips');
        if (clipsEl) {
            const clipsPerHour = Math.floor(Math.random() * 20 + 10); // 10-30 clips/hour
            clipsEl.textContent = clipsPerHour;
        }
        
        // Total Bytes Generated
        const bytesEl = document.getElementById('monitor-analytics-bytes');
        if (bytesEl) {
            const stats = JSON.parse(localStorage.getItem('generationStats') || '{"avgTime":0,"successCount":0,"totalCount":0,"totalBytes":0}');
            const totalGB = (stats.totalBytes / 1073741824).toFixed(2); // Convert to GB
            bytesEl.textContent = totalGB + 'GB';
        }
        
        // Most Used Theme
        const themeEl = document.getElementById('monitor-analytics-theme');
        if (themeEl) {
            const themeUsage = JSON.parse(localStorage.getItem('themeUsage') || '{}');
            const mostUsed = Object.keys(themeUsage).reduce((a, b) => themeUsage[a] > themeUsage[b] ? a : b, 'matrix');
            themeEl.textContent = mostUsed.toUpperCase();
        }
    }
    
    // Update server time
    function updateServerTime() {
        const serverTimeEl = document.getElementById('monitor-server-time');
        if (serverTimeEl) {
            const now = new Date();
            serverTimeEl.textContent = now.toISOString().replace('T', ' ').substring(0, 19);
        }
    }
    
    // Update editable MP4 display
    function updateEditableMP4Display() {
        const mp4FileEl = document.getElementById('monitor-editable-mp4');
        const mp4StatusEl = document.getElementById('monitor-mp4-status');
        const mp4DurationEl = document.getElementById('monitor-mp4-duration');
        const mp4SizeEl = document.getElementById('monitor-mp4-size');
        const editModeEl = document.getElementById('monitor-edit-mode');
        
        // These will be updated when MP4 is created
        if (mp4FileEl && !mp4FileEl.textContent || mp4FileEl.textContent === '--') {
            mp4FileEl.textContent = '--';
        }
        if (mp4StatusEl) mp4StatusEl.textContent = 'READY';
        if (mp4DurationEl) mp4DurationEl.textContent = '0.00s';
        if (mp4SizeEl) mp4SizeEl.textContent = '0 MB';
        if (editModeEl) editModeEl.textContent = 'ENABLED';
    }
    
    // Update Incremental MP4 Status (ENHANCED with editable MP4 display)
    window.updateIncrementalMP4Status = function(editableMp4Path, clipCount) {
        const monitorOutputFile = document.getElementById('monitor-output-file');
        const monitorEncodingStatus = document.getElementById('monitor-encoding-status');
        const monitorTextEl = document.getElementById('monitor-text');
        
        if (monitorOutputFile) {
            const fileName = editableMp4Path ? editableMp4Path.split('/').pop().split('\\').pop() : '--';
            monitorOutputFile.textContent = fileName || '--';
        }
        
        if (monitorEncodingStatus) {
            monitorEncodingStatus.textContent = `INCREMENTAL (${clipCount} clips)`;
        }
        
        // Update editable MP4 display section
        const mp4FileEl = document.getElementById('monitor-editable-mp4');
        const mp4StatusEl = document.getElementById('monitor-mp4-status');
        const mp4DurationEl = document.getElementById('monitor-mp4-duration');
        const mp4SizeEl = document.getElementById('monitor-mp4-size');
        const editModeEl = document.getElementById('monitor-edit-mode');
        
        if (editableMp4Path) {
            const fileName = editableMp4Path.split('/').pop().split('\\').pop();
            if (mp4FileEl) mp4FileEl.textContent = fileName;
            if (mp4StatusEl) mp4StatusEl.textContent = 'READY';
            if (editModeEl) editModeEl.textContent = 'ENABLED';
            
            // Estimate MP4 info based on clip count
            if (mp4DurationEl) {
                const estimatedDuration = (clipCount * 5).toFixed(2); // Assume 5s per clip
                mp4DurationEl.textContent = estimatedDuration + 's';
            }
            if (mp4SizeEl) {
                const estimatedSize = (clipCount * 2.5).toFixed(1); // Assume 2.5MB per clip
                mp4SizeEl.textContent = estimatedSize + ' MB';
            }
        }
        
        if (monitorTextEl && editableMp4Path) {
            const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
            const fileName = editableMp4Path.split('/').pop().split('\\').pop();
            // Use limited lines function
            if (typeof addMonitorTextLine === 'function') {
                addMonitorTextLine(`[${timestamp}] > MP4: ${fileName.substring(0, 30)} | ${clipCount} clips | EDITABLE`);
            } else {
                monitorTextEl.textContent += `[${timestamp}] > MP4: ${fileName} | ${clipCount} clips | EDITABLE\n`;
            monitorTextEl.scrollTop = monitorTextEl.scrollHeight;
            }
        }
    };
    
    // Helper function for backward compatibility
    function updateMonitorRequirements(prompt, title, themeName, emotion) {
        window.updateMonitorRequirements(prompt, title, themeName, emotion);
    }
    
    // Matrix Canvas Border for Monitor (code rain in border)
    const matrixCanvasBorder = document.getElementById('matrix-canvas-border');
    let matrixBorderCtx = null;
    let matrixBorderAnimationFrame = null;
    let matrixBorderDrops = [];
    
    function initMatrixCanvasBorder() {
        if (!matrixCanvasBorder) return;
        
        const rect = matrixMonitor?.getBoundingClientRect();
        if (rect) {
            matrixCanvasBorder.width = rect.width + 20;
            matrixCanvasBorder.height = rect.height + 20;
            matrixCanvasBorder.style.width = (rect.width + 20) + 'px';
            matrixCanvasBorder.style.height = (rect.height + 20) + 'px';
        } else {
            matrixCanvasBorder.width = 800;
            matrixCanvasBorder.height = 600;
        }
        
        matrixBorderCtx = matrixCanvasBorder.getContext('2d');
        const fontSize = 12;
        const columns = Math.ceil(matrixCanvasBorder.width / fontSize);
        matrixBorderDrops = [];
        for (let i = 0; i < columns; i++) {
            matrixBorderDrops[i] = Math.random() * -100;
        }
    }
    
    function startMatrixRainBorder() {
        if (!matrixCanvasBorder || !matrixBorderCtx) return;
        
        function animate() {
            matrixBorderCtx.fillStyle = 'rgba(0, 0, 0, 0.05)';
            matrixBorderCtx.fillRect(0, 0, matrixCanvasBorder.width, matrixCanvasBorder.height);
            
            matrixBorderCtx.fillStyle = 'rgba(0, 255, 0, 0.3)';
            matrixBorderCtx.font = '12px monospace';
            
            const chars = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!@#$%^&*()[]{}|;:<>?/';
            const fontSize = 12;
            const columns = Math.ceil(matrixCanvasBorder.width / fontSize);
            
            for (let i = 0; i < Math.min(matrixBorderDrops.length, columns); i++) {
                const text = chars[Math.floor(Math.random() * chars.length)];
                const x = i * fontSize;
                const y = matrixBorderDrops[i] * fontSize;
                matrixBorderCtx.fillText(text, x, y);
                
                if (y > matrixCanvasBorder.height && Math.random() > 0.975) {
                    matrixBorderDrops[i] = 0;
                } else {
                    matrixBorderDrops[i]++;
                }
            }
            
            matrixBorderAnimationFrame = requestAnimationFrame(animate);
        }
        
        animate();
    }
    
    function stopMatrixRainBorder() {
        if (matrixBorderAnimationFrame) {
            cancelAnimationFrame(matrixBorderAnimationFrame);
            matrixBorderAnimationFrame = null;
        }
        if (matrixBorderCtx && matrixCanvasBorder) {
            matrixBorderCtx.clearRect(0, 0, matrixCanvasBorder.width, matrixCanvasBorder.height);
        }
    }
    // ========== END MATRIX MONITOR FUNCTIONS ==========
    
    // Enhanced error handling
    const originalShowError = showError;
    showError = function(message) {
        originalShowError(message);
        const errorTextEl = errorMessage ? errorMessage.querySelector('.error-text') : null;
        if (errorTextEl) {
            errorTextEl.textContent = message;
        }
        
        if (errorClose) {
            errorClose.addEventListener('click', hideError);
        }
    };
    
    // Show toast notification
    function showToast(message, type = 'success') {
        if (!successToast) return;
        
        const toastMessage = successToast.querySelector('.toast-message');
        if (toastMessage) {
            toastMessage.textContent = message;
        }
        
        successToast.className = `toast toast-${type}`;
        successToast.style.display = 'flex';
        
        setTimeout(() => {
            successToast.style.display = 'none';
        }, 3000);
    }
    
    // Enhanced success message with confetti
    function showSuccess(message) {
        if (successMessage) {
            const successTextEl = successMessage.querySelector('.success-text');
            if (successTextEl) {
                successTextEl.textContent = message;
            }
            successMessage.style.display = 'flex';
            
            // Trigger confetti
            createConfetti();
        }
    }
    
    function createConfetti() {
        const confettiContainer = document.getElementById('confetti-container');
        if (!confettiContainer) return;
        
        confettiContainer.innerHTML = '';
        
        for (let i = 0; i < 50; i++) {
            const confetti = document.createElement('div');
            confetti.className = 'confetti';
            confetti.style.left = Math.random() * 100 + '%';
            confetti.style.animationDelay = Math.random() * 2 + 's';
            confetti.style.background = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe'][Math.floor(Math.random() * 5)];
            confettiContainer.appendChild(confetti);
        }
        
        setTimeout(() => {
            confettiContainer.innerHTML = '';
        }, 3000);
    }
    
    // Update embed code generation
    if (embedBtn && embedCode) {
        const originalEmbedClick = embedBtn.onclick;
        embedBtn.addEventListener('click', function() {
            if (currentDocumentaryId) {
                const embedPath = apiUrl(`embed/documentary/${currentDocumentaryId}`);
                const autoplay = embedAutoplay && embedAutoplay.checked ? 'true' : 'false';
                const controls = embedControls && embedControls.checked ? 'true' : 'false';
                const loop = embedLoop && embedLoop.checked ? 'true' : 'false';
                
                const embedHtml = `<iframe src="${window.location.origin}${embedPath}?autoplay=${autoplay}&controls=${controls}&loop=${loop}" width="640" height="360" frameborder="0" allowfullscreen></iframe>`;
                embedCode.value = embedHtml;
                embedCodeContainer.style.display = 'block';
            }
        });
    }
    
    // Update file upload handler
    if (fileUpload) {
        fileUpload.addEventListener('change', function() {
            handleFileUpload(Array.from(this.files));
        });
    }
    
    // Update video load to show success
    const originalLoadVideo = loadVideo;
    loadVideo = async function(docId) {
        await originalLoadVideo(docId);
        showSuccess('Documentary generated successfully!');
        saveDraft(); // Clear draft after successful generation
        localStorage.removeItem('documentaryDraft');
    };
    
    // ========== MATRIX RAIN BACKGROUND - FULL PAGE ==========
    // Initialize Matrix rain background (full page falling rain effect)
    let matrixRainCanvas = null;
    let matrixRainCtx = null;
    let matrixRainDrops = [];
    let matrixRainAnimationFrame = null;
    
    function initMatrixRainBackground() {
        matrixRainCanvas = document.getElementById('matrix-rain-background');
        if (!matrixRainCanvas) {
            console.warn('[Matrix Rain] Canvas element not found');
            return;
        }
        
        // Set canvas size to full window
        function resizeCanvas() {
            matrixRainCanvas.width = window.innerWidth;
            matrixRainCanvas.height = window.innerHeight;
        }
        
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);
        
        matrixRainCtx = matrixRainCanvas.getContext('2d');
        
        // Initialize drops for each column
        const fontSize = 14;
        const columns = Math.ceil(matrixRainCanvas.width / fontSize);
        matrixRainDrops = [];
        for (let i = 0; i < columns; i++) {
            matrixRainDrops[i] = Math.random() * -100;
        }
        
        console.log('[Matrix Rain] Background initialized:', matrixRainCanvas.width, 'x', matrixRainCanvas.height, 'columns:', columns);
        startMatrixRainBackground();
    }
    
    function startMatrixRainBackground() {
        if (!matrixRainCanvas || !matrixRainCtx) {
            console.warn('[Matrix Rain] Canvas or context not ready');
            return;
        }
        
        console.log('[Matrix Rain] Starting rain animation');
        
        function animate() {
            // Semi-transparent black fade for trailing effect
            matrixRainCtx.fillStyle = 'rgba(0, 0, 0, 0.05)';
            matrixRainCtx.fillRect(0, 0, matrixRainCanvas.width, matrixRainCanvas.height);
            
            // Use current theme color (default to Matrix green)
            const currentThemeObj = themes[currentTheme] || themes.matrix;
            const themeColor = currentThemeObj ? currentThemeObj.colors.primary : '#00ff00';
            const rgb = hexToRgb(themeColor);
            
            matrixRainCtx.font = 'bold 14px monospace';
            matrixRainCtx.textBaseline = 'top';
            
            // Matrix characters (Japanese katakana + alphanumeric)
            const chars = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!@#$%^&*()[]{}|;:<>?/';
            const fontSize = 14;
            const columns = Math.ceil(matrixRainCanvas.width / fontSize);
            
            // Ensure drops array matches columns
            while (matrixRainDrops.length < columns) {
                matrixRainDrops.push(Math.random() * -100);
            }
            
            for (let i = 0; i < Math.min(matrixRainDrops.length, columns); i++) {
                const text = chars[Math.floor(Math.random() * chars.length)];
                const x = i * fontSize;
                const y = matrixRainDrops[i] * fontSize;
                
                // Fade effect - brighter at top, dimmer at bottom
                const opacity = Math.min(1, Math.max(0.2, (matrixRainCanvas.height - y) / fontSize / 10));
                const intensity = Math.min(255, 50 + (opacity * 205));
                matrixRainCtx.fillStyle = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${opacity})`;
                
                matrixRainCtx.fillText(text, x, y);
                
                // Reset drop when it reaches bottom
                if (y > matrixRainCanvas.height && Math.random() > 0.975) {
                    matrixRainDrops[i] = 0;
                } else {
                    matrixRainDrops[i]++;
                }
            }
            
            matrixRainAnimationFrame = requestAnimationFrame(animate);
        }
        
        animate();
    }
    
    function stopMatrixRainBackground() {
        if (matrixRainAnimationFrame) {
            cancelAnimationFrame(matrixRainAnimationFrame);
            matrixRainAnimationFrame = null;
        }
        if (matrixRainCtx && matrixRainCanvas) {
            matrixRainCtx.clearRect(0, 0, matrixRainCanvas.width, matrixRainCanvas.height);
        }
    }
    // ========== END MATRIX RAIN BACKGROUND ==========
    
    // ========== THEME SYSTEM ==========
    // Theme definitions with colors, backgrounds, effects, and content
    // Futuristic Theme Model Structure (Year 3025) - Matrix as Main Theme
    const themes = {
        matrix: {
            id: 'matrix',
            name: 'Matrix',
            description: 'The digital reality simulation - Main Theme',
            era: '1999-futuristic',
            category: 'sci-fi',
            isMain: true,  // Mark Matrix as main theme
            colors: {
                primary: '#00ff00',
                secondary: '#00cc00',
                accent: '#00ff88',
                background: 'linear-gradient(135deg, #000000 0%, #001100 50%, #000000 100%)',
                text: '#00ff00',
                glow: '#00ff00',
                shadow: '#003300'
            },
            keywords: ['matrix', 'simulation', 'reality', 'digital', 'code', 'hacker', 'neo', 'morpheus', 'trinity', 'agent', 'red pill', 'blue pill', 'awakening'],
            quotes: [
                'There is no spoon.',
                'Welcome to the desert of the real.',
                'You take the blue pill, the story ends.',
                'You take the red pill, you stay in Wonderland.',
                'There is no spoon.',
                'What is real?',
                'Welcome to the real world.'
            ],
            characters: ['neo', 'morpheus', 'trinity', 'agent smith', 'oracle', 'architect', 'seraph', 'the keymaker', 'tank', 'mouse', 'cypher', 'switch', 'apoc', 'ghost', 'niobe', 'link', 'zee', 'persephone'],
            visualElements: ['falling green code', 'digital rain', 'code walls', 'bullet time effect', 'wireframe world', 'hacker terminal', 'red pill', 'blue pill', 'mirror portals', 'glitch effects', 'binary streams', 'matrix grid'],
            sounds: ['digital rain', 'electronic beeps', 'hacker typing', 'bullet time woosh', 'glitch sounds', 'matrix code', 'synthesizer tones', 'data stream'],
            locations: ['the matrix', 'zion', 'machine city', 'construct', 'oracle apartment', 'morpheus ship', 'train station', 'highway', 'chateau'],
            items: ['red pill', 'blue pill', 'cell phone', 'glasses', 'coat', 'pistols', 'kung fu', 'jump program'],
            concepts: ['simulation', 'reality', 'choice', 'awakening', 'prophecy', 'destiny', 'control', 'freedom'],
            effects: {
                particles: ['code rain', 'digital particles', 'glitch particles'],
                animations: ['matrix rain', 'bullet time', 'wireframe transition'],
                filters: ['green tint', 'scan lines', 'data overlay'],
                overlays: ['code overlay', 'binary overlay', 'matrix grid']
            },
            interactive: {
                particles: true,
                hoverEffects: true,
                clickEffects: true,
                gestures: false
            },
            quantum: {
                entanglement: true,
                superposition: false,
                tunneling: true
            },
            ai: {
                voice: 'synthetic',
                personality: 'oracle',
                responses: ['There is no spoon.', 'What is real?', 'Welcome to the real world.']
            },
            holographic: {
                enabled: true,
                depth: 10,
                layers: 3,
                projections: ['code walls', 'data streams', 'wireframe objects']
            },
            neural: {
                enabled: false,
                thoughtControl: false,
                brainSync: false
            },
            temporal: {
                timeDilation: true,
                timeTravel: false,
                parallel: true
            }
        },
        stargate: {
            id: 'stargate',
            name: 'Stargate Atlantis',
            description: 'Ancient technology and intergalactic travel',
            era: 'ancient-futuristic',
            category: 'sci-fi',
            colors: {
                primary: '#00aaff',
                secondary: '#0066cc',
                accent: '#00ddff',
                background: 'linear-gradient(135deg, #001122 0%, #003366 50%, #001122 100%)',
                text: '#00aaff',
                glow: '#00aaff',
                shadow: '#001133'
            },
            keywords: ['stargate', 'atlantis', 'ancient', 'wraith', 'puddle jumper', 'stargate', 'dial home device', 'wormhole', 'ascension', 'pegasus', 'rodney', 'sheppard'],
            quotes: [
                'Indeed.',
                'Off-world activation!',
                'Chevron seven locked!',
                'Unscheduled off-world activation!',
                'The Ancients were here.',
                'Power levels critical!',
                'Incoming wormhole!'
            ],
            characters: ['john sheppard', 'rodney mckay', 'ronon dex', 'teyla emmagan', 'carson beckett', 'jennifer keller', 'richard woolsey', 'camile wray', 'elizabeth weir', 'david parrish', 'chuck', 'lantean', 'wraith', 'todd', 'michael', 'kolya'],
            visualElements: ['stargate activation', 'wormhole kawoosh', 'puddle jumper', 'ancient architecture', 'dial home device', 'energy shield', 'stargate chevrons', 'atlantis city', 'pegasus galaxy', 'ancient symbols', 'wraith ships', 'dart fighter'],
            sounds: ['stargate dialing', 'wormhole whoosh', 'chevron lock', 'energy shield', 'puddle jumper engines', 'ancient activation', 'wraith hive', 'transport beam'],
            locations: ['atlantis', 'lantea', 'pegasus galaxy', 'earth', 'athos', 'sateda', 'asuras', 'athosian village'],
            items: ['puddle jumper', 'zat gun', 'wraith stunner', 'ancient database', 'asgard beam'],
            concepts: ['ascension', 'ancient technology', 'intergalactic travel', 'wormholes', 'destiny'],
            effects: {
                particles: ['wormhole particles', 'energy particles', 'stargate symbols'],
                animations: ['stargate dialing', 'wormhole activation', 'energy waves'],
                filters: ['blue energy glow', 'ancient symbols overlay'],
                overlays: ['stargate chevrons', 'energy field', 'ancient text']
            },
            quantum: { entanglement: true, superposition: false, tunneling: true },
            ai: { voice: 'ancient', personality: 'wise', responses: ['Indeed.', 'The Ancients were here.'] },
            holographic: { enabled: true, depth: 8, layers: 2, projections: ['stargate', 'ancient database'] },
            neural: { enabled: false, thoughtControl: false, brainSync: false },
            temporal: { timeDilation: false, timeTravel: true, parallel: false }
        },
        mtg: {
            name: 'Magic the Gathering',
            colors: {
                primary: '#ff6b6b',
                secondary: '#ffd93d',
                background: 'linear-gradient(135deg, #1a0033 0%, #4a148c 50%, #1a0033 100%)',
                text: '#ffd93d'
            },
            keywords: ['planeswalker', 'mana', 'summon', 'creature', 'instant', 'sorcery', 'enchantment', 'artifact', 'planeswalk', 'tap', 'untap', 'attack', 'block', 'battlefield'],
            quotes: [
                'I summon a creature!',
                'Pay the mana cost.',
                'Tap three lands.',
                'Cast a spell!',
                'Draw a card!',
                'The battlefield awaits.',
                'Planeswalk activated!'
            ],
            characters: ['jace beleren', 'chandra nalaar', 'gideon jura', 'liliana vess', 'garruk wildspeaker', 'ajani goldmane', 'elspeth tirel', 'sorin markov', 'nissa revane', 'karn', 'bolas', 'ugin', 'teferi', 'kaya', 'tyvar', 'niko', 'lukka', 'calix'],
            visualElements: ['mana symbols', 'card artwork', 'planeswalker sparks', 'battlefield', 'spell casting', 'creature summoning', 'mana crystals', 'card draw', 'tapping animation', 'combat phase', 'library', 'graveyard', 'exile zone'],
            sounds: ['card draw', 'mana tapping', 'spell casting', 'creature summoning', 'combat phase', 'planeswalk', 'artifact activation', 'enchantment trigger']
        },
        warhammer40k: {
            name: 'Warhammer 40K',
            colors: {
                primary: '#ff3333',
                secondary: '#cc0000',
                background: 'linear-gradient(135deg, #1a0000 0%, #330000 50%, #1a0000 100%)',
                text: '#ff3333'
            },
            keywords: ['imperium', 'space marine', 'chaos', 'ork', 'eldar', 'tyranid', 'necron', 'tau', 'inquisitor', 'emperor', 'heretic', 'xenos', 'warp', 'bolter', 'chainsword'],
            quotes: [
                'For the Emperor!',
                'Heretic!',
                'In the grim darkness of the far future...',
                'There is only war.',
                'Exterminatus!',
                'Purge the xenos!',
                'The Emperor protects!'
            ],
            characters: ['space marine', 'primarch', 'commissar', 'inquisitor', 'chaos marine', 'ork warboss', 'eldar farseer', 'tyranid hive tyrant', 'necron overlord', 'tau ethereal', 'grey knight', 'sisters of battle', 'mechanicus adept', 'dark eldar archon', 'death korps', 'salamander', 'blood angel', 'ultramarine'],
            visualElements: ['imperial eagle', 'gothic architecture', 'space marine armor', 'bolter', 'chainsword', 'power armor', 'warp energy', 'chaos symbols', 'ork glyphs', 'eldar runes', 'tyranid biomorph', 'necron technology', 'tau battlesuit', 'exterminatus', 'warhammer', 'double-headed eagle', 'aquila'],
            sounds: ['bolter fire', 'chainsword revving', 'warp crackling', 'ork waaagh', 'eldar shuriken', 'tyranid screech', 'necron gauss', 'tau plasma', 'imperial march', 'chaos chanting', 'exterminatus warning']
        },
        halo: {
            name: 'Halo 4',
            colors: {
                primary: '#00ff88',
                secondary: '#00cc66',
                background: 'linear-gradient(135deg, #000a1a 0%, #001a33 50%, #000a1a 100%)',
                text: '#00ff88'
            },
            keywords: ['master chief', 'cortana', 'covenant', 'flood', 'forerunner', 'spartan', 'mjolnir', 'halo', 'ring', 'reclaimer', 'promethean', 'didact', 'infinity'],
            quotes: [
                'Wake up, Chief.',
                'I need a weapon.',
                'We\'re going to finish this fight.',
                'I thought I\'d try shooting my way out.',
                'This is Spartan-117.',
                'Cortana?',
                'The Reclaimer.'
            ],
            characters: ['master chief', 'cortana', 'sarah palmer', 'thomas lasky', 'didact', 'librarian', 'arbiter', 'grave mind', 'sergeant johnson', 'commander keyes', 'noble team', 'buck', 'carter', 'kat', 'jorge', 'jun', 'emile', 'noble six'],
            visualElements: ['halo ring', 'forerunner architecture', 'spartan armor', 'cortana interface', 'energy shield', 'promethean technology', 'covenant ships', 'infinity cruiser', 'requiem', 'didact cryptum', 'librarian terminal', 'hardlight constructs', 'warthog', 'scorpion tank', 'pelican', 'phantom'],
            sounds: ['halo theme', 'cortana voice', 'energy shield', 'plasma rifle', 'assault rifle', 'spartan laser', 'covenant chanting', 'forerunner activation', 'promethean teleport', 'gravity lift', 'warthog engine', 'pelican engines']
        },
        dnd: {
            name: 'Dungeon & Dragons',
            colors: {
                primary: '#d4af37',
                secondary: '#b8860b',
                background: 'linear-gradient(135deg, #1a0f00 0%, #4a2c00 50%, #1a0f00 100%)',
                text: '#d4af37'
            },
            keywords: ['dungeon', 'dragon', 'dnd', 'd&d', 'adventure', 'party', 'dungeon master', 'dice', 'roll', 'initiative', 'spell', 'magic', 'character', 'level', 'xp', 'hp', 'd20'],
            quotes: [
                'Roll for initiative!',
                'I cast a spell!',
                'Roll a D20!',
                'Natural 20!',
                'How do you want to do this?',
                'You encounter a dragon!',
                'The adventure begins!'
            ],
            characters: ['wizard', 'rogue', 'paladin', 'barbarian', 'cleric', 'ranger', 'bard', 'druid'],
            visualElements: ['dice rolling', 'dungeon corridors', 'treasure chests', 'dragon scales', 'magic runes', 'spell circles'],
            sounds: ['dice rolling', 'sword clashing', 'spell casting', 'dragon roar', 'treasure collection']
        },
        disney: {
            name: 'Disney',
            colors: {
                primary: '#ffd700',
                secondary: '#ff69b4',
                background: 'linear-gradient(135deg, #1a0033 0%, #4a0080 30%, #ff69b4 50%, #ffd700 70%, #1a0033 100%)',
                text: '#ffd700'
            },
            keywords: ['disney', 'magic', 'dreams', 'wish', 'adventure', 'princess', 'prince', 'castle', 'kingdom', 'fairy tale', 'enchantment', 'sparkle', 'wonder', 'imagination', 'happily ever after'],
            quotes: [
                'A dream is a wish your heart makes.',
                'When you wish upon a star...',
                'Happily ever after.',
                'Bibbidi-bobbidi-boo!',
                'Let it go!',
                'Remember, you are braver than you believe.',
                'The magic begins when you believe.',
                'All our dreams can come true!',
                'If you can dream it, you can do it!',
                'Adventure is out there!'
            ],
            characters: ['mickey mouse', 'minnie mouse', 'donald duck', 'goofy', 'pluto', 'snow white', 'cinderella', 'ariel', 'belle', 'aurora', 'jasmine', 'pocahontas', 'mulan', 'tiana', 'rapunzel', 'elsa', 'anna', 'moana', 'simba', 'buzz lightyear', 'woody'],
            visualElements: ['sparkling stars', 'magical castle', 'floating sparkles', 'princess dress', 'crown jewels', 'fairy wand', 'magic mirror', 'glass slipper', 'rose petals', 'snowflakes', 'aurora borealis', 'tropical islands', 'enchanted forest'],
            sounds: ['magical chimes', 'whistle melody', 'castle bells', 'ocean waves', 'jungle sounds', 'magical transformation'],
            iconicElements: ['mickey ears', 'disney castle', 'wishing star', 'magic wand', 'glass slipper', 'rose', 'crown', 'sparkles', 'butterflies', 'doves'],
            locations: ['disneyland', 'disney world', 'magic kingdom', 'enchanted castle', 'fantasyland', 'adventureland'],
            items: ['glass slipper', 'magic wand', 'crown', 'rose', 'wishing star', 'treasure chest'],
            concepts: ['magic', 'dreams', 'wishes', 'happily ever after', 'believe', 'adventure'],
            effects: {
                particles: ['sparkles', 'stars', 'magic dust', 'princess sparkles'],
                animations: ['sparkle burst', 'magical transformation', 'castle glow'],
                filters: ['magical glow', 'rainbow overlay', 'dreamy blur'],
                overlays: ['sparkles overlay', 'princess overlay', 'magical symbols']
            },
            quantum: { entanglement: false, superposition: false, tunneling: true },
            ai: { voice: 'friendly', personality: 'magical', responses: ['A dream is a wish your heart makes.'] },
            holographic: { enabled: true, depth: 5, layers: 2, projections: ['castle', 'sparkles'] },
            neural: { enabled: false, thoughtControl: false, brainSync: false },
            temporal: { timeDilation: false, timeTravel: false, parallel: false }
        }
    };
    
    // Register all themes with Theme Model System
    if (window.ThemeModel) {
        Object.keys(themes).forEach(themeId => {
            window.ThemeModel.register(themes[themeId]);
        });
        // Set Matrix as main theme
        window.ThemeModel.setMain('matrix');
    }
    
    // Current active theme
    let currentTheme = 'matrix';
    
    // Initialize theme system (with Futuristic Theme Model)
    function initThemeSystem() {
        // Initialize Theme Model System (3025 technology)
        if (window.ThemeModel) {
            window.ThemeModel.init();
        }
        
        // Load saved theme from localStorage (default to Matrix main theme)
        const savedTheme = localStorage.getItem('documentaryTheme') || 'matrix';
        setTheme(savedTheme);
        
        // Add theme selector to settings panel if it exists
        const settingsContent = document.querySelector('.settings-content');
        if (settingsContent) {
            const themeSelector = document.createElement('div');
            themeSelector.className = 'setting-group';
            themeSelector.innerHTML = `
                <label for="theme-selector">
                    <i class="fas fa-palette"></i> Visual Theme
                    <span class="tooltip-icon" data-tooltip="Choose a theme for the generator interface">ℹ️</span>
                </label>
                <select id="theme-selector" class="setting-input">
                    ${Object.keys(themes).map(key => 
                        `<option value="${key}" ${key === savedTheme ? 'selected' : ''}>${themes[key].name}</option>`
                    ).join('')}
                </select>
            `;
            settingsContent.appendChild(themeSelector);
            
            // Theme selector change handler
            const themeSelect = document.getElementById('theme-selector');
            if (themeSelect) {
                themeSelect.addEventListener('change', function() {
                    setTheme(this.value);
                    localStorage.setItem('documentaryTheme', this.value);
                });
            }
        }
        
        // Add theme toggle button functionality (quick theme switcher)
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', function() {
                const themeNames = Object.keys(themes);
                const currentIndex = themeNames.indexOf(currentTheme);
                const nextIndex = (currentIndex + 1) % themeNames.length;
                const nextTheme = themeNames[nextIndex];
                setTheme(nextTheme);
                localStorage.setItem('documentaryTheme', nextTheme);
                
                // Update theme selector if it exists
                const themeSelect = document.getElementById('theme-selector');
                if (themeSelect) {
                    themeSelect.value = nextTheme;
                }
                
                // Show notification
                console.log('[Theme] Switched to:', themes[nextTheme].name);
            });
        }
    }
    
    // Theme background video paths (10-second clips)
    const themeVideos = {
        matrix: '/static/video/themes/matrix_background.mp4',
        stargate: '/static/video/themes/stargate_background.mp4',
        mtg: '/static/video/themes/mtg_background.mp4',
        warhammer40k: '/static/video/themes/warhammer40k_background.mp4',
        halo: '/static/video/themes/halo_background.mp4',
        dnd: '/static/video/themes/dnd_background.mp4',
        disney: '/static/video/themes/disney_background.mp4'
    };
    
    // Theme background images (fallback) - OPTIMIZED WITH WEBP SUPPORT
    // Performance: WebP format with fallback to PNG/JPG for better compression
    const themeBackgrounds = {
        matrix: 'linear-gradient(135deg, #000000 0%, #001100 30%, #003300 50%, #001100 70%, #000000 100%), radial-gradient(ellipse at 50% 50%, rgba(0, 255, 0, 0.1) 0%, transparent 70%)',
        stargate: 'linear-gradient(135deg, #000511 0%, #001122 30%, #002244 50%, #001122 70%, #000511 100%), radial-gradient(ellipse at 50% 50%, rgba(0, 170, 255, 0.15) 0%, transparent 70%), url(/static/img/themes/stargate_bg.webp), url(/static/img/themes/stargate_bg.png), url(/static/img/themes/stargate_bg.jpg)',
        mtg: 'linear-gradient(135deg, #1a0033 0%, #2d0055 30%, #4a148c 50%, #2d0055 70%, #1a0033 100%), radial-gradient(ellipse at 50% 50%, rgba(255, 107, 107, 0.1) 0%, rgba(255, 217, 61, 0.1) 50%, transparent 70%), url(/static/img/themes/mtg_bg.webp), url(/static/img/themes/mtg_bg.png), url(/static/img/themes/mtg_bg.jpg)',
        warhammer40k: 'linear-gradient(135deg, #1a0000 0%, #330000 30%, #550000 50%, #330000 70%, #1a0000 100%), radial-gradient(ellipse at 50% 50%, rgba(255, 51, 51, 0.15) 0%, transparent 70%), url(/static/img/themes/warhammer40k_bg.webp), url(/static/img/themes/warhammer40k_bg.jpg)',
        halo: 'linear-gradient(135deg, #000a1a 0%, #001a33 30%, #003366 50%, #001a33 70%, #000a1a 100%), radial-gradient(ellipse at 50% 50%, rgba(0, 255, 136, 0.1) 0%, transparent 70%), url(/static/img/themes/halo_bg.webp), url(/static/img/themes/halo_bg.jpg)',
        dnd: 'linear-gradient(135deg, #1a0f00 0%, #2d1a00 30%, #4a2c00 50%, #2d1a00 70%, #1a0f00 100%), radial-gradient(ellipse at 50% 50%, rgba(212, 175, 55, 0.1) 0%, rgba(184, 134, 11, 0.1) 50%, transparent 70%), url(/static/img/themes/dnd_bg.webp), url(/static/img/themes/dnd_bg.jpg)',
        disney: 'linear-gradient(135deg, #1a0033 0%, #4a0080 30%, #ff69b4 50%, #ffd700 70%, #1a0033 100%), radial-gradient(ellipse at 50% 50%, rgba(255, 215, 0, 0.2) 0%, rgba(255, 105, 180, 0.15) 50%, transparent 70%), url(/static/img/themes/disney_bg.webp), url(/static/img/themes/disney_bg.jpg)'
    };
    
    // Set theme function with interactive elements
    function setTheme(themeName) {
        if (!themes[themeName]) {
            console.warn('[Theme] Unknown theme:', themeName);
            return;
        }
        
        currentTheme = themeName;
        const theme = themes[themeName];
        
        // Apply theme colors to CSS variables
        const root = document.documentElement;
        root.style.setProperty('--color-matrix-green', theme.colors.primary);
        root.style.setProperty('--color-matrix-green-dim', theme.colors.secondary);
        root.style.setProperty('--theme-background', theme.colors.background);
        root.style.setProperty('--theme-text', theme.colors.text);
        
        // Apply background
        document.body.style.background = theme.colors.background;
        document.body.style.color = theme.colors.text;
        
        // Load theme background image FIRST (always visible) - FORCE
        loadThemeBackgroundImage(themeName);
        
        // Force show background image immediately
        const bgImage = document.getElementById('theme-background-image');
        if (bgImage) {
            bgImage.style.setProperty('display', 'block', 'important');
            bgImage.style.setProperty('visibility', 'visible', 'important');
            bgImage.style.setProperty('opacity', '0.15', 'important');
        }
        
        // Load theme background video (will overlay image if available)
        loadThemeBackgroundVideo(themeName);
        
        // Force activate all elements after theme change
        if (typeof forceActivateAllElements === 'function') {
            setTimeout(forceActivateAllElements, 100);
        }
        
        // Create interactive particles
        createThemeParticles(theme);
        
        // Update IR/UV decorations
        updateIRUVDecorations(theme);
        
        // Initialize or update Matrix rain background for theme
        if (themeName === 'matrix') {
            // Start Matrix rain background immediately when Matrix theme is set
            if (typeof initMatrixRainBackground === 'function' && !matrixRainAnimationFrame) {
                console.log('[Matrix Rain] Starting rain background for Matrix theme');
                initMatrixRainBackground();
            }
        } else if (matrixRainCtx) {
            // For non-matrix themes, adjust rain color
            const themeColor = hexToRgb(theme.colors.primary);
            // This will be handled in the rain animation
        }
        
        // Update Monitor with theme info
        updateMonitorTheme(themeName, theme);
        
        console.log('[Theme] Theme set to:', theme.name);
    }
    
    // Load theme background video (10-second clips) - ENHANCED WITH FALLBACK
    function loadThemeBackgroundVideo(themeName) {
        const videoContainer = document.getElementById('theme-background-video');
        const videoEl = document.getElementById('theme-video');
        const imageContainer = document.getElementById('theme-background-image');
        
        if (!videoContainer || !videoEl) {
            // If video container doesn't exist, just use image background
            if (imageContainer) {
                const backgroundStyle = themeBackgrounds[themeName];
                if (backgroundStyle) {
                    imageContainer.style.background = backgroundStyle;
                    imageContainer.style.display = 'block';
                }
            }
            return;
        }
        
        const videoPath = themeVideos[themeName];
        if (!videoPath) {
            // If video path doesn't exist, hide video and show image background
            videoContainer.style.display = 'none';
            if (imageContainer) {
                const backgroundStyle = themeBackgrounds[themeName];
                if (backgroundStyle) {
                    imageContainer.style.background = backgroundStyle;
                    imageContainer.style.display = 'block';
                }
            }
            return;
        }
        
        // Always show image background first (as fallback)
        if (imageContainer) {
            const backgroundStyle = themeBackgrounds[themeName];
            if (backgroundStyle) {
                imageContainer.style.background = backgroundStyle;
                imageContainer.style.display = 'block';
            }
        }
        
        // Set video source
        videoEl.src = videoPath;
        videoEl.load();
        
        // Show video container (will overlay image if video loads)
        videoContainer.style.display = 'block';
        
        // Play video on load
        const playVideo = function() {
            videoEl.play().then(() => {
                console.log('[Theme Video] Video playing:', themeName);
                // Video playing - it will overlay the image background
            }).catch(e => {
                console.log('[Theme Video] Autoplay prevented:', e, '- using image background');
                // Fallback to image background only
                videoContainer.style.display = 'none';
            });
        };
        
        videoEl.addEventListener('loadeddata', playVideo, { once: true });
        videoEl.addEventListener('canplay', playVideo, { once: true });
        
        // Handle video error - fallback to image
        videoEl.addEventListener('error', function(e) {
            console.log('[Theme Video] Error loading video:', themeName, '- using image background only');
            videoContainer.style.display = 'none';
            // Image background is already showing
        });
        
        // Loop video seamlessly
        videoEl.addEventListener('ended', function() {
            videoEl.currentTime = 0;
            videoEl.play().catch(e => {
                console.log('[Theme Video] Loop play prevented:', e);
            });
        });
        
        // Try to play immediately if already loaded
        if (videoEl.readyState >= 2) {
            playVideo();
        }
    }
    
    // Load theme background image (fallback) - ENHANCED
    function loadThemeBackgroundImage(themeName) {
        const imageContainer = document.getElementById('theme-background-image');
        if (!imageContainer) {
            console.warn('[Theme Background] Image container not found, creating it...');
            // Create image container if it doesn't exist
            const newContainer = document.createElement('div');
            newContainer.id = 'theme-background-image';
            newContainer.className = 'theme-background-image';
            document.body.insertBefore(newContainer, document.body.firstChild);
            return loadThemeBackgroundImage(themeName); // Retry after creation
        }
        
        const backgroundStyle = themeBackgrounds[themeName];
        if (backgroundStyle) {
            imageContainer.style.background = backgroundStyle;
            imageContainer.style.setProperty('display', 'block', 'important');
            imageContainer.style.setProperty('opacity', '0.15', 'important');
            imageContainer.style.setProperty('visibility', 'visible', 'important');
            imageContainer.style.setProperty('background-size', 'cover', 'important');
            imageContainer.style.setProperty('background-position', 'center', 'important');
            imageContainer.style.setProperty('background-repeat', 'no-repeat', 'important');
            console.log('[Theme Background] Image background loaded for theme:', themeName);
        } else {
            console.warn('[Theme Background] No background style found for theme:', themeName);
        }
    }
    
    // Initialize MasterNoder2 Crypto Commercial
    function initMasterNoder2Commercial() {
        const commercial = document.getElementById('masternoder2-commercial');
        const teleportParticles = document.getElementById('teleport-particles');
        const nodesValue = document.getElementById('mn2-nodes');
        const connectedValue = document.getElementById('mn2-connected');
        
        if (!commercial) return;
        
        // Create teleport particles
        if (teleportParticles) {
            createTeleportParticles(teleportParticles);
        }
        
        // Update stats periodically
        if (nodesValue) {
            setInterval(function() {
                const nodes = Math.floor(Math.random() * 1000) + 5000;
                nodesValue.textContent = nodes.toLocaleString();
            }, 3000);
        }
        
        if (connectedValue) {
            const locations = ['GLOBAL', 'WORLDWIDE', 'UNIVERSAL', 'INTERSTELLAR', 'MULTIVERSE'];
            let locationIndex = 0;
            setInterval(function() {
                connectedValue.textContent = locations[locationIndex % locations.length];
                locationIndex++;
            }, 5000);
        }
        
        // Add click interaction - teleport effect
        commercial.addEventListener('click', function() {
            triggerTeleportEffect();
        });
        
        // Add intelligent connection indicator
        setInterval(function() {
            commercial.style.boxShadow = `5px 0 ${Math.random() * 30 + 20}px rgba(${Math.random() * 255}, ${200 + Math.random() * 55}, 255, 0.8)`;
        }, 1000);
    }
    
    // Create teleport particles
    function createTeleportParticles(container) {
        for (let i = 0; i < 12; i++) {
            const particle = document.createElement('div');
            particle.style.position = 'absolute';
            particle.style.width = '4px';
            particle.style.height = '4px';
            particle.style.background = `rgba(${Math.random() * 100 + 150}, ${200 + Math.random() * 55}, 255, 0.8)`;
            particle.style.borderRadius = '50%';
            particle.style.left = '50%';
            particle.style.top = '50%';
            particle.style.transform = `translate(-50%, -50%) rotate(${i * 30}deg) translateY(-35px)`;
            particle.style.animation = `teleportParticle 2s ease-in-out infinite`;
            particle.style.animationDelay = `${i * 0.15}s`;
            container.appendChild(particle);
        }
    }
    
    // Trigger teleport effect
    function triggerTeleportEffect() {
        const commercial = document.getElementById('masternoder2-commercial');
        if (!commercial) return;
        
        commercial.style.transform = 'translateY(-50%) scale(1.1)';
        commercial.style.filter = 'brightness(1.5)';
        
        setTimeout(function() {
            commercial.style.transform = 'translateY(-50%) scale(1)';
            commercial.style.filter = 'brightness(1)';
        }, 300);
    }
    
    // Create interactive theme particles
    function createThemeParticles(theme) {
        const particlesContainer = document.getElementById('theme-particles');
        if (!particlesContainer) return;
        
        // Clear existing particles
        particlesContainer.innerHTML = '';
        
        // Create 15-20 interactive particles
        const particleCount = 18;
        const themeColor = hexToRgb(theme.colors.primary);
        
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'theme-particle';
            
            // Random size (20-60px)
            const size = Math.random() * 40 + 20;
            particle.style.width = size + 'px';
            particle.style.height = size + 'px';
            
            // Random position
            particle.style.left = Math.random() * 100 + '%';
            particle.style.top = Math.random() * 100 + '%';
            
            // Theme color with opacity
            particle.style.background = `radial-gradient(circle, rgba(${themeColor.r}, ${themeColor.g}, ${themeColor.b}, 0.4) 0%, rgba(${themeColor.r}, ${themeColor.g}, ${themeColor.b}, 0.1) 100%)`;
            particle.style.boxShadow = `0 0 ${size}px rgba(${themeColor.r}, ${themeColor.g}, ${themeColor.b}, 0.5)`;
            
            // Random animation delay
            particle.style.animationDelay = Math.random() * 20 + 's';
            particle.style.animationDuration = (Math.random() * 10 + 15) + 's';
            
            // Add click interaction - show theme quote
            particle.addEventListener('click', function() {
                const quotes = theme.quotes || [];
                if (quotes.length > 0) {
                    const randomQuote = quotes[Math.floor(Math.random() * quotes.length)];
                    showToast(randomQuote, 'success');
                    
                    // Visual feedback
                    particle.style.transform = 'scale(3)';
                    particle.style.opacity = '1';
                    setTimeout(() => {
                        particle.style.transform = '';
                        particle.style.opacity = '';
                    }, 500);
                }
            });
            
            particlesContainer.appendChild(particle);
        }
    }
    
    // Update IR/UV decorations (17% opacity)
    function updateIRUVDecorations(theme) {
        const decorationsContainer = document.getElementById('ir-uv-decorations');
        if (!decorationsContainer) return;
        
        // Clear existing decorations
        decorationsContainer.innerHTML = '';
        
        // Create 8-12 IR decorations (pink/magenta)
        for (let i = 0; i < 10; i++) {
            const irDeco = document.createElement('div');
            irDeco.className = 'ir-decoration';
            irDeco.style.width = (Math.random() * 200 + 100) + 'px';
            irDeco.style.height = irDeco.style.width;
            irDeco.style.left = Math.random() * 100 + '%';
            irDeco.style.top = Math.random() * 100 + '%';
            irDeco.style.opacity = '0.17';
            irDeco.style.animationDelay = Math.random() * 8 + 's';
            irDeco.style.animationDuration = (Math.random() * 4 + 6) + 's';
            decorationsContainer.appendChild(irDeco);
        }
        
        // Create 8-12 UV decorations (cyan/blue)
        for (let i = 0; i < 10; i++) {
            const uvDeco = document.createElement('div');
            uvDeco.className = 'uv-decoration';
            uvDeco.style.width = (Math.random() * 200 + 100) + 'px';
            uvDeco.style.height = uvDeco.style.width;
            uvDeco.style.left = Math.random() * 100 + '%';
            uvDeco.style.top = Math.random() * 100 + '%';
            uvDeco.style.opacity = '0.17';
            uvDeco.style.animationDelay = Math.random() * 8 + 's';
            uvDeco.style.animationDuration = (Math.random() * 4 + 6) + 's';
            decorationsContainer.appendChild(uvDeco);
        }
    }
    
    // Update Monitor with theme information
    function updateMonitorTheme(themeName, theme) {
        const monitorThemeEl = document.getElementById('monitor-theme');
        if (monitorThemeEl) {
            monitorThemeEl.textContent = theme.name.toUpperCase();
        }
    }
    
    // Helper function to convert hex to RGB
    function hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : { r: 0, g: 255, b: 0 };
    }
    
    // Get theme-specific content
    function getThemeContent(type) {
        const theme = themes[currentTheme];
        if (!theme) return [];
        
        switch(type) {
            case 'quotes':
                return theme.quotes || [];
            case 'keywords':
                return theme.keywords || [];
            default:
                return [];
        }
    }
    
    // Make theme functions available globally
    window.themes = themes;
    window.currentTheme = currentTheme;
    window.setTheme = setTheme;
    window.getThemeContent = getThemeContent;
    // ========== END THEME SYSTEM ==========
    
    // ==========================================
    // SIDEBAR FUNCTIONALITY
    // ==========================================
    function initializeSidebars() {
        const leftSidebar = document.getElementById('left-sidebar');
        const rightSidebar = document.getElementById('right-sidebar');
        const leftToggle = document.getElementById('left-sidebar-toggle');
        const rightToggle = document.getElementById('right-sidebar-toggle');
        
        // Left sidebar toggle
        if (leftToggle && leftSidebar) {
            leftToggle.addEventListener('click', function() {
                leftSidebar.classList.toggle('collapsed');
                const icon = leftToggle.querySelector('i');
                if (icon) {
                    icon.classList.toggle('fa-chevron-left');
                    icon.classList.toggle('fa-chevron-right');
                }
            });
        }
        
        // Right sidebar toggle
        if (rightToggle && rightSidebar) {
            rightToggle.addEventListener('click', function() {
                rightSidebar.classList.toggle('collapsed');
                const icon = rightToggle.querySelector('i');
                if (icon) {
                    icon.classList.toggle('fa-chevron-right');
                    icon.classList.toggle('fa-chevron-left');
                }
            });
        }
        
        // Quick action buttons
        const quickGenerate = document.getElementById('quick-generate');
        const quickSave = document.getElementById('quick-save');
        const quickExport = document.getElementById('quick-export');
        
        if (quickGenerate) {
            quickGenerate.addEventListener('click', function() {
                const generateBtn = document.getElementById('generate-btn');
                if (generateBtn) generateBtn.click();
            });
        }
        
        if (quickSave) {
            quickSave.addEventListener('click', function() {
                saveDraft();
            });
        }
        
        if (quickExport) {
            quickExport.addEventListener('click', function() {
                const videoPlayer = document.getElementById('video-player');
                if (videoPlayer && videoPlayer.src) {
                    const a = document.createElement('a');
                    a.href = videoPlayer.src;
                    a.download = 'documentary.mp4';
                    a.click();
                }
            });
        }
        
        // Load recent items
        loadRecentItems();
        
        // Update statistics
        updateSidebarStats();
    }
    
    function loadRecentItems() {
        const recentItems = document.getElementById('recent-items');
        if (!recentItems) return;
        
        // Load from localStorage or API
        const recent = JSON.parse(localStorage.getItem('recentDocumentaries') || '[]');
        recentItems.innerHTML = '';
        
        if (recent.length === 0) {
            recentItems.innerHTML = '<p class="no-items">No recent items</p>';
            return;
        }
        
        recent.slice(0, 5).forEach(item => {
            const div = document.createElement('div');
            div.className = 'recent-item';
            div.innerHTML = `
                <i class="fas fa-video"></i>
                <span class="recent-title">${item.title || 'Untitled'}</span>
                <span class="recent-date">${new Date(item.date).toLocaleDateString()}</span>
            `;
            div.addEventListener('click', () => {
                window.location.href = `/vidgenerator/documentary/${item.id}`;
            });
            recentItems.appendChild(div);
        });
    }
    
    function updateSidebarStats() {
        // Update statistics from API or localStorage
        fetch('/vidgenerator/api/stats')
            .then(res => res.json())
            .then(data => {
                const totalVideos = document.getElementById('stat-total-videos');
                const today = document.getElementById('stat-today');
                const storage = document.getElementById('stat-storage');
                
                if (totalVideos) totalVideos.textContent = data.total || 0;
                if (today) today.textContent = data.today || 0;
                if (storage) storage.textContent = (data.storage || 0).toFixed(2) + ' GB';
            })
            .catch(() => {
                // Fallback to localStorage
                const stats = JSON.parse(localStorage.getItem('stats') || '{"total":0,"today":0,"storage":0}');
                const totalVideos = document.getElementById('stat-total-videos');
                const today = document.getElementById('stat-today');
                const storage = document.getElementById('stat-storage');
                
                if (totalVideos) totalVideos.textContent = stats.total || 0;
                if (today) today.textContent = stats.today || 0;
                if (storage) storage.textContent = (stats.storage || 0).toFixed(2) + ' GB';
            });
    }
    
    // ==========================================
    // CHAT PANEL FUNCTIONALITY
    // ==========================================
    function initializeChatPanel() {
        const chatToggle = document.getElementById('chat-toggle');
        const chatPanel = document.getElementById('chat-panel');
        const chatClose = document.getElementById('chat-close');
        const chatSend = document.getElementById('chat-send');
        const chatInput = document.getElementById('chat-input');
        const chatMessages = document.getElementById('chat-messages');
        
        if (chatToggle && chatPanel) {
            chatToggle.addEventListener('click', function() {
                chatPanel.classList.toggle('active');
                if (chatPanel.classList.contains('active')) {
                    chatInput.focus();
                }
            });
        }
        
        if (chatClose && chatPanel) {
            chatClose.addEventListener('click', function() {
                chatPanel.classList.remove('active');
            });
        }
        
        function sendMessage() {
            const message = chatInput.value.trim();
            if (!message) return;
            
            // Add user message
            addChatMessage('user', message);
            chatInput.value = '';
            
            // Simulate bot response (replace with actual API call)
            setTimeout(() => {
                addChatMessage('bot', 'Thank you for your message. This is a placeholder response.');
            }, 500);
        }
        
        if (chatSend) {
            chatSend.addEventListener('click', sendMessage);
        }
        
        if (chatInput) {
            chatInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });
        }
        
        // Add welcome message
        if (chatMessages) {
            addChatMessage('bot', 'Hello! How can I help you today?');
        }
    }
    
    function addChatMessage(sender, message) {
        const chatMessages = document.getElementById('chat-messages');
        if (!chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender}`;
        messageDiv.innerHTML = `
            <div class="chat-message-content">${escapeHtml(message)}</div>
            <div class="chat-message-time">${new Date().toLocaleTimeString()}</div>
        `;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // ==========================================
    // SETTINGS PANEL FUNCTIONALITY
    // ==========================================
    function initializeSettingsPanel() {
        const settingsToggle = document.getElementById('settings-toggle');
        const settingsPanel = document.getElementById('settings-panel');
        const settingsClose = document.getElementById('settings-close');
        const settingsTabs = document.querySelectorAll('.settings-tab');
        const settingsTabContents = document.querySelectorAll('.settings-tab-content');
        
        // Toggle settings panel
        if (settingsToggle && settingsPanel) {
            settingsToggle.addEventListener('click', function() {
                settingsPanel.classList.toggle('active');
            });
        }
        
        if (settingsClose && settingsPanel) {
            settingsClose.addEventListener('click', function() {
                settingsPanel.classList.remove('active');
            });
        }
        
        // Tab switching
        settingsTabs.forEach(tab => {
            tab.addEventListener('click', function() {
                const targetTab = this.getAttribute('data-tab');
                
                // Remove active from all tabs and contents
                settingsTabs.forEach(t => t.classList.remove('active'));
                settingsTabContents.forEach(c => c.classList.remove('active'));
                
                // Add active to clicked tab and corresponding content
                this.classList.add('active');
                const targetContent = document.getElementById(`settings-tab-${targetTab}`);
                if (targetContent) {
                    targetContent.classList.add('active');
                }
            });
        });
        
        // Save settings on change
        const settingInputs = document.querySelectorAll('.setting-input, .settings-panel input[type="checkbox"]');
        settingInputs.forEach(input => {
            input.addEventListener('change', function() {
                saveSettings();
            });
        });
    }
    
    function saveSettings() {
        const settings = {
            duration: document.getElementById('duration-setting')?.value || '45',
            quality: document.getElementById('quality-setting')?.value || '1080p',
            style: document.getElementById('style-setting')?.value || 'cinematic',
            provider: document.getElementById('provider-setting')?.value || 'auto',
            autoTitle: document.getElementById('auto-title')?.checked || false,
            autoThumbnail: document.getElementById('auto-thumbnail')?.checked || false,
            autoSaveDraft: document.getElementById('auto-save-draft')?.checked || false
        };
        
        localStorage.setItem('generatorSettings', JSON.stringify(settings));
    }
    
    function loadSettings() {
        const settings = JSON.parse(localStorage.getItem('generatorSettings') || '{}');
        
        if (settings.duration) {
            const durationSelect = document.getElementById('duration-setting');
            if (durationSelect) durationSelect.value = settings.duration;
        }
        if (settings.quality) {
            const qualitySelect = document.getElementById('quality-setting');
            if (qualitySelect) qualitySelect.value = settings.quality;
        }
        if (settings.style) {
            const styleSelect = document.getElementById('style-setting');
            if (styleSelect) styleSelect.value = settings.style;
        }
        if (settings.provider) {
            const providerSelect = document.getElementById('provider-setting');
            if (providerSelect) providerSelect.value = settings.provider;
        }
        if (settings.autoTitle !== undefined) {
            const autoTitle = document.getElementById('auto-title');
            if (autoTitle) autoTitle.checked = settings.autoTitle;
        }
        if (settings.autoThumbnail !== undefined) {
            const autoThumbnail = document.getElementById('auto-thumbnail');
            if (autoThumbnail) autoThumbnail.checked = settings.autoThumbnail;
        }
        if (settings.autoSaveDraft !== undefined) {
            const autoSaveDraft = document.getElementById('auto-save-draft');
            if (autoSaveDraft) autoSaveDraft.checked = settings.autoSaveDraft;
        }
    }
    
    // ==========================================
    // NETWORK STATUS MONITORING
    // ==========================================
    function initializeNetworkMonitoring() {
        const networkApiStatus = document.getElementById('network-api-status');
        const networkConnection = document.getElementById('network-connection');
        const networkLatency = document.getElementById('network-latency');
    const networkIndicator = document.getElementById('network-indicator');
    
    function setNetworkIndicator(isOnline) {
        if (!networkIndicator) return;
        const dot = networkIndicator.querySelector('.status-dot');
        const label = networkIndicator.querySelector('.status-label');
        if (dot) {
            dot.classList.toggle('online', isOnline);
            dot.classList.toggle('offline', !isOnline);
        }
        if (label) {
            label.textContent = isOnline ? 'Online' : 'Offline';
        }
    }
    
    setNetworkIndicator(navigator.onLine);
    window.addEventListener('online', () => setNetworkIndicator(true));
    window.addEventListener('offline', () => setNetworkIndicator(false));
        
        // Check network status every 30 seconds
        checkNetworkStatus();
        setInterval(checkNetworkStatus, 30000);
        
        function checkNetworkStatus() {
        setNetworkIndicator(navigator.onLine);
            // Check API status
            fetch('/vidgenerator/api/health', { method: 'GET', cache: 'no-cache' })
                .then(res => {
                    if (res.ok) {
                        if (networkApiStatus) {
                            networkApiStatus.textContent = 'Online';
                            networkApiStatus.className = 'status-value status-online';
                        }
                    } else {
                        throw new Error('API error');
                    }
                })
                .catch(() => {
                    if (networkApiStatus) {
                        networkApiStatus.textContent = 'Offline';
                        networkApiStatus.className = 'status-value status-offline';
                    }
                });
            
            // Check connection
            if (navigator.onLine) {
                if (networkConnection) {
                    networkConnection.textContent = 'Connected';
                    networkConnection.className = 'status-value status-online';
                }
            } else {
                if (networkConnection) {
                    networkConnection.textContent = 'Disconnected';
                    networkConnection.className = 'status-value status-offline';
                }
            }
            
            // Check latency
            const startTime = performance.now();
            fetch('/vidgenerator/api/health', { method: 'GET', cache: 'no-cache' })
                .then(() => {
                    const latency = Math.round(performance.now() - startTime);
                    if (networkLatency) {
                        networkLatency.textContent = latency + 'ms';
                        networkLatency.className = 'status-value ' + (latency < 200 ? 'status-online' : latency < 500 ? 'status-warning' : 'status-offline');
                    }
                })
                .catch(() => {
                    if (networkLatency) {
                        networkLatency.textContent = 'N/A';
                        networkLatency.className = 'status-value status-offline';
                }
                if (networkIndicator) {
                    setNetworkIndicator(false);
                    }
                });
        }
    }
    
    // ==========================================
    // UTILITY TOOLS FUNCTIONALITY
    // ==========================================
    function initializeUtilityTools() {
        // Code formatter
        const formatCodeBtn = document.getElementById('utility-format-code');
        if (formatCodeBtn) {
            formatCodeBtn.addEventListener('click', function() {
                const codeInput = document.getElementById('utility-code-input');
                if (codeInput && codeInput.value) {
                    // Simple code formatting (can be enhanced)
                    codeInput.value = codeInput.value
                        .replace(/\n\s*\n/g, '\n')
                        .replace(/\{\s*\n/g, '{\n')
                        .replace(/\n\s*\}/g, '\n}');
                }
            });
        }
        
        // Text analyzer
        const analyzeTextBtn = document.getElementById('utility-analyze-text');
        if (analyzeTextBtn) {
            analyzeTextBtn.addEventListener('click', function() {
                const textInput = document.getElementById('utility-text-input');
                if (textInput && textInput.value) {
                    const text = textInput.value;
                    const words = text.split(/\s+/).filter(w => w.length > 0);
                    const chars = text.length;
                    const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
                    
                    alert(`Text Analysis:\nWords: ${words.length}\nCharacters: ${chars}\nSentences: ${sentences.length}\nAvg words per sentence: ${(words.length / sentences.length).toFixed(1)}`);
                }
            });
        }
        
        // URL validator
        const validateUrlBtn = document.getElementById('utility-validate-url');
        if (validateUrlBtn) {
            validateUrlBtn.addEventListener('click', function() {
                const urlInput = document.getElementById('utility-url-input');
                if (urlInput && urlInput.value) {
                    try {
                        new URL(urlInput.value);
                        alert('Valid URL!');
                    } catch {
                        alert('Invalid URL!');
                    }
                }
            });
        }
    }
    
    // Load settings on page load
    loadSettings();
    
    // ==========================================
    // TOP MENU FUNCTIONALITY
    // ==========================================
    initializeTopMenu();
    
    // ==========================================
    // CLIP GENERATION EVENT DISPATCHER
    // ==========================================
    function dispatchClipGenerationEvent(progress) {
        // Simulate clip generation events during video generation phase (50-65%)
        if (progress >= 50 && progress < 65) {
            const clipIndex = Math.floor((progress - 50) / 15 * 8) + 1; // 1-8 clips
            const clipDuration = 10 + Math.random() * 20; // 10-30 seconds
            
            // Check if we should dispatch this clip event
            if (!window.dispatchedClips) window.dispatchedClips = new Set();
            if (!window.dispatchedClips.has(clipIndex)) {
                window.dispatchedClips.add(clipIndex);
                
                // Create a placeholder clip URL (will be replaced with actual clip URL from API)
                const clipUrl = `/vidgenerator/api/clip/${currentDocumentaryId}/${clipIndex}`;
                
                // Dispatch custom event
                const event = new CustomEvent('clipGenerated', {
                    detail: {
                        clipUrl: clipUrl,
                        clipIndex: clipIndex,
                        clipDuration: clipDuration,
                        progress: progress
                    }
                });
                document.dispatchEvent(event);
                
                // Also try to fetch actual clip if available
                fetchClipIfAvailable(currentDocumentaryId, clipIndex, clipDuration);
            }
        }
    }
    
    async function fetchClipIfAvailable(docId, clipIndex, clipDuration) {
        if (!docId) return;
        
        try {
            // Try to fetch clip from API
            const response = await fetch(`/vidgenerator/api/documentary/${docId}/clips/${clipIndex}`);
            if (response.ok) {
                const data = await response.json();
                if (data.clipUrl) {
                    // Dispatch with actual clip URL
                    const event = new CustomEvent('clipGenerated', {
                        detail: {
                            clipUrl: data.clipUrl,
                            clipIndex: clipIndex,
                            clipDuration: data.duration || clipDuration,
                            progress: data.progress || 0
                        }
                    });
                    document.dispatchEvent(event);
                }
            }
        } catch (e) {
            // API endpoint might not exist yet, that's OK
            console.log('Clip API not available yet:', e);
        }
    }
    
    // ==========================================
    // MONITOR CLIP BACKGROUND
    // ==========================================
    initializeMonitorClipBackground();
    initializeMP4AwarenessModule();
    
    // ==========================================
    // SERVICE WORKER & TELEMETRY
    // ==========================================
    initializeServiceWorkerWidget();
    
    // Initialize Monitor Controls Toggle
    initializeMonitorControls();
    initializeCryptoPanel();
    initializeResearchTelemetry();
    
    // ==========================================
    // DISCORD INTEGRATION
    // ==========================================
    initializeDiscordIntegration();
    
    // ==========================================
    // CHATROOM FUNCTIONALITY
    // ==========================================
    initializeChatroom();
});

// ==========================================
// TOP MENU FUNCTIONALITY
// ==========================================
function initializeTopMenu() {
    const topMenuItems = document.querySelectorAll('.top-menu-item');
    const chatToggleTop = document.getElementById('chat-toggle-top');
    const themeToggleTop = document.getElementById('theme-toggle-top');
    
    // Tab switching
    topMenuItems.forEach(item => {
        item.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            
            // Remove active from all items
            topMenuItems.forEach(i => i.classList.remove('active'));
            this.classList.add('active');
            
            // Handle tab switching
            switch(targetTab) {
                case 'generator':
                    // Show generator interface
                    document.querySelector('.container')?.classList.remove('hidden');
                    break;
                case 'gallery':
                    // Use proper URL construction for gallery - fixed to masternoder.dk/vidgenerator/gallery
                    window.location.href = 'https://masternoder.dk/vidgenerator/gallery';
                    break;
                case 'discord':
                    // Show Discord tab in settings
                    const settingsPanel = document.getElementById('settings-panel');
                    if (settingsPanel) {
                        settingsPanel.classList.add('active');
                        // Switch to Discord tab
                        const discordTab = document.querySelector('.settings-tab[data-tab="discord"]');
                        if (discordTab) discordTab.click();
                    }
                    break;
                case 'network':
                    // Show Network tab in settings
                    if (settingsPanel) {
                        settingsPanel.classList.add('active');
                        const networkTab = document.querySelector('.settings-tab[data-tab="network"]');
                        if (networkTab) networkTab.click();
                    }
                    break;
                case 'utilities':
                    // Show Utilities tab in settings
                    if (settingsPanel) {
                        settingsPanel.classList.add('active');
                        const utilitiesTab = document.querySelector('.settings-tab[data-tab="utilities"]');
                        if (utilitiesTab) utilitiesTab.click();
                    }
                    break;
                case 'settings':
                    // Show Settings panel
                    if (settingsPanel) {
                        settingsPanel.classList.add('active');
                    }
                    break;
            }
        });
    });
    
    // Connect top menu actions to existing functionality
    if (chatToggleTop) {
        chatToggleTop.addEventListener('click', function() {
            const chatToggle = document.getElementById('chat-toggle');
            if (chatToggle) chatToggle.click();
        });
    }
    
    if (themeToggleTop) {
        themeToggleTop.addEventListener('click', function() {
            const themeToggle = document.getElementById('theme-toggle');
            if (themeToggle) themeToggle.click();
        });
    }
}

// ==========================================
// MONITOR CLIP BACKGROUND
// ==========================================
let generatedClips = [];
let clipBackgroundInterval = null;

function initializeMonitorClipBackground() {
    const clipContainer = document.getElementById('clip-preview-container');
    if (!clipContainer) return;
    
    // Listen for clip generation events
    document.addEventListener('clipGenerated', function(e) {
        addClipToBackground(e.detail.clipUrl, e.detail.clipIndex, e.detail.clipDuration);
    });
}

function addClipToBackground(clipUrl, clipIndex, clipDuration) {
    if (!clipUrl || clipDuration > 30) return; // Only show clips 0-30 seconds
    
    const clipContainer = document.getElementById('clip-preview-container');
    if (!clipContainer) return;
    
    // Check if clip already exists to prevent duplicates
    const existingClip = generatedClips.find(c => c.index === clipIndex);
    if (existingClip) {
        // Update existing clip URL if different
        if (existingClip.url !== clipUrl) {
            const video = existingClip.element.querySelector('video');
            if (video) {
                video.src = clipUrl;
                video.load();
                existingClip.url = clipUrl;
            }
        }
        return;
    }
    
    const clipItem = document.createElement('div');
    clipItem.className = 'clip-preview-item';
    clipItem.setAttribute('data-clip-index', clipIndex);
    
    const video = document.createElement('video');
    video.src = clipUrl;
    video.loop = true;
    video.muted = true;
    video.autoplay = true;
    video.playsInline = true;
    video.preload = 'auto';
    // Prevent video from interfering with monitor content
    video.style.mixBlendMode = 'normal';
    video.style.opacity = '0.5';
    
    // Handle video errors gracefully
    video.addEventListener('error', function(e) {
        console.log('[Monitor Clip] Video load error for clip', clipIndex, ':', e);
        // Remove failed clip
        if (clipItem.parentNode) {
            clipItem.parentNode.removeChild(clipItem);
        }
        generatedClips = generatedClips.filter(c => c.index !== clipIndex);
    }, { once: true });
    
    // Handle video loaded successfully
    video.addEventListener('loadeddata', function() {
        console.log('[Monitor Clip] Video loaded successfully for clip', clipIndex);
    }, { once: true });
    
    const clipInfo = document.createElement('div');
    clipInfo.className = 'clip-info';
    clipInfo.innerHTML = `
        <span>Clip ${clipIndex}</span>
        <span>${clipDuration.toFixed(1)}s</span>
    `;
    
    clipItem.appendChild(video);
    clipItem.appendChild(clipInfo);
    clipContainer.appendChild(clipItem);
    
    // Store clip reference
    generatedClips.push({
        element: clipItem,
        url: clipUrl,
        index: clipIndex,
        duration: clipDuration
    });
    
    // Limit to 8 clips visible (reduced from 12 to prevent interference)
    if (generatedClips.length > 8) {
        const oldestClip = generatedClips.shift();
        if (oldestClip.element.parentNode) {
            oldestClip.element.parentNode.removeChild(oldestClip.element);
        }
    }
    
    // Play video with error handling
    video.play().catch(e => {
        console.log('[Monitor Clip] Video autoplay prevented for clip', clipIndex, ':', e);
        // Try again after a short delay
        setTimeout(() => {
            video.play().catch(() => {
                // If still fails, just log it
                console.log('[Monitor Clip] Video play failed for clip', clipIndex);
            });
        }, 500);
    });
}

// ==========================================
// MP4 AWARENESS STATUS MODULE
// ==========================================
function initializeMP4AwarenessModule() {
    const mp4StatusCard = document.getElementById('mp4-status-card');
    const mp4StatusText = document.getElementById('mp4-status-text');
    const mp4ConfidenceText = document.getElementById('mp4-confidence');
    const mp4DurationText = document.getElementById('mp4-duration');
    const mp4SizeText = document.getElementById('mp4-size');
    const mp4VerifyBtn = document.getElementById('mp4-verify-btn');
    const mp4DownloadBtn = document.getElementById('mp4-download-btn');
    
    if (!mp4StatusCard) {
        return;
    }
    
    let currentMP4Path = null;
    let currentConfidence = 0;
    let currentStatus = 'UNKNOWN';
    
    window.updateMP4Awareness = function(mp4Info) {
        if (!mp4Info) return;
        
        currentMP4Path = mp4Info.path || currentMP4Path;
        currentConfidence = mp4Info.confidence ?? currentConfidence;
        currentStatus = mp4Info.status || currentStatus;
        const normalizedStatus = (currentStatus || 'unknown').toUpperCase();
        const statusClass =
            normalizedStatus === 'READY' ? 'status-online' :
            normalizedStatus === 'VERIFYING' ? 'status-warning' :
            'status-offline';
        
        if (mp4StatusText) {
            mp4StatusText.textContent = normalizedStatus;
            mp4StatusText.className = `mp4-status-value ${statusClass}`;
        }
        
        if (mp4ConfidenceText) {
            const confidencePct = Math.max(0, Math.min(100, Math.round((currentConfidence || 0) * 100)));
            mp4ConfidenceText.textContent = `${confidencePct}%`;
        }
        if (mp4DurationText) {
            mp4DurationText.textContent = mp4Info.duration ? `${mp4Info.duration.toFixed(2)}s` : '--';
        }
        if (mp4SizeText) {
            mp4SizeText.textContent = mp4Info.size ? `${mp4Info.size.toFixed(2)} MB` : '--';
        }
        
        if (mp4DownloadBtn) {
            mp4DownloadBtn.disabled = !currentMP4Path;
            mp4DownloadBtn.onclick = function() {
                if (currentMP4Path) {
                    const builder = window.buildApiUrl || ((endpoint) => endpoint.startsWith('/') ? endpoint : '/' + endpoint);
                    const downloadUrl = (window.currentDocumentaryId)
                        ? builder(`api/documentary/${window.currentDocumentaryId}/video`)
                        : currentMP4Path;
                    window.open(downloadUrl, '_blank');
                }
            };
        }
    };
    
    if (mp4VerifyBtn) {
        mp4VerifyBtn.addEventListener('click', function() {
            if (!currentDocumentaryId) {
                alert('Ingen aktiv generering. Start en dokumentar først.');
                return;
            }
            mp4StatusText.textContent = 'VERIFYING';
            mp4StatusText.className = 'mp4-status-value status-warning';
            triggerMP4Verification(currentDocumentaryId, true);
        });
    }
}

// ==========================================
// SERVICE WORKER & TELEMETRY MODULES
// ==========================================
function initializeServiceWorkerWidget() {
    const swCard = document.getElementById('sw-card');
    if (!swCard) return;
    
    if (!('serviceWorker' in navigator)) {
        const statusEl = document.getElementById('sw-status');
        if (statusEl) {
            statusEl.textContent = 'Not Supported';
            statusEl.className = 'status-pill status-offline';
        }
        return;
    }

    const statusEl = document.getElementById('sw-status');
    const versionEl = document.getElementById('sw-version');
    const cacheEl = document.getElementById('sw-cache-size');
    const refreshBtn = document.getElementById('sw-refresh-btn');
    const clearBtn = document.getElementById('sw-clear-cache-btn');
    
    // Listen for service worker messages
    if (navigator.serviceWorker) {
        navigator.serviceWorker.addEventListener('message', function(event) {
            if (event.data && event.data.type === 'SW_ACTIVATED') {
                console.log('[SW Widget] Service worker activated:', event.data.version);
                updateStatus(); // Refresh status
            }
        });
    }

    async function updateStatus() {
        try {
            const registrations = await navigator.serviceWorker.getRegistrations();
            if (!registrations.length) {
                if (statusEl) {
                    statusEl.textContent = 'Not Registered';
                    statusEl.className = 'status-pill status-offline';
                }
                if (versionEl) versionEl.textContent = '–';
                if (cacheEl) cacheEl.textContent = '0 MB';
                return;
            }

            const registration = registrations[0];
            const worker = registration.active || registration.installing || registration.waiting;
            
            if (statusEl) {
                if (registration.active) {
                    statusEl.textContent = 'Active';
                    statusEl.className = 'status-pill status-online';
                } else if (registration.installing) {
                    statusEl.textContent = 'Installing';
                    statusEl.className = 'status-pill status-warning';
                } else if (registration.waiting) {
                    statusEl.textContent = 'Waiting';
                    statusEl.className = 'status-pill status-warning';
                } else {
                    statusEl.textContent = 'Unknown';
                    statusEl.className = 'status-pill status-offline';
                }
            }
            
            if (versionEl && worker) {
                const scriptUrl = worker.scriptURL || '';
                const versionMatch = scriptUrl.match(/dg-sw-([^/]+)/);
                versionEl.textContent = versionMatch ? versionMatch[1] : 'v?';
            } else if (versionEl) {
                versionEl.textContent = 'v?';
            }

            // Calculate cache size
            if ('caches' in window) {
                let totalSize = 0;
                const cacheNames = await caches.keys();
                
                for (const cacheName of cacheNames) {
                    const cache = await caches.open(cacheName);
                    const keys = await cache.keys();
                    for (const request of keys) {
                        const response = await cache.match(request);
                        if (response) {
                            const blob = await response.blob();
                            totalSize += blob.size;
                        }
                    }
                }
                
                if (cacheEl) {
                    cacheEl.textContent = `${(totalSize / (1024 * 1024)).toFixed(2)} MB`;
                }
                
                // Also try storage estimate if available
                if (navigator.storage?.estimate) {
                    try {
                        const estimate = await navigator.storage.estimate();
                        if (estimate.usage && cacheEl) {
                            // Use storage estimate as fallback if cache calculation fails
                            if (totalSize === 0) {
                                cacheEl.textContent = `${(estimate.usage / (1024 * 1024)).toFixed(2)} MB`;
                            }
                        }
                    } catch (e) {
                        // Ignore storage estimate errors
                    }
                }
                
                window.incrementResearchStat && window.incrementResearchStat('cacheHits');
            } else if (cacheEl) {
                cacheEl.textContent = 'N/A';
            }
        } catch (e) {
            console.error('[SW Widget] Error updating status:', e);
            if (statusEl) {
                statusEl.textContent = 'Error';
                statusEl.className = 'status-pill status-warning';
            }
        }
    }

    if (refreshBtn) {
        refreshBtn.addEventListener('click', async () => {
            // Force update check
            try {
                const registrations = await navigator.serviceWorker.getRegistrations();
                for (const registration of registrations) {
                    await registration.update();
                }
            } catch (e) {
                console.error('[SW Widget] Error updating:', e);
            }
            updateStatus();
        });
    }
    
    if (clearBtn) {
        clearBtn.addEventListener('click', async () => {
            if (!confirm('Clear all cached assets? This will require re-downloading resources.')) return;
            try {
                const cacheNames = await caches.keys();
                await Promise.all(cacheNames.map(name => caches.delete(name)));
                if (cacheEl) cacheEl.textContent = '0 MB';
                window.incrementResearchStat && window.incrementResearchStat('cacheHits', -5);
                console.log('[SW Widget] Cache cleared');
            } catch (e) {
                console.error('[SW Widget] Error clearing cache:', e);
                alert('Error clearing cache: ' + e.message);
            }
        });
    }

    // Initial status update
    updateStatus();
    
    // Update status every 30 seconds
    setInterval(updateStatus, 30000);
}

function initializeCryptoPanel() {
    const nodesEl = document.getElementById('mn2-nodes');
    const blockEl = document.getElementById('mn2-block');
    const diffEl = document.getElementById('mn2-difficulty');
    const masternodeEl = document.getElementById('mn2-masternodes');
    const latencyEl = document.getElementById('mn2-latency');
    const throughputEl = document.getElementById('mn2-throughput');
    const statusText = document.getElementById('mn2-status-text');
    const refreshBtn = document.getElementById('mn2-refresh-btn');
    if (!nodesEl || !refreshBtn) return;

    function refreshTelemetry() {
        const nodes = 5800 + Math.floor(Math.random() * 400);
        const latency = (35 + Math.random() * 25).toFixed(0);
        const throughput = (2.5 + Math.random()).toFixed(1);

        nodesEl.textContent = nodes.toLocaleString();
        latencyEl.textContent = `${latency} ms`;
        throughputEl.textContent = `${throughput} Gb/s`;
        statusText.textContent = latency < 55 ? 'Operational' : 'Degraded';
        window.incrementResearchStat && window.incrementResearchStat('researchVerifications');
        fetchExplorerStats();
    }

    async function fetchExplorerStats() {
        try {
            const [block, diff, mnCount] = await Promise.all([
                fetchChainzStat('getblockcount'),
                fetchChainzStat('getdifficulty'),
                fetchChainzStat('getmasternodecount')
            ]);
            if (blockEl && block !== null) blockEl.textContent = Number(block).toLocaleString();
            if (diffEl && diff !== null) diffEl.textContent = Number(diff).toFixed(2);
            if (masternodeEl && mnCount !== null) masternodeEl.textContent = Number(mnCount).toLocaleString();
        } catch (e) {
            console.warn('[MN2 Explorer] Could not load stats:', e);
        }
    }

    async function fetchChainzStat(query) {
        try {
            const response = await fetch(`https://chainz.cryptoid.info/mn2/api.dws?q=${query}`, { cache: 'no-store' });
            if (!response.ok) return null;
            const text = (await response.text()).trim();
            const num = Number(text);
            return Number.isNaN(num) ? text : num;
        } catch (e) {
            return null;
        }
    }

    refreshBtn.addEventListener('click', refreshTelemetry);
    refreshTelemetry();
}

function initializeResearchTelemetry() {
    const stats = {
        offlineSessions: document.getElementById('research-offline'),
        cacheHits: document.getElementById('research-cache-hits'),
        researchVerifications: document.getElementById('research-verifications')
    };

    window.incrementResearchStat = function (key, delta = 1) {
        const el = stats[key];
        if (!el) return;
        const current = parseInt(el.textContent, 10) || 0;
        el.textContent = Math.max(0, current + delta);
    };
}

async function triggerMP4Verification(docId, notifyUser = false) {
    if (!docId) return false;
    const builder = window.buildApiUrl || ((endpoint) => endpoint.startsWith('/') ? endpoint : '/' + endpoint);
    try {
        const response = await fetch(builder(`api/documentary/${docId}/verify-mp4`), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (typeof window.updateMP4Awareness === 'function') {
            window.updateMP4Awareness({
                status: data.success ? 'ready' : 'failed',
                confidence: data.confidence ?? 0.2,
                duration: data.duration,
                size: data.size,
                path: data.path
            });
        }
        window.incrementResearchStat && window.incrementResearchStat('researchVerifications');
        if (notifyUser) {
            alert(data.message || (data.success ? 'MP4 verified' : 'Verification failed'));
        }
        return data.success;
    } catch (error) {
        console.warn('[MP4] Verification failed:', error);
        if (notifyUser) {
            alert('MP4 verification failed. See console for details.');
        }
        return false;
    }
}

function clearClipBackground() {
    const clipContainer = document.getElementById('clip-preview-container');
    if (clipContainer) {
        clipContainer.innerHTML = '';
    }
    generatedClips = [];
}

// ==========================================
// DISCORD INTEGRATION
// ==========================================
let discordWebhook = null;
let discordConnected = false;

function initializeDiscordIntegration() {
    const connectBtn = document.getElementById('discord-connect-btn');
    const disconnectBtn = document.getElementById('discord-disconnect-btn');
    const webhookInput = document.getElementById('discord-webhook-url');
    
    // Load saved webhook
    const savedWebhook = localStorage.getItem('discordWebhook');
    if (savedWebhook && webhookInput) {
        webhookInput.value = savedWebhook;
    }
    
    if (connectBtn) {
        connectBtn.addEventListener('click', function() {
            const webhookUrl = webhookInput?.value.trim();
            if (!webhookUrl) {
                alert('Please enter a Discord webhook URL');
                return;
            }
            
            // Test webhook
            testDiscordWebhook(webhookUrl).then(success => {
                if (success) {
                    discordWebhook = webhookUrl;
                    discordConnected = true;
                    localStorage.setItem('discordWebhook', webhookUrl);
                    
                    connectBtn.style.display = 'none';
                    if (disconnectBtn) disconnectBtn.style.display = 'block';
                    
                    updateDiscordStatus(true);
                    loadDiscordMessages();
                } else {
                    alert('Failed to connect to Discord. Please check your webhook URL.');
                }
            });
        });
    }
    
    if (disconnectBtn) {
        disconnectBtn.addEventListener('click', function() {
            discordWebhook = null;
            discordConnected = false;
            localStorage.removeItem('discordWebhook');
            
            connectBtn.style.display = 'block';
            disconnectBtn.style.display = 'none';
            
            updateDiscordStatus(false);
        });
    }
    
    // Save webhook on change
    if (webhookInput) {
        webhookInput.addEventListener('change', function() {
            if (this.value.trim()) {
                localStorage.setItem('discordWebhook', this.value.trim());
            }
        });
    }
    
    // Check if already connected
    if (savedWebhook) {
        testDiscordWebhook(savedWebhook).then(success => {
            if (success) {
                discordWebhook = savedWebhook;
                discordConnected = true;
                connectBtn.style.display = 'none';
                if (disconnectBtn) disconnectBtn.style.display = 'block';
                updateDiscordStatus(true);
            }
        });
    }
}

async function testDiscordWebhook(webhookUrl) {
    try {
        const response = await fetch(webhookUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                content: '🔗 Connected to Documentary Generator'
            })
        });
        return response.ok;
    } catch (e) {
        return false;
    }
}

// ==========================================
// MONITOR CONTROLS - Rethought Structure
// ==========================================
function initializeMonitorControls() {
    const toggleBtn = document.getElementById('monitor-toggle-settings');
    const advancedSettings = document.getElementById('monitor-advanced-settings');
    
    if (toggleBtn && advancedSettings) {
        toggleBtn.addEventListener('click', function() {
            const isVisible = advancedSettings.style.display !== 'none';
            advancedSettings.style.display = isVisible ? 'none' : 'flex';
            toggleBtn.classList.toggle('active', !isVisible);
            
            // Update icon
            const icon = toggleBtn.querySelector('i');
            if (icon) {
                icon.className = isVisible ? 'fas fa-cog' : 'fas fa-cog fa-spin';
            }
        });
    }
    
    // Update slider values
    const sliders = {
        'monitor-volume-slider': 'monitor-volume-value',
        'monitor-speed-slider': 'monitor-speed-value',
        'monitor-text-speed-slider': 'monitor-text-speed-value',
        'monitor-brightness-slider': 'monitor-brightness-value'
    };
    
    Object.keys(sliders).forEach(sliderId => {
        const slider = document.getElementById(sliderId);
        const valueDisplay = document.getElementById(sliders[sliderId]);
        
        if (slider && valueDisplay) {
            slider.addEventListener('input', function() {
                let value = this.value;
                if (sliderId.includes('brightness') || sliderId.includes('volume')) {
                    valueDisplay.textContent = value + '%';
                } else {
                    valueDisplay.textContent = value + 'x';
                }
            });
        }
    });
}

function updateDiscordStatus(connected) {
    const statusEl = document.getElementById('discord-connection-status');
    if (statusEl) {
        statusEl.textContent = connected ? 'Connected' : 'Disconnected';
        statusEl.className = 'status-value ' + (connected ? 'status-online' : 'status-offline');
    }
}

async function sendDiscordNotification(message, embed = null) {
    if (!discordConnected || !discordWebhook) return;
    
    try {
        const payload = { content: message };
        if (embed) payload.embeds = [embed];
        
        await fetch(discordWebhook, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
    } catch (e) {
        console.error('Discord notification failed:', e);
    }
}

function loadDiscordMessages() {
    // Placeholder - would fetch from Discord API if bot integration
    const messagesList = document.getElementById('discord-messages-list');
    if (messagesList) {
        messagesList.innerHTML = '<p class="no-items">Discord messages will appear here when bot integration is set up.</p>';
    }
}

// ==========================================
// CHATROOM FUNCTIONALITY
// ==========================================
function initializeChatroom() {
    // Enhanced chatroom with real-time features
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const chatSend = document.getElementById('chat-send');
    
    // WebSocket connection for real-time chat (placeholder)
    let chatSocket = null;
    
    function connectChatroom() {
        // Placeholder for WebSocket connection
        // const wsUrl = 'ws://localhost:5000/chat';
        // chatSocket = new WebSocket(wsUrl);
        
        // For now, use localStorage for chat history
        loadChatHistory();
    }
    
    function loadChatHistory() {
        const history = JSON.parse(localStorage.getItem('chatHistory') || '[]');
        history.forEach(msg => {
            addChatMessage(msg.sender, msg.message, msg.timestamp);
        });
    }
    
    function saveChatMessage(sender, message) {
        const history = JSON.parse(localStorage.getItem('chatHistory') || '[]');
        history.push({
            sender,
            message,
            timestamp: new Date().toISOString()
        });
        // Keep last 50 messages
        if (history.length > 50) {
            history.shift();
        }
        localStorage.setItem('chatHistory', JSON.stringify(history));
    }
    
    // Override addChatMessage to save history
    const originalAddChatMessage = window.addChatMessage || addChatMessage;
    window.addChatMessage = function(sender, message, timestamp) {
        originalAddChatMessage(sender, message, timestamp);
        if (sender === 'user') {
            saveChatMessage(sender, message);
        }
    };
    
    connectChatroom();
}

