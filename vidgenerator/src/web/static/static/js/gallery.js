// Enhanced Gallery JavaScript - Advanced Search, Local Caching, Accessibility

(function() {
    'use strict';
    
    // Local storage cache for gallery data
    const CACHE_KEY = 'gallery_cache';
    const CACHE_EXPIRY = 5 * 60 * 1000; // 5 minutes
    
    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function() {
        initGallery();
    });
    
    function initGallery() {
        // Initialize search functionality
        initAdvancedSearch();
        
        // Auto-refresh generating items
        initAutoRefresh();
        
        // Initialize local caching
        initLocalCache();
        
        // Initialize accessibility features
        initAccessibility();
        
        // Initialize lazy loading
        initLazyLoading();
    }
    
    function initAdvancedSearch() {
        const searchInput = document.getElementById('gallery-search-input');
        const searchForm = document.getElementById('gallery-search-form');
        const clearBtn = document.getElementById('search-clear-btn');
        const suggestions = document.getElementById('search-suggestions');
        
        if (!searchInput) return;
        
        // Show/hide clear button
        searchInput.addEventListener('input', function() {
            if (this.value.length > 0) {
                clearBtn.style.display = 'block';
            } else {
                clearBtn.style.display = 'none';
                if (suggestions) suggestions.style.display = 'none';
            }
        });
        
        // Clear search
        if (clearBtn) {
            clearBtn.addEventListener('click', function() {
                searchInput.value = '';
                clearBtn.style.display = 'none';
                if (suggestions) suggestions.style.display = 'none';
                searchInput.focus();
                // Trigger search with empty query
                if (searchForm) searchForm.submit();
            });
        }
        
        // Real-time search suggestions (client-side filtering)
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.toLowerCase().trim();
            
            if (query.length < 2) {
                if (suggestions) suggestions.style.display = 'none';
                return;
            }
            
            searchTimeout = setTimeout(() => {
                showSearchSuggestions(query);
            }, 300);
        });
        
        // Keyboard navigation for suggestions
        searchInput.addEventListener('keydown', function(e) {
            if (!suggestions || suggestions.style.display === 'none') return;
            
            const items = suggestions.querySelectorAll('.suggestion-item');
            const current = suggestions.querySelector('.suggestion-item.active');
            let index = Array.from(items).indexOf(current);
            
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                index = (index + 1) % items.length;
                items[index].classList.add('active');
                if (current) current.classList.remove('active');
                items[index].scrollIntoView({ block: 'nearest' });
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                index = index <= 0 ? items.length - 1 : index - 1;
                items[index].classList.add('active');
                if (current) current.classList.remove('active');
                items[index].scrollIntoView({ block: 'nearest' });
            } else if (e.key === 'Enter' && current) {
                e.preventDefault();
                current.click();
            } else if (e.key === 'Escape') {
                suggestions.style.display = 'none';
                searchInput.focus();
            }
        });
        
        // Close suggestions when clicking outside
        document.addEventListener('click', function(e) {
            if (suggestions && !suggestions.contains(e.target) && e.target !== searchInput) {
                suggestions.style.display = 'none';
            }
        });
    }
    
    function showSearchSuggestions(query) {
        const suggestions = document.getElementById('search-suggestions');
        if (!suggestions) return;
        
        const items = document.querySelectorAll('.gallery-item');
        const matches = [];
        
        items.forEach(item => {
            const title = (item.dataset.title || '').toLowerCase();
            const prompt = (item.dataset.prompt || '').toLowerCase();
            const description = (item.dataset.description || '').toLowerCase();
            
            if (title.includes(query) || prompt.includes(query) || description.includes(query)) {
                const titleText = item.querySelector('.doc-title')?.textContent || '';
                matches.push({
                    title: titleText,
                    id: item.dataset.id
                });
            }
        });
        
        if (matches.length === 0) {
            suggestions.style.display = 'none';
            return;
        }
        
        // Show top 5 matches
        suggestions.innerHTML = matches.slice(0, 5).map(match => 
            `<div class="suggestion-item" data-id="${match.id}" tabindex="0">
                ${escapeHtml(match.title)}
            </div>`
        ).join('');
        
        // Add click handlers
        suggestions.querySelectorAll('.suggestion-item').forEach(item => {
            item.addEventListener('click', function() {
                const docId = this.dataset.id;
                window.location.href = `/?watch=${docId}`;
            });
        });
        
        suggestions.style.display = 'block';
    }
    
    function initAutoRefresh() {
        const generatingItems = document.querySelectorAll('.gallery-item[data-status="generating"]');
        
        if (generatingItems.length > 0) {
            // Refresh page every 10 seconds if there are generating items
            setTimeout(() => {
                // Only refresh if still on gallery page and items are still generating
                const stillGenerating = document.querySelectorAll('.gallery-item[data-status="generating"]');
                if (stillGenerating.length > 0 && window.location.pathname.includes('/gallery')) {
                    location.reload();
                }
            }, 10000);
        }
    }
    
    function initLocalCache() {
        // Save current gallery state to local storage
        try {
            const galleryData = {
                timestamp: Date.now(),
                items: Array.from(document.querySelectorAll('.gallery-item')).map(item => ({
                    id: item.dataset.id,
                    title: item.dataset.title,
                    status: item.dataset.status,
                    prompt: item.dataset.prompt
                }))
            };
            
            localStorage.setItem(CACHE_KEY, JSON.stringify(galleryData));
        } catch (e) {
            console.warn('Could not save to local storage:', e);
        }
    }
    
    function getCachedData() {
        try {
            const cached = localStorage.getItem(CACHE_KEY);
            if (!cached) return null;
            
            const data = JSON.parse(cached);
            if (Date.now() - data.timestamp > CACHE_EXPIRY) {
                localStorage.removeItem(CACHE_KEY);
                return null;
            }
            
            return data;
        } catch (e) {
            return null;
        }
    }
    
    function initAccessibility() {
        // Add keyboard navigation for gallery items
        const items = document.querySelectorAll('.gallery-item .doc-link');
        items.forEach((link, index) => {
            link.setAttribute('tabindex', '0');
            
            link.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.click();
                }
            });
        });
        
        // Announce search results to screen readers
        const stats = document.getElementById('gallery-stats');
        if (stats) {
            const count = document.getElementById('total-count');
            if (count) {
                const countValue = count.textContent;
                stats.setAttribute('role', 'status');
                stats.setAttribute('aria-live', 'polite');
                stats.setAttribute('aria-atomic', 'true');
            }
        }
    }
    
    function initLazyLoading() {
        // Use Intersection Observer for lazy loading images
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                            observer.unobserve(img);
                        }
                    }
                });
            });
            
            document.querySelectorAll('.doc-thumbnail-img[data-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    }
    
    // Utility function to escape HTML
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Smooth scroll for pagination
    document.querySelectorAll('.page-link').forEach(link => {
        link.addEventListener('click', function(e) {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    });
    
    // Add click handlers for generating items
    document.querySelectorAll('.gallery-item[data-status="generating"]').forEach(item => {
        item.addEventListener('click', function(e) {
            const link = this.querySelector('.doc-link');
            if (link) {
                // Allow navigation to see progress
            }
        });
    });
})();
