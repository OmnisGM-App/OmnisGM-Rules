---
paths:
  - "web/src/lib/page-title.ts"
  - "web/src/components/ReaderShell.astro"
  - "web/e2e/daggerheart.spec.ts"
  - "src/daggerheart/**"
---

# Daggerheart (DPCGL): what is easy to break without noticing

Rules#166 (closed 2026-08-13, PR #191) settled how the Daggerheart SRD is published under the DPCGL. The
reasoning lives outside this public repo; this file keeps only the parts a routine edit can undo.

1. **The system label always carries «SRD»** («Daggerheart SRD 1.0» in full; «Daggerheart SRD» on the short rung of
   the ladder and in the home heading), **and «SRD» never drops out of a `<title>`** — not
   even on the last step of the shortening ladder in `web/src/lib/page-title.ts`. DPCGL §2.5(a) forbids the Name
   Mark as the title of a work or chapter; the mark is allowed as part of the source document's name, which §4.1
   itself prescribes («Daggerheart System Reference Document 1.0»). PR #189 (SEO task #185) removed «SRD» to save
   title characters and the regression lived a week. Navigation labels (systems tab, breadcrumb, search badge)
   are not titles and stay as they are.
2. **§2.5(c) («Compatible» next to the mark) is deliberately not applied literally**: it is about third-party
   compatible products, while we republish the Public Game Content itself; «Daggerheart Compatible SRD» would be
   a false claim. The full document name is used instead. The question to DRP is on record with the owner.
3. **The §4.1(a–e) attribution lives in `ATTRIB` in `web/src/components/ReaderShell.astro`** (markup, rendered
   with `set:html`): copyright, the exact PGC name, the link to daggerheart.com (that is (c)), the licence link,
   and both halves of the modification notice — ours (translation + Markdown) and the earlier third-party one (the
   seansbox conversion the EN text is partly built from). The licence's stock sentence «There are no previous
   modifications by others» must NOT be used: for us it is false.
4. The e2e «DPCGL: атрибуция §4.1 в футере и §2.5 в `<title>`» in `web/e2e/daggerheart.spec.ts` holds the
   §4.1 attribution in the footer and «SRD» in hub titles that fit the first rung of the ladder; the short rung
   (`short ? 'Daggerheart SRD' : …`) has no test yet — Rules#446. e2e does not run in CI, so a change to the title
   ladder or to `ATTRIB` runs that spec by hand before the push.

Adding another licensed system: its attribution formula and trademark line come from its licence before the
first content commit (`third-party-trademarks.md` rule 5).
