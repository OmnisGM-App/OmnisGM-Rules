// Манифест сигнатур страниц для стриминга IndexNow — issue #186.
//
// Зачем: deploy.yml пинговал IndexNow ВЕСЬ sitemap на каждом деплое (5975 URL за раз), из-за
// чего Bing показывает рекомендацию «IndexNow is in batch mode» и советует слать только
// изменённые URL. Чтобы слать изменённые, их надо уметь считать — а сравнивать не с чем:
// прошлой сборки на раннере нет.
//
// Решение: после каждой сборки пишем манифест «URL → сигнатура содержимого», а прошлый
// манифест приносим из кэша GitHub Actions. Разница двух манифестов и есть список изменённых.
//
// Сигнатура НЕ хеш файла: Astro штампует хеши в имена ассетов и в имена классов, поэтому
// побайтовое сравнение показывало бы «изменилось всё» на каждой сборке. Берём то, что видит
// поисковик: <title>, meta description и ТЕКСТ страницы без разметки. Правка стилей сигнатуру
// не двигает, правка шаблона мета или контента — двигает.
//
// Использование:
//   node scripts/indexnow_manifest.mjs --out .indexnow/manifest.json
//   node scripts/indexnow_manifest.mjs --out new.json --prev old.json --changed changed.txt
import { readdirSync, readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { dirname, resolve, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

const here = dirname(fileURLToPath(import.meta.url));
const DIST = resolve(here, '../dist');
const ORIGIN = 'https://rules.omnisgm.com';

const arg = (name, fallback = null) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
};

function* htmlFiles(dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = resolve(dir, e.name);
    if (e.isDirectory()) yield* htmlFiles(p);
    else if (e.name.endsWith('.html')) yield p;
  }
}

// Файл dist → канонический URL страницы (index.html → директория со слэшем).
const urlFor = (file) => {
  const rel = relative(DIST, file).split(sep).join('/');
  return `${ORIGIN}/${rel === 'index.html' ? '' : rel.replace(/index\.html$/, '')}`;
};

// Видимый поисковику текст: снимаем script/style целиком, затем теги, схлопываем пробелы.
const textOf = (html) =>
  html
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

const signature = (html) => {
  const head = html.slice(0, html.indexOf('</head>'));
  const body = html.slice(html.indexOf('</head>'));
  const title = (head.match(/<title>([^<]*)<\/title>/) || [, ''])[1];
  const desc = (head.match(/<meta\s+name="description"\s+content="([^"]*)"/) || [, ''])[1];
  return createHash('sha1').update(`${title}\n${desc}\n${textOf(body)}`).digest('hex').slice(0, 16);
};

// Индексируемый набор — ровно то, что в sitemap: там уже нет noindex-страниц (#37) и нет
// служебных вроде 404.html. Пинговать что-то помимо него — тратить квоту и слать поисковику
// то, что мы сами закрыли. Если sitemap не нашёлся, страхуемся и не фильтруем (кроме 404).
const sitemapUrls = new Set();
for (const f of readdirSync(DIST)) {
  if (!/^sitemap-\d+\.xml$/.test(f)) continue;
  for (const m of readFileSync(resolve(DIST, f), 'utf8').matchAll(/<loc>([^<]+)<\/loc>/g)) {
    sitemapUrls.add(m[1].trim());
  }
}
const indexable = (url) =>
  sitemapUrls.size ? sitemapUrls.has(url) : !url.endsWith('/404.html');

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
  // Первый запуск или кэш истёк. Пинговать всё — значит вернуться ровно в тот batch-режим,
  // от которого уходим, поэтому не пингуем: страницы всё равно найдутся через sitemap и
  // Cloudflare Crawler Hints, а следующий деплой уже посчитает нормальный дифф.
  writeFileSync(resolve(changedPath), '');
  console.log(`::notice::Прошлого манифеста нет (${prevPath}) — пинг пропущен, база записана.`);
  process.exit(0);
}

const prev = JSON.parse(readFileSync(resolve(prevPath), 'utf8'));
const changed = Object.keys(manifest).filter((url) => prev[url] !== manifest[url]);
const added = changed.filter((url) => !(url in prev));

// Порядок отправки: сначала короткие пути. Хабы и страницы классов лежат выше по дереву и
// стоят дороже длинного хвоста сущностей — если сработает верхний предел, отрежется хвост.
changed.sort((a, b) => a.length - b.length || a.localeCompare(b));

writeFileSync(resolve(changedPath), changed.join('\n') + (changed.length ? '\n' : ''));
console.log(
  `Изменилось: ${changed.length} из ${Object.keys(manifest).length} страниц ` +
    `(новых ${added.length}, было в прошлом манифесте ${Object.keys(prev).length})`,
);
