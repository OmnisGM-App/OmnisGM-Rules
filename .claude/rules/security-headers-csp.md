---
paths:
  - "firebase.json"
  - "web/scripts/check_security_headers.sh"
  - "web/scripts/check_csp.mjs"
  - "web/e2e/csp.spec.ts"
  - "web/scripts/test_csp_policy.mjs"
---

# Security headers and CSP (#218, #225)

`X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`, HSTS and CSP
are set in `firebase.json` — a `hosting.headers` rule with `source: "**"`, first in the list, and NOT
in Cloudflare Transform Rules: config in the repository is visible in review and ships with the deploy.
Firebase merges rules by key, so the targeted `Cache-Control` entries (`/img/**`, `sw.js`) stay alive —
that is what `bash web/scripts/check_security_headers.sh` checks (no argument — prod, with a URL —
the emulator). HSTS without `preload`: the list accepts the apex `omnisgm.com` and covers ALL subdomains,
so preload is a separate owner decision on the landing site, not from here.

**CSP is in enforce since #225.** Source inventory — `node web/scripts/check_csp.mjs` (no
argument — against prod, with a URL — against a local build, the policy is taken from `firebase.json`).
It must be run against prod SPECIFICALLY: Cloudflare injects its own beacon into the HTML
(`static.cloudflareinsights.com`) at the edge, the origin response does not have it, and locally the
analytics does not even load (no `PUBLIC_*` IDs in `.env`). And the main thing about the method: **CSP violations are logged by
the browser itself, they are not visible through the console-reading API** — you must catch the
`securitypolicyviolation` event with a listener installed before the page scripts. The regression is held by
`web/e2e/csp.spec.ts` (the policy from `firebase.json` is injected into preview responses).

**The run's verdict is incomplete by construction (#325).** "No violations" means "none from the sources
that were live IN THIS run". A tracker that did not load produces no violations — and
that is exactly how the hole went unseen since 01.09: on the owner's machine the connection to `mc.yandex.ru` is cut by
the ad blocker (`ERR_CONNECTION_REFUSED`), Yandex Metrica does not start, the run is green. Now the script itself
checks that GA4 and Metrica responded, prints what the verdict does not cover, and on the prod run
in CI goes red; `static.cloudflareinsights.com` is not covered there either — the beacon is injected by
Cloudflare itself, that is the state of the CF dashboard, not of the repository.

**Pairing of Metrica hosts — the permanent gate `node web/scripts/test_csp_policy.mjs`.** Metrica
loads `tag.js` from `mc.yandex.ru`, and sends hits to a host that `tag.js` itself picks by the visitor's
region: for foreign visitors — **`mc.yandex.com`**. That host is nowhere in our code, it cannot be derived
from the sources — so the required sources are listed in the gate explicitly (`METRIKA`):
`script-src`, `img-src`, `connect-src` (and `wss://` — Webvisor), `frame-src`. The rule reads
like this: **any Metrica host in the policy exists only as a `.ru` + `.com` pair.** The gate also keeps the
policy in `enforce`, forbids duplicate directives (the browser applies the first copy) and checks the
script hosts from client code against `script-src`.

**The gate does not catch dynamic tags.** e2e sees only what is in our bundle, and
there is no `report-to`/`report-uri` in the policy — so a violation in prod happens SILENTLY (the tag does not
work, an error in the user's console, not a sound on our side). Hence the rule: **added a tag
in GTM, enabled a new Metrica mode or connected an external service — run
`node web/scripts/check_csp.mjs` against prod AND make sure the output has no warning about
unloaded analytics.** Without that second half the run proves exactly nothing — on a
machine with an ad blocker it is always green (#325).
