// Портреты существ (issue #201): силуэты в едином стиле, 512×512 webp, лежат в репо
// как статика — `public/img/{game}/creatures/{slug}.webp`.
//
// Папка ОДНА НА ИГРУ, а не на коллекцию API: один и тот же слаг живёт в разных
// коллекциях (83 существа есть и в `monsters` 5.1, и в `animals` 5.2 — в 2024 их
// вынесли в отдельный раздел), и раскладка по коллекциям означала бы две копии одного
// файла и два разных изображения у одного существа после следующей генерации (#202).
// Слаг уникален внутри игры, поэтому «игра + слаг» — достаточный ключ.
//
// Файла может не быть (новая сущность до прогона генератора) — потребители обязаны
// спрашивать hasCreatureImage(), а не строить URL вслепую.
import fs from 'node:fs';
import path from 'node:path';

export const CREATURE_IMAGE_SIZE = 512;

const PUBLIC_DIR = path.resolve(process.cwd(), 'public');

// Листинг папки кэшируем: getStaticPaths зовёт это на каждую из ~500 сущностей ×2 языка.
const cache = new Map();
const listing = (game) => {
  let set = cache.get(game);
  if (!set) {
    const dir = path.join(PUBLIC_DIR, 'img', game, 'creatures');
    set = new Set(
      fs.existsSync(dir) ? fs.readdirSync(dir).filter((f) => f.endsWith('.webp')).map((f) => f.slice(0, -5)) : [],
    );
    cache.set(game, set);
  }
  return set;
};

/** Путь от корня сайта. Не проверяет наличие файла — см. hasCreatureImage. */
export const creatureImagePath = (game, slug) => `/img/${game}/creatures/${slug}.webp`;

/** Есть ли портрет у существа. */
export const hasCreatureImage = (game, slug) => listing(game).has(slug);

/** Путь от корня либо null, если портрета нет. */
export const creatureImage = (game, slug) => (hasCreatureImage(game, slug) ? creatureImagePath(game, slug) : null);
