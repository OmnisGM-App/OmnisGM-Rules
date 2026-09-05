#!/usr/bin/env python3
"""Гейт карты терминов, которую собирает `/translate-content` (issue #256).

Зачем. `build_term_map.py` сводит словари и ЛОГИ в одну карту {EN: RU}, и заголовок
записи лога (`### EN → RU`, стрелка годится и ASCII-`->`) переопределяет словарь с
абсолютным приоритетом. Значит любая прозаическая строка со стрелкой в заголовке
попадает в карту как термин: так `Dragon` однажды уехал в кусок предложения, а
«Различие есть в EN, но в русском отсутствует» — в ключ. Карта — вход перевода
следующей главы, но её не гонял ни один CI-чек, и класс ловился только руками.

Проверяем не формы дефекта (их можно обойти переформулировкой), а СОСТАВ карты:

  1) «что перебивает что» пришпилено ПАРАМИ «имя → значение»: всё, что пришло из
     заголовков записей логов, перекрытия между тирами словарей и конфликты. Именной пин
     ловил бы только новое имя, а подмена значения у знакомого имени возвращала бы
     исходный дефект зелёной. Исчезнувшая запись — тоже красная. Этим закрываются и
     ASCII-стрелка, и латинская проза, и подтипы, положенные в общий словарь;
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
#
# Пинится ПАРА «имя → значение», а не имя: именной пин ловит только появление новой
# записи, а подмена значения у пришпиленного имени возвращает исходный дефект зелёной
# («### Feature → кусок абзаца» — карта отравлена, имя прежнее). Исчезнувшая запись —
# тоже красная: пин, которым никто не пользуется, это снятая строгость без причины.
#   log_terms  — всё, что пришло в карту ИЗ ЛОГОВ (заголовки записей);
#   cross_tier — перекрытия между тирами словарей, со значениями «было → стало»;
#   conflicts  — осознанные конфликты внутри тира, со значениями;
#   min_terms  — пол по числу терминов (падение вдвое = схлопнувшаяся карта).
PINS = {
    "dnd": {
        "log_terms": {
            "Advantage": "Преимущество", "Blinded": "Ослеплённый",
            "Casting Time": "Время накладывания", "D20 Test": "Проверка d20",
            "Deafened": "Оглохший", "Disadvantage": "Помеха",
            "Feature": "Умение (класса) / Особенность", "Feet": "футов",
            "Force": "Силовое поле", "Gamemaster": "Мастер игры",
            "Gargantuan": "Громадный", "Long Rest": "Долгий отдых",
            "Medium or Small": "Средний или Маленький",
            "Opportunity Attack": "Провоцированная атака", "Perception": "Внимательность",
            "Proficiency Bonus": "Бонус мастерства", "Prone": "Лежащий",
            "Restrained": "Опутанный", "Saving Throw": "Спасбросок", "Skilled": "Умелый",
            "Stunned": "Ошеломлённый", "Swarm of Tiny Beasts": "Рой Крошечных зверей",
            "ability": "характеристика", "ability score": "показатель характеристики",
            "monster": "чудовище", "target number": "целевое значение",
        },
        "cross_tier": {
            # Системный словарь уточняет общий — законно.
            ("Hit Points (HP)", ("Хиты (ХП)", "Хиты")),
            ("Game Master (GM)", ("Мастер игры (МИ)", "Мастер")),
            # А это ОМОНИМЫ, а не уточнения: у D&D «Divination» — и заклинание «Гадание»,
            # и школа «Прорицание»; «Light» — и заклинание «Свет», и свойство оружия
            # «Лёгкое». Карта отдаёт по этим ключам системное значение, то есть перевод
            # заклинания придётся брать не из неё. Сведение — словарная работа (#260).
            ("Divination", ("Гадание", "Прорицание")),
            ("Light", ("Свет", "Лёгкое")),
        },
        "conflicts": {
            ("Ammunition", ("Боеприпасы", "Боеприпас")),        # предмет и свойство оружия
            ("Succubus/Incubus", ("Инкуб", "Суккуб")),          # парная сущность, две строки
        },
        "min_terms": 1300,
    },
    "daggerheart": {
        "log_terms": {
            "D20 Test": "Проверка d20", "Feet": "футов", "Gamemaster": "Мастер",
            "Long Rest": "Долгий Отдых", "Stunned": "Ошеломлённый",
            "Swashbuckler": "Сорвиголова", "ability": "характеристика",
            "ability score": "показатель характеристики", "monster": "чудовище",
            "target number": "целевое значение",
        },
        "cross_tier": set(), "conflicts": set(), "min_terms": 780,
    },
    "brp": {
        "log_terms": {
            "Constitution": "Выносливость", "D20 Test": "Проверка d20", "Feet": "футов",
            "Gamemaster": "Мастер игры", "Hit Points": "Хиты",
            "Non-Player Character": "Неигровой персонаж",
            "Player Character": "Персонаж игрока", "ability": "характеристика",
            "ability score": "показатель характеристики", "monster": "чудовище",
            "target number": "целевое значение",
        },
        "cross_tier": set(), "conflicts": set(), "min_terms": 220,
    },
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
            # Все словарные тиры, а не только `*_dicts`: у общего и системного базовых
            # ярлык кончается на `_dict`, и обнуление общего словаря проходило молча.
            if label.endswith("_dict") or label.endswith("_dicts"):
                if not count:
                    failures.append(f"{game} {version}: тир «{label}» дал ноль терминов")

        # Всё, что пришло из логов, — пара «имя → значение».
        actual_logs = {t: data["terms"][t] for t in data["log_terms"]}
        for term, value in sorted(actual_logs.items()):
            if (game, "ov", term) in seen_terms:
                continue
            seen_terms.add((game, "ov", term))
            pinned_value = pin["log_terms"].get(term)
            if pinned_value is None:
                failures.append(
                    f"{game}: из заголовка записи лога в карту приехал «{term}» = "
                    f"«{value}». Если это термин — впишите пару в PINS; если это "
                    f"прозаический заголовок, уберите из него стрелку (её видит билдер)")
            elif pinned_value != value:
                failures.append(
                    f"{game}: лог даёт «{term}» = «{value}», а в пине «{pinned_value}» — "
                    f"либо решение изменилось (обновите пин), либо заголовок записи "
                    f"поехал")
        for term in sorted(set(pin["log_terms"]) - set(actual_logs)):
            if (game, "ovpin", term) in seen_terms:
                continue
            seen_terms.add((game, "ovpin", term))
            failures.append(
                f"{game}: пара «{term}» из пина больше не приходит из логов — запись "
                f"удалена или переформулирована; уберите её из PINS осознанно")

        actual_cross = {o["term"]: tuple(o["values"]) for o in data["cross_tier_overrides"]}
        pinned_cross = dict(pin["cross_tier"])
        for term, values in sorted(actual_cross.items()):
            if (game, "ct", term) in seen_terms:
                continue
            seen_terms.add((game, "ct", term))
            if term not in pinned_cross:
                failures.append(
                    f"{game}: «{term}» перекрыт тиром {[o for o in data['cross_tier_overrides'] if o['term'] == term][0]['to']} "
                    f"({' → '.join(values)}) — словарь спорит сам с собой")
            elif pinned_cross[term] != values:
                failures.append(
                    f"{game}: перекрытие «{term}» теперь ({' → '.join(values)}), "
                    f"а в пине ({' → '.join(pinned_cross[term])})")
        for term in sorted(set(pinned_cross) - set(actual_cross)):
            if (game, "ctpin", term) in seen_terms:
                continue
            seen_terms.add((game, "ctpin", term))
            failures.append(
                f"{game}: перекрытие «{term}» из пина исчезло — уберите запись из PINS")

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
    else:
        # Обратное направление к проверке ниже: исчезнувший каталог словарей молча
        # выводил игру из-под гейта.
        failures.append(
            f"{game}: игра есть в VERSIONS, но каталога src/{game}/translate нет — "
            f"карта этой системы не собирается")

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
