const CACHE_NAME = 'foragro-kiosk-v2';
const STATIC_ASSETS = [
    '/kiosk/',
    '/kiosk/index.html',
    '/kiosk/css/style.css',
    '/kiosk/js/app-ws.js',
    '/kiosk/js/offline-engine.js',
    '/shared/logo.png',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

// Install event: cache static assets
self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME)
        .then(cache => cache.addAll(STATIC_ASSETS))
        .then(() => self.skipWaiting())
    );
});

// Activate event: clean up old caches
self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.map(key => {
                    if (key !== CACHE_NAME) {
                        return caches.delete(key);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch event: network first for API, cache first for static
self.addEventListener('fetch', (e) => {
    // Si es una llamada a la API, no usar caché (excepto para offline-cache)
    if (e.request.url.includes('/api/')) {
        if (e.request.url.includes('/api/offline-cache')) {
            e.respondWith(
                fetch(e.request)
                .then(res => {
                    const resClone = res.clone();
                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(e.request, resClone);
                    });
                    return res;
                })
                .catch(() => caches.match(e.request))
            );
            return;
        }
        return; // network normal para el resto de la API
    }

    // Para estáticos, Cache First, fallback to Network
    e.respondWith(
        caches.match(e.request)
        .then(cachedResponse => {
            if (cachedResponse) {
                return cachedResponse;
            }
            return fetch(e.request).then(response => {
                if (!response || response.status !== 200 || response.type !== 'basic') {
                    return response;
                }
                const responseToCache = response.clone();
                caches.open(CACHE_NAME).then(cache => {
                    cache.put(e.request, responseToCache);
                });
                return response;
            });
        })
    );
});
