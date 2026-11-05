#!/usr/bin/env python3
"""Виды SRD 5.2 структурой и ресурс species-lineages JSON API (#413): факты вида, особенности
списком, наследия отдельными записями, выравнивание RU по EN.

Запуск: python3 .github/scripts/test_species_parser.py
"""
import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]
sys.path.insert(0, str(SCRIPTS))
from config import SKIP_HEADINGS_SPELL  # noqa: E402
from generate_api import build_species_lineages, resolve_lineage_grants  # noqa: E402
from parsers import parse_origins, parse_spells, structure_species  # noqa: E402
from schemas import SPECIES_LINEAGE_SCHEMA  # noqa: E402

failures = []


def eq(name, got, want):
    if got != want:
        failures.append(f"{name}: получили {got!r}, ждали {want!r}")


SECTION = {"en": "Species Descriptions", "ru": "Описания видов"}


def species(lang):
    text = (ROOT / "src/dnd/srd-5.2" / lang / "04_CharacterOrigins.md").read_text(encoding="utf-8")
    return parse_origins(text, SECTION[lang], lang)


pristine = {("srd52", lang, "species"): species(lang) for lang in ("en", "ru")}
live = copy.deepcopy(pristine)
eq("живой корпус: ошибок нет", build_species_lineages(live), [])

# Вид → (размеры, скорость, особенности; особенность с наследиями помечена звёздочкой).
SPECIES = {
    "dragonborn": (["medium"], 30, ["Draconic Ancestry*", "Breath Weapon", "Damage Resistance", "Darkvision", "Draconic Flight"]),
    "dwarf": (["medium"], 30, ["Darkvision", "Dwarven Resilience", "Dwarven Toughness", "Stonecunning"]),
    "elf": (["medium"], 30, ["Darkvision", "Elven Lineage*", "Fey Ancestry", "Keen Senses", "Trance"]),
    "gnome": (["small"], 30, ["Darkvision", "Gnomish Cunning", "Gnomish Lineage*"]),
    "goliath": (["medium"], 35, ["Giant Ancestry*", "Large Form", "Powerful Build"]),
    "halfling": (["small"], 30, ["Brave", "Halfling Nimbleness", "Luck", "Naturally Stealthy"]),
    "human": (["medium", "small"], 30, ["Resourceful", "Skillful", "Versatile"]),
    "orc": (["medium"], 30, ["Adrenaline Rush", "Darkvision", "Relentless Endurance"]),
    "tiefling": (["medium", "small"], 30, ["Darkvision", "Fiendish Legacy*", "Otherworldly Presence"]),
}
en = live[("srd52", "en", "species")]
eq("EN: факты и особенности девяти видов",
   {s["slug"]: (s["size"]["options"], s["speed"], [t["name"] + "*" * t["lineages"] for t in s["traits"]]) for s in en},
   SPECIES)
eq("EN: тип существа", {s["creature_type"] for s in en}, {"Humanoid"})
ru = live[("srd52", "ru", "species")]
eq("RU: размеры и скорость — как у EN, число особенностей то же",
   {s["slug"]: (s["size"]["options"], s["speed"], len(s["traits"]), sum(t["lineages"] for t in s["traits"])) for s in ru},
   {slug: (sizes, speed, len(traits), sum(t.endswith("*") for t in traits)) for slug, (sizes, speed, traits) in SPECIES.items()})
eq("RU: текст свой", (ru[6]["creature_type"], ru[6]["traits"][0]["name"], ru[6]["size"]["text"][:7]),
   ("Гуманоид", "Находчивость", "Средний"))
eq("описание вида не тронуто", [s["description_md"] for s in en],
   [s["description_md"] for s in pristine[("srd52", "en", "species")]])

LINEAGES = {
    "dragonborn": ["black", "blue", "brass", "bronze", "copper", "gold", "green", "red", "silver", "white"],
    "elf": ["drow", "high-elf", "wood-elf"],
    "gnome": ["forest-gnome", "rock-gnome"],
    "goliath": ["cloud-giant", "fire-giant", "frost-giant", "hill-giant", "stone-giant", "storm-giant"],
    "tiefling": ["abyssal", "chthonic", "infernal"],
}
for lang in ("en", "ru"):
    lineages = live[("srd52", lang, "species-lineages")]
    eq(f"{lang}: 24 наследия пяти видов, слаг — вид и вариант",
       [l["slug"] for l in lineages], [f"{sp}-{v}" for sp, variants in LINEAGES.items() for v in variants])
    eq(f"{lang}: у каждого наследия свой текст", [l["slug"] for l in lineages if not l["description_md"]], [])
    # Полную сверку со схемой делает шаг «Validate JSON API schema»; здесь — что поля те же.
    eq(f"{lang}: поля записи — поля схемы", {tuple(sorted(l)) for l in lineages},
       {tuple(sorted(SPECIES_LINEAGE_SCHEMA["required"]))})
by_slug = {lang: {l["slug"]: l for l in live[("srd52", lang, "species-lineages")]} for lang in ("en", "ru")}
eq("EN дроу: колонки таблицы в details и в тексте",
   (by_slug["en"]["elf-drow"]["trait"], [d["label"] for d in by_slug["en"]["elf-drow"]["details"]],
    by_slug["en"]["elf-drow"]["details"][1]["text"], "**Level 3:** Faerie Fire" in by_slug["en"]["elf-drow"]["description_md"]),
   ("Elven Lineage", ["Level 1", "Level 3", "Level 5"], "Faerie Fire", True))
eq("EN чёрный дракон: тип урона", by_slug["en"]["dragonborn-black"]["details"], [{"label": "Damage Type", "text": "Acid"}])
eq("EN голиаф: имя как в тексте, слаг по великану, текст абзаца",
   (by_slug["en"]["goliath-cloud-giant"]["name"], by_slug["en"]["goliath-cloud-giant"]["details"],
    by_slug["en"]["goliath-cloud-giant"]["description_md"][:19]),
   ("Cloud's Jaunt (Cloud Giant)", [], "As a Bonus Action, "))
eq("RU: имя своё, name_en и слаг из EN",
   (by_slug["ru"]["gnome-rock-gnome"]["name"], by_slug["ru"]["gnome-rock-gnome"]["name_en"],
    by_slug["ru"]["gnome-rock-gnome"]["trait"], by_slug["ru"]["tiefling-infernal"]["details"][0]["label"]),
   ("Скальный гном", "Rock Gnome", "Гномья родословная", "Уровень 1"))
# RU-наследие получает слаг EN по позиции: эталон имён ловит перестановку строк внутри вида.
RU_NAMES = {
    "dragonborn-black": "Чёрный", "dragonborn-blue": "Синий", "dragonborn-brass": "Латунный",
    "dragonborn-bronze": "Бронзовый", "dragonborn-copper": "Медный", "dragonborn-gold": "Золотой",
    "dragonborn-green": "Зелёный", "dragonborn-red": "Красный", "dragonborn-silver": "Серебряный",
    "dragonborn-white": "Белый", "elf-drow": "Дроу", "elf-high-elf": "Высший эльф", "elf-wood-elf": "Лесной эльф",
    "gnome-forest-gnome": "Лесной гном", "gnome-rock-gnome": "Скальный гном",
    "goliath-cloud-giant": "Прыжок облака (Облачный великан)", "goliath-fire-giant": "Ожог огня (Огненный великан)",
    "goliath-frost-giant": "Холод мороза (Ледяной великан)", "goliath-hill-giant": "Опрокидывание холма (Холмовой великан)",
    "goliath-stone-giant": "Стойкость камня (Каменный великан)", "goliath-storm-giant": "Гром бури (Штормовой великан)",
    "tiefling-abyssal": "Бездны", "tiefling-chthonic": "Хтоническое", "tiefling-infernal": "Инфернальное",
}
eq("RU: имя каждого наследия под своим слагом", {slug: l["name"] for slug, l in by_slug["ru"].items()}, RU_NAMES)
eq("наследия-абзацы не попали в особенности гнома и голиафа",
   [t["name"] for s in en if s["slug"] in ("gnome", "goliath") for t in s["traits"]
    if t["name"] in ("Forest Gnome", "Rock Gnome") or "Giant)" in t["name"]], [])


# --- Отказы ---------------------------------------------------------------------------
def broken(lang, slug, old, new):
    data = copy.deepcopy(pristine)
    target = next(s for s in data[("srd52", lang, "species")]
                  if (s["slug"] or "") == slug or s.get("name_en") == slug)
    if old not in target["description_md"]:
        return [f"нет фрагмента {old!r}"]
    target["description_md"] = target["description_md"].replace(old, new)
    return build_species_lineages(data)


eq("вид без скорости роняет сборку", broken("en", "dwarf", "**Speed:** 30 feet", ""),
   ["srd52: Dwarf: species facts lack ['Speed']"])
eq("незнакомый размер роняет сборку", broken("en", "orc", "**Size:** Medium", "**Size:** Large"),
   ["srd52: Orc: size 'Large (about 6–7 feet tall)' or speed '30 feet' not read"])
eq("особенность с наследиями переименована — сборка падает",
   broken("en", "elf", "**Elven Lineage.**", "**Elven Heritage.**"),
   ["srd52: Elf: lineage trait 'Elven Lineage' not found"])
eq("строка таблицы наследий пропала — сборка падает",
   broken("en", "tiefling", "| Infernal ", "Infernal "), ["srd52: Tiefling: 2 lineages, declared 3"])
eq("вариант голиафа пропал — особенность за ним не становится наследием",
   broken("en", "goliath", "**Storm's Thunder (Storm Giant).**", "Storm's Thunder (Storm Giant)."),
   ["srd52: Goliath: lineages of 'Giant Ancestry' do not match the declaration: ['Large Form']"])
eq("третий вариант гнома не уходит молча в особенности",
   broken("en", "gnome", "**Rock Gnome.**", "**Deep Gnome.** Text.\n\n**Rock Gnome.**")[0][:60],
   "srd52: Gnome: lineages of 'Gnomish Lineage' do not match the")
eq("строка таблицы наследий короче заголовка — сборка падает",
   broken("en", "elf", '| Faerie Fire  | Darkness           |', "| Faerie Fire |"),
   ["srd52: Elf: lineage row 'Drow' has 3 cells, the header has 4"])
eq("таблица у вида без объявленных наследий — сборка падает",
   broken("en", "human", "**Skillful.**", "| A | B |\n|---|---|\n| 1 | 2 |\n\n**Skillful.**"),
   ["srd52: Human: a table in a species without a declared lineage table"])
eq("RU-вид без особенности — ошибка структуры",
   any("ru/halfling: структура RU ≠ EN" in e for e in broken("ru", "Halfling", "**Удача.**", "Удача.")), True)
eq("RU-вид с другим размером — ошибка структуры",
   any("ru/gnome: структура RU ≠ EN" in e for e in broken("ru", "Gnome", "**Размер:** Маленький", "**Размер:** Средний")), True)
eq("RU-таблица, разорванная посередине, — сборка падает",
   broken("ru", "Elf", "| Дроу ", "Дроу "), ["srd52: Эльф: expected one lineage table, found 2"])


# --- Механика наследий и уровни особенностей (#476) ------------------------------------
SPELLS = {lang: parse_spells((ROOT / "src/dnd/srd-5.2" / lang / "07_Spells.md").read_text(encoding="utf-8"),
                             3, lang, None, SKIP_HEADINGS_SPELL) for lang in ("en", "ru")}


def granted(lang="en", slug=None, old=None, new=None, spells=None):
    data = copy.deepcopy(pristine)
    if old is not None:
        target = next(s for s in data[("srd52", lang, "species")] if s["slug"] == slug)
        assert old in target["description_md"], old
        target["description_md"] = target["description_md"].replace(old, new)
    for spell_lang in ("en", "ru"):
        data[("srd52", spell_lang, "spells")] = (spells or {}).get(spell_lang, SPELLS[spell_lang])
    errors = build_species_lineages(data)
    errors += resolve_lineage_grants(data)
    return data, errors


grants_data, grant_errors = granted()
eq("живой корпус с заклинаниями: ошибок нет", grant_errors, [])
ONCE = {"count": 1, "recharge": "long-rest"}
PB = {"count": "proficiency-bonus", "recharge": "long-rest"}


def spells_of(*rows):
    return [{"slug": slug, "level": level, "uses": uses} for slug, level, uses in rows]


def grants(spells=(), damage_type=None, resistances=(), darkvision=None, speed_min=None, uses=None):
    return {"spells": spells_of(*spells), "damage_type": damage_type, "resistances": list(resistances),
            "darkvision": darkvision, "speed_min": speed_min, "uses": uses}


DRAGON = {"black": "acid", "blue": "lightning", "brass": "fire", "bronze": "lightning", "copper": "acid",
          "gold": "fire", "green": "poison", "red": "fire", "silver": "cold", "white": "cold"}
GIANT = {"cloud": None, "fire": "fire", "frost": "cold", "hill": None, "stone": None, "storm": "thunder"}
GRANTS = {
    **{f"dragonborn-{colour}": grants(damage_type=t) for colour, t in DRAGON.items()},
    "elf-drow": grants([("dancing-lights", 1, None), ("faerie-fire", 3, ONCE), ("darkness", 5, ONCE)], darkvision=120),
    "elf-high-elf": grants([("prestidigitation", 1, None), ("detect-magic", 3, ONCE), ("misty-step", 5, ONCE)]),
    "elf-wood-elf": grants([("druidcraft", 1, None), ("longstrider", 3, ONCE), ("pass-without-trace", 5, ONCE)],
                           speed_min=35),
    "gnome-forest-gnome": grants([("minor-illusion", 1, None), ("speak-with-animals", 1, PB)]),
    "gnome-rock-gnome": grants([("mending", 1, None), ("prestidigitation", 1, None)]),
    **{f"goliath-{giant}-giant": grants(damage_type=t, uses=PB) for giant, t in GIANT.items()},
    "tiefling-abyssal": grants([("poison-spray", 1, None), ("ray-of-sickness", 3, ONCE), ("hold-person", 5, ONCE)],
                               resistances=["poison"]),
    "tiefling-chthonic": grants([("chill-touch", 1, None), ("false-life", 3, ONCE), ("ray-of-enfeeblement", 5, ONCE)],
                                resistances=["necrotic"]),
    "tiefling-infernal": grants([("fire-bolt", 1, None), ("hellish-rebuke", 3, ONCE), ("darkness", 5, ONCE)],
                                resistances=["fire"]),
}
for lang in ("en", "ru"):
    eq(f"{lang}: механика 24 наследий", {l["slug"]: l["grants"] for l in grants_data[("srd52", lang, "species-lineages")]},
       GRANTS)
    eq(f"{lang}: уровни особенностей вида",
       {(s["slug"], t["level"]) for s in grants_data[("srd52", lang, "species")] for t in s["traits"] if t["level"]},
       {("dragonborn", 5), ("goliath", 5)})
eq("EN: details и description_md наследий не тронуты",
   [(l["details"], l["description_md"]) for l in grants_data[("srd52", "en", "species-lineages")]],
   [(l["details"], l["description_md"]) for l in structure_species(copy.deepcopy(pristine[("srd52", "en", "species")]), "en")[0]])


def grant_errors_of(*args, **kwargs):
    return granted(*args, **kwargs)[1]


eq("EN: заклинание, которого нет в spells, — ошибка",
   grant_errors_of("en", "elf", "| Faerie Fire  |", "| Fairy Fire  |"),
   ["srd52/en/elf-drow: заклинание «Fairy Fire» не найдено в spells"])
eq("EN: заклинание с уровнем без фразы о бесплатных сотворениях — ошибка",
   grant_errors_of("en", "gnome", "a number of times equal to your Proficiency Bonus, and you regain all expended uses",
                   "twice, and you regain all expended uses"),
   ["srd52/en/gnome-forest-gnome: у «Speak with Animals» нет фразы о бесплатных сотворениях"])
eq("EN: тип урона вне списка — ошибка",
   grant_errors_of("en", "dragonborn", "| Black  | Acid ", "| Black  | Ooze "),
   ["srd52/en/dragonborn-black: тип урона «ooze» вне списка"])
eq("EN: уровень особенности из «Starting at character level N»",
   [t["level"] for s in granted("en", "goliath", "Starting at character level 5", "Starting at character level 7")[0]
    [("srd52", "en", "species")] if s["slug"] == "goliath" for t in s["traits"] if t["name"] == "Large Form"], [7])
eq("RU: имя заклинания RU не стоит в тексте наследия — ошибка",
   grant_errors_of("ru", "tiefling", "*Тьма* |", "*Мрак* |"),
   ["srd52/ru/tiefling-infernal: в тексте нет заклинания «Тьма» (darkness)"])
eq("RU: слага заклинания нет в RU spells — ошибка",
   grant_errors_of(spells={"ru": [s for s in SPELLS["ru"] if s["slug"] != "longstrider"]}),
   ["srd52/ru/elf-wood-elf: заклинания «longstrider» нет в RU spells"])
eq("RU: другое число тёмного зрения — ошибка",
   grant_errors_of("ru", "elf", "увеличивается до 120 футов", "увеличивается до 90 футов"),
   ["srd52/ru/elf-drow: в тексте нет числа darkvision = 120 из EN"])
eq("RU: в особенности нет уровня из EN — ошибка",
   grant_errors_of("ru", "goliath", "Начиная с 5-го уровня персонажа", "Начиная с 7-го уровня персонажа"),
   ["srd52/ru/goliath: в особенности «Большая форма» нет уровня 5 из EN"])

if failures:
    print(f"❌ species/species-lineages ({len(failures)}):")
    for f in failures:
        print(f"  — {f}")
    sys.exit(1)
print("✅ species/species-lineages: факты и особенности 9 видов, 24 наследия, механика наследий, выравнивание RU, отказы")
