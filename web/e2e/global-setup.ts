import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import type { FullConfig } from '@playwright/test';
import { E2E_PORT } from './ports';
import { FINGERPRINT_FILE, fingerprint } from '../scripts/build_fingerprint.mjs';

/**
 * Страж e2e: на порту прогона — НАШ preview (Table#469, приём из Table#345) из свежей сборки (#251);
 * иначе `reuseExistingServer` молча гонит матрицу против чужой ветки или устаревшего `dist`.
 * Слепое пятно: `globalSetup` идёт ПОСЛЕ `webServer` — НЕ-HTTP сквоттер на порту даёт таймаут
 * ожидания сервера, и страж не говорит ничего.
 */

/** macOS: `lsof` отдаёт `/private/tmp/…`, конфиг — `/tmp/…`; без realpath — ложный «чужой сервер». */
function real(dir: string): string {
  try {
    return fs.realpathSync.native(dir);
  } catch {
    return path.resolve(dir);
  }
}

/** От пути конфига, а не `process.cwd()`: прогон запускают откуда угодно. */
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
    // Ненулевой код — штатный ответ («никто не слушает» / «не репозиторий»); нет инструмента —
    // слепота, о ней говорим вслух.
    if ((err as NodeJS.ErrnoException)?.code === 'ENOENT') {
      console.warn(`[global-setup] ${file} недоступен — проверка владельца порта пропущена`);
    }
    return null;
  }
}

/** Пусто — порт свободен либо `lsof` недоступен. */
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

/** Нет отпечатка — падаем, а не молчим: иначе preview со сборкой до #251 проходил бы мимо стража. */
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
  // В CI сервер поднимается с нуля: проверять нечего, а `lsof` может не быть.
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
