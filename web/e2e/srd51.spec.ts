import { test, expect } from '@playwright/test';

// Программные страницы SRD 5.1 (issue #20): те же механики, что 5.2, но НЕЗАВИСИМО — подсказки и
// автолинки версий не смешиваются. Общий с 5.2 рендер покрыт профильными спеками.

test('entity-страницы 5.1 рендерятся (спот по ресурсам)', async ({ page }) => {
  for (const url of [
    '/ru/dnd/srd-5.1/spells/fireball/',
    '/en/dnd/srd-5.1/monsters-a-z/imp/',
    '/ru/dnd/srd-5.1/magic-items/bag-of-holding/',
    '/ru/dnd/srd-5.1/weapons/battleaxe/',
    '/ru/dnd/srd-5.1/armor/chain-mail/',
    '/ru/dnd/srd-5.1/equipment/acid/',
    '/ru/dnd/srd-5.1/feats/grappler/',
    '/en/dnd/srd-5.1/rules-glossary/conditions/prone/',
  ]) {
    const res = await page.goto(url);
    expect(res?.status(), url).toBe(200);
    await expect(page.locator('.rd-doc h1')).toBeVisible();
  }
});

test('канонический слаг EN↔RU: таблично-парсируемые ресурсы 5.1 на англ. слаге', async ({ page }) => {
  // Оружие/снаряжение/черта: RU-источник получил английское имя → общий слаг (не кириллица).
  for (const [ok, bad] of [
    ['/ru/dnd/srd-5.1/weapons/battleaxe/', '/ru/dnd/srd-5.1/weapons/%D1%81%D0%B5%D0%BA%D0%B8%D1%80%D0%B0/'],
    ['/ru/dnd/srd-5.1/equipment/acid/', '/ru/dnd/srd-5.1/equipment/%D0%BA%D0%B8%D1%81%D0%BB%D0%BE%D1%82%D0%B0/'],
    ['/ru/dnd/srd-5.1/feats/grappler/', '/ru/dnd/srd-5.1/feats/%D0%B1%D0%BE%D1%80%D0%B5%D1%86/'],
  ]) {
    expect((await page.goto(ok))?.status(), ok).toBe(200);
    expect((await page.goto(bad))?.status(), bad).toBe(404);
  }
});

test('независимость: 5.1-страница линкует и глоссит ТОЛЬКО через бакет srd51', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.1/monsters-a-z/imp/');
  const doc = page.locator('.rd-doc');
  const hrefs = await doc.locator('a.ent-link').evaluateAll((els) =>
    els.map((e) => (e as HTMLAnchorElement).getAttribute('href') || ''));
  for (const h of hrefs) expect(h, `ent-link ${h}`).toContain('/dnd/srd-5.1/');
  const hc = await doc.locator('[data-hc]').evaluateAll((els) =>
    els.map((e) => e.getAttribute('data-hc') || ''));
  for (const b of hc) expect(b, `data-hc ${b}`).toContain('dnd/srd51/');
});

test('5.1 gloss: свой rules-terms-бакет (srd51), изолирован от 5.2', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.1/classes/barbarian/');
  await expect(page.locator('.rd-doc .gloss[data-hc^="dnd/srd51/ru/rules-terms/"]').first()).toBeVisible();
  await expect(page.locator('.rd-doc .gloss[data-hc*="srd52"]')).toHaveCount(0);
  await page.goto('/ru/dnd/srd-5.2/playing-the-game/');
  await expect(page.locator('.rd-doc .gloss[data-hc*="rules-terms"]').first()).toBeVisible();
});

test('5.1 gloss-бакет отдаёт карточки терминов (нет мёртвых подсказок)', async ({ request }) => {
  const res = await request.get('/hc/dnd/srd51/ru.json');
  expect(res.status()).toBe(200);
  const map = await res.json();
  expect(map['rules-terms/initiative']).toBeTruthy();
  expect(map['rules-terms/concentration']).toBeTruthy();
});

test('5.1 rules-terms: канонические слаги 5.2 (глоссарий 5.1 кодирует аббревиатуру в имени)', async ({ request }) => {
  // Глоссарий 5.1 пишет ед.ч. и аббревиатуры («Armor Class (AC)») — канонизатор сводит их к слагам 5.2.
  const map = await (await request.get('/hc/dnd/srd51/ru.json')).json();
  for (const slug of ['armor-class', 'challenge-rating', 'experience-points', 'opportunity-attacks']) {
    expect(map[`rules-terms/${slug}`], slug).toBeTruthy();
  }
  // Старых слагов-с-аббревиатурой/ед.ч. быть не должно (иначе CORE_TERMS-гейт бы промахнулся).
  for (const dead of ['armor-class-ac', 'challenge-rating-cr', 'experience-points-xp', 'opportunity-attack']) {
    expect(map[`rules-terms/${dead}`], dead).toBeFalsy();
  }
});

test('5.1 gloss: канонические термы подсвечены в прозе (не только в бакете)', async ({ page }) => {
  // Показатель опасности — в прозе заклинаний призыва («ПО 2 или ниже»): подсказка уместна.
  await page.goto('/ru/dnd/srd-5.1/spells/conjure-animals/');
  await expect(page.locator('.rd-doc .gloss[data-hc$="/rules-terms/challenge-rating"]').first()).toBeVisible();
});

test('5.1 gloss-гейт: ярлыки стат-блоков («Класс Доспеха:») НЕ глоссятся (без ковра)', async ({ page }) => {
  // Каждый стат-блок пишет «**Класс Доспеха:** 17» — терм-ярлык не место для подсказки.
  await page.goto('/ru/dnd/srd-5.1/monsters-a-z/');
  const label = page.locator('.rd-doc strong', { hasText: /^Класс Доспеха:$/ }).first();
  await expect(label).toBeVisible();
  await expect(label.locator('.gloss')).toHaveCount(0);
  // Ковра нет: armor-class на всей мега-странице — единицы, не сотни.
  const carpet = await page.locator('.rd-doc .gloss[data-hc$="/rules-terms/armor-class"]').count();
  expect(carpet).toBeLessThan(5);
});

test('монстр 5.1: чистый тип (запятая в скобках подтипа) + бэклинк в type-хаб', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.1/monsters-a-z/imp/');
  // Тип-строка должна быть «… Fiend (Devil, Shapechanger) …», без обрезанного «Fiend (Devil».
  await expect(page.locator('.mon-type')).toContainText('Fiend');
  await expect(page.locator('.mon-type')).toContainText('Devil, Shapechanger');
  await expect(page.locator('.ent-hubs a[href$="/monsters-a-z/type/fiend/"]')).toBeVisible();
});

test('type-хабы монстров 5.1: есть beast и swarm (beast-хаба в 5.2 нет)', async ({ page }) => {
  expect((await page.goto('/en/dnd/srd-5.1/monsters-a-z/type/beast/'))?.status()).toBe(200);
  expect((await page.goto('/en/dnd/srd-5.1/monsters-a-z/type/swarm/'))?.status()).toBe(200);
  // В 5.2 звери — в animals, beast-хаба нет; swarm-хаб в 5.2 есть (#196).
  expect((await page.goto('/en/dnd/srd-5.2/monsters-a-z/type/beast/'))?.status()).toBe(404);
  expect((await page.goto('/en/dnd/srd-5.2/monsters-a-z/type/swarm/'))?.status()).toBe(200);
});

test('расы 5.1: страница расы — EN-имя, подрасы, автолинк заклинаний, «другие расы»', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.1/races/tiefling/');
  await expect(page.locator('.rd-doc h1')).toContainText('Тифлинг');
  await expect(page.locator('.ent-en')).toHaveText('Tiefling');
  await expect(page.locator('.rd-doc a.ent-link[href="/ru/dnd/srd-5.1/spells/darkness/"]')).toBeVisible();
  await expect(page.locator('.ent-related a[href$="/races/elf/"]')).toBeVisible();
});

test('хаб рас 5.1: сортируемая таблица всех рас со ссылками + доступен из страницы расы', async ({ page }) => {
  const res = await page.goto('/ru/dnd/srd-5.1/races/all/');
  expect(res?.status()).toBe(200);
  const links = page.locator('.hub-table[data-sortable] tbody td:first-child a');
  await expect(links).toHaveCount(9);
  await expect(page.locator('.hub-table a[href$="/races/tiefling/"]')).toBeVisible();
  await page.goto('/ru/dnd/srd-5.1/races/dwarf/');
  await expect(page.locator(`a[href$="/dnd/srd-5.1/races/all/"]`).first()).toBeVisible();
});

test('раса 5.1 с подрасой: чипы подрас + канонический слаг', async ({ page }) => {
  const res = await page.goto('/en/dnd/srd-5.1/races/dwarf/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('.race-subraces')).toContainText('Hill Dwarf');
  expect((await page.goto('/ru/dnd/srd-5.1/races/dwarf/'))?.status()).toBe(200);
});

test('SEO 5.1: hreflang-тройка + races/weapons в sitemap', async ({ page, request }) => {
  const res = await page.goto('/en/dnd/srd-5.1/races/human/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="ru"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="x-default"]')).toHaveCount(1);
  const sm = await (await request.get('/sitemap-0.xml')).text();
  expect(sm).toContain('/dnd/srd-5.1/races/human/');
  expect(sm).toContain('/dnd/srd-5.1/weapons/battleaxe/');
});

test('hovercard-эндпоинт srd51: непустой, карточки заклинаний/предметов', async ({ request }) => {
  const ru = await (await request.get('/hc/dnd/srd51/ru.json')).json();
  expect(Object.keys(ru).length).toBeGreaterThan(500);
  expect(ru['spells/fireball']?.name_en).toBe('Fireball');
  expect(ru['magic-items/bag-of-holding']?.name_en).toBe('Bag of Holding');
  expect(Object.keys(ru).some((k) => k.startsWith('rules-terms/'))).toBe(true);
  expect(ru['rules-terms/initiative']?.name_en).toBe('Initiative');
});
