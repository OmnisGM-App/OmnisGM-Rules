import { test, expect } from '@playwright/test';

// Программные страницы монстров (issue #20, волна 3): /{lang}/dnd/{ver}/monsters-a-z/{slug}/.
// Стат-блок (защиты/характеристики/ПО), автоссылки состояний+заклинаний в телах + hovercard,
// ссылки-иммунитеты к состояниям, SEO (hreflang, sitemap), related «тот же тип».

test('страница монстра: заголовок, EN-имя, строка типа, стат-блок', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/monsters-a-z/adult-green-dragon/');
  await expect(page.locator('.rd-doc h1')).toContainText('Взрослый зелёный дракон');
  await expect(page.locator('.ent-en')).toHaveText('Adult Green Dragon');
  await expect(page.locator('.mon-type')).toContainText('дракон'); // тип существа
  const stat = page.locator('.mon-stat');
  await expect(stat).toContainText('Класс доспеха');
  await expect(stat).toContainText('Хиты');
  await expect(stat).toContainText('Показатель опасности');
  // таблица характеристик: 6 колонок + 3 ряда (ЗНАЧ/МОД/СПАС)
  await expect(page.locator('.mon-abil thead th')).toHaveCount(7); // пустая + 6 характеристик
  await expect(page.locator('.mon-abil tbody tr')).toHaveCount(3);
});

test('стат-блок: иммунитеты к урону + состояниям, состояние — ссылка на страницу', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/monsters-a-z/adult-green-dragon/');
  const imm = page.locator('.mon-row', { hasText: 'Иммунитеты' });
  await expect(imm).toContainText('Ядовитый'); // урон
  // условный иммунитет линкуется на страницу состояния (+ data-hc для hovercard)
  const cond = imm.locator('a.ent-link[href$="/conditions/poisoned/"]');
  await expect(cond).toHaveText('Отравленный');
  await expect(cond).toHaveAttribute('data-hc', 'dnd/srd52/ru/conditions/poisoned');
});

test('тело действий: автоссылки заклинаний и состояний + hovercard', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/monsters-a-z/adult-green-dragon/');
  // заклинание из блока «Сотворение заклинаний» линкуется на страницу заклинания
  await expect(
    page.locator('.mon-section a.ent-link[href*="/spells/"]').first(),
  ).toBeVisible();
  // наведение на любую автоссылку в теле открывает карточку
  const link = page.locator('.mon-section a.ent-link[data-hc]').first();
  await link.scrollIntoViewIfNeeded();
  await link.hover();
  await expect(page.locator('#ent-hovercard')).toBeVisible();
});

test('related: другие существа того же типа', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/monsters-a-z/adult-green-dragon/');
  const rel = page.locator('.ent-related');
  await expect(rel).toContainText('дракон'); // тип существа в RU строчный

  await expect(rel.locator('a[href*="/monsters-a-z/"]').first()).toBeVisible();
});

test('SEO: hreflang-тройка, индексируема, в sitemap', async ({ page, request }) => {
  const res = await page.goto('/en/dnd/srd-5.2/monsters-a-z/aboleth/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="ru"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="x-default"]')).toHaveCount(1);
  await expect(page.locator('meta[name="robots"][content*="noindex"]')).toHaveCount(0);
  const sm = await (await request.get('/sitemap-0.xml')).text();
  expect(sm).toContain('/dnd/srd-5.2/monsters-a-z/aboleth/');
});
