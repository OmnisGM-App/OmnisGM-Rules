import { test, expect } from '@playwright/test';
import { isNarrow } from './viewport';

test('главная ридера рендерит бренд-шапку и разделы @cross-engine', async ({ page }) => {
  await page.goto('/en/');

  await expect(page.locator('.rd-brand-name')).toHaveText('OmnisGM');
  await expect(page.locator('.rd-brand-sub')).toContainText('rules');

  if (isNarrow(page)) {
    await expect(page.locator('.rd-nav')).toBeHidden();

    // Панель закрыта сдвигом (`translateX(-100%)`, reader.css): `toBeVisible()` видит её всегда —
    // смотрим геометрию.
    const drawer = page.locator('.rd-drawer');
    const closed = await drawer.boundingBox();
    expect(closed, 'панель разделов должна быть в DOM до открытия').not.toBeNull();
    expect(closed!.x + closed!.width).toBeLessThanOrEqual(1);

    await page.locator('.rd-act-nav').click();

    // Панель выезжает transition'ом — ждём геометрию: мгновенный boundingBox ловит середину анимации.
    await expect
      .poll(async () => (await drawer.boundingBox())?.x ?? -1, { timeout: 5000 })
      .toBeGreaterThanOrEqual(0);

    const opened = await drawer.boundingBox();
    expect(opened!.width).toBeGreaterThan(100);
    const item = drawer.locator('.rd-nav-page, .rd-nav-group').first();
    const itemBox = await item.boundingBox();
    expect(itemBox, 'в панели нет ни одного раздела').not.toBeNull();
    expect(itemBox!.x).toBeGreaterThanOrEqual(0);
  } else {
    await expect(page.locator('.rd-nav')).toBeVisible();
    await expect(page.locator('.rd-systabs')).toBeVisible();
  }
});
