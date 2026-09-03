#!/usr/bin/env python3
"""Конверсионные документы: строка переименования не должна быть тождеством (issue #197).

Конверсионный док перечисляет переименования в виде «Новое (ранее «Старое»)». В EN
различие бывает в слове, которого в русском просто нет: Poisonous → Venomous («ядовитый»
и там, и там), Sea Horse → Seahorse (одно написание), Acolyte → Priest Acolyte
(«Послушник» и там, и там). Тогда строка схлопывается в «Ядовитая змея (ранее «Ядовитая
змея»)» — утверждение о переименовании, которое ничего не сообщает и выглядит опечаткой.

Лечится добавлением оригиналов: «Ядовитая змея *(Venomous Snake, ранее Poisonous Snake)*».
Проверка ловит остаток: строки, где новое и старое названия совпали. Регистр учитываем —
«Латы (ранее «латы»)» тоже нечитаемо.

Запуск: python3 .github/scripts/test_conversion_renames.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RENAME = re.compile(r"^-\s+(.+?)\s+\(ранее\s+«(.+?)»\)\s*$")
failures = []

docs = sorted(ROOT.glob("src/*/converting-*/ru/*.md"))
if not docs:
    print("❌ не найдено ни одного конверсионного RU-документа — проверять нечего")
    sys.exit(1)

for doc in docs:
    for number, line in enumerate(doc.read_text(encoding="utf-8").split("\n"), 1):
        m = RENAME.match(line.strip())
        if m and m.group(1).casefold() == m.group(2).casefold():
            rel = doc.relative_to(ROOT)
            failures.append(f"{rel}:{number} — «{m.group(1)}» переименовано в само себя")

if failures:
    print(f"❌ Схлопнувшиеся строки переименований ({len(failures)}):")
    for f in failures:
        print(f"  — {f}")
    print("  Лечение: дать оригиналы — «Новое *(New EN, ранее Old EN)*».")
    sys.exit(1)

print(f"✅ Конверсионные документы ({len(docs)}): схлопнувшихся переименований нет")
