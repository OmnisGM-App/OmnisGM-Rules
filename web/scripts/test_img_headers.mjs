// Заголовки картинок сущностей в `firebase.json` (#378): `Access-Control-Allow-Origin: *` даёт
// сторонней PWA (компендиум Table) кэшировать их не opaque-ответом; `no-cache` держит обновление
// картинок (documentation/entity-images.md → «Кэш»). Пропажу не видят ни сборка, ни e2e.
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

if (failed) {
  console.error(`\n${failed} проверок не прошло`);
  process.exit(1);
}
