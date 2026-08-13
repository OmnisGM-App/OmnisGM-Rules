// Шаблонные <meta description> сущностных страниц из СТРУКТУРИРОВАННЫХ данных (issue #185).
//
// Зачем: раньше сущностные страницы брали description как excerpt() первого абзаца/черты.
// У стат-блоков это давало (а) дубли — «Дракон может дышать воздухом и водой.» на 33 страницах,
// (б) сниппет без имени существа и без фактов, которые люди ищут («сколько кд у бурого медведя
// в днд», «днд монстры опасности 1»). Факты из JSON уникальны по определению и совпадают с
// формулировкой спроса.
//
// Формулировки сверены с выгрузкой запросов Вебмастера за 05–11.08.2026:
//   • «днд» кириллицей — 80% показов, обязателен в RU; «5e»/«srd» в RU-спросе ≈ 0;
//   • сущность идёт первой («плут днд», а не «днд: плут»);
//   • «D&D» латиницей оставляем (Google RU + латиничные формы «dnd»/«d&d»);
//   • маркер редакции — человеческий «2024»/«2014», а не машинный «5.2»/«5.1»: спроса на него
//     почти нет, но он разводит одноимённые страницы SRD 5.1 и 5.2 между собой.
//
// Модуль — общий дом для фактовых сниппетов всех типов сущностей; сейчас здесь стат-блоки
// (монстры/животные), класс-страницы живут в class-facts.ts и берут отсюда редакцию.

// Редакция D&D по ключу версии. Принимаем оба написания, которые ходят по коду: ключ API
// («srd52», как в VERSION_SLUG) и сегмент URL («srd-5.2», как в catch-all-роуте).
const EDITION: Record<string, string> = {
  srd52: '2024',
  srd51: '2014',
  'srd-5.2': '2024',
  'srd-5.1': '2014',
};

/** Человеческая метка редакции («2024»/«2014») или '' для не-D&D версий. */
export function edition(version: string): string {
  return EDITION[version] ?? '';
}

/** «D&D 2024» / «D&D» — общая для RU и EN часть, чтобы редакция не разъезжалась по шаблонам. */
export function editionLabel(version: string): string {
  const ed = edition(version);
  return ed ? `D&D ${ed}` : 'D&D';
}

// ── Стат-блоки (монстры и животные) ──────────────────────────────────────────

interface StatBlockEntity {
  name: string;
  size?: unknown;
  type?: unknown;
  subtype?: unknown;
  ac?: unknown;
  hp?: unknown;
  cr?: unknown;
}

export type StatBlockKind = 'monster' | 'animal';

const KIND_WORD: Record<StatBlockKind, { ru: string; en: string }> = {
  monster: { ru: 'монстр', en: 'monster' },
  animal: { ru: 'животное', en: 'animal' },
};

const str = (v: unknown) => (typeof v === 'string' ? v.trim() : '');
const num = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? v : null);

/**
 * «маленькая фея (гоблиноид)» / «Small Fey (Goblinoid)». В RU размер уже переведён в роде
 * своего типа («Маленькая фея», «Большой зверь») — просто снимаем капитализацию, чтобы фраза
 * села в середину предложения. В EN оставляем Title Case как в стат-блоке.
 */
function creatureLine(entity: StatBlockEntity, lang: 'en' | 'ru', withSubtype: boolean): string {
  const size = str(entity.size);
  const type = str(entity.type);
  const subtype = str(entity.subtype);
  let line = [size, type].filter(Boolean).join(' ');
  if (lang === 'ru') line = line.toLowerCase();
  if (withSubtype && subtype) line += ` (${lang === 'ru' ? subtype.toLowerCase() : subtype})`;
  return line;
}

/**
 * Фактовый <meta description> стат-блока. null, если ключевых фактов (КД/хиты/опасность) нет —
 * вызывающий откатывается к прежнему excerpt(), сборку это не валит.
 *
 * Уникальность: в строке есть имя существа (уникально внутри раздела) и редакция — значит
 * одноимённые страницы 5.1 и 5.2 тоже не дублируются.
 */
export function statBlockDescription(opts: {
  entity: StatBlockEntity;
  lang: 'en' | 'ru';
  version: string;
  kind: StatBlockKind;
}): string | null {
  const { entity, lang, version, kind } = opts;

  const ac = num((entity.ac as { value?: unknown } | undefined)?.value);
  const hp = num((entity.hp as { average?: unknown } | undefined)?.average);
  const cr = str((entity.cr as { value?: unknown } | undefined)?.value);
  if (ac == null || hp == null || !cr) return null;

  const ed = editionLabel(version);
  const word = KIND_WORD[kind][lang];

  const compose = (withSubtype: boolean, shortTail: boolean) => {
    const creature = creatureLine(entity, lang, withSubtype);
    if (lang === 'ru') {
      const facts = [`КД ${ac}`, `хиты ${hp}`, `опасность ${cr}`, creature].filter(Boolean).join(', ');
      const tail = shortTail
        ? 'Полный стат-блок SRD на русском.'
        : 'Характеристики, атаки и особенности — стат-блок SRD на русском.';
      return `${entity.name} — ${word} ${ed} (днд): ${facts}. ${tail}`;
    }
    const facts = [`AC ${ac}`, `HP ${hp}`, `CR ${cr}`, creature].filter(Boolean).join(', ');
    const tail = shortTail
      ? 'Full SRD stat block.'
      : 'Full stat block with abilities, attacks and traits from the SRD.';
    return `${entity.name} — a ${ed} ${word}: ${facts}. ${tail}`;
  };

  // Держим сниппет в пределах ~160 символов: сначала укорачиваем хвост, потом снимаем подтип.
  // Имя и факты не режем никогда — ради них сниппет и существует.
  for (const [withSubtype, shortTail] of [[true, false], [true, true], [false, true]] as const) {
    const out = compose(withSubtype, shortTail);
    if (out.length <= 160) return out;
  }
  return compose(false, true);
}
