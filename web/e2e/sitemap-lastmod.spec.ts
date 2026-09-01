import { test, expect, type APIRequestContext } from '@playwright/test';

// lastmod в sitemap (issue #221). Дата берётся из `dateModified` собранной страницы (#219),
// а туда — из истории git по исходному markdown. Смысл проверок: sitemap и страница говорят
// одно и то же, и это не дата сборки — иначе после каждого деплоя «обновилось всё», и
// поисковик перестаёт верить сигналу вообще.

const ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$/;
const ORIGIN = 'https://rules.omnisgm.com';

const sitemap = async (request: APIRequestContext) => {
  const res = await request.get('/sitemap-0.xml');
  expect(res.ok()).toBeTruthy();
  return res.text();
};
// Все пары «URL → lastmod» (lastmod может отсутствовать — тогда undefined).
const entries = (xml: string) =>
  [...xml.matchAll(/<url><loc>([^<]+)<\/loc>(?:<lastmod>([^<]+)<\/lastmod>)?/g)].map((m) => ({
    url: m[1],
    lastmod: m[2],
  }));

test('lastmod есть почти у всех URL и в формате ISO 8601', async ({ request }) => {
  const all = entries(await sitemap(request));
  expect(all.length).toBeGreaterThan(5000);

  const withDate = all.filter((e) => e.lastmod);
  // Без даты законно остаются только языковые хабы («/», «/en/», «/ru/») — у них нет Article.
  expect(all.length - withDate.length).toBeLessThanOrEqual(3);
  for (const e of withDate.slice(0, 50)) expect(e.lastmod, e.url).toMatch(ISO);
});

test('lastmod совпадает с dateModified самой страницы', async ({ page, request }) => {
  const url = `${ORIGIN}/ru/dnd/srd-5.2/monsters-a-z/aboleth/`;
  const entry = entries(await sitemap(request)).find((e) => e.url === url);
  expect(entry, 'страница пропала из sitemap').toBeTruthy();

  await page.goto('/ru/dnd/srd-5.2/monsters-a-z/aboleth/');
  const raw = await page.locator('head script[type="application/ld+json"]').first().textContent();
  const article = JSON.parse(raw!)['@graph'].find((n: any) => n['@type'] === 'Article');
  expect(entry!.lastmod).toBe(article.dateModified);
});

test('даты не схлопнуты в одну — это был бы признак даты сборки', async ({ request }) => {
  const dates = new Set(entries(await sitemap(request)).map((e) => e.lastmod).filter(Boolean));
  expect(dates.size).toBeGreaterThan(1);
  // И ни одна страница не помечена «сегодня»: контент правился раньше этой сборки.
  const today = new Date().toISOString().slice(0, 10);
  expect([...dates].filter((d) => d!.slice(0, 10) === today)).toEqual([]);
});
