// Замер CLS/LCP на живых страницах (issue #201, последний пункт чеклиста).
//
// Зачем свой скрипт, а не PageSpeed Insights: у публичного PSI-API общая анонимная квота на
// всех, и она регулярно исчерпана («Quota exceeded … per day» — поймано 2026-09-01). Плюс PSI
// меряет одну страницу за прогон и не умеет сравнивать шаблон с картинкой против того же
// шаблона без неё — а нам важно именно это сравнение: портрет добавили, вопрос «не запрыгала
// ли вёрстка».
//
// Что меряем:
//   CLS — сумма layout-shift без recent input (тот же расчёт, что у Core Web Vitals);
//   LCP — последняя запись largest-contentful-paint + какой элемент им оказался;
//   размеры <img> — картинка без width/height это первая причина сдвига, проверяем явно.
//
// Сеть троттлится (Fast 3G): без троттлинга картинка приезжает мгновенно, сдвиг не успевает
// проявиться и прогон всегда зелёный — то есть бесполезен.
//
//   node scripts/check_layout_shift.mjs                       # прод
//   node scripts/check_layout_shift.mjs http://localhost:4321 # локальная сборка
//
// Выход 1, если CLS вышел за порог или у картинки нет размеров.
import { chromium, devices } from '@playwright/test';

const BASE = process.argv[2] ?? 'https://rules.omnisgm.com';

// Порог CLS «Good» по Core Web Vitals. Держим общий: у статичной читалки без рекламы и
// поздних виджетов любой заметный сдвиг — это дефект, а не шум.
const CLS_BUDGET = 0.1;

// Пары «с картинкой / без картинки» одного шаблона — чтобы отличить вклад портрета от
// фонового поведения страницы.
const PAGES = [
  { url: '/en/dnd/srd-5.2/monsters-a-z/aboleth/', what: 'существо с портретом', image: true },
  { url: '/ru/dnd/srd-5.2/monsters-a-z/aboleth/', what: 'существо с портретом RU', image: true },
  { url: '/en/dnd/srd-5.2/spells/fireball/', what: 'заклинание с иконкой', image: true },
  { url: '/en/daggerheart/srd-1.0/adversaries/acid-burrower/', what: 'противник с портретом', image: true },
  { url: '/en/dnd/srd-5.2/magic-items/bag-of-holding/', what: 'сущность без картинки (контроль)', image: false },
  { url: '/en/dnd/srd-5.2/playing-the-game/', what: 'глава правил (контроль)', image: false },
];

const collect = () => {
  window.__cls = 0;
  window.__lcp = null;
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      // hadRecentInput — сдвиг как реакция на действие пользователя, в CLS не входит.
      if (!entry.hadRecentInput) window.__cls += entry.value;
    }
  }).observe({ type: 'layout-shift', buffered: true });
  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    const last = entries[entries.length - 1];
    window.__lcp = { time: last.startTime, el: last.element?.tagName ?? '?', cls: last.element?.className ?? '' };
  }).observe({ type: 'largest-contentful-paint', buffered: true });
};

const browser = await chromium.launch();

// Каждой странице — свой контекст и свой троттлинг. Оба «свой» важны, оба поймал на себе:
// CDP-сессия привязана к вкладке и соседние не замедляет; а общий контекст между страницами
// тащит прогретый HTTP-кэш и, главное, зарегистрированный service worker, который дальше
// отдаёт всё из Cache Storage — LCP выходил 76 мс «по Fast 3G» вместо честных ~800.
const measure = async () => {
  const context = await browser.newContext({ ...devices['Pixel 7'] });
  await context.addInitScript(collect);
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  await cdp.send('Network.enable');
  await cdp.send('Network.emulateNetworkConditions', {
    offline: false, latency: 150, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8,
  });
  return { context, page };
};

const rows = [];
let failed = 0;
for (const p of PAGES) {
  const { context, page } = await measure();
  await page.goto(BASE + p.url, { waitUntil: 'load' });
  // Сдвиги случаются и после load (шрифты, отложенные картинки) — даём им время произойти.
  await page.waitForTimeout(3000);

  const cls = await page.evaluate(() => window.__cls);
  const lcp = await page.evaluate(() => window.__lcp);
  const imgs = await page.$$eval('img', (nodes) =>
    nodes.map((n) => ({ src: n.getAttribute('src'), w: n.getAttribute('width'), h: n.getAttribute('height') })));
  await context.close();

  const sized = imgs.filter((i) => i.w && i.h).length;
  const unsized = imgs.filter((i) => !i.w || !i.h);
  const over = cls > CLS_BUDGET;
  if (over) failed++;
  if (p.image && imgs.length === 0) {
    console.error(`  ✗ ${p.url} — ожидали картинку, а <img> на странице нет`);
    failed++;
  }
  if (unsized.length) {
    console.error(`  ✗ ${p.url} — без width/height: ${unsized.map((i) => i.src).join(', ')}`);
    failed++;
  }
  rows.push({ what: p.what, url: p.url, cls, lcp, imgs: imgs.length, sized });
}

console.log(`\nCLS / LCP, ${BASE}, Pixel 7 + Fast 3G (порог CLS ${CLS_BUDGET}):\n`);
for (const r of rows) {
  const lcp = r.lcp ? `${Math.round(r.lcp.time)} мс (${r.lcp.el}${r.lcp.cls ? '.' + String(r.lcp.cls).split(' ')[0] : ''})` : '—';
  console.log(`  ${r.cls > CLS_BUDGET ? '✗' : '✓'} CLS ${r.cls.toFixed(4).padEnd(8)} LCP ${lcp.padEnd(28)} img ${r.sized}/${r.imgs} с размерами — ${r.what}`);
}

await browser.close();
if (failed) {
  console.error(`\n✗ Проверок не прошло: ${failed}.`);
  process.exit(1);
}
console.log('\n✓ CLS в бюджете, у всех картинок заданы размеры.');
