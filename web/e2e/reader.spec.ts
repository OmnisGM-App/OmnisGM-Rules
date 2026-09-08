import { test, expect } from '@playwright/test';
import { isNarrow } from './viewport';

// Смоук ридера: страница правил открывается, рендерится бренд-шапка и навигация по разделам.
//
// Из проверяемого этим спеком навигация — единственное, что на узком экране устроено
// принципиально иначе: боковой aside скрывается, а разделы уезжают в выдвижную панель за
// кнопкой «Разделы». Мобильная раскладка меняет и другое (вкладки систем и язык становятся
// <select>, поиск — кнопкой); язык покрыт `lang.spec.ts`, переключение системы и поиск на
// узком экране не покрыты ничем (ревью #302).
test('главная ридера рендерит бренд-шапку и разделы @cross-engine', async ({ page }) => {
  await page.goto('/en/');

  await expect(page.locator('.rd-brand-name')).toHaveText('OmnisGM');
  await expect(page.locator('.rd-brand-sub')).toContainText('rules');

  if (isNarrow(page)) {
    // Боковой aside по ширине скрыт — разделы открываются кнопкой и живут в панели-диалоге.
    await expect(page.locator('.rd-nav')).toBeHidden();

    // Панель закрыта НЕ через display/visibility, а сдвигом за экран
    // (`transform: translateX(-100%)`, reader.css). Для `toBeVisible()` она видима всегда:
    // матчер смотрит CSS-видимость и непустой bounding box, а не положение относительно
    // вьюпорта — то есть проверял бы кликабельность кнопки, но не то, что панель выехала
    // (ревью #302). Поэтому смотрим геометрию: до клика панель левее экрана, после — в нём.
    const drawer = page.locator('.rd-drawer');
    const closed = await drawer.boundingBox();
    expect(closed, 'панель разделов должна быть в DOM до открытия').not.toBeNull();
    expect(closed!.x + closed!.width).toBeLessThanOrEqual(1);

    await page.locator('.rd-act-nav').click();

    // Панель выезжает transition'ом, поэтому ждём геометрию, а не снимаем её сразу:
    // мгновенный boundingBox поймал бы середину анимации (или её начало) и дал ложное
    // красное на работающей панели.
    await expect
      .poll(async () => (await drawer.boundingBox())?.x ?? -1, { timeout: 5000 })
      .toBeGreaterThanOrEqual(0);

    const opened = await drawer.boundingBox();
    expect(opened!.width).toBeGreaterThan(100);
    // …и в выехавшей панели действительно есть разделы, а не пустой контейнер.
    const item = drawer.locator('.rd-nav-page, .rd-nav-group').first();
    const itemBox = await item.boundingBox();
    expect(itemBox, 'в панели нет ни одного раздела').not.toBeNull();
    expect(itemBox!.x).toBeGreaterThanOrEqual(0);
  } else {
    await expect(page.locator('.rd-nav')).toBeVisible();
    // На широком экране скрима нет, и панель разделов не нужна.
    await expect(page.locator('.rd-systabs')).toBeVisible();
  }
});
