// Содержательный <meta description> для markdown-страниц (issue #213).
//
// Раньше страницы без кастомного описания получали чистый бойлерплейт:
// «Druid — Daggerheart SRD 1.0. Tabletop RPG System Reference Document in the OmnisGM
// ecosystem.» — 92–102 символа, из которых уникальны только первые три слова. Bing
// (Recommendations, правило 118 «Meta descriptions too short») держал на этом «умеренную»
// рекомендацию, а сниппет в выдаче и в AI-цитированиях не говорил о странице ничего.
//
// Здесь описание собирается ИЗ САМОЙ СТРАНИЦЫ, тремя ступенями по убыванию качества:
//   1. вводная проза — первый абзац после H1, до первого подзаголовка (есть у большинства глав);
//   2. структура — перечень подзаголовков (глава: разделы; справочник: термины) или, если
//      страница начинается таблицей, число строк и первые имена из неё;
//   3. бойлерплейт — как раньше (страница без прозы и без структуры; сборку не валим).
// Ступени комбинируются: если прозы не хватило до нижней границы, к ней добавляется
// структура, а если и её нет — брендовый хвост.
//
// Кастомные описания (классы D&D — class-facts.ts, сущностные страницы — свои шаблоны,
// #173/#185) сюда не заходят: вызывающий пробует их первыми.
//
// Длина: целимся в 110–160 символов (нижняя граница комфорта Bing — ~110, обрезка выдачи —
// ~160). Режем ТОЛЬКО по границе предложения или слова и никогда — посреди слова.

// Максимум и минимум для итоговой строки.
const MAX = 160;
const MIN = 110;
// Короче этого проза не считается вступлением (подпись автора, одна ремарка).
const MIN_PROSE = 40;

/**
 * Убрать из markdown то, что не является текстом страницы: html-блоки со стилями и
 * скриптами (лист персонажа BRP — целиком вёрстка с <style>), html-комментарии и
 * огороженный код. Без этого в сниппет уезжает CSS.
 */
function sanitize(md) {
  return (md ?? '')
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/^```[\s\S]*?^```/gm, '');
}

/** Плоский текст из строки markdown: разметка, ссылки, html и сноски — прочь. */
function plain(md) {
  return md
    .replace(/<[^>]+>/g, ' ') // html-теги
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ') // картинки
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1') // ссылки → текст
    .replace(/`+/g, '')
    .replace(/[*_]{1,3}/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

const isHeading = (line) => /^#{1,6}\s/.test(line);
const isTableRow = (line) => /^\s*\|/.test(line);
const isSeparator = (line) => /^\s*\|[\s:|-]+\|?\s*$/.test(line) && line.includes('-');
// «Не проза»: списки атрибутов, цитаты, разделители, остатки html.
const isProse = (line) =>
  line.trim() !== '' &&
  !isHeading(line) &&
  !isTableRow(line) &&
  !/^\s*([-*+]\s|\d+[.)]\s|>|---+|<)/.test(line);

/** Ячейки строки markdown-таблицы. */
const cells = (line) =>
  line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());

/**
 * Строки тела после заголовка H1 (сам H1 в сниппет не идёт — он уже в имени страницы).
 * Файла без единого заголовка это не касается: глоссарные справочники (14_Glossary/02_Spells.md)
 * начинаются прямо с таблицы, и «всё после H1» для них — это всё тело.
 */
function afterTitle(body) {
  const lines = sanitize(body).split('\n');
  const first = lines.findIndex(isHeading);
  return first < 0 ? lines : lines.slice(first + 1);
}

/**
 * ПЕРВЫЙ абзац вступления — тот, что стоит после H1 и до первого подзаголовка. Именно
 * вступление, а не «первый попавшийся абзац»: у страниц-справочников (Монстры А–Я,
 * глоссарии) первым абзацем идёт кусок первой же сущности («Large Aberration, Lawful
 * Evil»), и в сниппет он лезть не должен.
 *
 * Абзац именно один: на пустой строке после набранного текста выходим намеренно — в
 * сниппет всё равно влезает 110–160 символов, а склейка двух абзацев дала бы обрывок
 * второй мысли вместо целой первой. Break убирать не надо.
 */
export function introProse(body) {
  const out = [];
  for (const line of afterTitle(body)) {
    if (isHeading(line)) break;
    if (isProse(line)) out.push(plain(line));
    else if (out.length && line.trim() === '') break; // абзац кончился — хватит
  }
  return out.join(' ').trim();
}

/**
 * Подзаголовки страницы — как перечень того, что на ней есть. Уровень выбираем самый
 * населённый: у главы это разделы (##), у справочника — сами термины (#### в rules-glossary,
 * ### у монстров), а они для сниппета ценнее двух служебных «Соглашения / Определения».
 */
export function outline(body, limit = 14) {
  const byLevel = new Map([[2, []], [3, []], [4, []]]);
  const seen = new Set();
  for (const line of afterTitle(body)) {
    const m = /^(#{2,4})\s+(.+?)\s*$/.exec(line);
    if (!m) continue;
    const name = plain(m[2]).replace(/[:.]+$/, '');
    if (!name || seen.has(name)) continue;
    seen.add(name);
    byLevel.get(m[1].length).push(name);
  }
  let best = [];
  for (const level of [2, 3, 4]) {
    if (byLevel.get(level).length > best.length) best = byLevel.get(level);
  }
  return best.slice(0, limit);
}

/**
 * Сводка по таблице, с которой страница НАЧИНАЕТСЯ: сколько строк и что в первой колонке.
 * Для справочников без прозы и подзаголовков (глоссарные списки заклинаний, монстров,
 * магпредметов). Таблица где-то в середине страницы сюда не считается — иначе в сниппет
 * главы уезжает случайная таблица (у rules-glossary это была таблица сокращений).
 */
export function tableSummary(body, limit = 4) {
  const lines = afterTitle(body);
  let i = 0;
  while (i < lines.length && lines[i].trim() === '') i++;
  if (i >= lines.length || !isTableRow(lines[i])) return null;
  const names = [];
  let rows = 0;
  for (let j = i + 1; j < lines.length && isTableRow(lines[j]); j++) {
    if (isSeparator(lines[j])) continue;
    rows++;
    const first = plain(cells(lines[j])[0] ?? '');
    if (first && names.length < limit) names.push(first);
  }
  return rows ? { rows, names } : null;
}

/**
 * Перечень, влезающий в budget: элементы добавляются, пока помещаются. Обрезаем по границе
 * элемента, а не слова — «Aboleth, Ankheg, Assa…» в сниппете смотрелось бы поломкой.
 */
export function listFit(items, budget) {
  const out = [];
  for (const item of items) {
    const next = out.concat(item).join(', ');
    if (next.length + 1 > budget) break; // +1 — точка либо многоточие
    out.push(item);
  }
  if (!out.length) return '';
  return out.join(', ') + (out.length < items.length ? '…' : '.');
}

/** Обрезка до limit символов по границе предложения, иначе — по границе слова. */
export function clamp(text, limit = MAX) {
  const s = text.trim();
  if (s.length <= limit) return s;
  const head = s.slice(0, limit + 1);
  const sentence = Math.max(head.lastIndexOf('. '), head.lastIndexOf('! '), head.lastIndexOf('? '));
  // Предложение годится, только если после обрезки остаётся содержательный кусок.
  if (sentence >= Math.floor(limit * 0.6)) return s.slice(0, sentence + 1);
  const cut = s.slice(0, limit - 1);
  const space = cut.lastIndexOf(' ');
  return (space > 0 ? cut.slice(0, space) : cut).replace(/[\s,;:—–-]+$/, '') + '…';
}

/**
 * Описание markdown-страницы: 110–160 символов (короче — только если страница пуста
 * настолько, что не набралось даже с хвостом).
 *
 * name — подпись страницы, sysLabel/docLabel — система и документ («Daggerheart», «SRD 1.0»).
 */
export function pageDescription({ name, body, lang, sysLabel, docLabel }) {
  const ru = lang !== 'en';
  const head = ru ? `${name} — ${sysLabel} ${docLabel} на русском` : `${name} — ${sysLabel} ${docLabel}`;
  const tail = ru
    ? 'SRD настольных ролевых игр в экосистеме OmnisGM.'
    : 'Tabletop RPG System Reference Document in the OmnisGM ecosystem.';
  // Укороченный хвост — когда полный не влезает в 160 (страница с одной фразой вступления).
  const shortTail = ru ? 'SRD настольных игр в экосистеме OmnisGM.' : 'Tabletop RPG SRD in the OmnisGM ecosystem.';
  const fill = (s) => {
    for (const t of [tail, shortTail]) if (s.length + 1 + t.length <= MAX) return `${s} ${t}`;
    return s;
  };

  // Ступень 1 — вводная проза (после точки: «Друид — Daggerheart SRD 1.0. Стать друидом…»).
  const prose = introProse(body);
  if (prose.length >= MIN_PROSE) {
    const budget = MAX - head.length - 2;
    let out = `${head}. ${clamp(prose.replace(/:$/, '.'), budget)}`;
    if (out.length >= MIN) return out;
    // Проза короткая — добираем до нижней границы структурой, а если её нет — хвостом.
    const items = outline(body);
    const rest = MAX - out.length - 1;
    if (items.length >= 2) {
      const list = listFit(items, rest);
      if (list && out.length + 1 + list.length >= MIN) return `${out} ${list}`;
    }
    return fill(out);
  }

  // Ступень 2 — структура: подзаголовки, а если их нет — таблица, с которой страница начата.
  // Перечень идёт через двоеточие: «Rules Glossary — D&D SRD 5.2.1: Ability Check, Action…».
  const budget = MAX - head.length - 2;
  const items = outline(body);
  let content = items.length >= 2 ? listFit(items, budget) : '';
  if (!content) {
    const t = tableSummary(body);
    if (t) {
      const label = ru ? `${t.rows} записей — ` : `${t.rows} entries — `;
      content = clamp(label + t.names.join(', ') + '.', budget);
    }
  }

  // Ступень 3 — бойлерплейт как раньше.
  if (!content) return `${head}. ${tail}`;

  const out = `${head}: ${content}`;
  return out.length < MIN ? fill(out) : out;
}
