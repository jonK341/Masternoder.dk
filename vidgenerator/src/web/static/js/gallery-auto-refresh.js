/**
 * Gallery Auto-Refresh System
 * Automatically refreshes gallery when new videos are generated
 */
class GalleryAutoRefresh {
    constructor() {
        this.refreshInterval = null;
        this.refreshIntervalMs = 30000; // 30 seconds
        this.isRefreshing = false;
        this.lastVideoCount = 0;
        this.lastUpdateTime = null;
    }

    init() {
        console.log('[GalleryAutoRefresh] Initializing auto-refresh system...');
        
        // Start auto-refresh
        this.startAutoRefresh();
        
        // Listen for visibility changes (refresh when tab becomes visible)
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                console.log('[GalleryAutoRefresh] Tab visible, refreshing...');
                this.refreshGallery();
            }
        });
        
        // Listen for focus events
        window.addEventListener('focus', () => {
            console.log('[GalleryAutoRefresh] Window focused, refreshing...');
            this.refreshGallery();
        });
        
        // Listen for custom events from generator
        window.addEventListener('generationCompleted', () => {
            console.log('[GalleryAutoRefresh] Generation completed event received, refreshing...');
            setTimeout(() => this.refreshGallery(), 2000); // Wait 2 seconds for video to be saved
        });
        
        console.log('[GalleryAutoRefresh] Auto-refresh system initialized');
    }

    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        this.refreshInterval = setInterval(() => {
            if (!document.hidden && !this.isRefreshing) {
                this.refreshGallery();
            }
        }, this.refreshIntervalMs);
        
        console.log(`[GalleryAutoRefresh] Auto-refresh started (${this.refreshIntervalMs}ms interval)`);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
            console.log('[GalleryAutoRefresh] Auto-refresh stopped');
        }
    }

    async refreshGallery(showNotification = false) {
        if (this.isRefreshing) {
            console.log('[GalleryAutoRefresh] Already refreshing, skipping...');
            return;
        }

        this.isRefreshing = true;
        console.log('[GalleryAutoRefresh] Refreshing gallery...');

        try {
            // Get current page from gallery grid
            const galleryGrid = document.getElementById('gallery-grid');
            const currentPage = galleryGrid ? parseInt(galleryGrid.dataset.page || '1') : 1;
            
            // Get current filters
            const urlParams = new URLSearchParams(window.location.search);
            const statusFilter = urlParams.get('status') || 'all';
            const sortBy = urlParams.get('sort') || 'newest';
            const searchQuery = urlParams.get('search') || '';

            // Fetch updated gallery data
            const apiUrl = `/vidgenerator/api/gallery?page=${currentPage}&per_page=12&status=${statusFilter}&sort=${sortBy}${searchQuery ? '&search=' + encodeURIComponent(searchQuery) : ''}`;
            
            const response = await fetch(apiUrl);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            
            if (data.success && data.documentaries) {
                const newVideoCount = data.pagination.total;
                
                // Check if new videos were added
                if (newVideoCount > this.lastVideoCount && this.lastVideoCount > 0) {
                    const newVideos = newVideoCount - this.lastVideoCount;
                    console.log(`[GalleryAutoRefresh] ${newVideos} new video(s) detected!`);
                    
                    if (showNotification) {
                        this.showNotification(`${newVideos} new video(s) added!`);
                    }
                    
                    // Reload the page to show new videos
                    window.location.reload();
                } else {
                    // Update gallery grid without full reload
                    this.updateGalleryGrid(data.documentaries);
                }
                
                this.lastVideoCount = newVideoCount;
                this.lastUpdateTime = new Date();
            }
        } catch (error) {
            console.error('[GalleryAutoRefresh] Error refreshing gallery:', error);
        } finally {
            this.isRefreshing = false;
        }
    }

    updateGalleryGrid(documentaries) {
        const galleryGrid = document.getElementById('gallery-grid');
        if (!galleryGrid) return;

        // Update gallery items
        const existingItems = galleryGrid.querySelectorAll('.gallery-item');
        const existingIds = new Set(Array.from(existingItems).map(item => item.dataset.id));

        // Add new items
        documentaries.forEach(doc => {
            if (!existingIds.has(doc.id)) {
                const item = this.createGalleryItem(doc);
                galleryGrid.insertBefore(item, galleryGrid.firstChild);
            }
        });

        // Update status badges for generating items
        existingItems.forEach(item => {
            const docId = item.dataset.id;
            const doc = documentaries.find(d => d.id === docId);
            if (doc) {
                const statusBadge = item.querySelector('.status-badge');
                if (statusBadge && statusBadge.textContent.trim() !== doc.status) {
                    statusBadge.className = `status-badge status-${doc.status}`;
                    statusBadge.textContent = doc.status.charAt(0).toUpperCase() + doc.status.slice(1);
                    
                    // If status changed to completed, reload to show video
                    if (doc.status === 'completed' && item.dataset.status !== 'completed') {
                        setTimeout(() => window.location.reload(), 1000);
                    }
                }
            }
        });
    }

    createGalleryItem(doc) {
        const item = document.createElement('div');
        item.className = 'gallery-item';
        item.dataset.id = doc.id;
        item.dataset.status = doc.status;
        item.dataset.title = doc.title.toLowerCase();
        
        const createdDate = doc.created_at ? new Date(doc.created_at).toISOString().split('T')[0] : 'N/A';
        const duration = doc.duration ? `${Math.floor(doc.duration / 60)}m ${doc.duration % 60}s` : '';
        
        item.innerHTML = `
            <a href="/vidgenerator/documentary/${doc.id}" class="doc-link">
                <div class="doc-thumbnail">
                    <div class="placeholder-thumbnail" style="display: flex;">
                        <span class="thumbnail-icon">🎬</span>
                    </div>
                    ${doc.status === 'generating' ? `
                        <div class="generating-overlay">
                            <div class="spinner"></div>
                            <span>Generating...</span>
                        </div>
                    ` : ''}
                    <div class="status-badge status-${doc.status}">
                        ${doc.status.charAt(0).toUpperCase() + doc.status.slice(1)}
                    </div>
                    ${duration ? `
                        <div class="duration-badge">
                            ⏱️ ${Math.floor(doc.duration / 60)}m
                        </div>
                    ` : ''}
                </div>
                <div class="doc-info">
                    <h3 class="doc-title">${doc.title}</h3>
                    <p class="doc-description">${(doc.prompt || '').substring(0, 80)}${(doc.prompt || '').length > 80 ? '...' : ''}</p>
                    <div class="doc-meta">
                        <span class="meta-item">📅 ${createdDate}</span>
                        ${duration ? `<span class="meta-item">⏱️ ${duration}</span>` : ''}
                    </div>
                </div>
            </a>
        `;
        
        return item;
    }

    showNotification(message) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'gallery-refresh-notification';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0, 200, 255, 0.9);
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        const galleryRefresh = new GalleryAutoRefresh();
        galleryRefresh.init();
        window.galleryAutoRefresh = galleryRefresh; // Make it accessible globally
    });
} else {
    const galleryRefresh = new GalleryAutoRefresh();
    galleryRefresh.init();
    window.galleryAutoRefresh = galleryRefresh;
}

