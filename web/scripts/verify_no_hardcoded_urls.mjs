/**
 * Гейт: в e2e нет литеральных адресов и портов сервера (#252). При смене порта (слот)
 * `href.replace('http://localhost:4321', SITE)` молча не совпадает, и `expect` становится тавтологией.
 */
import { readdir, readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join, relative, resolve } from 'node:path';
import { PORT_BLOCKS } from '@omnisgm-app/core/blocks';

const web = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const e2eDir = join(web, 'e2e');

const DEFINITION_FILE = 'ports.ts';

const ADDRESS = /(?:https?:\/\/)?(?:localhost|127\.0\.0\.1|\[::1\]):\d{2,5}/g;

/** Голый порт (`const PORT = 4321`) — та же регрессия; базы — из карты `@omnisgm-app/core` (Table#477). */
const basePorts = Object.values(PORT_BLOCKS.rules).map(String);
if (basePorts.length === 0) {
  console.error('❌ В карте портов пуст блок `rules` — гейт проверял бы половину правила');
  process.exit(1);
}
const BARE_PORTS = new RegExp(`\\b(?:${basePorts.join('|')})\\b`, 'g');

/**
 * @param {string} dir
 * @param {string[]} out
 * @returns {Promise<string[]>}
 */
async function walk(dir, out = []) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) await walk(full, out);
    else if (/\.(ts|mjs|js)$/.test(entry.name)) out.push(full);
  }
  return out;
}

/** @type {string[]} */
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
// Ноль проверенных файлов — тавтология этажом выше: пустой `e2e/` или расширение вне обхода.
if (checked === 0) {
  console.error('❌ Гейт не проверил ни одного файла — обход сломан (пустой e2e/ или иное расширение)');
  process.exit(1);
}
console.log(`✓ Литеральных адресов сервера в e2e нет (проверено файлов: ${checked})`);
