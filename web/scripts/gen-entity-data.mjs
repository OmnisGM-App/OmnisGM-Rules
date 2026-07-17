// Build-time entity data for programmatic pages (issue #20).
//
// getStaticPaths needs structured entity JSON at BUILD time, but the public
// /api is generated at DEPLOY (firebase predeploy, after astro build). So we run
// the SAME parser here, before astro build, writing to src/data/api/ (gitignored).
// --no-validate keeps it dependency-free (plain python3, no jsonschema) so it
// runs in CI without extra setup.
import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '../..'); // .../OmnisGM-Rules
const script = resolve(repoRoot, '.github/scripts/generate_api.py');
const outDir = resolve(here, '../src/data/api');
const python = process.env.PYTHON || 'python3';

// Каждая игра — свой конфиг (config.py / config_{game}.py) и src-root; общий output-dir
// (api/{game}/…). Порядок неважен — игры пишут в непересекающиеся поддеревья.
const GAMES = [
  { game: 'dnd', srcRoot: resolve(repoRoot, 'src/dnd') },
  { game: 'daggerheart', srcRoot: resolve(repoRoot, 'src/daggerheart') },
];

if (!existsSync(script)) {
  console.error(`[gen-entity-data] parser not found: ${script}`);
  process.exit(1);
}

for (const { game, srcRoot } of GAMES) {
  try {
    execFileSync(
      python,
      [script, '--game', game, '--src-root', srcRoot, '--output-dir', outDir, '--no-validate'],
      { stdio: 'inherit' },
    );
  } catch (err) {
    console.error(`[gen-entity-data] generation failed (${game}):`, err.message);
    process.exit(1);
  }
}
console.log(`[gen-entity-data] entity data → ${outDir}`);
