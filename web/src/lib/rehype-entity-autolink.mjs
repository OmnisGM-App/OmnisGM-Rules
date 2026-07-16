// Автоссылки на программные страницы сущностей (issue #20): имена сущностей в контенте
// становятся ссылками на их страницы. Ручной обход hast-дерева — без доп. зависимостей.
//
// Два режима матчинга (по ресурсу):
//  • text  — состояния: plain-текст, case-sensitive keyword с границами слова (SRD капитализирует
//    имена состояний; строчное «prone» не ловим). Синонимы-краткие формы — в ALIASES.
//  • exact — заклинания/монстры: линкуем ТОЛЬКО там, где SRD сам разметил ссылку. Контейнер
//    задаётся ресурсом: заклинания — курсив `<em>Свет</em>` (полный текст = имя) ИЛИ первая
//    колонка спелл-таблиц классов; монстры — жирный `<strong>Скелет</strong>` (сигнал SRD
//    «см. Монстры»). Строчное «свет» / генеричное «Стражник» в прозе не трогаем — только
//    явную разметку. Так снимается переусердствование.
//
// Не трогаем текст внутри <a>/<code>/<pre>/<kbd> и заголовков <h1>…<h6>.
import fs from 'node:fs';
import path from 'node:path';

// process.cwd() (= web/ на билде) — резолвится одинаково в конфиг-контексте (главы) и под Vite
// (страницы сущностей). import.meta.url под Vite указывает не туда.
const DATA_ROOT = path.resolve(process.cwd(), 'src/data/api');

// Ресурсы с программными страницами. mode: 'text' | 'exact'. container (для exact) — тег-обёртка
// разметки-сигнала SRD: 'em' (курсив, заклинания) или 'strong' (жирный, монстры). versions —
// ограничение по версиям (где реально есть страницы); без него — все версии.
const RESOURCES = [
  { key: 'conditions', urlParent: 'rules-glossary/conditions', mode: 'text' },
  { key: 'spells', urlParent: 'spells', mode: 'exact', container: 'em', versions: ['srd-5.2', 'srd-5.1'] },
  { key: 'monsters', urlParent: 'monsters-a-z', mode: 'exact', container: 'strong', versions: ['srd-5.2', 'srd-5.1'] },
  // Животные — тот же жирный сигнал SRD, что и монстры («**Волк**» → см. Животные). Слаги и имена
  // животных не пересекаются с монстрами (проверено) → общий strong-матч безопасен. Только 5.2:
  // в 5.1 звери входят в общий бестиарий (ресурс monsters), отдельного animals нет.
  { key: 'animals', urlParent: 'animals', mode: 'exact', container: 'strong', versions: ['srd-5.2'] },
  // Предметы — тоже курсив (SRD размечает ссылки на предметы как «*Название*», как заклинания).
  // Имена предметов и заклинаний не пересекаются → общий em-матч безопасен.
  { key: 'magic-items', urlParent: 'magic-items', mode: 'exact', container: 'em', versions: ['srd-5.2', 'srd-5.1'] },
  // Черты: имена НЕ размечены курсивом/жирным и часто омонимичны обычным словам
  // (Defense/Archery/Skilled). Поэтому режим 'feats': (1) ячейка таблицы, точно равная имени
  // черты (колонка «Черты/Features» таблиц классов — ASI на всех уровнях, боевые стили) →
  // безопасно и всегда корректно; (2) в прозе линкуем ТОЛЬКО много-словные имена (ASI,
  // эпические дары «Дар …», «Посвящённый в магию»…) — они дистинктивны; одно-словные в прозе
  // не трогаем.
  { key: 'feats', urlParent: 'feats', mode: 'feats', versions: ['srd-5.2', 'srd-5.1'] },
  // Оружие/доспехи/снаряжение: имена не размечены (ни курсив, ни жирный) и часто омонимичны
  // обычным словам («Молот», «Щит», «Верёвка»). Поэтому режим 'cells' — линкуем ТОЛЬКО ячейку
  // таблицы, точно равную имени (таблицы главы «Снаряжение» → детальные страницы). Прозу не
  // трогаем вовсе. Точное совпадение ячейки → 0 ложных срабатываний.
  { key: 'weapons', urlParent: 'weapons', mode: 'cells', versions: ['srd-5.2', 'srd-5.1'] },
  { key: 'armor', urlParent: 'armor', mode: 'cells', versions: ['srd-5.2', 'srd-5.1'] },
  { key: 'equipment', urlParent: 'equipment', mode: 'cells', versions: ['srd-5.2', 'srd-5.1'] },
];

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

// Синонимы для exact-ресурсов (в разметке-контейнере): `${game}/${lang}` → { [resource]: { slug: [form…] } }.
// Имя сущности в тексте склоняется (RU-падежи) / стоит во мн. числе (EN), а exact-матч — по
// именительному. Здесь — реальные жирные формы монстров из данных, чтобы они тоже линковались.
// Строго курируемый список (не морфология-эвристика) → 0 ложных срабатываний.
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
    // Курируемый список реальных форм → на статблок животного. Именительный уже ловится сам.
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

const escapeRegExp = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const verKeyOf = (version) => version.replace(/[.\-]/g, ''); // srd-5.2 → srd52

// Кэш: `${game}/${version}/${lang}` → { text: {regexSource, byName} | null, exact: Map, verKey } | null
const mapCache = new Map();

function loadMap(game, version, lang) {
  const cacheKey = `${game}/${version}/${lang}`;
  if (mapCache.has(cacheKey)) return mapCache.get(cacheKey);
  const verKey = verKeyOf(version);
  const aliases = ALIASES[`${game}/${lang}`] || {};
  const exactAliases = EXACT_ALIASES[`${game}/${lang}`] || {};
  const textEntries = [];
  // exact-карты по контейнеру: em (заклинания) и strong (монстры) — держим раздельно, чтобы
  // имя монстра в курсиве / имя заклинания в жирном не матчились не в своём контексте.
  const exact = { em: new Map(), strong: new Map() };
  // Черты: exact-карта «имя → сущность» (lowercase) для точечного матча ячеек таблиц.
  const feats = new Map();
  // Оружие/доспехи/снаряжение: карта «имя → сущность» для матча точных ячеек таблиц.
  const cells = new Map();
  // Имена magic-items/monsters — зарезервированы: их не линкуем как cells (редкие кросс-ресурс
  // коллизии: «Свиток заклинания» = equipment+magic-item, «Страж-щит» = magic-item+monster).
  // magic-items/monsters идут в RESOURCES раньше оружия → к моменту cells набор полон.
  const reserved = new Set();
  for (const { key, urlParent, mode, container, versions } of RESOURCES) {
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
        // Ключ в lowercase: SRD размечает ссылки и СТРОЧНЫМИ («*лечение ран*»), и с заглавной
        // («*Благословение*», «**Скелет**») — ловим оба. Внутри разметки-контейнера полное
        // совпадение фразы с именем безопасно и без учёта регистра.
        const m = exact[container];
        const k = e.name.toLowerCase();
        if (m && !m.has(k)) m.set(k, entry);
        // Склонённые/мн.-числа формы того же имени → на ту же сущность.
        for (const form of exactAliases[key]?.[e.slug] || []) {
          const fk = form.toLowerCase();
          if (m && !m.has(fk)) m.set(fk, entry);
        }
      } else if (mode === 'feats') {
        // Ячейки таблиц — любое имя черты (точное совпадение текста ячейки).
        const k = e.name.toLowerCase();
        if (!feats.has(k)) feats.set(k, entry);
        // Проза — только много-словные (дистинктивные) имена; одно-словные омонимичны.
        if (e.name.trim().split(/\s+/).length >= 2) textEntries.push(entry);
      } else if (mode === 'cells') {
        const k = e.name.toLowerCase();
        if (!reserved.has(k) && !cells.has(k)) cells.set(k, entry);
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
  const result = text || exact.em.size || exact.strong.size || feats.size || cells.size
    ? { text, exact, feats, cells, verKey } : null;
  mapCache.set(cacheKey, result);
  return result;
}

function linkifyText(value, textMap, skip, ctx) {
  const re = new RegExp(textMap.regexSource, 'gu');
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

function linkNode(entry, text, ctx) {
  return {
    type: 'element',
    tagName: 'a',
    properties: {
      className: ['ent-link'],
      href: `/${ctx.lang}/${ctx.game}/${ctx.verSlug}/${entry.urlParent}/${entry.slug}/`,
      // Ключ для hovercard: game/verKey/lang/resource/slug.
      'data-hc': `${ctx.game}/${ctx.verKey}/${ctx.lang}/${entry.resource}/${entry.slug}`,
    },
    children: [{ type: 'text', value: text }],
  };
}

// Полный текст элемента, только если ВСЕ прямые потомки — текстовые (иначе null).
function directText(el) {
  if (!el.children || !el.children.length) return null;
  if (!el.children.every((c) => c.type === 'text')) return null;
  return el.children.map((c) => c.value).join('');
}

// Все <tr> внутри таблицы (thead/tbody прозрачны).
function collectRows(node, out) {
  for (const c of node.children || []) {
    if (c.type !== 'element') continue;
    if (c.tagName === 'tr') out.push(c);
    else collectRows(c, out);
  }
}

// Ядро: линкует имена сущностей прямо в hast-дереве. Общая логика для глав (rehype) и страниц
// сущностей (marked → hast). selfSlug — не линковать саму сущность на её же странице.
export function autolinkTree(tree, { game, version, lang, selfSlug }) {
  const map = loadMap(game, version, lang);
  if (!map) return tree;
  const skip = new Set();
  if (selfSlug) skip.add(selfSlug);
  const ctx = { game, lang, verSlug: version, verKey: map.verKey };

  const exactEntry = (rawText, container) => {
    if (rawText == null) return null;
    const t = rawText.trim();
    const entry = map.exact[container].get(t.toLowerCase()); // регистро-независимо (текст ссылки — как в оригинале)
    return entry && !skip.has(entry.slug) ? { entry, text: t } : null;
  };

  const isSpellTable = (table) => {
    const rows = [];
    collectRows(table, rows);
    if (!rows.length) return false;
    const first = rows[0].children.find((c) => c.type === 'element' && (c.tagName === 'th' || c.tagName === 'td'));
    const head = first && directText(first);
    return head != null && SPELL_TABLE_HEAD.has(head.trim());
  };

  const linkSpellTable = (table) => {
    const rows = [];
    collectRows(table, rows);
    for (const tr of rows) {
      const cell = tr.children.find((c) => c.type === 'element' && c.tagName === 'td'); // только данные (не th)
      if (!cell) continue;
      const hit = exactEntry(directText(cell), 'em');
      if (hit) cell.children = [linkNode(hit.entry, hit.text, ctx)];
    }
  };

  // Черты: любая ячейка <td>, точно равная имени черты (колонка «Черты/Features» таблиц классов
  // — ASI на всех уровнях, боевые стили в таблицах). Точное совпадение → 0 ложных срабатываний.
  const linkFeatCells = (table) => {
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

  // Таблица-перечень снаряжения: последняя колонка — Цена/Cost/Стоимость (так размечены
  // таблицы оружия/доспехов/снаряжения в главе). Гейт нужен, чтобы не линковать ячейки в чужих
  // таблицах, где имя совпадает случайно (напр. вариант «Кнут» у Жетона пера — там нет колонки
  // цены), — как isSpellTable для спелл-листов.
  const isEquipmentListing = (table) => {
    const rows = [];
    collectRows(table, rows);
    if (!rows.length) return false;
    const hcells = rows[0].children.filter((c) => c.type === 'element' && (c.tagName === 'th' || c.tagName === 'td'));
    const last = hcells.length ? directText(hcells[hcells.length - 1]) : null;
    return last != null && /^(Цена|Cost|Стоимость)/.test(last.trim());
  };

  // Оружие/доспехи/снаряжение: ПЕРВАЯ колонка (имя) каждой строки-данных, точно равная имени
  // сущности → детальная страница. Точное совпадение ячейки → безопасно даже для «Молот»/«Щит».
  const linkNameCells = (table) => {
    const rows = [];
    collectRows(table, rows);
    for (const tr of rows) {
      const cell = tr.children.find((c) => c.type === 'element' && c.tagName === 'td'); // только данные (не th)
      if (!cell) continue;
      const txt = directText(cell);
      if (txt == null) continue;
      const entry = map.cells.get(txt.trim().toLowerCase());
      if (entry && !skip.has(entry.slug)) cell.children = [linkNode(entry, txt.trim(), ctx)];
    }
  };

  const walk = (node, insideSkip) => {
    if (!node.children) return;
    for (let i = 0; i < node.children.length; i++) {
      const child = node.children[i];
      if (child.type === 'element') {
        const tag = child.tagName;
        // Спелл-таблица класса: линкуем первую колонку (данные), затем обычный обход остального.
        if (tag === 'table' && map.exact.em.size && isSpellTable(child)) linkSpellTable(child);
        // Черты в ячейках любых таблиц (таблицы прогрессии классов и т.п.).
        if (tag === 'table' && map.feats && map.feats.size) linkFeatCells(child);
        // Оружие/доспехи/снаряжение — первая колонка таблиц-перечней (глава «Снаряжение»).
        if (tag === 'table' && map.cells && map.cells.size && isEquipmentListing(child)) linkNameCells(child);
        // Курсивная ссылка на заклинание <em>Имя</em> / жирная на монстра <strong>Имя</strong> —
        // полный текст элемента = имя. Внутрь уже-ссылки не идём.
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
  return (tree, file) => {
    const p = (file && (file.path || (file.history && file.history[0]))) || '';
    const m = p.replace(/\\/g, '/').match(/\/(dnd|daggerheart|brp)\/([^/]+)\/(en|ru)\//);
    if (!m) return;
    const [, game, version, lang] = m;
    autolinkTree(tree, { game, version, lang });
  };
}
