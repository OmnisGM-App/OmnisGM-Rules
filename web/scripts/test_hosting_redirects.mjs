// hosting-redirects.mjs (#399) на синтетике: сопоставление путей и строгая форма источников.
import { isRedirected, redirectsOf } from '../src/lib/hosting-redirects.mjs';

let failed = 0;
const eq = (/** @type {unknown} */ got, /** @type {unknown} */ want, /** @type {string} */ what) => {
  if (got !== want) { failed++; console.error(`  ✗ ${what}\n      ожидалось ${want}, получено ${got}`); }
};
const throws = (/** @type {() => unknown} */ fn, /** @type {RegExp} */ re, /** @type {string} */ what) => {
  try { fn(); failed++; console.error(`  ✗ ${what}: ошибки нет`); }
  catch (e) { if (!re.test(String(e))) { failed++; console.error(`  ✗ ${what}: не та ошибка — ${e}`); } }
};

const list = redirectsOf({ redirects: [
  { source: '/:lang/dnd/srd-5.2/glossary/spells', destination: '/:lang/dnd/srd-5.2/spells/all/', type: 301 },
  { source: '/sitemap.xml', destination: '/sitemap-index.xml', type: 301 },
] });
eq(isRedirected('/ru/dnd/srd-5.2/glossary/spells/', list), true, ':lang → ru, со слэшем');
eq(isRedirected('/en/dnd/srd-5.2/glossary/spells', list), true, ':lang → en, без слэша');
eq(isRedirected('/de/dnd/srd-5.2/glossary/spells/', list), false, 'чужой язык не совпадает');
eq(isRedirected('/ru/dnd/srd-5.2/glossary/spells-extra/', list), false, 'префикс — не совпадение');
eq(isRedirected('/sitemap.xml', list), true, 'литеральный источник без :lang');
eq(isRedirected('/ru/dnd/srd-5.2/spells/all/', list), false, 'цель редиректа сама не редирект');

throws(() => redirectsOf({ redirects: [] }), /непустого/, 'пустой список — ошибка');
throws(() => redirectsOf({}), /непустого/, 'нет ключа redirects — ошибка');
throws(() => redirectsOf([{ redirects: [] }]), /непустого/, 'hosting массивом (мультисайт) — ошибка');
for (const source of ['/:lang/glossary/**', '/:lang/@(a|b)', '/:lang/{a,b}', '/:lang/:game/x', '/:lang(en|ru)/x', 'no-slash']) {
  throws(() => redirectsOf({ redirects: [{ source, destination: '/', type: 301 }] }), /неподдержанная форма/, `форма «${source}» — ошибка`);
}
throws(() => redirectsOf({ redirects: [{ regex: '^/x$', destination: '/', type: 301 }] }), /без source/, 'запись с regex — ошибка');

if (failed) { console.error(`\n❌ Редиректы хостинга: ${failed} расхождений`); process.exit(1); }
console.log('✅ Редиректы хостинга: сопоставление путей — 6, форма источников — 10');
