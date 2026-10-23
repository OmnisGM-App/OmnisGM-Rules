---
paths:
  - "web/src/lib/rehype-*.mjs"
  - "web/src/lib/keyword-highlight.mjs"
  - "web/src/lib/rules-gloss.mjs"
  - "web/src/lib/equipment-path.mjs"
  - "web/src/data/api/**"
  - "web/astro.config.*"
  - "web/src/content.config.*"
---

# Astro content cache: clear `.astro` after a markdown-pipeline edit

Astro's content layer caches the rendered Markdown per file and does not invalidate it on a change inside a plugin
module (a plugin added to or removed from the config may reset the store; an edit inside the module does not). Symptom: `npm run build` in `web/` finishes fast (~4 s instead of ~15 s), the
plugin's standalone test passes, and the built page in `dist` still shows the old rendering (seen with
`rehype-entity-autolink`).

- After editing any module from `markdown.rehypePlugins` in `web/astro.config.mjs` (`rehype-*.mjs`,
  `keyword-highlight.mjs`, `rules-gloss.mjs`), a module they import (`equipment-path.mjs`), the data they read
  during the render (`src/data/api/**/all.json`) or the markdown config, build with
  `rm -rf .astro node_modules/.astro node_modules/.vite dist && npm run build` in `web/`.
- Clearing only `node_modules/.vite` (the snapshot recipe in `authoring-e2e.md`) is not enough: the Markdown render
  cache lives in `.astro` separately.
- The Playwright `webServer` builds through the same cache (`npm run build && npm run preview`; locally
  `reuseExistingServer` may even skip the build), so the same `rm -rf …` goes before `npm run test:e2e`; a hand
  check of `dist` is fooled the same way.
