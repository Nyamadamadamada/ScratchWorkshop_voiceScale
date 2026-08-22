const CACHE = 'voice-scale-v1';
const FILES = [
  './',
  './index.html',
  './style.css',
  './app.js',
  './pitch.js',
  './check.js',
  './audio.js',
  './scale.js',
  './wav.js',
  './recorder.js',
  './player.js',
  './sounds.js',
  './recorder-worklet.js',
  './manifest.webmanifest',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(FILES)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    caches.match(event.request).then((hit) => hit || fetch(event.request))
  );
});
