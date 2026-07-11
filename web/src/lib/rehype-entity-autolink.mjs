// Автоссылки на программные страницы сущностей (issue #20): имена сущностей в контенте
// становятся ссылками на их страницы. Ручной обход hast-дерева — без доп. зависимостей.
//
// Два режима матчинга (по ресурсу):
//  • text  — состояния: plain-текст, case-sensitive keyword с границами слова (SRD капитализирует
//    имена состояний; строчное «prone» не ловим). Синонимы-краткие формы — в ALIASES.
//  • exact — заклинания: линкуем ТОЛЬКО там, где SRD сам разметил ссылку — курсив `<em>Свет</em>`
//    (полный текст = имя) ИЛИ первая колонка таблиц спелл-листов классов. Слово «свет» в прозе
//    не трогаем — только явные курсивные упоминания. Так снимается переусердствование.
//
// Не трогаем текст внутри <a>/<code>/<pre>/<kbd> и заголовков <h1>…<h6>.
import fs from 'node:fs';
import path from 'node:path';

// process.cwd() (= web/ на билде) — резолвится одинаково в конфиг-контексте (главы) и под Vite
// (страницы сущностей). import.meta.url под Vite указывает не туда.
const DATA_ROOT = path.resolve(process.cwd(), 'src/data/api');

// Ресурсы с программными страницами. mode: 'text' | 'exact'. versions — ограничение по версиям
// (где реально есть страницы); без него — все версии.
const RESOURCES = [
  { key: 'conditions', urlParent: 'rules-glossary/conditions', mode: 'text' },
  { key: 'spells', urlParent: 'spells', mode: 'exact', versions: ['srd-5.2'] },
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
  const textEntries = [];
  const exact = new Map();
  for (const { key, urlParent, mode, versions } of RESOURCES) {
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
        // Ключ в lowercase: SRD размечает курсивом ссылки на заклинания и СТРОЧНЫМИ
        // («*лечение ран*»), и с заглавной («*Благословение*») — ловим оба. Внутри <em>/ячейки
        // спелл-таблицы полное совпадение фразы с именем безопасно и без учёта регистра.
        const k = e.name.toLowerCase();
        if (!exact.has(k)) exact.set(k, entry);
      } else {
        textEntries.push(entry);
        for (const alias of aliases[e.slug] || []) textEntries.push({ ...entry, name: alias });
      }
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
  const result = text || exact.size ? { text, exact, verKey } : null;
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

  const exactEntry = (rawText) => {
    if (rawText == null) return null;
    const t = rawText.trim();
    const entry = map.exact.get(t.toLowerCase()); // регистро-независимо (текст ссылки — как в оригинале)
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
      const hit = exactEntry(directText(cell));
      if (hit) cell.children = [linkNode(hit.entry, hit.text, ctx)];
    }
  };

  const walk = (node, insideSkip) => {
    if (!node.children) return;
    for (let i = 0; i < node.children.length; i++) {
      const child = node.children[i];
      if (child.type === 'element') {
        const tag = child.tagName;
        // Спелл-таблица класса: линкуем первую колонку (данные), затем обычный обход остального.
        if (tag === 'table' && map.exact.size && isSpellTable(child)) linkSpellTable(child);
        // Курсивная ссылка на заклинание: <em>Имя</em> целиком.
        if (tag === 'em' && !insideSkip && map.exact.size) {
          const hit = exactEntry(directText(child));
          if (hit) {
            child.children = [linkNode(hit.entry, hit.text, ctx)];
            continue; // уже ссылка — внутрь не идём
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
