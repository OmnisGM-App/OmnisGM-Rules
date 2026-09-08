import { test, expect } from '@playwright/test';

// Смоук ридера: страница правил открывается, рендерится бренд-шапка и навигация по разделам.
//
// Навигация — единственное, что на узком экране устроено принципиально иначе: боковой aside
// скрывается, а разделы уезжают в выдвижную панель за кнопкой «Разделы». Поэтому проверка
// ветвится по ширине вьюпорта, а не игнорирует мобилу: «на телефоне до разделов не добраться»
// — это ровно тот дефект, ради которого мобильный проект и заведён (#286).
test('главная ридера рендерит бренд-шапку и разделы @cross-engine', async ({ page }) => {
  await page.goto('/en/');

  await expect(page.locator('.rd-brand-name')).toHaveText('OmnisGM');
  await expect(page.locator('.rd-brand-sub')).toContainText('rules');

  const narrow = (page.viewportSize()?.width ?? 0) < 900;
  if (narrow) {
    // Боковой aside по ширине скрыт — разделы открываются кнопкой и живут в панели-диалоге.
    await expect(page.locator('.rd-nav')).toBeHidden();
    await page.locator('.rd-act-nav').click();
    const drawer = page.locator('.rd-drawer');
    await expect(drawer).toBeVisible();
    await expect(drawer.locator('.rd-nav-page, .rd-nav-group').first()).toBeVisible();
  } else {
    await expect(page.locator('.rd-nav')).toBeVisible();
  }

  // Панель вкладок систем (D&D / Daggerheart / BRP + поиск) есть на обеих ширинах.
  await expect(page.locator('.rd-systabs')).toBeVisible();
});
