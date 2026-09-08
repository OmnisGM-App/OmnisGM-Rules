#!/usr/bin/env node
// Страж состава агрегаторов `test:unit` / `test:unit:py` (issue #283).
//
// Корневые агрегаторы обещают «прогнать всё как CI». Обещание живёт ровно до первого нового
// юнита в ci.yml, добавленного мимо package.json: агрегатор остаётся зелёным, но проверяет
// меньше — а человек, прогнавший его локально, считает, что проверил всё. Это хуже, чем не
// иметь агрегатора вовсе, поэтому состав сверяется, а не декларируется.
//
// Сверяем ОБЕ стороны: юнит из CI обязан быть в агрегаторе, а команда из агрегатора —
// в CI. Вторая половина не формальность: строка, оставшаяся в package.json после
// переименования файла, — это «зелёный локальный прогон» несуществующего теста.
//
// Что считается юнитом: шаг ci.yml, чей `run` зовёт скрипт с именем `test_*` (node или
// python3). Гейты по собранному dist (`verify_dist_*`), схема JSON API и сборка сюда не
// входят — им нужен билд, а агрегатор задуман как то, что гоняется за секунды.
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const CI = resolve(REPO, '.github/workflows/ci.yml');
const PKG = resolve(REPO, 'package.json');

/**
 * Команды `node …/test_*.mjs` и `python3 …/test_*.py` из строки скрипта.
 * @param {string} text
 * @returns {Set<string>}
 */
function unitPaths(text) {
  const out = new Set();
  for (const m of text.matchAll(/(?:node|python3)\s+([\w./-]*test_[\w.-]+\.(?:mjs|py))/g)) {
    out.add(m[1]);
  }
  return out;
}

const ciText = readFileSync(CI, 'utf8');
// В ci.yml юниты web гоняются с `working-directory: web`, поэтому путь у них относительный
// («scripts/test_plural.mjs»), а в корневом агрегаторе — от корня («web/scripts/…»).
// Приводим к одному виду по самому файлу шага, иначе сверка ловила бы разницу написания,
// а не разницу состава.
// Сам этот страж — тоже шаг CI с именем `test_*`, но не «юнит из списка»: он проверяет
// СОСТАВ списка, и попади он в агрегатор, тот звал бы сам себя.
const SELF = 'scripts/test_unit_agenda.mjs';

const ciUnits = new Set();
for (const block of ciText.split(/\n\s*- name: /)) {
  const run = [...block.matchAll(/(?:node|python3)\s+([\w./-]*test_[\w.-]+\.(?:mjs|py))/g)].map((m) => m[1]);
  if (!run.length) continue;
  const inWeb = /working-directory:\s*web/.test(block);
  for (const path of run) {
    const full = inWeb ? `web/${path}` : path;
    if (full !== SELF) ciUnits.add(full);
  }
}

const scripts = JSON.parse(readFileSync(PKG, 'utf8')).scripts ?? {};
const agenda = new Set([
  ...unitPaths(scripts['test:unit'] ?? ''),
  ...unitPaths(scripts['test:unit:py'] ?? ''),
]);

const failures = [];
for (const path of [...ciUnits].sort()) {
  if (!agenda.has(path)) {
    failures.push(`${path} — юнит есть в ci.yml, но его нет в test:unit / test:unit:py`);
  }
}
for (const path of [...agenda].sort()) {
  if (!ciUnits.has(path)) {
    failures.push(`${path} — команда есть в агрегаторе, но такого шага нет в ci.yml`);
  }
}
if (failures.length) {
  console.error(`❌ Состав агрегаторов разошёлся с ci.yml (${failures.length}):`);
  for (const f of failures) console.error(`  — ${f}`);
  process.exit(1);
}
console.log(`✅ Агрегаторы: ${agenda.size} юнитов, состав совпадает с ci.yml`);
