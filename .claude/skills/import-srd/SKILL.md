---
description: "Оркестратор полного пайплайна импорта PDF в markdown. Вызывает convert-pdf, cleanup-artifacts, verify-import, integrate-srd."
user-invocable: true
---

# /import-srd — Полный пайплайн импорта SRD

## Использование

```
/import-srd <pdf_path> <game> <version>
```

Пример: `/import-srd /tmp/brp-srd.pdf brp srd-1.0`

## Пайплайн

Выполняй фазы строго последовательно. Каждая фаза — отдельный skill.

### Phase 0: Создание ветки

1. **Создай ветку импорта:**
   ```bash
   git checkout -b import/{game}-{version}
   ```
   - Если ветка уже существует (продолжение прерванного пайплайна) → переключись на неё: `git checkout import/{game}-{version}`
2. Все коммиты фаз 1-3 идут в эту ветку

```
✓ Phase 0 завершена: ветка import/{game}-{version} создана
```

### Phase 1: Конвертация PDF

```
→ /convert-pdf {pdf_path} {game} {version}
```

Результат: три файла в `/tmp/` — сырой markdown от трёх конвертеров.

После завершения:
```
✓ Phase 1 завершена: PDF конвертирован (marker + pymupdf4llm + docling)
```

### Phase 2: Сведение + разбивка + чистка

```
→ /cleanup-artifacts {game} {version}
```

После завершения:
```
✓ Phase 2 завершена: файлы созданы и очищены (K файлов)
```

### Phase 3: Верификация полноты

```
→ /verify-import {game} {version}
```

Это включает:
- Автоматическая проверка полноты, структуры, таблиц, форматирования
- Циклические исправления до полной чистоты
- Пауза для ручной проверки пользователем

После завершения:
```
✓ Phase 3 завершена: верификация пройдена (N раундов, M исправлений)
```

### Phase 3.5: Squash merge в main

1. Переключись на main:
   ```bash
   git checkout main
   ```
2. Squash merge ветки импорта:
   ```bash
   git merge --squash import/{game}-{version}
   ```
3. Создай коммит:
   ```
   Импорт {game} {version}: EN markdown из PDF (N файлов)
   ```
4. Удали ветку:
   ```bash
   git branch -d import/{game}-{version}
   ```

```
✓ Phase 3.5 завершена: squash merge в main
```

### Phase 4: Интеграция в сайт

```
→ /integrate-srd {game} {version}
```

После завершения:
```
✓ Phase 4 завершена: интеграция в сайт + релиз
✓ Полный пайплайн импорта завершён для {game} {version}
```

## Восстановление после сбоя

Перезапуск с любой фазы — вызовом соответствующего skill напрямую (ветку восстанови как в Phase 0).

```
PDF не конвертирован         → /convert-pdf       (Phase 1)
PDF конвертирован (в /tmp/)  → /cleanup-artifacts (Phase 2)
файлы созданы, не проверены  → /verify-import     (Phase 3)
всё чисто и проверено        → /integrate-srd     (Phase 4, в main)
```

## Технические требования

- Все агенты во всех фазах — **model: "opus"**
- При ошибке в любой фазе — остановка и отчёт пользователю
- Сообщения коммитов на русском
