// Выбор вида очереди картинок (issue #291): правило на синтетике — живой корпус проверял бы
// состояние репозитория, а не правило.
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, delimiter } from 'node:path';
import { nextKind, emptyKinds, orderProblems, codexTail, codexExec, runCodex, runCodexText, isAuthError, ORDER, KINDS } from './gen-images.mjs';

let failed = 0;
const eq = (/** @type {unknown} */ actual, /** @type {unknown} */ expected, /** @type {string} */ what) => {
  if (actual !== expected) {
    failed++;
    console.error(`  ✗ ${what}\n      ожидалось «${expected}», получено «${actual}»`);
  }
};

const rows = (/** @type {[string, number][]} */ ...pairs) =>
  pairs.map(([kind, left]) => ({ kind, left, total: left + 10 }));

eq(nextKind(rows(['spells', 0], ['magic-items', 377], ['gear', 480])), 'magic-items',
   'закрытый вид пропускается');
eq(nextKind(rows(['spells', 1], ['magic-items', 377])), 'spells',
   'берётся первый непустой, а не самый длинный');
eq(nextKind(rows(['spells', 0], ['magic-items', 0])), null, 'все виды закрыты');
eq(nextKind([]), null, 'пустой список видов');
eq(nextKind(rows(['spells', 0], ['magic-items', 0], ['gear', 3])), 'gear',
   'два закрытых подряд');

// Явные total: `rows` даёт total = left + 10 и нулевого размера не строит.
const sized = (/** @type {[string, number, number][]} */ ...triples) =>
  triples.map(([kind, left, total]) => ({ kind, left, total }));
eq(emptyKinds(sized(['spells', 0, 0], ['magic-items', 377, 383])).join(','), 'spells',
   'вид без данных назван, соседний с данными — нет');
eq(emptyKinds(sized(['spells', 0, 0], ['magic-items', 377, 383], ['creatures', 0, 0])).join(','),
   'spells,creatures', 'смешанный случай: API потерян, markdown-виды целы');
eq(emptyKinds(sized(['spells', 0, 341], ['magic-items', 0, 383])).length, 0,
   'закрытые, но непустые очереди — не «нет данных»');
eq(emptyKinds([]).length, 0, 'пустой список видов');

// Новые виды (#380) идут раньше снаряжения: их ждут, а у снаряжения очередь длинная.
for (const kind of ['class-options', 'rules']) {
  if (!(ORDER.indexOf(kind) >= 0 && ORDER.indexOf(kind) < ORDER.indexOf('gear'))) {
    failed++;
    console.error(`  ✗ вид ${kind} должен стоять в ORDER раньше gear`);
  }
}

// Термины правил (#380) — только из 5.2: у 5.1 страниц терминов нет, а сама коллекция несёт сокращения.
if (JSON.stringify(KINDS.rules.versions?.['rules-terms']) !== JSON.stringify(['srd52'])) {
  failed++;
  console.error('  ✗ rules-terms в очереди понятий должны браться только из srd52');
}

// Полнота порядка — дважды: независимый счёт ловит ослабленную orderProblems() (ранний `return null`).
const problem = orderProblems();
if (problem) {
  failed++;
  console.error(`  ✗ ${problem}`);
}
const forgotten = Object.keys(KINDS).filter((k) => !ORDER.includes(k));
const unknown = ORDER.filter((k) => !(/** @type {Record<string, unknown>} */ (KINDS)[k]));
if (forgotten.length || unknown.length) {
  failed++;
  console.error(`  ✗ ORDER и KINDS разошлись: нет в порядке — ${forgotten.join(', ') || '—'}, ` +
                `нет среди видов — ${unknown.join(', ') || '—'}`);
  if (!problem) console.error('      …и orderProblems() при этом молчит — страж ослаблен');
}

// Хвост ответа codex в логе пропуска: служебные строки уходят, содержательные остаются, длина ограничена.
const answer = [
  'codex', 'I can’t generate that image.', 'hook: Stop', 'hook: Stop Completed', 'tokens used', '14 916', '14,916', '',
].join('\n');
eq(codexTail(answer), 'codex\nI can’t generate that image.', 'хвост ответа без хуков и счётчика токенов');
eq(codexTail(`HEAD${'x'.repeat(20)}TAIL`, 8), '…xxxTAIL', 'хвост с многоточием — конец ответа и не длиннее max');
eq(codexTail(''), '', 'пустой ответ — пустой хвост');

// Протухший токен узнаётся по ошибке codexExec: заглушка codex в PATH пишет 401 и выходит с кодом 1.
const stubDir = mkdtempSync(join(tmpdir(), 'codex-stub-'));
writeFileSync(join(stubDir, 'codex'), '#!/bin/sh\necho "401 unauthorized" >&2\nexit 1\n', { mode: 0o755 });
const savedPath = process.env.PATH;
process.env.PATH = `${stubDir}${delimiter}${savedPath}`;
let thrown = null;
try { codexExec('read-only', 'x', 1024 * 1024); } catch (err) { thrown = err; }
// Успешный вызов: ответ — в stdout, шапка сессии — в stderr.
writeFileSync(join(stubDir, 'codex'),
  "#!/bin/sh\necho 'a crescent moon'\necho 'session header' >&2\nexit 0\n", { mode: 0o755 });
const ok = codexExec('read-only', 'x', 1024 * 1024);
eq(`${ok.stdout}|${ok.stderr}`, 'a crescent moon\n|session header\n', 'успешный вызов отдаёт stdout и stderr раздельно');
eq(runCodexText('x'), 'a crescent moon\n', 'описание берёт только stdout');
eq(runCodex('x'), 'session header\na crescent moon\n', 'ответ картинки кончается stdout — им и кончится хвост');
process.env.PATH = savedPath;
rmSync(stubDir, { recursive: true, force: true });
eq(Boolean(thrown && isAuthError(thrown)), true, 'отказ codex с 401 узнаётся как протухший токен');
eq(String(/** @type {any} */ (thrown)?.message).includes('unauthorized'), false,
   'сообщение ошибки короткое: вывод — только в полях stdout/stderr');

if (failed) {
  console.error(`\n❌ Выбор вида очереди: ${failed} расхождений`);
  process.exit(1);
}
console.log(`✅ Выбор вида очереди: 9 сценариев, хвост ответа codex — 3, вызов codex — 5, порядок покрывает все ${ORDER.length} вида, ` +
            `виды: ${Object.keys(KINDS).length}`);
