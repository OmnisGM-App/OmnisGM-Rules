#!/usr/bin/env node
// Страж полноты тайпчека инструментов (issue #304): `files` в `web/tsconfig.tools.json` ловит
// исчезнувшую запись (TS6053), но не ПОЯВЛЕНИЕ нового файла — каждый `.mjs` трёх каталогов обязан
// быть в `files` или под маской `include`. Разбор текстовый (JSONC) и падает на непонятной форме.
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const CONFIG = 'web/tsconfig.tools.json';
// Каталоги, чьи `.mjs` обязаны быть под тайпчеком. Пути — от `web/`, как в самом конфиге.
const WATCHED = ['scripts', 'src/lib', '../scripts'];

/** Значения массива `files`/`include` из JSONC-конфига. Бросает, если формы нет. */
export function listOf(/** @type {string} */ text, /** @type {string} */ key) {
  // Комментарии снимаем только внутри массива: регулярка по всему тексту съела бы `https://`.
  const at = text.indexOf(`"${key}"`);
  if (at < 0) throw new Error(`в конфиге нет ключа «${key}»`);
  const open = text.indexOf('[', at);
  const close = text.indexOf(']', open);
  if (open < 0 || close < 0) throw new Error(`ключ «${key}» — не массив`);
  const body = text.slice(open + 1, close).replace(/\/\/[^\n]*/g, '');
  return [...body.matchAll(/"([^"]+)"/g)].map((m) => m[1]);
}

/** `.mjs` каталога, путями от `web/` (как их пишет конфиг). */
function mjsOf(/** @type {string} */ rel) {
  const abs = resolve(REPO, 'web', rel);
  if (!existsSync(abs)) return [];
  return readdirSync(abs, { withFileTypes: true })
    .filter((e) => e.isFile() && e.name.endsWith('.mjs'))
    .map((e) => `${rel}/${e.name}`);
}

/**
 * @param {string[]} files поимённые записи
 * @param {string[]} include маски
 * @param {string[]} present фактические пути от `web/`
 * @returns {string[]}
 */
export function uncovered(files, include, present) {
  const named = new Set(files);
  // Маска → префикс до первого `*`: маски простые, второй реализации глоба не заводим.
  const prefixes = include
    .filter((i) => i.endsWith('.mjs'))
    .map((i) => i.slice(0, i.indexOf('*')));
  return present.filter((p) => !named.has(p) && !prefixes.some((pre) => pre && p.startsWith(pre)));
}

// ── Самопроверки ────────────────────────────────────────────────────────────────────────
/** @type {string[]} */
const failures = [];
let checksRun = 0;
const check = (/** @type {string} */ label, /** @type {string[]} */ want,
               /** @type {string[]} */ files, /** @type {string[]} */ include,
               /** @type {string[]} */ present) => {
  checksRun++;
  const got = uncovered(files, include, present).sort();
  if (got.join('|') !== [...want].sort().join('|')) {
    failures.push(`самопроверка «${label}»: непокрыто [${got}], ожидалось [${want}]`);
  }
};
check('поимённый покрыт', [], ['scripts/a.mjs'], [], ['scripts/a.mjs']);
check('новый файл рядом с поимённым — дыра', ['scripts/b.mjs'],
      ['scripts/a.mjs'], [], ['scripts/a.mjs', 'scripts/b.mjs']);
check('маска покрывает новый файл', [], [], ['src/lib/**/*.mjs'],
      ['src/lib/a.mjs', 'src/lib/b.mjs']);
check('маска чужого каталога не покрывает', ['scripts/a.mjs'], [], ['src/lib/**/*.mjs'],
      ['scripts/a.mjs']);
check('пустое дерево', [], [], [], []);

/** @type {[string, string, string[]][]} */
const CONF_CASES = [
  ['files с комментарием между записями',
   '{ "files": [\n  // пояснение\n  "scripts/a.mjs",\n  "scripts/b.mjs"\n] }',
   ['scripts/a.mjs', 'scripts/b.mjs']],
  ['include одной строкой', '{ "include": ["e2e/**/*.ts", "src/lib/**/*.mjs"] }',
   ['e2e/**/*.ts', 'src/lib/**/*.mjs']],
];
for (const [label, text, want] of CONF_CASES) {
  checksRun++;
  const key = text.includes('"files"') ? 'files' : 'include';
  const got = listOf(text, key);
  if (got.join('|') !== want.join('|')) {
    failures.push(`самопроверка чтения «${label}»: [${got}], ожидалось [${want}]`);
  }
}
checksRun++;
try {
  listOf('{ "compilerOptions": {} }', 'files');
  failures.push('самопроверка «ключа нет»: разбор промолчал вместо исключения');
} catch { /* ожидаемо */ }

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const text = readFileSync(resolve(REPO, CONFIG), 'utf8');
  const problems = [...failures];
  try {
    const files = listOf(text, 'files');
    const include = listOf(text, 'include');
    const present = WATCHED.flatMap(mjsOf);
    if (!present.length) problems.push(`${CONFIG}: ни одного .mjs не найдено — разбор дерева сломан`);
    for (const miss of uncovered(files, include, present)) {
      problems.push(`${CONFIG}: ${miss} не под тайпчеком — впишите в files или под маску include`);
    }
    if (!problems.length) {
      console.log(`✅ Тайпчек инструментов: ${present.length} файлов .mjs в ${WATCHED.length} ` +
                  `каталогах покрыты (files ${files.length}, масок ${include.length}); ` +
                  `${checksRun} самопроверок`);
      process.exit(0);
    }
  } catch (e) {
    problems.push(`${CONFIG}: ${e instanceof Error ? e.message : e}`);
  }
  console.error(`❌ Тайпчек инструментов неполон (${problems.length}):`);
  for (const f of problems) console.error(`  — ${f}`);
  process.exit(1);
}
