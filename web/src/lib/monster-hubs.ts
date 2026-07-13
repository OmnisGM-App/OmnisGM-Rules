// Хабы монстров (issue #20, SEO §2.3, PR B): фасетные списки по типу и по CR.
// Роуты: monsters-a-z/type/[type] и monsters-a-z/cr/[cr] (детали монстров — под monsters-a-z/).
//
// ВАЖНО: RU-поле `type` переведено НЕПОСЛЕДОВАТЕЛЬНО (construct → «конструкт»/«конструкция»,
// fey → «фей»/«фея», monstrosity → «чудовище»/«чудовищность») — фильтровать по нему нельзя.
// Группируем по СЛАГУ через чистый EN-тип (слаг языконезависим); `cr.value` чист в обоих языках.
import { loadEntities } from './entities';

export type Lang = 'en' | 'ru';

export interface MonsterLite {
  slug: string;
  name: string;
  size: string;
  cr: string;         // «0», «1/2», «5», «30»
  hp: number | null;  // среднее
  ac: number | null;
  typeSlug: string;   // канонический слаг типа (из EN-данных)
}

// Канонические типы (13). slug = EN-тип в lowercase. ru — единая подпись (без разнобоя данных).
export const MONSTER_TYPES: { slug: string; en: string; ru: string }[] = [
  { slug: 'aberration', en: 'Aberration', ru: 'Аберрация' },
  { slug: 'celestial', en: 'Celestial', ru: 'Небожитель' },
  { slug: 'construct', en: 'Construct', ru: 'Конструкт' },
  { slug: 'dragon', en: 'Dragon', ru: 'Дракон' },
  { slug: 'elemental', en: 'Elemental', ru: 'Элементаль' },
  { slug: 'fey', en: 'Fey', ru: 'Фей' },
  { slug: 'fiend', en: 'Fiend', ru: 'Исчадие' },
  { slug: 'giant', en: 'Giant', ru: 'Великан' },
  { slug: 'humanoid', en: 'Humanoid', ru: 'Гуманоид' },
  { slug: 'monstrosity', en: 'Monstrosity', ru: 'Чудовище' },
  { slug: 'ooze', en: 'Ooze', ru: 'Слизь' },
  { slug: 'plant', en: 'Plant', ru: 'Растение' },
  { slug: 'undead', en: 'Undead', ru: 'Нежить' },
];
export const typeBySlug = (slug: string) => MONSTER_TYPES.find((t) => t.slug === slug);
export const typeLabel = (slug: string, lang: Lang) => {
  const t = typeBySlug(slug);
  return t ? t[lang] : slug;
};

// CR-хабы: одиночные для частых 0–10 (все ≥5 монстров), редкий тяжёлый хвост — в диапазоны.
const CR_SINGLES = ['0', '1/8', '1/4', '1/2', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'];
const RANGE = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => String(a + i));
export const crSlug = (v: string) => v.replace('/', '-'); // «1/2» → «1-2»
export interface CrHub { slug: string; label: string; values: string[] }
export const CR_HUBS: CrHub[] = [
  ...CR_SINGLES.map((v) => ({ slug: crSlug(v), label: v, values: [v] })),
  { slug: '11-16', label: '11–16', values: RANGE(11, 16) },
  { slug: '17-30', label: '17–30', values: RANGE(17, 30) },
];
export const crHubBySlug = (slug: string) => CR_HUBS.find((h) => h.slug === slug);
export const crHubTitle = (h: CrHub, lang: Lang) => (lang === 'ru' ? `ПО ${h.label}` : `CR ${h.label}`);

// Порядок CR для сортировки: «1/8»→0.125, «10»→10.
export const crOrder = (v: string): number => {
  if (v.includes('/')) { const [a, b] = v.split('/').map(Number); return a / b; }
  return Number(v);
};
export const byCrThenName = (a: MonsterLite, b: MonsterLite) =>
  crOrder(a.cr) - crOrder(b.cr) || a.name.localeCompare(b.name);

// Монстры текущего языка с приклеенными фасетами. typeSlug — из EN-данных (чистый источник).
export function monstersWithFacets(ver: string, lang: Lang): MonsterLite[] {
  const enType = new Map(
    (loadEntities(ver, 'en', 'monsters') as any[]).map((m) => [m.slug, String(m.type || '').toLowerCase()]),
  );
  return (loadEntities(ver, lang, 'monsters') as any[]).map((m) => ({
    slug: m.slug,
    name: m.name,
    size: m.size ?? '',
    cr: m.cr?.value ?? '0',
    hp: typeof m.hp?.average === 'number' ? m.hp.average : null,
    ac: typeof m.ac?.value === 'number' ? m.ac.value : null,
    typeSlug: enType.get(m.slug) ?? 'monstrosity',
  }));
}
