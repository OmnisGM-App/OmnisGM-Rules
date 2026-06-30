// Копирует бренд-иконки из @omnisgm-app/brand в public/ — единый источник (кит).
// Запускается на predev/prebuild. og.png остаётся per-app (свой текст), не трогаем.
import { copyFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = join(root, 'node_modules', '@omnisgm-app', 'brand', 'assets');
const pub = join(root, 'public');
mkdirSync(pub, { recursive: true });

const FILES = [
  'favicon.svg', 'icon.svg', 'maskable.svg',
  'icon-192.png', 'icon-512.png', 'maskable-192.png', 'maskable-512.png', 'apple-touch-icon.png',
];
for (const f of FILES) copyFileSync(join(src, f), join(pub, f));
console.log(`✓ бренд-иконки скопированы из @omnisgm-app/brand (${FILES.length} файлов)`);
