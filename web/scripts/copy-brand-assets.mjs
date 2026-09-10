// Раскладка ассетов кита в public/ — обёртка над @omnisgm-app/brand/copy-assets (Core#1).
//
// Копирование жило тремя копиями (Table, News, здесь) и разошлось не только картой имён, но и
// механикой: Table резолвил ассеты через `require.resolve` (в workspaces кит hoist'ится в
// корневой node_modules), а здесь путь `node_modules/@omnisgm-app/brand/assets` складывался
// руками — то есть работало ровно до первого переезда в workspace. Теперь копирует кит, и
// резолва у потребителя нет вовсе: файлы считаются от модуля изнутри пакета.
//
// ОСТАЛОСЬ ЗДЕСЬ: карта имён и решение про 404. Имена у нас канонические — переименований нет,
// в отличие от Table с его `pwa-512x512.png`.
//
// ОТДАНО КИТУ: шрифты self-host (#10) — все `*.woff2` уезжают в `public/fonts/`, на них
// ссылается `@omnisgm-app/brand/fonts.css` (импортируется в `Reader.astro`), а число начертаний
// пришпилено `e2e/pwa-sw.spec.ts` («ровно 18», не «больше нуля»). Раньше это была строка здесь;
// теперь список ведёт кит, и здесь о нём только этот абзац — указатели из `Reader.astro` и
// `web/.gitignore` приводят сюда.
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { copyBrandAssets } from '@omnisgm-app/brand/copy-assets';

copyBrandAssets({
  publicDir: join(dirname(fileURLToPath(import.meta.url)), '..', 'public'),
  // og.png остаётся per-app (свой текст), поэтому кит его не отдаёт и здесь его нет.
  icons: [
    'favicon.svg', 'favicon.ico', 'icon.svg', 'maskable.svg',
    'icon-192.png', 'icon-512.png', 'maskable-192.png', 'maskable-512.png', 'apple-touch-icon.png',
  ],
  // 404 кита НЕ берём, и причина не в дизайне: `src/pages/404.astro` — ТОТ ЖЕ дизайн кита, но с
  // Rules-спецификой (язык в home-ссылке `/en/` · `/ru/`, свои favicon/manifest). Причина
  // механическая: `public/404.html` кита столкнулся бы с `dist/404.html`, который Astro генерит
  // из этой страницы, — в `dist/` победил бы один из двух, и какой именно, зависело бы от порядка.
  notFound: false,
});
