// Touch Grass Planner - Service Worker
const CACHE_NAME = "touch-grass-v2";

const CORE_ASSETS = [
  "/",
  "/index.html",
  "/style.css",
  "/app.js",
  "/manifest.webmanifest",
  "/icons/icon.svg",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/icon-maskable-512.png",
  "/icons/apple-touch-icon.png",
  "/icons/icon-32.png"
];

// Install: Cache critical app shell
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(CORE_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// Activate: Clean up previous caches and claim clients immediately
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: Strategy depending on request type
self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Ignore non-GET requests (e.g. POST /api/suggest, POST /api/feedback)
  if (request.method !== "GET") {
    return;
  }

  // Handle API GET requests (e.g. /api/health, /api/history)
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(request).catch(async () => {
        // Return fallback JSON if offline
        if (url.pathname === "/api/health") {
          return new Response(
            JSON.stringify({
              ollama: false,
              model: "offline",
              model_available: false,
              offline: true
            }),
            { headers: { "Content-Type": "application/json" } }
          );
        }
        if (url.pathname === "/api/history") {
          return new Response(
            JSON.stringify({ events: [], offline: true }),
            { headers: { "Content-Type": "application/json" } }
          );
        }
        return new Response(
          JSON.stringify({
            error: "Offline",
            detail: "You are currently offline. Connect to the internet to get new suggestions."
          }),
          { status: 503, headers: { "Content-Type": "application/json" } }
        );
      })
    );
    return;
  }

  // HTML navigation: Stale-while-revalidate with offline fallback
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          return response;
        })
        .catch(async () => {
          const cached = await caches.match(request);
          return cached || (await caches.match("/index.html")) || (await caches.match("/"));
        })
    );
    return;
  }

  // Core static assets: Cache first, update in background (Stale-While-Revalidate)
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      const fetchPromise = fetch(request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return networkResponse;
        })
        .catch(() => null);

      return cachedResponse || fetchPromise;
    })
  );
});
