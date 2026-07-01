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
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `npm run build && npm run preview -- --port ${PORT}`,
    url: BASE,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
