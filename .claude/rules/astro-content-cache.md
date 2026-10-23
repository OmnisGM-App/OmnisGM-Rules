---
paths:
  - "web/src/lib/rehype-*.mjs"
  - "web/src/lib/remark-*.mjs"
  - "web/astro.config.*"
  - "web/src/content.config.*"
---

# Astro content cache: clear `.astro` after a markdown-pipeline edit

Astro's content layer caches the rendered Markdown per file and does not invalidate it when a rehype/remark plugin
or the markdown config changes. Symptom: `npm run build` in `web/` finishes fast (~4 s instead of ~15 s), the
plugin's standalone test passes, and the built page in `dist` still shows the old rendering (seen with
`rehype-entity-autolink`).

- After editing any `src/lib/rehype-*.mjs` / `remark-*.mjs` or the markdown config, build with
  `rm -rf .astro node_modules/.astro node_modules/.vite dist && npm run build` in `web/`.
- Clearing only `.vite` / `dist` (the snapshot recipe in `authoring-e2e.md`) is not enough: the Markdown render
  cache lives in `.astro` separately.
- The Playwright `webServer` runs a fresh build, so e2e is not fooled; a hand check of `dist` is, unless the cache
  was cleared.
