import { test, expect } from '@playwright/test';

test('404 отдаёт статус 404 и тёмный бренд-фон @cross-engine', async ({ page }) => {
  const resp = await page.goto('/no-such-page-xyz/');
  expect(resp?.status()).toBe(404);

  await expect(page.locator('.nf-code')).toHaveText('404');

  const probe = await page.evaluate(() => {
    const root = getComputedStyle(document.documentElement);
    return {
      ogBg: root.getPropertyValue('--og-bg').trim(), // tokens.css загружен?
      bodyBg: getComputedStyle(document.body).backgroundColor, // base.css применён?
    };
  });

  expect(probe.ogBg).not.toBe('');
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
