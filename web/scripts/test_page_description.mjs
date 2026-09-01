// Юнит-проверка page-description.mjs (issue #213) — сниппет markdown-страниц.
//
// Гейт по dist (verify_dist_meta_budget.mjs) считает, сколько описаний короче 110 символов,
// но не видит, ИЗ ЧЕГО они собраны: сниппет из служебной таблицы посреди страницы или из
// куска CSS тоже будет «достаточно длинным». Инварианты выбора источника проверяем здесь,
// на синтетике: живой контент их не различает (сегодня у всех глав есть вступление).
//
// Запуск: node web/scripts/test_page_description.mjs
import {
  introProse,
  outline,
  tableSummary,
  listFit,
  clamp,
  pageDescription,
} from '../src/lib/page-description.mjs';

const failures = [];
const check = (name, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) failures.push(`${name}: получили ${JSON.stringify(got)}, ожидали ${JSON.stringify(want)}`);
};
const checkFn = (name, got, pred, why) => {
  if (!pred(got)) failures.push(`${name}: ${why}; получили ${JSON.stringify(got)}`);
};

const SYS = { lang: 'en', sysLabel: 'D&D', docLabel: 'SRD 5.2.1' };

// --- Ступень 1: вводная проза ---------------------------------------------------------
const chapter = `# Weapons

All weapons have a tier, trait, range, damage die, damage type, and burden. Some weapons also have a feature.

## Category

A weapon's category specifies whether it is a Primary or Secondary weapon.
`;
check('проза берётся до первого подзаголовка', introProse(chapter),
  'All weapons have a tier, trait, range, damage die, damage type, and burden. Some weapons also have a feature.');
checkFn('описание главы начинается с прозы', pageDescription({ name: 'Weapons', body: chapter, ...SYS }),
  (s) => s.startsWith('Weapons — D&D SRD 5.2.1. All weapons have a tier'), 'ожидали шапку и вступление');

// Проза ПОСЛЕ подзаголовка вступлением не считается: у справочников первый абзац — кусок
// первой же сущности («Large Aberration, Lawful Evil»), и в сниппет ему нельзя.
const reference = `# Monsters A–Z

## Monsters: A

### Aboleth

*Large Aberration, Lawful Evil*

### Ankheg

*Large Monstrosity, Unaligned*
`;
check('проза после подзаголовка не берётся', introProse(reference), '');
checkFn('справочник описывается своими сущностями', pageDescription({ name: 'Monsters A–Z', body: reference, ...SYS }),
  (s) => s.includes('Aboleth') && s.includes('Ankheg') && !s.includes('Aberration'),
  'ожидали перечень существ без куска статблока');

// --- Ступень 2: структура --------------------------------------------------------------
// Уровень заголовков выбирается самый населённый: у rules-glossary два служебных ## против
// сотни терминов ####, и в сниппете ценны термины.
const glossary = `# Rules Glossary

## Glossary Conventions

The glossary uses the following conventions:

## Rules Definitions

#### Ability Check

Text.

#### Advantage

Text.

#### Alignment

Text.
`;
check('берётся самый населённый уровень', outline(glossary),
  ['Ability Check', 'Advantage', 'Alignment']);

// Таблица считается, только если страница с неё НАЧИНАЕТСЯ: иначе в сниппет главы уезжает
// случайная служебная таблица (у rules-glossary это была таблица сокращений «AC, C, CE»).
const tableMidPage = `# Rules Glossary

## Conventions

| Abbr. | Full Term |
|---|---|
| AC | Armor Class |
| CE | Chaotic Evil |
`;
check('таблица посреди страницы не берётся', tableSummary(tableMidPage), null);
const tableFirst = `| Spell | Level | School |
|---|---|---|
| Acid Splash | Cantrip | Evocation |
| Chill Touch | Cantrip | Necromancy |
`;
check('таблица в начале страницы — берётся', tableSummary(tableFirst),
  { rows: 2, names: ['Acid Splash', 'Chill Touch'] });
checkFn('справочник-таблица: число записей и первые имена',
  pageDescription({ name: 'Spells (Reference)', body: tableFirst, ...SYS }),
  (s) => s.includes('2 entries') && s.includes('Acid Splash'), 'ожидали счётчик и имена');

// --- Мусор из тела не попадает в сниппет -----------------------------------------------
const withStyle = `# Character Sheet

<style>
/* BRP Character Sheet */
.brp-sheet { font-family: 'Segoe UI', Arial, sans-serif; font-size: 11px; }
</style>

<div class="brp-sheet">
`;
checkFn('CSS не уезжает в описание', pageDescription({ name: 'Character Sheet', body: withStyle, ...SYS }),
  (s) => !s.includes('font-family') && !s.includes('brp-sheet'), 'в сниппете куски стилей');

// --- Длина и обрезка -------------------------------------------------------------------
// Слова уникальны (word00, word01, …) — так видно, обрезали по границе слова или посреди него.
const words = Array.from({ length: 40 }, (_, i) => `word${String(i).padStart(2, '0')}`);
const long = `# T\n\n${words.join(' ')} end.`;
const longOut = pageDescription({ name: 'T', body: long, ...SYS });
checkFn('не длиннее 160', longOut, (s) => s.length <= 160, 'описание переросло 160 символов');
checkFn('обрезка не рвёт слово', longOut, (s) => {
  if (!s.endsWith('…')) return false; // текст длиннее бюджета — обрезка обязана случиться
  const last = s.replace(/…$/, '').split(' ').pop();
  return words.includes(last);
}, 'последнее слово обрезано посреди себя');

// Пустая страница — старый бойлерплейт, а не пустое/битое описание.
check('пустое тело — бойлерплейт', pageDescription({ name: 'Empty', body: '# Empty\n', ...SYS }),
  'Empty — D&D SRD 5.2.1. Tabletop RPG System Reference Document in the OmnisGM ecosystem.');

// Короткое вступление добивается до нижней границы, а не остаётся 96-символьным.
const shortIntro = `# Loot

Loot comprises any consumables or reusable items the party acquires.
`;
checkFn('короткое вступление добирается хвостом', pageDescription({ name: 'Loot', body: shortIntro, ...SYS }),
  (s) => s.length >= 110 && s.length <= 160 && s.includes('OmnisGM'), 'ожидали 110–160 с брендовым хвостом');

// Русская страница — своя шапка и свой хвост, без английских хвостов в выдаче.
checkFn('русская шапка', pageDescription({ name: 'Добыча', body: shortIntro, lang: 'ru', sysLabel: 'Daggerheart', docLabel: 'SRD 1.0' }),
  (s) => s.startsWith('Добыча — Daggerheart SRD 1.0 на русском.') && !s.includes('Tabletop'),
  'ожидали русскую шапку без английского хвоста');

// Вспомогательные функции.
check('listFit режет по границе элемента', listFit(['Aboleth', 'Ankheg', 'Assassin'], 20), 'Aboleth, Ankheg…');
check('listFit целиком — с точкой', listFit(['Aboleth', 'Ankheg'], 40), 'Aboleth, Ankheg.');
// clamp предпочитает границу предложения, но только если после неё остаётся хотя бы 60%
// бюджета: иначе из 160 символов сниппета получилась бы одна короткая фраза.
check('clamp по границе предложения',
  clamp('A reasonably long first sentence about spells. And a second one after it.', 60),
  'A reasonably long first sentence about spells.');
check('clamp не жертвует объёмом ради точки',
  clamp('Short one. And a much longer second sentence goes here.', 40),
  'Short one. And a much longer second…');

if (failures.length) {
  console.error('page-description: ПРОВАЛЕНО');
  for (const f of failures) console.error(`  ${f}`);
  process.exit(1);
}
console.log('page-description: ок');
