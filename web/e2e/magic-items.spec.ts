import { test, expect } from '@playwright/test';

// Программные страницы магических предметов (issue #20, волна 3): /{lang}/dnd/{ver}/magic-items/{slug}/.

test('страница предмета: заголовок, EN-имя, тип·редкость, стат-блок', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/magic-items/dwarven-thrower/');
  await expect(page.locator('.rd-doc h1')).toContainText('Дварфийский метатель');
  await expect(page.locator('.ent-en')).toHaveText('Dwarven Thrower');
  await expect(page.locator('.item-meta-line')).toContainText('очень редкий'); // редкость локализована
  const stat = page.locator('.item-stat');
  await expect(stat).toContainText('Тип');
  await expect(stat).toContainText('Редкость');
  await expect(stat.locator('.item-row', { hasText: 'Настройка' })).toContainText('требуется');
  await expect(stat.locator('.item-row', { hasText: 'Настройка' })).toContainText('дварф'); // Belt of Dwarvenkind (5.2)
});

test('related: другие предметы того же типа', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/magic-items/dwarven-thrower/');
  const rel = page.locator('.ent-related');
  await expect(rel).toContainText('Оружие');
  await expect(rel.locator('a[href*="/magic-items/"]').first()).toBeVisible();
});

test('канонический слаг для вложенных скобок (Stone of Good Luck) — EN и RU совпадают', async ({ page }) => {
  // Вложенная скобка «Камень удачи (Камень везения) (Stone of Good Luck (Luckstone))» — слаг stone-of-good-luck.
  for (const lang of ['en', 'ru']) {
    const res = await page.goto(`/${lang}/dnd/srd-5.2/magic-items/stone-of-good-luck/`);
    expect(res?.status(), `${lang} страница существует`).toBe(200);
  }
  await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="ru"]')).toHaveCount(1);
});

test('SEO: hreflang-тройка, индексируема, в sitemap', async ({ page, request }) => {
  const res = await page.goto('/en/dnd/srd-5.2/magic-items/bag-of-holding/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="ru"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="x-default"]')).toHaveCount(1);
  await expect(page.locator('meta[name="robots"][content*="noindex"]')).toHaveCount(0);
  const sm = await (await request.get('/sitemap-0.xml')).text();
  expect(sm).toContain('/dnd/srd-5.2/magic-items/bag-of-holding/');
});

// Семейства (#412): запись «Оружие, +1, +2 или +3» — страница на прежнем адресе, её предметы — под ней,
// каждый со своей редкостью и в своём хабе редкости.
test('семейство: прежний адрес, подпись редкостей, перечень предметов, без перехода в компендиум', async ({ page }) => {
  const res = await page.goto('/ru/dnd/srd-5.2/magic-items/weapon-1-2-or-3/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('.item-meta-line')).toContainText('необычный, редкий или очень редкий');
  const items = page.getByTestId('magic-item-group-items');
  await expect(items.locator('tbody tr')).toHaveCount(3);
  await expect(items.locator('a[href="/ru/dnd/srd-5.2/magic-items/weapon-1-2-or-3/weapon-2/"]')).toHaveText('Оружие +2');
  await expect(items.locator('tr', { hasText: 'Оружие +2' })).toContainText('редкий');
  await expect(page.locator('a[href*="omnisgm.com/compendium"]')).toHaveCount(0);
  await page.goto('/en/dnd/srd-5.2/magic-items/potions-of-healing/');
  await expect(page.locator('.item-meta-line')).toContainText('rarity varies');
  await expect(page.getByTestId('magic-item-group-items').locator('tbody tr')).toHaveCount(4);
});

test('предмет семейства: вложенный адрес, одна редкость, ссылка на семейство и в компендиум', async ({ page }) => {
  const res = await page.goto('/en/dnd/srd-5.2/magic-items/potions-of-healing/potion-of-healing-greater/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('.rd-doc h1')).toContainText('Potion of Healing (greater)');
  const stat = page.locator('.item-stat');
  await expect(stat.locator('.item-row', { hasText: 'Rarity' })).toContainText('uncommon');
  await expect(stat.locator('a[href="/en/dnd/srd-5.2/magic-items/potions-of-healing/"]')).toHaveText('Potions of Healing');
  await expect(page.locator('.rd-doc')).toContainText('4d4 + 4');
  await expect(page.locator('a[href*="/compendium/dnd2024/magic-item/potion-of-healing-greater?"]').first()).toBeAttached();
  const flat = await page.goto('/en/dnd/srd-5.2/magic-items/potion-of-healing-greater/');
  expect(flat?.status()).toBe(404);
});

test('хабы редкости: предмет семейства стоит в хабе своей редкости с вложенным адресом', async ({ page }) => {
  for (const [rarity, slug] of [['uncommon', 'weapon-1'], ['rare', 'weapon-2'], ['very-rare', 'weapon-3']]) {
    await page.goto(`/en/dnd/srd-5.2/magic-items/rarity/${rarity}/`);
    await expect(page.locator(`.rd-doc a[href$="/magic-items/weapon-1-2-or-3/${slug}/"]`), rarity).toHaveCount(1);
    // Само семейство в хабах не стоит: у него нет своей редкости.
    await expect(page.locator('.rd-doc a[href$="/magic-items/weapon-1-2-or-3/"]'), rarity).toHaveCount(0);
  }
  await page.goto('/en/dnd/srd-5.2/magic-items/rarity/legendary/');
  await expect(page.locator('.rd-doc a[href*="/magic-items/weapon-1-2-or-3/"]')).toHaveCount(0);
  await expect(page.locator('.rd-doc a[href$="/magic-items/armor-1-2-or-3/armor-3/"]')).toHaveCount(1);
});
