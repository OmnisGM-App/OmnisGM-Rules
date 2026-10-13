// Адрес страницы сущности внутри раздела её ресурса. Вложенный путь есть у снаряжения и магических
// предметов (#412): предмет группы живёт под ней — `equipment/musical-instrument/lute/`,
// `magic-items/potions-of-healing/potion-of-healing/`; обычный предмет и сама группа — `{slug}/`.
// У остальных ресурсов путь — слаг: у монстров тоже есть поле `group`, но это буква алфавитного
// указателя, а не сегмент адреса.

const NESTED = new Set(['equipment', 'magic-items']);

/**
 * @param {string} resource
 * @param {{ slug: string, group?: unknown }} entity
 * @returns {string}
 */
export const entityPath = (resource, entity) =>
  (NESTED.has(resource) && typeof entity.group === 'string' && entity.group ? `${entity.group}/${entity.slug}` : entity.slug);
