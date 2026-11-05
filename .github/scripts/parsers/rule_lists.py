"""Списки правил SRD 5.2 из именованных таблиц глав (#482): ресурс `languages` и подписи членов списков выбора."""

import re

from .base import slugify

_TITLE = re.compile(r"^(?:Table|Таблица): (.+)$")


def _table(text: str, title: str) -> list[list[str]]:
    """Строки таблицы под строкой «Table: <title>» без шапки и разделителя."""
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if (m := _TITLE.match(line.strip())) and m.group(1).strip() == title), None)
    if start is None:
        raise ValueError(f"no table «{title}»")
    rows = []
    for line in lines[start + 1:]:
        line = line.strip()
        if not line and not rows:
            continue
        if not line.startswith("|"):
            break
        rows.append([c.strip() for c in line.strip("|").split("|")])
    rows = [r for r in rows[1:] if not set("".join(r)) <= set("-: ")]
    if not rows:
        raise ValueError(f"table «{title}» has no rows")
    return rows


def parse_table_terms(text: str, tables: dict[str, str]) -> list[dict]:
    """Первая колонка каждой таблицы `{заголовок: ключ списка}` — по строке на член списка, в порядке текста."""
    return [{"list": key, "name": row[0]} for title, key in tables.items() for row in _table(text, title)]


def parse_languages(text: str, lang: str, tables: dict[str, str]) -> list[dict]:
    """Языки из таблиц `{заголовок: категория}`. В таблице стандартных языков имя — последняя колонка
    (первая — бросок d12); таблица редких — две колонки имён, читается по столбцам. Сноска «*» отрезается."""
    out = []
    for title, category in tables.items():
        rows = _table(text, title)
        if category == "standard":
            names = [r[-1] for r in rows]
        else:
            names = [r[col] for col in range(len(rows[0])) for r in rows if col < len(r)]
        for name in (n.rstrip("*").strip() for n in names):
            if name:
                out.append({"slug": slugify(name) if lang == "en" else None, "name": name, "name_en": None,
                            "category": category})
    return out
