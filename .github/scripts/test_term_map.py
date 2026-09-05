#!/usr/bin/env python3
"""Гейт карты терминов, которую собирает `/translate-content` (issue #256).

Зачем. `build_term_map.py` сводит словари и ЛОГИ в одну карту {EN: RU}, и заголовок
записи лога `### EN → RU` переопределяет словарь с абсолютным приоритетом. Значит любая
прозаическая строка со стрелкой в заголовке записи попадает в карту как термин: так
`Dragon` однажды уехал в кусок предложения, а «Различие есть в EN, но в русском
отсутствует» — в ключ. Карта — вход перевода следующей главы, но её не гонял ни один
CI-чек, поэтому класс ловился только руками.

Проверяем три инварианта, каждый — форма уже случившегося дефекта:
  1) EN-ключ пишется латиницей (кириллица в ключе = прозаический заголовок лога);
  2) в значении нет стрелки и оно не начинается с кавычки-ёлочки (обломок заголовка);
  3) конфликтов не больше, чем в списке известных: новый конфликт означает, что один
     термин переведён двумя способами в источниках одного приоритета.

Запуск: python3 .github/scripts/test_term_map.py
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]
BUILDER = ROOT / ".claude/skills/translate-content/build_term_map.py"

# Пары (игра, версия), для которых карта вообще собирается: у игры должны быть свои
# словари. Список закрытый — новая система добавляется сюда осознанно.
TARGETS = [("dnd", "srd-5.2"), ("dnd", "srd-5.1"),
           ("daggerheart", "srd-1.0"), ("brp", "srd-1.0")]

# Конфликты, живущие в словарях осознанно: омонимы с пометкой в комментарии и парный
# термин. Новый конфликт — красный, чтобы расщепление не приезжало молча.
KNOWN_CONFLICTS = {
    ("dnd", "Ammunition"),        # предмет «Боеприпасы» и свойство оружия «Боеприпас»
    ("dnd", "Succubus/Incubus"),  # парная сущность, в словаре двумя строками
}

CYRILLIC = re.compile(r"[А-Яа-яЁё]")
failures = []


def build(game: str, version: str):
    """Карта одной пары (игра, версия) или None, если словарей у игры нет."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "map.json"
        result = subprocess.run(
            [sys.executable, str(BUILDER), game, version, "--out", str(out)],
            cwd=ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            # Отсутствие словарей у системы — не дефект карты, а её отсутствие.
            if "no dictionaries" in (result.stdout + result.stderr).lower():
                return None
            failures.append(
                f"{game} {version}: build_term_map.py упал ({result.returncode}): "
                f"{(result.stderr or result.stdout).strip()[:200]}")
            return None
        return json.loads(out.read_text(encoding="utf-8"))


for game, version in TARGETS:
    data = build(game, version)
    if data is None:
        continue
    for en, ru in sorted(data["terms"].items()):
        if CYRILLIC.search(en):
            failures.append(
                f"{game} {version}: ключ «{en}» написан кириллицей — почти наверняка "
                f"это прозаический заголовок записи лога, а не термин "
                f"(формат заголовка: «### EN → RU»)")
        if "→" in ru or ru.startswith("«"):
            failures.append(
                f"{game} {version}: перевод термина «{en}» = «{ru}» — обломок заголовка "
                f"записи лога; уберите стрелку из прозаического заголовка")
    for conflict in data.get("conflicts", []):
        if (game, conflict["term"]) not in KNOWN_CONFLICTS:
            failures.append(
                f"{game} {version}: новый конфликт «{conflict['term']}» "
                f"({' | '.join(conflict['values'])}) на уровне {conflict['tier']}")

if failures:
    print(f"❌ Карта терминов перевода собрана с дефектами ({len(failures)}):")
    for f in failures[:40]:
        print(f"  — {f}")
    if len(failures) > 40:
        print(f"  … и ещё {len(failures) - 40}")
    sys.exit(1)

print("✅ Карта терминов перевода: ключи латиницей, переводы целые, новых конфликтов нет")
