import { defineConfig, devices } from '@playwright/test';

// E2E гоняются ЛОКАЛЬНО (npm run test:e2e), в CI не тащим — там только astro check + build.
// Тестируем прод-вывод: собираем бандл и поднимаем `astro preview` (ровно то, что уедет
// на хостинг), а не dev-сервер.
const PORT = 4321;
const BASE = `http://localhost:${PORT}`;

export default defineConfig({
  testDir: './e2e',
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
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `npm run build && npm run preview -- --port ${PORT}`,
    url: BASE,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
