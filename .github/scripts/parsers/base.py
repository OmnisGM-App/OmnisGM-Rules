"""Base utilities for splitting Markdown into blocks and extracting names/slugs."""

import re
import unicodedata


def slugify(name: str) -> str:
    """Convert an English name to a URL-friendly slug.

    >>> slugify("Magic Missile")
    'magic-missile'
    >>> slugify("Amulet of Proof Against Detection and Location")
    'amulet-of-proof-against-detection-and-location'
    >>> slugify("Ammunition, +1, +2, or +3")
    'ammunition-1-2-or-3'
    """
    s = name.lower()
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"[^\w\s-]", " ", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s


def extract_names(heading: str, lang: str) -> tuple[str, str | None, str]:
    """Extract (name, name_en, slug) from a heading.

    RU headings: "Магическая стрела (Magic Missile)" → name, name_en, slug
    EN headings: "Magic Missile" → name, None, slug
    """
    if lang != "en":
        # RU headings: extract EN name from parentheses (Latin characters). EN-имя может само
        # содержать вложенную скобку — «Камень удачи (Камень везения) (Stone of Good Luck
        # (Luckstone))»: жадный первый захват + один уровень вложенности во внутренней группе.
        m = re.match(r"^(.+)\s*\(([A-Za-z][^()]*(?:\([^()]*\)[^()]*)*)\)\s*$", heading)
        if m:
            name_local = m.group(1).strip()
            name_en = m.group(2).strip()
            # Слаг — как в EN-ветке: без хвостовой «(...)», чтобы EN/RU слаги совпали (hreflang).
            slug_base = re.sub(r"\s*\([^)]*\)\s*$", "", name_en).strip()
            return name_local, name_en, slugify(slug_base)
    # EN headings or RU without parentheses: use full heading as name
    # Strip parenthetical suffixes for slug (e.g., "Young Red Dragon (Chromatic)")
    full_name = heading.strip()
    slug_base = re.sub(r"\s*\([^)]*\)\s*$", "", full_name).strip()
    return full_name, None, slugify(slug_base)


def split_blocks(text: str, heading_level: int, after: str | None = None) -> list[tuple[str, str]]:
    """Split markdown text into blocks by heading level.

    Returns list of (heading_text, body_text) tuples.
    If `after` is specified, only blocks after that section heading are returned.
    """
    prefix = "#" * heading_level + " "

    if after:
        idx = text.find(after)
        if idx == -1:
            return []
        text = text[idx + len(after):]

    # Build set of higher-level prefixes that should end the current block
    # e.g. for heading_level=4 (####), stop at ##, ###
    stop_prefixes = [("#" * lv + " ") for lv in range(1, heading_level)]

    blocks = []
    current_heading = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        if line.startswith(prefix) and not line.startswith(prefix + "#"):
            if current_heading is not None:
                blocks.append((current_heading, "\n".join(current_lines)))
            current_heading = line[len(prefix):].strip()
            current_lines = []
        elif current_heading is not None:
            # Stop current block at higher-level heading
            is_stop = False
            for sp in stop_prefixes:
                if line.startswith(sp) and not line.startswith(sp + "#"):
                    is_stop = True
                    break
            if is_stop:
                blocks.append((current_heading, "\n".join(current_lines)))
                current_heading = None
                current_lines = []
            else:
                current_lines.append(line)

    if current_heading is not None:
        blocks.append((current_heading, "\n".join(current_lines)))

    return blocks


def get_prop(body: str, labels: list[str]) -> str | None:
    """Extract a property value from body text by label.

    Looks for patterns like **Label:** Value or **Label** Value.
    """
    for label in labels:
        pattern = rf"\*\*{re.escape(label)}:?\*\*:?\s*(.+)"
        m = re.search(pattern, body)
        if m:
            return m.group(1).strip()
    return None


def get_list_prop(body: str, labels: list[str]) -> str | None:
    """Extract a property from a markdown list item (- **Label:** Value)."""
    for label in labels:
        pattern = rf"-\s*\*\*{re.escape(label)}:?\*\*:?\s*(.+)"
        m = re.search(pattern, body)
        if m:
            return m.group(1).strip()
    return None
