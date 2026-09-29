// Список URL для точечного purge edge-кэша Cloudflare после деплоя — issue #175.
//
// Не «purge everything»: зона одна на весь omnisgm.com (сброс выносит кэш News и Table), а purge
// по префиксу/хосту — только на Enterprise. /_astro/* не сбрасываем: хеш в имени = новый URL.
import { readdirSync, readFileSync, writeFileSync, existsSync, statSync } from 'node:fs';
import { dirname, resolve, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const DIST = resolve(here, '../dist');
const ORIGIN = 'https://rules.omnisgm.com';

/**
 * @param {string} name
 * @param {string|null} [fallback]
 * @returns {string|null}
 */
const arg = (name, fallback = null) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
};

/**
 * @param {string|null} path
 * @returns {string[]}
 */
const lines = (path) =>
  path && existsSync(resolve(path))
    ? readFileSync(resolve(path), 'utf8').split('\n').map((s) => s.trim()).filter(Boolean)
    : [];

// Явный список, а не маска: случайный файл в корне dist не должен молча попадать в purge.
const FIXED = [
  'favicon.svg', 'favicon.ico', 'icon.svg', 'maskable.svg',
  'icon-192.png', 'icon-512.png', 'maskable-192.png', 'maskable-512.png',
  'apple-touch-icon.png', 'og.png',
  'robots.txt', 'llms.txt', 'manifest.webmanifest', 'sw.js',
  'sitemap-index.xml',
];

const urls = new Set();

// Корень — всегда: правки <head> не меняют сигнатуру контента, а фавикон Google берёт с главной (#199).
urls.add(`${ORIGIN}/`);
urls.add(`${ORIGIN}/index.html`);

for (const name of FIXED) {
  if (existsSync(resolve(DIST, name))) urls.add(`${ORIGIN}/${name}`);
}
for (const f of readdirSync(DIST)) {
  if (/^sitemap-\d+\.xml$/.test(f)) urls.add(`${ORIGIN}/${f}`);
}

const apiDir = resolve(DIST, 'api');
/**
 * @param {string} dir
 * @returns {Generator<string>}
 */
function* walk(dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = resolve(dir, e.name);
    if (e.isDirectory()) yield* walk(p);
    else yield p;
  }
}
if (existsSync(apiDir) && statSync(apiDir).isDirectory()) {
  for (const file of walk(apiDir)) {
    const rel = relative(DIST, file).split(sep).join('/');
    // /api/dnd/ и /api/dnd/index.html кэшируются отдельными записями.
    urls.add(`${ORIGIN}/${rel}`);
    if (rel.endsWith('/index.html')) urls.add(`${ORIGIN}/${rel.replace(/index\.html$/, '')}`);
  }
}

// Firebase отдаёт /…/index.html с 200, без редиректа (проверено на проде) — это отдельная запись
// в кэше, которую краулер мог однажды дёрнуть.
/**
 * @param {string} url
 * @returns {string[]}
 */
const withIndexHtml = (url) => (url.endsWith('/') ? [url, `${url}index.html`] : [url]);

for (const u of lines(arg('changed'))) withIndexHtml(u).forEach((x) => urls.add(x));
for (const u of lines(arg('removed'))) withIndexHtml(u).forEach((x) => urls.add(x));

const out = arg('out');
if (!out) {
  console.error('Не задан --out');
  process.exit(2);
}
const list = [...urls];
writeFileSync(resolve(out), list.join('\n') + (list.length ? '\n' : ''));
console.log(`Purge-список: ${list.length} URL → ${out}`);
