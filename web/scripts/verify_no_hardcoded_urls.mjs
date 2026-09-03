/**
 * Гейт: в e2e нет литеральных адресов сервера (#252).
 *
 * Класс проблемы, ради которого гейт заведён. Строка вида
 *
 *     href.replace('http://localhost:4321', SITE)
 *
 * при смене порта (слот, переезд) перестаёт совпадать: `replace` молча возвращает исходное
 * значение, и `expect` вырождается в тавтологию — тест зелёный, но не проверяет ничего.
 * Ровно это чинилось в PR #247, и ловить такое глазами на ревью — плохая опора: литерал
 * выглядит безобидно, а последствие видно только на другом слоте.
 *
 * Адрес берётся из `e2e/ports.ts` (`BASE_URL`, `E2E_PORT`) — единственного места, где он живёт.
 *
 * Гоняется в CI и локально: `node scripts/verify_no_hardcoded_urls.mjs`. E2E для этого не нужны,
 * поэтому гейт работает там, где сами e2e не запускаются.
 */
import { readdir, readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join, relative, resolve } from 'node:path';

const web = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const e2eDir = join(web, 'e2e');

/** Единственный файл, которому литерал положен по должности. */
const ALLOWED = new Set(['ports.ts']);

// `localhost:4321`, `127.0.0.1:4321`, `[::1]:4321` — с протоколом и без.
const ADDRESS = /(?:https?:\/\/)?(?:localhost|127\.0\.0\.1|\[::1\]):\d{2,5}/g;

async function walk(dir, out = []) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) await walk(full, out);
    else if (/\.(ts|mjs|js)$/.test(entry.name)) out.push(full);
  }
  return out;
}

const findings = [];
for (const file of (await walk(e2eDir)).sort()) {
  const rel = relative(e2eDir, file);
  if (ALLOWED.has(rel)) continue;

  const lines = (await readFile(file, 'utf8')).split('\n');
  lines.forEach((line, i) => {
    for (const hit of line.match(ADDRESS) ?? []) {
      findings.push(`  e2e/${rel}:${i + 1}  ${hit}   ${line.trim().slice(0, 80)}`);
    }
  });
}

if (findings.length) {
  console.error('❌ Литеральный адрес сервера в e2e — порт зависит от слота (#469), и такой');
  console.error('   литерал молча перестаёт совпадать, превращая проверку в тавтологию.');
  console.error('   Берите адрес из e2e/ports.ts (BASE_URL / E2E_PORT).\n');
  console.error(findings.join('\n'));
  process.exit(1);
}
console.log('✓ Литеральных адресов сервера в e2e нет');
