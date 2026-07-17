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
  // attack-roll намеренно НЕ глоссим (батч 2 включал, откатили): EN 5.2 формализовал
  // «Melee/Ranged Attack Roll» как капитал-компаунд (429×), матч ловил «Attack Roll» внутри,
  // а RU пишет «рукопашная/дальнобойная атака» БЕЗ «бросок атаки» → структурная асимметрия
  // (dist 864/427), стемом не лечится. Карточка HC у attack-roll остаётся (это сущность).
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
// Курируемые термины глоссария Daggerheart для gloss-подсказок. Дистинктивные
// (многословные броски/пороги/жаргон) + 3 состояния (в стат-блоках курсивом, высокая
// ценность). en — точная фраза (регистро-зависимо); ru — стем/явные формы (регистро-
// независимо, ловит склонения). Все слаги существуют в ресурсе rules-terms (карточки HC).
const DH_TERMS = [
  // Состояния.
  { slug: 'hidden', en: 'Hidden', ru: 'Скрыт(?:ый|ого|ому|ым|ом|ая|ую|ое|ые|ых|ыми)' },
  { slug: 'restrained', en: 'Restrained', ru: 'Опутанн[а-яё]+' },
  { slug: 'vulnerable', en: 'Vulnerable', ru: 'Уязвим[а-яё]+' },
  // Броски (многословные механики → регистро-независимы даже в EN, char-класс первых букв:
  // SRD пишет их и с заглавной, и строчными — «make an action roll» / «Reaction Roll»).
  { slug: 'action-roll', en: '[Aa]ction [Rr]olls?', ru: 'Броск[а-яё]+\\s+Действия' },
  { slug: 'attack-roll', en: '[Aa]ttack [Rr]olls?', ru: 'Броск[а-яё]+\\s+Атаки' },
  { slug: 'damage-roll', en: '[Dd]amage [Rr]olls?', ru: 'Броск[а-яё]+\\s+Урона' },
  { slug: 'reaction-roll', en: '[Rr]eaction [Rr]olls?', ru: 'Броск[а-яё]+\\s+Реакции' },
  { slug: 'spellcast-roll', en: '[Ss]pellcast [Rr]olls?', ru: 'Броск[а-яё]+\\s+Магической\\s+Характеристики' },
  // Ядро (дистинктивные).
  { slug: 'armor-slots', en: 'Armor Slots?', ru: 'Ячейк[а-яё]+\\s+Брони' },
  { slug: 'damage-thresholds', en: 'Damage Thresholds?', ru: 'Порог[а-яё]*\\s+[Уу]рона' },
  { slug: 'death-door', en: 'Death Door', ru: 'Врат[а-яё]*\\s+[Сс]мерти' },
  { slug: 'direct-damage', en: 'Direct Damage', ru: 'Прям[а-яё]+\\s+[Уу]рон[а-яё]*' },
  { slug: 'recall-cost', en: 'Recall Cost', ru: 'Стоимост[а-яё]+\\s+[Оо]тзыва' },
  { slug: 'countdown', en: 'Countdown', ru: 'Обратн[а-яё]+\\s+[Оо]тсч[её]т[а-яё]*' },
  { slug: 'evasion', en: 'Evasion', ru: 'Уклонени[а-яё]+' },
];

const TERMS_BY_GAME = { dnd: CORE_TERMS, daggerheart: DH_TERMS };

const grp = (slug) => slug.replace(/-/g, '_');
const slugFromGroups = (groups, terms) => {
  for (const t of terms) if (groups[grp(t.slug)] != null) return t.slug;
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
  // Глоссим ТОЛЬКО если у версии есть ресурс rules-terms (иначе data-hc указывал бы на пустой
  // hovercard-бакет — «мёртвая» подсказка). В 5.1 rules-terms нет → gloss ядра выключен, версии
  // независимы (подсказки не смешиваются). CORE_TERMS выверены на 5.2-корпусе.
  // Термины ядра по игре (D&D — CORE_TERMS, Daggerheart — DH_TERMS). Гейт на наличие
  // ресурса rules-terms у версии: иначе data-hc указывал бы в пустой бакет («мёртвая»
  // подсказка). В D&D 5.1 rules-terms нет → gloss ядра выключен. Наборы разных игр не
  // пересекаются (изоляция бакетов game/ver/lang → подсказки не смешиваются).
  const terms = TERMS_BY_GAME[game] || [];
  let coreRe = null;
  // termSlugs — слаги, реально присутствующие в rules-terms версии. Глоссим ТОЛЬКО их: если у
  // версии нет карточки для терма (частичный глоссарий, напр. 5.1), span не создаётся — иначе
  // была бы «мёртвая» подсказка в пустой бакет. Для 5.2 набор полный → поведение не меняется.
  let termSlugs = null;
  const rtData = read('rules-terms');
  if (terms.length && rtData) {
    termSlugs = new Set(rtData.map((e) => e && e.slug).filter(Boolean));
    // В альтернацию берём только термы, у которых есть карточка (иначе матч → мёртвый span).
    const present = terms.filter((t) => termSlugs.has(t.slug));
    if (present.length) {
      const field = lang === 'en' ? 'en' : 'ru';
      const parts = present.map((t) => `(?<${grp(t.slug)}>${t[field]})`).join('|');
      const flags = lang === 'en' ? 'gu' : 'giu';
      coreRe = new RegExp(`(?<![\\p{L}\\p{N}_])(?:${parts})(?![\\p{L}\\p{N}_])`, flags);
    }
  }

  const res = actionRe || coreRe ? { actionRe, actionByName, coreRe, terms, termSlugs, verKey } : null;
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
      const slug = slugFromGroups(m.groups || {}, map.terms);
      if (!slug) continue;
      const end = m.index + m[0].length;
      // Гейт ярлыка стат-блока: терм — это ВЕСЬ узел «Термин:» (жирный ярлык вроде
      // «**Класс Доспеха:** 17», «**Показатель опасности:** 10»). В 5.1 стат-блоки пишут
      // термин словами (в 5.2 — аббревиатурой «КД»/«ПО»), из-за чего КД/ПО глоссились ковром
      // на каждой строке бестиария. Ярлык-определение — не место для подсказки; пропускаем.
      if (m.index === 0 && /^:\s*$/.test(value.slice(end))) continue;
      spans.push({ idx: m.index, end, term: m[0], slug, resource: 'rules-terms' });
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
