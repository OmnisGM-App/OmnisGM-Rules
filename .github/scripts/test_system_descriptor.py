#!/usr/bin/env python3
"""Описатель версии системы JSON API (#473, #481): флаг готовности компендиума и правила мультикласса.

Запуск: python3 .github/scripts/test_system_descriptor.py
"""
import sys
import types
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]
sys.path.insert(0, str(SCRIPTS))
import jsonschema  # noqa: E402
import config  # noqa: E402
import config_brp  # noqa: E402
import config_daggerheart  # noqa: E402
from generate_api import system_descriptor  # noqa: E402
from parsers import parse_multiclass_rules  # noqa: E402
from schemas import SYSTEM_SCHEMA  # noqa: E402

failures = []


def eq(name, got, want):
    if got != want:
        failures.append(f"{name}: получили {got!r}, ждали {want!r}")


SRC = ROOT / "src/dnd"
CREATION = (SRC / "srd-5.2/en/02_CharacterCreation.md").read_text(encoding="utf-8")
valid = jsonschema.Draft7Validator(SYSTEM_SCHEMA).is_valid

# --- SRD 5.2.1: правила мультикласса из главы создания персонажа -----------------------
srd52 = system_descriptor(config, "srd52", SRC)
eq("srd52: шапка описателя", {k: v for k, v in srd52.items() if k != "multiclass"},
   {"system": "dnd", "version": "srd52", "name": "SRD 5.2.1"})
rules = srd52["multiclass"] or {"prerequisite_score": None, "caster_level_rounding": None,
                                "spell_slots": [{"level": None, "spell_slots": None}] * 20}
eq("srd52: порог характеристики", rules["prerequisite_score"], 13)
eq("srd52: округление доли половинного заклинателя", rules["caster_level_rounding"], "up")
eq("srd52: уровни таблицы ячеек", [r["level"] for r in rules["spell_slots"]], list(range(1, 21)))
eq("srd52: ячейки уровней 1, 5, 17, 20",
   [rules["spell_slots"][n - 1]["spell_slots"] for n in (1, 5, 17, 20)],
   [[2, 0, 0, 0, 0, 0, 0, 0, 0], [4, 3, 2, 0, 0, 0, 0, 0, 0], [4, 3, 3, 3, 2, 1, 1, 1, 1],
    [4, 3, 3, 3, 3, 2, 2, 1, 1]])
eq("srd52: описатель проходит схему", valid(srd52), True)

# --- Флаг готовности: нет записи — поля нет («ещё меняется»), «stable» — из конфигурации ----
for cfg in (config, config_daggerheart, config_brp):
    eq(f"{cfg.SYSTEM}: ни одна версия не объявлена стабильной", getattr(cfg, "COMPENDIUM", {}), {})
eq("srd52: без записи нет флага", "compendium" in srd52, False)
stable_cfg = types.SimpleNamespace(**{k: getattr(config, k) for k in ("SYSTEM", "VERSION_NAMES", "MULTICLASS_RULES")},
                                   COMPENDIUM={"srd52": "stable"})
stable = system_descriptor(stable_cfg, "srd52", SRC)
eq("srd52: «stable» из конфигурации", (stable.get("compendium"), valid(stable)), ("stable", True))
eq("srd51: флаг другой версии не протекает", "compendium" in system_descriptor(stable_cfg, "srd51", SRC), False)
eq("схема: неизвестное значение флага отклонено", valid({**srd52, "compendium": "changing"}), False)

# --- Версии без главы правил мультикласса ------------------------------------------------
srd51 = system_descriptor(config, "srd51", SRC)
eq("srd51: правил мультикласса пока нет (#461)", (srd51["multiclass"], valid(srd51)), (None, True))
dh = system_descriptor(config_daggerheart, "srd10", ROOT / "src/daggerheart")
eq("daggerheart: описатель без мультикласса", (dh["system"], dh["multiclass"], valid(dh)),
   ("daggerheart", None, True))

# --- Отказы ------------------------------------------------------------------------------


def rules_error(old, new):
    if old not in CREATION:
        return f"нет фрагмента {old!r}"
    try:
        parse_multiclass_rules(CREATION.replace(old, new))
    except Exception as err:
        return str(err)
    return None


eq("5.1-форма «rounded down» читается как down",
   parse_multiclass_rules(CREATION.replace("(round up)", "(rounded down)"))["caster_level_rounding"], "down")
eq("округление без скобки роняет сборку",
   rules_error("Half your levels (round up) in the", "Half your levels, rounded up, in the"),
   "multiclass rules: 0 matches for the half-caster rounding")
eq("порог другой формулировкой роняет сборку",
   rules_error("you must have a score of at least 13", "you need a score of 13"),
   "multiclass rules: 0 matches for the prerequisite score")
eq("порог берётся числом из текста",
   parse_multiclass_rules(CREATION.replace("a score of at least 13", "a score of at least 15"))["prerequisite_score"], 15)
eq("переименованная таблица роняет сборку",
   rules_error("Table: Multiclass Spellcaster: Spell Slots per Spell Level", "Table: Multiclass Spellcaster"),
   "multiclass rules: 0 «Table: Multiclass Spellcaster: Spell Slots per Spell Level» tables")
eq("пропавшая строка таблицы роняет сборку",
   rules_error("| 20    | 4 | 3 | 3 | 3 | 3 | 2 | 2 | 1 | 1 |\n", ""),
   f"multiclass rules: slot table levels {list(range(1, 20))}")
eq("нечисловая ячейка роняет сборку",
   rules_error("| 9     | 4 | 3 | 3 | 3 | 1 |", "| 9     | 4 | 3 | 3 | 3 | x |"),
   "multiclass rules: slot table row ['9', '4', '3', '3', '3', 'x', '—', '—', '—', '—']")
eq("схема: таблица короче 20 уровней отклонена",
   valid({**srd52, "multiclass": {**rules, "spell_slots": rules["spell_slots"][:19]}}), False)
eq("схема: округление вне up/down отклонено",
   valid({**srd52, "multiclass": {**rules, "caster_level_rounding": "nearest"}}), False)

if failures:
    print(f"❌ system descriptor ({len(failures)}):")
    for f in failures:
        print(f"  — {f}")
    sys.exit(1)
print("✅ system descriptor: флаг компендиума и правила мультикласса")
