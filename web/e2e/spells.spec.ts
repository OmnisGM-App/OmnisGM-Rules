import { test, expect } from '@playwright/test';

// Программные страницы заклинаний (issue #20, волна 2): /{lang}/dnd/{ver}/spells/{slug}/.
// Стат-блок, ссылки классов/подклассов, тултип компонентов, автоссылки состояний + hovercard,
// SEO (hreflang, sitemap, индексируемость), нормализация школы.

test('страница заклинания: заголовок, EN-имя, стат-блок', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/fireball/');
  await expect(page.locator('.rd-doc h1')).toContainText('Огненный шар');
  await expect(page.locator('.ent-en')).toHaveText('Fireball');
  await expect(page.locator('.spell-lvl')).toHaveText('3-й уровень, Воплощения'); // школа нормализована
  const meta = page.locator('.spell-meta');
  await expect(meta).toContainText('Время накладывания');
  await expect(meta).toContainText('Дистанция');
  await expect(meta).toContainText('Длительность');
});

test('компоненты В/С/М — abbr с подсказкой (полное слово в title)', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/fireball/');
  const abbrs = page.locator('.spell-meta abbr');
  await expect(abbrs).toHaveCount(3);
  await expect(abbrs.nth(0)).toHaveAttribute('title', 'Вербальный');
  await expect(abbrs.nth(1)).toHaveAttribute('title', 'Соматический');
  await expect(abbrs.nth(2)).toHaveAttribute('title', 'Материальный');
});

test('классы и подклассы — ссылки на страницы классов', async ({ page }) => {
  // Aid даётся Домом жизни (Жрец) и Клятвой преданности (Паладин).
  await page.goto('/ru/dnd/srd-5.2/spells/aid/');
  const meta = page.locator('.spell-meta');
  // класс-ссылка «Жрец» (точное совпадение — подкласс тоже ведёт на cleric, но текст «Жрец: …»)
  await expect(meta.locator('a[href="/ru/dnd/srd-5.2/classes/cleric/"]', { hasText: /^Жрец$/ })).toBeVisible();
  // строка подклассов: формат «Класс: Подкласс», ссылка на страницу класса
  await expect(meta).toContainText('Подклассы');
  await expect(meta.locator('a[href="/ru/dnd/srd-5.2/classes/cleric/"]', { hasText: 'Жрец: Домен жизни' })).toBeVisible();
  await expect(meta.locator('a[href="/ru/dnd/srd-5.2/classes/paladin/"]', { hasText: 'Паладин: Клятва преданности' })).toBeVisible();
});

test('в теле заклинания — автоссылки состояний и hovercard', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/hold-person/');
  const cond = page.locator('.rd-doc a.ent-link[data-hc]').first();
  await expect(cond).toBeVisible();
  await cond.hover();
  await expect(page.locator('#ent-hovercard')).toBeVisible();
});

test('SEO: hreflang-тройка, индексируема, в sitemap', async ({ page, request }) => {
  const res = await page.goto('/en/dnd/srd-5.2/spells/fireball/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="ru"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="x-default"]')).toHaveCount(1);
  await expect(page.locator('meta[name="robots"][content*="noindex"]')).toHaveCount(0);
  const sm = await (await request.get('/sitemap-0.xml')).text();
  expect(sm).toContain('/dnd/srd-5.2/spells/fireball/');
});
