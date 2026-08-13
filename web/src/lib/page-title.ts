// Шаблоны <title> сущностных и хабовых страниц (issue #185, часть 2).
//
// Было два несвязанных семейства:
//   • MD-страницы (catch-all [...slug].astro): «Плут · D&D SRD 5.2.1 · OmnisGM Rules» —
//     тип сущности отсутствует вовсе, а это самый крупный кластер спроса («плут днд» —
//     ~280 показов/нед при нулевом CTR);
//   • сущностные страницы: «Гоблин-воин — Монстр D&D 5.2 · OmnisGM Rules» — тип есть, но
//     версия машинная («5.2»), а формы, которой ищут («днд»), нет.
//
// Что говорит выгрузка Вебмастера за 05–11.08.2026 (2394 показа, 1223 запроса):
//   • «днд» кириллицей — 1912 показов (80%). В RU-title обязателен;
//   • порядок слов: сущность первой — «…днд» в конце 1354 показа против 367 у «днд…»;
//   • «5e» в RU-спросе — 0 показов, «srd» — 7, «2024» — 4. Бюджет символов на них не тратим;
//   • «днд 5» — 163 показа: форма живёт как голая цифра. Отсюда основной вариант «(днд 5)» —
//     он содержит и «днд», и «днд 5», а стоит на 2 символа больше;
//   • латиница маргинальна («dnd» 32, «d&d» 13), но «D&D» в title нужен — Google RU и
//     латиничные формы;
//   • маркер редакции — человеческий «2024»/«2014» вместо машинного «5.2»/«5.1»: спроса на
//     него почти нет, но он разводит одноимённые страницы SRD 5.1 и 5.2. Из лестницы
//     укорачивания НИКОГДА не выпадает — иначе получим дубли title между редакциями.
//
// EN-формы («rogue 5e», «rogue 5.5e», «dnd rogue class») выгрузкой не покрыты — Яндекс её не
// даёт, а /en/ от него вообще закрыт (#182). Поэтому EN — зеркало RU-структуры: «(5.5e)» на
// страницах 2024 (содержит «5e» подстрокой, значит покрывает оба употребления, как «(днд 5)»
// покрывает «днд») и «(5e)» на 2014. Проверять по Search Console, когда наберётся статистика.
import { VERSION_LABEL } from './entities';
import { edition } from './entity-facts';

const BRAND = 'OmnisGM Rules';
// Bing ругается на title длиннее 65 символов (#172) — это и есть бюджет лестницы.
const LIMIT = 65;

// Версия приходит в двух написаниях: ключ API («srd52») и сегмент URL («srd-5.2»).
const verKey = (version: string) => version.replace(/[-.]/g, '');

export interface TitleOpts {
  /** Имя сущности или заголовок страницы — всегда первым, никогда не режется. */
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
  if (game === 'daggerheart') return short ? 'Daggerheart' : `Daggerheart ${ver}`.trim();
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
  // EN: тот же приём, что и с «(днд 5)» — строка «5.5e» СОДЕРЖИТ «5e» как подстроку, поэтому
  // на страницах редакции 2024 она покрывает оба употребления («rogue 5e» и «rogue 5.5e») за
  // +2 символа и ничего не теряет. У 5.1 никакой «5.5e» нет — там всегда «(5e)».
  return level === 'long' && edition(version) === '2024' ? '(5.5e)' : '(5e)';
}

/**
 * <title> страницы. Лестница укорачивания под бюджет в 65 символов:
 *   1. полная форма спроса + бренд      «Плут — класс D&D 2024 (днд 5) · OmnisGM Rules»
 *   2. короткая форма спроса + бренд    «… (днд) · OmnisGM Rules»
 *   3. короткая форма без бренда        «… (днд)»
 *   4. без формы спроса                 «Плут — класс D&D 2024»
 *   5. короткая метка системы           (BRP: «Basic Roleplaying 1.0» → «BRP 1.0»)
 * Бренд роняем раньше формы спроса намеренно: брендовые запросы приходят на корень,
 * а «днд» — 80% показов сущностных страниц. Имя, тип и редакция не режутся никогда,
 * поэтому длинные имена сущностей всё равно могут вылезти за 65 — это осознанный хвост.
 */
export function pageTitle(opts: TitleOpts): string {
  const { name, kind = '', lang, game, version } = opts;
  // Тип идёт в середину фразы — «Магический предмет» → «магический предмет». Если тип совпал
  // с самим именем, роняем его: «Щит — щит D&D 2024» читается как заикание.
  const kindLower = kind.trim().toLowerCase();
  const type = kindLower === name.trim().toLowerCase() ? '' : kindLower;

  const compose = (form: 'long' | 'short' | 'none', brand: boolean, short: boolean) => {
    const sys = systemLabel(game, version, short);
    // Порядок слов родной для языка: RU «плут — класс D&D 2024», EN «— D&D 2024 class».
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
