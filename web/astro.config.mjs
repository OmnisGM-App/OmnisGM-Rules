import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import pagefind from 'astro-pagefind';
import rehypePromoteHeadings from './src/lib/rehype-promote-headings.mjs';
import rehypeWrapTables from './src/lib/rehype-wrap-tables.mjs';
import rehypeSortableGlossary from './src/lib/rehype-sortable-glossary.mjs';
import rehypeEntityAutolink from './src/lib/rehype-entity-autolink.mjs';
import rehypeClassOptionLinks from './src/lib/rehype-class-option-links.mjs';
import rehypeKeywordHighlight from './src/lib/keyword-highlight.mjs';
import rehypeRulesGloss from './src/lib/rules-gloss.mjs';
import { isIndexableGlossary } from './src/lib/glossary-seo.mjs';
import { DEV_PORT } from './e2e/ports.ts';

// rules.omnisgm.com — статический (SSG) ридер SRD экосистемы OmnisGM.
export default defineConfig({
  site: 'https://rules.omnisgm.com',
  // Везде trailing slash: директорийные URL (/en/.../legal/) и индекс API (/api/dnd/) тогда
  // работают с относительными ссылками; Firebase trailingSlash:true их не ломает редиректом.
  trailingSlash: 'always',
  integrations: [
    // Глоссарии noindex и вне sitemap (#37), кроме справочников без entity-хаба (#106).
    sitemap({ filter: (page) => !page.includes('/glossary/') || isIndexableGlossary(page) }),
    pagefind(),
  ],
  build: {
    format: 'directory',
  },
  // Порт здесь, а `strictPort` — в `vite.server`: Astro перезаписывает `vite.server.port` своим
  // `server`, а `strictPort` в его схеме нет.
  server: { port: DEV_PORT },
  vite: {
    // Занятый порт — ошибка, а не тихий переезд на порт соседнего слота. Только dev: Astro не
    // прокидывает `vite.preview` в preview-сервер; переезд preview ловит `e2e/global-setup.ts`.
    server: { strictPort: true },
  },
  markdown: {
    // Порядок важен (#20): уровни заголовков — до сбора TOC; keyword-highlight — после autolink,
    // чтобы не лезть внутрь ссылок (<a> в его SKIP_TAGS).
    rehypePlugins: [rehypePromoteHeadings, rehypeSortableGlossary, rehypeWrapTables, rehypeEntityAutolink, rehypeClassOptionLinks, rehypeKeywordHighlight, rehypeRulesGloss],
  },
});
