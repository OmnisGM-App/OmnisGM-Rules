import { test, expect, type Page } from '@playwright/test';

// JSON-LD контентных страниц (issue #219). Сплошной счёт по dist делает
// verify_dist_meta_budget.mjs (гейт «Article без обязательных полей» = 0); здесь — смысловые
// проверки на живой странице: что именно лежит в полях и что граф связан ссылками @id.
//
// Почему это важно ровно так: без image и дат Google не выдаёт Article-rich-result вовсе,
// а даты у нас приезжают из git по исходному markdown — на сборке без истории они молча
// исчезают, и подмены датой билда мы не делаем (это шум для поисковика, а не свежесть).

const graphOf = async (page: Page) => {
  const raw = await page.locator('head script[type="application/ld+json"]').first().textContent();
  return JSON.parse(raw!)['@graph'] as any[];
};
const node = (graph: any[], type: string) => graph.find((n) => n['@type'] === type);
const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$/;

test('сущность с портретом: image = портрет, даты ISO, автор — Organization', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/monsters-a-z/aboleth/');
  const graph = await graphOf(page);
  const article = node(graph, 'Article');

  expect(article.image).toBe('https://rules.omnisgm.com/img/dnd/creatures/aboleth.webp');
  expect(article.datePublished).toMatch(ISO);
  expect(article.dateModified).toMatch(ISO);
  expect(new Date(article.dateModified).getTime()).toBeGreaterThanOrEqual(
    new Date(article.datePublished).getTime(),
  );
  // author/publisher — ссылки на узел Organization в том же графе, а не строки.
  expect(article.author).toEqual({ '@id': 'https://rules.omnisgm.com/#org' });
  expect(article.publisher).toEqual({ '@id': 'https://rules.omnisgm.com/#org' });
  expect(node(graph, 'Organization')['@id']).toBe('https://rules.omnisgm.com/#org');
  expect(article.mainEntityOfPage['@id']).toBe(article.url);
});

test('страница без портрета: image — общий og.png, а не пустое поле', async ({ page }) => {
  await page.goto('/en/daggerheart/srd-1.0/classes/druid/');
  const article = node(await graphOf(page), 'Article');
  expect(article.image).toBe('https://rules.omnisgm.com/og.png');
  expect(article.datePublished).toMatch(ISO);
});

test('дата изменения — из контента, а не из даты сборки', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/spells/fireball/');
  const article = node(await graphOf(page), 'Article');
  // Дата не «сегодня»: контент правился раньше сборки. Сравнивать даты ДВУХ конкретных глав
  // здесь нельзя — один общий коммит по обеим (прогон форматера, массовая правка терминов)
  // сделал бы их равными при полностью исправном механизме. Инвариант «дат в сборке больше
  // одной» проверяется по всему dist в scripts/verify_dist_meta_budget.mjs.
  const today = new Date().toISOString().slice(0, 10);
  expect(article.dateModified.slice(0, 10)).not.toBe(today);
});

test('Organization.sameAs связывает ресурсы экосистемы и репозиторий', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/fireball/');
  const org = node(await graphOf(page), 'Organization');
  expect(org.sameAs).toEqual(
    expect.arrayContaining([
      'https://omnisgm.com/',
      'https://news.omnisgm.com/',
      'https://rules.omnisgm.com/',
      'https://github.com/OmnisGM-App/OmnisGM-Rules',
    ]),
  );
});

test('хаб раздела тоже получает даты (контент тот же файл главы)', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/all/');
  const article = node(await graphOf(page), 'Article');
  expect(article.datePublished).toMatch(ISO);
  expect(article.dateModified).toMatch(ISO);
});
