// SEO-классификация глоссарных страниц (issue #106, этап 1).
// Список — явный allow-list (а не «всё кроме дублей»): так безопаснее — новые/прочие
// `/glossary/` по умолчанию остаются вне индекса, пока их сюда явно не добавят.
export const INDEXABLE_GLOSSARY = [
  '/daggerheart/srd-1.0/glossary/weapons/',
  '/daggerheart/srd-1.0/glossary/armor/',
  '/daggerheart/srd-1.0/glossary/items/',
  '/daggerheart/srd-1.0/glossary/consumables/',
  '/brp/srd-1.0/glossary/weapons/',
  '/brp/srd-1.0/glossary/armor/',
];

export const isIndexableGlossary = (/** @type {string} */ urlOrPath) =>
  INDEXABLE_GLOSSARY.some((s) => urlOrPath.includes(s));
