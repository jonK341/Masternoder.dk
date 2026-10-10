/* Documentary Generator - Service Worker (Phase 3) - Enhanced */
const APP_VERSION = 'dg-sw-v3';
const PRECACHE = `dg-precache-${APP_VERSION}`;
const RUNTIME = `dg-runtime-${APP_VERSION}`;
const OFFLINE_FALLBACK_URL = '/vidgenerator/offline';

const PRECACHE_URLS = [
  '/',
  '/vidgenerator/',
  OFFLINE_FALLBACK_URL,
  '/static/css/style.css?v=3.30.0-phase3-complete',
  '/static/js/main.js?v=3.30.0-phase3-complete',
  '/static/js/utils.js?v=1.0.0-performance',
  '/static/js/additional_themes.js?v=1.0.0-themes',
  '/static/js/theme_model.js?v=1.0.0-futuristic',
  '/static/img/favicon.png',
  '/static/img/masternoder2_sword.gif'
];

// Install event - precache critical assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker version:', APP_VERSION);
  self.skipWaiting(); // Activate immediately
  
  event.waitUntil(
    caches.open(PRECACHE)
      .then((cache) => {
        console.log('[SW] Precaching', PRECACHE_URLS.length, 'assets');
        return cache.addAll(PRECACHE_URLS).catch((err) => {
          console.warn('[SW] Some precache assets failed:', err);
          // Continue even if some assets fail
          return Promise.resolve();
        });
      })
      .then(() => {
        console.log('[SW] Precache complete');
      })
      .catch((err) => {
        console.error('[SW] Precache failed:', err);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker version:', APP_VERSION);
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      const oldCaches = cacheNames.filter((name) => {
        return name.startsWith('dg-') && ![PRECACHE, RUNTIME].includes(name);
      });
      
      console.log('[SW] Cleaning up', oldCaches.length, 'old caches');
      
      return Promise.all(
        oldCaches.map((name) => {
          console.log('[SW] Deleting old cache:', name);
          return caches.delete(name);
        })
      );
    })
    .then(() => {
      console.log('[SW] Activation complete, claiming clients');
      return self.clients.claim();
    })
    .then(() => {
      console.log('[SW] Service worker activated and ready');
      // Notify all clients
      return self.clients.matchAll().then((clients) => {
        clients.forEach((client) => {
          client.postMessage({
            type: 'SW_ACTIVATED',
            version: APP_VERSION
          });
        });
      });
    })
    .catch((err) => {
      console.error('[SW] Activation error:', err);
    })
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') {
    return;
  }

  const url = new URL(request.url);

  // Only handle same-origin requests
  if (url.origin !== self.location.origin) {
    return;
  }

  // Navigation requests – network-first with fallback
  if (request.mode === 'navigate' || request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(networkFirst(request, true));
    return;
  }

  // Static assets
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // API requests – network-first with cache fallback
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/vidgenerator/api/')) {
    event.respondWith(networkFirst(request));
    return;
  }
});

// Cache-first strategy for static assets
async function cacheFirst(request) {
  try {
    const cached = await caches.match(request);
    if (cached) {
      console.log('[SW] Cache hit:', request.url);
      return cached;
    }

    console.log('[SW] Cache miss, fetching:', request.url);
    const response = await fetch(request);
    
    // Only cache successful responses
    if (response && response.status === 200) {
      const cache = await caches.open(RUNTIME);
      await cache.put(request, response.clone());
    }
    
    return response;
  } catch (error) {
    console.error('[SW] Cache-first error:', error);
    // Return a basic error response
    return new Response('Network error', {
      status: 503,
      statusText: 'Service Unavailable'
    });
  }
}

// Network-first strategy with cache fallback
async function networkFirst(request, isHTML = false) {
  const cache = await caches.open(RUNTIME);
  
  try {
    // Try network first
    const response = await fetch(request, {
      cache: 'no-store', // Always fetch fresh
      headers: {
        'Cache-Control': 'no-cache'
      }
    });
    
    // Only cache successful responses
    if (response && response.status === 200) {
      await cache.put(request, response.clone());
      console.log('[SW] Network response cached:', request.url);
    }
    
    return response;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', request.url);
    
    // Try cache
    const cached = await caches.match(request);
    if (cached) {
      console.log('[SW] Serving from cache:', request.url);
      return cached;
    }

    // HTML fallback
    if (isHTML) {
      const fallback = await caches.match(OFFLINE_FALLBACK_URL);
      if (fallback) {
        console.log('[SW] Serving offline fallback');
        return fallback;
      }
    }

    // Return appropriate error response
    if (isHTML) {
      return new Response(
        '<!DOCTYPE html><html><head><title>Offline</title></head><body><h1>You are offline</h1><p>Please check your connection.</p></body></html>',
        {
          status: 503,
          headers: { 'Content-Type': 'text/html; charset=utf-8' }
        }
      );
    }

    return new Response(
      JSON.stringify({ 
        error: 'Offline', 
        message: 'Resource unavailable offline.',
        url: request.url
      }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

// Message handler for communication with clients
self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({ version: APP_VERSION });
  }
  
  if (event.data && event.data.type === 'CLEAR_CACHE') {
    caches.keys().then((cacheNames) => {
      return Promise.all(cacheNames.map((name) => caches.delete(name)));
    }).then(() => {
      event.ports[0].postMessage({ success: true });
    });
  }
});

