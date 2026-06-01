/* ═══════════════════════════════════════════════════════════
   UniBurkina Hub — Service Worker v1.0
   PWA offline support — landing page & assets
   ═══════════════════════════════════════════════════════════ */

const CACHE_NAME = 'uniburkina-v1';
const OFFLINE_URL = '/';

// Assets à mettre en cache immédiatement
const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
];

// ── Install : précache ──────────────────────────────────────
self.addEventListener('install', (event) => {
  console.log('[SW] Installing UniBurkina Hub SW...');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Precaching assets...');
      // On essaie chaque asset individuellement pour éviter l'échec total
      return Promise.allSettled(
        PRECACHE_ASSETS.map(url =>
          cache.add(url).catch(e => console.warn('[SW] Could not cache:', url, e))
        )
      );
    }).then(() => self.skipWaiting())
  );
});

// ── Activate : purge anciens caches ────────────────────────
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(
        cacheNames
          .filter(name => name !== CACHE_NAME)
          .map(name => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      )
    ).then(() => self.clients.claim())
  );
});

// ── Fetch : stratégie Network-First avec fallback cache ────
self.addEventListener('fetch', (event) => {
  // On ne gère que les requêtes GET
  if (event.request.method !== 'GET') return;

  // Ignorer les requêtes vers des API externes (fonts Google, etc.)
  const url = new URL(event.request.url);
  if (url.origin !== location.origin &&
      !url.hostname.includes('fonts.googleapis.com') &&
      !url.hostname.includes('fonts.gstatic.com')) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        // Si la réponse réseau est valide, on la met en cache
        if (networkResponse && networkResponse.status === 200) {
          const cloned = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, cloned));
        }
        return networkResponse;
      })
      .catch(() => {
        // Réseau indisponible → on sert depuis le cache
        return caches.match(event.request).then(cachedResponse => {
          if (cachedResponse) {
            console.log('[SW] Serving from cache (offline):', event.request.url);
            return cachedResponse;
          }
          // Fallback ultime : la page d'accueil
          return caches.match(OFFLINE_URL);
        });
      })
  );
});

// ── Push notifications (placeholder pour le futur) ─────────
self.addEventListener('push', (event) => {
  if (!event.data) return;
  const data = event.data.json();
  self.registration.showNotification(data.title || 'UniBurkina Hub', {
    body: data.body || 'Nouveau contenu disponible',
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-192.png',
    data: { url: data.url || '/' }
  });
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data.url)
  );
});
