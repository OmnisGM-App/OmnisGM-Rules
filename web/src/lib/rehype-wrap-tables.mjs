// Оборачивает каждую <table> в <div class="rd-table-wrap"> с overflow-x:auto, чтобы широкая
// таблица скроллилась внутри себя (а не растягивала/скроллила всю страницу). Ручной обход —
// как rehype-promote-headings, без доп. зависимостей.
export default function rehypeWrapTables() {
  return (tree) => {
    const walk = (node) => {
      if (!node || !node.children) return;
      for (let i = 0; i < node.children.length; i++) {
        const child = node.children[i];
        if (child.type === 'element' && child.tagName === 'table') {
          node.children[i] = {
            type: 'element',
            tagName: 'div',
            // tabindex=0 — чтобы скроллящуюся по горизонтали обёртку можно было прокрутить
            // с клавиатуры (иначе axe scrollable-region-focusable: контент недостижим без мыши).
            properties: { className: ['rd-table-wrap'], tabIndex: 0 },
            children: [child],
          };
          walk(child); // вложенные таблицы (редко)
        } else {
          walk(child);
        }
      }
    };
    walk(tree);
  };
}
