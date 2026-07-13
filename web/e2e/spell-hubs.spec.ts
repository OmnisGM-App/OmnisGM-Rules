import { test, expect } from '@playwright/test';

// Хабы заклинаний (issue #20, SEO §2.3): фасетные списки по классу и уровню.
// Класс-хаб — секции H2 по уровням; уровень-хаб — таблица с колонкой классов (ссылки на класс-хабы).

test('класс-хаб: волшебник — секции по уровням + ссылки на заклинания (EN/RU симметрично)', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/class/wizard/');
  await expect(page.locator('h1')).toHaveText('Заклинания волшебника');
  // Секции уровней (заговоры + 1..9 = 10) и ссылка на конкретное заклинание.
  await expect(page.locator('.rd-doc h2[id^="lvl-"]')).toHaveCount(10);
  const fireball = page.locator('.hub-table a[href$="/spells/fireball/"]');
  await expect(fireball.first()).toBeVisible();
  // Симметрия: EN-хаб на том же (англ.) слаге, столько же ссылок на заклинания.
  const ruCount = await page.locator('.hub-table a[href*="/spells/"]').count();
  await page.goto('/en/dnd/srd-5.2/spells/class/wizard/');
  await expect(page.locator('h1')).toHaveText('Wizard Spells');
  expect(await page.locator('.hub-table a[href*="/spells/"]').count()).toBe(ruCount);
});

test('класс-хаб: ссылка на заклинание ведёт на его страницу', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/class/wizard/');
  await page.locator('.hub-table a[href$="/spells/fireball/"]').first().click();
  await expect(page).toHaveURL(/\/spells\/fireball\/$/);
  await expect(page.locator('h1')).toContainText('Огненный шар');
});

test('класс-хаб: перелинковка на другие классы и на уровни', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/class/wizard/');
  const links = page.locator('.hub-links');
  await expect(links.locator('a[href$="/spells/class/cleric/"]')).toBeVisible();
  await expect(links.locator('a[href$="/spells/level/3/"]')).toBeVisible();
});

test('уровень-хаб: 3 уровень — таблица заклинаний, классы ссылаются на класс-хабы', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/level/3/');
  await expect(page.locator('h1')).toHaveText('Заклинания 3 уровня');
  await expect(page.locator('.hub-table a[href$="/spells/fireball/"]').first()).toBeVisible();
  // В колонке «Классы» — ссылки на класс-хабы.
  await expect(page.locator('.hub-table a[href$="/spells/class/wizard/"]').first()).toBeVisible();
});

test('уровень-хаб: заговоры (level 0) — заголовок «Заговоры»', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/level/0/');
  await expect(page.locator('h1')).toHaveText('Заговоры');
  await page.goto('/en/dnd/srd-5.2/spells/level/0/');
  await expect(page.locator('h1')).toHaveText('Cantrips');
});

test('обратная перелинковка (PR C): страница заклинания ведёт в хабы классов и уровня', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/fireball/');
  const hubs = page.locator('.ent-hubs');
  await expect(hubs.locator('a[href$="/spells/class/wizard/"]')).toBeVisible();
  await expect(hubs.locator('a[href$="/spells/class/sorcerer/"]')).toBeVisible();
  await expect(hubs.locator('a[href$="/spells/level/3/"]')).toBeVisible();
});

test('SEO: класс-хаб самоканоничен + hreflang-тройка', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/class/wizard/');
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
    'href', 'https://rules.omnisgm.com/ru/dnd/srd-5.2/spells/class/wizard/');
  for (const hl of ['en', 'ru', 'x-default']) {
    await expect(page.locator(`link[rel="alternate"][hreflang="${hl}"]`)).toHaveCount(1);
  }
});
