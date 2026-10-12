"""Parser for D&D SRD magic item blocks."""

import re

from .base import split_blocks, extract_names


# Rarity mappings
RARITIES_EN = {
    "common": "common", "uncommon": "uncommon", "rare": "rare",
    "very rare": "very rare", "legendary": "legendary", "artifact": "artifact",
}
RARITIES_RU = {
    "обычный": "common", "необычный": "uncommon", "редкий": "rare",
    "очень редкий": "very rare", "легендарный": "legendary", "артефакт": "artifact",
    "обычная": "common", "необычная": "uncommon", "редкая": "rare",
    "очень редкая": "very rare", "легендарная": "legendary",
    "обычное": "common", "необычное": "uncommon", "редкое": "rare",
    "очень редкое": "very rare", "легендарное": "legendary",
}


def _parse_type_rarity_line(line: str, lang: str) -> dict:
    """Parse the type/rarity line of a magic item.

    EN: '*Armor (Any Medium or Heavy, Except Hide Armor), Uncommon*'
    EN: '*Wondrous Item, Rare (Requires Attunement)*'
    RU: '*Доспех (среднего или тяжёлого типа, но не кольчуга-хауберк), необычный*'
    RU: '*Чудесный предмет, редкий (требуется настройка)*'
    """
    text = line.strip().strip("*").strip()

    # Extract attunement info
    attunement_required = False
    attunement_condition = None

    att_match = re.search(r"\((?:Requires Attunement|требуется настройка)(?:\s+(.+?))?\)", text, re.IGNORECASE)
    if att_match:
        attunement_required = True
        attunement_condition = att_match.group(1)
        # Remove attunement parenthetical from text
        text = text[:att_match.start()].strip().rstrip(",").strip()

    # Редкостей в строке бывает несколько («Uncommon (+1), Rare (+2), or Very Rare (+3)») или ни одной
    # (редкость варьируется): тип — всё до первой из них.
    item_type = ""
    subtype = None
    rarity_map = RARITIES_RU if lang == "ru" else RARITIES_EN
    keys = "|".join(re.escape(k) for k in sorted(rarity_map, key=len, reverse=True))
    found = list(re.finditer(rf"(?<!\w)(?:{keys})(?!\w)", text, re.IGNORECASE))
    # Формы источника: 5.2 «Rarity Varies», 5.1 ещё «Varies» и «Rarity by Figurine».
    varies = re.search(
        r"(?<!\w)(?:(?:rarity\s+)?varies|rarity by figurine|(?:редкость\s+)?варьируется|редкость зависит от фигурки)(?!\w)",
        text, re.IGNORECASE)
    rarities = list(dict.fromkeys(rarity_map[m.group(0).lower()] for m in found))
    cut = min([m.start() for m in found] + ([varies.start()] if varies else []), default=len(text))
    type_part = text[:cut].strip().rstrip(",").strip()

    # Parse type and subtype
    # Pattern: "Armor (Medium or Heavy)" or "Weapon (Any Sword)"
    m = re.match(r"(.+?)\s*\((.+?)\)\s*$", type_part)
    if m:
        item_type = m.group(1).strip()
        subtype = m.group(2).strip()
    else:
        item_type = type_part.strip()

    return {
        "type": item_type,
        "subtype": subtype,
        "rarity": rarities[0] if len(rarities) == 1 else None,
        "rarities": rarities,
        "attunement": {
            "required": attunement_required,
            "condition": attunement_condition,
        },
    }


def _extract_spell_refs(description: str) -> list[str]:
    """Extract spell names referenced in italic from description."""
    found = re.findall(r"(?<!\*)\*([^*]+?)\*(?!\*)", description)
    spells = []
    for s in found:
        cleaned = s.strip().rstrip(".")
        if cleaned and len(cleaned.split()) <= 6:
            spells.append(cleaned)
    return spells


def parse_magic_items(text: str, heading_level: int, lang: str,
                      after: str | None = None, skip_headings: set | None = None) -> list[dict]:
    """Parse all magic item blocks from markdown text."""
    blocks = split_blocks(text, heading_level, after)
    items = []

    for heading, body in blocks:
        if skip_headings and heading in skip_headings:
            continue

        name, name_en, slug = extract_names(heading, lang)

        # Must have a type/rarity line (italic)
        # May be: "*Type, Rarity*" or "*Type, Rarity* description on same line"
        lines = body.strip().split("\n")
        type_line = None
        type_line_idx = -1
        extra_desc = ""
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("*") and not stripped.startswith("**"):
                # Find the closing * for the italic type portion
                close_idx = stripped.find("*", 1)
                if close_idx > 0:
                    type_line = stripped[:close_idx + 1]
                    extra_desc = stripped[close_idx + 1:].strip()
                    type_line_idx = i
                    break

        if not type_line:
            continue

        # Verify it looks like a magic item type line
        type_lower = type_line.lower()
        is_item = False
        item_keywords = [
            "armor", "weapon", "potion", "ring", "rod", "scroll", "staff",
            "wand", "wondrous", "доспех", "оружие", "зелье", "кольцо",
            "жезл", "свиток", "посох", "палочка", "чудесный",
        ]
        for kw in item_keywords:
            if kw in type_lower:
                is_item = True
                break

        # Also accept if a known rarity is present
        rarity_keywords = list(RARITIES_EN.keys()) + list(RARITIES_RU.keys())
        for kw in rarity_keywords:
            if kw in type_lower:
                is_item = True
                break

        if not is_item:
            continue

        type_info = _parse_type_rarity_line(type_line, lang)

        # Description is everything after the type line
        # If type line had extra text after closing *, prepend it
        desc_lines = lines[type_line_idx + 1:]
        description_md = "\n".join(desc_lines).strip()
        if extra_desc:
            description_md = extra_desc + ("\n" + description_md if description_md else "")

        spell_refs = _extract_spell_refs(description_md)

        item = {
            "slug": slug,
            "name": name,
            "name_en": name_en,
            "type": type_info["type"],
            "subtype": type_info["subtype"],
            "rarity": type_info["rarity"],
            "rarities": type_info["rarities"],
            "attunement": type_info["attunement"],
            "description_md": description_md,
            "spells": spell_refs,
        }
        items.append(item)

    return items
