import { test, expect, type APIRequestContext } from '@playwright/test';
import { fromHtml } from 'hast-util-from-html';
import type { Element, Nodes } from 'hast';

// Автоссылки на программные страницы сущностей (issue #20, rehype-entity-autolink):
const CHAPTER = '/en/dnd/srd-5.2/spells/'; // глава с множеством упоминаний состояний
const ENTITY = '/en/dnd/srd-5.2/rules-glossary/conditions/paralyzed/'; // тело ссылается на Incapacitated

test('глава: автоссылки ведут на страницы сущностей (состояния/заклинания)', async ({ page }) => {
  await page.goto(CHAPTER);
  const links = page.locator('.rd-doc a.ent-link');
  expect(await links.count()).toBeGreaterThan(0);
  for (const href of await links.evaluateAll((els) => els.map((e) => e.getAttribute('href')))) {
    expect(href).toMatch(/\/(rules-glossary\/conditions|spells|monsters-a-z|animals|magic-items|equipment|weapons|armor|feats)\/[a-z0-9-]+\/$/);
  }
});

test('заклинания: имена в спелл-таблицах классов и в курсиве линкуются на страницы заклинаний', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/classes/cleric/');
  const spellLinks = page.locator('.rd-doc a.ent-link[href*="/dnd/srd-5.2/spells/"]');
  expect(await spellLinks.count()).toBeGreaterThan(20);
  await expect(page.locator('.rd-doc td a.ent-link[href*="/spells/"]').first()).toBeVisible();
  await expect(page.locator('.rd-doc em a.ent-link[href*="/spells/"]').first()).toBeVisible();
  // обычное слово (не курсив, не в спелл-таблице) НЕ линкуется: «свет» строчным в прозе
  await expect(page.locator('.rd-doc a.ent-link', { hasText: /^свет$/ })).toHaveCount(0);
});

test('монстры: имя в жирном линкуется на страницу монстра; генеричное слово в прозе — нет', async ({ page }) => {
  // Animate Dead: «a **Skeleton** … or a **Zombie**» — жирный = сигнал SRD «see Monsters».
  await page.goto('/en/dnd/srd-5.2/spells/animate-dead/');
  await expect(
    page.locator('.rd-doc strong a.ent-link[href$="/monsters-a-z/skeleton/"]'),
  ).toBeVisible();
  await expect(
    page.locator('.rd-doc strong a.ent-link[href$="/monsters-a-z/zombie/"]'),
  ).toBeVisible();
  await expect(page.locator('.rd-doc a.ent-link[href*="/monsters-a-z/humanoid/"]')).toHaveCount(0);
});

test('монстры RU: склонённые жирные формы линкуются (Упырём → ghoul)', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/spells/create-undead/');
  await expect(
    page.locator('.rd-doc strong a.ent-link[href$="/monsters-a-z/ghoul/"]').first(),
  ).toBeVisible();
  // Терминология выровнена по бестиарию: «Гастами» (не «Вурдалаками») → ghast.
  await expect(
    page.locator('.rd-doc strong a.ent-link[href$="/monsters-a-z/ghast/"]', { hasText: 'Гастами' }).first(),
  ).toBeVisible();
});

test('монстры RU: термин выровнен по бестиарию (Бюлетт, не Буллет) → bulette', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/magic-items/');
  await expect(page.locator('.rd-doc a.ent-link[href$="/monsters-a-z/bulette/"]', { hasText: 'Бюлетт' })).toBeVisible();
  await expect(page.locator('.rd-doc', { hasText: 'Буллет' })).toHaveCount(0);
});

test('животные RU: склонённые жирные формы линкуются (Слоном/Мастифом/Вороном → animals)', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/magic-items/figurine-of-wondrous-power/');
  for (const slug of ['elephant', 'mastiff', 'raven']) {
    await expect(
      page.locator(`.rd-doc strong a.ent-link[href$="/animals/${slug}/"]`).first(),
    ).toBeVisible();
  }
});

test('животные EN: множественная жирная форма линкуется (Giant Wasps → giant-wasp)', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/gameplay-toolbox/');
  await expect(
    page.locator('.rd-doc strong a.ent-link[href$="/animals/giant-wasp/"]', { hasText: 'Giant Wasps' }).first(),
  ).toBeVisible();
});

test('снаряжение: ячейки таблиц главы линкуются на страницы оружия/доспехов/снаряжения + data-hc', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/equipment/');
  const w = page.locator('.rd-doc td a.ent-link[href$="/weapons/greataxe/"]').first();
  await expect(w).toBeVisible();
  await expect(w).toHaveAttribute('data-hc', /weapons\/greataxe/);
  await expect(page.locator('.rd-doc td a.ent-link[href$="/armor/plate-armor/"]').first()).toBeVisible();
  await expect(page.locator('.rd-doc td a.ent-link[href$="/equipment/acid/"]').first()).toBeVisible();
});

test('снаряжение: имя-омоним в чужой таблице НЕ линкуется (вариант «Кнут» у Жетона пера)', async ({ page }) => {
  // Таблица вариантов Жетона пера — без колонки «Цена», то есть не перечень снаряжения.
  await page.goto('/ru/dnd/srd-5.2/magic-items/feather-token/');
  await expect(page.locator('.rd-doc a.ent-link[href*="/weapons/whip/"]')).toHaveCount(0);
});

test('hovercard-эндпоинт: есть карточки оружия/доспехов/снаряжения (name_en + мета)', async ({ request }) => {
  const ru = await (await request.get('/hc/dnd/srd52/ru.json')).json();
  expect(ru['weapons/greataxe']?.name_en).toBe('Greataxe');
  expect(ru['weapons/greataxe']?.effect).toContain('рубящий');
  expect(ru['armor/plate-armor']?.name_en).toBe('Plate Armor');
  expect(ru['equipment/acid']?.name_en).toBe('Acid');
});

test('предметы: имя в курсиве линкуется на страницу предмета', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/magic-items/');
  const link = page.locator('.rd-doc em a.ent-link[href*="/dnd/srd-5.2/magic-items/"]').first();
  await expect(link).toBeVisible();
  await expect(link).toHaveAttribute('data-hc', /^dnd\/srd52\/en\/magic-items\//);
});

test('черты: ячейка таблицы класса (Увеличение характеристики) линкуется на страницу черты', async ({ page }) => {
  // Источник выровнен к каноническому имени черты — матч без алиасов.
  await page.goto('/ru/dnd/srd-5.2/classes/fighter/');
  const cell = page.locator('.rd-doc td a.ent-link[href$="/feats/ability-score-improvement/"]');
  expect(await cell.count()).toBeGreaterThan(1);
  await expect(cell.first()).toHaveAttribute('data-hc', /feats\/ability-score-improvement/);
});

test('черты: эпический дар (много-словное имя) линкуется в прозе; фичи класса — нет', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/classes/fighter/');
  await expect(
    page.locator('.rd-doc a.ent-link[href$="/feats/boon-of-combat-prowess/"]').first(),
  ).toBeVisible();
});

test('черты: одно-словное имя (Defense) в прозе класса НЕ линкуется ложно', async ({ page }) => {
  // «Unarmored/Superior Defense» у Монаха — фичи класса, не черта Defense.
  await page.goto('/en/dnd/srd-5.2/classes/monk/');
  await expect(page.locator('.rd-doc a.ent-link[href*="/feats/defense/"]')).toHaveCount(0);
});

test('автолинк не попадает в заголовки и не вкладывается в другие ссылки', async ({ page }) => {
  await page.goto(CHAPTER);
  await expect(page.locator('.rd-doc :is(h1,h2,h3,h4,h5,h6) a.ent-link')).toHaveCount(0);
  await expect(page.locator('.rd-doc a a.ent-link')).toHaveCount(0);
});

test('линкуются ВСЕ вхождения имени, а не только первое', async ({ page }) => {
  await page.goto(CHAPTER);
  const hrefs = await page
    .locator('.rd-doc a.ent-link')
    .evaluateAll((els) => els.map((e) => e.getAttribute('href')));
  const counts = hrefs.reduce<Record<string, number>>((a, h) => ((a[h!] = (a[h!] || 0) + 1), a), {});
  expect(Math.max(...Object.values(counts))).toBeGreaterThan(1);
});

test('страница состояния: тело линкует другие состояния, но не саму себя', async ({ page }) => {
  await page.goto(ENTITY);
  const doc = page.locator('.rd-doc');
  await expect(
    doc.locator('a.ent-link[href$="/conditions/incapacitated/"]').first(),
  ).toBeVisible();
  await expect(doc.locator('a.ent-link[href$="/conditions/paralyzed/"]')).toHaveCount(0);
});

test('автоссылка несёт data-hc для будущего hovercard', async ({ page }) => {
  await page.goto(CHAPTER);
  const first = page.locator('.rd-doc a.ent-link').first();
  await expect(first).toHaveAttribute('data-hc', /^dnd\/srd52\/en\/(conditions|spells|monsters|magic-items)\//);
});

// Паритет EN/RU: набор слинкованных состояний зеркальных глав совпадает. Расхождения — в EXCEPTIONS
// с причиной; тест падает и на новом расхождении, и на протухшей записи.
const EXCEPTIONS: Record<string, string[]> = {
  '/en/dnd/srd-5.2/classes/monk/': ['exhaustion'], // RU не использует «Истощение»
  '/en/dnd/srd-5.2/classes/ranger/': ['exhaustion'],
  '/en/dnd/srd-5.2/feats/': ['grappled'], // RU не использует «Схваченный»
};

/**
 * Слаги состояний в контенте. Разбираем ГОТОВЫЙ HTML, а не браузером (#248): сотни навигаций не
 * влезали в бюджет теста. Парсер, а не регулярка: «ссылка внутри rd-doc» — структура дерева.
 */
function linkedConditionsIn(html: string): Set<string> {
  const tree = fromHtml(html);

  const classesOf = (node: Element): string[] => {
    const className = node.properties?.className;
    return Array.isArray(className) ? className.map(String) : [];
  };

  const collect = (node: Nodes, inDoc: boolean, out: Set<string>): void => {
    const element = node.type === 'element' ? (node as Element) : null;
    const insideDoc = inDoc || (element ? classesOf(element).includes('rd-doc') : false);

    if (element && insideDoc && element.tagName === 'a' && classesOf(element).includes('ent-link')) {
      const slug = String(element.properties?.href ?? '').match(/\/conditions\/([a-z-]+)\//)?.[1];
      if (slug) out.add(slug);
    }

    for (const child of ('children' in node ? node.children : []) as Nodes[]) {
      collect(child, insideDoc, out);
    }
  };

  const slugs = new Set<string>();
  collect(tree, false, slugs);
  return slugs;
}

async function linkedConditions(request: APIRequestContext, path: string): Promise<Set<string>> {
  const response = await request.get(path);
  expect(response.ok(), `${path} отдал ${response.status()}`).toBeTruthy();
  return linkedConditionsIn(await response.text());
}

test('EN/RU: набор слинкованных состояний совпадает по всем главам (кроме allowlist)', async ({ request }) => {
  const sitemap = await (await request.get('/sitemap-0.xml')).text();
  const chapters = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)]
    .map((m) => new URL(m[1]).pathname)
    .filter(
      (p) =>
        p.startsWith('/en/dnd/srd-5.2/') &&
        !p.includes('/glossary/') && // справочные таблицы вне индекса
        // страницы отдельных сущностей: описания переведены независимо, паритет линковки не гарантирован.
        !/\/rules-glossary\/[^/]+\/[^/]+\/$/.test(p) &&
        !/\/spells\/[^/]+\/$/.test(p) &&
        !/\/monsters-a-z\/[^/]+\/$/.test(p) &&
        !/\/animals\/[^/]+\/$/.test(p) &&
        !/\/magic-items\/[^/]+\/$/.test(p) &&
        !/\/equipment\/[^/]+\/$/.test(p) &&
        !/\/feats\/[^/]+\/$/.test(p),
    );
  expect(chapters.length).toBeGreaterThan(10);

  const usedExceptions = new Set<string>();
  const failures: string[] = [];
  // Порог ловит вырождение парсера: пустые множества везде выглядели бы как «расхождений нет».
  let pagesWithLinks = 0;
  for (const en of chapters) {
    const ru = en.replace('/en/', '/ru/');
    const [enSet, ruSet] = await Promise.all([
      linkedConditions(request, en),
      linkedConditions(request, ru),
    ]);
    if (enSet.size) pagesWithLinks++;
    if (ruSet.size) pagesWithLinks++;
    const diff = [...new Set([...enSet, ...ruSet])].filter((s) => enSet.has(s) !== ruSet.has(s));
    const allow = new Set(EXCEPTIONS[en] || []);
    for (const s of diff) {
      if (allow.has(s)) usedExceptions.add(`${en}:${s}`);
      else failures.push(`${en}: '${s}' (EN=${enSet.has(s)} RU=${ruSet.has(s)}) — вне allowlist`);
    }
  }
  // Порог — с запасом вниз от замера: не ломается от правок контента, но ловит обнуление.
  expect(pagesWithLinks, 'ссылки на состояния не найдены нигде — парсер вырожден').toBeGreaterThan(30);

  expect(failures, `новые EN/RU-расхождения:\n${failures.join('\n')}`).toEqual([]);

  // Протухшие исключения: каждая запись allowlist должна реально срабатывать (иначе — убрать).
  const declared = Object.entries(EXCEPTIONS).flatMap(([u, arr]) => arr.map((s) => `${u}:${s}`));
  const stale = declared.filter((k) => !usedExceptions.has(k));
  expect(stale, `протухшие записи allowlist (расхождение исчезло — уберите):\n${stale.join('\n')}`).toEqual([]);
});
