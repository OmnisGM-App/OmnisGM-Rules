import { test, expect } from '@playwright/test';

// Подсветка ключевых игромеханических слов (issue #20): характеристики/навыки/спасброски
// в тексте заклинаний и способностей монстров получают бренд-цвет (span.kw) — БЕЗ ссылки
// и БЕЗ hovercard (в отличие от .ent-link).

test('заклинание: спасбросок хар-ки подсвечен span.kw (не ссылка)', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/fireball/');
  const kw = page.locator('.rd-doc .kw');
  expect(await kw.count()).toBeGreaterThan(0);
  // «Ловкости» из «спасбросок Ловкости»
  await expect(kw.filter({ hasText: 'Ловкости' }).first()).toBeVisible();
  // Это НЕ ссылка и НЕ hovercard-таргет.
  await expect(page.locator('.rd-doc a.kw')).toHaveCount(0);
  await expect(page.locator('.rd-doc .kw[data-hc]')).toHaveCount(0);
});

test('монстр: хар-ки в тексте действий подсвечены (Ловкости, Харизму)', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/monsters-a-z/adult-red-dragon/');
  const kw = page.locator('.rd-doc .kw');
  expect(await kw.count()).toBeGreaterThan(0);
  await expect(kw.filter({ hasText: /^Ловкости$/ }).first()).toBeVisible();
  await expect(kw.filter({ hasText: /^Харизму$/ }).first()).toBeVisible();
});

test('список навыков класса: подсвечены ВСЕ, включая первый и последний', async ({ page }) => {
  // Таблица черт Варвара: «Выберите 2: Уход за животными, Атлетика, …, Внимательность или
  // Выживание». Раньше первый (после «2:») и последний (после «или») выпадали — навык
  // подсвечивался только после запятой. Список — единая группа: подсвечены все 6.
  await page.goto('/ru/dnd/srd-5.2/classes/barbarian/');
  const kw = page.locator('.rd-doc .kw');
  for (const skill of ['Уход за животными', 'Атлетика', 'Запугивание', 'Природа', 'Внимательность', 'Выживание']) {
    await expect(kw.filter({ hasText: new RegExp(`^${skill}$`) }).first()).toBeVisible();
  }
});

test('список навыков EN: первый и последний тоже подсвечены (Animal Handling … or Survival)', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/classes/barbarian/');
  const kw = page.locator('.rd-doc .kw');
  for (const skill of ['Animal Handling', 'Survival']) {
    await expect(kw.filter({ hasText: new RegExp(`^${skill}$`) }).first()).toBeVisible();
  }
});

test('подсветка НЕ трогает главы-определения (Как играть)', async ({ page }) => {
  // Глава «Как играть» определяет термины — там подсветки быть не должно (был бы ковёр).
  await page.goto('/ru/dnd/srd-5.2/playing-the-game/');
  await expect(page.locator('.rd-doc .kw')).toHaveCount(0);
});

test('hovercard-эндпоинт: EN-имя присутствует и в en-бакете (шапка всегда с оригиналом)', async ({ request }) => {
  const en = await (await request.get('/hc/dnd/srd52/en.json')).json();
  const cond = en['conditions/blinded'];
  expect(cond).toBeTruthy();
  // Для EN-сущности оригинал = само имя (раньше было null → шапка скрывалась).
  expect(cond.name_en).toBe(cond.name);
});
