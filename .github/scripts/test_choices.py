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
import jsonschema  # noqa: E402
import config  # noqa: E402
from schemas import _CHOICES, CLASS_SCHEMA  # noqa: E402

failures = []


def eq(name, got, want):
    if got != want:
        failures.append(f"{name}: получили {got!r}, ждали {want!r}")


RESOURCES = ("classes", "subclasses", "species", "species-lineages", "backgrounds", "feats", "class-options",
             "spells", "weapons", "equipment", "equipment-groups", "choice-lists", "languages")
# --site-data: сверке ссылок нужны и группы снаряжения, которых в публичном API нет.
with tempfile.TemporaryDirectory() as out:
    run = subprocess.run([sys.executable, str(SCRIPTS / "generate_api.py"), "--src-root", str(ROOT / "src/dnd"),
                          "--output-dir", out, "--no-validate", "--site-data"], capture_output=True, text=True)
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
                        ("backgrounds", None), ("feats", None), ("class-options", None), ("species-lineages", None)):
        for e in live[("srd52", lang, res)]:
            if res != "subclasses":
                out[(res, e["slug"])] = e.get("choices", [])
            if res == "classes":
                out[(res, e["slug"], "multiclass")] = e["multiclass"].get("choices")
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
   {slug: [(c["kind"], c["count"], c["from"]) for c in cls["choices"]] for slug, cls in classes.items() if cls["choices"]},
   {"bard": [("tool", 3, {"resource": "equipment", "filter": {"group": "musical-instrument"}})],
    "monk": [("tool", 1, {"list": "artisan-tools-or-musical-instruments", "values": None})]})
eq("мультикласс: инструмент на выбор — только у барда, из музыкальных инструментов",
   {slug: [(c["kind"], c["count"], c["from"]) for c in cls["multiclass"]["choices"]]
    for slug, cls in classes.items() if cls["multiclass"]["choices"]},
   {"bard": [("tool", 1, {"resource": "equipment", "filter": {"group": "musical-instrument"}})]})
eq("Круг Земли: земля из ключей always_prepared, замена на долгом отдыхе",
   (one(feature("en", "subclasses", "circle-of-the-land", "Circle of the Land Spells"), "land")["from"]["values"],
    one(feature("en", "subclasses", "circle-of-the-land", "Circle of the Land Spells"), "land")["replace"]),
   (["arid-land", "polar-land", "temperate-land", "tropical-land"], "long-rest"))
eq("владелец таблицы always_prepared — одно умение у каждого подкласса с таблицей, RU — на той же позиции",
   {lang: {slug: [f["name"] for f in sub["features"] if f["always_prepared"]] for slug, sub in by_slug(lang, "subclasses").items()
           if sub["always_prepared"]} for lang in ("en",)}
   | {"ru-positions": {slug: [i for i, f in enumerate(sub["features"]) if f.get("always_prepared")]
                       for slug, sub in by_slug("ru", "subclasses").items() if sub["always_prepared"]}},
   {"en": {"circle-of-the-land": ["Circle of the Land Spells"], "draconic-sorcery": ["Draconic Spells"],
           "fiend-patron": ["Fiend Spells"], "life-domain": ["Life Domain Spells"], "oath-of-devotion": ["Oath of Devotion Spells"]},
    "ru-positions": {slug: [i for i, f in enumerate(sub["features"]) if f.get("always_prepared")]
                     for slug, sub in by_slug("en", "subclasses").items() if sub["always_prepared"]}})
eq("у подклассов без таблицы флаг — false на каждом умении",
   [f"{slug}/{f['name']}" for lang in ("en", "ru") for slug, sub in by_slug(lang, "subclasses").items()
    if not sub["always_prepared"] for f in sub["features"] if f.get("always_prepared") is not False], [])
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
HIGH_ELF_CANTRIP = [{"id": "cantrip", "kind": "spell", "count": 1,
                     "from": {"resource": "spells", "filter": {"class": "wizard", "level": 0}},
                     "replace": "long-rest", "suggest": {"slug": "prestidigitation"}}]
for lang in ("en", "ru"):
    eq(f"{lang}: заговор волшебника — выбор высшего эльфа, не дроу и не лесного эльфа",
       {slug: l.get("choices") for slug, l in by_slug(lang, "species-lineages").items() if l["species"] == "elf"},
       {"elf-drow": [], "elf-high-elf": HIGH_ELF_CANTRIP, "elf-wood-elf": []})
for lang in ("en", "ru"):
    eq(f"{lang}: Prestidigitation высшего эльфа в grants связан с выбором cantrip, других связей нет",
       {(slug, sp["slug"]): sp["choice"] for slug, l in by_slug(lang, "species-lineages").items()
        for sp in l["grants"]["spells"] if "choice" in sp},
       {("elf-high-elf", "prestidigitation"): "cantrip"})
eq("выбор заговора — у наследия, а не у особенности «Эльфийская родословная»",
   [c["id"] for c in feature("en", "species", "elf", "Elven Lineage")["choices"]], ["lineage", "spellcasting-ability"])
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
   {"acolyte": [], "criminal": [], "sage": [], "soldier": [{"resource": "equipment", "filter": {"group": "gaming-set"}}]})

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
eq("всего объявлено выборов", sum(len(v) for v in all_choices("en").values()), 134)


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


def errors_or_exception(**tables):
    """Ошибки сборки списком; исключение вместо ошибки — тоже строка, чтобы кейс упал на сверке, а не трассой."""
    try:
        return rebuilt(**tables)
    except Exception as exc:  # noqa: BLE001
        return [f"исключение {type(exc).__name__}: {exc}"]


def also(table, key, value):
    return {**getattr(choices, table), key: value}


eq("чистая пересборка — без ошибок", rebuilt(), [])
eq("объявление для умения, которого нет, роняет сборку",
   rebuilt(CLASS_FEATURES=also("CLASS_FEATURES", ("bard", "Bardic Lore"), [])),
   ["объявление без хозяина: class-feature ('bard', 'Bardic Lore')"])
eq("объявление для особенности вида, которой нет, роняет сборку",
   rebuilt(SPECIES_TRAITS=also("SPECIES_TRAITS", ("orc", "Menacing"), [])),
   ["объявление без хозяина: species-trait ('orc', 'Menacing')"])
eq("объявление для наследия, которого нет, роняет сборку",
   rebuilt(LINEAGES=also("LINEAGES", "elf-sun-elf", [])), ["объявление без хозяина: species-lineages/elf-sun-elf"])
eq("объявление для черты, которой нет, роняет сборку",
   rebuilt(FEATS=also("FEATS", "lucky", [])), ["объявление без хозяина: feats/lucky"])
eq("владелец таблицы для умения, которого нет, роняет сборку",
   rebuilt(ALWAYS_PREPARED_OWNERS=choices.ALWAYS_PREPARED_OWNERS | {("life-domain", "Life Spells")}),
   ["объявление без хозяина: always-prepared ('life-domain', 'Life Spells')"])
eq("два владельца одной таблицы роняют сборку",
   rebuilt(ALWAYS_PREPARED_OWNERS=choices.ALWAYS_PREPARED_OWNERS | {("life-domain", "Disciple of Life")}),
   ["subclasses/life-domain: у таблицы always_prepared умений-владельцев 2, ждали одно"])
eq("таблица без владельца роняет сборку",
   rebuilt(ALWAYS_PREPARED_OWNERS=choices.ALWAYS_PREPARED_OWNERS - {("fiend-patron", "Fiend Spells")}),
   ["subclasses/fiend-patron: у таблицы always_prepared умений-владельцев 0, ждали одно"])


def no_life_table(data):
    next(s for s in data[("srd52", "en", "subclasses")] if s["slug"] == "life-domain")["always_prepared"] = []


eq("владелец у подкласса без таблицы роняет сборку", rebuilt(no_life_table),
   ["subclasses/life-domain: умение-владелец объявлено, а таблицы always_prepared нет"])
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
    ("группы снаряжения нет", {"BACKGROUNDS": {"soldier": [choices.ch("tool", "tool", 1, choices.res("equipment", group="no-such"))]}},
     "backgrounds/soldier: группы снаряжения 'no-such' нет"),
    ("подклассов класса нет", {"FEATS": also("FEATS", "skilled", [choices.ch("c", "subclass", 1, choices.res("subclasses", **{"class": "artificer"}))])},
     "feats/skilled: класса 'artificer' нет"),
    ("наследий вида нет", {"FEATS": also("FEATS", "skilled", [choices.ch("c", "lineage", 1, choices.res("species-lineages", species="orc"))])},
     "feats/skilled: наследий вида 'orc' нет"),
    ("черты-подсказки нет", {"FEATS": also("FEATS", "skilled", [choices.ch("c", "feat", 1, choices.ANY_FEAT, suggest={"slug": "no-such"})])},
     "feats/skilled: черты-подсказки 'no-such' нет"),
    ("заклинания-подсказки нет", {"LINEAGES": {"elf-high-elf": [choices.ch(
        "cantrip", "spell", 1, choices.res("spells", **{"class": "wizard"}, level=0), suggest={"slug": "no-such"})]}},
     "species-lineages/elf-high-elf: заклинания-подсказки 'no-such' нет"),
    ("заклинание-подсказка в grants без связи с выбором", {"LINEAGE_GRANT_CHOICES": {}},
     "species-lineages/elf-high-elf: заклинание 'prestidigitation' в grants — подсказка выбора 'cantrip', а связи choice нет"),
    ("связь с выбором, которого у наследия нет", {"LINEAGE_GRANT_CHOICES": {("elf-high-elf", "prestidigitation"): "spell"}},
     "species-lineages/elf-high-elf: заклинание 'prestidigitation' связано с выбором 'spell', а такого выбора у наследия нет"),
    ("связь для заклинания, которого нет в grants наследия", {"LINEAGE_GRANT_CHOICES": also(
        "LINEAGE_GRANT_CHOICES", ("elf-drow", "prestidigitation"), "cantrip")},
     "объявление без хозяина: lineage-grant ('elf-drow', 'prestidigitation')"),
    ("подсказка у выбора вида без подсказок", {"FEATS": also("FEATS", "skilled", [choices.ch(
        "c", "skill", 1, choices.lst("skills"), suggest={"slug": "athletics"})])},
     "feats/skilled: подсказка у выбора вида 'skill' не поддерживается"),
    ("подсказка не слагом", {"FEATS": also("FEATS", "skilled", [choices.ch("c", "feat", 1, choices.ANY_FEAT, suggest={"category": "origin"})])},
     "feats/skilled: подсказка — только слаг записи, получено ['category']"),
    ("списка нет в словаре", {"FEATS": also("FEATS", "skilled", [choices.ch("c", "skill", 1, choices.lst("hobbies"))])},
     "feats/skilled: список 'hobbies' вне словаря"),
    ("плохое значение во втором источнике", {"CLASS_FEATURES": STYLE_OR(choices.res("feats", category="heroic"))},
     "classes/paladin/Fighting Style: категории черт 'heroic' нет"),
    ("типа оружия нет", {"FEATS": also("FEATS", "skilled", [choices.ch("c", "weapon-mastery", 1, choices.res("weapons", type="thrown"))])},
     "feats/skilled: типа оружия 'thrown' нет"),
):
    eq(f"{name} — сборка падает", [e for e in errors_or_exception(**tables) if e == want], [want])


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


def class_tool(slug, owner, value):
    def mutate(data):
        next(c for c in data[("srd52", "en", "classes")] if c["slug"] == slug)[owner]["tools"] = value
    return mutate


eq("инструмента класса нет в equipment — сборка падает",
   rebuilt(class_tool("druid", "proficiencies", {"text": "Herbalism Kit", "slug": "herbal-kit"})),
   ["classes/druid/proficiencies: инструмента 'herbal-kit' нет в equipment"])
eq("инструмент на выбор в мультиклассе без объявления — сборка падает", rebuilt(MULTICLASS={}),
   ["classes/bard/multiclass: инструмент на выбор в тексте и в объявлении расходятся"])
eq("объявление выбора мультикласса при названном инструменте — сборка падает",
   rebuilt(class_tool("bard", "multiclass", {"text": "proficiency with Lute", "slug": "lute"})),
   ["classes/bard/multiclass: инструмент на выбор в тексте и в объявлении расходятся"])
eq("объявление мультикласса для класса, которого нет, роняет сборку",
   rebuilt(MULTICLASS=also("MULTICLASS", "artificer", [])), ["объявление без хозяина: multiclass artificer"])


# --- choice-lists и languages (#482) -------------------------------------------------------------
def lists(lang):
    return {e["slug"]: e["members"] for e in live[("srd52", lang, "choice-lists")]}


eq("choice-lists: каждый список из LISTS, у каждого члены, RU — те же слаги и типы",
   {lang: sorted(k for k, v in lists(lang).items() if v) for lang in ("en", "ru")}
   | {"ru-keys": {k: [(m["type"], m["slug"]) for m in v] for k, v in lists("ru").items()}},
   {lang: sorted(choices.LISTS) for lang in ("en", "ru")}
   | {"ru-keys": {k: [(m["type"], m["slug"]) for m in v] for k, v in lists("en").items()}})
eq("choice-lists: члены по типам и ресурсам",
   {k: (len(v), sorted({m["type"] for m in v})) for k, v in lists("en").items()},
   {"abilities": (6, ["ability"]), "classes": (12, ["class"]), "damage-types": (13, ["damage-type"]),
    "lands": (4, ["land"]), "languages": (19, ["language"]), "sizes": (6, ["size"]), "skills": (18, ["skill"]),
    "tools": (37, ["tool"]), "skills-or-tools": (55, ["skill", "tool"]),
    "artisan-tools-or-musical-instruments": (27, ["tool"])})
eq("choice-lists: слаги инструментов, языков и классов разрешаются в своих ресурсах",
   [(k, m["slug"]) for k, v in lists("en").items() for m in v
    if m["slug"] not in {"tool": by_slug("en", "equipment"), "language": by_slug("en", "languages"),
                         "class": classes}.get(m["type"], {m["slug"]: 1})], [])
eq("choice-lists: подписи RU — из таблиц правил, не EN",
   {k: lists("ru")[k][0]["name"] for k in ("skills", "abilities", "damage-types", "sizes", "languages", "lands")},
   {"skills": "Акробатика", "abilities": "Сила", "damage-types": "Кислота", "sizes": "Крошечный",
    "languages": "Общий", "lands": "Засушливая земля"})
languages = live[("srd52", "ru", "languages")]
eq("languages: 10 стандартных и 9 редких, RU — слаг и name_en из EN",
   ([l["category"] for l in live[("srd52", "en", "languages")]].count("standard"),
    [l["category"] for l in languages].count("rare"),
    {l["slug"]: l["name_en"] for l in languages}["thieves-cant"]), (10, 9, "Thieves' Cant"))


def drop_list(key):
    def mutate(data):
        data[("srd52", "en", "choice-lists")] = [e for e in data[("srd52", "en", "choice-lists")] if e["slug"] != key]
    return mutate


eq("объявление называет список, которого нет в choice-lists, — сборка падает", [e for e in rebuilt(drop_list("languages"))
   if "languages" in e], ["classes/druid/Druidic: языка 'druidic' нет в списке languages",
                          "classes/ranger/Deft Explorer: списка 'languages' нет в choice-lists",
                          "classes/rogue/Thieves' Cant: списка 'languages' нет в choice-lists",
                          "classes/rogue/Thieves' Cant: языка 'thieves-cant' нет в списке languages"])
eq("значение не из членов списка — сборка падает",
   rebuilt(SPECIES_TRAITS=also("SPECIES_TRAITS", ("elf", "Keen Senses"),
                               [choices.ch("skill", "skill", 1, choices.lst("sizes", ["colossal"]))])),
   ["species/elf/Keen Senses: значения ['colossal'] не из списка 'sizes'"])


def with_terms(mutate=None):
    """Данные до сборки списков: таблицы правил из глав, без choice-lists, RU-языки без слагов."""
    from parsers import parse_table_terms
    data = copy.deepcopy(live)
    for lang in ("en", "ru"):
        del data[("srd52", lang, "choice-lists")]
        data[("srd52", lang, "list-terms")] = [
            t for src in config.SOURCES if src["type"] == "list_terms" and src["lang"] == lang
            for t in parse_table_terms((ROOT / "src/dnd" / src["file"]).read_text(encoding="utf-8"), src["tables"])]
    for l in data[("srd52", "ru", "languages")]:
        l["slug"] = l["name_en"] = None
    if mutate:
        mutate(data)
    errors = choices.build_choice_lists(data)
    return errors, data


def unordered(entries):
    """all.json пишет записи по слагу, а пересборка берёт предметы и языки уже из all.json."""
    return {e["slug"]: sorted(e["members"], key=lambda m: (m["type"], m["slug"])) for e in entries}


errors, rebuilt_lists = with_terms()
eq("сборка списков из глав — без ошибок и как в API",
   (errors, {lang: unordered(rebuilt_lists[("srd52", lang, "choice-lists")]) for lang in ("en", "ru")},
    rebuilt_lists[("srd52", "ru", "languages")], ("srd52", "en", "list-terms") in rebuilt_lists),
   ([], {lang: unordered(live[("srd52", lang, "choice-lists")]) for lang in ("en", "ru")}, live[("srd52", "ru", "languages")], False))


def drop_term(lang, name):
    def mutate(data):
        data[("srd52", lang, "list-terms")] = [t for t in data[("srd52", lang, "list-terms")] if t["name"] != name]
    return mutate


eq("RU-таблица навыков без строки — сборка падает", with_terms(drop_term("ru", "Магия"))[0],
   ["srd52/ru/skills: строк 17, в EN 18"])
eq("EN-таблица навыков без строки — ошибка словаря первой",
   with_terms(drop_term("en", "Arcana"))[0][0].startswith("srd52/en/skills: таблица даёт"), True)


def ru_language_swapped(data):
    data[("srd52", "ru", "languages")][0]["category"] = "standard"


eq("RU-язык не напротив EN — сборка падает", with_terms(ru_language_swapped)[0],
   ["srd52/ru/languages: строки RU не напротив EN (19 против 19)"])


def no_tool_lists(data):
    for lang in ("en", "ru"):
        for e in data[("srd52", lang, "equipment")]:
            e["tool_type"] = e["group"] = None


eq("список без членов — сборка падает", [e for e in with_terms(no_tool_lists)[0] if "choice-lists" in e],
   [f"srd52/{lang}/choice-lists: у списка 'artisan-tools-or-musical-instruments' нет членов" for lang in ("en", "ru")])


def tool_type(lang, slug, value):
    def mutate(data):
        next(e for e in data[("srd52", lang, "equipment")] if e["slug"] == slug)["tool_type"] = value
    return mutate


eq("тип инструмента вне словаря — сборка падает", with_terms(tool_type("en", "lute", "instrument"))[0],
   [f"srd52/{lang}/equipment/lute: тип инструмента {v!r} вне словаря или ≠ EN" for lang, v in (("en", "instrument"), ("ru", None))])
eq("RU-тип инструмента ≠ EN — сборка падает", with_terms(tool_type("ru", "smith-s-tools", None))[0],
   ["srd52/ru/equipment/smith-s-tools: тип инструмента None вне словаря или ≠ EN"])
eq("у типа инструмента нет предметов — сборка падает", [e for e in with_terms(no_tool_lists)[0] if "нет предметов" in e],
   [f"srd52/{lang}/equipment: у типа инструмента 'artisan-tools' нет предметов" for lang in ("en", "ru")])
eq("инструменты ремесленника или музыкальные: 17 ремесленника из раздела «Artisan's Tools» и 10 инструментов",
   sorted(m["slug"] for m in lists("en")["artisan-tools-or-musical-instruments"]),
   sorted([e["slug"] for e in live[("srd52", "en", "equipment")] if e["tool_type"] == "artisan-tools"]
          + [e["slug"] for e in live[("srd52", "en", "equipment")] if e["group"] == "musical-instrument"]))
eq("тип artisan-tools — ровно у инструментов раздела «Artisan's Tools», RU — те же",
   {lang: sorted(e["slug"] for e in live[("srd52", lang, "equipment")] if e["tool_type"]) for lang in ("en", "ru")},
   {lang: ["alchemist-s-supplies", "brewer-s-supplies", "calligrapher-s-supplies", "carpenter-s-tools",
           "cartographer-s-tools", "cobbler-s-tools", "cook-s-utensils", "glassblower-s-tools", "jeweler-s-tools",
           "leatherworker-s-tools", "mason-s-tools", "painter-s-supplies", "potter-s-tools", "smith-s-tools",
           "tinker-s-tools", "weaver-s-tools", "woodcarver-s-tools"] for lang in ("en", "ru")})
saved_lists = choices.LISTS
choices.LISTS = saved_lists + ("hobbies",)
try:
    eq("список в LISTS, которого сборка не собирает, — сборка падает", with_terms()[0],
       [f"srd52/{lang}/choice-lists: список 'hobbies' не объявлен в LISTS или не собран" for lang in ("en", "ru")])
finally:
    choices.LISTS = saved_lists


# --- Слаги классов и школы у заклинаний (#482) ---------------------------------------------------
from generate_api import slug_spell_refs  # noqa: E402

eq("заклинания: class_slugs напротив classes, школа слагом, RU — как EN",
   ([s["slug"] for s in live[("srd52", "en", "spells")] if len(s["class_slugs"]) != len(s["classes"])
     or s["school_slug"] != s["school"].lower()],
    {s["slug"]: (sorted(s["class_slugs"]), s["school_slug"]) for s in live[("srd52", "ru", "spells")]}),
   ([], {s["slug"]: (sorted(s["class_slugs"]), s["school_slug"]) for s in live[("srd52", "en", "spells")]}))
# --- Weapon Mastery: сколько видов оружия меняется за раз (#491) ---------------------------------
MASTERY = {"barbarian": "one", "fighter": "one", "paladin": "any", "ranger": "any", "rogue": "any"}
for lang in ("en", "ru"):
    eq(f"{lang}: replace_count у Weapon Mastery пяти классов",
       {slug: [c.get("replace_count") for c in feature(lang, "classes", slug, i)["choices"] if c["kind"] == "weapon-mastery"]
        for slug, cls in by_slug(lang, "classes").items() for i, f in enumerate(cls["features"])
        if any(c["kind"] == "weapon-mastery" for c in f["choices"])},
       {slug: [count] for slug, count in MASTERY.items()})
eq("replace_count только у weapon-mastery",
   sorted({c["kind"] for owner in all_choices("en").values() for c in owner if "replace_count" in c}), ["weapon-mastery"])


def mastery_text(slug, old, new):
    def mutate(data):
        cls = next(c for c in data[("srd52", "en", "classes")] if c["slug"] == slug)
        f = next(f for f in cls["features"] if f["name"] == "Weapon Mastery")
        assert old in f["description_md"]
        f["description_md"] = f["description_md"].replace(old, new)
    return mutate


eq("Weapon Mastery без фразы о замене роняет сборку",
   rebuilt(mastery_text("fighter", "change one of those weapon choices", "change a weapon choice")),
   ["classes/fighter/Weapon Mastery: сколько видов оружия меняется — фраз нет"])
eq("обе фразы о замене в одном умении роняют сборку",
   rebuilt(mastery_text("rogue", "change the kinds of weapons you chose",
                        "change the kinds of weapons you chose or change one of those weapon choices")),
   ["classes/rogue/Weapon Mastery: сколько видов оружия меняется — фраз ['one', 'any']"])
choice_ok = jsonschema.Draft7Validator(_CHOICES).is_valid
mastery = one(feature("en", "classes", "rogue", "Weapon Mastery"), "weapons")
eq("схема: weapon-mastery без replace_count отклонён",
   choice_ok([{k: v for k, v in mastery.items() if k != "replace_count"}]), False)
eq("схема: replace_count вне one/any отклонён", choice_ok([{**mastery, "replace_count": "two"}]), False)
eq("схема: replace_count у другого вида отклонён",
   choice_ok([{**one(feature("en", "classes", "bard", "Bard Subclass"), "subclass"), "replace_count": "one"}]), False)
eq("схема: живые выборы приняты",
   [where for where, owner in all_choices("en").items() if not choice_ok(owner)], [])

spell_data = copy.deepcopy(live)
spell_data[("srd52", "ru", "spells")][0]["classes"] = ["Изобретатель"]
eq("класс заклинания не найден по имени — сборка падает", slug_spell_refs(spell_data),
   [f"srd52/ru/spells/{spell_data[('srd52', 'ru', 'spells')][0]['slug']}: класс ['Изобретатель'] или школа "
    f"{spell_data[('srd52', 'ru', 'spells')][0]['school_slug']!r} не найдены"])

# --- Механика умений: фиксированные языки (#502) и бонус урона по выбору (#501) ---------------------
LANGS = {("classes", "druid", "Druidic"): ["druidic"], ("classes", "rogue", "Thieves' Cant"): ["thieves-cant"]}
AFFINITY = [{"ability": "cha", "applies_to": "spell", "rolls": "one", "damage_type": {"choice": "damage-type"}}]


def mechanic(lang, field):
    return {(res, e["slug"], i): f[field] for res in ("classes", "subclasses") for e in live[("srd52", lang, res)]
            for i, f in enumerate(e["features"]) if f.get(field)}


en_index = {(res, e["slug"], f["name"]): i for res in ("classes", "subclasses") for e in live[("srd52", "en", res)]
            for i, f in enumerate(e["features"])}
for lang in ("en", "ru"):
    eq(f"{lang}: languages — у Druidic и Thieves' Cant, на позициях EN", mechanic(lang, "languages"),
       {(res, slug, en_index[(res, slug, name)]): value for (res, slug, name), value in LANGS.items()})
    eq(f"{lang}: damage_bonuses — только у Elemental Affinity", mechanic(lang, "damage_bonuses"),
       {("subclasses", "draconic-sorcery", en_index[("subclasses", "draconic-sorcery", "Elemental Affinity")]): AFFINITY})
    cant = feature(lang, "classes", "rogue", en_index[("classes", "rogue", "Thieves' Cant")])
    eq(f"{lang}: Thieves' Cant — фиксированный язык и выбор ещё одного",
       (cant.get("languages"), [(c["kind"], c["count"], c["from"]) for c in cant["choices"]]),
       (["thieves-cant"], [("language", 1, {"list": "languages", "values": None})]))
    fiend = feature(lang, "subclasses", "fiend-patron", en_index[("subclasses", "fiend-patron", "Fiendish Resilience")])
    eq(f"{lang}: Fiendish Resilience — выбор damage-type без бонуса урона",
       ([c["kind"] for c in fiend["choices"]], fiend.get("damage_bonuses")), (["damage-type"], []))
eq("слаги языков механики — члены списка languages",
   {slug for value in LANGS.values() for slug in value}
   <= {m["slug"] for lst_ in live[("srd52", "en", "choice-lists")] if lst_["slug"] == "languages" for m in lst_["members"]},
   True)

eq("язык вне списка languages роняет сборку",
   rebuilt(FEATURE_LANGUAGES=also("FEATURE_LANGUAGES", ("rogue", "Thieves' Cant"), ["thieves-argot"])),
   ["classes/rogue/Thieves' Cant: языка 'thieves-argot' нет в списке languages",
    "classes/rogue/Thieves' Cant: языки в тексте ['thieves-cant'] ≠ объявленным ['thieves-argot']"])
eq("язык объявлен, а в тексте его нет, — сборка падает",
   rebuilt(FEATURE_LANGUAGES=also("FEATURE_LANGUAGES", ("rogue", "Thieves' Cant"), ["thieves-cant", "druidic"])),
   ["classes/rogue/Thieves' Cant: языки в тексте ['thieves-cant'] ≠ объявленным ['thieves-cant', 'druidic']"])
eq("язык в тексте без объявления роняет сборку",
   rebuilt(FEATURE_LANGUAGES={k: v for k, v in choices.FEATURE_LANGUAGES.items() if k[0] != "druid"}),
   ["classes/druid/Druidic: языки в тексте ['druidic'] ≠ объявленным []"])
eq("объявление языка для умения, которого нет, роняет сборку",
   rebuilt(FEATURE_LANGUAGES=also("FEATURE_LANGUAGES", ("rogue", "Thieves Cant"), ["thieves-cant"])),
   ["объявление без хозяина: languages ('rogue', 'Thieves Cant')"])
eq("бонус урона по выбору, которого у умения нет, роняет сборку",
   rebuilt(DAMAGE_BONUSES=also("DAMAGE_BONUSES", ("draconic-sorcery", "Elemental Affinity"),
                               [{**AFFINITY[0], "damage_type": {"choice": "element"}}])),
   ["subclasses/draconic-sorcery/Elemental Affinity: бонус урона ссылается на выбор 'element', "
    "а выбора вида damage-type с таким id у умения нет"])
eq("бонус урона у умения без выбора damage-type роняет сборку",
   rebuilt(DAMAGE_BONUSES=also("DAMAGE_BONUSES", ("draconic-sorcery", "Draconic Resilience"), AFFINITY)),
   ["subclasses/draconic-sorcery/Draconic Resilience: бонус урона ссылается на выбор 'damage-type', "
    "а выбора вида damage-type с таким id у умения нет"])


def mutate_feature(res, slug, name, **fields):
    def go(data):
        next(f for e in data[("srd52", "en", res)] if e["slug"] == slug for f in e["features"] if f["name"] == name).update(fields)
    return go


eq("неизвестный ключ атак и группа КД роняют сборку",
   rebuilt(mutate_feature("classes", "monk", "Unarmored Defense",
                          attacks={"key": "flurry", "count": 2, "weapon": None},
                          armor_class={"group": "natural-armor", "base": 13, "abilities": ["dex"], "shield": True,
                                       "armor": False})),
   ["classes/monk/Unarmored Defense: ключ атак 'flurry' вне ATTACK_KEYS",
    "classes/monk/Unarmored Defense: группа КД 'natural-armor' вне ARMOR_CLASS_GROUPS"])


def option_attacks(data):
    next(o for o in data[("srd52", "en", "class-options")] if o["slug"] == "thirsting-blade")["attacks"]["key"] = "pact-strike"


eq("неизвестный ключ атак у варианта роняет сборку", rebuilt(option_attacks),
   ["class-options/thirsting-blade: ключ атак 'pact-strike' вне ATTACK_KEYS"])

feature_ok = jsonschema.Draft7Validator(CLASS_SCHEMA["properties"]["features"]["items"]).is_valid
cant_en = feature("en", "classes", "rogue", "Thieves' Cant")
affinity_en = {**feature("en", "subclasses", "draconic-sorcery", "Elemental Affinity")}
affinity_en.pop("always_prepared")
eq("схема: живые умения с механикой приняты, без languages / damage_bonuses и с чужой формой бонуса — нет",
   [feature_ok(cant_en), feature_ok(affinity_en),
    feature_ok({k: v for k, v in cant_en.items() if k != "languages"}),
    feature_ok({k: v for k, v in affinity_en.items() if k != "damage_bonuses"}),
    feature_ok({**affinity_en, "damage_bonuses": [{**AFFINITY[0], "applies_to": "weapon"}]}),
    feature_ok({**affinity_en, "damage_bonuses": [{**AFFINITY[0], "rolls": "all"}]}),
    feature_ok({**affinity_en, "damage_bonuses": [{**AFFINITY[0], "damage_type": {"value": "fire"}}]})],
   [True, True, False, False, False, False, False])

if failures:
    print(f"❌ choices ({len(failures)}):")
    for f in failures:
        print(f"  — {f}")
    sys.exit(1)
print("✅ choices: 134 объявления выбора, число по уровням, источники, RU копией EN, отказы сборки")
