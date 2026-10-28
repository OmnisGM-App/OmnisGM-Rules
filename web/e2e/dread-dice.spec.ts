import { test, expect } from '@playwright/test';

const URL_RU = '/ru/dnd/homebrew/dread-dice/';
const URL_EN = '/en/dnd/homebrew/dread-dice/';

test('калькулятор стоит в статье перед руководством мастера и свёрнут', async ({ page }) => {
  await page.goto(URL_RU);
  const calc = page.locator('details.dd');
  await expect(calc).toHaveCount(1);
  await expect(calc).not.toHaveAttribute('open', '');
  const order = await page.evaluate(() => {
    const d = document.querySelector('details.dd')!;
    const h = document.getElementById('руководство-мастера')!;
    return d.compareDocumentPosition(h) & Node.DOCUMENT_POSITION_FOLLOWING;
  });
  expect(order).toBeTruthy();
  expect(await page.content()).not.toContain('dread-dice-calculator');
});

test('по умолчанию: мешок 5+1 кружками, T=5, шансы следующей проверки', async ({ page }) => {
  await page.goto(URL_RU);
  await page.locator('details.dd > summary').click();
  await expect(page.locator('[data-dd-chance="normal"]')).toHaveText('3,3 %');
  await expect(page.locator('[data-dd-chance="advantage"]')).toHaveText('0,7 %');
  await expect(page.locator('[data-dd-chance="disadvantage"]')).toHaveText('6,0 %');
  await expect(page.locator('[data-dd-danger]')).toHaveText('опасны 1–4');
  await expect(page.locator('[data-dd-bag] .dd-die-dark')).toHaveCount(1);
  await expect(page.locator('[data-dd-bag] .dd-die-light')).toHaveCount(5);
});

test('ручной ввод: тёмная 3 при T=5 — событие и сброс к T₀, тёмная 9 — рост', async ({ page }) => {
  await page.goto(URL_EN);
  await page.locator('details.dd > summary').click();
  await page.locator('details.dd-more > summary').click();
  await page.locator('input[name="manualValue"]').fill('9');
  await page.locator('[data-dd-manual]').click();
  await expect(page.locator('input[name="threshold"]')).toHaveValue('6');
  await page.locator('input[name="manualValue"]').fill('3');
  await page.locator('[data-dd-manual]').click();
  await expect(page.locator('input[name="threshold"]')).toHaveValue('5');
  await expect(page.locator('[data-dd-log] li').first()).toContainText('threat event! · T 6 → 5');
});

test('пустой состав мешка — кнопки броска выключены, шанс 0', async ({ page }) => {
  await page.goto(URL_RU);
  await page.locator('details.dd > summary').click();
  for (const name of ['light', 'dark']) await page.locator(`input[name="${name}"]`).fill('0');
  await expect(page.locator('[data-dd-roll="normal"]')).toBeDisabled();
  await expect(page.locator('[data-dd-chance="normal"]')).toHaveText('0,0 %');
});

test.describe('без JavaScript', () => {
  test.use({ javaScriptEnabled: false });
  test('правила читаются, калькулятор называет причину', async ({ page }) => {
    await page.goto(URL_RU);
    await page.locator('details.dd > summary').click();
    await expect(page.locator('[data-dd-nojs]')).toBeVisible();
    await expect(page.locator('[data-dd-form]')).toBeHidden();
    await expect(page.locator('#руководство-мастера')).toBeVisible();
  });
});

test('футер хоумбрю — своя лицензия, без атрибуции SRD', async ({ page }) => {
  await page.goto(URL_RU);
  await expect(page.locator('.rd-attrib')).toContainText('Хоумбрю OmnisGM, не материал SRD.');
  await expect(page.locator('.rd-attrib')).not.toContainText('System Reference Document');
  await expect(page.locator('[data-testid="trademark"]')).toBeVisible();
});

test('ползунок состава сразу пересчитывает шанс и мешок', async ({ page }) => {
  await page.goto(URL_RU);
  await page.locator('details.dd > summary').click();
  await page.locator('input[name="dark"]').fill('3');
  await expect(page.locator('[data-dd-out="dark"]')).toHaveText('3');
  await expect(page.locator('[data-dd-bag] .dd-die-dark')).toHaveCount(3);
  await expect(page.locator('[data-dd-chance="normal"]')).toHaveText('7,5 %');
});

/** Значение ползунка одним `input`, без `change` — как промежуточный шаг перетаскивания. */
async function dragStep(page: import('@playwright/test').Page, name: string, value: string) {
  await page.locator(`input[name="${name}"]`).evaluate((el, v) => {
    (el as HTMLInputElement).value = v;
    el.dispatchEvent(new Event('input', { bubbles: true }));
  }, value);
}

test('один жест T₀ без change через край: надбавка сохраняется (T=8, T₀ 5→20→10 → T=13)', async ({ page }) => {
  await page.goto(URL_RU);
  await page.locator('details.dd > summary').click();
  await page.locator('input[name="threshold"]').fill('8');
  for (const v of ['6', '10', '15', '20', '15', '10']) await dragStep(page, 'base', v);
  await expect(page.locator('input[name="threshold"]')).toHaveValue('13');
});

test('change между жестами сбрасывает якорь (T=18, T₀ 5→20, затем 20→5 → T=5)', async ({ page }) => {
  await page.goto(URL_RU);
  await page.locator('details.dd > summary').click();
  await page.locator('input[name="threshold"]').fill('18');
  await page.locator('input[name="base"]').fill('20');
  await page.locator('input[name="base"]').fill('5');
  await expect(page.locator('input[name="threshold"]')).toHaveValue('5');
});

test('pointerdown начинает новый жест: T=8, жест T₀ 5→20 без change, затем 20→10 → T=10', async ({ page }) => {
  await page.goto(URL_RU);
  await page.locator('details.dd > summary').click();
  await page.locator('input[name="threshold"]').fill('8');
  for (const v of ['10', '20']) await dragStep(page, 'base', v);
  await expect(page.locator('input[name="threshold"]')).toHaveValue('20');
  await page.locator('input[name="base"]').dispatchEvent('pointerdown');
  await dragStep(page, 'base', '10');
  await expect(page.locator('input[name="threshold"]')).toHaveValue('10');
});

test('жест T₀ без change → ручной ввод → другой ползунок: T и журнал на месте', async ({ page }) => {
  await page.goto(URL_RU);
  await page.locator('details.dd > summary').click();
  await page.locator('details.dd-more > summary').click();
  for (const v of ['6', '9', '6', '5']) await dragStep(page, 'base', v);
  await dragStep(page, 'manualValue', '9');
  await page.locator('[data-dd-manual]').dispatchEvent('click');
  await expect(page.locator('input[name="threshold"]')).toHaveValue('6');
  await dragStep(page, 'dark', '3');
  await expect(page.locator('input[name="threshold"]')).toHaveValue('6');
  await expect(page.locator('[data-dd-log] li')).toHaveCount(1);
});
