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
