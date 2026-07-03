import { test, expect } from '@playwright/test';

// Переключение языка EN → RU: кнопка RU ведёт на контрагент-страницу, <html lang> меняется.
test('тумблер языка переключает EN → RU', async ({ page }) => {
  await page.goto('/en/');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');

  await page.locator('.rd-lang-btn', { hasText: 'RU' }).click();

  await expect(page).toHaveURL(/\/ru\//);
  await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
});

// hreflang: три взаимных тега (en/ru/x-default) с абсолютными URL на каждой странице.
// Собираем { hreflang → href } из <head>. Проверяем ровно три ключа и абсолютность URL.
async function hreflangMap(page: import('@playwright/test').Page) {
  return page.$$eval('head link[rel="alternate"][hreflang]', (ls) =>
    Object.fromEntries(ls.map((l) => [l.getAttribute('hreflang'), l.getAttribute('href')])),
  );
}

const EN_CONTENT = '/en/dnd/srd-5.2/legal/';
const RU_CONTENT = '/ru/dnd/srd-5.2/legal/';

test('hreflang: контентная EN-страница — 3 абсолютных тега, x-default → EN', async ({ page }) => {
  await page.goto(EN_CONTENT);
  const m = await hreflangMap(page);
  expect(Object.keys(m).sort()).toEqual(['en', 'ru', 'x-default']);
  for (const href of Object.values(m)) expect(href).toMatch(/^https?:\/\//);
  expect(new URL(m.en!).pathname).toBe(EN_CONTENT);
  expect(new URL(m.ru!).pathname).toBe(RU_CONTENT);
  expect(m['x-default']).toBe(m.en); // на контентных x-default зеркалит EN-версию
});

test('hreflang: RU-пара выводит ту же тройку (взаимность)', async ({ page }) => {
  await page.goto(EN_CONTENT);
  const en = await hreflangMap(page);
  await page.goto(RU_CONTENT);
  const ru = await hreflangMap(page);
  expect(ru).toEqual(en); // взаимность: односторонний hreflang Google игнорирует
});

test('hreflang: хаб /en/ и корень / дают согласованную тройку', async ({ page }) => {
  await page.goto('/en/');
  const hub = await hreflangMap(page);
  expect(new URL(hub.en!).pathname).toBe('/en/');
  expect(new URL(hub.ru!).pathname).toBe('/ru/');
  expect(new URL(hub['x-default']!).pathname).toBe('/'); // хаб-кластер: x-default → корень

  await page.goto('/');
  const root = await hreflangMap(page);
  expect(root).toEqual(hub); // корень и хабы — один кластер, тройка совпадает
});
