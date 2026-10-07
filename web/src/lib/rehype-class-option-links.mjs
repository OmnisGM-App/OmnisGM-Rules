// Глава класса SRD 5.2 → страница группы вариантов (#379): под заголовком умения «Level N: <имя>»,
// у которого есть варианты (`class-options`), — ссылка «все варианты на одной странице».
import fs from 'node:fs';
import path from 'node:path';

const DATA_ROOT = path.resolve(process.cwd(), 'src/data/api');
const CHAPTER = /\/dnd\/srd-5\.2\/(en|ru)\/03_Classes\/\d+_(\w+)\.md$/;
const FEATURE_HEADING = /^(?:Level|Уровень) \d+: (.+)$/;
/** @type {Record<'en' | 'ru', (name: string) => string>} */
const LINK_TEXT = { en: (name) => `All ${name} options on one page →`, ru: (name) => `Все варианты «${name}» на одной странице →` };

// Сборка заменяет апостроф типографским («Hunter’s Prey»), в данных он прямой.
const norm = (/** @type {string} */ s) => s.replace(/[’‘]/g, "'").trim();

/** @type {Map<string, Map<string, { key: string, classes: Set<string> }>>} язык → имя умения → группа */
const byLang = new Map();
function groupsByName(/** @type {string} */ lang) {
  let map = byLang.get(lang);
  if (!map) {
    map = new Map();
    const file = path.join(DATA_ROOT, 'dnd', 'srd52', lang, 'class-options', 'all.json');
    const options = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : [];
    for (const o of options) {
      const name = norm(o.feature.name);
      const group = map.get(name) ?? { key: o.feature.key, classes: new Set() };
      group.classes.add(o.class);
      map.set(name, group);
    }
    byLang.set(lang, map);
  }
  return map;
}

const textOf = (/** @type {any} */ node) =>
  node.type === 'text' ? node.value : (node.children ?? []).map(textOf).join('');

/** Вставляет ссылки в дерево главы; экспорт — для юнита. */
export function linkClassOptionGroups(/** @type {any} */ tree, /** @type {'en' | 'ru'} */ lang, /** @type {string} */ classSlug) {
  const groups = groupsByName(lang);
  const done = new Set();
  const walk = (/** @type {any} */ parent) => {
    const kids = parent.children ?? [];
    for (let i = 0; i < kids.length; i++) {
      const node = kids[i];
      if (node.type === 'element' && /^h[2-6]$/.test(node.tagName)) {
        const name = FEATURE_HEADING.exec(norm(textOf(node)))?.[1];
        const group = name ? groups.get(name) : undefined;
        // Одноимённое умение другого класса (боевой стиль воина — черты) на чужую группу не ведёт.
        const key = group?.classes.has(classSlug) ? group.key : undefined;
        if (name && key && !done.has(key)) {
          done.add(key);
          kids.splice(i + 1, 0, {
            type: 'element', tagName: 'p', properties: { className: ['class-option-link'] },
            children: [{
              type: 'element', tagName: 'a', properties: { href: `/${lang}/dnd/srd-5.2/class-options/${key}/` },
              children: [{ type: 'text', value: LINK_TEXT[lang](name) }],
            }],
          });
          i++;
        }
      } else if (node.children) walk(node);
    }
  };
  walk(tree);
}

export default function rehypeClassOptionLinks() {
  return (/** @type {any} */ tree, /** @type {any} */ file) => {
    const p = ((file && (file.path || (file.history && file.history[0]))) || '').replace(/\\/g, '/');
    const m = CHAPTER.exec(p);
    if (m) linkClassOptionGroups(tree, /** @type {'en' | 'ru'} */ (m[1]), m[2].toLowerCase());
  };
}
