// Строка о товарных знаках D&D (Table#912) по ВСЕМУ dist: у каждой страницы справочника (её рендерит
// ReaderShell, признак — `rd-content`) в футере стоит строка на языке страницы, на двуязычном корне —
// обе. Плюс раздел Licenses в llms.txt. e2e (`e2e/trademark.spec.ts`) в PR CI не ходит, поэтому пропажу
// строки из шелла ловит этот гейт. Литералы — свои, не из шелла: иначе правка формулы прошла бы сама.
// Там же — <title> каждой страницы Daggerheart по DPCGL §2.5(a) (#446).
import { readFileSync, readdirSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const DIST = resolve(dirname(fileURLToPath(import.meta.url)), '../dist');
const amp = (/** @type {string} */ s) => s.replaceAll('&', '&amp;');
const EN = amp('Dungeons & Dragons and D&D are trademarks of Wizards of the Coast LLC. OmnisGM is an independent project, not affiliated with or endorsed by Wizards of the Coast.');
const RU = amp('Dungeons & Dragons и D&D — товарные знаки Wizards of the Coast LLC. OmnisGM — независимый проект, не связан с Wizards of the Coast и не одобрен ею.');

/** Все index.html под каталогом. @returns {Generator<string>} */
function* pages(/** @type {string} */ dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) yield* pages(p);
    else if (e.name === 'index.html') yield p;
  }
}

/** Ошибка для одной страницы или null. Экспорт — для самопроверки ниже. */
export function trademarkProblem(/** @type {string} */ html, /** @type {boolean} */ bilingual) {
  if (!html.includes('class="rd-content')) return null; // не страница справочника
  const m = html.match(/<div class="rd-tm"[^>]*data-testid="trademark"[^>]*>(.*?)<\/div>/s);
  if (!m) return 'нет строки о товарных знаках';
  const lang = html.match(/<html lang="(en|ru)"/)?.[1];
  const want = bilingual ? `<span class="l-en">${EN}</span><span class="l-ru">${RU}</span>` : lang === 'ru' ? RU : EN;
  return m[1] === want ? null : `строка не та (lang=${lang}): «${m[1].slice(0, 120)}…»`;
}

/**
 * DPCGL §2.5(a) в <title> страницы Daggerheart (#446): марка — только как часть имени источника
 * «Daggerheart SRD», голой её быть не должно. Лестница page-title.ts на длинных именах доходит до
 * короткой ступени (`short ? 'Daggerheart SRD' : …`), которую e2e не посещают и CI не гоняет —
 * поэтому проверяем каждую собранную страницу. Экспорт — для самопроверки ниже.
 */
export function dpcglTitleProblem(/** @type {string} */ title) {
  if (!title.includes('Daggerheart SRD')) return 'в <title> нет «Daggerheart SRD»';
  if (/Daggerheart(?! SRD)/.test(title)) return 'в <title> голая марка «Daggerheart»';
  return null;
}

const errors = [];
if (!dpcglTitleProblem('Вулканический дракон: Обсидиановый хищник — Daggerheart')) errors.push('самопроверка: голая марка в <title> не замечена');
if (!dpcglTitleProblem('Бард — класс · OmnisGM Rules')) errors.push('самопроверка: <title> без источника не замечен');
if (dpcglTitleProblem('Вулканический дракон: Обсидиановый хищник — Daggerheart SRD') !== null) errors.push('самопроверка: короткая ступень засчитана ошибкой');
// Самопроверка: страница без строки и со строкой чужого языка — ошибки; чужая разметка — не страница.
if (!trademarkProblem('<html lang="en"><main class="rd-content">x</main>', false)) errors.push('самопроверка: пропажа строки не замечена');
if (!trademarkProblem(`<html lang="ru"><main class="rd-content"><div class="rd-tm" data-testid="trademark">${EN}</div>`, false)) errors.push('самопроверка: EN-строка на RU-странице не замечена');
if (trademarkProblem('<html lang="en"><body>404</body>', false) !== null) errors.push('самопроверка: страница вне справочника засчитана');

let checked = 0;
let dhTitles = 0;
let dhShortRung = 0;
for (const file of pages(DIST)) {
  const html = readFileSync(file, 'utf8');
  const rel = relative(DIST, file);
  const problem = trademarkProblem(html, rel === 'index.html');
  if (html.includes('class="rd-content')) checked++;
  if (problem) errors.push(`${rel}: ${problem}`);
  if (/^(en|ru)\/daggerheart\//.test(rel.split('\\').join('/'))) {
    const title = html.match(/<title>([^<]*)<\/title>/)?.[1] ?? '';
    dhTitles++;
    if (title.endsWith('Daggerheart SRD')) dhShortRung++;
    const bad = dpcglTitleProblem(title);
    if (bad) errors.push(`${rel}: ${bad} («${title}»)`);
  }
}
if (checked < 1000) errors.push(`страниц справочника всего ${checked} — признак rd-content потерян?`);
if (dhTitles < 300) errors.push(`страниц Daggerheart всего ${dhTitles} — сменился путь /{lang}/daggerheart/?`);

const llms = readFileSync(join(DIST, 'llms.txt'), 'utf8');
for (const phrase of [
  'Dungeons & Dragons and D&D are trademarks of Wizards of the Coast LLC.',
  'not affiliated with or endorsed by Wizards of the Coast',
  'Not affiliated with or endorsed by Chaosium Inc.',
]) if (!llms.includes(phrase)) errors.push(`llms.txt: нет «${phrase}»`);

if (errors.length) {
  console.error(`❌ Товарные знаки в dist: ${errors.length} ошибок\n  ${errors.slice(0, 20).join('\n  ')}`);
  process.exit(1);
}
console.log(`✅ Товарные знаки в dist: строка на месте у ${checked} страниц справочника, llms.txt в порядке; ` +
  `<title> Daggerheart по DPCGL §2.5 у ${dhTitles} страниц (короткая ступень — ${dhShortRung}); 6 самопроверок`);
