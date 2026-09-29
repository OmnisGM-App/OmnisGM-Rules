import { test, expect } from '@playwright/test';
import fs from 'node:fs';

// Service worker (issue #224): sw.js читаем файлом — мёртвый рантайм-роут в браузере никак не проявляется.

const sw = () => fs.readFileSync('dist/sw.js', 'utf-8');

test('шрифты self-hosted: ни одного роута к Google Fonts', () => {
  expect(sw()).not.toMatch(/googleapis|gstatic|google-fonts/);
});

test('шрифты precache-ятся из своей папки', () => {
  const fonts = [...sw().matchAll(/fonts\/[^"']+\.woff2/g)].map((m) => m[0]);
  // Не «> 0»: набор начертаний фиксирован, потеря половины порогом не ловится.
  expect(new Set(fonts).size).toBe(18);
});

test('рантайм-кэши — только те, что нам нужны', () => {
  const names = [...sw().matchAll(/cacheName:"([a-z-]+)"/g)].map((m) => m[1]).sort();
  expect([...new Set(names)]).toEqual(['entity-images', 'pagefind', 'pages']);
});
