// Адреса, которые хостинг уводит 301 (`hosting.redirects` в firebase.json), — одна правда для сборки и
// тестов (#399). Страница под таким адресом на проде недостижима: собирать её незачем, а собранная она
// жила бы только в dist, без навигации, с сырым заголовком и вне проверок. Поддержан ровно тот вид
// источника, что есть в конфиге: литеральный путь с параметром `:lang`, без глобов.
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// От рабочего каталога, а не от import.meta.url: Astro бандлит модуль в dist/.prerender/chunks, и
// относительный путь от файла там уже не ведёт в корень репы. Сборка, e2e и скрипты идут из `web/`.
const CONFIG = resolve(process.cwd(), '..', 'firebase.json');

/** @returns {{ source: string, destination: string, type: number }[]} */
export function hostingRedirects() {
  // Молча вернуть «редиректов нет» нельзя: тогда собрались бы и страницы под 301 (#399).
  if (!existsSync(CONFIG)) throw new Error(`hosting-redirects: нет ${CONFIG} — запускай из web/`);
  return JSON.parse(readFileSync(CONFIG, 'utf8')).hosting?.redirects ?? [];
}

/** Путь без завершающего слэша — так записаны источники в конфиге. */
const bare = (/** @type {string} */ p) => p.replace(/\/+$/, '');

/**
 * Уводит ли хостинг этот путь редиректом. `path` — вида `/ru/dnd/srd-5.2/glossary/spells/`.
 * @param {string} path
 * @param {ReturnType<typeof hostingRedirects>} [redirects]
 */
export function isRedirected(path, redirects = hostingRedirects()) {
  const p = bare(path);
  return redirects.some((r) => {
    if (/[*?]/.test(r.source)) throw new Error(`hosting-redirects: глоб в источнике не поддержан: ${r.source}`);
    return ['en', 'ru'].some((lang) => bare(r.source.replaceAll(':lang', lang)) === p);
  });
}
