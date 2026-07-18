// SEO-классификация глоссарных страниц (issue #106, этап 1).
//
// Чистка #37 накрыла ВСЕ `/glossary/` одинаково (noindex + вне sitemap). Но контент разный:
//  • Дубли хабов (DH: способности/противники/происхождения/сообщества; BRP: навыки/профессии)
//    — у них есть функциональные entity-хабы. Со старых URL — 301 на хаб (см. firebase.json),
//    в индекс/sitemap НЕ возвращаем.
//  • Оглавления-термины (00_Glossary) — тонкие списки; оставляем noindex (наполнение
//    per-term programmatic-страницами — отдельный этап #106).
//  • Содержательные справочники БЕЗ хаба (DH: оружие/броня/предметы/расходники; BRP:
//    оружие/броня) — это аналог D&D rules-glossary. Их ВОЗВРАЩАЕМ в индекс и sitemap.
//
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

// Глоссарная страница, которую возвращаем в индекс (принимает pathname или полный URL —
// матч по подстроке, язык-агностично: /ru/… и /en/… оба ловятся).
export const isIndexableGlossary = (urlOrPath) =>
  INDEXABLE_GLOSSARY.some((s) => urlOrPath.includes(s));
