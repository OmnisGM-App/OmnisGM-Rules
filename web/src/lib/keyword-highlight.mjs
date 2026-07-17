// Подсветка ключевых игромеханических слов (issue #20): характеристики, навыки и спасброски
// в тексте получают бренд-цвет (span.kw). Это НЕ ссылка и НЕ hovercard — только визуальный
// акцент, чтобы читатель выхватывал механику («спасбросок Ловкости», «проверка Мудрости
// (Внимательность)»). Ручной обход hast-дерева, без зависимостей.
//
// Точность важнее полноты:
//  • Характеристики — по всем падежным формам, но только с Заглавной (строчное «сила» —
//    обычное слово, не трогаем).
//  • Навыки — многие названия омонимичны обычным словам (История, Природа, Магия, Медицина),
//    поэтому подсвечиваем ТОЛЬКО в игромеханическом контексте: в скобках «(Внимательность)»,
//    в строке статблока «Навыки …», после «навык…/владени…/проверк…».
//
// Применяется точечно: страницы заклинаний и монстров (в их render()), глава классов
// (rehype с гейтом на /03_Classes/). НЕ на главах-определениях (Как играть, Глоссарий),
// где термины встречаются сплошь и подсветка стала бы ковром.

import fs from 'node:fs';
import path from 'node:path';

const SKIP_TAGS = new Set(['a', 'code', 'pre', 'kbd', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']);
const DATA_ROOT = path.resolve(process.cwd(), 'src/data/api');

// Per-game термсеты (issue #20): у каждой системы свои «ключевые» механические слова.
// В каждом наборе `abil` — подсвечиваем всегда при Заглавной (дистинктивны); `skill` — только
// в игромеханическом контексте (омонимы обычных слов).

// --- D&D (5.2/5.1): 6 характеристик (по падежам RU) ---
const DND_ABIL = {
  ru: [
    'Сила', 'Силы', 'Силе', 'Силу', 'Силой', 'Силою',
    'Ловкость', 'Ловкости', 'Ловкостью',
    'Телосложение', 'Телосложения', 'Телосложению', 'Телосложением',
    'Интеллект', 'Интеллекта', 'Интеллекту', 'Интеллектом', 'Интеллекте',
    'Мудрость', 'Мудрости', 'Мудростью',
    'Харизма', 'Харизмы', 'Харизме', 'Харизму', 'Харизмой', 'Харизмою',
  ],
  en: ['Strength', 'Dexterity', 'Constitution', 'Intelligence', 'Wisdom', 'Charisma'],
};
// Навыки D&D (именительный — как в скобках и в статблоке). Длинные раньше коротких.
const DND_SKILL = {
  ru: [
    'Уход за животными', 'Ловкость рук', 'Проницательность', 'Внимательность',
    'Выступление', 'Запугивание', 'Скрытность', 'Убеждение', 'Выживание',
    'Акробатика', 'Атлетика', 'История', 'Медицина', 'Природа', 'Религия',
    'Анализ', 'Магия', 'Обман',
  ],
  en: [
    'Animal Handling', 'Sleight of Hand', 'Investigation', 'Intimidation',
    'Perception', 'Persuasion', 'Performance', 'Acrobatics', 'Athletics',
    'Deception', 'Medicine', 'Religion', 'Survival', 'History', 'Insight',
    'Arcana', 'Nature', 'Stealth',
  ],
};

// --- Daggerheart: 6 черт (по падежам RU). Всегда подсвечиваем — дистинктивны в правилах DH. ---
const DH_ABIL = {
  ru: [
    'Проворство', 'Проворства', 'Проворству', 'Проворством',
    'Точность', 'Точности', 'Точностью',
    'Инстинкт', 'Инстинкта', 'Инстинкту', 'Инстинктом',
    'Обаяние', 'Обаяния', 'Обаянию', 'Обаянием',
    'Знание', 'Знания', 'Знанию', 'Знанием',
    'Сила', 'Силы', 'Силе', 'Силу', 'Силой', 'Силою',
  ],
  en: ['Agility', 'Strength', 'Finesse', 'Instinct', 'Presence', 'Knowledge'],
};

// --- BRP: аббревиатуры характеристик — всегда (жаргон, дистинктивны); полные имена — в контексте. ---
const BRP_ABIL = {
  ru: ['СИЛ', 'ВЫН', 'РАЗ', 'ИНТ', 'ВОЛ', 'ЛОВ', 'ВНШ'],
  en: ['STR', 'CON', 'SIZ', 'INT', 'POW', 'DEX', 'APP'],
};
const BRP_CHAR_FULL = {
  ru: ['Выносливость', 'Внешность', 'Интеллект', 'Ловкость', 'Размер', 'Сила', 'Воля'],
  en: ['Constitution', 'Intelligence', 'Appearance', 'Dexterity', 'Strength', 'Power', 'Size'],
};

// Навыки BRP (56) омонимичны обычным словам (Лазание, Драка) → грузим из данных, подсвечиваем
// ТОЛЬКО в контексте (как навыки D&D). Ленивая загрузка + кэш по языку.
const brpSkillCache = new Map();
function brpSkills(lang) {
  if (brpSkillCache.has(lang)) return brpSkillCache.get(lang);
  let names = [];
  try {
    const data = JSON.parse(fs.readFileSync(path.join(DATA_ROOT, 'brp', 'srd10', lang, 'skills', 'all.json'), 'utf8'));
    names = data.map((s) => String(s.name || '').replace(/\s*\([^)]*\)\s*$/, '').trim()).filter(Boolean);
  } catch { names = []; }
  brpSkillCache.set(lang, names);
  return names;
}

// Термсет по игре: { abil, skill } на язык. abil — всегда; skill — в контексте.
function gameTerms(game, lang) {
  if (game === 'daggerheart') return { abil: DH_ABIL[lang] || [], skill: [] };
  if (game === 'brp') return { abil: BRP_ABIL[lang] || [], skill: [...(BRP_CHAR_FULL[lang] || []), ...brpSkills(lang)] };
  return { abil: DND_ABIL[lang] || [], skill: DND_SKILL[lang] || [] };
}

// Контекст-слова, легитимирующие подсветку навыка/характеристики (если не в скобках). Общие.
const SKILL_CTX = {
  ru: /(?:навык\w*|владе\w+|проверк\w+|спасброс\w+|характеристик\w*|Навыки)\s*$/u,
  en: /(?:proficiency|proficient|check|save|saving throw|skill|characteristic|roll|Skills|\bin)\s*$/iu,
};

// Разделитель списка навыков: запятая и/или союз («A, B, or C», «A, B … или F»). Если два
// соседних навыка разделены только им — они члены одного перечисления. Пустой зазор (только
// пробел) НЕ считается разделителем — иначе слиплись бы случайные соседние слова.
const SKILL_LIST_SEP = /^\s*(?:,\s*(?:или|и|or|and)?|(?:или|и|or|and))\s*$/iu;

const escapeRegExp = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const cache = new Map(); // `${game}/${lang}` → { re, abil:Set, skill:Set, ctx }

function build(game, lang) {
  const cacheKey = `${game}/${lang}`;
  if (cache.has(cacheKey)) return cache.get(cacheKey);
  const { abil, skill } = gameTerms(game, lang);
  if (!abil.length && !skill.length) { cache.set(cacheKey, null); return null; }
  // Длинные формы раньше коротких (в альтернации побеждает первый матч).
  const all = [...abil, ...skill].sort((a, b) => b.length - a.length);
  const alt = all.map(escapeRegExp).join('|');
  const re = new RegExp(`(?<![\\p{L}\\p{N}_])(${alt})(?![\\p{L}\\p{N}_])`, 'gu');
  const res = { re, abil: new Set(abil), skill: new Set(skill), ctx: SKILL_CTX[lang] };
  cache.set(cacheKey, res);
  return res;
}

function spanNode(text) {
  return { type: 'element', tagName: 'span', properties: { className: ['kw'] }, children: [{ type: 'text', value: text }] };
}

function highlightText(value, m) {
  m.re.lastIndex = 0;
  const matches = [];
  let match;
  while ((match = m.re.exec(value))) {
    matches.push({
      term: match[1], idx: match.index, end: match.index + match[1].length,
      skill: m.skill.has(match[1]),
    });
  }
  if (!matches.length) return null;

  // Индивидуальная легитимность навыка: «(Навык)» / после запятой или контекст-слова.
  // Характеристики подсвечиваем всегда (заглавная форма уже отсеяла обычные слова).
  const decide = matches.map((mt) => {
    if (!mt.skill) return true;
    const before = value.slice(0, mt.idx);
    return /[(,]\s*$/.test(before) || m.ctx.test(before);
  });

  // Список навыков — единая группа: соседние навыки, разделённые только запятой/союзом,
  // связаны. Если хоть один член легитимен, подсвечиваем весь список (иначе первый после
  // «Выберите N:» и последний после «или» выпадали — issue #20). Прямой проход тянет «ок»
  // вперёд по цепочке, обратный — назад; для непрерывного списка этого достаточно.
  const linked = (a, b) => a.skill && b.skill && SKILL_LIST_SEP.test(value.slice(a.end, b.idx));
  for (let i = 1; i < matches.length; i++)
    if (decide[i - 1] && linked(matches[i - 1], matches[i])) decide[i] = true;
  for (let i = matches.length - 2; i >= 0; i--)
    if (decide[i + 1] && linked(matches[i], matches[i + 1])) decide[i] = true;

  const nodes = [];
  let last = 0;
  let changed = false;
  for (let i = 0; i < matches.length; i++) {
    if (!decide[i]) continue;
    const mt = matches[i];
    changed = true;
    if (mt.idx > last) nodes.push({ type: 'text', value: value.slice(last, mt.idx) });
    nodes.push(spanNode(mt.term));
    last = mt.end;
  }
  if (!changed) return null;
  if (last < value.length) nodes.push({ type: 'text', value: value.slice(last) });
  return nodes;
}

// Ядро: подсвечивает ключевые слова прямо в hast-дереве. game — термсет системы (по умолчанию dnd).
export function highlightKeywords(tree, { lang, game = 'dnd' }) {
  const m = build(game, lang);
  if (!m) return tree;
  const walk = (node, insideSkip) => {
    if (!node.children) return;
    for (let i = 0; i < node.children.length; i++) {
      const child = node.children[i];
      if (child.type === 'element') {
        walk(child, insideSkip || SKIP_TAGS.has(child.tagName));
      } else if (child.type === 'text' && !insideSkip) {
        const replaced = highlightText(child.value, m);
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

// Главы прозы, где подсветка уместна (классы/создание персонажа — там механику обсуждают явно).
// Остальные главы (Как играть, Глоссарий) — сплошные определения → подсветка была бы ковром.
//  • dnd: классы 5.2 (03_Classes) и 5.1 (06_Classes).
//  • daggerheart: классы (04_Classes) — там черты в описаниях.
//  • brp: НЕ гейтим главы. Единственная характеристико-/навыко-плотная глава (02_CharacterCreation)
//    — это по сути полный список навыков → подсветка там стала бы ковром (200+). BRP-подсветка
//    остаётся на entity-страницах (навык/профессия/точечное правило), где она контекстна.
const PROSE_GATE = {
  dnd: /\/(03_Classes|06_Classes)\//,
  daggerheart: /\/04_Classes\//,
};

// rehype-обёртка: подсветка ТОЛЬКО в разрешённых главах системы (PROSE_GATE).
export default function rehypeKeywordHighlight() {
  return (tree, file) => {
    const p = (file && (file.path || (file.history && file.history[0]))) || '';
    const norm = p.replace(/\\/g, '/');
    const m = norm.match(/\/(dnd|daggerheart|brp)\/[^/]+\/(en|ru)\//);
    if (!m) return;
    const [, game, lang] = m;
    const gate = PROSE_GATE[game];
    if (!gate || !gate.test(norm)) return;
    highlightKeywords(tree, { lang, game });
  };
}
