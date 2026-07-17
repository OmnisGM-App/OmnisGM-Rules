import { test, expect } from '@playwright/test';

// Programmatic-страницы Basic Roleplaying SRD 1.0: навыки (+by-category), профессии,
// точечные правила + хабы. Независимо от других систем: game=brp, свой бакет данных.

test('entity-страницы BRP рендерятся', async ({ page }) => {
  for (const url of [
    '/ru/brp/srd-1.0/skills/climb/',
    '/en/brp/srd-1.0/skills/first-aid/',
    '/ru/brp/srd-1.0/professions/cowboy/',
    '/en/brp/srd-1.0/professions/detective/',
    '/ru/brp/srd-1.0/spot-rules/ambush/',
    '/en/brp/srd-1.0/spot-rules/cover/',
  ]) {
    const res = await page.goto(url);
    expect(res?.status(), url).toBe(200);
    await expect(page.locator('.rd-doc h1')).toBeVisible();
  }
});

test('навык: EN-имя, мета (базовый шанс + категория), related по категории', async ({ page }) => {
  await page.goto('/ru/brp/srd-1.0/skills/climb/');
  await expect(page.locator('.rd-doc h1')).toContainText('Лазание');
  await expect(page.locator('.ent-en')).toHaveText('Climb');
  const meta = page.locator('.ent-meta');
  await expect(meta).toContainText('40%');
  await expect(meta.locator('a[href$="/skills/category/physical/"]')).toBeVisible();
  // related — навыки той же категории (Physical), напр. Jump/Hide.
  await expect(page.locator('.ent-related a').first()).toBeVisible();
});

test('независимость: страница BRP не содержит ссылок на D&D/Daggerheart', async ({ page }) => {
  await page.goto('/en/brp/srd-1.0/skills/dodge/');
  const doc = page.locator('.rd-doc');
  const links = await doc.locator('a').evaluateAll((els) =>
    els.map((e) => (e as HTMLAnchorElement).getAttribute('href') || ''));
  for (const h of links) {
    expect(h.includes('/dnd/'), `link ${h}`).toBeFalsy();
    expect(h.includes('/daggerheart/'), `link ${h}`).toBeFalsy();
  }
});

test('канонический слаг EN↔RU: RU-сущность на английском слаге', async ({ page }) => {
  expect((await page.goto('/ru/brp/srd-1.0/skills/first-aid/'))?.status()).toBe(200);
  expect((await page.goto('/ru/brp/srd-1.0/professions/cowboy/'))?.status()).toBe(200);
  expect((await page.goto('/ru/brp/srd-1.0/spot-rules/ambush/'))?.status()).toBe(200);
  // Кириллический слаг не существует.
  expect((await page.goto('/ru/brp/srd-1.0/skills/%D0%BB%D0%B0%D0%B7%D0%B0%D0%BD%D0%B8%D0%B5/'))?.status()).toBe(404);
});

test('хабы: сортируемые таблицы навыков (+фасет категории), профессий, правил', async ({ page }) => {
  expect((await page.goto('/ru/brp/srd-1.0/skills/all/'))?.status()).toBe(200);
  await expect(page.locator('.hub-table[data-sortable] a[href$="/skills/climb/"]')).toBeVisible();
  // «Категория» кликабельна в колонке таблицы + в футере.
  await expect(page.locator('.hub-table[data-sortable] a[href*="/skills/category/"]').first()).toBeVisible();
  await expect(page.locator('.hub-links a[href$="/skills/category/combat/"]')).toBeVisible();

  expect((await page.goto('/en/brp/srd-1.0/skills/category/physical/'))?.status()).toBe(200);
  await expect(page.locator('a[href$="/skills/climb/"]')).toBeVisible();

  expect((await page.goto('/ru/brp/srd-1.0/professions/all/'))?.status()).toBe(200);
  await expect(page.locator('.hub-table[data-sortable] a[href$="/professions/detective/"]')).toBeVisible();

  expect((await page.goto('/en/brp/srd-1.0/spot-rules/all/'))?.status()).toBe(200);
  await expect(page.locator('.hub-table[data-sortable] a[href$="/spot-rules/ambush/"]')).toBeVisible();
});

test('автолинк: таблица навыков в глоссарии линкует навыки (grid-режим) + hovercard', async ({ page }) => {
  await page.goto('/ru/brp/srd-1.0/glossary/skills/');
  const link = page.locator('.rd-doc a.ent-link[href*="/skills/"][data-hc^="brp/srd10/ru/skills/"]').first();
  await expect(link).toBeVisible();
});

test('SEO: hreflang-тройка + сущности в sitemap', async ({ page, request }) => {
  const res = await page.goto('/en/brp/srd-1.0/skills/dodge/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="ru"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="x-default"]')).toHaveCount(1);
  const sm = await (await request.get('/sitemap-0.xml')).text();
  expect(sm).toContain('/brp/srd-1.0/skills/dodge/');
  expect(sm).toContain('/brp/srd-1.0/professions/cowboy/');
  expect(sm).toContain('/brp/srd-1.0/spot-rules/ambush/');
});

test('хаб-справочники BRP — в боковом меню (группа «Глоссарий»), плоский список скрыт', async ({ page }) => {
  await page.goto('/ru/brp/srd-1.0/skills/climb/');
  // Наш entity-хаб виден в сайдбаре и подсвечен (currentId страницы навыка → хаб).
  await expect(page.locator('.rd-nav a.rd-nav-active[href$="/skills/all/"]')).toBeVisible();
  // Заменённый плоский глоссарий-список навыков скрыт из дерева (страница живёт по URL).
  await expect(page.locator('.rd-nav a[href$="/brp/srd-1.0/glossary/skills/"]')).toHaveCount(0);
});
