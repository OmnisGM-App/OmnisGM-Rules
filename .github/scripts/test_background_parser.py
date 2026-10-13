#!/usr/bin/env python3
"""Предыстории SRD 5.2 структурой в JSON API (#413): характеристики, черта с вариантом, навыки и
инструмент кодами и слагами; RU берёт их из EN; слаги сверяются с feats, equipment и classes.

Запуск: python3 .github/scripts/test_background_parser.py
"""
import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]
sys.path.insert(0, str(SCRIPTS))
from generate_api import build_backgrounds  # noqa: E402
from parsers import parse_origins  # noqa: E402

failures = []


def eq(name, got, want):
    if got != want:
        failures.append(f"{name}: получили {got!r}, ждали {want!r}")


SECTION = {"en": "Background Descriptions", "ru": "Описания предысторий"}


def backgrounds(lang):
    text = (ROOT / "src/dnd/srd-5.2" / lang / "04_CharacterOrigins.md").read_text(encoding="utf-8")
    return parse_origins(text, SECTION[lang], lang)


def slugs(*names):
    return [{"slug": n} for n in names]


pristine = {("srd52", lang, "backgrounds"): backgrounds(lang) for lang in ("en", "ru")}
pristine[("srd52", "en", "feats")] = slugs("magic-initiate", "alert", "savage-attacker")
pristine[("srd52", "en", "equipment")] = slugs("calligrapher-s-supplies", "thieves-tools", "gaming-set")
pristine[("srd52", "en", "classes")] = slugs("cleric", "wizard")
live = copy.deepcopy(pristine)
eq("живой корпус: ошибок нет", build_backgrounds(live), [])

# Предыстория → (характеристики, черта, вариант, навыки, инструмент, выбор инструмента).
BACKGROUNDS = {
    "acolyte": (["int", "wis", "cha"], "magic-initiate", "cleric", ["insight", "religion"], "calligrapher-s-supplies", None),
    "criminal": (["dex", "con", "int"], "alert", None, ["sleight-of-hand", "stealth"], "thieves-tools", None),
    "sage": (["con", "int", "wis"], "magic-initiate", "wizard", ["arcana", "history"], "calligrapher-s-supplies", None),
    "soldier": (["str", "dex", "con"], "savage-attacker", None, ["athletics", "intimidation"], None, "gaming-set"),
}
for lang in ("en", "ru"):
    eq(f"{lang}: коды и слаги четырёх предысторий",
       {b["slug"]: (b["ability_scores"]["abilities"], b["feat"]["slug"], b["feat"]["variant"], b["skills"]["slugs"],
                    b["tool"]["slug"], b["tool"]["choose_from"]) for b in live[("srd52", lang, "backgrounds")]},
       BACKGROUNDS)
en = {b["slug"]: b for b in live[("srd52", "en", "backgrounds")]}
ru = {b["slug"]: b for b in live[("srd52", "ru", "backgrounds")]}
eq("EN: текст фактов без отсылок «see …» и без курсива",
   (en["acolyte"]["feat"]["text"], en["soldier"]["tool"]["text"], en["sage"]["skills"]["text"],
    en["criminal"]["equipment"][:16]),
   ("Magic Initiate (Cleric)", "Choose one kind of Gaming Set", "Arcana and History", "*Choose A or B:*"))
eq("RU: текст свой", (ru["acolyte"]["feat"]["text"], ru["soldier"]["tool"]["text"], ru["sage"]["ability_scores"]["text"]),
   ("Посвящённый в магию (Жрец)", "Выберите один игровой набор", "Телосложение, Интеллект, Мудрость"))
eq("описание предыстории не тронуто", [b["description_md"] for b in live[("srd52", "en", "backgrounds")]],
   [b["description_md"] for b in pristine[("srd52", "en", "backgrounds")]])


# --- Отказы ---------------------------------------------------------------------------
def broken(lang, slug, old, new, drop=None):
    data = copy.deepcopy(pristine)
    if drop:
        data[("srd52", "en", drop[0])] = [e for e in data[("srd52", "en", drop[0])] if e["slug"] != drop[1]]
    target = next(b for b in data[("srd52", lang, "backgrounds")] if b["slug"] == slug)
    if old not in target["description_md"]:
        return [f"нет фрагмента {old!r}"]
    target["description_md"] = target["description_md"].replace(old, new)
    return build_backgrounds(data)


eq("предыстория без строки черты роняет сборку",
   [e[:44] for e in broken("en", "criminal", "**Feat:**", "Feat:")], ["srd52: Criminal: background facts ['Ability "])
eq("незнакомая характеристика роняет сборку",
   broken("en", "sage", "Constitution, Intelligence, Wisdom", "Constitution, Intellect, Wisdom"),
   ["srd52: Sage: three ability scores expected in 'Constitution, Intellect, Wisdom'"])
eq("незнакомый навык роняет сборку", broken("en", "sage", "Arcana and History", "Arcana and Lore"),
   ["srd52: Sage: two known skills expected in 'Arcana and Lore'"])
eq("черта, которой нет в feats, роняет сборку", broken("en", "criminal", "", "", drop=("feats", "alert")),
   ["srd52/en/criminal: feat «alert» не найден в feats"])
eq("вариант черты, которого нет в classes, роняет сборку", broken("en", "sage", "", "", drop=("classes", "wizard")),
   ["srd52/en/sage: feat variant «wizard» не найден в classes"])
eq("инструмент, которого нет в equipment, роняет сборку",
   broken("en", "criminal", "", "", drop=("equipment", "thieves-tools")),
   ["srd52/en/criminal: tool «thieves-tools» не найден в equipment"])
eq("родитель выбора инструмента, которого нет в equipment, роняет сборку",
   broken("en", "soldier", "", "", drop=("equipment", "gaming-set")),
   ["srd52/en/soldier: tool choice «gaming-set» не найден в equipment"])
eq("RU-предыстория без строки навыков роняет сборку",
   [e[:35] for e in broken("ru", "acolyte", "**Владение навыками:**", "Владение навыками:")],
   ["srd52: Послушник: background facts "])

if failures:
    print(f"❌ backgrounds ({len(failures)}):")
    for f in failures:
        print(f"  — {f}")
    sys.exit(1)
print("✅ backgrounds: коды и слаги 4 предысторий, RU из EN, сверка с feats/equipment/classes, отказы")
