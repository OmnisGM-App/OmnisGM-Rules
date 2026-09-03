import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import type { FullConfig } from '@playwright/test';
import { E2E_PORT } from './ports';
import { FINGERPRINT_FILE, fingerprint } from '../scripts/build_fingerprint.mjs';

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
 * ВТОРАЯ проверка — свежесть сборки (#251). Каталога мало: при `reuseExistingServer`
 * Playwright, получив ответ по HTTP, возвращается ДО запуска команды `webServer`, то есть
 * `npm run build` не выполняется. Поднятый час назад preview продолжает отдавать `dist`,
 * собранный из кода, которого в дереве уже нет, — и матрица идёт против него, показывая
 * зелёное. Сверяем отпечаток исходников: записанный при сборке против сегодняшнего
 * (`scripts/build_fingerprint.mjs`).
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

/**
 * Сверка: `dist`, из которого отвечает сервер, собран из ТЕКУЩИХ исходников.
 *
 * Проверяем всегда, без условий. `globalSetup` идёт ПОСЛЕ `webServer`, поэтому к этому моменту
 * сборка либо только что прошла (сервер поднял Playwright), либо не проводилась вовсе (сервер
 * переиспользован) — в обоих случаях `dist` на месте и отпечаток в нём есть.
 *
 * Отпечатка нет — падаем, а не молчим. Это ровно то состояние, в котором проверка бесполезна:
 * `dist` из сборки до #251 или собранный мимо `npm run build` (например, голым `astro build`).
 * Тихий пропуск здесь означал бы, что в день мёржа у всех, у кого поднят старый preview,
 * страж молча пропускает прогон против устаревшей сборки — то есть сценарий #251 переживает
 * собственный фикс.
 */
async function checkBuildFreshness(web: string): Promise<void> {
  const file = path.join(web, 'dist', FINGERPRINT_FILE);
  if (!fs.existsSync(file)) {
    throw new Error(
      [
        `В сборке нет отпечатка (${path.relative(web, file)}) — свежесть проверить нечем.`,
        'Так выглядит `dist` из сборки до #251 или собранный мимо `npm run build`.',
        'Останови сервер на порту прогона и запусти заново: `npm run build` положит отпечаток.',
      ].join('\n'),
    );
  }

  const built = fs.readFileSync(file, 'utf8').trim();
  const current = await fingerprint();
  if (built === current) return;

  throw new Error(
    [
      'Сборка в `dist` СТАРШЕ рабочего дерева — прогон проверял бы код, которого уже нет.',
      `  собрано из исходников: ${built}`,
      `  сейчас в рабочем дереве: ${current}`,
      'Обычная причина: preview поднят давно, Playwright переиспользует живой сервер и',
      '`npm run build` при этом НЕ выполняет, поэтому поздние правки в прогон не попадают.',
      'Останови сервер на порту прогона — он соберёт и поднимет свой.',
    ].join('\n'),
  );
}

export default async function globalSetup(config: FullConfig): Promise<void> {
  // На CI e2e не гоняются вовсе (там только `astro check` + `build`), но если однажды поедут —
  // сервер там поднимается с нуля в свежем раннере: проверять нечего, а `lsof` может и не быть.
  if (process.env.CI) return;

  const ours = webDir(config);
  const foreign = listenerDirs(E2E_PORT).filter((dir) => real(dir) !== ours);
  if (foreign.length === 0) {
    await checkBuildFreshness(ours);
    return;
  }

  throw new Error(
    [
      `На порту ${E2E_PORT} висит сервер из ЧУЖОГО каталога — прогон пошёл бы против чужой сборки.`,
      `  слушает: ${foreign.map(describe).join(', ')}`,
      `  ожидалось: ${ours}`,
      'Разведи каталоги слотами (в соседнем worktree — OMNISGM_SLOT=1) либо останови тот сервер.',
    ].join('\n'),
  );
}
