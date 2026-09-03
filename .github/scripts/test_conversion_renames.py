#!/usr/bin/env python3
"""Конверсионные документы: строка переименования не должна быть тождеством (issue #197).

Конверсионный док перечисляет переименования как «Новое (ранее «Старое»)». В EN различие
бывает в слове, которого в русском просто нет: Poisonous → Venomous («ядовитый» и там, и
там), Sea Horse → Seahorse (одно написание), Acolyte → Priest Acolyte («Послушник»).
Тогда строка схлопывается в «Ядовитая змея (ранее «Ядовитая змея»)» — утверждение о
переименовании, которое ничего не сообщает и читается как опечатка.

Лечится оригиналами в скобках у каждого имени, русская пара при этом остаётся на месте:
«Ядовитая змея *(Venomous Snake)* (ранее «Ядовитая змея» *(Poisonous Snake)*)».

Проверка ловит остаток: строки, где русские имена совпали и различие ничем не показано —
оригиналов нет вовсе или они тоже совпали. Регистр учитываем: «Латы (ранее «латы»)»
нечитаемо ровно так же.

Запуск: python3 .github/scripts/test_conversion_renames.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# «Новое[ *(Оригинал)*] (ранее «Старое»[ *(Оригинал)*])» — хвост оригинала необязателен.
RENAME = re.compile(r"^-\s+(?P<new>.+?)\s+\(ранее\s+(?P<old>.+)\)\s*$")
ORIGIN = re.compile(r"\*\(([^)]*)\)\*")
failures = []


def split_name(part: str) -> tuple:
    """«Ядовитая змея *(Venomous Snake)*» → («ядовитая змея», «venomous snake»)."""
    origin = ORIGIN.search(part)
    ru = ORIGIN.sub("", part).strip().strip("«»").strip()
    return ru.casefold(), (origin.group(1).strip().casefold() if origin else None)


docs = sorted(ROOT.glob("src/*/converting-*/ru/*.md"))
if not docs:
    print("❌ не найдено ни одного конверсионного RU-документа — проверять нечего")
    sys.exit(1)

checked = 0
for doc in docs:
    for number, line in enumerate(doc.read_text(encoding="utf-8").split("\n"), 1):
        m = RENAME.match(line.strip())
        if not m:
            continue
        checked += 1
        new_ru, new_en = split_name(m.group("new"))
        old_ru, old_en = split_name(m.group("old"))
        if new_ru != old_ru:
            continue
        rel = doc.relative_to(ROOT)
        if new_en is None or old_en is None:
            failures.append(f"{rel}:{number} — «{new_ru}» переименовано в само себя, оригиналов нет")
        elif new_en == old_en:
            failures.append(f"{rel}:{number} — совпали и русские имена, и оригиналы ({new_en})")

if failures:
    print(f"❌ Схлопнувшиеся строки переименований ({len(failures)}):")
    for f in failures:
        print(f"  — {f}")
    print("  Лечение: дать оригиналы — «Новое *(New EN)* (ранее «Старое» *(Old EN)*)».")
    sys.exit(1)

print(f"✅ Конверсионные документы ({len(docs)}): {checked} строк переименований, схлопнувшихся нет")
