// Инварианты политики CSP (issue #325). Юнит, а не «посмотреть глазами»: политика лежит одной
// строкой в 700 символов в `firebase.json`, и пропажа хоста в ней не роняет ни сборку, ни e2e —
// она роняет ЧУЖОЙ скрипт в браузере посетителя, молча.
//
// Что проверяем и почему именно это:
//
//   1. Парность `mc.yandex.ru` ↔ `mc.yandex.com`. Метрика грузит `tag.js` с `.ru`, а хиты шлёт
//      на тот хост, который выбирает сам `tag.js` по региону посетителя: зарубежным — `.com`.
//      Хоста в политике не было, и с 01.09 (перевод в enforce, #225) для этой аудитории
//      счётчик не считал ничего: 21 нарушение на 6 страницах, `script-src-elem` + `connect-src`
//      + `img-src`. В нашем коде этого хоста нет вовсе — вывести его из исходников нельзя,
//      поэтому правило записано здесь явно, вместе с причиной.
//
//   2. Хосты, которые клиентский код грузит СКРИПТАМИ, перечислены в `script-src`. Это вторая
//      половина той же дыры: список источников и код аналитики живут в разных файлах и
//      разъезжаются молча.
//
//   3. Заголовок — `Content-Security-Policy`, а не `-Report-Only`. Возврат в Report-Only —
//      отмена решения #225, и он обязан быть заметным, а не диффом в одну строку.
//
// Механизм каждой проверки прогоняется на СИНТЕТИКЕ (внизу файла): на живой политике
// самопроверки проверяли бы состояние репозитория, а не правило.
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, '../..');

let failed = 0;
let checksRun = 0;
const check = (/** @type {unknown} */ ok, /** @type {string} */ what, extra = '') => {
  checksRun++;
  if (!ok) {
    failed++;
    console.error(`  ✗ ${what}${extra ? `\n      ${extra}` : ''}`);
  }
};

/**
 * Политика → директива: список источников.
 * @param {string} csp
 * @returns {Map<string, string[]>}
 */
export function parseDirectives(csp) {
  const out = new Map();
  for (const part of csp.split(';')) {
    const [name, ...sources] = part.trim().split(/\s+/).filter(Boolean);
    if (name) out.set(name, sources);
  }
  return out;
}

/**
 * Источники Метрики без пары `.com` — по каждой директиве и КАЖДОЙ схеме отдельно:
 * `wss://mc.yandex.ru` без `wss://mc.yandex.com` — та же дыра, что и в https (вебвизор).
 * @param {Map<string, string[]>} directives
 * @returns {string[]}
 */
export function yandexPairProblems(directives) {
  const problems = [];
  for (const [name, sources] of directives) {
    for (const src of sources) {
      const m = /^(https|wss):\/\/mc\.yandex\.ru$/.exec(src);
      if (!m) continue;
      const want = `${m[1]}://mc.yandex.com`;
      if (!sources.includes(want)) problems.push(`${name}: есть ${src}, нет ${want}`);
    }
  }
  return problems;
}

/**
 * Хосты, которые код грузит как скрипты (`<script src>`), из исходника аналитики.
 * Интерполяция в шаблонной строке не мешает: хост стоит до неё.
 * @param {string} source
 * @returns {string[]}
 */
export function scriptHostsInCode(source) {
  const hosts = new Set();
  for (const m of source.matchAll(/\.src\s*=\s*[`'"](https:\/\/[^`'"$/]+)/g)) hosts.add(m[1].slice('https://'.length));
  return [...hosts];
}

/**
 * Хосты кода, не покрытые `script-src`. Покрытием считается точное совпадение или подходящая
 * маска `*.` — как их понимает браузер.
 * @param {Map<string, string[]>} directives
 * @param {string[]} hosts
 * @returns {string[]}
 */
export function uncoveredScriptHosts(directives, hosts) {
  const sources = directives.get('script-src') ?? [];
  const covers = (/** @type {string} */ host) =>
    sources.some((s) => {
      const bare = s.replace(/^https:\/\//, '');
      if (bare === host) return true;
      return bare.startsWith('*.') && host.endsWith(bare.slice(1));
    });
  return hosts.filter((h) => !covers(h));
}

// ——— Живая политика ———

const hosting = JSON.parse(readFileSync(resolve(REPO, 'firebase.json'), 'utf8')).hosting;
const header = hosting.headers[0].headers.find((/** @type {{key: string}} */ h) =>
  h.key.startsWith('Content-Security-Policy'),
);
check(!!header, 'в firebase.json есть заголовок CSP');
check(header?.key === 'Content-Security-Policy', 'политика в enforce, а не в Report-Only (#225)', `key = ${header?.key}`);

const directives = parseDirectives(header?.value ?? '');
const pairs = yandexPairProblems(directives);
check(pairs.length === 0, 'у каждого mc.yandex.ru в политике есть парный mc.yandex.com (#325)', pairs.join('\n      '));

const analytics = readFileSync(resolve(REPO, 'web/src/lib/analytics-client.ts'), 'utf8');
const hosts = scriptHostsInCode(analytics);
check(hosts.length >= 2, 'в коде аналитики нашлись хосты скриптов', `нашлось: ${hosts.join(', ') || 'ничего'}`);
const uncovered = uncoveredScriptHosts(directives, hosts);
check(uncovered.length === 0, 'все хосты скриптов из кода аналитики разрешены script-src', uncovered.join(', '));

// ——— Самопроверки механизма на синтетике ———

const SYN_OK = "script-src 'self' https://mc.yandex.ru https://mc.yandex.com; connect-src https://mc.yandex.ru https://mc.yandex.com wss://mc.yandex.ru wss://mc.yandex.com";
const synOk = parseDirectives(SYN_OK);
check(synOk.size === 2, 'разбор: две директивы', `получилось ${synOk.size}`);
check((synOk.get('script-src') ?? []).length === 3, 'разбор: script-src с тремя источниками');
check(yandexPairProblems(synOk).length === 0, 'парность: полная политика чиста');

const synNoCom = parseDirectives("script-src https://mc.yandex.ru; img-src https://mc.yandex.ru https://mc.yandex.com");
const noCom = yandexPairProblems(synNoCom);
check(noCom.length === 1, 'парность: ловит пропажу .com ровно в одной директиве', `нашлось ${noCom.length}: ${noCom.join('; ')}`);
check(noCom[0] === 'script-src: есть https://mc.yandex.ru, нет https://mc.yandex.com', 'парность: называет директиву и хост', noCom[0]);

const synNoWss = parseDirectives("connect-src https://mc.yandex.ru https://mc.yandex.com wss://mc.yandex.ru");
const noWss = yandexPairProblems(synNoWss);
check(noWss.length === 1 && noWss[0].includes('wss://mc.yandex.com'), 'парность: схема wss проверяется отдельно от https', noWss.join('; '));

const synComOnly = parseDirectives('script-src https://mc.yandex.com');
check(yandexPairProblems(synComOnly).length === 0, 'парность: один .com без .ru — не претензия (правило про пропажу пары к .ru)');

check(scriptHostsInCode("s.src = 'https://mc.yandex.ru/metrika/tag.js';").join() === 'mc.yandex.ru', 'разбор кода: обычная строка');
check(
  scriptHostsInCode('s.src = `https://www.googletagmanager.com/gtag/js?id=${id}`;').join() === 'www.googletagmanager.com',
  'разбор кода: шаблонная строка с интерполяцией',
);
check(scriptHostsInCode("const url = 'https://example.com/x.js';").length === 0, 'разбор кода: не .src — не хост скрипта');

const synCover = parseDirectives("script-src 'self' https://mc.yandex.ru https://*.google-analytics.com");
check(uncoveredScriptHosts(synCover, ['mc.yandex.ru']).length === 0, 'покрытие: точное совпадение хоста');
check(uncoveredScriptHosts(synCover, ['a.google-analytics.com']).length === 0, 'покрытие: маска *. покрывает поддомен');
check(uncoveredScriptHosts(synCover, ['google-analytics.com']).length === 1, 'покрытие: маска *. НЕ покрывает сам домен');
check(uncoveredScriptHosts(synCover, ['mc.yandex.com']).join() === 'mc.yandex.com', 'покрытие: ловит хост, которого нет в script-src');
check(uncoveredScriptHosts(parseDirectives("img-src https://mc.yandex.ru"), ['mc.yandex.ru']).length === 1, 'покрытие: чужая директива не считается за script-src');

if (failed) {
  console.error(`\n❌ Политика CSP: ${failed} из ${checksRun} проверок не прошло`);
  process.exit(1);
}
console.log(`✓ Политика CSP: ${checksRun} проверок — парность Метрики (.ru ↔ .com), хосты кода в script-src, enforce`);
