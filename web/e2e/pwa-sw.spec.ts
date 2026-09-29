import { test, expect } from '@playwright/test';
import fs from 'node:fs';

// Service worker: что в нём должно быть и, главное, чего быть не должно (issue #224).
// Собранный sw.js читаем файлом, а не через браузер: рантайм-роуты внутри него — код, который
// на живой странице никак не проявляется, пока не совпадёт URL. Мёртвое правило и работающее
// выглядят в браузере одинаково — никак.

const sw = () => fs.readFileSync('dist/sw.js', 'utf-8');

test('шрифты self-hosted: ни одного роута к Google Fonts', () => {
  // Шрифты лежат в public/fonts и уезжают в precache; роут к Google Fonts был бы мёртвым
  // кодом, который читается как рабочая политика, и с enforce-CSP (#225) ещё и нерабочим.
  expect(sw()).not.toMatch(/googleapis|gstatic|google-fonts/);
});

test('шрифты precache-ятся из своей папки', () => {
  const fonts = [...sw().matchAll(/fonts\/[^"']+\.woff2/g)].map((m) => m[0]);
  // Не «больше нуля»: набор начертаний фиксирован, и молчаливая потеря половины из них —
  // это ровно тот случай, который порогом «>0» не ловится.
  expect(new Set(fonts).size).toBe(18);
});

test('рантайм-кэши — только те, что нам нужны', () => {
  const names = [...sw().matchAll(/cacheName:"([a-z-]+)"/g)].map((m) => m[1]).sort();
  expect([...new Set(names)]).toEqual(['entity-images', 'pagefind', 'pages']);
});
