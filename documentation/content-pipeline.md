# Контентный пайплайн: импорт и перевод SRD

Как SRD (System Reference Document) попадает в репозиторий: PDF → markdown → перевод → сайт.
Пайплайн производит `.md` в `src/{game}/{version}/{en,ru}/`, а публикует их Astro-приложение
из `web/` (см. `CLAUDE.md`, раздел про стек). Раньше этот файл был разделом B корневого
`CLAUDE.md`; вынесен отдельно, чтобы корневой файл читался за минуту (#288).

## Структура проекта

```
src/{game}/{version}/en/       — EN оригинал (markdown)
src/{game}/{version}/ru/       — RU перевод
src/{game}/{version}/ru/*_Glossary/  — глоссарий (словарь терминов)
src/{game}/translate/          — словари и логи (logs/, 01_dictionary_base, ...)
src/translate/                 — общие переводческие артефакты (все системы)
web/                           — Astro-приложение (сайт rules.omnisgm.com)
.github/scripts/               — скрипты сборки, генерации и гейты импорта
.github/workflows/             — CI/CD workflows

{version} — идентификатор документа, не обязательно версия: srd-5.2, srd-1.0, kobold-toe и т.д.
```

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

Скилла у этого шага нет и не заводим: он делается руками, разово на систему или редакцию, и
состоит из правок в разных местах `web/`, каждая из которых требует решения (заголовки навигации,
состав справочников, тексты карточек). Прежний скилл integrate-srd описывал интеграцию в MkDocs и
удалён вместе с движком (#296). Порядок — ниже, в разделе «Подключение новой системы или редакции».

## Правила (rules)

Автоматически подключаются по `paths:` при работе с соответствующими файлами.

### Импорт

| Правило | Описание | Подключается к |
|---|---|---|
| `file-naming-conventions.md` | Соглашения об именовании файлов и директорий | `src/**`, cleanup/build-glossary скиллы |
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
Phase 4:   интеграция в сайт   — вручную в Astro (см. «Подключение новой системы или редакции»)
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
Phase 8:   интеграция в сайт   — вручную в Astro (см. «Подключение новой системы или редакции»)
```

## Сборка сайта

Сайт — Astro-приложение в `web/`; markdown из `src/` подключён content collections, копирования
в `docs/` больше нет:

```bash
cd web
npm run dev      # локальный сервер (predev собирает данные сущностей и даты контента)
npm run build    # статический билд в web/dist
npm run check    # astro check
npm run test:e2e # Playwright
```

Деплой — `astro build` + `firebase deploy --only hosting` (`.github/workflows/deploy.yml`).

## Подключение новой системы или редакции

Финальный шаг обоих пайплайнов. Делается руками; ниже — все места, где новая система себя
объявляет. Для новой РЕДАКЦИИ существующей игры (например второй SRD у Daggerheart) нужны только
пункты 2–4 и 7.

1. **Content collection** — `web/src/content.config.ts`: глоб перечисляет игры явно
   (`@(dnd|daggerheart|brp)`), поэтому новая игра добавляется в него. Ограничение намеренное: без
   него в коллекцию затянуло бы `src/{game}/translate/` — рабочие артефакты перевода, не контент.
   Новая редакция существующей игры подхватывается сама.
2. **Навигация** — `web/src/lib/nav.ts`: группа игры и страницы внутри неё (`id`, RU- и
   EN-заголовок, путь). Отсюда же строятся сайдбар, крошки и хабы документов — второго списка
   разделов в проекте нет.
3. **Хаб редакции** — `web/src/pages/[lang]/{game}/[version]/index.astro`: в реестре `DOCS`
   добавляется строка `{ version, groupId, api }`. `groupId` — группа из `nav.ts`, `api` — имя
   каталога в JSON API (`srd-5.2` → `srd52`). Для новой игры файл заводится по образцу соседнего.
4. **Главная** — `web/src/pages/index.astro` и `web/src/pages/[lang]/index.astro`: карточка системы
   с ссылкой на Legal-страницу и описанием (оба языка, оба файла).
5. **Сущности и JSON API** (если у системы есть справочники — заклинания, существа, предметы):
   `.github/scripts/config_{game}.py` описывает, какие файлы и каким парсером разбираются; вызов
   `generate_api.py --game {game}` добавляется в `hosting.predeploy` в `firebase.json`. Дальше —
   маршруты сущностей и хабов в `web/src/pages/[lang]/{game}/[version]/{resource}/`, реестр хабов
   в `web/src/lib/*-hubs.ts` и пары для hovercard в `web/src/pages/hc/[game]/[ver]/[lang].json.ts`.
6. **Редирект уровня системы** — `firebase.json`: `/{lang}/{game}` → свежая редакция, 301, **по
   одному правилу на язык**. Ограничения вида `/:lang(en|ru)` понимает эмулятор, но не прод — такое
   правило молча отдаёт 404 (см. CLAUDE.md).
7. **Картинки сущностей** — раскладка и промты в `documentation/entity-images.md`; очередь
   генератора строится от JSON API сама, отдельной регистрации не требует.

Проверка: `npm run build` (гейты меты и sitemap валят сборку сами), `npm run check`,
`npm run test:e2e`. Sitemap, hreflang и JSON-LD собираются из тех же источников — руками их не
правят.

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
- Сайт: Astro (SSG) + PWA (`@vite-pwa/astro`) + Pagefind; хостинг Firebase, эдж — Cloudflare
- Релиз: один rolling-релиз с тегом `latest` (`.github/workflows/release.yml`). Триггерится
  `push` в `main` при изменении `src/**/*.md` и пересобирает/перезаписывает **только** документы
  затронутой системы/версии (D&D 5.2/5.1/converting, Daggerheart, BRP); `workflow_dispatch` —
  полная пересборка всех. Прежние пер-системные теги `{short}-srd-v*` выведены из употребления.
