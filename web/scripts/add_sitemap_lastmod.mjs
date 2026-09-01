// lastmod в sitemap (issue #221) — postbuild, сразу после astro build.
//
// Зачем: в sitemap не было ни одного `lastmod`, то есть краулеру нечем отличить свежую правку
// от страницы, которая не менялась год. Дата билда у всех записей разом такой сигнал не даёт,
// а обесценивает: после каждого деплоя «обновилось всё», и Google перестаёт верить lastmod.
//
// Откуда дата: из САМОЙ СОБРАННОЙ СТРАНИЦЫ — `dateModified` в её JSON-LD (#219), а он приходит
// из истории git по исходному markdown. Так мы не повторяем ни маршрутизацию, ни карту
// «URL → исходный файл»: sitemap и разметка страницы говорят одно и то же по построению.
// Альтернатива (serialize в @astrojs/sitemap) потребовала бы собрать URL→файл заново,
// продублировав логику роутинга — ровно тот дубль, на котором тут уже обжигались.
//
// Идемпотентно: повторный запуск не плодит теги. Страницы без `dateModified` (языковые хабы,
// у них нет Article) остаются без `lastmod` — это законно, отсутствие лучше выдумки.
import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const DIST = resolve(here, '../dist');
const ORIGIN = 'https://rules.omnisgm.com';

/** Путь к HTML-файлу страницы по её URL из sitemap. */
const fileOf = (url) => {
  const path = url.replace(ORIGIN, '').replace(/^\//, '');
  return resolve(DIST, path.endsWith('/') || path === '' ? `${path}index.html` : path);
};

/** dateModified из JSON-LD страницы (null, если Article на ней нет). */
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
    const article = (JSON.parse(ld[1])['@graph'] ?? []).find((n) => n['@type'] === 'Article');
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
// Ноль дат — это не «пусто», а поломка источника (сборка без git-истории, см. #219).
// Дальше по конвейеру такой sitemap уехал бы молча, поэтому валим сборку здесь.
if (!stamped) {
  console.error(
    '[sitemap-lastmod] ни одной даты: на страницах нет dateModified.\n' +
      '  Даты приходят из JSON-LD (#219), а туда — из git. Проверь prebuild (gen-content-dates.mjs)\n' +
      '  и глубину клона: в CI нужен actions/checkout с fetch-depth: 0.',
  );
  process.exit(1);
}
// Без даты законно остаются только языковые хабы (у них нет Article) — это единицы.
// Если их стало много, значит поехала маршрутизация или шаблон, и sitemap молча обеднел.
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
