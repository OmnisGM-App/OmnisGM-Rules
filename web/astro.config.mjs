import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import sitemap from '@astrojs/sitemap';

// rules.omnisgm.com — статический (SSG) ридер SRD экосистемы OmnisGM.
// Контент — Markdown из ../src/{game}/{version}/{en,ru}/**.md (вход контентного пайплайна),
// рендерится на билде. Pagefind (статический поиск) и PWA подключаются следующими шагами.
export default defineConfig({
  site: 'https://rules.omnisgm.com',
  trailingSlash: 'ignore',
  integrations: [
    react(),
    sitemap(),
  ],
  build: {
    format: 'directory',
  },
});
