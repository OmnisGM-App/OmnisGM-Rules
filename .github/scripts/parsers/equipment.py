"""Parser for D&D SRD equipment items (5.2 heading format + 5.1 bold-italic format)."""

import re

from .base import split_blocks, extract_names, get_prop, slugify


def _parse_cost_from_heading(heading: str) -> tuple[str, str | None]:
    """Extract item name and cost from heading like 'Acid (25 GP)'.

    Returns (name, cost).
    """
    m = re.match(r"^(.+?)\s*\(([^)]+)\)\s*$", heading)
    if m:
        name = m.group(1).strip()
        cost = m.group(2).strip()
        return name, cost
    return heading.strip(), None


def _parse_craft(value: str) -> list[str]:
    """Split Craft value into list: 'Acid, Alchemist's Fire, ...' → [...]."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _detect_section(heading: str, body: str, lang: str) -> str:
    """Detect whether an item is a tool or adventuring gear.

    Tools have **Ability:** or **Характеристика:** properties.
    """
    ability_labels = ["Ability", "Характеристика"]
    for label in ability_labels:
        if f"**{label}:**" in body or f"**{label}**" in body:
            return "tools"
    # Also check for Utilize/Craft which are tool-specific
    tool_labels = ["Utilize", "Использование", "Craft", "Создание"]
    for label in tool_labels:
        if f"**{label}:**" in body or f"**{label}**" in body:
            return "tools"
    return "adventuring_gear"


# ---------------------------------------------------------------------------
# SRD 5.1: table cost/weight lookup
# ---------------------------------------------------------------------------

def _normalize_table_name(name: str) -> str:
    """Normalize a table item name for fuzzy matching.

    Strips parenthetical suffixes, leading '~ ', and lowercases.
    """
    name = name.strip()
    if name.startswith("~"):
        name = name.lstrip("~").strip()
    # Remove italic markers
    name = name.replace("*", "")
    # Remove parenthetical suffixes: "Acid (vial)" → "Acid"
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name)
    return name.lower().strip()


def _parse_51_cost_weight_table(text: str, table_marker: str) -> dict[str, dict]:
    """Parse a cost/weight table from SRD 5.1 and return {normalized_name: {cost, weight}}.

    table_marker: e.g. "Table: Adventuring Gear" or "Таблица: Снаряжение для приключений"
    """
    idx = text.find(table_marker)
    if idx == -1:
        return {}

    rest = text[idx:]
    # Find end of table (next ## heading or blank line after table rows end)
    end_match = re.search(r"\n## |\n\\\*|\nTable:|\nТаблица:", rest[1:])
    table_text = rest[:end_match.start() + 1] if end_match else rest

    result = {}
    for line in table_text.split("\n"):
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c is not None]
        while cells and cells[0] == "":
            cells.pop(0)
        while cells and cells[-1] == "":
            cells.pop()
        if len(cells) < 3:
            continue
        # Skip separator and header rows
        if "---" in cells[0]:
            continue
        first_lower = cells[0].lower().strip()
        if first_lower in ("item", "предмет"):
            continue
        # Skip category rows (italic, e.g. *Ammunition*)
        raw_name = cells[0].strip()
        if raw_name.startswith("*") and raw_name.endswith("*") and not raw_name.startswith("**"):
            continue

        cost = cells[1].strip() if len(cells) > 1 else ""
        weight = cells[2].strip() if len(cells) > 2 else ""

        norm = _normalize_table_name(raw_name)
        if norm:
            result[norm] = {
                "cost": cost if cost and cost not in ("-", "—", "") else None,
                "weight": weight if weight and weight not in ("-", "—", "") else None,
            }
    return result


def _lookup_cost_weight(name: str, table_data: dict[str, dict]) -> tuple[str | None, str | None]:
    """Look up cost and weight for a given item name in the table data."""
    # Direct match
    norm = name.lower().strip()
    if norm in table_data:
        d = table_data[norm]
        return d["cost"], d["weight"]

    # Try without trailing period/punctuation
    norm2 = norm.rstrip(".")
    if norm2 in table_data:
        d = table_data[norm2]
        return d["cost"], d["weight"]

    # Try with apostrophe variations
    for key, d in table_data.items():
        if key.replace("\u2019", "'") == norm.replace("\u2019", "'"):
            return d["cost"], d["weight"]

    # Fuzzy: table key starts with the item name (e.g. "tent" matches "tent, two-person")
    for key, d in table_data.items():
        if key.startswith(norm + ",") or key.startswith(norm + " "):
            return d["cost"], d["weight"]

    return None, None


# ---------------------------------------------------------------------------
# SRD 5.1: bold-italic block parsing
# ---------------------------------------------------------------------------

_BOLD_ITALIC_RE = re.compile(r"\*\*_(.+?)_\*\*")

# Section markers for Adventuring Gear
_AG_MARKERS = ["## Adventuring Gear", "## Снаряжение для приключений"]
# Section markers for Tools
_TOOLS_MARKERS = ["## Tools", "## Инструменты"]
# Table markers for cost/weight lookup
_AG_TABLE_MARKERS = [
    "Table: Adventuring Gear", "Таблица: Снаряжение для приключений",
]
_TOOLS_TABLE_MARKERS = [
    "Table: Tools", "Таблица: Инструменты",
]


def _find_section(text: str, markers: list[str]) -> int:
    """Find the start index of a section by its ## heading."""
    for marker in markers:
        idx = text.find(marker)
        if idx != -1:
            return idx
    return -1


def _extract_section_text(text: str, start: int) -> str:
    """Extract text from a ## section start to the next ## heading or EOF."""
    rest = text[start:]
    # Skip the heading line itself
    nl = rest.find("\n")
    if nl == -1:
        return ""
    rest = rest[nl + 1:]
    # Find next ## heading
    end = re.search(r"\n## ", rest)
    return rest[:end.start()] if end else rest


def _parse_bold_italic_blocks(section_text: str, section: str,
                              table_data: dict[str, dict],
                              lang: str) -> list[dict]:
    """Parse **_Name._** blocks from a section of SRD 5.1 text."""
    items = []

    # Split by **_Name._** pattern — each match starts a new item
    parts = _BOLD_ITALIC_RE.split(section_text)
    # parts[0] = text before first match (preamble)
    # parts[1] = first name, parts[2] = body after first name
    # parts[3] = second name, parts[4] = body, etc.

    i = 1  # skip preamble
    while i < len(parts) - 1:
        raw_header = parts[i].strip()
        body = parts[i + 1].strip()
        i += 2

        # Equipment Packs have cost in the name: "Burglar's Pack (16 gp)."
        # Regular items end with period: "Acid."
        # Strip trailing period
        raw_header = raw_header.rstrip(".")

        # Check for cost in parentheses (equipment packs: "Burglar's Pack (16 gp)").
        # Цена ВСЕГДА начинается с цифры («16 gp»/«16 зм») — так отличаем её от английской
        # скобки-имени («Кислота (Acid)»), которую нужно оставить extract_names для name_en/слага.
        cost = None
        m_cost = re.match(r"^(.+?)\s*\((\d[^)]*)\)\s*$", raw_header)
        if m_cost:
            item_name = m_cost.group(1).strip()
            cost = m_cost.group(2).strip()
        else:
            item_name = raw_header

        name, name_en, slug = extract_names(item_name, lang)

        # Lookup cost/weight from table by the LOCAL name (без английской скобки-имени —
        # таблица цен/веса ключуется русским именем «Кислота», а item_name = «Кислота (Acid)»).
        t_cost, t_weight = _lookup_cost_weight(name, table_data)
        if cost is None:
            cost = t_cost
        weight = t_weight

        description_md = body.strip()

        items.append({
            "slug": slug,
            "name": name,
            "name_en": name_en,
            "section": section,
            "cost": cost,
            "weight": weight,
            "ability": None,
            "utilize": None,
            "craft": [],
            "variants": None,
            "description_md": description_md,
        })

    return items


def _parse_51_equipment(text: str, lang: str) -> list[dict]:
    """Parse SRD 5.1 equipment from **_Name._** blocks in Adventuring Gear and Tools sections."""
    items = []

    # Build cost/weight lookup tables
    ag_table = {}
    for marker in _AG_TABLE_MARKERS:
        ag_table = _parse_51_cost_weight_table(text, marker)
        if ag_table:
            break

    tools_table = {}
    for marker in _TOOLS_TABLE_MARKERS:
        tools_table = _parse_51_cost_weight_table(text, marker)
        if tools_table:
            break

    # Parse Adventuring Gear section
    ag_start = _find_section(text, _AG_MARKERS)
    if ag_start != -1:
        ag_text = _extract_section_text(text, ag_start)
        items.extend(_parse_bold_italic_blocks(ag_text, "adventuring_gear", ag_table, lang))

    # Parse Tools section
    tools_start = _find_section(text, _TOOLS_MARKERS)
    if tools_start != -1:
        tools_text = _extract_section_text(text, tools_start)
        items.extend(_parse_bold_italic_blocks(tools_text, "tools", tools_table, lang))

    return items


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def parse_equipment(text: str, heading_level: int, lang: str,
                    after: str | None = None,
                    skip_headings: set | None = None) -> list[dict]:
    """Parse all equipment items from markdown text.

    SRD 5.2: heading_level > 0 → #### headings with cost in parens.
    SRD 5.1: heading_level == 0 → **_Name._** bold-italic blocks.
    """
    if heading_level == 0:
        return _parse_51_equipment(text, lang)

    # SRD 5.2 path (unchanged)
    blocks = split_blocks(text, heading_level, after)
    items = []

    for heading, body in blocks:
        if skip_headings and heading in skip_headings:
            continue

        # Equipment headings have cost in parentheses: "Acid (25 GP)"
        # Headings without cost/parentheses that don't look like items → skip
        raw_name, cost = _parse_cost_from_heading(heading)

        # If no cost in parens, check if it looks like a non-item heading
        # (property descriptions, rules sections, etc.)
        if cost is None:
            continue

        name, name_en, slug = extract_names(raw_name, lang)

        section = _detect_section(heading, body, lang)

        # Extract structured properties
        ability = get_prop(body, ["Ability", "Характеристика"])
        weight = get_prop(body, ["Weight", "Вес"])
        utilize = get_prop(body, ["Utilize", "Использование"])
        craft_raw = get_prop(body, ["Craft", "Создание"])
        craft = _parse_craft(craft_raw) if craft_raw else []
        variants = get_prop(body, ["Variants", "Варианты"])

        description_md = body.strip()

        item = {
            "slug": slug,
            "name": name,
            "name_en": name_en,
            "section": section,
            "cost": cost,
            "weight": weight,
            "ability": ability,
            "utilize": utilize,
            "craft": craft,
            "variants": variants,
            "description_md": description_md,
        }
        items.append(item)

    return items
