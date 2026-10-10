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
                           '/vidgenerator/static/img/placeholder.png';
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

    // Get page-specific images
    getPageImages(pagePath) {
        const pageImages = {
            '/vidgenerator/': {
                header: '/vidgenerator/static/img/pages/home-header.jpg',
                background: '/vidgenerator/static/img/pages/home-bg.jpg'
            },
            '/vidgenerator/battle': {
                header: '/vidgenerator/static/img/pages/battle-header.jpg',
                background: '/vidgenerator/static/img/pages/battle-bg.jpg'
            },
            '/vidgenerator/game': {
                header: '/vidgenerator/static/img/pages/game-header.jpg',
                background: '/vidgenerator/static/img/pages/game-bg.jpg'
            },
            '/vidgenerator/profile': {
                header: '/vidgenerator/static/img/pages/profile-header.jpg',
                background: '/vidgenerator/static/img/pages/profile-bg.jpg'
            },
            '/vidgenerator/shop': {
                header: '/vidgenerator/static/img/pages/shop-header.jpg',
                background: '/vidgenerator/static/img/pages/shop-bg.jpg'
            },
            '/vidgenerator/gallery': {
                header: '/vidgenerator/static/img/pages/gallery-header.jpg',
                background: '/vidgenerator/static/img/pages/gallery-bg.jpg'
            }
        };

        return pageImages[pagePath] || {
            header: '/vidgenerator/static/img/pages/default-header.jpg',
            background: '/vidgenerator/static/img/pages/default-bg.jpg'
        };
    }

    // Apply page images
    applyPageImages(pagePath) {
        const images = this.getPageImages(pagePath);
        
        // Apply header image
        const headerImg = document.querySelector('.page-header img, header img, .header-image');
        if (headerImg) {
            headerImg.setAttribute('data-src', images.header);
            this.loadImage(headerImg);
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
