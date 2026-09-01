import { test, expect, type APIRequestContext } from '@playwright/test';

// robots.txt (issue #229). Проверяется не «строка есть в файле», а СМЫСЛ: правило действует
// для конкретного бота. Грабля, ради которой этот спек и написан: секция `User-agent: Yandex`
// полностью ЗАМЕЩАЕТ `*` — правило, добавленное только в `*`, для Яндекса не существует.
// Один раз на этом уже обожглись с /api/ (см. комментарий в самом robots.txt).

const groups = (txt: string) => {
  const out = new Map<string, string[]>();
  let current: string[] = [];
  for (const raw of txt.split('\n')) {
    const line = raw.replace(/#.*$/, '').trim();
    if (!line) continue;
    const [k, ...rest] = line.split(':');
    const key = k.trim().toLowerCase();
    const value = rest.join(':').trim();
    if (key === 'user-agent') {
      current = out.get(value) ?? [];
      out.set(value, current);
    } else if (key === 'disallow' && value) {
      current.push(value);
    }
  }
  return out;
};

const robots = async (request: APIRequestContext) => {
  const res = await request.get('/robots.txt');
  expect(res.ok()).toBeTruthy();
  return groups(await res.text());
};

test('технические ассеты закрыты для ВСЕХ ботов, включая Яндекс', async ({ request }) => {
  const g = await robots(request);
  for (const agent of ['*', 'Yandex']) {
    const rules = g.get(agent);
    expect(rules, `нет секции User-agent: ${agent}`).toBeTruthy();
    // /pagefind — индексы клиентского поиска, /hc — бандлы ховеркардов (до 660 КБ файл).
    expect(rules, `${agent}: не закрыт /pagefind/`).toContain('/pagefind/');
    expect(rules, `${agent}: не закрыт /hc/`).toContain('/hc/');
    expect(rules, `${agent}: не закрыт /api/`).toContain('/api/');
  }
});

test('закрытие в robots не ломает сам сайт: поиск и ховеркарды живы', async ({ page }) => {
  // robots.txt — инструкция краулерам, браузер его не читает. Тест страхует от подмены
  // смысла: если однажды кто-то «закроет» пути редиректом или 404 вместо robots, тут упадёт.
  await page.goto('/en/dnd/srd-5.2/spells/fireball/');
  await page.locator('input[type="text"]').first().fill('dragon');
  await expect(page.locator('mark').first()).toBeVisible({ timeout: 10_000 });

  const hc = await page.request.get('/hc/dnd/srd52/en.json');
  expect(hc.ok(), 'бандл ховеркардов должен отдаваться браузеру').toBeTruthy();
});
