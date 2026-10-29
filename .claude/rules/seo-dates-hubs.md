---
paths:
  - "web/src/**"
  - "web/scripts/*.mjs"
  - "firebase.json"
---

# Site SEO mechanics: dates, sitemap, hubs, breadcrumbs (#219, #221, #230, #220)

## Content dates for JSON-LD (#219)

`datePublished`/`dateModified` on `Article` come from the **git history** of the source markdown:
`web/scripts/gen-content-dates.mjs` (prebuild) does one pass of `git log --name-only` over `src/`
and writes the map to `web/src/data/content-dates.json` (gitignored), while `web/src/lib/content-dates.mjs`
serves the dates to the page. An entity page knows its resource and passes `contentSource` to
`ReaderShell`; which `.md` files stand behind a resource is told by `_sources.json` from the parser
(`generate_api.py --emit-sources`), so that this knowledge is not duplicated in JS.

**A shallow clone yields no dates.** `actions/checkout` without `fetch-depth: 0` brings no history, and
pages are left WITHOUT dates — deliberately: a build date on 6000 pages would mean "everything updated
at once". That is why `ci.yml` and `deploy.yml` have `fetch-depth: 0` + `filter: blob:none`, and the gate
`verify_dist_meta_budget.mjs` fails the build if an Article is left without the required fields.

## lastmod in the sitemap (#221)

Set by the postbuild script `web/scripts/add_sitemap_lastmod.mjs`: it reads `dateModified`
from the JSON-LD of the already built pages (#219) and writes `<lastmod>` into `dist/sitemap-N.xml`. This way
the routing and the "URL → source file" map are not duplicated anywhere — the sitemap and the page markup
agree by construction. The script is idempotent and fails the build if there are no dates at all or any URL
is left without one. The language hubs (`/`, `/en/`, `/ru/`) have no `Article`: they get the newest date among
the pages of their language (the root — of all pages), still a content date, never the build date (#468).

## Breadcrumb name of a document (#468)

The game level is collapsed into the edition (#220), so the edition label alone must name the system.
D&D labels do («SRD 5.2.1 (5.5e, 2024)»); Daggerheart and BRP label the edition «SRD 1.0», so their NAV
groups carry `crumb` («Daggerheart SRD 1.0», «Basic Roleplaying SRD 1.0») used in the breadcrumb instead.
`verify_dist_meta_budget.mjs` fails on any breadcrumb named bare «SRD x.y».

## Robots meta and snippet budget (#468)

Every indexable page carries `<meta name="robots" content="max-image-preview:large">` (`Reader.astro`);
noindex pages keep `noindex, follow`. The JSON API `/api/**` gets `X-Robots-Tag: noindex` from
`firebase.json`. `verify_dist_meta_budget.mjs` fails on an indexable page without the directive and on a
description longer than 155 characters on the entrances (`/`, `/en/`, `/ru/`, document hubs).

## Document-level hubs (#230)

`/{lang}/{game}/{version}/` — the page of the edition itself: a table of contents of all sections (classes
expand into a list) plus the reference lists with entity counts. One template —
`web/src/components/DocHub.astro`, the route pages are thin (one per game). Links are built
from the same NAV tree as the sidebar, the counts — from the `meta.json` of the same JSON API that feeds the
pages themselves: no second source of truth. Dates for JSON-LD — across ALL files of the document
(`datesForDoc`), because the hub has no markdown of its own.

Why: per the 2026-09-01 audit the site's main deficit is crawling ("Discovered – currently not indexed"
for 5 807 URLs out of 5 975), and there was no top-level structure node at all. Since #230 the document breadcrumb leads
to the hub (previously — to the "first content page", the compromise of option 2 from #220).
The system level (`/{lang}/dnd/`) has NO page of its own — a 301 to the latest edition
in `firebase.json`: D&D has two editions plus a conversion document, there is no honest content for
such a page.

## Firebase emulator ≠ prod in redirect syntax (#230)

The emulator matches `source` via path-to-regexp and understands constraints like `/:lang(en|ru)`;
**prod Hosting does not understand them** — the rule silently does not fire, the URL returns 404. Caught
on the system-level redirects: on the emulator all three led where they should, after the release `/ru/dnd`
returned 404. Write routes explicitly (one rule per language) or via the `regex` key (RE2),
and **verify after deploy on prod itself** — a green emulator proves nothing here.
(For headers the emulator remains authoritative: the merging of rules by key matches.)

## Breadcrumbs (#220)

The `BreadcrumbList` markup and the visible `.rd-crumb` row are built from ONE array in
`web/src/components/ReaderShell.astro` — Google's requirement is "markup describes what is visible".
The levels are not taken from the NAV tree one-to-one: game and edition are collapsed into one document crumb
(the link — the edition's first content page, Legal is skipped), and a group without its own
page («Классы» "Classes", «Глоссарий» "Glossary") stays as visible text but does not go into the markup — otherwise it
gets "the first leaf page inside" substituted, and that is what produced duplicate URLs and a link to the barbarian.
Entity pages append themselves as the last level (their `currentId` is the parent chapter).
Held by: the gates in `verify_dist_meta_budget.mjs` (duplicate URLs in the trail 0, links to nowhere 0) and
`web/e2e/seo-breadcrumbs.spec.ts`.
