---
description: "Интеграция переведённого SRD в сайт — скрипты, CI, навигация. Используй как последний шаг пайплайна."
user-invocable: true
---

# /integrate-srd — Интеграция SRD в сайт

## Использование

```
/integrate-srd <game> <version>
```

Пример: `/integrate-srd daggerheart srd-1.0`

## Алгоритм

### Шаг 0: Проверка ветки

1. Убедись что текущая ветка — `main`:
   ```bash
   git branch --show-current
   ```
2. Если не main — останови и сообщи пользователю (интеграция должна выполняться в main после squash merge)

### Шаг 1: Сканирование структуры SRD

1. Найди все файлы в `src/{game}/{version}/en/` и `src/{game}/{version}/ru/`
2. Определи подпапки (классы, глоссарий и т.д.)
3. Определи номер глоссария (`*_Glossary/`)
4. Выведи структуру пользователю для подтверждения

### Шаг 2: Главная страница `src/site/index.md` и `src/site/en/index.md`

Главная страница существует в двух версиях — RU (`src/site/index.md`) и EN (`src/site/en/index.md`). Нужно добавить блок в ОБА файла.

1. Прочитай `src/site/index.md` (RU) и `src/site/en/index.md` (EN)
2. Добавь блок для нового SRD **по образцу существующих** (D&D, Daggerheart):

**RU (`index.md`):**
```markdown
## {Game Title RU}

[:material-download: Скачать](https://github.com/OmnisGM-App/OmnisGM-Rules/releases?q={short}-srd)

- **[SRD {ver}]({game}/{version}/00_Legal.md)** — Описание SRD на русском. Опубликовано по лицензии [название](url).
```

**EN (`en/index.md`):**
```markdown
## {Game Title EN}

[:material-download: Download](https://github.com/OmnisGM-App/OmnisGM-Rules/releases?q={short}-srd)

- **[SRD {ver}]({game}/{version}/00_Legal.md)** — Description in English. Published under [License Name](url).
```

3. Добавь перед разделителем `---` в каждом файле
4. **Коммит:** `Интеграция {game} {version}: главная страница (RU + EN)`

### Шаг 3: `.github/scripts/prepare_docs.sh`

1. Прочитай `.github/scripts/prepare_docs.sh`
2. Добавь блок для нового SRD **по образцу существующих** (Daggerheart, D&D):

```bash
# {Game Title} {Version}
mkdir -p docs/en/{game}/{version}/{subdirs} docs/en/{game}/{version}/{NN}_Glossary
mkdir -p docs/ru/{game}/{version}/{subdirs} docs/ru/{game}/{version}/{NN}_Glossary
cp -r src/{game}/{version}/en/* docs/en/{game}/{version}/
cp -r src/{game}/{version}/en/* docs/ru/{game}/{version}/
cp -r src/{game}/{version}/ru/* docs/ru/{game}/{version}/
```

RU: сначала копируем EN как fallback (`cp -r en/* docs/ru/`), затем поверх RU (`cp -r ru/* docs/ru/`) — EN fallback для ещё не переведённых файлов.

3. `mkdir -p` для каждой подпапки (классы, глоссарий и т.д.)
4. **Коммит:** `Интеграция {game} {version}: prepare_docs.sh`

### Шаг 4: `.github/workflows/pages.yml`

1. Прочитай `.github/workflows/pages.yml`
2. В секции "Copy source files to docs" (`run: |`) добавь **те же команды** что и в prepare_docs.sh:

```yaml
          mkdir -p docs/en/{game}/{version}/{subdirs} docs/en/{game}/{version}/{NN}_Glossary
          mkdir -p docs/ru/{game}/{version}/{subdirs} docs/ru/{game}/{version}/{NN}_Glossary
          cp -r src/{game}/{version}/en/* docs/en/{game}/{version}/
          cp -r src/{game}/{version}/en/* docs/ru/{game}/{version}/
          cp -r src/{game}/{version}/ru/* docs/ru/{game}/{version}/
```

3. Команды должны быть **идентичны** prepare_docs.sh (единый источник правды)
4. **Коммит:** `Интеграция {game} {version}: pages.yml`

### Шаг 5: `mkdocs.yml` — навигация

1. Прочитай `src/site/mkdocs.yml`
2. Определи RU-имена для навигации:
   - Из глоссария `00_Glossary.md` (RU имена категорий)
   - Из заголовков `#` в каждом файле
   - Из существующих nav_translations (если переводы уже есть)
3. Добавь блок навигации в `nav:` по образцу существующих SRD:

```yaml
  - {Game Title}:
      - {Version Title}:
          - Правовая информация: {game}/{version}/00_Legal.md
          - ...: {game}/{version}/01_....md
          - Классы:
              - {Класс1}: {game}/{version}/NN_Classes/01_....md
              - ...
          - Глоссарий:
              - Термины: {game}/{version}/{NN}_Glossary/00_Glossary.md
              - ...
```

4. Добавь nav_translations для новых RU-имён в секцию `plugins.i18n.languages[en].nav_translations`
5. **Коммит:** `Интеграция {game} {version}: навигация src/site/mkdocs.yml`

### Шаг 6: Сборка объединённого markdown (опционально)

Для проверки можно собрать объединённый файл скриптом:
```bash
bash .claude/skills/integrate-srd/build_combined_md.sh src/{game}/{version}/ru {SHORT}-SRD-{VER}-RU.md
```

### Шаг 7: Release workflow

1. Определи короткий префикс для тега — см. `.claude/rules/file-naming-conventions.md` (раздел "Релизные теги")
2. Проверь существует ли уже workflow `.github/workflows/release-{game}.yml`
3. Если нет — скопируй `.github/workflows/release-daggerheart.yml` → `release-{game}.yml`, подставив: `source-dir` = `src/{game}/{version}/{ru,en}`, `output-file`/`input-file` = `{SHORT}-SRD-{VER}-{RU,EN}`, тег-триггер `{short}-srd-v*`, заголовок release = `{Game Title} SRD — RU + EN`. Значения `lang`/`toc-title` в образце уже корректны. Файл-образец — единый источник правды.
4. **Коммит:** `Интеграция {game} {version}: release workflow`

### Шаг 8: Создание релизного тега

1. Определи версию тега: `{short}-srd-v1.0.0` (первый релиз для этой игры)
2. Если тег уже существует — инкрементируй patch: `v1.0.1`, `v1.0.2` и т.д.
3. Спроси пользователя через **AskUserQuestion**:
   - "Создать и запушить релизный тег `{tag}`? Это запустит сборку MD+PDF и создаст GitHub Release."
   - Опции: "Да, создать тег" / "Нет, сделаю позже"
4. Если "Да":

```bash
git tag {tag}
git push origin {tag}
```

5. Если "Нет" — вывести инструкцию:

```
Чтобы создать релиз позже:
  git tag {tag}
  git push origin {tag}
```

### Шаг 9: Проверка

1. Запусти `bash .github/scripts/prepare_docs.sh` и проверь что файлы появились в `docs/`
2. Проверь структуру:

```bash
ls docs/en/{game}/{version}/
ls docs/ru/{game}/{version}/
```

3. Если ошибки — исправь и переделай коммит
4. Выведи итог:

```
Интеграция {game} {version} завершена:
- .github/scripts/prepare_docs.sh ✓
- .github/workflows/pages.yml ✓
- src/site/mkdocs.yml — навигация ✓
- src/site/mkdocs.yml — nav_translations ✓
- Release workflow: .github/workflows/release-{game}.yml ✓
- Релизный тег: {tag} ✓ / (ожидает ручного создания)
- Проверка: docs/ структура корректна ✓
```

## Технические требования

- Проверить работоспособность через `bash .github/scripts/prepare_docs.sh`
- Коммит после каждого изменённого файла
- Сообщения коммитов на русском
