#!/usr/bin/env python3
"""Гейт таблиц цен главы «Equipment» SRD 5.2 (#547): ресурсы `mounts`, `vehicles`, `services`.

RU-строка получает слаг по позиции EN-строки, поэтому строка не напротив своей дала бы запись с чужой
ценой: числа каждой пары строк сверяются. Запуск: python3 .github/scripts/test_price_tables.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import SOURCES  # noqa: E402
from parsers import parse_price_tables  # noqa: E402

ROOT = Path(__file__).resolve().parents[2] / "src" / "dnd"
failures = []


def check(ok: bool, message: str) -> None:
    if not ok:
        failures.append(message)


def numbers(entity: dict) -> list[str]:
    values = " ".join(str(v) for k, v in entity.items() if k not in ("slug", "name", "name_en", "category") and v)
    return re.findall(r"\d+|[½¼¾]", values.replace(",", ""))


def parsed(lang: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for s in SOURCES:
        if s.get("type") == "price_tables" and s["lang"] == lang:
            out.setdefault(s["out"], []).extend(parse_price_tables((ROOT / s["file"]).read_text(encoding="utf-8"), lang, s["tables"]))
    return out


en, ru = parsed("en"), parsed("ru")
check(sorted(en) == ["mounts", "services", "vehicles"], f"resources: {sorted(en)}")
check(sorted(ru) == sorted(en), f"RU resources: {sorted(ru)}")
for resource, rows in en.items():
    slugs = [r["slug"] for r in rows]
    check(len(set(slugs)) == len(slugs) and all(slugs), f"{resource}: slugs are not unique: {slugs}")
    check(all(r["cost"] for r in rows), f"{resource}: a row without a cost")
    pairs = ru.get(resource, [])
    check(len(pairs) == len(rows), f"{resource}: EN {len(rows)} rows, RU {len(pairs)}")
    for e, r in zip(rows, pairs):
        check(e["category"] == r["category"] and numbers(e) == numbers(r),
              f"{resource}: «{r['name']}» is not the row of «{e['name']}»: {numbers(r)} vs {numbers(e)}")

by_slug = {r["slug"]: r for rows in en.values() for r in rows}
check(by_slug.get("warhorse", {}).get("carrying_capacity") == "540 lb.", "warhorse: carrying capacity")
check(by_slug.get("rowboat", {}).get("damage_threshold", "") is None, "rowboat: a dash is null")
check(by_slug.get("inn-stay-squalid", {}).get("cost") == "7 CP", "lodging: the slug carries the table prefix")
check(by_slug.get("meal-squalid", {}).get("cost") == "1 CP", "meal: its own slug next to the lodging of the same name")
check(by_slug.get("spellcasting-level-9", {}).get("availability") == "City only", "spellcasting: availability")

SAMPLE = "Table: Prices\n\n| Item | Cost |\n|---|---|\n| Ale | 4 CP |\n| Water | — |\n"
table = {"title": "Prices", "category": "food-and-drink", "columns": ["name", "cost"]}
check(parse_price_tables(SAMPLE, "en", [table]) == [
    {"slug": "ale", "name": "Ale", "name_en": None, "category": "food-and-drink", "cost": "4 CP"},
    {"slug": "water", "name": "Water", "name_en": None, "category": "food-and-drink", "cost": None},
], "sample: rows of a table")
check(parse_price_tables(SAMPLE, "ru", [table])[0]["slug"] is None, "sample: a RU row waits for the EN slug")
try:
    parse_price_tables(SAMPLE, "en", [{**table, "columns": ["name", "weight", "cost"]}])
    check(False, "sample: a column count mismatch must raise")
except ValueError:
    pass

if failures:
    print("\n".join(failures))
    sys.exit(1)
print("price tables: mounts, vehicles and services parse, RU rows match EN")
