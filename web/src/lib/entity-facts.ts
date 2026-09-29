// Шаблонные <meta description> сущностных страниц из СТРУКТУРИРОВАННЫХ данных (issue #185).
// Модуль — общий дом для фактовых сниппетов всех типов сущностей: стат-блоки (монстры/животные),
// заклинания, магические предметы. Класс-страницы живут в class-facts.ts и берут отсюда редакцию.
// Локализованные подписи (школа, редкость) НЕ дублируем — берём из *-hubs.ts, где они уже есть.
import { excerpt } from './entities';
import { listFit } from './page-description.mjs';
import { schoolLabel } from './spell-hubs';
import { rarityLabel } from './magic-item-hubs';

// Редакция D&D по ключу версии. Принимаем оба написания, которые ходят по коду: ключ API
// («srd52», как в VERSION_SLUG) и сегмент URL («srd-5.2», как в catch-all-роуте).
const EDITION: Record<string, string> = {
  srd52: '2024',
  srd51: '2014',
  'srd-5.2': '2024',
  'srd-5.1': '2014',
};

/** Человеческая метка редакции («2024»/«2014») или '' для не-D&D версий. */
export function edition(version: string): string {
  return EDITION[version] ?? '';
}

/** «D&D 2024» / «D&D» — общая для RU и EN часть, чтобы редакция не разъезжалась по шаблонам. */
export function editionLabel(version: string): string {
  const ed = edition(version);
  return ed ? `D&D ${ed}` : 'D&D';
}

// ── Стат-блоки (монстры и животные) ──────────────────────────────────────────

interface StatBlockEntity {
  name: string;
  size?: unknown;
  type?: unknown;
  subtype?: unknown;
  ac?: unknown;
  hp?: unknown;
  cr?: unknown;
}

export type StatBlockKind = 'monster' | 'animal';

const KIND_WORD: Record<StatBlockKind, { ru: string; en: string }> = {
  monster: { ru: 'монстр', en: 'monster' },
  animal: { ru: 'животное', en: 'animal' },
};

const str = (v: unknown) => (typeof v === 'string' ? v.trim() : '');
const num = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? v : null);
// Значение поля данных в середину предложения: «Мгновенная» → «мгновенная». Только первая
// буква — внутри могут быть имена собственные («Пояс дварфов»).
const lower = (s: string) => (s ? s[0].toLowerCase() + s.slice(1) : s);

/**
 * Точка в конце предложения без удвоения: значения веса в данных уже сокращения с точкой
 * («10 фнт.», «10 lb.»), и наивный шаблон давал «вес 10 фнт..».
 */
export const endSentence = (s: string) => (s.endsWith('.') ? s : `${s}.`);

// Предел сниппета: длиннее ~160 символов поисковики обрезают.
const LIMIT = 160;

/**
 * Первый вариант сниппета, влезающий в LIMIT; если не влез ни один — последний (самый
 * короткий). Варианты — от самого информативного к самому урезанному.
 */
function fit(variants: string[]): string {
  return variants.find((v) => v.length <= LIMIT) ?? variants[variants.length - 1];
}

/**
 * «маленькая фея (гоблиноид)» / «Small Fey (Goblinoid)». В RU размер уже переведён в роде
 * своего типа («Маленькая фея», «Большой зверь») — просто снимаем капитализацию, чтобы фраза
 * села в середину предложения. В EN оставляем Title Case как в стат-блоке.
 */
function creatureLine(entity: StatBlockEntity, lang: 'en' | 'ru', withSubtype: boolean): string {
  const size = str(entity.size);
  const type = str(entity.type);
  const subtype = str(entity.subtype);
  let line = [size, type].filter(Boolean).join(' ');
  if (lang === 'ru') line = line.toLowerCase();
  if (withSubtype && subtype) line += ` (${lang === 'ru' ? subtype.toLowerCase() : subtype})`;
  return line;
}

/**
 * Фактовый <meta description> стат-блока. null, если ключевых фактов (КД/хиты/опасность) нет —
 * вызывающий откатывается к прежнему excerpt(), сборку это не валит.
 */
export function statBlockDescription(opts: {
  entity: StatBlockEntity;
  lang: 'en' | 'ru';
  version: string;
  kind: StatBlockKind;
}): string | null {
  const { entity, lang, version, kind } = opts;

  const ac = num((entity.ac as { value?: unknown } | undefined)?.value);
  const hp = num((entity.hp as { average?: unknown } | undefined)?.average);
  const cr = str((entity.cr as { value?: unknown } | undefined)?.value);
  if (ac == null || hp == null || !cr) return null;

  const ed = editionLabel(version);
  const word = KIND_WORD[kind][lang];

  const compose = (withSubtype: boolean, shortTail: boolean) => {
    const creature = creatureLine(entity, lang, withSubtype);
    if (lang === 'ru') {
      const facts = [`КД ${ac}`, `хиты ${hp}`, `опасность ${cr}`, creature].filter(Boolean).join(', ');
      const tail = shortTail
        ? 'Полный стат-блок SRD на русском.'
        : 'Характеристики, атаки и особенности — стат-блок SRD на русском.';
      return `${entity.name} — ${word} ${ed} (днд): ${facts}. ${tail}`;
    }
    const facts = [`AC ${ac}`, `HP ${hp}`, `CR ${cr}`, creature].filter(Boolean).join(', ');
    const tail = shortTail
      ? 'Full SRD stat block.'
      : 'Full stat block with abilities, attacks and traits from the SRD.';
    return `${entity.name} — a ${ed} ${word}: ${facts}. ${tail}`;
  };

  // Переполнение: сначала укорачиваем хвост, потом снимаем подтип.
  return fit([compose(true, false), compose(true, true), compose(false, true)]);
}

// ── Заклинания ───────────────────────────────────────────────────────────────

interface SpellEntity {
  name: string;
  level?: unknown;
  school?: unknown;
  casting_time?: unknown;
  range?: unknown;
  duration?: unknown;
}

/**
 * Фактовый <meta description> заклинания: уровень + школа, время накладывания, дистанция,
 * длительность (с пометкой концентрации). null, если уровня/школы нет — откат к excerpt().
 */
export function spellDescription(opts: {
  entity: SpellEntity;
  lang: 'en' | 'ru';
  version: string;
}): string | null {
  const { entity, lang, version } = opts;

  const lvl = num(entity.level);
  const rawSchool = str(entity.school);
  if (lvl == null || !rawSchool) return null;
  const school = schoolLabel(rawSchool, lang);

  const val = (s: string) => (lang === 'ru' ? lower(s) : s);

  // Время накладывания: у реакций value содержит ВЕСЬ триггер («Реакция, которую вы
  // совершаете, когда…») — в сниппет берём голову до первой запятой.
  const castTime = val(str((entity.casting_time as { value?: unknown } | undefined)?.value).split(',')[0]);
  const range = val(str((entity.range as { value?: unknown } | undefined)?.value));
  const dur = entity.duration as { value?: unknown; concentration?: unknown } | undefined;
  const duration = val(str(dur?.value));
  const concentration = dur?.concentration === true;

  const ed = editionLabel(version);

  const compose = (withDuration: boolean, shortTail: boolean, withRange = true) => {
    if (lang === 'ru') {
      const head = lvl === 0 ? `заговор, школа ${school}` : `${lvl}-й уровень, школа ${school}`;
      const facts = [
        castTime && `Накладывание: ${castTime}`,
        withRange && range && `дистанция ${range}`,
        withDuration && duration && `длительность ${duration}${concentration ? ' (концентрация)' : ''}`,
      ].filter(Boolean).join(', ');
      const tail = shortTail ? 'Полное описание SRD.' : 'Полное описание и правила SRD на русском.';
      return `${entity.name} — заклинание ${ed} (днд): ${head}. ${facts ? `${facts}. ` : ''}${tail}`;
    }
    const head = lvl === 0 ? `${school} cantrip` : `level ${lvl} ${school}`;
    const facts = [
      castTime && `Casting time: ${castTime}`,
      withRange && range && `range ${range}`,
      withDuration && duration && `duration ${duration}${concentration ? ' (concentration)' : ''}`,
    ].filter(Boolean).join(', ');
    const tail = shortTail ? 'Full SRD description.' : 'Full description and rules from the SRD.';
    return `${entity.name} — a ${ed} spell: ${head}. ${facts ? `${facts}. ` : ''}${tail}`;
  };

  // Вариант «без длительности, но с полным хвостом» (#214) стоит выше короткого хвоста:
  // у половины заклинаний длительность длинная («Концентрация, до 1 часа»).
  return fit([
    compose(true, false),
    compose(true, true),
    compose(false, false),
    compose(false, true),
    compose(false, true, false),
  ]);
}

// ── Снаряжение (обычные предметы) ────────────────────────────────────────────

interface GearEntity {
  name: string;
  cost?: unknown;
  weight?: unknown;
  description_md?: unknown;
}

/**
 * Фактовый <meta description> снаряжения: цена и вес впереди — это и есть спрос
 * («сколько стоит…»), дальше начало описания. null, если ни цены, ни веса нет.
 */
export function gearDescription(opts: {
  entity: GearEntity;
  lang: 'en' | 'ru';
  version: string;
}): string | null {
  const { entity, lang, version } = opts;

  const cost = lower(str(entity.cost));
  const weight = lower(str(entity.weight));
  if (!cost && !weight) return null;

  const ed = editionLabel(version);
  const facts =
    lang === 'ru'
      ? [cost && `цена ${cost}`, weight && `вес ${weight}`].filter(Boolean).join(', ')
      : [cost && `cost ${cost}`, weight && `weight ${weight}`].filter(Boolean).join(', ');
  const head = endSentence(
    lang === 'ru'
      ? `${entity.name} — снаряжение ${ed} (днд): ${facts}`
      : `${entity.name} — ${ed} equipment: ${facts}`,
  );

  // Остатка почти нет — excerpt() вернул бы голое «…», тогда хвост не добавляем.
  const MIN_TAIL = 20;
  const room = LIMIT - head.length - 1;
  const tail = room >= MIN_TAIL ? excerpt(str(entity.description_md), room) : '';
  const withProse = tail ? `${head} ${tail}` : head;

  // Однострочное описание («A Basket holds up to 40 pounds») добираем служебным хвостом, но
  // только целиком: обрубленная служебная фраза хуже её отсутствия (#214).
  const SHORT = 110;
  if (withProse.length >= SHORT) return withProse;
  const rules = lang === 'ru' ? 'Полные правила снаряжения SRD на русском.' : 'Full equipment rules from the SRD.';
  return fit([`${withProse} ${rules}`, withProse]);
}

// ── Магические предметы ──────────────────────────────────────────────────────

interface MagicItemEntity {
  name: string;
  type?: unknown;
  subtype?: unknown;
  rarity?: unknown;
  attunement?: unknown;
}

/**
 * Фактовый <meta description> магического предмета: тип, редкость, настройка (самостоятельный
 * кластер спроса); условие настройки — только если влезает. null, если типа и редкости нет.
 */
export function magicItemDescription(opts: {
  entity: MagicItemEntity;
  lang: 'en' | 'ru';
  version: string;
}): string | null {
  const { entity, lang, version } = opts;

  const type = str(entity.type);
  const rawRarity = str(entity.rarity);
  if (!type && !rawRarity) return null;
  const rarity = rawRarity ? rarityLabel(rawRarity, lang) : '';
  const subtype = str(entity.subtype);

  const att = entity.attunement as { required?: unknown; condition?: unknown } | undefined;
  const needsAttunement = att?.required === true;
  const attCondition = str(att?.condition);

  const ed = editionLabel(version);

  const compose = (withCondition: boolean, shortTail: boolean, bareType = false) => {
    // bareType срезает перечисление в скобках («Оружие (боевой топор, …)») — последняя ступень.
    const base = bareType ? type.replace(/\s*\(.*$/, '') : type;
    const rawType = lang === 'ru' ? lower(base) : base;
    const typeLine = type ? rawType + (!bareType && subtype ? ` (${lang === 'ru' ? lower(subtype) : subtype})` : '') : '';
    if (lang === 'ru') {
      const attune = needsAttunement
        ? `требует настройки${withCondition && attCondition ? ` (${attCondition})` : ''}`
        : 'настройка не нужна';
      const facts = [typeLine, rarity, attune].filter(Boolean).join(', ');
      const tail = shortTail ? 'Полное описание SRD.' : 'Полное описание и правила SRD на русском.';
      return `${entity.name} — магический предмет ${ed} (днд): ${facts}. ${tail}`;
    }
    const attune = needsAttunement
      ? `requires attunement${withCondition && attCondition ? ` (${lower(attCondition)})` : ''}`
      : 'no attunement required';
    const facts = [typeLine, rarity, attune].filter(Boolean).join(', ');
    const tail = shortTail ? 'Full SRD description.' : 'Full description and rules from the SRD.';
    return `${entity.name} — a ${ed} magic item: ${facts}. ${tail}`;
  };

  return fit([
    compose(true, false),
    compose(true, true),
    compose(false, true),
    compose(false, true, true),
  ]);
}

// ── Оружие ───────────────────────────────────────────────────────────────────

/** Фактовый <meta description> оружия (issue #214). */
export function weaponDescription(opts: {
  name: string;
  lang: 'en' | 'ru';
  version: string;
  catLabel: string;   // «Простое» / «Simple» — локализовано в шаблоне страницы
  typeLabel: string;  // «ближнего боя» / «Melee»
  damageLine: string; // «1d8 рубящий» / «1d8 Slashing»
  rangeLine: string;  // «30/120 фт» / «30/120 ft»
  properties: string[];
  mastery: string;
  cost: string;
  weight: string;
}): string {
  const { name, lang, version, catLabel, typeLabel, damageLine, rangeLine, mastery, cost, weight } = opts;
  const ed = editionLabel(version);
  // «Универсальное (1d10)» → «универсальное»: скобки повторяют то, что уже сказано фактами.
  const props = opts.properties
    .map((p) => p.replace(/\s*\(.*$/, '').trim())
    .filter(Boolean)
    .map((p) => (lang === 'ru' ? lower(p) : p));

  const compose = (withProps: boolean, withMastery: boolean, withGear: boolean) => {
    const gear = withGear
      ? [cost && (lang === 'ru' ? `цена ${cost}` : `cost ${cost}`),
         weight && (lang === 'ru' ? `вес ${weight}` : `weight ${weight}`)].filter(Boolean).join(', ')
      : '';
    if (lang === 'ru') {
      // Точка с запятой: внутри перечня свойств уже есть запятые.
      const kit = [
        withProps && props.length && `свойства: ${props.join(', ')}`,
        withMastery && mastery && `мастерство «${mastery}»`,
      ].filter(Boolean).join('; ');
      const facts = [
        damageLine && `урон ${damageLine}`,
        rangeLine && `дистанция ${rangeLine}`,
        kit,
        gear,
      ].filter(Boolean).join(', ');
      return endSentence(`${name} — ${catLabel.toLowerCase()} оружие ${typeLabel} ${ed} (днд): ${facts}`);
    }
    const kit = [
      withProps && props.length && `properties: ${props.join(', ')}`,
      withMastery && mastery && `${mastery} mastery`,
    ].filter(Boolean).join('; ');
    const facts = [
      damageLine && `${damageLine} damage`,
      rangeLine && `range ${rangeLine}`,
      kit,
      gear,
    ].filter(Boolean).join(', ');
    return endSentence(`${name} — a ${ed} ${catLabel.toLowerCase()} ${typeLabel.toLowerCase()} weapon: ${facts}`);
  };

  // От самого полного к самому урезанному: первым уходит мастерство (одно слово), затем
  // свойства (самая длинная часть). Цена и вес остаются всегда — это отдельный кластер спроса.
  return fit([
    compose(true, true, true),
    compose(true, false, true),
    compose(false, false, true),
  ]);
}

// ── Навыки BRP ───────────────────────────────────────────────────────────────

/**
 * Фактовый <meta description> навыка BRP (issue #214): базовый шанс — это и есть то, что ищут;
 * описание идёт хвостом в остаток бюджета.
 */
export function brpSkillDescription(opts: {
  name: string;
  lang: 'en' | 'ru';
  baseChance: string;
  category: string;
  descriptionMd: string;
}): string | null {
  const { name, lang, baseChance, category, descriptionMd } = opts;
  if (!baseChance && !category) return null;

  const facts =
    lang === 'ru'
      ? [baseChance && `базовый шанс ${baseChance}`, category && `категория «${category}»`]
      : [baseChance && `base chance ${baseChance}`, category && `${category.toLowerCase()} category`];
  const head = endSentence(
    lang === 'ru'
      ? `${name} — навык Basic Roleplaying: ${facts.filter(Boolean).join(', ')}`
      : `${name} — a Basic Roleplaying skill: ${facts.filter(Boolean).join(', ')}`,
  );

  // Тот же порог, что у снаряжения: слишком короткий обрезок превратился бы в голое «…».
  const MIN_TAIL = 20;
  const room = LIMIT - head.length - 1;
  const tail = room >= MIN_TAIL ? excerpt(descriptionMd, room) : '';
  return tail ? `${head} ${tail}` : head;
}

// ── Хабы и фасеты ────────────────────────────────────────────────────────────

/**
 * Достройка сниппета хаба именами того, что внутри (issue #214). Список режется по границе
 * элемента: обрубленное на середине имя в выдаче выглядит как ошибка.
 */
export function hubDescription(opts: { base: string; names: string[]; lang: 'en' | 'ru' }): string {
  const { base, names, lang } = opts;
  const lead = lang === 'ru' ? 'Среди них: ' : 'Includes: ';
  // Меньше двух имён смысла не имеет: «Среди них: Аболет.» звучит как обрывок, а не как обзор.
  const MIN_NAMES = 2;
  const room = LIMIT - base.length - 1 - lead.length;
  if (room <= 0) return base;
  const list = listFit(names, room);
  if (!list) return base;
  const shown = list.replace(/[.…]$/, '').split(', ').length;
  return shown >= MIN_NAMES ? `${base} ${lead}${list}` : base;
}

// ── Доспехи ──────────────────────────────────────────────────────────────────

/**
 * Фактовый <meta description> доспеха (issue #214): требование Силы и помеха Скрытности — то,
 * из-за чего доспех выбирают или не берут. У лёгких доспехов их нет — добираем хвостом.
 */
export function armorDescription(opts: {
  name: string;
  lang: 'en' | 'ru';
  version: string;
  armorKind: string;  // «средний доспех» / «medium armor» / «щит» — локализовано в шаблоне
  acFact: string;     // «КД 14 + мод. Ловкости (макс. 2)» / «AC 14 + Dex modifier (max 2)»
  gear: string;       // «цена 400 зм, вес 20 фнт.»
  strengthReq: number | null;
  stealthDisadvantage: boolean;
}): string {
  const { name, lang, version, armorKind, acFact, gear, strengthReq, stealthDisadvantage } = opts;
  const ed = editionLabel(version);

  const compose = (withTail: boolean, shortTail: boolean) => {
    if (lang === 'ru') {
      const facts = [
        acFact,
        strengthReq ? `требование Силы ${strengthReq}` : '',
        stealthDisadvantage ? 'помеха Скрытности' : '',
        gear,
      ].filter(Boolean).join(', ');
      const tail = !withTail ? '' : shortTail ? ' Полные правила SRD.' : ' Полные правила доспехов SRD на русском.';
      return endSentence(`${name} — ${armorKind} ${ed} (днд): ${facts}`) + tail;
    }
    const facts = [
      acFact,
      strengthReq ? `Strength ${strengthReq} required` : '',
      stealthDisadvantage ? 'Stealth disadvantage' : '',
      gear,
    ].filter(Boolean).join(', ');
    const tail = !withTail ? '' : shortTail ? ' Full SRD rules.' : ' Full armor rules from the SRD.';
    return endSentence(`${name} — a ${ed} ${armorKind}: ${facts}`) + tail;
  };

  return fit([compose(true, false), compose(true, true), compose(false, false)]);
}

// ── Термины глоссария правил ─────────────────────────────────────────────────

/**
 * Сниппет термина «Глоссария правил» (issue #214): фактов у термина нет, поэтому коротким
 * определениям добавляем контекст — раздел и редакцию (он же различает термины 5.1 и 5.2).
 */
export function glossaryTermDescription(opts: {
  definitionMd: string;
  lang: 'en' | 'ru';
  version: string;
  kindRu: string; // «термин», «состояние», «действие», «область эффекта»
  kindEn: string;
}): string {
  const { definitionMd, lang, version, kindRu, kindEn } = opts;
  const ed = editionLabel(version);
  const kind = lang === 'ru' ? `${kindRu[0].toUpperCase()}${kindRu.slice(1)}` : kindEn;
  const tailLong =
    lang === 'ru'
      ? `${kind} из глоссария правил ${ed} (днд) — определение и правила SRD на русском.`
      : `A ${ed} Rules Glossary ${kindEn} — definition and rules from the SRD.`;
  const tailShort =
    lang === 'ru' ? `${kind} из глоссария правил ${ed} (днд).` : `A ${ed} Rules Glossary ${kindEn}.`;

  // Ниже этой длины сниппет считается коротким (тот же порог, что у гейта по dist).
  const SHORT = 110;
  const full = excerpt(definitionMd, LIMIT);
  if (!full) return tailLong;
  if (full.length >= SHORT) return full;

  // Определение НЕ режем ради хвоста: хвост подбираем под остаток — длинный, короткий или никакого.
  return fit([`${full} ${tailLong}`, `${full} ${tailShort}`, full]);
}
