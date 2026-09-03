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
 * размер.
 *
 * Где этого НЕ хватает — правка «символ на символ». Она не теоретическая: замена
 * `Math.max(1, …)` на `Math.max(2, …)` в rehype-плагине меняет заголовки всех страниц, не
 * трогая размер файла. Поэтому код и конфиги, задающие поведение сборки, читаются ЦЕЛИКОМ:
 * `web/src/lib`, `web/scripts` (генераторы данных и sitemap), `astro.config.mjs`,
 * `package.json`, `package-lock.json`, `tsconfig.json` и `web/.env` (переменные `PUBLIC_*`
 * инлайнятся в бандл).
 *
 * Что осознанно ОСТАВЛЕНО за бортом:
 *   • `.github/scripts/generate_api.py` — собирает JSON API при деплое (`firebase predeploy`),
 *     в локальный `dist` не попадает и на e2e не влияет;
 *   • `.github/**` целиком — CI в локальной сборке не участвует;
 *   • `documentation/`, `README*` — не входы сборки.
 */
import { createHash } from 'node:crypto';
import { readdir, readFile, rm, stat, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, relative, resolve } from 'node:path';

const web = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const repoRoot = resolve(web, '..');

export const FINGERPRINT_FILE = 'build-id.txt';

/** Входы, учитываемые как «путь + размер»: контент и ассеты, где правка меняет размер. */
const INPUT_DIRS = [
  join(web, 'src'),
  join(web, 'public'),
  join(repoRoot, 'src'),
];

/** Каталоги, читаемые целиком: код, где правка «символ на символ» меняет вывод сборки. */
const INPUT_DIRS_FULL = [
  join(web, 'src', 'lib'),
  join(web, 'scripts'),
];

/** Файлы, читаемые целиком: конфиги и окружение сборки. */
const INPUT_FILES = [
  join(web, 'astro.config.mjs'),
  join(web, 'package.json'),
  join(web, 'package-lock.json'),
  join(web, 'tsconfig.json'),
  join(web, '.env'),
];

/**
 * Мусор файловых менеджеров: к сборке отношения не имеет, а открытая в Finder папка `public`
 * иначе двигала бы отпечаток и давала ложное красное.
 */
const JUNK = /^(\.DS_Store|Thumbs\.db|\._.*)$/;

async function walk(dir, out = []) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    if (JUNK.test(entry.name)) continue;

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
  for (const dir of INPUT_DIRS_FULL) {
    if (!existsSync(dir)) continue;
    for (const file of (await walk(dir)).sort()) {
      hash.update(await readFile(file));
    }
  }
  for (const file of INPUT_FILES) {
    if (existsSync(file)) hash.update(await readFile(file));
  }

  return hash.digest('hex').slice(0, 16);
}

/**
 * Снимок берётся ДО сборки, а кладётся в `dist` ПОСЛЕ неё — двумя фазами, и это не лишний шаг.
 *
 * Считай мы отпечаток в `postbuild`, между чтением исходников сборкой и снятием отпечатка было
 * бы открыто окно: файл, сохранённый в эти секунды, попал бы в отпечаток, но не в `dist`.
 * Страж потом вечно видел бы совпадение и молчал про правку, которой в сборке нет.
 */
const STASH = join(web, '.build-fingerprint');

if (process.argv[1]?.endsWith('build_fingerprint.mjs')) {
  if (process.argv.includes('--stash')) {
    const id = await fingerprint();
    await writeFile(STASH, `${id}\n`);
    console.log(`✔ отпечаток исходников снят до сборки: ${id}`);
  } else {
    // `--commit` (и запуск без флагов — ручной пересчёт): кладём снимок в dist.
    const id = existsSync(STASH) ? (await readFile(STASH, 'utf8')).trim() : await fingerprint();
    await writeFile(join(web, 'dist', FINGERPRINT_FILE), `${id}\n`);
    if (existsSync(STASH)) await rm(STASH);
    console.log(`✔ отпечаток исходников: ${id} → dist/${FINGERPRINT_FILE}`);
  }
}
