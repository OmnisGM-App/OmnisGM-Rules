// Адреса компендиума Table (#164): эталоны — URL, которые открываются на omnisgm.com, а не константы модуля.
import { compendiumHref } from '../src/lib/compendium-link.mjs';

let failed = 0;
const eq = (/** @type {unknown} */ actual, /** @type {unknown} */ expected, /** @type {string} */ what) => {
  if (actual !== expected) {
    failed++;
    console.error(`  ✗ ${what}\n      ожидалось «${expected}», получено «${actual}»`);
  }
};
const APP = 'https://omnisgm.com/compendium/dnd2024';

eq(compendiumHref('srd52', 'spells', 'fireball'), `${APP}/spell/fireball`, 'заклинание');
eq(compendiumHref('srd52', 'weapons', 'longsword'), `${APP}/weapon/longsword`, 'оружие');
eq(compendiumHref('srd52', 'armor', 'breastplate'), `${APP}/armor/breastplate`, 'доспех');
eq(compendiumHref('srd52', 'equipment', 'rope'), `${APP}/item/rope`, 'снаряжение');
eq(compendiumHref('srd52', 'magic-items', 'bag-of-holding'), `${APP}/magic-item/bag-of-holding`, 'магический предмет');
eq(compendiumHref('srd52', 'feats', 'alert'), `${APP}/feat/alert`, 'черта');
eq(compendiumHref('srd52', 'species', 'dwarf'), `${APP}/species/dwarf`, 'вид');
eq(compendiumHref('srd52', 'backgrounds', 'acolyte'), `${APP}/background/acolyte`, 'предыстория');
eq(compendiumHref('srd52', 'actions', 'hide'), `${APP}/action/hide`, 'действие');
eq(compendiumHref('srd52', 'conditions', 'blinded'), `${APP}/rule/condition-blinded`, 'состояние — rule с префиксом');
eq(compendiumHref('srd52', 'rules-terms', 'reach'), `${APP}/rule/term-reach`, 'термин — rule с префиксом');
eq(compendiumHref('srd52', 'areas-of-effect', 'cone'), `${APP}/rule/area-of-effect-cone`, 'область действия');
eq(compendiumHref('srd52', 'rules-terms', 'unarmed-strike'), `${APP}/action/unarmed-strike`, 'безоружный удар — стандартное действие');
eq(compendiumHref('srd52', 'rules-terms', 'opportunity-attacks'), `${APP}/action/opportunity-attacks`, 'провоцированная атака — стандартное действие');

eq(compendiumHref('srd52', 'monsters', 'aboleth'), null, 'существа — без ссылки (Table#776)');
eq(compendiumHref('srd52', 'animals', 'wolf'), null, 'животные — без ссылки');
eq(compendiumHref('srd51', 'spells', 'fireball'), null, 'SRD 5.1 — без ссылки');
eq(compendiumHref('srd51', 'races', 'dwarf'), null, 'расы 5.1 — без ссылки');

if (failed) {
  console.error(`test_compendium_link: ${failed} провал(ов)`);
  process.exit(1);
}
console.log('test_compendium_link: ok');
