#!/usr/bin/env node
// Страж связки setup в workflow (issue #287).
//
// Связка «setup-node + cache + npm ci + setup-python» дублировалась в четырёх workflow, и
// дублирование уже дало дрейф: node 20 в трёх против 22 в четвёртом — молча, потому что
// сравнивать было негде. Composite-шаг убирает копии, но НЕ мешает завести их заново: он
// не запрещает написать `uses: actions/setup-node` рядом. Поэтому запрет — здесь.
//
// Проверяем два утверждения:
//  1) прямых `actions/setup-node` в наших workflow нет — версия Node объявляется в одном
//     месте (`.github/actions/setup-web/action.yml`), а несогласие с ней пишется input'ом;
//  2) у каждой джобы есть `timeout-minutes` — без него зависший шаг держит очередь до
//     дефолтных шести часов.
//
// Исключение одно и явное: `claude-review.yml` — вендорный workflow авторевью, он живёт по
// своим правилам и синхронизируется из донора целиком, поэтому наши правила ему не указ.
import { readdirSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DIR = resolve(REPO, '.github/workflows');
const VENDORED = new Set(['claude-review.yml']);

const failures = [];
for (const name of readdirSync(DIR).filter((f) => f.endsWith('.yml')).sort()) {
  if (VENDORED.has(name)) continue;
  const text = readFileSync(resolve(DIR, name), 'utf8');

  if (/uses:\s*actions\/setup-node/.test(text)) {
    failures.push(`${name}: прямой actions/setup-node — версия Node объявляется в ` +
                  `.github/actions/setup-web, зовите его (#287)`);
  }
  // Джоба — ключ второго уровня под `jobs:`; на полноценный YAML-разбор здесь смысла нет,
  // отступы в наших workflow единообразны.
  const jobsAt = text.indexOf('\njobs:');
  if (jobsAt < 0) { failures.push(`${name}: нет секции jobs`); continue; }
  const body = text.slice(jobsAt);
  const blocks = body.split(/\n {2}(?=[\w-]+:\n)/).slice(1);
  for (const block of blocks) {
    const job = block.match(/^([\w-]+):/)?.[1] ?? '?';
    if (!/\n {4}timeout-minutes:/.test(block)) {
      failures.push(`${name}: у джобы «${job}» нет timeout-minutes (#287)`);
    }
  }
}

if (failures.length) {
  console.error(`❌ Связка setup в workflow разошлась (${failures.length}):`);
  for (const f of failures) console.error(`  — ${f}`);
  process.exit(1);
}
console.log('✅ Workflow: прямых setup-node нет, timeout-minutes у всех джоб');
