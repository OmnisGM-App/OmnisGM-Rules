"""Parser for D&D SRD spell blocks."""

import re

from .base import split_blocks, extract_names, get_prop


# School name mappings (RU → EN canonical, for level/school line parsing)
SCHOOL_NAMES_RU = {
    "ограждение": "Abjuration", "вызов": "Conjuration",
    "прорицание": "Divination", "очарование": "Enchantment",
    "воплощение": "Evocation", "иллюзия": "Illusion",
    "некромантия": "Necromancy", "преобразование": "Transmutation",
}

SCHOOL_NAMES_EN = {
    "abjuration": "Abjuration", "conjuration": "Conjuration",
    "divination": "Divination", "enchantment": "Enchantment",
    "evocation": "Evocation", "illusion": "Illusion",
    "necromancy": "Necromancy", "transmutation": "Transmutation",
}


def _parse_school_level(line: str, lang: str) -> tuple[str, int, list[str]]:
    """Parse the school/level line.

    EN SRD 5.2: "*Level 1 Evocation (Sorcerer, Wizard)*"
    EN SRD 5.1: "*Conjuration Cantrip (Sorcerer, Wizard)*"
    RU SRD 5.2: "*Воплощение 1-го уровня (Чародей, Волшебник)*"
    RU SRD 5.1: "*Заговор Вызова (Чародей, Волшебник)*"

    Returns (school, level, classes).
    """
    text = line.strip().strip("*").strip()

    # Extract classes from parentheses
    classes = []
    m = re.search(r"\(([^)]+)\)", text)
    if m:
        classes = [c.strip() for c in m.group(1).split(",")]
        text = text[:m.start()].strip()

    school = ""
    level = 0

    if lang == "en":
        text_lower = text.lower()
        if "cantrip" in text_lower:
            level = 0
            school_part = text_lower.replace("cantrip", "").strip()
            school = SCHOOL_NAMES_EN.get(school_part, school_part.title())
        else:
            # "Level 1 Evocation" or "Evocation 1st-level" etc.
            m2 = re.match(r"level\s+(\d+)\s+(\w+)", text_lower)
            if m2:
                level = int(m2.group(1))
                school = SCHOOL_NAMES_EN.get(m2.group(2), m2.group(2).title())
            else:
                m2 = re.match(r"(\w+)\s+(\d+)\w*-?level", text_lower)
                if m2:
                    school = SCHOOL_NAMES_EN.get(m2.group(1), m2.group(1).title())
                    level = int(m2.group(2))
    else:
        text_lower = text.lower()
        if "заговор" in text_lower:
            level = 0
            school_part = text_lower.replace("заговор", "").strip()
            school = SCHOOL_NAMES_RU.get(school_part, school_part.title())
        else:
            # "Воплощение 1-го уровня"
            m2 = re.match(r"(.+?)\s+(\d+)-\w+\s+уровня", text_lower)
            if m2:
                school = SCHOOL_NAMES_RU.get(m2.group(1).strip(), m2.group(1).strip().title())
                level = int(m2.group(2))

    return school, level, classes


def _parse_casting_time(value: str, lang: str) -> dict:
    """Parse casting time into structured data."""
    v_lower = value.lower()
    ritual = False
    condition = None

    if lang == "ru":
        ritual = "ритуал" in v_lower
        if v_lower.startswith("реакция"):
            ct_type = "reaction"
            m = re.search(r"реакция,?\s*которую\s+.+", value, re.IGNORECASE)
            if m:
                condition = value[len("Реакция, "):].strip() if ", " in value else value[len("Реакция "):].strip()
        elif "бонусное действие" in v_lower:
            ct_type = "bonus_action"
        elif "действие" in v_lower.replace("бонусное действие", ""):
            ct_type = "action"
        elif "минут" in v_lower:
            ct_type = "minute"
        elif "час" in v_lower:
            ct_type = "hour"
        else:
            ct_type = "special"
    else:
        ritual = "ritual" in v_lower
        if v_lower.startswith("reaction"):
            ct_type = "reaction"
            m = re.search(r"reaction,?\s*which\s+.+", value, re.IGNORECASE)
            if m:
                sep = ", which " if ", which " in value else " which "
                parts = value.split(sep, 1)
                condition = parts[1].strip() if len(parts) > 1 else None
        elif "bonus action" in v_lower:
            ct_type = "bonus_action"
        elif "action" in v_lower:
            ct_type = "action"
        elif "minute" in v_lower:
            ct_type = "minute"
        elif "hour" in v_lower:
            ct_type = "hour"
        else:
            ct_type = "special"

    # Clean ritual marker from value
    clean = value
    for marker in ["или Ритуал", "или ритуал", "or Ritual", "or ritual"]:
        clean = clean.replace(marker, "").strip().rstrip(",").strip()

    return {
        "value": clean,
        "type": ct_type,
        "ritual": ritual,
        "condition": condition,
    }


def _parse_range(value: str, lang: str) -> dict:
    """Parse spell range into structured data."""
    v_lower = value.lower()

    if lang == "ru":
        if v_lower in ("на себя", "себя"):
            rtype = "self"
        elif v_lower in ("касание",):
            rtype = "touch"
        elif v_lower in ("зрение", "в пределах видимости"):
            rtype = "sight"
        elif v_lower in ("без ограничений", "неограниченная"):
            rtype = "unlimited"
        elif "фут" in v_lower or "миль" in v_lower:
            rtype = "distance"
        else:
            rtype = "special"
    else:
        if v_lower == "self":
            rtype = "self"
        elif v_lower == "touch":
            rtype = "touch"
        elif v_lower == "sight":
            rtype = "sight"
        elif v_lower == "unlimited":
            rtype = "unlimited"
        elif "feet" in v_lower or "foot" in v_lower or "mile" in v_lower:
            rtype = "distance"
        else:
            rtype = "special"

    distance_ft = None
    shape = None

    if rtype == "distance":
        m = re.search(r"(\d[\d,]*)", value)
        if m:
            distance_ft = int(m.group(1).replace(",", ""))
        if "mile" in v_lower or "мил" in v_lower:
            m = re.search(r"(\d+)", value)
            if m:
                distance_ft = int(m.group(1)) * 5280

    if rtype == "self":
        shape_patterns = {
            "cone": r"(\d+)[- ](?:foot|фут)",
            "line": r"(\d+)[- ](?:foot|фут)",
            "cube": r"(\d+)[- ](?:foot|фут)",
            "sphere": r"(\d+)[- ](?:foot|фут)",
            "hemisphere": r"(\d+)[- ](?:foot|фут)",
        }
        for shape_type in ("cone", "line", "cube", "sphere", "hemisphere"):
            if shape_type in v_lower or _ru_shape(shape_type) in v_lower:
                m = re.search(r"(\d+)", value)
                if m:
                    shape = {"type": shape_type, "size_ft": int(m.group(1))}
                    break

    return {
        "value": value,
        "type": rtype,
        "distance_ft": distance_ft,
        "shape": shape,
    }


def _ru_shape(shape_type: str) -> str:
    return {"cone": "конус", "line": "линия", "cube": "куб",
            "sphere": "сфер", "hemisphere": "полусфер"}.get(shape_type, "")


# Область эффекта из ОПИСАНИЯ (5.2 пишет форму там: «in a 60-foot Cone»), а не в строке
# Дистанции. Извлекаем из EN (надёжно); RU получает area по слагу (бэкфилл в generate_api),
# т.к. RU-проза выражает форму разнородно.
_AREA_RE = re.compile(
    r"(\d+)-foot(-radius)?\s+(Cone|Cube|Cylinder|Emanation|Line|Sphere)\b")


def parse_area_from_desc(desc_md: str) -> dict | None:
    """→ {shape, size_ft, radius} по первому измеренному упоминанию формы (EN-описание)."""
    if not desc_md:
        return None
    m = _AREA_RE.search(desc_md)
    if not m:
        return None
    return {
        "shape": m.group(3).lower(),
        "size_ft": int(m.group(1)),
        "radius": m.group(2) is not None,
    }


def _parse_components(value: str, lang: str) -> dict:
    """Parse spell components."""
    v_upper = value.upper()

    if lang == "ru":
        verbal = "В" in v_upper.split(",")[0] or value.startswith("В")
        somatic = "С" in [c.strip() for c in value.split(",")][:3] or ", С" in value or value.startswith("С")
        material = "М" in value.split("(")[0] if "(" in value else "М" in value.split(",")[-1] if "," in value else False
    else:
        verbal = "V" in v_upper.split(",")[0]
        somatic = "S" in [c.strip() for c in v_upper.split(",")][:3]
        material = "M" in v_upper

    # More precise: check if V/В, S/С, M/М appear as standalone component letters
    if lang == "ru":
        parts = re.split(r"[,(]", value)
        letters = [p.strip().rstrip(")").strip() for p in parts]
        verbal = "В" in letters
        somatic = "С" in letters
        material = any(l.startswith("М") for l in letters)
    else:
        parts = re.split(r"[,(]", value)
        letters = [p.strip().rstrip(")").strip() for p in parts]
        verbal = "V" in letters
        somatic = "S" in letters
        material = any(l.startswith("M") for l in letters)

    material_desc = None
    material_cost_gp = None
    material_consumed = False

    if material:
        m = re.search(r"\((.+)\)", value)
        if m:
            material_desc = m.group(1).strip()

            # Extract cost
            cost_match = re.search(r"(\d[\d,]*)\+?\s*(?:GP|gp|зм)", material_desc)
            if cost_match:
                material_cost_gp = float(cost_match.group(1).replace(",", ""))
            else:
                cost_match = re.search(r"(\d[\d,]*)\+?\s*(?:мм|CP|cp|SP|sp)", material_desc)
                if cost_match:
                    val = float(cost_match.group(1).replace(",", ""))
                    if "мм" in material_desc or "CP" in material_desc.upper():
                        material_cost_gp = val * 0.01
                    elif "SP" in material_desc.upper() or "см" in material_desc:
                        material_cost_gp = val * 0.1

            consumed_markers = [
                "consume", "потребляемый", "расходует", "поглощает",
                "the spell consumes", "which the spell consumes",
                "которое заклинание поглощает",
            ]
            desc_lower = material_desc.lower()
            material_consumed = any(m in desc_lower for m in consumed_markers)

    return {
        "verbal": verbal,
        "somatic": somatic,
        "material": material,
        "material_desc": material_desc,
        "material_cost_gp": material_cost_gp,
        "material_consumed": material_consumed,
    }


def _parse_duration(value: str, lang: str) -> dict:
    """Parse spell duration."""
    v_lower = value.lower()

    concentration = False
    if lang == "ru":
        concentration = "концентрация" in v_lower
    else:
        concentration = "concentration" in v_lower

    if lang == "ru":
        if v_lower in ("мгновенная",):
            dtype = "instantaneous"
        elif "пока не рассеется" in v_lower or "пока не будет рассеяно" in v_lower:
            dtype = "until_dispelled"
        elif "мгновенная" in v_lower:
            dtype = "instantaneous"
        elif concentration or re.search(r"\d+\s*(минут|час|раунд|день)", v_lower):
            dtype = "timed"
        else:
            dtype = "special"
    else:
        if v_lower == "instantaneous":
            dtype = "instantaneous"
        elif "until dispelled" in v_lower:
            dtype = "until_dispelled"
        elif concentration or re.search(r"\d+\s*(minute|hour|round|day)", v_lower):
            dtype = "timed"
        else:
            dtype = "special"

    return {
        "value": value,
        "type": dtype,
        "concentration": concentration,
    }


def parse_spells(text: str, heading_level: int, lang: str,
                 after: str | None = None, skip_headings: set | None = None) -> list[dict]:
    """Parse all spell blocks from markdown text.

    Returns a list of spell dictionaries.
    """
    blocks = split_blocks(text, heading_level, after)
    spells = []

    for heading, body in blocks:
        if skip_headings and heading in skip_headings:
            continue

        name, name_en, slug = extract_names(heading, lang)

        # Skip non-spell headings: must have a school/level line
        lines = body.strip().split("\n")
        school_line = None
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("*") and stripped.endswith("*") and not stripped.startswith("**"):
                school_line = stripped
                break

        if not school_line:
            continue

        # Verify it looks like a spell school line
        sl = school_line.lower()
        is_spell = False
        for kw in list(SCHOOL_NAMES_EN.keys()) + list(SCHOOL_NAMES_RU.keys()) + ["cantrip", "заговор", "level", "уровня"]:
            if kw in sl:
                is_spell = True
                break
        if not is_spell:
            continue

        school, level, classes = _parse_school_level(school_line, lang)

        # Extract properties
        ct_labels = ["Casting Time", "Время сотворения", "Время накладывания"]
        range_labels = ["Range", "Дистанция"]
        comp_labels = ["Components", "Компоненты"]
        dur_labels = ["Duration", "Длительность"]

        ct_raw = get_prop(body, ct_labels) or ""
        range_raw = get_prop(body, range_labels) or ""
        comp_raw = get_prop(body, comp_labels) or ""
        dur_raw = get_prop(body, dur_labels) or ""

        casting_time = _parse_casting_time(ct_raw, lang)
        spell_range = _parse_range(range_raw, lang)
        components = _parse_components(comp_raw, lang)
        duration = _parse_duration(dur_raw, lang)

        # Extract description: everything after Duration line
        desc_md, higher_md, cantrip_md, has_stat_block = _extract_description(body, lang)

        spell = {
            "slug": slug,
            "name": name,
            "name_en": name_en,
            "level": level,
            "school": school,
            "classes": classes,
            "casting_time": casting_time,
            "range": spell_range,
            "components": components,
            "duration": duration,
            # area из EN-описания; для RU останется None и заполнится по слагу (backfill).
            "area": parse_area_from_desc(desc_md) if lang == "en" else None,
            "description_md": desc_md,
            "higher_levels_md": higher_md,
            "cantrip_upgrade_md": cantrip_md,
            "has_stat_block": has_stat_block,
        }
        spells.append(spell)

    return spells


def _extract_description(body: str, lang: str) -> tuple[str | None, str | None, str | None, bool]:
    """Extract description, higher levels, cantrip upgrade from spell body.

    Returns (description_md, higher_levels_md, cantrip_upgrade_md, has_stat_block).
    """
    # Find the line after Duration
    dur_labels = ["**Duration:**", "**Длительность:**"]
    lines = body.split("\n")
    desc_start = 0

    for i, line in enumerate(lines):
        for label in dur_labels:
            if label in line:
                desc_start = i + 1
                break

    # Skip blank lines after duration
    while desc_start < len(lines) and not lines[desc_start].strip():
        desc_start += 1

    desc_lines = lines[desc_start:]
    full_desc = "\n".join(desc_lines).strip()

    # Split out higher levels / cantrip upgrade sections
    higher_md = None
    cantrip_md = None

    higher_markers = [
        "**_Using a Higher-Level Spell Slot._**",
        "**_Использование ячейки более высокого уровня._**",
        "**_At Higher Levels._**",
        "**_На более высоких уровнях._**",
    ]
    cantrip_markers = [
        "**_Cantrip Upgrade._**",
        "**_Улучшение заговора._**",
        "**_Усиление заговора._**",
    ]

    description_parts = []
    current_section = "desc"

    for line in desc_lines:
        stripped = line.strip()
        found_marker = False

        for marker in higher_markers:
            if marker in stripped:
                current_section = "higher"
                higher_md = stripped[len(marker):].strip()
                found_marker = True
                break

        if not found_marker:
            for marker in cantrip_markers:
                if marker in stripped:
                    current_section = "cantrip"
                    cantrip_md = stripped[len(marker):].strip()
                    found_marker = True
                    break

        if not found_marker:
            if current_section == "desc":
                description_parts.append(line)
            elif current_section == "higher":
                if higher_md and stripped:
                    higher_md += "\n" + stripped
                elif stripped:
                    higher_md = stripped
            elif current_section == "cantrip":
                if cantrip_md and stripped:
                    cantrip_md += "\n" + stripped
                elif stripped:
                    cantrip_md = stripped

    desc_md = "\n".join(description_parts).strip() or None
    has_stat_block = ">" in (desc_md or "")

    return desc_md, higher_md, cantrip_md, has_stat_block
