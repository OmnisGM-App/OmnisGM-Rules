#!/usr/bin/env python3
"""Регресс-тесты разбора строки типа статблока (issue #260).

Формы приходят из ВРЕЗОК — блоков вне глав монстров. Уникальное покрытие даёт одна из
них: граница диапазона («Huge or Smaller», RU «Огромный или меньший») — её откат оба
соседних гейта пропускают, потому что врезки не идут в JSON API. Остальные формы держит и
`test_statblock_headers.py`; здесь они стоят как контракт функции, а не как единственная
защита. Помимо положительных форм фиксируем и отрицательные: мусор не должен превращаться
в размер.

Запуск: python3 .github/scripts/test_monster_parser.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parsers.monster import _parse_type_line  # noqa: E402

CASES = [
    # (строка, язык, размер, тип, подтип, мировоззрение)
    ("*Large Aberration, Lawful Evil*", "en",
     "Large", "Aberration", None, "Lawful Evil"),
    ("*Medium or Small Humanoid, Neutral*", "en",
     "Medium or Small", "Humanoid", None, "Neutral"),
    # Граница диапазона: без неё размер уезжал в тип («or Smaller Construct»).
    ("*Huge or Smaller Construct, Unaligned*", "en",
     "Huge or Smaller", "Construct", None, "Unaligned"),
    # Составной тип: мировоззрение — после ПОСЛЕДНЕЙ запятой вне скобок, иначе тип
    # рвался по первой и «Fey, or Fiend (Your Choice)» уезжало в мировоззрение.
    ("*Large Celestial, Fey, or Fiend (Your Choice), Neutral*", "en",
     "Large", "Celestial, Fey, or Fiend", "Your Choice", "Neutral"),
    # Запятая ВНУТРИ скобок разделителем не считается (5.1).
    ("*Medium Fiend (Demon, Shapechanger), Chaotic Evil*", "en",
     "Medium", "Fiend", "Demon, Shapechanger", "Chaotic Evil"),
    ("*Огромный или меньший конструкт, без мировоззрения*", "ru",
     "Огромный или меньший", "конструкт", None, "без мировоззрения"),
    ("*Среднее или Маленькое Чудовище (ликантроп), нейтрально-добрый*", "ru",
     "Среднее или Маленькое", "Чудовище", "ликантроп", "нейтрально-добрый"),
]

# Отрицательные: строка без размера разбирается как есть и НЕ выдумывает составной размер.
NEGATIVE = [
    ("*Conjuration Level 4 (Druid)*", "en", "Conjuration"),
    ("*Вызов 4-го уровня (Друид)*", "ru", "Вызов"),
    ("*Medium or Cheese Humanoid, Neutral*", "en", "Medium"),
    ("", "en", ""),
]

failures = []
for line, lang, size in NEGATIVE:
    got = _parse_type_line(line, lang)
    if got.get("size") != size:
        failures.append(f"«{line}» [{lang}] size: получили {got.get('size')!r}, ждали {size!r}")
for line, lang, size, ctype, subtype, alignment in CASES:
    got = _parse_type_line(line, lang)
    want = {"size": size, "type": ctype, "subtype": subtype, "alignment": alignment}
    for key, value in want.items():
        if got.get(key) != value:
            failures.append(f"«{line}» [{lang}] {key}: получили {got.get(key)!r}, ждали {value!r}")

if failures:
    print(f"❌ Разбор строки типа ({len(failures)}):")
    for f in failures:
        print(f"  — {f}")
    sys.exit(1)
print(f"✅ Разбор строки типа: {len(CASES)} форм и {len(NEGATIVE)} отрицательных случая")
