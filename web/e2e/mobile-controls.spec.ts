import { test, expect } from '@playwright/test';
import { isBarCompact } from './viewport';

// Тач-ввод и свёрнутые контролы бара (issue #308).
//
// Всё это на десктопе НЕДОСТИЖИМО: тач-ветка hovercard отсекается по `pointerType`, а селект
// систем и кнопка поиска показываются только под `@media (max-width: 920px)`. До #308 их не
// проверял никто — регресс был виден только руками на телефоне, а мобильный трафик у
// публичного ридера основной (ревью #302).

// Глава заклинаний RU — самая плотная по автоссылкам на состояния.
const CHAPTER = '/ru/dnd/srd-5.2/spells/';

test.describe('тач-ввод', () => {
  // Тач-ветка проверяется только там, где тач есть: в десктопном Chromium её не достать
  // вовсе, а `.tap()` без `hasTouch` падает с внятной ошибкой Playwright.
  test.skip(({ hasTouch }) => !hasTouch, 'проект без тач-ввода');

  // Контракт со стороны пользователя: первый тап по автоссылке — это переход, а не «показ
  // карточки, потом ещё раз». Регресс самой ветки ловит соседний тест на `.gloss` (здесь
  // страница уезжает, и по её DOM после перехода уже ничего не докажешь).
  test('тап по автоссылке ведёт по ссылке с первого раза @cross-engine', async ({ page }) => {
    await page.goto(CHAPTER);
    const link = page.locator('.rd-doc a.ent-link[data-hc]').first();
    await expect(link).toBeVisible();
    const href = await link.getAttribute('href');
    expect(href, 'у автоссылки есть адрес — тап обязан куда-то вести').toBeTruthy();

    await link.tap();
    await page.waitForURL(`**${href}`);
  });

  // Главный страж ветки `pointerType === 'touch'`. Термин `.gloss` для этого и годится:
  // страницы у него нет, тап никуда не уводит, и DOM остаётся на месте — а на десктопе
  // ровно тот же элемент карточку показывает (hovercard.spec.ts).
  test('тап по глоссарному термину не открывает карточку', async ({ page }) => {
    await page.goto(CHAPTER);
    const gloss = page.locator('.rd-doc .gloss[data-hc]').first();
    // Термины ядра есть не в каждой главе — если их тут нет, проверять нечего.
    test.skip(await gloss.count() === 0, 'на странице нет глоссарных терминов');
    await gloss.tap();

    // Ждём ДОЛЬШЕ задержки показа (130 мс в ReaderShell) и только потом утверждаем «нет».
    // Мгновенная проверка `toHaveCount(0)` зелена по построению: матчер ретраится до успеха,
    // а на нулевой миллисекунде карточки нет и у сломанной ветки — проверено мутацией (#308).
    await page.waitForTimeout(500);
    await expect(page.locator('#ent-hovercard')).toHaveCount(0);
  });
});

test.describe('свёрнутые контролы бара', () => {
  test.skip(({ viewport }) => (viewport?.width ?? 0) > 920, 'широкий вьюпорт — контролы не свёрнуты');

  test('выбор системы в селекте ведёт на её страницу', async ({ page }) => {
    await page.goto('/ru/');
    expect(isBarCompact(page), 'вьюпорт проекта попадает под порог 920px').toBe(true);

    const menu = page.locator('select.rd-sysmenu');
    await expect(menu).toBeVisible();
    // Вкладки-ссылки на этой ширине спрятаны — иначе селект был бы декорацией.
    await expect(page.locator('.rd-systab').first()).toBeHidden();

    // Берём вариант, отличный от текущего: выбор уже выбранного не вызвал бы `change`,
    // и тест был бы зелёным при полностью мёртвом обработчике.
    const options = menu.locator('option');
    const values = await options.evaluateAll((els) =>
      els.map((el) => ({ value: (el as HTMLOptionElement).value, selected: (el as HTMLOptionElement).selected })));
    const other = values.find((o) => !o.selected && o.value);
    expect(other, 'в селекте есть хотя бы одна невыбранная система').toBeTruthy();

    await menu.selectOption(other!.value);
    await page.waitForURL(`**${other!.value}`);
    await expect(page.locator('.rd-doc, .rd-hub').first()).toBeVisible();
  });

  test('поиск открывается кнопкой', async ({ page }) => {
    await page.goto('/ru/');
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
