// Выбор вида очереди картинок (issue #291). Юнит-тест, а не прогон воркера: сам выбор
// упирается в данные JSON API и наличие webp, и на живом корпусе он проверяет состояние
// репозитория, а не правило. Проверяем правило — и полноту порядка видов.
import { nextKind, orderProblems, ORDER, KINDS } from './gen-images.mjs';

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

// Полнота порядка проверяется ДВАЖДЫ, и это не дублирование:
//  1) зовём прод-функцию — это её контракт, тот же вызов делает сам скрипт;
//  2) считаем расхождение НЕЗАВИСИМО — иначе ослабленная функция (ранний `return null`)
//     оставляла бы тест зелёным, то есть страж проверял бы сам себя (ревью #292).
const problem = orderProblems();
if (problem) {
  failed++;
  console.error(`  ✗ ${problem}`);
}
const forgotten = Object.keys(KINDS).filter((k) => !ORDER.includes(k));
const unknown = ORDER.filter((k) => !KINDS[k]);
if (forgotten.length || unknown.length) {
  failed++;
  console.error(`  ✗ ORDER и KINDS разошлись: нет в порядке — ${forgotten.join(', ') || '—'}, ` +
                `нет среди видов — ${unknown.join(', ') || '—'}`);
  if (!problem) console.error('      …и orderProblems() при этом молчит — страж ослаблен');
}

if (failed) {
  console.error(`\n❌ Выбор вида очереди: ${failed} расхождений`);
  process.exit(1);
}
console.log(`✅ Выбор вида очереди: 5 сценариев, порядок покрывает все ${ORDER.length} вида, ` +
            `виды: ${Object.keys(KINDS).length}`);
