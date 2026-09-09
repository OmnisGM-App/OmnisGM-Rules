// Оборачивает каждую <table> в <div class="rd-table-wrap"> с overflow-x:auto, чтобы широкая
// таблица скроллилась внутри себя (а не растягивала/скроллила всю страницу). Ручной обход —
// как rehype-promote-headings, без доп. зависимостей.
export default function rehypeWrapTables() {
  return (/** @type {import('hast').Root} */ tree) => {
    // Типы hast, а не `any`: ровно в этих файлах `any` не проверял НИЧЕГО — опечатка
    // `child.tagNme` проходила молча, и обёртка просто переставала применяться на части
    // из 6000 страниц (ревью #315). `@types/hast` уже в devDependencies.
    // Узел любой: у текстового нет `children`, и обход обязан спокойно на нём кончаться.
    const walk = (/** @type {import('hast').Nodes} */ node) => {
      if (!node || !('children' in node)) return;
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
