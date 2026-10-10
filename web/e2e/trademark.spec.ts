import { test, expect } from '@playwright/test';

// Товарные знаки (Table#912): CC BY 4.0 не покрывает знаки Dungeons & Dragons и D&D, поэтому строка
// о них стоит в футере каждой страницы — хабов, контента D&D и чужих систем — на языке страницы.
const EN = 'Dungeons & Dragons and D&D are trademarks of Wizards of the Coast LLC. OmnisGM is an independent project, not affiliated with or endorsed by Wizards of the Coast.';
const RU = 'Dungeons & Dragons и D&D — товарные знаки Wizards of the Coast LLC. OmnisGM — независимый проект, не связан с Wizards of the Coast и не одобрен ею.';

for (const [url, text] of [
  ['/en/', EN],
  ['/ru/', RU],
  ['/en/dnd/srd-5.2/spells/fireball/', EN],
  ['/ru/dnd/srd-5.1/spells/fireball/', RU],
  ['/en/daggerheart/srd-1.0/ancestries/clank/', EN],
  ['/ru/daggerheart/srd-1.0/ancestries/dwarf/', RU],
] as const) {
  test(`строка о товарных знаках: ${url}`, async ({ page }) => {
    await page.goto(url);
    await expect(page.getByTestId('trademark')).toHaveText(text);
  });
}

test('строка о товарных знаках на двуязычном корне — на языке посетителя', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('trademark').locator('.l-en')).toHaveText(EN);
  await page.evaluate(() => { document.documentElement.dataset.rootlang = 'ru'; });
  await expect(page.getByTestId('trademark').locator('.l-ru')).toBeVisible();
  await expect(page.getByTestId('trademark').locator('.l-ru')).toHaveText(RU);
  await expect(page.getByTestId('trademark').locator('.l-en')).toBeHidden();
});

test('BRP: атрибуция говорит, что Chaosium проект не одобряла', async ({ page }) => {
  await page.goto('/en/brp/srd-1.0/');
  await expect(page.locator('.rd-attrib')).toContainText('Not affiliated with or endorsed by Chaosium Inc.');
});
