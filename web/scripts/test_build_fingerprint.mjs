// Инварианты отпечатка сборки (issue #255, введён в #251). Юнит-тест на игрушечном дереве, а
// не проверка вручную: страж свежести — единственное, что мешает прогону идти против сборки,
// собранной из кода, которого в дереве уже нет, и его поведение проверялось только руками.
//
// Дерево строится во временном каталоге и повторяет структуру входов: `web/src`, `web/public`,
// `web/src/lib`, `web/scripts`, контент `src/` в корне и конфиги. Так проверки не зависят от
// содержимого репозитория и ничего в нём не трогают.
import { mkdtemp, mkdir, writeFile, rm, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fingerprint, FINGERPRINT_FILE } from './build_fingerprint.mjs';

const run = promisify(execFile);

let failed = 0;
const check = (ok, what, extra = '') => {
  if (!ok) {
    failed++;
    console.error(`  ✗ ${what}${extra ? `\n      ${extra}` : ''}`);
  }
};

/** Игрушечное дерево: минимум файлов на каждый вид входа. */
async function makeTree() {
  const root = await mkdtemp(join(tmpdir(), 'fp-test-'));
  const web = join(root, 'web');

  for (const dir of ['src/lib', 'src/pages', 'public/img', 'scripts', 'dist']) {
    await mkdir(join(web, dir), { recursive: true });
  }
  await mkdir(join(root, 'src', 'dnd'), { recursive: true });

  await writeFile(join(web, 'src/lib/plugin.mjs'), 'export const shift = Math.max(1, 2);\n');
  await writeFile(join(web, 'src/pages/index.astro'), '<h1>Заголовок</h1>\n');
  await writeFile(join(web, 'public/img/logo.svg'), '<svg/>\n');
  await writeFile(join(web, 'scripts/gen.mjs'), 'export const gen = () => 1;\n');
  await writeFile(join(web, 'astro.config.mjs'), 'export default {};\n');
  await writeFile(join(web, 'package.json'), '{"name":"toy"}\n');
  await writeFile(join(root, 'src/dnd/spells.md'), '# Заклинания\n');

  return { root, web };
}

const { root, web } = await makeTree();

// 1. Детерминированность: на неизменном дереве отпечаток повторяется.
const base = await fingerprint(web);
check(base === await fingerprint(web), 'отпечаток детерминирован на неизменном дереве');
check(/^[0-9a-f]{16}$/.test(base), 'отпечаток — 16 hex-символов', `получено «${base}»`);

// 2. Правка «символ на символ» в коде: размер файла НЕ меняется, вывод сборки — да.
// Ровно этот случай «путь + размер» пропускал бы, ради него код и читается целиком.
const plugin = join(web, 'src/lib/plugin.mjs');
const before = await readFile(plugin, 'utf8');
await writeFile(plugin, before.replace('Math.max(1', 'Math.max(2'));
check(before.length === (await readFile(plugin, 'utf8')).length, 'проба и правда не меняет размер файла');
check(await fingerprint(web) !== base, 'правка «символ на символ» в web/src/lib двигает отпечаток');
await writeFile(plugin, before);
check(await fingerprint(web) === base, 'откат правки возвращает прежний отпечаток');

// 3. Правка контента (размер меняется) и новый файл в public.
await writeFile(join(root, 'src/dnd/spells.md'), '# Заклинания\n\nОгненный шар.\n');
check(await fingerprint(web) !== base, 'правка контента двигает отпечаток');
await writeFile(join(root, 'src/dnd/spells.md'), '# Заклинания\n');

await writeFile(join(web, 'public/img/new.svg'), '<svg/>\n');
check(await fingerprint(web) !== base, 'новый файл в web/public двигает отпечаток');
await rm(join(web, 'public/img/new.svg'));

// 4. Мусор файловых менеджеров отпечаток не двигает: иначе открытая в Finder папка давала бы
// ложное красное на ровном месте.
for (const junk of ['.DS_Store', '._logo.svg']) {
  await writeFile(join(web, 'public/img', junk), 'мусор\n');
}
check(await fingerprint(web) === base, '.DS_Store и ._-файлы отпечаток НЕ двигают');
for (const junk of ['.DS_Store', '._logo.svg']) await rm(join(web, 'public/img', junk));

// 5. Конфиги читаются целиком — правка «символ на символ» в них тоже видна.
const cfg = join(web, 'astro.config.mjs');
await writeFile(cfg, 'export default {}; ');
check(await fingerprint(web) !== base, 'правка astro.config.mjs двигает отпечаток');
await writeFile(cfg, 'export default {};\n');

// 6. `--stash` / `--commit`: снимок берётся ДО сборки и переносится в dist ПОСЛЕ неё, иначе
// файл, сохранённый во время сборки, попал бы в отпечаток, но не в dist.
const script = new URL('build_fingerprint.mjs', import.meta.url).pathname;
const stash = join(web, '.build-fingerprint');

await run(process.execPath, [script, '--stash', `--web=${web}`]);
check(await readFile(stash, 'utf8').then(() => true, () => false), '--stash кладёт снимок в .build-fingerprint');
const stashed = (await readFile(stash, 'utf8')).trim();

// Между фазами дерево МЕНЯЕТСЯ — как если бы файл сохранили во время сборки. В dist обязан
// попасть снимок, снятый ДО, иначе страж вечно молчал бы именно про эту правку.
await writeFile(join(web, 'src/pages/index.astro'), '<h1>Правка во время сборки</h1>\n');

await run(process.execPath, [script, '--commit', `--web=${web}`]);
const committed = (await readFile(join(web, 'dist', FINGERPRINT_FILE), 'utf8')).trim();
check(committed === stashed, '--commit кладёт в dist снимок, снятый ДО сборки, а не пересчитанный');
check(committed !== await fingerprint(web), 'правка во время сборки в снимок не попала — окно закрыто');
check(await readFile(stash, 'utf8').then(() => false, () => true), '--commit удаляет временный снимок');

await rm(root, { recursive: true, force: true });

if (failed) {
  console.error(`\n❌ Отпечаток сборки: ${failed} проверок не прошло`);
  process.exit(1);
}
console.log('✓ Отпечаток сборки: все проверки прошли');
