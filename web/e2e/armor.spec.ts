import { test, expect } from '@playwright/test';

// Программные страницы доспехов (issue #20, Дорожка A): /{lang}/dnd/{ver}/armor/{slug}/.
// Тонкий стат-блок (КД/категория/требование Силы/скрытность/вес/цена). RU получает
// канонический (англ.) слаг + name_en через сверку стат-блоков EN↔RU → общий слаг, hreflang.

test('доспех: заголовок, EN-имя, категория, КД + требование Силы', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/armor/plate-armor/');
  await expect(page.locator('.rd-doc h1')).toContainText('Латы');
  await expect(page.locator('.ent-en')).toHaveText('Plate Armor');
  const stat = page.locator('.item-stat');
  await expect(stat.locator('.item-row', { hasText: 'Класс доспеха' })).toContainText('18');
  await expect(stat.locator('.item-row', { hasText: 'Требование Силы' })).toContainText('Сила 15');
  await expect(stat.locator('.item-row', { hasText: 'Скрытность' })).toContainText('помеха');
});

test('средний доспех: КД с модификатором Ловкости и капом', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/armor/breastplate/');
  await expect(page.locator('.item-stat .item-row', { hasText: 'Класс доспеха' }))
    .toContainText('14 + мод. Ловкости (макс. 2)');
});

test('щит: КД как бонус (+2 к КД)', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/armor/shield/');
  await expect(page.locator('.ent-en')).toHaveText('Shield');
  await expect(page.locator('.item-stat .item-row', { hasText: 'Класс доспеха' })).toContainText('+2 к КД');
});

test('канонический слаг: RU-доспех на англ. слаге, кириллического нет', async ({ page }) => {
  const ok = await page.goto('/ru/dnd/srd-5.2/armor/plate-armor/');
  expect(ok?.status()).toBe(200);
  // «Латы» кириллицей
  const cyr = await page.goto('/ru/dnd/srd-5.2/armor/%D0%BB%D0%B0%D1%82%D1%8B/');
  expect(cyr?.status()).toBe(404);
});

test('SEO: hreflang-тройка, индексируема, в sitemap', async ({ page, request }) => {
  const res = await page.goto('/en/dnd/srd-5.2/armor/plate-armor/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="ru"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="x-default"]')).toHaveCount(1);
  await expect(page.locator('meta[name="robots"][content*="noindex"]')).toHaveCount(0);
  const sm = await (await request.get('/sitemap-0.xml')).text();
  expect(sm).toContain('/dnd/srd-5.2/armor/plate-armor/');
});
