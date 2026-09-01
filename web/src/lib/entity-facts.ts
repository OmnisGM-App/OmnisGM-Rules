// Шаблонные <meta description> сущностных страниц из СТРУКТУРИРОВАННЫХ данных (issue #185).
//
// Зачем: раньше сущностные страницы брали description как excerpt() первого абзаца/черты.
// У стат-блоков это давало (а) дубли — «Дракон может дышать воздухом и водой.» на 33 страницах,
// (б) сниппет без имени существа и без фактов, которые люди ищут («сколько кд у бурого медведя
// в днд», «днд монстры опасности 1»). Факты из JSON уникальны по определению и совпадают с
// формулировкой спроса.
//
// Формулировки сверены с выгрузкой запросов Вебмастера за 05–11.08.2026:
//   • «днд» кириллицей — 80% показов, обязателен в RU; «5e»/«srd» в RU-спросе ≈ 0;
//   • сущность идёт первой («плут днд», а не «днд: плут»);
//   • «D&D» латиницей оставляем (Google RU + латиничные формы «dnd»/«d&d»);
//   • маркер редакции — человеческий «2024»/«2014», а не машинный «5.2»/«5.1»: спроса на него
//     почти нет, но он разводит одноимённые страницы SRD 5.1 и 5.2 между собой.
//
// Модуль — общий дом для фактовых сниппетов всех типов сущностей: стат-блоки (монстры/животные),
// заклинания, магические предметы. Класс-страницы живут в class-facts.ts и берут отсюда редакцию.
// Локализованные подписи (школа, редкость) НЕ дублируем — берём из *-hubs.ts, где они уже есть.
import { excerpt } from './entities';
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
 * короткий). Варианты передаются от самого информативного к самому урезанному; имя сущности
 * и ключевые факты не режем никогда — ради них сниппет и существует.
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
 *
 * Уникальность: в строке есть имя существа (уникально внутри раздела) и редакция — значит
 * одноимённые страницы 5.1 и 5.2 тоже не дублируются.
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

  // В RU значения приходят с заглавной («Действие», «Мгновенная») — снимаем для середины
  // предложения; в EN это Title Case самого SRD («Action», «Instantaneous»), сохраняем.
  const val = (s: string) => (lang === 'ru' ? lower(s) : s);

  // Время накладывания: у реакций и бонусных действий value содержит ВЕСЬ триггер («Реакция,
  // которую вы совершаете, когда видите существо…» — 200+ символов). В сниппет берём голову
  // до первой запятой: «реакция», «бонусное действие». Запятая в этом поле бывает ТОЛЬКО
  // перед триггером — проверено по всем 4 наборам данных (5.1/5.2 × en/ru).
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

  return fit([
    compose(true, false),
    compose(true, true),
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
 * Фактовый <meta description> снаряжения: цена и вес впереди, дальше — начало описания.
 * Цена и вес это и есть спрос («набор взломщика днд», «сколько стоит…»), а excerpt() первого
 * абзаца начинал сниппет с прозы и часто обрезал самое полезное. null, если ни цены, ни веса
 * нет — вызывающий откатывается к чистому excerpt().
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

  // Хвост — начало описания ровно в остаток бюджета; без него сниппет вышел бы голым перечнем.
  // Но если остатка почти нет, excerpt() вернул бы голое «…» — тогда хвост не добавляем вовсе
  // (ревью #188). MIN_TAIL — минимальная осмысленная длина куска прозы.
  const MIN_TAIL = 20;
  const room = LIMIT - head.length - 1;
  const tail = room >= MIN_TAIL ? excerpt(str(entity.description_md), room) : '';
  return tail ? `${head} ${tail}` : head;
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
 * Фактовый <meta description> магического предмета: тип, редкость, настройка. Настройка —
 * самостоятельный кластер спроса («настройка на магический предмет днд»), поэтому она в
 * сниппете, а условие настройки («…дварфом») — только если влезает. null, если типа и
 * редкости нет — откат к excerpt().
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
    // В RU тип приходит с заглавной («Чудесный предмет») — снимаем для середины предложения;
    // в EN это Title Case стат-блока («Wondrous Item»), его сохраняем. bareType срезает
    // перечисление в скобках («Оружие (боевой топор, большой топор или алебарда)») — последняя
    // ступень укорачивания перед тем, как сниппет вылезет за предел.
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

/**
 * Фактовый <meta description> оружия (issue #214). Раньше строился прямо в шаблоне страницы и
 * состоял из урона, цены и веса — 74–90 символов, то есть заметно короче того, что поисковик
 * готов показать. Добавлены свойства, мастерство и дистанция: это ровно те факты, которыми
 * оружие и отличается друг от друга («какое оружие универсальное», «мастерство оглушение»).
 *
 * Свойства берём БЕЗ скобочных уточнений: «Боеприпас (дистанция 30/120; снаряд)» съело бы пол
 * сниппета, а дистанция и так стоит отдельным фактом.
 *
 * Урон есть не у всего: у Сети его нет вовсе, и прежний шаблон печатал «урон , цена 1 зм» —
 * с висящей запятой и пустым местом. Пустые факты просто не попадают в строку.
 */
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
      // Свойства и мастерство отделяем точкой с запятой: внутри перечня свойств уже есть
      // запятые, и «свойства: боеприпас, мастерство «Замедление»» читалось бы как одно
      // перечисление из трёх свойств.
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
 * Фактовый <meta description> навыка BRP (issue #214). Раньше шёл голый excerpt() описания —
 * одна строка на 46–62 символа («Move quietly and remain unseen while in motion»), без имени
 * навыка, без системы и без базового шанса, а базовый шанс — это и есть то, что ищут.
 * Описание идёт хвостом ровно в остаток бюджета, как у снаряжения.
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

  // Тот же порог, что у снаряжения: обрезок короче 20 символов превратился бы в голое «…».
  const MIN_TAIL = 20;
  const room = LIMIT - head.length - 1;
  const tail = room >= MIN_TAIL ? excerpt(descriptionMd, room) : '';
  return tail ? `${head} ${tail}` : head;
}
