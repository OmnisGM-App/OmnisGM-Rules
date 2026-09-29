import { test, expect } from '@playwright/test';

// Программные страницы магических предметов (issue #20, волна 3): /{lang}/dnd/{ver}/magic-items/{slug}/.

test('страница предмета: заголовок, EN-имя, тип·редкость, стат-блок', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/magic-items/dwarven-thrower/');
  await expect(page.locator('.rd-doc h1')).toContainText('Дварфийский метатель');
  await expect(page.locator('.ent-en')).toHaveText('Dwarven Thrower');
  await expect(page.locator('.item-meta-line')).toContainText('очень редкий'); // редкость локализована
  const stat = page.locator('.item-stat');
  await expect(stat).toContainText('Тип');
  await expect(stat).toContainText('Редкость');
  await expect(stat.locator('.item-row', { hasText: 'Настройка' })).toContainText('требуется');
  await expect(stat.locator('.item-row', { hasText: 'Настройка' })).toContainText('дварф'); // Belt of Dwarvenkind (5.2)
});

test('related: другие предметы того же типа', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/magic-items/dwarven-thrower/');
  const rel = page.locator('.ent-related');
  await expect(rel).toContainText('Оружие');
  await expect(rel.locator('a[href*="/magic-items/"]').first()).toBeVisible();
});

test('канонический слаг для вложенных скобок (Stone of Good Luck) — EN и RU совпадают', async ({ page }) => {
  // Вложенная скобка «Камень удачи (Камень везения) (Stone of Good Luck (Luckstone))» — слаг stone-of-good-luck.
  for (const lang of ['en', 'ru']) {
    const res = await page.goto(`/${lang}/dnd/srd-5.2/magic-items/stone-of-good-luck/`);
    expect(res?.status(), `${lang} страница существует`).toBe(200);
  }
  await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="ru"]')).toHaveCount(1);
});

test('SEO: hreflang-тройка, индексируема, в sitemap', async ({ page, request }) => {
  const res = await page.goto('/en/dnd/srd-5.2/magic-items/bag-of-holding/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="ru"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="x-default"]')).toHaveCount(1);
  await expect(page.locator('meta[name="robots"][content*="noindex"]')).toHaveCount(0);
  const sm = await (await request.get('/sitemap-0.xml')).text();
  expect(sm).toContain('/dnd/srd-5.2/magic-items/bag-of-holding/');
});
