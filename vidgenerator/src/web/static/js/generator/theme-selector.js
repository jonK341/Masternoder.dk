/**
 * Intelligent Theme Selector for Generator
 * Controls theme switching based on content analysis
 */

class GeneratorThemeSelector {
    constructor() {
        this.currentTheme = 'matrix'; // Default theme
        this.themeConfig = null;
        this.initializeThemeUI();
        this.setupThemeDetection();
    }
    
    initializeThemeUI() {
        // Create theme selector UI if it doesn't exist
        const themeContainer = document.getElementById('theme-selector-container');
        if (!themeContainer) {
            const container = document.createElement('div');
            container.id = 'theme-selector-container';
            container.className = 'theme-selector-container';
            container.innerHTML = `
                <label for="theme-select">Theme:</label>
                <select id="theme-select" class="theme-select">
                    <option value="auto">Auto (Intelligent)</option>
                    <option value="matrix" selected>Matrix</option>
                    <option value="mtg">Magic the Gathering</option>
                    <option value="halo4">Halo 4</option>
                    <option value="nazi_wwii">WWII Historical</option>
                    <option value="cyberpunk">Cyberpunk</option>
                    <option value="sci-fi">Sci-Fi</option>
                    <option value="nature">Nature</option>
                </select>
                <div id="theme-preview" class="theme-preview"></div>
            `;
            
            // Insert before generate button or in appropriate location
            const promptContainer = document.querySelector('.prompt-container') || document.getElementById('prompt-input')?.parentElement;
            if (promptContainer) {
                promptContainer.appendChild(container);
            }
        }
        
        // Setup theme change handler
        const themeSelect = document.getElementById('theme-select');
        if (themeSelect) {
            themeSelect.addEventListener('change', (e) => {
                this.setTheme(e.target.value);
            });
        }
    }
    
    setupThemeDetection() {
        // Auto-detect theme when prompt changes
        const promptInput = document.getElementById('prompt-input');
        if (promptInput) {
            let detectTimeout;
            promptInput.addEventListener('input', (e) => {
                clearTimeout(detectTimeout);
                detectTimeout = setTimeout(() => {
                    this.autoDetectTheme(e.target.value);
                }, 500); // Debounce 500ms
            });
        }
    }
    
    async autoDetectTheme(prompt) {
        const themeSelect = document.getElementById('theme-select');
        if (!themeSelect || themeSelect.value !== 'auto') {
            return; // Only auto-detect if "auto" is selected
        }
        
        try {
            // Try /vidgenerator prefix first, fallback to root
            let response = await fetch('/vidgenerator/api/theme/detect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            });
            
            // If 404, try without prefix
            if (response.status === 404) {
                response = await fetch('/api/theme/detect', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt })
                });
            }
            
            if (response.ok) {
                const data = await response.json();
                this.currentTheme = data.theme;
                this.themeConfig = data.config;
                this.updateThemePreview();
                console.log(`[ThemeSelector] Auto-detected theme: ${data.theme} (confidence: ${data.confidence})`);
            }
        } catch (error) {
            console.error('[ThemeSelector] Auto-detection failed:', error);
        }
    }
    
    setTheme(themeName) {
        if (themeName === 'auto') {
            // Trigger auto-detection
            const promptInput = document.getElementById('prompt-input');
            if (promptInput && promptInput.value) {
                this.autoDetectTheme(promptInput.value);
            }
            return;
        }
        
        this.currentTheme = themeName;
        this.loadThemeConfig(themeName);
        this.applyTheme(themeName);
    }
    
    async loadThemeConfig(themeName) {
        try {
            // Try /vidgenerator prefix first, fallback to root
            let response = await fetch(`/vidgenerator/api/theme/config/${themeName}`);
            
            // If 404, try without prefix
            if (response.status === 404) {
                response = await fetch(`/api/theme/config/${themeName}`);
            }
            
            if (response.ok) {
                this.themeConfig = await response.json();
                this.updateThemePreview();
            } else {
                console.warn(`[ThemeSelector] Theme config not found for ${themeName}, using defaults`);
                // Use default theme config
                this.themeConfig = { name: themeName, colors: {} };
            }
        } catch (error) {
            console.error('[ThemeSelector] Failed to load theme config:', error);
            // Use default theme config on error
            this.themeConfig = { name: themeName, colors: {} };
        }
    }
    
    applyTheme(themeName) {
        // Apply theme to UI
        document.body.setAttribute('data-theme', themeName);
        
        // Update theme-specific styles
        if (this.themeConfig && this.themeConfig.colors) {
            const root = document.documentElement;
            root.style.setProperty('--theme-primary', this.themeConfig.colors.primary);
            root.style.setProperty('--theme-secondary', this.themeConfig.colors.secondary);
            root.style.setProperty('--theme-accent', this.themeConfig.colors.accent);
            root.style.setProperty('--theme-background', this.themeConfig.colors.background);
        }
        
        // Load theme background video and image
        this.loadThemeBackgrounds(themeName);
        
        // Also call main.js setTheme if available (for compatibility)
        // Wait a bit for main.js to be fully loaded (it uses defer)
        setTimeout(() => {
            if (typeof window.setTheme === 'function') {
                console.log(`[ThemeSelector] Calling main.js setTheme: ${themeName}`);
                window.setTheme(themeName);
            } else {
                console.warn('[ThemeSelector] window.setTheme not available yet, main.js may not be loaded');
            }
        }, 100);
        
        // Save to localStorage
        localStorage.setItem('documentaryTheme', themeName);
        
        console.log(`[ThemeSelector] Applied theme: ${themeName}`);
    }
    
    async loadThemeBackgrounds(themeName) {
        console.log(`[ThemeSelector] loadThemeBackgrounds called for theme: ${themeName}`);
        
        // Load theme background video
        const themeVideo = document.getElementById('theme-video');
        const themeVideoContainer = document.getElementById('theme-background-video');
        const themeImage = document.getElementById('theme-background-image');
        
        console.log('[ThemeSelector] Elements found:', {
            themeVideo: !!themeVideo,
            themeVideoContainer: !!themeVideoContainer,
            themeImage: !!themeImage
        });
        
        // Check if theme cache is available
        const useCache = typeof window.themeCache !== 'undefined';
        
        // Theme video paths - try both with and without /vidgenerator prefix
        const themeVideos = {
            matrix: ['/vidgenerator/static/video/themes/matrix_background.mp4', '/static/video/themes/matrix_background.mp4'],
            mtg: ['/vidgenerator/static/video/themes/mtg_background.mp4', '/static/video/themes/mtg_background.mp4'],
            halo4: ['/vidgenerator/static/video/themes/halo_background.mp4', '/static/video/themes/halo_background.mp4'],
            halo: ['/vidgenerator/static/video/themes/halo_background.mp4', '/static/video/themes/halo_background.mp4'],
            cyberpunk: ['/vidgenerator/static/video/themes/cyberpunk_background.mp4', '/static/video/themes/cyberpunk_background.mp4'],
            nazi_wwii: ['/vidgenerator/static/video/themes/wwii_background.mp4', '/static/video/themes/wwii_background.mp4'],
            'sci-fi': ['/vidgenerator/static/video/themes/scifi_background.mp4', '/static/video/themes/scifi_background.mp4'],
            nature: ['/vidgenerator/static/video/themes/nature_background.mp4', '/static/video/themes/nature_background.mp4']
        };
        
        // Theme background images - try both with and without /vidgenerator prefix
        const themeImages = {
            matrix: ['/vidgenerator/static/img/themes/matrix_bg.jpg', '/static/img/themes/matrix_bg.jpg'],
            mtg: ['/vidgenerator/static/img/themes/mtg_bg.jpg', '/static/img/themes/mtg_bg.jpg'],
            halo4: ['/vidgenerator/static/img/themes/halo_bg.jpg', '/static/img/themes/halo_bg.jpg'],
            halo: ['/vidgenerator/static/img/themes/halo_bg.jpg', '/static/img/themes/halo_bg.jpg'],
            cyberpunk: ['/vidgenerator/static/img/themes/cyberpunk_bg.jpg', '/static/img/themes/cyberpunk_bg.jpg'],
            nazi_wwii: ['/vidgenerator/static/img/themes/wwii_bg.jpg', '/static/img/themes/wwii_bg.jpg'],
            'sci-fi': ['/vidgenerator/static/img/themes/scifi_bg.jpg', '/static/img/themes/scifi_bg.jpg'],
            nature: ['/vidgenerator/static/img/themes/nature_bg.jpg', '/static/img/themes/nature_bg.jpg']
        };
        
        // Load video with cache support
        if (themeVideo) {
            const videoPaths = themeVideos[themeName] || themeVideos['matrix'];
            if (videoPaths && videoPaths.length > 0) {
                // Try to load from cache first
                if (useCache) {
                    try {
                        const cached = await window.themeCache.getCachedVideo(themeName);
                        if (cached && cached.blobUrl) {
                            console.log(`[ThemeSelector] Using cached video for ${themeName}`);
                            themeVideo.src = cached.blobUrl;
                            themeVideo.onloadeddata = function() {
                                console.log(`[ThemeSelector] Cached video loaded successfully`);
                            };
                            themeVideo.load();
                            if (themeVideoContainer) {
                                themeVideoContainer.style.setProperty('display', 'block', 'important');
                                themeVideoContainer.style.setProperty('visibility', 'visible', 'important');
                                themeVideoContainer.style.setProperty('opacity', '0.18', 'important');
                            }
                            themeVideo.play().catch(e => {
                                console.log(`[ThemeSelector] Video autoplay prevented: ${e.message}`);
                            });
                            return; // Successfully loaded from cache
                        }
                    } catch (error) {
                        console.warn(`[ThemeSelector] Cache error, falling back to network:`, error);
                    }
                }
                
                // Load from network (and cache if available)
                const loadVideo = async (pathIndex = 0) => {
                    const videoPath = videoPaths[pathIndex];
                    if (!videoPath) {
                        console.warn(`[ThemeSelector] No more video paths to try for theme: ${themeName}`);
                        return;
                    }
                    
                    try {
                        // Try to download and cache if cache is available
                        if (useCache) {
                            try {
                                const blobUrl = await window.themeCache.downloadAndCacheVideo(themeName, videoPath);
                                themeVideo.src = blobUrl;
                                console.log(`[ThemeSelector] Video downloaded and cached: ${videoPath}`);
                            } catch (cacheError) {
                                // If cache fails, try direct URL
                                console.warn(`[ThemeSelector] Cache download failed, using direct URL:`, cacheError);
                                themeVideo.src = videoPath;
                            }
                        } else {
                            themeVideo.src = videoPath;
                        }
                        
                        themeVideo.onerror = function() {
                            if (videoPaths.length > pathIndex + 1) {
                                console.log(`[ThemeSelector] Video error, trying fallback: ${videoPaths[pathIndex + 1]}`);
                                loadVideo(pathIndex + 1);
                            } else {
                                console.warn(`[ThemeSelector] Video failed to load for theme: ${themeName}`);
                            }
                        };
                        
                        themeVideo.onloadeddata = function() {
                            console.log(`[ThemeSelector] Video loaded successfully: ${videoPath}`);
                        };
                        
                        themeVideo.load();
                        if (themeVideoContainer) {
                            themeVideoContainer.style.setProperty('display', 'block', 'important');
                            themeVideoContainer.style.setProperty('visibility', 'visible', 'important');
                            themeVideoContainer.style.setProperty('opacity', '0.18', 'important');
                        }
                        themeVideo.play().catch(e => {
                            console.log(`[ThemeSelector] Video autoplay prevented: ${e.message}`);
                        });
                        console.log(`[ThemeSelector] Loading theme video: ${videoPath}`);
                    } catch (error) {
                        console.error(`[ThemeSelector] Error loading video:`, error);
                        if (videoPaths.length > pathIndex + 1) {
                            loadVideo(pathIndex + 1);
                        }
                    }
                };
                
                loadVideo(0);
            } else {
                console.warn(`[ThemeSelector] No video paths found for theme: ${themeName}`);
            }
        } else {
            console.warn('[ThemeSelector] Theme video element not found');
        }
        
        // Load background image with cache support
        if (themeImage) {
            const imagePaths = themeImages[themeName] || themeImages['matrix'];
            if (imagePaths && imagePaths.length > 0) {
                // Try to load from cache first
                if (useCache) {
                    try {
                        const cached = await window.themeCache.getCachedImage(themeName);
                        if (cached && cached.blobUrl) {
                            console.log(`[ThemeSelector] Using cached image for ${themeName}`);
                            themeImage.style.backgroundImage = `url(${cached.blobUrl})`;
                            themeImage.style.setProperty('display', 'block', 'important');
                            themeImage.style.setProperty('visibility', 'visible', 'important');
                            themeImage.style.setProperty('opacity', '0.15', 'important');
                            return; // Successfully loaded from cache
                        }
                    } catch (error) {
                        console.warn(`[ThemeSelector] Cache error, falling back to network:`, error);
                    }
                }
                
                // Load from network (and cache if available)
                const loadImage = async (pathIndex = 0) => {
                    const imagePath = imagePaths[pathIndex];
                    if (!imagePath) {
                        // Use gradient fallback
                        console.log(`[ThemeSelector] No more image paths, using gradient fallback for theme: ${themeName}`);
                        const gradientFallbacks = {
                            matrix: 'linear-gradient(135deg, #000000 0%, #001100 30%, #003300 50%, #001100 70%, #000000 100%), radial-gradient(ellipse at 50% 50%, rgba(0, 255, 0, 0.1) 0%, transparent 70%)',
                            mtg: 'linear-gradient(135deg, #1a0033 0%, #2d0055 30%, #4a148c 50%, #2d0055 70%, #1a0033 100%), radial-gradient(ellipse at 50% 50%, rgba(255, 107, 107, 0.1) 0%, rgba(255, 217, 61, 0.1) 50%, transparent 70%)',
                            halo4: 'linear-gradient(135deg, #000a1a 0%, #001a33 30%, #003366 50%, #001a33 70%, #000a1a 100%), radial-gradient(ellipse at 50% 50%, rgba(0, 255, 136, 0.1) 0%, transparent 70%)',
                            halo: 'linear-gradient(135deg, #000a1a 0%, #001a33 30%, #003366 50%, #001a33 70%, #000a1a 100%), radial-gradient(ellipse at 50% 50%, rgba(0, 255, 136, 0.1) 0%, transparent 70%)',
                            cyberpunk: 'linear-gradient(135deg, #1a0033 0%, #330066 30%, #6600cc 50%, #330066 70%, #1a0033 100%), radial-gradient(ellipse at 50% 50%, rgba(255, 0, 255, 0.15) 0%, rgba(0, 255, 255, 0.1) 50%, transparent 70%)',
                            nazi_wwii: 'linear-gradient(135deg, #1a0000 0%, #330000 30%, #550000 50%, #330000 70%, #1a0000 100%), radial-gradient(ellipse at 50% 50%, rgba(255, 51, 51, 0.15) 0%, transparent 70%)',
                            'sci-fi': 'linear-gradient(135deg, #000511 0%, #001122 30%, #002244 50%, #001122 70%, #000511 100%), radial-gradient(ellipse at 50% 50%, rgba(0, 170, 255, 0.15) 0%, transparent 70%)',
                            nature: 'linear-gradient(135deg, #001100 0%, #003300 30%, #006600 50%, #003300 70%, #001100 100%), radial-gradient(ellipse at 50% 50%, rgba(0, 255, 128, 0.1) 0%, transparent 70%)'
                        };
                        const fallback = gradientFallbacks[themeName] || gradientFallbacks['matrix'];
                        themeImage.style.background = fallback;
                        themeImage.style.setProperty('display', 'block', 'important');
                        themeImage.style.setProperty('visibility', 'visible', 'important');
                        themeImage.style.setProperty('opacity', '0.15', 'important');
                        return;
                    }
                    
                    try {
                        // Try to download and cache if cache is available
                        let imageUrl = imagePath;
                        if (useCache) {
                            try {
                                const blobUrl = await window.themeCache.downloadAndCacheImage(themeName, imagePath);
                                imageUrl = blobUrl;
                                console.log(`[ThemeSelector] Image downloaded and cached: ${imagePath}`);
                            } catch (cacheError) {
                                // If cache fails, try direct URL
                                console.warn(`[ThemeSelector] Cache download failed, using direct URL:`, cacheError);
                                imageUrl = imagePath;
                            }
                        }
                        
                        const img = new Image();
                        img.onload = function() {
                            themeImage.style.backgroundImage = `url(${imageUrl})`;
                            themeImage.style.setProperty('display', 'block', 'important');
                            themeImage.style.setProperty('visibility', 'visible', 'important');
                            themeImage.style.setProperty('opacity', '0.15', 'important');
                            console.log(`[ThemeSelector] Loaded theme image: ${imagePath}`);
                        };
                        img.onerror = function() {
                            if (imagePaths.length > pathIndex + 1) {
                                console.log(`[ThemeSelector] Image error, trying fallback: ${imagePaths[pathIndex + 1]}`);
                                loadImage(pathIndex + 1);
                            } else {
                        // Use theme-specific gradient fallback
                        console.log(`[ThemeSelector] Using gradient fallback for theme: ${themeName}`);
                        const gradientFallbacks = {
                            matrix: 'linear-gradient(135deg, #000000 0%, #001100 30%, #003300 50%, #001100 70%, #000000 100%), radial-gradient(ellipse at 50% 50%, rgba(0, 255, 0, 0.1) 0%, transparent 70%)',
                            mtg: 'linear-gradient(135deg, #1a0033 0%, #2d0055 30%, #4a148c 50%, #2d0055 70%, #1a0033 100%), radial-gradient(ellipse at 50% 50%, rgba(255, 107, 107, 0.1) 0%, rgba(255, 217, 61, 0.1) 50%, transparent 70%)',
                            halo4: 'linear-gradient(135deg, #000a1a 0%, #001a33 30%, #003366 50%, #001a33 70%, #000a1a 100%), radial-gradient(ellipse at 50% 50%, rgba(0, 255, 136, 0.1) 0%, transparent 70%)',
                            halo: 'linear-gradient(135deg, #000a1a 0%, #001a33 30%, #003366 50%, #001a33 70%, #000a1a 100%), radial-gradient(ellipse at 50% 50%, rgba(0, 255, 136, 0.1) 0%, transparent 70%)',
                            cyberpunk: 'linear-gradient(135deg, #1a0033 0%, #330066 30%, #6600cc 50%, #330066 70%, #1a0033 100%), radial-gradient(ellipse at 50% 50%, rgba(255, 0, 255, 0.15) 0%, rgba(0, 255, 255, 0.1) 50%, transparent 70%)',
                            nazi_wwii: 'linear-gradient(135deg, #1a0000 0%, #330000 30%, #550000 50%, #330000 70%, #1a0000 100%), radial-gradient(ellipse at 50% 50%, rgba(255, 51, 51, 0.15) 0%, transparent 70%)',
                            'sci-fi': 'linear-gradient(135deg, #000511 0%, #001122 30%, #002244 50%, #001122 70%, #000511 100%), radial-gradient(ellipse at 50% 50%, rgba(0, 170, 255, 0.15) 0%, transparent 70%)',
                            nature: 'linear-gradient(135deg, #001100 0%, #003300 30%, #006600 50%, #003300 70%, #001100 100%), radial-gradient(ellipse at 50% 50%, rgba(0, 255, 128, 0.1) 0%, transparent 70%)'
                        };
                        const fallback = gradientFallbacks[themeName] || gradientFallbacks['matrix'];
                        themeImage.style.background = fallback;
                        themeImage.style.setProperty('display', 'block', 'important');
                        themeImage.style.setProperty('visibility', 'visible', 'important');
                        themeImage.style.setProperty('opacity', '0.15', 'important');
                    }
                };
                img.src = imagePaths[0];
            } else {
                // Use gradient fallback if no paths
                console.log(`[ThemeSelector] No image paths found, using gradient for theme: ${themeName}`);
                themeImage.style.background = 'linear-gradient(135deg, #000000 0%, #001100 50%, #000000 100%)';
                themeImage.style.setProperty('display', 'block', 'important');
                themeImage.style.setProperty('visibility', 'visible', 'important');
                themeImage.style.setProperty('opacity', '0.15', 'important');
            }
        } else {
            console.warn('[ThemeSelector] Theme image element not found');
        }
    }
    
    updateThemePreview() {
        const preview = document.getElementById('theme-preview');
        if (!preview || !this.themeConfig) return;
        
        preview.innerHTML = `
            <div class="theme-preview-content">
                <span class="theme-name">${this.themeConfig.name || this.currentTheme}</span>
                ${this.themeConfig.intelligence ? '<span class="theme-badge">Intelligent</span>' : ''}
            </div>
        `;
    }
    
    getSelectedTheme() {
        const themeSelect = document.getElementById('theme-select');
        if (themeSelect && themeSelect.value === 'auto') {
            return this.currentTheme; // Return auto-detected theme
        }
        return themeSelect ? themeSelect.value : 'matrix';
    }
    
    getThemeConfig() {
        return this.themeConfig;
    }
}

// Initialize theme selector
let generatorThemeSelector = null;

// Wait for both DOM and main.js to be ready
function initializeThemeSelector() {
    if (generatorThemeSelector) return; // Already initialized
    
    // Check if required elements exist
    const themeVideo = document.getElementById('theme-video');
    const themeVideoContainer = document.getElementById('theme-background-video');
    const themeImage = document.getElementById('theme-background-image');
    
    if (!themeVideo && !themeVideoContainer && !themeImage) {
        console.warn('[ThemeSelector] Theme elements not found in DOM, retrying...');
        setTimeout(initializeThemeSelector, 100);
        return;
    }
    
    console.log('[ThemeSelector] Creating GeneratorThemeSelector instance...');
    generatorThemeSelector = new GeneratorThemeSelector();
    console.log('[ThemeSelector] Initialized');
    
    // Wait for main.js to load (it uses defer)
    function activateTheme() {
        const savedTheme = localStorage.getItem('documentaryTheme') || 'matrix';
        if (generatorThemeSelector) {
            console.log(`[ThemeSelector] Activating theme: ${savedTheme}`);
            generatorThemeSelector.setTheme(savedTheme);
            console.log(`[ThemeSelector] Theme activated: ${savedTheme}`);
        }
        
        // Make available globally for generator
        window.getGeneratorTheme = () => generatorThemeSelector?.getSelectedTheme() || 'matrix';
        window.getGeneratorThemeConfig = () => generatorThemeSelector?.getThemeConfig() || null;
    }
    
    // Try multiple times to ensure main.js is loaded
    let attempts = 0;
    const maxAttempts = 10;
    const checkMainJS = setInterval(() => {
        attempts++;
        if (typeof window.setTheme === 'function' || attempts >= maxAttempts) {
            clearInterval(checkMainJS);
            activateTheme();
        }
    }, 100);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('[ThemeSelector] DOMContentLoaded fired');
        initializeThemeSelector();
    });
} else {
    // DOM already ready
    console.log('[ThemeSelector] DOM already ready');
    initializeThemeSelector();
}

// Also try after window load (when all scripts including defer are loaded)
window.addEventListener('load', () => {
    console.log('[ThemeSelector] Window load fired');
    if (!generatorThemeSelector) {
        console.log('[ThemeSelector] Initializing on window load');
        initializeThemeSelector();
    } else {
        // Re-apply theme to ensure it's visible
        const currentTheme = generatorThemeSelector.getSelectedTheme() || localStorage.getItem('documentaryTheme') || 'matrix';
        console.log(`[ThemeSelector] Re-applying theme on window load: ${currentTheme}`);
        generatorThemeSelector.setTheme(currentTheme);
    }
});

