#!/usr/bin/env python3
"""Ресурсы classes / subclasses / class-options JSON API (#365, #374): разбор главы класса,
выравнивание RU по EN, резолв таблиц «всегда подготовленных» заклинаний и предусловий-воззваний
в слаги.

Запуск: python3 .github/scripts/test_class_parser.py
"""
import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]
sys.path.insert(0, str(SCRIPTS))
import config  # noqa: E402
from generate_api import (align_class_options, align_classes, disambiguate_option_slugs,  # noqa: E402
                          resolve_always_prepared, slug_collisions)
from parsers import parse_class, parse_class_options, parse_spells, parse_subclasses  # noqa: E402
from parsers.classes import CANTRIP_PREREQS, COST_UNITS  # noqa: E402
from schemas import CLASS_OPTION_SCHEMA  # noqa: E402

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
eq("RU чародей: навыки из EN", ru_cls["sorcerer"]["proficiencies"]["skills"]["options"],
   ["arcana", "deception", "insight", "intimidation", "persuasion", "religion"])
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
eq("RU-класс со сдвинутым уровнем строки — ошибка структуры",
   ru_class_mutant("bard", lambda c: c["progression"]["rows"][4].update(level=6)), True)
eq("RU-класс с лишним умением в строке — ошибка структуры",
   ru_class_mutant("bard", lambda c: c["progression"]["rows"][4]["features"].append("x")), True)
eq("RU-класс с другим числом в колонке — ошибка структуры",
   ru_class_mutant("warlock", lambda c: c["progression"]["rows"][0]["values"].__setitem__(0, "9")), True)
eq("RU-колонка кости «к6» ≡ EN «D6»",
   ru_class_mutant("bard", lambda c: c["progression"]["rows"][0]["values"].__setitem__(0, "к6")), False)

bad = copy.deepcopy(pristine)
bad[("srd52", "ru", "subclasses")][0]["features"].pop()
eq("RU-подкласс с потерянным умением — ошибка структуры",
   any("subclasses: структура RU" in e for e in align_classes(bad)), True)
bad = copy.deepcopy(pristine)
bad[("srd52", "ru", "subclasses")].pop()
eq("RU без одного подкласса — ошибка числа записей",
   any("subclasses: EN" in e and ", RU " in e for e in align_classes(bad)), True)
ru_sorc_text = read("ru", "10_Sorcerer.md").replace("| 4 | 2 | — |", "| 4 | 2 | ? |", 1)
try:
    parse_class(ru_sorc_text, "ru")
    eq("нецифровая ячейка кругов — ValueError", "разобрано", "ValueError")
except ValueError as exc:
    eq("нецифровая ячейка кругов — ValueError с уровнем", "Чародей: progression level 3: spell slot cell '?'" in str(exc), True)

# --- Варианты классовых умений (#374) -------------------------------------------------
CLASS_FILES = sorted(p.name for p in (ROOT / "src/dnd/srd-5.2/en/03_Classes").glob("[01][0-9]_*.md")
                     if not p.name.startswith("00_"))
# Сверка с исходником: число вариантов на главу, посчитанное руками по markdown.
EXPECTED_OPTIONS = {"01_Barbarian.md": 4, "02_Bard.md": 0, "03_Cleric.md": 4, "04_Druid.md": 4,
                    "05_Fighter.md": 0, "06_Monk.md": 3, "07_Paladin.md": 1, "08_Ranger.md": 5,
                    "09_Rogue.md": 7, "10_Sorcerer.md": 10, "11_Warlock.md": 28, "12_Wizard.md": 0}
for lang in ("en", "ru"):
    eq(f"{lang}: вариантов по главам",
       {f: len(parse_class_options(read(lang, f), lang)) for f in CLASS_FILES}, EXPECTED_OPTIONS)


def section_headings(lang, name, title):
    """Независимый счёт: #### внутри раздела «### title» до следующего ###."""
    inside, n = False, 0
    for line in read(lang, name).split("\n"):
        if line.startswith("### "):
            inside = line[4:].strip() == title
        elif inside and line.startswith("#### "):
            n += 1
    return n


eq("воззвания = #### раздела EN", section_headings("en", "11_Warlock.md", "Eldritch Invocation Options"), 28)
eq("воззвания = #### раздела RU", section_headings("ru", "11_Warlock.md", "Опции таинственных воззваний"), 28)
eq("метамагия = #### раздела EN", section_headings("en", "10_Sorcerer.md", "Metamagic Options"), 10)
eq("метамагия = #### раздела RU", section_headings("ru", "10_Sorcerer.md", "Опции Метамагии"), 10)

inv = {o["slug"]: o for o in parse_class_options(read("en", "11_Warlock.md"), "en")}
eq("воззвание: родитель", inv["agonizing-blast"]["feature"],
   {"key": "eldritch-invocations", "name": "Eldritch Invocations", "level": 1})
eq("воззвание: предусловие уровень + заговор", inv["agonizing-blast"]["prerequisites"],
   {"text": "Level 2+ Warlock, a Warlock Cantrip That Deals Damage", "level": 2, "options": [],
    "cantrip": "damage"})
eq("воззвание: заговор с броском атаки", inv["repelling-blast"]["prerequisites"]["cantrip"],
   "damage-attack-roll")
eq("воззвание: предусловие-воззвание (имя до резолва)",
   inv["devouring-blade"]["prerequisites"]["options"], ["Thirsting Blade"])
eq("воззвание без предусловия", inv["armor-of-shadows"]["prerequisites"], None)
eq("повторяемые воззвания", sorted(s for s, o in inv.items() if o["repeatable"]),
   ["agonizing-blast", "eldritch-spear", "lessons-of-the-first-ones", "repelling-blast"])
eq("строка предусловия не дублируется в описании",
   any("Prerequisite" in o["description_md"] for o in inv.values()), False)
eq("абзац Repeatable остаётся в описании",
   "**Repeatable.**" in inv["agonizing-blast"]["description_md"], True)
eq("воззвания учатся (learned), без стоимости",
   {(o["selection"], o["cost"] is None) for o in inv.values()}, {("learned", True)})

meta = {o["slug"]: o for o in parse_class_options(read("en", "10_Sorcerer.md"), "en")}
eq("метамагия: родитель ур. 2", meta["careful-spell"]["feature"],
   {"key": "metamagic", "name": "Metamagic", "level": 2})
eq("метамагия: стоимость 2 очка", meta["heightened-spell"]["cost"],
   {"text": "2 Sorcery Points", "amount": 2, "unit": "sorcery-point"})
eq("метамагия: стоимость по вариантам",
   sorted((s, o["cost"]["amount"]) for s, o in meta.items() if o["cost"]["amount"] != 1),
   [("heightened-spell", 2), ("quickened-spell", 2)])
eq("строка стоимости не дублируется в описании",
   any("Cost:" in o["description_md"] for o in meta.values()), False)

rogue = {o["slug"]: o for o in parse_class_options(read("en", "09_Rogue.md"), "en")}
eq("Cunning Strike: стоимость в костях Скрытой атаки", rogue["knock-out"]["cost"],
   {"text": "6d6", "amount": 6, "unit": "sneak-attack-die"})
eq("Cunning Strike: имя без «(Cost: …)»", rogue["poison"]["name"], "Poison")
eq("абзац-продолжение остаётся у варианта", "Poisoner's Kit" in rogue["poison"]["description_md"], True)
eq("Devious Strikes пополняет Cunning Strike", (rogue["daze"]["feature"]["key"], rogue["daze"]["granted_by"]),
   ("cunning-strike", {"key": "devious-strikes", "name": "Devious Strikes", "level": 14}))
eq("Supreme Sneak: курсивный вариант подкласса Thief",
   (rogue["stealth-attack"]["subclass"], rogue["stealth-attack"]["feature"]["key"],
    rogue["stealth-attack"]["granted_by"]["key"], rogue["stealth-attack"]["cost"]["amount"]),
   ("thief", "cunning-strike", "supreme-sneak", 1))
eq("Cunning Strike выбирается при применении", {o["selection"] for o in rogue.values()}, {"on_use"})

barb = {o["slug"]: o for o in parse_class_options(read("en", "01_Barbarian.md"), "en")}
eq("Brutal Strike: «of your choice» вне фразы-маркера — всё равно on_use",
   {o["selection"] for o in barb.values()}, {"on_use"})
eq("Improved Brutal Strike пополняет Brutal Strike",
   (barb["sundering-blow"]["feature"]["key"], barb["sundering-blow"]["granted_by"]["key"]),
   ("brutal-strike", "improved-brutal-strike"))
cleric = parse_class_options(read("en", "03_Cleric.md"), "en")
eq("жрец: варианты и родители", [(o["slug"], o["feature"]["key"], o["selection"]) for o in cleric],
   [("protector", "divine-order", "learned"), ("thaumaturge", "divine-order", "learned"),
    ("divine-strike", "blessed-strikes", "learned"), ("potent-spellcasting", "blessed-strikes", "learned")])
hunter = parse_class_options(read("en", "08_Ranger.md"), "en")
eq("следопыт: варианты подкласса Hunter и Druidic Warrior класса",
   {(o["subclass"], o["feature"]["key"]) for o in hunter},
   {(None, "fighting-style"), ("hunter", "hunter-s-prey"), ("hunter", "defensive-tactics")})
paladin = parse_class_options(read("en", "07_Paladin.md"), "en")
eq("паладин: Blessed Warrior — альтернатива черте Fighting Style",
   [(o["slug"], o["feature"], o["selection"], o["cost"], o["prerequisites"]) for o in paladin],
   [("blessed-warrior", {"key": "fighting-style", "name": "Fighting Style", "level": 2},
     "learned", None, None)])
eq("Druidic Warrior: learned", [o["selection"] for o in hunter if o["slug"] == "druidic-warrior"],
   ["learned"])
monk = parse_class_options(read("en", "06_Monk.md"), "en")
eq("монах: Open Hand Technique при применении", [(o["slug"], o["subclass"], o["selection"]) for o in monk],
   [(s, "warrior-of-the-open-hand", "on_use") for s in ("addle", "push", "topple")])
eq("Fast Hands («one of the following.») — не список вариантов",
   any(o["feature"]["key"] == "fast-hands" for o in rogue.values()), False)

for bad_text, label in (
        (read("en", "10_Sorcerer.md").replace("*Cost: 2 Sorcery Points*", "*Cost: 2 Focus Points*", 1),
         "unknown option cost '2 Focus Points'"),
        (read("en", "11_Warlock.md").replace("Level 15+ Warlock*", "Level 15+ Warlock, Elf*", 1),
         "unknown prerequisite 'Elf'"),
        (read("en", "11_Warlock.md").replace('"Eldritch Invocation Options"', '"Invocation List"', 1),
         "no feature refers to section 'Eldritch Invocation Options'")):
    try:
        parse_class_options(bad_text, "en")
        eq(f"{label} — ValueError", "разобрано", "ValueError")
    except ValueError as exc:
        eq(f"{label} — ValueError", label in str(exc), True)

eq("перечисления схемы = перечисления парсера",
   (CLASS_OPTION_SCHEMA["properties"]["cost"]["anyOf"][1]["properties"]["unit"]["enum"],
    CLASS_OPTION_SCHEMA["properties"]["prerequisites"]["anyOf"][1]["properties"]["cantrip"]["enum"]),
   (list(COST_UNITS), [None, *CANTRIP_PREREQS]))

opts = {}
for src in config.SOURCES:
    if src["ver"] == "srd52" and src["type"] == "class_option":
        text = (ROOT / "src/dnd" / src["file"]).read_text(encoding="utf-8")
        opts.setdefault(("srd52", src["lang"], "class-options"), []).extend(
            parse_class_options(text, src["lang"]))
opts_pristine = copy.deepcopy(opts)
eq("живой корпус: 66 вариантов в EN и RU",
   [len(opts[("srd52", lang, "class-options")]) for lang in ("en", "ru")], [66, 66])
disambiguate_option_slugs(opts)
eq("живой корпус: выравнивание вариантов без ошибок", align_class_options(opts), [])
eq("живой корпус: слаги вариантов уникальны", slug_collisions(opts, "dnd"), [])
for lang in ("en", "ru"):
    by = {o["slug"]: o for o in opts[("srd52", lang, "class-options")]}
    eq(f"{lang}: одноимённые варианты — с префиксом класса, прочие — нет",
       sorted(s for s in by if "potent-spellcasting" in s) + [s for s in ("primal-strike",) if s in by],
       ["cleric-potent-spellcasting", "druid-potent-spellcasting", "primal-strike"])
    eq(f"{lang}: предусловие-воззвание резолвится в слаг",
       by["devouring-blade"]["prerequisites"]["options"], ["thirsting-blade"])
    try:
        import jsonschema
        for o in by.values():
            jsonschema.validate(o, CLASS_OPTION_SCHEMA)
    except ImportError:
        pass
ru_opt = {o["slug"]: o for o in opts[("srd52", "ru", "class-options")]}
eq("RU воззвание: коды из EN, текст свой",
   (ru_opt["agonizing-blast"]["name"], ru_opt["agonizing-blast"]["name_en"],
    ru_opt["agonizing-blast"]["feature"], ru_opt["agonizing-blast"]["prerequisites"]),
   ("Мучительный заряд", "Agonizing Blast",
    {"key": "eldritch-invocations", "name": "Таинственные воззвания", "level": 1},
    {"text": "Колдун 2-го уровня или выше, заговор колдуна, наносящий урон", "level": 2,
     "options": [], "cantrip": "damage"}))
eq("RU Eldritch Spear: RU-текст с дистанцией, код — из EN",
   (ru_opt["eldritch-spear"]["prerequisites"]["text"].endswith("с дистанцией 10+ футов"),
    ru_opt["eldritch-spear"]["prerequisites"]["cantrip"]), (True, "damage"))
eq("RU Devious Strikes: granted_by со своим именем и ключом EN", ru_opt["daze"]["granted_by"],
   {"key": "devious-strikes", "name": "Коварные удары", "level": 14})
eq("RU Blessed Warrior: своё имя и родитель, ключ из EN",
   (ru_opt["blessed-warrior"]["name"], ru_opt["blessed-warrior"]["feature"]),
   ("Благословенный воин", {"key": "fighting-style", "name": "Боевой стиль", "level": 2}))
eq("RU стоимость метамагии своя, единица общая", ru_opt["heightened-spell"]["cost"],
   {"text": "2 очка чародейства", "amount": 2, "unit": "sorcery-point"})


def options_errors(mutate):
    data = copy.deepcopy(opts_pristine)
    mutate(data)
    disambiguate_option_slugs(data)
    return align_class_options(data)


eq("RU-вариант с другой стоимостью — ошибка структуры",
   any("class-options: структура RU" in e for e in options_errors(
       lambda d: next(o for o in d[("srd52", "ru", "class-options")]
                     if o["name"] == "Усложнённое заклинание")["cost"].update(amount=9))), True)
eq("RU без одного варианта — ошибка числа записей",
   any("class-options: EN 66, RU 65" in e for e in options_errors(
       lambda d: d[("srd52", "ru", "class-options")].pop())), True)
eq("неизвестное воззвание в предусловии — ошибка сборки с именем",
   any("«Thirsting Bladee»" in e for e in options_errors(
       lambda d: next(o for o in d[("srd52", "en", "class-options")] if o["slug"] == "devouring-blade")
       ["prerequisites"]["options"].__setitem__(0, "Thirsting Bladee"))), True)
dup = copy.deepcopy(opts)
dup[("srd52", "en", "class-options")][1]["slug"] = dup[("srd52", "en", "class-options")][0]["slug"]
eq("дубль слага внутри ресурса — ошибка сборки",
   any("class-options: слаг" in e for e in slug_collisions(dup, "dnd")), True)

if failures:
    print(f"❌ classes/subclasses/class-options ({len(failures)}):")
    for f in failures:
        print(f"  — {f}")
    sys.exit(1)
print("✅ classes/subclasses/class-options: разбор, выравнивание RU, резолв always_prepared и предусловий")
