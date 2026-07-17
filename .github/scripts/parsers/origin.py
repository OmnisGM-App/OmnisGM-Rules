"""Parser for D&D SRD 5.2 character origins — species and backgrounds."""

import re

from .base import extract_names


def parse_origins(text: str, section: str, lang: str) -> list[dict]:
    """Parse origin entries (#### Name) from a given `### {section}` block.

    section — «Background Descriptions» / «Species Descriptions» (и их RU-эквиваленты).
    Границей секции служит следующий `## ` (h2) либо конец файла, поэтому общие
    подразделы «Parts of a …» (#### Ability Scores и т.п.) вне Descriptions не попадают.
    Тело сущности (черты/особенности) → description_md.
    """
    start = text.find(f"### {section}")
    if start < 0:
        return []
    body = text[start + len(f"### {section}"):]
    # Обрезаем по следующему разделу верхнего уровня (## …).
    nxt = re.search(r"\n## ", body)
    if nxt:
        body = body[:nxt.start()]

    origins = []
    for block in re.split(r"(?m)^#### ", body)[1:]:
        heading, _, rest = block.partition("\n")
        name, name_en, slug = extract_names(heading.strip(), lang)
        origins.append({
            "slug": slug,
            "name": name,
            "name_en": name_en,
            "description_md": rest.strip(),
        })
    return origins
