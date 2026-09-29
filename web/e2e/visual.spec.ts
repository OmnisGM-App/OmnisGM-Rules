import { test, expect, type Page } from '@playwright/test';

// Визуальные снапшоты ридера; baseline — …-darwin.png. Обновление (без чистки .vite Vite отдаст
// старый бандл против нового кода):
//   rm -r node_modules/.vite && npm run test:e2e -- visual --update-snapshots

// Ждём готовности шрифтов — иначе снапшот дрожит на фолбэк-шрифтах.
async function settle(page: Page) {
  await page.evaluate(() => (document as any).fonts?.ready);
  await page.waitForLoadState('networkidle');
}

test('состояние — десктоп', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto('/en/dnd/srd-5.2/rules-glossary/conditions/frightened/');
  await settle(page);
  await expect(page).toHaveScreenshot('condition-desktop.png', { fullPage: true });
});

test('состояние — мобилка', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/ru/dnd/srd-5.2/rules-glossary/conditions/frightened/');
  await settle(page);
  await expect(page).toHaveScreenshot('condition-mobile.png', { fullPage: true });
});

test('резерв столбца TOC — Legal без панели (десктоп)', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto('/en/dnd/srd-5.2/legal/');
  await settle(page);
  await expect(page).toHaveScreenshot('legal-reserved-toc.png', {
    clip: { x: 0, y: 0, width: 1280, height: 900 },
  });
});

// Шапка сущности (#201/#202): CLS-тесты ловят прыжок, но не «портрет стал вдвое меньше». Клип по
// первому экрану: правка текста статблока ниже давала бы ложное расхождение.
const firstScreen = (w: number, h: number) => ({ clip: { x: 0, y: 0, width: w, height: h } });

test('шапка существа с портретом — десктоп', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto('/ru/dnd/srd-5.2/monsters-a-z/aboleth/');
  // Курсор от предыдущего теста даёт :hover в кадре — уводим за пределы контента.
  await page.mouse.move(0, 0);
  await settle(page);
  await expect(page).toHaveScreenshot('entity-portrait-desktop.png', firstScreen(1280, 900));
});

test('шапка существа с портретом — мобилка', async ({ page }) => {
  // На мобилке своя колонка (92 px) и свой размер портрета — отдельный кадр обязателен.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/ru/dnd/srd-5.2/monsters-a-z/aboleth/');
  await page.mouse.move(0, 0);
  await settle(page);
  await expect(page).toHaveScreenshot('entity-portrait-mobile.png', firstScreen(390, 844));
});
