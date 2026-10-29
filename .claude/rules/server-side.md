# Server-side pieces: no open endpoints

Copy of the template from OmnisGM-App/claude-plugins/templates/server-side.md — edit there, roll out
as copies into repos with workers or functions (Table, News). Owner's decision 2026-10-05 (Table#149,
#787): the only threat to the free quotas is a script eating them, and an open URL on our domain that
sends mail is a mail cannon for someone else's inboxes. Revised 2026-10-29 (owner): the hard ban held while
everything had to fit the free plan; an endpoint is now the owner's call, one endpoint at a time.

1. **No HTTP endpoint without the owner's word.** A Cloudflare Worker route, an HTTP or callable Cloud
   Function, any API path that takes a request from the public internet — even behind a Firebase ID token —
   is proposed to the owner only when no other shape works (rule 2) or the gain is large, and lands only on
   the owner's explicit approval of that one endpoint, with rule 3's protections. A Firestore-triggered or scheduled
   function is not an endpoint.
2. **The default shape is outbox + cron.** The client writes a document into a queue collection under the
   Firestore rules (the rules are the authorization); a Cloudflare Worker on a Cron Trigger reads the queue
   with a service account over Firestore REST (a JWT signed with WebCrypto — the Admin SDK does not run in
   Workers) and does the work. Abuse limits live inside the worker (per-user daily cap, de-duplication by
   target). Mail in Table is this shape (`mailQueue`, every 5 minutes). On Blaze a Firestore-triggered or
   scheduled Cloud Function with the Admin SDK is the same shape, with `maxInstances` set on the function and a
   budget alert on the project: a trigger fires on every queued write, a script can flood the queue.
3. **Every approved public receiver** gets its protection in the first commit, not "later":
   - a Cloudflare Worker route (the Sentry tunnel: the DSN is in the bundle anyway): one path, `POST` only,
     `Origin` check, an allow-list of what it forwards (our DSN only), body size cap; a Cloudflare Rate Limiting
     rule; an App Check token verified in the worker (Firebase JWKS, offline); per-key limits and spike
     protection on the receiving service;
   - an HTTP or callable Cloud Function: `enforceAppCheck`, the caller's auth checked, body size cap, a per-uid
     limit inside the function, `maxInstances`, a budget alert on the project.
4. **Propose it this way.** Any plan for a server-side piece names the outbox + cron or trigger variant first;
   an endpoint appears in a plan only with the reason it is needed — the other shapes do not work, or the gain
   over them — the list from rule 3 attached, and a question to the owner.
