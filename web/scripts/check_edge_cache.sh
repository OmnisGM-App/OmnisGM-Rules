#!/usr/bin/env bash
# Проверка edge-кэша Cloudflare на rules.omnisgm.com — issue #175.
#
#   bash web/scripts/check_edge_cache.sh
#
# ── Что настроено на стороне Cloudflare (применено 2026-08-13, ruleset-правило
#    id=024fc569b4a6436385e67ed5bf1a69d5, зона omnisgm.com, фаза http_request_cache_settings):
#
#      description:  "rules.omnisgm.com — cache HTML (issue #175)"
#      expression:   (http.host eq "rules.omnisgm.com")
#      action:       set_cache_settings
#      parameters:   cache=true
#                    edge_ttl    = respect_origin
#                    browser_ttl = respect_origin
#                    cache_key.custom_key.query_string.exclude = {all: true}
#
#    Почему так, чтобы не переоткрывать вопрос:
#      • cache=true — Cloudflare по умолчанию HTML не кэширует (был cf-cache-status: DYNAMIC),
#        а весь смысл затеи — снять egress с Firebase и отдавать страницы с эджа;
#      • respect_origin, а НЕ фиксированный TTL: Firebase отдаёт страницам max-age=3600,
#        а sw.js и manifest.webmanifest — no-cache. Принудительный TTL закэшировал бы и их;
#        именно так у новостей умерли обновления PWA — CF держал годовалый sw.js;
#      • ключ кэша без query-строки: иначе каждая ссылка с utm/fbclid заводит отдельную
#        запись, до которой purge по URL из deploy.yml не достаёт. В коде сайта query нигде
#        не читается (ни location.search, ни searchParams), так что терять нечего.
#
#    Восстановить правило, если его снесут (нужен токен с Zone → Cache Rules: Edit):
#      curl -X PUT "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/rulesets/phases/http_request_cache_settings/entrypoint" \
#        -H "Authorization: Bearer $CF_API_TOKEN" -H "Content-Type: application/json" \
#        --data '{"rules":[{"description":"rules.omnisgm.com — cache HTML (issue #175)","expression":"(http.host eq \"rules.omnisgm.com\")","action":"set_cache_settings","action_parameters":{"cache":true,"edge_ttl":{"mode":"respect_origin"},"browser_ttl":{"mode":"respect_origin"},"cache_key":{"custom_key":{"query_string":{"exclude":{"all":true}}}}},"enabled":true}]}'
#    ⚠️ PUT заменяет ВСЕ правила фазы — сначала прочитать текущие тем же URL через GET.
#
# Что должно получиться:
#   • HTML-страницы и JSON API — HIT со второго запроса (кэшируются на эдже, egress не тратится);
#   • sw.js и manifest.webmanifest — НЕ HIT никогда: origin отдаёт им no-cache, и правило обязано
#     это уважать. Ровно на этом обжигались новости: CF закэшировал sw.js, и PWA-обновления
#     переставали доходить до пользователей (см. omnisgm-news, Cloudflare-кэш).
set -u
BASE="${1:-https://rules.omnisgm.com}"

status() {  # $1 — путь; печатает cf-cache-status
  curl -sSI "$BASE$1" | tr -d '\r' | awk -F': ' 'tolower($1)=="cf-cache-status"{print $2}'
}

fail=0
check() {  # $1 — путь, $2 — «cacheable» | «bypass»
  local path="$1" want="$2"
  status "$path" > /dev/null          # первый запрос — прогрев (MISS)
  local st; st=$(status "$path")
  case "$want" in
    cacheable)
      if [ "$st" = "HIT" ]; then echo "  ✔ $path — $st"
      else echo "  ✘ $path — $st (ожидался HIT: правило не кэширует этот тип)"; fail=1; fi ;;
    bypass)
      if [ "$st" = "HIT" ]; then echo "  ✘ $path — HIT (origin отдаёт no-cache, кэшировать нельзя)"; fail=1
      else echo "  ✔ $path — $st"; fi ;;
  esac
}

echo "Edge-кэш $BASE"
echo "Должны кэшироваться:"
check "/ru/" cacheable
check "/ru/dnd/srd-5.2/classes/rogue/" cacheable
check "/api/" cacheable
echo "Не должны кэшироваться (no-cache от origin):"
check "/sw.js" bypass
check "/manifest.webmanifest" bypass

[ "$fail" -eq 0 ] && echo "Итог: edge-кэш настроен верно." || echo "Итог: есть расхождения — см. ✘ выше."
exit "$fail"
