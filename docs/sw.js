const CACHE = 'voice-scale-v1';
const FILES = [
  './',
  './index.html',
  './style.css',
  './manifest.webmanifest',
  './app.js',
  './sound/pitch.js',
  './sound/check.js',
  './sound/audio.js',
  './sound/scale.js',
  './sound/wav.js',
  './save/sounds.js',
  './save/zip.js',
  './device/recorder.js',
  './device/recorder-worklet.js',
  './device/player.js',
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
