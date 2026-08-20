import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import { execFileSync } from 'node:child_process';

// Картинки сущностей (#201 — портреты существ, #202 — иконки заклинаний и магпредметов):
// картинка живёт в Rules, показывается на странице сущности, уходит в og:image и в поле
// `image` JSON API. Страница без картинки не должна регрессировать.

test('страница монстра: портрет виден, размеры заданы, alt = имя', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/monsters-a-z/aboleth/');
  const img = page.locator('.rd-doc .ent-portrait');
  await expect(img).toBeVisible();
  await expect(img).toHaveAttribute('src', '/img/dnd/creatures/aboleth.webp');
  await expect(img).toHaveAttribute('alt', 'Аболет');
  // width/height обязательны: по ним резервируется место, иначе растёт CLS.
  await expect(img).toHaveAttribute('width', '512');
  await expect(img).toHaveAttribute('height', '512');
  // Картинка реально отдаётся и декодируется, а не висит битой ссылкой.
  const natural = await img.evaluate((el: HTMLImageElement) => [el.naturalWidth, el.naturalHeight]);
  expect(natural).toEqual([512, 512]);
});

test('og:image страницы существа = портрет, с реальными размерами', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/monsters-a-z/aboleth/');
  const og = (p: string) => page.locator(`head meta[property="og:${p}"]`).getAttribute('content');
  expect(await og('image')).toBe('https://rules.omnisgm.com/img/dnd/creatures/aboleth.webp');
  expect(await og('image:width')).toBe('512');
  expect(await og('image:height')).toBe('512');
  // Квадратную картинку широкая карточка обрезала бы по центру.
  await expect(page.locator('head meta[name="twitter:card"]')).toHaveAttribute('content', 'summary');
});

test('страница без портрета: общий og.png и никакой пустой рамки', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/rules-glossary/');
  await expect(page.locator('.ent-portrait')).toHaveCount(0);
  await expect(page.locator('head meta[property="og:image"]')).toHaveAttribute(
    'content', 'https://rules.omnisgm.com/og.png',
  );
  await expect(page.locator('head meta[property="og:image:width"]')).toHaveAttribute('content', '1200');
});

test('животные и противники Daggerheart тоже с портретами', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/animals/ape/');
  await expect(page.locator('.ent-portrait')).toHaveAttribute('src', '/img/dnd/creatures/ape.webp');

  await page.goto('/ru/daggerheart/srd-1.0/adversaries/acid-burrower/');
  await expect(page.locator('.ent-portrait')).toHaveAttribute(
    'src', '/img/daggerheart/creatures/acid-burrower.webp',
  );
});

test('авторство картинок — отдельной строкой и только на страницах с портретом', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/monsters-a-z/aboleth/');
  await expect(page.locator('.rd-attrib-img')).toContainText('© OmnisGM');

  await page.goto('/ru/dnd/srd-5.2/rules-glossary/');
  await expect(page.locator('.rd-attrib-img')).toHaveCount(0);
});

// JSON API публикуется на деплое (firebase predeploy → dist/api), в preview его нет,
// поэтому проверяем ТОТ ЖЕ артефакт, что генерит prebuild из generate_api.py.
const api = (p: string) => JSON.parse(fs.readFileSync(`src/data/api/${p}`, 'utf-8'));

test('JSON API: image есть у существ с файлом и отсутствует у остальных', () => {
  const monsters = api('dnd/srd52/ru/monsters/all.json');
  const aboleth = monsters.find((m: { slug: string }) => m.slug === 'aboleth');
  expect(aboleth.image).toBe('https://rules.omnisgm.com/img/dnd/creatures/aboleth.webp');
  // Поля нет вовсе, а не пустая строка/null — потребитель проверяет наличие ключа.
  // Берём заклинание, которого генератор ещё не касался (первое по алфавиту уже с иконкой).
  const spells = api('dnd/srd52/ru/spells/all.json');
  expect(spells.find((s: { slug: string }) => s.slug === 'fireball')).not.toHaveProperty('image');
  // Окружения Daggerheart делят схему с противниками, но картинок у них нет.
  expect(api('daggerheart/srd10/ru/environments/all.json')[0]).not.toHaveProperty('image');
  expect(api('daggerheart/srd10/ru/adversaries/all.json')[0].image).toContain('/img/daggerheart/creatures/');
});

test('у каждой сущности с полем image файл реально отдаётся', async ({ request }) => {
  // Ловит рассинхрон «URL написан вслепую»: поле есть, а по ссылке 404.
  const all = [
    ...api('dnd/srd52/ru/monsters/all.json'),
    ...api('dnd/srd52/ru/animals/all.json'),
    ...api('daggerheart/srd10/ru/adversaries/all.json'),
  ].filter((e: { image?: string }) => e.image);
  expect(all.length).toBeGreaterThan(400);
  for (const e of all.slice(0, 12)) {
    const path = new URL(e.image).pathname;
    const res = await request.get(path);
    expect(res.status(), `${e.slug} → ${path}`).toBe(200);
    expect(res.headers()['content-type']).toContain('image/webp');
  }
});

test('обратная сторона: у каждого файла есть сущность (нет осиротевших картинок)', () => {
  const slugs = new Set<string>([
    ...api('dnd/srd52/ru/monsters/all.json'),
    ...api('dnd/srd51/ru/monsters/all.json'),
    ...api('dnd/srd52/ru/animals/all.json'),
  ].map((e: { slug: string }) => e.slug));
  const orphans = fs.readdirSync('public/img/dnd/creatures')
    .filter((f) => f.endsWith('.webp'))
    .map((f) => f.slice(0, -5))
    .filter((slug) => !slugs.has(slug));
  expect(orphans, `картинки без сущности: ${orphans.join(', ')}`).toEqual([]);
});

test('заклинание и магпредмет с иконкой — тот же механизм, что у существ (#202)', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/acid-arrow/');
  await expect(page.locator('.ent-portrait')).toHaveAttribute('src', '/img/dnd/spells/acid-arrow.webp');
  await expect(page.locator('head meta[property="og:image"]')).toHaveAttribute(
    'content', 'https://rules.omnisgm.com/img/dnd/spells/acid-arrow.webp',
  );
  await expect(page.locator('.rd-attrib-img')).toContainText('© OmnisGM');

  await page.goto('/ru/dnd/srd-5.2/magic-items/amulet-of-health/');
  await expect(page.locator('.ent-portrait')).toHaveAttribute(
    'src', '/img/dnd/magic-items/amulet-of-health.webp',
  );
});

test('сущность без картинки: страница как раньше', async ({ page }) => {
  // Огненный шар в очереди генератора — иконки пока нет.
  await page.goto('/ru/dnd/srd-5.2/spells/fireball/');
  await expect(page.locator('img.ent-portrait')).toHaveCount(0);
  await expect(page.locator('head meta[property="og:image"]')).toHaveAttribute(
    'content', 'https://rules.omnisgm.com/og.png',
  );
  await expect(page.locator('.rd-attrib-img')).toHaveCount(0);
});

test('очередь генератора: поле image ровно у тех, чей файл лежит', () => {
  // Тот же расчёт, что делает scripts/gen-images.mjs: сущности API минус лежащие webp.
  const spells = api('dnd/srd52/en/spells/all.json');
  const done = fs.readdirSync('public/img/dnd/spells').filter((f) => f.endsWith('.webp'));
  expect(done.length).toBeGreaterThan(0);
  const withImage = spells.filter((s: { image?: string }) => s.image).length;
  expect(withImage).toBe(
    spells.filter((s: { slug: string }) => done.includes(`${s.slug}.webp`)).length,
  );
});

// Очередь генератора берёт снаряжение и предметы Daggerheart/BRP прямо из markdown-таблиц
// (в JSON API этих коллекций пока нет) и сама считает слаг. Если её формула разойдётся
// с parsers/base.py, картинки лягут под именами, которых сущности никогда не получат —
// молча, без единой ошибки. Поэтому сверяем обе реализации на реальных именах.
test('слаг в генераторе и в парсерах считается одинаково', () => {
  const FILES = [
    'src/daggerheart/srd-1.0/en/17_Glossary/03_Weapons.md',
    'src/daggerheart/srd-1.0/en/17_Glossary/04_Armor.md',
    'src/daggerheart/srd-1.0/en/17_Glossary/06_Items.md',
    'src/daggerheart/srd-1.0/en/17_Glossary/07_Consumables.md',
    'src/brp/srd-1.0/en/09_Glossary/02_Weapons.md',
    'src/brp/srd-1.0/en/09_Glossary/03_Armor.md',
  ];
  // Та же формула, что в scripts/gen-images.mjs.
  const slugify = (n: string) => n.toLowerCase().normalize('NFKD')
    .replace(/[^\w\s-]/g, ' ').replace(/[-\s]+/g, '-').replace(/^-+|-+$/g, '');

  const names: string[] = [];
  for (const rel of FILES) {
    let header = true;
    for (const line of fs.readFileSync(`../${rel}`, 'utf-8').split('\n')) {
      const t = line.trim();
      if (!t.startsWith('|')) { header = true; continue; }
      if (/^\|[\s:-]+\|/.test(t)) continue;
      if (header) { header = false; continue; }
      const first = t.split('|').slice(1, -1).map((c) => c.trim())[0];
      if (first && first !== '—') names.push(first);
    }
  }
  expect(names.length).toBeGreaterThan(400);

  const py = execFileSync('python3', ['-c', `
import json, sys
sys.path.insert(0, '../.github/scripts')
from parsers.base import slugify
print(json.dumps([slugify(n) for n in json.load(sys.stdin)]))
`], { input: JSON.stringify(names), encoding: 'utf-8' });
  const fromPython: string[] = JSON.parse(py);
  const mismatched = names
    .map((n, i) => ({ n, js: slugify(n), py: fromPython[i] }))
    .filter((r) => r.js !== r.py);
  expect(mismatched, `расходятся: ${mismatched.slice(0, 5).map((r) => r.n).join(', ')}`).toEqual([]);
});
