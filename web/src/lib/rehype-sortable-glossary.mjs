// Делает markdown-таблицы глав ГЛОССАРИЯ сортируемыми (issue #20): помечает каждую <table>
// атрибутом data-sortable. Тот же общий sort-скрипт в ReaderShell (клик по <th>) подхватывает
// любую table[data-sortable] — и наши хаб-таблицы, и эти markdown-таблицы (оружие/броня/
// предметы/расходники DH, оружие/броня BRP, списки терминов 5.1 и т.п.).
//
// Гейт — только главы глоссария (NN_Glossary/*): там таблицы-справочники, сортировка полезна.
// Прочие главы (проза) не трогаем — их редкие таблицы обычно не для сортировки.
const GLOSSARY = /\/\d+_Glossary\//;
// Порог строк-данных: крошечные таблицы (аббревиатуры, 1–2 строки) сортировать бессмысленно —
// не вешаем на них role=button/стрелки. ≥3 строки → сортируемая.
const MIN_ROWS = 3;

// Число строк-данных таблицы (<tr> внутри <tbody>; при отсутствии tbody — все <tr> минус шапка).
function dataRowCount(table) {
  const rows = [];
  const collect = (n) => {
    for (const c of n.children || []) {
      if (c.type !== 'element') continue;
      if (c.tagName === 'tr') rows.push(c);
      else collect(c);
    }
  };
  const tbody = (table.children || []).find((c) => c.type === 'element' && c.tagName === 'tbody');
  if (tbody) { collect(tbody); return rows.length; }
  collect(table);
  return Math.max(0, rows.length - 1); // без <tbody> первая строка — шапка
}

export default function rehypeSortableGlossary() {
  return (tree, file) => {
    const p = (file && (file.path || (file.history && file.history[0]))) || '';
    if (!GLOSSARY.test(p.replace(/\\/g, '/'))) return;
    const walk = (node) => {
      if (!node || !node.children) return;
      for (const child of node.children) {
        if (child.type === 'element' && child.tagName === 'table' && dataRowCount(child) >= MIN_ROWS) {
          child.properties = child.properties || {};
          child.properties['data-sortable'] = '';
        }
        walk(child);
      }
    };
    walk(tree);
  };
}
