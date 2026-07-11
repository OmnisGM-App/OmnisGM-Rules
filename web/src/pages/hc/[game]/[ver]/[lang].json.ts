import type { APIRoute } from 'astro';
import { loadEntities, excerpt, VERSION_SLUG } from '../../../../lib/entities';

// Hovercard-данные для автоссылок (issue #20, вариант B: fetch-on-hover served JSON).
// Бакет `game/verKey/lang` → карта `resource/slug` → { name, name_en, effect(HTML), href }.
// Ключ бакета = префикс `data-hc` из rehype-entity-autolink. Клиент рендерит name_en + источник
// + effect(HTML). Собираем только там, где реально существуют страницы сущностей.

const escapeHtml = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// ── Состояния: эффект → компактный HTML (вводная «Пока вы находитесь…» выкинута, ярлыки жирным).
function conditionHtml(md: string | undefined): string {
  if (!md) return '';
  const blocks = md.split(/\n{2,}/).map((b) => b.trim()).filter(Boolean);
  const isIntro = (b: string) => /^(Пока вы находитесь в состоянии|While you have the .* condition)/.test(b);
  const body = blocks.length > 1 && isIntro(blocks[0]) ? blocks.slice(1) : blocks;
  return body
    .map((b) => {
      const html = escapeHtml(b)
        .replace(/\*\*_([^*]+?)_\*\*/g, '<strong>$1</strong>')
        .replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>')
        .replace(/(?<![\w*])_([^_]+?)_(?![\w*])/g, '<em>$1</em>')
        .replace(/(?<![\w*])\*([^*]+?)\*(?![\w*])/g, '<em>$1</em>');
      return `<p>${html}</p>`;
    })
    .join('');
}

// ── Заклинания: школа в RU JSON переведена наполовину — нормализуем двусторонним мапом.
const SCHOOLS: [string, string][] = [
  ['Abjuration', 'Ограждения'], ['Conjuration', 'Вызова'], ['Divination', 'Прорицания'],
  ['Enchantment', 'Очарования'], ['Evocation', 'Воплощения'], ['Illusion', 'Иллюзии'],
  ['Necromancy', 'Некромантии'], ['Transmutation', 'Преобразования'],
];
const schoolLabel = (raw: string, lang: string) => {
  const p = SCHOOLS.find(([en, ru]) => en === raw || ru === raw);
  return p ? (lang === 'ru' ? p[1] : p[0]) : raw;
};
const ordinalEn = (n: string) => {
  const s = ['th', 'st', 'nd', 'rd'], v = Number(n) % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
};

// Карточка заклинания: «уровень, школа» + компактная мета (время · дистанция · длительность)
// + короткая выдержка описания.
function spellHtml(e: Record<string, unknown>, lang: string): string {
  const lvl = String(e.level ?? '');
  const school = schoolLabel(e.school as string, lang);
  const levelLine = lvl === '0'
    ? (lang === 'ru' ? `Заговор, ${school}` : `${school} cantrip`)
    : (lang === 'ru' ? `${lvl}-й уровень, ${school}` : `${ordinalEn(lvl)}-level ${school}`);
  const val = (o: unknown) => (o as Record<string, unknown> | undefined)?.value as string | undefined;
  const meta = [val(e.casting_time), val(e.range), val(e.duration)].filter(Boolean).join(' · ');
  const ex = excerpt(e.description_md as string | undefined, 190);
  return (
    `<p class="hc-sub">${escapeHtml(levelLine)}</p>` +
    (meta ? `<p class="hc-meta">${escapeHtml(meta)}</p>` : '') +
    (ex ? `<p>${escapeHtml(ex)}</p>` : '')
  );
}

// Карточка монстра: строка типа (размер тип, мировоззрение) + компактная мета (КД · хиты · ПО).
function monsterHtml(e: Record<string, unknown>, lang: string): string {
  const size = (e.size as string) ?? '';
  const type = (e.type as string) ?? '';
  const subtype = e.subtype as string | null;
  const alignment = e.alignment as string | null;
  const typeLine = [
    [size, type].filter(Boolean).join(' ') + (subtype ? ` (${subtype})` : ''),
    alignment,
  ].filter(Boolean).join(', ');
  const ac = (e.ac as { value?: number })?.value;
  const hp = (e.hp as { average?: number })?.average;
  const cr = (e.cr as { value?: string })?.value;
  const meta = [
    ac != null ? `${lang === 'ru' ? 'КД' : 'AC'} ${ac}` : '',
    hp != null ? (lang === 'ru' ? `${hp} хитов` : `${hp} HP`) : '',
    cr ? `${lang === 'ru' ? 'ПО' : 'CR'} ${cr}` : '',
  ].filter(Boolean).join(' · ');
  return (
    (typeLine ? `<p class="hc-sub">${escapeHtml(typeLine)}</p>` : '') +
    (meta ? `<p class="hc-meta">${escapeHtml(meta)}</p>` : '')
  );
}

// resource → { urlParent, build(entity) → HTML тела карточки }.
const RESOURCES: { key: string; urlParent: string; body: (e: Record<string, unknown>, lang: string) => string }[] = [
  { key: 'conditions', urlParent: 'rules-glossary/conditions', body: (e) => conditionHtml(e.description_md as string) },
  { key: 'spells', urlParent: 'spells', body: (e, lang) => spellHtml(e, lang) },
  { key: 'monsters', urlParent: 'monsters-a-z', body: (e, lang) => monsterHtml(e, lang) },
];

// Согласовано со сборкой страниц сущностей: пока только srd52 (en/ru).
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
  for (const { key, urlParent, body } of RESOURCES) {
    for (const e of loadEntities(ver, lang, key)) {
      map[`${key}/${e.slug}`] = {
        name: e.name,
        name_en: (e.name_en as string) ?? null,
        effect: body(e as unknown as Record<string, unknown>, lang),
        href: `/${lang}/${game}/${verSlug}/${urlParent}/${e.slug}/`,
      };
    }
  }
  return new Response(JSON.stringify(map), {
    headers: { 'content-type': 'application/json; charset=utf-8' },
  });
};
