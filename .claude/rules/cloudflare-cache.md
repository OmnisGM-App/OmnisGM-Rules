---
paths:
  - "firebase.json"
  - ".github/workflows/deploy.yml"
---

# Cloudflare: a headers-only change does not land without a zone purge (#227)

The build diff (which drives the purge list and IndexNow streaming) computes a signature of the
page's **content**. Editing `firebase.json` does not change page bodies → the list is empty →
nothing to purge, and when the TTL expires Cloudflare revalidates the entry by ETag, gets `304`
and **keeps the previously stored headers**, resetting the entry's age. "Wait for the TTL" does not
help: a hot page keeps the old set indefinitely (caught on #218 — part of prod
had security headers, part did not). That is why the "Purge Cloudflare cache" step in `deploy.yml`
purges the **whole zone** if `firebase.json` changed in the commit range being deployed
(or manually — `workflow_dispatch` with `purge_all`). The price: the zone is one for all of `omnisgm.com`,
so News and Table get re-warmed too; header edits are rare, and a partial prod state is worse.

The same gives the checking rule: **after a release, check meta, schema and headers by origin**
`omnisgm-rules.web.app`, not by `rules.omnisgm.com` — otherwise the validator (Rich Results Test,
`check_security_headers.sh`) reads the copy stuck at CF and gives a false negative.
