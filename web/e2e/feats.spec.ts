import { test, expect } from '@playwright/test';

// Программные страницы черт (issue #20, Дорожка A):
// /{lang}/dnd/{ver}/feats/{slug}/. Шапка (EN-имя, категория), стат-блок, автолинк в теле,
// related «та же категория», SEO (hreflang, sitemap, индексируемость).

test('страница черты: заголовок, EN-имя, категория, стат-блок', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/feats/alert/');
  await expect(page.locator('.rd-doc h1')).toContainText('Бдительность');
  await expect(page.locator('.ent-en')).toHaveText('Alert');
  await expect(page.locator('.item-meta-line')).toContainText('происхождения');
  const stat = page.locator('.item-stat');
  await expect(stat.locator('.item-row', { hasText: 'Категория' })).toContainText('происхождения');
});

test('стат-блок черты: хар-ки в «Требовании» подсвечены span.kw (как в теле)', async ({ page }) => {
  // Борец (grappler): «Требование: Уровень 4+, Сила или Ловкость 13+» — Сила/Ловкость должны
  // быть красными, как в описании ниже (консистентность стат-блок ↔ тело).
  await page.goto('/ru/dnd/srd-5.2/feats/grappler/');
  const req = page.locator('.item-stat .item-row', { hasText: 'Требование' });
  await expect(req.locator('.kw', { hasText: 'Сила' }).first()).toBeVisible();
  await expect(req.locator('.kw', { hasText: 'Ловкость' }).first()).toBeVisible();
});

test('в теле черты — автоссылка на состояние (Недееспособный) + hovercard-таргет', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/feats/alert/');
  const link = page.locator('.rd-doc a.ent-link[href*="/rules-glossary/conditions/incapacitated/"]').first();
  await expect(link).toBeVisible();
  await expect(link).toHaveAttribute('data-hc', /conditions\/incapacitated/);
});

test('related: другие черты той же категории', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/feats/alert/');
  const rel = page.locator('.ent-related');
  await expect(rel).toContainText('происхождения');
  await expect(rel.locator('a[href*="/feats/"]').first()).toBeVisible();
});

test('SEO: hreflang-тройка, индексируема, в sitemap', async ({ page, request }) => {
  const res = await page.goto('/en/dnd/srd-5.2/feats/alert/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="ru"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="x-default"]')).toHaveCount(1);
  await expect(page.locator('meta[name="robots"][content*="noindex"]')).toHaveCount(0);
  const sm = await (await request.get('/sitemap-0.xml')).text();
  expect(sm).toContain('/dnd/srd-5.2/feats/alert/');
});
