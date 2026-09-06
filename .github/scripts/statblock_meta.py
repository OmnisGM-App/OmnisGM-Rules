"""Общее для гейтов статблоков: служебные ключи эталона и нормализация шапки.

Живут отдельно, потому что их читают двое: гейт `test_statblock_fields.py` и сборщик
`build_statblock_fields.py`. Копия в каждом из них уже разъезжалась.
"""

import re

# Служебные ключи эталона: это не поля статблока, а пометки о самом эталоне —
# объявленные опечатки PDF (`cr_note`/`cr_repo`/`xp_note`/`pb_note`) и признак врезки.
META_KEYS = ("cr_note", "cr_repo", "xp_note", "pb_note", "abilities_note", "abilities_repo",
              "outside_chapters")

STRIP_TAIL = re.compile(r"\s*\([^()]*\)$")


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
