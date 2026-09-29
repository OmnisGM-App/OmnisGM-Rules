import { test, expect } from '@playwright/test';

// Глоссарии — noindex,follow и вне sitemap (#37), кроме справочников без entity-хаба (#106).
const GLOSSARY = '/en/dnd/srd-5.2/glossary/glossary/';  // индекс-термины 14_Glossary → noindex (не редиректится)
const CONTENT = '/en/dnd/srd-5.2/legal/';
const RULES_GLOSSARY = '/en/dnd/srd-5.2/rules-glossary/'; // реальная глава, НЕ /glossary/ — индексируется
const GLOSSARY_INDEXED = '/en/daggerheart/srd-1.0/glossary/weapons/'; // справочник без хаба → индексируем

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

test('справочник без хаба (#106): индексируем — без robots-meta, с hreflang', async ({ page }) => {
  await page.goto(GLOSSARY_INDEXED);
  await expect(page.locator('head meta[name="robots"]')).toHaveCount(0);
  await expect(page.locator('head link[rel="alternate"][hreflang]')).toHaveCount(3);
});

test('sitemap: содержит справочники без хаба (#106), но НЕ дубли/термы-глоссарий', async ({ page }) => {
  const res = await page.request.get('/sitemap-0.xml');
  expect(res.ok()).toBeTruthy();
  const xml = await res.text();
  expect(xml).toContain('/daggerheart/srd-1.0/glossary/weapons/');
  expect(xml).toContain('/brp/srd-1.0/glossary/armor/');
  // Дубли хабов (301) и оглавления-термины — НЕ в sitemap.
  expect(xml).not.toContain('/glossary/adversaries/');
  expect(xml).not.toContain('/glossary/skills/');
  expect(xml).not.toContain('/glossary/glossary/');
  expect(xml).not.toContain('/dnd/srd-5.2/glossary/');
});

test('индексируемый справочник имеет ровно один H1 с названием раздела (#228)', async ({ page }) => {
  // Markdown начинается сразу с таблицы — H1 дорисовывает шаблон nav-подписью, той же, что в <title>:
  // проверяем согласованность с <title>, а не константу.
  await page.goto(GLOSSARY_INDEXED);
  const h1 = page.locator('h1');
  await expect(h1).toHaveCount(1);
  const heading = (await h1.textContent())!.trim();
  expect(heading).toBe('Weapons (Reference)');
  expect(await page.title()).toContain(heading);
});

test('страница с собственным H1 второго не получает', async ({ page }) => {
  // Иначе фолбэк дорисовал бы заголовок и обычным главам — два H1.
  await page.goto(CONTENT);
  await expect(page.locator('h1')).toHaveCount(1);
});
