import type { Page } from '@playwright/test';

/** = `@media (max-width: 820px)` в `src/styles/reader.css` — мобильная раскладка ридера. */
export const NARROW_MAX = 820;

/**
 * = `@media (max-width: 920px)` в `reader.css`: сворачивает только поиск; навигация и вкладки
 * систем в 821–920 ещё десктопные (#308).
 */
export const BAR_COMPACT_MAX = 920;

export const isNarrow = (page: Page) => (page.viewportSize()?.width ?? 0) <= NARROW_MAX;

export const isSearchCollapsed = (page: Page) =>
  (page.viewportSize()?.width ?? 0) <= BAR_COMPACT_MAX;
