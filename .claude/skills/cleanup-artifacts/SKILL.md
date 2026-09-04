---
description: "Сведение результатов трёх конвертеров + разбивка на файлы + чистка артефактов PDF. Используй после /convert-pdf."
user-invocable: true
---

# /cleanup-artifacts — Сведение, разбивка и чистка

## Использование

```
/cleanup-artifacts <game> <version>
```

Пример: `/cleanup-artifacts brp srd-1.0`

## Предварительные условия

Файлы из `/convert-pdf` в `/tmp/`:
- `/tmp/{game}_{version}_marker.md`
- `/tmp/{game}_{version}_pymupdf.md`
- `/tmp/{game}_{version}_docling.md`
- `/tmp/{game}_{version}_convert_summary.json` (опционально — сводка от скрипта конвертации)

Оригинальный PDF для сверки — спросить путь если неизвестен.

## Алгоритм

### Фаза A: Сведение (merge)

Чеклист: **`.claude/rules/merge-extraction.md`**

Агент сведения — **model: "opus"**. Большие файлы (>3000 строк) читать чанками через offset/limit.

Агент анализирует все результаты конвертации и выбирает лучшие части для каждого раздела. Если есть `convert_summary.json` — используй статистику для предварительной оценки (конвертер с 0 таблиц не годится для таблиц).

**Частый сценарий:** один конвертер значительно лучше остальных (например, marker даёт 98% результата). В этом случае — бери его за основу целиком, остальные только для верификации. Не трать время на посекционное сравнение, если разница очевидна из статистики.

Результат: `/tmp/{game}_{version}_merged.md`

**Отчёт о полезности конвертеров:**

```
Полезность конвертеров для {game} {version}:

marker:      ~N% (основной / верификация)
pymupdf4llm: ~N% (основной / верификация)
docling:     ~N% (основной / верификация)
```

### Фаза B: Layout Recovery (восстановление структуры)

Чеклист: **`.claude/rules/layout-recovery.md`**

#### Шаг 1: Автоматические исправления (скрипт)

```bash
python3 .claude/skills/cleanup-artifacts/layout_recovery.py /tmp/{game}_{version}_merged.md /tmp/{game}_{version}_recovered.md
```

Скрипт исправляет: разрыв вывода по словам (узкая колонка PDF — см. `layout-recovery.md` §11a),
bold в заголовках, артефакты `<br>`, дефисные переносы, split components, склеенные поля stat-блока (`**Casting Time:** … **Range:** …` → по строкам), trailing пустые колонки таблиц. Регресс-тесты скрипта: `python3 .claude/skills/cleanup-artifacts/test_layout_recovery.py`.

#### Шаг 2: Ручные исправления (агент)

После скрипта агент выполняет ручные исправления по `.claude/rules/layout-recovery.md` (§4–6, §10).

### Фаза C: Разбивка на файлы

1. **Определи структуру** — найди все H1 заголовки:
   ```bash
   grep -n '^# ' /tmp/{game}_{version}_recovered.md
   ```

2. **Точки разбивки:**
   - Каждый H1 → отдельный файл
   - `00_Legal.md` — лицензия/OGL всегда первым
   - Нумерация: `00_Legal.md`, `01_Name.md`, `02_Name.md`, ...

3. **Подпапки** — если глава содержит много однотипных H2 сущностей (например, 12 классов персонажей), создай подпапку:
   ```
   NN_Classes/
     00_Classes.md     (заголовок главы, если есть вводный текст)
     01_Barbarian.md
     02_Bard.md
     ...
   ```
   Критерий: 5+ однотипных H2 внутри одного H1 → подпапка.

4. **Именование** — `.claude/rules/file-naming-conventions.md` (CamelCase, двузначный номер)

5. **Глоссарий НЕ создаётся** (задача `/build-glossary`)

### Фаза D: Markdown Normalization (нормализация)

Чеклист: **`.claude/rules/pdf-cleanup.md`**

```bash
python3 .claude/skills/cleanup-artifacts/normalize_markdown.py src/{game}/{version}/en/
```

Скрипт нормализует все файлы в директории: лигатуры, soft hyphens, двойные пробелы, trailing whitespace, em dashes, пустые строки.

### Коммиты

**Один коммит на файл** (создание + нормализация вместе, не два отдельных), сообщение на русском:
```
Импорт {game} {version}: {filename}
```

### Финальная сводка

```
Сведение и чистка завершены:

Файлы созданы: K
- src/{game}/{version}/en/00_Legal.md
- src/{game}/{version}/en/01_....md
...

Следующий шаг: /verify-import {game} {version}
```
