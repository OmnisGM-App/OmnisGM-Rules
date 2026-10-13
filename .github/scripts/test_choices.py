#!/usr/bin/env python3
"""Объявления выборов SRD 5.2 в JSON API (#413): `choices` у умений классов и подклассов, особенностей
видов, предысторий, черт и вариантов умений; число по уровням; RU — копией EN; отказы сборки.

API собирается во временную папку тем же generate_api, что и в сборке сайта.
Запуск: python3 .github/scripts/test_choices.py
"""
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]
sys.path.insert(0, str(SCRIPTS))
import choices  # noqa: E402

failures = []


def eq(name, got, want):
    if got != want:
        failures.append(f"{name}: получили {got!r}, ждали {want!r}")


RESOURCES = ("classes", "subclasses", "species", "species-lineages", "backgrounds", "feats", "class-options",
             "spells", "weapons", "equipment")
with tempfile.TemporaryDirectory() as out:
    run = subprocess.run([sys.executable, str(SCRIPTS / "generate_api.py"), "--src-root", str(ROOT / "src/dnd"),
                          "--output-dir", out, "--no-validate"], capture_output=True, text=True)
    if run.returncode:
        print(f"❌ choices: generate_api упал\n{run.stderr[-2000:]}")
        sys.exit(1)
    live = {("srd52", lang, res): json.loads((Path(out) / "dnd/srd52" / lang / res / "all.json").read_text(encoding="utf-8"))
            for lang in ("en", "ru") for res in RESOURCES}


def by_slug(lang, res):
    return {e["slug"]: e for e in live[("srd52", lang, res)]}


def feature(lang, res, slug, index_or_name):
    items = by_slug(lang, res)[slug]["features" if res != "species" else "traits"]
    return items[index_or_name] if isinstance(index_or_name, int) else next(i for i in items if i["name"] == index_or_name)


def one(owner, key):
    return next(c for c in owner["choices"] if c["id"] == key)


classes = by_slug("en", "classes")


# --- Поле есть везде; RU — те же выборы, что EN -------------------------------------------------
def all_choices(lang):
    out = {}
    for res, nested in (("classes", "features"), ("subclasses", "features"), ("species", "traits"),
                        ("backgrounds", None), ("feats", None), ("class-options", None)):
        for e in live[("srd52", lang, res)]:
            if res != "subclasses":
                out[(res, e["slug"])] = e["choices"]
            for index, item in enumerate(e[nested]) if nested else ():
                out[(res, e["slug"], index)] = item["choices"]
    return out


# --- Все 12 классов: подкласс, черта на уровнях улучшения характеристик, эпический дар ------------
ASI = {slug: [4, 8, 12, 16] for slug in classes} | {"fighter": [4, 6, 8, 12, 14, 16], "rogue": [4, 8, 10, 12, 16]}
eq("улучшение характеристик: уровни каждого класса",
   {slug: one(feature("en", "classes", slug, "Ability Score Improvement"), "feat")["levels"] for slug in classes}, ASI)
eq("подкласс: из подклассов своего класса",
   {slug: one(feature("en", "classes", slug, f"{c['name']} Subclass"), "subclass")["from"] for slug, c in classes.items()},
   {slug: {"resource": "subclasses", "filter": {"class": slug}} for slug in classes})
eq("эпический дар: любая черта, подсказка — дар, который советует текст класса",
   {slug: (c["from"]["filter"], c["suggest"]["slug"]) for slug in classes
    for c in feature("en", "classes", slug, "Epic Boon")["choices"]},
   {slug: ({}, boon) for slug, boon in {
       "barbarian": "boon-of-irresistible-offense", "bard": "boon-of-spell-recall", "cleric": "boon-of-fate",
       "druid": "boon-of-dimensional-travel", "fighter": "boon-of-combat-prowess",
       "monk": "boon-of-irresistible-offense", "paladin": "boon-of-truesight", "ranger": "boon-of-dimensional-travel",
       "rogue": "boon-of-the-night-spirit", "sorcerer": "boon-of-dimensional-travel", "warlock": "boon-of-fate",
       "wizard": "boon-of-spell-recall"}.items()})
eq("подсказки из текста: защита у воина, умелый у человека",
   (one(feature("en", "classes", "fighter", "Fighting Style"), "feat")["suggest"],
    one(feature("en", "species", "human", "Versatile"), "feat")["suggest"]),
   ({"slug": "defense"}, {"slug": "skilled"}))

# --- Число по уровням ---------------------------------------------------------------------------
def steps(owner, key):
    count = one(owner, key)["count"]
    return count if isinstance(count, int) else [(s["level"], s["count"]) for s in count]


eq("приёмы оружия: варвар и воин — по колонке, паладин, следопыт и плут — два",
   {slug: steps(feature("en", "classes", slug, "Weapon Mastery"), "weapons")
    for slug in ("barbarian", "fighter", "paladin", "ranger", "rogue")},
   {"barbarian": [(1, 2), (4, 3), (10, 4)], "fighter": [(1, 3), (4, 4), (10, 5), (16, 6)],
    "paladin": 2, "ranger": 2, "rogue": 2})
eq("метамагия: две, четыре с 10-го, шесть с 17-го",
   steps(feature("en", "classes", "sorcerer", "Metamagic"), "options"), [(2, 2), (10, 4), (17, 6)])
eq("экспертиза: бард, плут, следопыт (два умения)",
   (steps(feature("en", "classes", "bard", "Expertise"), "skills"), steps(feature("en", "classes", "rogue", "Expertise"), "skills"),
    steps(feature("en", "classes", "ranger", "Deft Explorer"), "skill"), steps(feature("en", "classes", "ranger", "Expertise"), "skills")),
   ([(2, 2), (9, 4)], [(1, 2), (6, 4)], 1, 2))
eq("воззвания колдуна — по колонке",
   steps(feature("en", "classes", "warlock", "Eldritch Invocations"), "invocations"),
   [(1, 1), (2, 3), (5, 5), (7, 6), (9, 7), (12, 8), (15, 9), (18, 10)])
# Числа выписаны из таблиц классов SRD 5.2 («Cantrips», «Prepared Spells»), не из собранной прогрессии.
FULL = [(1, 4), (2, 5), (3, 6), (4, 7), (5, 9), (6, 10), (7, 11), (8, 12), (9, 14), (10, 15), (11, 16), (13, 17),
        (15, 18), (17, 19), (18, 20), (19, 21), (20, 22)]
HALF = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (7, 7), (9, 9), (11, 10), (13, 11), (15, 12), (17, 14), (19, 15)]
CASTERS = {
    "bard": ("Spellcasting", [(1, 2), (4, 3), (10, 4)], "level", FULL, "level"),
    "cleric": ("Spellcasting", [(1, 3), (4, 4), (10, 5)], "level", FULL, "long-rest"),
    "druid": ("Spellcasting", [(1, 2), (4, 3), (10, 4)], "level", FULL, "long-rest"),
    "paladin": ("Spellcasting", None, None, HALF, "long-rest"),
    "ranger": ("Spellcasting", None, None, HALF, "long-rest"),
    "sorcerer": ("Spellcasting", [(1, 4), (4, 5), (10, 6)], "level", [(1, 2), (2, 4)] + FULL[2:], "level"),
    "warlock": ("Pact Magic", [(1, 2), (4, 3), (10, 4)], "level",
                [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9), (9, 10), (11, 11), (13, 12), (15, 13),
                 (17, 14), (19, 15)], "level"),
    "wizard": ("Spellcasting", [(1, 3), (4, 4), (10, 5)], "long-rest",
               FULL[:12] + [(14, 18), (15, 19), (16, 21), (17, 22), (18, 23), (19, 24), (20, 25)], "long-rest"),
}


def caster(slug, name):
    f = feature("en", "classes", slug, name)
    cantrips = next((c for c in f["choices"] if c["id"] == "cantrips"), None)
    return (name, steps(f, "cantrips") if cantrips else None, cantrips["replace"] if cantrips else None,
            steps(f, "prepared"), one(f, "prepared")["replace"])


eq("заговоры и подготовленные заклинания восьми заклинателей: число по уровням и замена",
   {slug: caster(slug, row[0]) for slug, row in CASTERS.items()}, CASTERS)

# Числа, написанные руками в объявлениях: (ресурс, слаг, умение или None, id) → сколько.
MANUAL = {
    ("class-options", "pact-of-the-tome", None, "cantrips"): 3, ("class-options", "pact-of-the-tome", None, "rituals"): 2,
    ("class-options", "blessed-warrior", None, "cantrips"): 2, ("class-options", "druidic-warrior", None, "cantrips"): 2,
    ("class-options", "thaumaturge", None, "cantrip"): 1, ("class-options", "magician", None, "cantrip"): 1,
    ("feats", "skilled", None, "proficiencies"): 3, ("feats", "magic-initiate", None, "cantrips"): 2,
    ("feats", "magic-initiate", None, "spell"): 1,
    ("subclasses", "college-of-lore", "Bonus Proficiencies", "skills"): 3,
    ("subclasses", "college-of-lore", "Magical Discoveries", "spells"): 2,
    ("subclasses", "evoker", "Evocation Savant", "spells"): 2,
    ("classes", "ranger", "Deft Explorer", "languages"): 2, ("classes", "rogue", "Thieves' Cant", "language"): 1,
    ("classes", "wizard", "Signature Spells", "spells"): 2,
}
eq("ручные числа объявлений",
   {key: one(feature("en", key[0], key[1], key[2]) if key[2] else by_slug("en", key[0])[key[1]], key[3])["count"]
    for key in MANUAL}, MANUAL)
eq("тайный аркан: четыре выбора со своим уровнем и кругом",
   [(c["id"], c["level"], c["from"]["filter"]["level"]) for c in feature("en", "classes", "warlock", "Mystic Arcanum")["choices"]],
   [("arcanum-6", 11, 6), ("arcanum-7", 13, 7), ("arcanum-8", 15, 8), ("arcanum-9", 17, 9)])

# --- Источники ----------------------------------------------------------------------------------
eq("боевой стиль паладина: черта или вариант умения",
   (one(feature("en", "classes", "paladin", "Fighting Style"), "feat")["from"],
    one(feature("en", "classes", "paladin", "Fighting Style"), "feat")["or"]),
   ({"resource": "feats", "filter": {"category": "fighting_style"}},
    {"resource": "class-options", "filter": {"class": "paladin", "feature": "fighting-style"}}))
eq("боевой стиль меняется при уровне только у воина",
   {slug: one(feature("en", "classes", slug, "Fighting Style"), "feat")["replace"] for slug in ("fighter", "paladin", "ranger")}
   | {"champion": one(feature("en", "subclasses", "champion", "Additional Fighting Style"), "feat")["replace"]},
   {"fighter": "level", "paladin": "never", "ranger": "never", "champion": "never"})
eq("первобытное знание варвара — из списка навыков класса",
   one(feature("en", "classes", "barbarian", "Primal Knowledge"), "skill")["from"]["values"],
   classes["barbarian"]["proficiencies"]["skills"]["options"])
eq("учёный волшебника — экспертиза в одном из шести своих навыков",
   one(feature("en", "classes", "wizard", "Scholar"), "skill")["from"],
   {"character": "skill-proficiencies",
    "filter": {"values": ["arcana", "history", "investigation", "medicine", "nature", "religion"]}})
eq("выборы самого класса: инструменты барда и монаха",
   {slug: [(c["kind"], c["count"], c["from"]["list"]) for c in cls["choices"]] for slug, cls in classes.items() if cls["choices"]},
   {"bard": [("tool", 3, "musical-instruments")], "monk": [("tool", 1, "artisan-tools-or-musical-instruments")]})
eq("Круг Земли: земля из ключей always_prepared, замена на долгом отдыхе",
   (one(feature("en", "subclasses", "circle-of-the-land", "Circle of the Land Spells"), "land")["from"]["values"],
    one(feature("en", "subclasses", "circle-of-the-land", "Circle of the Land Spells"), "land")["replace"]),
   (["arid-land", "polar-land", "temperate-land", "tropical-land"], "long-rest"))
eq("исчадие: любой тип урона, кроме силового",
   "force" in one(feature("en", "subclasses", "fiend-patron", "Fiendish Resilience"), "damage-type")["from"]["values"], False)

species = by_slug("en", "species")
eq("наследие — у пяти видов, из их наследий",
   {slug: [c["from"]["filter"]["species"] for t in sp["traits"] for c in t["choices"] if c["kind"] == "lineage"]
    for slug, sp in species.items() if any(t["lineages"] for t in sp["traits"])},
   {slug: [slug] for slug in ("dragonborn", "elf", "gnome", "goliath", "tiefling")})
eq("заклинательная характеристика наследия: эльф, гном, тифлинг",
   sorted(slug for slug, sp in species.items() for t in sp["traits"] for c in t["choices"] if c["kind"] == "spellcasting-ability"),
   ["elf", "gnome", "tiefling"])
eq("размер — выбор у человека и тифлинга",
   {slug: [c["from"]["values"] for c in sp["choices"]] for slug, sp in species.items() if sp["choices"]},
   {"human": [["medium", "small"]], "tiefling": [["medium", "small"]]})

backgrounds = by_slug("en", "backgrounds")
eq("предыстории: прибавки из своих трёх характеристик, +2/+1 или +1/+1/+1",
   {slug: (one(b, "ability-scores")["from"]["values"] == b["ability_scores"]["abilities"],
           one(b, "ability-scores")["increase"], one(b, "ability-scores")["max"]) for slug, b in backgrounds.items()},
   {slug: (True, [[2, 1], [1, 1, 1]], 20) for slug in backgrounds})
eq("выбор инструмента — только у солдата",
   {slug: [c["from"] for c in b["choices"] if c["kind"] == "tool"] for slug, b in backgrounds.items()},
   {"acolyte": [], "criminal": [], "sage": [], "soldier": [{"resource": "equipment", "filter": {"variants_of": "gaming-set"}}]})

feats = by_slug("en", "feats")
eq("Magic Initiate: список заклинаний — выбор, на него ссылаются заговоры",
   (one(feats["magic-initiate"], "spell-list")["from"]["values"], one(feats["magic-initiate"], "cantrips")["from"]["filter"]),
   (["cleric", "druid", "wizard"], {"class": "@spell-list", "level": 0}))
eq("прибавки черт: ASI, дары, борец",
   {slug: (one(f, "ability-score")["increase"], one(f, "ability-score")["max"], one(f, "ability-score")["from"]["values"])
    for slug, f in feats.items() if any(c["kind"] == "ability-score" for c in f["choices"])},
   {"ability-score-improvement": ([[2], [1, 1]], 20, None), "grappler": ([[1]], 20, ["str", "dex"]),
    "boon-of-combat-prowess": ([[1]], 30, None), "boon-of-dimensional-travel": ([[1]], 30, None),
    "boon-of-fate": ([[1]], 30, None), "boon-of-irresistible-offense": ([[1]], 30, ["str", "dex"]),
    "boon-of-spell-recall": ([[1]], 30, ["int", "wis", "cha"]), "boon-of-the-night-spirit": ([[1]], 30, None),
    "boon-of-truesight": ([[1]], 30, None)})
eq("варианты умений с выбором",
   sorted(o["slug"] for o in live[("srd52", "en", "class-options")] if o["choices"]),
   ["agonizing-blast", "blessed-warrior", "druidic-warrior", "eldritch-spear", "lessons-of-the-first-ones",
    "magician", "pact-of-the-tome", "repelling-blast", "thaumaturge"])
eq("умелый: навык или инструмент", (one(feats["skilled"], "proficiencies")["kind"],
                                    one(feats["skilled"], "proficiencies")["from"]["list"]),
   ("skill-or-tool", "skills-or-tools"))
eq("заговоры воззваний — из известных заговоров колдуна, условие в тексте",
   {slug: one(by_slug("en", "class-options")[slug], "cantrip")["from"]
    for slug in ("agonizing-blast", "eldritch-spear", "repelling-blast")},
   {slug: {"character": "known-cantrips", "filter": {"class": "warlock"}}
    for slug in ("agonizing-blast", "eldritch-spear", "repelling-blast")})
eq("ключи фильтров — только из словаря",
   sorted({(src.get("resource") or src.get("character"), key) for v in all_choices("en").values() for c in v
           for src in (c["from"], c.get("or", {})) for key in src.get("filter", {})}
          - {(name, key) for name, keys in choices.FILTERS.items() for key in keys}), [])

eq("RU несёт те же выборы, что EN, у каждой записи, умения и особенности", all_choices("ru"), all_choices("en"))
eq("всего объявлено выборов", sum(len(v) for v in all_choices("en").values()), 132)


# --- Отказы: сборка на испорченных объявлениях и данных -----------------------------------------
def rebuilt(mutate_data=None, **tables):
    """Повторная сборка выборов на копии данных; таблицы объявлений подменяются на время вызова."""
    data = copy.deepcopy(live)
    if mutate_data:
        mutate_data(data)
    saved = {name: getattr(choices, name) for name in tables}
    for name, table in tables.items():
        setattr(choices, name, table)
    try:
        return choices.attach_choices(data)
    finally:
        for name, table in saved.items():
            setattr(choices, name, table)


def also(table, key, value):
    return {**getattr(choices, table), key: value}


eq("чистая пересборка — без ошибок", rebuilt(), [])
eq("объявление для умения, которого нет, роняет сборку",
   rebuilt(CLASS_FEATURES=also("CLASS_FEATURES", ("bard", "Bardic Lore"), [])),
   ["объявление без хозяина: class-feature ('bard', 'Bardic Lore')"])
eq("объявление для особенности вида, которой нет, роняет сборку",
   rebuilt(SPECIES_TRAITS=also("SPECIES_TRAITS", ("orc", "Menacing"), [])),
   ["объявление без хозяина: species-trait ('orc', 'Menacing')"])
eq("объявление для черты, которой нет, роняет сборку",
   rebuilt(FEATS=also("FEATS", "lucky", [])), ["объявление без хозяина: feats/lucky"])
eq("колонки прогрессии нет — сборка падает",
   rebuilt(CLASS_FEATURES=also("CLASS_FEATURES", ("rogue", "Weapon Mastery"),
                               [choices.ch("weapons", "weapon-mastery", ("column", "weapon-mastery"), choices.res("weapons"))])),
   ["classes/rogue/Weapon Mastery: колонки прогрессии «weapon-mastery» у класса нет"])
eq("навык не из словаря — сборка падает",
   rebuilt(SPECIES_TRAITS=also("SPECIES_TRAITS", ("human", "Skillful"),
                               [choices.ch("skill", "skill", 1, choices.lst("skills", ["lore"]))])),
   ["species/human/Skillful: значения ['lore'] не из списка 'skills'"])
eq("категории черт нет — сборка падает",
   rebuilt(SPECIES_TRAITS=also("SPECIES_TRAITS", ("human", "Versatile"),
                               [choices.ch("feat", "feat", 1, choices.res("feats", category="heroic"))])),
   ["species/human/Versatile: категории черт 'heroic' нет"])
eq("группы вариантов нет — сборка падает",
   rebuilt(CLASS_FEATURES=also("CLASS_FEATURES", ("cleric", "Divine Order"),
                               [choices.ch("option", "option", 1, choices.res("class-options", **{"class": "cleric"}, feature="holy-order"))])),
   ["classes/cleric/Divine Order: группы вариантов cleric/holy-order нет"])
eq("повтор id выбора — сборка падает",
   rebuilt(FEATS=also("FEATS", "skilled", [choices.ch("a", "skill", 1, choices.lst("skills")),
                                           choices.ch("a", "tool", 1, choices.lst("tools"))])),
   ["feats/skilled: повтор id выбора в ['a', 'a']"])
STYLE_OR = lambda source: also("CLASS_FEATURES", ("paladin", "Fighting Style"),  # noqa: E731
                               [choices.ch("feat", "feat", 1, choices.STYLE, **{"or": source})])
for name, tables, want in (
    ("класса в фильтре нет", {"CLASS_OPTIONS": also("CLASS_OPTIONS", "blessed-warrior",
                                                   [choices.ch("c", "spell", 2, choices.res("spells", **{"class": "wizrd"}))])},
     "class-options/blessed-warrior: класса 'wizrd' нет"),
    ("ключа фильтра нет в словаре", {"CLASS_OPTIONS": also("CLASS_OPTIONS", "agonizing-blast",
                                                          [choices.ch("c", "spell", 1, choices.own("known-cantrips", deals="damage"))])},
     "class-options/agonizing-blast: ключа фильтра 'deals' у источника 'known-cantrips' нет"),
    ("ссылка @id без такого выбора", {"FEATS": also("FEATS", "skilled",
                                                    [choices.ch("c", "spell", 1, choices.res("spells", **{"class": "@spell-lst"}))])},
     "feats/skilled: ссылка '@spell-lst' — выбора с таким id у хозяина нет"),
    ("школы нет", {"FEATS": also("FEATS", "skilled", [choices.ch("c", "spell", 1, choices.res("spells", school="evocatoin"))])},
     "feats/skilled: школы 'evocatoin' нет"),
    ("круга вне словаря нет", {"FEATS": also("FEATS", "skilled", [choices.ch("c", "spell", 1, choices.res("spells", level="any"))])},
     "feats/skilled: круг заклинания 'any' вне словаря"),
    ("записи снаряжения с разновидностями нет", {"BACKGROUNDS": {"soldier": [choices.ch("tool", "tool", 1, choices.res("equipment", variants_of="no-such"))]}},
     "backgrounds/soldier: записи снаряжения с разновидностями 'no-such' нет"),
    ("подклассов класса нет", {"FEATS": also("FEATS", "skilled", [choices.ch("c", "subclass", 1, choices.res("subclasses", **{"class": "artificer"}))])},
     "feats/skilled: класса 'artificer' нет"),
    ("наследий вида нет", {"FEATS": also("FEATS", "skilled", [choices.ch("c", "lineage", 1, choices.res("species-lineages", species="orc"))])},
     "feats/skilled: наследий вида 'orc' нет"),
    ("черты-подсказки нет", {"FEATS": also("FEATS", "skilled", [choices.ch("c", "feat", 1, choices.ANY_FEAT, suggest={"slug": "no-such"})])},
     "feats/skilled: черты-подсказки 'no-such' нет"),
    ("подсказка не слагом", {"FEATS": also("FEATS", "skilled", [choices.ch("c", "feat", 1, choices.ANY_FEAT, suggest={"category": "origin"})])},
     "feats/skilled: подсказка — только слаг черты, получено ['category']"),
    ("списка нет в словаре", {"FEATS": also("FEATS", "skilled", [choices.ch("c", "skill", 1, choices.lst("hobbies"))])},
     "feats/skilled: список 'hobbies' вне словаря"),
    ("плохое значение во втором источнике", {"CLASS_FEATURES": STYLE_OR(choices.res("feats", category="heroic"))},
     "classes/paladin/Fighting Style: категории черт 'heroic' нет"),
    ("типа оружия нет", {"FEATS": also("FEATS", "skilled", [choices.ch("c", "weapon-mastery", 1, choices.res("weapons", type="thrown"))])},
     "feats/skilled: типа оружия 'thrown' нет"),
):
    eq(f"{name} — сборка падает", [e for e in rebuilt(**tables) if e == want], [want])


def whole_spell_list(data):
    # Список заклинаний, объявленный целиком, не роняет сверку варианта предыстории исключением.
    choices.FEATS["magic-initiate"][0]["from"]["values"] = None


saved_values = choices.FEATS["magic-initiate"][0]["from"]["values"]
try:
    eq("список заклинаний целиком: вариант предыстории сверяется с классами", rebuilt(whole_spell_list), [])
finally:
    choices.FEATS["magic-initiate"][0]["from"]["values"] = saved_values

eq("вид выбора вне словаря — сборка падает",
   rebuilt(FEATS=also("FEATS", "skilled", [choices.ch("a", "hobby", 1, choices.lst("skills"))])),
   ["feats/skilled: вид 'hobby' или замена 'never' вне словаря"])


def drop_variant(data):
    next(b for b in data[("srd52", "en", "backgrounds")] if b["slug"] == "sage")["feat"]["variant"] = "bard"


eq("вариант черты предыстории не из списка черты — сборка падает", rebuilt(drop_variant),
   ["backgrounds/sage: варианта черты 'bard' нет среди выборов «magic-initiate»"])


def tool_without_choice(data):
    next(b for b in data[("srd52", "en", "backgrounds")] if b["slug"] == "sage")["tool"]["choose_from"] = "gaming-set"


eq("выбор инструмента в тексте без объявления — сборка падает", rebuilt(tool_without_choice),
   ["backgrounds/sage: выбор инструмента в тексте и в объявлении расходятся"])


def ru_without_feature(data):
    next(c for c in data[("srd52", "ru", "classes")] if c["slug"] == "bard")["features"].pop()


eq("RU-класс с другим числом умений — выборы не копируются молча", rebuilt(ru_without_feature),
   ["ru/classes/bard: нет пары в EN для выборов"])

if failures:
    print(f"❌ choices ({len(failures)}):")
    for f in failures:
        print(f"  — {f}")
    sys.exit(1)
print("✅ choices: 132 объявления выбора, число по уровням, источники, RU копией EN, отказы сборки")
