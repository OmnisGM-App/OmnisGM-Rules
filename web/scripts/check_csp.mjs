// Инвентаризация нарушений CSP на живых страницах (issue #225).
//
// Нарушения пишет САМ браузер, API консоли их не видит — слушаем `securitypolicyviolation` до
// скриптов страницы. По проду: beacon Cloudflare вставляется только на эдже, в origin его нет.
// Слепота с адблоком (#325): Метрика не стартует и нарушать нечего — загрузку счётчиков проверяем.
//   node scripts/check_csp.mjs [http://localhost:<порт preview из e2e/ports.ts>]   # иначе прод
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';

const here = dirname(fileURLToPath(import.meta.url));

/**
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
await context.addInitScript(() => {
  // Двойной каст: внешний возвращает тайпчек накопителю — с голым `any` опечатка в `.push` прошла бы молча.
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
// Локальная сборка — без заголовков хостинга: подставляем политику сами.
if (!BASE.startsWith('https://rules.omnisgm.com')) {
  await context.route('**/*', async (route) => {
    const res = await route.fetch();
    const headers = { ...res.headers() };
    if ((headers['content-type'] ?? '').includes('text/html')) headers[cspHeader.key.toLowerCase()] = cspHeader.value;
    await route.fulfill({ response: res, headers });
  });
}

// Оффлайн-PWA: в оффлайне ничего не должно ломиться наружу (аналитика — в очередь, шрифты и wasm — из кэша).
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

// Счётчики вне эфира не выпадают из вердикта молча (#325). Ждём только те, чей ID есть в сборке
// прода: без ID блок не грузится (`analytics-client.ts`).
const EXPECTED = ['mc.yandex.ru', 'www.googletagmanager.com'];
const silent = EXPECTED.filter((h) => !analytics.loaded.has(h));
if (silent.length) {
  const why = silent.map((h) => `${h} (${analytics.failed.get(h) ?? 'ответа не было'})`).join(', ');
  console.error(`\n⚠ Аналитика не загрузилась: ${why}`);
  console.error('  Её источники этим прогоном НЕ проверены. Причины, по убыванию вероятности:');
  console.error('  локально — адблок; счётчик не включён в сборку (нет PUBLIC_*-ID);');
  console.error('  на проде — поломка сниппета или недоступность сервиса.');
}
console.error(
  `${silent.length ? '' : '\n'}⚠ Вердикт не покрывает static.cloudflareinsights.com: beacon вставляет сам Cloudflare,` +
    ' его наличие — состояние панели CF, а не репозитория.',
);
// Красное — только по ПРОДУ: локально аналитика штатно выключена.
const silentIsFatal = silent.length > 0 && !!process.env.CI && BASE.startsWith('https://rules.omnisgm.com');

if (!all.length && !silentIsFatal) {
  console.log(`\n✓ Нарушений CSP нет${silent.length ? ' среди проверенного (см. предупреждение выше)' : ' — политику можно держать в enforce.'}`);
  process.exit(0);
}
if (!all.length) {
  console.error('\n❌ Вердикт неполон на прогоне по проду в CI — считаем красным.');
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
