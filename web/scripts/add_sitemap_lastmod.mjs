// lastmod в sitemap (issue #221) — postbuild, сразу после astro build.
// Дата — из САМОЙ собранной страницы (`dateModified` JSON-LD, #219), а не serialize в @astrojs/sitemap:
// тот потребовал бы заново собрать карту URL→файл, продублировав роутинг. Дата билда у всех разом
// обесценивает lastmod. У языковых хабов (`/`, `/en/`, `/ru/`) Article нет: им — самая свежая дата
// страниц их языка (корню — всех), то есть тоже дата контента, а не сборки (#468).
import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const DIST = resolve(here, '../dist');
const ORIGIN = 'https://rules.omnisgm.com';

/**
 * @param {string} url
 * @returns {string}
 */
const fileOf = (url) => {
  const path = url.replace(ORIGIN, '').replace(/^\//, '');
  return resolve(DIST, path.endsWith('/') || path === '' ? `${path}index.html` : path);
};

/**
 * dateModified из JSON-LD страницы (null, если Article на ней нет).
 * @param {string} url
 * @returns {string|null}
 */
function pageDate(url) {
  let html;
  try {
    html = readFileSync(fileOf(url), 'utf8');
  } catch {
    return null;
  }
  const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/);
  if (!ld) return null;
  try {
    /** @type {{'@type'?: string, dateModified?: string}[]} */
    const graph = JSON.parse(ld[1])['@graph'] ?? [];
    const article = graph.find((n) => n['@type'] === 'Article');
    return article?.dateModified ?? null;
  } catch {
    return null;
  }
}

const HUBS = new Set([`${ORIGIN}/`, `${ORIGIN}/en/`, `${ORIGIN}/ru/`]);
/** @type {Record<string, number>} самая свежая дата по языку ('' — по всем) */
const newest = {};
/** @type {Record<string, string>} её исходная запись (с часовым поясом страницы) */
const newestIso = {};
const URL_RE = /<url><loc>([^<]+)<\/loc>(?:<lastmod>[^<]*<\/lastmod>)?/g;

/** @type {{file: string, xml: string}[]} */
const sitemaps = [];
for (const name of readdirSync(DIST)) {
  if (!/^sitemap-\d+\.xml$/.test(name)) continue;
  const file = resolve(DIST, name);
  sitemaps.push({ file, xml: readFileSync(file, 'utf8') });
}
const files = sitemaps.length;

// Первый проход — даты страниц и самые свежие по языку для хабов.
/** @type {Map<string, string|null>} */
const dates = new Map();
for (const { xml } of sitemaps) {
  for (const [, url] of xml.matchAll(URL_RE)) {
    const date = HUBS.has(url) ? null : pageDate(url);
    dates.set(url, date);
    if (!date) continue;
    const lang = url.slice(ORIGIN.length + 1, ORIGIN.length + 3);
    for (const key of ['', lang]) {
      const t = Date.parse(date);
      if (!(t <= newest[key])) {
        newest[key] = t;
        newestIso[key] = date;
      }
    }
  }
}
for (const hub of HUBS) {
  const lang = hub.slice(ORIGIN.length + 1, ORIGIN.length + 3);
  dates.set(hub, newestIso[hub === `${ORIGIN}/` ? '' : lang] ?? null);
}

let stamped = 0;
let missing = 0;
for (const { file, xml } of sitemaps) {
  const out = xml.replace(URL_RE, (_, url) => {
    const date = dates.get(url);
    if (!date) {
      missing++;
      return `<url><loc>${url}</loc>`;
    }
    stamped++;
    return `<url><loc>${url}</loc><lastmod>${date}</lastmod>`;
  });
  writeFileSync(file, out);
}

if (!files) {
  console.error('[sitemap-lastmod] sitemap-N.xml не найден — сборка сломана или не завершена');
  process.exit(1);
}
// Ноль дат — поломка источника (сборка без git-истории, #219), а не «пусто».
if (!stamped) {
  console.error(
    '[sitemap-lastmod] ни одной даты: на страницах нет dateModified.\n' +
      '  Даты приходят из JSON-LD (#219), а туда — из git. Проверь prebuild (gen-content-dates.mjs)\n' +
      '  и глубину клона: в CI нужен actions/checkout с fetch-depth: 0.',
  );
  process.exit(1);
}
// Дата нужна каждому URL: хабы берут её у страниц своего языка (#468), остальные — из своего JSON-LD.
if (missing) {
  console.error(
    `[sitemap-lastmod] без даты ${missing} из ${stamped + missing} URL.\n` +
      '  Проверь, что URL из sitemap ведут на файлы dist и что у страниц на месте JSON-LD с dateModified.',
  );
  process.exit(1);
}
console.log(`[sitemap-lastmod] ${stamped} URL с датой, ${missing} без (файлов sitemap: ${files})`);
