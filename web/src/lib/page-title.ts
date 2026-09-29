// Шаблоны <title> сущностных и хабовых страниц (issue #185, часть 2).
import { VERSION_LABEL } from './entities';
import { edition } from './entity-facts';

const BRAND = 'OmnisGM Rules';
// Bing ругается на title длиннее 65 символов (#172) — это и есть бюджет лестницы.
const LIMIT = 65;

// Версия приходит в двух написаниях: ключ API («srd52») и сегмент URL («srd-5.2»).
const verKey = (version: string) => version.replace(/[-.]/g, '');

export interface TitleOpts {
  /** Имя сущности или заголовок страницы. */
  name: string;
  /** Тип сущности: «класс», «монстр», «magic item». Пусто — для страниц без типа. */
  kind?: string;
  lang: 'en' | 'ru';
  game: string;
  /** «srd52» или «srd-5.2» — принимаются оба. */
  version: string;
}

// Метка системы. Длинная — для title, короткая — последняя ступень укорачивания
// (нужна только BRP: «Basic Roleplaying 1.0» съедает треть бюджета).
function systemLabel(game: string, version: string, short: boolean): string {
  const ver = VERSION_LABEL[verKey(version)] ?? '';
  if (game === 'dnd') {
    const ed = edition(version);
    return ed ? `D&D ${ed}` : `D&D ${ver}`.trim();
  }
  if (game === 'brp') return short ? `BRP ${ver}`.trim() : `Basic Roleplaying ${ver}`.trim();
  // «SRD» в метке Daggerheart — требование DPCGL §2.5(a): марка не может быть заголовком работы,
  // а «Daggerheart SRD 1.0» — ссылка на источник, как в атрибуции §4.1. Короткая ступень роняет
  // версию, но НЕ «SRD» (issue #166).
  if (game === 'daggerheart') return short ? 'Daggerheart SRD' : `Daggerheart SRD ${ver}`.trim();
  return `${game.toUpperCase()} ${ver}`.trim();
}

// Форма спроса в скобках — только у D&D: у Daggerheart и BRP кириллического кластера нет.
function searchForm(
  game: string,
  lang: 'en' | 'ru',
  level: 'long' | 'short' | 'none',
  version: string,
): string {
  if (game !== 'dnd' || level === 'none') return '';
  if (lang === 'ru') return level === 'long' ? '(днд 5)' : '(днд)';
  // EN: слэш разделяет токены — точное вхождение получают и «5e», и «5.5e» (#188).
  return level === 'long' && edition(version) === '2024' ? '(5e/5.5e)' : '(5e)';
}

/**
 * <title> страницы — первая ступень лестницы, влезшая в LIMIT. Бренд роняем раньше формы
 * спроса: брендовые запросы приходят на корень. Длинное имя может вылезти за LIMIT.
 */
export function pageTitle(opts: TitleOpts): string {
  const { name, kind = '', lang, game, version } = opts;
  // Тип совпал с именем — роняем: «Щит — щит D&D 2024» читается как заикание.
  const kindLower = kind.trim().toLowerCase();
  const type = kindLower === name.trim().toLowerCase() ? '' : kindLower;

  const compose = (form: 'long' | 'short' | 'none', brand: boolean, short: boolean) => {
    const sys = systemLabel(game, version, short);
    const middle = type
      ? lang === 'ru'
        ? `${type} ${sys}`
        : `${sys} ${type}`
      : sys;
    const head = [name, middle].filter(Boolean).join(' — ');
    const withForm = [head, searchForm(game, lang, form, version)].filter(Boolean).join(' ');
    return brand ? `${withForm} · ${BRAND}` : withForm;
  };

  const ladder = [
    compose('long', true, false),
    compose('short', true, false),
    compose('short', false, false),
    compose('none', false, false),
    compose('none', false, true),
  ];
  return ladder.find((v) => v.length <= LIMIT) ?? ladder[ladder.length - 1];
}
