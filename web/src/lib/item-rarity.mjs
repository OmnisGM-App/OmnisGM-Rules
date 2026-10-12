// Редкости магического предмета и их подпись: у предмета их бывает несколько («+1, +2 или +3»)
// или ни одной («редкость варьируется»).

/** EN-ключ API → [RU, EN] в единственном числе; порядок ключей — возрастание редкости. */
const SINGULAR = {
  common: ['обычный', 'common'],
  uncommon: ['необычный', 'uncommon'],
  rare: ['редкий', 'rare'],
  'very rare': ['очень редкий', 'very rare'],
  legendary: ['легендарный', 'legendary'],
  artifact: ['артефакт', 'artifact'],
};
const ORDER = Object.keys(SINGULAR);
const rank = (/** @type {string} */ r) => (ORDER.includes(r) ? ORDER.indexOf(r) : ORDER.length);

/**
 * Редкости предмета по возрастанию; без `rarities` — одиночная `rarity`.
 * @param {object} item @returns {string[]}
 */
export function itemRarities(item) {
  const { rarity, rarities } = /** @type {{ rarity?: unknown, rarities?: unknown }} */ (item);
  const all = Array.isArray(rarities) ? rarities.map(String) : typeof rarity === 'string' && rarity ? [rarity] : [];
  return [...all].sort((a, b) => rank(a) - rank(b));
}

/**
 * «редкий», «необычный, редкий или очень редкий», «редкость варьируется».
 * @param {object} item @param {'en' | 'ru'} lang @returns {string}
 */
export function itemRarityLabel(item, lang) {
  const col = lang === 'ru' ? 0 : 1;
  const labels = itemRarities(item).map((r) => /** @type {Record<string, string[]>} */ (SINGULAR)[r]?.[col] ?? r);
  if (!labels.length) return lang === 'ru' ? 'редкость варьируется' : 'rarity varies';
  if (labels.length === 1) return labels[0];
  return `${labels.slice(0, -1).join(', ')} ${lang === 'ru' ? 'или' : 'or'} ${labels[labels.length - 1]}`;
}
