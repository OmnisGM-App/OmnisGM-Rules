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
