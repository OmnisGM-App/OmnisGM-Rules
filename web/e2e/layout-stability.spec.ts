import { test, expect } from '@playwright/test';

// Стабильность макета: пока TOC помещается по ширине (десктоп), правый столбец
// зарезервирован ВСЕГДА — даже на страницах без оглавления (Legal, страницы сущностей).
// Иначе контент прыгает на ширину TOC при навигации со страницы с TOC на страницу без.
// Регрессия к «страница прыгает если панели нет, а потом есть».

test.use({ viewport: { width: 1280, height: 900 } });

test('правый столбец TOC зарезервирован и без оглавления — контент не прыгает', async ({ page }) => {
  // Страница С оглавлением: глава заклинаний (разделы уровней = много h2).
  await page.goto('/en/dnd/srd-5.2/spells/');
  await expect(page.locator('#rd-toc')).toBeVisible();
  const withToc = await page.locator('.rd-content').boundingBox();

  // Страница БЕЗ оглавления: правовая информация (нет h2/h3 → TOC не рендерится).
  await page.goto('/en/dnd/srd-5.2/legal/');
  await expect(page.locator('#rd-toc')).toHaveCount(0); // самой панели нет
  const noToc = await page.locator('.rd-content').boundingBox();

  // Но грид всё равно держит 3 колонки — место под TOC зарезервировано.
  const trackCount = await page.locator('.rd-body').evaluate(
    (el) => getComputedStyle(el).gridTemplateColumns.trim().split(/\s+/).length,
  );
  expect(trackCount).toBe(3);

  // Ключевое: ширина контентной колонки одинакова с TOC и без → нет горизонтального прыжка.
  expect(withToc).not.toBeNull();
  expect(noToc).not.toBeNull();
  expect(Math.abs(withToc!.width - noToc!.width)).toBeLessThanOrEqual(1);
});

test('страница сущности (состояние) не прыгает относительно главы с TOC', async ({ page }) => {
  await page.goto('/en/dnd/srd-5.2/spells/');
  const withToc = await page.locator('.rd-content').boundingBox();

  // Страница состояния — headings=[] → TOC нет, но столбец зарезервирован.
  await page.goto('/en/dnd/srd-5.2/rules-glossary/conditions/frightened/');
  await expect(page.locator('#rd-toc')).toHaveCount(0);
  const entity = await page.locator('.rd-content').boundingBox();

  expect(Math.abs(withToc!.width - entity!.width)).toBeLessThanOrEqual(1);
});

// ── CLS на страницах с картинкой (#201) ────────────────────────────────────────────────
// Картинка — главный источник сдвига: пока она не пришла, место под неё либо зарезервировано,
// либо контент прыгнет, когда она приедет. Место резервируют два независимых слоя — колонка
// грида в EntityHead.astro (168 px десктоп / 92 px мобилка) и атрибуты width/height, — и тест
// проверяет результат обоих: сумму layout-shift, как её считают Core Web Vitals.
//
// Троттлинг обязателен: с localhost картинка приезжает раньше первой отрисовки, сдвигу неоткуда
// взяться и тест зеленеет по построению, ничего не проверив.

const CLS_BUDGET = 0.1; // «Good» по Core Web Vitals; у статичной читалки любой сдвиг — дефект

// Layout Instability API не описан в lib.dom — объявляем ровно те два поля, что читаем.
interface LayoutShiftEntry extends PerformanceEntry { value: number; hadRecentInput: boolean }
declare global {
  interface Window { __cls: number }
}

const observeCls = () => {
  window.__cls = 0;
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries() as unknown as LayoutShiftEntry[]) {
      // hadRecentInput — сдвиг как реакция на действие пользователя, в CLS не входит.
      if (!entry.hadRecentInput) window.__cls += entry.value;
    }
  }).observe({ type: 'layout-shift', buffered: true });
};

async function clsOf(page: import('@playwright/test').Page, url: string) {
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Network.enable');
  // Fast 3G: картинка гарантированно приходит после первой отрисовки.
  await cdp.send('Network.emulateNetworkConditions', {
    offline: false, latency: 150,
    downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8,
  });
  await page.addInitScript(observeCls);
  await page.goto(url, { waitUntil: 'load' });
  // Сдвиги случаются и после load — шрифты, поздние картинки; даём им произойти.
  await page.waitForTimeout(1500);
  return page.evaluate(() => window.__cls);
}

const WITH_IMAGE = [
  { url: '/ru/dnd/srd-5.2/monsters-a-z/aboleth/', what: 'существо' },
  { url: '/en/dnd/srd-5.2/spells/fireball/', what: 'заклинание с иконкой' },
  { url: '/ru/daggerheart/srd-1.0/adversaries/acid-burrower/', what: 'противник Daggerheart' },
];

for (const { url, what } of WITH_IMAGE) {
  test(`CLS в бюджете на странице «${what}» — десктоп`, async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    expect(await clsOf(page, url)).toBeLessThanOrEqual(CLS_BUDGET);
  });

  test(`CLS в бюджете на странице «${what}» — мобилка`, async ({ page }) => {
    // Мобильная раскладка — своя колонка (92 px) и свой размер портрета: отдельный риск сдвига.
    await page.setViewportSize({ width: 390, height: 844 });
    expect(await clsOf(page, url)).toBeLessThanOrEqual(CLS_BUDGET);
  });
}

test('контроль: измеритель ловит сдвиг, а не зеленеет по построению', async ({ page }) => {
  // Синтетическая страница того же класса, что и наша: текст, под ним картинка БЕЗ резерва
  // места — ни атрибутов width/height, ни размеров в CSS. Когда картинка приезжает, она
  // раздвигает содержимое, и CLS обязан вылезти за бюджет. Проверяем именно измеритель:
  // если он этого не увидит, зелёные проверки выше ничего не стоят.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route('**/__cls-control/', (route) =>
    route.fulfill({
      contentType: 'text/html',
      // Текста под картинкой на целый экран: CLS считается как доля затронутой площади,
      // умноженная на дистанцию, и на паре строк сдвиг вышел бы 0.02 — ниже бюджета,
      // хотя контент честно прыгнул на пол-экрана.
      body: `<!doctype html><meta charset="utf-8"><body style="margin:0;font:16px/1.6 system-ui">
        <p>Текст над картинкой.</p>
        <img src="/img/dnd/creatures/aboleth.webp">
        ${'<p>Текст под картинкой, заполняющий экран.</p>'.repeat(30)}</body>`,
    }));
  const cls = await clsOf(page, '/__cls-control/');
  // Сначала убеждаемся, что картинка вообще загрузилась. Иначе переименование файла дало бы
  // 404 → сдвига нет → падение с сообщением «измеритель сломан», хотя сломался путь. Саму
  // картинку перехватывать нельзя: уйдёт из-под троттлинга и приедет до отрисовки текста.
  const loaded = await page.evaluate(() => document.querySelector('img')?.naturalWidth ?? 0);
  expect(loaded, 'картинка контроля не загрузилась — проверь путь, а не измеритель').toBeGreaterThan(0);
  expect(cls, 'без резерва места картинка обязана двигать контент').toBeGreaterThan(CLS_BUDGET);
});
