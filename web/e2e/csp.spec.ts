import { test, expect, type BrowserContext } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// CSP не ломает страницу (issue #225). Регрессионный гейт: если кто-то добавит на страницу
// внешний скрипт/шрифт/запрос, не описанный политикой, тест покраснеет ЗДЕСЬ, а не на проде
// белым экраном. Полная инвентаризация источников — `node scripts/check_csp.mjs` (гоняется
// по проду: часть источников существует только на эдже, напр. beacon Cloudflare).
//
// Важно про метод: нарушения CSP пишет сам браузер, и через API чтения консоли они не видны —
// ловим событие `securitypolicyviolation`, причём слушатель ставится ДО скриптов страницы.
// Локальный preview отдаётся без заголовков хостинга, поэтому политику из firebase.json
// подставляем сами — тестируем ровно то, что уедет на прод.

const csp = (() => {
  const hosting = JSON.parse(readFileSync(resolve(process.cwd(), '../firebase.json'), 'utf8')).hosting;
  const h = hosting.headers[0].headers.find((x: any) => x.key.startsWith('Content-Security-Policy'));
  if (!h) throw new Error('в firebase.json нет заголовка Content-Security-Policy');
  return h as { key: string; value: string };
})();

/**
 * Снять перехват до конца теста (#249).
 *
 * `arm` вешает route на ВЕСЬ трафик, а страница продолжает грузить ассеты и после проверок:
 * service worker дотягивает css/js в фоне (в логе видно `referer: /sw.js`). Когда тест
 * заканчивается раньше этих запросов, колбэк route падает уже вне теста — «route.fetch: Test
 * ended», и Playwright засчитывает прогону ошибку вне теста, а один тест остаётся
 * незапущенным. Гонка тайминговая: проявляется тем чаще, чем быстрее идут соседние тесты.
 *
 * Именно ХУК, а не строка в конце каждого теста: первый упавший `expect` обрывает тело, и
 * перехват остался бы висеть ровно в том случае, ради которого этот файл написан, — при
 * настоящей регрессии CSP. Тогда поверх честного падения легла бы ещё и «route.fetch: Test
 * ended» с незапущенным тестом. `afterEach` выполняется и после упавшего тела, и после
 * таймаута, и покрывает будущие тесты файла даром.
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

  // Поиск — самое рисковое место: Pagefind тянет воркер и wasm (отсюда 'wasm-unsafe-eval'
  // и worker-src в политике). Ищем то, что заведомо найдётся.
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
  // Ждём САМО событие нарушения, а не onerror скрипта: под нагрузкой (полный прогон в 6
  // воркеров) событие приходит позже колбэка загрузки, и проверка «сразу после» флакует.
  await page.waitForFunction(() => ((window as any).__csp ?? []).length > 0);
  expect(await page.evaluate(() => (window as any).__csp)).toContain(
    'script-src-elem ← https://cdn.example.com/evil.js',
  );
});
