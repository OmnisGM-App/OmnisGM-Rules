#!/usr/bin/env python3
"""Семейства магических предметов SRD 5.2 в JSON API (#412): запись-семейство уходит из `magic-items`,
её разновидности — отдельные записи с одной редкостью; RU выравнивается по EN.

Запуск: python3 .github/scripts/test_magic_item_families.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]
sys.path.insert(0, str(SCRIPTS))
import config  # noqa: E402
from generate_api import build_magic_item_groups  # noqa: E402
from parsers import parse_magic_items  # noqa: E402

failures = []


def eq(name, got, want):
    if got != want:
        failures.append(f"{name}: получили {got!r}, ждали {want!r}")


def source(lang, ver="srd52"):
    return next(s for s in config.SOURCES if s["ver"] == ver and s["lang"] == lang and s["type"] == "magic_item")


def text(lang):
    return (ROOT / "src/dnd" / source(lang)["file"]).read_text(encoding="utf-8")


def parsed(lang, body=None):
    src = source(lang)
    return parse_magic_items(body if body is not None else text(lang), src["h"], lang, src.get("after"), families=True)


def build(en_text=None, ru_text=None):
    data = {("srd52", "en", "magic-items"): parsed("en", en_text), ("srd52", "ru", "magic-items"): parsed("ru", ru_text)}
    return data, build_magic_item_groups(data)


live, errors = build()
eq("живой корпус: ошибок нет", errors, [])

# Семейство → предметы: (слаг, имя, редкость). Выписано из главы «Magic Items A–Z».
BONUS = lambda base, slug, rarities: [(f"{slug}-{n}", f"{base} +{n}", r) for n, r in zip((1, 2, 3), rarities)]  # noqa: E731
GIANTS = lambda base, slug, rarities: [  # noqa: E731
    (f"{slug}-{s}", f"{base} ({g})", r) for (s, g), r in zip(
        (("hill", "hill"), ("frost-or-stone", "frost or stone"), ("fire", "fire"), ("cloud", "cloud"), ("storm", "storm")), rarities)]
IOUN = [("absorption", "Absorption", "very rare"), ("agility", "Agility", "very rare"), ("awareness", "Awareness", "rare"),
        ("fortitude", "Fortitude", "very rare"), ("greater-absorption", "Greater Absorption", "legendary"),
        ("insight", "Insight", "very rare"), ("intellect", "Intellect", "very rare"), ("leadership", "Leadership", "very rare"),
        ("mastery", "Mastery", "legendary"), ("protection", "Protection", "rare"), ("regeneration", "Regeneration", "legendary"),
        ("reserve", "Reserve", "rare"), ("strength", "Strength", "very rare"), ("sustenance", "Sustenance", "rare")]
FAMILIES = {
    "ammunition-1-2-or-3": BONUS("Ammunition", "ammunition", ("uncommon", "rare", "very rare")),
    "armor-1-2-or-3": BONUS("Armor", "armor", ("rare", "very rare", "legendary")),
    "belt-of-giant-strength": GIANTS("Belt of Giant Strength", "belt-of-giant-strength",
                                     ("rare", "very rare", "very rare", "legendary", "legendary")),
    "feather-token": [(f"feather-token-{s}", f"Feather Token ({n})", r) for s, n, r in (
        ("anchor", "Anchor", "uncommon"), ("bird", "Bird", "rare"), ("fan", "Fan", "uncommon"),
        ("swan-boat", "Swan Boat", "rare"), ("tree", "Tree", "uncommon"), ("whip", "Whip", "rare"))],
    "figurine-of-wondrous-power": [
        ("bronze-griffon", "Bronze Griffon", "rare"), ("ebony-fly", "Ebony Fly", "rare"), ("golden-lions", "Golden Lions", "rare"),
        ("ivory-goats", "Ivory Goats", "rare"), ("marble-elephant", "Marble Elephant", "rare"),
        ("obsidian-steed", "Obsidian Steed", "very rare"), ("onyx-dog", "Onyx Dog", "rare"),
        ("serpentine-owl", "Serpentine Owl", "rare"), ("silver-raven", "Silver Raven", "uncommon")],
    "horn-of-valhalla": [(f"horn-of-valhalla-{s}", f"Horn of Valhalla ({n})", r) for s, n, r in (
        ("silver", "Silver", "rare"), ("brass", "Brass", "rare"), ("bronze", "Bronze", "very rare"), ("iron", "Iron", "legendary"))],
    "ioun-stone": [(f"ioun-stone-{s}", f"Ioun Stone ({n})", r) for s, n, r in IOUN],
    "potion-of-giant-strength": GIANTS("Potion of Giant Strength", "potion-of-giant-strength",
                                       ("uncommon", "rare", "rare", "very rare", "legendary")),
    "potions-of-healing": [("potion-of-healing", "Potion of Healing", "common"),
                           ("potion-of-healing-greater", "Potion of Healing (greater)", "uncommon"),
                           ("potion-of-healing-superior", "Potion of Healing (superior)", "rare"),
                           ("potion-of-healing-supreme", "Potion of Healing (supreme)", "very rare")],
    "shield-1-2-or-3": BONUS("Shield", "shield", ("uncommon", "rare", "very rare")),
    "wand-of-the-war-mage-1-2-or-3": BONUS("Wand of the War Mage", "wand-of-the-war-mage", ("uncommon", "rare", "very rare")),
    "weapon-1-2-or-3": BONUS("Weapon", "weapon", ("uncommon", "rare", "very rare")),
}
en = {e["slug"]: e for e in live[("srd52", "en", "magic-items")]}
ru = {e["slug"]: e for e in live[("srd52", "ru", "magic-items")]}
en_groups = {g["slug"]: g for g in live[("srd52", "en", "magic-item-groups")]}
ru_groups = {g["slug"]: g for g in live[("srd52", "ru", "magic-item-groups")]}
eq("EN: 12 семейств, 62 предмета — слаг, имя, одна редкость",
   {slug: [(i, en[i]["name"], en[i]["rarity"]) for i in g["items"]] for slug, g in en_groups.items()}, FAMILIES)
eq("всего предметов семейств", sum(len(v) for v in FAMILIES.values()), 62)
eq("у каждого предмета семейства rarities — его одна редкость",
   [s for g in en_groups.values() for s in g["items"] if en[s]["rarities"] != [en[s]["rarity"]]], [])
eq("записи-семейства ушли из magic-items", sorted(set(FAMILIES) & set(en)), [])
eq("без редкости остался только свиток заклинания", [s for s, e in en.items() if not e["rarities"]], ["spell-scroll"])
eq("предметов с несколькими редкостями не осталось", [s for s, e in en.items() if len(e["rarities"]) > 1], [])
eq("у предмета вне семейства group — null",
   {e["group"] for s, e in en.items() if s not in {i for v in FAMILIES.values() for i, _, _ in v}}, {None})
eq("тип, подтип и настройка — от семейства",
   (en["weapon-1"]["type"], en["weapon-1"]["subtype"], en["ioun-stone-mastery"]["attunement"]["required"],
    en["wand-of-the-war-mage-2"]["attunement"]["condition"]),
   ("Weapon", "Any Simple or Martial", True, "by a Spellcaster"))
eq("строка таблицы: общий текст и своя величина",
   (en["potion-of-healing-greater"]["description_md"].startswith("You regain Hit Points when you drink this potion."),
    en["potion-of-healing-greater"]["description_md"].endswith("\n\n**HP Regained:** 4d4 + 4"),
    en["belt-of-giant-strength-fire"]["description_md"].endswith("\n\n**Str.:** 25")),
   (True, True, True))
eq("рог: редкость по металлу из строки типа, духи и требование",
   en["horn-of-valhalla-bronze"]["description_md"].endswith("\n\n**Spirits:** 4\n\n**Requirement:** Training with all Medium armor"), True)
eq("«+N»: бонус строкой, текст семейства сохранён",
   (en["shield-3"]["description_md"].endswith("\n\n**Bonus:** +3"), en["shield-3"]["description_md"][:20]), (True, "While holding this S"))
eq("камень Иоун: общий текст семейства и свой абзац",
   ("orbit" in en["ioun-stone-protection"]["description_md"][:400],
    en["ioun-stone-protection"]["description_md"].endswith(
        "\n\nYou gain a +1 bonus to Armor Class while this dusty-rose prism orbits your head.")),
   (True, True))
eq("козлы из слоновой кости — один предмет с тремя фигурками в описании",
   [w in en["ivory-goats"]["description_md"] for w in ("Goat of Terror", "Goat of Traveling", "Goat of Travail", "Marble Elephant")],
   [True, True, True, False])
eq("в описаниях предметов семейств нет таблиц",
   [s for lang_items, groups in ((en, en_groups), (ru, ru_groups)) for g in groups.values() for s in g["items"]
    if "|" in lang_items[s]["description_md"] and s != "ebony-fly"], [])

# RU: слаг и name_en — от EN по позиции; эталон имён ловит перестановку.
RU_NAMES = {
    "potion-of-healing": "Зелье лечения", "potion-of-healing-greater": "Зелье лечения (усиленное)",
    "potion-of-healing-superior": "Зелье лечения (превосходное)", "potion-of-healing-supreme": "Зелье лечения (высшее)",
    "weapon-1": "Оружие +1", "armor-3": "Доспех +3", "shield-2": "Щит +2", "ammunition-1": "Боеприпасы +1",
    "wand-of-the-war-mage-3": "Волшебная палочка боевого мага +3",
    "belt-of-giant-strength-hill": "Пояс силы великана (холмовой)", "belt-of-giant-strength-storm": "Пояс силы великана (штормовой)",
    "potion-of-giant-strength-frost-or-stone": "Зелье силы великана (ледяного или каменного)",
    "horn-of-valhalla-silver": "Рог Валгаллы (Серебряный)", "horn-of-valhalla-iron": "Рог Валгаллы (Железный)",
    "ioun-stone-absorption": "Боевой камень Иуна (Поглощение)", "ioun-stone-sustenance": "Боевой камень Иуна (Пропитание)",
    "feather-token-anchor": "Перо-талисман (Якорь)", "feather-token-whip": "Перо-талисман (Кнут)",
    "bronze-griffon": "Бронзовый грифон", "ivory-goats": "Козлы из слоновой кости", "silver-raven": "Серебряный ворон",
}
eq("RU: имена под слагами EN", {s: ru[s]["name"] for s in RU_NAMES}, RU_NAMES)
eq("RU: name_en, семейство и редкость — как у EN",
   [s for g in en_groups.values() for s in g["items"]
    if (ru[s]["name_en"], ru[s]["group"], ru[s]["rarity"]) != (en[s]["name"], en[s]["group"], en[s]["rarity"])], [])
eq("RU-семейства: те же слаги и предметы", {s: g["items"] for s, g in ru_groups.items()}, {s: g["items"] for s, g in en_groups.items()})
eq("всего магических предметов: 308 в каждом языке", (len(en), len(ru)), (308, 308))

# 5.1 семейства не режет: там они не объявлены.
old = source("en", "srd51")
legacy = parse_magic_items((ROOT / "src/dnd" / old["file"]).read_text(encoding="utf-8"), old["h"], "en", old.get("after"))
eq("5.1: записей-семейств нет, поле group пустое", ({i.get("_group", False) for i in legacy}, {i["group"] for i in legacy}), ({False}, {None}))


# --- Отказы ---------------------------------------------------------------------------
def broken(lang, old_text, new_text):
    body = text(lang)
    if old_text not in body:
        return [f"нет фрагмента {old_text!r}"]
    try:
        return build(**{f"{lang}_text": body.replace(old_text, new_text)})[1]
    except ValueError as err:
        return [str(err)]


eq("строка таблицы зелий пропала — сборка падает",
   broken("en", "| Potion of Healing (supreme)  | 10d4 + 20   | Very Rare |\n", ""), ["Potions of Healing: 3 varieties, declared 4"])
eq("незнакомая редкость в таблице — сборка падает",
   broken("en", "| Potion of Healing (greater)  | 4d4 + 4     | Uncommon  |", "| Potion of Healing (greater)  | 4d4 + 4     | Unusual   |"),
   ["Potions of Healing: unknown rarity 'Unusual'"])
eq("абзац камня без редкости в скобках — число не сходится",
   broken("en", "**_Mastery (Legendary)._**", "**_Mastery._**"), ["Ioun Stone: 13 varieties, declared 14"])
eq("редкость бонуса пропала из строки типа — сборка падает",
   broken("en", "*Armor (Shield), Uncommon (+1), Rare (+2), or Very Rare (+3)*", "*Armor (Shield), Uncommon (+1) or Rare (+2)*")[0][:39],
   "Shield, +1, +2, or +3: no rarity for +3")
eq("металл рога без редкости — сборка падает",
   broken("en", "| 76–90 | Bronze    |", "| 76–90 | Copper    |")[0][:44], "Horn of Valhalla: no rarity for 'Copper' in ")
eq("RU: абзац жетона пропал — сборка падает",
   broken("ru", "**_Кнут (редкий)._**", "Кнут."), ["Перо-талисман: 5 varieties, declared 6"])
eq("RU: редкость строки не как у EN — расхождение",
   broken("ru", "| Зелье лечения (усиленное) | 4d4 + 4 | Необычный |", "| Зелье лечения (усиленное) | 4d4 + 4 | Редкий |"),
   ["srd52/ru/potions-of-healing: «Зелье лечения (усиленное)» (rare) не сходится с EN «Potion of Healing (greater)» (uncommon)"])

# Семейство — не ресурс API: в публичной сборке его нет, в сборке сайта (--site-data) есть.
with tempfile.TemporaryDirectory() as out:
    for flags, want in (([], False), (["--site-data"], True)):
        run = subprocess.run([sys.executable, str(SCRIPTS / "generate_api.py"), "--src-root", str(ROOT / "src/dnd"),
                              "--output-dir", f"{out}/{len(flags)}", "--no-validate", *flags], capture_output=True, text=True)
        eq(f"generate_api {' '.join(flags) or 'без флага'}: сборка прошла", run.returncode, 0)
        eq(f"generate_api {' '.join(flags) or 'без флага'}: magic-item-groups {'есть' if want else 'нет'}",
           [(Path(out) / str(len(flags)) / "dnd/srd52" / lang / "magic-item-groups").exists() for lang in ("en", "ru")], [want, want])

if failures:
    print(f"❌ magic-item-families ({len(failures)}):")
    for f in failures:
        print(f"  — {f}")
    sys.exit(1)
print("✅ magic-item-families: 12 семейств и 62 предмета с одной редкостью, RU по EN, 5.1 не тронут, отказы")
