import { test, expect } from '@playwright/test';

// Программные страницы сущностей SRD 5.1 (issue #20): те же механики, что и 5.2, но полностью
// НЕЗАВИСИМО — подсказки/автолинки 5.1 не должны смешиваться с 5.2. Рендер общий с 5.2 (покрыт
// профильными спеками); здесь — 5.1-специфика: паритет слагов, независимость версий, расы,
// beast/swarm-хабы монстров, чистый тип, отсутствие «мёртвого» gloss.

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
  // Все автоссылки в теле → srd-5.1.
  const hrefs = await doc.locator('a.ent-link').evaluateAll((els) =>
    els.map((e) => (e as HTMLAnchorElement).getAttribute('href') || ''));
  for (const h of hrefs) expect(h, `ent-link ${h}`).toContain('/dnd/srd-5.1/');
  // Любой data-hc в теле (автолинк ИЛИ gloss ядра) → бакет srd51, не srd52 (изоляция версий).
  const hc = await doc.locator('[data-hc]').evaluateAll((els) =>
    els.map((e) => e.getAttribute('data-hc') || ''));
  for (const b of hc) expect(b, `data-hc ${b}`).toContain('dnd/srd51/');
});

test('5.1 gloss: свой rules-terms-бакет (srd51), изолирован от 5.2', async ({ page }) => {
  // 5.1 теперь глоссит термины ядра из собственного глоссария (парсер секций-таблиц).
  await page.goto('/ru/dnd/srd-5.1/classes/barbarian/');
  await expect(page.locator('.rd-doc .gloss[data-hc^="dnd/srd51/ru/rules-terms/"]').first()).toBeVisible();
  // Изоляция: ни одной 5.2-подсказки на 5.1-странице.
  await expect(page.locator('.rd-doc .gloss[data-hc*="srd52"]')).toHaveCount(0);
  // 5.2 тоже глоссит (не сломали).
  await page.goto('/ru/dnd/srd-5.2/playing-the-game/');
  await expect(page.locator('.rd-doc .gloss[data-hc*="rules-terms"]').first()).toBeVisible();
});

test('5.1 gloss-бакет отдаёт карточки терминов (нет мёртвых подсказок)', async ({ request }) => {
  const res = await request.get('/hc/dnd/srd51/ru.json');
  expect(res.status()).toBe(200);
  const map = await res.json();
  // Символические термы, покрытые глоссарием 5.1 (симметрично EN/RU).
  expect(map['rules-terms/initiative']).toBeTruthy();
  expect(map['rules-terms/concentration']).toBeTruthy();
});

test('монстр 5.1: чистый тип (запятая в скобках подтипа) + бэклинк в type-хаб', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.1/monsters-a-z/imp/');
  // Тип-строка должна быть «… Fiend (Devil, Shapechanger) …», без обрезанного «Fiend (Devil».
  await expect(page.locator('.mon-type')).toContainText('Fiend');
  await expect(page.locator('.mon-type')).toContainText('Devil, Shapechanger');
  // Бэклинк в хаб типа — на канонический fiend.
  await expect(page.locator('.ent-hubs a[href$="/monsters-a-z/type/fiend/"]')).toBeVisible();
});

test('type-хабы монстров 5.1: есть beast и swarm (в 5.2 их нет)', async ({ page }) => {
  expect((await page.goto('/en/dnd/srd-5.1/monsters-a-z/type/beast/'))?.status()).toBe(200);
  expect((await page.goto('/en/dnd/srd-5.1/monsters-a-z/type/swarm/'))?.status()).toBe(200);
  // В 5.2 звери вынесены в animals — beast-хаба нет.
  expect((await page.goto('/en/dnd/srd-5.2/monsters-a-z/type/beast/'))?.status()).toBe(404);
});

test('расы 5.1: страница расы — EN-имя, подрасы, автолинк заклинаний, «другие расы»', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.1/races/tiefling/');
  await expect(page.locator('.rd-doc h1')).toContainText('Тифлинг');
  await expect(page.locator('.ent-en')).toHaveText('Tiefling');
  // Автолинк расовых заклинаний → страницы заклинаний 5.1.
  await expect(page.locator('.rd-doc a.ent-link[href="/ru/dnd/srd-5.1/spells/darkness/"]')).toBeVisible();
  // «Другие расы» ведут на другие entity-страницы рас.
  await expect(page.locator('.ent-related a[href$="/races/elf/"]')).toBeVisible();
});

test('хаб рас 5.1: сортируемая таблица всех рас со ссылками + доступен из страницы расы', async ({ page }) => {
  const res = await page.goto('/ru/dnd/srd-5.1/races/all/');
  expect(res?.status()).toBe(200);
  // 9 строк-ссылок на entity-страницы рас.
  const links = page.locator('.hub-table[data-sortable] tbody td:first-child a');
  await expect(links).toHaveCount(9);
  await expect(page.locator('.hub-table a[href$="/races/tiefling/"]')).toBeVisible();
  // Со страницы расы «в раздел» ведёт на хаб (entity → хаб).
  await page.goto('/ru/dnd/srd-5.1/races/dwarf/');
  await expect(page.locator(`a[href$="/dnd/srd-5.1/races/all/"]`).first()).toBeVisible();
});

test('раса 5.1 с подрасой: чипы подрас + канонический слаг', async ({ page }) => {
  const res = await page.goto('/en/dnd/srd-5.1/races/dwarf/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('.race-subraces')).toContainText('Hill Dwarf');
  // Общий слаг EN↔RU (hreflang-пара существует).
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
  // 5.1 теперь имеет rules-terms (парсер секций-таблиц глоссария) → бакет их содержит.
  expect(Object.keys(ru).some((k) => k.startsWith('rules-terms/'))).toBe(true);
  expect(ru['rules-terms/initiative']?.name_en).toBe('Initiative');
});
