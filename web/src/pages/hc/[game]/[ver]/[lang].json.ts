import type { APIRoute } from 'astro';
import { loadEntities, excerpt, VERSION_SLUG } from '../../../../lib/entities';

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
  const map: Record<string, { name: string; name_en: string | null; excerpt: string; href: string }> = {};
  for (const { key, urlParent } of RESOURCES) {
    for (const e of loadEntities(ver, lang, key)) {
      map[`${key}/${e.slug}`] = {
        name: e.name,
        name_en: (e.name_en as string) ?? null,
        excerpt: excerpt(e.description_md, 160),
        href: `/${lang}/${game}/${verSlug}/${urlParent}/${e.slug}/`,
      };
    }
  }
  return new Response(JSON.stringify(map), {
    headers: { 'content-type': 'application/json; charset=utf-8' },
  });
};
