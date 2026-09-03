import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import type { FullConfig } from '@playwright/test';
import { E2E_PORT } from './ports';

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
 * Чего страж НЕ различает: серверы из ОДНОГО каталога. Если в `web/` поднят `npm run dev`, а
 * его порт совпал с нашим, Playwright переиспользует его без пересборки (при живом HTTP-ответе
 * раннер возвращается ДО запуска команды `webServer`), и матрица молча пойдёт против
 * dev-сервера вопреки шапке конфига «тестируем прод-вывод». Сегодня это закрыто разведением
 * портов — у dev своя база (`DEV_PORT`), — но не самим стражем: отличать свежую сборку от
 * устаревшей он сможет только по отпечатку `dist`, и это отдельная задача.
 *
 * О порядке: `globalSetup` запускается ПОСЛЕ `webServer`, не раньше. Для нашего сценария это
 * ничего не меняет — чужой preview отвечает по HTTP, Playwright его переиспользует и сразу
 * отдаёт управление сюда, так что падаем мы до первого теста. Но если порт занял НЕ-HTTP
 * сквоттер, первым придёт таймаут ожидания сервера, и страж не скажет ничего.
 */

/**
 * Реальный путь без симлинков: `lsof` отдаёт каталог уже разрешённым (`/private/tmp/…`), а
 * путь из конфига — тот, через который открыли (`/tmp/…`). На macOS `/tmp → /private/tmp`, и
 * без выравнивания worktree, живущий под `/tmp`, получил бы ложное «чужой сервер».
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
 * Отсчитываем от пути конфига, который даёт сам Playwright, а не от `process.cwd()`: прогон
 * запускают откуда угодно.
 */
function webDir(config: FullConfig): string {
  return real(config.configFile ? path.dirname(config.configFile) : process.cwd());
}

function sh(file: string, args: string[]): string | null {
  try {
    return execFileSync(file, args, {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
      // Зависший `lsof` иначе подвесил бы прогон ещё до первого теста.
      timeout: 10_000,
    }).trim();
  } catch (err) {
    // Ненулевой код у `lsof` означает «никто не слушает», у `git` — «не репозиторий»: штатные
    // ответы. А вот отсутствующий инструмент — не ответ, а слепота: страж молча сказал бы
    // «порт свободен», не проверив ничего. Про такое говорим вслух.
    if ((err as NodeJS.ErrnoException)?.code === 'ENOENT') {
      console.warn(`[global-setup] ${file} недоступен — проверка владельца порта пропущена`);
    }
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
  const foreign = listenerDirs(E2E_PORT).filter((dir) => real(dir) !== ours);
  if (foreign.length === 0) return;

  throw new Error(
    [
      `На порту ${E2E_PORT} висит сервер из ЧУЖОГО каталога — прогон пошёл бы против чужой сборки.`,
      `  слушает: ${foreign.map(describe).join(', ')}`,
      `  ожидалось: ${ours}`,
      'Разведи каталоги слотами (в соседнем worktree — OMNISGM_SLOT=1) либо останови тот сервер.',
    ].join('\n'),
  );
}
