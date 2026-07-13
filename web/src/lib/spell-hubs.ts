// Хабы заклинаний (issue #20, SEO §2.3): фасетные списки по классу и по уровню.
// Общие данные/подписи для двух роутов: spells/class/[class] и spells/level/[level].
//
// ВАЖНО: в JSON-данных поле `classes` ПЕРЕВЕДЕНО (RU: «Волшебник», EN: «Wizard»), а URL-слаг
// фасета обязан быть языконезависимым (общий каноникал + hreflang, как у слагов сущностей).
// Поэтому фильтруем по имени класса НА ЯЗЫКЕ ДАННЫХ, а слаг берём из этой таблицы.
export type Lang = 'en' | 'ru';

export interface SpellLite {
  slug: string;
  name: string;
  level: number;
  school: string;
  classes: string[];
}

// ruGen — родительный падеж («заклинания <кого?>»); наивное «+а» ломается на Чародей/Жрец.
export const SPELL_CLASSES: { slug: string; en: string; ru: string; ruGen: string }[] = [
  { slug: 'bard', en: 'Bard', ru: 'Бард', ruGen: 'барда' },
  { slug: 'cleric', en: 'Cleric', ru: 'Жрец', ruGen: 'жреца' },
  { slug: 'druid', en: 'Druid', ru: 'Друид', ruGen: 'друида' },
  { slug: 'paladin', en: 'Paladin', ru: 'Паладин', ruGen: 'паладина' },
  { slug: 'ranger', en: 'Ranger', ru: 'Следопыт', ruGen: 'следопыта' },
  { slug: 'sorcerer', en: 'Sorcerer', ru: 'Чародей', ruGen: 'чародея' },
  { slug: 'warlock', en: 'Warlock', ru: 'Колдун', ruGen: 'колдуна' },
  { slug: 'wizard', en: 'Wizard', ru: 'Волшебник', ruGen: 'волшебника' },
];

export const LEVELS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];

export const classBySlug = (slug: string) => SPELL_CLASSES.find((c) => c.slug === slug);
export const classLabel = (slug: string, lang: Lang) => {
  const c = classBySlug(slug);
  return c ? c[lang] : slug;
};
// «Заклинания <классаGen>» (RU род.п.) / «<Class>» (EN, атрибутив в «X Spells»).
export const classHubName = (slug: string, lang: Lang) => {
  const c = classBySlug(slug);
  if (!c) return slug;
  return lang === 'ru' ? c.ruGen : c.en;
};
// Имя класса в том виде, в каком оно лежит в данных этого языка (для фильтра spell.classes).
export const classNameInData = (slug: string, lang: Lang) => classLabel(slug, lang);

export const levelLabel = (n: number, lang: Lang) =>
  n === 0 ? (lang === 'ru' ? 'Заговоры' : 'Cantrips') : lang === 'ru' ? `${n}-й уровень` : `Level ${n}`;
// Короткая подпись уровня заклинания в таблице/строке.
export const levelShort = (n: number, lang: Lang) =>
  n === 0 ? (lang === 'ru' ? 'Заговор' : 'Cantrip') : lang === 'ru' ? `${n} ур.` : `Lv ${n}`;

// Школа: в RU JSON поле переведено наполовину (Evocation vs Воплощения) — нормализуем
// двусторонним мапом (тот же, что на странице заклинания).
const SCHOOLS: [string, string][] = [
  ['Abjuration', 'Ограждения'], ['Conjuration', 'Вызова'], ['Divination', 'Прорицания'],
  ['Enchantment', 'Очарования'], ['Evocation', 'Воплощения'], ['Illusion', 'Иллюзии'],
  ['Necromancy', 'Некромантии'], ['Transmutation', 'Преобразования'],
];
export const schoolLabel = (raw: string, lang: Lang) => {
  const p = SCHOOLS.find(([en, ru]) => en === raw || ru === raw);
  return p ? (lang === 'ru' ? p[1] : p[0]) : raw;
};

// Классы заклинания (слаги) — из переведённого поля classes через обратный поиск по языку данных.
export const spellClassSlugs = (spell: SpellLite, lang: Lang): string[] =>
  (spell.classes || [])
    .map((name) => SPELL_CLASSES.find((c) => c[lang] === name)?.slug)
    .filter((s): s is string => Boolean(s));

export const byName = (a: { name: string }, b: { name: string }) => a.name.localeCompare(b.name);
