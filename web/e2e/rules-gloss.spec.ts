import { test, expect } from '@playwright/test';

// Глоссинг терминов Rules Glossary (issue #20): действия (Dash/Dodge/…) в тексте получают
// hovercard-определение (span.gloss[data-hc], НЕ ссылка). Матчатся ТОЛЬКО в контексте
// «X action» (EN) / «действие X» (RU) — голые омонимы («Attack» ×499) не трогаются.

test('спелл: действие в тексте глоссится + наведение показывает определение', async ({ page }) => {
  // Bestow Curse: «…действие Уклонение…» → span.gloss на «Уклонение».
  await page.goto('/ru/dnd/srd-5.2/spells/bestow-curse/');
  const g = page.locator('.rd-doc .gloss[data-hc*="/actions/dodge"]', { hasText: 'Уклонение' }).first();
  await expect(g).toBeVisible();
  await g.hover();
  const card = page.locator('#ent-hovercard.is-open');
  await expect(card).toBeVisible();
  await expect(card.locator('.ent-hc-en')).toHaveText('Dodge');
  await expect(card.locator('.ent-hc-body')).toContainText('Уклонение');
});

test('глава класса: действие глоссится (EN и RU симметрично)', async ({ page }) => {
  // Воин: «take the Attack action» / «совершаете действие Атака» → gloss.
  await page.goto('/en/dnd/srd-5.2/classes/fighter/');
  await expect(page.locator('.rd-doc .gloss[data-hc*="/actions/attack"]').first()).toBeVisible();
  await page.goto('/ru/dnd/srd-5.2/classes/fighter/');
  await expect(page.locator('.rd-doc .gloss[data-hc*="/actions/attack"]').first()).toBeVisible();
});

test('точность: глосс действия стоит в контексте (за ним «action»)', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/classes/fighter/');
  // Каждый глосс действия на этой странице — часть «X action» (текст сразу после = " action…").
  const glosses = page.locator('.rd-doc .gloss[data-hc*="/actions/"]');
  const n = await glosses.count();
  expect(n).toBeGreaterThan(0);
  for (let i = 0; i < n; i++) {
    const tail = await glosses.nth(i).evaluate((el) => (el.nextSibling?.textContent || '').slice(0, 8));
    expect(tail.toLowerCase()).toMatch(/^\s+action/);
  }
});

test('hovercard-эндпоинт: есть карточки действий', async ({ request }) => {
  const ru = await (await request.get('/hc/dnd/srd52/ru.json')).json();
  expect(ru['actions/dash']?.name_en).toBe('Dash');
  expect(ru['actions/dash']?.effect).toContain('Рывок');
  expect(ru['actions/dodge']?.name_en).toBe('Dodge');
});

test('термин ядра: Концентрация глоссится + наведение показывает определение', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/bestow-curse/');
  const g = page.locator('.rd-doc .gloss[data-hc*="/rules-terms/concentration"]').first();
  await expect(g).toBeVisible();
  await g.hover();
  const card = page.locator('#ent-hovercard.is-open');
  await expect(card).toBeVisible();
  await expect(card.locator('.ent-hc-en')).toHaveText('Concentration');
});

test('термин ядра: многословный дистинктивный (Труднопроходимая местность) — EN и RU', async ({ page }) => {
  // Стем-матч ловит склонения RU; EN — точная фраза.
  await page.goto('/ru/dnd/srd-5.2/spells/arcane-hand/');
  await expect(page.locator('.rd-doc .gloss[data-hc*="/rules-terms/difficult-terrain"]').first()).toBeVisible();
  await page.goto('/en/dnd/srd-5.2/spells/arcane-hand/');
  await expect(page.locator('.rd-doc .gloss[data-hc*="/rules-terms/difficult-terrain"]').first()).toBeVisible();
});

test('безопасность: обычное слово (Cover/Укрытие) НЕ в наборе — не глоссится', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/rules-glossary/');
  await expect(page.locator('.gloss[data-hc*="/rules-terms/cover"]')).toHaveCount(0);
});

test('hovercard-эндпоинт: есть карточки терминов ядра', async ({ request }) => {
  const ru = await (await request.get('/hc/dnd/srd52/ru.json')).json();
  expect(ru['rules-terms/concentration']?.name_en).toBe('Concentration');
  expect(ru['rules-terms/difficult-terrain']?.name_en).toBe('Difficult Terrain');
  expect(ru['rules-terms/passive-perception']?.effect).toContain('Пассивная Внимательность');
});

test('термин ядра (батч 2): многословный (Долгий отдых) глоссится симметрично EN/RU', async ({ page }) => {
  // Глава класса «Воин» — «Long Rest» / «Долгий отдых» получают глосс на обеих локалях.
  await page.goto('/en/dnd/srd-5.2/classes/fighter/');
  await expect(page.locator('.rd-doc .gloss[data-hc*="/rules-terms/long-rest"]').first()).toBeVisible();
  await page.goto('/ru/dnd/srd-5.2/classes/fighter/');
  const g = page.locator('.rd-doc .gloss[data-hc*="/rules-terms/long-rest"]').first();
  await expect(g).toBeVisible();
  await g.hover();
  const card = page.locator('#ent-hovercard.is-open');
  await expect(card).toBeVisible();
  await expect(card.locator('.ent-hc-en')).toHaveText('Long Rest');
});

test('термин ядра (батч 2): дистинктивный однословный (Класс доспеха) без ложных на «класс»', async ({ page }) => {
  // «Класс доспеха» глоссится, а «класс» персонажа рядом — нет (стем требует «доспех»).
  await page.goto('/ru/dnd/srd-5.2/classes/monk/');
  await expect(page.locator('.rd-doc .gloss[data-hc*="/rules-terms/armor-class"]').first()).toBeVisible();
  // Ни один глосс armor-class не должен обойтись без слова «доспех» в тексте.
  const texts = await page.locator('.rd-doc .gloss[data-hc*="/rules-terms/armor-class"]').allTextContents();
  for (const t of texts) expect(t.toLowerCase()).toContain('доспех');
});

test('hovercard-эндпоинт: есть карточки терминов ядра батча 2', async ({ request }) => {
  const ru = await (await request.get('/hc/dnd/srd52/ru.json')).json();
  expect(ru['rules-terms/armor-class']?.name_en).toBe('Armor Class');
  expect(ru['rules-terms/long-rest']?.name_en).toBe('Long Rest');
  expect(ru['rules-terms/initiative']?.name_en).toBe('Initiative');
  expect(ru['rules-terms/challenge-rating']?.name_en).toBe('Challenge Rating');
  expect(ru['rules-terms/unarmed-strike']?.name_en).toBe('Unarmed Strike');
  expect((ru['rules-terms/unarmed-strike']?.effect || '').toLowerCase()).toContain('безоружный удар');
});

test('область эффекта: стат-блок заклинания — строка «Область» с глоссом формы', async ({ page }) => {
  // Конус холода: форма извлечена структурно из описания → строка «Область: Конус, 60 футов».
  await page.goto('/ru/dnd/srd-5.2/spells/cone-of-cold/');
  const row = page.locator('.spell-meta-row', { hasText: 'Область' });
  await expect(row).toContainText('Конус');
  await expect(row).toContainText('60 футов');
  const g = row.locator('.gloss[data-hc*="/areas-of-effect/cone"]');
  await expect(g).toBeVisible();
  await g.hover();
  const card = page.locator('#ent-hovercard.is-open');
  await expect(card).toBeVisible();
  await expect(card.locator('.ent-hc-en')).toHaveText('Cone');
});

test('область эффекта: EN — «N-foot Shape», форма глоссится (симметрия)', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/spells/fireball/');
  const row = page.locator('.spell-meta-row', { hasText: 'Area' });
  await expect(row).toContainText('20-foot-radius');
  await expect(row.locator('.gloss[data-hc*="/areas-of-effect/sphere"]')).toBeVisible();
});

test('hovercard-эндпоинт: есть карточки областей эффекта', async ({ request }) => {
  const ru = await (await request.get('/hc/dnd/srd52/ru.json')).json();
  expect(ru['areas-of-effect/cone']?.name_en).toBe('Cone');
  expect(ru['areas-of-effect/sphere']?.name_en).toBe('Sphere');
});
