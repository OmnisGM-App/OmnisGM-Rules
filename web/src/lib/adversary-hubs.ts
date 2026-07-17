// Хабы противников Daggerheart (issue #20): фасет по ТИПУ (Solo/Bruiser/Minion/…).
// Роут: adversaries/type/[type]. Тип в данных — локализованное слово (EN «Solo» / RU
// «Одиночка»); URL-слаг языконезависим ('solo') → каноникал + hreflang. Ранг (tier) —
// отдельный фасет (adversaries/tier/[tier]), уже существует.
export type Lang = 'en' | 'ru';

export interface AdversaryLite {
  slug: string;
  name: string;
  name_en?: string | null;
  tier: number;
  type?: string | null; // локализованное слово типа
}

// 10 типов противников DH. slug = EN в lowercase. en/ru — подписи из SRD (по обеим сверено 129/129).
export const ADVERSARY_TYPES: { slug: string; en: string; ru: string }[] = [
  { slug: 'bruiser', en: 'Bruiser', ru: 'Громила' },
  { slug: 'horde', en: 'Horde', ru: 'Орда' },
  { slug: 'leader', en: 'Leader', ru: 'Лидер' },
  { slug: 'minion', en: 'Minion', ru: 'Приспешник' },
  { slug: 'ranged', en: 'Ranged', ru: 'Стрелок' },
  { slug: 'skulk', en: 'Skulk', ru: 'Скрытник' },
  { slug: 'social', en: 'Social', ru: 'Дипломат' },
  { slug: 'solo', en: 'Solo', ru: 'Одиночка' },
  { slug: 'standard', en: 'Standard', ru: 'Обычный' },
  { slug: 'support', en: 'Support', ru: 'Поддержка' },
];

export const advTypeBySlug = (slug: string) => ADVERSARY_TYPES.find((t) => t.slug === slug);
// Локализованное слово типа ('Solo'/'Одиночка') → слаг ('solo'); undefined, если не распознано.
export const advTypeSlug = (raw?: string | null): string | undefined =>
  ADVERSARY_TYPES.find((t) => t.en === raw || t.ru === raw)?.slug;
export const advTypeLabel = (slug: string, lang: Lang): string => {
  const t = advTypeBySlug(slug);
  return t ? t[lang] : slug;
};

export const byName = (a: { name: string }, b: { name: string }) => a.name.localeCompare(b.name);
