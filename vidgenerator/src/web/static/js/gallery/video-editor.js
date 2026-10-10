/**
 * Video Editor for Gallery
 * Allows editing of video clips directly from the gallery
 */
class VideoEditor {
    constructor() {
        this.currentClip = null;
        this.editorContainer = null;
        this.isEditing = false;
    }

    /**
     * Initialize video editor
     */
    init() {
        console.log('[VideoEditor] Initialized');
        this.createEditorUI();
        this.attachEventListeners();
    }

    /**
     * Create editor UI elements
     */
    createEditorUI() {
        // Create editor modal/panel
        const editorHTML = `
            <div id="video-editor-modal" class="video-editor-modal" style="display: none;">
                <div class="video-editor-content">
                    <div class="video-editor-header">
                        <h2>🎬 Video Editor</h2>
                        <button class="editor-close-btn" id="editor-close-btn">×</button>
                    </div>
                    <div class="video-editor-body">
                        <div class="editor-video-preview">
                            <video id="editor-video-player" controls></video>
                        </div>
                        <div class="editor-controls">
                            <div class="editor-section">
                                <h3>Clip Information</h3>
                                <div class="info-item">
                                    <label>Title:</label>
                                    <input type="text" id="editor-clip-title" placeholder="Clip title">
                                </div>
                                <div class="info-item">
                                    <label>Duration:</label>
                                    <span id="editor-clip-duration">0s</span>
                                </div>
                                <div class="info-item">
                                    <label>Quality Score:</label>
                                    <span id="editor-clip-quality">0.0</span>
                                </div>
                            </div>
                            <div class="editor-section">
                                <h3>Edit Options</h3>
                                <button class="editor-btn" id="editor-trim-btn">✂️ Trim Clip</button>
                                <button class="editor-btn" id="editor-enhance-btn">✨ Enhance Quality</button>
                                <button class="editor-btn" id="editor-separate-btn">🔀 Separate Audio/Video</button>
                                <button class="editor-btn" id="editor-subtitle-btn">📝 Add Subtitles</button>
                            </div>
                            <div class="editor-section">
                                <h3>AI Editing</h3>
                                <select id="editor-strategy-select">
                                    <option value="quality">Quality Enhancement</option>
                                    <option value="speed">Speed Optimization</option>
                                    <option value="creative">Creative Enhancement</option>
                                    <option value="balanced">Balanced</option>
                                    <option value="custom">Custom</option>
                                </select>
                                <button class="editor-btn primary" id="editor-ai-edit-btn">🤖 Apply AI Edit</button>
                            </div>
                        </div>
                        <div class="editor-actions">
                            <button class="editor-btn cancel" id="editor-cancel-btn">Cancel</button>
                            <button class="editor-btn save" id="editor-save-btn">💾 Save Changes</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Append to body
        document.body.insertAdjacentHTML('beforeend', editorHTML);
        this.editorContainer = document.getElementById('video-editor-modal');
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Close button
        document.getElementById('editor-close-btn').addEventListener('click', () => this.close());
        document.getElementById('editor-cancel-btn').addEventListener('click', () => this.close());

        // Save button
        document.getElementById('editor-save-btn').addEventListener('click', () => this.saveChanges());

        // Edit buttons
        document.getElementById('editor-trim-btn').addEventListener('click', () => this.trimClip());
        document.getElementById('editor-enhance-btn').addEventListener('click', () => this.enhanceQuality());
        document.getElementById('editor-separate-btn').addEventListener('click', () => this.separateAudioVideo());
        document.getElementById('editor-subtitle-btn').addEventListener('click', () => this.addSubtitles());
        document.getElementById('editor-ai-edit-btn').addEventListener('click', () => this.applyAIEdit());

        // Close on outside click
        this.editorContainer.addEventListener('click', (e) => {
            if (e.target === this.editorContainer) {
                this.close();
            }
        });
    }

    /**
     * Open editor for a clip
     */
    async openEditor(clipId, clipData) {
        console.log('[VideoEditor] Opening editor for clip:', clipId);
        this.currentClip = { id: clipId, ...clipData };
        this.isEditing = true;

        // Load clip data
        await this.loadClipData(clipData);

        // Show editor
        this.editorContainer.style.display = 'flex';
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
    }

    /**
     * Load clip data into editor
     */
    async loadClipData(clipData) {
        const videoPlayer = document.getElementById('editor-video-player');
        const titleInput = document.getElementById('editor-clip-title');
        const durationSpan = document.getElementById('editor-clip-duration');
        const qualitySpan = document.getElementById('editor-clip-quality');

        // Set video source
        if (clipData.video_path) {
            videoPlayer.src = clipData.video_path;
        } else if (clipData.clip_path) {
            videoPlayer.src = clipData.clip_path;
        }

        // Set metadata
        titleInput.value = clipData.title || '';
        durationSpan.textContent = `${clipData.duration || 0}s`;
        qualitySpan.textContent = (clipData.quality_score || 0.0).toFixed(2);

        // Wait for video metadata
        videoPlayer.addEventListener('loadedmetadata', () => {
            durationSpan.textContent = `${Math.round(videoPlayer.duration)}s`;
        }, { once: true });
    }

    /**
     * Close editor
     */
    close() {
        this.editorContainer.style.display = 'none';
        document.body.style.overflow = '';
        this.isEditing = false;
        this.currentClip = null;
    }

    /**
     * Trim clip
     */
    async trimClip() {
        console.log('[VideoEditor] Trim clip');
        // TODO: Implement trim functionality
        alert('Trim functionality coming soon!');
    }

    /**
     * Enhance quality
     */
    async enhanceQuality() {
        console.log('[VideoEditor] Enhance quality');
        // TODO: Implement quality enhancement
        alert('Quality enhancement coming soon!');
    }

    /**
     * Separate audio/video
     */
    async separateAudioVideo() {
        console.log('[VideoEditor] Separate audio/video');
        if (!this.currentClip) return;

        try {
            const response = await fetch(`/vidgenerator/api/clip/${this.currentClip.id}/separate`, {
                method: 'POST'
            });

            if (response.ok) {
                const result = await response.json();
                console.log('[VideoEditor] Separation result:', result);
                alert('Audio and video separated successfully!');
                // Reload clip data
                await this.loadClipData(result);
            } else {
                alert('Failed to separate audio/video');
            }
        } catch (error) {
            console.error('[VideoEditor] Separation error:', error);
            alert('Error separating audio/video');
        }
    }

    /**
     * Add subtitles
     */
    async addSubtitles() {
        console.log('[VideoEditor] Add subtitles');
        // TODO: Implement subtitle addition
        alert('Subtitle functionality coming soon!');
    }

    /**
     * Apply AI edit
     */
    async applyAIEdit() {
        if (!this.currentClip) return;

        const strategy = document.getElementById('editor-strategy-select').value;
        console.log('[VideoEditor] Apply AI edit with strategy:', strategy);

        try {
            const response = await fetch(`/vidgenerator/api/clip/${this.currentClip.id}/ai-edit`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    strategy: strategy
                })
            });

            if (response.ok) {
                const result = await response.json();
                console.log('[VideoEditor] AI edit result:', result);
                alert(`AI edit applied successfully! Quality improved by ${result.quality_improvement || 0}%`);
                // Reload clip data
                await this.loadClipData(result.clip);
            } else {
                alert('Failed to apply AI edit');
            }
        } catch (error) {
            console.error('[VideoEditor] AI edit error:', error);
            alert('Error applying AI edit');
        }
    }

    /**
     * Save changes
     */
    async saveChanges() {
        if (!this.currentClip) return;

        const title = document.getElementById('editor-clip-title').value;

        try {
            const response = await fetch(`/vidgenerator/api/clip/${this.currentClip.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: title,
                    // Add other fields as needed
                })
            });

            if (response.ok) {
                alert('Changes saved successfully!');
                this.close();
                // Refresh gallery if needed
                if (window.galleryRefresh) {
                    window.galleryRefresh();
                }
            } else {
                alert('Failed to save changes');
            }
        } catch (error) {
            console.error('[VideoEditor] Save error:', error);
            alert('Error saving changes');
        }
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.videoEditor = new VideoEditor();
        window.videoEditor.init();
        attachEditButtons();
    });
} else {
    window.videoEditor = new VideoEditor();
    window.videoEditor.init();
    attachEditButtons();
}

// Attach edit buttons to gallery items
function attachEditButtons() {
    document.querySelectorAll('.edit-clip-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            const docId = btn.dataset.docId;
            // For now, open editor with documentary data
            // In future, fetch clips for this documentary
            try {
                const response = await fetch(`/vidgenerator/api/gallery?search=${docId}`);
                const data = await response.json();
                if (data.success && data.documentaries.length > 0) {
                    const doc = data.documentaries[0];
                    // Open editor (will be enhanced to show clips)
                    window.videoEditor.openEditor(docId, {
                        title: doc.title,
                        video_path: doc.video_path,
                        duration: doc.duration
                    });
                }
            } catch (error) {
                console.error('Error loading documentary:', error);
            }
        });
    });
}

