#!/usr/bin/env python3
"""Ресурсы classes / subclasses JSON API (#365): разбор главы класса, выравнивание RU по EN
и резолв таблиц «всегда подготовленных» заклинаний в слаги.

Запуск: python3 .github/scripts/test_class_parser.py
"""
import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]
sys.path.insert(0, str(SCRIPTS))
import config  # noqa: E402
from generate_api import align_classes, resolve_always_prepared  # noqa: E402
from parsers import parse_class, parse_spells, parse_subclasses  # noqa: E402

failures = []


def eq(name, got, want):
    if got != want:
        failures.append(f"{name}: получили {got!r}, ждали {want!r}")


def read(lang, name):
    return (ROOT / "src/dnd/srd-5.2" / lang / "03_Classes" / name).read_text(encoding="utf-8")


# --- Класс: чародей EN ---------------------------------------------------------------
sorc = parse_class(read("en", "10_Sorcerer.md"), "en")[0]
eq("слаг класса", sorc["slug"], "sorcerer")
eq("кость хитов", sorc["hit_die"], 6)
eq("спасброски", sorc["saving_throws"], ["con", "cha"])
eq("навыки: сколько", sorc["proficiencies"]["skills"]["choose"], 2)
eq("навыки: слаги", sorc["proficiencies"]["skills"]["options"],
   ["arcana", "deception", "insight", "intimidation", "persuasion", "religion"])
eq("доспехи «None» — без категорий", sorc["proficiencies"]["armor"]["categories"], [])
eq("колонки прогрессии", [c["key"] for c in sorc["progression"]["columns"]],
   ["sorcery-points", "cantrips", "prepared-spells"])
eq("строк прогрессии", len(sorc["progression"]["rows"]), 20)
row3 = sorc["progression"]["rows"][2]
eq("прогрессия ур. 3", (row3["level"], row3["proficiency_bonus"], row3["features"],
                        row3["values"], row3["spell_slots"]),
   (3, 2, ["Sorcerer Subclass"], {"sorcery-points": "3", "cantrips": "4", "prepared-spells": "6"},
    [4, 2, 0, 0, 0, 0, 0, 0, 0]))
eq("умения: уровни и имена до 3-го",
   [(f["level"], f["name"]) for f in sorc["features"] if f["level"] <= 3],
   [(1, "Spellcasting"), (1, "Innate Sorcery"), (2, "Font of Magic"), (2, "Metamagic"),
    (3, "Sorcerer Subclass")])
eq("тело умения не захватывает Metamagic Options",
   "Careful Spell" in sorc["features"][-1]["description_md"], False)
eq("заклинательство", sorc["spellcasting"],
   {"feature": "Spellcasting", "level": 1, "ability": "cha", "change_on": "level_up",
    "change_count": "one", "prepare_from": "class_list", "slots": "standard"})

monk = parse_class(read("en", "06_Monk.md"), "en")[0]
eq("монах: частичное воинское оружие не даёт категорию martial",
   monk["proficiencies"]["weapons"]["categories"], ["simple"])
fighter = parse_class(read("en", "05_Fighter.md"), "en")[0]
eq("воин без заклинательства", fighter["spellcasting"], None)
eq("воин: «Strength or Dexterity» — любая из двух", fighter["primary_ability"]["require"], "any")
eq("монах: «Dexterity and Wisdom» — обе", monk["primary_ability"]["require"], "all")
eq("воин: доспехи", fighter["proficiencies"]["armor"]["categories"],
   ["light", "medium", "heavy", "shield"])
eq("воин: оружие", fighter["proficiencies"]["weapons"]["categories"], ["simple", "martial"])
casting = lambda f: {k: v for k, v in parse_class(read("en", f), "en")[0]["spellcasting"].items()
                     if k in ("change_on", "change_count", "prepare_from", "ability")}
eq("друид: подготовка", casting("04_Druid.md"),
   {"change_on": "long_rest", "change_count": "any", "prepare_from": "class_list", "ability": "wis"})
eq("паладин: подготовка", casting("07_Paladin.md"),
   {"change_on": "long_rest", "change_count": "one", "prepare_from": "class_list", "ability": "cha"})
warlock = parse_class(read("en", "11_Warlock.md"), "en")[0]
eq("колдун: ячейки договора", (warlock["spellcasting"]["slots"],
                                warlock["progression"]["rows"][0]["spell_slots"]), ("pact", None))
eq("волшебник готовит из книги",
   parse_class(read("en", "12_Wizard.md"), "en")[0]["spellcasting"]["prepare_from"], "spellbook")
eq("бард: любые навыки — options null",
   parse_class(read("en", "02_Bard.md"), "en")[0]["proficiencies"]["skills"]["options"], None)

# --- Подкласс: драконье чародейство EN --------------------------------------------------
drac = parse_subclasses(read("en", "10_Sorcerer.md"), "en")
eq("подклассов у чародея", [s["slug"] for s in drac], ["draconic-sorcery"])
eq("класс подкласса", drac[0]["class"], "sorcerer")
eq("умения подкласса", [(f["level"], f["name"]) for f in drac[0]["features"]],
   [(3, "Draconic Resilience"), (3, "Draconic Spells"), (6, "Elemental Affinity"),
    (14, "Dragon Wings"), (18, "Dragon Companion")])
eq("таблица Draconic Spells (имена до резолва)", drac[0]["always_prepared"][0],
   {"level": 3, "spells": ["Alter Self", "Chromatic Orb", "Command", "Dragon's Breath"],
    "choice": None})
land = parse_subclasses(read("en", "04_Druid.md"), "en")[0]
eq("Круг Земли: строки четырёх таблиц-альтернатив с choice",
   sorted({r["choice"]["key"] for r in land["always_prepared"]}),
   ["arid-land", "polar-land", "temperate-land", "tropical-land"])

# --- Живой корпус: выравнивание RU и резолв в слаги -----------------------------------
live = {}
for src in config.SOURCES:
    if src["ver"] != "srd52" or src["type"] not in ("class", "subclass", "spell"):
        continue
    text = (ROOT / "src/dnd" / src["file"]).read_text(encoding="utf-8")
    if src["type"] == "spell":
        key, ents = "spells", parse_spells(text, src["h"], src["lang"], src.get("after"),
                                           config.SKIP_HEADINGS_SPELL)
    elif src["type"] == "class":
        key, ents = "classes", parse_class(text, src["lang"])
    else:
        key, ents = "subclasses", parse_subclasses(text, src["lang"])
    live.setdefault(("srd52", src["lang"], key), []).extend(ents)
pristine = copy.deepcopy(live)

eq("живой корпус: ошибок выравнивания и резолва нет",
   align_classes(live) + resolve_always_prepared(live), [])
for lang in ("en", "ru"):
    subs = {s["slug"]: s for s in live[("srd52", lang, "subclasses")]}
    eq(f"{lang}: draconic-sorcery ур. 3",
       subs["draconic-sorcery"]["always_prepared"][0]["spells"],
       ["alter-self", "chromatic-orb", "command", "dragon-s-breath"])
ru_cls = {c["slug"]: c for c in live[("srd52", "ru", "classes")]}
eq("RU чародей: коды из EN, текст свой", (ru_cls["sorcerer"]["name_en"],
                                          ru_cls["sorcerer"]["saving_throws"],
                                          ru_cls["sorcerer"]["spellcasting"]["feature"]),
   ("Sorcerer", ["con", "cha"], "Сотворение заклинаний"))
eq("RU воин: require копируется из EN", ru_cls["fighter"]["primary_ability"]["require"], "any")
eq("RU чародей: values ур. 3 по ключам EN-колонок", ru_cls["sorcerer"]["progression"]["rows"][2]["values"],
   {"sorcery-points": "3", "cantrips": "4", "prepared-spells": "6"})

# --- Отказы ---------------------------------------------------------------------------
bad = copy.deepcopy(pristine)
align_classes(bad)
next(s for s in bad[("srd52", "en", "subclasses")]
     if s["slug"] == "draconic-sorcery")["always_prepared"][0]["spells"][0] = "Alter Selff"
errs = resolve_always_prepared(bad)
eq("неизвестное заклинание — ошибка сборки с именем",
   any("«Alter Selff»" in e for e in errs), True)

bad = copy.deepcopy(pristine)
align_classes(bad)
ru_drac = next(s for s in bad[("srd52", "ru", "subclasses")] if s["slug"] == "draconic-sorcery")
ru_drac["always_prepared"][0]["spells"][2] = "Страх"
errs = resolve_always_prepared(bad)
eq("RU-таблица с другим заклинанием — ошибка расхождения с EN",
   any("ru/draconic-sorcery" in e and "≠ EN" in e for e in errs), True)

bad = copy.deepcopy(pristine)
bad[("srd52", "ru", "classes")][0]["features"].pop()
eq("RU-класс с потерянным умением — ошибка структуры",
   any("структура RU" in e for e in align_classes(bad)), True)


def ru_class_mutant(slug, mutate):
    data = copy.deepcopy(pristine)
    en_slugs = [c["slug"] for c in data[("srd52", "en", "classes")]]
    mutate(data[("srd52", "ru", "classes")][en_slugs.index(slug)])
    return any("структура RU" in e for e in align_classes(data))


def drop_column(c):
    c["progression"]["columns"].pop()
    for row in c["progression"]["rows"]:
        row["values"].pop()


eq("RU-класс без колонки прогрессии — ошибка структуры", ru_class_mutant("sorcerer", drop_column), True)
eq("RU-класс без инструментов — ошибка структуры",
   ru_class_mutant("druid", lambda c: c["proficiencies"].update(tools=None)), True)
eq("RU-класс с другой костью хитов — ошибка структуры",
   ru_class_mutant("barbarian", lambda c: c.update(hit_die=10)), True)
eq("RU-класс с другим числом навыков — ошибка структуры",
   ru_class_mutant("rogue", lambda c: c["proficiencies"]["skills"].update(choose=3)), True)
eq("RU-класс с другой ячейкой кругов — ошибка структуры",
   ru_class_mutant("wizard", lambda c: c["progression"]["rows"][4]["spell_slots"].__setitem__(2, 3)), True)
eq("RU-класс с другим бонусом мастерства — ошибка структуры",
   ru_class_mutant("bard", lambda c: c["progression"]["rows"][4].update(proficiency_bonus=2)), True)
ru_sorc_text = read("ru", "10_Sorcerer.md").replace("| 4 | 2 | — |", "| 4 | 2 | ? |", 1)
try:
    parse_class(ru_sorc_text, "ru")
    eq("нецифровая ячейка кругов — ValueError", "разобрано", "ValueError")
except ValueError as exc:
    eq("нецифровая ячейка кругов — ValueError с уровнем", "spell slot cell '?'" in str(exc), True)

if failures:
    print(f"❌ classes/subclasses ({len(failures)}):")
    for f in failures:
        print(f"  — {f}")
    sys.exit(1)
print("✅ classes/subclasses: разбор, выравнивание RU и резолв always_prepared")
