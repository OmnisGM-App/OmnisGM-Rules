import { test, expect } from '@playwright/test';

// Смоук ридера: страница правил открывается, рендерится бренд-шапка и nav-дерево.
test('главная ридера рендерит бренд-шапку и разделы', async ({ page }) => {
  await page.goto('/en/');

  await expect(page.locator('.rd-brand-name')).toHaveText('OmnisGM');
  await expect(page.locator('.rd-brand-sub')).toContainText('rules');

  // Слева — навигация по разделам (десктопный aside)
  await expect(page.locator('.rd-nav')).toBeVisible();

  // Панель вкладок систем (D&D / Daggerheart / BRP + поиск)
  await expect(page.locator('.rd-systabs')).toBeVisible();
});
