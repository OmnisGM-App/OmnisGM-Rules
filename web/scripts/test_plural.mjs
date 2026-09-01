// Инварианты согласования числительных (issue #240). Юнит-тест, а не e2e: правила русского
// счёта проверяются на числах, а не на страницах — 11, 21, 111 и 24 в сборке просто не
// встречаются, а сломать их правкой хелпера легко.
import { pluralRu, countPhrase, countLeadEn, pluralEn } from '../src/lib/plural.mjs';

let failed = 0;
const eq = (actual, expected, what) => {
  if (actual !== expected) {
    failed++;
    console.error(`  ✗ ${what}\n      ожидалось «${expected}», получено «${actual}»`);
  }
};

const MONSTER = ['монстр', 'монстра', 'монстров'];
const ANIMAL = ['животное', 'животных', 'животных'];

// Базовые три формы.
eq(pluralRu(1, MONSTER), 'монстр', 'pluralRu(1)');
eq(pluralRu(2, MONSTER), 'монстра', 'pluralRu(2)');
eq(pluralRu(5, MONSTER), 'монстров', 'pluralRu(5)');
// Подводные камни русского счёта: 11–14 всегда «многие», а 21/22 идут по последней цифре.
for (const n of [11, 12, 13, 14, 111]) eq(pluralRu(n, MONSTER), 'монстров', `pluralRu(${n}) — «надцать»`);
eq(pluralRu(21, MONSTER), 'монстр', 'pluralRu(21)');
eq(pluralRu(22, MONSTER), 'монстра', 'pluralRu(22)');
eq(pluralRu(101, MONSTER), 'монстр', 'pluralRu(101)');

// «Все» согласуется только с множественным: «Все 21 монстр» ломается так же, как «Все 1».
eq(countPhrase(1, 'ru', ANIMAL, ['animal', 'animals']), '1 животное', 'countPhrase(1)');
eq(countPhrase(21, 'ru', ANIMAL, ['animal', 'animals']), '21 животное', 'countPhrase(21) — без «Все»');
eq(countPhrase(2, 'ru', ANIMAL, ['animal', 'animals']), 'Все 2 животных', 'countPhrase(2)');
eq(countPhrase(24, 'ru', MONSTER, ['monster', 'monsters']), 'Все 24 монстра', 'countPhrase(24)');
eq(countPhrase(5, 'ru', MONSTER, ['monster', 'monsters']), 'Все 5 монстров', 'countPhrase(5)');

// Хабы документов (#245): числа там произвольные и крупные — «884 страниц» вместо «страницы»
// висело на проде, потому что форма была захардкожена. Реальные значения четырёх хабов.
const PAGE = ['страница', 'страницы', 'страниц'];
eq(pluralRu(884, PAGE), 'страницы', 'pluralRu(884) — D&D 5.1');
eq(pluralRu(1042, PAGE), 'страницы', 'pluralRu(1042) — D&D 5.2');
eq(pluralRu(364, PAGE), 'страницы', 'pluralRu(364) — Daggerheart');
eq(pluralRu(78, PAGE), 'страниц', 'pluralRu(78) — BRP');
eq(pluralRu(25, ['раздел', 'раздела', 'разделов']), 'разделов', 'pluralRu(25) — разделы хаба');

// Английский: форм две, «All» уходит при единице.
eq(countPhrase(1, 'en', ANIMAL, ['animal', 'animals']), '1 animal', 'countPhrase(1, en)');
eq(countPhrase(3, 'en', ANIMAL, ['animal', 'animals']), 'All 3 animals', 'countPhrase(3, en)');
eq(countLeadEn(1), '1', 'countLeadEn(1)');
eq(countLeadEn(3), 'All 3', 'countLeadEn(3)');
eq(pluralEn(1, ['spell', 'spells']), 'spell', 'pluralEn(1)');
eq(pluralEn(0, ['spell', 'spells']), 'spells', 'pluralEn(0)');

if (failed) {
  console.error(`\n❌ Склонение числительных: ${failed} проверок не прошло`);
  process.exit(1);
}
console.log('✓ Склонение числительных: все проверки прошли');
