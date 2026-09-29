// Build-time entity data for programmatic pages (issue #20): getStaticPaths needs entity JSON at BUILD
// time, while the public /api is generated at DEPLOY — so the SAME parser runs here, before astro build.
// --no-validate keeps it dependency-free (plain python3, no jsonschema).
import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '../..'); // .../OmnisGM-Rules
const script = resolve(repoRoot, '.github/scripts/generate_api.py');
const outDir = resolve(here, '../src/data/api');
// Карта «ресурс → исходные .md» (#219): нужна сборке, чтобы проставить сущностным страницам
// datePublished/dateModified. Знание живёт в SOURCES генератора, здесь его не дублируем.
const sourcesFile = resolve(outDir, '_sources.json');
const python = process.env.PYTHON || 'python3';

// Порядок игр неважен — они пишут в непересекающиеся поддеревья api/{game}/….
const GAMES = [
  { game: 'dnd', srcRoot: resolve(repoRoot, 'src/dnd') },
  { game: 'daggerheart', srcRoot: resolve(repoRoot, 'src/daggerheart') },
  { game: 'brp', srcRoot: resolve(repoRoot, 'src/brp') },
];

if (!existsSync(script)) {
  console.error(`[gen-entity-data] parser not found: ${script}`);
  process.exit(1);
}

for (const { game, srcRoot } of GAMES) {
  try {
    execFileSync(
      python,
      [script, '--game', game, '--src-root', srcRoot, '--output-dir', outDir, '--no-validate',
       '--emit-sources', sourcesFile],
      { stdio: 'inherit' },
    );
  } catch (err) {
    console.error(`[gen-entity-data] generation failed (${game}):`,
                  err instanceof Error ? err.message : err);
    process.exit(1);
  }
}
console.log(`[gen-entity-data] entity data → ${outDir}`);
