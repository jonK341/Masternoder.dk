/**
 * Custom Video Player Component
 * Features: Custom controls, playback speed, quality selection
 */

class CustomVideoPlayer {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container with id "${containerId}" not found`);
            return;
        }
        
        this.options = {
            autoplay: options.autoplay || false,
            controls: options.controls !== false,
            playbackSpeeds: options.playbackSpeeds || [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2],
            defaultSpeed: options.defaultSpeed || 1,
            showQualitySelector: options.showQualitySelector !== false,
            ...options
        };
        
        this.video = null;
        this.currentSpeed = this.options.defaultSpeed;
        this.isPlaying = false;
        this.isFullscreen = false;
        
        this.init();
    }
    
    init() {
        // Create video element
        this.video = document.createElement('video');
        this.video.className = 'custom-video-player';
        this.video.preload = 'metadata';
        
        if (this.options.autoplay) {
            this.video.autoplay = true;
        }
        
        // Create controls container
        const controlsContainer = document.createElement('div');
        controlsContainer.className = 'custom-video-controls-container';
        
        // Create custom controls
        const controls = this.createControls();
        controlsContainer.appendChild(controls);
        
        // Create wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'custom-video-wrapper';
        wrapper.appendChild(this.video);
        wrapper.appendChild(controlsContainer);
        
        this.container.appendChild(wrapper);
        
        // Setup event listeners
        this.setupEventListeners();
    }
    
    createControls() {
        const controls = document.createElement('div');
        controls.className = 'custom-video-controls';
        
        // Play/Pause button
        const playPauseBtn = document.createElement('button');
        playPauseBtn.className = 'control-btn play-pause-btn';
        playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
        playPauseBtn.title = 'Play/Pause';
        playPauseBtn.addEventListener('click', () => this.togglePlayPause());
        
        // Progress bar
        const progressContainer = document.createElement('div');
        progressContainer.className = 'progress-container';
        
        const progressBar = document.createElement('div');
        progressBar.className = 'progress-bar';
        
        const progressFill = document.createElement('div');
        progressFill.className = 'progress-fill';
        progressFill.id = 'video-progress-fill';
        
        const progressHandle = document.createElement('div');
        progressHandle.className = 'progress-handle';
        progressHandle.id = 'video-progress-handle';
        
        progressBar.appendChild(progressFill);
        progressBar.appendChild(progressHandle);
        progressContainer.appendChild(progressBar);
        
        // Time display
        const timeDisplay = document.createElement('div');
        timeDisplay.className = 'time-display';
        timeDisplay.innerHTML = '<span id="current-time">0:00</span> / <span id="total-time">0:00</span>';
        
        // Volume control
        const volumeContainer = document.createElement('div');
        volumeContainer.className = 'volume-container';
        
        const volumeBtn = document.createElement('button');
        volumeBtn.className = 'control-btn volume-btn';
        volumeBtn.innerHTML = '<i class="fas fa-volume-up"></i>';
        volumeBtn.title = 'Mute/Unmute';
        volumeBtn.addEventListener('click', () => this.toggleMute());
        
        const volumeSlider = document.createElement('input');
        volumeSlider.type = 'range';
        volumeSlider.className = 'volume-slider';
        volumeSlider.min = '0';
        volumeSlider.max = '100';
        volumeSlider.value = '100';
        volumeSlider.title = 'Volume';
        volumeSlider.addEventListener('input', (e) => this.setVolume(e.target.value / 100));
        
        volumeContainer.appendChild(volumeBtn);
        volumeContainer.appendChild(volumeSlider);
        
        // Playback speed selector
        const speedContainer = document.createElement('div');
        speedContainer.className = 'speed-container';
        
        const speedLabel = document.createElement('span');
        speedLabel.textContent = 'Speed:';
        speedLabel.className = 'speed-label';
        
        const speedSelect = document.createElement('select');
        speedSelect.className = 'speed-select';
        speedSelect.title = 'Playback Speed';
        this.options.playbackSpeeds.forEach(speed => {
            const option = document.createElement('option');
            option.value = speed;
            option.textContent = speed === 1 ? 'Normal' : speed + 'x';
            if (speed === this.currentSpeed) option.selected = true;
            speedSelect.appendChild(option);
        });
        speedSelect.addEventListener('change', (e) => this.setPlaybackSpeed(parseFloat(e.target.value)));
        
        speedContainer.appendChild(speedLabel);
        speedContainer.appendChild(speedSelect);
        
        // Fullscreen button
        const fullscreenBtn = document.createElement('button');
        fullscreenBtn.className = 'control-btn fullscreen-btn';
        fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i>';
        fullscreenBtn.title = 'Fullscreen';
        fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());
        
        // Assemble controls
        controls.appendChild(playPauseBtn);
        controls.appendChild(progressContainer);
        controls.appendChild(timeDisplay);
        controls.appendChild(volumeContainer);
        controls.appendChild(speedContainer);
        controls.appendChild(fullscreenBtn);
        
        return controls;
    }
    
    setupEventListeners() {
        // Video events
        this.video.addEventListener('loadedmetadata', () => {
            this.updateTotalTime();
            this.updateProgress();
        });
        
        this.video.addEventListener('timeupdate', () => {
            this.updateProgress();
            this.updateCurrentTime();
        });
        
        this.video.addEventListener('play', () => {
            this.isPlaying = true;
            this.updatePlayPauseButton();
        });
        
        this.video.addEventListener('pause', () => {
            this.isPlaying = false;
            this.updatePlayPauseButton();
        });
        
        this.video.addEventListener('ended', () => {
            this.isPlaying = false;
            this.updatePlayPauseButton();
        });
        
        this.video.addEventListener('volumechange', () => {
            this.updateVolumeButton();
        });
        
        // Progress bar interaction
        const progressBar = this.container.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.addEventListener('click', (e) => {
                const rect = progressBar.getBoundingClientRect();
                const percent = (e.clientX - rect.left) / rect.width;
                this.seek(percent);
            });
            
            // Drag handle
            const handle = this.container.querySelector('.progress-handle');
            if (handle) {
                let isDragging = false;
                
                handle.addEventListener('mousedown', (e) => {
                    isDragging = true;
                    e.preventDefault();
                });
                
                document.addEventListener('mousemove', (e) => {
                    if (isDragging && progressBar) {
                        const rect = progressBar.getBoundingClientRect();
                        const percent = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
                        this.seek(percent);
                    }
                });
                
                document.addEventListener('mouseup', () => {
                    isDragging = false;
                });
            }
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (this.container.contains(document.activeElement) || this.isPlaying) {
                switch(e.key) {
                    case ' ':
                        e.preventDefault();
                        this.togglePlayPause();
                        break;
                    case 'ArrowLeft':
                        e.preventDefault();
                        this.seekRelative(-10);
                        break;
                    case 'ArrowRight':
                        e.preventDefault();
                        this.seekRelative(10);
                        break;
                    case 'ArrowUp':
                        e.preventDefault();
                        this.setVolume(Math.min(1, this.video.volume + 0.1));
                        break;
                    case 'ArrowDown':
                        e.preventDefault();
                        this.setVolume(Math.max(0, this.video.volume - 0.1));
                        break;
                    case 'f':
                    case 'F':
                        e.preventDefault();
                        this.toggleFullscreen();
                        break;
                }
            }
        });
    }
    
    setSource(src) {
        this.video.src = src;
        this.video.load();
    }
    
    togglePlayPause() {
        if (this.isPlaying) {
            this.video.pause();
        } else {
            this.video.play();
        }
    }
    
    seek(percent) {
        if (this.video.duration) {
            this.video.currentTime = percent * this.video.duration;
        }
    }
    
    seekRelative(seconds) {
        this.video.currentTime = Math.max(0, Math.min(this.video.duration, this.video.currentTime + seconds));
    }
    
    setVolume(volume) {
        this.video.volume = Math.max(0, Math.min(1, volume));
        const slider = this.container.querySelector('.volume-slider');
        if (slider) {
            slider.value = volume * 100;
        }
    }
    
    toggleMute() {
        this.video.muted = !this.video.muted;
    }
    
    setPlaybackSpeed(speed) {
        this.currentSpeed = speed;
        this.video.playbackRate = speed;
    }
    
    toggleFullscreen() {
        const wrapper = this.container.querySelector('.custom-video-wrapper');
        if (!wrapper) return;
        
        if (!this.isFullscreen) {
            if (wrapper.requestFullscreen) {
                wrapper.requestFullscreen();
            } else if (wrapper.webkitRequestFullscreen) {
                wrapper.webkitRequestFullscreen();
            } else if (wrapper.mozRequestFullScreen) {
                wrapper.mozRequestFullScreen();
            } else if (wrapper.msRequestFullscreen) {
                wrapper.msRequestFullscreen();
            }
        } else {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            } else if (document.mozCancelFullScreen) {
                document.mozCancelFullScreen();
            } else if (document.msExitFullscreen) {
                document.msExitFullscreen();
            }
        }
        
        // Listen for fullscreen changes
        document.addEventListener('fullscreenchange', () => {
            this.isFullscreen = !!document.fullscreenElement;
            this.updateFullscreenButton();
        });
        document.addEventListener('webkitfullscreenchange', () => {
            this.isFullscreen = !!document.webkitFullscreenElement;
            this.updateFullscreenButton();
        });
    }
    
    updatePlayPauseButton() {
        const btn = this.container.querySelector('.play-pause-btn');
        if (btn) {
            btn.innerHTML = this.isPlaying ? '<i class="fas fa-pause"></i>' : '<i class="fas fa-play"></i>';
        }
    }
    
    updateVolumeButton() {
        const btn = this.container.querySelector('.volume-btn');
        if (btn) {
            if (this.video.muted || this.video.volume === 0) {
                btn.innerHTML = '<i class="fas fa-volume-mute"></i>';
            } else if (this.video.volume < 0.5) {
                btn.innerHTML = '<i class="fas fa-volume-down"></i>';
            } else {
                btn.innerHTML = '<i class="fas fa-volume-up"></i>';
            }
        }
    }
    
    updateFullscreenButton() {
        const btn = this.container.querySelector('.fullscreen-btn');
        if (btn) {
            btn.innerHTML = this.isFullscreen ? '<i class="fas fa-compress"></i>' : '<i class="fas fa-expand"></i>';
        }
    }
    
    updateProgress() {
        if (!this.video.duration) return;
        
        const percent = (this.video.currentTime / this.video.duration) * 100;
        const fill = this.container.querySelector('.progress-fill');
        const handle = this.container.querySelector('.progress-handle');
        
        if (fill) {
            fill.style.width = percent + '%';
        }
        if (handle) {
            handle.style.left = percent + '%';
        }
    }
    
    updateCurrentTime() {
        const currentTimeEl = this.container.querySelector('#current-time');
        if (currentTimeEl) {
            currentTimeEl.textContent = this.formatTime(this.video.currentTime);
        }
    }
    
    updateTotalTime() {
        const totalTimeEl = this.container.querySelector('#total-time');
        if (totalTimeEl) {
            totalTimeEl.textContent = this.formatTime(this.video.duration);
        }
    }
    
    formatTime(seconds) {
        if (!seconds || isNaN(seconds)) return '0:00';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
    
    destroy() {
        if (this.video) {
            this.video.pause();
            this.video.src = '';
            this.video.load();
        }
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CustomVideoPlayer;
}

