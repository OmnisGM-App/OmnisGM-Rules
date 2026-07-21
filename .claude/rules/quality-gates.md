---
paths:
  - ".claude/skills/import-srd/**"
  - ".claude/skills/translate-srd/**"
  - ".claude/skills/convert-pdf/**"
  - ".claude/skills/cleanup-artifacts/**"
  - ".claude/skills/verify-import/**"
  - ".claude/skills/translate-content/**"
  - ".claude/skills/verify-content/**"
  - ".claude/skills/validate-markdown/**"
---

# Quality Gates — блокирующие условия по этапам

## Severity levels

Используются во всех этапах:

| Уровень | Значение | Действие |
|---|---|---|
| **error** | Блокирует этап. Переход дальше невозможен | Исправить до продолжения |
| **warning** | Требует просмотра. Может быть допущен осознанно | Показать пользователю, продолжить если подтвердил |
| **note** | Рекомендация. Не блокирует | Зафиксировать в отчёте |

## Этап 0: Конвертация PDF (convert-pdf)

### Блокирующие (error)

- Менее 2 из 3 конвертеров отработали успешно
- Результирующий файл пуст или содержит менее 100 строк

### Требующие просмотра (warning)

- Один из конвертеров не установлен (сведение будет менее точным)
- Конвертер завершился с ошибкой (stderr сохранён)

## Этап 1: Импорт (cleanup-artifacts → verify-import)

Критерии error/warning/note (полнота, структура, таблицы, форматирование) — см. `.claude/rules/verify-import.md`.

## Этап 2: Глоссарий (build-glossary → translate-glossary → translate-verify)

Критерии error (синонимы, омонимы, пропущенные термины, колонка «Оригинал», кросс-версионный конфликт) — см. `.claude/rules/translation-validation.md` §6, §7.

Уточнения severity, не покрытые целевым файлом:

- **warning** — перевод термина отличается от устоявшегося в русскоязычном сообществе; аббревиатура может быть неоднозначной
- **note** — термин имеет несколько допустимых переводов (зафиксирован один, остальные отвергнуты)

## Этап 3: Перевод контента (translate-content → verify-content)

Критерии error/warning/note — см. `.claude/rules/translation-validation.md` §1 (структура), §5 (локализация), §8 (severity).

## Этап 4: Валидация markdown (validate-markdown)

Критерии error/warning/note — см. скилл `/validate-markdown`.

## Правило перехода между этапами

```
Этап N → Этап N+1 разрешён ТОЛЬКО если:
  - 0 ошибок уровня error
  - Все warning'и показаны пользователю И подтверждены
```
