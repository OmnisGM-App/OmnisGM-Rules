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
  // 404 кита НЕ берём: у нас своя `src/pages/404.astro` с навигацией сайта, а самодостаточный
  // HTML кита рассчитан на продукт без своей вёрстки.
  notFound: false,
});
