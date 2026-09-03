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
import { basename, dirname, join, relative, resolve } from 'node:path';

const DEFAULT_WEB = resolve(dirname(fileURLToPath(import.meta.url)), '..');

export const FINGERPRINT_FILE = 'build-id.txt';

/**
 * Наборы входов считаются от корня `web`, а не берутся из констант модуля: так тест
 * (`test_build_fingerprint.mjs`) собирает игрушечное дерево во временном каталоге и проверяет
 * инварианты, не трогая рабочее. Поведение по умолчанию при этом прежнее.
 */
function inputsOf(web) {
  const repoRoot = resolve(web, '..');

  return {
    repoRoot,
    /** Учитываются как «путь + размер»: контент и ассеты, где правка меняет размер. */
    dirs: [join(web, 'src'), join(web, 'public'), join(repoRoot, 'src')],
    /** Читаются целиком: код, где правка «символ на символ» меняет вывод сборки. */
    dirsFull: [join(web, 'src', 'lib'), join(web, 'scripts')],
    /** Читаются целиком: конфиги и окружение сборки. */
    files: [
      join(web, 'astro.config.mjs'),
      join(web, 'package.json'),
      join(web, 'package-lock.json'),
      join(web, 'tsconfig.json'),
      join(web, '.env'),
    ],
  };
}

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
 * Снимок берётся ДО сборки, а кладётся в `dist` ПОСЛЕ неё — двумя фазами, и это не лишний шаг.
 *
 * Считай мы отпечаток в `postbuild`, между чтением исходников сборкой и снятием отпечатка было
 * бы открыто окно: файл, сохранённый в эти секунды, попал бы в отпечаток, но не в `dist`.
 * Страж потом вечно видел бы совпадение и молчал про правку, которой в сборке нет.
 */
export const stashPath = (web = DEFAULT_WEB) => join(web, '.build-fingerprint');

// Сравнение по ИМЕНИ ФАЙЛА, а не `endsWith`: `test_build_fingerprint.mjs` тоже заканчивается
// на `build_fingerprint.mjs`, и при импорте из теста запускалась CLI-ветка — она писала в
// настоящий `dist`, которого в CI на этом шаге ещё нет. Локально дефект прятался за тем, что
// `dist` уже был собран.
if (basename(process.argv[1] ?? '') === 'build_fingerprint.mjs') {
  // `--web=<путь>` нужен тесту (`test_build_fingerprint.mjs`): он гоняет обе фазы на игрушечном
  // дереве во временном каталоге, а не на рабочем — иначе проверка переписывала бы настоящий
  // `dist/build-id.txt` и зависела бы от того, была ли уже сборка.
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
