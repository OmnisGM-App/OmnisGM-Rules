// CTA сущностных страниц по собранному dist (#164): ссылка на запись компендиума Table там, где у Table
// она есть, и общий CTA воронки на остальных. e2e (`e2e/cta-compendium.spec.ts`) в PR CI не ходит.
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const DIST = resolve(dirname(fileURLToPath(import.meta.url)), '../dist');
const APP = 'https://omnisgm.com/compendium/dnd2024';
const D52 = '/dnd/srd-5.2';

/** Страница → адрес записи в Table и nav-id страницы (`utm_content`). @type {[string, string, string][]} */
const COMPENDIUM = [
  [`/ru${D52}/spells/fireball`, `${APP}/spell/fireball`, 'd52-spells'],
  [`/en${D52}/weapons/longsword`, `${APP}/weapon/longsword`, 'd52-equipment'],
  [`/en${D52}/armor/plate-armor`, `${APP}/armor/plate-armor`, 'd52-equipment'],
  [`/en${D52}/equipment/acid`, `${APP}/item/acid`, 'd52-equipment'],
  [`/en${D52}/magic-items/bag-of-holding`, `${APP}/magic-item/bag-of-holding`, 'd52-magicitems'],
  [`/en${D52}/feats/alert`, `${APP}/feat/alert`, 'd52-feats'],
  [`/en${D52}/species/dwarf`, `${APP}/species/dwarf`, 'd52-origins-hub'],
  [`/en${D52}/backgrounds/acolyte`, `${APP}/background/acolyte`, 'd52-origins-hub'],
  [`/en${D52}/rules-glossary/action/hide`, `${APP}/action/hide`, 'd52-rulesterms-hub'],
  [`/en${D52}/rules-glossary/conditions/blinded`, `${APP}/rule/condition-blinded`, 'd52-rulesglossary'],
  [`/en${D52}/rules-glossary/term/reach`, `${APP}/rule/term-reach`, 'd52-rulesterms-hub'],
  [`/en${D52}/rules-glossary/term/unarmed-strike`, `${APP}/action/unarmed-strike`, 'd52-rulesterms-hub'],
  [`/en${D52}/rules-glossary/area-of-effect/cone`, `${APP}/rule/area-of-effect-cone`, 'd52-rulesterms-hub'],
];
const FUNNEL = [
  `/en${D52}/monsters-a-z/aboleth`, `/en${D52}/animals/wolf`, `/en${D52}/spells/all`,
  '/ru/dnd/srd-5.1/spells/fireball', '/en/dnd/srd-5.1/races/dwarf', '/ru/daggerheart/srd-1.0/ancestries/dwarf',
];

const errors = [];
/** @returns {{ href: string, kind: string, onclick: string } | null} */
function cta(/** @type {string} */ page) {
  const file = join(DIST, page, 'index.html');
  if (!existsSync(file)) { errors.push(`${page}: страницы нет в dist`); return null; }
  const tag = /<a\b[^>]*class="rd-cta"[^>]*>/.exec(readFileSync(file, 'utf8'))?.[0];
  if (!tag) { errors.push(`${page}: нет ссылки .rd-cta`); return null; }
  const attr = (/** @type {string} */ name) => (new RegExp(` ${name}="([^"]*)"`).exec(tag)?.[1] ?? '').replaceAll('&amp;', '&');
  return { href: attr('href'), kind: attr('data-cta'), onclick: attr('onclick') };
}
const utm = (/** @type {string} */ id) => `utm_source=rules&utm_medium=cta&utm_campaign=funnel&utm_content=${id}`;

for (const [page, target, navId] of COMPENDIUM) {
  const a = cta(page);
  if (!a) continue;
  const want = `${target}?lang=${page.slice(1, 3)}&${utm(navId)}`;
  if (a.href !== want) errors.push(`${page}: href «${a.href}», ожидался «${want}»`);
  if (a.kind !== 'compendium') errors.push(`${page}: data-cta «${a.kind}», ожидался «compendium»`);
  if (!a.onclick.includes(`page:'${navId}',to:'compendium'`)) errors.push(`${page}: событие без page/to: ${a.onclick}`);
}
for (const page of FUNNEL) {
  const a = cta(page);
  if (!a) continue;
  if (!/^https:\/\/omnisgm\.com\/(ru)?\?utm_source=rules&utm_medium=cta&utm_campaign=funnel&utm_content=[a-z0-9-]+$/.test(a.href)) errors.push(`${page}: href «${a.href}» — не общий CTA воронки`);
  if (a.kind !== 'funnel') errors.push(`${page}: data-cta «${a.kind}», ожидался «funnel»`);
  if (!a.onclick.includes(`to:'funnel'`)) errors.push(`${page}: событие без to:'funnel': ${a.onclick}`);
}

if (errors.length) {
  console.error(`❌ CTA по dist: ${errors.length} ошибок\n  ${errors.join('\n  ')}`);
  process.exit(1);
}
console.log(`✅ CTA по dist: ${COMPENDIUM.length} страниц ведут в компендиум, ${FUNNEL.length} — в воронку`);
