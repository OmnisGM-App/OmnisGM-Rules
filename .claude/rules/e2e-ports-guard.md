---
paths:
  - "web/e2e/**"
  - "web/playwright.config.*"
  - "web/scripts/build_fingerprint*"
---

# Parallel e2e runs: port slot and freshness guard (Table#469, #251)

Ports are derived from the `OMNISGM_SLOT` slot (integer 0–3, default 0): e2e-preview — **4321 + slot × 10**,
`npm run dev` — **4381 + slot × 10**. All the arithmetic is in `web/e2e/ports.ts`. The main directory
stays on the familiar 4321; a neighbouring worktree only needs `OMNISGM_SLOT=1` — and two runs (as well as
two dev servers) go at the same time without interfering.

Why: `reuseExistingServer` is valuable here (the server command is a full site rebuild), but without
separating the ports Playwright silently attaches to the neighbouring directory's preview, and the matrix runs against
someone else's branch — green on someone else's build.

**The one safety net is the guard** `web/e2e/global-setup.ts`: it checks the directory of the port's owner and fails
with a clear line before the first test. `strictPort` is set only on the **dev** server; on preview it
cannot be set — Astro does not pass `vite.preview` through to the preview server, and such a setting would
be dead (verified: with the port taken, `astro preview` moves to the next one regardless of it).

The guard's second check is **build freshness** (#251). The directory is not enough: with `reuseExistingServer`
Playwright, once it gets an HTTP response, returns BEFORE launching the `webServer` command, i.e.
`npm run build` does not run. A preview started an hour ago keeps serving a `dist`
built from code that is no longer in the tree.

Comparing the server against `dist` is useless for this — verified by experiment: `astro preview` reads
files from disk on every request, so such a comparison always matches. Therefore a fingerprint of the
**sources** is compared: `web/scripts/build_fingerprint.mjs` takes it in `prebuild`, `postbuild` puts the
snapshot into `dist/build-id.txt`, and the guard recomputes and compares. Two phases, because computing
only in `postbuild` leaves a window open: a file saved during the build would get into the fingerprint but
not into `dist`, and the guard would stay silent about that edit forever.

Inputs: `web/src`, `web/public` and the `src/` content in the root — by "path + size"; `web/src/lib`,
`web/scripts`, `astro.config.mjs`, `package.json`, `package-lock.json`, `tsconfig.json`,
`web/.env` and the root `firebase.json` (its `hosting.redirects` decide which pages get built,
#399) — read in full (there a "character for character" edit changes the output without touching the size).
Deliberately left out: `.github/**` and `generate_api.py` — they build the JSON API on deploy and do not
land in the local `dist`. Computed in ~50 ms.

No fingerprint in `dist` — the guard fails rather than stays silent: that is what a build from before #251 or one made
outside `npm run build` looks like, and that is exactly the state in which the check is useless.

What the guard still cannot do: it does not ask the server itself. Your own `npm run dev`, were it on
the e2e port, would be reused silently — which is why dev has its own port base (`DEV_PORT`).
