// Инвентаризация нарушений CSP на живых страницах (issue #225).
//
// Зачем отдельный скрипт, а не «посмотреть в консоли»: нарушения CSP пишет САМ браузер, и
// инструментами чтения консоли они не видны (проверено — тред #225). Единственный надёжный
// способ — слушать событие `securitypolicyviolation`, причём слушатель обязан появиться ДО
// скриптов страницы, иначе первые же нарушения пройдут мимо. Отсюда addInitScript.
//
// Отдельная причина гонять по ПРОДУ, а не по локальной сборке: часть источников появляется
// только на эдже — Cloudflare вставляет свой beacon (static.cloudflareinsights.com) в HTML
// браузерным запросам, в origin-ответе его нет. Локальный прогон такое не поймает никогда.
//
// Молчаливая слепота, из-за которой скрипт два дня печатал «нарушений нет» при 21 живом
// нарушении (#325): на машине с адблоком `mc.yandex.ru` не резолвится вовсе, Метрика не
// стартует — и нарушать нечего. Поэтому загрузка счётчика теперь ПРОВЕРЯЕТСЯ: без неё
// вердикт объявляется неполным, а в CI (адблока там нет) это красное.
//
//   node scripts/check_csp.mjs                      # прод
//   node scripts/check_csp.mjs http://localhost:4321 # локальная сборка (CSP подставим сами)
//   4321 — порт слота 0; при OMNISGM_SLOT=N preview слушает 4321 + N*10 (см. e2e/ports.ts)
//
// Выход 1, если нашлись нарушения, не покрытые политикой.
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';

const here = dirname(fileURLToPath(import.meta.url));

/**
 * Нарушения CSP пишет БРАУЗЕР, и API консоли их не видит — их ловит слушатель
 * `securitypolicyviolation` на самой странице и копит в `window`. Отсюда и объявление:
 * поле нештатное, но именно оно — канал доставки (#225).
 * @typedef {{directive: string, blocked: string, source: string, disposition: string, page?: string}} CspViolation
 */

const BASE = process.argv[2] ?? 'https://rules.omnisgm.com';

// Политика — из firebase.json, чтобы скрипт и прод не разъезжались.
/** @type {{headers: {headers: {key: string, value: string}[]}[]}} */
const hosting = JSON.parse(readFileSync(resolve(here, '../../firebase.json'), 'utf8')).hosting;
const cspHeader = hosting.headers[0].headers.find((h) => h.key.startsWith('Content-Security-Policy'));
if (!cspHeader) {
  console.error('В firebase.json нет заголовка Content-Security-Policy — проверять нечего.');
  process.exit(1);
}
console.log(`Политика из firebase.json: ${cspHeader.key}`);

// Страницы разных шаблонов + сценарий поиска (Pagefind тянет воркер и wasm — самое рисковое место).
const PAGES = [
  { url: '/ru/', what: 'языковой хаб RU' },
  { url: '/en/dnd/srd-5.2/playing-the-game/', what: 'глава EN' },
  { url: '/ru/dnd/srd-5.2/monsters-a-z/aboleth/', what: 'сущность с портретом RU' },
  { url: '/en/dnd/srd-5.2/spells/fireball/', what: 'сущность с иконкой EN', search: 'dragon' },
  { url: '/ru/dnd/srd-5.2/spells/all/', what: 'хаб-справочник RU' },
];

const browser = await chromium.launch();
/**
 * Нарушения, накопленные страницей.
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<CspViolation[]>}
 */
const violationsOf = (page) =>
  page.evaluate(() => /** @type {any} */ (window).__cspViolations ?? []);

const context = await browser.newContext();

// Загрузился ли счётчик. Считаем по УСПЕШНОМУ ответу его хоста, а не по факту запроса:
// адблок режет запрос на резолве, и «запрос был» — не то же самое, что «скрипт выполнился».
const analytics = { loaded: new Set(), failed: new Map() };
const isCounter = (/** @type {string} */ url) => /^https:\/\/(mc\.yandex\.[a-z]+|www\.googletagmanager\.com)\//.test(url);
context.on('response', (r) => {
  if (isCounter(r.url()) && r.status() < 400) analytics.loaded.add(new URL(r.url()).host);
});
context.on('requestfailed', (r) => {
  // Причину запоминаем ПЕРВУЮ: оффлайн-прогон ниже сам рвёт сеть, и его
  // `ERR_INTERNET_DISCONNECTED` затёр бы настоящую («адблок режет хост»).
  const host = isCounter(r.url()) ? new URL(r.url()).host : null;
  if (host && !analytics.failed.has(host)) analytics.failed.set(host, r.failure()?.errorText ?? 'неизвестно');
});
// Слушатель ставится до любых скриптов страницы — иначе ранние нарушения не увидим.
await context.addInitScript(() => {
  // Каст двойной, и второй слой обязателен: `any` на `window` делает `any` ВСЮ цепочку, и
  // опечатка в `.push` или в имени поля записи проходила бы молча — то есть накопитель
  // молча возвращал бы пустой массив, а скрипт печатал «нарушений нет» при живом нарушении
  // (ревью #298). Внутренний каст снимает незнание типа у `window`, внешний возвращает
  // проверку тому, ради чего тайпчек и заводился.
  /** @type {CspViolation[]} */ (/** @type {any} */ (window).__cspViolations = []);
  document.addEventListener('securitypolicyviolation', (e) => {
    /** @type {CspViolation[]} */ (/** @type {any} */ (window).__cspViolations).push({
      directive: e.effectiveDirective || e.violatedDirective,
      blocked: e.blockedURI,
      disposition: e.disposition,
      source: e.sourceFile ?? '',
    });
  });
});
// Локальная сборка отдаётся без заголовков хостинга — подставляем ту же политику сами,
// чтобы прогон по localhost проверял ровно то, что уедет на прод.
if (!BASE.startsWith('https://rules.omnisgm.com')) {
  await context.route('**/*', async (route) => {
    const res = await route.fetch();
    const headers = { ...res.headers() };
    if ((headers['content-type'] ?? '').includes('text/html')) headers[cspHeader.key.toLowerCase()] = cspHeader.value;
    await route.fulfill({ response: res, headers });
  });
}

// Оффлайн-PWA: страницы отдаёт service worker из Cache Storage. Заголовки хранятся вместе
// с ответом, то есть политика там та же — но проверить надо не это, а что в оффлайне ничего
// не начинает ломиться наружу (аналитика уходит в очередь, шрифты и wasm — из кэша).
async function offlineRun() {
  const page = await context.newPage();
  await page.goto(BASE + '/ru/', { waitUntil: 'networkidle' });
  const sw = await page.evaluate(async () => {
    if (!('serviceWorker' in navigator)) return 'нет serviceWorker';
    const reg = await navigator.serviceWorker.ready.catch(() => null);
    return reg?.active ? 'активен' : 'не активировался';
  });
  if (sw !== 'активен') {
    console.log(`  — оффлайн-прогон пропущен: service worker ${sw}`);
    await page.close();
    return [];
  }
  await context.setOffline(true);
  let served = false;
  try {
    await page.reload({ waitUntil: 'domcontentloaded' });
    served = await page.locator('main').first().isVisible();
  } catch (err) {
    console.log(`  ✗ оффлайн: страница не отдалась из кэша (${String(err).split('\n')[0]})`);
  }
  const v = await violationsOf(page);
  console.log(`  ${served && !v.length ? '✔' : '✗'} оффлайн из кэша — /ru/ (отдалась: ${served ? 'да' : 'нет'}${v.length ? `, нарушений: ${v.length}` : ''})`);
  await context.setOffline(false);
  await page.close();
  return v.map((x) => ({ ...x, page: '/ru/ (оффлайн)' }));
}

/** @type {CspViolation[]} */
const all = [];
for (const p of PAGES) {
  const page = await context.newPage();
  await page.goto(BASE + p.url, { waitUntil: 'networkidle' });
  if (p.search) {
    await page.locator('input[type="text"]').first().fill(p.search);
    await page.waitForTimeout(2500); // Pagefind грузит воркер, wasm и индексы
  }
  const v = await violationsOf(page);
  console.log(`  ${v.length ? '✗' : '✔'} ${p.what} — ${p.url}${v.length ? ` (нарушений: ${v.length})` : ''}`);
  all.push(...v.map((x) => ({ ...x, page: p.url })));
  await page.close();
}
all.push(...(await offlineRun()));
await browser.close();

// Счётчики, которых не было в эфире, из вердикта НЕ выпадают молча: их источники не
// проверены ничем, и «нарушений нет» про них ничего не значит (#325).
const silent = ['mc.yandex.ru', 'www.googletagmanager.com'].filter((h) => !analytics.loaded.has(h));
if (silent.length) {
  const why = silent.map((h) => `${h} (${analytics.failed.get(h) ?? 'ответа не было'})`).join(', ');
  console.error(`\n⚠ Аналитика не загрузилась: ${why}`);
  console.error('  Её источники этим прогоном НЕ проверены. Обычная причина локально — адблок;');
  console.error('  в CI адблока нет, поэтому там это поломка сниппета или недоступность сервиса.');
}
const silentIsFatal = silent.length > 0 && !!process.env.CI;

if (!all.length && !silentIsFatal) {
  console.log(`\n✓ Нарушений CSP нет${silent.length ? ' среди проверенного (см. предупреждение выше)' : ' — политику можно держать в enforce.'}`);
  process.exit(0);
}
if (!all.length) {
  console.error('\n❌ Вердикт неполон в CI — считаем красным.');
  process.exit(1);
}
// Группируем по «директива + хост»: один и тот же источник обычно бьётся на всех страницах.
const groups = new Map();
for (const v of all) {
  const host = v.blocked.startsWith('http') ? new URL(v.blocked).origin : v.blocked;
  const key = `${v.directive} ← ${host}`;
  if (!groups.has(key)) groups.set(key, { n: 0, disp: v.disposition, example: v.blocked, pages: new Set() });
  const g = groups.get(key);
  g.n++; g.pages.add(v.page);
}
console.error(`\n❌ Нарушений CSP: ${all.length} (${groups.size} источников)`);
for (const [key, g] of [...groups.entries()].sort((a, b) => b[1].n - a[1].n)) {
  console.error(`  ${key} — ${g.n} шт, страниц ${g.pages.size}, режим «${g.disp}»`);
  console.error(`    напр. ${g.example}`);
}
process.exit(1);
