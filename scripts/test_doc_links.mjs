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

// Что считаем ссылкой на инструмент. Только эти формы — расширение обязательно, каталог
// фиксирован: `web/scripts/foo.mjs` проверяем, `web/src/lib/foo.mjs` (код, а не инструмент) нет.
const TOOL_PATHS = [
  /\.github\/scripts\/[\w.-]+\.(?:sh|py)/g,
  /\.github\/workflows\/[\w.-]+\.ya?ml/g,
  /\.github\/actions\/[\w-]+\/action\.ya?ml/g,
  /(?:web\/)?scripts\/[\w.-]+\.mjs/g,
  /\.claude\/skills\/[\w-]+\/[\w.-]+/g,
];
// Слэш-команда: `/integrate-srd` — это .claude/skills/integrate-srd/SKILL.md.
const SLASH = /\/([a-z][a-z0-9-]{2,})(?=`)/g;
// Слова, похожие на слэш-команду по форме, но командами не являющиеся.
const NOT_A_SKILL = new Set(['api', 'img', 'sitemap-index', 'srd-5', 'srd-1']);

/** Ссылки на инструменты в одном документе: путь → как он записан. */
export function toolRefs(text) {
  const refs = new Set();
  // Ссылки живут в `коде`; вне бэктиков — проза, там путь может быть примером или частью URL.
  for (const [, code] of text.matchAll(/`([^`\n]+)`/g)) {
    for (const re of TOOL_PATHS) {
      for (const m of code.matchAll(re)) refs.add(m[0]);
    }
    const slash = code.match(/^\/([a-z][a-z0-9-]{2,})$/);
    if (slash && !NOT_A_SKILL.has(slash[1])) refs.add(`.claude/skills/${slash[1]}/SKILL.md`);
  }
  return [...refs];
}

/** Расхождения: названный инструмент, которого нет на диске. */
export function linkProblems(docs, exists) {
  const problems = [];
  for (const { name, text } of docs) {
    for (const ref of toolRefs(text)) {
      if (!exists(ref)) problems.push(`${name}: назван ${ref}, а его нет в репозитории`);
    }
  }
  return problems;
}

/** Документы, которые обязаны говорить правду про инструментарий. */
function readDocs(root) {
  const out = [];
  const add = (rel) => {
    const abs = resolve(root, rel);
    if (existsSync(abs) && statSync(abs).isFile()) out.push({ name: rel, text: readFileSync(abs, 'utf8') });
  };
  const walk = (rel) => {
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
const failures = [];
let checksRun = 0;
const check = (label, want, text, present = []) => {
  checksRun++;
  const has = new Set(present);
  const got = linkProblems([{ name: 'd.md', text }], (r) => has.has(r)).length;
  if (got !== want) failures.push(`самопроверка «${label}»: проблем ${got}, ожидалось ${want}`);
};

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
