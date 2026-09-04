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

// Канонические типы. slug = EN-тип в lowercase. ru — единая подпись (без разнобоя данных).
// beast есть только в 5.1 (в 5.2 звери вынесены в отдельный ресурс animals); swarm — в
// обеих версиях: в 5.2 это рой ползучих когтей, тип которого («Swarm of Tiny Undead»)
// восстановлен по PDF в #196. Набор «активных» типов версии выводится из данных
// (activeTypeSlugs) — пустых хабов и битых ссылок на них не будет.
export const MONSTER_TYPES: { slug: string; en: string; ru: string }[] = [
  { slug: 'aberration', en: 'Aberration', ru: 'Аберрация' },
  { slug: 'beast', en: 'Beast', ru: 'Зверь' },
  { slug: 'celestial', en: 'Celestial', ru: 'Небожитель' },
  { slug: 'construct', en: 'Construct', ru: 'Конструкт' },
  { slug: 'dragon', en: 'Dragon', ru: 'Дракон' },
  { slug: 'elemental', en: 'Elemental', ru: 'Элементаль' },
  { slug: 'fey', en: 'Fey', ru: 'Фея' },
  { slug: 'fiend', en: 'Fiend', ru: 'Исчадие' },
  { slug: 'giant', en: 'Giant', ru: 'Великан' },
  { slug: 'humanoid', en: 'Humanoid', ru: 'Гуманоид' },
  { slug: 'monstrosity', en: 'Monstrosity', ru: 'Чудовище' },
  { slug: 'ooze', en: 'Ooze', ru: 'Слизь' },
  { slug: 'plant', en: 'Plant', ru: 'Растение' },
  { slug: 'swarm', en: 'Swarm', ru: 'Рой' },
  { slug: 'undead', en: 'Undead', ru: 'Нежить' },
];
export const typeBySlug = (slug: string) => MONSTER_TYPES.find((t) => t.slug === slug);
export const typeLabel = (slug: string, lang: Lang) => {
  const t = typeBySlug(slug);
  return t ? t[lang] : slug;
};

// Сырой EN-тип → канонический слаг. Типы из парсера уже чистые и совпадают со слагами;
// исключение — «Swarm of Tiny Beasts» (D&D-категория роя) → 'swarm'.
export const canonTypeSlug = (rawType: string): string => {
  const t = String(rawType || '').toLowerCase().trim();
  if (t.startsWith('swarm')) return 'swarm';
  return t;
};

// Базовый тип роя: «Swarm of Tiny Beasts» → 'beast', «Swarm of Tiny Undead» → 'undead'.
// Нужен для соседей по типу: в 5.2 рой ровно один (ползучие когти), и по слагу 'swarm'
// соседей у него нет вовсе — а по смыслу его семья это нежить. Для хабов такое сведение
// не годится: там все рои — одна группа, и это правильно.
export const swarmBaseTypeSlug = (rawType: string): string | null => {
  const m = /^swarm of \w+ (\w+)$/.exec(String(rawType || '').toLowerCase().trim());
  if (!m) return null;
  const base = m[1].replace(/s$/, '');            // beasts → beast; undead уже без -s
  return MONSTER_TYPES.some((t) => t.slug === base) ? base : null;
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
// Хаб, покрывающий конкретное значение CR (одиночный или диапазон) — для ссылки со страницы монстра.
export const crHubForValue = (v: string) => CR_HUBS.find((h) => h.values.includes(v));
export const crHubTitle = (h: CrHub, lang: Lang) => (lang === 'ru' ? `ПО ${h.label}` : `CR ${h.label}`);

// Карта slug → канонический слаг типа (из EN-данных) — чтобы страница монстра любого языка
// сослалась на верный type-хаб, не завися от непоследовательного RU-поля type.
// Слаг базового типа роя по EN-данным: slug монстра → 'undead'/'beast'. Считается по EN,
// потому что RU-строка типа своя («рой Крошечной нежити»), а решение должно быть общим.
export function swarmBaseMap(ver: string): Map<string, string> {
  const out = new Map<string, string>();
  for (const m of loadEntities(ver, 'en', 'monsters') as any[]) {
    const base = swarmBaseTypeSlug(m.type as string);
    if (base) out.set(m.slug, base);
  }
  return out;
}

export function enTypeMap(ver: string): Map<string, string> {
  return new Map(
    (loadEntities(ver, 'en', 'monsters') as any[]).map((m) => [m.slug, canonTypeSlug(m.type as string)]),
  );
}

// Слаги типов, реально присутствующих в версии (из EN-данных) — для фасетной навигации,
// чтобы не показывать/не линковать пустые хабы (напр. beast в 5.2 отсутствует).
export function activeTypeSlugs(ver: string): Set<string> {
  return new Set((loadEntities(ver, 'en', 'monsters') as any[]).map((m) => canonTypeSlug(m.type as string)));
}
export const activeMonsterTypes = (ver: string) => {
  const active = activeTypeSlugs(ver);
  return MONSTER_TYPES.filter((t) => active.has(t.slug));
};

// Порядок CR для сортировки: «1/8»→0.125, «10»→10.
export const crOrder = (v: string): number => {
  if (v.includes('/')) { const [a, b] = v.split('/').map(Number); return a / b; }
  return Number(v);
};
export const byCrThenName = (a: MonsterLite, b: MonsterLite) =>
  crOrder(a.cr) - crOrder(b.cr) || a.name.localeCompare(b.name);

// Монстры текущего языка с приклеенными фасетами. typeSlug — из EN-данных (чистый источник).
export function monstersWithFacets(ver: string, lang: Lang): MonsterLite[] {
  const enType = enTypeMap(ver);
  return (loadEntities(ver, lang, 'monsters') as any[]).map((m) => ({
    slug: m.slug,
    name: m.name,
    size: m.size ?? '',
    cr: m.cr?.value ?? '0',
    hp: typeof m.hp?.average === 'number' ? m.hp.average : null,
    ac: typeof m.ac?.value === 'number' ? m.ac.value : null,
    typeSlug: enType.get(m.slug) ?? canonTypeSlug(m.type as string),
  }));
}
