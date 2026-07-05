/**
 * Image Support System
 * Provides image loading, lazy loading, and placeholder management for all pages
 */
class ImageSupport {
    constructor() {
        this.imageCache = new Map();
        this.lazyLoadObserver = null;
        this.init();
    }

    init() {
        // Initialize lazy loading observer
        if ('IntersectionObserver' in window) {
            this.lazyLoadObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        this.loadImage(entry.target);
                        this.lazyLoadObserver.unobserve(entry.target);
                    }
                });
            }, {
                rootMargin: '50px'
            });
        }

        // Load all images with data-src attribute (lazy loading)
        document.querySelectorAll('img[data-src]').forEach(img => {
            if (this.lazyLoadObserver) {
                this.lazyLoadObserver.observe(img);
            } else {
                this.loadImage(img);
            }
        });

        // Handle broken images
        document.querySelectorAll('img').forEach(img => {
            img.addEventListener('error', (e) => this.handleImageError(e.target));
        });
    }

    loadImage(imgElement) {
        const src = imgElement.getAttribute('data-src');
        if (!src) return;

        // Check cache
        if (this.imageCache.has(src)) {
            imgElement.src = this.imageCache.get(src);
            imgElement.classList.add('loaded');
            return;
        }

        // Create new image to preload
        const img = new Image();
        img.onload = () => {
            imgElement.src = src;
            imgElement.classList.add('loaded');
            this.imageCache.set(src, src);
        };
        img.onerror = () => {
            this.handleImageError(imgElement);
        };
        img.src = src;
    }

    handleImageError(imgElement) {
        // Use placeholder or default image
        const placeholder = imgElement.getAttribute('data-placeholder') || 
                           '/static/img/placeholder.png';
        imgElement.src = placeholder;
        imgElement.classList.add('error');
        imgElement.alt = 'Image not available';
    }

    // Preload images
    preloadImages(urls) {
        urls.forEach(url => {
            if (!this.imageCache.has(url)) {
            const img = new Image();
            img.onload = () => this.imageCache.set(url, url);
            img.src = url;
            }
        });
    }

    // Get page-specific images (only set when assets exist to avoid 404s)
    getPageImages(pagePath) {
        // No page images deployed under static/img/pages/ - return empty to avoid 404s.
        // When you add e.g. profile-bg.jpg, add: '/profile': { background: '/static/img/pages/profile-bg.jpg' }
        return { header: null, background: null };
    }

    // Apply page images
    applyPageImages(pagePath) {
        const images = this.getPageImages(pagePath);
        if (!images || (!images.header && !images.background)) return;

        // Apply header image
        if (images.header) {
            const headerImg = document.querySelector('.page-header img, header img, .header-image');
            if (headerImg) {
                headerImg.setAttribute('data-src', images.header);
                this.loadImage(headerImg);
            }
        }

        // Apply background image
        if (images.background) {
            document.body.style.backgroundImage = `url('${images.background}')`;
            document.body.style.backgroundSize = 'cover';
            document.body.style.backgroundPosition = 'center';
            document.body.style.backgroundAttachment = 'fixed';
        }
    }
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.imageSupport = new ImageSupport();
        // Apply page images based on current path
        window.imageSupport.applyPageImages(window.location.pathname);
    });
} else {
    window.imageSupport = new ImageSupport();
    window.imageSupport.applyPageImages(window.location.pathname);
}
