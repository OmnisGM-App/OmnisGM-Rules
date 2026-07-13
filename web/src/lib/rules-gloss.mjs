// Глоссинг терминов Rules Glossary в тексте (issue #20): имя термина оборачивается в
// <span class="gloss" data-hc> с hovercard-определением (НЕ ссылка — страниц у них нет).
//
// Сейчас — только ДЕЙСТВИЯ (Dash/Dodge/…). Их имена омонимичны обычным словам («Attack»
// голым = 499 вхождений: броски атаки, не действие), поэтому матчим ТОЛЬКО в явном
// контексте ссылки на действие:
//   • EN: «<Term> action» (Term + слово-маркер «action»);
//   • RU: «действие <Term>» (слово-маркер «действие/действия…» перед Term).
// Голые вхождения не трогаем → 0 ложных срабатываний. AoE отложены: в RU-прозе нет
// надёжного сигнала (спелл «Конус холода», списки форм) — EN-only сломал бы паритет.
import fs from 'node:fs';
import path from 'node:path';

const DATA_ROOT = path.resolve(process.cwd(), 'src/data/api');
const verKeyOf = (version) => version.replace(/[.\-]/g, '');
const escapeRegExp = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

// Не трогаем текст внутри ссылок/кода/заголовков и уже-глоссированного.
const SKIP_TAGS = new Set(['a', 'code', 'pre', 'kbd', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']);
const hasSkipClass = (el) => {
  const c = el.properties && el.properties.className;
  if (!c) return false;
  const arr = Array.isArray(c) ? c : [c];
  return arr.includes('gloss') || arr.includes('ent-link') || arr.includes('kw');
};

// Маркер контекста: EN — сразу после Term идёт « action»; RU — перед Term стоит «действие ».
// NB: JS \w — ASCII-only, кириллицу не ловит; RU-суффикс задаём явным классом [а-яё].
const AFTER_CTX = { en: /^\s+action\b/i, ru: null };
const BEFORE_CTX = { en: null, ru: /действ[а-яё]*\s+[«"„]?$/i };

const cache = new Map(); // `${game}/${version}/${lang}` → { re, byName, verKey } | null

function loadActions(game, version, lang) {
  const cacheKey = `${game}/${version}/${lang}`;
  if (cache.has(cacheKey)) return cache.get(cacheKey);
  const verKey = verKeyOf(version);
  let data;
  try {
    data = JSON.parse(fs.readFileSync(path.join(DATA_ROOT, game, verKey, lang, 'actions', 'all.json'), 'utf8'));
  } catch {
    cache.set(cacheKey, null);
    return null;
  }
  const byName = new Map();
  for (const e of data) if (e && e.name && e.slug) byName.set(e.name, e.slug);
  if (!byName.size) { cache.set(cacheKey, null); return null; }
  // Длинные имена раньше коротких; границы — юникод-aware (ASCII \b ломает кириллицу).
  const alt = [...byName.keys()].sort((a, b) => b.length - a.length).map(escapeRegExp).join('|');
  const re = new RegExp(`(?<![\\p{L}\\p{N}_])(${alt})(?![\\p{L}\\p{N}_])`, 'gu');
  const res = { re, byName, verKey };
  cache.set(cacheKey, res);
  return res;
}

function glossNode(term, slug, ctx) {
  return {
    type: 'element',
    tagName: 'span',
    properties: {
      className: ['gloss'],
      tabindex: '0',
      'data-hc': `${ctx.game}/${ctx.verKey}/${ctx.lang}/actions/${slug}`,
    },
    children: [{ type: 'text', value: term }],
  };
}

function glossText(value, map, lang, ctx) {
  map.re.lastIndex = 0;
  const after = AFTER_CTX[lang];
  const before = BEFORE_CTX[lang];
  const nodes = [];
  let last = 0;
  let changed = false;
  let m;
  while ((m = map.re.exec(value))) {
    const term = m[1];
    const idx = m.index;
    const end = idx + term.length;
    const okAfter = after ? after.test(value.slice(end)) : false;
    const okBefore = before ? before.test(value.slice(0, idx)) : false;
    if (!okAfter && !okBefore) continue;
    const slug = map.byName.get(term);
    if (!slug) continue;
    changed = true;
    if (idx > last) nodes.push({ type: 'text', value: value.slice(last, idx) });
    nodes.push(glossNode(term, slug, ctx));
    last = end;
  }
  if (!changed) return null;
  if (last < value.length) nodes.push({ type: 'text', value: value.slice(last) });
  return nodes;
}

// Ядро: глоссит термины прямо в hast-дереве. Общая логика для глав (rehype) и страниц
// сущностей (spells/monsters render()).
export function glossRules(tree, { game, version, lang }) {
  const map = loadActions(game, version, lang);
  if (!map) return tree;
  const ctx = { game, lang, verKey: map.verKey };
  const walk = (node, skip) => {
    if (!node.children) return;
    for (let i = 0; i < node.children.length; i++) {
      const child = node.children[i];
      if (child.type === 'element') {
        walk(child, skip || SKIP_TAGS.has(child.tagName) || hasSkipClass(child));
      } else if (child.type === 'text' && !skip) {
        const replaced = glossText(child.value, map, lang, ctx);
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

// rehype-обёртка для глав (весь контент). Порядок в pipeline — ПОСЛЕ автолинка/подсветки,
// чтобы не лезть внутрь уже-ссылок/подсветки (они в SKIP через hasSkipClass).
export default function rehypeRulesGloss() {
  return (tree, file) => {
    const p = (file && (file.path || (file.history && file.history[0]))) || '';
    const m = p.replace(/\\/g, '/').match(/\/(dnd|daggerheart|brp)\/([^/]+)\/(en|ru)\//);
    if (!m) return;
    const [, game, version, lang] = m;
    glossRules(tree, { game, version, lang });
  };
}
