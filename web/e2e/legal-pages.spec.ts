import { test, expect } from '@playwright/test';

// Лицензии систем (#397): Legal каждой системы несёт формулу своей лицензии, футер раздела — свою
// атрибуцию (модификации SRD для CC BY §3(a)(1)(B), Open Game Content для BRP §9), логотип BRP ведёт
// на страницу BRP SRD и его лицензии, а не на ORC. Литералы — свои, не из шелла.
const BRP_SRD = 'https://www.chaosium.com/brp-system-reference-document/';

for (const [url, text] of [
  ['/en/dnd/srd-5.2/legal/', 'Creative Commons Attribution 4.0'],
  ['/ru/dnd/srd-5.2/legal/', 'Creative Commons Attribution 4.0'],
  ['/en/dnd/srd-5.1/legal/', 'Creative Commons Attribution 4.0'],
  ['/en/daggerheart/srd-1.0/legal/', 'Darrington Press Community Gaming'],
  ['/en/brp/srd-1.0/legal/', 'Open Game Content on OmnisGM Rules (Section 9)'],
  ['/ru/brp/srd-1.0/legal/', 'Open Game Content на OmnisGM Rules (раздел 9)'],
] as const) {
  test(`Legal: формула лицензии на ${url}`, async ({ page }) => {
    await page.goto(url);
    await expect(page.locator('.rd-doc')).toContainText(text);
  });
}

for (const [url, text] of [
  ['/en/dnd/srd-5.2/spells/fireball/', 'Converted to Markdown, split into pages and cross-linked by OmnisGM.'],
  ['/ru/dnd/srd-5.2/spells/fireball/', 'Перевод на русский, конвертация в Markdown, разбивка на страницы и перекрёстные ссылки — OmnisGM.'],
  ['/en/brp/srd-1.0/', 'The rules text on these pages is Open Game Content, excluding Prohibited Content (Section 1(e)) and Chaosium’s trademarks; the site design, navigation, images and code are not.'],
  ['/ru/brp/srd-1.0/', 'Текст правил на этих страницах, включая перевод, — Open Game Content, кроме Prohibited Content (раздел 1(e)) и товарных знаков Chaosium; оформление сайта, навигация, картинки и код — нет.'],
] as const) {
  test(`футер: атрибуция с модификациями / OGC на ${url}`, async ({ page }) => {
    await page.goto(url);
    await expect(page.locator('.rd-attrib')).toContainText(text);
  });
}

test('логотип «Powered by BRP» ведёт на BRP SRD, а не на ORC', async ({ page }) => {
  await page.goto('/en/brp/srd-1.0/');
  await expect(page.locator('.rd-attrib-logo')).toHaveAttribute('href', BRP_SRD);
});

test('хаб и главная не заявляют связь BRP с Call of Cthulhu / RuneQuest (BRP OGL §8)', async ({ page }) => {
  for (const url of ['/', '/en/', '/ru/', '/en/brp/srd-1.0/', '/ru/brp/srd-1.0/']) {
    await page.goto(url);
    // Текст самого SRD (глава 1 упоминает игры Chaosium) — за пределами хаба и главной.
    await expect(page.locator('main'), url).not.toContainText(/Call of Cthulhu|RuneQuest/);
  }
});
