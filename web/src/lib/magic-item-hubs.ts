// Хабы магических предметов (issue #20): фасетные списки по редкости.
// Роут: magic-items/rarity/[rarity]. Редкость в данных — английский ключ ('very rare');
// URL-слаг языконезависим ('very-rare') → общий каноникал + hreflang.
export { itemRarities, itemRarityLabel } from './item-rarity.mjs';
export type Lang = 'en' | 'ru';

export interface ItemLite {
  slug: string;
  name: string;
  name_en?: string | null;
  type?: string;
  rarity?: string | null; // EN-ключ: 'common' | … | 'artifact'; null — редкостей несколько или она варьируется
  rarities?: string[];    // все редкости предмета; пусто — «редкость варьируется»
  attunement?: { required?: boolean };
}

// Порядок = возрастание редкости (обычный → артефакт). slug — языконезависимый.
export const RARITIES: { slug: string; en: string; ru: string }[] = [
  { slug: 'common', en: 'common', ru: 'обычные' },
  { slug: 'uncommon', en: 'uncommon', ru: 'необычные' },
  { slug: 'rare', en: 'rare', ru: 'редкие' },
  { slug: 'very-rare', en: 'very rare', ru: 'очень редкие' },
  { slug: 'legendary', en: 'legendary', ru: 'легендарные' },
  { slug: 'artifact', en: 'artifact', ru: 'артефакты' },
];

export const rarityBySlug = (slug: string) => RARITIES.find((r) => r.slug === slug);
// Сырое поле rarity ('very rare') → слаг ('very-rare'); undefined, если редкость не задана/неизвестна.
export const raritySlug = (raw?: string | null): string | undefined => RARITIES.find((r) => r.en === raw)?.slug;
// Заголовок хаба редкости (мн. число): «Редкие предметы» / «Rare items».
export const rarityHubLabel = (slug: string, lang: Lang): string => {
  const r = rarityBySlug(slug);
  return r ? r[lang] : slug;
};
export const rarityRank = (raw?: string | null): number => {
  const i = RARITIES.findIndex((r) => r.en === raw);
  return i === -1 ? 99 : i;
};

export const byName = (a: { name: string }, b: { name: string }) => a.name.localeCompare(b.name);
