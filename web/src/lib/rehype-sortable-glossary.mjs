// Делает markdown-таблицы глав ГЛОССАРИЯ сортируемыми (issue #20): помечает каждую <table>
// атрибутом data-sortable. Тот же общий sort-скрипт в ReaderShell (клик по <th>) подхватывает
// любую table[data-sortable] — и наши хаб-таблицы, и эти markdown-таблицы (оружие/броня/
// предметы/расходники DH, оружие/броня BRP, списки терминов 5.1 и т.п.).
//
// Гейт — только главы глоссария (NN_Glossary/*): там таблицы-справочники, сортировка полезна.
// Прочие главы (проза) не трогаем — их редкие таблицы обычно не для сортировки.
const GLOSSARY = /\/\d+_Glossary\//;

export default function rehypeSortableGlossary() {
  return (tree, file) => {
    const p = (file && (file.path || (file.history && file.history[0]))) || '';
    if (!GLOSSARY.test(p.replace(/\\/g, '/'))) return;
    const walk = (node) => {
      if (!node || !node.children) return;
      for (const child of node.children) {
        if (child.type === 'element' && child.tagName === 'table') {
          child.properties = child.properties || {};
          child.properties['data-sortable'] = '';
        }
        walk(child);
      }
    };
    walk(tree);
  };
}
