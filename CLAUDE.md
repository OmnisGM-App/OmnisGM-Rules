# OmnisGM Rules — rules.omnisgm.com

> SRD reader for tabletop games (D&D 5.2.1/5.1, Daggerheart 1.0, BRP 1.0) — **a product of the OmnisGM ecosystem**.
> This file covers the product, the stack and the infrastructure. The content pipeline (PDF import → markdown → translation)
> lives in **[documentation/content-pipeline.md](documentation/content-pipeline.md)** (#288):
> it has a life of its own and is not needed in day-to-day work on the site.

## Where to look

| Topic | Where |
|---|---|
| SRD import and translation, pipeline skills, `.claude/rules` rules | [documentation/content-pipeline.md](documentation/content-pipeline.md) |
| Entity images: format, layout, prompts | [documentation/entity-images.md](documentation/entity-images.md), [image-prompts.md](documentation/image-prompts.md) |
| Product, stack, infrastructure, accumulated pitfalls | this file, below |

## Product and the OmnisGM ecosystem

### Product lineup
- **Main** — the interactive character sheet.
- **Secondary** — news (The Guild Herald, news.omnisgm.com; separate repo `OmnisGM-News`).
- **This one** — rules/SRD (`rules.omnisgm.com`).

### Main goal — an SEO funnel into the main product
A person googles a rules clarification → lands on our **static** rules page → a CTA takes them
to the interactive character sheet. Hence **SEO is critical** and content **must render to static HTML**
(NOT a client-rendered SPA — client-render is exactly what killed SEO for the news site: the crawler sees an empty `<div id=root>`).

### Publishing stack — Astro (SSG)
The site is published by **Astro (SSG)**; the former MkDocs Material + GitHub Pages is decommissioned
(`pages.yml` deleted). The import/translation content pipeline does not depend on the engine — it produces
`.md` files that the site consumes.

Why Astro: (1) the designer delivered ready-made **React components**, and Astro can both take them
as islands and ship them as static output; (2) **PWA is mandatory**;
(3) shared stack with the ecosystem. In practice no islands were needed: the components were ported
as `.astro`, and the pages ship zero-JS — SEO is intact by construction.

The MkDocs leftovers are gone (#296): the src/site directory, the prepare_docs.sh and
split_sitemap.py scripts, the `/site/ /docs/ /mkdocs.yml /overrides/` entries in `.gitignore`. (The paths here
are deliberately without backticks: the links gate reads them as a claim about a live tool, and these
files no longer exist.) The `/integrate-srd` skill is still ALIVE: it was rewritten for Astro (#318) and
no longer touches MkDocs files — it is the integration checklist, and
`documentation/content-pipeline.md` only points to it.

The gate `scripts/test_doc_links.mjs` keeps the dead tooling from growing back: a path
to a script, skill, rule or workflow named in documentation or in a skill must
exist. A link inside a ```-block is checked the same as an inline one — that is exactly how a skill
names its helpers.

- **Layout:** the Astro app lives in its own folder **`web/`**. The repo's `src/` is Markdown content
  (`src/{game}/{version}/{en,ru}/*.md`), the content pipeline's input — **do not touch**. Astro content collections
  reference `src/{game}/...md`. Dynamic routes `/{lang}/{game}/{version}/{...slug}` via
  `getStaticPaths` (static). Markdown is rendered **at build time**, not in the browser.
- **Integrations:** **Pagefind** (static search), `@astrojs/sitemap`. PWA is mandatory and is built
  without an integration: the manifest is static in `web/public/manifest.webmanifest`, the service worker is
  `web/scripts/build-sw.mjs` (`workbox-build`) after `astro build`. i18n EN/RU + hreflang, sitemap, JSON-LD. There is NO React in the stack: the designer's
  components were ported as `.astro`, there is not a single island in the project (review #297) — if one
  is ever needed, that is a separate decision, not "already wired in".
- **SEO funnel:** a "to the character sheet" CTA block on every page; an Analytics event on CTA click.

### Design
claude.ai/design project `28349954-9a6f-47fd-a34d-406e6775544e` (the same one that holds the news Gazette).
Read via DesignSync (`get_file`). Files: `Rules.html` (viewport preview wrapper),
**`rules-docs.jsx` — the `RulesDocsApp` component, the real UI**; `rules-docs.css`; `rules-docs-data.jsx`;
shared `omnis-site.css` + `site-shell.jsx` (`OmnisSeal`, `C` tokens). Reader skin: top bar (OmnisGM seal +
"OmnisGM / rules", typeahead search, GitHub, ENG/RU, burger) → system tabs → nav tree on the left, Markdown
in the center, TOC «На этой странице» ("On this page") on the right → prev/next, «Источник» ("Source") row, mobile drawer.

### Infrastructure
- **Repo:** `OmnisGM-App/OmnisGM-Rules`. Cloned locally at `/Users/petrradilov/Documents/OmnisGM/OmnisGM-Rules`
  next to `OmnisGM News`.
- **Firebase:** a SEPARATE project **`omnisgm-rules`** (not `omnisgm-news`). Hosting + the `rules.omnisgm.com` domain
  (the owner will set up DNS once hosting is up).
- **Repo secrets/variables:** `FIREBASE_SERVICE_ACCOUNT` (secret, the deploy SA key — set it with `gh secret set < file`
  WITHOUT reading it). The client `firebaseConfig` is 7 public values in **repo variables** `VITE_FIREBASE_*`
  (variables, NOT secrets — a web apiKey is not a credential).
- **Analytics:** `measurementId G-RRH57ELLZS` — traffic + CTA-funnel conversion; a separate
  client-island, no effect on static HTML / SEO.
- **Deploy:** `astro build` + `firebase deploy --only hosting` (project `omnisgm-rules`).
  The JSON API is built by `hosting.predeploy` in `firebase.json` (`generate_api.py` once per game),
  releases — `.github/workflows/release.yml` (rolling tag `latest`).

### Infrastructure narratives — in `.claude/rules/` (paths-scoped)

The deep "why" sections are moved out into rules; they attach automatically when working
with the corresponding files:

- `e2e-ports-guard.md` — the `OMNISGM_SLOT` port slot + the build freshness guard (Table#469, #251)
- `seo-dates-hubs.md` — JSON-LD dates from git, lastmod in the sitemap, document hubs, breadcrumbs,
  emulator ≠ prod for redirects (#219, #221, #230, #220)
- `security-headers-csp.md` — headers in `firebase.json`, CSP enforce and how to check it (#218, #225)
- `cloudflare-cache.md` — a headers-only change requires a zone purge; post-release checks go by origin (#227)
- `codex-images.md` — entity images, the CLS test, the codex token runbook (#201, #202)

### Workflow setup bundle — one shared step (#287)
`setup-node` + cache + `npm ci` + `setup-python` live in the composite action
`.github/actions/setup-web`; workflows call `- uses: ./.github/actions/setup-web`. Node and
Python versions are declared ONLY there (input defaults), and opting out is written explicitly — `node-version: ''`
on a Python-only job. Held by `scripts/test_workflow_setup.mjs`:
it forbids direct `actions/setup-node`/`setup-python` in our workflows and in composite actions,
forbids callers' own version literals and requires `timeout-minutes` on every job (without it
a hung step holds the queue up to the default six hours — `release` once ran into 360 minutes).
The one exception: the vendored `claude-review.yml`.

### Prod watcher (#284)
`.github/workflows/health.yml` — a daily cron (06:00 UTC) + manual run. It runs the already
written checks that previously had no caller: the Cloudflare edge cache, security headers
(twice — via the live domain and via the origin `omnisgm-rules.web.app`, see the #227 trap above) and CSP
violations in the browser. The curl checks go FIRST, before installing Node and Chromium: an infrastructure
blip must not sink checks that do not need it. A red job = a GitHub email to the owner.

### Local gates and pre-commit
`npm run test:unit` (node unit tests), `npm run test:unit:py` (python gates), `npm run test:gates` —
all at once; the roster is checked against `ci.yml` by the guard `scripts/test_unit_agenda.mjs`.

The hook is wired by a root-level **`npm install`** — in the root specifically, without `--prefix web`: `npm ci
--prefix web` does not run the root `prepare`, and there will be no hook. An already configured
`core.hooksPath` is left alone by the install script, which only names it. To bypass the hook — `SKIP_HOOK=1` or
`git commit --no-verify`.

### Owner's working style
Incremental, reviews every step; deploy/push — on explicit request; **"audit ≠ fixes"** (on "check/make sure"
report first, do not change code until told "do it"); prefers generalized data models.
