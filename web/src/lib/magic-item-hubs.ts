// Хабы магических предметов (issue #20): фасетные списки по редкости.
// Роут: magic-items/rarity/[rarity]. Редкость в данных — английский ключ ('very rare');
// URL-слаг языконезависим ('very-rare') → общий каноникал + hreflang.
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
// Подпись редкости в единственном числе (для колонки таблицы): 'редкий' / 'rare'.
const SINGULAR: Record<string, [string, string]> = {
  common: ['обычный', 'common'], uncommon: ['необычный', 'uncommon'], rare: ['редкий', 'rare'],
  'very-rare': ['очень редкий', 'very rare'], legendary: ['легендарный', 'legendary'], artifact: ['артефакт', 'artifact'],
};
export const rarityLabel = (raw: string | null | undefined, lang: Lang): string => {
  const slug = raritySlug(raw);
  return slug && SINGULAR[slug] ? SINGULAR[slug][lang === 'ru' ? 0 : 1] : (raw ?? '');
};
// Заголовок хаба редкости (мн. число): «Редкие предметы» / «Rare items».
export const rarityHubLabel = (slug: string, lang: Lang): string => {
  const r = rarityBySlug(slug);
  return r ? r[lang] : slug;
};
export const rarityRank = (raw?: string | null): number => {
  const i = RARITIES.findIndex((r) => r.en === raw);
  return i === -1 ? 99 : i;
};

type WithRarity = Record<string, unknown> | { rarity?: unknown; rarities?: unknown };
/** Редкости предмета по возрастанию: у «+1, +2 или +3» их три, у «редкость варьируется» — ни одной. */
export const itemRarities = (it: WithRarity): string[] => {
  const { rarity, rarities } = it as { rarity?: unknown; rarities?: unknown };
  const all = Array.isArray(rarities) ? (rarities as string[]) : typeof rarity === 'string' && rarity ? [rarity] : [];
  return [...all].sort((a, b) => rarityRank(a) - rarityRank(b));
};
/** Подпись редкости предмета: «редкий», «необычный, редкий или очень редкий», «редкость варьируется». */
export const itemRarityLabel = (it: WithRarity, lang: Lang): string => {
  const labels = itemRarities(it).map((r) => rarityLabel(r, lang));
  if (!labels.length) return lang === 'ru' ? 'редкость варьируется' : 'rarity varies';
  if (labels.length === 1) return labels[0];
  return `${labels.slice(0, -1).join(', ')} ${lang === 'ru' ? 'или' : 'or'} ${labels[labels.length - 1]}`;
};

export const byName = (a: { name: string }, b: { name: string }) => a.name.localeCompare(b.name);
