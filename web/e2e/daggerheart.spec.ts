import { test, expect } from '@playwright/test';

// Programmatic-страницы Daggerheart SRD 1.0: происхождения, сообщества, доменные карты
// (+by-domain), противники/окружения (+by-tier), хабы, gloss-подсказки глоссария.
// Полностью независимо от D&D: game=daggerheart, свой бакет данных/hc (подсказки не смешиваются).

test('entity-страницы Daggerheart рендерятся', async ({ page }) => {
  for (const url of [
    '/ru/daggerheart/srd-1.0/ancestries/dwarf/',
    '/en/daggerheart/srd-1.0/ancestries/clank/',
    '/ru/daggerheart/srd-1.0/communities/highborne/',
    '/en/daggerheart/srd-1.0/domain-cards/rune-ward/',
    '/ru/daggerheart/srd-1.0/adversaries/acid-burrower/',
    '/en/daggerheart/srd-1.0/environments/abandoned-grove/',
  ]) {
    const res = await page.goto(url);
    expect(res?.status(), url).toBe(200);
    await expect(page.locator('.rd-doc h1')).toBeVisible();
  }
});

test('происхождение: EN-имя, related «другие происхождения», upLink на хаб', async ({ page }) => {
  await page.goto('/ru/daggerheart/srd-1.0/ancestries/dwarf/');
  await expect(page.locator('.rd-doc h1')).toContainText('Дварф');
  await expect(page.locator('.ent-en')).toHaveText('Dwarf');
  await expect(page.locator('.ent-related a[href$="/ancestries/elf/"]')).toBeVisible();
  await expect(page.locator('a[href$="/ancestries/all/"]').first()).toBeVisible();
});

test('доменная карта: мета (уровень · домен · стоимость отзыва) + ссылка на by-domain', async ({ page }) => {
  await page.goto('/ru/daggerheart/srd-1.0/domain-cards/rune-ward/');
  await expect(page.locator('.ent-en')).toHaveText('Rune Ward');
  const meta = page.locator('.card-meta');
  await expect(meta).toContainText('Уровень 1');
  await expect(meta).toContainText('Стоимость отзыва 0');
  await expect(meta.locator('a[href$="/domain-cards/domain/arcana/"]')).toBeVisible();
});

test('gloss: термины глоссария подсвечены, бакет только daggerheart (изоляция от D&D)', async ({ page }) => {
  await page.goto('/ru/daggerheart/srd-1.0/adversaries/acid-burrower/');
  const doc = page.locator('.rd-doc');
  // Есть хотя бы одна gloss-подсказка с бакетом daggerheart/srd10.
  await expect(doc.locator('.gloss[data-hc^="daggerheart/srd10/ru/rules-terms/"]').first()).toBeVisible();
  // Ни одной подсказки/ссылки D&D на странице Daggerheart.
  const hc = await doc.locator('[data-hc]').evaluateAll((els) => els.map((e) => e.getAttribute('data-hc') || ''));
  for (const b of hc) expect(b, `data-hc ${b}`).toContain('daggerheart/');
});

test('независимость: страница Daggerheart не содержит ссылок/подсказок на D&D', async ({ page }) => {
  await page.goto('/en/daggerheart/srd-1.0/domain-cards/rune-ward/');
  const doc = page.locator('.rd-doc');
  const links = await doc.locator('a').evaluateAll((els) =>
    els.map((e) => (e as HTMLAnchorElement).getAttribute('href') || ''));
  for (const h of links) expect(h.includes('/dnd/'), `link ${h}`).toBeFalsy();
});

test('хабы: сортируемые таблицы (происхождения, доменные карты, противники) + фасет-колонки', async ({ page }) => {
  // Хаб происхождений — таблица со ссылками.
  expect((await page.goto('/ru/daggerheart/srd-1.0/ancestries/all/'))?.status()).toBe(200);
  await expect(page.locator('.hub-table[data-sortable] a[href$="/ancestries/clank/"]')).toBeVisible();

  // Доменные карты — единая таблица; «Домен» кликабелен (в колонке и в футере).
  expect((await page.goto('/ru/daggerheart/srd-1.0/domain-cards/all/'))?.status()).toBe(200);
  await expect(page.locator('.hub-table[data-sortable] a[href*="/domain-cards/domain/"]').first()).toBeVisible();
  await expect(page.locator('a[href$="/domain-cards/domain/arcana/"]').first()).toBeVisible();

  // Фасет одного домена.
  expect((await page.goto('/en/daggerheart/srd-1.0/domain-cards/domain/blade/'))?.status()).toBe(200);
  await expect(page.locator('a[href$="/domain-cards/a-soldier-s-bond/"]')).toBeVisible();

  // Противники: хаб-таблица, «Ранг» кликабелен → фасет тира.
  expect((await page.goto('/ru/daggerheart/srd-1.0/adversaries/all/'))?.status()).toBe(200);
  await expect(page.locator('.hub-table[data-sortable] a[href*="/adversaries/tier/"]').first()).toBeVisible();
  expect((await page.goto('/en/daggerheart/srd-1.0/adversaries/tier/1/'))?.status()).toBe(200);
  await expect(page.locator('a[href$="/adversaries/acid-burrower/"]')).toBeVisible();
});

test('противники: колонка «Тип» кликабельна → type-фасет (Solo/Bruiser/…)', async ({ page }) => {
  await page.goto('/ru/daggerheart/srd-1.0/adversaries/all/');
  await expect(page.locator('.hub-table[data-sortable] a[href*="/adversaries/type/"]').first()).toBeVisible();
  const res = await page.goto('/en/daggerheart/srd-1.0/adversaries/type/solo/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('.rd-doc h1')).toContainText('Solo');
  await expect(page.locator('.hub-table[data-sortable] a[href*="/adversaries/tier/"]').first()).toBeVisible();
});

test('глоссарий «Способности» = доменные карты → скрыт из сайдбара (как D&D), но страница жива', async ({ page }) => {
  await page.goto('/ru/daggerheart/srd-1.0/domain-cards/all/');
  // Дубль-список скрыт из nav, показан наш хаб доменных карт.
  await expect(page.locator('.rd-nav a[href$="/17_glossary/01_abilities/"]')).toHaveCount(0);
  await expect(page.locator('.rd-nav a.rd-nav-active[href$="/domain-cards/all/"]')).toBeVisible();
  // Сама страница-дубль остаётся доступной и держит nav-контекст (не сирота).
  const res = await page.goto('/ru/daggerheart/srd-1.0/glossary/abilities/');
  expect(res?.status()).toBe(200);
  // Метка системы в <title>: «Daggerheart SRD 1.0» — марка не должна стоять в заголовке
  // голой (DPCGL §2.5(a), issue #166), поэтому «SRD» из лестницы укорачивания не выпадает.
  await expect(page).toHaveTitle(/Daggerheart SRD 1\.0/);
});

test('автолинк: глава «Домены» линкует доменные карты (grid-режим) + hovercard', async ({ page }) => {
  await page.goto('/ru/daggerheart/srd-1.0/domains/');
  // Ячейки-имена карт в сетке домена стали ссылками на страницы карт с data-hc.
  const link = page.locator('.rd-doc a.ent-link[href*="/domain-cards/"][data-hc^="daggerheart/srd10/ru/domain-cards/"]').first();
  await expect(link).toBeVisible();
});

test('канонический слаг EN↔RU: RU-сущность на английском слаге', async ({ page }) => {
  expect((await page.goto('/ru/daggerheart/srd-1.0/ancestries/goblin/'))?.status()).toBe(200);
  expect((await page.goto('/ru/daggerheart/srd-1.0/domain-cards/rune-ward/'))?.status()).toBe(200);
  // Кириллический слаг не существует.
  expect((await page.goto('/ru/daggerheart/srd-1.0/ancestries/%D0%B3%D0%BE%D0%B1%D0%BB%D0%B8%D0%BD/'))?.status()).toBe(404);
});

test('SEO: hreflang-тройка + сущности в sitemap', async ({ page, request }) => {
  const res = await page.goto('/en/daggerheart/srd-1.0/ancestries/orc/');
  expect(res?.status()).toBe(200);
  await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="ru"]')).toHaveCount(1);
  await expect(page.locator('link[rel="alternate"][hreflang="x-default"]')).toHaveCount(1);
  const sm = await (await request.get('/sitemap-0.xml')).text();
  expect(sm).toContain('/daggerheart/srd-1.0/ancestries/orc/');
  expect(sm).toContain('/daggerheart/srd-1.0/domain-cards/rune-ward/');
  expect(sm).toContain('/daggerheart/srd-1.0/adversaries/acid-burrower/');
});

test('prev/next пропускает скрытые глоссарий-списки (замена хабами)', async ({ page }) => {
  // С последнего видимого хаба глоссария «дальше» не должно уводить в скрытый плоский список.
  await page.goto('/ru/daggerheart/srd-1.0/environments/all/');
  const nextHref = await page.locator('.rd-pn-r').first().getAttribute('href');
  expect(nextHref, 'next не ведёт в скрытый /glossary/ список').not.toContain('/glossary/');
});

test('глоссарий: markdown-таблица оружия сортируема (клик по <th> переупорядочивает)', async ({ page }) => {
  await page.goto('/ru/daggerheart/srd-1.0/glossary/weapons/');
  const table = page.locator('.rd-doc table[data-sortable]').first();
  await expect(table).toBeVisible();
  const firstBefore = await table.locator('tbody tr td:first-child').first().textContent();
  await table.locator('thead th').first().click();
  await expect(table.locator('thead th').first()).toHaveAttribute('aria-sort', 'ascending');
  const firstAfter = await table.locator('tbody tr td:first-child').first().textContent();
  expect(firstAfter).not.toBe(firstBefore);
});

test('hovercard-бакет daggerheart отдаёт карточки терминов', async ({ request }) => {
  const res = await request.get('/hc/daggerheart/srd10/ru.json');
  expect(res.status()).toBe(200);
  const map = await res.json();
  expect(map['rules-terms/vulnerable']).toBeTruthy();
  expect(map['rules-terms/action-roll']).toBeTruthy();
});

// DPCGL-комплаенс (issue #166). Требования лицензии, которые обязаны жить на КАЖДОЙ странице
// Daggerheart, а не только на Legal: §4.1(a) копирайт, (b) точное имя Public Game Content,
// (c) гиперссылка на него, (d) гиперссылка на лицензию, (e) пометка о модификациях;
// §2.5(a) — Name Mark «Daggerheart» не должен стоять в заголовке главы/страницы голым.
test('DPCGL: атрибуция §4.1 в футере и §2.5 в <title>', async ({ page }) => {
  for (const [url, mods] of [
    ['/ru/daggerheart/srd-1.0/adversaries/all/', /переведён на русский/],
    ['/en/daggerheart/srd-1.0/adversaries/all/', /the rules text is unchanged/],
  ] as const) {
    await page.goto(url);
    const attrib = page.locator('.rd-attrib');
    await expect(attrib).toContainText('Daggerheart System Reference Document 1.0');
    await expect(attrib).toContainText('Critical Role, LLC');
    await expect(attrib).toContainText(mods);
    await expect(attrib.locator('a[href="https://www.daggerheart.com"]')).toHaveCount(1);
    await expect(attrib.locator('a[href="https://darringtonpress.com/license"]')).toHaveCount(1);
    // Марка в заголовке — только как часть имени документа-источника.
    const title = await page.title();
    expect(title).toMatch(/Daggerheart SRD/);
    expect(title).not.toMatch(/Daggerheart(?! SRD)/);
  }
});
