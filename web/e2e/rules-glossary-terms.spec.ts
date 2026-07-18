import { test, expect } from '@playwright/test';

// Programmatic-страницы терминов Rules Glossary (issue #106): термины/действия/области эффекта
// главы 08_RulesGlossary — свои URL под /rules-glossary/{type}/{slug}/, индексируемы, со
// ссылкой-источником в главу правил (где источник известен из «See also»).

test('термин: страница рендерится, индексируема, hreflang-тройка', async ({ page }) => {
  const res = await page.goto('/ru/dnd/srd-5.2/rules-glossary/term/advantage/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('.rd-doc h1')).toContainText('Преимущество');
  await expect(page.locator('.ent-en')).toHaveText('Advantage');
  // Индексируема (НЕ /glossary/ → без noindex), с тройкой hreflang.
  await expect(page.locator('head meta[name="robots"]')).toHaveCount(0);
  await expect(page.locator('head link[rel="alternate"][hreflang]')).toHaveCount(3);
});

test('источник-ссылка (#106): термин ведёт в главу-раздел с точным якорем (RU и EN)', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/rules-glossary/term/advantage/');
  const src = page.locator('.ent-source a');
  await expect(src).toHaveAttribute('href', '/ru/dnd/srd-5.2/playing-the-game/#проверки-d20');
  await expect(src).toContainText('Процесс игры');

  await page.goto('/en/dnd/srd-5.2/rules-glossary/term/advantage/');
  await expect(page.locator('.ent-source a')).toHaveAttribute(
    'href', '/en/dnd/srd-5.2/playing-the-game/#d20-tests');
});

test('источник-якорь реально существует в целевой главе', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/playing-the-game/');
  await expect(page.locator('#d20-tests')).toHaveCount(1);
});

test('термин без главы-источника: страница жива, source-блока нет, upLink на глоссарий', async ({ page }) => {
  // adventure → «See also Encounter» (термин, не глава) → chapter-source-link не строится.
  const res = await page.goto('/en/dnd/srd-5.2/rules-glossary/term/adventure/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('.ent-source')).toHaveCount(0);
  await expect(page.locator('a[href$="/rules-glossary/"]').first()).toBeVisible();
});

test('действие: страница + список «Другие действия»', async ({ page }) => {
  const res = await page.goto('/ru/dnd/srd-5.2/rules-glossary/action/dash/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('.ent-related-h')).toContainText('Другие действия');
  await expect(page.locator('.ent-related-list a[href$="/action/dodge/"]')).toBeVisible();
});

test('область эффекта: страница рендерится', async ({ page }) => {
  const res = await page.goto('/en/dnd/srd-5.2/rules-glossary/area-of-effect/cone/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('.rd-doc h1')).toContainText('Cone');
});

test('канонический слаг EN↔RU: RU-термин на английском слаге', async ({ page }) => {
  expect((await page.goto('/ru/dnd/srd-5.2/rules-glossary/term/difficult-terrain/'))?.status()).toBe(200);
});

test('sitemap: страницы терминов включены (индексируются)', async ({ page }) => {
  const xml = await (await page.request.get('/sitemap-0.xml')).text();
  expect(xml).toContain('/dnd/srd-5.2/rules-glossary/term/advantage/');
  expect(xml).toContain('/dnd/srd-5.2/rules-glossary/action/dash/');
  expect(xml).toContain('/dnd/srd-5.2/rules-glossary/area-of-effect/cone/');
});
