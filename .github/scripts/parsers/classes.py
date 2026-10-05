"""Parser for D&D SRD 5.2 class chapters (03_Classes/*.md): classes and subclasses (#365).

Language-invariant codes (abilities, skills, armor, spellcasting, progression column keys) are
read from EN only; RU entities carry None there (progression values as a list in column order)
until generate_api.align_classes copies them by position.
"""

import re

from .base import slugify

ABILITY_CODES = {"strength": "str", "dexterity": "dex", "constitution": "con",
                 "intelligence": "int", "wisdom": "wis", "charisma": "cha"}
SKILLS = {"Acrobatics", "Animal Handling", "Arcana", "Athletics", "Deception", "History",
          "Insight", "Intimidation", "Investigation", "Medicine", "Nature", "Perception",
          "Performance", "Persuasion", "Religion", "Sleight of Hand", "Stealth", "Survival"}
ARMOR_CATEGORIES = ("light", "medium", "heavy", "shield")

_TRAIT_KEYS = {
    "Primary Ability": "primary_ability", "Основная характеристика": "primary_ability",
    "Hit Point Die": "hit_die", "Кость Хитов": "hit_die",
    "Saving Throw Proficiencies": "saving_throws", "Владение спасбросками": "saving_throws",
    "Skill Proficiencies": "skills", "Владение навыками": "skills",
    "Weapon Proficiencies": "weapons", "Владение оружием": "weapons",
    "Tool Proficiencies": "tools", "Владение инструментами": "tools",
    "Armor Training": "armor", "Владение доспехами": "armor",
    "Starting Equipment": "starting_equipment", "Начальное снаряжение": "starting_equipment",
}

_FEATURE_RE = re.compile(r"^#{3,4} (?:Level|Уровень) (\d+): (.+)$")
_SUBCLASS_RE = {"en": re.compile(r"^### (.+?) Subclass: (.+)$"),
                "ru": re.compile(r"^### Подкласс (.+?): (.+)$")}
_TABLE_TITLE_RE = re.compile(r"^(?:Table|Таблица): (.+)$")
_SLOT_COLUMNS = [str(n) for n in range(1, 10)]


def _clean(line: str) -> str:
    return line.replace("**", "").strip()


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_separator(cells: list[str]) -> bool:
    joined = "".join(cells)
    return bool(joined) and set(joined) <= set("-: ")


def _tables(lines: list[str]) -> list[dict]:
    """Every markdown table as {title, header, rows}; title is the preceding `Table:` line."""
    out = []
    title = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = _TABLE_TITLE_RE.match(line)
        if m:
            title = m.group(1).strip()
        elif line.startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(_cells(lines[i]))
                i += 1
            rows = [c for c in block[1:] if not _is_separator(c)]
            out.append({"title": title, "header": block[0], "rows": rows})
            title = None
            continue
        elif line.startswith("#"):
            title = None
        i += 1
    return out


def _features(lines: list[str]) -> list[dict]:
    """`Level N: Name` headings (### or ####); the body runs to the next heading of any level."""
    out = []
    current = None
    for line in lines:
        if line.startswith("#"):
            if current:
                out.append(current)
                current = None
            m = _FEATURE_RE.match(_clean(line))
            if m:
                current = {"level": int(m.group(1)), "name": m.group(2).strip(), "body": []}
        elif current is not None:
            current["body"].append(line)
    if current:
        out.append(current)
    return [{"level": f["level"], "name": f["name"],
             "description_md": "\n".join(f["body"]).strip()} for f in out]


def _abilities(text: str) -> list[str]:
    found = re.findall(r"[A-Za-z]+", text)
    codes = [ABILITY_CODES[w.lower()] for w in found if w.lower() in ABILITY_CODES]
    if not codes:
        raise ValueError(f"no ability in {text!r}")
    return codes


def _skills(text: str, lang: str) -> dict:
    m = re.search(r"\d+", text)
    if not m:
        raise ValueError(f"no skill count in {text!r}")
    out = {"text": text, "choose": int(m.group()), "options": None}
    if lang != "en":
        return out
    if re.match(r"Choose any \d+ skills", text):
        return out  # любой навык — options остаётся null
    listed = text.split(":", 1)[1]
    names = [re.sub(r"^or ", "", n.strip()) for n in listed.split(",")]
    unknown = [n for n in names if n not in SKILLS]
    if unknown:
        raise ValueError(f"unknown skills {unknown} in {text!r}")
    out["options"] = [slugify(n) for n in names]
    return out


def _armor(text: str, lang: str) -> dict:
    if lang != "en":
        return {"text": text, "categories": None}
    lower = text.lower()
    return {"text": text, "categories": [c for c in ARMOR_CATEGORIES if c in lower]}


def _weapons(text: str, lang: str) -> dict:
    """categories — categories granted whole: Monk's «Martial weapons that have…» is not one."""
    if lang != "en":
        return {"text": text, "categories": None}
    cats = ["simple"] if "Simple" in text else []
    if re.search(r"Martial weapons(?! that)", text):
        cats.append("martial")
    return {"text": text, "categories": cats}


def _slot_count(cell: str, level: str, name: str) -> int:
    if cell == "—":
        return 0
    if not cell.isdigit():
        raise ValueError(f"{name}: progression level {level}: spell slot cell {cell!r}")
    return int(cell)


def _progression(table: dict, lang: str, name: str) -> dict:
    header = table["header"]
    extra = [(i, h) for i, h in enumerate(header) if i > 2 and h not in _SLOT_COLUMNS]
    keys = [slugify(h) if lang == "en" else None for _, h in extra]
    slot_idx = [i for i, h in enumerate(header) if h in _SLOT_COLUMNS]
    rows = []
    for cells in table["rows"]:
        slots = None
        if slot_idx:
            slots = [0] * 9
            for i in slot_idx:
                slots[int(header[i]) - 1] = _slot_count(cells[i], cells[0], name)
        feats = [] if cells[2] in ("—", "") else [f.strip() for f in cells[2].split(",")]
        rows.append({
            "level": int(cells[0]),
            "proficiency_bonus": int(cells[1]),
            "features": feats,
            "values": ({k: cells[i] for k, (i, _) in zip(keys, extra)} if lang == "en"
                       else [cells[i] for i, _ in extra]),
            "spell_slots": slots,
        })
    return {"columns": [{"key": k, "name": h} for k, (_, h) in zip(keys, extra)], "rows": rows}


def _spellcasting(features: list[dict], progression: dict) -> dict | None:
    for f in features:
        body = f["description_md"]
        m = re.search(r"\*\*Spellcasting Ability\.\*\* (\w+) is", body)
        if not m:
            continue
        change = re.search(r"\*\*Changing Your Prepared Spells\.\*\* ([^\n]+)", body)
        if not change:
            raise ValueError(f"{f['name']}: no «Changing Your Prepared Spells» paragraph")
        rule = change.group(1)
        if "finish a Long Rest" in rule:
            change_on = "long_rest"
        elif re.search(r"gain an? \w+ level", rule):
            change_on = "level_up"
        else:
            raise ValueError(f"{f['name']}: unknown prepared-spell change rule {rule!r}")
        keys = {c["key"] for c in progression["columns"]}
        return {
            "feature": f["name"],
            "level": f["level"],
            "ability": ABILITY_CODES[m.group(1).lower()],
            "change_on": change_on,
            "change_count": "one" if "replace one spell" in rule else "any",
            "prepare_from": "spellbook" if "spellbook" in rule else "class_list",
            "slots": "pact" if "slot-level" in keys else "standard",
        }
    return None


def _subclass_starts(lines: list[str], lang: str) -> list[tuple[int, str, str]]:
    out = []
    for i, line in enumerate(lines):
        m = _SUBCLASS_RE[lang].match(_clean(line))
        if m:
            out.append((i, m.group(1).strip(), m.group(2).strip()))
    return out


def parse_class(text: str, lang: str) -> list[dict]:
    """One class record from a class chapter; everything after the first subclass heading is skipped."""
    lines = text.split("\n")
    name = next((_clean(l)[3:] for l in lines if l.startswith("## ")), None)
    if not name:
        return []
    starts = _subclass_starts(lines, lang)
    class_lines = lines[:starts[0][0]] if starts else lines
    tables = _tables(class_lines)

    traits: dict[str, str] = {}
    for label, value, *_ in tables[0]["rows"]:
        key = _TRAIT_KEYS.get(label)
        if not key:
            raise ValueError(f"{name}: unknown core trait {label!r}")
        traits[key] = value
    missing = {"primary_ability", "hit_die", "saving_throws", "skills", "weapons", "armor",
               "starting_equipment"} - set(traits)
    if missing:
        raise ValueError(f"{name}: core traits table lacks {sorted(missing)}")
    die = re.search(r"[dDкКдД](\d+)", traits["hit_die"])
    if not die:
        raise ValueError(f"{name}: no die in {traits['hit_die']!r}")

    prog_table = next((t for t in tables if t["header"][0] in ("Level", "Уровень")), None)
    if not prog_table:
        raise ValueError(f"{name}: no class progression table")
    progression = _progression(prog_table, lang, name)
    features = _features(class_lines)
    en = lang == "en"
    return [{
        "slug": slugify(name) if en else None,
        "name": name,
        "name_en": None,
        "hit_die": int(die.group(1)),
        "primary_ability": {"text": traits["primary_ability"],
                            "abilities": _abilities(traits["primary_ability"]) if en else None,
                            "require": ("any" if " or " in traits["primary_ability"] else "all")
                                       if en else None},
        "saving_throws": _abilities(traits["saving_throws"]) if en else None,
        "proficiencies": {
            "armor": _armor(traits["armor"], lang),
            "weapons": _weapons(traits["weapons"], lang),
            "tools": {"text": traits["tools"]} if "tools" in traits else None,
            "skills": _skills(traits["skills"], lang),
        },
        "starting_equipment": traits["starting_equipment"],
        "progression": progression,
        "features": features,
        "spellcasting": _spellcasting(features, progression) if en else None,
    }]


def _spell_tables(lines: list[str]) -> list[dict]:
    """Subclass spell tables: two columns, `<Class> Level | …Spells`, integer level rows."""
    out = []
    for t in _tables(lines):
        if len(t["header"]) != 2 or not re.search(r"Level|Уровень", t["header"][0]):
            continue
        rows = []
        for level, spells in t["rows"]:
            if not level.isdigit():
                raise ValueError(f"table {t['title']!r}: level cell {level!r}")
            rows.append({"level": int(level),
                         "spells": [s.strip() for s in spells.split(",") if s.strip()]})
        out.append({"title": t["title"], "rows": rows})
    return out


def parse_subclasses(text: str, lang: str) -> list[dict]:
    """Subclass records; `always_prepared` holds spell NAMES until generate_api resolves them to slugs.

    Several spell tables in one subclass are alternatives (Circle of the Land: one per land),
    so each row then carries `choice` = {key, name} of its table; a single table gives choice null.
    """
    lines = text.split("\n")
    class_name = next((_clean(l)[3:] for l in lines if l.startswith("## ")), "")
    starts = _subclass_starts(lines, lang)
    out = []
    for n, (start, _, name) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        section = lines[start + 1:end]
        first_feature = next((i for i, l in enumerate(section) if _FEATURE_RE.match(_clean(l))),
                             len(section))
        tables = _spell_tables(section)
        always = []
        for t in tables:
            choice = None
            if len(tables) > 1:
                choice = {"key": slugify(t["title"]) if lang == "en" else None, "name": t["title"]}
            always += [{**row, "choice": choice} for row in t["rows"]]
        out.append({
            "slug": slugify(name) if lang == "en" else None,
            "name": name,
            "name_en": None,
            "class": slugify(class_name) if lang == "en" else None,
            "description_md": "\n".join(section[:first_feature]).strip(),
            "features": _features(section),
            "always_prepared": always,
        })
    return out


# --- Варианты классовых умений (#374) -------------------------------------------------------
# Два вида списков. Раздел «### … Options» / «### Опции …» с вариантами-#### (воззвания,
# метамагия) — родитель тот, чьё тело ссылается на раздел в кавычках. И варианты абзацами
# «**Имя.**» в теле умения после фразы-маркера («one of the following options…», у Fighting
# Style — «you can choose the option below» вместо черты); список-
# расширение («…are now among your Cunning Strike options») пополняет ближайший предыдущий
# базовый список главы, и тогда умение-источник — granted_by.

_OPTION_SECTION_RE = {"en": re.compile(r"^### (.+ Options)$"), "ru": re.compile(r"^### (Опции .+)$")}
_LIST_MARKER_RE = {
    "en": re.compile(r"one of the following (?:sacred roles|(?:feature )?options|(?:[\w ]+ )?effects)"
                     r"|following effect options|following effects are now among"
                     r"|following [\w ]+ option\b|choose the option below"),
    "ru": re.compile(r"од(?:ин|н\w+) из следующих (?:священных ролей|опций|эффектов)"
                     r"|следующие варианты эффектов|[Сс]ледующие эффекты теперь входят"
                     r"|следующую опцию|выбрать опцию ниже"),
}
_EXTENSION_RE = {"en": re.compile(r"now among your|You gain the following [\w ]+ option\b"),
                 "ru": re.compile(r"теперь входят в|следующую опцию")}
# «Выбрал и держишь» — фраза-маркер с «of your choice» или альтернатива черте боевого стиля
# («Instead of choosing one of those feats, you can choose the option below»: Blessed Warrior).
_LEARNED_RE = {"en": re.compile(r"of your choice|choose the option below"),
               "ru": re.compile(r"на свой выбор|выбрать опцию ниже")}
_COST_WORD = r"(?:Cost|Стоимость)"
_BOLD_OPTION_RE = re.compile(rf"^\*\*(.+?)(?: \({_COST_WORD}: ([^)]+)\))?\.\*\* ?(.*)$")
_INLINE_OPTION_RE = re.compile(rf"\*([^*]+?) \({_COST_WORD}: ([^)]+)\)\.\* (.+)$")
_META_LINE_RE = re.compile(r"^\*(Prerequisite|Требование|Cost|Стоимость): (.+)\*$")
_REPEATABLE_RE = re.compile(r"^\*\*(?:Repeatable|Повторяемое)\.\*\*")
_CANTRIP_PREREQS = {"a Warlock Cantrip That Deals Damage": "damage",
                    "a Warlock Cantrip That Deals Damage via an Attack Roll": "damage-attack-roll"}
COST_UNITS = ("sorcery-point", "sneak-attack-die")
CANTRIP_PREREQS = tuple(_CANTRIP_PREREQS.values())


def _option_cost(text: str) -> dict:
    """Closed set of units: an unknown cost form is a build error, not a free-text field."""
    m = re.fullmatch(r"(\d+) (?:Sorcery Points?|очк\w+ чародейства)", text)
    if m:
        return {"text": text, "amount": int(m.group(1)), "unit": "sorcery-point"}
    m = re.fullmatch(r"(\d+)d6", text)
    if m:
        return {"text": text, "amount": int(m.group(1)), "unit": "sneak-attack-die"}
    raise ValueError(f"unknown option cost {text!r}")


def _option_prerequisites(text: str, lang: str) -> dict:
    """level / options (EN invocation NAMES until generate_api resolves them) / cantrip — from EN;
    RU keeps its own text and gets the codes from EN by position."""
    if lang != "en":
        return {"text": text, "level": None, "options": None, "cantrip": None}
    out = {"text": text, "level": None, "options": [], "cantrip": None}
    for part in text.split(", "):
        m = re.fullmatch(r"Level (\d+)\+ \w+", part)
        if m:
            out["level"] = int(m.group(1))
        elif part in _CANTRIP_PREREQS:
            out["cantrip"] = _CANTRIP_PREREQS[part]
        elif part.endswith(" Invocation"):
            out["options"].append(part[:-len(" Invocation")])
        else:
            raise ValueError(f"unknown prerequisite {part!r} in {text!r}")
    return out


def _feature_blocks(lines: list[str], lang: str) -> list[dict]:
    """`Level N: Name` features of the whole chapter with their subclass (None for the class)."""
    out = []
    current = None
    subclass = None
    for line in lines:
        if line.startswith("#"):
            current = None
            m = _SUBCLASS_RE[lang].match(_clean(line))
            if m:
                subclass = m.group(2).strip()
                continue
            m = _FEATURE_RE.match(_clean(line))
            if m:
                current = {"level": int(m.group(1)), "name": m.group(2).strip(),
                           "subclass": subclass, "body": []}
                out.append(current)
        elif current is not None:
            current["body"].append(line)
    return out


def _paragraphs(body: list[str]) -> list[str]:
    return [p.strip() for p in "\n".join(body).split("\n\n") if p.strip()]


def _ref(feature: dict | None, en: bool) -> dict | None:
    if feature is None:
        return None
    return {"key": slugify(feature["name"]) if en else None, "name": feature["name"],
            "level": feature["level"]}


def _option(name, body_md, cost, prereq, repeatable, feature, granted_by, selection,
            class_name, en) -> dict:
    return {
        "slug": slugify(name) if en else None,
        "name": name,
        "name_en": None,
        "class": slugify(class_name) if en else None,
        "subclass": (slugify(feature["subclass"]) if feature["subclass"] else None) if en else None,
        "feature": _ref(feature, en),
        "granted_by": _ref(granted_by, en),
        "selection": selection,
        "prerequisites": prereq,
        "cost": cost,
        "repeatable": repeatable,
        "description_md": body_md,
    }


def _section_options(lines, features, class_name, lang) -> list[dict]:
    """«### … Options» sections: each #### is an option; leading *Prerequisite:*/*Cost:* lines
    become fields and leave description_md."""
    en = lang == "en"
    out = []
    i = 0
    while i < len(lines):
        m = _OPTION_SECTION_RE[lang].match(lines[i].strip())
        if not m:
            i += 1
            continue
        title = m.group(1)
        quoted = (f'"{title}"', f"«{title}»")
        parent = next((f for f in features if f["subclass"] is None
                       and any(q in "\n".join(f["body"]) for q in quoted)), None)
        if parent is None:
            raise ValueError(f"{class_name}: no feature refers to section {title!r}")
        i += 1
        items = []
        while i < len(lines) and not re.match(r"^#{1,3} ", lines[i]):
            if lines[i].startswith("#### "):
                items.append({"name": _clean(lines[i])[5:], "body": []})
            elif items:
                items[-1]["body"].append(lines[i])
            i += 1
        if not items:
            raise ValueError(f"{class_name}: section {title!r} has no options")
        for it in items:
            paras = _paragraphs(it["body"])
            cost = prereq = None
            while paras and (meta := _META_LINE_RE.match(paras[0])):
                if meta.group(1) in ("Cost", "Стоимость"):
                    cost = _option_cost(meta.group(2))
                else:
                    prereq = _option_prerequisites(meta.group(2), lang)
                paras.pop(0)
            out.append(_option(it["name"], "\n\n".join(paras), cost, prereq,
                               any(_REPEATABLE_RE.match(p) for p in paras),
                               parent, None, "learned", class_name, en))
    return out


def _inline_options(features, class_name, lang) -> list[dict]:
    en = lang == "en"
    out = []
    base = None  # последний базовый список главы — родитель для списков-расширений
    for f in features:
        paras = _paragraphs(f["body"])
        first = next((n for n, p in enumerate(paras) if _BOLD_OPTION_RE.match(p)), len(paras))
        intro = " ".join(paras[:first])
        marker = _LIST_MARKER_RE[lang].search(intro)
        if not marker:
            continue
        extension = bool(_EXTENSION_RE[lang].search(intro))
        if extension and base is None:
            raise ValueError(f"{class_name}: {f['name']!r} extends no earlier option list")
        sentence = re.split(r"(?<=[.!?])\s", intro[marker.start():], maxsplit=1)[0]
        selection = base["selection"] if extension else (
            "learned" if _LEARNED_RE[lang].search(sentence) else "on_use")
        parent, granted_by = (base["feature"], f) if extension else (f, None)
        items = []
        inline = _INLINE_OPTION_RE.search(paras[first - 1]) if first else None
        if inline and first == len(paras):
            items.append([inline.group(1), inline.group(2), [inline.group(3)]])
        for p in paras[first:]:
            m = _BOLD_OPTION_RE.match(p)
            if m:
                items.append([m.group(1), m.group(2), [m.group(3)] if m.group(3) else []])
            else:
                items[-1][2].append(p)  # абзац-продолжение варианта («To use this effect…»)
        if not items:
            raise ValueError(f"{class_name}: {f['name']!r} announces options but lists none")
        for name, cost, body in items:
            out.append(_option(name, "\n\n".join(body), _option_cost(cost) if cost else None,
                               None, False, {**parent, "subclass": f["subclass"]}, granted_by,
                               selection, class_name, en))
        if not extension:
            base = {"feature": f, "selection": selection}
    return out


def parse_class_options(text: str, lang: str) -> list[dict]:
    """Class feature options (Eldritch Invocations, Metamagic, Cunning Strike, Divine Order…), #374.

    EN/RU chapters are line-paired: generate_api.align_class_options copies slug, name_en and
    the codes to RU by position and resolves prerequisite invocation names to slugs.
    """
    lines = text.split("\n")
    class_name = next((_clean(l)[3:] for l in lines if l.startswith("## ")), None)
    if not class_name:
        return []
    features = _feature_blocks(lines, lang)
    return _section_options(lines, features, class_name, lang) + \
        _inline_options(features, class_name, lang)
