#!/usr/bin/env node
// Подключение pre-commit хука (issue #283), вызывается корневым `prepare`.
//
// Отдельный скрипт вместо `git config core.hooksPath .githooks || true` по двум причинам
// (ревью #299): прежняя строка молча ПЕРЕЗАПИСЫВАЛА уже настроенный `core.hooksPath` —
// локальный или глобальный, — и `|| true` заодно маскировал реальный отказ `git config`
// (например, запуск вне git-репозитория) под успех.
//
// Здесь: чужое значение не трогаем, а называем; отсутствие git не притворяется успехом,
// но и не валит установку зависимостей — хук это удобство, а не обязательное условие.
import { execFileSync } from 'node:child_process';

const WANT = '.githooks';

/** Значение git-конфига или null. */
function config(key) {
  try {
    return execFileSync('git', ['config', '--get', key], { encoding: 'utf8' }).trim() || null;
  } catch {
    return null; // ключ не задан (rc=1) или git недоступен
  }
}

try {
  execFileSync('git', ['rev-parse', '--git-dir'], { stdio: 'ignore' });
} catch {
  console.log('[hooks] не git-репозиторий — pre-commit не подключён');
  process.exit(0);
}

const current = config('core.hooksPath');
if (current === WANT) process.exit(0);
if (current) {
  console.log(`[hooks] core.hooksPath уже задан («${current}») — НЕ трогаю. ` +
              `Хук репозитория лежит в ${WANT}/, подключить: git config core.hooksPath ${WANT}`);
  process.exit(0);
}

try {
  execFileSync('git', ['config', 'core.hooksPath', WANT]);
  console.log(`[hooks] core.hooksPath = ${WANT}`);
} catch (error) {
  const reason = error instanceof Error ? error.message.split('\n')[0] : String(error);
  console.log(`[hooks] не удалось задать core.hooksPath (${reason}) — pre-commit не подключён`);
}
