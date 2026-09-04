import { test, expect } from '@playwright/test';

// Программные страницы животных (issue #20, Дорожка A):
// /{lang}/dnd/{ver}/animals/{slug}/. Стат-блок зеркалит монстра (КД/хиты/хар-ки/ПО),
// EN-имя в шапке, автолинк состояний в теле, related «тот же ПО», SEO (hreflang, sitemap).

test('страница животного: заголовок, EN-имя, тип, стат-блок', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/animals/wolf/');
  await expect(page.locator('.rd-doc h1')).toContainText('Волк');
  await expect(page.locator('.ent-en')).toHaveText('Wolf');
  await expect(page.locator('.mon-type')).toContainText('Зверь');
  const stat = page.locator('.mon-stat');
  await expect(stat.locator('.mon-row', { hasText: 'Класс доспеха' })).toBeVisible();
  await expect(stat.locator('.mon-row', { hasText: 'Показатель опасности' })).toContainText('1/4');
  // Таблица характеристик присутствует.
  await expect(stat.locator('.mon-abil')).toBeVisible();
});

test('в теле животного — автоссылка на состояние (Лежащий) + hovercard-таргет', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/animals/wolf/');
  const link = page.locator('.rd-doc a.ent-link[href*="/rules-glossary/conditions/prone/"]').first();
  await expect(link).toBeVisible();
  await expect(link).toHaveAttribute('data-hc', /conditions\/prone/);
});

test('related: другие животные того же ПО', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/animals/wolf/');
  const rel = page.locator('.ent-related');
  await expect(rel).toContainText('ПО 1/4');
  await expect(rel.locator('a[href*="/animals/"]').first()).toBeVisible();
});

test('SEO: hreflang-тройка, индексируема, в sitemap', async ({ page, request }) => {
  const res = await page.goto('/en/dnd/srd-5.2/animals/wolf/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="ru"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="x-default"]')).toHaveCount(1);
  await expect(page.locator('meta[name="robots"][content*="noindex"]')).toHaveCount(0);
  const sm = await (await request.get('/sitemap-0.xml')).text();
  expect(sm).toContain('/dnd/srd-5.2/animals/wolf/');
});
