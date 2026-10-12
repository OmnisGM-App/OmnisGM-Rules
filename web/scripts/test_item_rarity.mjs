// Подпись и порядок редкостей магического предмета (#410): страницы с несколькими редкостями в сборке
// единичны, а подпись идёт в шапку, список, ховеркарту и сниппет.
import { itemRarities, itemRarityLabel } from '../src/lib/item-rarity.mjs';

let failed = 0;
const eq = (/** @type {unknown} */ actual, /** @type {unknown} */ expected, /** @type {string} */ what) => {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    failed++;
    console.error(`  ✗ ${what}\n      ожидалось «${JSON.stringify(expected)}», получено «${JSON.stringify(actual)}»`);
  }
};

eq(itemRarities({ rarity: 'rare', rarities: ['rare'] }), ['rare'], 'одна редкость');
eq(itemRarities({ rarity: null, rarities: ['very rare', 'uncommon', 'rare'] }), ['uncommon', 'rare', 'very rare'], 'сортировка по возрастанию');
eq(itemRarities({ rarity: null, rarities: [] }), [], 'редкость варьируется');
eq(itemRarities({ rarity: 'legendary' }), ['legendary'], 'запись без rarities — одиночная rarity');
eq(itemRarities({}), [], 'нет ни одного поля');

eq(itemRarityLabel({ rarities: ['very rare'] }, 'ru'), 'очень редкий', 'RU: одна');
eq(itemRarityLabel({ rarities: ['very rare'] }, 'en'), 'very rare', 'EN: одна');
eq(itemRarityLabel({ rarities: ['rare', 'uncommon'] }, 'en'), 'uncommon or rare', 'EN: две');
eq(itemRarityLabel({ rarities: ['uncommon', 'rare', 'very rare'] }, 'ru'), 'необычный, редкий или очень редкий', 'RU: три');
eq(itemRarityLabel({ rarities: ['rare', 'very rare', 'legendary'] }, 'en'), 'rare, very rare or legendary', 'EN: три');
eq(itemRarityLabel({ rarities: [] }, 'ru'), 'редкость варьируется', 'RU: варьируется');
eq(itemRarityLabel({ rarities: [] }, 'en'), 'rarity varies', 'EN: варьируется');

if (failed) {
  console.error(`test_item_rarity: ${failed} провал(ов)`);
  process.exit(1);
}
console.log('test_item_rarity: ok');
