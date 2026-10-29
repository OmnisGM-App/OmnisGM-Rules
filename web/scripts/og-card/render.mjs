// OG-картинка 1200×630 (#466): node scripts/og-card/render.mjs → public/og.png.
// Ручной запуск при смене бренда или текста карточки, не в сборке; знак и шрифты — из @omnisgm-app/brand.
import { chromium } from '@playwright/test';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const BRAND = dirname(createRequire(import.meta.url).resolve('@omnisgm-app/brand/assets/mark.svg'));

// Большой знак фоном — контурный, цвет задаёт `.ghost` через currentColor.
const ghost = readFileSync(join(BRAND, 'mark-outline.svg'), 'utf8');
const html = readFileSync(join(HERE, 'card.html'), 'utf8')
  .replaceAll('__BRAND__', () => pathToFileURL(BRAND).href)
  .replace('__GHOST__', () => ghost);

const page = join(mkdtempSync(join(tmpdir(), 'og-card-')), 'card.html');
writeFileSync(page, html);

const out = process.env.OG_CARD_OUT ?? join(HERE, '..', '..', 'public', 'og.png');
const browser = await chromium.launch();
try {
  const tab = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
  await tab.goto(pathToFileURL(page).href);
  // `fonts.ready` резолвится и после неудачной загрузки, а битый <img> не мешает `load`: без этой
  // проверки переезд файла в ките дал бы карточку на запасных шрифтах и без знака с exit 0.
  const missing = await tab.evaluate(async () => {
    await document.fonts.ready;
    const miss = [...document.fonts].filter((f) => f.status !== 'loaded').map((f) => f.family);
    const img = /** @type {HTMLImageElement} */ (document.querySelector('.brand img'));
    if (!img.complete || !img.naturalWidth) miss.push('mark.svg');
    return miss;
  });
  if (missing.length) throw new Error(`og-card: not loaded: ${missing.join(', ')}`);
  await tab.screenshot({ path: out });
} finally {
  await browser.close();
  rmSync(dirname(page), { recursive: true, force: true });
}
console.log(`✔ ${out}`);
