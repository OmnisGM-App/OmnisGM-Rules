// Страницы сущностей с картинкой (#407): по разделу очереди генератора (`KINDS` в scripts/gen-images.mjs)
// со своей страницей — первая сущность API с `image`. Общий источник для e2e `entity-images.spec.ts`
// и гейта `verify_dist_entity_images.mjs`: e2e в PR CI не ходит, гейт ходит.
import fs from 'node:fs';
import path from 'node:path';
import { KINDS, ORDER } from '../../scripts/gen-images.mjs';
import { entityPath } from '../src/lib/equipment-path.mjs';

/** Ключ версии в API → сегмент URL; то же, что `VERSION_SLUG` в src/lib/entities.ts (сверяет e2e). */
export const VERSION_SEGMENT = { srd52: 'srd-5.2', srd51: 'srd-5.1', srd10: 'srd-1.0' };

// Коллекция API и сегмент её маршрута совпадают не всегда, а общей карты для этого нет.
export const PAGE_SEGMENT = {
  monsters: 'monsters-a-z',
  actions: 'rules-glossary/action',
  'rules-terms': 'rules-glossary/term',
  'areas-of-effect': 'rules-glossary/area-of-effect',
  conditions: 'rules-glossary/conditions',
};
// Варианты классовых умений (#379) показываются на странице своей группы, у варианта — якорь.
export const GROUP_PAGES = new Set(['class-options']);
// Мастерство и свойства оружия своих страниц не имеют: картинка нужна только полю `image` API.
export const API_ONLY = new Set(['masteries', 'weapon-properties']);
// Снаряжение (#412): предмет группы живёт под ней, поэтому маршрут — с остатком пути.
export const NESTED = new Set(['equipment', 'magic-items']);

/**
 * @typedef {{ json: string, game: string, version: string, segment: string, collection: string }} ImageSource
 */

/**
 * Коллекции очереди, от вида, который генератор закрывает первым, к последнему.
 * @param {string} apiRoot папка `src/data/api`
 * @returns {ImageSource[]}
 */
export function imageSources(apiRoot) {
  /** @type {ImageSource[]} */
  const out = [];
  for (const kind of ORDER) {
    for (const [game, collections] of Object.entries(KINDS[kind].api ?? {})) {
      const gameDir = path.join(apiRoot, game);
      if (!fs.existsSync(gameDir)) continue;
      for (const ver of fs.readdirSync(gameDir).sort()) {
        // Без сегмента версии страницы нет.
        const version = VERSION_SEGMENT[/** @type {keyof typeof VERSION_SEGMENT} */ (ver)];
        if (!version) continue;
        for (const collection of /** @type {string[]} */ (collections)) {
          const versions = KINDS[kind].versions?.[collection];
          if (versions && !versions.includes(ver)) continue;
          const json = `${game}/${ver}/ru/${collection}/all.json`;
          if (!fs.existsSync(path.join(apiRoot, json))) continue;
          out.push({ json, game, version, segment: PAGE_SEGMENT[/** @type {keyof typeof PAGE_SEGMENT} */ (collection)] ?? collection, collection });
        }
      }
    }
  }
  return out;
}

/**
 * Адрес страницы сущности (RU), без хоста.
 * @param {ImageSource} s
 * @param {{ slug: string, feature?: { key: string }, group?: unknown }} entity
 */
export const pageUrl = (s, entity) => (GROUP_PAGES.has(s.collection)
  ? `/ru/${s.game}/${s.version}/${s.segment}/${entity.feature?.key}/#${entity.slug}`
  : `/ru/${s.game}/${s.version}/${s.segment}/${entityPath(s.collection, entity)}/`);

/**
 * По разделу со своей страницей — первая сущность с `image`. Раздел без такой сущности — ошибка:
 * иначе проверка молча стала бы пустой.
 * @param {string} apiRoot
 * @returns {{ pages: { url: string, image: string, json: string }[], missing: string[] }}
 */
export function imagePages(apiRoot) {
  const pages = [];
  const missing = [];
  for (const s of imageSources(apiRoot)) {
    if (API_ONLY.has(s.collection) || GROUP_PAGES.has(s.collection)) continue;
    const entity = JSON.parse(fs.readFileSync(path.join(apiRoot, s.json), 'utf8')).find((/** @type {{ image?: string }} */ e) => e.image);
    if (!entity) { missing.push(s.json); continue; }
    pages.push({ url: pageUrl(s, entity), image: entity.image, json: s.json });
  }
  return { pages, missing };
}
