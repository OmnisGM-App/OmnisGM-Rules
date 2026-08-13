// Бюджет мета-тегов по ВСЕМУ собранному dist — issue #185. В отличие от verify_dist_seo.mjs
// (фиксированный сэмпл по одному slug на тип страницы, проверка инвариантов <head>), здесь
// сплошной обход всех страниц и три количественных гейта:
//
//   1) ДУБЛИ <meta name="description"> — Вебмастер показал 39 дублей; сплошной замер дал
//      520 страниц в 191 группе. Причина: сущностные страницы брали excerpt() первого
//      абзаца/черты («Дракон может дышать воздухом и водой.» — 33 страницы).
//   2) ДЛИННЫЕ <title> — Bing ругался «Title too long» (#172); порог 65 символов.
//   3) ДУБЛИ <title> — до шаблонов из page-title.ts глава и хаб «all» различались только
//      разделителем (· против —), то есть были дублями по существу.
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
  // Страниц, чей description не уникален. Было 520 (191 группа) до волн монстров/животных
  // и заклинаний/магпредметов, стало 0 — теперь гейт нулевой: любой дубль валит CI.
  dupDescriptionPages: 0,
  // Страниц с <title> длиннее LIMIT. Было 567 до шаблонов title, стало 13 — хвост из длинных
  // имён сущностей: имя, тип и редакцию лестница укорачивания в page-title.ts не режет
  // никогда, так что нулём тут не станет.
  longTitlePages: 15,
  // Страниц с неуникальным <title>. Метка редакции («D&D 2024»/«D&D 2014») специально не
  // выпадает из лестницы — иначе одноимённые страницы 5.1 и 5.2 схлопнутся в дубли.
  dupTitlePages: 0,
};
const TITLE_LIMIT = 65;
// Разрешённая «недобранность»: если фактическое число упало ниже бюджета более чем на
// SLACK, требуем обновить бюджет — иначе гейт молча перестаёт ловить регрессии.
const SLACK = 25;
// Страховка от «гниения» парсера: теги ищутся регекспами, и если шаблон <head> сменит
// порядок атрибутов или кавычки, они молча перестанут находиться. Тогда «дублей 0» означало
// бы не порядок, а сломанный парсер, а гейт вместо этого потребовал бы опустить бюджет и
// увёл бы диагностику не туда. Поэтому требуем покрытия: тег обязан находиться почти везде.
const MIN_COVERAGE = 0.9;

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
const byTitle = new Map(); // title → [страницы]
const longTitles = []; // { page, len }
let pages = 0;
let withDescription = 0;
let withTitle = 0;

for (const file of htmlFiles(DIST)) {
  const html = readFileSync(file, 'utf8');
  const head = html.slice(0, html.indexOf('</head>'));
  const page = '/' + relative(DIST, file).split(sep).join('/');
  pages++;

  const desc = head.match(/<meta\s+name="description"\s+content="([^"]*)"/);
  if (desc) {
    const key = decode(desc[1]).trim();
    if (key) {
      withDescription++;
      if (!byDescription.has(key)) byDescription.set(key, []);
      byDescription.get(key).push(page);
    }
  }

  const title = head.match(/<title>([^<]*)<\/title>/);
  if (title) {
    const text = decode(title[1]).trim();
    if (text.length > TITLE_LIMIT) longTitles.push({ page, len: text.length });
    if (text) {
      withTitle++;
      if (!byTitle.has(text)) byTitle.set(text, []);
      byTitle.get(text).push(page);
    }
  }
}

const dupGroups = [...byDescription.entries()].filter(([, v]) => v.length > 1);
const dupPages = dupGroups.reduce((n, [, v]) => n + v.length, 0);
const dupTitleGroups = [...byTitle.entries()].filter(([, v]) => v.length > 1);
const dupTitlePages = dupTitleGroups.reduce((n, [, v]) => n + v.length, 0);

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
console.log(`  дубли <title>: ${dupTitlePages} страниц в ${dupTitleGroups.length} группах (бюджет ${BUDGET.dupTitlePages})`);

const errors = [];

// Сначала — покрытие: без него все числа ниже бессмысленны.
for (const [what, found] of [['description', withDescription], ['<title>', withTitle]]) {
  const share = pages ? found / pages : 0;
  if (share < MIN_COVERAGE) {
    errors.push(
      `${what} найден только на ${found} из ${pages} страниц (${Math.round(share * 100)}%) — ` +
        `похоже, сломался парсер в этом скрипте, а не мета в шаблонах. Числа ниже не читай.`,
    );
  }
}

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

if (dupTitlePages > BUDGET.dupTitlePages) {
  errors.push(`дубли <title>: ${dupTitlePages} > бюджета ${BUDGET.dupTitlePages}`);
  console.error('\n  Топ дублирующихся <title>:');
  for (const [text, list] of dupTitleGroups.sort((a, b) => b[1].length - a[1].length).slice(0, 10)) {
    console.error(`    ×${list.length} «${text}» — напр. ${list[0]}`);
  }
} else if (dupTitlePages < BUDGET.dupTitlePages - SLACK) {
  errors.push(
    `дублей <title> стало ${dupTitlePages} при бюджете ${BUDGET.dupTitlePages} — опусти BUDGET.dupTitlePages`,
  );
}

if (errors.length) {
  console.error(`\n❌ Мета-бюджет нарушен:`);
  for (const e of errors) console.error(`  • ${e}`);
  process.exit(1);
}
console.log('✓ Мета-бюджет в норме');
