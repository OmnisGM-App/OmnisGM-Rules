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

const SKIP_TAGS = new Set(['a', 'code', 'pre', 'kbd', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']);

// Формы характеристик (RU — по падежам; EN — одна форма). Заглавная обязательна.
const ABILITIES = {
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

// Названия навыков (именительный — как в скобках и в статблоке). Длинные раньше коротких,
// чтобы «Ловкость рук» победила «Ловкость».
const SKILLS = {
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

// Контекст-слова, легитимирующие подсветку навыка (если он не в скобках).
const SKILL_CTX = {
  ru: /(?:навык\w*|владе\w+|проверк\w+|спасброс\w+|Навыки)\s*$/u,
  en: /(?:proficiency|proficient|check|save|saving throw|skill|Skills|\bin)\s*$/iu,
};

const escapeRegExp = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const cache = new Map(); // lang → { re, abil:Set, skill:Set, ctx }

function build(lang) {
  if (cache.has(lang)) return cache.get(lang);
  const abil = ABILITIES[lang] || [];
  const skill = SKILLS[lang] || [];
  if (!abil.length && !skill.length) { cache.set(lang, null); return null; }
  // Длинные формы раньше коротких (в альтернации побеждает первый матч).
  const all = [...abil, ...skill].sort((a, b) => b.length - a.length);
  const alt = all.map(escapeRegExp).join('|');
  const re = new RegExp(`(?<![\\p{L}\\p{N}_])(${alt})(?![\\p{L}\\p{N}_])`, 'gu');
  const res = { re, abil: new Set(abil), skill: new Set(skill), ctx: SKILL_CTX[lang] };
  cache.set(lang, res);
  return res;
}

function spanNode(text) {
  return { type: 'element', tagName: 'span', properties: { className: ['kw'] }, children: [{ type: 'text', value: text }] };
}

function highlightText(value, m) {
  m.re.lastIndex = 0;
  const nodes = [];
  let last = 0;
  let changed = false;
  let match;
  while ((match = m.re.exec(value))) {
    const term = match[1];
    const idx = match.index;
    if (m.skill.has(term)) {
      // Навык — только в игромеханическом контексте: «(Навык)» или после контекст-слова.
      const before = value.slice(0, idx);
      const inParen = /[(,]\s*$/.test(before);
      if (!inParen && !m.ctx.test(before)) continue;
    }
    changed = true;
    if (idx > last) nodes.push({ type: 'text', value: value.slice(last, idx) });
    nodes.push(spanNode(term));
    last = idx + term.length;
  }
  if (!changed) return null;
  if (last < value.length) nodes.push({ type: 'text', value: value.slice(last) });
  return nodes;
}

// Ядро: подсвечивает ключевые слова прямо в hast-дереве.
export function highlightKeywords(tree, { lang }) {
  const m = build(lang);
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

// rehype-обёртка: подсветка ТОЛЬКО в главе классов (умения классов). Остальные главы
// (Как играть, Глоссарий) — определения терминов, там подсветка была бы шумом.
export default function rehypeKeywordHighlight() {
  return (tree, file) => {
    const p = (file && (file.path || (file.history && file.history[0]))) || '';
    const norm = p.replace(/\\/g, '/');
    if (!/\/03_Classes\//.test(norm)) return;
    const m = norm.match(/\/(dnd|daggerheart|brp)\/[^/]+\/(en|ru)\//);
    if (!m) return;
    highlightKeywords(tree, { lang: m[2] });
  };
}
