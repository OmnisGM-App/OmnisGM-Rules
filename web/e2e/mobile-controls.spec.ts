import { test, expect } from '@playwright/test';
import { isNarrow, isSearchCollapsed, NARROW_MAX, BAR_COMPACT_MAX } from './viewport';

// Тач-ввод и свёрнутые контролы бара (issue #308) — на десктопе недостижимы. Порогов два и они
// разные — константы из `viewport.ts`, а не литералы.

// Глава заклинаний RU — самая плотная по автоссылкам и глоссарным терминам.
const CHAPTER = '/ru/dnd/srd-5.2/spells/';

test.describe('тач-ввод', () => {
  // `.tap()` без `hasTouch` падает, а в десктопном Chromium тач-ветку не достать.
  test.skip(({ hasTouch }) => !hasTouch, 'проект без тач-ввода');

  // Слепое пятно: снятие гейта `pointerType` оставляет тест зелёным — `.tap()` шлёт touch-события,
  // а совместимостный `pointerover` шлёт только настоящее устройство (проверено мутацией, #316).
  test('тап по автоссылке не открывает карточку @cross-engine', async ({ page }) => {
    await page.goto(CHAPTER);
    const link = page.locator('.rd-doc a.ent-link[data-hc]').first();
    await expect(link).toBeVisible();
    const href = (await link.getAttribute('href'))!;
    expect(href, 'у автоссылки есть адрес — тап обязан куда-то вести').toBeTruthy();

    // Переход глушим: иначе документ выгрузится раньше, чем карточка успела бы появиться (#316).
    await page.route(`**${href}`, (route) => route.abort());
    await link.tap();

    // Дольше таймера показа (130 мс) и ленивого `fetch` бакета: карточка монтируется в `.then()`.
    await page.waitForTimeout(700);
    await expect(page.locator('#ent-hovercard')).toHaveCount(0);
  });

  test('тап по глоссарному термину ОТКРЫВАЕТ карточку @cross-engine', async ({ page }) => {
    await page.goto(CHAPTER);
    const gloss = page.locator('.rd-doc .gloss[data-hc]').first();
    // Не `test.skip` при пустом наборе: исчезновение терминов обязано краснеть.
    expect(await gloss.count(), 'глава обязана содержать глоссарные термины').toBeGreaterThan(0);

    await gloss.tap();
    // У `.gloss` нет `href`: на телефоне тап — единственный способ прочитать определение (#308).
    await expect(page.locator('#ent-hovercard')).toBeVisible();
  });

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

    // Вариант, отличный от текущего: выбор уже выбранного не вызвал бы `change`.
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
    await expect(page.locator('.rd-bar-actions .rd-search-slot')).toBeHidden();
    const button = page.locator('.rd-act-search');
    await expect(button).toBeVisible();

    const overlay = page.locator('.rd-search-overlay');
    // Закрыт через `opacity: 0` + `pointer-events: none` (reader.css): `toBeVisible()` видит его всегда.
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
