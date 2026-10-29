// Заголовки в `firebase.json`, пропажу которых не видят ни сборка, ни e2e. Картинки сущностей (#378):
// `Access-Control-Allow-Origin: *` даёт сторонней PWA (компендиум Table) кэшировать их не opaque-ответом;
// `no-cache` держит обновление картинок (documentation/entity-images.md → «Кэш»). JSON API — ниже (#468).
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const config = JSON.parse(readFileSync(resolve(REPO, 'firebase.json'), 'utf8'));
const rules = config.hosting.headers.filter((/** @type {{ source: string }} */ r) => r.source === '/img/**');

let failed = 0;
const check = (/** @type {string} */ name, /** @type {boolean} */ ok) => {
  console.log(`${ok ? '✔' : '✘'} ${name}`);
  if (!ok) failed++;
};

check('ровно одно правило для /img/**', rules.length === 1);
const headers = Object.fromEntries((rules[0]?.headers ?? []).map((/** @type {{ key: string, value: string }} */ h) => [h.key.toLowerCase(), h.value]));
check('/img/** — Access-Control-Allow-Origin: *', headers['access-control-allow-origin'] === '*');
check('/img/** — Cache-Control: no-cache', headers['cache-control'] === 'no-cache');
// Другое совпадающее правило с ACAO подменило бы значение: приоритет правил `headers` Firebase не документирует.
const withAcao = config.hosting.headers.filter((/** @type {{ headers: { key: string }[] }} */ r) =>
  r.headers.some((h) => h.key.toLowerCase() === 'access-control-allow-origin'));
check('Access-Control-Allow-Origin задан только в правиле /img/**', withAcao.length === 1 && withAcao[0].source === '/img/**');

// JSON API (#468): robots.txt закрывает /api/ от обхода, но URL, найденный по ссылке, Google может
// проиндексировать и без обхода — заголовок запрещает это явно. Маска `/api/**` покрывает и сам `/api/`.
const api = config.hosting.headers.filter((/** @type {{ source: string }} */ r) => r.source === '/api/**');
check('ровно одно правило для /api/**', api.length === 1);
const apiRobots = (api[0]?.headers ?? []).find((/** @type {{ key: string }} */ h) => h.key.toLowerCase() === 'x-robots-tag');
check('/api/** — X-Robots-Tag: noindex', apiRobots?.value === 'noindex');
// Тот же заголовок на страницах ридера снял бы весь сайт из индекса.
const robotsElsewhere = config.hosting.headers.filter((/** @type {{ source: string, headers: { key: string }[] }} */ r) =>
  r.source !== '/api/**' && r.headers.some((h) => h.key.toLowerCase() === 'x-robots-tag'));
check('X-Robots-Tag задан только в правиле /api/**', robotsElsewhere.length === 0);

if (failed) {
  console.error(`\n${failed} проверок не прошло`);
  process.exit(1);
}
