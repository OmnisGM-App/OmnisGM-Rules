// Адрес страницы сущности внутри раздела её ресурса. Вложенный путь есть только у снаряжения (#412):
// предмет группы живёт под ней — `equipment/musical-instrument/lute/`, обычный предмет и сама
// группа — `equipment/{slug}/`. У остальных ресурсов путь — слаг: у монстров тоже есть поле `group`,
// но это буква алфавитного указателя, а не сегмент адреса.

/**
 * @param {string} resource
 * @param {{ slug: string, group?: unknown }} entity
 * @returns {string}
 */
export const entityPath = (resource, entity) =>
  (resource === 'equipment' && typeof entity.group === 'string' && entity.group ? `${entity.group}/${entity.slug}` : entity.slug);
