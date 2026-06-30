import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import pagefind from 'astro-pagefind';
import AstroPWA from '@vite-pwa/astro';
import rehypePromoteHeadings from './src/lib/rehype-promote-headings.mjs';
import rehypeWrapTables from './src/lib/rehype-wrap-tables.mjs';

// rules.omnisgm.com — статический (SSG) ридер SRD экосистемы OmnisGM.
// Контент — Markdown из ../src/{game}/{version}/{en,ru}/**.md (вход контентного пайплайна),
// рендерится на билде. Pagefind (статический поиск) и PWA подключаются следующими шагами.
export default defineConfig({
  site: 'https://rules.omnisgm.com',
  // Везде trailing slash: директорийные URL (/en/.../legal/) и индекс API (/api/dnd/) тогда
  // работают с относительными ссылками; Firebase trailingSlash:true их не ломает редиректом.
  trailingSlash: 'always',
  integrations: [
    sitemap(),
    pagefind(),
    AstroPWA({
      registerType: 'autoUpdate',
      // Интеграция генерит manifest.webmanifest + sw.js, но НЕ инъектирует их в HTML Astro-страниц
      // (особенность @vite-pwa/astro). Поэтому линкуем манифест и регистрируем SW вручную в Reader.astro.
      injectRegister: false,
      includeAssets: ['favicon.svg', 'apple-touch-icon.png', 'icon.svg'],
      manifest: {
        id: '/',
        name: 'OmnisGM Rules — TTRPG SRD',
        short_name: 'OmnisGM Rules',
        description:
          'A fast, offline-ready reader for freely-licensed tabletop RPG System Reference Documents — D&D 5.2.1 / 5.1, Daggerheart, Basic Roleplaying.',
        lang: 'en',
        dir: 'ltr',
        categories: ['books', 'reference', 'education', 'games'],
        theme_color: '#0F1016',
        background_color: '#0F1016',
        display: 'standalone',
        display_override: ['standalone', 'minimal-ui'],
        // Ридер читают и в портрете (телефон), и в альбоме (планшет/десктоп) — 'any'
        // (в News стоит 'portrait', т.к. там телефонная лента). Закрывает warning PWABuilder.
        orientation: 'any',
        start_url: '/en/',
        scope: '/',
        // Фокусируем уже открытое окно (ридер — одно-инстансный).
        launch_handler: { client_mode: 'navigate-existing' },
        edge_side_panel: { preferred_width: 400 },
        // Раздаётся с 3 доменов — объявляем одним приложением (нужен /.well-known/web-app-origin-association).
        scope_extensions: [
          { type: 'origin', origin: 'https://rules.omnisgm.com' },
          { type: 'origin', origin: 'https://omnisgm-rules.web.app' },
          { type: 'origin', origin: 'https://omnisgm-rules.firebaseapp.com' },
        ],
        shortcuts: [
          { name: 'D&D SRD 5.2.1', short_name: 'D&D 5.2', url: '/en/dnd/srd-5.2/legal/' },
          { name: 'Daggerheart SRD', short_name: 'Daggerheart', url: '/en/daggerheart/srd-1.0/legal/' },
          { name: 'На русском', short_name: 'Русский', url: '/ru/' },
        ],
        translations: {
          ru: {
            name: 'OmnisGM Rules — SRD настольных игр',
            short_name: 'OmnisGM Rules',
            description:
              'Быстрый офлайн-ридер свободно-лицензированных SRD настольных ролевых игр — D&D 5.2.1 / 5.1, Daggerheart, Basic Roleplaying.',
          },
        },
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
          { src: '/maskable-192.png', sizes: '192x192', type: 'image/png', purpose: 'maskable' },
          { src: '/maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
          { src: '/icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' },
        ],
      },
      workbox: {
        // Прекэшим только лёгкие ассеты (не 228 HTML); страницы и pagefind — рантайм-кэш.
        globPatterns: ['**/*.{js,css,svg,woff2}'],
        globIgnores: ['**/og*.png', '**/pagefind/**'],
        navigateFallback: null,
        cleanupOutdatedCaches: true,
        skipWaiting: true,
        clientsClaim: true,
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
            handler: 'CacheFirst',
            options: { cacheName: 'google-fonts-stylesheets', expiration: { maxEntries: 10, maxAgeSeconds: 31536000 }, cacheableResponse: { statuses: [0, 200] } },
          },
          {
            urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
            handler: 'CacheFirst',
            options: { cacheName: 'google-fonts-webfonts', expiration: { maxEntries: 30, maxAgeSeconds: 31536000 }, cacheableResponse: { statuses: [0, 200] } },
          },
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
        ],
      },
    }),
  ],
  build: {
    format: 'directory',
  },
  markdown: {
    // Нормализуем уровни заголовков ДО сбора TOC (headings) Astro — чтобы titled h1 не попадал в TOC.
    rehypePlugins: [rehypePromoteHeadings, rehypeWrapTables],
  },
});
