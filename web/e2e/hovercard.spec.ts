import { test, expect } from '@playwright/test';

// Hovercard автоссылок (issue #20, вариант B: fetch-on-hover served JSON).
// При наведении/фокусе на a.ent-link[data-hc] показывается карточка сущности с данными
// из /hc/{game}/{ver}/{lang}.json. RU-глава заклинаний богата упоминаниями состояний.
const CHAPTER = '/ru/dnd/srd-5.2/spells/';

test('карточка появляется при наведении на автоссылку', async ({ page }) => {
  await page.goto(CHAPTER);
  const link = page.locator('.rd-doc a.ent-link[data-hc*="/conditions/"]').first();
  await expect(link).toBeVisible();
  const card = page.locator('#ent-hovercard');
  await expect(card).toHaveCount(0); // до первого показа элемента нет в DOM
  await link.hover();
  await expect(card).toBeVisible();
  // шапка: источник + EN-имя (RU-карточка); RU-имя не дублируем (навели на само слово)
  await expect(card.locator('.ent-hc-src')).toHaveText('SRD 5.2.1');
  await expect(card.locator('.ent-hc-en')).not.toBeEmpty();
  await expect(card.locator('.ent-hc-name')).toHaveCount(0);
  // эффект — форматированный блок с подэффектами, без вводной «Пока вы находитесь…»
  const body = card.locator('.ent-hc-body');
  await expect(body).not.toBeEmpty();
  await expect(body).not.toContainText('Пока вы находитесь в состоянии');
  await expect(body.locator('strong').first()).toBeVisible(); // жирные ярлыки сохранены
});

test('содержимое карточки соответствует данным сущности из /hc JSON', async ({ page, request }) => {
  await page.goto(CHAPTER);
  const link = page.locator('.rd-doc a.ent-link[data-hc*="/conditions/"]').first();
  const hc = (await link.getAttribute('data-hc'))!; // dnd/srd52/ru/conditions/<slug>
  const [game, ver, lang, ...rest] = hc.split('/');
  const bucket = await (await request.get(`/hc/${game}/${ver}/${lang}.json`)).json();
  const c = bucket[rest.join('/')];
  expect(c, 'запись сущности есть в бакете hovercard').toBeTruthy();

  await link.hover();
  const card = page.locator('#ent-hovercard');
  await expect(card).toBeVisible();
  // RU-карточка показывает оригинальное EN-имя (не RU-имя, на которое навели).
  if (c.name_en && c.name_en !== c.name) await expect(card.locator('.ent-hc-en')).toHaveText(c.name_en);
});

test('клавиатурный фокус открывает карточку и связывает aria-describedby', async ({ page }) => {
  await page.goto(CHAPTER);
  const link = page.locator('.rd-doc a.ent-link[data-hc*="/conditions/"]').first();
  await link.focus();
  const card = page.locator('#ent-hovercard');
  await expect(card).toBeVisible();
  await expect(link).toHaveAttribute('aria-describedby', 'ent-hovercard');
  await page.keyboard.press('Escape');
  await expect(card).toBeHidden();
  await expect(link).not.toHaveAttribute('aria-describedby', 'ent-hovercard');
});

test('карточка скрывается, когда курсор уходит со ссылки', async ({ page }) => {
  await page.goto(CHAPTER);
  const link = page.locator('.rd-doc a.ent-link[data-hc*="/conditions/"]').first();
  await link.hover();
  await expect(page.locator('#ent-hovercard')).toBeVisible();
  await page.mouse.move(0, 0);
  await expect(page.locator('#ent-hovercard')).toBeHidden();
});
