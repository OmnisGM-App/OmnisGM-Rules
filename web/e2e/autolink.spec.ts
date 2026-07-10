import { test, expect } from '@playwright/test';

// Автоссылки на программные страницы сущностей (issue #20, rehype-entity-autolink):
// имена состояний в контенте становятся ссылками .ent-link на страницу состояния.
const CHAPTER = '/en/dnd/srd-5.2/spells/'; // глава с множеством упоминаний состояний
const ENTITY = '/en/dnd/srd-5.2/rules-glossary/conditions/paralyzed/'; // тело ссылается на Incapacitated

test('глава: имена состояний автолинкуются на страницы состояний', async ({ page }) => {
  await page.goto(CHAPTER);
  const links = page.locator('.rd-doc a.ent-link');
  expect(await links.count()).toBeGreaterThan(0);
  // Все ent-link ведут на страницы состояний.
  for (const href of await links.evaluateAll((els) => els.map((e) => e.getAttribute('href')))) {
    expect(href).toContain('/rules-glossary/conditions/');
  }
});

test('автолинк не попадает в заголовки и не вкладывается в другие ссылки', async ({ page }) => {
  await page.goto(CHAPTER);
  await expect(page.locator('.rd-doc :is(h1,h2,h3,h4,h5,h6) a.ent-link')).toHaveCount(0);
  await expect(page.locator('.rd-doc a a.ent-link')).toHaveCount(0);
});

test('каждое состояние линкуется не более одного раза на страницу (первое упоминание)', async ({ page }) => {
  await page.goto(CHAPTER);
  const hrefs = await page
    .locator('.rd-doc a.ent-link')
    .evaluateAll((els) => els.map((e) => e.getAttribute('href')));
  expect(new Set(hrefs).size).toBe(hrefs.length);
});

test('страница состояния: тело линкует другие состояния, но не саму себя', async ({ page }) => {
  await page.goto(ENTITY);
  const doc = page.locator('.rd-doc');
  // ссылка на Incapacitated в теле есть…
  await expect(
    doc.locator('a.ent-link[href$="/conditions/incapacitated/"]').first(),
  ).toBeVisible();
  // …а самоссылки на paralyzed в теле нет.
  await expect(doc.locator('a.ent-link[href$="/conditions/paralyzed/"]')).toHaveCount(0);
});

test('автоссылка несёт data-hc для будущего hovercard', async ({ page }) => {
  await page.goto(CHAPTER);
  const first = page.locator('.rd-doc a.ent-link').first();
  await expect(first).toHaveAttribute('data-hc', /^dnd\/srd52\/en\/conditions\//);
});
