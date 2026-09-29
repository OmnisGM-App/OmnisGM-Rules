// Нормализует уровни заголовков: если на странице нет h1 (файлы SRD-классов начинаются с ## —
// их вырезали из секции под общим "# Classes"), поднимает ВСЕ заголовки так, чтобы минимальный
// стал h1.
export default function rehypePromoteHeadings() {
  return (/** @type {import('hast').Root} */ tree) => {
    /** @type {import('hast').Element[]} */
    const headings = [];
    const walk = (/** @type {import('hast').Nodes} */ node) => {
      if (!node) return;
      if (node.type === 'element' && /^h[1-6]$/.test(node.tagName)) headings.push(node);
      if ('children' in node) for (const child of node.children) walk(child);
    };
    walk(tree);
    if (!headings.length) return;
    const min = Math.min(...headings.map((h) => Number(h.tagName[1])));
    if (min <= 1) return;
    const shift = min - 1;
    for (const h of headings) {
      const lvl = Number(h.tagName[1]);
      h.tagName = 'h' + Math.max(1, lvl - shift);
    }
  };
}
