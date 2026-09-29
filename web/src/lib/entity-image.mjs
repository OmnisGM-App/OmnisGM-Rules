// Картинки сущностей (issue #201 — портреты существ, #202 — иконки заклинаний и
// магических предметов): 512×512 webp, лежат в репо статикой —
// `public/img/{game}/{kind}/{slug}.webp`.
// Раскладка и формат целиком: documentation/entity-images.md.
import fs from 'node:fs';
import path from 'node:path';

export const ENTITY_IMAGE_SIZE = 512;

const PUBLIC_DIR = path.resolve(process.cwd(), 'public');

// Листинг папки кэшируем: getStaticPaths зовёт это на каждую сущность ×2 языка.
/** @type {Map<string, Set<string>>} */
const cache = new Map();
const listing = (/** @type {string} */ game, /** @type {string} */ kind) => {
  const key = `${game}/${kind}`;
  let set = cache.get(key);
  if (!set) {
    const dir = path.join(PUBLIC_DIR, 'img', game, kind);
    set = new Set(
      fs.existsSync(dir) ? fs.readdirSync(dir).filter((f) => f.endsWith('.webp')).map((f) => f.slice(0, -5)) : [],
    );
    cache.set(key, set);
  }
  return set;
};

/** Путь от корня сайта. Не проверяет наличие файла — см. hasEntityImage. */
export const entityImagePath = (/** @type {string} */ game, /** @type {string} */ kind, /** @type {string} */ slug) => `/img/${game}/${kind}/${slug}.webp`;

export const hasEntityImage = (/** @type {string} */ game, /** @type {string} */ kind, /** @type {string} */ slug) => listing(game, kind).has(slug);

export const entityImage = (/** @type {string} */ game, /** @type {string} */ kind, /** @type {string} */ slug) =>
  (hasEntityImage(game, kind, slug) ? entityImagePath(game, kind, slug) : null);

/** Портрет существа — папка существ общая на игру. */
export const creatureImage = (/** @type {string} */ game, /** @type {string} */ slug) => entityImage(game, 'creatures', slug);
