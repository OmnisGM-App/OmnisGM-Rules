import { test, expect } from '@playwright/test';

// Стабильность макета: пока TOC помещается по ширине (десктоп), правый столбец
// зарезервирован ВСЕГДА — даже на страницах без оглавления (Legal, страницы сущностей).
// Иначе контент прыгает на ширину TOC при навигации со страницы с TOC на страницу без.
// Регрессия к «страница прыгает если панели нет, а потом есть».

test.use({ viewport: { width: 1280, height: 900 } });

test('правый столбец TOC зарезервирован и без оглавления — контент не прыгает', async ({ page }) => {
  // Страница С оглавлением: глава заклинаний (разделы уровней = много h2).
  await page.goto('/en/dnd/srd-5.2/spells/');
  await expect(page.locator('#rd-toc')).toBeVisible();
  const withToc = await page.locator('.rd-content').boundingBox();

  // Страница БЕЗ оглавления: правовая информация (нет h2/h3 → TOC не рендерится).
  await page.goto('/en/dnd/srd-5.2/legal/');
  await expect(page.locator('#rd-toc')).toHaveCount(0); // самой панели нет
  const noToc = await page.locator('.rd-content').boundingBox();

  // Но грид всё равно держит 3 колонки — место под TOC зарезервировано.
  const trackCount = await page.locator('.rd-body').evaluate(
    (el) => getComputedStyle(el).gridTemplateColumns.trim().split(/\s+/).length,
  );
  expect(trackCount).toBe(3);

  // Ключевое: ширина контентной колонки одинакова с TOC и без → нет горизонтального прыжка.
  expect(withToc).not.toBeNull();
  expect(noToc).not.toBeNull();
  expect(Math.abs(withToc!.width - noToc!.width)).toBeLessThanOrEqual(1);
});

test('страница сущности (состояние) не прыгает относительно главы с TOC', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/spells/');
  const withToc = await page.locator('.rd-content').boundingBox();

  // Страница состояния — headings=[] → TOC нет, но столбец зарезервирован.
  await page.goto('/en/dnd/srd-5.2/rules-glossary/conditions/frightened/');
  await expect(page.locator('#rd-toc')).toHaveCount(0);
  const entity = await page.locator('.rd-content').boundingBox();

  expect(Math.abs(withToc!.width - entity!.width)).toBeLessThanOrEqual(1);
});
