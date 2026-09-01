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
