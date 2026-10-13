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

# --- Все 12 классов: подкласс, черта на уровнях улучшения характеристик, эпический дар ------------
ASI = {slug: [4, 8, 12, 16] for slug in classes} | {"fighter": [4, 6, 8, 12, 14, 16], "rogue": [4, 8, 10, 12, 16]}
eq("улучшение характеристик: уровни каждого класса",
   {slug: one(feature("en", "classes", slug, "Ability Score Improvement"), "feat")["levels"] for slug in classes}, ASI)
eq("подкласс: из подклассов своего класса",
   {slug: one(feature("en", "classes", slug, f"{c['name']} Subclass"), "subclass")["from"] for slug, c in classes.items()},
   {slug: {"resource": "subclasses", "filter": {"class": slug}} for slug in classes})
eq("эпический дар: любая черта, категория — подсказкой",
   {(c["from"]["filter"] == {}, c["suggest"]["category"]) for slug in classes
    for c in feature("en", "classes", slug, "Epic Boon")["choices"]}, {(True, "epic_boon")})

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
eq("заговоры барда — по колонке, замена на уровне; подготовленные жреца — на долгом отдыхе",
   (steps(feature("en", "classes", "bard", "Spellcasting"), "cantrips"),
    one(feature("en", "classes", "bard", "Spellcasting"), "cantrips")["replace"],
    one(feature("en", "classes", "cleric", "Spellcasting"), "prepared")["replace"]),
   ([(1, 2), (4, 3), (10, 4)], "level", "long-rest"))
eq("тайный аркан: четыре выбора со своим уровнем и кругом",
   [(c["id"], c["level"], c["from"]["filter"]["level"]) for c in feature("en", "classes", "warlock", "Mystic Arcanum")["choices"]],
   [("arcanum-6", 11, 6), ("arcanum-7", 13, 7), ("arcanum-8", 15, 8), ("arcanum-9", 17, 9)])

# --- Источники ----------------------------------------------------------------------------------
eq("боевой стиль паладина: черта или вариант умения",
   (one(feature("en", "classes", "paladin", "Fighting Style"), "feat")["from"],
    one(feature("en", "classes", "paladin", "Fighting Style"), "feat")["or"]),
   ({"resource": "feats", "filter": {"category": "fighting_style"}},
    {"resource": "class-options", "filter": {"class": "paladin", "feature": "fighting-style"}}))
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
   sorted(o["slug"] for o in live[("srd52", "en", "class-options")] if o["choices"]), sorted(choices.CLASS_OPTIONS))

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


eq("RU несёт те же выборы, что EN, у каждой записи, умения и особенности", all_choices("ru"), all_choices("en"))
eq("всего объявлено выборов", sum(len(v) for v in all_choices("en").values()), 130)


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
print("✅ choices: 130 объявлений выбора, число по уровням, источники, RU копией EN, отказы сборки")
