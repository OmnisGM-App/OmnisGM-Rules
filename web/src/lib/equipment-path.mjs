// Адрес страницы снаряжения (#412): разновидность составной записи живёт под своей группой —
// `equipment/musical-instrument/lute/`, обычный предмет и сама группа — `equipment/{slug}/`.

/** @param {{ slug: string, group?: string | null }} entity */
export const equipmentPath = (entity) => (entity.group ? `${entity.group}/${entity.slug}` : entity.slug);
