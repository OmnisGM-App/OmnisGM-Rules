// Глоссинг терминов Rules Glossary в тексте (issue #20): имя термина оборачивается в
// <span class="gloss" data-hc> с hovercard-определением (НЕ ссылка — страниц у них нет).
//
// Две группы:
//  • ДЕЙСТВИЯ (actions, Dash/Dodge/…): имена омонимичны словам («Attack» голым = 499
//    вхождений), поэтому матчим ТОЛЬКО в явном контексте — EN «<Term> action», RU «действие
//    <Term>». Голые вхождения не трогаем.
//  • ТЕРМИНЫ ЯДРА (rules-terms): курируемый список ДИСТИНКТИВНЫХ терминов (многословных —
//    «Труднопроходимая местность», «Провоцированные атаки» — и пары надёжных: Концентрация).
//    RU склоняется без сигнала капитализации → матчим по СТЕМ-паттерну (инвариантная основа,
//    ловит все падежи); EN — точная фраза с заглавной. Общие односложные слова (Укрытие/Урон/
//    Спасбросок) НЕ включены — риск пере-линковки.
//
// AoE отложены: в RU-прозе нет надёжного сигнала (спелл «Конус холода», списки форм).
import fs from 'node:fs';
import path from 'node:path';

const DATA_ROOT = path.resolve(process.cwd(), 'src/data/api');
const verKeyOf = (version) => version.replace(/[.\-]/g, '');
const escapeRegExp = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const SKIP_TAGS = new Set(['a', 'code', 'pre', 'kbd', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']);
const hasSkipClass = (el) => {
  const c = el.properties && el.properties.className;
  if (!c) return false;
  const arr = Array.isArray(c) ? c : [c];
  return arr.includes('gloss') || arr.includes('ent-link') || arr.includes('kw');
};

// Контекст действий: EN — сразу после Term «action»; RU — перед Term «действие ».
// NB: JS \w — ASCII-only; RU-суффиксы задаём явным классом [а-яё].
const AFTER_CTX = { en: /^\s+action\b/iu, ru: null };
const BEFORE_CTX = { en: null, ru: /действ[а-яё]*\s+[«"„]?$/iu };

// Курируемые термины ядра. en — точная фраза (регэксп-фрагмент, матч с учётом регистра);
// ru — стем-паттерн (регэксп-фрагмент, матч БЕЗ учёта регистра, ловит склонения). Все —
// дистинктивные (многословные либо однозначные), чтобы не задеть обычные слова.
const CORE_TERMS = [
  { slug: 'difficult-terrain', en: 'Difficult Terrain', ru: 'Труднопроходим[а-яё]+\\s+местност[а-яё]+' },
  { slug: 'passive-perception', en: 'Passive Perception', ru: 'Пассивн[а-яё]+\\s+[Вв]нимательност[а-яё]+' },
  { slug: 'opportunity-attacks', en: 'Opportunity Attacks?', ru: 'Провоцированн[а-яё]+\\s+атак[а-яё]+' },
  { slug: 'temporary-hit-points', en: 'Temporary Hit Points', ru: 'Временн[а-яё]+\\s+хит[а-яё]+' },
  { slug: 'heroic-inspiration', en: 'Heroic Inspiration', ru: 'Героическ[а-яё]+\\s+вдохновени[а-яё]+' },
  { slug: 'critical-hit', en: 'Critical Hits?', ru: 'Критическ[а-яё]+\\s+попадани[а-яё]+' },
  { slug: 'death-saving-throw', en: 'Death Saving Throws?', ru: 'Спасброс[а-яё]+\\s+от\\s+смерти' },
  { slug: 'concentration', en: 'Concentration', ru: 'Концентрац[а-яё]+' },
  // Батч 2 (#20): ещё 14 дистинктивных. Симметрия RU/EN подтверждена замером в семантике кода
  // (EN регистрозависимо, RU регистронезависимо-стем). Аббревиатуры (AC/КД, CR/ПО) не глоссим
  // ни на одной стороне. Все многословны либо однозначны в этом корпусе (ложных срабатываний нет).
  { slug: 'armor-class', en: 'Armor Class', ru: 'Класс[а-яё]*\\s+доспех[а-яё]+' },
  { slug: 'bonus-action', en: 'Bonus Actions?', ru: 'Бонусн[а-яё]+\\s+действи[а-яё]+' },
  { slug: 'attack-roll', en: 'Attack Rolls?', ru: 'Брос[а-яё]+\\s+атак[а-яё]+' },
  { slug: 'initiative', en: 'Initiative', ru: 'Инициатив[а-яё]+' },
  { slug: 'challenge-rating', en: 'Challenge Rating', ru: 'Показател[а-яё]+\\s+опасност[а-яё]+' },
  { slug: 'unarmed-strike', en: 'Unarmed Strikes?', ru: 'Безоружн[а-яё]+\\s+удар[а-яё]*' },
  { slug: 'short-rest', en: 'Short Rest', ru: 'Коротк[а-яё]+\\s+отдых[а-яё]*' },
  { slug: 'long-rest', en: 'Long Rest', ru: 'Продолжительн[а-яё]+\\s+отдых[а-яё]*' },
  { slug: 'bright-light', en: 'Bright Light', ru: 'Ярк[а-яё]+\\s+свет[а-яё]*' },
  { slug: 'dim-light', en: 'Dim Light', ru: 'Тускл[а-яё]+\\s+свет[а-яё]*' },
  { slug: 'experience-points', en: 'Experience Points', ru: 'Очк[а-яё]+\\s+опыт[а-яё]+' },
  { slug: 'spellcasting-focus', en: 'Spellcasting Focus', ru: 'Заклинательн[а-яё]+\\s+фокус[а-яё]*' },
  { slug: 'carrying-capacity', en: 'Carrying Capacity', ru: 'Грузоподъ[её]мност[а-яё]+' },
  { slug: 'damage-threshold', en: 'Damage Threshold', ru: 'Порог[а-яё]*\\s+урон[а-яё]*' },
  // Сенсорные термины (Тёмное/Слепое зрение, Truesight, Tremorsense) намеренно НЕ включены:
  // ковром идут по строкам «Чувства» в бестиарии, а RU-проза для truesight использует другой
  // термин («истинное зрение» ≠ глоссарное «Видение истины»). Отдельно, с гейтом «не в статблоке».
];
const grp = (slug) => slug.replace(/-/g, '_');
const slugFromGroups = (groups) => {
  for (const t of CORE_TERMS) if (groups[grp(t.slug)] != null) return t.slug;
  return null;
};

const cache = new Map();

function loadGloss(game, version, lang) {
  const cacheKey = `${game}/${version}/${lang}`;
  if (cache.has(cacheKey)) return cache.get(cacheKey);
  const verKey = verKeyOf(version);
  const read = (res) => {
    try { return JSON.parse(fs.readFileSync(path.join(DATA_ROOT, game, verKey, lang, res, 'all.json'), 'utf8')); }
    catch { return null; }
  };
  // Действия: имя → slug + альтернация (юникод-границы; ASCII \b ломает кириллицу).
  const actionsData = read('actions');
  let actionRe = null;
  const actionByName = new Map();
  if (actionsData) {
    for (const e of actionsData) if (e && e.name && e.slug) actionByName.set(e.name, e.slug);
    if (actionByName.size) {
      const alt = [...actionByName.keys()].sort((a, b) => b.length - a.length).map(escapeRegExp).join('|');
      actionRe = new RegExp(`(?<![\\p{L}\\p{N}_])(${alt})(?![\\p{L}\\p{N}_])`, 'gu');
    }
  }
  // Термины ядра: именованные группы; EN — регистро-зависимо, RU — регистро-независимо (стемы).
  const field = lang === 'en' ? 'en' : 'ru';
  const parts = CORE_TERMS.map((t) => `(?<${grp(t.slug)}>${t[field]})`).join('|');
  const flags = lang === 'en' ? 'gu' : 'giu';
  const coreRe = new RegExp(`(?<![\\p{L}\\p{N}_])(?:${parts})(?![\\p{L}\\p{N}_])`, flags);

  const res = actionRe || coreRe ? { actionRe, actionByName, coreRe, verKey } : null;
  cache.set(cacheKey, res);
  return res;
}

function glossNode(term, slug, resource, ctx) {
  return {
    type: 'element',
    tagName: 'span',
    properties: {
      className: ['gloss'],
      tabindex: '0',
      'data-hc': `${ctx.game}/${ctx.verKey}/${ctx.lang}/${resource}/${slug}`,
    },
    children: [{ type: 'text', value: term }],
  };
}

function glossText(value, map, lang, ctx) {
  const spans = []; // { idx, end, term, slug, resource }
  // Действия — с контекст-гейтом.
  if (map.actionRe) {
    map.actionRe.lastIndex = 0;
    const after = AFTER_CTX[lang], before = BEFORE_CTX[lang];
    let m;
    while ((m = map.actionRe.exec(value))) {
      const term = m[1], idx = m.index, end = idx + term.length;
      const ok = (after && after.test(value.slice(end))) || (before && before.test(value.slice(0, idx)));
      if (!ok) continue;
      const slug = map.actionByName.get(term);
      if (slug) spans.push({ idx, end, term, slug, resource: 'actions' });
    }
  }
  // Термины ядра — прямой матч (дистинктивные).
  if (map.coreRe) {
    map.coreRe.lastIndex = 0;
    let m;
    while ((m = map.coreRe.exec(value))) {
      const slug = slugFromGroups(m.groups || {});
      if (slug) spans.push({ idx: m.index, end: m.index + m[0].length, term: m[0], slug, resource: 'rules-terms' });
    }
  }
  if (!spans.length) return null;
  // Сортировка + отбрасывание пересечений (первый по позиции побеждает).
  spans.sort((a, b) => a.idx - b.idx || b.end - a.end);
  const nodes = [];
  let last = 0;
  for (const s of spans) {
    if (s.idx < last) continue; // пересечение с уже вставленным
    if (s.idx > last) nodes.push({ type: 'text', value: value.slice(last, s.idx) });
    nodes.push(glossNode(s.term, s.slug, s.resource, ctx));
    last = s.end;
  }
  if (last < value.length) nodes.push({ type: 'text', value: value.slice(last) });
  return nodes;
}

// Ядро: глоссит термины прямо в hast-дереве. Для глав (rehype) и страниц сущностей (render()).
export function glossRules(tree, { game, version, lang }) {
  const map = loadGloss(game, version, lang);
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

// rehype-обёртка для глав. Порядок в pipeline — ПОСЛЕ автолинка/подсветки (они в SKIP).
export default function rehypeRulesGloss() {
  return (tree, file) => {
    const p = (file && (file.path || (file.history && file.history[0]))) || '';
    const m = p.replace(/\\/g, '/').match(/\/(dnd|daggerheart|brp)\/([^/]+)\/(en|ru)\//);
    if (!m) return;
    const [, game, version, lang] = m;
    glossRules(tree, { game, version, lang });
  };
}
