import { test, expect } from '@playwright/test';

// Автоссылки на программные страницы сущностей (issue #20, rehype-entity-autolink):
// имена состояний в контенте становятся ссылками .ent-link на страницу состояния.
const CHAPTER = '/en/dnd/srd-5.2/spells/'; // глава с множеством упоминаний состояний
const ENTITY = '/en/dnd/srd-5.2/rules-glossary/conditions/paralyzed/'; // тело ссылается на Incapacitated

test('глава: автоссылки ведут на страницы сущностей (состояния/заклинания)', async ({ page }) => {
  await page.goto(CHAPTER);
  const links = page.locator('.rd-doc a.ent-link');
  expect(await links.count()).toBeGreaterThan(0);
  // Все ent-link ведут на программную страницу сущности: состояние / заклинание / монстр.
  for (const href of await links.evaluateAll((els) => els.map((e) => e.getAttribute('href')))) {
    expect(href).toMatch(/\/(rules-glossary\/conditions|spells|monsters-a-z|animals|magic-items|feats)\/[a-z0-9-]+\/$/);
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

test('монстры: имя в жирном линкуется на страницу монстра; генеричное слово в прозе — нет', async ({ page }) => {
  // Animate Dead: «becomes an Undead creature: a **Skeleton** … or a **Zombie**» — жирный = ссылка
  // на статблок (сигнал SRD «see Monsters»).
  await page.goto('/en/dnd/srd-5.2/spells/animate-dead/');
  await expect(
    page.locator('.rd-doc strong a.ent-link[href$="/monsters-a-z/skeleton/"]'),
  ).toBeVisible();
  await expect(
    page.locator('.rd-doc strong a.ent-link[href$="/monsters-a-z/zombie/"]'),
  ).toBeVisible();
  // «Undead», «creature», «Humanoid» в прозе (не жирные имена монстров) НЕ линкуются на монстров.
  await expect(page.locator('.rd-doc a.ent-link[href*="/monsters-a-z/humanoid/"]')).toHaveCount(0);
});

test('монстры RU: склонённые жирные формы линкуются (Упырём → ghoul)', async ({ page }) => {
  // RU-текст склоняет имя монстра («становится **Упырём**»), а страница монстра — «Упырь».
  // Курируемый alias падежных форм линкует их на ту же сущность.
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
  // старый неканоничный термин не встречается в тексте
  await expect(page.locator('.rd-doc', { hasText: 'Буллет' })).toHaveCount(0);
});

test('животные RU: склонённые жирные формы линкуются (Слоном/Мастифом/Вороном → animals)', async ({ page }) => {
  // Фигурка чудесной силы: RU склоняет имена животных в жирном («стать **Слоном**»),
  // а страница животного — в именительном. Курируемый alias падежных форм линкует их.
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

test('предметы: имя в курсиве линкуется на страницу предмета', async ({ page }) => {
  // Глава маг. предметов: предмет↔предмет ссылки — «*Portable Hole*» и т.п. в курсиве.
  await page.goto('/en/dnd/srd-5.2/magic-items/');
  const link = page.locator('.rd-doc em a.ent-link[href*="/dnd/srd-5.2/magic-items/"]').first();
  await expect(link).toBeVisible();
  await expect(link).toHaveAttribute('data-hc', /^dnd\/srd52\/en\/magic-items\//);
});

test('черты: ячейка таблицы класса (Увеличение характеристики) линкуется на страницу черты', async ({ page }) => {
  // Таблица прогрессии воина: «Увеличение характеристики» на уровнях 4/6/… → ссылка на ASI-черту.
  // Источник выровнен к каноническому имени черты (формы «…характеристик» приведены к ед.ч.),
  // поэтому матч идёт по имени напрямую, без алиасов.
  await page.goto('/ru/dnd/srd-5.2/classes/fighter/');
  const cell = page.locator('.rd-doc td a.ent-link[href$="/feats/ability-score-improvement/"]');
  expect(await cell.count()).toBeGreaterThan(1); // несколько уровней
  await expect(cell.first()).toHaveAttribute('data-hc', /feats\/ability-score-improvement/);
});

test('черты: эпический дар (много-словное имя) линкуется в прозе; фичи класса — нет', async ({ page }) => {
  // «Boon of Combat Prowess is recommended» — много-словное имя черты в прозе → ссылка.
  await page.goto('/en/dnd/srd-5.2/classes/fighter/');
  await expect(
    page.locator('.rd-doc a.ent-link[href$="/feats/boon-of-combat-prowess/"]').first(),
  ).toBeVisible();
});

test('черты: одно-словное имя (Defense) в прозе класса НЕ линкуется ложно', async ({ page }) => {
  // «Unarmored Defense»/«Superior Defense» в Монахе — фичи класса, не черта «Оборона/Defense».
  // Одно-словные имена черт в прозе не трогаем → ложной ссылки на feats/defense быть не должно.
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
  await expect(first).toHaveAttribute('data-hc', /^dnd\/srd52\/en\/(conditions|spells|monsters|magic-items)\//);
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
  // (magic-items: prone/unconscious — сняты после переперевода главы по EN 5.2: RU теперь
  //  использует канонические состояния, расхождение исчезло.)
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
        !/\/monsters-a-z\/[^/]+\/$/.test(p) && // отдельных монстров (не глава /monsters-a-z/):
        !/\/animals\/[^/]+\/$/.test(p) && // отдельных животных (не глава /animals/):
        !/\/magic-items\/[^/]+\/$/.test(p) && // отдельных предметов (не глава /magic-items/):
        !/\/feats\/[^/]+\/$/.test(p), // и отдельных черт (не глава /feats/):
        // их описания переведены независимо → паритет линковки состояний тут не гарантирован
        // (главы /spells/, /monsters-a-z/, /magic-items/ остаются в наборе).
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
