// Каноническое NAV-дерево ридера (из дизайна rules-docs-data.jsx): игра → версия → разделы,
// двуязычные подписи RU/EN. Пути из дизайна (/dnd/srd-5.2/00_Legal/) маппятся в наши SEO-слаги
// (dnd/srd-5.2/legal) тем же slugifySegment, что и роутинг — поэтому узлы дерева матчатся с контентом.
import { slugifySegment } from './slug';

export type Lang = 'en' | 'ru';

export interface NavPage {
  id: string;
  ru: string;
  en: string;
  slug: string; // путь без языка: "dnd/srd-5.2/legal"
}
export interface NavGroup {
  id: string;
  ru: string;
  en: string;
  kids: NavNode[];
}
export type NavNode = NavPage | NavGroup;
export const isGroup = (n: NavNode): n is NavGroup => 'kids' in n;

// "/dnd/srd-5.2/03_Classes/01_Barbarian/" → "dnd/srd-5.2/classes/barbarian"
function pathToSlug(path: string): string {
  const parts = path.replace(/^\/+|\/+$/g, '').split('/');
  const [game, version, ...rest] = parts;
  return [game, version, ...rest.map(slugifySegment)].join('/');
}

const page = (id: string, ru: string, en: string, path: string): NavPage => ({ id, ru, en, slug: pathToSlug(path) });
const group = (id: string, ru: string, en: string, kids: NavNode[]): NavGroup => ({ id, ru, en, kids });

// Классы D&D — одни и те же 12 имён в 5.2/5.1 (разный индекс папки).
const DND_CLASSES: [string, string, string][] = [
  ['Barbarian', 'Варвар', 'Barbarian'], ['Bard', 'Бард', 'Bard'],
  ['Cleric', 'Жрец', 'Cleric'], ['Druid', 'Друид', 'Druid'],
  ['Fighter', 'Воин', 'Fighter'], ['Monk', 'Монах', 'Monk'],
  ['Paladin', 'Паладин', 'Paladin'], ['Ranger', 'Следопыт', 'Ranger'],
  ['Rogue', 'Плут', 'Rogue'], ['Sorcerer', 'Чародей', 'Sorcerer'],
  ['Warlock', 'Колдун', 'Warlock'], ['Wizard', 'Волшебник', 'Wizard'],
];
const dndClassKids = (verPrefix: string, classesIndex: string, ver: string): NavNode[] =>
  DND_CLASSES.map(([slug, ru, en], i) =>
    page(`${verPrefix}-cls-${slug.toLowerCase()}`, ru, en,
      `/dnd/srd-${ver}/${classesIndex}_Classes/${String(i + 1).padStart(2, '0')}_${slug}/`));

const DH_CLASSES: [string, string, string][] = [
  ['Bard', 'Бард', 'Bard'], ['Druid', 'Друид', 'Druid'], ['Guardian', 'Страж', 'Guardian'],
  ['Ranger', 'Следопыт', 'Ranger'], ['Rogue', 'Плут', 'Rogue'], ['Seraph', 'Серафим', 'Seraph'],
  ['Sorcerer', 'Чародей', 'Sorcerer'], ['Warrior', 'Воитель', 'Warrior'], ['Wizard', 'Волшебник', 'Wizard'],
];

export const NAV: NavNode[] = [
  group('dnd', 'D&D', 'D&D', [
    group('d52', 'SRD 5.2.1', 'SRD 5.2.1', [
      page('d52-legal', 'Правовая информация', 'Legal', '/dnd/srd-5.2/00_Legal/'),
      page('d52-playing', 'Как играть', 'Playing the Game', '/dnd/srd-5.2/01_PlayingTheGame/'),
      page('d52-charcreation', 'Создание персонажа', 'Character Creation', '/dnd/srd-5.2/02_CharacterCreation/'),
      group('d52-classes', 'Классы', 'Classes', dndClassKids('d52', '03', '5.2')),
      page('d52-origins', 'Происхождение персонажа', 'Character Origins', '/dnd/srd-5.2/04_CharacterOrigins/'),
      page('d52-feats', 'Черты', 'Feats', '/dnd/srd-5.2/05_Feats/'),
      page('d52-equipment', 'Снаряжение', 'Equipment', '/dnd/srd-5.2/06_Equipment/'),
      page('d52-spells', 'Заклинания', 'Spells', '/dnd/srd-5.2/07_Spells/'),
      page('d52-rulesglossary', 'Глоссарий правил', 'Rules Glossary', '/dnd/srd-5.2/08_RulesGlossary/'),
      page('d52-toolbox', 'Инструментарий', 'Gameplay Toolbox', '/dnd/srd-5.2/09_GameplayToolbox/'),
      page('d52-magicitems', 'Магические предметы', 'Magic Items', '/dnd/srd-5.2/10_MagicItems/'),
      page('d52-monsters', 'Монстры', 'Monsters', '/dnd/srd-5.2/11_Monsters/'),
      page('d52-monstersaz', 'Монстры от А до Я', 'Monsters A–Z', '/dnd/srd-5.2/12_MonstersA-Z/'),
      page('d52-animals', 'Животные', 'Animals', '/dnd/srd-5.2/13_Animals/'),
      group('d52-glossary', 'Глоссарий', 'Glossary', [
        page('d52-g-terms', 'Термины', 'Terms', '/dnd/srd-5.2/14_Glossary/00_Glossary/'),
        page('d52-g-spells', 'Заклинания (справочник)', 'Spells (reference)', '/dnd/srd-5.2/14_Glossary/02_Spells/'),
        page('d52-g-magicitems', 'Магические предметы (справочник)', 'Magic Items (reference)', '/dnd/srd-5.2/14_Glossary/03_MagicItems/'),
        page('d52-g-monsters', 'Монстры (справочник)', 'Monsters (reference)', '/dnd/srd-5.2/14_Glossary/04_Monsters/'),
        page('d52-g-animals', 'Животные (справочник)', 'Animals (reference)', '/dnd/srd-5.2/14_Glossary/05_Animals/'),
      ]),
    ]),
    group('d51', 'SRD 5.1', 'SRD 5.1', [
      page('d51-legal', 'Правовая информация', 'Legal', '/dnd/srd-5.1/00_Legal/'),
      page('d51-abilities', 'Способности', 'Abilities', '/dnd/srd-5.1/01_Abilities/'),
      page('d51-adventuring', 'Приключения', 'Adventuring', '/dnd/srd-5.1/02_Adventuring/'),
      page('d51-combat', 'Бой', 'Combat', '/dnd/srd-5.1/03_Combat/'),
      page('d51-races', 'Расы', 'Races', '/dnd/srd-5.1/04_Races/'),
      page('d51-details', 'Детали персонажа', 'Character Details', '/dnd/srd-5.1/05_CharacterDetails/'),
      group('d51-classes', 'Классы', 'Classes', dndClassKids('d51', '06', '5.1')),
      page('d51-multiclass', 'Мультиклассирование', 'Multiclassing', '/dnd/srd-5.1/07_Multiclassing/'),
      page('d51-feats', 'Черты', 'Feats', '/dnd/srd-5.1/08_Feats/'),
      page('d51-equipment', 'Снаряжение', 'Equipment', '/dnd/srd-5.1/09_Equipment/'),
      page('d51-spells', 'Заклинания', 'Spells', '/dnd/srd-5.1/10_Spells/'),
      page('d51-conditions', 'Состояния', 'Conditions', '/dnd/srd-5.1/11_Conditions/'),
      page('d51-toolbox', 'Инструментарий мастера', 'Gamemastering Toolbox', '/dnd/srd-5.1/12_GamemasteringToolbox/'),
      page('d51-magicitems', 'Магические предметы', 'Magic Items', '/dnd/srd-5.1/13_MagicItems/'),
      page('d51-monsters', 'Монстры', 'Monsters', '/dnd/srd-5.1/14_Monsters/'),
      page('d51-monstersaz', 'Монстры от А до Я', 'Monsters A–Z', '/dnd/srd-5.1/15_MonstersA-Z/'),
      group('d51-glossary', 'Глоссарий', 'Glossary', [
        page('d51-g-terms', 'Термины', 'Terms', '/dnd/srd-5.1/16_Glossary/00_Glossary/'),
        page('d51-g-spells', 'Заклинания (справочник)', 'Spells (reference)', '/dnd/srd-5.1/16_Glossary/02_Spells/'),
        page('d51-g-magicitems', 'Магические предметы (справочник)', 'Magic Items (reference)', '/dnd/srd-5.1/16_Glossary/03_MagicItems/'),
        page('d51-g-monsters', 'Монстры (справочник)', 'Monsters (reference)', '/dnd/srd-5.1/16_Glossary/04_Monsters/'),
      ]),
    ]),
    page('d52-converting', 'Конвертация в SRD 5.2.1', 'Converting to SRD 5.2.1', '/dnd/converting-srd-5.2/converting-to-srd-5.2.1/'),
  ]),

  group('daggerheart', 'Daggerheart', 'Daggerheart', [
    group('dh', 'SRD 1.0', 'SRD 1.0', [
      page('dh-legal', 'Правовая информация', 'Legal', '/daggerheart/srd-1.0/00_Legal/'),
      page('dh-intro', 'Введение', 'Introduction', '/daggerheart/srd-1.0/01_Introduction/'),
      page('dh-charcreation', 'Создание персонажа', 'Character Creation', '/daggerheart/srd-1.0/02_CharacterCreation/'),
      page('dh-domains', 'Домены', 'Domains', '/daggerheart/srd-1.0/03_Domains/'),
      group('dh-classes', 'Классы', 'Classes', DH_CLASSES.map(([slug, ru, en], i) =>
        page(`dh-cls-${slug.toLowerCase()}`, ru, en, `/daggerheart/srd-1.0/04_Classes/${String(i + 1).padStart(2, '0')}_${slug}/`))),
      page('dh-ancestries', 'Происхождения', 'Ancestries', '/daggerheart/srd-1.0/05_Ancestries/'),
      page('dh-communities', 'Сообщества', 'Communities', '/daggerheart/srd-1.0/06_Communities/'),
      page('dh-core', 'Основные механики', 'Core Mechanics', '/daggerheart/srd-1.0/07_CoreMechanics/'),
      page('dh-weapons', 'Оружие', 'Weapons', '/daggerheart/srd-1.0/08_Weapons/'),
      page('dh-armor', 'Броня', 'Armor', '/daggerheart/srd-1.0/09_Armor/'),
      page('dh-loot', 'Добыча', 'Loot', '/daggerheart/srd-1.0/10_Loot/'),
      page('dh-consumables', 'Расходники', 'Consumables', '/daggerheart/srd-1.0/11_Consumables/'),
      page('dh-gmguide', 'Руководство мастера', 'GM Guide', '/daggerheart/srd-1.0/12_GMGuide/'),
      page('dh-adversaries', 'Противники', 'Adversaries', '/daggerheart/srd-1.0/13_Adversaries/'),
      page('dh-environments', 'Окружения', 'Environments', '/daggerheart/srd-1.0/14_Environments/'),
      page('dh-witherwild', 'Витервилд', 'Witherwild', '/daggerheart/srd-1.0/15_Witherwild/'),
      page('dh-domaincards', 'Справочник доменных карт', 'Domain Card Reference', '/daggerheart/srd-1.0/16_DomainCardReference/'),
      group('dh-glossary', 'Глоссарий', 'Glossary', [
        page('dh-g-terms', 'Термины', 'Terms', '/daggerheart/srd-1.0/17_Glossary/00_Glossary/'),
        page('dh-g-abilities', 'Способности (справочник)', 'Abilities (reference)', '/daggerheart/srd-1.0/17_Glossary/01_Abilities/'),
        page('dh-g-adversaries', 'Противники (справочник)', 'Adversaries (reference)', '/daggerheart/srd-1.0/17_Glossary/02_Adversaries/'),
        page('dh-g-weapons', 'Оружие (справочник)', 'Weapons (reference)', '/daggerheart/srd-1.0/17_Glossary/03_Weapons/'),
        page('dh-g-armor', 'Броня (справочник)', 'Armor (reference)', '/daggerheart/srd-1.0/17_Glossary/04_Armor/'),
        page('dh-g-ancestries', 'Происхождения (справочник)', 'Ancestries (reference)', '/daggerheart/srd-1.0/17_Glossary/05_Ancestries/'),
        page('dh-g-items', 'Предметы (справочник)', 'Items (reference)', '/daggerheart/srd-1.0/17_Glossary/06_Items/'),
        page('dh-g-consumables', 'Расходники (справочник)', 'Consumables (reference)', '/daggerheart/srd-1.0/17_Glossary/07_Consumables/'),
        page('dh-g-communities', 'Сообщества (справочник)', 'Communities (reference)', '/daggerheart/srd-1.0/17_Glossary/08_Communities/'),
      ]),
    ]),
  ]),

  group('brp', 'Basic Roleplaying', 'Basic Roleplaying', [
    group('brp10', 'SRD 1.0', 'SRD 1.0', [
      page('brp-legal', 'Правовая информация', 'Legal', '/brp/srd-1.0/00_Legal/'),
      page('brp-intro', 'Введение', 'Introduction', '/brp/srd-1.0/01_Introduction/'),
      page('brp-charcreation', 'Создание персонажа (BRP)', 'Character Creation', '/brp/srd-1.0/02_CharacterCreation/'),
      page('brp-system', 'Система', 'System', '/brp/srd-1.0/03_System/'),
      page('brp-time', 'Время', 'Time', '/brp/srd-1.0/04_Time/'),
      page('brp-combat', 'Бой', 'Combat', '/brp/srd-1.0/05_Combat/'),
      page('brp-spotrules', 'Точечные правила', 'Spot Rules', '/brp/srd-1.0/06_SpotRules/'),
      page('brp-samplefoe', 'Пример противника', 'Sample Foe', '/brp/srd-1.0/07_SampleFoe/'),
      page('brp-charsheet', 'Лист персонажа', 'Character Sheet', '/brp/srd-1.0/08_CharacterSheet/'),
      group('brp-glossary', 'Глоссарий (BRP)', 'Glossary', [
        page('brp-g-terms', 'Термины', 'Terms', '/brp/srd-1.0/09_Glossary/00_Glossary/'),
        page('brp-g-skills', 'Навыки', 'Skills', '/brp/srd-1.0/09_Glossary/01_Skills/'),
        page('brp-g-weapons', 'Оружие', 'Weapons', '/brp/srd-1.0/09_Glossary/02_Weapons/'),
        page('brp-g-armor', 'Броня', 'Armor', '/brp/srd-1.0/09_Glossary/03_Armor/'),
        page('brp-g-professions', 'Профессии', 'Professions', '/brp/srd-1.0/09_Glossary/04_Professions/'),
      ]),
    ]),
  ]),
];

// Верхние табы (по играм + Home)
export interface SystemTab { id: string; ru: string; en: string; firstId: string }
export const SYSTEMS: SystemTab[] = [
  { id: 'home', ru: 'Главная', en: 'Home', firstId: 'home' },
  { id: 'dnd', ru: 'D&D', en: 'D&D', firstId: 'd52-legal' },
  { id: 'daggerheart', ru: 'Daggerheart', en: 'Daggerheart', firstId: 'dh-legal' },
  { id: 'brp', ru: 'Basic Roleplaying', en: 'Basic Roleplaying', firstId: 'brp-legal' },
];

// ── Helpers ─────────────────────────────────────────────────────────────────
export function flattenPages(nodes: NavNode[] = NAV, acc: NavPage[] = []): NavPage[] {
  for (const n of nodes) {
    if (isGroup(n)) flattenPages(n.kids, acc);
    else acc.push(n);
  }
  return acc;
}
export const FLAT_PAGES: NavPage[] = flattenPages();

export function findPath(id: string, nodes: NavNode[] = NAV, trail: NavNode[] = []): NavNode[] | null {
  for (const n of nodes) {
    if (n.id === id) return [...trail, n];
    if (isGroup(n)) {
      const r = findPath(id, n.kids, [...trail, n]);
      if (r) return r;
    }
  }
  return null;
}
export function systemOf(id: string): string {
  if (id === 'home') return 'home';
  const tp = findPath(id);
  return tp ? tp[0].id : 'home';
}
export const nodeBySlug = (slug: string): NavPage | undefined => FLAT_PAGES.find((p) => p.slug === slug);
export const nodeById = (id: string): NavNode | undefined =>
  FLAT_PAGES.find((p) => p.id === id) ?? (findPath(id) ?? []).slice(-1)[0];

export const label = (n: NavNode, lang: Lang) => (lang === 'en' ? n.en : n.ru);
export const routeOf = (slug: string, lang: Lang) => `/${lang}/${slug}`;

// Маршрут для верхнего таба системы
export function systemRoute(sysId: string, lang: Lang): string {
  if (sysId === 'home') return `/${lang}`;
  const sys = SYSTEMS.find((s) => s.id === sysId);
  const node = sys && nodeById(sys.firstId);
  return node && !isGroup(node) ? routeOf(node.slug, lang) : `/${lang}`;
}
