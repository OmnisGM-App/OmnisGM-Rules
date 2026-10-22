// Картинки сущностей по собранному dist (#407): страница сущности с `image` в API показывает портрет,
// og:image — та же картинка 512×512, карточка `summary`. До #407 шаблоны видов, рас, предысторий и черт
// картинку не выводили, а CI молчал: e2e (`e2e/entity-images.spec.ts`) в PR CI не ходит.
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { imagePages } from './entity-image-pages.mjs';

const WEB = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DIST = join(WEB, 'dist');
const SIZE = '512';

const { pages, missing } = imagePages(join(WEB, 'src/data/api'));
const errors = missing.map((json) => `${json}: ни у одной сущности нет image`);
if (!pages.length) errors.push('нет ни одной страницы с картинкой — проверять нечего');

const meta = (/** @type {string} */ html, /** @type {string} */ attr, /** @type {string} */ name) =>
  new RegExp(`<meta\\b[^>]*${attr}="${name}"[^>]*content="([^"]*)"`).exec(html)?.[1]
  ?? new RegExp(`<meta\\b[^>]*content="([^"]*)"[^>]*${attr}="${name}"`).exec(html)?.[1];

for (const { url, image } of pages) {
  const file = join(DIST, url, 'index.html');
  if (!existsSync(file)) { errors.push(`${url}: страницы нет в dist`); continue; }
  const html = readFileSync(file, 'utf8');
  const src = new URL(image).pathname;
  const img = /<img\b[^>]*class="ent-portrait"[^>]*>/.exec(html)?.[0];
  if (!img) errors.push(`${url}: нет портрета .ent-portrait`);
  else if (!img.includes(`src="${src}"`)) errors.push(`${url}: портрет не ${src}: ${img}`);
  if (meta(html, 'property', 'og:image') !== image) errors.push(`${url}: og:image «${meta(html, 'property', 'og:image')}», ожидался «${image}»`);
  for (const side of ['width', 'height']) {
    const v = meta(html, 'property', `og:image:${side}`);
    if (v !== SIZE) errors.push(`${url}: og:image:${side} «${v}», ожидался ${SIZE}`);
  }
  const card = meta(html, 'name', 'twitter:card');
  if (card !== 'summary') errors.push(`${url}: twitter:card «${card}», ожидался summary — широкая карточка обрежет квадрат`);
}

if (errors.length) {
  console.error(`❌ Картинки сущностей по dist: ${errors.length} ошибок\n  ${errors.join('\n  ')}`);
  process.exit(1);
}
console.log(`✅ Картинки сущностей по dist: ${pages.length} страниц с портретом и og:image 512×512`);
