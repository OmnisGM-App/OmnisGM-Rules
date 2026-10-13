// Подпись подкласса из `spells.subclasses` («Круг Земли (Засушливая земля)») → ссылка на секцию
// подкласса на странице класса (#367). Класс и его имя — из ресурсов `subclasses` и `classes`.

// Якорь секции — слаг заголовка «Подкласс друида: Круг Земли», которого в данных нет.
// Подкласс без строки здесь получает ссылку на страницу класса без якоря.
export const SUBCLASS_ANCHOR = {
  'life-domain':        { ru: 'подкласс-жреца-домен-жизни',            en: 'cleric-subclass-life-domain' },
  'oath-of-devotion':   { ru: 'подкласс-паладина-клятва-преданности',   en: 'paladin-subclass-oath-of-devotion' },
  'fiend-patron':       { ru: 'подкласс-колдуна-покровитель-исчадие',   en: 'warlock-subclass-fiend-patron' },
  'draconic-sorcery':   { ru: 'подкласс-чародея-драконье-чародейство',  en: 'sorcerer-subclass-draconic-sorcery' },
  'circle-of-the-land': { ru: 'подкласс-друида-круг-земли',            en: 'druid-subclass-circle-of-the-land' },
};

/**
 * @param {Array<{ slug: string; name: string; class: string }>} subclasses
 * @param {Array<{ slug: string; name: string }>} classes
 * @param {{ lang: string; classUrl: (slug: string) => string }} options
 * @returns {(label: string) => { className: string; href: string } | null} null — подпись не из ресурса
 */
export function subclassLinker(subclasses, classes, { lang, classUrl }) {
  const classNames = new Map(classes.map((c) => [c.slug, c.name]));
  return (label) => {
    const sub = subclasses.find((x) => label === x.name || label.startsWith(`${x.name} (`));
    if (!sub) return null;
    const anchor = SUBCLASS_ANCHOR[/** @type {keyof typeof SUBCLASS_ANCHOR} */ (sub.slug)]?.[lang === 'ru' ? 'ru' : 'en'];
    return { className: classNames.get(sub.class) ?? '', href: classUrl(sub.class) + (anchor ? `#${anchor}` : '') };
  };
}
