import { test, expect } from '@playwright/test';

// Программные страницы происхождений SRD 5.2 (глава «Происхождение персонажа»): виды (species)
// и предыстории (backgrounds) + хаб-справочник. Виды — 5.2-аналог рас 5.1, но отдельный ресурс
// (независимо; страницы линкуют только 5.2).

test('entity-страницы происхождений 5.2 рендерятся', async ({ page }) => {
  for (const url of [
    '/ru/dnd/srd-5.2/species/dwarf/',
    '/en/dnd/srd-5.2/species/tiefling/',
    '/ru/dnd/srd-5.2/backgrounds/acolyte/',
    '/en/dnd/srd-5.2/backgrounds/soldier/',
  ]) {
    const res = await page.goto(url);
    expect(res?.status(), url).toBe(200);
    await expect(page.locator('.rd-doc h1')).toBeVisible();
  }
});

test('вид 5.2: EN-имя, автолинк расовых заклинаний, gloss (rules-terms есть), «другие виды»', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/species/tiefling/');
  await expect(page.locator('.rd-doc h1')).toContainText('Тифлинг');
  await expect(page.locator('.ent-en')).toHaveText('Tiefling');
  await expect(page.locator('.rd-doc a.ent-link[href="/ru/dnd/srd-5.2/spells/darkness/"]')).toBeVisible();
  // В 5.2 есть rules-terms → термины ядра глоссятся.
  await expect(page.locator('.rd-doc .gloss[data-hc*="rules-terms"]').first()).toBeVisible();
  await expect(page.locator('.ent-related a[href$="/species/elf/"]')).toBeVisible();
});

test('независимость: страница вида 5.2 линкует только srd-5.2, data-hc → srd52', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/species/dragonborn/');
  const doc = page.locator('.rd-doc');
  const hrefs = await doc.locator('a.ent-link').evaluateAll((els) =>
    els.map((e) => (e as HTMLAnchorElement).getAttribute('href') || ''));
  for (const h of hrefs) expect(h, `ent-link ${h}`).toContain('/dnd/srd-5.2/');
  const hc = await doc.locator('[data-hc]').evaluateAll((els) => els.map((e) => e.getAttribute('data-hc') || ''));
  for (const b of hc) expect(b, `data-hc ${b}`).toContain('dnd/srd52/');
});

test('канонический слаг EN↔RU: RU-вид/предыстория на англ. слаге', async ({ page }) => {
  expect((await page.goto('/ru/dnd/srd-5.2/species/goliath/'))?.status()).toBe(200);
  expect((await page.goto('/ru/dnd/srd-5.2/backgrounds/criminal/'))?.status()).toBe(200);
  // Кириллический слаг не существует.
  expect((await page.goto('/ru/dnd/srd-5.2/species/%D0%B3%D0%BE%D0%BB%D0%B8%D0%B0%D1%84/'))?.status()).toBe(404);
});

test('хаб происхождений: таблица видов и предысторий (сортируемая) + entity→хаб', async ({ page }) => {
  const res = await page.goto('/ru/dnd/srd-5.2/character-origins/all/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('.hub-table[data-sortable] a[href$="/species/human/"]')).toBeVisible();
  await expect(page.locator('.hub-table a[href$="/backgrounds/sage/"]')).toBeVisible();
  await expect(page.locator('.hub-table tbody td:first-child a')).toHaveCount(13); // 9 видов + 4 предыстории
  // Со страницы вида «в раздел» → хаб.
  await page.goto('/ru/dnd/srd-5.2/species/elf/');
  await expect(page.locator(`a[href$="/character-origins/all/"]`).first()).toBeVisible();
});

test('SEO происхождений: hreflang-тройка + в sitemap', async ({ page, request }) => {
  const res = await page.goto('/en/dnd/srd-5.2/species/orc/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="ru"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="x-default"]')).toHaveCount(1);
  const sm = await (await request.get('/sitemap-0.xml')).text();
  expect(sm).toContain('/dnd/srd-5.2/species/orc/');
  expect(sm).toContain('/dnd/srd-5.2/backgrounds/acolyte/');
});
