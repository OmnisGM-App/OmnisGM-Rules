import { test, expect } from '@playwright/test';
import { hostingRedirects } from '../src/lib/hosting-redirects.mjs';

// Редиректы хостинга (`hosting.redirects` в firebase.json) против dist (#399). Источник 301 на проде
// недостижим — страницы под ним в сборке быть не должно (иначе она живёт вне навигации и проверок), а цель
// обязана существовать: 301 в пустоту хуже дубля. Preview хостинговых редиректов не исполняет — поэтому
// источник здесь честно 404, а цель 200.
const redirects = hostingRedirects();

test('в firebase.json есть редиректы — проверять есть что', () => {
  expect(redirects.length).toBeGreaterThan(0);
});

// Источник с `:lang` — два адреса, без него — один. Страница — со слэшем, файл (`/sitemap.xml`) — как есть.
const pairs = redirects.flatMap((r) => (r.source.includes(':lang') ? ['en', 'ru'] : ['']).map((lang) => {
  const sub = (p: string) => (lang ? p.replaceAll(':lang', lang) : p);
  const from = sub(r.source);
  return { type: r.type, from: /\.[a-z]+$/.test(from) ? from : `${from}/`, to: sub(r.destination) };
}));

for (const { type, from, to } of pairs) {
  test(`301 ${from} → ${to}: источник не собран, цель собрана`, async ({ request }) => {
    expect(type).toBe(301);
    expect((await request.get(from)).status(), from).toBe(404);
    expect((await request.get(to)).status(), to).toBe(200);
  });
}
