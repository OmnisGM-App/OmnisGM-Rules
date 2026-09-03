/**
 * Отпечаток ИСХОДНИКОВ, из которых собран `dist` (#251).
 *
 * Задача: не дать матрице пройти против устаревшей сборки. При `reuseExistingServer`
 * Playwright, получив ответ по HTTP, возвращается ДО запуска команды `webServer` — то есть
 * `npm run build` не выполняется. Поднятый час назад preview продолжает отдавать `dist`,
 * собранный из кода, которого в рабочем дереве давно нет, и прогон показывает зелёное.
 *
 * Сравнивать сервер с `dist` бессмысленно, и это выяснилось экспериментом: `astro preview` —
 * обычный статик-сервер, он читает файлы с диска на каждый запрос. Пересобрал `dist` — сервер
 * тут же отдаёт новое; такая сверка сходится всегда и не проверяет ничего.
 *
 * Значит сравнивать надо `dist` с ИСХОДНИКАМИ: на сборке отпечаток входных файлов пишется в
 * `dist/build-id.txt`, а страж считает его заново и сверяет. Разошлись — код менялся после
 * сборки, и переиспользовать этот preview нельзя.
 *
 * Почему хеш содержимого, а не случайный id: одинаковые исходники дают одинаковый отпечаток,
 * поэтому красное означает РЕАЛЬНОЕ расхождение, а не «ты пересобрал».
 *
 * Почему `путь + размер`, а не хеш содержимого каждого файла: контента тысячи файлов, читать
 * их целиком перед каждым прогоном расточительно, `stat` дешёв, а правка почти всегда меняет
 * размер. Исключение — правка «символ на символ»; ради неё целиком читаем конфиги и код
 * (`astro.config.mjs`, `package.json`, `web/src/lib`), где такая правка меняет поведение
 * сборки сильнее всего.
 */
import { createHash } from 'node:crypto';
import { readdir, readFile, stat, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, relative, resolve } from 'node:path';

const web = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const repoRoot = resolve(web, '..');

export const FINGERPRINT_FILE = 'build-id.txt';

/** Входы сборки: код и разметка сайта, ассеты и весь контент SRD (он лежит вне `web/`). */
const INPUT_DIRS = [
  join(web, 'src'),
  join(web, 'public'),
  join(repoRoot, 'src'),
];

/** Файлы, читаемые целиком: их правки меняют поведение сборки и не всегда меняют размер. */
const INPUT_FILES = [
  join(web, 'astro.config.mjs'),
  join(web, 'package.json'),
];

async function walk(dir, out = []) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) await walk(full, out);
    else out.push(full);
  }
  return out;
}

/** Отпечаток входов сборки. Те же исходники — тот же отпечаток. */
export async function fingerprint() {
  const hash = createHash('sha256');

  for (const dir of INPUT_DIRS) {
    if (!existsSync(dir)) continue;
    for (const file of (await walk(dir)).sort()) {
      hash.update(`${relative(repoRoot, file)}:${(await stat(file)).size}\n`);
    }
  }
  for (const file of INPUT_FILES) {
    hash.update(await readFile(file));
  }

  return hash.digest('hex').slice(0, 16);
}

if (process.argv[1]?.endsWith('build_fingerprint.mjs')) {
  const id = await fingerprint();
  await writeFile(join(web, 'dist', FINGERPRINT_FILE), `${id}\n`);
  console.log(`✔ отпечаток исходников: ${id} → dist/${FINGERPRINT_FILE}`);
}
