import { test, expect, type Page } from '@playwright/test';

// Визуальные регресс-снапшоты страниц ридера. Гоняются ЛОКАЛЬНО (как и весь e2e —
// в CI не тащим), baseline привязан к платформе (…-darwin.png) → на одной машине стабилен.
//
// Обновить baseline после осознанного изменения вида:
//   rm -rf node_modules/.vite && npm run test:e2e -- visual --update-snapshots
// (чистка .vite обязательна — иначе Astro/Vite отдаст старый бандл против нового кода; урок из Table.)

// Ждём готовности шрифтов (async Google Fonts) — иначе снапшот дрожит на фолбэк-шрифтах.
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
  // Первый экран: виден зарезервированный пустой правый столбец (регрессия «прыжка»).
  await expect(page).toHaveScreenshot('legal-reserved-toc.png', {
    clip: { x: 0, y: 0, width: 1280, height: 900 },
  });
});
