import { test, expect } from '@playwright/test';

// Программные страницы снаряжения (issue #20, Дорожка A): /{lang}/dnd/{ver}/equipment/{slug}/.

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

// Составное снаряжение (#412): группа остаётся страницей на прежнем адресе, её предметы — под ней.
test('группа: прежний адрес, перечень предметов со ссылками, без перехода в компендиум', async ({ page }) => {
  const res = await page.goto('/ru/dnd/srd-5.2/equipment/musical-instrument/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('.rd-doc h1')).toContainText('Музыкальный инструмент');
  const items = page.getByTestId('equipment-group-items');
  await expect(items.locator('tbody tr')).toHaveCount(10);
  const lute = items.locator('a[href="/ru/dnd/srd-5.2/equipment/musical-instrument/lute/"]');
  await expect(lute).toHaveText('Лютня');
  await expect(items.locator('tr', { hasText: 'Лютня' })).toContainText('35 зм');
  // Группа — не запись компендиума Table: кнопки перехода на неё нет.
  await expect(page.locator('a[href*="omnisgm.com/compendium"]')).toHaveCount(0);
});

test('предмет группы: вложенный адрес, свои цена и вес, ссылка на группу и в компендиум', async ({ page }) => {
  const res = await page.goto('/ru/dnd/srd-5.2/equipment/musical-instrument/lute/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('.rd-doc h1')).toContainText('Лютня');
  const stat = page.locator('.item-stat');
  await expect(stat).toContainText('35 зм');
  await expect(stat).toContainText('2 фнт.');
  await expect(stat.locator('a[href="/ru/dnd/srd-5.2/equipment/musical-instrument/"]')).toHaveText('Музыкальный инструмент');
  await expect(page.locator('a[href*="/compendium/dnd2024/item/lute?"]').first()).toBeAttached();
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', /\/ru\/dnd\/srd-5\.2\/equipment\/musical-instrument\/lute\/$/);
});

test('пачка боеприпасов: число, хранение и цена пачки; плоского адреса нет', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/equipment/ammunition/');
  const row = page.getByTestId('equipment-group-items').locator('tr', { hasText: 'Arrows' });
  await expect(row).toContainText('20');
  await expect(row).toContainText('Quiver');
  await page.goto('/en/dnd/srd-5.2/equipment/ammunition/arrows/');
  await expect(page.locator('.rd-doc h1')).toContainText('Arrows');
  const stat = page.locator('.item-stat');
  await expect(stat).toContainText('1 GP');
  await expect(stat.locator('.item-row', { hasText: 'Amount' })).toContainText('20');
  await expect(stat.locator('.item-row', { hasText: 'Storage' })).toContainText('Quiver');
  const flat = await page.goto('/en/dnd/srd-5.2/equipment/arrows/');
  expect(flat?.status()).toBe(404);
});

test('«Изготовление» ведёт и на группу, и на обычный предмет', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/equipment/jeweler-s-tools/');
  const craft = page.locator('.item-stat .item-row', { hasText: 'Craft' });
  await expect(craft.locator('a[href$="/equipment/arcane-focus/"]')).toHaveText('Arcane Focus');
  await expect(craft.locator('a[href$="/equipment/holy-symbol/"]')).toHaveText('Holy Symbol');
});

test('глава: ячейка таблицы ведёт на предмет группы, строка общей таблицы — на группу', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/equipment/');
  await expect(page.locator('.rd-doc td a.ent-link[href$="/equipment/ammunition/arrows/"]').first()).toHaveText('Arrows');
  await expect(page.locator('.rd-doc td a.ent-link[href$="/equipment/arcane-focus/crystal/"]').first()).toHaveText('Crystal');
  await expect(page.locator('.rd-doc td a.ent-link[href$="/equipment/arcane-focus/"]').first()).toHaveText('Arcane Focus');
});
