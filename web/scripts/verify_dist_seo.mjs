// SEO-мета по собранному dist — issue #22, этап 3. Скриптовая проверка БЕЗ Playwright:
// читаем HTML фиксированного детерминированного сэмпла (по одному slug на тип страницы, EN+RU)
// и проверяем инварианты <head>. Гоняется в CI check-build ПОСЛЕ astro build (dist уже собран).
//
// SEO-мета генерят Astro-шаблоны/лейауты (web/src), а НЕ markdown-контент (src/**), поэтому
// проверка живёт в check-build (триггерится на web/**), а не в content.yml (гейт по src/**).
//
// Проверяем на каждой странице:
//   • ровно один <link rel="canonical">, абсолютный на https://rules.omnisgm.com и равный
//     собственному URL страницы (правильные язык и путь);
//   • hreflang-тройка en/ru/x-default; en/ru — абсолютные и ведут на РЕАЛЬНО существующие в dist
//     страницы (взаимные ссылки не битые);
//   • ≥1 JSON-LD блок, каждый парсится JSON.parse;
//   • непустой <title>, уникальный внутри сэмпла;
//   • нет noindex (allowlist noindex-страниц пуст после снятия с глоссариев в #106).
import { readFileSync, existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const DIST = resolve(here, '../dist');
const ORIGIN = 'https://rules.omnisgm.com';

// Фиксированный сэмпл: «хвост» URL после /{lang}/ (пусто = лендинг). По одному на тип страницы.
const SAMPLE = [
  { type: 'landing', tail: '' },
  { type: 'chapter', tail: 'dnd/srd-5.2/classes/fighter/' },
  { type: 'spell', tail: 'dnd/srd-5.2/spells/fireball/' },
  { type: 'monster', tail: 'dnd/srd-5.2/monsters-a-z/aboleth/' },
  { type: 'animal', tail: 'dnd/srd-5.2/animals/hippopotamus/' },
  { type: 'feat', tail: 'dnd/srd-5.2/feats/boon-of-fate/' },
  { type: 'glossary', tail: 'dnd/srd-5.2/rules-glossary/' },
  { type: 'spell-hub-class', tail: 'dnd/srd-5.2/spells/class/wizard/' },
  { type: 'spell-hub-level', tail: 'dnd/srd-5.2/spells/level/3/' },
];
const LANGS = ['en', 'ru'];
// Страницы, где noindex ЛЕГИТИМЕН (сейчас пусто — глоссарии переоткрыты в #106).
const NOINDEX_ALLOW = new Set();

const errors = [];
const titles = new Map(); // title → "lang tail" (проверка уникальности)

const distFile = (lang, tail) => resolve(DIST, lang, tail, 'index.html');
const urlFor = (lang, tail) => `${ORIGIN}/${lang}/${tail}`;
// URL rules.omnisgm.com → путь файла в dist (для проверки существования взаимных ссылок).
const urlToDist = (url) => {
  if (!url.startsWith(ORIGIN + '/')) return null;
  let p = url.slice(ORIGIN.length + 1); // «en/dnd/.../» или «» (корень)
  return resolve(DIST, p, 'index.html');
};

for (const lang of LANGS) {
  for (const { type, tail } of SAMPLE) {
    const id = `[${lang}/${type}] /${lang}/${tail}`;
    const file = distFile(lang, tail);
    if (!existsSync(file)) {
      errors.push(`${id}: страница отсутствует в dist (${file}) — тип страницы исчез?`);
      continue;
    }
    const html = readFileSync(file, 'utf8');
    const head = html.slice(0, html.indexOf('</head>'));

    // — title —
    const titleM = head.match(/<title>([^<]*)<\/title>/);
    const title = titleM && titleM[1].trim();
    if (!title) errors.push(`${id}: пустой или отсутствующий <title>`);
    else if (titles.has(title)) errors.push(`${id}: <title> «${title}» не уникален (уже у ${titles.get(title)})`);
    else titles.set(title, `${lang}/${tail || 'landing'}`);

    // — canonical —
    const canon = [...head.matchAll(/<link\s+rel="canonical"\s+href="([^"]*)"/g)].map((m) => m[1]);
    if (canon.length !== 1) {
      errors.push(`${id}: ожидался ровно один canonical, найдено ${canon.length}`);
    } else {
      const want = urlFor(lang, tail);
      if (canon[0] !== want) errors.push(`${id}: canonical=${canon[0]}, ожидался ${want}`);
    }

    // — hreflang-тройка —
    const alts = [...head.matchAll(/<link\s+rel="alternate"\s+hreflang="([^"]*)"\s+href="([^"]*)"/g)];
    const byLang = new Map(alts.map((m) => [m[1], m[2]]));
    for (const need of ['en', 'ru', 'x-default']) {
      if (!byLang.has(need)) errors.push(`${id}: нет hreflang="${need}"`);
    }
    // en/ru альтернативы обязаны вести на реально существующие страницы dist.
    for (const need of ['en', 'ru']) {
      const href = byLang.get(need);
      if (!href) continue;
      if (!href.startsWith(ORIGIN + '/')) { errors.push(`${id}: hreflang="${need}" href не абсолютный: ${href}`); continue; }
      const target = urlToDist(href);
      if (!target || !existsSync(target)) errors.push(`${id}: hreflang="${need}" ведёт на несуществующую страницу: ${href}`);
    }

    // — JSON-LD —
    const blocks = [...head.matchAll(/<script\s+type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
    if (blocks.length === 0) errors.push(`${id}: нет JSON-LD блока`);
    blocks.forEach((b, i) => {
      try { JSON.parse(b); } catch (e) { errors.push(`${id}: JSON-LD блок #${i + 1} не парсится: ${e.message}`); }
    });

    // — noindex —
    const robots = [...head.matchAll(/<meta\s+name="robots"\s+content="([^"]*)"/g)].map((m) => m[1].toLowerCase());
    const hasNoindex = robots.some((c) => c.includes('noindex'));
    if (hasNoindex && !NOINDEX_ALLOW.has(tail)) errors.push(`${id}: noindex, а страница должна индексироваться`);
  }
}

const checked = LANGS.length * SAMPLE.length;
if (errors.length) {
  console.error(`\n❌ SEO-мета: ${errors.length} проблем(ы) на ${checked} страницах сэмпла:\n`);
  for (const e of errors) console.error(`  • ${e}`);
  process.exit(1);
}
console.log(`✓ SEO-мета: ${checked} страниц сэмпла (${SAMPLE.length} типов × ${LANGS.length} языка) — canonical/hreflang/JSON-LD/title/noindex в норме`);
