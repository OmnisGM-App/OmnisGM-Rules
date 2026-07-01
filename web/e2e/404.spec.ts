import { test, expect } from '@playwright/test';

// Регресс-guard выноса бренда: 404 должна тянуть @omnisgm-app/brand/base.css (тёмный фон
// body), а не остаться на дефолтном белом. Ровно этот баг был, когда на 404 забыли импорт
// base.css — шапка/подвал тёмные, а середина белая. См. web/src/pages/404.astro.
test('404 отдаёт статус 404 и тёмный бренд-фон', async ({ page }) => {
  const resp = await page.goto('/no-such-page-xyz/');
  expect(resp?.status()).toBe(404);

  // Контент 404 отрисован
  await expect(page.locator('.nf-code')).toHaveText('404');

  const probe = await page.evaluate(() => {
    const root = getComputedStyle(document.documentElement);
    return {
      ogBg: root.getPropertyValue('--og-bg').trim(), // tokens.css загружен?
      bodyBg: getComputedStyle(document.body).backgroundColor, // base.css применён?
    };
  });

  // tokens.css на месте — переменная определена
  expect(probe.ogBg).not.toBe('');
  // base.css применён — у body есть непрозрачный фон (это и был симптом регрессии)
  expect(probe.bodyBg).not.toBe('rgba(0, 0, 0, 0)');
  expect(probe.bodyBg).not.toBe('transparent');

  // И этот фон тёмный, а не белый (если сериализовалось в rgb — считаем яркость)
  const nums = probe.bodyBg.match(/[\d.]+/g)?.map(Number);
  if (nums && nums.length >= 3) {
    const [r, g, b] = nums;
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    expect(luminance).toBeLessThan(0.3);
  }
});
