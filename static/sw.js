/* Moora service worker — Web Push */
self.addEventListener('push', (event) => {
  let data = { title: 'Moora', body: 'Bạn có thông báo mới', url: '/' };
  try {
    if (event.data) data = { ...data, ...event.data.json() };
  } catch (_) {}
  event.waitUntil(
    self.registration.showNotification(data.title || 'Moora', {
      body: data.body || '',
      icon: '/static/img/favicon.ico',
      badge: '/static/img/favicon.ico',
      data: { url: data.url || '/' },
      tag: data.tag || 'moora-notif',
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      for (const client of list) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});
