#!/usr/bin/env node
// Страж связки setup в workflow (issue #287).
//
// Связка setup жила в четырёх workflow: полностью (setup-node + cache + npm ci +
// setup-python) — в ci и deploy, частично — в content и gen-images. Дублирование уже дало
// дрейф: node 20 в трёх против 22 в четвёртом — молча, потому что сравнивать было негде.
// Composite-шаг убирает копии, но НЕ мешает завести их заново: он не запрещает написать
// `uses: actions/setup-node` рядом. Поэтому запрет — здесь.
//
// Проверяем два утверждения:
//  1) прямых `actions/setup-node` и `actions/setup-python` в наших workflow нет — версии
//     объявляются в одном месте (`.github/actions/setup-web/action.yml`), а несогласие с
//     ними пишется input'ом. Python попал сюда не сразу: пока запрет был только на Node,
//     мутация «3.12 → 3.11» в отдельной джобе оставляла гейт зелёным (ревью #300);
//  2) у каждой джобы есть `timeout-minutes` — без него зависший шаг держит очередь до
//     дефолтных шести часов.
//
// Исключение одно и явное: `claude-review.yml` — вендорный workflow авторевью, он живёт по
// своим правилам и синхронизируется из донора целиком, поэтому наши правила ему не указ.
//
// Разбор текстовый, и он ОБЯЗАН падать при непонятной форме, а не молчать: fail-open —
// худший исход для гейта. Число распознанных блоков-джоб сверяется с числом ключей под
// `jobs:`, расширения — обе формы GitHub (`.yml` и `.yaml`), а сами composite-действия
// проверяются вторым проходом: именно оттуда растёт исходный дрейф версий (ревью #300).
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const WF_DIR = resolve(REPO, '.github/workflows');
const ACTIONS_DIR = resolve(REPO, '.github/actions');
const VENDORED = new Set(['claude-review.yml']);
// Единственное место, где прямой вызов setup-* законен, — сам общий шаг.
const HOME = 'setup-web';

/** Прямые вызовы setup-node / setup-python (кавычки вокруг значения — валидный YAML). */
export function directSetups(text) {
  return [...text.matchAll(/uses:\s*['"]?(actions\/setup-(?:node|python))/g)].map((m) => m[1]);
}

/**
 * Джобы файла: имя → есть ли у неё timeout-minutes. Бросает, если форма непонятна.
 *
 * @param {string} text
 * @returns {{jobs: Map<string, boolean>, problem: string|null}}
 */
export function jobsOf(text) {
  const jobs = new Map();
  // `jobs:` бывает и самой первой строкой (в самопроверках — всегда), поэтому ищем обе формы.
  const at = text.startsWith('jobs:') ? 0 : text.indexOf('\njobs:');
  if (at < 0) return { jobs, problem: 'нет секции jobs' };
  const body = text.slice(at).replace(/\r\n/g, '\n');
  // Ключи джоб — по строкам, а не split'ом по разделителю: split требовал, чтобы за именем
  // сразу шёл перевод строки, и любой хвост (комментарий, пробел, кавычки) прятал джобу.
  const lines = body.split('\n');
  const keys = [];
  for (let i = 0; i < lines.length; i++) {
    const m = lines[i].match(/^ {2}(['"]?)([\w-]+)\1\s*:(.*)$/);
    if (!m) continue;
    const tail = m[3].replace(/#.*$/, '').trim();
    // Flow-стиль (`job: {runs-on: …}`) в наших workflow не встречается, и разбирать его
    // текстом — заведомо хрупко: называем и падаем, а не делаем вид, что проверили.
    if (tail && !tail.startsWith('#')) {
      return { jobs, problem: `джоба «${m[2]}» записана в одну строку — разбор не берётся` };
    }
    keys.push({ name: m[2], line: i });
  }
  for (let k = 0; k < keys.length; k++) {
    const from = keys[k].line;
    const to = k + 1 < keys.length ? keys[k + 1].line : lines.length;
    const block = lines.slice(from, to).join('\n');
    jobs.set(keys[k].name, / {4}timeout-minutes:/.test(block));
  }
  return { jobs, problem: null };
}

/** Все расхождения по каталогу workflow и composite-действиям. */
export function setupProblems(files, actions) {
  const problems = [];
  for (const { name, text } of files) {
    for (const used of directSetups(text)) {
      problems.push(`${name}: прямой ${used} — версии объявляются в ` +
                    `.github/actions/${HOME}, зовите его (#287)`);
    }
    const { jobs, problem } = jobsOf(text);
    if (problem) { problems.push(`${name}: ${problem}`); continue; }
    if (!jobs.size) { problems.push(`${name}: ни одной джобы не распознано — разбор сломан`); continue; }
    for (const [job, hasTimeout] of jobs) {
      if (!hasTimeout) problems.push(`${name}: у джобы «${job}» нет timeout-minutes (#287)`);
    }
  }
  for (const { name, text } of actions) {
    for (const used of directSetups(text)) {
      problems.push(`${name}: прямой ${used} в composite-действии — вторая точка объявления ` +
                    `версии, ровно то, из чего вырос #287`);
    }
  }
  return problems;
}

function read(dir, filter) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true })
    .flatMap((e) => {
      if (e.isDirectory()) {
        const file = resolve(dir, e.name, 'action.yml');
        return existsSync(file) && e.name !== HOME
          ? [{ name: `.github/actions/${e.name}/action.yml`, text: readFileSync(file, 'utf8') }]
          : [];
      }
      return filter(e.name)
        ? [{ name: e.name, text: readFileSync(resolve(dir, e.name), 'utf8') }]
        : [];
    });
}

// ── Самопроверки разбора: формы, на которых гейт молчал (ревью #300) ────────────────────
const SELF_CHECKS = [
  ['обычная джоба без потолка', 'jobs:\n  build:\n    runs-on: x\n    steps: []\n', 1],
  ['джоба с потолком', 'jobs:\n  build:\n    runs-on: x\n    timeout-minutes: 5\n', 0],
  ['комментарий после имени', 'jobs:\n  build:  # сборка\n    runs-on: x\n', 1],
  ['хвостовой пробел', 'jobs:\n  build: \n    runs-on: x\n', 1],
  ['имя в кавычках', 'jobs:\n  "build":\n    runs-on: x\n', 1],
  ['CRLF', 'jobs:\r\n  build:\r\n    runs-on: x\r\n', 1],
  ['flow-стиль — не притворяемся', 'jobs:\n  build: {runs-on: x}\n', 1],
  ['две джобы, потолок у одной', 'jobs:\n  a:\n    timeout-minutes: 5\n  b:\n    runs-on: x\n', 1],
];
const failures = [];
for (const [label, text, want] of SELF_CHECKS) {
  const got = setupProblems([{ name: 't.yml', text }], []).length;
  if (got !== want) failures.push(`самопроверка «${label}»: проблем ${got}, ожидалось ${want}`);
}
for (const [label, text, want] of [
  ['прямой setup-node', 'jobs:\n  a:\n    timeout-minutes: 1\n    steps:\n      - uses: actions/setup-node@v7\n', 1],
  ['он же в кавычках', "jobs:\n  a:\n    timeout-minutes: 1\n    steps:\n      - uses: 'actions/setup-node@v7'\n", 1],
  ['прямой setup-python', 'jobs:\n  a:\n    timeout-minutes: 1\n    steps:\n      - uses: actions/setup-python@v7\n', 1],
  ['наш общий шаг', 'jobs:\n  a:\n    timeout-minutes: 1\n    steps:\n      - uses: ./.github/actions/setup-web\n', 0],
]) {
  const got = setupProblems([{ name: 't.yml', text }], []).length;
  if (got !== want) failures.push(`самопроверка «${label}»: проблем ${got}, ожидалось ${want}`);
}
if (setupProblems([], [{ name: 'a/action.yml', text: 'runs:\n  steps:\n    - uses: actions/setup-node@v7\n' }]).length !== 1) {
  failures.push('самопроверка «composite с прямым setup-node»: не замечен');
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const files = read(WF_DIR, (n) => /\.ya?ml$/.test(n) && !VENDORED.has(n));
  const actions = read(ACTIONS_DIR, () => false);
  const problems = [...failures, ...setupProblems(files, actions)];
  if (problems.length) {
    console.error(`❌ Связка setup в workflow разошлась (${problems.length}):`);
    for (const f of problems) console.error(`  — ${f}`);
    process.exit(1);
  }
  console.log(`✅ Workflow (${files.length}) и composite (${actions.length}): прямых setup-* нет, ` +
              `timeout-minutes у всех джоб; ${SELF_CHECKS.length + 5} самопроверок разбора`);
}
