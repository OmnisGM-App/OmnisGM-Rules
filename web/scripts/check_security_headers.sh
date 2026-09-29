#!/usr/bin/env bash
# Проверка security-заголовков на rules.omnisgm.com — issue #218.
#   bash web/scripts/check_security_headers.sh                 # прод
#   bash web/scripts/check_security_headers.sh http://127.0.0.1:5002   # эмулятор Firebase
#
# Заголовки — в `firebase.json` (правило `**` первым; Firebase мержит правила по ключам), не в CF.
# HSTS без preload: preload — решение уровня апекса omnisgm.com (#218). CSP — enforce (#225).
set -u
BASE="${1:-https://rules.omnisgm.com}"

# HSTS у *.web.app свой, от Firebase, и наше правило там не видно: по origin (#227) сверяем
# только форму заголовка — пропавший или обнулённый HSTS ловится, значение не наше.
case "$BASE" in
  *.web.app*) HSTS_WANT="max-age=[0-9]+; includeSubDomains" ;;
  *)          HSTS_WANT="max-age=31536000; includeSubDomains" ;;
esac

EXPECT_NAMES=(
  "x-content-type-options"
  "referrer-policy"
  "x-frame-options"
  "strict-transport-security"
  "content-security-policy"
)
EXPECT_VALUES=(
  "^nosniff$"
  "^strict-origin-when-cross-origin$"
  "^SAMEORIGIN$"
  "$HSTS_WANT"
  "default-src 'self'"
)

header() {  # $1 — путь, $2 — имя заголовка
  curl -sSI "$BASE$1" | tr -d '\r' | awk -F': ' -v n="$2" 'tolower($1)==n{sub(/^[^:]*: /,""); print; exit}'
}

fail=0
check_page() {  # $1 — путь
  local path="$1"
  echo "  $path"
  for i in "${!EXPECT_NAMES[@]}"; do
    local name="${EXPECT_NAMES[$i]}" want="${EXPECT_VALUES[$i]}"
    local got=""
    got="$(header "$path" "$name")"
    if [ -z "$got" ]; then
      echo "    ✘ $name — отсутствует"; fail=1
    elif ! printf '%s' "$got" | grep -qE "$want"; then
      echo "    ✘ $name — «${got}» (ожидали /$want/)"; fail=1
    else
      echo "    ✔ $name"
    fi
  done
}

echo "Security-заголовки $BASE"
check_page "/ru/"
check_page "/en/dnd/srd-5.2/spells/fireball/"

# Точечные Cache-Control обязаны пережить глобальное правило: иначе картинки и sw.js залипнут.
echo "  кэш-политика не потерялась:"
for p in "/img/dnd/creatures/aboleth.webp" "/sw.js"; do
  cc="$(header "$p" "cache-control")"
  nosniff="$(header "$p" "x-content-type-options")"
  if printf '%s' "$cc" | grep -q "no-cache"; then echo "    ✔ $p — Cache-Control: $cc"
  else echo "    ✘ $p — Cache-Control «${cc}», ожидали no-cache"; fail=1; fi
  [ -n "$nosniff" ] || echo "    ⚠ $p — без security-заголовков (мерж правил не сработал; кэш при этом цел)"
done

[ "$fail" -eq 0 ] && echo "Итог: заголовки на месте." || echo "Итог: есть расхождения — см. ✘ выше."
exit "$fail"
