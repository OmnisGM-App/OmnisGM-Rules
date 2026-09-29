import { test, expect } from '@playwright/test';

// Длина и содержательность <meta description> у markdown-страниц (issue #213).
//
// Сплошной счёт — verify_dist_meta_budget.mjs, инварианты сниппета — test_page_description.mjs;
// здесь — мета на живой отрендеренной странице.
const MIN = 110;
const MAX = 160;

const BING_REPORT = [
  '/en/daggerheart/srd-1.0/classes/druid/',
  '/en/daggerheart/srd-1.0/classes/ranger/',
  '/en/daggerheart/srd-1.0/weapons/',
  '/en/dnd/srd-5.2/rules-glossary/',
  '/en/daggerheart/srd-1.0/armor/',
];

for (const url of BING_REPORT) {
  test(`description 110–160 и без бойлерплейта: ${url}`, async ({ page }) => {
    await page.goto(url);
    const desc = await page.locator('head meta[name="description"]').getAttribute('content');
    expect(desc, 'description отсутствует').toBeTruthy();
    expect(desc!.length).toBeGreaterThanOrEqual(MIN);
    expect(desc!.length).toBeLessThanOrEqual(MAX);
    // Брендовый хвост допустим только как добивка короткого вступления.
    expect(desc).not.toMatch(/^[^.]+\.\s*Tabletop RPG System Reference Document/);
  });
}

test('описание собрано из контента страницы, а не из шаблона', async ({ page }) => {
  await page.goto('/en/daggerheart/srd-1.0/classes/druid/');
  const desc = await page.locator('head meta[name="description"]').getAttribute('content');
  // Первая фраза главы «Druid» — признак того, что сниппет пришёл из тела markdown.
  expect(desc).toContain('Becoming a druid');

  // Справочник без вступительной прозы описывается своими терминами.
  await page.goto('/en/dnd/srd-5.2/rules-glossary/');
  const glossary = await page.locator('head meta[name="description"]').getAttribute('content');
  expect(glossary).toContain('Ability Check');

  const og = await page.locator('head meta[property="og:description"]').getAttribute('content');
  expect(og).toBe(glossary);
});

test('русская страница описана по-русски', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/rules-glossary/');
  const desc = await page.locator('head meta[name="description"]').getAttribute('content');
  expect(desc!.length).toBeGreaterThanOrEqual(MIN);
  expect(desc!.length).toBeLessThanOrEqual(MAX);
  expect(desc).not.toContain('Tabletop RPG');
  expect(desc).toContain('на русском');
});

// ── Сущностные шаблоны (issue #214, волна 1: оружие и навыки BRP) ─────────────

const facts = async (page: import('@playwright/test').Page, url: string) => {
  await page.goto(url);
  const d = await page.locator('head meta[name="description"]').getAttribute('content');
  expect(d, `нет description: ${url}`).toBeTruthy();
  expect(d!.length, `слишком длинно: ${d}`).toBeLessThanOrEqual(MAX);
  return d!;
};

test('оружие: в сниппете свойства и мастерство, а не только урон и цена', async ({ page }) => {
  const d = await facts(page, '/ru/dnd/srd-5.2/weapons/longsword/');
  expect(d.length).toBeGreaterThanOrEqual(MIN);
  expect(d).toContain('свойства: универсальное');
  expect(d).toContain('мастерство «Оглушение»');
  expect(d).toContain('урон 1d8 рубящий');
});

test('оружие без урона не даёт «урон ,» с пустым местом', async ({ page }) => {
  // У Сети урона нет вовсе — пустые факты в строку не попадают (без висящей запятой).
  const d = await facts(page, '/ru/dnd/srd-5.1/weapons/net/');
  expect(d).not.toContain('урон ,');
  expect(d).not.toMatch(/:\s*,/);
  expect(d).toContain('свойства:');
});

test('навык BRP: базовый шанс и категория впереди описания', async ({ page }) => {
  const d = await facts(page, '/en/brp/srd-1.0/skills/stealth/');
  expect(d).toContain('Basic Roleplaying');
  expect(d).toContain('base chance');
  expect(d.startsWith('Stealth —'), `начинается не с имени навыка: ${d}`).toBe(true);
});

test('навык BRP по-русски: та же формула, русские подписи', async ({ page }) => {
  const d = await facts(page, '/ru/brp/srd-1.0/skills/appraise/');
  expect(d.startsWith('Оценка — навык Basic Roleplaying:'), `не тот заход: ${d}`).toBe(true);
  expect(d).toContain('базовый шанс 15%');
  expect(d).toContain('категория «Ментальный»');
  expect(d).not.toContain('base chance');
});

// ── Хабы, глоссарий и остальные шаблоны (issue #214, волна 2) ─────────────────

test('хаб перечисляет, что внутри, а не только считает', async ({ page }) => {
  const d = await facts(page, '/ru/dnd/srd-5.2/monsters-a-z/cr/0/');
  expect(d.length).toBeGreaterThanOrEqual(MIN);
  expect(d).toContain('Среди них:');
  const other = await facts(page, '/ru/dnd/srd-5.2/monsters-a-z/cr/1/');
  expect(d).not.toBe(other);
});

test('список в сниппете хаба режется по границе имени, а не посреди слова', async ({ page }) => {
  const d = await facts(page, '/en/dnd/srd-5.2/spells/level/0/');
  expect(d).toContain('Includes:');
  const list = d.split('Includes: ')[1];
  // Факт обрезки виден многоточием, целый список — точкой.
  expect(list.endsWith('…') || list.endsWith('.')).toBe(true);
  // Режем по границе элемента: последнее имя сверяем с текстом ссылки, а не регекспом «похоже на слово».
  const names = list.replace(/[.…]$/, '').split(', ');
  const onPage = await page.locator('main a').allTextContents();
  expect(onPage.map((s) => s.trim())).toContain(names[names.length - 1]);
});

test('термин глоссария: определение целое, хвост добавлен только если влез', async ({ page }) => {
  const d = await facts(page, '/en/dnd/srd-5.1/rules-glossary/conditions/deafened/');
  expect(d).toContain("can't hear and automatically fails any ability check that requires hearing.");
  expect(d).toContain('Rules Glossary condition');
});

test('маркер списка не уезжает в сниппет', async ({ page }) => {
  for (const url of [
    '/en/dnd/srd-5.1/rules-glossary/conditions/deafened/',
    '/ru/dnd/srd-5.1/rules-glossary/conditions/incapacitated/',
  ]) {
    const d = await facts(page, url);
    expect(d.startsWith('-'), `сниппет начинается с маркера списка: ${d}`).toBe(false);
  }
});

test('доспех: требование Силы и помеха Скрытности в сниппете', async ({ page }) => {
  const d = await facts(page, '/ru/dnd/srd-5.2/armor/plate-armor/');
  expect(d.length).toBeGreaterThanOrEqual(MIN);
  expect(d).toContain('требование Силы 15');
  expect(d).toContain('помеха Скрытности');
});

// ── Согласование числительных на хабах (issue #240) ──────────────────────────
// Правила счёта — scripts/test_plural.mjs; здесь — singular-ветка хаба с ОДНОЙ сущностью.

test('хаб с одной сущностью не пишет «Все 1 животных»', async ({ page }) => {
  const d = await facts(page, '/ru/dnd/srd-5.2/animals/cr/6/');
  expect(d.startsWith('1 животное'), `плохое начало сниппета: ${d}`).toBe(true);
  expect(d).not.toContain('Все 1');
  const en = await facts(page, '/en/dnd/srd-5.2/animals/cr/6/');
  expect(en.startsWith('1 animal'), `плохое начало сниппета: ${en}`).toBe(true);
  expect(en).not.toContain('All 1 ');
});

test('множественные хабы согласованы по последней цифре', async ({ page }) => {
  // формы 2–4 и 5+ различаются, и обе должны выбираться правильно.
  expect(await facts(page, '/ru/dnd/srd-5.2/spells/level/0/')).toContain('Все 27 заговоров');
  expect(await facts(page, '/ru/dnd/srd-5.2/spells/all/')).toContain('Все 339 заклинаний');
});
