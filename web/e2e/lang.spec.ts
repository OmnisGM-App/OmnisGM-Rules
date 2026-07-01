import { test, expect } from '@playwright/test';

// Переключение языка EN → RU: кнопка RU ведёт на контрагент-страницу, <html lang> меняется.
test('тумблер языка переключает EN → RU', async ({ page }) => {
  await page.goto('/en/');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');

  await page.locator('.rd-lang-btn', { hasText: 'RU' }).click();

  await expect(page).toHaveURL(/\/ru\//);
  await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
});
