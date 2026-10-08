// Группы вариантов классовых умений (#379): ресурс `class-options` JSON API, группа — умение
// (`feature.key`). Один ключ бывает у нескольких классов (боевой стиль паладина и следопыта).
import { DND_CLASSES } from './nav';
export { classOptionGroupHref } from './rehype-class-option-links.mjs';

export type Lang = 'en' | 'ru';

export interface ClassOption {
  slug: string;
  name: string;
  name_en?: string | null;
  class: string;
  subclass?: string | null;
  feature: { key: string; name: string; level: number };
  granted_by?: { key: string; name: string; level: number } | null;
  selection: 'learned' | 'on_use';
  prerequisites?: { text: string; level: number } | null;
  cost?: { text: string } | null;
  repeatable?: boolean;
  description_md?: string;
}

export interface ClassOptionGroup {
  key: string;
  name: string;
  level: number;
  /** Слаги классов в порядке первого появления. */
  classes: string[];
  /** Подкласс, если у всех вариантов группы он один; иначе подкласс подписан у варианта. */
  subclass: string | null;
  options: ClassOption[];
}

/** Группы в порядке API (порядок глав классов), варианты — в порядке главы. */
export function groupClassOptions(options: ClassOption[]): ClassOptionGroup[] {
  const groups = new Map<string, ClassOptionGroup>();
  for (const option of options) {
    const { key, name, level } = option.feature;
    let group = groups.get(key);
    if (!group) groups.set(key, (group = { key, name, level, classes: [], subclass: option.subclass ?? null, options: [] }));
    if (group.subclass !== (option.subclass ?? null)) group.subclass = null;
    if (!group.classes.includes(option.class)) group.classes.push(option.class);
    group.level = Math.min(group.level, level);
    group.options.push(option);
  }
  return [...groups.values()];
}

/** Имя класса на языке страницы; неизвестный слаг — как есть. */
export function classLabel(slug: string, lang: Lang): string {
  const row = DND_CLASSES.find(([en]) => en.toLowerCase() === slug);
  return row ? (lang === 'ru' ? row[1] : row[2]) : slug;
}

/** Глава класса в SRD 5.2 (адрес собранной страницы, не путь исходника). */
export function classChapterHref(slug: string, lang: Lang): string | null {
  return DND_CLASSES.some(([en]) => en.toLowerCase() === slug) ? `/${lang}/dnd/srd-5.2/classes/${slug}/` : null;
}


/** Имена подклассов по слагу — из ресурса `subclasses`. */
export const subclassNames = (subclasses: Array<{ slug: string; name: string }>): Map<string, string> =>
  new Map(subclasses.map((s) => [s.slug, s.name]));
