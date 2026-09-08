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
// худший исход для гейта. Поэтому КАЖДАЯ строка секции `jobs:` с отступом в два пробела
// обязана быть распознана как ключ джобы: нераспознанная — не «не наш случай», а причина
// покраснеть. Расширения — обе формы GitHub (`.yml` и `.yaml`), у composite-действий тоже,
// и их каталог обходится на уровень вглубь: именно оттуда растёт исходный дрейф версий.
// Сам `setup-web` не сканируется намеренно — он и есть объявленное место версий, второй
// `setup-node` внутри него виден в одном файле рядом с первым (ревью #300).
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const WF_DIR = resolve(REPO, '.github/workflows');
const ACTIONS_DIR = resolve(REPO, '.github/actions');
const VENDORED = new Set(['claude-review.yml']);
// Единственное место, где прямой вызов setup-* законен, — сам общий шаг.
const HOME = 'setup-web';

/**
 * Прямые вызовы setup-node / setup-python (кавычки вокруг значения — валидный YAML).
 *
 * Ищем ПО СТРОКАМ-ключам `uses:`, а не подстрокой по всему файлу: подстрочный поиск красил
 * файл за упоминание `actions/setup-node` в комментарии или внутри `run:` — то есть за
 * прозу, а не за шаг (ревью #300).
 */
export function directSetups(text) {
  const found = [];
  for (const raw of text.replace(/\r\n/g, '\n').split('\n')) {
    const line = raw.trim();
    if (line.startsWith('#')) continue;
    const m = line.replace(/\s+#.*$/, '').match(/^-?\s*uses:\s*['"]?(actions\/setup-(?:node|python))/);
    if (m) found.push(m[1]);
  }
  return found;
}

/**
 * Литералы версий в вызывающем workflow. Пустая строка законна — это явный отказ («Node
 * этой джобе не нужен»); любое другое значение — вторая копия версии, ровно тот дрейф,
 * ради которого заведён composite: запрет прямого `uses: actions/setup-python` закрывал
 * только форму записи, а мутация «3.12 → 3.11» в одном из четырёх вызовов гейт не видел
 * (ревью #300).
 */
export function versionLiterals(text) {
  const found = [];
  for (const raw of text.replace(/\r\n/g, '\n').split('\n')) {
    const line = raw.trim();
    if (line.startsWith('#')) continue;
    const m = line.replace(/\s+#.*$/, '').match(/^(node|python)-version:\s*(.*)$/);
    if (!m) continue;
    const value = m[2].replace(/^['"]|['"]$/g, '').trim();
    if (value) found.push(`${m[1]}-version: ${m[2].trim()}`);
  }
  return found;
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
  const norm = text.replace(/\r\n/g, '\n');
  const at = norm.startsWith('jobs:') ? 0 : norm.indexOf('\njobs:') + 1;
  if (at === 0 && !norm.startsWith('jobs:')) return { jobs, problem: 'нет секции jobs' };
  // Секция кончается следующим ключом нулевого уровня: `jobs:` не обязан быть последним.
  const rest = norm.slice(at).split('\n');
  const end = rest.findIndex((l, i) => i > 0 && /^[^\s#]/.test(l));
  const lines = end < 0 ? rest : rest.slice(0, end);
  // Ключи джоб — по строкам, а не split'ом по разделителю: split требовал, чтобы за именем
  // сразу шёл перевод строки, и любой хвост (комментарий, пробел, кавычки) прятал джобу.
  const keys = [];
  for (let i = 0; i < lines.length; i++) {
    // Всё, что стоит на два пробела внутри `jobs:`, — ключ джобы. Строка, которую не
    // разобрали, останавливает гейт: сверять «сколько нашли» с «сколько нашли» смысла нет,
    // а вот нераспознанная форма — ровно тот fail-open, ради которого гейт написан.
    if (!/^ {2}[^\s]/.test(lines[i]) || /^ {2}#/.test(lines[i])) continue;
    const m = lines[i].match(/^ {2}(['"]?)([\w-]+)\1\s*:(.*)$/);
    // Flow-стиль (`job: {runs-on: …}`) в наших workflow не встречается, и разбирать его
    // текстом — заведомо хрупко: называем и падаем, а не делаем вид, что проверили.
    const tail = m ? m[3].replace(/#.*$/, '').trim() : '';
    if (!m || tail) {
      return { jobs, problem: `строка ${i + 1} секции jobs («${lines[i].trim()}») не разобрана` };
    }
    keys.push({ name: m[2], line: i });
  }
  for (let k = 0; k < keys.length; k++) {
    const from = keys[k].line;
    const to = k + 1 < keys.length ? keys[k + 1].line : lines.length;
    const block = lines.slice(from, to).join('\n');
    // Якорь по началу строки и ровно по отступу джобы — обязателен: незакреплённый
    // `/ {4}timeout-minutes:/` ловил ШАГОВЫЙ потолок (8 пробелов) и зеленил джобу без
    // своего; ровно на release.yml, единственной джобе с историей упора в шестичасовой
    // дефолт (ревью #300). Значение — целое положительное: `0` и пустое не считаются.
    jobs.set(keys[k].name, /^ {4}timeout-minutes:\s*[1-9][0-9]*\s*(?:#.*)?$/m.test(block));
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
    for (const lit of versionLiterals(text)) {
      problems.push(`${name}: своя версия «${lit}» — канон живёт в ` +
                    `.github/actions/${HOME}, здесь законен только явный отказ '' (#287)`);
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

/** Файлы каталога workflow: обе формы расширения, вендорные — мимо. */
function readWorkflows(dir) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true })
    .filter((e) => e.isFile() && /\.ya?ml$/.test(e.name) && !VENDORED.has(e.name))
    .map((e) => ({ name: e.name, text: readFileSync(resolve(dir, e.name), 'utf8') }));
}

/**
 * Composite-действия: `action.yml` и `action.yaml`, на уровень вглубь (группирующий каталог
 * — законная раскладка). Сам `setup-web` пропускаем: он и есть место объявления версий.
 */
function readActions(dir, rel = '.github/actions', depth = 1) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    if (!e.isDirectory() || e.name === HOME) return [];
    const here = readdirSync(resolve(dir, e.name), { withFileTypes: true })
      .filter((f) => f.isFile() && /^action\.ya?ml$/.test(f.name))
      .map((f) => ({
        name: `${rel}/${e.name}/${f.name}`,
        text: readFileSync(resolve(dir, e.name, f.name), 'utf8'),
      }));
    const deeper = depth > 0 ? readActions(resolve(dir, e.name), `${rel}/${e.name}`, depth - 1) : [];
    return [...here, ...deeper];
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
  // Ровно форма release.yml, на которой гейт был fail-open: у джобы своего потолка нет,
  // а у шага — есть (ревью #300).
  ['потолок только у шага', 'jobs:\n  a:\n    steps:\n      - run: x\n        timeout-minutes: 40\n', 1],
  ['потолок нулевой', 'jobs:\n  a:\n    timeout-minutes: 0\n', 1],
  ['потолок пустой', 'jobs:\n  a:\n    timeout-minutes:\n', 1],
  ['потолок с комментарием', 'jobs:\n  a:\n    timeout-minutes: 5  # хватает\n', 0],
  ['неразобранная строка на уровне джобы', 'jobs:\n  - a\n', 1],
  ['секция после jobs не считается джобой',
   'jobs:\n  a:\n    timeout-minutes: 1\nfoo:\n  bar: 1\n', 0],
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
  // Проза про setup-node — не шаг: подстрочный поиск красил файл за упоминание (ревью #300).
  ['упоминание в комментарии',
   'jobs:\n  a:\n    timeout-minutes: 1\n    # не пишите uses: actions/setup-node здесь\n', 0],
  ['упоминание внутри run',
   'jobs:\n  a:\n    timeout-minutes: 1\n    steps:\n      - run: echo "uses: actions/setup-node"\n', 0],
  ['шаг с комментарием в хвосте',
   'jobs:\n  a:\n    timeout-minutes: 1\n    steps:\n      - uses: actions/setup-node@v7  # зачем-то\n', 1],
  ['своя версия Python у вызывающего',
   "jobs:\n  a:\n    timeout-minutes: 1\n    steps:\n      - uses: ./.github/actions/setup-web\n        with:\n          python-version: '3.11'\n", 1],
  ['явный отказ от Node — законен',
   "jobs:\n  a:\n    timeout-minutes: 1\n    steps:\n      - uses: ./.github/actions/setup-web\n        with:\n          node-version: ''\n", 0],
]) {
  const got = setupProblems([{ name: 't.yml', text }], []).length;
  if (got !== want) failures.push(`самопроверка «${label}»: проблем ${got}, ожидалось ${want}`);
}
if (setupProblems([], [{ name: 'a/action.yml', text: 'runs:\n  steps:\n    - uses: actions/setup-node@v7\n' }]).length !== 1) {
  failures.push('самопроверка «composite с прямым setup-node»: не замечен');
}

// `process.argv[1]` пуст при `node --input-type=module -e` — импорт гейта из другого
// скрипта не должен падать на самом определении «запущен ли я напрямую» (ревью #300).
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const files = readWorkflows(WF_DIR);
  const actions = readActions(ACTIONS_DIR);
  const problems = [...failures, ...setupProblems(files, actions)];
  if (problems.length) {
    console.error(`❌ Связка setup в workflow разошлась (${problems.length}):`);
    for (const f of problems) console.error(`  — ${f}`);
    process.exit(1);
  }
  console.log(`✅ Workflow (${files.length}) и composite (${actions.length}): прямых setup-* нет, ` +
              `timeout-minutes у всех джоб; ${SELF_CHECKS.length + 10} самопроверок разбора`);
}
