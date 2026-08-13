// Бюджет мета-тегов по ВСЕМУ собранному dist — issue #185. В отличие от verify_dist_seo.mjs
// (фиксированный сэмпл по одному slug на тип страницы, проверка инвариантов <head>), здесь
// сплошной обход всех страниц и два количественных гейта:
//
//   1) ДУБЛИ <meta name="description"> — Вебмастер показал 39 дублей; сплошной замер дал
//      520 страниц в 191 группе. Причина: сущностные страницы брали excerpt() первого
//      абзаца/черты («Дракон может дышать воздухом и водой.» — 33 страницы).
//   2) ДЛИННЫЕ <title> — Bing ругался «Title too long» (#172); порог 65 символов.
//
// Гейт — БЮДЖЕТНЫЙ, а не нулевой: чиним разделы волнами (монстры/животные → заклинания →
// магпредметы → …), и до конца волн нули недостижимы. Скрипт валит CI, если стало ХУЖЕ
// бюджета, и требует опустить бюджет, если стало лучше — чтобы починенное не отъехало назад.
//
// Гоняется в CI check-build после astro build, рядом с verify_dist_seo.mjs.
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, resolve, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const DIST = resolve(here, '../dist');

// Бюджеты. Опускать по мере починки разделов; поднимать — только с обоснованием в PR.
const BUDGET = {
  // Страниц, чей description не уникален. Было 520 (191 группа) до волны монстров/животных,
  // стало 113 (56 групп). Остаток — заклинания (58) и магпредметы (55), их чиним следующим
  // PR по #185; в основном это одинаковый текст в 5.1 и 5.2.
  dupDescriptionPages: 125,
  // Страниц с <title> длиннее LIMIT (сейчас 347). Хвост — длинные имена сущностей;
  // упадёт вместе с переработкой шаблонов title во второй части #185.
  longTitlePages: 360,
};
const TITLE_LIMIT = 65;
// Разрешённая «недобранность»: если фактическое число упало ниже бюджета более чем на
// SLACK, требуем обновить бюджет — иначе гейт молча перестаёт ловить регрессии.
const SLACK = 25;

// Рекурсивный обход dist в поисках index.html.
function* htmlFiles(dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = resolve(dir, e.name);
    if (e.isDirectory()) yield* htmlFiles(p);
    else if (e.name.endsWith('.html')) yield p;
  }
}

// Мини-декод HTML-сущностей: в атрибуте description Astro экранирует &#38; и т.п.,
// а сравнивать дубли нужно по тексту, а не по экранированию.
const decode = (s) =>
  s.replace(/&#(\d+);/g, (_, d) => String.fromCharCode(+d))
    .replace(/&amp;/g, '&').replace(/&quot;/g, '"')
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>');

const byDescription = new Map(); // description → [страницы]
const longTitles = []; // { page, len }
let pages = 0;

for (const file of htmlFiles(DIST)) {
  const html = readFileSync(file, 'utf8');
  const head = html.slice(0, html.indexOf('</head>'));
  const page = '/' + relative(DIST, file).split(sep).join('/');
  pages++;

  const desc = head.match(/<meta\s+name="description"\s+content="([^"]*)"/);
  if (desc) {
    const key = decode(desc[1]).trim();
    if (key) {
      if (!byDescription.has(key)) byDescription.set(key, []);
      byDescription.get(key).push(page);
    }
  }

  const title = head.match(/<title>([^<]*)<\/title>/);
  if (title) {
    const len = decode(title[1]).trim().length;
    if (len > TITLE_LIMIT) longTitles.push({ page, len });
  }
}

const dupGroups = [...byDescription.entries()].filter(([, v]) => v.length > 1);
const dupPages = dupGroups.reduce((n, [, v]) => n + v.length, 0);

// Раздел = первые 4 сегмента пути (/ru/dnd/srd-5.2/monsters-a-z) — для внятного отчёта.
const section = (p) => p.split('/').slice(1, 5).join('/');
const bySection = (list) => {
  const c = new Map();
  for (const p of list) c.set(section(p), (c.get(section(p)) ?? 0) + 1);
  return [...c.entries()].sort((a, b) => b[1] - a[1]);
};

console.log(`Мета-бюджет: обойдено ${pages} страниц dist`);
console.log(`  дубли description: ${dupPages} страниц в ${dupGroups.length} группах (бюджет ${BUDGET.dupDescriptionPages})`);
console.log(`  <title> > ${TITLE_LIMIT} символов: ${longTitles.length} страниц (бюджет ${BUDGET.longTitlePages})`);

const errors = [];

if (dupPages > BUDGET.dupDescriptionPages) {
  errors.push(`дубли description: ${dupPages} > бюджета ${BUDGET.dupDescriptionPages}`);
  console.error('\n  Топ дублирующихся description:');
  for (const [text, list] of dupGroups.sort((a, b) => b[1].length - a[1].length).slice(0, 10)) {
    console.error(`    ×${list.length} «${text.slice(0, 90)}…» — напр. ${list[0]}`);
  }
  console.error('\n  По разделам:');
  for (const [s, n] of bySection(dupGroups.flatMap(([, v]) => v)).slice(0, 10)) console.error(`    ${n}\t${s}`);
} else if (dupPages < BUDGET.dupDescriptionPages - SLACK) {
  errors.push(
    `дублей стало ${dupPages} при бюджете ${BUDGET.dupDescriptionPages} — опусти BUDGET.dupDescriptionPages, иначе гейт не ловит регрессии`,
  );
}

if (longTitles.length > BUDGET.longTitlePages) {
  errors.push(`длинных <title>: ${longTitles.length} > бюджета ${BUDGET.longTitlePages}`);
  console.error('\n  Самые длинные <title>:');
  for (const { page, len } of longTitles.sort((a, b) => b.len - a.len).slice(0, 10)) {
    console.error(`    ${len}\t${page}`);
  }
} else if (longTitles.length < BUDGET.longTitlePages - SLACK) {
  errors.push(
    `длинных <title> стало ${longTitles.length} при бюджете ${BUDGET.longTitlePages} — опусти BUDGET.longTitlePages`,
  );
}

if (errors.length) {
  console.error(`\n❌ Мета-бюджет нарушен:`);
  for (const e of errors) console.error(`  • ${e}`);
  process.exit(1);
}
console.log('✓ Мета-бюджет в норме');
