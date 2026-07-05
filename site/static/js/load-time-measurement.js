/**
 * P1: Loading Time Measurement
 * Captures Navigation Timing metrics on page load and logs to console.
 * Add to key pages: unified_dashboard, profile, stats, generator, battle, shop.
 * How it works: Runs on load; reads performance.timing; logs fullLoad, domReady, etc.
 */
(function() {
    'use strict';
    window._pageLoadStart = window._pageLoadStart || performance.now();

    function captureLoadTime() {
        try {
            var t = performance.timing;
            if (!t || t.loadEventEnd === 0) return;

            var fullLoad = t.loadEventEnd - t.navigationStart;
            var domReady = t.domContentLoadedEventEnd - t.navigationStart;
            var page = window.location.pathname || 'unknown';

            var metrics = {
                full: fullLoad + 'ms',
                domReady: domReady + 'ms',
                page: page,
                navigationStart: t.navigationStart
            };

            console.log('[LoadTime]', metrics);

            try {
                var history = JSON.parse(sessionStorage.getItem('loadTimeHistory') || '[]');
                history.unshift({ ts: new Date().toISOString(), full: fullLoad, domReady: domReady, page: page });
                history = history.slice(0, 5);
                sessionStorage.setItem('loadTimeHistory', JSON.stringify(history));
            } catch (e) {}

            window._lastLoadTime = metrics;
        } catch (err) {
            console.warn('[LoadTime] Capture failed:', err);
        }
    }

    if (document.readyState === 'complete') {
        captureLoadTime();
    } else {
        window.addEventListener('load', captureLoadTime);
    }
})();
