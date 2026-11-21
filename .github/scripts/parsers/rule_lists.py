"""Списки правил SRD 5.2 из именованных таблиц глав (#482): ресурс `languages` и подписи членов списков выбора."""

import re

from .base import slugify

_TITLE = re.compile(r"^(?:Table|Таблица): (.+)$")


def _table(text: str, title: str) -> list[list[str]]:
    """Строки таблицы под строкой «Table: <title>» без шапки и разделителя."""
    return _table_with_head(text, title)[1]


def _table_with_head(text: str, title: str) -> tuple[list[str], list[list[str]]]:
    """Шапка и строки таблицы под строкой «Table: <title>»."""
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
    head, rows = (rows[0] if rows else []), [r for r in rows[1:] if not set("".join(r)) <= set("-: ")]
    if not rows:
        raise ValueError(f"table «{title}» has no rows")
    return head, rows


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


def _titled_name(label: str, head: str, cell: str, lang: str) -> str:
    """Имя строки с контекстом таблицы, в форме самого источника («Meal - Squalid», «Еда, убогая»)."""
    part = f"{head} {cell}" if cell[:1].isdigit() else cell
    return f"{label} - {part}" if lang == "en" else f"{label}, {part[:1].lower()}{part[1:]}"


def parse_price_tables(text: str, lang: str, tables: list[dict]) -> list[dict]:
    """Строки таблиц цен главы «Equipment»: `{title, category, columns, prefix, titled, unit}` на таблицу.

    `columns` — ключи полей по позиции колонки (первая — `name`), прочерк в ячейке — None. Слаг — из
    EN-ячейки с `prefix`; RU получает слаг и `name_en` по позиции строки (`align_positional_name_en`).
    `titled` — имя собирается из заголовка таблицы и ячейки, у ячейки-числа перед ней слово шапки колонки;
    `unit` — хвост заголовка («per Day»): уходит из имени в цену.
    """
    out = []
    for table in tables:
        title, unit = table["title"], table.get("unit")
        if unit and not title.endswith(f" {unit}"):
            raise ValueError(f"table «{title}» does not end with its unit «{unit}»")
        label = title[: -len(unit) - 1] if unit else title
        head, rows = _table_with_head(text, title)
        for row in rows:
            if len(row) != len(table["columns"]):
                raise ValueError(f"table «{title}»: {len(row)} cells, {len(table['columns'])} columns declared")
            cells = dict(zip(table["columns"], row))
            cell = cells.pop("name")
            slug = slugify(f"{table.get('prefix', '')} {cell}") if lang == "en" else None
            fields = {key: None if value in ("—", "-", "") else value for key, value in cells.items()}
            if unit and fields.get("cost"):
                fields["cost"] = f"{fields['cost']} {unit.lower()}"
            name = _titled_name(label, head[0], cell, lang) if table.get("titled") else cell
            out.append({"slug": slug, "name": name, "name_en": None, "category": table["category"], **fields})
    return out
