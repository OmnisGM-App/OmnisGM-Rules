#!/usr/bin/env python3
"""Составное снаряжение SRD 5.2 в JSON API (#412): записи-таблицы уходят в `equipment-groups`,
их разновидности — отдельные записи `equipment` со своей ценой и весом; RU выравнивается по EN.

Запуск: python3 .github/scripts/test_equipment_groups.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]
sys.path.insert(0, str(SCRIPTS))
import config  # noqa: E402
from generate_api import build_equipment_groups  # noqa: E402
from parsers import parse_equipment  # noqa: E402

failures = []


def eq(name, got, want):
    if got != want:
        failures.append(f"{name}: получили {got!r}, ждали {want!r}")


def source(lang):
    return next(s for s in config.SOURCES if s["ver"] == "srd52" and s["lang"] == lang and s["type"] == "equipment")


def text(lang):
    return (ROOT / "src/dnd" / source(lang)["file"]).read_text(encoding="utf-8")


def parsed(lang, body=None):
    src = source(lang)
    return parse_equipment(body if body is not None else text(lang), src["h"], lang, src.get("after"),
                           getattr(config, "SKIP_HEADINGS_EQUIPMENT", None))


def build(en_text=None, ru_text=None):
    data = {("srd52", "en", "equipment"): parsed("en", en_text), ("srd52", "ru", "equipment"): parsed("ru", ru_text)}
    return data, build_equipment_groups(data)


live, errors = build()
eq("живой корпус: ошибок нет", errors, [])

# Группа → (EN-имя, предметы: слаг, цена, вес). Выписано из таблиц и строк «Variants» главы «Equipment».
GROUPS = {
    "ammunition": ("Ammunition", [("arrows", "1 GP", "1 lb."), ("bolts", "1 GP", "1½ lb."), ("bullets-firearm", "3 GP", "2 lb."),
                                  ("bullets-sling", "4 CP", "1½ lb."), ("needles", "1 GP", "1 lb.")]),
    "arcane-focus": ("Arcane Focus", [("crystal", "10 GP", "1 lb."), ("orb", "20 GP", "3 lb."), ("rod", "10 GP", "2 lb."),
                                      ("staff", "5 GP", "4 lb."), ("wand", "10 GP", "1 lb.")]),
    "druidic-focus": ("Druidic Focus", [("sprig-of-mistletoe", "1 GP", None), ("wooden-staff", "5 GP", "4 lb."),
                                        ("yew-wand", "10 GP", "1 lb.")]),
    "gaming-set": ("Gaming Set", [("dice", "1 SP", None), ("dragonchess", "1 GP", None), ("playing-cards", "5 SP", None),
                                  ("three-dragon-ante", "1 GP", None)]),
    "holy-symbol": ("Holy Symbol", [("amulet", "5 GP", "1 lb."), ("emblem", "5 GP", None), ("reliquary", "5 GP", "2 lb.")]),
    "musical-instrument": ("Musical Instrument", [
        ("bagpipes", "30 GP", "6 lb."), ("drum", "6 GP", "3 lb."), ("dulcimer", "25 GP", "10 lb."), ("flute", "2 GP", "1 lb."),
        ("horn", "3 GP", "2 lb."), ("lute", "35 GP", "2 lb."), ("lyre", "30 GP", "2 lb."), ("pan-flute", "12 GP", "2 lb."),
        ("shawm", "2 GP", "1 lb."), ("viol", "30 GP", "1 lb.")]),
}
en = {e["slug"]: e for e in live[("srd52", "en", "equipment")]}
ru = {e["slug"]: e for e in live[("srd52", "ru", "equipment")]}
en_groups = {g["slug"]: g for g in live[("srd52", "en", "equipment-groups")]}
ru_groups = {g["slug"]: g for g in live[("srd52", "ru", "equipment-groups")]}
eq("EN: шесть групп, 30 предметов со своей ценой и весом",
   {slug: (g["name"], [(i, en[i]["cost"], en[i]["weight"]) for i in g["items"]]) for slug, g in en_groups.items()}, GROUPS)
eq("записи-таблицы ушли из equipment", sorted(set(GROUPS) & set(en)), [])
eq("у предмета — слаг своей группы, у остального снаряжения — null",
   ({e["group"] for e in en.values() if e["slug"] not in {i for _, items in GROUPS.values() for i, _, _ in items}},
    {slug: en[i]["group"] for slug, (_, items) in GROUPS.items() for i, _, _ in items[:1]}),
   ({None}, {slug: slug for slug in GROUPS}))
eq("пачки боеприпасов: число и хранение",
   {i: (en[i]["quantity"], en[i]["storage"]) for i in en_groups["ammunition"]["items"]},
   {"arrows": (20, "Quiver"), "bolts": (20, "Case"), "bullets-firearm": (10, "Pouch"), "bullets-sling": (20, "Pouch"),
    "needles": (50, "Pouch")})
eq("таблица «Adventuring Gear» ушла из описаний", [slug for slug, e in en.items() if "Alchemist's Fire" in e["description_md"]
                                                   and "|" in e["description_md"]], [])
for lang, items, groups in (("en", en, en_groups), ("ru", ru, ru_groups)):
    eq(f"{lang}: в описаниях предметов и групп нет ни таблиц, ни их заголовков",
       [slug for slug, e in {**items, **{f"group:{k}": v for k, v in groups.items()}}.items()
        if (e.get("group") or slug.startswith("group:"))
        and ("|" in e["description_md"] or "Table:" in e["description_md"] or "Таблица:" in e["description_md"])], [])
eq("пометка из скобок — первой строкой описания",
   (en["staff"]["name"], en["staff"]["description_md"][:20], en["amulet"]["description_md"][:13], en["wooden-staff"]["name"]),
   ("Staff", "Also a Quarterstaff.", "Worn or held.", "Wooden Staff"))
eq("разновидность инструмента: свойства группы, свой вес в тексте",
   (en["lute"]["ability"], en["lute"]["utilize"][:17], en["lute"]["section"], "**Weight:** 2 lb." in en["lute"]["description_md"],
    "Variants" in en["lute"]["description_md"], en["dice"]["weight"], "**Weight:** —" in en["dice"]["description_md"]),
   ("Charisma", "Play a known tune", "tools", True, False, None, True))
eq("имена: заглавные по словам, служебные слова строчными",
   [en[s]["name"] for s in ("three-dragon-ante", "sprig-of-mistletoe", "playing-cards", "pan-flute", "bullets-firearm")],
   ["Three-Dragon Ante", "Sprig of Mistletoe", "Playing Cards", "Pan Flute", "Bullets, Firearm"])

# RU: слаг и name_en — от EN по позиции в группе; эталон имён ловит перестановку строк.
RU_NAMES = {
    "arrows": "Стрелы", "bolts": "Болты", "bullets-firearm": "Пули огнестрельные", "bullets-sling": "Снаряды для пращи",
    "needles": "Иглы", "crystal": "Кристалл", "orb": "Сфера", "rod": "Скипетр", "staff": "Посох", "wand": "Жезл",
    "sprig-of-mistletoe": "Веточка омелы", "wooden-staff": "Деревянный посох", "yew-wand": "Тисовый жезл",
    "dice": "Кости", "dragonchess": "Драконьи шахматы", "playing-cards": "Игральные карты",
    "three-dragon-ante": "Трёхдраконовое анте", "amulet": "Амулет", "emblem": "Эмблема", "reliquary": "Реликварий",
    "bagpipes": "Волынка", "drum": "Барабан", "dulcimer": "Цимбалы", "flute": "Флейта", "horn": "Рожок", "lute": "Лютня",
    "lyre": "Лира", "pan-flute": "Свирель", "shawm": "Шалмей", "viol": "Виола",
}
eq("RU: имя каждого предмета под слагом EN", {s: ru[s]["name"] for s in RU_NAMES}, RU_NAMES)
eq("RU: name_en и группа — как у EN",
   {s: (ru[s]["name_en"], ru[s]["group"]) for s in RU_NAMES}, {s: (en[s]["name"], en[s]["group"]) for s in RU_NAMES})
eq("RU-группы: те же слаги и предметы, имя своё",
   ({slug: g["items"] for slug, g in ru_groups.items()}, ru_groups["musical-instrument"]["name"], ru["lute"]["cost"]),
   ({slug: g["items"] for slug, g in en_groups.items()}, "Музыкальный инструмент", "35 зм"))
eq("всего снаряжения: 130 записей в каждом языке", (len(en), len(ru)), (130, 130))


# --- Отказы ---------------------------------------------------------------------------
def broken(lang, old, new):
    body = text(lang)
    if old not in body:
        return [f"нет фрагмента {old!r}"]
    try:
        return build(**{f"{lang}_text": body.replace(old, new)})[1]
    except ValueError as err:
        return [str(err)]


eq("строка таблицы пропала — сборка падает",
   broken("en", "| Needles          | 50     | Pouch   | 1 lb.  | 1 GP |\n", ""), ["Ammunition: 4 varieties, declared 5"])
eq("вариант инструмента пропал — сборка падает",
   broken("en", "Dice (1 SP), dragonchess (1 GP)", "Dice (1 SP)"), ["Gaming Set: 3 varieties, declared 4"])
eq("число в пачке не число — сборка падает",
   broken("en", "| Arrows           | 20     |", "| Arrows           | many   |"), ["Ammunition: amount 'many' of 'Arrows' is not a number"])
eq("RU-таблица без строки — сборка падает",
   broken("ru", "| Иглы | 50 | Кошель | 1 фнт. | 1 зм |\n", ""), ["Боеприпасы: 4 varieties, declared 5"])
eq("RU-строки переставлены — цена не сходится с EN",
   broken("ru", "Кости (1 см), драконьи шахматы (1 зм)", "Драконьи шахматы (1 зм), кости (1 см)"),
   ["srd52/ru/gaming-set: «Драконьи шахматы» не сходится с EN «Dice» по цене, весу или числу",
    "srd52/ru/gaming-set: «Кости» не сходится с EN «Dragonchess» по цене, весу или числу"])
eq("RU-предмет с другим весом — не сходится с EN",
   broken("ru", "| Сфера | 3 фнт. |", "| Сфера | 4 фнт. |"),
   ["srd52/ru/arcane-focus: «Сфера» не сходится с EN «Orb» по цене, весу или числу"])
eq("строка таблицы без ячейки — сборка падает",
   broken("en", "| Needles          | 50     | Pouch   | 1 lb.  | 1 GP |", "| Needles          | 50     | Pouch   | 1 GP |"),
   ["Ammunition: row 'Needles' has 4 cells, the header has 5"])
eq("RU-пачка с другим числом — не сходится с EN",
   broken("ru", "| Стрелы | 20 |", "| Стрелы | 30 |"),
   ["srd52/ru/ammunition: «Стрелы» не сходится с EN «Arrows» по цене, весу или числу"])

# Группа — не ресурс API: в публичной сборке её нет, в сборке сайта (--site-data) есть.
with tempfile.TemporaryDirectory() as out:
    for flags, want in (([], False), (["--site-data"], True)):
        run = subprocess.run([sys.executable, str(SCRIPTS / "generate_api.py"), "--src-root", str(ROOT / "src/dnd"),
                              "--output-dir", f"{out}/{len(flags)}", "--no-validate", *flags], capture_output=True, text=True)
        eq(f"generate_api {' '.join(flags) or 'без флага'}: сборка прошла", run.returncode, 0)
        eq(f"generate_api {' '.join(flags) or 'без флага'}: equipment-groups {'есть' if want else 'нет'}",
           [(Path(out) / str(len(flags)) / "dnd/srd52" / lang / "equipment-groups").exists() for lang in ("en", "ru")],
           [want, want])
        eq(f"generate_api {' '.join(flags) or 'без флага'}: предметы групп в equipment на месте",
           (Path(out) / str(len(flags)) / "dnd/srd52/en/equipment/all.json").read_text(encoding="utf-8").count('"group": "ammunition"'), 5)

if failures:
    print(f"❌ equipment-groups ({len(failures)}):")
    for f in failures:
        print(f"  — {f}")
    sys.exit(1)
print("✅ equipment-groups: 6 групп и 30 предметов с ценой и весом, пачки, RU по EN, отказы")
