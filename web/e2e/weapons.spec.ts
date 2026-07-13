import { test, expect } from '@playwright/test';

// Программные страницы оружия (issue #20, Дорожка A): /{lang}/dnd/{ver}/weapons/{slug}/.
// Тонкий стат-блок (урон/свойства/мастерство/категория/вес/цена). RU получает канонический
// (англ.) слаг + name_en через сверку стат-блоков EN↔RU в generate_api → общий слаг, hreflang.

test('оружие: заголовок, EN-имя, категория, урон (тип переведён)', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/weapons/longsword/');
  await expect(page.locator('.rd-doc h1')).toContainText('Длинный меч');
  await expect(page.locator('.ent-en')).toHaveText('Longsword');
  await expect(page.locator('.item-meta-line')).toContainText('Воинское оружие ближнего боя');
  const stat = page.locator('.item-stat');
  // Тип урона переведён на русский (в данных хранится «Slashing»).
  await expect(stat.locator('.item-row', { hasText: 'Урон' })).toContainText('1d8 рубящий');
  await expect(stat.locator('.item-row', { hasText: 'Мастерство' })).toContainText('Оглушение');
});

test('канонический слаг: RU-страница на англ. слаге, кириллического слага нет', async ({ page }) => {
  // RU оружие теперь на /weapons/longsword/ (не /weapons/длинный-меч/).
  const ok = await page.goto('/ru/dnd/srd-5.2/weapons/longsword/');
  expect(ok?.status()).toBe(200);
  const cyr = await page.goto('/ru/dnd/srd-5.2/weapons/%D0%B4%D0%BB%D0%B8%D0%BD%D0%BD%D1%8B%D0%B9-%D0%BC%D0%B5%D1%87/');
  expect(cyr?.status()).toBe(404);
});

test('свойства/мастерство — gloss-подсказки; при наведении всплывает определение', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/weapons/longsword/');
  // Свойство «Универсальное» — gloss-спан с data-hc на weapon-properties (хвост «(1d10)» вне спана).
  const prop = page.locator('.item-stat .gloss[data-hc*="weapon-properties/versatile"]', { hasText: 'Универсальное' });
  await expect(prop).toBeVisible();
  // Мастерство «Оглушение» → masteries.
  const mastery = page.locator('.item-stat .gloss[data-hc*="masteries/sap"]', { hasText: 'Оглушение' });
  await expect(mastery).toBeVisible();
  // Наведение → hovercard с EN-именем и определением.
  await prop.hover();
  const card = page.locator('#ent-hovercard.is-open');
  await expect(card).toBeVisible();
  await expect(card.locator('.ent-hc-en')).toHaveText('Versatile');
  await expect(card.locator('.ent-hc-body')).toContainText('одной или двумя руками');
});

test('hovercard-эндпоинт: есть карточки свойств и мастерств оружия', async ({ request }) => {
  const ru = await (await request.get('/hc/dnd/srd52/ru.json')).json();
  expect(ru['weapon-properties/finesse']?.name_en).toBe('Finesse');
  expect(ru['weapon-properties/finesse']?.effect).toContain('Силы или Ловкости');
  expect(ru['masteries/cleave']?.name_en).toBe('Cleave');
});

test('related: другое оружие той же категории и типа', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/weapons/longsword/');
  const rel = page.locator('.ent-related');
  await expect(rel).toContainText('Воинское оружие ближнего боя');
  await expect(rel.locator('a[href*="/weapons/"]').first()).toBeVisible();
});

test('SEO: hreflang-тройка, индексируема, в sitemap', async ({ page, request }) => {
  const res = await page.goto('/en/dnd/srd-5.2/weapons/longsword/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="ru"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="x-default"]')).toHaveCount(1);
  await expect(page.locator('meta[name="robots"][content*="noindex"]')).toHaveCount(0);
  const sm = await (await request.get('/sitemap-0.xml')).text();
  expect(sm).toContain('/dnd/srd-5.2/weapons/longsword/');
});
