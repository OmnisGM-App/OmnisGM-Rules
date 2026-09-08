import { defineConfig, devices } from '@playwright/test';
// Порт — от слота (Table#469): соседний worktree берёт OMNISGM_SLOT=1 и не мешает этому.
import { E2E_PORT as PORT, BASE_URL as BASE } from './e2e/ports';

// Спеки, которые имеет смысл гонять на узком экране: навигационный костяк ридера. Список
// ЯВНЫЙ, а не маска: маска затянула бы визуальные снапшоты и проверки меты, которые от
// ширины не зависят, и удвоила бы прогон без единой новой находки (#286).
const MOBILE_SPECS = [
  /reader\.spec\.ts/,
  /doc-hub\.spec\.ts/,
  /lang\.spec\.ts/,
  /404\.spec\.ts/,
];

// E2E гоняются ЛОКАЛЬНО (npm run test:e2e), в CI не тащим — там только astro check + build.
// Тестируем прод-вывод: собираем бандл и поднимаем `astro preview` (ровно то, что уедет
// на хостинг), а не dev-сервер.
export default defineConfig({
  testDir: './e2e',
  // Страж чужого preview на нашем порту — см. комментарий в самом файле.
  globalSetup: './e2e/global-setup.ts',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: BASE,
    trace: 'on-first-retry',
  },
  // Визуальные снапшоты (e2e/visual.spec.ts): небольшой допуск под сглаживание.
  // Baseline привязаны к платформе (…-darwin.png) — гоняем локально на одной машине,
  // кросс-ОС расхождений нет (в CI e2e не запускаем). Обновление:
  //   rm -rf node_modules/.vite && npm run test:e2e -- visual --update-snapshots
  expect: {
    // maxDiffPixels (абсолют), а НЕ maxDiffPixelRatio: небольшое цветовое изменение
    // (напр. цвет ссылок ~2000 пикс.) — это <1% полной страницы, и ratio 0.01 такое
    // «проглатывал» (снапшот не ловил регрессию и не обновлялся). Абсолютный порог
    // терпит AA-джиттер шрифтов, но ловит реальные правки.
    toHaveScreenshot: { maxDiffPixels: 80, animations: 'disabled' },
  },
  projects: [
    // Основной набор: десктопный Chromium, все спеки, включая пиксельные снапшоты.
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    // Мобильный вьюпорт (#286). Ридер — публичная страница, и телефон у неё основной
    // носитель, а до сих пор мобильную вёрстку трогали ровно два спека из 37, каждый
    // своим `setViewportSize`.
    //
    // Гоняем НЕ ВЕСЬ набор, и это осознанно (урок Table#377): вторая полная матрица удваивает
    // время и приносит одни и те же падения дважды. Здесь — навигационный костяк: то, что
    // на узком экране действительно перестраивается (шапка, дерево разделов, хаб, тумблер
    // языка). Спеки про мету, sitemap, JSON-LD и robots от ширины не зависят вовсе.
    {
      name: 'mobile',
      testMatch: MOBILE_SPECS,
      use: { ...devices['Pixel 7'] },
    },
    // WebKit (движок Safari) на том же вьюпорте — смоук, а не матрица: только тесты с
    // тегом @cross-engine. Пиксельные снапшоты пропускаем — кросс-движковой пиксель-парити
    // не существует (шрифты и сглаживание рендерятся иначе), сравнение шло бы движка с
    // самим собой.
    //
    // ВАЖНО и проверено на своей шкуре: Playwright-WebKit НЕ ловит квирки НАТИВНЫХ контролов
    // Safari — там был ложный зелёный на сломанном <select>. Этот проект закрывает движок
    // (раскладка, поддержка CSS/JS), а не браузер; ручной смоук в Safari он не отменяет.
    {
      name: 'webkit-mobile',
      testMatch: MOBILE_SPECS,
      grep: /@cross-engine/,
      ignoreSnapshots: true,
      use: { ...devices['iPhone 14'] },
    },
  ],
  webServer: {
    command: `npm run build && npm run preview -- --port ${PORT}`,
    url: BASE,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
