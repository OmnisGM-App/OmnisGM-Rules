// Автоссылки на программные страницы сущностей (issue #20): имена сущностей в контенте
// становятся ссылками на их страницы. Ручной обход hast-дерева — без доп. зависимостей.
import fs from 'node:fs';
import path from 'node:path';

// process.cwd() (= web/ на билде) — резолвится одинаково в конфиг-контексте (главы) и под Vite
// (страницы сущностей). import.meta.url под Vite указывает не туда.
const DATA_ROOT = path.resolve(process.cwd(), 'src/data/api');

// Ресурсы с программными страницами. mode: 'text' | 'exact' | 'feats' | 'cells' | 'grid'.
// container (для exact) — тег-обёртка сигнала SRD: 'em' (курсив, заклинания) / 'strong' (жирный,
// монстры). versions — где реально есть страницы. chapters (для grid) — regex главы-источника.
const DND_RESOURCES = [
  { key: 'conditions', urlParent: 'rules-glossary/conditions', mode: 'text' },
  { key: 'spells', urlParent: 'spells', mode: 'exact', container: 'em', versions: ['srd-5.2', 'srd-5.1'] },
  { key: 'monsters', urlParent: 'monsters-a-z', mode: 'exact', container: 'strong', versions: ['srd-5.2', 'srd-5.1'] },
  // Животные — тот же жирный сигнал SRD, что и монстры; только 5.2: в 5.1 звери входят в monsters.
  { key: 'animals', urlParent: 'animals', mode: 'exact', container: 'strong', versions: ['srd-5.2'] },
  // Предметы — тоже курсив (SRD размечает ссылки на предметы как «*Название*», как заклинания).
  { key: 'magic-items', urlParent: 'magic-items', mode: 'exact', container: 'em', versions: ['srd-5.2', 'srd-5.1'] },
  // Черты не размечены и омонимичны словам (Defense/Archery) → режим 'feats': точные ячейки
  // таблиц классов, а в прозе — только много-словные имена.
  { key: 'feats', urlParent: 'feats', mode: 'feats', versions: ['srd-5.2', 'srd-5.1'] },
  // Оружие/доспехи/снаряжение не размечены и омонимичны словам («Молот», «Щит») → только ячейки таблиц.
  { key: 'weapons', urlParent: 'weapons', mode: 'cells', versions: ['srd-5.2', 'srd-5.1'] },
  { key: 'armor', urlParent: 'armor', mode: 'cells', versions: ['srd-5.2', 'srd-5.1'] },
  { key: 'equipment', urlParent: 'equipment', mode: 'cells', versions: ['srd-5.2', 'srd-5.1'] },
];

// Daggerheart: имена в прозе не размечены — линкуем только ячейки сетки доменных карт.
const DH_RESOURCES = [
  { key: 'domain-cards', urlParent: 'domain-cards', mode: 'grid', versions: ['srd-1.0'], chapters: /\/03_Domains/ },
];

// BRP: то же — линкуем только таблицу навыков в глоссарии.
const BRP_RESOURCES = [
  { key: 'skills', urlParent: 'skills', mode: 'grid', versions: ['srd-1.0'], chapters: /\/09_Glossary\/01_Skills/ },
];

const RESOURCES_BY_GAME = { dnd: DND_RESOURCES, daggerheart: DH_RESOURCES, brp: BRP_RESOURCES };

// Заголовок первой колонки таблицы спелл-листа класса (по языку) — сигнал линковать её ячейки.
const SPELL_TABLE_HEAD = new Set(['Заклинание', 'Spell']);

// Доп. имена-синонимы (краткие формы состояний): `${game}/${lang}` → { [slug]: [alias, …] }.
const ALIASES = {
  'dnd/ru': {
    blinded: ['Ослеплён'], charmed: ['Очарован'], frightened: ['Испуган'], grappled: ['Схвачен'],
    incapacitated: ['Недееспособен'], invisible: ['Невидим'], paralyzed: ['Парализован'],
    poisoned: ['Отравлен'], restrained: ['Опутан'], stunned: ['Ошеломлён'],
  },
};

// Имя сущности в тексте склоняется (RU-падежи) / стоит во мн. числе (EN), а exact-матч — по
// именительному. Здесь — реальные жирные формы монстров из данных, чтобы они тоже линковались.
const EXACT_ALIASES = {
  'dnd/ru': {
    monsters: {
      ghoul: ['Упырём', 'Упырями'], griffon: ['Грифоном'], nightmare: ['Кошмаром'],
      berserker: ['Берсерка'], djinni: ['Джинна'], wight: ['Умертвиями'],
      mummy: ['Мумиями', 'Мумией'], knight: ['Рыцаря'], skeleton: ['Скелетов'],
      ghast: ['Гастами'], 'shrieker-fungus': ['Визгуна'],
      'air-elemental': ['Воздушного элементаля'], 'earth-elemental': ['Земляного элементаля'],
      'fire-elemental': ['Огненного элементаля'], 'water-elemental': ['Водного элементаля'],
      'awakened-shrub': ['Пробуждённого куста'], 'awakened-tree': ['Пробуждённого дерева'],
    },
    // Животные: жирные упоминания в RU-корпусе склоняются (Фигурка чудесной силы, спелл-листы).
    animals: {
      elephant: ['Слоном'], mastiff: ['Мастифом'], raven: ['Вороном'],
      lion: ['Львом'], // «Золотые львы» Фигурки: «может стать Львом» (тв.п., нерег. склонение Лев→Львом)
      bat: ['Летучую мышь'], 'riding-horse': ['Верховой лошади'],
      'giant-constrictor-snake': ['Гигантского удава'], 'giant-owl': ['Гигантской совой'],
      'giant-goat': ['Гигантским козлом'], 'giant-rat': ['Гигантских крыс'],
      'giant-wasp': ['Гигантские осы'],
    },
    'magic-items': {
      'bag-of-holding': ['Сумкой вместимости', 'Сумку вместимости'], 'bead-of-force': ['Бусины силы'],
      'belt-of-giant-strength': ['Поясом силы великана'], 'gauntlets-of-ogre-power': ['Перчатками силы огра'],
      'portable-hole': ['Переносной дырой', 'Переносной дыры'],
      'dragon-orb': ['Сфера драконов'], 'gloves-of-missile-snaring': ['Перчатку похищения снарядов'],
      'handy-haversack': ['Практичным рюкзаком'],
      'horn-of-valhalla': ['Рога Валгаллы'], 'oil-of-etherealness': ['Масла эфирности'],
      'oil-of-slipperiness': ['Маслом скольжения'],
      'potions-of-healing': ['Зелье лечения'], 'ring-of-djinni-summoning': ['Кольца призыва джинна'],
      'spell-scroll': ['Свитке заклинания', 'Свитки заклинаний', 'Свитков заклинаний'],
      'sphere-of-annihilation': ['Сферу уничтожения', 'Сферы уничтожения'],
      'sun-blade': ['Солнечным клинком'], 'universal-solvent': ['Универсального растворителя'],
    },
  },
  'dnd/en': {
    monsters: {
      ghoul: ['Ghouls'], ghast: ['Ghasts'], wight: ['Wights'], mummy: ['Mummies'],
      'shrieker-fungus': ['Shrieker Fungi'],
    },
    // Животные: множественные жирные формы EN (тулбокс/спелл-листы) → на статблок.
    animals: {
      'giant-wasp': ['Giant Wasps'], 'giant-rat': ['Giant Rats'],
    },
    'magic-items': {
      'bead-of-force': ['Beads of Force'], 'gloves-of-missile-snaring': ['Glove of Missile Snaring'],
      'ring-of-djinni-summoning': ['Rings of Djinni Summoning'],
    },
  },
};

const SKIP_TAGS = new Set(['a', 'code', 'pre', 'kbd', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']);

const escapeRegExp = (/** @type {string} */ s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const verKeyOf = (/** @type {string} */ version) => version.replace(/[.\-]/g, ''); // srd-5.2 → srd52

// Кэш: `${game}/${version}/${lang}` → { text: {regexSource, byName} | null, exact: Map, verKey } | null
/** @type {Map<string, any>} */
const mapCache = new Map();

function loadMap(/** @type {string} */ game, /** @type {string} */ version, /** @type {string} */ lang) {
  const cacheKey = `${game}/${version}/${lang}`;
  if (mapCache.has(cacheKey)) return mapCache.get(cacheKey);
  const verKey = verKeyOf(version);
  const byGameLang = /** @type {(set: object) => Record<string, any>} */
    ((set) => /** @type {Record<string, any>} */ (set)[`${game}/${lang}`] || {});
  const aliases = byGameLang(ALIASES);
  const exactAliases = byGameLang(EXACT_ALIASES);
  /** @type {any[]} */
  const textEntries = [];
  // exact-карты по контейнеру: em (заклинания) и strong (монстры) — держим раздельно, чтобы
  // имя монстра в курсиве / имя заклинания в жирном не матчились не в своём контексте.
  const exact = { em: new Map(), strong: new Map() };
  const feats = new Map();
  const cells = new Map();
  const grid = new Map();
  // Имена magic-items/monsters — зарезервированы: их не линкуем как cells (редкие кросс-ресурс
  // коллизии: «Свиток заклинания» = equipment+magic-item, «Страж-щит» = magic-item+monster).
  // magic-items/monsters идут в RESOURCES раньше оружия → к моменту cells набор полон.
  const reserved = new Set();
  for (const { key, urlParent, mode, container, versions, chapters } of
    (/** @type {Record<string, any[]>} */ (RESOURCES_BY_GAME)[game] || [])) {
    if (versions && !versions.includes(version)) continue;
    const file = path.join(DATA_ROOT, game, verKey, lang, key, 'all.json');
    let data;
    try {
      data = JSON.parse(fs.readFileSync(file, 'utf8'));
    } catch {
      continue; // ресурса нет для игры/версии/языка
    }
    for (const e of data) {
      if (!e || !e.name || !e.slug) continue;
      const entry = { name: e.name, slug: e.slug, resource: key, urlParent };
      if (mode === 'exact') {
        // Ключ в lowercase: SRD размечает ссылки и строчными («*лечение ран*»), и с заглавной.
        const m = /** @type {Record<string, Map<string, any>>} */ (exact)[container];
        const k = e.name.toLowerCase();
        if (m && !m.has(k)) m.set(k, entry);
        // Склонённые/мн.-числа формы того же имени → на ту же сущность.
        for (const form of exactAliases[key]?.[e.slug] || []) {
          const fk = form.toLowerCase();
          if (m && !m.has(fk)) m.set(fk, entry);
        }
      } else if (mode === 'feats') {
        const k = e.name.toLowerCase();
        if (!feats.has(k)) feats.set(k, entry);
        // Проза — только много-словные (дистинктивные) имена; одно-словные омонимичны.
        if (e.name.trim().split(/\s+/).length >= 2) textEntries.push(entry);
      } else if (mode === 'cells') {
        const k = e.name.toLowerCase();
        if (!reserved.has(k) && !cells.has(k)) cells.set(k, entry);
      } else if (mode === 'grid') {
        const k = e.name.toLowerCase();
        if (!grid.has(k)) grid.set(k, { ...entry, chapters });
      } else {
        textEntries.push(entry);
        for (const alias of aliases[e.slug] || []) textEntries.push({ ...entry, name: alias });
      }
      if (key === 'magic-items' || key === 'monsters') reserved.add(e.name.toLowerCase());
    }
  }
  let text = null;
  if (textEntries.length) {
    // Длинные имена раньше коротких: в альтернации побеждает первый матч, а не самый длинный.
    textEntries.sort((a, b) => b.name.length - a.name.length);
    const byName = new Map(textEntries.map((e) => [e.name, e]));
    const alt = textEntries.map((e) => escapeRegExp(e.name)).join('|');
    text = { regexSource: `(?<![\\p{L}\\p{N}_])(${alt})(?![\\p{L}\\p{N}_])`, byName };
  }
  const result = text || exact.em.size || exact.strong.size || feats.size || cells.size || grid.size
    ? { text, exact, feats, cells, grid, verKey } : null;
  mapCache.set(cacheKey, result);
  return result;
}

/**
 * @param {string} value
 * @param {{regexSource: string, byName: Map<string, any>}} textMap
 * @param {Set<string>} skip
 * @param {any} ctx
 */
function linkifyText(value, textMap, skip, ctx) {
  const re = new RegExp(textMap.regexSource, 'gu');
  /** @type {any[]} */
  const nodes = [];
  let last = 0;
  let changed = false;
  let match;
  while ((match = re.exec(value))) {
    const name = match[1];
    const entry = textMap.byName.get(name);
    if (!entry || skip.has(entry.slug)) continue;
    changed = true;
    if (match.index > last) nodes.push({ type: 'text', value: value.slice(last, match.index) });
    nodes.push(linkNode(entry, name, ctx));
    last = match.index + name.length;
  }
  if (!changed) return null;
  if (last < value.length) nodes.push({ type: 'text', value: value.slice(last) });
  return nodes;
}

/**
 * @param {{slug: string, resource: string, urlParent: string}} entry
 * @param {string} text
 * @param {{game: string, lang: string, verSlug: string, verKey: string}} ctx
 */
function linkNode(entry, text, ctx) {
  return {
    type: 'element',
    tagName: 'a',
    properties: {
      className: ['ent-link'],
      href: `/${ctx.lang}/${ctx.game}/${ctx.verSlug}/${entry.urlParent}/${entry.slug}/`,
      'data-hc': `${ctx.game}/${ctx.verKey}/${ctx.lang}/${entry.resource}/${entry.slug}`,
    },
    children: [{ type: 'text', value: text }],
  };
}

// Полный текст элемента, только если ВСЕ прямые потомки — текстовые (иначе null).
function directText(/** @type {any} */ el) {
  if (!el.children || !el.children.length) return null;
  if (!el.children.every((/** @type {any} */ c) => c.type === 'text')) return null;
  return el.children.map((/** @type {any} */ c) => c.value).join('');
}

// Все <tr> внутри таблицы (thead/tbody прозрачны).
function collectRows(/** @type {any} */ node, /** @type {any[]} */ out) {
  for (const c of node.children || []) {
    if (c.type !== 'element') continue;
    if (c.tagName === 'tr') out.push(c);
    else collectRows(c, out);
  }
}

// Ядро: линкует имена сущностей прямо в hast-дереве. Общая логика для глав (rehype) и страниц
// сущностей (marked → hast). selfSlug — не линковать саму сущность на её же странице.
/**
 * @param {any} tree
 * @param {{game: string, version: string, lang: string, selfSlug?: string, chapterPath?: string}} ctx
 */
export function autolinkTree(tree, { game, version, lang, selfSlug, chapterPath = '' }) {
  const map = loadMap(game, version, lang);
  if (!map) return tree;
  /** @type {Set<string>} */
  const skip = new Set();
  if (selfSlug) skip.add(selfSlug);
  const ctx = { game, lang, verSlug: version, verKey: map.verKey };

  const exactEntry = (/** @type {string|null|undefined} */ rawText, /** @type {string} */ container) => {
    if (rawText == null) return null;
    const t = rawText.trim();
    const entry = map.exact[container].get(t.toLowerCase()); // регистро-независимо (текст ссылки — как в оригинале)
    return entry && !skip.has(entry.slug) ? { entry, text: t } : null;
  };

  const isSpellTable = (/** @type {any} */ table) => {
    /** @type {any[]} */
    const rows = [];
    collectRows(table, rows);
    if (!rows.length) return false;
    const first = rows[0].children.find((/** @type {any} */ c) => c.type === 'element' && (c.tagName === 'th' || c.tagName === 'td'));
    const head = first && directText(first);
    return head != null && SPELL_TABLE_HEAD.has(head.trim());
  };

  const linkSpellTable = (/** @type {any} */ table) => {
    /** @type {any[]} */
    const rows = [];
    collectRows(table, rows);
    for (const tr of rows) {
      const cell = tr.children.find((/** @type {any} */ c) => c.type === 'element' && c.tagName === 'td'); // только данные (не th)
      if (!cell) continue;
      const hit = exactEntry(directText(cell), 'em');
      if (hit) cell.children = [linkNode(hit.entry, hit.text, ctx)];
    }
  };

  const linkFeatCells = (/** @type {any} */ table) => {
    /** @type {any[]} */
    const rows = [];
    collectRows(table, rows);
    for (const tr of rows) {
      for (const cell of tr.children) {
        if (cell.type !== 'element' || cell.tagName !== 'td') continue;
        const txt = directText(cell);
        if (txt == null) continue;
        const entry = map.feats.get(txt.trim().toLowerCase());
        if (entry && !skip.has(entry.slug)) cell.children = [linkNode(entry, txt.trim(), ctx)];
      }
    }
  };

  // Гейт по колонке цены: иначе линковались бы случайные совпадения в чужих таблицах
  // (вариант «Кнут» у Жетона пера).
  const isEquipmentListing = (/** @type {any} */ table) => {
    /** @type {any[]} */
    const rows = [];
    collectRows(table, rows);
    if (!rows.length) return false;
    const hcells = rows[0].children.filter((/** @type {any} */ c) => c.type === 'element' && (c.tagName === 'th' || c.tagName === 'td'));
    const last = hcells.length ? directText(hcells[hcells.length - 1]) : null;
    return last != null && /^(Цена|Cost|Стоимость)/.test(last.trim());
  };

  const linkNameCells = (/** @type {any} */ table) => {
    /** @type {any[]} */
    const rows = [];
    collectRows(table, rows);
    for (const tr of rows) {
      const cell = tr.children.find((/** @type {any} */ c) => c.type === 'element' && c.tagName === 'td'); // только данные (не th)
      if (!cell) continue;
      const txt = directText(cell);
      if (txt == null) continue;
      const entry = map.cells.get(txt.trim().toLowerCase());
      if (entry && !skip.has(entry.slug)) cell.children = [linkNode(entry, txt.trim(), ctx)];
    }
  };

  const linkGridCells = (/** @type {any} */ table) => {
    /** @type {any[]} */
    const rows = [];
    collectRows(table, rows);
    for (const tr of rows) {
      for (const cell of tr.children) {
        if (cell.type !== 'element' || cell.tagName !== 'td') continue;
        const txt = directText(cell);
        if (txt == null) continue;
        const entry = map.grid.get(txt.trim().toLowerCase());
        if (entry && !skip.has(entry.slug) && (!entry.chapters || entry.chapters.test(chapterPath || ''))) {
          cell.children = [linkNode(entry, txt.trim(), ctx)];
        }
      }
    }
  };

  const walk = (/** @type {any} */ node, /** @type {boolean} */ insideSkip) => {
    if (!node.children) return;
    for (let i = 0; i < node.children.length; i++) {
      const child = node.children[i];
      if (child.type === 'element') {
        const tag = child.tagName;
        if (tag === 'table' && map.exact.em.size && isSpellTable(child)) linkSpellTable(child);
        if (tag === 'table' && map.grid && map.grid.size && chapterPath) linkGridCells(child);
        if (tag === 'table' && map.feats && map.feats.size) linkFeatCells(child);
        if (tag === 'table' && map.cells && map.cells.size && isEquipmentListing(child)) linkNameCells(child);
        if (!insideSkip && (tag === 'em' || tag === 'strong')) {
          const container = tag === 'em' ? 'em' : 'strong';
          if (map.exact[container].size) {
            const hit = exactEntry(directText(child), container);
            if (hit) {
              child.children = [linkNode(hit.entry, hit.text, ctx)];
              continue;
            }
          }
        }
        walk(child, insideSkip || SKIP_TAGS.has(tag));
      } else if (child.type === 'text' && !insideSkip && map.text) {
        const replaced = linkifyText(child.value, map.text, skip, ctx);
        if (replaced) {
          node.children.splice(i, 1, ...replaced);
          i += replaced.length - 1;
        }
      }
    }
  };
  walk(tree, false);
  return tree;
}

export default function rehypeEntityAutolink() {
  return (/** @type {any} */ tree, /** @type {any} */ file) => {
    const p = (file && (file.path || (file.history && file.history[0]))) || '';
    const m = p.replace(/\\/g, '/').match(/\/(dnd|daggerheart|brp)\/([^/]+)\/(en|ru)\//);
    if (!m) return;
    const [, game, version, lang] = m;
    autolinkTree(tree, { game, version, lang, chapterPath: p.replace(/\\/g, '/') });
  };
}
