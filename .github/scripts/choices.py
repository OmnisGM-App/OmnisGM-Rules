"""Объявления выборов SRD 5.2 (#413): что игрок выбирает при сборке персонажа и откуда берутся варианты.

Текст правил объявляет выбор словами («of your choice»), поэтому объявления написаны руками и
прикрепляются к умению класса или подкласса, особенности вида, предыстории, черте и варианту умения
по EN-имени. Объявление, которому не нашлось хозяина, и ссылка, которая не разрешилась, роняют сборку.

Выбор при применении (цель, форма области, эффект удара) не объявляется: он не хранится у персонажа.
Стартовое снаряжение «A или B» остаётся текстом.
"""

ABILITIES = ("str", "dex", "con", "int", "wis", "cha")
DAMAGE_TYPES = ("acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic", "piercing",
                "poison", "psychic", "radiant", "slashing", "thunder")
KINDS = ("subclass", "feat", "option", "skill", "expertise", "tool", "language", "weapon-mastery", "spell",
         "spell-list", "damage-type", "ability-score", "spellcasting-ability", "lineage", "size", "land")
# Закрытые списки: values — подмножество, null — список целиком.
LISTS = ("skills", "abilities", "damage-types", "sizes", "languages", "tools", "skills-or-tools",
         "musical-instruments", "artisan-tools-or-musical-instruments", "classes", "lands")
RESOURCES = ("feats", "subclasses", "class-options", "spells", "weapons", "species-lineages", "equipment")
CHARACTER = ("skill-proficiencies", "weapon-proficiencies", "known-cantrips", "spellbook")
REPLACE = ("never", "level", "long-rest", "short-rest")


def lst(name, values=None):
    # Строка — подстановка сборки ("{lands}"), её заменит `_fill`.
    return {"list": name, "values": values if values is None or isinstance(values, str) else list(values)}


def res(resource, **filters):
    return {"resource": resource, "filter": filters}


def own(what, **filters):
    return {"character": what, "filter": filters}


def ch(key, kind, count, source, replace="never", **extra):
    """count — число, список пар (уровень, всего на уровне) или ("column", ключ колонки прогрессии)."""
    return {"id": key, "kind": kind, "count": count, "from": source, "replace": replace, **extra}


MENTAL = ("int", "wis", "cha")
ANY_FEAT = res("feats")
STYLE = res("feats", category="fighting_style")

# --- Классы: (слаг класса или "*", EN-имя умения) → выборы ---------------------------------------
# "{class}" в фильтре заменяется слагом класса; "{Class} Subclass" — имя умения «Bard Subclass».
CLASS_FEATURES = {
    ("*", "{Class} Subclass"): [ch("subclass", "subclass", 1, res("subclasses", **{"class": "{class}"}))],
    # «…or another feat of your choice for which you qualify»: любая черта, названная — подсказкой.
    ("*", "Ability Score Improvement"): [
        ch("feat", "feat", 1, ANY_FEAT, suggest={"slug": "ability-score-improvement"})],
    ("*", "Epic Boon"): [ch("feat", "feat", 1, ANY_FEAT, suggest={"category": "epic_boon"})],

    ("barbarian", "Weapon Mastery"): [
        ch("weapons", "weapon-mastery", ("column", "weapon-mastery"), res("weapons", type="melee"), "long-rest")],
    ("barbarian", "Primal Knowledge"): [ch("skill", "skill", 1, lst("skills", "{class-skills}"))],

    ("bard", "Spellcasting"): [
        ch("cantrips", "spell", ("column", "cantrips"), res("spells", **{"class": "bard"}, level=0), "level"),
        ch("prepared", "spell", ("column", "prepared-spells"), res("spells", **{"class": "bard"}, level="slots"), "level")],
    ("bard", "Expertise"): [ch("skills", "expertise", [(2, 2), (9, 4)], own("skill-proficiencies"))],

    ("cleric", "Spellcasting"): [
        ch("cantrips", "spell", ("column", "cantrips"), res("spells", **{"class": "cleric"}, level=0), "level"),
        ch("prepared", "spell", ("column", "prepared-spells"), res("spells", **{"class": "cleric"}, level="slots"), "long-rest")],
    ("cleric", "Divine Order"): [ch("option", "option", 1, res("class-options", **{"class": "cleric"}, feature="divine-order"))],
    ("cleric", "Blessed Strikes"): [ch("option", "option", 1, res("class-options", **{"class": "cleric"}, feature="blessed-strikes"))],

    ("druid", "Spellcasting"): [
        ch("cantrips", "spell", ("column", "cantrips"), res("spells", **{"class": "druid"}, level=0), "level"),
        ch("prepared", "spell", ("column", "prepared-spells"), res("spells", **{"class": "druid"}, level="slots"), "long-rest")],
    ("druid", "Primal Order"): [ch("option", "option", 1, res("class-options", **{"class": "druid"}, feature="primal-order"))],
    ("druid", "Elemental Fury"): [ch("option", "option", 1, res("class-options", **{"class": "druid"}, feature="elemental-fury"))],

    ("fighter", "Fighting Style"): [ch("feat", "feat", 1, STYLE, "level")],
    ("fighter", "Weapon Mastery"): [
        ch("weapons", "weapon-mastery", ("column", "weapon-mastery"), res("weapons"), "long-rest")],

    # «Instead of choosing one of those feats, you can choose the option below» — второй источник в `or`.
    ("paladin", "Fighting Style"): [
        ch("feat", "feat", 1, STYLE, "level", **{"or": res("class-options", **{"class": "paladin"}, feature="fighting-style")})],
    ("paladin", "Weapon Mastery"): [ch("weapons", "weapon-mastery", 2, own("weapon-proficiencies"), "long-rest")],
    ("paladin", "Spellcasting"): [
        ch("prepared", "spell", ("column", "prepared-spells"), res("spells", **{"class": "paladin"}, level="slots"), "long-rest")],

    ("ranger", "Fighting Style"): [
        ch("feat", "feat", 1, STYLE, "level", **{"or": res("class-options", **{"class": "ranger"}, feature="fighting-style")})],
    ("ranger", "Weapon Mastery"): [ch("weapons", "weapon-mastery", 2, own("weapon-proficiencies"), "long-rest")],
    ("ranger", "Spellcasting"): [
        ch("prepared", "spell", ("column", "prepared-spells"), res("spells", **{"class": "ranger"}, level="slots"), "long-rest")],
    ("ranger", "Deft Explorer"): [
        ch("skill", "expertise", 1, own("skill-proficiencies")),
        ch("languages", "language", 2, lst("languages"))],
    ("ranger", "Expertise"): [ch("skills", "expertise", 2, own("skill-proficiencies"))],

    ("rogue", "Expertise"): [ch("skills", "expertise", [(1, 2), (6, 4)], own("skill-proficiencies"))],
    ("rogue", "Thieves' Cant"): [ch("language", "language", 1, lst("languages"))],
    ("rogue", "Weapon Mastery"): [ch("weapons", "weapon-mastery", 2, own("weapon-proficiencies"), "long-rest")],

    ("sorcerer", "Spellcasting"): [
        ch("cantrips", "spell", ("column", "cantrips"), res("spells", **{"class": "sorcerer"}, level=0), "level"),
        ch("prepared", "spell", ("column", "prepared-spells"), res("spells", **{"class": "sorcerer"}, level="slots"), "level")],
    ("sorcerer", "Metamagic"): [
        ch("options", "option", [(2, 2), (10, 4), (17, 6)], res("class-options", **{"class": "sorcerer"}, feature="metamagic"), "level")],

    ("warlock", "Pact Magic"): [
        ch("cantrips", "spell", ("column", "cantrips"), res("spells", **{"class": "warlock"}, level=0), "level"),
        ch("prepared", "spell", ("column", "prepared-spells"), res("spells", **{"class": "warlock"}, level="slots"), "level")],
    ("warlock", "Eldritch Invocations"): [
        ch("invocations", "option", ("column", "eldritch-invocations"),
           res("class-options", **{"class": "warlock"}, feature="eldritch-invocations"), "level")],
    ("warlock", "Mystic Arcanum"): [
        ch(f"arcanum-{spell}", "spell", 1, res("spells", **{"class": "warlock"}, level=spell), "level", level=level)
        for level, spell in ((11, 6), (13, 7), (15, 8), (17, 9))],

    ("wizard", "Spellcasting"): [
        ch("cantrips", "spell", ("column", "cantrips"), res("spells", **{"class": "wizard"}, level=0), "long-rest"),
        ch("prepared", "spell", ("column", "prepared-spells"), own("spellbook"), "long-rest")],
    ("wizard", "Scholar"): [
        ch("skill", "expertise", 1,
           own("skill-proficiencies", values=["arcana", "history", "investigation", "medicine", "nature", "religion"]))],
    ("wizard", "Spell Mastery"): [
        ch("level-1", "spell", 1, own("spellbook", level=1, casting_time="action"), "long-rest"),
        ch("level-2", "spell", 1, own("spellbook", level=2, casting_time="action"), "long-rest")],
    ("wizard", "Signature Spells"): [ch("spells", "spell", 2, own("spellbook", level=3))],
}

# Владение инструментом из таблицы черт класса — выбор самого класса, не умения.
CLASSES = {
    "bard": [ch("instruments", "tool", 3, lst("musical-instruments"))],
    "monk": [ch("tool", "tool", 1, lst("artisan-tools-or-musical-instruments"))],
}

# --- Подклассы: (слаг подкласса, EN-имя умения) → выборы -----------------------------------------
SUBCLASS_FEATURES = {
    ("champion", "Additional Fighting Style"): [ch("feat", "feat", 1, STYLE)],
    # Земля уже размечена в `always_prepared[].choice`; значения списка подставляет сборка.
    ("circle-of-the-land", "Circle of the Land Spells"): [ch("land", "land", 1, lst("lands", "{lands}"), "long-rest")],
    ("college-of-lore", "Bonus Proficiencies"): [ch("skills", "skill", 3, lst("skills"))],
    ("college-of-lore", "Magical Discoveries"): [
        ch("spells", "spell", 2, res("spells", **{"class": ["cleric", "druid", "wizard"]}, level="cantrip-or-slots"), "level")],
    ("draconic-sorcery", "Elemental Affinity"): [
        ch("damage-type", "damage-type", 1, lst("damage-types", ["acid", "cold", "fire", "lightning", "poison"]))],
    # Плюс по заклинанию школы на каждый новый круг ячеек — в тексте умения, числом не объявлено.
    ("evoker", "Evocation Savant"): [
        ch("spells", "spell", 2, res("spells", **{"class": "wizard"}, school="evocation", max_level=2))],
    ("fiend-patron", "Fiendish Resilience"): [
        ch("damage-type", "damage-type", 1, lst("damage-types", [d for d in DAMAGE_TYPES if d != "force"]), "short-rest")],
    ("hunter", "Hunter's Prey"): [
        ch("option", "option", 1, res("class-options", **{"class": "ranger"}, feature="hunter-s-prey"), "short-rest")],
    ("hunter", "Defensive Tactics"): [
        ch("option", "option", 1, res("class-options", **{"class": "ranger"}, feature="defensive-tactics"), "short-rest")],
}

# --- Виды: (слаг вида, EN-имя особенности) → выборы. Размер и наследие сборка объявляет сама ------
SPECIES_TRAITS = {
    ("elf", "Elven Lineage"): [ch("spellcasting-ability", "spellcasting-ability", 1, lst("abilities", MENTAL))],
    ("elf", "Keen Senses"): [ch("skill", "skill", 1, lst("skills", ["insight", "perception", "survival"]))],
    ("gnome", "Gnomish Lineage"): [ch("spellcasting-ability", "spellcasting-ability", 1, lst("abilities", MENTAL))],
    ("tiefling", "Fiendish Legacy"): [ch("spellcasting-ability", "spellcasting-ability", 1, lst("abilities", MENTAL))],
    ("human", "Skillful"): [ch("skill", "skill", 1, lst("skills"))],
    ("human", "Versatile"): [ch("feat", "feat", 1, res("feats", category="origin"))],
}

# --- Предыстории: правило прибавок у всех одно; характеристики — свои, подставляет сборка ---------
# increase — допустимые распределения: +2 и +1 либо по +1 к каждой из трёх.
BACKGROUND = [ch("ability-scores", "ability-score", 1, lst("abilities", "{abilities}"), increase=[[2, 1], [1, 1, 1]], max=20)]
BACKGROUNDS = {
    "soldier": [ch("tool", "tool", 1, res("equipment", group="{tool.choose_from}"))],
}


def _boon(values=None):
    return [ch("ability-score", "ability-score", 1, lst("abilities", values), increase=[[1]], max=30)]


# --- Черты ---------------------------------------------------------------------------------------
FEATS = {
    "ability-score-improvement": [ch("ability-score", "ability-score", 1, lst("abilities"), increase=[[2], [1, 1]], max=20)],
    "grappler": [ch("ability-score", "ability-score", 1, lst("abilities", ["str", "dex"]), increase=[[1]], max=20)],
    "boon-of-combat-prowess": _boon(),
    "boon-of-dimensional-travel": _boon(),
    "boon-of-fate": _boon(),
    "boon-of-irresistible-offense": _boon(["str", "dex"]),
    "boon-of-spell-recall": _boon(MENTAL),
    "boon-of-the-night-spirit": _boon(),
    "boon-of-truesight": _boon(),
    # Список заклинаний — вариант черты, который называет предыстория («Magic Initiate (Cleric)»).
    "magic-initiate": [
        ch("spell-list", "spell-list", 1, lst("classes", ["cleric", "druid", "wizard"])),
        ch("spellcasting-ability", "spellcasting-ability", 1, lst("abilities", MENTAL)),
        ch("cantrips", "spell", 2, res("spells", **{"class": "@spell-list"}, level=0), "level"),
        ch("spell", "spell", 1, res("spells", **{"class": "@spell-list"}, level=1), "level")],
    "skilled": [ch("proficiencies", "skill", 3, lst("skills-or-tools"))],
}

# --- Варианты классовых умений -------------------------------------------------------------------
CLASS_OPTIONS = {
    "agonizing-blast": [ch("cantrip", "spell", 1, own("known-cantrips", **{"class": "warlock"}, deals="damage"))],
    "eldritch-spear": [ch("cantrip", "spell", 1, own("known-cantrips", **{"class": "warlock"}, deals="damage", min_range=10))],
    "repelling-blast": [ch("cantrip", "spell", 1, own("known-cantrips", **{"class": "warlock"}, requires="attack-roll"))],
    "blessed-warrior": [ch("cantrips", "spell", 2, res("spells", **{"class": "cleric"}, level=0), "level")],
    "druidic-warrior": [ch("cantrips", "spell", 2, res("spells", **{"class": "druid"}, level=0), "level")],
    "lessons-of-the-first-ones": [ch("feat", "feat", 1, res("feats", category="origin"))],
    "pact-of-the-tome": [
        ch("cantrips", "spell", 3, res("spells", level=0), "short-rest"),
        ch("rituals", "spell", 2, res("spells", level=1, ritual=True), "short-rest")],
}


# --- Сборка: объявления → поле `choices` ---------------------------------------------------------
SKILL_SLUGS = ("acrobatics", "animal-handling", "arcana", "athletics", "deception", "history", "insight",
               "intimidation", "investigation", "medicine", "nature", "perception", "performance",
               "persuasion", "religion", "sleight-of-hand", "stealth", "survival")
_LIST_VALUES = {"skills": SKILL_SLUGS, "abilities": ABILITIES, "damage-types": DAMAGE_TYPES,
                "sizes": ("medium", "small")}


def _count(count, cls, where, errors):
    """Число, либо «уровень → всего»: парами из объявления или сменами значения колонки прогрессии."""
    if isinstance(count, int):
        return count
    if isinstance(count, list):
        return [{"level": level, "count": total} for level, total in count]
    column = count[1]
    steps, last = [], None
    for row in (cls or {"progression": {"rows": []}})["progression"]["rows"]:
        value = row["values"].get(column) if isinstance(row["values"], dict) else None
        if value is None or not str(value).isdigit():
            if value not in (None, "—"):
                errors.append(f"{where}: колонка «{column}», уровень {row['level']}: не число {value!r}")
            continue
        if int(value) != last:
            last = int(value)
            steps.append({"level": row["level"], "count": last})
    if not steps:
        errors.append(f"{where}: колонки прогрессии «{column}» у класса нет")
    return steps


def _fill(value, context):
    """Подстановки сборки: "{class}" в строке; значение целиком из контекста — "{class-skills}" и т. п."""
    if isinstance(value, str) and value in context:
        return context[value]
    if isinstance(value, list):
        return [_fill(v, context) for v in value]
    if isinstance(value, dict):
        return {k: _fill(v, context) for k, v in value.items()}
    return value


def _build(declared, context, where, errors, cls=None, levels=None):
    out = []
    for choice in declared:
        built = _fill({k: v for k, v in choice.items() if k != "count"}, context)
        built["count"] = _count(choice["count"], cls, where, errors)
        # Умение, которое класс даёт несколько раз (Ability Score Improvement), — выбор на каждом уровне.
        if levels and len(levels) > 1 and isinstance(built["count"], int):
            built["levels"] = levels
        out.append(built)
    ids = [c["id"] for c in out]
    if len(set(ids)) != len(ids):
        errors.append(f"{where}: повтор id выбора в {ids}")
    return out


def _check(choice, where, known, errors):
    """Ссылки объявления разрешаются: список, ресурс с фильтром, слаги."""
    if choice["kind"] not in KINDS or choice["replace"] not in REPLACE:
        errors.append(f"{where}: вид {choice['kind']!r} или замена {choice['replace']!r} вне словаря")
    for source in [choice["from"]] + ([choice["or"]] if "or" in choice else []):
        if "list" in source:
            allowed = known["classes"] if source["list"] == "classes" else _LIST_VALUES.get(source["list"])
            if source["list"] not in LISTS:
                errors.append(f"{where}: список {source['list']!r} вне словаря")
            elif source["values"] is not None and (not source["values"] or (
                    allowed is not None and [v for v in source["values"] if v not in allowed])):
                errors.append(f"{where}: значения {source['values']} не из списка {source['list']!r}")
        elif "resource" in source:
            resource, flt = source["resource"], source["filter"]
            if resource not in RESOURCES or resource not in known["resources"]:
                errors.append(f"{where}: ресурса {resource!r} нет")
                continue
            for cls in ([flt["class"]] if isinstance(flt.get("class"), str) else flt.get("class", [])):
                if not (cls.startswith("@") or cls in known["classes"]):
                    errors.append(f"{where}: класса {cls!r} нет")
            if resource == "feats" and flt.get("category") not in (None, *known["feat-categories"]):
                errors.append(f"{where}: категории черт {flt['category']!r} нет")
            if resource == "class-options" and (flt.get("class"), flt.get("feature")) not in known["option-groups"]:
                errors.append(f"{where}: группы вариантов {flt.get('class')}/{flt.get('feature')} нет")
            if resource == "subclasses" and flt.get("class") not in known["subclass-classes"]:
                errors.append(f"{where}: подклассов класса {flt.get('class')!r} нет")
            if resource == "species-lineages" and flt.get("species") not in known["lineage-species"]:
                errors.append(f"{where}: наследий вида {flt.get('species')!r} нет")
            if resource == "equipment" and flt.get("group") not in known["equipment"]:
                errors.append(f"{where}: записи снаряжения {flt.get('group')!r} нет")
        elif source.get("character") not in CHARACTER:
            errors.append(f"{where}: источник {source!r} вне словаря")
    suggest = choice.get("suggest", {})
    if "slug" in suggest and suggest["slug"] not in known["feats"]:
        errors.append(f"{where}: черты-подсказки {suggest['slug']!r} нет")
    if "category" in suggest and suggest["category"] not in known["feat-categories"]:
        errors.append(f"{where}: категории-подсказки {suggest['category']!r} нет")


def attach_choices(all_data: dict, ver: str = "srd52") -> list[str]:
    """Пишет `choices` классам и их умениям, подклассам, видам и их особенностям, предысториям, чертам
    и вариантам умений. EN — из объявлений этого файла, RU — копией EN по слагу и позиции."""
    errors: list[str] = []
    en = {res_: all_data.get((ver, "en", res_), []) for res_ in
          ("classes", "subclasses", "species", "species-lineages", "backgrounds", "feats", "class-options",
           "spells", "weapons", "equipment")}
    known = {
        "resources": {name for name, items in en.items() if items},
        "classes": {c["slug"] for c in en["classes"]},
        "feats": {f["slug"] for f in en["feats"]},
        "feat-categories": {f["category"] for f in en["feats"]},
        "option-groups": {(o["class"], o["feature"]["key"]) for o in en["class-options"] if o["selection"] == "learned"},
        "subclass-classes": {s["class"] for s in en["subclasses"]},
        "lineage-species": {l["species"] for l in en["species-lineages"]},
        "equipment": {e["slug"] for e in en["equipment"]},
    }
    used: set = set()

    def put(owner, declared, context, where, cls=None, levels=None):
        owner["choices"] = _build(declared, context, where, errors, cls, levels)
        for choice in owner["choices"]:
            _check(choice, where, known, errors)

    for cls in en["classes"]:
        slug = cls["slug"]
        context = {"{class}": slug, "{class-skills}": cls["proficiencies"]["skills"]["options"]}
        put(cls, CLASSES.get(slug, []), context, f"classes/{slug}")
        used.add(("class", slug))
        for feature in cls["features"]:
            name = feature["name"]
            key = next((k for k in ((slug, name), ("*", name), ("*", "{Class} Subclass"))
                        if k in CLASS_FEATURES and (k[1] != "{Class} Subclass" or name == f"{cls['name']} Subclass")), None)
            levels = [row["level"] for row in cls["progression"]["rows"] if name in row["features"]]
            put(feature, CLASS_FEATURES[key] if key else [], context, f"classes/{slug}/{name}", cls, levels)
            if key:
                used.add(("class-feature", key if key[0] == "*" else (slug, name)))
    for sub in en["subclasses"]:
        lands = sorted({row["choice"]["key"] for row in sub["always_prepared"] if row["choice"]})
        context = {"{class}": sub["class"], "{lands}": lands}
        for feature in sub["features"]:
            key = (sub["slug"], feature["name"])
            put(feature, SUBCLASS_FEATURES.get(key, []), context, f"subclasses/{sub['slug']}/{feature['name']}")
            if key in SUBCLASS_FEATURES:
                used.add(("subclass-feature", key))
    for sp in en["species"]:
        sizes = sp["size"]["options"]
        put(sp, [ch("size", "size", 1, lst("sizes", sizes))] if len(sizes) > 1 else [], {}, f"species/{sp['slug']}")
        for trait in sp["traits"]:
            key = (sp["slug"], trait["name"])
            declared = ([ch("lineage", "lineage", 1, res("species-lineages", species=sp["slug"]))]
                        if trait["lineages"] else []) + SPECIES_TRAITS.get(key, [])
            put(trait, declared, {}, f"species/{sp['slug']}/{trait['name']}")
            if key in SPECIES_TRAITS:
                used.add(("species-trait", key))
    feats = {f["slug"]: f for f in en["feats"]}
    for feat in en["feats"]:
        put(feat, FEATS.get(feat["slug"], []), {}, f"feats/{feat['slug']}")
    for bg in en["backgrounds"]:
        context = {"{abilities}": bg["ability_scores"]["abilities"], "{tool.choose_from}": bg["tool"]["choose_from"]}
        put(bg, BACKGROUND + BACKGROUNDS.get(bg["slug"], []), context, f"backgrounds/{bg['slug']}")
        if bool(bg["tool"]["choose_from"]) != any(c["kind"] == "tool" for c in bg["choices"]):
            errors.append(f"backgrounds/{bg['slug']}: выбор инструмента в тексте и в объявлении расходятся")
        # Вариант черты предыстории — значение выбора «список заклинаний» этой черты.
        variant, feat = bg["feat"]["variant"], feats.get(bg["feat"]["slug"], {})
        lists = [c["from"]["values"] for c in feat.get("choices", []) if c["kind"] == "spell-list"]
        if variant and not any(variant in values for values in lists):
            errors.append(f"backgrounds/{bg['slug']}: варианта черты {variant!r} нет среди выборов «{bg['feat']['slug']}»")
    for option in en["class-options"]:
        put(option, CLASS_OPTIONS.get(option["slug"], []), {}, f"class-options/{option['slug']}")

    declared = ({("class", k) for k in CLASSES} | {("class-feature", k) for k in CLASS_FEATURES}
                | {("subclass-feature", k) for k in SUBCLASS_FEATURES} | {("species-trait", k) for k in SPECIES_TRAITS})
    for kind, key in sorted(declared - used, key=str):
        errors.append(f"объявление без хозяина: {kind} {key}")
    for name, table in (("backgrounds", BACKGROUNDS), ("feats", FEATS), ("class-options", CLASS_OPTIONS)):
        for slug in sorted(set(table) - {e["slug"] for e in en[name]}):
            errors.append(f"объявление без хозяина: {name}/{slug}")

    # RU: те же выборы, что у EN — по слагу записи и по позиции умения или особенности.
    for name, nested in (("classes", "features"), ("subclasses", "features"), ("species", "traits"),
                         ("backgrounds", None), ("feats", None), ("class-options", None)):
        source = {e["slug"]: e for e in en[name]}
        for entity in all_data.get((ver, "ru", name), []):
            origin = source.get(entity["slug"])
            if origin is None or (nested and len(origin[nested]) != len(entity[nested])):
                errors.append(f"ru/{name}/{entity['slug']}: нет пары в EN для выборов")
                continue
            if "choices" in origin:
                entity["choices"] = origin["choices"]
            for item, pair in zip(entity[nested], origin[nested]) if nested else ():
                item["choices"] = pair["choices"]
    return errors
