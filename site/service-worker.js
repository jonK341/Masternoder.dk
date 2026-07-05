/**
 * Minimal Service Worker – no cache, no background sync, no fetch interception.
 * Replaces the previous heavy SW so the app works reliably and uses minimal power.
 * All requests go straight to the network; disable with ?sw=0 or localStorage.sw_disabled=1.
 */
const VERSION = 'minimal-v1';

self.addEventListener('install', (event) => {
    event.waitUntil(Promise.resolve());
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys()
            .then((names) => Promise.all(names.map((n) => caches.delete(n))))
            .then(() => self.clients.claim())
    );
});

// No fetch handler – browser uses network for every request (no interception, no cache, no power use).
// No sync / periodicsync – no background work.
// No message handler – agent tasks can run in the main page when the user has the tab open.

console.log('Service Worker: minimal (no cache, no background)');
