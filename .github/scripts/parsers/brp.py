"""Parsers for Basic Roleplaying (BRP) SRD entities.

BRP-контент — таблицы (навыки) и нумерованная проза (точечные правила, профессии).
Достаём именованные записи в structured JSON для programmatic-страниц (аналог D&D/DH).

Паритет слагов EN↔RU: у навыков RU-таблица несёт колонку «Оригинал» (английское имя);
у профессий/правил — inline-English в заголовках (`### Аристократ (Noble)`).
"""

import re
import sys

from .base import slugify, split_blocks, extract_names


# RU-категория навыка → каноническая английская (фасет skills/category/{slug}).
_SKILL_CAT_EN = {
    "Боевой": "Combat", "Общение": "Communication", "Манипуляция": "Manipulation",
    "Ментальный": "Mental", "Восприятие": "Perception", "Физический": "Physical",
}


def _section_table(text: str, heading_needles: list[str]) -> tuple[list[str], list[list[str]]]:
    """(header, data_rows) таблицы в секции `## …heading…` до следующего `## `.

    Ячейки — trim; separator-строка (---) отброшена. Возвращает ([], []) если не найдено.
    """
    rows: list[list[str]] = []
    capturing = False
    for line in text.split("\n"):
        stripped = line.strip()
        if not capturing:
            if stripped.startswith("## ") and any(n in stripped for n in heading_needles):
                capturing = True
            continue
        if stripped.startswith("## "):
            break
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue  # separator
            rows.append(cells)
    if not rows:
        return [], []
    return rows[0], rows[1:]


def parse_brp_skills(text: str, lang: str) -> list[dict]:
    """Навыки из «Complete Skill List» / «Полный список навыков».

    EN-колонки: # | Skill | Base Chance | Category | Description.
    RU добавляет колонку «Оригинал» (английское имя) → канонический слаг.
    """
    header, data = _section_table(text, ["Complete Skill List", "Полный список навыков"])
    if not header:
        return []
    idx = {h: i for i, h in enumerate(header)}

    def col(row, names, default=None):
        for n in names:
            if n in idx and idx[n] < len(row):
                return row[idx[n]]
        return default

    out = []
    for row in data:
        name = col(row, ["Skill", "Навык"])
        if not name:
            continue
        name_en = col(row, ["Оригинал"])  # только RU
        base = col(row, ["Base Chance", "Базовый шанс"])
        category = col(row, ["Category", "Категория"])
        if lang == "en":
            category_en = category
        else:
            # Fail-loud на неизвестную RU-категорию: тихий фолбэк дал бы кириллический
            # category_slug и «пустой» фасет (категорий всего 6 — это опечатка/дрейф).
            category_en = _SKILL_CAT_EN.get(category)
            if category_en is None:
                print(f"  Warning: неизвестная RU-категория навыка {category!r} "
                      f"(навык {name!r}) — фасет будет кириллическим", file=sys.stderr)
                category_en = category
        description = col(row, ["Description", "Описание"], "")
        slug_src = name_en or name
        out.append({
            "slug": slugify(re.sub(r"\s*\([^)]*\)\s*$", "", slug_src).strip()),
            "name": name,
            "name_en": name_en,
            "base_chance": base,
            "category": category,
            "category_en": category_en,
            "category_slug": slugify(category_en) if category_en else None,
            "description_md": description,
        })
    return out


def parse_brp_professions(text: str, lang: str) -> list[dict]:
    """Профессии — `### Имя` в секции «Detailed Profession Skill Lists».

    Тело (Primary-характеристики + таблица навыков) целиком в description_md.
    """
    after = "Detailed Profession Skill Lists" if lang == "en" else "Подробные списки навыков профессий"
    out = []
    for heading, body in split_blocks(text, 3, after):
        name, name_en, slug = extract_names(heading.strip(), lang)
        out.append({
            "slug": slug,
            "name": name,
            "name_en": name_en,
            "description_md": body.strip(),
        })
    return out


def parse_brp_spot_rules(text: str, lang: str) -> list[dict]:
    """Точечные правила — `## 6.N Имя` (номер срезаем, имя → слаг)."""
    out = []
    for heading, body in split_blocks(text, 2):
        h = re.sub(r"^\d+\.\d+\s+", "", heading.strip())  # убрать «6.1 »
        name, name_en, slug = extract_names(h, lang)
        out.append({
            "slug": slug,
            "name": name,
            "name_en": name_en,
            "description_md": body.strip(),
        })
    return out
