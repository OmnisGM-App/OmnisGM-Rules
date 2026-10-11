// Адреса, которые хостинг уводит 301 (`hosting.redirects` в firebase.json), — одна правда для сборки и
// тестов (#399). Страница под таким адресом на проде недостижима: собирать её незачем, а собранная она
// жила бы только в dist, без навигации, с сырым заголовком и вне проверок.
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// От рабочего каталога, а не от import.meta.url: Astro бандлит модуль в dist/.prerender/chunks, и
// относительный путь от файла там уже не ведёт в корень репы. Сборка, e2e и скрипты идут из `web/`.
const CONFIG = resolve(process.cwd(), '..', 'firebase.json');

// Поддержанная форма источника — белый список: сегменты из литералов и `:lang`. Всё остальное, что
// умеет Firebase (глобы, extglob `@(a|b)`, `{a,b}`, другие параметры, `:lang(en|ru)`, ключ `regex`),
// сравнилось бы буквально и молча вернуло бы страницу под 301 в сборку — поэтому это ошибка.
const SEGMENT = /^(?::lang|[A-Za-z0-9._-]+)$/;

/**
 * Проверенный список редиректов. Экспорт формы — для юнита.
 * @param {unknown} hosting — значение `hosting` из firebase.json
 * @returns {{ source: string, destination: string, type: number }[]}
 */
export function redirectsOf(hosting) {
  const list = /** @type {any} */ (hosting)?.redirects;
  // Молча вернуть «редиректов нет» нельзя: тогда собрались бы и страницы под 301 (#399).
  if (!Array.isArray(list) || list.length === 0) {
    throw new Error('hosting-redirects: в firebase.json нет непустого hosting.redirects');
  }
  for (const r of list) {
    if (typeof r?.source !== 'string') throw new Error(`hosting-redirects: запись без source: ${JSON.stringify(r)}`);
    const segments = /** @type {string[]} */ (r.source.split('/').slice(1));
    if (!r.source.startsWith('/') || !segments.every((/** @type {string} */ s) => SEGMENT.test(s))) {
      throw new Error(`hosting-redirects: неподдержанная форма источника: ${r.source}`);
    }
  }
  return list;
}

/** @returns {{ source: string, destination: string, type: number }[]} */
export function hostingRedirects() {
  if (!existsSync(CONFIG)) throw new Error(`hosting-redirects: нет ${CONFIG} — запускай из web/`);
  return redirectsOf(JSON.parse(readFileSync(CONFIG, 'utf8')).hosting);
}

/** Путь без завершающего слэша — так записаны источники в конфиге. */
const bare = (/** @type {string} */ p) => p.replace(/\/+$/, '');

/**
 * Уводит ли хостинг этот путь редиректом. `path` — вида `/ru/dnd/srd-5.2/glossary/spells/`.
 * @param {string} path
 * @param {{ source: string }[]} [redirects]
 */
export function isRedirected(path, redirects = hostingRedirects()) {
  const p = bare(path);
  return redirects.some((r) => ['en', 'ru'].some((lang) => bare(r.source.replaceAll(':lang', lang)) === p));
}
