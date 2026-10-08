import { defineConfig, devices } from '@playwright/test';
import { E2E_PORT as PORT, BASE_URL as BASE } from './e2e/ports';
import { NARROW_MAX } from './e2e/viewport';

// Спеки проекта `mobile`. Список ЯВНЫЙ, а не маска: маска затянула бы визуальные снапшоты и
// весь набор целиком, удвоив прогон без единой новой находки (#286).
// `404` от ширины не зависит — он здесь ради мобильного Chromium: частый вход из выдачи.
const MOBILE_SPECS = [
  /reader\.spec\.ts/,
  /doc-hub\.spec\.ts/,
  /lang\.spec\.ts/,
  /404\.spec\.ts/,
  // Тач-ввод и свёрнутые контролы бара (#308): на десктопе обе ветки сами себя пропускают.
  /mobile-controls\.spec\.ts/,
  // Страницы групп вариантов и таблица хаба (#379) — на узком экране.
  /class-options\.spec\.ts/,
];

// Свой вьюпорт, а не дескрипторов: у Pixel 7 и iPhone 14 он разный, а движки сравниваем на одной ширине.
const MOBILE_VIEWPORT = { width: 390, height: 844 };

if (MOBILE_VIEWPORT.width > NARROW_MAX) {
  throw new Error(`Мобильный вьюпорт ${MOBILE_VIEWPORT.width}px шире порога узкой ` +
                  `раскладки ${NARROW_MAX}px — проекты mobile/webkit-mobile проверяли бы десктоп`);
}

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: BASE,
    trace: 'on-first-retry',
  },
  // Baseline — …-darwin.png, e2e только локально. Обновление (кэш .vite отдаёт старый код):
  //   rm -r node_modules/.vite && npm run test:e2e -- visual --update-snapshots
  expect: {
    // maxDiffPixels, а не ratio: 0.01 полной страницы проглатывал смену цвета ссылок (~2000 пикс.).
    toHaveScreenshot: { maxDiffPixels: 80, animations: 'disabled' },
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    // Не весь набор (урок Table#377): вторая полная матрица удваивает время ради тех же падений.
    {
      name: 'mobile',
      testMatch: MOBILE_SPECS,
      use: { ...devices['Pixel 7'], viewport: MOBILE_VIEWPORT },
    },
    // Смоук по тегу @cross-engine; снапшоты пропускаем — кросс-движкового пиксель-парити нет.
    // Playwright-WebKit НЕ ловит квирки нативных контролов Safari (ложный зелёный на <select>).
    {
      name: 'webkit-mobile',
      // Только `grep`: с `testMatch` они конъюнктивны, и тег вне MOBILE_SPECS молча не запускался бы.
      grep: /@cross-engine/,
      ignoreSnapshots: true,
      use: { ...devices['iPhone 14'], viewport: MOBILE_VIEWPORT },
    },
  ],
  webServer: {
    command: `npm run build && npm run preview -- --port ${PORT}`,
    url: BASE,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
