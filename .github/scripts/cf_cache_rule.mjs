// Cache Rule для rules.omnisgm.com — issue #175. Кэширование HTML на эдже Cloudflare.
//
// Почему скриптом, а не руками в дашборде: правило — часть инфраструктуры деплоя, и через год
// «почему у нас HTML кэшируется» должно отвечать репо, а не память. Плюс dry-run показывает,
// что именно изменится, до того как это применится к проду.
//
// Токен нужен с правами Zone → Cache Rules: Edit (у purge-токена их может не быть — скрипт
// проверяет это отдельно и говорит прямо, а не падает с невнятной ошибкой).
//
//   node .github/scripts/cf_cache_rule.mjs            # показать текущее состояние (dry-run)
//   node .github/scripts/cf_cache_rule.mjs --apply    # создать/обновить правило
//
// Читает CF_API_TOKEN и CF_ZONE_ID из окружения.
const TOKEN = process.env.CF_API_TOKEN;
const ZONE = process.env.CF_ZONE_ID;
const APPLY = process.argv.includes('--apply');
const HOST = 'rules.omnisgm.com';
const PHASE = 'http_request_cache_settings';
// По описанию находим своё правило при повторном запуске — иначе каждый прогон плодил бы дубли.
const DESCRIPTION = `${HOST} — cache HTML (issue #175)`;

if (!TOKEN || !ZONE) {
  console.error('Нет CF_API_TOKEN / CF_ZONE_ID в окружении.');
  process.exit(2);
}

const api = async (path, init = {}) => {
  const res = await fetch(`https://api.cloudflare.com/client/v4${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
  });
  const body = await res.json().catch(() => ({}));
  return { status: res.status, body };
};

const errText = (body) =>
  (body?.errors ?? []).map((e) => `${e.code}: ${e.message}`).join('; ') || JSON.stringify(body);

// Само правило. Три вещи, каждая — с ценой ошибки:
//   • cache: true — собственно «кэшировать HTML» (по умолчанию Cloudflare этого не делает);
//   • edge/browser TTL = respect_origin — берём max-age от Firebase. НЕ фиксированный TTL:
//     sw.js и manifest.webmanifest отдаются с no-cache, и принудительный TTL закэшировал бы
//     их тоже. Ровно так у новостей умерли обновления PWA — CF держал годовалый sw.js;
//   • query_string.exclude — ключ кэша без query. Иначе каждая ссылка с utm-меткой заводит
//     свою запись, а purge по URL до этих вариантов не достаёт (ревью #192).
const rule = (queryStringExclude) => ({
  description: DESCRIPTION,
  expression: `(http.host eq "${HOST}")`,
  action: 'set_cache_settings',
  action_parameters: {
    cache: true,
    edge_ttl: { mode: 'respect_origin' },
    browser_ttl: { mode: 'respect_origin' },
    cache_key: { custom_key: { query_string: { exclude: queryStringExclude } } },
  },
  enabled: true,
});

// 1. Права токена — проверяем до всего остального, чтобы не гадать по 403 в середине.
const verify = await api('/user/tokens/verify');
if (verify.status !== 200) {
  console.error(`❌ Токен не прошёл проверку: ${errText(verify.body)}`);
  process.exit(1);
}
console.log('✔ Токен валиден');

// 2. Текущее состояние фазы Cache Rules.
const current = await api(`/zones/${ZONE}/rulesets/phases/${PHASE}/entrypoint`);
if (current.status === 403) {
  console.error(
    '❌ У токена нет доступа к Cache Rules (нужно право Zone → Cache Rules: Edit).\n' +
      '   Токен деплоя обычно умеет только Cache Purge — добавьте право или заведите отдельный токен.',
  );
  process.exit(1);
}
// 404 — фазы ещё нет, это нормально для зоны без единого Cache Rule.
const existing = current.status === 404 ? [] : (current.body?.result?.rules ?? []);
console.log(`Сейчас в фазе Cache Rules: ${existing.length} правил`);
for (const r of existing) {
  console.log(`  • ${r.description || '(без описания)'} — ${r.expression} [${r.enabled ? 'вкл' : 'выкл'}]`);
}

// 3. Page Rules — старый механизм, он ПЕРЕБИВАЕТ Cache Rules. Если там висит Bypass cache,
// новое правило будет создано и не сработает; лучше сказать об этом сразу.
const pr = await api(`/zones/${ZONE}/pagerules`);
if (pr.status === 200) {
  const bypass = (pr.body?.result ?? []).filter((p) =>
    (p.actions ?? []).some((a) => a.id === 'cache_level' && a.value === 'bypass'),
  );
  if (bypass.length) {
    console.log('::warning::Есть Page Rules с «Cache Level: Bypass» — они перебивают Cache Rules:');
    for (const p of bypass) console.log(`  • ${p.targets?.[0]?.constraint?.value}`);
  } else {
    console.log('✔ Page Rules с bypass не найдено');
  }
} else {
  console.log(`(Page Rules не проверены: HTTP ${pr.status} — нет прав, не критично)`);
}

const mine = existing.find((r) => r.description === DESCRIPTION);
console.log(mine ? '\nНаше правило уже есть — будет перезаписано.' : '\nНашего правила нет — будет добавлено.');

if (!APPLY) {
  console.log('\nDry-run. Что будет отправлено:');
  console.log(JSON.stringify(rule({ all: true }), null, 2));
  console.log('\nЗапустить с --apply, чтобы применить.');
  process.exit(0);
}

// 4. Применяем. PUT на entrypoint ЗАМЕНЯЕТ весь набор правил фазы, поэтому чужие правила
// переносим как есть — вместе с id, чтобы Cloudflare обновил их на месте, а не пересоздал
// с новыми идентификаторами (иначе в дашборде теряется история правила).
//
// Своё правило ставим ПЕРВЫМ. В фазе cache settings срабатывают ВСЕ совпавшие правила, и
// каждое следующее переопределяет предыдущее — то есть побеждает последнее. Наше правило
// самое общее (весь хост), поэтому оно должно стоять раньше: любое более специфичное
// правило, добавленное позже, окажется ниже и сможет его переопределить (ревью #193).
const others = existing.filter((r) => r.description !== DESCRIPTION).map((r) => ({
  ...(r.id ? { id: r.id } : {}),
  description: r.description,
  expression: r.expression,
  action: r.action,
  action_parameters: r.action_parameters,
  enabled: r.enabled,
}));

// Схема query_string.exclude у Cloudflare менялась: сейчас объект {all: true}, раньше строка "*".
// Пробуем актуальную, при ошибке валидации — старую, чтобы скрипт не зависел от даты.
for (const variant of [{ all: true }, '*']) {
  const res = await api(`/zones/${ZONE}/rulesets/phases/${PHASE}/entrypoint`, {
    method: 'PUT',
    body: JSON.stringify({ rules: [rule(variant), ...others] }),
  });
  if (res.status === 200) {
    const saved = (res.body?.result?.rules ?? []).find((r) => r.description === DESCRIPTION);
    console.log(`✔ Правило применено (exclude=${JSON.stringify(variant)}), id=${saved?.id ?? '?'}`);
    console.log(`  правил в фазе: ${res.body?.result?.rules?.length}`);
    console.log('\nТеперь проверить: bash web/scripts/check_edge_cache.sh');
    process.exit(0);
  }
  console.log(`Вариант exclude=${JSON.stringify(variant)} не принят (HTTP ${res.status}): ${errText(res.body)}`);
}
console.error('❌ Не удалось применить правило ни одним вариантом схемы.');
process.exit(1);
