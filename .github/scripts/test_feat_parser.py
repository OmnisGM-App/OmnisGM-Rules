#!/usr/bin/env python3
"""Предусловия черт структурой в JSON API (#478): уровень, характеристики и умение кодами рядом со
строкой; RU берёт коды из EN по слагу; умение сверяется с умениями классов.

Запуск: python3 .github/scripts/test_feat_parser.py
"""
import copy
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]
sys.path.insert(0, str(SCRIPTS))
from config import SOURCES, SKIP_HEADINGS_FEAT  # noqa: E402
from generate_api import align_feat_prerequisites  # noqa: E402
from parsers import parse_feats  # noqa: E402
from parsers.feat import feat_prerequisites  # noqa: E402

failures = []


def eq(name, got, want):
    if got != want:
        failures.append(f"{name}: получили {got!r}, ждали {want!r}")


def feats(ver, lang, edit=None):
    src = next(s for s in SOURCES if (s["ver"], s["lang"], s["type"]) == (ver, lang, "feat"))
    text = (ROOT / "src/dnd" / src["file"]).read_text(encoding="utf-8")
    if edit:
        assert edit[0] in text, edit[0]
        text = text.replace(*edit)
    return parse_feats(text, src["h"], lang, src.get("after"), SKIP_HEADINGS_FEAT)


CLASSES = [{"features": [{"name": "Fighting Style"}, {"name": "Spellcasting"}]}]


def corpus(edit=None, edit_lang="ru"):
    data = {(ver, lang, "feats"): feats(ver, lang, edit if lang == edit_lang and ver == "srd52" else None)
            for ver in ("srd52", "srd51") for lang in ("en", "ru")}
    data[("srd52", "en", "classes")] = CLASSES
    return data


def codes(entities):
    return {f["slug"]: f["prerequisites"] and (f["prerequisites"]["level"], f["prerequisites"]["abilities"],
                                               f["prerequisites"]["feature"])
            for f in entities if f["prerequisite"]}


live = corpus()
eq("живой корпус: ошибок нет", align_feat_prerequisites(live), [])

STR_DEX_13 = {"values": ["str", "dex"], "min": 13}
BOON = (19, None, None)
FIGHTING_STYLE = (None, None, "fighting-style")
SRD52 = {
    "ability-score-improvement": (4, None, None), "grappler": (4, STR_DEX_13, None),
    "archery": FIGHTING_STYLE, "defense": FIGHTING_STYLE, "great-weapon-fighting": FIGHTING_STYLE,
    "two-weapon-fighting": FIGHTING_STYLE,
    "boon-of-combat-prowess": BOON, "boon-of-dimensional-travel": BOON, "boon-of-fate": BOON,
    "boon-of-irresistible-offense": BOON, "boon-of-spell-recall": (19, None, "spellcasting"),
    "boon-of-the-night-spirit": BOON, "boon-of-truesight": BOON,
}
for lang in ("en", "ru"):
    eq(f"srd52/{lang}: коды предусловий всех черт со строкой", codes(live[("srd52", lang, "feats")]), SRD52)
    eq(f"srd51/{lang}: «Strength 13 or higher» — характеристика без уровня",
       codes(live[("srd51", lang, "feats")]), {"grappler": (None, {"values": ["str"], "min": 13}, None)})
ru = {f["slug"]: f for f in live[("srd52", "ru", "feats")]}
eq("RU: text — своя строка, prerequisite не тронута",
   ((ru["grappler"]["prerequisites"] or {}).get("text"), ru["grappler"]["prerequisite"]),
   ("Уровень 4+, Сила или Ловкость 13+", "Уровень 4+, Сила или Ловкость 13+"))
eq("черта без строки — prerequisites null",
   [f["prerequisites"] for f in live[("srd52", "en", "feats")] if f["slug"] == "alert"], [None])

eq("невыразимая часть остаётся только в text",
   feat_prerequisites("Level 4+, Elf or Half-Elf", "en"),
   {"text": "Level 4+, Elf or Half-Elf", "level": 4, "abilities": None, "feature": None})
eq("RU сам кодов не разбирает",
   feat_prerequisites("Уровень 4+", "ru"), {"text": "Уровень 4+", "level": None, "abilities": None, "feature": None})


def broken(edit, edit_lang="ru", mutate=None):
    data = corpus(edit, edit_lang)
    if mutate:
        mutate(data)
    return align_feat_prerequisites(copy.deepcopy(data))


eq("RU: другое число в предусловии — ошибка",
   broken(("*Общая черта (Требование: Уровень 4+)*", "*Общая черта (Требование: Уровень 8+)*")),
   ["srd52/ru/ability-score-improvement: предусловие RU «Уровень 8+» ≠ EN «Level 4+» (число частей или числа)"])
eq("RU: лишняя часть предусловия — ошибка",
   broken(("Уровень 19+, умение", "Уровень 19+, Сила 13+, умение")),
   ["srd52/ru/boon-of-spell-recall: предусловие RU «Уровень 19+, Сила 13+, умение «Сотворение заклинаний»» ≠ "
    "EN «Level 19+, Spellcasting Feature» (число частей или числа)"])
eq("RU: предусловие пропало — ошибка",
   broken(("*Общая черта (Требование: Уровень 4+)*", "*Общая черта*")),
   ["srd52/ru/ability-score-improvement: предусловие есть только в одном языке"])
eq("EN: умение, которого нет у классов, — ошибка",
   broken(("Fighting Style Feat (Prerequisite: Fighting Style Feature)*\n\nYou gain a +2 bonus to attack rolls",
           "Fighting Style Feat (Prerequisite: Rage Feature)*\n\nYou gain a +2 bonus to attack rolls"), "en"),
   ["srd52/en/archery: умение-предусловие «rage» не найдено в classes"])


def first_with_prereq_ru(data):
    f = next(f for f in data[("srd52", "ru", "feats")] if f["prerequisite"])
    f["prerequisites"] = None


eq("черта со строкой, но без структуры — ошибка",
   broken(None, mutate=first_with_prereq_ru),
   ["srd52/ru/ability-score-improvement: prerequisites не сходится со строкой prerequisite"])

if failures:
    print(f"❌ feats ({len(failures)}):")
    for f in failures:
        print(f"  — {f}")
    sys.exit(1)
print("✅ feats: предусловия кодами в srd52/srd51, RU из EN, сверка с умениями классов, отказы")
