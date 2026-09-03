import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import type { FullConfig } from '@playwright/test';
import { PORT } from './ports';

/**
 * Проверка, что на порту прогона висит НАШ preview (Table#469, приём из Table#345).
 *
 * `reuseExistingServer` здесь ценен как нигде: команда сервера — `npm run build && npm run
 * preview`, то есть полная пересборка сайта. Гонять её ради одного спека незачем, если
 * preview уже поднят.
 *
 * Ломает не переиспользование, а переиспользование НЕ ТОГО сервера. Соседний worktree со
 * своим слотом на наш порт не сядет — но если оба каталога забыли развести слоты, Playwright
 * молча возьмёт чужой preview, и прогон пойдёт против чужой ветки. Зелёное по чужой сборке
 * хуже красного: оно ничего не проверило и об этом не сказало.
 *
 * Поэтому: не совпал каталог — падаем одной внятной строкой ещё до первого теста.
 *
 * Порядок с `webServer` не важен: если сервер поднимет сам Playwright, владельцем порта
 * окажется наш же каталог, и проверка пройдёт в любом случае.
 */

/**
 * Реальный путь без симлинков. `lsof` отдаёт каталог уже разрешённым (`/private/tmp/…`), а
 * относительный путь — тот, через который открыли (`/tmp/…`); на macOS `/tmp → /private/tmp`,
 * и без выравнивания worktree под `/tmp` получил бы ложное «чужой сервер».
 */
function real(dir: string): string {
  try {
    return fs.realpathSync.native(dir);
  } catch {
    return path.resolve(dir);
  }
}

/**
 * Каталог сайта: `webServer` запускается из каталога конфига (`web/`), с ним и сверяемся.
 * Отсчитываем от файла конфига, который даёт сам Playwright, а не от `import.meta.url`:
 * прогон запускают откуда угодно, и `cwd` тут не показатель.
 */
function webDir(config: FullConfig): string {
  return real(config.configFile ? path.dirname(config.configFile) : process.cwd());
}

function sh(file: string, args: string[]): string | null {
  try {
    return execFileSync(file, args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  } catch {
    // Ненулевой код у `lsof` означает «никто не слушает», у `git` — «не репозиторий».
    return null;
  }
}

/** Каталоги процессов, слушающих порт. Пусто — порт свободен либо `lsof` недоступен. */
function listenerDirs(port: number): string[] {
  const pids = sh('lsof', ['-t', '-i', `tcp:${port}`, '-sTCP:LISTEN']);
  if (!pids) return [];

  const dirs = new Set<string>();
  for (const pid of pids.split('\n').filter(Boolean)) {
    // -Fn — машинный вывод; строка каталога начинается с «n».
    const out = sh('lsof', ['-a', '-p', pid, '-d', 'cwd', '-Fn']);
    const dir = out?.split('\n').find((line) => line.startsWith('n'))?.slice(1);
    if (dir) dirs.add(dir);
  }
  return [...dirs];
}

function describe(dir: string): string {
  const branch = sh('git', ['-C', dir, 'rev-parse', '--abbrev-ref', 'HEAD']);
  return branch ? `${dir} (ветка ${branch})` : dir;
}

export default function globalSetup(config: FullConfig): void {
  // На CI e2e не гоняются вовсе (там только `astro check` + `build`), но если однажды поедут —
  // сервер там поднимается с нуля в свежем раннере: проверять нечего, а `lsof` может и не быть.
  if (process.env.CI) return;

  const ours = webDir(config);
  const foreign = listenerDirs(PORT).filter((dir) => real(dir) !== ours);
  if (foreign.length === 0) return;

  throw new Error(
    [
      `На порту ${PORT} висит ЧУЖОЙ preview — прогон пошёл бы против чужой сборки.`,
      `  слушает: ${foreign.map(describe).join(', ')}`,
      `  ожидалось: ${ours}`,
      'Разведи каталоги слотами (в соседнем worktree — OMNISGM_SLOT=1) либо останови тот preview.',
    ].join('\n'),
  );
}
