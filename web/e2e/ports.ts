import { ports } from '@omnisgm-app/core/blocks';
import { slot } from '@omnisgm-app/core/ports';

/**
 * Порты прогона — от «слота» (Table#469): соседний worktree с `OMNISGM_SLOT=1` не цепляется
 * к чужому preview через `reuseExistingServer` (Table#345). Слот 0 — привычные порты.
 * Карта баз экосистемы и её проверка на пересечения — в `@omnisgm-app/core` (Table#477).
 */

const rules = ports('rules');

export { slot };

export const E2E_PORT = rules.e2e;

/**
 * Не `E2E_PORT`: dev и preview — разные серверы, общий порт узаконил бы прогон матрицы
 * против dev-сервера.
 */
export const DEV_PORT = rules.dev;

export const BASE_URL = `http://localhost:${E2E_PORT}`;
