#!/usr/bin/env bash
# Проверка edge-кэша Cloudflare на rules.omnisgm.com — issue #175.
# ── Что настроено на стороне Cloudflare (применено 2026-08-13, ruleset-правило
#    id=024fc569b4a6436385e67ed5bf1a69d5, зона omnisgm.com, фаза http_request_cache_settings):
#    respect_origin, а НЕ фиксированный TTL: иначе закэшируется no-cache sw.js (так у News умерли
#    обновления PWA). Ключ без query: иначе utm/fbclid плодят записи, до которых purge по URL не достаёт.
#
#    Восстановить правило, если его снесут (нужен токен с Zone → Cache Rules: Edit):
#      curl -X PUT "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/rulesets/phases/http_request_cache_settings/entrypoint" \
#        -H "Authorization: Bearer $CF_API_TOKEN" -H "Content-Type: application/json" \
#        --data '{"rules":[{"description":"rules.omnisgm.com — cache HTML (issue #175)","expression":"(http.host eq \"rules.omnisgm.com\")","action":"set_cache_settings","action_parameters":{"cache":true,"edge_ttl":{"mode":"respect_origin"},"browser_ttl":{"mode":"respect_origin"},"cache_key":{"custom_key":{"query_string":{"exclude":{"all":true}}}}},"enabled":true}]}'
#    ⚠️ PUT заменяет ВСЕ правила фазы — сначала прочитать текущие тем же URL через GET.
set -u
BASE="${1:-https://rules.omnisgm.com}"

status() {  # $1 — путь; печатает cf-cache-status
  curl -sSI "$BASE$1" | tr -d '\r' | awk -F': ' 'tolower($1)=="cf-cache-status"{print $2}'
}

fail=0
# Для «cacheable» проходом считается только HIT, но не с первого раза: REVALIDATED значит, что истёк
# max-age и edge переспросил origin (следующий запрос на тот же PoP — уже HIT), а MISS после прогрева
# бывает, когда запросы с раннера попадают на разные PoP Cloudflare. Поэтому до ATTEMPTS попыток с паузой
# PAUSE секунд (ложный красный Health check 2026-10-13, run 38406564551). no-cache-объект HIT не даст
# никогда (замер: EXPIRED), так что подмену правила проверка по-прежнему ловит.
ATTEMPTS="${ATTEMPTS:-3}"
PAUSE="${PAUSE:-2}"
check() {  # $1 — путь, $2 — «cacheable» | «bypass»
  local path="$1" want="$2"
  status "$path" > /dev/null          # первый запрос — прогрев (MISS)
  local st; st=$(status "$path")
  case "$want" in
    cacheable)
      local i=1
      while [ "$st" != "HIT" ] && [ "$i" -lt "$ATTEMPTS" ]; do
        i=$((i+1)); sleep "$PAUSE"; st=$(status "$path")
      done
      if [ "$st" = "HIT" ]; then echo "  ✔ $path — $st"
      else echo "  ✘ $path — $st после $i попыток (ожидался HIT: правило не кэширует этот тип)"; fail=1; fi ;;
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
