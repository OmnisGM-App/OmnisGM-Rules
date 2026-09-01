# OmnisGM Rules — rules.omnisgm.com

> Ридер SRD настольных игр (D&D 5.2.1/5.1, Daggerheart 1.0, BRP 1.0) — **продукт экосистемы OmnisGM**.
> Этот файл состоит из двух частей: **(A)** контекст продукта/стека/инфраструктуры OmnisGM (ниже) и
> **(B)** документация контентного пайплайна импорта/перевода (исходный `TTRPG SRD — импорт и перевод`,
> сохранён без изменений). Старт переноса в экосистему — 2026-06-29.

## A. Продукт и экосистема OmnisGM

### Расстановка продуктов
- **Основной** — интерактивный лист персонажа.
- **Доп** — новости (The Guild Herald, news.omnisgm.com; отдельное репо `OmnisGM-News`).
- **Этот** — правила/SRD (`rules.omnisgm.com`).

### Главная цель — SEO-воронка в основной продукт
Человек гуглит уточнение по правилу → попадает на нашу **статичную** страницу правил → CTA уводит его
в интерактивный лист персонажа. Поэтому **SEO критичен** и контент **обязан рендериться в статический HTML**
(НЕ client-rendered SPA — именно client-render убил SEO новостям: краулер видит пустой `<div id=root>`).

### Стек публикации — Astro (SSG) ⚠️ заменяет MkDocs
Раздел B ниже описывает **прежний** способ публикации (MkDocs Material + GitHub Pages, `pages.yml`,
`src/site/`, `prepare_docs.sh`). Он **выводится из эксплуатации** и заменяется на **Astro (SSG)**.
Контентный пайплайн импорта/перевода (раздел B, скиллы/правила в `.claude/`) — **НЕ трогаем**, он
просто производит `.md`, которые потребляет любой движок.

Почему Astro, а не MkDocs: (1) дизайнер отдал готовые **React-компоненты**; (2) **PWA обязателен**
(first-class `@vite-pwa/astro` против ручного болта в MkDocs); (3) единый React-стек с экосистемой.
Astro статичен по умолчанию (zero-JS HTML) → SEO целы; риск «React убьёт SEO» снят, т.к. рендер на билде.

- **Раскладка:** Astro-приложение в отдельной папке **`web/`**. `src/` репо — это Markdown-контент
  (`src/{game}/{version}/{en,ru}/*.md`), вход контентного пайплайна — **не трогать**. Content collections
  Astro ссылаются на `src/{game}/...md`. Динамические роуты `/{lang}/{game}/{version}/{...slug}` через
  `getStaticPaths` (статика). Markdown рендерится **на билде**, не в браузере.
- **Интеграции:** `@astrojs/react` (компоненты дизайнера как islands), `@vite-pwa/astro` (PWA — обязателен),
  **Pagefind** (статический поиск). i18n EN/RU + hreflang, sitemap, JSON-LD.
- **SEO-воронка:** CTA-блок «в лист персонажа» на каждой странице; событие Analytics на клик CTA.

### Дизайн
claude.ai/design проект `28349954-9a6f-47fd-a34d-406e6775544e` (тот же, где Gazette новостей).
Читается через DesignSync (`get_file`). Файлы: `Rules.html` (обёртка-превью вьюпортов),
**`rules-docs.jsx` — компонент `RulesDocsApp`, реальный UI**; `rules-docs.css`; `rules-docs-data.jsx`;
общий `omnis-site.css` + `site-shell.jsx` (`OmnisSeal`, токены `C`). Скин ридера: топбар (печать OmnisGM +
«OmnisGM / rules», поиск-типахед, GitHub, ENG/RU, бургер) → вкладки систем → слева nav-дерево, центр
Markdown, справа TOC «На этой странице» → prev/next, строка «Источник», мобильный drawer.

### Инфраструктура
- **Репо:** `OmnisGM-App/OmnisGM-Rules`. Локально склонирован `/Users/petrradilov/Documents/OmnisGM/OmnisGM-Rules`
  рядом с `OmnisGM News`.
- **Firebase:** ОТДЕЛЬНЫЙ проект **`omnisgm-rules`** (не `omnisgm-news`). Hosting + домен `rules.omnisgm.com`
  (DNS владелец настроит после поднятия хостинга).
- **Секреты/переменные репо:** `FIREBASE_SERVICE_ACCOUNT` (secret, SA-ключ деплоя — ставить `gh secret set < файл`
  НЕ читая). Клиентский `firebaseConfig` — 7 публичных значений в **repo variables** `VITE_FIREBASE_*`
  (variables, НЕ secrets — web apiKey не credential).
- **Analytics:** подключаем (`measurementId G-RRH57ELLZS`) — мерить трафик + конверсию CTA-воронки.
  В Astro — отдельный client-island, не влияет на статический HTML / SEO.
- **Деплой:** заменить `pages.yml` (GitHub Pages) на `astro build` + `firebase deploy --only hosting`
  (проект `omnisgm-rules`). JSON API (`generate_api.py`) и release-воркфлоу — решить отдельно при сборке.

### Даты контента для JSON-LD (#219)
`datePublished`/`dateModified` у `Article` берутся из **истории git** по исходному markdown:
`web/scripts/gen-content-dates.mjs` (prebuild) делает один проход `git log --name-only` по `src/`
и пишет карту в `web/src/data/content-dates.json` (gitignored), а `web/src/lib/content-dates.mjs`
отдаёт даты странице. Сущностная страница знает свой ресурс и передаёт `contentSource` в
`ReaderShell`; какие `.md` стоят за ресурсом — говорит `_sources.json` от парсера
(`generate_api.py --emit-sources`), чтобы это знание не дублировалось в JS.

**Мелкий клон дат не даёт.** `actions/checkout` без `fetch-depth: 0` не привозит историю, и
страницы остаются БЕЗ дат — намеренно: дата билда на 6000 страницах означала бы «всё обновилось
разом». Поэтому в `ci.yml` и `deploy.yml` стоит `fetch-depth: 0` + `filter: blob:none`, а гейт
`verify_dist_meta_budget.mjs` валит сборку, если Article остался без обязательных полей.

### lastmod в sitemap (#221)
Проставляется postbuild-скриптом `web/scripts/add_sitemap_lastmod.mjs`: он читает `dateModified`
из JSON-LD уже собранных страниц (#219) и вписывает `<lastmod>` в `dist/sitemap-N.xml`. Так
маршрутизация и карта «URL → исходный файл» нигде не дублируются — sitemap и разметка страницы
согласованы по построению. Скрипт идемпотентен и валит сборку, если дат нет вовсе или они
пропали больше чем у 1% URL (без даты законно только языковые хабы — у них нет `Article`).

### Хлебные крошки (#220)
Разметка `BreadcrumbList` и видимая строка `.rd-crumb` строятся из ОДНОГО массива в
`web/src/components/ReaderShell.astro` — у Google требование «разметка описывает видимое».
Уровни берутся из NAV-дерева не один-в-один: игра и редакция схлопнуты в одну крошку документа
(ссылка — первая содержательная страница редакции, Legal пропускается), а группа без собственной
страницы («Классы», «Глоссарий») остаётся видимым текстом, но в разметку не идёт — иначе ей
подставляется «первая страница-лист внутри», а это и давало дубли URL и ссылку на варвара.
Сущностные страницы дописывают себя последним уровнем (их `currentId` — глава-родитель).
Держат: гейты в `verify_dist_meta_budget.mjs` (дублей URL в трейле 0, ссылок в никуда 0) и
`web/e2e/seo-breadcrumbs.spec.ts`. Настоящие хабы документов — #230; когда приедут, меняется
только `docEntry`.

### Security-заголовки (#218)
`X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`, HSTS и CSP (пока Report-Only)
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

### Cloudflare: правка только заголовков не доезжает без сброса зоны (#227)
Дифф сборки (по нему строится purge-список и стриминг IndexNow) считает сигнатуру
**содержимого** страницы. Правка `firebase.json` тела страниц не меняет → список пуст →
чистить нечего, а Cloudflare при истечении TTL ревалидирует запись по ETag, получает `304`
и **оставляет ранее сохранённые заголовки**, сбрасывая возраст записи. «Подождать TTL» не
помогает: горячая страница держит старый набор сколько угодно (поймано на #218 — часть прода
была с security-заголовками, часть без). Поэтому шаг «Purge Cloudflare cache» в `deploy.yml`
сбрасывает **зону целиком**, если в деплоящемся диапазоне коммитов менялся `firebase.json`
(или вручную — `workflow_dispatch` с `purge_all`). Цена: зона одна на весь `omnisgm.com`,
заодно прогреются News и Table; правка заголовков редка, а частичное состояние прода хуже.

Отсюда же правило проверок: **мету, схему и заголовки после релиза проверять по origin**
`omnisgm-rules.web.app`, а не по `rules.omnisgm.com` — иначе валидатор (Rich Results Test,
`check_security_headers.sh`) читает застрявшую у CF копию и даёт ложный минус.

### Картинки сущностей и генератор (#201, #202)
Портреты существ и иконки заклинаний/магпредметов лежат в репо статикой (`web/public/img/{game}/{kind}/`),
показываются на странице сущности и уходят в поле `image` JSON API. Формат и раскладка —
`documentation/entity-images.md`, промты — `documentation/image-prompts.md`. Генератор: `scripts/gen-images.mjs`
+ `.github/workflows/gen-images.yml` (codex на подписке, очередь от данных Rules, ветка `images-queue`
→ draft-PR без автомёржа).

**Ранбук токена codex.** Держателей токена **двое** — CI News и CI Rules, оба от одного
локального `~/.codex/auth.json`. (Третьим был CI Table, пока там жил свой генератор портретов;
он снесён вместе с ним — Table#403.) Прогон падает с `refresh_token_reused` / `token_revoked` /
`401` — значит локальный перелогин обесценил токен в CI. Починка: `codex login` локально,
затем обновить секрет в ОБОИХ репозиториях:

```bash
for r in OmnisGM-App/OmnisGM-News OmnisGM-App/OmnisGM-Rules; do
  gh secret set CODEX_AUTH_JSON --repo $r < ~/.codex/auth.json
done
```

Значение секрета не читать и не печатать — только перенаправлением из файла.

### План сборки (статус 2026-06-29)
Первый шаг (согласован): каркас Astro в `web/` на ветке + **вертикальный срез D&D SRD 5.2** от и до
(скин дизайнера, реальный рендер MD, PWA, поиск) → визуальная сверка с дизайном → масштаб на 5.1/Daggerheart/BRP.

### Стиль работы владельца
Инкрементально, ревьюит каждый шаг; деплой/пуш — по явной просьбе; **«аудит ≠ фиксы»** (на «проверь/убедись»
сначала репорт, код не менять, пока не скажет «делай»); предпочитает обобщённые модели данных.

---

# B. TTRPG SRD — импорт и перевод (контентный пайплайн)

Проект для импорта, перевода и публикации SRD (System Reference Document) настольных ролевых игр.

## Структура проекта

```
src/{game}/{version}/en/       — EN оригинал (markdown)
src/{game}/{version}/ru/       — RU перевод
src/{game}/{version}/ru/*_Glossary/  — глоссарий (словарь терминов)
src/{game}/translate/          — словари и логи (logs/, 01_dictionary_base, ...)
src/translate/                 — общие переводческие артефакты (все системы)
src/site/                      — исходники сайта (index, assets, mkdocs.yml, overrides)
.github/scripts/               — скрипты сборки и генерации
.github/workflows/             — CI/CD workflows

{version} — идентификатор документа, не обязательно версия: srd-5.2, srd-1.0, kobold-toe и т.д.
```

При сборке (`prepare_docs.sh` или CI) `mkdocs.yml` и `overrides/` копируются из `src/site/` в корень.

Игры: `dnd` (D&D 5.1, 5.2), `daggerheart` (SRD 1.0), `brp` (BRP SRD 1.0).

## Скиллы (slash-команды)

### Импорт PDF → markdown

| Команда | Описание |
|---|---|
| `/import-srd` | Оркестратор полного пайплайна: convert → cleanup → verify → integrate |
| `/convert-pdf` | Конвертация PDF тремя инструментами (marker + pymupdf4llm + docling) |
| `/cleanup-artifacts` | Сведение результатов конвертеров + разбивка на файлы + чистка артефактов |
| `/verify-import` | Верификация полноты импорта — циклическая сверка markdown с PDF |

### Перевод EN → RU

| Команда | Описание |
|---|---|
| `/translate-srd` | Оркестратор полного пайплайна: глоссарий → перевод → верификация → интеграция |
| `/build-glossary` | Создание EN глоссария из исходников SRD |
| `/translate-glossary` | Перевод EN глоссария в RU (с сохранением оригинальных EN имён) |
| `/translate-verify` | Верификация RU глоссария командой из 3 агентов (минимум 3 раунда) |
| `/translate-content` | Перевод контентных файлов строго по глоссарию |
| `/verify-content` | Верификация перевода: весь перевод (3 агента) или одна страница (1 агент) |

### Утилиты

| Команда | Описание |
|---|---|
| `/validate-markdown` | Валидация структуры markdown: таблицы, заголовки, списки, форматирование, парная проверка EN↔RU |

### Интеграция в сайт

| Команда | Описание |
|---|---|
| `/integrate-srd` | Интеграция: prepare_docs.sh, pages.yml, mkdocs.yml nav, release workflow + tag |

## Правила (rules)

Автоматически подключаются по `paths:` при работе с соответствующими файлами.

### Импорт

| Правило | Описание | Подключается к |
|---|---|---|
| `file-naming-conventions.md` | Соглашения об именовании файлов и директорий | `src/**`, cleanup/build/integrate скиллы |
| `glossary-format.md` | Формат таблиц глоссария | `src/**/*_Glossary/**`, build/translate-glossary |
| `layout-recovery.md` | Восстановление структуры документа из PDF | cleanup-artifacts |
| `merge-extraction.md` | Сведение результатов PDF-конвертеров | cleanup-artifacts |
| `pdf-cleanup.md` | Нормализация markdown после конвертации | cleanup-artifacts, `src/**/en/**` |
| `verify-import.md` | Правила верификации импорта | verify-import, `src/**/en/**` |

### Перевод

| Правило | Описание | Подключается к |
|---|---|---|
| `translation-style.md` | Стиль перевода TTRPG-правил + конкретные антипаттерны с примерами | `src/**/ru/**`, translate-content/glossary |
| `translation-validation.md` | Чеклист валидации перевода (структура, термины, оформление) | `src/**/ru/**`, translate-*/verify-content |
| `translation-quality-review.md` | Системный промт агента качества (жёсткая редакторская проверка) | `src/**/ru/**`, translate-verify/verify-content |
| `translate-dictionaries.md` | Структура и формат словарей `translate/`, приоритет источников | `src/*/translate/**`, translate-*/verify-content |
| `terminology-propagation.md` | Пропагация терминологических изменений, conflict resolution, verify loop | `src/**/ru/**`, `src/*/translate/**`, translate-*/verify-content |

### Общие

| Правило | Описание | Подключается к |
|---|---|---|
| `quality-gates.md` | Блокирующие условия по этапам (error/warning/note) | Все pipeline-скиллы, validate-markdown |

## Пайплайн импорта

Оркестратор: `/import-srd` — все фазы последовательно.

```
Phase 0:   Создание ветки import/{game}-{version}
Phase 1:   /convert-pdf        — PDF → 3 markdown в /tmp/
Phase 2:   /cleanup-artifacts  — сведение + разбивка + чистка → src/{game}/{version}/en/
Phase 3:   /verify-import      — циклическая верификация + ручная проверка
Phase 3.5: Squash merge в main
Phase 4:   /integrate-srd      — интеграция в сайт (уже в main)
```

## Пайплайн перевода

Оркестратор: `/translate-srd` — все фазы последовательно.

```
Phase 0:   Проверка EN + создание ветки translate/{game}-{version}
Phase 0.5: Загрузка reference-глоссариев (кросс-версионная согласованность)
Phase 1:   /build-glossary     — EN глоссарий из исходников
Phase 2:   /translate-glossary — RU глоссарий + словари translate/
Phase 3:   /translate-verify   — верификация глоссария (3 агента, 3+ раундов)
Phase 4:   Ручная проверка глоссария
Phase 5:   /translate-content  — перевод контента по словарю
Phase 6:   /verify-content     — верификация контента (3 агента, 3+ раундов)
Phase 7:   Ручная проверка контента
Phase 7.5: Squash merge в main
Phase 8:   /integrate-srd      — интеграция в сайт (уже в main)
```

## Сборка сайта

Сайт собирается копированием — исходники из `src/` копируются в `docs/` и корень:

```bash
bash .github/scripts/prepare_docs.sh   # подготовка
mkdocs serve                            # локальный сервер
mkdocs build                            # билд в site/
bash .github/scripts/prepare_docs.sh --clean  # очистка
```

Скрипт: `src/site/mkdocs.yml` и `overrides/` → корень, `src/` → `docs/{en,ru}/`.
CI (`pages.yml`) вызывает тот же скрипт.

## Терминологические решения

Спорные переводческие решения и их обоснования:
- `src/{game}/translate/logs/{date}_log.md` — решения для конкретной системы
- `src/translate/logs/{date}_log.md` — общие решения (все системы)

Словари фиксируют **что** переводить как, логи — **когда и почему**.
При изменении термина — `.claude/rules/terminology-propagation.md`.

## Технические детали

- Все агенты используют **model: "opus"**
- Большие файлы (>3000 строк) — чанками через offset/limit
- Коммиты после каждого файла, сообщения на русском
- Сайт: MkDocs Material + mkdocs-static-i18n + mkdocs-minify-plugin
- Релиз: один rolling-релиз с тегом `latest` (`.github/workflows/release.yml`). Триггерится
  `push` в `main` при изменении `src/**/*.md` и пересобирает/перезаписывает **только** документы
  затронутой системы/версии (D&D 5.2/5.1/converting, Daggerheart, BRP); `workflow_dispatch` —
  полная пересборка всех. Прежние пер-системные теги `{short}-srd-v*` выведены из употребления.
