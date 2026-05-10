/* Atlas Suite — minimal service worker (no caching; Dash callbacks stay untouched). */
self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.clients.claim();
});
