"""Parser for D&D SRD magic item blocks."""

import re

from .base import split_blocks, extract_names, slugify, last_table, without_tables


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


# --- Семейства: одна запись правил — несколько предметов (#412) ---------------------------------
# Запись-семейство становится группой (страница сайта, не запись API), её разновидности — записями.
# Разновидность — та, что отличается редкостью или текстом правил. Вид семейства:
#   rows       — строка таблицы на предмет: имя — первая ячейка, редкость — последняя;
#   horn       — строка таблицы «тип рога», редкость — из строки типа записи;
#   paragraphs — абзац «**_Имя (Редкость)._**» на предмет; абзацы без редкости относятся к предыдущему;
#   bonus      — «+1, +2 или +3»: предмет на бонус, редкость — из строки типа записи.
# Число — сколько разновидностей: расхождение роняет сборку.
# Имя разновидности — как в тексте. Где текст даёт одно уточнение («Absorption», «Anchor», «Silver»),
# имя семейства ставится впереди, как сам текст делает у поясов: «Ioun Stone (Absorption)». У фигурок
# имя в тексте самостоятельное («Bronze Griffon») и остаётся как есть (`BARE_NAMES`).
MAGIC_FAMILIES = {
    "potions-of-healing": ("rows", 4),
    "potion-of-giant-strength": ("rows", 5),
    "belt-of-giant-strength": ("rows", 5),
    "horn-of-valhalla": ("horn", 4),
    "ioun-stone": ("paragraphs", 14),
    "feather-token": ("paragraphs", 6),
    "figurine-of-wondrous-power": ("paragraphs", 9),
    "ammunition-1-2-or-3": ("bonus", 3),
    "armor-1-2-or-3": ("bonus", 3),
    "shield-1-2-or-3": ("bonus", 3),
    "wand-of-the-war-mage-1-2-or-3": ("bonus", 3),
    "weapon-1-2-or-3": ("bonus", 3),
}
BARE_NAMES = {"figurine-of-wondrous-power"}
# Ссылки на таблицу семейства (#434): таблица остаётся на странице семейства, а из текста разновидности
# её строки вырезаны — фраза о ней уходит тоже. Тип у разновидности уже выбран, поэтому «Мастер выбирает
# тип … по таблице» уходит целиком. Фрагмент не нашёлся — текст SRD поменялся, сборка падает.
TABLE_REFS = {
    "belt-of-giant-strength": {"en": [" (see the table below)"], "ru": [" (см. таблицу ниже)"]},
    "potion-of-giant-strength": {"en": [" (see the table below)"], "ru": [" (см. таблицу ниже)"]},
    "potions-of-healing": {"en": [", as shown in the table below"], "ru": [", как показано в таблице ниже"]},
    "horn-of-valhalla": {
        "en": [" The GM chooses the horn's type or determines it randomly by rolling on the following table."],
        "ru": [" Мастер выбирает тип рога или определяет его случайно по следующей таблице."]},
    "feather-token": {
        "en": [" The GM chooses the kind of token or determines it randomly by rolling on the Feather Tokens table."],
        "ru": [" Мастер выбирает вид талисмана или определяет его случайно, бросая по таблице «Перья-талисманы»."]},
}
_RARITY_WORDS = {**RARITIES_EN, **RARITIES_RU}
_RARITY_ALT = "|".join(sorted((re.escape(w) for w in _RARITY_WORDS), key=len, reverse=True))
_VARIETY_LEAD = re.compile(rf"^\*\*_(.+?) \(({_RARITY_ALT})\)\._\*\*\s*(.*)$", re.IGNORECASE)
_BONUS_LABEL = {"en": "Bonus", "ru": "Бонус"}


def _rarity(word: str, where: str) -> str:
    code = _RARITY_WORDS.get(word.strip().lower())
    if not code:
        raise ValueError(f"{where}: unknown rarity {word!r}")
    return code


def _rarity_by_mark(type_line: str, where: str) -> dict[str, str]:
    """«Uncommon (+1), Rare (+2), or Very Rare (+3)» → {"+1": uncommon, …}; у рога — по металлу."""
    out: dict[str, str] = {}
    for word, marks in re.findall(rf"({_RARITY_ALT})\s*\(([^)]+)\)", type_line, flags=re.IGNORECASE):
        for mark in re.split(r"\s+(?:or|или)\s+|,\s*", marks):
            out[mark.strip().lower()] = _rarity(word, where)
    return out


def _without_table_refs(text: str, slug: str, lang: str, where: str) -> str:
    for fragment in TABLE_REFS.get(slug, {}).get(lang, []):
        if fragment not in text:
            raise ValueError(f"{where}: no table reference {fragment.strip()!r} to cut from the varieties")
        text = text.replace(fragment, "")
    return text


def _varieties(parent: dict, type_line: str, lang: str) -> list[dict]:
    """Разновидности семейства как записи `magic-items`; слаг и `name_en` — только у EN."""
    kind, expected = MAGIC_FAMILIES[parent["slug"]]
    where = parent["name"]
    body = parent["description_md"]
    rows: list[dict] = []  # name, rarity, text
    if kind in ("rows", "horn"):
        header, table = last_table(body)
        prose = _without_table_refs(without_tables(body), parent["slug"], lang, where)
        by_mark = _rarity_by_mark(type_line, where) if kind == "horn" else {}
        for cells in table:
            if len(cells) != len(header):
                raise ValueError(f"{where}: row {cells[0]!r} has {len(cells)} cells, the header has {len(header)}")
            if kind == "rows":
                name, rarity, facts = cells[0], _rarity(cells[-1], where), list(zip(header[1:-1], cells[1:-1]))
            else:  # 1d100 | Horn Type | Spirits | Requirement
                rarity = by_mark.get(cells[1].lower())
                if not rarity:
                    raise ValueError(f"{where}: no rarity for {cells[1]!r} in {type_line!r}")
                name, facts = f"{parent['name']} ({cells[1]})", list(zip(header[2:], cells[2:]))
            rows.append({"name": name, "rarity": rarity,
                         "text": "\n\n".join([prose] + [f"**{label}:** {value}" for label, value in facts])})
    elif kind == "paragraphs":
        intro: list[str] = []
        for line in without_tables(body).split("\n"):
            lead = _VARIETY_LEAD.match(line.strip())
            if lead:
                own = lead.group(1).strip()
                rows.append({"name": own if parent["slug"] in BARE_NAMES else f"{parent['name']} ({own})",
                             "rarity": _rarity(lead.group(2), where),
                             "text": [lead.group(3).strip()]})
            elif rows:
                rows[-1]["text"].append(line)
            else:
                intro.append(line)
        head = _without_table_refs("\n".join(intro).strip(), parent["slug"], lang, where)
        for row in rows:
            row["text"] = "\n\n".join(t for t in (head, "\n".join(row["text"]).strip()) if t)
    else:  # bonus
        by_mark = _rarity_by_mark(type_line, where)
        base = re.split(r",\s*\+1", parent["name"])[0].strip()
        for bonus in ("+1", "+2", "+3"):
            if bonus not in by_mark:
                raise ValueError(f"{where}: no rarity for {bonus} in {type_line!r}")
            rows.append({"name": f"{base} {bonus}", "rarity": by_mark[bonus],
                         "text": f"{body}\n\n**{_BONUS_LABEL[lang]}:** {bonus}"})
    if len(rows) != expected:
        raise ValueError(f"{where}: {len(rows)} varieties, declared {expected}")
    en = lang == "en"
    return [{
        "slug": slugify(row["name"]) if en else None,
        "name": row["name"],
        "name_en": None,
        "type": parent["type"],
        "subtype": parent["subtype"],
        "rarity": row["rarity"],
        "rarities": [row["rarity"]],
        "attunement": parent["attunement"],
        "description_md": row["text"],
        "spells": _extract_spell_refs(row["text"]),
        "group": parent["slug"],
    } for row in rows]


def parse_magic_items(text: str, heading_level: int, lang: str,
                      after: str | None = None, skip_headings: set | None = None,
                      families: bool = False) -> list[dict]:
    """Parse all magic item blocks from markdown text.

    `families` — резать семейства на разновидности (#412): только SRD 5.2, для неё они и объявлены.
    """
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
            "group": None,
        }
        if families and slug in MAGIC_FAMILIES:
            # Семейство — группа (`_group`): в `magic-items` идут её разновидности (#412).
            items.append({**item, "_group": True})
            items.extend(_varieties(item, type_line, lang))
        else:
            items.append(item)

    return items
