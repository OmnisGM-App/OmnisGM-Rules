"""Parser for D&D SRD races (5.1: `## Race` sections with `### Subrace` blocks)."""

import re

from .base import split_blocks, extract_names


# Вводный раздел общих расовых правил (не раса) — пропускаем.
_INTRO_HEADINGS = {"Racial Traits", "Расовые особенности"}


def parse_races(text: str, heading_level: int, lang: str,
                after: str | None = None) -> list[dict]:
    """Parse race entries from markdown.

    Каждая раса — секция `## Имя (English)`. Внутри могут быть подрасы `### …`
    (Hill Dwarf, High Elf, …) — собираем их именами в `subraces`. Тело секции
    (особенности + подрасы) идёт в description_md и рендерится на странице расы.
    """
    blocks = split_blocks(text, heading_level or 2, after)
    races = []

    for heading, body in blocks:
        if heading.strip() in _INTRO_HEADINGS:
            continue

        name, name_en, slug = extract_names(heading.strip(), lang)

        # Подрасы — заголовки уровня ### внутри тела расы (####-заголовок «Особенности» — не подраса).
        subraces = []
        for m in re.finditer(r"^###\s+(.+?)\s*$", body, flags=re.MULTILINE):
            s_name, s_name_en, s_slug = extract_names(m.group(1).strip(), lang)
            subraces.append({"slug": s_slug, "name": s_name, "name_en": s_name_en})

        races.append({
            "slug": slug,
            "name": name,
            "name_en": name_en,
            "subraces": subraces,
            "description_md": body.strip(),
        })

    return races
