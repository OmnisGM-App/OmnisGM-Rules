import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import pagefind from 'astro-pagefind';
import rehypePromoteHeadings from './src/lib/rehype-promote-headings.mjs';
import rehypeWrapTables from './src/lib/rehype-wrap-tables.mjs';
import rehypeSortableGlossary from './src/lib/rehype-sortable-glossary.mjs';
import rehypeEntityAutolink from './src/lib/rehype-entity-autolink.mjs';
import rehypeKeywordHighlight from './src/lib/keyword-highlight.mjs';
import rehypeRulesGloss from './src/lib/rules-gloss.mjs';
import { isIndexableGlossary } from './src/lib/glossary-seo.mjs';
import { DEV_PORT } from './e2e/ports.ts';

// rules.omnisgm.com — статический (SSG) ридер SRD экосистемы OmnisGM.
// Контент — Markdown из ../src/{game}/{version}/{en,ru}/**.md (вход контентного пайплайна),
// рендерится на билде. Service worker собирается после `astro build` — scripts/build-sw.mjs,
// манифест PWA лежит статикой в public/manifest.webmanifest.
export default defineConfig({
  site: 'https://rules.omnisgm.com',
  // Везде trailing slash: директорийные URL (/en/.../legal/) и индекс API (/api/dnd/) тогда
  // работают с относительными ссылками; Firebase trailingSlash:true их не ломает редиректом.
  trailingSlash: 'always',
  integrations: [
    // Глоссарные страницы по умолчанию noindex (см. Reader.astro) — исключаем их и из sitemap
    // (issue #37: не тратить краул-бюджет, не слать противоречивый сигнал). ИСКЛЮЧЕНИЕ (#106,
    // этап 1): содержательные справочники без entity-хаба (DH оружие/броня/предметы/расходники,
    // BRP оружие/броня) возвращаем в индекс и sitemap — спрос подтверждён кликами. Дубли хабов
    // и оглавления-термины остаются вне sitemap. IndexNow берёт URL из dist-sitemap.
    sitemap({ filter: (page) => !page.includes('/glossary/') || isIndexableGlossary(page) }),
    pagefind(),
  ],
  build: {
    format: 'directory',
  },
  // Порт dev-сервера — от слота (Table#469), как и порт e2e-preview: два worktree держат по
  // своему `npm run dev` и не спорят за порт.
  //
  // Порт задаётся ЗДЕСЬ, а `strictPort` — в `vite.server` ниже, и это не разнобой ради
  // разнобоя: Astro собирает свой `server` сам и перезаписывает им `vite.server.port`
  // (проверено: с портом внутри `vite` dev упрямо поднимался на 4321), а `strictPort` в его
  // собственной схеме отсутствует и доезжает только через vite.
  server: { port: DEV_PORT },
  vite: {
    // Занятый порт — ошибка, а не тихий переезд на соседний: без этого второй `npm run dev`
    // молча уехал бы на +1, то есть на порт соседнего слота.
    //
    // Только для dev, и это не забывчивость: Astro не прокидывает `vite.preview` в
    // preview-сервер (`astro/dist/core/preview/static-preview-server.js` зовёт vite
    // `preview({ configFile: false, preview: { host, port, headers, open, allowedHosts } })`),
    // так что `preview: { strictPort: true }` был бы мёртвой настройкой — а хуже того,
    // документировал бы страховку, которой нет. Тихий переезд preview ловит страж
    // (`e2e/global-setup.ts`), сверяющий владельца порта.
    server: { strictPort: true },
  },
  markdown: {
    // Нормализуем уровни заголовков ДО сбора TOC (headings) Astro — чтобы titled h1 не попадал в TOC.
    // Порядок важен (issue #20): rehypeEntityAutolink оборачивает имена сущностей в <a>, затем
    // rehypeKeywordHighlight красит ключевые слова — последним, чтобы не лезть внутрь ссылок
    // (<a> в его SKIP_TAGS) и работать по уже готовому дереву.
    rehypePlugins: [rehypePromoteHeadings, rehypeSortableGlossary, rehypeWrapTables, rehypeEntityAutolink, rehypeKeywordHighlight, rehypeRulesGloss],
  },
});
