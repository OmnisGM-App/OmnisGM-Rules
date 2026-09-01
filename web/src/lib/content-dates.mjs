// Даты контента страницы для JSON-LD (issue #219).
//
// Источник — карта из git (scripts/gen-content-dates.mjs, путь .md → published/modified) плюс
// карта «ресурс → исходные .md» из парсера (scripts/gen-entity-data.mjs → _sources.json).
// Обе генерятся в prebuild и лежат в gitignored src/data/.
//
// Страница бывает двух видов:
//   • markdown-глава — один исходный файл, известен как sourceId («dnd/srd-5.2/ru/07_Spells»);
//   • сущностная (заклинание, монстр, навык) — собрана парсером из одного-двух файлов главы;
//     ресурс знает страница, файлы — карта _sources.json.
//
// Дат может не быть вовсе (мелкий клон в CI, сборка без git) — тогда возвращаем null, и
// вызывающий просто не кладёт поля в JSON-LD. Дата билда вместо настоящей — хуже, чем ничего:
// на 6000 страниц она означала бы «всё обновилось разом», а это шум для поисковика.
import fs from 'node:fs';
import path from 'node:path';

const DATA_ROOT = path.resolve(process.cwd(), 'src/data');

const readJson = (file, fallback) => {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf-8'));
  } catch {
    return fallback;
  }
};

const dates = readJson(path.join(DATA_ROOT, 'content-dates.json'), { shallow: true, files: {} });
const sources = readJson(path.join(DATA_ROOT, 'api', '_sources.json'), {});

/** Есть ли вообще даты в этой сборке (false на мелком клоне / без git). */
export const hasContentDates = () => Object.keys(dates.files ?? {}).length > 0;

/** Даты одного .md (путь от src/, с расширением или без). null, если файла нет в карте. */
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
export function datesForFiles(mdPaths) {
  const found = (mdPaths ?? []).map(datesForFile).filter(Boolean);
  if (!found.length) return null;
  return {
    published: found.map((d) => d.published).sort()[0],
    modified: found.map((d) => d.modified).sort().at(-1),
  };
}

/** Даты сущностной страницы по её коллекции API: game/ver/lang/resource. */
export function datesForResource(game, ver, lang, resource) {
  return datesForFiles(sources[`${game}/${ver}/${lang}/${resource}`]);
}

/**
 * Единая точка для шаблона: что бы страница ни знала о себе — sourceId (глава) или
 * контентный ресурс (сущность), — отсюда выходит одна пара дат или null.
 */
export function pageDates({ sourceId, contentSource } = {}) {
  if (sourceId) return datesForFile(sourceId);
  if (contentSource) {
    const { game, ver, lang, resource } = contentSource;
    return datesForResource(game, ver, lang, resource);
  }
  return null;
}
