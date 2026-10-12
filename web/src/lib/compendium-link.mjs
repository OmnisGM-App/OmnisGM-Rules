// Адрес сущности в компендиуме листа персонажа: категория и baseId — как у импортёра Table
// (OmnisGM-Table `scripts/compendium/map.mts`); у `rule` baseId с префиксом вида (#164).

const APP = 'https://omnisgm.com';

/** @type {Record<string, string>} */
const SYSTEM = { srd52: 'dnd2024' };

/** @type {Record<string, { category: string, prefix?: string }>} */
const BY_RESOURCE = {
  spells: { category: 'spell' },
  weapons: { category: 'weapon' },
  armor: { category: 'armor' },
  equipment: { category: 'item' },
  'magic-items': { category: 'magic-item' },
  feats: { category: 'feat' },
  species: { category: 'species' },
  backgrounds: { category: 'background' },
  actions: { category: 'action' },
  conditions: { category: 'rule', prefix: 'condition' },
  'rules-terms': { category: 'rule', prefix: 'term' },
  'areas-of-effect': { category: 'rule', prefix: 'area-of-effect' },
};

// Термины глоссария во вкладке «Стандартные действия» Table (Table#410).
const TERM_ACTIONS = new Set(['unarmed-strike', 'opportunity-attacks']);

/** null — у Table нет такой записи. @param {string} ver @param {string} resource @param {string} slug @returns {string | null} */
export function compendiumHref(ver, resource, slug) {
  const system = SYSTEM[ver];
  const target = resource === 'rules-terms' && TERM_ACTIONS.has(slug) ? { category: 'action', prefix: undefined } : BY_RESOURCE[resource];
  if (!system || !target) return null;
  const baseId = target.prefix ? `${target.prefix}-${slug}` : slug;
  return `${APP}/compendium/${system}/${target.category}/${baseId}`;
}
