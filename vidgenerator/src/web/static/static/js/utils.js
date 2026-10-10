/**
 * Utility functions for performance optimization
 * Debounce, throttle, and other helper functions
 */

/**
 * Debounce function - delays execution until after wait time
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @param {boolean} immediate - Execute immediately on first call
 * @returns {Function} Debounced function
 */
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func(...args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func(...args);
    };
}

/**
 * Throttle function - limits execution to once per wait time
 * @param {Function} func - Function to throttle
 * @param {number} limit - Time limit in milliseconds
 * @returns {Function} Throttled function
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Request Animation Frame throttle - for smooth animations
 * @param {Function} func - Function to throttle with RAF
 * @returns {Function} RAF-throttled function
 */
function rafThrottle(func) {
    let rafId = null;
    return function(...args) {
        if (rafId === null) {
            rafId = requestAnimationFrame(() => {
                func.apply(this, args);
                rafId = null;
            });
        }
    };
}

/**
 * Batch DOM updates - collect multiple updates and apply at once
 * @param {Function} updateFn - Function that performs DOM updates
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} Batched update function
 */
function batchUpdates(updateFn, delay = 0) {
    let pending = false;
    return function(...args) {
        if (!pending) {
            pending = true;
            setTimeout(() => {
                updateFn.apply(this, args);
                pending = false;
            }, delay);
        }
    };
}

/**
 * Lazy load function - only execute when element is visible
 * @param {Element} element - Element to observe
 * @param {Function} callback - Callback when element is visible
 * @param {Object} options - IntersectionObserver options
 */
function lazyLoad(element, callback, options = {}) {
    if (!('IntersectionObserver' in window)) {
        // Fallback for browsers without IntersectionObserver
        callback();
        return;
    }
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                callback();
                observer.unobserve(entry.target);
            }
        });
    }, {
        rootMargin: '50px',
        threshold: 0.01,
        ...options
    });
    
    observer.observe(element);
}

/**
 * Performance monitor - measure function execution time
 * @param {string} label - Label for the measurement
 * @param {Function} fn - Function to measure
 * @returns {*} Result of function execution
 */
function measurePerformance(label, fn) {
    if (window.performance && window.performance.mark) {
        const startMark = `${label}-start`;
        const endMark = `${label}-end`;
        const measureName = label;
        
        performance.mark(startMark);
        const result = fn();
        performance.mark(endMark);
        performance.measure(measureName, startMark, endMark);
        
        const measure = performance.getEntriesByName(measureName)[0];
        console.log(`[Performance] ${label}: ${measure.duration.toFixed(2)}ms`);
        
        return result;
    }
    return fn();
}

/**
 * Memory usage monitor (if available)
 */
function logMemoryUsage() {
    if (performance.memory) {
        const memory = performance.memory;
        console.log('[Memory]', {
            used: `${(memory.usedJSHeapSize / 1048576).toFixed(2)} MB`,
            total: `${(memory.totalJSHeapSize / 1048576).toFixed(2)} MB`,
            limit: `${(memory.jsHeapSizeLimit / 1048576).toFixed(2)} MB`
        });
    }
}

/**
 * Check if element is in viewport
 * @param {Element} element - Element to check
 * @returns {boolean} True if element is in viewport
 */
function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

/**
 * Optimized querySelector with caching
 */
const queryCache = new Map();
function cachedQuery(selector) {
    if (queryCache.has(selector)) {
        return queryCache.get(selector);
    }
    const element = document.querySelector(selector);
    if (element) {
        queryCache.set(selector, element);
    }
    return element;
}

/**
 * Clear query cache (call when DOM changes significantly)
 */
function clearQueryCache() {
    queryCache.clear();
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        debounce,
        throttle,
        rafThrottle,
        batchUpdates,
        lazyLoad,
        measurePerformance,
        logMemoryUsage,
        isInViewport,
        cachedQuery,
        clearQueryCache
    };
}

