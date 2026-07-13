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

test('компоненты В/С/М — стилизованная подсказка (полное слово), не нативный title', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/fireball/');
  const abbrs = page.locator('.spell-meta abbr');
  await expect(abbrs).toHaveCount(3);
  // Полное слово в data-tip (для CSS-подсказки) + aria-label (для скринридеров); нативный title убран.
  await expect(abbrs.nth(0)).toHaveAttribute('data-tip', 'Вербальный');
  await expect(abbrs.nth(0)).toHaveAttribute('aria-label', 'Вербальный');
  await expect(abbrs.nth(1)).toHaveAttribute('data-tip', 'Соматический');
  await expect(abbrs.nth(2)).toHaveAttribute('data-tip', 'Материальный');
  // Подсказка реально всплывает по наведению (::after берёт текст из data-tip).
  await abbrs.nth(0).hover();
  const tip = await abbrs.nth(0).evaluate((el) => getComputedStyle(el, '::after').content);
  expect(tip).toContain('Вербальный');
});

test('классы и подклассы — ссылки; подкласс скрыт, если класс уже в списке', async ({ page }) => {
  // Fireball: классы Чародей/Волшебник; даётся подклассом Исчадие (Колдун) — Колдуна нет в
  // списке классов, поэтому «Колдун: Исчадие» показывается.
  await page.goto('/ru/dnd/srd-5.2/spells/fireball/');
  const meta = page.locator('.spell-meta');
  await expect(meta.locator('a[href="/ru/dnd/srd-5.2/classes/sorcerer/"]', { hasText: /^Чародей$/ })).toBeVisible();
  await expect(meta).toContainText('Подклассы');
  // подкласс ведёт на секцию подкласса на странице класса (#anchor)
  await expect(meta.locator('a[href^="/ru/dnd/srd-5.2/classes/warlock/#"]', { hasText: 'Колдун: Исчадие' })).toBeVisible();

  // Aid: даётся Домом жизни (Жрец) и Клятвой преданности (Паладин), но оба класса уже в полном
  // списке Aid → строка подклассов избыточна и НЕ показывается.
  await page.goto('/ru/dnd/srd-5.2/spells/aid/');
  await expect(page.locator('.spell-meta')).not.toContainText('Подклассы');
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
