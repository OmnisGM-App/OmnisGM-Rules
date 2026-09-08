"""Общее для гейтов статблоков: служебные ключи эталона и нормализация шапки.

Живут отдельно, потому что их читают трое: гейты `test_statblock_fields.py` и
`test_statblock_headers.py` и сборщик `build_statblock_fields.py`. Копия в каждом из них
уже разъезжалась.
"""

import re

# Служебные ключи эталона: это не поля статблока, а пометки о самом эталоне. Здесь —
# только ОБЪЯВЛЕНИЯ ОПЕЧАТОК источника; пометки СТРУКТУРЫ блока объявлены ниже, в
# STRUCTURE_KEYS, и требование «назвать пометку в _source.note» на них не распространяется.
NOTE_KEYS = ("cr_note", "cr_repo", "xp_note", "pb_note", "abilities_note", "abilities_repo",
             "saves_note", "saves_repo")
# …и пометки СТРУКТУРЫ блока: они не объявляют опечатку источника, а говорят, какого рода
# сам блок (врезка вне глав, статблок объекта без шапки и характеристик).
STRUCTURE_KEYS = ("outside_chapters", "object_block")
META_KEYS = NOTE_KEYS + STRUCTURE_KEYS

STRIP_TAIL = re.compile(r"\s*\([^()]*\)$")

# Статблоки ОБЪЕКТОВ 5.1: у них нет ни шапки «размер тип, мировоззрение», ни таблицы
# характеристик, поэтому эвристика шапки их не видит, а обязательные поля существа к ним
# не применяются. Список ЗАКРЫТ и живёт здесь, потому что его читают и гейт (сверяет
# пометки эталона в обе стороны), и сборщик (только по нему собирает такие блоки из
# выемки и только их пускает в обратную полноту).
OBJECT_BLOCKS_51 = ("Apparatus of the Crab",)

# Метки полей статблока 5.1: у редакции свой состав (спасброски отдельной строкой,
# иммунитеты разделены на урон и состояния, снаряжения и инициативы нет вовсе). Живут
# здесь, потому что их читают и гейт, и сборщик эталона: разъехавшись, они молча
# перестали бы видеть поле — сборщик его не собрал бы, а гейт сверил эталон сам с собой.
EN_LABELS_51 = {"Armor Class": "ac", "Hit Points": "hp", "Speed": "speed",
                "Saving Throws": "saves", "Skills": "skills", "Senses": "senses",
                "Languages": "languages", "Damage Immunities": "damage_immunities",
                "Condition Immunities": "condition_immunities",
                "Damage Resistances": "damage_resistances",
                "Damage Vulnerabilities": "damage_vulnerabilities"}
# RU обе формы («Damage Resistances» и единственное число источника) пишет одной меткой,
# поэтому EN-меток на одну больше — но у LAB_51 в сборщике, который читает PDF; здесь, в
# словарях НАШЕГО корпуса, мощность одинакова (по 11).
RU_LABELS_51 = {"Класс Доспеха": "ac", "Хиты": "hp", "Скорость": "speed",
                "Спасброски": "saves", "Навыки": "skills", "Чувства": "senses",
                "Языки": "languages", "Иммунитет к урону": "damage_immunities",
                "Иммунитет к состояниям": "condition_immunities",
                "Сопротивление к урону": "damage_resistances",
                "Уязвимость к урону": "damage_vulnerabilities"}


def paren_groups(text: str) -> list:
    """Группы верхнего уровня в скобках, с учётом вложенности."""
    out, depth, start = [], 0, None
    for i, ch in enumerate(text):
        if ch == "(":
            if depth == 0:
                start = i + 1
            depth += 1
        elif ch == ")" and depth:
            depth -= 1
            if depth == 0:
                out.append(text[start:i])
    return out


def en_group_from_ru_heading(heading: str) -> str:
    """Последняя группа скобок с латиницей — имя оригинала КАК НАПИСАНО, с хвостом."""
    latin = [g for g in paren_groups(heading) if re.search(r"[A-Za-z]", g)]
    return latin[-1].strip() if latin else heading.strip()


def en_name_from_ru_heading(heading: str) -> str:
    """Оригинальное имя из RU-заголовка статблока.

    В 5.2 всё просто: «Летучая мышь (Bat)». В 5.1 заголовки разнородны — «Балор (Balor)
    (Демон)», «Андросфинкс (Androsphinx (Sphinx))», «Гном глубинный (свирфнеблин)
    (Gnome, Deep (Svirfneblin))». Берём последнюю группу скобок с латиницей и снимаем
    её собственный таксономический хвост — так ключ сходится с именем EN-заголовка.
    """
    return STRIP_TAIL.sub("", en_group_from_ru_heading(heading)).strip()



# Служебные слова, которые в наших шапках остаются со строчной («Swarm of Tiny Beasts»).
TITLE_LOWER = {"of", "or"}


def titlecase_header(raw: str) -> str:
    """Строка PDF → наш формат: каждое слово с прописной, кроме служебных.

    PDF 5.1 пишет тип и мировоззрение со строчной («Large aberration, lawful evil»),
    импорт приводит их к прописным. Преобразование механическое, поэтому его можно
    проверять, а не принимать на веру.
    """
    out = []
    for token in raw.split(" "):
        if out and token.lower().strip("(),") in TITLE_LOWER:
            out.append(token)
            continue
        m = re.search(r"[A-Za-z]", token)
        out.append(token if not m else token[:m.start()] + token[m.start()].upper()
                   + token[m.start() + 1:])
    return " ".join(out)
