---
description: "Интеграция новой системы/версии SRD в сайт (Astro + JSON API + релиз latest): чеклист фактических точек подключения"
---

# /integrate-srd — Интеграция SRD в сайт

Подключение новой системы или версии (после `/import-srd` и/или `/translate-srd`,
контент уже в `src/{game}/{version}/{en,ru}/`) к сайту rules.omnisgm.com.
Интеграция ручная: единого генератора нет, скилл — чеклист фактических точек.

## Использование

```
/integrate-srd <game> <version>
```

Пример: `/integrate-srd daggerheart srd-1.0`

Выполняется в `main` после squash-мёржа контентной ветки: сначала `git branch --show-current`,
на другой ветке — остановись и сообщи пользователю.

## Точки подключения

### 1. JSON API (если у системы есть справочники сущностей)

- Конфиг парсера: `.github/scripts/config_{game}.py` (dnd — `config.py`) по образцу
  `config_daggerheart.py` / `config_brp.py`; читается через `load_game_config` в
  `generate_api.py`.
- Вызов на деплое: `hosting.predeploy` в `firebase.json` — по одной строке
  `generate_api.py --game {game} --src-root src/{game} --output-dir web/dist/api` на игру.

### 2. Astro (`web/`)

- Content collections уже смотрят на `src/{game}/...` глобом (`web/src/content.config.ts`) —
  обычно правок не требуют; проверить, что новые файлы попадают в коллекцию `srd`.
- NAV-дерево, страницы-маршруты (тонкие, по одной на игру) и хаб редакции (`DocHub.astro`) —
  по образцу существующих игр в `web/src/pages` и `web/src/lib`.
- Редиректы уровня системы — в `firebase.json` (см. правило `seo-dates-hubs.md`:
  эмулятор ≠ прод по синтаксису `source`).

### 3. CI контента

- `.github/workflows/content.yml`: непарные EN↔RU файлы — в `EXCLUSIONS`;
  slug-парность подключается только системам с JSON API.

### 4. Релиз (`release.yml`, rolling `latest`)

- Добавить группу в фильтр `dorny/paths-filter` (`src/{game}/{version}/**/*.md`),
  условие в шаг «Any group selected?» и шаги сборки
  (`.github/actions/build-markdown` / `build-pdf`) по образцу существующих групп.
- Тегов нет: релиз один, `latest`, апсертится по именам файлов
  (пер-системные теги `{short}-srd-v*` выведены из употребления).

### 5. Проверка

```bash
cd web
npm run build    # predev/prebuild соберут данные сущностей и даты контента
npm run test:e2e
```

После мёржа в `main` `release.yml` пересоберёт затронутые документы релиза сам;
полная пересборка — `workflow_dispatch`.

Опционально, для локальной проверки объединённого документа:
`bash .claude/skills/integrate-srd/build_combined_md.sh src/{game}/{version}/ru /tmp/{SHORT}-SRD-RU.md`

## Технические требования

- Коммит после каждого изменённого файла, сообщения на русском
