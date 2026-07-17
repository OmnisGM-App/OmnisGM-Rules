import { test, expect } from '@playwright/test';

// /all/-хабы D&D (issue #20): алфавитные индексы заклинаний/монстров/предметов/животных
// со ссылками на entity-страницы + фасеты. Заменили плоские глоссарий-списки в сайдбаре.

test('/all/-хабы рендерятся (5.2 + 5.1)', async ({ page }) => {
  for (const url of [
    '/ru/dnd/srd-5.2/spells/all/',
    '/en/dnd/srd-5.2/monsters-a-z/all/',
    '/ru/dnd/srd-5.2/magic-items/all/',
    '/en/dnd/srd-5.2/animals/all/',
    '/ru/dnd/srd-5.1/spells/all/',
    '/en/dnd/srd-5.1/monsters-a-z/all/',
    '/ru/dnd/srd-5.1/magic-items/all/',
  ]) {
    const res = await page.goto(url);
    expect(res?.status(), url).toBe(200);
    await expect(page.locator('.rd-doc h1')).toBeVisible();
  }
});

test('spells/all: ссылки на заклинание и класс-хаб', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/all/');
  await expect(page.locator('.hub-table a[href$="/spells/fireball/"]')).toBeVisible();
  await expect(page.locator('.hub-table a[href$="/spells/class/wizard/"]').first()).toBeVisible();
});

test('monsters-a-z/all: ссылки на монстра и type-хаб', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/monsters-a-z/all/');
  await expect(page.locator('.hub-table a[href$="/monsters-a-z/aboleth/"]')).toBeVisible();
  await expect(page.locator('.hub-table a[href*="/monsters-a-z/type/"]').first()).toBeVisible();
});

test('хаб в сайдбаре (глоссарий) виден и подсвечен; плоский список скрыт', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/all/');
  await expect(page.locator('.rd-nav a.rd-nav-active[href$="/spells/all/"]')).toBeVisible();
  await expect(page.locator('.rd-nav a[href$="/14_glossary/02_spells/"]')).toHaveCount(0);
});

test('заменённая глоссарий-страница жива и держит nav-контекст (не сирота)', async ({ page }) => {
  const res = await page.goto('/ru/dnd/srd-5.2/glossary/spells/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('.rd-doc')).toBeVisible();
  // Крошки/таб резолвятся через скрытый узел → активная система D&D 5.2, не «home»
  // (у сироты title был бы без «D&D SRD 5.2.1»).
  await expect(page).toHaveTitle(/D&D SRD 5\.2\.1/);
});

test('spells/all: уровень и школа кликабельны; школа-хаб рендерится', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/all/');
  // Уровень → level-хаб, школа → school-хаб (оба новые).
  await expect(page.locator('.hub-table a[href*="/spells/level/"]').first()).toBeVisible();
  const school = page.locator('.hub-table a[href*="/spells/school/"]').first();
  await expect(school).toBeVisible();
  const res = await page.goto('/en/dnd/srd-5.2/spells/school/evocation/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('.rd-doc h1')).toContainText('Evocation');
  await expect(page.locator('.hub-table a[href*="/spells/level/"]').first()).toBeVisible();
});

test('monsters/all + animals/all: ПО кликабельно → CR-хаб (у животных свой)', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/monsters-a-z/all/');
  await expect(page.locator('.hub-table a[href*="/monsters-a-z/cr/"]').first()).toBeVisible();
  await page.goto('/en/dnd/srd-5.2/animals/all/');
  const acr = page.locator('.hub-table a[href*="/animals/cr/"]').first();
  await expect(acr).toBeVisible();
  const res = await page.goto('/en/dnd/srd-5.2/animals/cr/0/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('.hub-table')).toBeVisible();
});

test('сортировка: клик по заголовку столбца переупорядочивает строки', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/monsters-a-z/all/');
  const firstBefore = await page.locator('.hub-table tbody tr td:first-child').first().textContent();
  const crHeader = page.locator('.hub-table[data-sortable] thead th').nth(3); // столбец «CR»
  await crHeader.click();
  await expect(crHeader).toHaveAttribute('aria-sort', 'ascending');
  const firstAfter = await page.locator('.hub-table tbody tr td:first-child').first().textContent();
  expect(firstAfter).not.toBe(firstBefore); // порядок изменился (алфавит → по CR)
});

test('SEO: hreflang-тройка + /all/-хабы в sitemap', async ({ page, request }) => {
  const res = await page.goto('/en/dnd/srd-5.2/spells/all/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('link[rel="alternate"][hreflang="x-default"]')).toHaveCount(1);
  const sm = await (await request.get('/sitemap-0.xml')).text();
  expect(sm).toContain('/dnd/srd-5.2/spells/all/');
  expect(sm).toContain('/dnd/srd-5.2/monsters-a-z/all/');
});
