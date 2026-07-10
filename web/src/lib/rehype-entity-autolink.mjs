// Автоссылки на программные страницы сущностей (issue #20): в контенте глав имена сущностей,
// у которых есть отдельная страница (пока — состояния/conditions), становятся ссылками на неё.
// Ручной обход hast-дерева — как rehype-wrap-tables/promote-headings, без доп. зависимостей.
//
// Правила матчинга:
//  • Совпадение по display-имени в языке страницы (EN «Frightened», RU «Испуганный»).
//  • Case-sensitive: SRD капитализирует имена состояний как ключевые слова, поэтому строчное
//    «prone/frightened» в обычной прозе не ловится — только «Prone/Frightened».
//  • Границы слова через unicode-lookaround (\b в JS не работает с кириллицей).
//  • Первое вхождение каждой сущности на страницу (конвенция глоссариев — линкуем первое упоминание).
//  • Не трогаем текст внутри <a>/<code>/<pre> и заголовков <h1>…<h6>.
import fs from 'node:fs';
import path from 'node:path';

// process.cwd() (= web/ на билде) — резолвится одинаково и в конфиг-контексте (главы через
// astro.config), и под Vite (страницы сущностей). import.meta.url под Vite указывает не туда.
const DATA_ROOT = path.resolve(process.cwd(), 'src/data/api');

// Ресурсы с программными страницами → сегмент URL-родителя под главой.
const RESOURCES = [{ key: 'conditions', urlParent: 'rules-glossary/conditions' }];

const SKIP_TAGS = new Set(['a', 'code', 'pre', 'kbd', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']);

const escapeRegExp = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const verKeyOf = (version) => version.replace(/[.\-]/g, ''); // srd-5.2 → srd52

// Кэш карт совпадений: `${game}/${version}/${lang}` → { regexSource, byName, verKey } | null
const mapCache = new Map();

function loadMap(game, version, lang) {
  const cacheKey = `${game}/${version}/${lang}`;
  if (mapCache.has(cacheKey)) return mapCache.get(cacheKey);
  const verKey = verKeyOf(version);
  const entries = [];
  for (const { key, urlParent } of RESOURCES) {
    const file = path.join(DATA_ROOT, game, verKey, lang, key, 'all.json');
    let data;
    try {
      data = JSON.parse(fs.readFileSync(file, 'utf8'));
    } catch {
      continue; // ресурса нет для этой игры/версии/языка — просто пропускаем
    }
    for (const e of data) {
      if (e && e.name && e.slug) entries.push({ name: e.name, slug: e.slug, resource: key, urlParent });
    }
  }
  if (!entries.length) {
    mapCache.set(cacheKey, null);
    return null;
  }
  // Длинные имена раньше коротких: в JS-альтернации побеждает первый матч, а не самый длинный.
  entries.sort((a, b) => b.name.length - a.name.length);
  const byName = new Map(entries.map((e) => [e.name, e]));
  const alt = entries.map((e) => escapeRegExp(e.name)).join('|');
  const regexSource = `(?<![\\p{L}\\p{N}_])(${alt})(?![\\p{L}\\p{N}_])`;
  const result = { regexSource, byName, verKey };
  mapCache.set(cacheKey, result);
  return result;
}

function linkifyText(value, map, linked, ctx) {
  const re = new RegExp(map.regexSource, 'gu');
  const nodes = [];
  let last = 0;
  let changed = false;
  let match;
  while ((match = re.exec(value))) {
    const name = match[1];
    const entry = map.byName.get(name);
    if (!entry || linked.has(entry.slug)) continue; // уже слинковано на странице — оставляем текстом
    linked.add(entry.slug);
    changed = true;
    if (match.index > last) nodes.push({ type: 'text', value: value.slice(last, match.index) });
    const href = `/${ctx.lang}/${ctx.game}/${ctx.verSlug}/${entry.urlParent}/${entry.slug}/`;
    nodes.push({
      type: 'element',
      tagName: 'a',
      properties: {
        className: ['ent-link'],
        href,
        // Ключ для hovercard (PR B): game/verKey/lang/resource/slug.
        'data-hc': `${ctx.game}/${map.verKey}/${ctx.lang}/${entry.resource}/${entry.slug}`,
      },
      children: [{ type: 'text', value: name }],
    });
    last = match.index + name.length;
  }
  if (!changed) return null;
  if (last < value.length) nodes.push({ type: 'text', value: value.slice(last) });
  return nodes;
}

// Ядро: линкует имена сущностей прямо в hast-дереве. Используется и rehype-обёрткой (главы Astro),
// и страницами сущностей (marked → hast → toHtml), поэтому логика одна.
//  game/version/lang — контекст страницы; selfSlug — не линковать саму сущность на её же странице.
export function autolinkTree(tree, { game, version, lang, selfSlug }) {
  const map = loadMap(game, version, lang);
  if (!map) return tree;
  const linked = new Set();
  if (selfSlug) linked.add(selfSlug); // самоссылку не ставим
  const ctx = { game, lang, verSlug: version };

  const walk = (node, insideSkip) => {
    if (!node.children) return;
    for (let i = 0; i < node.children.length; i++) {
      const child = node.children[i];
      if (child.type === 'element') {
        walk(child, insideSkip || SKIP_TAGS.has(child.tagName));
      } else if (child.type === 'text' && !insideSkip) {
        const replaced = linkifyText(child.value, map, linked, ctx);
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
