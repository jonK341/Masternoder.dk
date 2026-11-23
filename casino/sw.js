/* Casino PWA service worker — push + notificationclick (no offline cache). */
const SW_VERSION = 'casino-push-v1';

self.addEventListener('install', (event) => {
  event.waitUntil(Promise.resolve());
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('push', (event) => {
  let data = { title: 'MasterNoder Casino', body: 'Something happened in the lounge.', url: '/casino/', tag: 'casino' };
  try {
    if (event.data) {
      const parsed = event.data.json();
      data = Object.assign(data, parsed || {});
    }
  } catch (e) {
    try {
      data.body = event.data ? event.data.text() : data.body;
    } catch (_) { /* ignore */ }
  }
  event.waitUntil(
    self.registration.showNotification(data.title || 'MasterNoder Casino', {
      body: data.body || '',
      icon: '/static/img/casino/icon-192.svg',
      badge: '/static/img/casino/icon-maskable.svg',
      tag: data.tag || 'casino',
      data: { url: data.url || '/casino/' },
      renotify: true,
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || '/casino/';
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if ('focus' in client) {
          client.navigate(target);
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(target);
      }
      return undefined;
    })
  );
});

console.log('Casino SW', SW_VERSION);
