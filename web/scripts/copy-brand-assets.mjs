// Раскладка ассетов кита в public/ — обёртка над @omnisgm-app/brand/copy-assets (Core#1).
// Шрифты self-host (#10) раскладывает кит в `public/fonts/` — сюда ведёт указатель из `Reader.astro`.
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
  // 404 кита не берём: `public/404.html` столкнулся бы с `dist/404.html` из `src/pages/404.astro`.
  notFound: false,
});
