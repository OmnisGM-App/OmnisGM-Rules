import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import sitemap from '@astrojs/sitemap';
import pagefind from 'astro-pagefind';
import rehypePromoteHeadings from './src/lib/rehype-promote-headings.mjs';

// rules.omnisgm.com — статический (SSG) ридер SRD экосистемы OmnisGM.
// Контент — Markdown из ../src/{game}/{version}/{en,ru}/**.md (вход контентного пайплайна),
// рендерится на билде. Pagefind (статический поиск) и PWA подключаются следующими шагами.
export default defineConfig({
  site: 'https://rules.omnisgm.com',
  // Везде trailing slash: директорийные URL (/en/.../legal/) и индекс API (/api/dnd/) тогда
  // работают с относительными ссылками; Firebase trailingSlash:true их не ломает редиректом.
  trailingSlash: 'always',
  integrations: [
    react(),
    sitemap(),
    pagefind(),
  ],
  build: {
    format: 'directory',
  },
  markdown: {
    // Нормализуем уровни заголовков ДО сбора TOC (headings) Astro — чтобы titled h1 не попадал в TOC.
    rehypePlugins: [rehypePromoteHeadings],
  },
});
