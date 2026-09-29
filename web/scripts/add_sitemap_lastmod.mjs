// lastmod в sitemap (issue #221) — postbuild, сразу после astro build.
// Дата — из САМОЙ собранной страницы (`dateModified` JSON-LD, #219), а не serialize в @astrojs/sitemap:
// тот потребовал бы заново собрать карту URL→файл, продублировав роутинг. Дата билда у всех разом
// обесценивает lastmod. Страницы без Article (языковые хабы) остаются без `lastmod`.
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

let files = 0;
let stamped = 0;
let missing = 0;

for (const name of readdirSync(DIST)) {
  if (!/^sitemap-\d+\.xml$/.test(name)) continue;
  files++;
  const file = resolve(DIST, name);
  const xml = readFileSync(file, 'utf8');
  const out = xml.replace(/<url><loc>([^<]+)<\/loc>(?:<lastmod>[^<]*<\/lastmod>)?/g, (_, url) => {
    const date = pageDate(url);
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
// Без даты законно только языковые хабы; много таких — поехала маршрутизация или шаблон.
const share = stamped / (stamped + missing);
if (share < 0.99) {
  console.error(
    `[sitemap-lastmod] дата есть только у ${stamped} из ${stamped + missing} URL (${Math.round(share * 100)}%).\n` +
      '  Ожидались единицы без даты (языковые хабы). Проверь, что URL из sitemap ведут на файлы dist\n' +
      '  и что у страниц на месте JSON-LD с dateModified.',
  );
  process.exit(1);
}
console.log(`[sitemap-lastmod] ${stamped} URL с датой, ${missing} без (файлов sitemap: ${files})`);
