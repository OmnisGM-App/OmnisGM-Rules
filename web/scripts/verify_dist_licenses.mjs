// Лицензии систем по ВСЕМУ dist (#397): у каждой страницы D&D в футере сказано, что SRD изменён
// (CC BY 4.0 §3(a)(1)(B)); у каждой страницы BRP — какие части Open Game Content (BRP OGL §9) и логотип
// ведёт на BRP SRD, а не на ORC; Legal BRP несёт раздел §9; хаб и главная не заявляют связь BRP с
// Call of Cthulhu / RuneQuest (§8). Плюс корневой LICENSE. e2e (`e2e/legal-pages.spec.ts`) в PR CI не
// ходит — пропажу формул из шелла ловит этот гейт. Литералы свои, не из шелла.
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const WEB = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DIST = join(WEB, 'dist');
const DND = {
  en: 'Converted to Markdown, split into pages and cross-linked by OmnisGM.',
  ru: 'Перевод на русский, конвертация в Markdown, разбивка на страницы и перекрёстные ссылки — OmnisGM.',
};
const BRP = {
  en: 'The rules text on these pages is Open Game Content; the site design, navigation, images and code are not.',
  ru: 'Текст правил на этих страницах, включая перевод, — Open Game Content; оформление сайта, навигация, картинки и код — нет.',
};
const BRP_LOGO = '<a class="rd-attrib-logo" href="https://www.chaosium.com/brp-system-reference-document/"';
const BRP_LEGAL = { en: 'Open Game Content on OmnisGM Rules (Section 9)', ru: 'Open Game Content на OmnisGM Rules (раздел 9)' };

/** Все index.html под каталогом. @returns {Generator<string>} */
function* pages(/** @type {string} */ dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) yield* pages(p);
    else if (e.name === 'index.html') yield p;
  }
}

/** Ошибки одной страницы по её пути `en/dnd/…/index.html`. Экспорт — для самопроверки ниже. */
export function licenseProblems(/** @type {string} */ rel, /** @type {string} */ html) {
  const m = rel.match(/^(en|ru)\/(dnd|brp)\//);
  if (!m || !html.includes('class="rd-attrib"')) return [];
  const [, lang, sys] = /** @type {[string, 'en' | 'ru', 'dnd' | 'brp']} */ (/** @type {unknown} */ (m));
  const out = [];
  if (sys === 'dnd' && !html.includes(DND[lang])) out.push('нет фразы о модификациях SRD');
  if (sys === 'brp') {
    if (!html.includes(BRP[lang])) out.push('нет фразы об Open Game Content');
    if (!html.includes(BRP_LOGO)) out.push('логотип BRP ведёт не на BRP SRD');
  }
  return out;
}

const errors = [];
// Самопроверка: D&D без фразы и BRP с логотипом на ORC — ошибки; страница вне D&D/BRP — не проверяется.
if (!licenseProblems('en/dnd/x/index.html', '<div class="rd-attrib">x</div>').length) errors.push('самопроверка: D&D без фразы не замечена');
if (!licenseProblems('en/brp/x/index.html', `<div class="rd-attrib">${BRP.en}<a class="rd-attrib-logo" href="https://www.chaosium.com/orclicense/"`).length) errors.push('самопроверка: логотип на ORC не замечен');
if (licenseProblems('en/daggerheart/x/index.html', '<div class="rd-attrib">x</div>').length) errors.push('самопроверка: Daggerheart засчитан');

let dnd = 0, brp = 0;
for (const file of pages(DIST)) {
  const rel = relative(DIST, file);
  const html = readFileSync(file, 'utf8');
  if (/^(en|ru)\/dnd\//.test(rel) && html.includes('class="rd-attrib"')) dnd++;
  if (/^(en|ru)\/brp\//.test(rel) && html.includes('class="rd-attrib"')) brp++;
  for (const p of licenseProblems(rel, html)) errors.push(`${rel}: ${p}`);
}
if (dnd < 1000 || brp < 10) errors.push(`страниц D&D ${dnd}, BRP ${brp} — признак rd-attrib потерян?`);

for (const lang of /** @type {const} */ (['en', 'ru'])) {
  const legal = join(DIST, lang, 'brp/srd-1.0/legal/index.html');
  if (!existsSync(legal) || !readFileSync(legal, 'utf8').includes(BRP_LEGAL[lang])) errors.push(`${lang}/brp/srd-1.0/legal: нет раздела §9`);
  for (const rel of [`${lang}/index.html`, `${lang}/brp/srd-1.0/index.html`]) {
    const main = readFileSync(join(DIST, rel), 'utf8').match(/<main[\s\S]*?<\/main>/)?.[0] ?? '';
    if (/Call of Cthulhu|RuneQuest/.test(main)) errors.push(`${rel}: упоминание Call of Cthulhu / RuneQuest (BRP OGL §8)`);
  }
}

const license = join(WEB, '..', 'LICENSE');
if (!existsSync(license) || !/^MIT License$/m.test(readFileSync(license, 'utf8')) || !readFileSync(license, 'utf8').includes('Copyright (c) 2026 Petr Radilov (OmnisGM)')) {
  errors.push('корневой LICENSE: нет MIT с правообладателем');
}

if (errors.length) {
  console.error(`❌ Лицензии систем в dist: ${errors.length} ошибок\n  ${errors.slice(0, 20).join('\n  ')}`);
  process.exit(1);
}
console.log(`✅ Лицензии систем в dist: D&D ${dnd} стр., BRP ${brp} стр., Legal BRP §9, без CoC/RQ на хабе и главной, LICENSE на месте; 3 самопроверки`);
