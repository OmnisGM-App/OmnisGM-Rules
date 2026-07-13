"""Parser for glossary-style definition sections (#### Name + body text).

Используется для свойств оружия и свойств мастерства (глава «Снаряжение», секции
«Properties»/«Свойства» и «Mastery Properties»/«Свойства мастерства»): каждое
определение — заголовок #### и абзац(ы) под ним. Питает hovercard-подсказки.
"""

import re

from .base import slugify


def parse_defs(text: str, section: str) -> list[dict]:
    """Собрать определения #### внутри секции ### {section}.

    Возвращает [{slug, name, name_en, description_md}]. name_en=None — RU-выравнивание
    (по позиции с EN) делается на уровне generate_api (порядок определений одинаков —
    построчный паритет).
    """
    lines = text.split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.strip() == f"### {section}":
            start = i + 1
            break
    if start is None:
        return []

    body = []
    for line in lines[start:]:
        # Заголовок уровня 1–3 завершает секцию; #### (уровень 4) остаётся внутри.
        if re.match(r"^#{1,3} \S", line):
            break
        body.append(line)

    section_text = "\n".join(body)
    # parts: [pre, name1, body1, name2, body2, …]
    parts = re.split(r"^#### (.+)$", section_text, flags=re.M)
    defs = []
    for j in range(1, len(parts), 2):
        name = parts[j].strip()
        desc = parts[j + 1].strip() if j + 1 < len(parts) else ""
        defs.append({
            "slug": slugify(name),
            "name": name,
            "name_en": None,
            "description_md": desc,
        })
    return defs
