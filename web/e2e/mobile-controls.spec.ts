import { test, expect } from '@playwright/test';
import { isNarrow, isSearchCollapsed, NARROW_MAX, BAR_COMPACT_MAX } from './viewport';

// Тач-ввод и свёрнутые контролы бара (issue #308).
//
// Всё это на десктопе НЕДОСТИЖИМО: тач-ветка hovercard отсекается по `pointerType`, а селект
// систем и кнопка поиска показываются только под своими media-порогами. До #308 их не проверял
// никто — регресс был виден только руками на телефоне, а мобильный трафик у публичного ридера
// основной (ревью #302).
//
// Порогов ДВА, и они разные: поиск сворачивается на 920, а навигация и селект систем — на 820
// (ревью #316 поймало, что описание путало их). Гейты берут константы, а не литералы: литерал,
// разошедшийся с CSS, — ровно тот дефект, ради которого заведён `viewport.ts`.

// Глава заклинаний RU — самая плотная по автоссылкам и глоссарным терминам.
const CHAPTER = '/ru/dnd/srd-5.2/spells/';

test.describe('тач-ввод', () => {
  // Тач-ветка проверяется только там, где тач есть: в десктопном Chromium её не достать
  // вовсе, а `.tap()` без `hasTouch` падает с внятной ошибкой Playwright.
  test.skip(({ hasTouch }) => !hasTouch, 'проект без тач-ввода');

  // Что этот тест доказывает — и чего НЕ доказывает. Он пинует пользовательский контракт
  // («тап по автоссылке не выкидывает карточку»), но стражем кода не является: снятие гейта
  // `pointerType` оставляет его зелёным в обоих движках — Playwright на `.tap()` шлёт
  // touch-события, а совместимостный `pointerover`, ради которого гейт и написан, шлёт
  // настоящее устройство. Проверено мутацией; сказано вслух, чтобы следующий не принял
  // зелёное за подтверждение гейта (ревью #316).
  test('тап по автоссылке не открывает карточку @cross-engine', async ({ page }) => {
    await page.goto(CHAPTER);
    const link = page.locator('.rd-doc a.ent-link[data-hc]').first();
    await expect(link).toBeVisible();
    const href = (await link.getAttribute('href'))!;
    expect(href, 'у автоссылки есть адрес — тап обязан куда-то вести').toBeTruthy();

    // Переход глушим, а не ждём: иначе документ выгружается прежде, чем карточка успела бы
    // появиться, и тест был бы зелёным при полностью снятом запрете (ревью #316). С
    // оборванной навигацией страница остаётся на месте, и «карточки нет» — настоящее
    // утверждение о поведении, а не гонка с выгрузкой.
    await page.route(`**${href}`, (route) => route.abort());
    await link.tap();

    // Ждём дольше и таймера показа (130 мс), и ответа на ленивый `fetch` бакета: карточка
    // монтируется в `.then()`, поэтому граница негативного утверждения — «таймер + сеть».
    await page.waitForTimeout(700);
    await expect(page.locator('#ent-hovercard')).toHaveCount(0);
  });

  test('тап по глоссарному термину ОТКРЫВАЕТ карточку @cross-engine', async ({ page }) => {
    await page.goto(CHAPTER);
    const gloss = page.locator('.rd-doc .gloss[data-hc]').first();
    // Не `test.skip` при пустом наборе: страж, который умеет молча отключиться, — не страж.
    // Термины ядра на этой странице есть, и их исчезновение обязано краснеть (ревью #316).
    expect(await gloss.count(), 'глава обязана содержать глоссарные термины').toBeGreaterThan(0);

    await gloss.tap();
    // У `.gloss` нет `href` — перехватывать тапом нечего, и на телефоне это ЕДИНСТВЕННЫЙ
    // способ прочитать определение. Запрет тач-показа касается только ссылок (#308/#316).
    await expect(page.locator('#ent-hovercard')).toBeVisible();
  });

  // Тач не должен «отравлять» клавиатурный путь на остаток жизни страницы: именно это
  // делала первая редакция #308, запоминавшая источник ввода глобально.
  test('после тапа клавиатурный фокус по-прежнему показывает карточку', async ({ page }) => {
    await page.goto(CHAPTER);
    const gloss = page.locator('.rd-doc .gloss[data-hc]').first();
    const link = page.locator('.rd-doc a.ent-link[data-hc]').first();
    await expect(link).toBeVisible();

    await gloss.tap();
    await expect(page.locator('#ent-hovercard')).toBeVisible();
    await page.keyboard.press('Escape');

    await page.keyboard.press('Tab');
    await link.focus();
    await expect(page.locator('#ent-hovercard')).toBeVisible();
  });
});

test.describe('селект систем на узком экране', () => {
  test.skip(({ viewport }) => (viewport?.width ?? 0) > NARROW_MAX, 'широкий вьюпорт — вкладки систем на месте');

  test('выбор системы в селекте ведёт на её страницу', async ({ page }) => {
    await page.goto('/ru/');
    expect(isNarrow(page), 'вьюпорт проекта попадает под порог мобильной раскладки').toBe(true);

    const menu = page.locator('select.rd-sysmenu');
    await expect(menu).toBeVisible();
    // Вкладки-ссылки на этой ширине спрятаны — иначе селект был бы декорацией.
    await expect(page.locator('.rd-systab').first()).toBeHidden();

    // Берём вариант, отличный от текущего: выбор уже выбранного не вызвал бы `change`,
    // и тест был бы зелёным при полностью мёртвом обработчике.
    const values = await menu.locator('option').evaluateAll((els) =>
      els.map((el) => ({ value: (el as HTMLOptionElement).value, selected: (el as HTMLOptionElement).selected })));
    const other = values.find((o) => !o.selected && o.value);
    expect(other, 'в селекте есть хотя бы одна невыбранная система').toBeTruthy();

    await menu.selectOption(other!.value);
    await page.waitForURL(`**${other!.value}`);
    await expect(page.locator('.rd-doc')).toBeVisible();
  });
});

test.describe('поиск на узком экране', () => {
  test.skip(({ viewport }) => (viewport?.width ?? 0) > BAR_COMPACT_MAX, 'широкий вьюпорт — поле поиска в баре');

  test('поиск открывается кнопкой', async ({ page }) => {
    await page.goto('/ru/');
    expect(isSearchCollapsed(page), 'вьюпорт проекта попадает под порог свёрнутого поиска').toBe(true);
    // Поле в баре на этой ширине убрано, вместо него — лупа.
    await expect(page.locator('.rd-bar-actions .rd-search-slot')).toBeHidden();
    const button = page.locator('.rd-act-search');
    await expect(button).toBeVisible();

    const overlay = page.locator('.rd-search-overlay');
    // Оверлей закрыт НЕ через display: он всегда в потоке, а гасится `opacity: 0` +
    // `pointer-events: none` (reader.css). Для `toBeVisible()` он видим и закрытым — ровно
    // та же слепота матчера, что у выехавшей панели разделов (ревью #302), только по другому
    // свойству. Поэтому смотрим вычисленный стиль.
    const state = () => overlay.evaluate((el) => {
      const s = getComputedStyle(el);
      return { opacity: Number(s.opacity), clickable: s.pointerEvents !== 'none' };
    });
    expect(await state()).toEqual({ opacity: 0, clickable: false });

    await button.click();
    // Оверлей проявляется transition'ом (.15s) — ждём состояние, а не снимаем его сразу.
    await expect.poll(state, { timeout: 5000 }).toEqual({ opacity: 1, clickable: true });
    await expect(overlay.locator('input[type="text"]').first()).toBeVisible();

    // И закрывается: незакрываемый полноэкранный поиск запирает страницу на телефоне.
    await overlay.locator('.rd-drawer-x').click();
    await expect.poll(state, { timeout: 5000 }).toEqual({ opacity: 0, clickable: false });
  });
});
