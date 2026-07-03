import { test, expect } from '@playwright/test';

// Глоссарные страницы (справочные таблицы) выведены из индекса: meta noindex,follow
// + исключены из sitemap (issue #37). Контентные страницы — индексируемы как прежде.
const GLOSSARY = '/en/dnd/srd-5.2/glossary/spells/';
const CONTENT = '/en/dnd/srd-5.2/legal/';
const RULES_GLOSSARY = '/en/dnd/srd-5.2/rules-glossary/'; // реальная глава, НЕ /glossary/ — индексируется

test('глоссарий: noindex,follow и без hreflang', async ({ page }) => {
  await page.goto(GLOSSARY);
  await expect(page.locator('head meta[name="robots"]')).toHaveAttribute(
    'content',
    'noindex, follow',
  );
  await expect(page.locator('head link[rel="alternate"][hreflang]')).toHaveCount(0);
});

test('контентная страница: индексируема (без robots-meta) и с тройкой hreflang', async ({ page }) => {
  await page.goto(CONTENT);
  await expect(page.locator('head meta[name="robots"]')).toHaveCount(0);
  await expect(page.locator('head link[rel="alternate"][hreflang]')).toHaveCount(3);
});

test('rules-glossary — контентная глава, НЕ noindex', async ({ page }) => {
  await page.goto(RULES_GLOSSARY);
  await expect(page.locator('head meta[name="robots"]')).toHaveCount(0);
});

test('sitemap не содержит /glossary/', async ({ page }) => {
  const res = await page.request.get('/sitemap-0.xml');
  expect(res.ok()).toBeTruthy();
  const xml = await res.text();
  expect(xml).not.toContain('/glossary/');
});
