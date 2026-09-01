import { test, expect } from '@playwright/test';

// Длина и содержательность <meta description> у markdown-страниц (issue #213).
// URL — ровно те, на которые ругался Bing Webmaster Tools (правило 118 «Meta descriptions
// too short»): у них был бойлерплейт 95–102 символа, одинаковый по всему сайту.
//
// Сплошной счёт коротких описаний по dist делает web/scripts/verify_dist_meta_budget.mjs
// (гоняется в CI), инварианты сборки сниппета — web/scripts/test_page_description.mjs.
// Здесь — проверка на живой отрендеренной странице: мета доезжает до HTML и не пустая.
const MIN = 110;
const MAX = 160;

const BING_REPORT = [
  '/en/daggerheart/srd-1.0/classes/druid/',
  '/en/daggerheart/srd-1.0/classes/ranger/',
  '/en/daggerheart/srd-1.0/weapons/',
  '/en/dnd/srd-5.2/rules-glossary/',
  '/en/daggerheart/srd-1.0/armor/',
];

for (const url of BING_REPORT) {
  test(`description 110–160 и без бойлерплейта: ${url}`, async ({ page }) => {
    await page.goto(url);
    const desc = await page.locator('head meta[name="description"]').getAttribute('content');
    expect(desc, 'description отсутствует').toBeTruthy();
    expect(desc!.length).toBeGreaterThanOrEqual(MIN);
    expect(desc!.length).toBeLessThanOrEqual(MAX);
    // Брендовый хвост допустим только как добивка короткого вступления — на этих
    // страницах контента хватает, и целиком бойлерплейтным описание быть не должно.
    expect(desc).not.toMatch(/^[^.]+\.\s*Tabletop RPG System Reference Document/);
  });
}

test('описание собрано из контента страницы, а не из шаблона', async ({ page }) => {
  await page.goto('/en/daggerheart/srd-1.0/classes/druid/');
  const desc = await page.locator('head meta[name="description"]').getAttribute('content');
  // Первая фраза главы «Druid» — признак того, что сниппет пришёл из тела markdown.
  expect(desc).toContain('Becoming a druid');

  // Справочник без вступительной прозы описывается своими терминами.
  await page.goto('/en/dnd/srd-5.2/rules-glossary/');
  const glossary = await page.locator('head meta[name="description"]').getAttribute('content');
  expect(glossary).toContain('Ability Check');

  // og:description и twitter:description идут из того же значения — расхождения быть не должно.
  const og = await page.locator('head meta[property="og:description"]').getAttribute('content');
  expect(og).toBe(glossary);
});

test('русская страница описана по-русски', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/rules-glossary/');
  const desc = await page.locator('head meta[name="description"]').getAttribute('content');
  expect(desc!.length).toBeGreaterThanOrEqual(MIN);
  expect(desc!.length).toBeLessThanOrEqual(MAX);
  expect(desc).not.toContain('Tabletop RPG');
  expect(desc).toContain('на русском');
});

// ── Сущностные шаблоны (issue #214, волна 1: оружие и навыки BRP) ─────────────
// Прежние сниппеты этих типов были 46–90 символов: у оружия только урон, цена и вес,
// у навыков BRP вообще голый excerpt() описания без имени и системы.

const facts = async (page: import('@playwright/test').Page, url: string) => {
  await page.goto(url);
  const d = await page.locator('head meta[name="description"]').getAttribute('content');
  expect(d, `нет description: ${url}`).toBeTruthy();
  expect(d!.length, `слишком длинно: ${d}`).toBeLessThanOrEqual(MAX);
  return d!;
};

test('оружие: в сниппете свойства и мастерство, а не только урон и цена', async ({ page }) => {
  const d = await facts(page, '/ru/dnd/srd-5.2/weapons/longsword/');
  expect(d.length).toBeGreaterThanOrEqual(MIN);
  expect(d).toContain('свойства: универсальное');
  expect(d).toContain('мастерство «Оглушение»');
  expect(d).toContain('урон 1d8 рубящий');
});

test('оружие без урона не даёт «урон ,» с пустым местом', async ({ page }) => {
  // У Сети урона нет вовсе, и прежний шаблон печатал «урон , цена 1 зм» — висящая запятая
  // прямо в выдаче. Пустые факты в строку не попадают.
  const d = await facts(page, '/ru/dnd/srd-5.1/weapons/net/');
  expect(d).not.toContain('урон ,');
  expect(d).not.toMatch(/:\s*,/);
  expect(d).toContain('свойства:');
});

test('навык BRP: базовый шанс и категория впереди описания', async ({ page }) => {
  const d = await facts(page, '/en/brp/srd-1.0/skills/stealth/');
  expect(d).toContain('Basic Roleplaying');
  expect(d).toContain('base chance');
  expect(d.startsWith('Stealth —'), `начинается не с имени навыка: ${d}`).toBe(true);
});

test('навык BRP по-русски: та же формула, русские подписи', async ({ page }) => {
  // RU-ветка шаблона отдельная (падежи и кавычки-ёлочки), и её формулировку общий гейт по
  // dist не проверяет — он считает только длины. Отсюда отдельный тест на язык.
  const d = await facts(page, '/ru/brp/srd-1.0/skills/appraise/');
  expect(d.startsWith('Оценка — навык Basic Roleplaying:'), `не тот заход: ${d}`).toBe(true);
  expect(d).toContain('базовый шанс 15%');
  expect(d).toContain('категория «Ментальный»');
  // Английские подписи в русский сниппет не протекают.
  expect(d).not.toContain('base chance');
});

// ── Хабы, глоссарий и остальные шаблоны (issue #214, волна 2) ─────────────────

test('хаб перечисляет, что внутри, а не только считает', async ({ page }) => {
  // Соседние фасеты («монстры ПО 0» и «ПО 1») отличались только числом и значением фасета —
  // сниппеты выходили почти одинаковыми. Имена делают их и длиннее, и по-настоящему разными.
  const d = await facts(page, '/ru/dnd/srd-5.2/monsters-a-z/cr/0/');
  expect(d.length).toBeGreaterThanOrEqual(MIN);
  expect(d).toContain('Среди них:');
  const other = await facts(page, '/ru/dnd/srd-5.2/monsters-a-z/cr/1/');
  expect(d).not.toBe(other);
});

test('список в сниппете хаба режется по границе имени, а не посреди слова', async ({ page }) => {
  const d = await facts(page, '/en/dnd/srd-5.2/spells/level/0/');
  expect(d).toContain('Includes:');
  const list = d.split('Includes: ')[1];
  // Факт обрезки виден многоточием, целый список — точкой.
  expect(list.endsWith('…') || list.endsWith('.')).toBe(true);
  // Обрубленное имя в выдаче читается как ошибка вёрстки, поэтому режем по границе элемента.
  // Проверяем это по существу: последнее имя в сниппете должно быть настоящим именем со
  // страницы, а не его началом. Сравнение с текстом ссылки, а не с регекспом «похоже на слово».
  const names = list.replace(/[.…]$/, '').split(', ');
  const onPage = await page.locator('main a').allTextContents();
  expect(onPage.map((s) => s.trim())).toContain(names[names.length - 1]);
});

test('термин глоссария: определение целое, хвост добавлен только если влез', async ({ page }) => {
  const d = await facts(page, '/en/dnd/srd-5.1/rules-glossary/conditions/deafened/');
  // Главное: определение не обрезано ради служебной фразы — «…requires… A D&D 2014 Rules
  // Glossary condition» было бы обрубленным ответом ради хвоста.
  expect(d).toContain("can't hear and automatically fails any ability check that requires hearing.");
  expect(d).toContain('Rules Glossary condition');
});

test('маркер списка не уезжает в сниппет', async ({ page }) => {
  // Определения состояний в SRD оформлены списком, и сниппет начинался с «- A deafened…».
  for (const url of [
    '/en/dnd/srd-5.1/rules-glossary/conditions/deafened/',
    '/ru/dnd/srd-5.1/rules-glossary/conditions/incapacitated/',
  ]) {
    const d = await facts(page, url);
    expect(d.startsWith('-'), `сниппет начинается с маркера списка: ${d}`).toBe(false);
  }
});

test('доспех: требование Силы и помеха Скрытности в сниппете', async ({ page }) => {
  const d = await facts(page, '/ru/dnd/srd-5.2/armor/plate-armor/');
  expect(d.length).toBeGreaterThanOrEqual(MIN);
  expect(d).toContain('требование Силы 15');
  expect(d).toContain('помеха Скрытности');
});
