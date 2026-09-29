#!/usr/bin/env node
// Страж состава агрегаторов `test:unit` / `test:unit:py` / `test:gates` (issue #283): состав
// сверяется с ci.yml в обе стороны, сцепка — только `&&` (`;`/`||` дают ноль на упавшем юните).
// Юнит — файл `test_*.mjs|py` в `run:` шага ci.yml; `verify_dist_*` агрегатор не гоняет: нужна сборка.
// Разбор построчный, с состоянием: комментарий о шаге — не шаг, путь — от `working-directory` шага.
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const CI = resolve(REPO, '.github/workflows/ci.yml');
const PKG = resolve(REPO, 'package.json');
// Сам страж — тоже `test_*` в CI; в агрегаторе он звал бы сам себя.
const SELF = 'scripts/test_unit_agenda.mjs';

/** Путь к файлу юнита из токена команды, нормализованный от корня репозитория. */
const norm = (/** @type {string} */ path, /** @type {string} */ cwd) =>
  resolve(cwd ? resolve(REPO, cwd) : REPO, path).slice(REPO.length + 1);

/** Имена файлов-юнитов внутри строки команды (любая форма вызова: `node --test`, `python3 -u`). */
const unitsInCommand = (/** @type {string} */ command) =>
  [...command.matchAll(/(?:^|[\s"'])([\w./-]*test_[\w.-]+\.(?:mjs|py))(?=$|[\s"';&|])/g)]
    .map((m) => m[1]);

/**
 * @param {string} text
 * @returns {Set<string>}
 */
export function ciUnits(text) {
  const out = new Set();
  let cwd = '';
  let stepIndent = null;   // отступ элементов списка шагов текущей джобы
  let runIndent = null;    // отступ ключа `run:` с блочным литералом
  let literalIndent = null; // отступ ЧУЖОГО блочного литерала (env:, with: …)

  const take = (/** @type {string} */ command) => {
    for (const path of unitsInCommand(command)) {
      const full = norm(path, cwd);
      if (full !== SELF) out.add(full);
    }
  };

  for (const raw of text.replace(/\r\n/g, '\n').split('\n')) {
    if (!raw.trim()) continue;
    const indent = raw.length - raw.trimStart().length;
    const line = raw.trim();
    // Комментарий — проза о шаге, а не сам шаг.
    if (line.startsWith('#')) continue;

    // Тело `run: |` — команды; тело чужого литерала (`env: |`) — данные, где «- bar» неотличим от шага.
    if (runIndent !== null) {
      if (indent > runIndent) { take(line); continue; }
      runIndent = null;
    }
    if (literalIndent !== null) {
      if (indent > literalIndent) continue;
      literalIndent = null;
    }

    if (/^steps:/.test(line)) { stepIndent = null; cwd = ''; continue; }
    if (line.startsWith('- ') || line === '-') {
      // Первый элемент списка задаёт отступ шагов джобы; всё, что глубже, — вложенные
      // списки внутри шага, а не новый шаг.
      if (stepIndent === null) stepIndent = indent;
      if (indent === stepIndent) { cwd = ''; }
    }

    const wd = line.match(/^(?:- )?working-directory:\s*(\S+)/);
    if (wd) { cwd = wd[1]; continue; }

    const run = line.match(/^(?:- )?run:\s*(.*)$/);
    if (run) {
      // Индикатор блока может нести YAML-комментарий («run: | # …»).
      if (/^[|>][-+\d]*(?:\s+#.*)?$/.test(run[1].trim())) runIndent = indent;
      else take(run[1]);
      continue;
    }
    const literal = line.match(/^(?:- )?[\w.-]+:\s*[|>][-+\d]*(?:\s+#.*)?$/);
    if (literal) { literalIndent = indent; }
  }
  return out;
}

/**
 * Юниты и проблемы сцепки из строки агрегатора.
 *
 * @param {string} name — имя npm-скрипта (для сообщений)
 * @param {string | undefined} command
 * @returns {{paths: Set<string>, problems: string[]}}
 */
export function agendaUnits(name, command) {
  const paths = new Set();
  const problems = [];
  if (!command) return { paths, problems: [`${name}: скрипта нет в package.json`] };
  const wrong = command.match(/;|\|\|/);
  if (wrong) {
    problems.push(`${name}: команды сцеплены через «${wrong[0]}» — упавший юнит не остановит ` +
                  `цепочку и агрегатор вернёт ноль; между вызовами обязан быть «&&»`);
  }
  for (const chunk of command.split('&&')) {
    for (const path of unitsInCommand(chunk.trim())) paths.add(norm(path, ''));
  }
  return { paths, problems };
}

/** @param {Record<string, string | undefined>} scripts */
export function gatesProblems(scripts) {
  const command = scripts['test:gates'] ?? '';
  const want = ['test:unit', 'test:unit:py', 'test:agenda'];
  const missing = want.filter((n) => !new RegExp(`npm run ${n.replace(':', ':')}(?![\\w:])`).test(command));
  return missing.length
    ? [`test:gates не зовёт ${missing.join(', ')} — «прогнать всё» перестало быть правдой`]
    : [];
}

/**
 * @param {string} ciText
 * @param {Record<string, string | undefined>} scripts
 */
export function agendaProblems(ciText, scripts) {
  const problems = [];
  const unit = agendaUnits('test:unit', scripts['test:unit']);
  const unitPy = agendaUnits('test:unit:py', scripts['test:unit:py']);
  problems.push(...unit.problems, ...unitPy.problems, ...gatesProblems(scripts));
  const agenda = new Set([...unit.paths, ...unitPy.paths]);
  const inCi = ciUnits(ciText);
  for (const path of [...inCi].sort()) {
    if (!agenda.has(path)) {
      problems.push(`${path} — юнит есть в ci.yml, но его нет в test:unit / test:unit:py`);
    }
  }
  for (const path of [...agenda].sort()) {
    if (!inCi.has(path)) {
      problems.push(`${path} — команда есть в агрегаторе, но такого шага нет в ci.yml`);
    }
  }
  return { problems, count: agenda.size };
}

// ── Самопроверки механизма ──────────────────────────────────────────────────────────────
const CI_HEAD = 'jobs:\n  check-build:\n    steps:\n';
/** @type {[string, string, string[]][]} */
const SELF_CHECKS = [
  ['простой шаг', `${CI_HEAD}      - name: Unit\n        run: node scripts/test_a.mjs\n`,
   ['scripts/test_a.mjs']],
  ['node --test', `${CI_HEAD}      - name: Unit\n        run: node --test scripts/test_a.mjs\n`,
   ['scripts/test_a.mjs']],
  ['python3 -u', `${CI_HEAD}      - name: Unit\n        run: python3 -u .github/scripts/test_b.py\n`,
   ['.github/scripts/test_b.py']],
  ['working-directory', `${CI_HEAD}      - name: Unit\n        working-directory: web\n        run: node scripts/test_c.mjs\n`,
   ['web/scripts/test_c.mjs']],
  ['шаг без name', `${CI_HEAD}      - run: node scripts/test_d.mjs\n`, ['scripts/test_d.mjs']],
  ['анонимный шаг после working-directory',
   `${CI_HEAD}      - name: A\n        working-directory: web\n        run: node scripts/test_c.mjs\n      - run: node scripts/test_d.mjs\n`,
   ['web/scripts/test_c.mjs', 'scripts/test_d.mjs']],
  ['комментарий не шаг', `${CI_HEAD}      # см. node scripts/test_ghost.mjs\n      - name: Unit\n        run: node scripts/test_a.mjs\n`,
   ['scripts/test_a.mjs']],
  ['закомментированный шаг', `${CI_HEAD}      # - name: Unit\n      #   run: node scripts/test_ghost.mjs\n`, []],
  ['многострочный run', `${CI_HEAD}      - name: Unit\n        run: |\n          node scripts/test_a.mjs\n          python3 .github/scripts/test_b.py\n`,
   ['scripts/test_a.mjs', '.github/scripts/test_b.py']],
  ['сам страж не в счёт', `${CI_HEAD}      - name: Гейт\n        run: node ./scripts/test_unit_agenda.mjs\n`, []],
  ['working-directory сбрасывается', `${CI_HEAD}      - name: A\n        working-directory: web\n        run: node scripts/test_c.mjs\n      - name: B\n        run: node scripts/test_d.mjs\n`,
   ['web/scripts/test_c.mjs', 'scripts/test_d.mjs']],
  ['список внутри чужого литерала',
   `${CI_HEAD}      - name: A\n        working-directory: web\n        env:\n          FOO: |\n            - bar\n            - baz\n        run: node scripts/test_c.mjs\n`,
   ['web/scripts/test_c.mjs']],
  ['вложенный список в with',
   `${CI_HEAD}      - name: A\n        working-directory: web\n        with:\n          args:\n            - one\n            - two\n        run: node scripts/test_c.mjs\n`,
   ['web/scripts/test_c.mjs']],
  ['комментарий после `run: |`',
   `${CI_HEAD}      - name: A\n        run: | # собираем данные\n          node scripts/test_c.mjs\n`,
   ['scripts/test_c.mjs']],
  ['комментарий после чужого `env: |`',
   `${CI_HEAD}      - name: A\n        env:\n          NOTE: | # заметка\n            node scripts/test_ghost.mjs\n        run: node scripts/test_c.mjs\n`,
   ['scripts/test_c.mjs']],
  ['юнит внутри чужого литерала не считается',
   `${CI_HEAD}      - name: A\n        env:\n          NOTE: |\n            node scripts/test_ghost.mjs\n        run: node scripts/test_c.mjs\n`,
   ['scripts/test_c.mjs']],
];

const failures = [];
for (const [label, text, want] of SELF_CHECKS) {
  const got = [...ciUnits(text)].sort();
  if (got.join('|') !== [...want].sort().join('|')) {
    failures.push(`самопроверка разбора «${label}»: ${JSON.stringify(got)}, ожидалось ${JSON.stringify([...want].sort())}`);
  }
}
for (const [label, command, wantProblem] of /** @type {[string, string, boolean][]} */ ([
  ['&& — норма', 'node a/test_x.mjs && node b/test_y.mjs', false],
  ['; вместо &&', 'node a/test_x.mjs ; node b/test_y.mjs', true],
  ['|| вместо &&', 'node a/test_x.mjs || node b/test_y.mjs', true],
])) {
  const got = agendaUnits('test:unit', command).problems.length > 0;
  if (got !== wantProblem) {
    failures.push(`самопроверка сцепки «${label}»: проблем ${got ? 'есть' : 'нет'}, ожидалось обратное`);
  }
}
if (gatesProblems({ 'test:gates': 'npm run test:unit && npm run test:agenda' }).length !== 1) {
  failures.push('самопроверка test:gates: потерянный test:unit:py не замечен');
}
if (gatesProblems({ 'test:gates': 'npm run test:unit && npm run test:unit:py && npm run test:agenda' }).length) {
  failures.push('самопроверка test:gates: полный состав объявлен неполным');
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const scripts = JSON.parse(readFileSync(PKG, 'utf8')).scripts ?? {};
  const { problems, count } = agendaProblems(readFileSync(CI, 'utf8'), scripts);
  const all = [...failures, ...problems];
  if (all.length) {
    console.error(`❌ Состав агрегаторов разошёлся с ci.yml (${all.length}):`);
    for (const f of all) console.error(`  — ${f}`);
    process.exit(1);
  }
  console.log(`✅ Агрегаторы: ${count} юнитов, состав совпадает с ci.yml; ` +
              `${SELF_CHECKS.length} самопроверок разбора`);
}
