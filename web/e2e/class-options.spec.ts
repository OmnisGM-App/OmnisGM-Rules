import { test, expect } from '@playwright/test';

// Страницы групп вариантов классовых умений (#379): /{lang}/dnd/srd-5.2/class-options/{group}/.

test('группа: все варианты на одной странице, якорь у каждого, индексируема, hreflang-тройка', async ({ page }) => {
  const res = await page.goto('/ru/dnd/srd-5.2/class-options/eldritch-invocations/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('.rd-doc h1')).toHaveText('Таинственные воззвания');
  await expect(page.getByTestId('class-option')).toHaveCount(28);
  await expect(page.locator('h2#agonizing-blast')).toHaveText('Мучительный заряд');
  await expect(page.getByTestId('class-option').filter({ has: page.locator('#agonizing-blast') }).locator('.class-option-meta'))
    .toContainText('Требование: Колдун 2-го уровня');
  await expect(page.locator('.class-option-lead a')).toHaveAttribute('href', '/ru/dnd/srd-5.2/classes/warlock/');
  await expect(page.locator('head meta[name="robots"]')).toHaveCount(0);
  await expect(page.locator('head link[rel="alternate"][hreflang]')).toHaveCount(3);
});

test('группа подкласса: лид называет подкласс; смешанная группа подписывает подкласс у варианта', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/class-options/hunter-s-prey/');
  await expect(page.locator('.class-option-lead')).toContainText('Умение подкласса Охотник класса Следопыт, с 3 уровня');
  await page.goto('/en/dnd/srd-5.2/class-options/cunning-strike/');
  const stealth = page.getByTestId('class-option').filter({ has: page.locator('#stealth-attack') });
  await expect(stealth.locator('.class-option-meta')).toContainText('Subclass: Thief');
  await expect(stealth.locator('.class-option-meta')).toContainText('Unlocked by');
});

test('группа двух классов: у варианта подписан класс', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/class-options/fighting-style/');
  const meta = page.getByTestId('class-option').locator('.class-option-meta');
  await expect(meta).toHaveCount(2);
  await expect(meta.nth(0)).toContainText('Paladin');
  await expect(meta.nth(1)).toContainText('Ranger');
});

test('хаб: запись в навигации, колонки таблицы, подкласс у группы подкласса, ссылка на группу', async ({ page }) => {
  const res = await page.goto('/en/dnd/srd-5.2/class-options/all/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('a[href="/en/dnd/srd-5.2/class-options/all/"]').first()).toBeAttached();
  const table = page.getByTestId('class-option-groups');
  await expect(table.locator('thead th')).toHaveText(['Group', 'Class', 'Level', 'Options']);
  await expect(table.locator('tr', { has: page.getByRole('link', { name: "Hunter's Prey" }) }).locator('td').nth(1)).toHaveText('Ranger (Hunter)');
  const metamagic = page.getByTestId('class-option-groups').getByRole('link', { name: 'Metamagic' });
  await expect(metamagic).toHaveAttribute('href', '/en/dnd/srd-5.2/class-options/metamagic/');
  await metamagic.click();
  await expect(page.locator('.rd-doc h1')).toHaveText('Metamagic');
});

test('глава класса ведёт на группу под заголовком умения; одноимённое умение другого класса — нет', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/classes/ranger/');
  await expect(page.locator('.class-option-link a')).toHaveCount(3);
  await expect(page.locator('.class-option-link a[href="/en/dnd/srd-5.2/class-options/hunter-s-prey/"]')).toHaveCount(1);
  await page.goto('/en/dnd/srd-5.2/classes/fighter/');
  await expect(page.locator('.class-option-link')).toHaveCount(0);
  await page.goto('/ru/dnd/srd-5.2/classes/warlock/');
  await expect(page.locator('.class-option-link a')).toHaveText('Все варианты «Таинственные воззвания» на одной странице →');
});
