import { test, expect } from '@playwright/test';

// Автоссылки на программные страницы сущностей (issue #20, rehype-entity-autolink):
// имена состояний в контенте становятся ссылками .ent-link на страницу состояния.
const CHAPTER = '/en/dnd/srd-5.2/spells/'; // глава с множеством упоминаний состояний
const ENTITY = '/en/dnd/srd-5.2/rules-glossary/conditions/paralyzed/'; // тело ссылается на Incapacitated

test('глава: автоссылки ведут на страницы сущностей (состояния/заклинания)', async ({ page }) => {
  await page.goto(CHAPTER);
  const links = page.locator('.rd-doc a.ent-link');
  expect(await links.count()).toBeGreaterThan(0);
  // Все ent-link ведут на программную страницу сущности: состояние или заклинание.
  for (const href of await links.evaluateAll((els) => els.map((e) => e.getAttribute('href')))) {
    expect(href).toMatch(/\/(rules-glossary\/conditions|spells)\/[a-z-]+\/$/);
  }
});

test('заклинания: имена в спелл-таблицах классов и в курсиве линкуются на страницы заклинаний', async ({ page }) => {
  await page.goto('/ru/dnd/srd-5.2/classes/cleric/');
  const spellLinks = page.locator('.rd-doc a.ent-link[href*="/dnd/srd-5.2/spells/"]');
  expect(await spellLinks.count()).toBeGreaterThan(20); // таблицы спелл-листов + курсивные упоминания
  // табличная ссылка (первая колонка спелл-листа)
  await expect(page.locator('.rd-doc td a.ent-link[href*="/spells/"]').first()).toBeVisible();
  // курсивная ссылка в прозе (<em><a>)
  await expect(page.locator('.rd-doc em a.ent-link[href*="/spells/"]').first()).toBeVisible();
  // обычное слово (не курсив, не в спелл-таблице) НЕ линкуется: «свет» строчным в прозе
  await expect(page.locator('.rd-doc a.ent-link', { hasText: /^свет$/ })).toHaveCount(0);
});

test('автолинк не попадает в заголовки и не вкладывается в другие ссылки', async ({ page }) => {
  await page.goto(CHAPTER);
  await expect(page.locator('.rd-doc :is(h1,h2,h3,h4,h5,h6) a.ent-link')).toHaveCount(0);
  await expect(page.locator('.rd-doc a a.ent-link')).toHaveCount(0);
});

test('линкуются ВСЕ вхождения имени, а не только первое', async ({ page }) => {
  await page.goto(CHAPTER);
  // В теле встречается хотя бы одно состояние, упомянутое (капитализированным именем) ≥2 раз —
  // проверяем, что таких ссылок тоже ≥2 (дедупа «первое упоминание» нет).
  const hrefs = await page
    .locator('.rd-doc a.ent-link')
    .evaluateAll((els) => els.map((e) => e.getAttribute('href')));
  const counts = hrefs.reduce<Record<string, number>>((a, h) => ((a[h!] = (a[h!] || 0) + 1), a), {});
  expect(Math.max(...Object.values(counts))).toBeGreaterThan(1);
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
  await expect(first).toHaveAttribute('data-hc', /^dnd\/srd52\/en\/(conditions|spells)\//);
});

// Паритет EN/RU: страницы одной главы — зеркальный перевод, значит НАБОР слинкованных состояний
// должен совпадать. Линкуем все вхождения, поэтому количество ссылок EN/RU может отличаться
// (инфлексия, частота), а множество — нет: набор не зависит от дедупа.
//
// Реальные расхождения вынесены в EXCEPTIONS с причиной — три вида:
//  • RU-перевод не использует термин состояния (EN капитализирует ключевое слово, RU дал прозу);
//  • RU капитализирует «Невидимый» как термин, а EN тут про заклинание Invisibility, не состояние;
//  • RU использует ДРУГОЙ термин, чем глоссарий (оглушённый вместо Ошеломлённый, обездвиженный
//    вместо Опутанный) → капитализация регистра не помогает, слово всё равно не матчится (это
//    terminology-propagation, не регистр).
// Часть прежних расхождений закрыта капитализацией RU-регистра под EN (issue #20).
// Тест падает и при НОВОМ расхождении (регрессия матчинга/перевода), и при ПРОТУХШЕЙ записи
// allowlist (расхождение исчезло → запись надо убрать).
const EXCEPTIONS: Record<string, string[]> = {
  // (bard/warlock/wizard : invisible — сняты: «Невидимость» теперь линкуется как ЗАКЛИНАНИЕ
  //  в спелл-листах, не как состояние, → расхождение состояния исчезло на обоих языках.)
  '/en/dnd/srd-5.2/classes/monk/': ['exhaustion'], // RU не использует «Истощение»
  '/en/dnd/srd-5.2/classes/ranger/': ['exhaustion'],
  '/en/dnd/srd-5.2/feats/': ['grappled'], // RU не использует «Схваченный»
  '/en/dnd/srd-5.2/magic-items/': ['prone', 'unconscious'], // RU: иные формы/прозой
};

async function linkedConditions(page: import('@playwright/test').Page, path: string): Promise<Set<string>> {
  await page.goto(path);
  const hrefs = await page
    .locator('.rd-doc a.ent-link')
    .evaluateAll((els) => els.map((e) => e.getAttribute('href') || ''));
  const slugs = hrefs.map((h) => h.match(/\/conditions\/([a-z-]+)\//)?.[1]).filter(Boolean) as string[];
  return new Set(slugs);
}

test('EN/RU: набор слинкованных состояний совпадает по всем главам (кроме allowlist)', async ({ page, request }) => {
  const sitemap = await (await request.get('/sitemap-0.xml')).text();
  const chapters = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)]
    .map((m) => new URL(m[1]).pathname)
    .filter(
      (p) =>
        p.startsWith('/en/dnd/srd-5.2/') &&
        !p.includes('/glossary/') && // справочные таблицы вне индекса
        !p.includes('/rules-glossary/conditions/') && // сами страницы состояний, не главы
        !/\/spells\/[^/]+\/$/.test(p) && // страницы отдельных заклинаний (не глава /spells/):
        !/\/monsters-a-z\/[^/]+\/$/.test(p), // и отдельных монстров (не глава /monsters-a-z/):
        // их описания переведены независимо → паритет линковки состояний тут не гарантирован
        // (главы /spells/ и /monsters-a-z/ остаются в наборе).
    );
  expect(chapters.length).toBeGreaterThan(10);

  const usedExceptions = new Set<string>();
  const failures: string[] = [];
  for (const en of chapters) {
    const ru = en.replace('/en/', '/ru/');
    const enSet = await linkedConditions(page, en);
    const ruSet = await linkedConditions(page, ru);
    const diff = [...new Set([...enSet, ...ruSet])].filter((s) => enSet.has(s) !== ruSet.has(s));
    const allow = new Set(EXCEPTIONS[en] || []);
    for (const s of diff) {
      if (allow.has(s)) usedExceptions.add(`${en}:${s}`);
      else failures.push(`${en}: '${s}' (EN=${enSet.has(s)} RU=${ruSet.has(s)}) — вне allowlist`);
    }
  }
  expect(failures, `новые EN/RU-расхождения:\n${failures.join('\n')}`).toEqual([]);

  // Протухшие исключения: каждая запись allowlist должна реально срабатывать (иначе — убрать).
  const declared = Object.entries(EXCEPTIONS).flatMap(([u, arr]) => arr.map((s) => `${u}:${s}`));
  const stale = declared.filter((k) => !usedExceptions.has(k));
  expect(stale, `протухшие записи allowlist (расхождение исчезло — уберите):\n${stale.join('\n')}`).toEqual([]);
});
