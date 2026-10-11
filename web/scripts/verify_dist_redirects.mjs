// Редиректы хостинга против собранного dist (#399): источник 301 на проде недостижим — его страницы в
// сборке быть не должно (иначе она живёт вне навигации и проверок), а цель обязана существовать: 301 в
// пустоту хуже дубля. e2e (`e2e/hosting-redirects.spec.ts`) в PR CI не ходит — инвариант держит этот гейт.
import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { hostingRedirects } from '../src/lib/hosting-redirects.mjs';

const DIST = resolve(dirname(fileURLToPath(import.meta.url)), '../dist');

/** Файл dist под адресом: страница — `<путь>/index.html`, файл с расширением — как есть. */
const fileOf = (/** @type {string} */ url) =>
  /\.[a-z]+$/.test(url) ? join(DIST, url) : join(DIST, url.replace(/\/+$/, ''), 'index.html');

const errors = [];
let checked = 0;
for (const r of hostingRedirects()) {
  if (r.type !== 301) errors.push(`${r.source}: тип ${r.type}, ожидался 301`);
  for (const lang of r.source.includes(':lang') ? ['en', 'ru'] : ['']) {
    const sub = (/** @type {string} */ p) => (lang ? p.replaceAll(':lang', lang) : p);
    const from = sub(r.source);
    const to = sub(r.destination);
    if (existsSync(fileOf(from))) errors.push(`${from}: собран, хотя хостинг уводит его 301 на ${to}`);
    if (!existsSync(fileOf(to))) errors.push(`${from} → ${to}: цели нет в dist`);
    checked++;
  }
}

if (errors.length) {
  console.error(`❌ Редиректы против dist: ${errors.length} ошибок\n  ${errors.join('\n  ')}`);
  process.exit(1);
}
console.log(`✅ Редиректы против dist: ${checked} адресов — источник не собран, цель на месте`);
