// Источник-ссылка для programmatic-страниц терминов rules-glossary (issue #106).
//
// Термин в глоссарии — сжатая выжимка; на его странице даём ссылку в главу-источник, где
// правило раскрыто полностью (и UX «провалиться в контекст», и внутренняя перелинковка:
// страницы-термины перестают быть тупиками и раздают вес главам).
//
// Источник зашит в description_md как «See also "Глава" ("Раздел")» /
// «См. также «Глава» («Раздел»)». Ссылку строим ТОЛЬКО когда первичная цель — реальная
// ГЛАВА (Playing the Game / Spells / Character Creation / Equipment): таких ~37, они дают
// точную главу + якорь-раздел. Прочие See-also указывают на другие ТЕРМИНЫ (перекрёстные
// ссылки — их обрабатывает автолинк в теле); для них главы-источника нет → fallback на
// upLink «Глоссарий правил» (уже есть в шаблоне).
//
// NB: строки берём из фактических See-also, а не из H1 глав — перевод разошёлся
// (RU-глоссарий ссылается на «Процесс игры», тогда как H1 главы — «Как играть»).

// Первичный заголовок See-also (EN/RU, как в SRD) → слаг главы (языконезависимый сегмент URL).
const CHAPTER_SLUG = {
  'Playing the Game': 'playing-the-game', 'Процесс игры': 'playing-the-game',
  'Character Creation': 'character-creation', 'Создание персонажа': 'character-creation',
  'Equipment': 'equipment', 'Снаряжение': 'equipment',
  'Spells': 'spells', 'Заклинания': 'spells',
};

// github-slugger-совместимый анкор (Astro так генерит id заголовков): нижний регистр,
// пунктуация убрана, пробелы → дефис, юникод-буквы/цифры сохранены. Best-effort: если
// раздел не совпал с заголовком главы, браузер просто останется наверху главы (не вредно).
function headingAnchor(s) {
  return s.toLowerCase().trim()
    .replace(/[^\p{L}\p{N}\s-]/gu, '')
    .replace(/\s+/g, '-');
}

// (description_md, lang) → { slug, anchor|null, chapterLabel, sectionLabel|null } | null.
export function parseSourceChapter(md, lang) {
  if (!md) return null;
  const re = lang === 'ru'
    ? /См\.?\s*также\*?\s*[«"]([^»"]+)[»"](?:\s*\(\s*[«"]([^»"]+)[»"])?/
    : /[Ss]ee also\*?\s*"([^"]+)"(?:\s*\(\s*"([^"]+)")?/;
  const m = md.match(re);
  if (!m) return null;
  const chapter = m[1].replace(/\.$/, '').trim();
  const slug = CHAPTER_SLUG[chapter];
  if (!slug) return null;
  const section = m[2] ? m[2].replace(/\.$/, '').trim() : null;
  return { slug, anchor: section ? headingAnchor(section) : null, chapterLabel: chapter, sectionLabel: section };
}

// Готовая ссылка-источник для компонента: { href, label } | null.
// href — /{lang}/dnd/{verSlug}/{chapter}/[#anchor]; label локализован («Глава», «раздел»).
export function sourceLinkFor(md, { verSlug, lang }) {
  const s = parseSourceChapter(md, lang);
  if (!s) return null;
  const href = `/${lang}/dnd/${verSlug}/${s.slug}/${s.anchor ? `#${s.anchor}` : ''}`;
  const label = lang === 'ru'
    ? `глава «${s.chapterLabel}»${s.sectionLabel ? `, раздел «${s.sectionLabel}»` : ''}`
    : `${s.chapterLabel}${s.sectionLabel ? ` — ${s.sectionLabel}` : ''}`;
  return { href, label };
}
