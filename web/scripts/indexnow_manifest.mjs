// Манифест сигнатур страниц для стриминга IndexNow — issue #186.
//
// Шлём только изменённые URL: весь sitemap на каждом деплое — «IndexNow is in batch mode» у Bing.
// Сигнатура — не хеш файла (Astro штампует хеши в имена ассетов и классов), а видимое поисковику:
// <title>, description и текст без разметки. Прошлый манифест — из кэша GitHub Actions.
import { readdirSync, readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { dirname, resolve, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

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
 * @param {string} dir
 * @returns {Generator<string>}
 */
function* htmlFiles(dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = resolve(dir, e.name);
    if (e.isDirectory()) yield* htmlFiles(p);
    else if (e.name.endsWith('.html')) yield p;
  }
}

/**
 * @param {string} file
 * @returns {string}
 */
const urlFor = (file) => {
  const rel = relative(DIST, file).split(sep).join('/');
  return `${ORIGIN}/${rel === 'index.html' ? '' : rel.replace(/index\.html$/, '')}`;
};

/**
 * @param {string} html
 * @returns {string}
 */
const textOf = (html) =>
  html
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

/**
 * @param {string} html
 * @returns {string}
 */
const signature = (html) => {
  const head = html.slice(0, html.indexOf('</head>'));
  const body = html.slice(html.indexOf('</head>'));
  const title = (head.match(/<title>([^<]*)<\/title>/) || [, ''])[1];
  const desc = (head.match(/<meta\s+name="description"\s+content="([^"]*)"/) || [, ''])[1];
  return createHash('sha1').update(`${title}\n${desc}\n${textOf(body)}`).digest('hex').slice(0, 16);
};

// Индексируемое — ровно sitemap: noindex-страницы (#37) пинговать — тратить квоту.
const sitemapUrls = new Set();
for (const f of readdirSync(DIST)) {
  if (!/^sitemap-\d+\.xml$/.test(f)) continue;
  for (const m of readFileSync(resolve(DIST, f), 'utf8').matchAll(/<loc>([^<]+)<\/loc>/g)) {
    sitemapUrls.add(m[1].trim());
  }
}
/**
 * @param {string} url
 * @returns {boolean}
 */
const indexable = (url) =>
  sitemapUrls.size ? sitemapUrls.has(url) : !url.endsWith('/404.html');

/** @type {Record<string, string>} */
const manifest = {};
let skipped = 0;
for (const file of htmlFiles(DIST)) {
  const url = urlFor(file);
  if (!indexable(url)) { skipped++; continue; }
  manifest[url] = signature(readFileSync(file, 'utf8'));
}

const outPath = arg('out');
if (!outPath) {
  console.error('Не задан --out');
  process.exit(2);
}
mkdirSync(dirname(resolve(outPath)), { recursive: true });
writeFileSync(resolve(outPath), JSON.stringify(manifest));
console.log(
  `Манифест: ${Object.keys(manifest).length} страниц → ${outPath}` +
    (skipped ? ` (вне sitemap пропущено ${skipped})` : ''),
);

const prevPath = arg('prev');
const changedPath = arg('changed');
if (!prevPath || !changedPath) process.exit(0);

if (!existsSync(resolve(prevPath))) {
  // Не пингуем: «всё сразу» и есть batch-режим, от которого уходим; база запишется для следующего.
  writeFileSync(resolve(changedPath), '');
  console.log(`::notice::Прошлого манифеста нет (${prevPath}) — пинг пропущен, база записана.`);
  process.exit(0);
}

/** @type {Record<string, string>} */
const prev = JSON.parse(readFileSync(resolve(prevPath), 'utf8'));
const changed = Object.keys(manifest).filter((url) => prev[url] !== manifest[url]);
const added = changed.filter((url) => !(url in prev));

// Исчезнувшие — не в IndexNow, а в purge Cloudflare: иначе удалённая страница живёт на эдже до TTL (#175).
const removed = Object.keys(prev).filter((url) => !(url in manifest));
const removedPath = arg('removed');
if (removedPath) {
  writeFileSync(resolve(removedPath), removed.join('\n') + (removed.length ? '\n' : ''));
  if (removed.length) console.log(`Исчезло: ${removed.length} URL → ${removedPath}`);
}

// Короткие пути первыми: хабы дороже хвоста сущностей, при пределе отрежется хвост.
changed.sort((a, b) => a.length - b.length || a.localeCompare(b));

writeFileSync(resolve(changedPath), changed.join('\n') + (changed.length ? '\n' : ''));
console.log(
  `Изменилось: ${changed.length} из ${Object.keys(manifest).length} страниц ` +
    `(новых ${added.length}, было в прошлом манифесте ${Object.keys(prev).length})`,
);
