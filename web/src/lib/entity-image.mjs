// Картинки сущностей (issue #201 — портреты существ, #202 — иконки заклинаний и
// магических предметов): 512×512 webp, лежат в репо статикой —
// `public/img/{game}/{kind}/{slug}.webp`.
//
// У существ папка ОДНА НА ИГРУ («creatures»), а не на коллекцию API: один и тот же слаг
// живёт в разных коллекциях (83 существа есть и в `monsters` 5.1, и в `animals` 5.2 — в
// 2024 их вынесли в отдельный раздел), и раскладка по коллекциям означала бы две копии
// одного файла и два разных изображения у одного существа после следующей генерации.
// У заклинаний и магпредметов слаги ни с чем не пересекаются — там папка своя.
// Раскладка и формат целиком: documentation/entity-images.md.
//
// Файла может не быть (новая сущность до прогона генератора) — потребители обязаны
// спрашивать hasCreatureImage(), а не строить URL вслепую.
import fs from 'node:fs';
import path from 'node:path';

export const ENTITY_IMAGE_SIZE = 512;

const PUBLIC_DIR = path.resolve(process.cwd(), 'public');

// Листинг папки кэшируем: getStaticPaths зовёт это на каждую сущность ×2 языка.
const cache = new Map();
const listing = (game, kind) => {
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
export const entityImagePath = (game, kind, slug) => `/img/${game}/${kind}/${slug}.webp`;

/** Есть ли картинка у сущности. */
export const hasEntityImage = (game, kind, slug) => listing(game, kind).has(slug);

/** Путь от корня либо null, если картинки нет. */
export const entityImage = (game, kind, slug) =>
  (hasEntityImage(game, kind, slug) ? entityImagePath(game, kind, slug) : null);

/** Портрет существа — папка существ общая на игру. */
export const creatureImage = (game, slug) => entityImage(game, 'creatures', slug);
