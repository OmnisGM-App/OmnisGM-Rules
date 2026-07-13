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

// Карточка предмета: «тип · редкость» + короткая выдержка описания.
const RARITY: Record<string, [string, string]> = {
  common: ['обычный', 'common'], uncommon: ['необычный', 'uncommon'], rare: ['редкий', 'rare'],
  'very rare': ['очень редкий', 'very rare'], legendary: ['легендарный', 'legendary'],
  artifact: ['артефакт', 'artifact'],
};
function itemHtml(e: Record<string, unknown>, lang: string): string {
  const type = (e.type as string) ?? '';
  const rawR = (e.rarity as string) ?? '';
  const rp = RARITY[rawR];
  const rarity = rp ? (lang === 'ru' ? rp[0] : rp[1]) : rawR;
  const sub = [type, rarity].filter(Boolean).join(', ');
  const ex = excerpt(e.description_md as string | undefined, 190);
  return (
    (sub ? `<p class="hc-sub">${escapeHtml(sub)}</p>` : '') +
    (ex ? `<p>${escapeHtml(ex)}</p>` : '')
  );
}

// ── Оружие: «категория оружие тип» + урон (тип переведён) · мастерство · цена.
const W_CAT: Record<string, [string, string]> = { simple: ['простое', 'simple'], martial: ['воинское', 'martial'] };
const W_TYPE: Record<string, [string, string]> = { melee: ['ближнего боя', 'melee'], ranged: ['дальнобойное', 'ranged'] };
const W_DMG: Record<string, [string, string]> = {
  Bludgeoning: ['дробящий', 'bludgeoning'], Piercing: ['колющий', 'piercing'], Slashing: ['рубящий', 'slashing'],
};
const pick = (map: Record<string, [string, string]>, k: string, lang: string) => {
  const p = map[k];
  return p ? (lang === 'ru' ? p[0] : p[1]) : k;
};
function weaponHtml(e: Record<string, unknown>, lang: string): string {
  const cat = pick(W_CAT, (e.category as string) ?? '', lang);
  const typ = pick(W_TYPE, (e.type as string) ?? '', lang);
  const sub = lang === 'ru' ? `${cat} оружие ${typ}` : `${cat} ${typ} weapon`;
  const dt = e.damage_type ? pick(W_DMG, e.damage_type as string, lang) : '';
  const dmg = [e.damage_dice as string, dt].filter(Boolean).join(' ');
  const meta = [dmg, e.mastery as string, e.cost as string].filter(Boolean).join(' · ');
  return (
    `<p class="hc-sub">${escapeHtml(sub)}</p>` +
    (meta ? `<p class="hc-meta">${escapeHtml(meta)}</p>` : '')
  );
}

// ── Доспехи: категория + КД (у щита бонус) · требование Силы · цена.
const A_CAT: Record<string, [string, string]> = {
  light: ['лёгкий доспех', 'light armor'], medium: ['средний доспех', 'medium armor'],
  heavy: ['тяжёлый доспех', 'heavy armor'], shield: ['щит', 'shield'],
};
function armorHtml(e: Record<string, unknown>, lang: string): string {
  const cat = pick(A_CAT, (e.category as string) ?? '', lang);
  const acBase = e.ac_base as number;
  let ac: string;
  if (e.category === 'shield') {
    ac = lang === 'ru' ? `+${acBase} к КД` : `+${acBase} AC`;
  } else {
    ac = `${lang === 'ru' ? 'КД' : 'AC'} ${acBase}`;
    if (e.ac_dex_bonus === true) {
      ac += lang === 'ru' ? ' + Лов' : ' + Dex';
      if (e.ac_max_dex != null) ac += ` (${lang === 'ru' ? 'макс' : 'max'} ${e.ac_max_dex})`;
    }
  }
  const str = e.strength_req != null ? (lang === 'ru' ? `Сила ${e.strength_req}` : `Str ${e.strength_req}`) : '';
  const meta = [ac, str, e.cost as string].filter(Boolean).join(' · ');
  return (
    `<p class="hc-sub">${escapeHtml(cat)}</p>` +
    (meta ? `<p class="hc-meta">${escapeHtml(meta)}</p>` : '')
  );
}

// ── Снаряжение: категория · стоимость + короткая выдержка описания.
const E_SECTION: Record<string, [string, string]> = {
  adventuring_gear: ['снаряжение', 'adventuring gear'], tools: ['инструменты', 'tools'],
};
function equipHtml(e: Record<string, unknown>, lang: string): string {
  const sec = pick(E_SECTION, (e.section as string) ?? '', lang);
  const sub = [sec, e.cost as string].filter(Boolean).join(' · ');
  const ex = excerpt(e.description_md as string | undefined, 190);
  return (
    (sub ? `<p class="hc-sub">${escapeHtml(sub)}</p>` : '') +
    (ex ? `<p>${escapeHtml(ex)}</p>` : '')
  );
}

// ── Определения (свойства/мастерства оружия): markdown-абзацы → компактный HTML.
// Без href (у свойств нет страниц) — карточка чисто справочная.
function defHtml(md: string | undefined): string {
  if (!md) return '';
  return md
    .split(/\n{2,}/)
    .map((b) => b.trim())
    .filter(Boolean)
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

// resource → { urlParent, build(entity) → HTML тела карточки }.
const RESOURCES: { key: string; urlParent: string; body: (e: Record<string, unknown>, lang: string) => string }[] = [
  { key: 'conditions', urlParent: 'rules-glossary/conditions', body: (e) => conditionHtml(e.description_md as string) },
  { key: 'spells', urlParent: 'spells', body: (e, lang) => spellHtml(e, lang) },
  { key: 'monsters', urlParent: 'monsters-a-z', body: (e, lang) => monsterHtml(e, lang) },
  // Животные — тот же стат-блок, что и монстры → та же карточка (тип/мировоззрение + КД·хиты·ПО).
  { key: 'animals', urlParent: 'animals', body: (e, lang) => monsterHtml(e, lang) },
  { key: 'magic-items', urlParent: 'magic-items', body: (e, lang) => itemHtml(e, lang) },
  { key: 'weapons', urlParent: 'weapons', body: (e, lang) => weaponHtml(e, lang) },
  { key: 'armor', urlParent: 'armor', body: (e, lang) => armorHtml(e, lang) },
  { key: 'equipment', urlParent: 'equipment', body: (e, lang) => equipHtml(e, lang) },
  // Свойства/мастерства оружия — только карточка-определение (страниц нет; href не используется
  // клиентом для gloss-подсказок).
  { key: 'weapon-properties', urlParent: 'weapon-properties', body: (e) => defHtml(e.description_md as string) },
  { key: 'masteries', urlParent: 'masteries', body: (e) => defHtml(e.description_md as string) },
  // Действия Rules Glossary — карточка-определение (страниц нет; глоссинг в тексте → span.gloss).
  { key: 'actions', urlParent: 'actions', body: (e) => defHtml(e.description_md as string) },
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
        // EN-оригинал показываем в шапке ВСЕГДА (и в EN-карточке тоже). Для EN-сущностей
        // name_en отсутствует → оригинал = само name (оно и есть английское).
        name_en: (e.name_en as string) ?? (e.name as string),
        effect: body(e as unknown as Record<string, unknown>, lang),
        href: `/${lang}/${game}/${verSlug}/${urlParent}/${e.slug}/`,
      };
    }
  }
  return new Response(JSON.stringify(map), {
    headers: { 'content-type': 'application/json; charset=utf-8' },
  });
};
