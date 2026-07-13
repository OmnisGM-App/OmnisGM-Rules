import { test, expect } from '@playwright/test';

// Программные страницы снаряжения (issue #20, Дорожка A):
// /{lang}/dnd/{ver}/equipment/{slug}/. Зеркало маг. предмета: стат-блок (категория/стоимость/
// вес; у инструментов — характеристика/использование/изготовление), автолинк состояний в теле,
// related «та же категория», SEO (hreflang, sitemap).

test('снаряжение: заголовок, EN-имя, категория, стоимость', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/equipment/acid/');
  await expect(page.locator('.rd-doc h1')).toContainText('Кислота');
  await expect(page.locator('.ent-en')).toHaveText('Acid');
  const stat = page.locator('.item-stat');
  await expect(stat.locator('.item-row', { hasText: 'Категория' })).toContainText('Снаряжение');
  await expect(stat.locator('.item-row', { hasText: 'Стоимость' })).toContainText('25 зм');
});

test('инструмент: характеристика, использование, изготовление со ссылками', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/equipment/alchemist-s-supplies/');
  const stat = page.locator('.item-stat');
  await expect(stat.locator('.item-row', { hasText: 'Характеристика' })).toContainText('Интеллект');
  await expect(stat.locator('.item-row', { hasText: 'Использование' })).toBeVisible();
  // Пункт «Изготовление» линкует на страницу изготавливаемого снаряжения.
  await expect(
    stat.locator('.item-row', { hasText: 'Изготовление' })
      .locator('a.ent-link[href$="/equipment/acid/"]'),
  ).toBeVisible();
});

test('в теле снаряжения — автоссылка на состояние (Сеть → Опутанный)', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/equipment/net/');
  const link = page.locator('.rd-doc a.ent-link[href*="/rules-glossary/conditions/restrained/"]').first();
  await expect(link).toBeVisible();
  await expect(link).toHaveAttribute('data-hc', /conditions\/restrained/);
});

test('related: другое снаряжение той же категории', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/equipment/alchemist-s-supplies/');
  const rel = page.locator('.ent-related');
  await expect(rel).toContainText('Инструменты');
  await expect(rel.locator('a[href*="/equipment/"]').first()).toBeVisible();
});

test('SEO: hreflang-тройка, индексируема, в sitemap', async ({ page, request }) => {
  const res = await page.goto('/en/dnd/srd-5.2/equipment/acid/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="ru"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="x-default"]')).toHaveCount(1);
  await expect(page.locator('meta[name="robots"][content*="noindex"]')).toHaveCount(0);
  const sm = await (await request.get('/sitemap-0.xml')).text();
  expect(sm).toContain('/dnd/srd-5.2/equipment/acid/');
});
