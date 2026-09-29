// Оборачивает каждую <table> в <div class="rd-table-wrap"> с overflow-x:auto, чтобы широкая
// таблица скроллилась внутри себя (а не растягивала/скроллила всю страницу).
export default function rehypeWrapTables() {
  return (/** @type {import('hast').Root} */ tree) => {
    const walk = (/** @type {import('hast').Nodes} */ node) => {
      if (!node || !('children' in node)) return;
      for (let i = 0; i < node.children.length; i++) {
        const child = node.children[i];
        if (child.type === 'element' && child.tagName === 'table') {
          node.children[i] = {
            type: 'element',
            tagName: 'div',
            // tabindex=0 — прокрутка с клавиатуры (axe scrollable-region-focusable).
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
