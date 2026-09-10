// Инварианты политики CSP (issue #325). Юнит, а не «посмотреть глазами»: политика лежит одной
// строкой под 800 символов в `firebase.json`, и пропажа хоста в ней не роняет ни сборку, ни
// e2e — она роняет ЧУЖОЙ скрипт в браузере посетителя, молча.
//
// Второго наблюдателя у этого класса нет: `web/e2e/csp.spec.ts` считает нарушения на preview,
// где аналитика не грузится вовсе (нет `PUBLIC_*` ID), а `check_csp.mjs` считает НАРУШЕНИЯ —
// от пропажи источника их не прибавляется там, где счётчик и не стартовал. Поэтому список
// источников проверяется отдельно и текстом.
//
// Что проверяем и почему именно это:
//
//   1. АБСОЛЮТНЫЙ список источников Метрики по директивам (`METRIKA`). Метрика грузит `tag.js`
//      с `.ru`, а хиты шлёт на хост, который выбирает сам `tag.js` по региону посетителя:
//      зарубежным — `.com`. Хоста в политике не было, и с перевода в enforce (01.09, #225) для
//      этой аудитории счётчик не считал ничего: 21 нарушение на 6 страницах — `script-src-elem`,
//      `connect-src`, `img-src`. В нашем коде `.com` не встречается вовсе, вывести его из
//      исходников нельзя — поэтому список записан явно, вместе с причиной каждой строки.
//   2. Парность `.ru` ↔ `.com` ВНЕ этого списка: директив в политике больше, чем знает список,
//      и новый источник Метрики не должен попасть в неё в одиночку.
//   3. Оба правила — по НОРМАЛИЗОВАННОМУ источнику: `https://mc.yandex.ru/watch/`,
//      `mc.yandex.ru` и `https://mc.yandex.ru:443` — та же запись того же хоста, и литеральное
//      сравнение молча выключалось бы на каждой из форм (ревью #326). Абсолютный список и
//      нормализация НЕ взаимозаменяемы: список ловит исчезновение носителя, нормализация —
//      форму записи.
//   4. Хосты, которые клиентский код грузит СКРИПТАМИ, перечислены в `script-src`. Это вторая
//      половина дыры: список источников и код аналитики живут в разных файлах.
//   5. Заголовок — `Content-Security-Policy`, а не `-Report-Only`, и он в политике ровно один:
//      Firebase мержит подходящие правила `hosting.headers`, и второе правило на `**` отдавало
//      бы посетителю не ту политику, которую судит гейт.
//   6. Директивы не дублируются: браузер применяет ПЕРВУЮ копию (CSP L3, «Ignoring duplicate
//      directive»), поэтому дубль — это тихо работающая другая политика.
//
// Механизм разбора и правил прогоняется на СИНТЕТИКЕ (внизу файла): на живой политике
// самопроверки проверяли бы состояние репозитория, а не правило.
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, '../..');

/**
 * Источники Метрики, обязательные поимённо. Директива → что в ней обязано быть и зачем.
 * Список абсолютный: пропажа ОБОИХ хостов (или всей директивы — её подхватит `default-src
 * 'self'`) — тот же прод-отказ, что и пропажа одного.
 */
export const METRIKA = {
  'script-src': ['https://mc.yandex.ru', 'https://mc.yandex.com'], // tag.js и скрипт хита
  'img-src': ['https://mc.yandex.ru', 'https://mc.yandex.com'], // пиксель синхронизации кук
  'connect-src': [
    'https://mc.yandex.ru',
    'https://mc.yandex.com',
    'wss://mc.yandex.ru',
    'wss://mc.yandex.com',
  ], // хиты и вебвизор
  'frame-src': ['https://mc.yandex.ru', 'https://mc.yandex.com'], // фрейм синхронизации
};

/**
 * Источник → каноническая форма. Браузер сравнивает источник с URL по схеме+хосту+порту, путь
 * в источнике лишь сужает — для вопроса «этот хост разрешён?» всё это одна запись.
 * @param {string} src
 * @returns {string}
 */
export function normalizeSource(src) {
  const s = src.trim().toLowerCase();
  if (s.startsWith("'")) return s; // 'self', 'unsafe-inline' — не хосты
  if (/^[a-z][a-z0-9+.-]*:$/.test(s)) return s; // схема целиком: data:, blob:
  const m = /^([a-z][a-z0-9+.-]*):\/\/(.*)$/.exec(s);
  const scheme = m ? m[1] : 'https'; // хост без схемы в CSP разрешает и https — считаем им
  const host = (m ? m[2] : s).replace(/\/.*$/, '').replace(/:443$/, ''); // путь и порт по умолчанию
  return `${scheme}://${host}`;
}

/**
 * Политика → директива: список источников. Оставляем ПЕРВОЕ вхождение — именно его применяет
 * браузер, повторную директиву с тем же именем он игнорирует.
 * @param {string} csp
 * @returns {Map<string, string[]>}
 */
export function parseDirectives(csp) {
  const out = new Map();
  for (const part of csp.split(';')) {
    const [name, ...sources] = part.trim().split(/\s+/).filter(Boolean);
    if (name && !out.has(name)) out.set(name, sources);
  }
  return out;
}

/**
 * Имена директив, встретившихся в политике больше одного раза.
 * @param {string} csp
 * @returns {string[]}
 */
export function duplicateDirectives(csp) {
  const seen = new Map();
  for (const part of csp.split(';')) {
    const name = part.trim().split(/\s+/).filter(Boolean)[0];
    if (name) seen.set(name, (seen.get(name) ?? 0) + 1);
  }
  return [...seen].filter(([, n]) => n > 1).map(([name]) => name);
}

/**
 * Претензии по Метрике: пропажа обязательного источника, пропажа целой директивы и одинокий
 * `.ru` без пары в любой другой директиве.
 * @param {Map<string, string[]>} directives
 * @returns {string[]}
 */
export function metrikaProblems(directives) {
  const problems = [];
  const normalized = new Map([...directives].map(([name, srcs]) => [name, srcs.map(normalizeSource)]));

  for (const [name, required] of Object.entries(METRIKA)) {
    const have = normalized.get(name);
    if (!have) {
      problems.push(`${name}: директивы нет вовсе — её подхватит default-src`);
      continue;
    }
    for (const want of required) if (!have.includes(want)) problems.push(`${name}: нет ${want}`);
  }

  for (const [name, have] of normalized) {
    for (const src of have) {
      const m = /^(https|wss):\/\/mc\.yandex\.ru$/.exec(src);
      if (!m) continue;
      const want = `${m[1]}://mc.yandex.com`;
      if (!have.includes(want)) problems.push(`${name}: есть ${src}, нет ${want}`);
    }
  }
  return [...new Set(problems)];
}

/**
 * Хосты, которые код грузит ЭЛЕМЕНТАМИ `<script>`: сначала находим переменные, созданные как
 * `createElement('script')`, и только их `.src`/`setAttribute('src', …)` считаем скриптовыми.
 * Пиксель `img.src = …` требует `img-src`, и записывать его в `script-src` — ложное красное.
 * @param {string} source
 * @returns {string[]}
 */
export function scriptHostsInCode(source) {
  const vars = new Set(
    [...source.matchAll(/(?:const|let|var)\s+(\w+)\s*=\s*document\.createElement\(\s*['"`]script['"`]/g)].map(
      (m) => m[1],
    ),
  );
  const hosts = new Set();
  for (const name of vars) {
    const assign = new RegExp(`\\b${name}\\.src\\s*=\\s*[\`'"](https://[^\`'"$/]+)`, 'g');
    const setAttr = new RegExp(`\\b${name}\\.setAttribute\\(\\s*['"\`]src['"\`]\\s*,\\s*[\`'"](https://[^\`'"$/]+)`, 'g');
    for (const re of [assign, setAttr]) {
      for (const m of source.matchAll(re)) hosts.add(m[1].slice('https://'.length));
    }
  }
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
  const sources = (directives.get('script-src') ?? []).map(normalizeSource);
  const covers = (/** @type {string} */ host) =>
    sources.some((s) => {
      const bare = s.replace(/^https:\/\//, '');
      if (bare === host) return true;
      return bare.startsWith('*.') && host.endsWith(bare.slice(1));
    });
  return hosts.filter((h) => !covers(h));
}

/**
 * Заголовки CSP во ВСЕХ правилах `hosting.headers` — Firebase мержит подходящие правила, и
 * второе правило на `**` отдало бы посетителю политику, которой гейт не видит.
 * @param {{headers?: {headers?: {key: string, value: string}[]}[]}} hosting
 * @returns {{key: string, value: string}[]}
 */
export function cspHeaders(hosting) {
  return (hosting.headers ?? []).flatMap((rule) =>
    (rule.headers ?? []).filter((h) => h.key.startsWith('Content-Security-Policy')),
  );
}

/**
 * Файлы клиентского кода, в которых вообще может стоять загрузка стороннего скрипта.
 * @param {string} dir
 * @returns {string[]}
 */
function sourceFiles(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) out.push(...sourceFiles(full));
    else if (/\.(ts|tsx|js|mjs|astro)$/.test(name)) out.push(full);
  }
  return out;
}

// ——— Прогон ———

function main() {
  let failed = 0;
  let checksRun = 0;
  const check = (/** @type {unknown} */ ok, /** @type {string} */ what, extra = '') => {
    checksRun++;
    if (!ok) {
      failed++;
      console.error(`  ✗ ${what}${extra ? `\n      ${extra}` : ''}`);
    }
  };

  // Живая политика.
  const hosting = JSON.parse(readFileSync(resolve(REPO, 'firebase.json'), 'utf8')).hosting;
  const headers = cspHeaders(hosting);
  check(headers.length === 1, 'заголовок CSP в firebase.json ровно один', `нашлось: ${headers.length}`);
  const header = headers[0];
  check(header?.key === 'Content-Security-Policy', 'политика в enforce, а не в Report-Only (#225)', `key = ${header?.key}`);

  const csp = header?.value ?? '';
  const dupes = duplicateDirectives(csp);
  check(dupes.length === 0, 'директивы в политике не дублируются (браузер применяет первую)', dupes.join(', '));

  const directives = parseDirectives(csp);
  const problems = metrikaProblems(directives);
  check(problems.length === 0, 'источники Метрики на месте и парны .ru ↔ .com (#325)', problems.join('\n      '));

  // Хосты скриптов — по всему клиентскому коду, обе формы записи (не только analytics-client).
  const hosts = [...new Set(sourceFiles(resolve(REPO, 'web/src')).flatMap((f) => scriptHostsInCode(readFileSync(f, 'utf8'))))];
  check(hosts.length >= 2, 'в клиентском коде нашлись хосты скриптов', `нашлось: ${hosts.join(', ') || 'ничего'}`);
  const uncovered = uncoveredScriptHosts(directives, hosts);
  check(uncovered.length === 0, 'все хосты скриптов из кода разрешены script-src', uncovered.join(', '));

  // ——— Самопроверки механизма на синтетике ———

  const SYN = Object.entries(METRIKA)
    .map(([name, srcs]) => `${name} 'self' ${srcs.join(' ')}`)
    .join('; ');
  const synOk = parseDirectives(SYN);
  check(synOk.size === 4, 'разбор: четыре директивы', `получилось ${synOk.size}`);
  check(metrikaProblems(synOk).length === 0, 'правило: полная политика чиста');

  // Одинокий `.ru` в директиве ИЗ списка задевает оба правила сразу — и это полезно: одно
  // называет пропавший источник, второе — разорванную пару. Ждём ровно две претензии.
  const noCom = metrikaProblems(parseDirectives(SYN.replace(' https://mc.yandex.com', '')));
  check(
    noCom.length === 2 && noCom.includes('script-src: нет https://mc.yandex.com') && noCom.includes('script-src: есть https://mc.yandex.ru, нет https://mc.yandex.com'),
    'правило: ловит пропажу .com в script-src — и списком, и парностью',
    noCom.join('; '),
  );

  const noWss = metrikaProblems(parseDirectives(SYN.replace(' wss://mc.yandex.com', '')));
  check(
    noWss.length === 2 && noWss.every((p) => p.includes('wss://mc.yandex.com')),
    'правило: схема wss проверяется отдельно от https',
    noWss.join('; '),
  );

  const noBoth = metrikaProblems(parseDirectives(SYN.replace("img-src 'self' https://mc.yandex.ru https://mc.yandex.com", "img-src 'self'")));
  check(noBoth.length === 2, 'правило: пропажа ОБОИХ хостов — две претензии, а не молчание', noBoth.join('; '));

  const noDirective = metrikaProblems(parseDirectives(SYN.split('; ').filter((d) => !d.startsWith('frame-src')).join('; ')));
  check(
    noDirective.length === 1 && noDirective[0] === 'frame-src: директивы нет вовсе — её подхватит default-src',
    'правило: пропажа целой директивы названа',
    noDirective.join('; '),
  );

  const masked = metrikaProblems(parseDirectives(SYN.replace('script-src \'self\' https://mc.yandex.ru https://mc.yandex.com', "script-src 'self' https://*.yandex.ru")));
  check(masked.length === 2, 'правило: маска *.yandex.ru не считается за поимённые хосты', masked.join('; '));

  const withPath = parseDirectives(SYN.replace('img-src \'self\' https://mc.yandex.ru', "img-src 'self' https://mc.yandex.ru/watch/"));
  check(metrikaProblems(withPath).length === 0, 'нормализация: путь в источнике не прячет хост');
  const bare = parseDirectives(SYN.replace("img-src 'self' https://mc.yandex.ru", "img-src 'self' mc.yandex.ru"));
  check(metrikaProblems(bare).length === 0, 'нормализация: хост без схемы — та же запись');
  const withPort = parseDirectives(SYN.replace("img-src 'self' https://mc.yandex.ru", "img-src 'self' https://mc.yandex.ru:443"));
  check(metrikaProblems(withPort).length === 0, 'нормализация: явный порт 443 — та же запись');
  check(normalizeSource("'self'") === "'self'", 'нормализация: ключевые слова не трогаем');

  const lonely = metrikaProblems(parseDirectives(`${SYN}; media-src https://mc.yandex.ru`));
  check(
    lonely.length === 1 && lonely[0] === 'media-src: есть https://mc.yandex.ru, нет https://mc.yandex.com',
    'парность: одинокий .ru в директиве вне списка — претензия',
    lonely.join('; '),
  );
  check(metrikaProblems(parseDirectives(`${SYN}; media-src https://mc.yandex.com`)).length === 0, 'парность: одинокий .com — не претензия');

  const dup = 'script-src https://mc.yandex.ru; script-src https://mc.yandex.ru https://mc.yandex.com';
  check((parseDirectives(dup).get('script-src') ?? []).length === 1, 'разбор: применяется ПЕРВАЯ копия директивы, как в браузере');
  check(duplicateDirectives(dup).join() === 'script-src', 'дубли: повтор директивы назван');
  check(duplicateDirectives(SYN).length === 0, 'дубли: нормальная политика чиста');

  const CODE = "const s = document.createElement('script');\ns.src = 'https://mc.yandex.ru/metrika/tag.js';";
  check(scriptHostsInCode(CODE).join() === 'mc.yandex.ru', 'разбор кода: скрипт с обычной строкой');
  check(
    scriptHostsInCode("const s = document.createElement('script');\ns.src = `https://www.googletagmanager.com/gtag/js?id=${id}`;").join() ===
      'www.googletagmanager.com',
    'разбор кода: шаблонная строка с интерполяцией',
  );
  check(
    scriptHostsInCode("const s = document.createElement('script');\ns.setAttribute('src', 'https://cdn.example.com/a.js');").join() === 'cdn.example.com',
    'разбор кода: форма setAttribute',
  );
  check(
    scriptHostsInCode("const px = document.createElement('img');\npx.src = 'https://pixel.example.com/p.gif';").length === 0,
    'разбор кода: .src картинки — не хост скрипта (ему нужен img-src)',
  );
  check(scriptHostsInCode("const url = 'https://example.com/x.js';").length === 0, 'разбор кода: строка вне .src — не хост');

  const synCover = parseDirectives("script-src 'self' https://mc.yandex.ru https://*.google-analytics.com");
  check(uncoveredScriptHosts(synCover, ['mc.yandex.ru']).length === 0, 'покрытие: точное совпадение хоста');
  check(uncoveredScriptHosts(synCover, ['a.google-analytics.com']).length === 0, 'покрытие: маска *. покрывает поддомен');
  check(uncoveredScriptHosts(synCover, ['google-analytics.com']).length === 1, 'покрытие: маска *. НЕ покрывает сам домен');
  check(uncoveredScriptHosts(synCover, ['mc.yandex.com']).join() === 'mc.yandex.com', 'покрытие: ловит хост, которого нет в script-src');
  check(uncoveredScriptHosts(parseDirectives('img-src https://mc.yandex.ru'), ['mc.yandex.ru']).length === 1, 'покрытие: чужая директива не считается за script-src');

  check(cspHeaders({ headers: [{ headers: [{ key: 'X-Frame-Options', value: 'DENY' }] }] }).length === 0, 'заголовки: без CSP — пусто');
  check(
    cspHeaders({
      headers: [
        { headers: [{ key: 'Content-Security-Policy', value: 'a' }] },
        { headers: [{ key: 'Content-Security-Policy', value: 'b' }] },
      ],
    }).length === 2,
    'заголовки: второе правило hosting.headers видно (Firebase их мержит)',
  );
  check(cspHeaders({ headers: [{ headers: [{ key: 'Content-Security-Policy-Report-Only', value: 'a' }] }] })[0].key.endsWith('Report-Only'), 'заголовки: Report-Only отличим от enforce');

  if (failed) {
    console.error(`\n❌ Политика CSP: ${failed} из ${checksRun} проверок не прошло`);
    process.exit(1);
  }
  console.log(`✓ Политика CSP: ${checksRun} проверок — источники Метрики (.ru ↔ .com), хосты кода в script-src, enforce без дублей`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) main();
