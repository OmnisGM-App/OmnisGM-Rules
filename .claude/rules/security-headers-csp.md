---
paths:
  - "firebase.json"
  - "web/scripts/check_security_headers.sh"
  - "web/scripts/check_csp.mjs"
  - "web/e2e/csp.spec.ts"
---

# Security-заголовки и CSP (#218, #225)

`X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`, HSTS и CSP
ставятся в `firebase.json` — правило `hosting.headers` с `source: "**"`, первым в списке, а НЕ
в Cloudflare Transform Rules: конфиг в репозитории виден в ревью и едет вместе с деплоем.
Firebase мержит правила по ключам, поэтому точечные `Cache-Control` (`/img/**`, `sw.js`) живы —
это и проверяет `bash web/scripts/check_security_headers.sh` (без аргумента — прод, с URL —
эмулятор). HSTS без `preload`: список принимает апекс `omnisgm.com` и накрывает ВСЕ поддомены,
так что preload — отдельное решение владельца на лендинге, не отсюда.

**CSP в enforce с #225.** Инвентаризация источников — `node web/scripts/check_csp.mjs` (без
аргумента — по проду, с URL — по локальной сборке, политика подставляется из `firebase.json`).
Гонять надо ИМЕННО по проду: Cloudflare вставляет в HTML свой beacon
(`static.cloudflareinsights.com`) на эдже, в origin-ответе его нет, а локально ещё и не
грузится аналитика (нет `PUBLIC_*` ID в `.env`). И главное про метод: **нарушения CSP пишет
сам браузер, через API чтения консоли они не видны** — ловить надо событие
`securitypolicyviolation`, слушателем, поставленным до скриптов страницы. Регрессию держит
`web/e2e/csp.spec.ts` (политика из `firebase.json` подставляется в ответы preview).

**Динамические теги гейт не ловит.** e2e видит только то, что лежит в нашем бандле, а
`report-to`/`report-uri` в политике нет — значит нарушение на проде происходит МОЛЧА (тег не
работает, в консоли пользователя ошибка, у нас ни звука). Поэтому правило: **добавил тег
в GTM, включил новый режим Метрики или подключил внешний сервис — прогони
`node web/scripts/check_csp.mjs` по проду.** Минута работы против «аналитика молчит, и никто
не знает почему».
