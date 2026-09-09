#!/usr/bin/env node
// Страж ссылок документации на инструментарий (issue #296).
//
// Повод. Скилл `/integrate-srd` полгода описывал интеграцию в MkDocs: правил `src/site/index.md`,
// звал `prepare_docs.sh` и дописывал `.github/workflows/pages.yml` — файл, которого в репозитории
// уже не было. Скилл при этом стоял фазой в обоих оркестраторах пайплайна, то есть новую систему
// «интегрировали в сайт» по инструкции для снесённого движка. Ничего не краснело: документация и
// скиллы ни во что не собираются, и удаление файла ничего в них не ломает.
//
// Поэтому проверяем ровно один класс утверждений — ССЫЛКУ НА ИНСТРУМЕНТ. Если документ называет
// скрипт, workflow, composite-действие или скилл, тот обязан существовать. Прозу, URL и пути к
// контенту не трогаем: они меняются на порядок чаще и ложные срабатывания похоронили бы гейт.
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), '..');

// Что считаем ссылкой на инструмент. Формы перечислены явно, и каждая слева заякорена:
// без якоря `packages/brand/scripts/build.mjs` давал бы находку про `scripts/build.mjs` —
// путь, которого в документе нет вовсе, и диагностика уводила бы не туда (ревью #314).
// Каталог фиксирован: `web/scripts/foo.mjs` проверяем, `web/src/lib/foo.mjs` (код системы,
// а не инструмент) — нет.
const HEAD = '(?<![\\w/.-])';
const TOOL_PATHS = [
  // Скрипты обоих каталогов и всех трёх расширений: `.sh` под `web/scripts` — это
  // `check_security_headers.sh` и `check_edge_cache.sh`, которые гоняет health.yml.
  new RegExp(`${HEAD}(?:\\.github|web)/scripts/[\\w.-]+\\.(?:mjs|sh|py)`, 'g'),
  new RegExp(`${HEAD}scripts/[\\w.-]+\\.mjs`, 'g'),
  new RegExp(`${HEAD}\\.github/workflows/[\\w.-]+\\.ya?ml`, 'g'),
  // Composite-действие называют и каталогом (`.github/actions/setup-web`), и файлом:
  // `existsSync` одинаково верен для обоих, а формы «только с /action.yml» в корпусе нет
  // ни одной — паттерн был непроверяемой веткой (ревью #314).
  new RegExp(`${HEAD}\\.github/actions/[\\w-]+(?:/action\\.ya?ml)?`, 'g'),
  new RegExp(`${HEAD}\\.claude/skills/[\\w-]+/[\\w.-]+`, 'g'),
  // Правила — тот же класс: их обходит `readDocs`, они называются в скиллах и в CLAUDE.md,
  // и снести правило так же легко, как скрипт.
  new RegExp(`${HEAD}\\.claude/rules/[\\w.-]+\\.md`, 'g'),
];
// Слэш-команда: `/integrate-srd` — это .claude/skills/integrate-srd/SKILL.md.
const SLASH = /\/([a-z][a-z0-9-]{2,})(?=`)/g;
// Слова, похожие на слэш-команду по форме, но командами не являющиеся.
const NOT_A_SKILL = new Set(['api', 'img', 'sitemap-index', 'srd-5', 'srd-1']);

/** Ссылки на инструменты в одном документе: путь → как он записан. */
export function toolRefs(/** @type {string} */ text) {
  /** @type {Set<string>} */
  const refs = new Set();
  const scan = (/** @type {string} */ chunk) => {
    for (const re of TOOL_PATHS) {
      for (const m of chunk.matchAll(re)) refs.add(m[0]);
    }
  };
  // Огороженные блоки — ПЕРВЫМИ и целиком. Команда внутри ```bash — самая частая форма
  // вызова инструмента в скилле (агент её исполняет), и путь там стоит вообще без
  // бэктиков. Инлайн-разбор её не видел: класс `[^`\n]` не пересекает перевод строки,
  // и тело блока не читалось вовсе — четыре живых хелпера скиллов гейт не проверял ни
  // до, ни после сноса (ревью #314). Маркер фенса в скиллах бывает отступлен, поэтому
  // `[ \t]*`.
  const FENCE = /^[ \t]*```[^\n]*\n([\s\S]*?)^[ \t]*```/gm;
  const fences = [...text.matchAll(FENCE)];
  for (const [, body] of fences) scan(body);
  // Вне блоков ссылки живут в `коде`: в прозе путь может быть примером или частью URL.
  // Текст блоков вырезаем, иначе бэктики фенса склеились бы с соседними в ложный спан.
  let inline = text;
  for (const [whole] of fences) inline = inline.replace(whole, '\n');
  for (const [, code] of inline.matchAll(/`([^`\n]+)`/g)) {
    scan(code);
    const slash = code.match(/^\/([a-z][a-z0-9-]{2,})$/);
    if (slash && !NOT_A_SKILL.has(slash[1])) refs.add(`.claude/skills/${slash[1]}/SKILL.md`);
  }
  return [...refs];
}

/** Расхождения: названный инструмент, которого нет на диске. */
/**
 * @param {{name: string, text: string}[]} docs
 * @param {(ref: string) => boolean} exists
 * @returns {string[]}
 */
export function linkProblems(docs, exists) {
  /** @type {string[]} */
  const problems = [];
  for (const { name, text } of docs) {
    for (const ref of toolRefs(text)) {
      if (!exists(ref)) problems.push(`${name}: назван ${ref}, а его нет в репозитории`);
    }
  }
  return problems;
}

/** Документы, которые обязаны говорить правду про инструментарий. */
function readDocs(/** @type {string} */ root) {
  /** @type {{name: string, text: string}[]} */
  const out = [];
  const add = (/** @type {string} */ rel) => {
    const abs = resolve(root, rel);
    if (existsSync(abs) && statSync(abs).isFile()) out.push({ name: rel, text: readFileSync(abs, 'utf8') });
  };
  const walk = (/** @type {string} */ rel) => {
    const abs = resolve(root, rel);
    if (!existsSync(abs)) return;
    for (const e of readdirSync(abs, { withFileTypes: true })) {
      if (e.isDirectory()) walk(`${rel}/${e.name}`);
      else if (e.name.endsWith('.md')) add(`${rel}/${e.name}`);
    }
  };
  add('CLAUDE.md');
  add('README.md');
  walk('documentation');
  walk('.claude/skills');
  walk('.claude/rules');
  return out;
}

// ── Самопроверки разбора: числа считаются, а не заявляются (ревью #300) ─────────────────
/** @type {string[]} */
const failures = [];
let checksRun = 0;
const check = (/** @type {string} */ label, /** @type {number} */ want, /** @type {string} */ text,
               /** @type {string[]} */ present = []) => {
  checksRun++;
  const has = new Set(present);
  const got = linkProblems([{ name: 'd.md', text }], (r) => has.has(r)).length;
  if (got !== want) failures.push(`самопроверка «${label}»: проблем ${got}, ожидалось ${want}`);
};

// Счёт расхождений — половина правды: ослепни один паттерн целиком, все проверки «сколько
// проблем» останутся зелёными (ревью #314). Поэтому вторая таблица сверяет РАСПОЗНАННОЕ:
// на каждую форму из TOOL_PATHS — свой ряд, и на каждую он один.
const recognizes = (/** @type {string} */ label, /** @type {string} */ text, /** @type {string[]} */ want) => {
  checksRun++;
  const got = toolRefs(text).sort().join('|');
  if (got !== [...want].sort().join('|')) {
    failures.push(`распознавание «${label}»: [${got}], ожидалось [${want.sort().join('|')}]`);
  }
};
recognizes('скрипт .github', '`.github/scripts/generate_api.py`', ['.github/scripts/generate_api.py']);
recognizes('скрипт web/.sh', '`web/scripts/check_edge_cache.sh`', ['web/scripts/check_edge_cache.sh']);
recognizes('скрипт корневой', '`scripts/test_unit_agenda.mjs`', ['scripts/test_unit_agenda.mjs']);
recognizes('workflow', '`.github/workflows/ci.yml`', ['.github/workflows/ci.yml']);
recognizes('composite каталогом', '`.github/actions/setup-web`', ['.github/actions/setup-web']);
recognizes('composite файлом', '`.github/actions/setup-web/action.yml`',
           ['.github/actions/setup-web/action.yml']);
recognizes('правило', '`.claude/rules/verify-import.md`', ['.claude/rules/verify-import.md']);
recognizes('хелпер скилла', '`.claude/skills/verify-import/check_markdown.py`',
           ['.claude/skills/verify-import/check_markdown.py']);
recognizes('слэш-команда', 'фаза `/verify-import`', ['.claude/skills/verify-import/SKILL.md']);
// Команда в ```bash — путь там стоит без бэктиков, и до ревью #314 гейт её не видел вовсе.
recognizes('путь внутри огороженного блока',
           '```bash\npython3 .claude/skills/verify-import/check_markdown.py src/\n```\n',
           ['.claude/skills/verify-import/check_markdown.py']);
recognizes('блок с отступом маркера',
           '  ```sh\n  bash web/scripts/check_csp.mjs\n  ```\n', ['web/scripts/check_csp.mjs']);
recognizes('чужой хвост не обрезается до нашего пути',
           '`packages/brand/scripts/build.mjs`', []);
recognizes('код web/src — не инструмент', '`web/src/lib/plural.mjs`', []);
recognizes('проза вне бэктиков и блоков', 'раньше был .github/scripts/prepare_docs.sh', []);

check('живой скрипт', 0, 'зовём `.github/scripts/generate_api.py`', ['.github/scripts/generate_api.py']);
check('снесённый скрипт', 1, 'зовём `.github/scripts/prepare_docs.sh`');
check('снесённый workflow', 1, 'см. `.github/workflows/pages.yml`');
check('живой composite', 0, '`.github/actions/setup-web/action.yml`', ['.github/actions/setup-web/action.yml']);
check('слэш-команда без скилла', 1, 'фаза `/integrate-srd`');
check('слэш-команда со скиллом', 0, 'фаза `/verify-import`', ['.claude/skills/verify-import/SKILL.md']);
// Проза — не ссылка: путь без бэктиков может быть примером, куском URL или именем из истории.
check('вне бэктиков не считается', 0, 'раньше был .github/scripts/prepare_docs.sh, теперь нет');
// Слэш-команда внутри пути или URL не должна превращаться в скилл.
check('часть пути не команда', 0, 'ставится в `web/public/img/dnd/creatures/`');
check('корневой скрипт', 1, 'гейт `scripts/test_missing.mjs`');
check('скрипт web', 0, '`web/scripts/check_csp.mjs`', ['web/scripts/check_csp.mjs']);
// Код системы под теми же расширениями инструментом не считается — иначе гейт лез бы в web/src.
check('код web/src вне области', 0, '`web/src/lib/plural.mjs`');
check('два расхождения в одном файле', 2,
      'зовём `.github/scripts/prepare_docs.sh` и `.github/scripts/split_sitemap.py`');

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const docs = readDocs(REPO);
  const problems = [...failures, ...linkProblems(docs, (r) => existsSync(resolve(REPO, r)))];
  if (problems.length) {
    console.error(`❌ Документация ссылается на несуществующий инструментарий (${problems.length}):`);
    for (const f of problems) console.error(`  — ${f}`);
    process.exit(1);
  }
  const refs = docs.reduce((n, d) => n + toolRefs(d.text).length, 0);
  console.log(`✅ Ссылки документации: ${refs} упоминаний инструментов в ${docs.length} документах ` +
              `на месте; ${checksRun} самопроверок разбора`);
}
