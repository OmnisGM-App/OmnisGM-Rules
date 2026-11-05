"""Parser for D&D SRD feat entries."""

import re

from .base import split_blocks, extract_names, slugify
from .classes import ABILITY_CODES


# Category detection from ### parent sections
CATEGORY_MAP_EN = {
    "origin feats": "origin",
    "general feats": "general",
    "fighting style feats": "fighting_style",
    "epic boon feats": "epic_boon",
}

CATEGORY_MAP_RU = {
    "черты происхождения": "origin",
    "общие черты": "general",
    "черты боевого стиля": "fighting_style",
    "черты эпического дара": "epic_boon",
}


def _detect_category_from_italic(italic_line: str, lang: str) -> tuple[str | None, str | None]:
    """Parse the italic category/prerequisite line.

    EN: '*Origin Feat*', '*General Feat (Prerequisite: Level 4+)*'
    RU: '*Черта происхождения*', '*Общая черта (Требование: Уровень 4+)*'
    SRD 5.1: '*Prerequisite: Strength 13 or higher*'

    Returns (category, prerequisite).
    """
    text = italic_line.strip().strip("*").strip()

    # Extract prerequisite from parentheses
    prerequisite = None
    m = re.search(r"\((?:Prerequisite|Требование):\s*(.+?)\)", text)
    if m:
        prerequisite = m.group(1).strip()
        text = text[:m.start()].strip()

    # SRD 5.1: entire line is prerequisite
    if not m:
        m2 = re.match(r"(?:Prerequisite|Требование):\s*(.+)", text, re.IGNORECASE)
        if m2:
            prerequisite = m2.group(1).strip()
            return None, prerequisite

    # Detect category from text
    text_lower = text.lower().strip()

    if lang == "en":
        if "origin" in text_lower:
            return "origin", prerequisite
        elif "general" in text_lower:
            return "general", prerequisite
        elif "fighting style" in text_lower:
            return "fighting_style", prerequisite
        elif "epic boon" in text_lower:
            return "epic_boon", prerequisite
    else:
        if "происхождения" in text_lower:
            return "origin", prerequisite
        elif "общая" in text_lower:
            return "general", prerequisite
        elif "боевого стиля" in text_lower:
            return "fighting_style", prerequisite
        elif "эпического дара" in text_lower:
            return "epic_boon", prerequisite

    return None, prerequisite


_ABILITY_WORD = "|".join(w.capitalize() for w in ABILITY_CODES)
_LEVEL_RE = re.compile(r"Level (\d+)\+")
# 5.2 «Strength or Dexterity 13+», 5.1 «Strength 13 or higher».
_ABILITIES_RE = re.compile(rf"((?:{_ABILITY_WORD})(?: or (?:{_ABILITY_WORD}))*) (\d+)(?:\+| or higher)")
_FEATURE_RE = re.compile(r"(.+) Feature")


def feat_prerequisites(text: str, lang: str) -> dict:
    """Codes from the EN parts; a part outside the three forms stays in `text` only (#478).
    RU keeps its own text and gets the codes from EN by slug in generate_api."""
    out = {"text": text, "level": None, "abilities": None, "feature": None}
    if lang != "en":
        return out
    for part in text.split(", "):
        if m := _LEVEL_RE.fullmatch(part):
            out["level"] = int(m.group(1))
        elif m := _ABILITIES_RE.fullmatch(part):
            out["abilities"] = {"values": [ABILITY_CODES[w.lower()] for w in m.group(1).split(" or ")],
                                "min": int(m.group(2))}
        elif m := _FEATURE_RE.fullmatch(part):
            out["feature"] = slugify(m.group(1))
    return out


def _parse_benefits(body: str) -> list[dict]:
    """Parse **Name.** entries from feat body into structured benefits.

    Pattern: **Name.** Description text...
    """
    benefits = []
    # Split on **Name.** pattern (bold with period)
    parts = re.split(r"\*\*(.+?\.)\*\*\s*", body)

    # parts[0] = text before first benefit
    # parts[1] = benefit name (with period), parts[2] = description, etc.
    i = 1
    while i < len(parts) - 1:
        name = parts[i].strip().rstrip(".").strip()
        text_md = parts[i + 1].strip()
        # Skip "Repeatable" / "Повторяемость" as it's handled separately
        if name.lower() in ("repeatable", "повторяемость"):
            i += 2
            continue
        if name:
            benefits.append({"name": name, "text_md": text_md})
        i += 2

    return benefits


def parse_feats(text: str, heading_level: int, lang: str,
                after: str | None = None,
                skip_headings: set | None = None) -> list[dict]:
    """Parse all feat entries from markdown text.

    Handles both SRD 5.2 (with category sections) and SRD 5.1 (simple format).
    """
    # First, build a map of ### section → category for SRD 5.2
    category_map = {**CATEGORY_MAP_EN, **CATEGORY_MAP_RU}
    current_category: str | None = None
    category_by_line: dict[int, str | None] = {}

    # Apply `after` filter
    if after:
        idx = text.find(after)
        if idx == -1:
            return []
        effective_text = text[idx + len(after):]
    else:
        effective_text = text

    # Track ### sections to determine category
    lines = effective_text.split("\n")
    for i, line in enumerate(lines):
        m = re.match(r"^###\s+(.+)", line)
        if m and not line.startswith("####"):
            section_name = m.group(1).strip().lower()
            if section_name in category_map:
                current_category = category_map[section_name]
        category_by_line[i] = current_category

    # Now parse #### blocks
    blocks = split_blocks(effective_text, heading_level, after=None)
    feats = []

    # Find which line each block heading is on, to determine its category
    block_line_map: dict[str, int] = {}
    for i, line in enumerate(lines):
        prefix = "#" * heading_level + " "
        if line.startswith(prefix) and not line.startswith(prefix + "#"):
            heading = line[len(prefix):].strip()
            if heading not in block_line_map:
                block_line_map[heading] = i

    for heading, body in blocks:
        if skip_headings and heading in skip_headings:
            continue

        name, name_en, slug = extract_names(heading, lang)

        # Find the italic category line
        body_lines = body.strip().split("\n")
        italic_line = None
        italic_idx = -1
        for j, line in enumerate(body_lines):
            stripped = line.strip()
            if stripped.startswith("*") and stripped.endswith("*") and not stripped.startswith("**"):
                italic_line = stripped
                italic_idx = j
                break

        if italic_line is None:
            continue

        # Parse category and prerequisite from italic line
        cat_from_italic, prerequisite = _detect_category_from_italic(italic_line, lang)

        # If italic line didn't give a category, use ### section mapping
        category = cat_from_italic
        if category is None:
            line_num = block_line_map.get(heading, 0)
            category = category_by_line.get(line_num)

        # Check for **Repeatable.** / **Повторяемость.**
        repeatable = bool(re.search(
            r"\*\*(?:Repeatable|Повторяемость)\.\*\*",
            body
        ))

        # Parse benefits (structured **Name.** entries)
        # Description is everything after italic line
        desc_lines = body_lines[italic_idx + 1:]
        desc_body = "\n".join(desc_lines).strip()
        benefits = _parse_benefits(desc_body)

        feats.append({
            "slug": slug,
            "name": name,
            "name_en": name_en,
            "category": category,
            "prerequisite": prerequisite,
            "prerequisites": feat_prerequisites(prerequisite, lang) if prerequisite else None,
            "repeatable": repeatable,
            "benefits": benefits,
            "description_md": desc_body,
        })

    return feats
