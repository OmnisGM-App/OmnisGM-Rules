# Server-side pieces: no open endpoints

Copy of the template from OmnisGM-App/claude-plugins/templates/server-side.md — edit there, roll out
as copies into repos with workers or functions (Table, News). Owner's decision 2026-10-05 (Table#149,
#787): the only threat to the free quotas is a script eating them, and an open URL on our domain that
sends mail is a mail cannon for someone else's inboxes.

1. **No HTTP endpoint that anyone can call.** No Cloudflare Worker route, Cloud Function or API path that
   takes a request from the public internet and does work on our behalf, even behind a Firebase ID token.
2. **The default shape is outbox + cron.** The client writes a document into a queue collection under the
   Firestore rules (the rules are the authorization); a Cloudflare Worker on a Cron Trigger reads the queue
   with a service account over Firestore REST (a JWT signed with WebCrypto — the Admin SDK does not run in
   Workers) and does the work. Abuse limits live inside the worker (per-user daily cap, de-duplication by
   target). Mail in Table is this shape (`mailQueue`, every 5 minutes).
3. **When a public receiver is unavoidable** (the Sentry tunnel: the DSN is in the bundle anyway), the
   protection goes into the first commit, not "later": one path, `POST` only, `Origin` check, our DSN only,
   body size cap; a Cloudflare Rate Limiting rule; an App Check token verified in the worker (Firebase JWKS,
   offline); per-key limits and spike protection on the receiving service.
4. **Propose it this way.** Any plan for a server-side piece names the outbox + cron variant first; an
   endpoint appears in a plan only with the list from rule 3 attached.
