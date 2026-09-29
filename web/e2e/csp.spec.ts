import { test, expect, type BrowserContext } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// CSP не ломает страницу (issue #225); полная инвентаризация по проду — `node scripts/check_csp.mjs`.
// Нарушения пишет браузер, консоль их не видит — слушаем `securitypolicyviolation` до скриптов
// страницы; preview отдаётся без заголовков хостинга — политику из firebase.json подставляем сами.

const csp = (() => {
  const hosting = JSON.parse(readFileSync(resolve(process.cwd(), '../firebase.json'), 'utf8')).hosting;
  const h = hosting.headers[0].headers.find((x: any) => x.key.startsWith('Content-Security-Policy'));
  if (!h) throw new Error('в firebase.json нет заголовка Content-Security-Policy');
  return h as { key: string; value: string };
})();

/**
 * Снять перехват до конца теста (#249): SW дотягивает ассеты в фоне, и колбэк route падает вне
 * теста («route.fetch: Test ended»). Хук, а не строка в конце: упавший `expect` обрывает тело.
 */
test.afterEach(async ({ context }) => {
  await context.unrouteAll({ behavior: 'ignoreErrors' });
});

const arm = async (context: BrowserContext) => {
  await context.addInitScript(() => {
    (window as any).__csp = [];
    document.addEventListener('securitypolicyviolation', (e) =>
      (window as any).__csp.push(`${e.effectiveDirective} ← ${e.blockedURI}`),
    );
  });
  await context.route('**/*', async (route) => {
    const res = await route.fetch();
    const headers = { ...res.headers() };
    if ((headers['content-type'] ?? '').includes('text/html')) headers[csp.key.toLowerCase()] = csp.value;
    await route.fulfill({ response: res, headers });
  });
};

test('политика не ломает главу, сущность и поиск', async ({ context }) => {
  await arm(context);
  const page = await context.newPage();

  await page.goto('/ru/dnd/srd-5.2/monsters-a-z/aboleth/');
  await expect(page.locator('h1')).toBeVisible();

  // Pagefind тянет воркер и wasm ('wasm-unsafe-eval' и worker-src в политике).
  await page.locator('input[type="text"]').first().fill('дракон');
  await expect(page.locator('mark').first()).toBeVisible({ timeout: 10_000 });

  expect(await page.evaluate(() => (window as any).__csp)).toEqual([]);
});

test('политика запрещает чужие источники (иначе гейт выше ничего не значит)', async ({ context }) => {
  await arm(context);
  const page = await context.newPage();
  await page.goto('/ru/');
  await page.evaluate(() => {
    const s = document.createElement('script');
    s.src = 'https://cdn.example.com/evil.js';
    document.head.appendChild(s);
  });
  // Ждём само событие, а не onerror скрипта: под нагрузкой событие приходит позже и проверка флакует.
  await page.waitForFunction(() => ((window as any).__csp ?? []).length > 0);
  expect(await page.evaluate(() => (window as any).__csp)).toContain(
    'script-src-elem ← https://cdn.example.com/evil.js',
  );
});
