// Выбор вида очереди картинок (issue #291). Юнит-тест, а не прогон воркера: сам выбор
// упирается в данные JSON API и наличие webp, и на живом корпусе он проверяет состояние
// репозитория, а не правило. Проверяем правило — и полноту порядка видов.
import { nextKind, ORDER, KINDS } from './gen-images.mjs';

let failed = 0;
const eq = (actual, expected, what) => {
  if (actual !== expected) {
    failed++;
    console.error(`  ✗ ${what}\n      ожидалось «${expected}», получено «${actual}»`);
  }
};

const rows = (...pairs) => pairs.map(([kind, left]) => ({ kind, left, total: left + 10 }));

// Основной сценарий #291: очередь первого вида закрыта, работа есть у следующего.
eq(nextKind(rows(['spells', 0], ['magic-items', 377], ['gear', 480])), 'magic-items',
   'закрытый вид пропускается');
// Порядок соблюдается: берётся ПЕРВЫЙ непустой, а не самый большой.
eq(nextKind(rows(['spells', 1], ['magic-items', 377])), 'spells',
   'берётся первый непустой, а не самый длинный');
// Все закрыты — работы нет вовсе (воркер не ставит codex и не тратит прогон).
eq(nextKind(rows(['spells', 0], ['magic-items', 0])), null, 'все виды закрыты');
eq(nextKind([]), null, 'пустой список видов');
// Ноль на входе — именно ноль: отрицательных остатков не бывает, но и «падать» не на чем.
eq(nextKind(rows(['spells', 0], ['magic-items', 0], ['gear', 3])), 'gear',
   'два закрытых подряд');

// Полнота порядка: вид, добавленный в KINDS и забытый в ORDER, никогда не попал бы в крон.
// Этот же страж стоит в самом скрипте (падение с кодом 2), здесь он проверяется явно.
const forgotten = Object.keys(KINDS).filter((k) => !ORDER.includes(k));
const unknown = ORDER.filter((k) => !KINDS[k]);
if (forgotten.length) {
  failed++;
  console.error(`  ✗ виды вне порядка ORDER: ${forgotten.join(', ')}`);
}
if (unknown.length) {
  failed++;
  console.error(`  ✗ в ORDER есть неизвестные виды: ${unknown.join(', ')}`);
}

if (failed) {
  console.error(`\n❌ Выбор вида очереди: ${failed} расхождений`);
  process.exit(1);
}
console.log(`✅ Выбор вида очереди: 5 сценариев, порядок покрывает все ${ORDER.length} вида`);
