#!/usr/bin/env python3
"""Строка типа и редкости магического предмета: одна редкость, несколько, «редкость варьируется».

Запуск: python3 .github/scripts/test_magic_item_parser.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parsers.magic_item import _parse_type_rarity_line  # noqa: E402

failures = []


def eq(name, got, want):
    if got != want:
        failures.append(f"{name}: получили {got!r}, ждали {want!r}")


def line(text, lang="en"):
    r = _parse_type_rarity_line(text, lang)
    return r["type"], r["subtype"], r["rarity"], r["rarities"], r["attunement"]["required"], r["attunement"]["condition"]


eq("одна редкость", line("*Wondrous Item, Rare (Requires Attunement)*"),
   ("Wondrous Item", None, "rare", ["rare"], True, None))
eq("«very rare» не читается как «rare»", line("*Ring, Very Rare*"),
   ("Ring", None, "very rare", ["very rare"], False, None))
eq("подтип в скобках", line("*Armor (Any Medium or Heavy, Except Hide Armor), Uncommon*"),
   ("Armor", "Any Medium or Heavy, Except Hide Armor", "uncommon", ["uncommon"], False, None))
eq("три редкости «+1, +2 или +3»", line("*Weapon (Any Ammunition), Uncommon (+1), Rare (+2), or Very Rare (+3)*"),
   ("Weapon", "Any Ammunition", None, ["uncommon", "rare", "very rare"], False, None))
eq("редкости с пояснением в скобках", line("*Wondrous Item, Rare (Silver or Brass), Very Rare (Bronze), or Legendary (Iron)*"),
   ("Wondrous Item", None, None, ["rare", "very rare", "legendary"], False, None))
eq("редкость варьируется", line("*Potion, Rarity Varies*"), ("Potion", None, None, [], False, None))
eq("варьируется + настройка", line("*Wondrous Item, Rarity Varies (Requires Attunement)*"),
   ("Wondrous Item", None, None, [], True, None))
eq("условие настройки", line("*Weapon (Warhammer), Very Rare (Requires Attunement by a Dwarf)*"),
   ("Weapon", "Warhammer", "very rare", ["very rare"], True, "by a Dwarf"))
eq("RU: три редкости и настройка", line("*Волшебная палочка, необычный (+1), редкий (+2) или очень редкий (+3) (требуется настройка заклинателем)*", "ru"),
   ("Волшебная палочка", None, None, ["uncommon", "rare", "very rare"], True, "заклинателем"))
eq("RU: варьируется", line("*Зелье, редкость варьируется*", "ru"), ("Зелье", None, None, [], False, None))
eq("5.1: «Varies» без слова Rarity", line("*Scroll, Varies*"), ("Scroll", None, None, [], False, None))
eq("5.1: редкость по фигурке", line("*Wondrous Item, Rarity by Figurine*"), ("Wondrous Item", None, None, [], False, None))
eq("5.1 RU: «варьируется»", line("*Свиток, варьируется*", "ru"), ("Свиток", None, None, [], False, None))
eq("5.1 RU: зависит от фигурки", line("*Чудесный предмет, редкость зависит от фигурки*", "ru"),
   ("Чудесный предмет", None, None, [], False, None))
eq("RU: род прилагательного", line("*Чудесный предмет, очень редкий*", "ru"),
   ("Чудесный предмет", None, "very rare", ["very rare"], False, None))

if failures:
    print("\n".join(f"  ✗ {f}" for f in failures))
    sys.exit(1)
print("magic_item_parser: ок")
