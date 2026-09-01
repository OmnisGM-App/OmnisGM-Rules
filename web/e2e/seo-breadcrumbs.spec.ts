import { test, expect, type Page } from '@playwright/test';

// Хлебные крошки (issue #220). Сплошной счёт по dist делает verify_dist_meta_budget.mjs
// (гейты «дублей URL в трейле» и «ссылок в никуда» — оба нулевые); здесь — смысловые проверки
// на живой странице: что именно стоит уровнями и что видимая строка совпадает с разметкой.
//
// Решение по #220 — вариант 2: игра и редакция схлопнуты в один уровень документа, группы без
// собственной страницы («Классы», «Глоссарий») остаются видимым текстом, но в разметку не идут.

type Crumb = { name: string; url: string };
const trail = async (page: Page): Promise<Crumb[]> => {
  const raw = await page.locator('head script[type="application/ld+json"]').first().textContent();
  const graph = JSON.parse(raw!)['@graph'] as any[];
  const list = graph.find((n) => n['@type'] === 'BreadcrumbList');
  return (list?.itemListElement ?? []).map((i: any) => ({ name: i.name as string, url: i.item as string }));
};
const SITE = 'https://rules.omnisgm.com';

test('уровни ведут на разные адреса, документ — одной крошкой', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/classes/warlock/');
  const items = await trail(page);
  expect(items.map((i) => i.name)).toEqual(['Главная', 'SRD 5.2.1 (5.5e, 2024)', 'Колдун']);
  // Дубли URL — исходный симптом #220 (позиции 2 и 3 указывали на один /legal/).
  expect(new Set(items.map((i) => i.url)).size).toBe(items.length);
  // Крошка документа ведёт в содержательную часть, а не на выходные данные.
  expect(items[1].url).toBe(`${SITE}/ru/dnd/srd-5.2/playing-the-game/`);
  expect(items[2].url).toBe(`${SITE}/ru/dnd/srd-5.2/classes/warlock/`);
});

test('на страницах 5.1 крошка документа не прыгает в 5.2', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.1/legal/');
  for (const item of await trail(page)) expect(item.url, item.name).not.toContain('/srd-5.2/');
});

test('группы без своей страницы («Классы») из разметки выпадают, но видны текстом', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/classes/warlock/');
  // Раньше «Классы» вели на первую страницу внутри группы — /classes/barbarian/.
  expect((await trail(page)).map((i) => i.url)).not.toContain(`${SITE}/ru/dnd/srd-5.2/classes/barbarian/`);
  await expect(page.locator('.rd-crumb')).toContainText('Классы');
  await expect(page.locator('.rd-crumb a', { hasText: 'Классы' })).toHaveCount(0);
});

test('крошка «Глоссарий» не ведёт на noindex-страницу', async ({ page }) => {
  // Хаб заклинаний лежит в NAV под группой «Глоссарий», у которой своей страницы нет: раньше
  // ей подставлялась первая страница внутри — /glossary/glossary/, а она под noindex.
  await page.goto('/ru/dnd/srd-5.2/spells/all/');
  const items = await trail(page);
  expect(items.map((i) => i.url)).not.toContain(`${SITE}/ru/dnd/srd-5.2/glossary/glossary/`);
  expect(items.filter((i) => i.name === 'Глоссарий')).toHaveLength(0);
  await expect(page.locator('.rd-crumb')).toContainText('Глоссарий');
});

test('трейл сущностной страницы кончается самой сущностью', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/fireball/');
  const items = await trail(page);
  // Раньше трейл обрывался на разделе «Заклинания» — конец был разным у разных шаблонов.
  expect(items.at(-1)).toEqual({ name: 'Огненный шар', url: `${SITE}/ru/dnd/srd-5.2/spells/fireball/` });
});

test('видимые крошки — рабочие ссылки на те же URL, что в разметке', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/fireball/');
  const marked = (await trail(page)).map((i) => i.url);
  const links = page.locator('.rd-crumb a');
  expect(await links.count()).toBeGreaterThan(1);
  for (const href of await links.evaluateAll((els) => els.map((e) => (e as HTMLAnchorElement).href))) {
    expect(marked, `видимая крошка ${href} отсутствует в разметке`).toContain(href.replace('http://localhost:4321', SITE));
  }
  await page.locator('.rd-crumb a', { hasText: 'Заклинания' }).click();
  await expect(page).toHaveURL(/\/ru\/dnd\/srd-5\.2\/spells\/$/);
});
