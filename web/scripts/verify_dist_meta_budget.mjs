// Бюджет мета-тегов по ВСЕМУ собранному dist — issue #185 (сэмпл инвариантов <head> — verify_dist_seo.mjs).
// Нулевые гейты: Article (#219), <h1> (#228), BreadcrumbList (#220); остальные — бюджетные.
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, resolve, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const DIST = resolve(here, '../dist');

// Бюджеты. Опускать по мере починки разделов; поднимать — только с обоснованием в PR.
const BUDGET = {
  dupDescriptionPages: 0,
  // Имя, тип и редакцию лестница в page-title.ts не режет; метка Daggerheart несёт «SRD» (DPCGL §2.5, #166).
  longTitlePages: 17,
  // Страниц с неуникальным <title>. Метка редакции («D&D 2024»/«D&D 2014») специально не
  // выпадает из лестницы — иначе одноимённые страницы 5.1 и 5.2 схлопнутся в дубли.
  dupTitlePages: 0,
  // Остаток — хабы ровно с ОДНОЙ сущностью (#214, #196) и черты с однострочным описанием:
  // дальше не выжать без выдумывания фактов.
  shortDescriptionPages: 62,
};
// Нижняя граница комфортного сниппета: короче — Bing считает description «too short».
const DESCRIPTION_MIN = 110;
const TITLE_LIMIT = 65;
// Разрешённая «недобранность»: если фактическое число упало ниже бюджета более чем на
// SLACK, требуем обновить бюджет — иначе гейт молча перестаёт ловить регрессии.
const SLACK = 25;
// Покрытие — страховка от «гниения» регексп-парсера: ненайденный тег дал бы «дублей 0».
const MIN_COVERAGE = 0.9;

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

// Мини-декод HTML-сущностей: в атрибуте description Astro экранирует &#38; и т.п.,
// а сравнивать дубли нужно по тексту, а не по экранированию.
const decode = (/** @type {string} */ s) =>
  s.replace(/&#(\d+);/g, (/** @type {string} */ _, /** @type {string} */ d) => String.fromCharCode(+d))
    .replace(/&amp;/g, '&').replace(/&quot;/g, '"')
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>');

const byDescription = new Map(); // description → [страницы]
const shortDescriptions = []; // { page, len }
// Article без обязательных полей (#219) и страницы, где JSON-LD вовсе не разобрался.
const ARTICLE_REQUIRED = ['image', 'datePublished', 'dateModified', 'author', 'publisher'];
const brokenArticles = []; // { page, why }
let withArticle = 0;
// Даты — из контента, а не из сборки: единственный dateModified на весь dist = источником стал билд.
const modifiedDates = new Set();
// Крошки (#220) проверяем после обхода: нужен полный список собранных страниц.
const crumbTrails = []; // { page, urls }
const noHeading = []; // страницы без <h1> (#228)
const manyHeadings = []; // и с несколькими — второй H1 размывает тему не меньше, чем его отсутствие
const pagePaths = new Set(); // '/ru/dnd/...' → страница существует в dist
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
  if (page.endsWith('/index.html')) pagePaths.add(page.slice(0, -'index.html'.length));

  const desc = head.match(/<meta\s+name="description"\s+content="([^"]*)"/);
  if (desc) {
    const key = decode(desc[1]).trim();
    if (key) {
      withDescription++;
      if (key.length < DESCRIPTION_MIN) shortDescriptions.push({ page, len: key.length });
      if (!byDescription.has(key)) byDescription.set(key, []);
      byDescription.get(key).push(page);
    }
  }

  // JSON-LD: сам граф — в <head>, но регексп по нему целиком дешевле, чем резать скрипты.
  const ld = head.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/);
  if (ld) {
    let graph = null;
    try {
      graph = JSON.parse(ld[1]);
    } catch {
      brokenArticles.push({ page, why: 'JSON-LD не парсится' });
    }
    const nodes = graph?.['@graph'] ?? [];
    const article = nodes.find((/** @type {any} */ n) => n['@type'] === 'Article');
    const org = nodes.find((/** @type {any} */ n) => n['@type'] === 'Organization');
    if (org && !(Array.isArray(org.sameAs) && org.sameAs.length)) {
      brokenArticles.push({ page, why: 'Organization без sameAs' });
    }
    const crumbs = nodes.find((/** @type {any} */ n) => n['@type'] === 'BreadcrumbList');
    if (crumbs) {
      crumbTrails.push({ page, urls: (crumbs.itemListElement ?? []).map((/** @type {any} */ i) => i.item) });
    }
    if (article) {
      withArticle++;
      const missing = ARTICLE_REQUIRED.filter((k) => !article[k]);
      if (missing.length) brokenArticles.push({ page, why: `Article без ${missing.join(', ')}` });
      if (article.dateModified) modifiedDates.add(article.dateModified);
    }
  }

  const h1count = (html.match(/<h1[\s>]/g) ?? []).length;
  if (h1count === 0) noHeading.push(page);
  else if (h1count > 1) manyHeadings.push({ page, n: h1count });

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

const SITE = 'https://rules.omnisgm.com';
const crumbDup = crumbTrails.filter((t) => new Set(t.urls).size !== t.urls.length);
const crumbDead = [];
for (const t of crumbTrails) {
  for (const u of t.urls) {
    const path = u.startsWith(SITE) ? u.slice(SITE.length) : null;
    if (!path || !pagePaths.has(path)) crumbDead.push({ page: t.page, url: u });
  }
}

const dupGroups = [...byDescription.entries()].filter(([, v]) => v.length > 1);
const dupPages = dupGroups.reduce((n, [, v]) => n + v.length, 0);
const dupTitleGroups = [...byTitle.entries()].filter(([, v]) => v.length > 1);
const dupTitlePages = dupTitleGroups.reduce((n, [, v]) => n + v.length, 0);

// Раздел = первые 4 сегмента пути (/ru/dnd/srd-5.2/monsters-a-z) — для внятного отчёта.
const section = (/** @type {string} */ p) => p.split('/').slice(1, 5).join('/');
const bySection = (/** @type {string[]} */ list) => {
  /** @type {Map<string, number>} */
  const c = new Map();
  for (const p of list) c.set(section(p), (c.get(section(p)) ?? 0) + 1);
  return [...c.entries()].sort((a, b) => b[1] - a[1]);
};

console.log(`Мета-бюджет: обойдено ${pages} страниц dist`);
console.log(`  дубли description: ${dupPages} страниц в ${dupGroups.length} группах (бюджет ${BUDGET.dupDescriptionPages})`);
console.log(`  <title> > ${TITLE_LIMIT} символов: ${longTitles.length} страниц (бюджет ${BUDGET.longTitlePages})`);
console.log(`  дубли <title>: ${dupTitlePages} страниц в ${dupTitleGroups.length} группах (бюджет ${BUDGET.dupTitlePages})`);
console.log(`  description < ${DESCRIPTION_MIN} символов: ${shortDescriptions.length} страниц (бюджет ${BUDGET.shortDescriptionPages})`);
console.log(`  Article в JSON-LD: ${withArticle} страниц, неполных ${brokenArticles.length} (бюджет 0); различных dateModified: ${modifiedDates.size}`);
console.log(`  <h1>: без заголовка ${noHeading.length}, с несколькими ${manyHeadings.length} (бюджет 0/0)`);
console.log(`  BreadcrumbList: ${crumbTrails.length} страниц, дублей URL в трейле ${crumbDup.length}, ссылок в никуда ${crumbDead.length} (бюджет 0/0)`);

/** @type {string[]} */
const errors = [];

// Сначала — покрытие: без него все числа ниже бессмысленны.
for (const [what, found] of /** @type {[string, number][]} */ ([['description', withDescription], ['<title>', withTitle]])) {
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

if (shortDescriptions.length > BUDGET.shortDescriptionPages) {
  errors.push(`коротких description: ${shortDescriptions.length} > бюджета ${BUDGET.shortDescriptionPages}`);
  console.error('\n  Самые короткие description:');
  for (const { page, len } of shortDescriptions.slice().sort((a, b) => a.len - b.len).slice(0, 10)) {
    console.error(`    ${len}\t${page}`);
  }
  console.error('\n  По разделам:');
  for (const [s, n] of bySection(shortDescriptions.map((x) => x.page)).slice(0, 10)) console.error(`    ${n}\t${s}`);
} else if (shortDescriptions.length < BUDGET.shortDescriptionPages - SLACK) {
  errors.push(
    `коротких description стало ${shortDescriptions.length} при бюджете ${BUDGET.shortDescriptionPages} — опусти BUDGET.shortDescriptionPages`,
  );
}

// Article — гейт нулевой: половинчатого состояния нет, только сломанный источник (мелкий клон).
if (brokenArticles.length) {
  errors.push(`неполный JSON-LD: ${brokenArticles.length} страниц`);
  console.error('\n  Примеры:');
  for (const { page, why } of brokenArticles.slice(0, 10)) console.error(`    ${why} — ${page}`);
  const noDates = brokenArticles.filter((b) => b.why.includes('datePublished')).length;
  if (noDates) {
    console.error(
      '\n  Даты берутся из коммитов по контентным .md (scripts/gen-content-dates.mjs). Две причины:\n' +
        '   • сборка без git-истории — в CI нужен actions/checkout с fetch-depth: 0;\n' +
        '   • разъехались ключи _sources.json (от generate_api.py --emit-sources) и content-dates.json —\n' +
        '     оба считают путь от src/, и src-root игры обязан лежать прямо в src/{game}.',
    );
  }
}
if (withArticle > 100 && modifiedDates.size < 2) {
  errors.push(
    `dateModified одинаковый на всех ${withArticle} страницах (${[...modifiedDates][0]}) — ` +
      `похоже, даты приехали из сборки, а не из истории контента`,
  );
}

if (noHeading.length) {
  errors.push(`страниц без <h1>: ${noHeading.length}`);
  console.error('\n  Примеры:');
  for (const p of noHeading.slice(0, 10)) console.error(`    ${p}`);
}
if (manyHeadings.length) {
  errors.push(`страниц с несколькими <h1>: ${manyHeadings.length}`);
  for (const { page, n } of manyHeadings.slice(0, 10)) console.error(`    ${n}×h1 — ${page}`);
}

// BreadcrumbList живёт в одном блоке шаблона с Article — покрытие сверяем с ним.
if (crumbDup.length) {
  errors.push(`BreadcrumbList с дублями URL: ${crumbDup.length} страниц`);
  console.error('\n  Примеры трейлов с дублем:');
  for (const t of crumbDup.slice(0, 5)) console.error(`    ${t.page}\n      ${t.urls.join('\n      ')}`);
}
if (crumbDead.length) {
  errors.push(`крошек, ведущих на несобранную страницу: ${crumbDead.length}`);
  for (const { page, url } of crumbDead.slice(0, 5)) console.error(`    ${url} ← ${page}`);
}
if (withArticle > 100 && crumbTrails.length < withArticle) {
  errors.push(
    `BreadcrumbList есть на ${crumbTrails.length} страницах против ${withArticle} с Article — ` +
      `часть страниц осталась без трейла`,
  );
}

// Покрытие Article: если он вдруг исчез со всех страниц, гейт выше промолчит (нечего ломать).
if (withArticle < pages * 0.9) {
  errors.push(`Article найден только на ${withArticle} из ${pages} страниц — шаблон JSON-LD сломан`);
}

if (errors.length) {
  console.error(`\n❌ Мета-бюджет нарушен:`);
  for (const e of errors) console.error(`  • ${e}`);
  process.exit(1);
}
console.log('✓ Мета-бюджет в норме');
