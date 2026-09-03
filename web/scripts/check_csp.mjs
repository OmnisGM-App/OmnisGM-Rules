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
const BASE = process.argv[2] ?? 'https://rules.omnisgm.com';

// Политика — из firebase.json, чтобы скрипт и прод не разъезжались.
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
const context = await browser.newContext();
// Слушатель ставится до любых скриптов страницы — иначе ранние нарушения не увидим.
await context.addInitScript(() => {
  window.__cspViolations = [];
  document.addEventListener('securitypolicyviolation', (e) => {
    window.__cspViolations.push({
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
  const v = await page.evaluate(() => window.__cspViolations ?? []);
  console.log(`  ${served && !v.length ? '✔' : '✗'} оффлайн из кэша — /ru/ (отдалась: ${served ? 'да' : 'нет'}${v.length ? `, нарушений: ${v.length}` : ''})`);
  await context.setOffline(false);
  await page.close();
  return v.map((x) => ({ ...x, page: '/ru/ (оффлайн)' }));
}

const all = [];
for (const p of PAGES) {
  const page = await context.newPage();
  await page.goto(BASE + p.url, { waitUntil: 'networkidle' });
  if (p.search) {
    await page.locator('input[type="text"]').first().fill(p.search);
    await page.waitForTimeout(2500); // Pagefind грузит воркер, wasm и индексы
  }
  const v = await page.evaluate(() => window.__cspViolations ?? []);
  console.log(`  ${v.length ? '✗' : '✔'} ${p.what} — ${p.url}${v.length ? ` (нарушений: ${v.length})` : ''}`);
  all.push(...v.map((x) => ({ ...x, page: p.url })));
  await page.close();
}
all.push(...(await offlineRun()));
await browser.close();

if (!all.length) {
  console.log('\n✓ Нарушений CSP нет — политику можно держать в enforce.');
  process.exit(0);
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
