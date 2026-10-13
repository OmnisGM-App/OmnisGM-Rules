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
from generate_api import build_species_lineages  # noqa: E402
from parsers import parse_origins, structure_species  # noqa: E402
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

if failures:
    print(f"❌ species/species-lineages ({len(failures)}):")
    for f in failures:
        print(f"  — {f}")
    sys.exit(1)
print("✅ species/species-lineages: факты и особенности 9 видов, 24 наследия, выравнивание RU, отказы")
