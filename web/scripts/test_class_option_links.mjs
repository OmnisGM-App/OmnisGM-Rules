// Ссылки из главы класса на страницу группы вариантов (#379): на синтетическом hast-дереве.
import { groupsByName, linkClassOptionGroups } from '../src/lib/rehype-class-option-links.mjs';

let failed = 0;
const eq = (/** @type {unknown} */ actual, /** @type {unknown} */ expected, /** @type {string} */ what) => {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    failed++;
    console.error(`  ✗ ${what}\n      ожидалось ${JSON.stringify(expected)}, получено ${JSON.stringify(actual)}`);
  }
};

const groups = groupsByName([
  { class: 'paladin', feature: { key: 'fighting-style', name: 'Fighting Style' } },
  { class: 'ranger', feature: { key: 'fighting-style', name: 'Fighting Style' } },
  { class: 'ranger', feature: { key: 'hunter-s-prey', name: "Hunter's Prey" } },
]);
const heading = (/** @type {string} */ text) => ({ type: 'element', tagName: 'h4', properties: {}, children: [{ type: 'text', value: text }] });
const links = (/** @type {any} */ tree) => tree.children
  .filter((/** @type {any} */ n) => n.tagName === 'p')
  .map((/** @type {any} */ p) => [p.children[0].properties.href, p.children[0].children[0].value]);

const paladin = { type: 'root', children: [heading('Level 2: Fighting Style'), heading('Level 7: Fighting Style')] };
linkClassOptionGroups(paladin, 'en', 'paladin', groups);
eq(links(paladin), [['/en/dnd/srd-5.2/class-options/fighting-style/', 'All Fighting Style options on one page →']],
  'паладин: ссылка под заголовком умения, вторая на ту же группу не ставится');

const fighter = { type: 'root', children: [heading('Level 1: Fighting Style')] };
linkClassOptionGroups(fighter, 'en', 'fighter', groups);
eq(links(fighter), [], 'воин: одноимённое умение без вариантов класса — без ссылки');

const ranger = { type: 'root', children: [heading('Level 3: Hunter’s Prey')] };
linkClassOptionGroups(ranger, 'en', 'ranger', groups);
eq(links(ranger), [['/en/dnd/srd-5.2/class-options/hunter-s-prey/', 'All Hunter’s Prey options on one page →']],
  'типографский апостроф в заголовке находит группу и остаётся в тексте ссылки');

const plain = { type: 'root', children: [heading('Spellcasting')] };
linkClassOptionGroups(plain, 'en', 'ranger', groups);
eq(links(plain), [], 'заголовок без «Level N:» — без ссылки');

if (failed) {
  console.error(`\nСсылки на группы вариантов: ${failed} проверок не прошло`);
  process.exit(1);
}
console.log('✓ Ссылки из главы класса на группы вариантов: все проверки прошли');
