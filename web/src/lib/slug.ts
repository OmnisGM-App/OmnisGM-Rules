// Пути контента: id коллекции = "<game>/<version>/<lang>/<...slug>" (из имени файла, без frontmatter).
// Напр. "dnd/srd-5.2/en/03_Classes/01_Barbarian". Отсюда строим SEO-дружелюбные URL.

export interface ContentRef {
  game: string;      // dnd | daggerheart | brp
  version: string;   // srd-5.2 | srd-5.1 | srd-1.0
  lang: 'en' | 'ru';
  slug: string;      // kebab-путь без числовых префиксов: "classes/barbarian"
  order: string;     // исходный путь с префиксами для сортировки: "03_classes/01_barbarian"
  id: string;        // исходный id коллекции
}

// "01_PlayingTheGame" → "playing-the-game"; "12_MonstersA-Z" → "monsters-a-z"; "00_Legal" → "legal"
export function slugifySegment(seg: string): string {
  return seg
    .replace(/^\d+[_-]/, '')           // числовой префикс-порядок
    .replace(/([a-z0-9])([A-Z])/g, '$1-$2') // camelCase → camel-Case
    .replace(/[_\s]+/g, '-')
    .replace(/-+/g, '-')
    .toLowerCase()
    .replace(/^-+|-+$/g, '');
}

// Разобрать id коллекции в структурную ссылку
export function parseId(id: string): ContentRef {
  const parts = id.split('/');
  const [game, version, lang, ...rest] = parts;
  const slug = rest.map(slugifySegment).join('/');
  const order = rest.map((s) => s.toLowerCase()).join('/');
  return { game, version, lang: lang as 'en' | 'ru', slug, order, id };
}

// URL страницы: /{lang}/{game}/{version}/{slug}
export function pageUrl(ref: ContentRef): string {
  return `/${ref.lang}/${ref.game}/${ref.version}/${ref.slug}`;
}

// Заголовок страницы из первой строки Markdown (# H1), т.к. frontmatter нет
export function titleFromBody(body: string | undefined): string {
  if (!body) return '';
  // Заголовок любого уровня: топ-страницы начинаются с "# H1", файлы классов — с "## H2".
  const m = body.match(/^\s*#{1,6}\s+(.+?)\s*$/m);
  return m ? m[1].replace(/\s*#+\s*$/, '').trim() : '';
}
