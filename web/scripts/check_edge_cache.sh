#!/usr/bin/env bash
# Проверка edge-кэша Cloudflare на rules.omnisgm.com — issue #175.
#
# Cache Rule включается руками в дашборде Cloudflare (API-токен деплоя умеет только purge),
# поэтому проверка отдельная и ручная: запусти после включения правила и после деплоя.
#
#   bash web/scripts/check_edge_cache.sh
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
