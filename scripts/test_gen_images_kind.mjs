// Выбор вида очереди картинок (issue #291): правило на синтетике — живой корпус проверял бы
// состояние репозитория, а не правило.
import { nextKind, emptyKinds, orderProblems, ORDER, KINDS } from './gen-images.mjs';

let failed = 0;
const eq = (/** @type {unknown} */ actual, /** @type {unknown} */ expected, /** @type {string} */ what) => {
  if (actual !== expected) {
    failed++;
    console.error(`  ✗ ${what}\n      ожидалось «${expected}», получено «${actual}»`);
  }
};

const rows = (/** @type {[string, number][]} */ ...pairs) =>
  pairs.map(([kind, left]) => ({ kind, left, total: left + 10 }));

eq(nextKind(rows(['spells', 0], ['magic-items', 377], ['gear', 480])), 'magic-items',
   'закрытый вид пропускается');
eq(nextKind(rows(['spells', 1], ['magic-items', 377])), 'spells',
   'берётся первый непустой, а не самый длинный');
eq(nextKind(rows(['spells', 0], ['magic-items', 0])), null, 'все виды закрыты');
eq(nextKind([]), null, 'пустой список видов');
eq(nextKind(rows(['spells', 0], ['magic-items', 0], ['gear', 3])), 'gear',
   'два закрытых подряд');

// Явные total: `rows` даёт total = left + 10 и нулевого размера не строит.
const sized = (/** @type {[string, number, number][]} */ ...triples) =>
  triples.map(([kind, left, total]) => ({ kind, left, total }));
eq(emptyKinds(sized(['spells', 0, 0], ['magic-items', 377, 383])).join(','), 'spells',
   'вид без данных назван, соседний с данными — нет');
eq(emptyKinds(sized(['spells', 0, 0], ['magic-items', 377, 383], ['creatures', 0, 0])).join(','),
   'spells,creatures', 'смешанный случай: API потерян, markdown-виды целы');
eq(emptyKinds(sized(['spells', 0, 341], ['magic-items', 0, 383])).length, 0,
   'закрытые, но непустые очереди — не «нет данных»');
eq(emptyKinds([]).length, 0, 'пустой список видов');

// Новые виды (#380) идут раньше снаряжения: их ждут, а у снаряжения очередь длинная.
for (const kind of ['class-options', 'rules']) {
  if (!(ORDER.indexOf(kind) >= 0 && ORDER.indexOf(kind) < ORDER.indexOf('gear'))) {
    failed++;
    console.error(`  ✗ вид ${kind} должен стоять в ORDER раньше gear`);
  }
}

// Полнота порядка — дважды: независимый счёт ловит ослабленную orderProblems() (ранний `return null`).
const problem = orderProblems();
if (problem) {
  failed++;
  console.error(`  ✗ ${problem}`);
}
const forgotten = Object.keys(KINDS).filter((k) => !ORDER.includes(k));
const unknown = ORDER.filter((k) => !(/** @type {Record<string, unknown>} */ (KINDS)[k]));
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
console.log(`✅ Выбор вида очереди: 9 сценариев, порядок покрывает все ${ORDER.length} вида, ` +
            `виды: ${Object.keys(KINDS).length}`);
