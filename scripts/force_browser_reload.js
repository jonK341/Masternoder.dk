/**
 * Force Browser Reload Script
 * Add this to profile page to force cache clear
 */

// Add timestamp to all script and link tags
(function() {
    const timestamp = Date.now();
    const version = '20260121191741';
    
    // Update all script tags with cache busting
    document.querySelectorAll('script[src]').forEach(script => {
        const src = script.getAttribute('src');
        if (src && !src.includes('?v=')) {
            script.setAttribute('src', src + '?v=' + version);
        } else if (src && src.includes('?v=')) {
            script.setAttribute('src', src.replace(/\?v=\d+/, '?v=' + version));
        }
    });
    
    // Update all link tags (CSS) with cache busting
    document.querySelectorAll('link[rel="stylesheet"]').forEach(link => {
        const href = link.getAttribute('href');
        if (href && !href.includes('?v=')) {
            link.setAttribute('href', href + '?v=' + version);
        } else if (href && href.includes('?v=')) {
            link.setAttribute('href', href.replace(/\?v=\d+/, '?v=' + version));
        }
    });
    
    // Force reload if version mismatch
    const pageVersion = document.querySelector('meta[name="version"]');
    if (pageVersion) {
        const storedVersion = localStorage.getItem('profile_page_version');
        if (storedVersion && storedVersion !== version) {
            console.log('Version mismatch detected, clearing cache...');
            localStorage.clear();
            sessionStorage.clear();
            location.reload(true);
        }
        localStorage.setItem('profile_page_version', version);
    }
})();
