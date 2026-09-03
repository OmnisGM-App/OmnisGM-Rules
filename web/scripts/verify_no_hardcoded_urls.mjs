/**
 * Гейт: в e2e нет литеральных адресов и портов сервера (#252).
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

/**
 * Исключений нет — и это осознанно. `ports.ts` собирает адрес шаблоном из числа, поэтому под
 * правило не подпадает: заводить для него поблажку значило бы вывести из-под гейта ровно тот
 * файл, где литерал опаснее всего.
 *
 * Сами базовые числа портов гейт при этом видеть обязан — иначе он не поймал бы `const PORT =
 * 4321` в спеке. Поэтому `ports.ts` из обхода исключён только как ФАЙЛ-ОПРЕДЕЛЕНИЕ этих чисел.
 */
const DEFINITION_FILE = 'ports.ts';

// `localhost:4321`, `127.0.0.1:4321`, `[::1]:4321` — с протоколом и без.
const ADDRESS = /(?:https?:\/\/)?(?:localhost|127\.0\.0\.1|\[::1\]):\d{2,5}/g;

/**
 * Голый порт без хоста — `const PORT = 4321` плюс шаблон воспроизводит ту же регрессию
 * насквозь, поэтому ловим и его.
 *
 * Числа читаем из `e2e/ports.ts` ТЕКСТОМ, а не импортом: скрипт гоняется в CI на Node 20,
 * который `.ts` из `.mjs` не подгрузит. Заодно список не разъезжается с реальностью.
 */
const portsSource = await readFile(join(e2eDir, 'ports.ts'), 'utf8');
const basePorts = [...portsSource.matchAll(/=\s*(\d{4})\s*\+\s*slot\(\)/g)].map((m) => m[1]);
if (basePorts.length === 0) {
  console.error('❌ В e2e/ports.ts не нашлось ни одной базы порта — гейт проверял бы половину правила');
  process.exit(1);
}
const BARE_PORTS = new RegExp(`\\b(?:${basePorts.join('|')})\\b`, 'g');

async function walk(dir, out = []) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) await walk(full, out);
    else if (/\.(ts|mjs|js)$/.test(entry.name)) out.push(full);
  }
  return out;
}

const findings = [];
let checked = 0;
for (const file of (await walk(e2eDir)).sort()) {
  const rel = relative(e2eDir, file);
  if (rel === DEFINITION_FILE) continue;

  checked++;
  const lines = (await readFile(file, 'utf8')).split('\n');
  lines.forEach((line, i) => {
    for (const hit of [...(line.match(ADDRESS) ?? []), ...(line.match(BARE_PORTS) ?? [])]) {
      findings.push(`  e2e/${rel}:${i + 1}  ${hit}   ${line.trim().slice(0, 80)}`);
    }
  });
}

if (findings.length) {
  console.error('❌ Литеральный адрес сервера в e2e — порт зависит от слота (Table#469), и такой');
  console.error('   литерал молча перестаёт совпадать, превращая проверку в тавтологию.');
  console.error('   Берите адрес из e2e/ports.ts (BASE_URL / E2E_PORT).\n');
  console.error(findings.join('\n'));
  process.exit(1);
}
// Ноль проверенных файлов — не «чисто», а тавтология этажом выше той, что гейт ловит: так
// выглядит пустой `e2e/`, переименованный каталог или новое расширение вне обхода.
if (checked === 0) {
  console.error('❌ Гейт не проверил ни одного файла — обход сломан (пустой e2e/ или иное расширение)');
  process.exit(1);
}
console.log(`✓ Литеральных адресов сервера в e2e нет (проверено файлов: ${checked})`);
