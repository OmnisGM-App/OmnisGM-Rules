// Список URL для точечного purge edge-кэша Cloudflare после деплоя — issue #175.
//
// Зачем не «purge everything»: зона в Cloudflare одна на весь omnisgm.com, и полный сброс
// выносит заодно кэш News и Table. Раз в квартал это не жалко, а на каждом деплое Rules —
// соседи постоянно ходят с холодным кэшем. Purge по префиксу/хосту в Cloudflare доступен
// только на Enterprise, поэтому точечный список URL — единственный способ сбросить своё,
// не трогая чужое.
//
// Что попадает в список:
//   • страницы, чьё содержимое изменилось (--changed, считает indexnow_manifest.mjs);
//   • страницы, которые исчезли (--removed) — иначе удалённый URL живёт на эдже до конца TTL;
//   • файлы с ФИКСИРОВАННЫМИ именами: sitemap, robots, llms.txt, иконки, манифест, sw.js —
//     их имена не меняются от сборки к сборке, поэтому сигнатурный дифф их не видит;
//   • JSON API (/api/**) целиком — он пересобирается predeploy'ем на каждом деплое, в sitemap
//     не входит и в манифест не попадает, а Cloudflare его кэширует наравне с остальным.
//
// Хэш-ассеты (/_astro/*.js|css) в список НЕ идут: их имена содержат хеш содержимого, новая
// сборка = новые имена = промах кэша по определению. Сбрасывать старые бессмысленно.
//
// Использование:
//   node scripts/cf_purge_urls.mjs --out /tmp/purge.txt [--changed changed.txt] [--removed removed.txt]
import { readdirSync, readFileSync, writeFileSync, existsSync, statSync } from 'node:fs';
import { dirname, resolve, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const DIST = resolve(here, '../dist');
const ORIGIN = 'https://rules.omnisgm.com';

const arg = (name, fallback = null) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
};

const lines = (path) =>
  path && existsSync(resolve(path))
    ? readFileSync(resolve(path), 'utf8').split('\n').map((s) => s.trim()).filter(Boolean)
    : [];

// Фикс-имена в корне dist. Перечислены явно, а не собраны по маске: список должен ломаться
// заметно (файл исчез — его просто не будет в purge), а не молча разрастаться от случайных
// файлов, попавших в корень сборки.
const FIXED = [
  'favicon.svg', 'favicon.ico', 'icon.svg', 'maskable.svg',
  'icon-192.png', 'icon-512.png', 'maskable-192.png', 'maskable-512.png',
  'apple-touch-icon.png', 'og.png',
  'robots.txt', 'llms.txt', 'manifest.webmanifest', 'sw.js',
  'sitemap-index.xml',
];

const urls = new Set();

// Корень сбрасываем всегда: сигнатурный дифф считает контент страницы, а правки в <head>
// (фавикон, мета, скрипты) его не меняют — и главная зависла бы на эдже со старым <head>
// до конца TTL. Именно с главной Google берёт фавикон (#199).
urls.add(`${ORIGIN}/`);
urls.add(`${ORIGIN}/index.html`);

for (const name of FIXED) {
  if (existsSync(resolve(DIST, name))) urls.add(`${ORIGIN}/${name}`);
}
// Пронумерованные sitemap-0.xml, -1.xml… — их количество растёт вместе с сайтом.
for (const f of readdirSync(DIST)) {
  if (/^sitemap-\d+\.xml$/.test(f)) urls.add(`${ORIGIN}/${f}`);
}

// JSON API целиком (обычно ~230 файлов) — вместе с его index.html-навигацией.
const apiDir = resolve(DIST, 'api');
function* walk(dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = resolve(dir, e.name);
    if (e.isDirectory()) yield* walk(p);
    else yield p;
  }
}
if (existsSync(apiDir) && statSync(apiDir).isDirectory()) {
  for (const file of walk(apiDir)) {
    const rel = relative(DIST, file).split(sep).join('/');
    // index.html отдаётся и как /api/dnd/, и как /api/dnd/index.html — кэшируются они
    // отдельными записями, поэтому сбрасываем оба адреса.
    urls.add(`${ORIGIN}/${rel}`);
    if (rel.endsWith('/index.html')) urls.add(`${ORIGIN}/${rel.replace(/index\.html$/, '')}`);
  }
}

// Страницы отдаются по двум адресам: канонический со слэшем и прямой /…/index.html. Firebase
// второй НЕ редиректит (отдаёт 200 — проверено на проде), значит в кэше это две независимые
// записи, и purge одной не трогает другую. Ссылок на index.html у нас нет, но краулер мог его
// однажды дёрнуть — и тогда именно эта версия зависла бы до конца TTL (ревью #192).
const withIndexHtml = (url) => (url.endsWith('/') ? [url, `${url}index.html`] : [url]);

for (const u of lines(arg('changed'))) withIndexHtml(u).forEach((x) => urls.add(x));
for (const u of lines(arg('removed'))) withIndexHtml(u).forEach((x) => urls.add(x));

const out = arg('out');
if (!out) {
  console.error('Не задан --out');
  process.exit(2);
}
const list = [...urls];
writeFileSync(resolve(out), list.join('\n') + (list.length ? '\n' : ''));
console.log(`Purge-список: ${list.length} URL → ${out}`);
