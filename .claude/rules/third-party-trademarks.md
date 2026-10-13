# Third-party games and their trademarks — rule for the author of text and code

<!-- COPY of the single template: source of truth — OmnisGM-App/claude-plugins/templates/third-party-trademarks.md;
     roll out edits as copies to the repos where texts about third-party systems are written (Table, Rules).
     Owner decision 2026-10-10, Table#912. -->

An open licence on an SRD covers the rules text, not the trademarks. CC BY 4.0 on SRD 5.1/5.2.1 grants no
rights to "Dungeons & Dragons", "D&D" or the dragon ampersand. Other systems have their own licences and their own marks.

1. **A third-party game is named only descriptively.** The game's name stands next to "for", "based on", "compatible with"
   or works as a category name ("a D&D 2024 spell"). It never becomes part of the name of a product,
   feature, page or of the brand part of `<title>`: we have one brand, OmnisGM. Do not write "OmnisGM D&D
   sheet" or "Official…". Do not put "D&D 2024." on its own line as if it were our tagline.
2. **No third-party logos.** The D&D ampersand mark, logos of WotC, Critical Role or Chaosium
   appear nowhere: not in icons, OG images, generated images, screenshots.
   Exception — a mark the licence requires to be shown (Powered by BRP per §15 BRP OGL), and only
   where it requires it.
3. **Independence — one formula, no "fan project".** «OmnisGM — независимый продукт / проект,
   не связан с Wizards of the Coast и не одобрен ею» (EN: "an independent product/project, not
   affiliated with or endorsed by Wizards of the Coast"). We will have a paid subscription, and the word
   "fan project" would become untrue. The D&D trademark line is carried by four places:
   - the footer of every Rules reference page, i.e. everything `ReaderShell` renders; the ecosystem's shared 404
     does not mention D&D and does not carry the line;
   - the footer of the Table landing page;
   - section 1 of the terms of service, four copies of `legal/terms-of-service*.md`;
   - the Table licences page `omnisgm.com/licenses`, `legal/licenses.{en,ru}.md`.

   The formula is written as literals in each repo's gates, and those literals are their own, not an import from the text:
   - Rules: e2e `web/e2e/trademark.spec.ts` and the CI gate `web/scripts/verify_dist_trademark.mjs`
     (the whole dist plus `llms.txt`);
   - Table: e2e `tests/e2e/landing.spec.ts` and `tests/e2e/legal.spec.ts`, a vitest guard in CI
     `frontend/src/shared/i18n/trademarkNotice.test.ts` (landing, terms, licences page).

   If you change the wording — change the text in all four places and the literals in all gates. There is no
   cross-repo check: if Rules and Table drift apart from each other, no gate will catch it.
4. **An entry's name comes from the document it was imported from.** The name is taken from the document
   the entry was imported from, is valid under that document's licence and does not
   move between documents: for 2014 content — SRD 5.1 names, for 2024 — SRD 5.2.1, and likewise for any
   other system and its SRD. If the object is absent from the document or WotC renamed it (in 5.2 that is how
   Deck of Many Things, Orb of Dragonkind and the like were dropped, so as not to touch protected marks),
   the old name does not appear in that document's content: not in data, not in hints, not
   in examples. In the SRD 5.1 section the same objects legitimately stand under their names; into 2024
   content and into the compendium built from 5.2.1 they are not carried over.
5. **A new system — its licence first.** The attribution formula and the trademark line are taken from the system's
   licence (DPCGL §4.1, BRP OGL, ORC and so on) before the first commit with its content. The
   non-affiliation line is added next to that system's attribution.
