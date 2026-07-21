---
description: "Создание EN глоссария из исходников SRD — извлечение терминов и сущностей. Используй как первый шаг перевода."
user-invocable: true
---

# /build-glossary — Создание EN глоссария

## Использование

```
/build-glossary <game> <version>
```

Пример: `/build-glossary daggerheart srd-1.0`

## Алгоритм

### Шаг 1: Сканирование и анализ исходников

1. Определи директорию: `src/{game}/{version}/en/`
2. Запусти скрипт анализа сущностей:
   ```bash
   python3 .claude/skills/build-glossary/extract_entities.py src/{game}/{version}/en/ > /tmp/{game}_entities.json
   ```
   Скрипт автоматически определяет типы файлов (spells, monsters, animals, magic_items, equipment, feats) и считает сущности. Используй его вывод для планирования файлов глоссария.

3. Если директория пуста — предложи `/convert-pdf` + `/cleanup-artifacts`

### Шаг 2: Определение директории глоссария

Именование: **`.claude/rules/glossary-format.md`** + **`.claude/rules/file-naming-conventions.md`**

1. Найди последний `NN_Name` в `src/{game}/{version}/en/`
2. Следующий номер → `{NN}_Glossary/`

### Шаг 3: Создание `00_Glossary.md` — основные термины

Прочитай ВСЕ EN файлы и извлеки термины по категориям.

Категории терминов (обязательные и расширенные) — см. `.claude/rules/translate-dictionaries.md` → «Категории терминов».

Откуда извлекать (специфика build-glossary):

| Категория | Откуда извлекать |
|-----------|-----------------|
| Характеристики | PlayingTheGame, CharacterCreation |
| Состояния | RulesGlossary, PlayingTheGame |
| Типы урона | RulesGlossary, Equipment |
| Классы | Classes/, CharacterCreation |
| Виды/расы | CharacterOrigins |
| Навыки | PlayingTheGame |
| Типы существ | Monsters, RulesGlossary |
| Ключевые механики | PlayingTheGame, RulesGlossary |

Формат таблиц — по `.claude/rules/glossary-format.md`. Сортировка A-Z.

**Коммит:** `Глоссарий EN {game} {version}: 00_Glossary.md`

### Шаг 4: Создание файлов справочных таблиц

Используй JSON от `extract_entities.py` чтобы определить какие файлы создавать. Типичные:

| Файл | Тип | Колонки (адаптировать под игру) |
|------|-----|------|
| `01_Spells.md` | Заклинания | Spell, Level, School, Classes |
| `02_Monsters.md` | Монстры | Monster, CR, Type, Size |
| `03_MagicItems.md` | Магические предметы | Item, Type, Rarity, Attunement |
| `04_Animals.md` | Животные | Animal, CR, Type, Size |

Не все игры имеют все типы. Создавай только то, что есть в исходниках.

**Коммит после КАЖДОГО файла:** `Глоссарий EN {game} {version}: {filename}`

### Шаг 5: Верификация и итог

1. Сравни количество сущностей в глоссарии с данными `extract_entities.py`:
   - Spells в глоссарии = spells в JSON
   - Monsters в глоссарии = monsters в JSON
   - ...
2. Если расхождение — найти пропущенные и добавить

```
Глоссарий EN создан:
- 00_Glossary.md: N категорий, M терминов
- 01_Spells.md: K заклинаний (extract: K) ✓
- 02_Monsters.md: L монстров (extract: L) ✓
...
```

## Скрипты

| Скрипт | Что делает |
|--------|------------|
| `extract_entities.py` | Сканирует EN файлы, классифицирует по типам, считает сущности, выводит JSON |

## Технические требования

- Все агенты — **model: "opus"**
- Большие файлы (>3000 строк) — чанками
- Коммит после каждого файла
- Сообщения коммитов на русском
