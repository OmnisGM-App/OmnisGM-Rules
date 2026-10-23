# Firebase operations: hosting releases, new sites, reading a stand

Copy of the template from OmnisGM-App/claude-plugins/templates/firebase-ops.md — edit there, roll out
as copies into repos deployed to Firebase (Table, Rules, News).

1. **`HTTP Error: 429 … exceeded the Hosting storage quota` on a deploy is the release store, not the diff.**
   Hosting keeps every past release until the site has a retention limit (console: Hosting → site → release
   storage settings; API: `maxVersions` in SiteConfig). Set since 2026-09-28: Table production keeps 10;
   Rules, News and the test sites keep 3. On a 429 check the limit first, then `gh run rerun`; in a failed
   deploy log look for `grep -aE 'HTTP Error'`. A new site gets its limit on the day it is created.
2. **A new Firebase project has no Hosting site** (since 2026-10-15): before the first `firebase deploy`
   from CI run `firebase hosting:sites:create <site> --project <id>`, or the deploy ends with
   `404 Site Not Found`. The four existing sites (rules, news, dnd24-character-manager, omnisgm-table)
   are not affected.
3. **Reading a stand's Firestore goes through the Admin SDK with a service-account key**, never through
   the REST API or a browser: REST without an App Check token is 403, and a real browser trips
   "App attestation failed" after a few visits. `GOOGLE_APPLICATION_CREDENTIALS=<path> node script.mjs` with
   `firebase-admin/app` (`initializeApp`, `applicationDefault`) and `firebase-admin/firestore`; the key's
   contents are never read, printed or committed — only its path is used. Production is read only on the
   owner's direct request.
4. **A web API key in a `.env.staging` is not a secret**, but it is restricted in Google Cloud (websites +
   the five APIs the app uses); a key that stops working from a new origin is that restriction, not a leak.
