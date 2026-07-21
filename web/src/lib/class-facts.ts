// Извлечение фактов класса из markdown-тела для содержательного <meta description>
// класс-страниц (issue #173, п.1). Класс-страницы рендерит catch-all [...slug].astro, где
// раньше был бойлерплейт «{Имя} — D&D SRD 5.2.1 на русском…» на самом крупном кластере
// спроса («плут днд»: 513 запросов). Здесь тянем умения 1-го уровня прямо из таблицы
// прогрессии класса — они уже локализованы в контенте, так что перевод не дублируется и
// не дрейфует. Версия таблиц 5.1 и 5.2 разъехалась (в 5.1 колонка умений последняя, в 5.2 —
// третья), поэтому колонку ищем по заголовку, а не по фикс-индексу.

// Разбить строку markdown-таблицы в ячейки (без ведущего/замыкающего «|»).
function cells(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((c) => c.trim());
}

const isTableRow = (line: string) => /^\s*\|/.test(line);
// Строка-разделитель шапки: «|---|:--:|…».
const isSeparator = (line: string) => /^\s*\|[\s:|-]+\|?\s*$/.test(line) && line.includes('-');

// Первая ячейка строки-заголовка таблицы прогрессии («Уровень»/«Level»).
const isLevelHeader = (c: string) => /^(уровень|level)$/i.test(c);
// Заголовок колонки умений: «Классовые умения»/«Умения»/«Class Features»/«Features».
const isFeatureHeader = (c: string) => /умен|features?/i.test(c);
// Ячейка уровня, равная 1 (учитываем «1», «1st», «1-й», «1-го»). «10»/«11» не ловим.
const isLevelOne = (c: string) => /^1(\D|$)/.test(c.replace(/\s+/g, ''));

/**
 * Умения 1-го уровня класса из таблицы прогрессии (напр. ['Экспертиза', 'Скрытая атака',
 * 'Воровской жаргон']). Пустой массив, если таблицу/строку не нашли (описание деградирует
 * к бойлерплейту — сборку это не валит).
 */
export function level1Features(body: string | undefined, limit = 3): string[] {
  if (!body) return [];
  const lines = body.split('\n');
  for (let i = 0; i < lines.length; i++) {
    if (!isTableRow(lines[i])) continue;
    const header = cells(lines[i]);
    if (!isLevelHeader(header[0] ?? '')) continue;
    const featCol = header.findIndex(isFeatureHeader);
    if (featCol < 0) continue;

    // Идём по строкам данных этой таблицы до её конца; берём строку уровня 1.
    for (let j = i + 1; j < lines.length && isTableRow(lines[j]); j++) {
      if (isSeparator(lines[j])) continue;
      const row = cells(lines[j]);
      if (!isLevelOne(row[0] ?? '')) continue;
      return (row[featCol] ?? '')
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
        .slice(0, limit);
    }
  }
  return [];
}

// Слаг версии → издание для сниппета: 5.2 = «D&D 2024», 5.1 = «D&D 2014». Кириллическая
// форма «(днд)» — частотное написание запросов (issue #173, п.2), одна встреча, не стаффинг.
const EDITION: Record<string, string> = { 'srd-5.2': '2024', 'srd-5.1': '2014' };

/**
 * Содержательный <meta description> класс-страницы. null, если умений не извлекли —
 * вызывающий откатывается к бойлерплейту. verLabel — метка версии из nav («SRD 5.2.1»).
 */
export function classDescription(opts: {
  name: string;
  body: string | undefined;
  lang: 'en' | 'ru';
  version: string;
  verLabel: string;
}): string | null {
  const { name, body, lang, version, verLabel } = opts;
  const feats = level1Features(body);
  if (feats.length === 0) return null;

  const ed = EDITION[version];
  const compose = (n: number) => {
    const list = feats.slice(0, n).join(', ');
    return lang === 'ru'
      ? `${name} — класс D&D${ed ? ` ${ed}` : ''} (днд): ${list}. Умения по уровням 1–20, подклассы. Полные правила ${verLabel} на русском.`
      : `${name} — a D&D${ed ? ` ${ed}` : ''} class: ${list}. Features by level 1–20 with subclasses. Full ${verLabel} rules.`;
  };

  // Держим сниппет в пределах ~160 символов: при переполнении срезаем до 2 умений.
  let out = compose(3);
  if (out.length > 160 && feats.length > 2) out = compose(2);
  return out;
}
