const CACHE_NAME = "green-vita-admin-v3";

self.addEventListener("install", event => {
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", event => {
  if (event.request.method !== "GET") return;
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
});

self.addEventListener("push", event => {
  const data = event.data ? event.data.json() : {};
  const count = Number(data.badge_count || 0);

  event.waitUntil((async () => {
    if (count > 0 && "setAppBadge" in self.registration) {
      await self.registration.setAppBadge(count).catch(() => {});
    }

    await self.registration.showNotification(
      data.title || "گرین ویتا",
      {
        body: data.body || "درخواست جدیدی ثبت شده است.",
        icon: "/static/icon-192-v2.png",
        badge: "/static/icon-192-v2.png",
        data: { url: data.url || "/visits" }
      }
    );
  })());
});

self.addEventListener("notificationclick", event => {
  event.notification.close();

  const url = event.notification.data?.url || "/visits";

  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true })
      .then(clients => {
        for (const client of clients) {
          if ("focus" in client) {
            client.navigate(url);
            return client.focus();
          }
        }
        return self.clients.openWindow(url);
      })
  );
});
