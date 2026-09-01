#!/usr/bin/env bash
# Проверка security-заголовков на rules.omnisgm.com — issue #218.
#
#   bash web/scripts/check_security_headers.sh                 # прод
#   bash web/scripts/check_security_headers.sh http://127.0.0.1:5002   # эмулятор Firebase
#
# ── Где заголовки настроены
# В `firebase.json` (`hosting.headers`, правило `source: "**"`), а НЕ в Cloudflare Transform
# Rules: конфиг в репозитории виден в ревью, едет вместе с деплоем и не требует токена зоны.
# Правило `**` стоит ПЕРВЫМ, дальше идут точечные правила Cache-Control (/img/**, /_astro/**,
# sw.js). Firebase применяет все подходящие правила и мержит их по ключам — проверено на
# эмуляторе: /img/ отдаёт и security-заголовки, и свой `Cache-Control: no-cache`. Порядок
# именно такой на случай, если поведение когда-нибудь станет «последнее правило побеждает
# целиком»: тогда пострадают security-заголовки на статике, а не кэш-политика (её ломать
# нельзя — на no-cache для /img/ и sw.js завязаны обновления картинок и PWA, см. #202/#175).
#
# ── Про HSTS
# `max-age=31536000; includeSubDomains`, БЕЗ preload. includeSubDomains здесь накрывает только
# поддомены rules.omnisgm.com (их нет) — соседние news/table это НЕ трогает, они сиблинги.
# А preload — решение уровня апекса: список принимает домен omnisgm.com, и он накроет ВСЕ
# поддомены разом и откатывается месяцами. Ставить его нужно на лендинге и отдельным решением
# владельца, отсюда это сделать нельзя (см. #218).
#
# ── Про CSP
# Сейчас Report-Only: политика собрана из того, что страницы реально грузят (свои бандлы и
# инлайновые модули Astro, шрифты, Pagefind с воркером и wasm, GA4 и Метрика). Инлайн-скриптов
# у Astro много и хэши менялись бы каждый билд — поэтому `'unsafe-inline'`; смысл политики в
# том, чтобы запретить ЧУЖИЕ источники, а не инлайн. Перевод в enforce — отдельным шагом,
# после того как прод в Report-Only отмолчится (проверять в devtools на страницах разных
# типов: глава, сущность, поиск, оффлайн-PWA).
set -u
BASE="${1:-https://rules.omnisgm.com}"

# Ожидаемые заголовки: имя → регексп значения.
EXPECT_NAMES=(
  "x-content-type-options"
  "referrer-policy"
  "x-frame-options"
  "strict-transport-security"
  "content-security-policy-report-only"
)
EXPECT_VALUES=(
  "^nosniff$"
  "^strict-origin-when-cross-origin$"
  "^SAMEORIGIN$"
  "max-age=31536000; includeSubDomains"
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

# Точечные правила Cache-Control обязаны пережить глобальное правило: если мерж когда-нибудь
# сломается, картинки и sw.js залипнут в кэше, а это дороже самих заголовков.
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
