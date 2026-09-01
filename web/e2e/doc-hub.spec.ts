import { test, expect, type Page } from '@playwright/test';

// Хабы уровня документа (issue #230): /{lang}/{game}/{version}/.
// Смысл страницы — верхний узел внутренней перелинковки: из неё краулер должен видеть ВСЕ
// разделы документа и все компендиумы за один переход. Поэтому тесты проверяют не «страница
// открылась», а что ссылки на месте и ведут внутрь того же документа.

const HUBS = [
  { url: '/ru/dnd/srd-5.2/', heading: 'D&D SRD 5.2.1 (5.5e, 2024)', doc: '/ru/dnd/srd-5.2/' },
  { url: '/en/daggerheart/srd-1.0/', heading: 'Daggerheart SRD 1.0', doc: '/en/daggerheart/srd-1.0/' },
  { url: '/ru/brp/srd-1.0/', heading: 'Basic Roleplaying SRD 1.0', doc: '/ru/brp/srd-1.0/' },
];

const trail = async (page: Page) => {
  const raw = await page.locator('head script[type="application/ld+json"]').first().textContent();
  const graph = JSON.parse(raw!)['@graph'] as any[];
  return (graph.find((n) => n['@type'] === 'BreadcrumbList')?.itemListElement ?? []).map(
    (i: any) => i.item as string,
  );
};

for (const hub of HUBS) {
  test(`хаб отдаёт оглавление документа: ${hub.url}`, async ({ page }) => {
    const res = await page.goto(hub.url);
    expect(res?.status()).toBe(200);
    await expect(page.locator('h1')).toHaveText(hub.heading);

    // Все ссылки основного текста ведут внутрь этого же документа: хаб — оглавление, а не
    // перекрёсток. Исключение — CTA-воронка и ссылки шаблона, они вне <article>.
    const hrefs = await page.locator('article a').evaluateAll((els) =>
      els.map((e) => new URL((e as HTMLAnchorElement).href).pathname),
    );
    // Порог — по самому маленькому документу: у BRP 14 ссылок (9 глав + 5 справочников),
    // у D&D 5.2 их 97 (главы + 12 классов + компендиумы). Смысл проверки — «оглавление есть»,
    // а не точное число: оно меняется с каждой новой главой.
    expect(hrefs.length, 'на хабе должно быть оглавление, а не пустая страница').toBeGreaterThan(10);
    expect(hrefs.every((h) => h.startsWith(hub.doc)), `есть ссылки наружу: ${hrefs.filter((h) => !h.startsWith(hub.doc)).slice(0, 3)}`).toBe(true);
  });
}

test('хаб D&D 5.2 перечисляет главы, классы и компендиумы с числами', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/');
  // Глава, вложенный класс и компендиум — три разных уровня оглавления.
  await expect(page.locator('article a', { hasText: 'Заклинания' }).first()).toBeVisible();
  await expect(page.locator('article a', { hasText: 'Колдун' })).toHaveAttribute(
    'href', '/ru/dnd/srd-5.2/classes/warlock/',
  );
  // Число рядом с компендиумом берётся из meta.json того же API, что кормит сами страницы.
  const spells = page.locator('article li', { hasText: 'Заклинания (справочник)' });
  await expect(spells).toContainText('339');
});

test('хаб не ведёт на noindex-страницы', async ({ page }) => {
  // «Термины» (/glossary/glossary/) закрыты от индекса (#37) — ссылка с хаба тратила бы
  // краул-бюджет ровно там, где мы его экономим.
  await page.goto('/ru/dnd/srd-5.2/');
  const hrefs = await page.locator('article a').evaluateAll((els) =>
    els.map((e) => new URL((e as HTMLAnchorElement).href).pathname),
  );
  expect(hrefs).not.toContain('/ru/dnd/srd-5.2/glossary/glossary/');
});

test('крошки страниц ведут на хаб документа, а не на первую страницу', async ({ page }) => {
  // До #230 крошка документа указывала на «первую содержательную страницу» — компромисс
  // варианта 2 из #220. Теперь у документа есть свой адрес.
  await page.goto('/ru/dnd/srd-5.2/classes/warlock/');
  expect(await trail(page)).toEqual([
    'https://rules.omnisgm.com/ru/',
    'https://rules.omnisgm.com/ru/dnd/srd-5.2/',
    'https://rules.omnisgm.com/ru/dnd/srd-5.2/classes/warlock/',
  ]);
  await page.locator('.rd-crumb a', { hasText: 'SRD 5.2.1' }).click();
  await expect(page).toHaveURL(/\/ru\/dnd\/srd-5\.2\/$/);
  await expect(page.locator('h1')).toHaveText('D&D SRD 5.2.1 (5.5e, 2024)');
});

test('хаб индексируем: в sitemap, с hreflang-парой и self-canonical', async ({ page, request }) => {
  await page.goto('/ru/dnd/srd-5.2/');
  await expect(page.locator('head link[rel="canonical"]')).toHaveAttribute(
    'href', 'https://rules.omnisgm.com/ru/dnd/srd-5.2/',
  );
  await expect(page.locator('head meta[name="robots"]')).toHaveCount(0);
  await expect(page.locator('head link[rel="alternate"][hreflang]')).toHaveCount(3);

  const xml = await (await request.get('/sitemap-0.xml')).text();
  for (const hub of HUBS) {
    expect(xml, `нет в sitemap: ${hub.url}`).toContain(`<loc>https://rules.omnisgm.com${hub.url}</loc>`);
  }
});
