// Даты контента страницы для JSON-LD (issue #219).
// Дат может не быть (мелкий клон, сборка без git) — null, а не дата билда: та означала бы
// для поисковика «всё обновилось разом».
import fs from 'node:fs';
import path from 'node:path';

const DATA_ROOT = path.resolve(process.cwd(), 'src/data');

/**
 * @template T
 * @param {string} file
 * @param {T} fallback
 * @returns {T}
 */
const readJson = (file, fallback) => {
  try {
    return /** @type {T} */ (JSON.parse(fs.readFileSync(file, 'utf-8')));
  } catch {
    return fallback;
  }
};

/** @type {{shallow: boolean, files: Record<string, {published: string, modified: string}>}} */
const DATES_EMPTY = { shallow: true, files: {} };
/** @type {Record<string, string[]>} */
const SOURCES_EMPTY = {};
const dates = readJson(path.join(DATA_ROOT, 'content-dates.json'), DATES_EMPTY);
const sources = readJson(path.join(DATA_ROOT, 'api', '_sources.json'), SOURCES_EMPTY);

export const hasContentDates = () => Object.keys(dates.files ?? {}).length > 0;

/** Даты одного .md (путь от src/, с расширением или без). null, если файла нет в карте. */
/**
 * @param {string|null|undefined} mdPath
 * @returns {{published: string, modified: string}|null}
 */
export function datesForFile(mdPath) {
  if (!mdPath) return null;
  const key = mdPath.endsWith('.md') ? mdPath : `${mdPath}.md`;
  return dates.files?.[key] ?? null;
}

/**
 * Даты набора файлов: published — самая ранняя, modified — самая поздняя. Ресурс может
 * собираться из нескольких глав (оружие и доспехи — из одной «Снаряжение»), и «страница
 * появилась» тогда = когда появился первый из источников.
 */
export function datesForFiles(/** @type {string[]|null|undefined} */ mdPaths) {
  const found = /** @type {{published: string, modified: string}[]} */
    ((mdPaths ?? []).map(datesForFile).filter(Boolean));
  if (!found.length) return null;
  return {
    published: found.map((d) => d.published).sort()[0],
    modified: found.map((d) => d.modified).sort().at(-1),
  };
}

/**
 * @param {string} game
 * @param {string} ver
 * @param {string} lang
 * @param {string} resource
 */
export function datesForResource(game, ver, lang, resource) {
  return datesForFiles(sources[`${game}/${ver}/${lang}/${resource}`]);
}

/**
 * Даты всего документа (#230): хаб редакции своего файла не имеет — он и есть документ целиком.
 */
/**
 * @param {string} game
 * @param {string} version
 * @param {string} lang
 */
export function datesForDoc(game, version, lang) {
  const prefix = `${game}/${version}/${lang}/`;
  return datesForFiles(Object.keys(dates.files ?? {}).filter((f) => f.startsWith(prefix)));
}

/**
 * @param {{
 *   sourceId?: string,
 *   contentSource?: {game: string, ver: string, lang: string, resource: string},
 *   docSource?: {game: string, version: string, lang: string},
 * }} [page]
 */
export function pageDates({ sourceId, contentSource, docSource } = {}) {
  if (sourceId) return datesForFile(sourceId);
  if (docSource) return datesForDoc(docSource.game, docSource.version, docSource.lang);
  if (contentSource) {
    const { game, ver, lang, resource } = contentSource;
    return datesForResource(game, ver, lang, resource);
  }
  return null;
}
