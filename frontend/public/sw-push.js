/* Service Worker for Push Notifications — Story Battle Engine */

self.addEventListener('push', function(event) {
  if (!event.data) return;

  let payload;
  try {
    payload = event.data.json();
  } catch (e) {
    payload = { title: 'Story Battle', body: event.data.text() };
  }

  const trigger = payload.data?.trigger || 'default';
  const title = payload.title || 'Story Battle';

  // Urgency-driven notification options per trigger type
  const options = {
    body: payload.body || '',
    icon: '/favicon.ico',
    badge: '/favicon.ico',
    tag: payload.tag || trigger,
    renotify: true,
    requireInteraction: trigger === 'rank_drop', // rank_drop stays until tapped
    data: payload.data || {},
    vibrate: trigger === 'rank_drop'
      ? [200, 100, 200, 100, 300] // aggressive pattern for rank drop
      : [200, 100, 200],
    actions: trigger === 'rank_drop'
      ? [{ action: 'open', title: 'Take it back' }]
      : trigger === 'near_win'
      ? [{ action: 'open', title: 'Claim #1' }]
      : [{ action: 'open', title: 'Open' }],
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();

  const deepLink = event.notification.data?.deep_link || '/app';
  const url = new URL(deepLink, self.location.origin).href;

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      return clients.openWindow(url);
    })
  );
});

self.addEventListener('install', function(event) {
  self.skipWaiting();
});

self.addEventListener('activate', function(event) {
  event.waitUntil(self.clients.claim());
});
