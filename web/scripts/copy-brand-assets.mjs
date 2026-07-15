// Копирует бренд-иконки из @omnisgm-app/brand в public/ — единый источник (кит).
// Запускается на predev/prebuild. og.png остаётся per-app (свой текст), не трогаем.
import { copyFileSync, mkdirSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = join(root, 'node_modules', '@omnisgm-app', 'brand', 'assets');
const pub = join(root, 'public');
mkdirSync(pub, { recursive: true });

const FILES = [
  'favicon.svg', 'favicon.ico', 'icon.svg', 'maskable.svg',
  'icon-192.png', 'icon-512.png', 'maskable-192.png', 'maskable-512.png', 'apple-touch-icon.png',
];
for (const f of FILES) copyFileSync(join(src, f), join(pub, f));
console.log(`✓ бренд-иконки скопированы из @omnisgm-app/brand (${FILES.length} файлов)`);

// Шрифты (self-host, #10): assets/fonts/*.woff2 → public/fonts/ (fonts.css ссылается на /fonts/*).
const fontsSrc = join(src, 'fonts');
const fontsDest = join(pub, 'fonts');
mkdirSync(fontsDest, { recursive: true });
const woff2 = readdirSync(fontsSrc).filter((f) => f.endsWith('.woff2'));
for (const f of woff2) copyFileSync(join(fontsSrc, f), join(fontsDest, f));
console.log(`✓ шрифты скопированы из @omnisgm-app/brand (${woff2.length} woff2) → public/fonts/`);
