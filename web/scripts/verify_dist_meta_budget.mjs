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
//   4) КОРОТКИЕ description — Bing (правило 118 «Meta descriptions too short», #213) ругался
//      на сниппеты 95–102 символа; нижняя граница комфорта — 110.
//   6) БИТЫЙ BreadcrumbList (#220) — уровни строятся из NAV-дерева, и раньше группе без
//      собственной страницы подставлялась «первая страница-лист внутри»: игра и её первая
//      редакция давали ОДИН URL (дубль позиций 2–3), «Классы» вели на варвара. Гейт нулевой:
//      внутри трейла все URL различны и каждый ведёт на существующую страницу dist.
//   5) НЕПОЛНЫЙ Article в JSON-LD (#219) — без image и дат Google не выдаёт rich-результат
//      вовсе, а даты у нас приезжают из git и на мелком клоне молча исчезают. Гейт нулевой.
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
  // никогда, так что нулём тут не станет. Стало 15 после #166: метка Daggerheart несёт «SRD»
  // (DPCGL §2.5(a) — Name Mark нельзя как заголовок), и двусоставные имена противников
  // («Вулканический дракон: Обсидиановый хищник») вылезли за 65. Бюджет держим на 2 выше факта.
  longTitlePages: 17,
  // Страниц с неуникальным <title>. Метка редакции («D&D 2024»/«D&D 2014») специально не
  // выпадает из лестницы — иначе одноимённые страницы 5.1 и 5.2 схлопнутся в дубли.
  dupTitlePages: 0,
  // Страниц с description короче DESCRIPTION_MIN. Было 936 до #213, стало 774: волна накрыла
  // фолбэк markdown-страниц (164 коротких → 3). Остаток — сущностные страницы, чьи описания
  // строятся из короткого контента (навык BRP в одну строку, заклинание без описания
  // в шапке); это отдельная волна, до неё нулём число не станет.
  // #214, волна 1 (оружие + навыки BRP): 774 → 528. Остаток — хабы, термины rules-glossary
  // и часть снаряжения; они идут второй порцией той же ишьи.
  shortDescriptionPages: 530,
};
// Нижняя граница комфортного сниппета: короче — Bing считает description «too short».
const DESCRIPTION_MIN = 110;
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
const shortDescriptions = []; // { page, len }
// Article без обязательных полей (#219) и страницы, где JSON-LD вовсе не разобрался.
const ARTICLE_REQUIRED = ['image', 'datePublished', 'dateModified', 'author', 'publisher'];
const brokenArticles = []; // { page, why }
let withArticle = 0;
// Инвариант «даты из контента, а не из сборки»: у 6000 страниц не может быть одной даты
// изменения. Ровно один dateModified на весь dist = источником дат стал момент билда.
const modifiedDates = new Set();
// Крошки (#220): собираем трейлы, проверяем после обхода — «ведёт ли URL на страницу» можно
// сказать, только когда известен полный список собранных страниц.
const crumbTrails = []; // { page, urls }
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
    const article = nodes.find((n) => n['@type'] === 'Article');
    const org = nodes.find((n) => n['@type'] === 'Organization');
    if (org && !(Array.isArray(org.sameAs) && org.sameAs.length)) {
      brokenArticles.push({ page, why: 'Organization без sameAs' });
    }
    const crumbs = nodes.find((n) => n['@type'] === 'BreadcrumbList');
    if (crumbs) {
      crumbTrails.push({ page, urls: (crumbs.itemListElement ?? []).map((i) => i.item) });
    }
    if (article) {
      withArticle++;
      const missing = ARTICLE_REQUIRED.filter((k) => !article[k]);
      if (missing.length) brokenArticles.push({ page, why: `Article без ${missing.join(', ')}` });
      if (article.dateModified) modifiedDates.add(article.dateModified);
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

// Разбор крошек: дубли URL внутри одного трейла и ссылки на несуществующие страницы.
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
console.log(`  description < ${DESCRIPTION_MIN} символов: ${shortDescriptions.length} страниц (бюджет ${BUDGET.shortDescriptionPages})`);
console.log(`  Article в JSON-LD: ${withArticle} страниц, неполных ${brokenArticles.length} (бюджет 0); различных dateModified: ${modifiedDates.size}`);
console.log(`  BreadcrumbList: ${crumbTrails.length} страниц, дублей URL в трейле ${crumbDup.length}, ссылок в никуда ${crumbDead.length} (бюджет 0/0)`);

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

// Article — гейт нулевой: поля либо есть у всех, либо сломался источник (напр. мелкий клон
// без git-истории → нет дат). Половинчатого состояния здесь не бывает.
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
// Одна-единственная дата изменения на весь dist означала бы, что источником стал момент
// сборки, а не история контента (см. #219). Порог мягкий: важно «не одна», а не «сколько».
if (withArticle > 100 && modifiedDates.size < 2) {
  errors.push(
    `dateModified одинаковый на всех ${withArticle} страницах (${[...modifiedDates][0]}) — ` +
      `похоже, даты приехали из сборки, а не из истории контента`,
  );
}

// Крошки — гейт нулевой: дубль URL и ссылка в никуда это всегда баг генерации трейла, а не
// «хвост незакрытой волны». Покрытие меряем отдельно: BreadcrumbList есть у всех страниц,
// у которых есть Article (оба живут в одном блоке шаблона).
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
