// Адрес сущности внутри раздела (#412): вложенный путь — только у предмета группы снаряжения.
import { entityPath } from '../src/lib/equipment-path.mjs';

let failed = 0;
const eq = (/** @type {unknown} */ actual, /** @type {unknown} */ expected, /** @type {string} */ what) => {
  if (actual !== expected) {
    failed++;
    console.error(`  ✗ ${what}\n      ожидалось ${JSON.stringify(expected)}, получено ${JSON.stringify(actual)}`);
  }
};

eq(entityPath('equipment', { slug: 'lute', group: 'musical-instrument' }), 'musical-instrument/lute', 'предмет группы — под группой');
eq(entityPath('equipment', { slug: 'acid', group: null }), 'acid', 'обычный предмет — по слагу');
eq(entityPath('equipment', { slug: 'acid' }), 'acid', 'предмет без поля group (5.1) — по слагу');
eq(entityPath('equipment-groups', { slug: 'musical-instrument' }), 'musical-instrument', 'группа — по слагу');
eq(entityPath('monsters', { slug: 'ghast', group: 'Г' }), 'ghast', 'у монстра group — буква указателя, не сегмент адреса');
eq(entityPath('magic-items', { slug: 'potion-of-healing', group: 'potions-of-healing' }), 'potions-of-healing/potion-of-healing', 'предмет семейства магических предметов — под семейством');
eq(entityPath('magic-items', { slug: 'bag-of-holding', group: null }), 'bag-of-holding', 'магический предмет вне семейства — по слагу');
eq(entityPath('magic-item-groups', { slug: 'ioun-stone' }), 'ioun-stone', 'семейство — по слагу');
eq(entityPath('spells', { slug: 'fireball', group: 'x' }), 'fireball', 'чужой ресурс с полем group — по слагу');

if (failed) {
  console.error(`❌ entity-path: ${failed}`);
  process.exit(1);
}
console.log('✅ entity-path: вложенный адрес только у предмета группы снаряжения или семейства магических предметов');
