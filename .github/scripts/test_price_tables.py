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


UNITS = {"зм": "gp", "см": "sp", "мм": "cp", "день": "day", "милю": "mile", "фнт": "lb"}
UNIT = re.compile(r"\d+|[½¼¾]|\b(?:gp|sp|cp|day|mile|lb|" + "|".join(UNITS) + r")\b")


def numbers(entity: dict) -> list[str]:
    """Числа и единицы строки (монета, «в день», «за милю») — одинаковые в EN и RU."""
    values = " ".join(str(v) for k, v in entity.items() if k not in ("slug", "name", "name_en", "category", "availability") and v)
    return [UNITS.get(token, token) for token in UNIT.findall(values.replace(",", "").lower())]


def grouping(values: list) -> list[int]:
    """Какие строки делят одно значение: «Town or city only» у тех же строк, что и его перевод."""
    return [values.index(v) for v in values]


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
    check(grouping([r.get("availability") for r in pairs]) == grouping([e.get("availability") for e in rows]),
          f"{resource}: RU availability does not repeat where EN does")

by_slug = {r["slug"]: r for rows in en.values() for r in rows}
check(by_slug.get("warhorse", {}).get("carrying_capacity") == "540 lb.", "warhorse: carrying capacity")
check(by_slug.get("rowboat", {}).get("damage_threshold", "") is None, "rowboat: a dash is null")
check(by_slug.get("inn-stay-squalid", {}).get("cost") == "7 CP per day", "lodging: the unit of the table title goes into the cost")
check(by_slug.get("inn-stay-squalid", {}).get("name") == "Inn Stay - Squalid", "lodging: the name carries the table title without its unit")
check(by_slug.get("spellcasting-level-cantrip", {}).get("name") == "Spellcasting Services - Cantrip", "spellcasting: a word row keeps its cell")
check(by_slug.get("spellcasting-level-4-5", {}).get("name") == "Spellcasting Services - Spell Level 4—5",
      "spellcasting: a number row takes the column heading")
ru_names = [r["name"] for r in ru["services"]]
check("Проживание в таверне, убогое" in ru_names and "Услуги заклинателей, заговор" in ru_names
      and "Услуги заклинателей, уровень заклинания 9" in ru_names, f"RU titled names: {ru_names}")
check(all(r["cost"].endswith(" в день") for r in ru["services"] if r["category"] == "lodging"), "RU lodging: «в день» in the cost")
SERVICE_SLUGS = (
    "ale-mug bread-loaf cheese-wedge meal-squalid meal-poor meal-modest meal-comfortable meal-wealthy meal-aristocratic "
    "wine-bottle-common wine-bottle-fine inn-stay-squalid inn-stay-poor inn-stay-modest inn-stay-comfortable inn-stay-wealthy "
    "inn-stay-aristocratic skilled-hireling untrained-hireling messenger spellcasting-level-cantrip spellcasting-level-1 "
    "spellcasting-level-2 spellcasting-level-3 spellcasting-level-4-5 spellcasting-level-6-8 spellcasting-level-9"
).split()
check([r["slug"] for r in en["services"]] == SERVICE_SLUGS, f"services: slugs moved: {[r['slug'] for r in en['services']]}")
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

TITLED = "Table: Stay per Night\n\n| Room | Cost |\n|---|---|\n| Poor | 1 SP |\n| 2 | — |\n"
titled = {"title": "Stay per Night", "category": "lodging", "columns": ["name", "cost"], "prefix": "stay", "titled": True, "unit": "per Night"}
check(parse_price_tables(TITLED, "en", [titled]) == [
    {"slug": "stay-poor", "name": "Stay - Poor", "name_en": None, "category": "lodging", "cost": "1 SP per night"},
    {"slug": "stay-2", "name": "Stay - Room 2", "name_en": None, "category": "lodging", "cost": None},
], f"titled sample: {parse_price_tables(TITLED, 'en', [titled])}")
check(parse_price_tables(TITLED, "ru", [titled])[0]["name"] == "Stay, poor", "titled sample: the RU form is «title, cell» in lower case")
check(parse_price_tables(TITLED, "en", [{**titled, "titled": False, "unit": None}])[0]["name"] == "Poor", "titled sample: off by default")
try:
    parse_price_tables(TITLED, "en", [{**titled, "unit": "per Day"}])
    check(False, "titled sample: a title that does not end with the unit must raise")
except ValueError:
    pass

if failures:
    print("\n".join(failures))
    sys.exit(1)
print("price tables: mounts, vehicles and services parse, RU rows match EN")
