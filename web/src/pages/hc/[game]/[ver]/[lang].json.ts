import type { APIRoute } from 'astro';
import { loadEntities, VERSION_SLUG } from '../../../../lib/entities';

const escapeHtml = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// Эффект состояния → компактный форматированный HTML для карточки.
// Выкидываем вводную «Пока вы находитесь в состоянии …» / «While you have the … condition» —
// имя состояния уже в заголовке карточки. Жирные ярлыки подэффектов сохраняем.
function effectHtml(md: string | undefined): string {
  if (!md) return '';
  const blocks = md.split(/\n{2,}/).map((b) => b.trim()).filter(Boolean);
  const isIntro = (b: string) => /^(Пока вы находитесь в состоянии|While you have the .* condition)/.test(b);
  const body = blocks.length > 1 && isIntro(blocks[0]) ? blocks.slice(1) : blocks;
  return body
    .map((b) => {
      const html = escapeHtml(b)
        .replace(/\*\*_([^*]+?)_\*\*/g, '<strong>$1</strong>') // bold-italic ярлык
        .replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>')
        .replace(/(?<![\w*])_([^_]+?)_(?![\w*])/g, '<em>$1</em>')
        .replace(/(?<![\w*])\*([^*]+?)\*(?![\w*])/g, '<em>$1</em>');
      return `<p>${html}</p>`;
    })
    .join('');
}

// Hovercard-данные для автоссылок (issue #20, вариант B: fetch-on-hover served JSON).
// На каждый бакет `game/verKey/lang` отдаём карту `resource/slug` → { name, name_en, excerpt, href }.
// Ключ бакета совпадает с префиксом `data-hc` из rehype-entity-autolink (game/verKey/lang/...).
// Бакеты собираем только там, где реально существуют страницы сущностей (см. [slug].astro).

const RESOURCES = [{ key: 'conditions', urlParent: 'rules-glossary/conditions' }];

// Согласовано со сборкой страниц состояний: пока только srd52 (en/ru).
const BUILDS = [
  { game: 'dnd', ver: 'srd52', lang: 'en' },
  { game: 'dnd', ver: 'srd52', lang: 'ru' },
];

export function getStaticPaths() {
  return BUILDS.map((b) => ({ params: { game: b.game, ver: b.ver, lang: b.lang } }));
}

export const GET: APIRoute = ({ params }) => {
  const { ver, lang, game } = params as { game: string; ver: string; lang: string };
  const verSlug = VERSION_SLUG[ver];
  const map: Record<string, { name: string; name_en: string | null; effect: string; href: string }> = {};
  for (const { key, urlParent } of RESOURCES) {
    for (const e of loadEntities(ver, lang, key)) {
      map[`${key}/${e.slug}`] = {
        name: e.name,
        name_en: (e.name_en as string) ?? null,
        effect: effectHtml(e.description_md as string | undefined),
        href: `/${lang}/${game}/${verSlug}/${urlParent}/${e.slug}/`,
      };
    }
  }
  return new Response(JSON.stringify(map), {
    headers: { 'content-type': 'application/json; charset=utf-8' },
  });
};
