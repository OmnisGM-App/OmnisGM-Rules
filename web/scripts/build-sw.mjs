// Service worker (dist/sw.js) — поверх готовой сборки Astro, после `astro build`.
// Манифест PWA лежит статикой: public/manifest.webmanifest.
import { generateSW } from 'workbox-build';

const { count, size, warnings } = await generateSW({
  swDest: 'dist/sw.js',
  globDirectory: 'dist',
  globPatterns: [
    '**/*.{js,css,svg,woff2}', 'manifest.webmanifest', 'apple-touch-icon.png', 'favicon.ico',
    // Иконки манифеста — в precache, как у прежней интеграции (`includeManifestIcons`).
    'icon-*.png', 'maskable-*.png',
  ],
  // img/** — картинки сущностей (#201/#202): их сотни, в precache раздули бы установку PWA.
  globIgnores: ['**/og*.png', '**/screenshot-*.png', '**/pagefind/**', '**/img/**'],
  cleanupOutdatedCaches: true,
  skipWaiting: true,
  clientsClaim: true,
  sourcemap: false,
  mode: 'production',
  runtimeCaching: [
    {
      urlPattern: ({ request }) => request.destination === 'document',
      handler: 'NetworkFirst',
      options: { cacheName: 'pages', expiration: { maxEntries: 120 }, cacheableResponse: { statuses: [0, 200] } },
    },
    {
      urlPattern: ({ url }) => url.pathname.startsWith('/pagefind/'),
      handler: 'StaleWhileRevalidate',
      options: { cacheName: 'pagefind' },
    },
    // Связка с firebase.json: там /img/ отдаётся с Cache-Control: no-cache, иначе фоновая
    // ревалидация упёрлась бы в HTTP-кэш и новая картинка до пользователя не доехала бы.
    {
      urlPattern: ({ url }) => url.pathname.startsWith('/img/'),
      handler: 'StaleWhileRevalidate',
      options: {
        cacheName: 'entity-images',
        expiration: { maxEntries: 800, maxAgeSeconds: 60 * 60 * 24 * 30 },
        cacheableResponse: { statuses: [0, 200] },
      },
    },
  ],
});

// Предупреждение workbox (файл больше лимита precache и т.п.) — красная сборка, не строка в
// логе: файл, выпавший из precache молча, никто не заметит.
if (warnings.length) {
  for (const w of warnings) console.error(`[sw] ${w}`);
  process.exit(1);
}
console.log(`[sw] precache: ${count} файлов, ${(size / 1024).toFixed(2)} КиБ → dist/sw.js`);
