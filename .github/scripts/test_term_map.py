#!/usr/bin/env python3
"""Гейт карты терминов, которую собирает `/translate-content` (issue #256).

Зачем. `build_term_map.py` сводит словари и ЛОГИ в одну карту {EN: RU}, и заголовок
записи лога (`### EN → RU`, стрелка годится и ASCII-`->`) переопределяет словарь с
абсолютным приоритетом. Значит любая прозаическая строка со стрелкой в заголовке
попадает в карту как термин: так `Dragon` однажды уехал в кусок предложения, а
«Различие есть в EN, но в русском отсутствует» — в ключ. Карта — вход перевода
следующей главы, но её не гонял ни один CI-чек, и класс ловился только руками.

Проверяем не формы дефекта (их можно обойти переформулировкой), а СОСТАВ карты:

  1) списки «что перебивает что» пришпилены. Переопределение словаря логом и перекрытие
     между тирами словарей — законные механики, но каждый случай перечислен здесь
     поимённо; новый — красный, пока его не осознали. Именно этим ловятся и ASCII-стрелка,
     и латинская проза, и подтипы, положенные в общий словарь через отдельный тир;
  2) карта не схлопывается: у каждой пары есть пол по числу терминов и по источникам,
     иначе потеря половины словаря прошла бы молча;
  3) конфликты пришпилены вместе со ЗНАЧЕНИЯМИ: протухшая запись allowlist краснеет
     так же, как новый конфликт;
  4) ключи латиницей, в переводах нет обломков заголовков — самые частые формы мусора,
     их держим ради внятного сообщения.

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

# Версии, для которых собирается карта. Игры не перечисляем: они находятся по наличию
# `src/{game}/translate/`, чтобы новая система не оказалась невидимой для гейта.
VERSIONS = {"dnd": ["srd-5.2", "srd-5.1"], "daggerheart": ["srd-1.0"], "brp": ["srd-1.0"]}

# Пины по играм. Версии одной игры делят словари и логи, поэтому пин общий.
#   overridden — термины, где запись лога намеренно перебивает словарь;
#   cross_tier — перекрытия между тирами словарей (общий → системный и т. п.);
#   conflicts  — осознанные конфликты внутри тира, вместе со значениями;
#   min_terms  — пол по числу терминов (падение вдвое = схлопнувшаяся карта).
PINS = {
    "dnd": {
        "overridden": {"Feature"},
        "cross_tier": {"Hit Points (HP)", "Divination", "Light", "Game Master (GM)"},
        "conflicts": {
            ("Ammunition", ("Боеприпасы", "Боеприпас")),        # предмет и свойство оружия
            ("Succubus/Incubus", ("Инкуб", "Суккуб")),          # парная сущность, две строки
        },
        "min_terms": 1300,
    },
    "daggerheart": {"overridden": set(), "cross_tier": set(), "conflicts": set(),
                    "min_terms": 780},
    "brp": {"overridden": {"Constitution"}, "cross_tier": set(), "conflicts": set(),
            "min_terms": 220},
}

CYRILLIC = re.compile(r"[А-Яа-яЁё]")
ARROW = re.compile(r"→|->")
failures = []


def build(game: str, version: str):
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "map.json"
        result = subprocess.run(
            [sys.executable, str(BUILDER), game, version, "--out", str(out)],
            cwd=ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            failures.append(
                f"{game} {version}: build_term_map.py упал ({result.returncode}): "
                f"{(result.stderr or result.stdout).strip()[:200]}")
            return None
        return json.loads(out.read_text(encoding="utf-8"))


def check_game(game: str, versions: list) -> None:
    pin = PINS.get(game)
    if pin is None:
        failures.append(
            f"{game}: словари есть, а пина в test_term_map.py нет — добавьте игру в PINS")
        return
    seen_terms = set()   # дефекты словарей у версий одной игры общие: не печатаем дважды
    for version in versions:
        data = build(game, version)
        if data is None:
            continue

        if len(data["terms"]) < pin["min_terms"]:
            failures.append(
                f"{game} {version}: в карте {len(data['terms'])} терминов при поле "
                f"{pin['min_terms']} — источник потерян или разобран не целиком")
        for label, count in data["sources"].items():
            if label.endswith("_dicts") and not count:
                failures.append(f"{game} {version}: тир «{label}» дал ноль терминов")

        for term in sorted(set(data["overridden_by_logs"]) - pin["overridden"]):
            if (game, "ov", term) in seen_terms:
                continue
            seen_terms.add((game, "ov", term))
            failures.append(
                f"{game}: запись лога перебивает словарь для «{term}» = "
                f"«{data['terms'][term]}». Если это термин — обновите словарь; если это "
                f"прозаический заголовок, уберите из него стрелку (её видит билдер)")
        for over in data["cross_tier_overrides"]:
            term = over["term"]
            if term in pin["cross_tier"] or (game, "ct", term) in seen_terms:
                continue
            seen_terms.add((game, "ct", term))
            failures.append(
                f"{game}: «{term}» перекрыт из тира {over['from']} тиром {over['to']} "
                f"({' → '.join(over['values'])}) — словарь спорит сам с собой")

        pinned = {t for t, _ in pin["conflicts"]}
        actual = {}
        for conflict in data["conflicts"]:
            actual[conflict["term"]] = tuple(conflict["values"])
            if conflict["term"] in pinned or (game, "cf", conflict["term"]) in seen_terms:
                continue
            seen_terms.add((game, "cf", conflict["term"]))
            failures.append(
                f"{game} {version}: новый конфликт «{conflict['term']}» "
                f"({' | '.join(conflict['values'])}) на уровне {conflict['tier']}")
        for term, values in sorted(pin["conflicts"]):
            if (game, "pin", term) in seen_terms:
                continue
            seen_terms.add((game, "pin", term))
            if term not in actual:
                failures.append(
                    f"{game}: конфликт «{term}» из пина исчез — уберите запись из PINS")
            elif set(actual[term]) != set(values):
                failures.append(
                    f"{game}: конфликт «{term}» теперь ({' | '.join(actual[term])}), "
                    f"а в пине ({' | '.join(values)})")

        # Ключ из лога — это термин: короткая именная группа. Фраза («Dragon and
        # Elemental headers use capital letters») попадает в карту так же легко, как
        # термин, и без этой проверки ловится только по кириллице.
        for en in data["log_terms"]:
            if len(en.split()) > 5 and (game, "phrase", en) not in seen_terms:
                seen_terms.add((game, "phrase", en))
                failures.append(
                    f"{game}: ключ «{en}» пришёл из заголовка записи лога и выглядит "
                    f"фразой, а не термином — уберите из заголовка стрелку")

        for en, ru in sorted(data["terms"].items()):
            if CYRILLIC.search(en) and (game, "cyr", en) not in seen_terms:
                seen_terms.add((game, "cyr", en))
                failures.append(
                    f"{game}: ключ «{en}» написан кириллицей — это прозаический заголовок "
                    f"записи лога или строка словаря с перепутанными колонками, а не термин")
            if (ARROW.search(ru) or ru.startswith("«")) and (game, "junk", en) not in seen_terms:
                seen_terms.add((game, "junk", en))
                failures.append(
                    f"{game}: перевод термина «{en}» = «{ru}» — обломок заголовка "
                    f"записи лога или ячейки словаря")


for game, versions in sorted(VERSIONS.items()):
    if (ROOT / "src" / game / "translate").is_dir():
        check_game(game, versions)

# Новая система не должна оказаться невидимой: её словари появятся раньше, чем кто-то
# вспомнит про этот гейт.
for path in sorted((ROOT / "src").glob("*/translate")):
    game = path.parent.name
    if game not in VERSIONS:
        failures.append(
            f"{game}: есть {path.relative_to(ROOT)}, но игры нет в VERSIONS "
            f"файла test_term_map.py — карта этой системы не проверяется")

if failures:
    print(f"❌ Карта терминов перевода собрана с дефектами ({len(failures)}):")
    for f in failures[:40]:
        print(f"  — {f}")
    if len(failures) > 40:
        print(f"  … и ещё {len(failures) - 40}")
    sys.exit(1)

print("✅ Карта терминов перевода: состав пришпилен, новых переопределений и конфликтов нет")
