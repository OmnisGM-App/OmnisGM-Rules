/**
 * Отпечаток ИСХОДНИКОВ, из которых собран `dist` (#251): страж e2e сверяет его с
 * `dist/build-id.txt`, чтобы `reuseExistingServer` не прогнал матрицу против устаревшей сборки.
 * Контент — «путь + размер» (`stat` дешёв); код и конфиги сборки — целиком: правка «символ на
 * символ» (`Math.max(1, …)` → `2` в rehype-плагине) размер не меняет.
 */
import { createHash } from 'node:crypto';
import { readdir, readFile, rm, stat, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { basename, dirname, join, relative, resolve } from 'node:path';

const DEFAULT_WEB = resolve(dirname(fileURLToPath(import.meta.url)), '..');

export const FINGERPRINT_FILE = 'build-id.txt';

/**
 * @param {string} web — корень `web/`
 */
function inputsOf(web) {
  const repoRoot = resolve(web, '..');

  return {
    repoRoot,
    dirs: [join(web, 'src'), join(web, 'public'), join(repoRoot, 'src')],
    dirsFull: [join(web, 'src', 'lib'), join(web, 'scripts')],
    files: [
      join(web, 'astro.config.mjs'),
      join(web, 'package.json'),
      join(web, 'package-lock.json'),
      join(web, 'tsconfig.json'),
      join(web, '.env'),
    ],
  };
}

/** Мусор файловых менеджеров: открытая в Finder `public` двигала бы отпечаток. */
const JUNK = /^(\.DS_Store|Thumbs\.db|\._.*)$/;

/**
 * @param {string} dir
 * @param {string[]} out
 * @returns {Promise<string[]>}
 */
async function walk(dir, out = []) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    if (JUNK.test(entry.name)) continue;

    const full = join(dir, entry.name);
    if (entry.isDirectory()) await walk(full, out);
    else out.push(full);
  }
  return out;
}

export async function fingerprint(web = DEFAULT_WEB) {
  const { repoRoot, dirs, dirsFull, files } = inputsOf(web);
  const hash = createHash('sha256');

  for (const dir of dirs) {
    if (!existsSync(dir)) continue;
    for (const file of (await walk(dir)).sort()) {
      hash.update(`${relative(repoRoot, file)}:${(await stat(file)).size}\n`);
    }
  }
  for (const dir of dirsFull) {
    if (!existsSync(dir)) continue;
    for (const file of (await walk(dir)).sort()) {
      hash.update(await readFile(file));
    }
  }
  for (const file of files) {
    if (existsSync(file)) hash.update(await readFile(file));
  }

  return hash.digest('hex').slice(0, 16);
}

/**
 * Снимок — ДО сборки (`--stash`), в `dist` — ПОСЛЕ: отпечаток в `postbuild` захватил бы файл,
 * сохранённый во время сборки, которого в `dist` нет.
 */
export const stashPath = (web = DEFAULT_WEB) => join(web, '.build-fingerprint');

// По имени файла, а не `endsWith`: `test_build_fingerprint.mjs` тоже так оканчивается, и импорт
// из теста запускал CLI-ветку.
if (basename(process.argv[1] ?? '') === 'build_fingerprint.mjs') {
  // `--web=<путь>` — для теста на игрушечном дереве вместо рабочего `dist`.
  const web = process.argv.find((arg) => arg.startsWith('--web='))?.slice('--web='.length) ?? DEFAULT_WEB;
  const stash = stashPath(web);

  if (process.argv.includes('--stash')) {
    const id = await fingerprint(web);
    await writeFile(stash, `${id}\n`);
    console.log(`✔ отпечаток исходников снят до сборки: ${id}`);
  } else {
    // `--commit` (и запуск без флагов — ручной пересчёт): кладём снимок в dist.
    const id = existsSync(stash) ? (await readFile(stash, 'utf8')).trim() : await fingerprint(web);
    await writeFile(join(web, 'dist', FINGERPRINT_FILE), `${id}\n`);
    if (existsSync(stash)) await rm(stash);
    console.log(`✔ отпечаток исходников: ${id} → dist/${FINGERPRINT_FILE}`);
  }
}
