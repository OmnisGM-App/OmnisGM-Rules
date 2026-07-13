import { test, expect } from '@playwright/test';

// Хабы монстров (issue #20, SEO §2.3, PR B): по типу (13) и по CR (одиночные 0–10 + диапазоны
// 11–16 / 17–30). Группировка по слагу через чистый EN-тип (RU-поле type непоследовательно).

test('тип-хаб: драконы — список + ссылки, EN/RU симметрично по числу монстров', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/monsters-a-z/type/dragon/');
  await expect(page.locator('h1')).toHaveText('Монстры типа «Дракон»');
  const ru = await page.locator('.hub-table tbody tr').count();
  expect(ru).toBeGreaterThan(30);
  await page.goto('/en/dnd/srd-5.2/monsters-a-z/type/dragon/');
  await expect(page.locator('h1')).toHaveText('Dragon Monsters');
  expect(await page.locator('.hub-table tbody tr').count()).toBe(ru);
});

test('тип-хаб: ссылка на монстра ведёт на его страницу', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/monsters-a-z/type/aberration/');
  await page.locator('.hub-table a[href$="/monsters-a-z/aboleth/"]').first().click();
  await expect(page).toHaveURL(/\/monsters-a-z\/aboleth\/$/);
  await expect(page.locator('h1')).toContainText('Aboleth');
});

test('CR-хаб: одиночный ПО 5 — все строки ровно CR 5', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/monsters-a-z/cr/5/');
  await expect(page.locator('h1')).toHaveText('Монстры с ПО 5');
  const crCells = await page.locator('.hub-table tbody tr td:nth-child(2)').allTextContents();
  expect(crCells.length).toBeGreaterThan(0);
  for (const c of crCells) expect(c.trim()).toBe('5');
  // Колонка типа ссылается на type-хаб.
  await expect(page.locator('.hub-table a[href*="/monsters-a-z/type/"]').first()).toBeVisible();
});

test('CR-хаб: диапазон 11–16 покрывает несколько CR + слаг дроби 1/2 → 1-2', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/monsters-a-z/cr/11-16/');
  await expect(page.locator('h1')).toHaveText('CR 11–16 Monsters');
  const crs = new Set(await page.locator('.hub-table tbody tr td:nth-child(2)').allTextContents());
  expect(crs.size).toBeGreaterThan(1); // диапазон, а не одно значение
  // Дробный CR — валидный слаг.
  await page.goto('/en/dnd/srd-5.2/monsters-a-z/cr/1-2/');
  await expect(page.locator('h1')).toContainText('CR 1/2');
});

test('SEO: тип-хаб самоканоничен + hreflang-тройка', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/monsters-a-z/type/dragon/');
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
    'href', 'https://rules.omnisgm.com/ru/dnd/srd-5.2/monsters-a-z/type/dragon/');
  for (const hl of ['en', 'ru', 'x-default']) {
    await expect(page.locator(`link[rel="alternate"][hreflang="${hl}"]`)).toHaveCount(1);
  }
});
