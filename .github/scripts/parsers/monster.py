"""Parser for D&D SRD monster and animal stat blocks."""

import re

from .base import split_blocks, extract_names, get_list_prop


# Size mappings
SIZES_EN = {"tiny", "small", "medium", "large", "huge", "gargantuan"}
SIZES_RU_TO_EN = {
    "крошечный": "Tiny", "маленький": "Small", "средний": "Medium",
    "крошечная": "Tiny", "маленькая": "Small", "средняя": "Medium",
    "крошечное": "Tiny", "маленькое": "Small", "среднее": "Medium",
    "большой": "Large", "большая": "Large", "большое": "Large",
    "огромный": "Huge", "огромная": "Huge", "огромное": "Huge",
    "громадный": "Gargantuan", "громадная": "Gargantuan", "громадное": "Gargantuan",
}


def _split_size(words: list, lang: str) -> tuple:
    """Split '['Medium', 'or', 'Small', 'Humanoid']' into ('Medium or Small', 'Humanoid').

    SRD 5.2 writes a choice of size for shape-shifters and playable-species NPCs
    ('Medium or Small Humanoid', RU 'Средний или Маленький гуманоид'). Taking only
    the first word would leave a dangling 'or Small' inside the creature type.
    """
    sizes = SIZES_EN if lang == "en" else SIZES_RU_TO_EN
    conj = "or" if lang == "en" else "или"
    if (
        len(words) > 3
        and words[0].lower() in sizes
        and words[1].lower() == conj
        and words[2].lower() in sizes
    ):
        return " ".join(words[:3]), " ".join(words[3:])
    return (words[0] if words else ""), " ".join(words[1:])


def _parse_type_line(line: str, lang: str) -> dict:
    """Parse the type/alignment line: '*Large Aberration, Lawful Evil*'."""
    text = line.strip().strip("*").strip()
    # Split on the alignment comma ONLY — a comma INSIDE the subtype parentheses
    # (5.1: '*Tiny Fiend (Devil, Shapechanger), Lawful Evil*') must not be treated
    # as the separator, else the type keeps a dangling '(Devil'. Negative lookahead
    # skips any comma still enclosed by an unclosed '(' . 5.2 lines have no comma
    # inside the type-parens, so this is a no-op there.
    parts = re.split(r",\s*(?![^(]*\))", text, maxsplit=1)
    first = parts[0].strip()
    alignment = parts[1].strip() if len(parts) > 1 else None

    words = first.split()
    size = ""
    creature_type = ""
    subtype = None

    if lang == "en":
        size, rest = _split_size(words, "en")

        # Check for subtype in parentheses
        m = re.match(r"(.+?)\s*\((.+)\)", rest)
        if m:
            creature_type = m.group(1).strip()
            subtype = m.group(2).strip()
        else:
            creature_type = rest
    else:
        if words:
            size, rest = _split_size(words, "ru")

            m = re.match(r"(.+?)\s*\((.+)\)", rest)
            if m:
                creature_type = m.group(1).strip()
                subtype = m.group(2).strip()
            else:
                creature_type = rest

    return {
        "size": size,
        "type": creature_type,
        "subtype": subtype,
        "alignment": alignment,
    }


def _parse_ac(value: str) -> dict:
    """Parse AC: '17 (natural armor)' or '17'."""
    m = re.match(r"(\d+)\s*(?:\((.+?)\))?", value)
    if m:
        return {"value": int(m.group(1)), "source": m.group(2)}
    return {"value": 0, "source": None}


def _parse_hp(value: str) -> dict:
    """Parse HP: '135 (18d10 + 36)' or '150 (20d10 + 40)'."""
    m = re.match(r"(\d+)\s*\((.+?)\)", value)
    if m:
        return {"average": int(m.group(1)), "formula": m.group(2).strip()}
    m2 = re.match(r"(\d+)", value)
    if m2:
        return {"average": int(m2.group(1)), "formula": ""}
    return {"average": 0, "formula": ""}


def _parse_speed(value: str, lang: str) -> dict:
    """Parse speed into structured data."""
    result = {
        "walk": None, "swim": None, "fly": None,
        "burrow": None, "climb": None, "hover": False,
        "raw": value,
    }

    v_lower = value.lower()
    result["hover"] = "hover" in v_lower or "парение" in v_lower or "парит" in v_lower

    # Extract walk speed (first number)
    m = re.match(r"(\d+)", value)
    if m:
        result["walk"] = int(m.group(1))

    speed_types = {
        "swim": ["swim", "плавание", "плав."],
        "fly": ["fly", "полёт", "лет."],
        "burrow": ["burrow", "рытьё", "копание"],
        "climb": ["climb", "лазание", "лаз."],
    }

    for key, keywords in speed_types.items():
        for kw in keywords:
            pattern = rf"{re.escape(kw)}\s+(\d+)"
            m = re.search(pattern, v_lower)
            if m:
                result[key] = int(m.group(1))
                break

    return result


def _parse_initiative(value: str) -> dict | None:
    """Parse initiative: '+3 (13)' → {mod: 3, score: 13}."""
    m = re.match(r"([+-]?\d+)\s*\((\d+)\)", value)
    if m:
        return {"mod": int(m.group(1)), "score": int(m.group(2))}
    return None


def _parse_abilities_table_52(body: str, lang: str) -> dict:
    """Parse SRD 5.2 3-row ability table."""
    abilities = {}
    ability_keys = ["str", "dex", "con", "int", "wis", "cha"]

    # Find the table rows
    table_rows = []
    for line in body.split("\n"):
        if "|" in line and "---" not in line:
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if len(cells) >= 7:
                table_rows.append(cells)

    if len(table_rows) >= 3:
        # Data rows: SCORE/ЗНАЧ, MOD/МОД, SAVE/СПАС (header row may have fewer cells)
        # Identify data rows: those with 7 cells (label + 6 values)
        data_rows = [r for r in table_rows if len(r) >= 7]
        if len(data_rows) >= 3:
            score_row = data_rows[0]
            mod_row = data_rows[1]
            save_row = data_rows[2]

            for i, key in enumerate(ability_keys):
                idx = i + 1  # skip first cell (label)
                if idx < len(score_row):
                    score = _parse_int(score_row[idx])
                    mod = _parse_signed_int(mod_row[idx]) if idx < len(mod_row) else 0
                    save = _parse_signed_int(save_row[idx]) if idx < len(save_row) else mod
                    abilities[key] = {"score": score, "mod": mod, "save": save}

    return abilities


def _parse_abilities_table_51(body: str, lang: str) -> dict:
    """Parse SRD 5.1 single-row ability table: '21 (+5) | 9 (-1) | ...'."""
    abilities = {}
    ability_keys = ["str", "dex", "con", "int", "wis", "cha"]

    table_rows = []
    for line in body.split("\n"):
        if "|" in line and "---" not in line:
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if len(cells) >= 6:
                table_rows.append(cells)

    if len(table_rows) >= 2:
        # Row 0: header (STR/DEX/...), Row 1: values like "21 (+5)"
        value_row = table_rows[1]
        for i, key in enumerate(ability_keys):
            if i < len(value_row):
                m = re.match(r"(\d+)\s*\(([+-]\d+)\)", value_row[i].strip())
                if m:
                    score = int(m.group(1))
                    mod = int(m.group(2))
                    abilities[key] = {"score": score, "mod": mod, "save": mod}

    return abilities


def _parse_int(s: str) -> int:
    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else 0


def _parse_signed_int(s: str) -> int:
    m = re.search(r"([+-]?\d+)", s)
    return int(m.group(1)) if m else 0


def _parse_cr(value: str, lang: str) -> dict:
    """Parse CR line.

    SRD 5.1 EN: "10 (5,900 XP)"
    SRD 5.1 RU: "10 (5 900 ОО)"
    SRD 5.2 EN: "10 (XP 5,900; PB +2)"
    SRD 5.2 RU: "10 (ОО 5900; БМ +2)"  or "10 (ОО 5900 или 7200 в логове)"
    """
    cr_value = ""
    xp = 0
    pb = None

    # Extract CR value (may be fraction like 1/2)
    m = re.match(r"([\d/]+)", value.strip())
    if m:
        cr_value = m.group(1)

    # Extract XP
    xp_match = re.search(r"(?:XP|ОО)\s*([\d\s,]+)", value)
    if xp_match:
        xp = int(re.sub(r"[\s,]", "", xp_match.group(1)))
    else:
        # SRD 5.1: "10 (5,900 XP)" or "10 (5 900 ОО)"
        m2 = re.search(r"\(([\d\s,]+)\s*(?:XP|ОО)", value)
        if m2:
            xp = int(re.sub(r"[\s,]", "", m2.group(1)))

    # Extract PB
    pb_match = re.search(r"(?:PB|БМ)\s*\+?(\d+)", value)
    if pb_match:
        pb = int(pb_match.group(1))

    return {"value": cr_value, "xp": xp, "proficiency_bonus": pb}


def _parse_senses(value: str, lang: str) -> dict:
    """Parse senses string."""
    result = {
        "darkvision_ft": None, "blindsight_ft": None,
        "tremorsense_ft": None, "truesight_ft": None,
        "passive_perception": None, "raw": value,
    }

    sense_map = {
        "darkvision_ft": ["darkvision", "тёмное зрение"],
        "blindsight_ft": ["blindsight", "слепое зрение"],
        "tremorsense_ft": ["tremorsense", "чувство вибрации"],
        "truesight_ft": ["truesight", "истинное зрение"],
    }

    v_lower = value.lower()
    for key, keywords in sense_map.items():
        for kw in keywords:
            m = re.search(rf"{re.escape(kw)}\s+(\d+)", v_lower)
            if m:
                result[key] = int(m.group(1))
                break

    pp_match = re.search(r"(?:Passive Perception|[Пп]ассивн\w+\s+(?:Восприяти|Внимательност)\w*)\s+(\d+)", value)
    if pp_match:
        result["passive_perception"] = int(pp_match.group(1))

    return result


def _extract_sections(body: str, lang: str) -> dict:
    """Extract #### sections (Traits, Actions, Legendary Actions, etc.) from body."""
    sections = {}
    current_section = "_preamble"
    current_lines: list[str] = []

    section_map_en = {
        "Traits": "traits", "Actions": "actions",
        "Legendary Actions": "legendary_actions",
        "Reactions": "reactions", "Bonus Actions": "bonus_actions",
        "Lair Actions": "lair_actions",
    }
    section_map_ru = {
        "Особенности": "traits", "Свойства": "traits",
        "Действия": "actions", "Легендарные действия": "legendary_actions",
        "Реакции": "reactions", "Бонусные действия": "bonus_actions",
        "Действия логова": "lair_actions",
    }
    section_map = {**section_map_en, **section_map_ru}

    for line in body.split("\n"):
        m = re.match(r"^####\s+(.+)", line)
        if m:
            if current_lines:
                sections[current_section] = "\n".join(current_lines)
            heading = m.group(1).strip()
            current_section = section_map.get(heading, heading.lower())
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_section] = "\n".join(current_lines)

    return sections


def _parse_section_entries(text: str) -> list[dict]:
    """Parse **_Name._** Description entries from a section."""
    entries = []
    # Pattern: **_Name._** or **_Name (details)._**
    parts = re.split(r"\*\*_(.+?)_\*\*\s*", text)

    # parts[0] is text before first entry (often section description)
    # parts[1] = name, parts[2] = description, parts[3] = name, etc.
    i = 1
    while i < len(parts) - 1:
        name = parts[i].strip().rstrip(".").strip()
        desc = parts[i + 1].strip()
        if name:
            entries.append({"name": name, "text_md": desc})
        i += 2

    # If no **_..._** entries found, maybe entire text is a single description
    if not entries and text.strip():
        preamble = parts[0].strip() if parts else text.strip()
        if preamble:
            entries.append({"name": "", "text_md": preamble})

    return entries


def _extract_spells_from_traits(traits: list[dict], lang: str) -> list[str]:
    """Extract spell names referenced in italic from spellcasting traits."""
    spells = []
    spellcasting_keywords = ["spellcasting", "сотворение заклинаний", "innate spellcasting",
                              "врождённое сотворение", "колдовство"]

    for trait in traits:
        if any(kw in trait["name"].lower() for kw in spellcasting_keywords):
            # Find all italic references: *spell name*
            found = re.findall(r"(?<!\*)\*([^*]+?)\*(?!\*)", trait["text_md"])
            for s in found:
                cleaned = s.strip().rstrip(".")
                if cleaned and not cleaned[0].isupper() or len(cleaned.split()) <= 5:
                    spells.append(cleaned)
            break

    # Also scan all traits/actions for italic spell references
    return spells


def _detect_is_52(body: str, lang: str) -> bool:
    """Detect if this is SRD 5.2 format (3-row ability table)."""
    if lang == "ru":
        return "ЗНАЧ" in body or "СПАС" in body
    return "SCORE" in body or "SAVE" in body


def _parse_saving_throws(value: str) -> list[str]:
    """Parse saving throws string into list."""
    if not value:
        return []
    return [s.strip() for s in value.split(",") if s.strip()]


def _parse_skills(value: str) -> list[str]:
    """Parse skills string into list."""
    if not value:
        return []
    return [s.strip() for s in value.split(",") if s.strip()]


def _parse_damage_field(value: str) -> list[str]:
    """Parse damage resistances/immunities/condition immunities."""
    if not value:
        return []
    return [s.strip() for s in value.split(",") if s.strip()]


# Закрытый список из 15 состояний SRD (всё, что не состояние в строке иммунитетов — урон).
# Классификатор нужен для combined-формата 5.2: «Immunities: Fire, Poison; Charmed, …» —
# `;` разделяет урон и состояния, но при одном виде разделителя нет («Acid» либо «Charmed»).
_CONDITIONS_EN = {
    "blinded", "charmed", "deafened", "exhaustion", "frightened", "grappled",
    "incapacitated", "invisible", "paralyzed", "petrified", "poisoned", "prone",
    "restrained", "stunned", "unconscious",
}
# RU включает варианты терминов, встречающиеся в бестиарии (Оглохший/Оглушённый,
# Опутан/Опутанный, Без сознания/Бессознательный).
_CONDITIONS_RU = {
    "ослеплённый", "ослепленный", "очарованный", "оглохший", "оглушённый", "оглушенный",
    "истощение", "испуганный", "схваченный", "недееспособный", "невидимый",
    "парализованный", "окаменевший", "отравленный", "лежащий", "опутанный", "опутан",
    "ошеломлённый", "ошеломленный", "бессознательный", "без сознания", "обездвиженный",
}


def _is_condition(token: str, lang: str) -> bool:
    """Является ли токен именем состояния (по первому слову, до скобки-уточнения)."""
    base = re.split(r"[(*]", token.strip().lower(), 1)[0].strip()
    conds = _CONDITIONS_RU if lang == "ru" else _CONDITIONS_EN
    if base in conds:
        return True
    # RU-состояния из двух слов («без сознания»)
    return any(base == c or base.startswith(c + " ") for c in conds)


def _split_immunities(value: str, lang: str) -> tuple[list[str], list[str]]:
    """Combined-строка иммунитетов 5.2 → (урон, состояния). Токены по `;` и `,`,
    классификация каждого по закрытому списку состояний."""
    dmg: list[str] = []
    cond: list[str] = []
    for token in re.split(r"[;,]", value):
        t = token.strip()
        if not t:
            continue
        (cond if _is_condition(t, lang) else dmg).append(t)
    return dmg, cond


def parse_monsters(text: str, heading_level: int, lang: str,
                   after: str | None = None, skip_headings: set | None = None) -> list[dict]:
    """Parse all monster/animal blocks from markdown text."""
    blocks = split_blocks(text, heading_level, after)
    monsters = []

    for heading, body in blocks:
        if skip_headings and heading in skip_headings:
            continue

        name, name_en, slug = extract_names(heading, lang)

        # Must have a type line (italic or plain) and stat list
        lines = body.strip().split("\n")
        type_line = None
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("*") and stripped.endswith("*") and not stripped.startswith("**"):
                type_line = stripped
                break

        # Some SRD 5.1 entries have unformatted type lines (no italic markers)
        if not type_line:
            for line in lines:
                stripped = line.strip()
                if not stripped or stripped.startswith("-") or stripped.startswith("|") or stripped.startswith("#") or stripped.startswith("*"):
                    continue
                # Check if it looks like "Size Type, Alignment"
                words = stripped.split()
                if words and (words[0].lower() in SIZES_EN or words[0].lower() in SIZES_RU_TO_EN):
                    type_line = f"*{stripped}*"
                    break

        if not type_line:
            continue

        # Verify it looks like a creature type line (size + type)
        type_info = _parse_type_line(type_line, lang)

        is_52 = _detect_is_52(body, lang)

        # Parse basic stats
        ac_raw = get_list_prop(body, ["Armor Class", "Класс доспеха", "Класс Доспеха"]) or ""
        hp_raw = get_list_prop(body, ["Hit Points", "Хиты"]) or ""
        speed_raw = get_list_prop(body, ["Speed", "Скорость"]) or ""
        init_raw = get_list_prop(body, ["Initiative", "Инициатива"])

        ac = _parse_ac(ac_raw)
        hp = _parse_hp(hp_raw)
        speed = _parse_speed(speed_raw, lang)
        initiative = _parse_initiative(init_raw) if init_raw else None

        # Parse abilities
        if is_52:
            abilities = _parse_abilities_table_52(body, lang)
        else:
            abilities = _parse_abilities_table_51(body, lang)

        # Parse additional properties
        saves_raw = get_list_prop(body, ["Saving Throws", "Спасброски"]) or ""
        skills_raw = get_list_prop(body, ["Skills", "Навыки"]) or ""
        dmg_resist_raw = get_list_prop(body, ["Damage Resistances", "Resistances", "Сопротивления к урону", "Сопротивления"]) or ""
        dmg_vuln_raw = get_list_prop(body, ["Damage Vulnerabilities", "Vulnerabilities", "Уязвимости к урону", "Уязвимости"]) or ""
        # Иммунитеты: 5.1 — раздельные строки Damage/Condition; 5.2 — одна строка «Immunities»
        # (урон; состояния), которую разбираем классификатором.
        sep_dmg = get_list_prop(body, ["Damage Immunities", "Иммунитеты к урону"])
        sep_cond = get_list_prop(body, ["Condition Immunities", "Иммунитеты к состояниям"])
        if sep_dmg is not None or sep_cond is not None:
            dmg_immune_list = _parse_damage_field(sep_dmg or "")
            cond_immune_list = _parse_damage_field(sep_cond or "")
        else:
            combined = get_list_prop(body, ["Immunities", "Иммунитеты"]) or ""
            dmg_immune_list, cond_immune_list = _split_immunities(combined, lang)
        senses_raw = get_list_prop(body, ["Senses", "Чувства"]) or ""
        languages_raw = get_list_prop(body, ["Languages", "Языки"]) or ""

        # CR/ПО: not a standard list prop, it might be "- **CR** 10 (XP ...)" without colon
        cr_raw = get_list_prop(body, ["CR", "ПО", "Challenge", "Показатель опасности"]) or ""
        cr = _parse_cr(cr_raw, lang)

        senses = _parse_senses(senses_raw, lang)

        # Parse sections
        sections = _extract_sections(body, lang)

        traits_md = _parse_section_entries(sections.get("traits", ""))
        actions_md = _parse_section_entries(sections.get("actions", ""))
        legendary_md = _parse_section_entries(sections.get("legendary_actions", ""))
        reactions_md = _parse_section_entries(sections.get("reactions", ""))
        bonus_actions_md = _parse_section_entries(sections.get("bonus_actions", ""))
        lair_actions = sections.get("lair_actions")

        # Extract spell references
        spell_refs = _extract_spells_from_traits(traits_md, lang)

        # Determine group letter from name
        group = name[0].upper() if name else ""

        monster = {
            "slug": slug,
            "name": name,
            "name_en": name_en,
            "size": type_info["size"],
            "type": type_info["type"],
            "subtype": type_info["subtype"],
            "alignment": type_info["alignment"],
            "ac": ac,
            "hp": hp,
            "speed": speed,
            "initiative": initiative,
            "abilities": abilities,
            "saving_throws": _parse_saving_throws(saves_raw),
            "skills": _parse_skills(skills_raw),
            "damage_resistances": _parse_damage_field(dmg_resist_raw),
            "damage_immunities": dmg_immune_list,
            "damage_vulnerabilities": _parse_damage_field(dmg_vuln_raw),
            "condition_immunities": cond_immune_list,
            "senses": senses,
            "languages": languages_raw or None,
            "cr": cr,
            "traits_md": traits_md if traits_md else [],
            "actions_md": actions_md if actions_md else [],
            "legendary_actions_md": legendary_md if legendary_md else [],
            "reactions_md": reactions_md if reactions_md else [],
            "bonus_actions_md": bonus_actions_md if bonus_actions_md else [],
            "lair_actions_md": lair_actions,
            "spells": spell_refs,
            "group": group,
        }
        monsters.append(monster)

    return monsters
