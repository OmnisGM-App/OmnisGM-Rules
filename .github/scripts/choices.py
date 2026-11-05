"""Объявления выборов SRD 5.2 (#413): что игрок выбирает при сборке персонажа и откуда берутся варианты.

Текст правил объявляет выбор словами («of your choice»), поэтому объявления написаны руками и
прикрепляются к умению класса или подкласса, особенности вида, наследию, предыстории, черте и варианту
умения по EN-имени или слагу. Объявление, которому не нашлось хозяина, и ссылка, которая не разрешилась, роняют сборку.

Выбор при применении (цель, форма области, эффект удара) не объявляется: он не хранится у персонажа.
Стартовое снаряжение «A или B» остаётся текстом.
"""

from parsers.base import slugify
from parsers.classes import ABILITY_CODES, SKILLS
from parsers.equipment import TOOL_TYPES

ABILITIES = tuple(ABILITY_CODES.values())
SKILL_SLUGS = tuple(sorted(slugify(name) for name in SKILLS))
DAMAGE_TYPES = ("acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic", "piercing",
                "poison", "psychic", "radiant", "slashing", "thunder")
KINDS = ("subclass", "feat", "option", "skill", "skill-or-tool", "expertise", "tool", "language", "weapon-mastery",
         "spell", "spell-list", "damage-type", "ability-score", "spellcasting-ability", "lineage", "size", "land")
# Закрытые списки: values — подмножество, null — список целиком.
LISTS = ("skills", "abilities", "damage-types", "sizes", "languages", "tools", "skills-or-tools",
         "artisan-tools-or-musical-instruments", "classes", "lands")
RESOURCES = ("feats", "subclasses", "class-options", "spells", "weapons", "species-lineages", "equipment")
CHARACTER = ("skill-proficiencies", "weapon-proficiencies", "known-cantrips", "spellbook")
# Когда выбор можно заменить — самый ранний момент: `short-rest` значит «на коротком или долгом отдыхе»
# (так в тексте у всех четырёх мест), `long-rest` — только на долгом, `level` — при получении уровня класса.
REPLACE = ("never", "level", "long-rest", "short-rest")

# Словарь фильтра: источник → ключ → какое поле записи он читает. Ключа вне словаря сборка не пропустит.
# Фильтр сужает по данным; условие, которого в данных нет («заговор, наносящий урон»), остаётся в тексте
# хозяина выбора и в фильтр не пишется.
FILTERS = {
    "feats": {"category": "`category`"},
    "subclasses": {"class": "`class`"},
    "class-options": {"class": "`class`", "feature": "`feature.key`"},
    "species-lineages": {"species": "`species`"},
    "weapons": {"type": "`type`: melee | ranged"},
    # Предметы группы (игровой набор → кости, карты…): значение поля `group` предметов `equipment`.
    "equipment": {"group": "`group`"},
    "spells": {
        # Слаг класса, список слагов или "@id" — ответ на выбор с этим id у того же хозяина.
        "class": "`class_slugs`",
        # Число — круг; "slots" — круги, на которые у персонажа есть ячейки; "cantrip-or-slots" — они же и заговоры.
        "level": "`level`",
        "max_level": "`level`, не выше",
        "school": "`school_slug`",
        "ritual": "`casting_time.ritual`",
    },
    "skill-proficiencies": {"values": "слаги навыков, из которых выбирают"},
    "weapon-proficiencies": {},
    "known-cantrips": {"class": "класс, чьи заговоры считаются"},
    "spellbook": {"level": "`level`", "casting_time": "`casting_time.type`"},
}
# Подсказка `suggest` по виду выбора: ресурс, в котором ищется слаг, и слово для ошибки.
SUGGESTED = {"feat": ("feats", "черты"), "spell": ("spells", "заклинания")}
SPELL_LEVELS = ("slots", "cantrip-or-slots")
SCHOOLS = ("abjuration", "conjuration", "divination", "enchantment", "evocation", "illusion", "necromancy",
           "transmutation")


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
    ("*", "Epic Boon"): [ch("feat", "feat", 1, ANY_FEAT, suggest={"slug": "{epic-boon}"})],

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

    ("fighter", "Fighting Style"): [ch("feat", "feat", 1, STYLE, "level", suggest={"slug": "defense"})],
    ("fighter", "Weapon Mastery"): [
        ch("weapons", "weapon-mastery", ("column", "weapon-mastery"), res("weapons"), "long-rest")],

    # «Instead of choosing one of those feats, you can choose the option below» — второй источник в `or`.
    # Замены черты у паладина и следопыта в тексте нет (у воина есть): меняются только заговоры варианта.
    ("paladin", "Fighting Style"): [
        ch("feat", "feat", 1, STYLE, **{"or": res("class-options", **{"class": "paladin"}, feature="fighting-style")})],
    ("paladin", "Weapon Mastery"): [ch("weapons", "weapon-mastery", 2, own("weapon-proficiencies"), "long-rest")],
    ("paladin", "Spellcasting"): [
        ch("prepared", "spell", ("column", "prepared-spells"), res("spells", **{"class": "paladin"}, level="slots"), "long-rest")],

    ("ranger", "Fighting Style"): [
        ch("feat", "feat", 1, STYLE, **{"or": res("class-options", **{"class": "ranger"}, feature="fighting-style")})],
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

# «Boon of … is recommended» в умении Epic Boon каждого класса — подсказка выбора черты.
EPIC_BOON = {
    "barbarian": "boon-of-irresistible-offense", "bard": "boon-of-spell-recall", "cleric": "boon-of-fate",
    "druid": "boon-of-dimensional-travel", "fighter": "boon-of-combat-prowess", "monk": "boon-of-irresistible-offense",
    "paladin": "boon-of-truesight", "ranger": "boon-of-dimensional-travel", "rogue": "boon-of-the-night-spirit",
    "sorcerer": "boon-of-dimensional-travel", "warlock": "boon-of-fate", "wizard": "boon-of-spell-recall",
}

# Владение инструментом из таблицы черт класса — выбор самого класса, не умения.
CLASSES = {
    "bard": [ch("instruments", "tool", 3, res("equipment", group="musical-instrument"))],
    "monk": [ch("tool", "tool", 1, lst("artisan-tools-or-musical-instruments"))],
}
# Инструмент на выбор из строки «As a Multiclass Character» — выбор в `multiclass.choices` класса (#480).
MULTICLASS = {
    "bard": [ch("instrument", "tool", 1, res("equipment", group="musical-instrument"))],
}

# --- Подклассы: умение, которому принадлежит таблица `always_prepared` (Table#817, срез 2d-2) ------
ALWAYS_PREPARED_OWNERS = {
    ("circle-of-the-land", "Circle of the Land Spells"),
    ("draconic-sorcery", "Draconic Spells"),
    ("fiend-patron", "Fiend Spells"),
    ("life-domain", "Life Domain Spells"),
    ("oath-of-devotion", "Oath of Devotion Spells"),
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
    ("human", "Versatile"): [ch("feat", "feat", 1, res("feats", category="origin"), suggest={"slug": "skilled"})],
}

# --- Наследия видов: слаг наследия → выборы (#490). Выбор одного наследия, а не всей особенности вида ---
LINEAGES = {
    # src/dnd/srd-5.2/en/04_CharacterOrigins.md, таблица Elven Lineages, строка High Elf.
    "elf-high-elf": [ch("cantrip", "spell", 1, res("spells", **{"class": "wizard"}, level=0), "long-rest",
                        suggest={"slug": "prestidigitation"})],
}
# Заклинание из grants наследия, которое заменяет выбор этого же наследия: (наследие, заклинание) → id выбора.
# Сборка пишет id в grants.spells[].choice; заклинание-подсказка выбора без такой связи роняет сборку.
LINEAGE_GRANT_CHOICES = {("elf-high-elf", "prestidigitation"): "cantrip"}

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
    "skilled": [ch("proficiencies", "skill-or-tool", 3, lst("skills-or-tools"))],
}

# --- Варианты классовых умений -------------------------------------------------------------------
CLASS_OPTIONS = {
    # Условие заговора («наносит урон», «дальность от 10 футов», «требует броска атаки») — в тексте варианта.
    "agonizing-blast": [ch("cantrip", "spell", 1, own("known-cantrips", **{"class": "warlock"}))],
    "eldritch-spear": [ch("cantrip", "spell", 1, own("known-cantrips", **{"class": "warlock"}))],
    "repelling-blast": [ch("cantrip", "spell", 1, own("known-cantrips", **{"class": "warlock"}))],
    # Лишний заговор сверх колонки прогрессии; меняется как заговоры класса — при получении уровня.
    "thaumaturge": [ch("cantrip", "spell", 1, res("spells", **{"class": "cleric"}, level=0), "level")],
    "magician": [ch("cantrip", "spell", 1, res("spells", **{"class": "druid"}, level=0), "level")],
    "blessed-warrior": [ch("cantrips", "spell", 2, res("spells", **{"class": "cleric"}, level=0), "level")],
    "druidic-warrior": [ch("cantrips", "spell", 2, res("spells", **{"class": "druid"}, level=0), "level")],
    "lessons-of-the-first-ones": [ch("feat", "feat", 1, res("feats", category="origin"))],
    "pact-of-the-tome": [
        ch("cantrips", "spell", 3, res("spells", level=0), "short-rest"),
        ch("rituals", "spell", 2, res("spells", level=1, ritual=True), "short-rest")],
}


# --- Ресурс `choice-lists` (#482): члены каждого списка из LISTS на языке издания --------------------
# Таблица правил → (тип члена, слаг по EN-строке, словарь слагов). Подписи RU — из той же таблицы по строке.
TERM_LISTS = {
    "skills": ("skill", slugify, SKILL_SLUGS),
    "abilities": ("ability", lambda name: ABILITY_CODES.get(name.lower()), ABILITIES),
    "damage-types": ("damage-type", slugify, DAMAGE_TYPES),
    "sizes": ("size", slugify, ("tiny", "small", "medium", "large", "huge", "gargantuan")),
}
# Список из инструментов `equipment`: поле записи → значения, по любому из которых она входит; None — любой инструмент.
TOOL_LISTS = {"tools": None,
              "artisan-tools-or-musical-instruments": {"tool_type": ("artisan-tools",), "group": ("musical-instrument",)}}


def build_choice_lists(all_data: dict) -> list[str]:
    """Пишет ресурсы `languages` (RU — слаг и name_en из EN по строке) и `choice-lists`, забирает внутренний
    `list-terms`. Члены списка — {type, slug, name}; tool — слаг `equipment`, language — `languages`, class — `classes`."""
    errors: list[str] = []
    for ver in sorted({key[0] for key in all_data if key[1:] == ("en", "classes")}):
        en_langs, ru_langs = all_data.get((ver, "en", "languages"), []), all_data.get((ver, "ru", "languages"))
        if ru_langs is not None:
            if [l["category"] for l in ru_langs] != [l["category"] for l in en_langs]:
                errors.append(f"{ver}/ru/languages: строки RU не напротив EN ({len(ru_langs)} против {len(en_langs)})")
            for r, e in zip(ru_langs, en_langs):
                r["slug"], r["name_en"] = e["slug"], e["name"]
        terms = {lang: all_data.pop((ver, lang, "list-terms"), []) for lang in ("en", "ru")}
        en_slugs: dict[str, list] = {}
        for key, (kind, to_slug, known) in TERM_LISTS.items():
            names = [t["name"] for t in terms["en"] if t["list"] == key]
            en_slugs[key] = [to_slug(n) for n in names]
            if sorted(map(str, en_slugs[key])) != sorted(known):
                errors.append(f"{ver}/en/{key}: таблица даёт {en_slugs[key]}, словарь — {sorted(known)}")
        for lang in ("en", "ru"):
            if (ver, lang, "classes") not in all_data:
                continue
            lists = {}
            for key, (kind, _, _) in TERM_LISTS.items():
                names = [t["name"] for t in terms[lang] if t["list"] == key]
                if len(names) != len(en_slugs[key]):
                    errors.append(f"{ver}/{lang}/{key}: строк {len(names)}, в EN {len(en_slugs[key])}")
                lists[key] = [{"type": kind, "slug": slug, "name": name} for slug, name in zip(en_slugs[key], names)]
            tools = [e for e in all_data.get((ver, lang, "equipment"), []) if e["section"] == "tools"]
            types = {e["slug"]: e["tool_type"] for e in all_data.get((ver, "en", "equipment"), [])}
            for e in tools:
                if e["tool_type"] not in (None, *TOOL_TYPES) or e["tool_type"] != types.get(e["slug"]):
                    errors.append(f"{ver}/{lang}/equipment/{e['slug']}: тип инструмента {e['tool_type']!r} вне словаря или ≠ EN")
            for kind in sorted(set(TOOL_TYPES) - {e["tool_type"] for e in tools}):
                errors.append(f"{ver}/{lang}/equipment: у типа инструмента {kind!r} нет предметов")
            for key, match in TOOL_LISTS.items():
                lists[key] = [{"type": "tool", "slug": e["slug"], "name": e["name"]} for e in tools
                              if match is None or any(e[field] in values for field, values in match.items())]
            lists["skills-or-tools"] = lists["skills"] + lists["tools"]
            lists["languages"] = [{"type": "language", "slug": l["slug"], "name": l["name"]}
                                  for l in all_data.get((ver, lang, "languages"), [])]
            lists["classes"] = [{"type": "class", "slug": c["slug"], "name": c["name"]}
                                for c in all_data.get((ver, lang, "classes"), [])]
            lands = {row["choice"]["key"]: row["choice"]["name"] for sub in all_data.get((ver, lang, "subclasses"), [])
                     for row in sub["always_prepared"] if row["choice"]}
            lists["lands"] = [{"type": "land", "slug": slug, "name": name} for slug, name in sorted(lands.items())]
            for key in sorted(set(LISTS) - set(lists)) + sorted(set(lists) - set(LISTS)):
                errors.append(f"{ver}/{lang}/choice-lists: список {key!r} не объявлен в LISTS или не собран")
            for key in sorted(k for k in LISTS if k in lists and not lists[k]):
                errors.append(f"{ver}/{lang}/choice-lists: у списка {key!r} нет членов")
            all_data[(ver, lang, "choice-lists")] = [{"slug": key, "members": lists[key]} for key in LISTS if key in lists]
    return errors


# --- Сборка: объявления → поле `choices` ---------------------------------------------------------


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


def _check_filter(name, flt, where, known, ids, errors):
    """Ключи фильтра — из словаря `FILTERS`, значения разрешаются в данных."""
    for key in sorted(set(flt) - set(FILTERS[name])):
        errors.append(f"{where}: ключа фильтра {key!r} у источника {name!r} нет")
    classes = [flt["class"]] if isinstance(flt.get("class"), str) else flt.get("class", [])
    for cls in classes if name in ("spells", "known-cantrips", "subclasses", "class-options") else ():
        if cls.startswith("@"):
            if cls[1:] not in ids:
                errors.append(f"{where}: ссылка {cls!r} — выбора с таким id у хозяина нет")
        elif cls not in known["classes"]:
            errors.append(f"{where}: класса {cls!r} нет")
    if name in ("spells", "spellbook"):
        level = flt.get("level")
        if level is not None and level not in SPELL_LEVELS and not (isinstance(level, int) and 0 <= level <= 9):
            errors.append(f"{where}: круг заклинания {level!r} вне словаря")
        if flt.get("school") not in (None, *SCHOOLS):
            errors.append(f"{where}: школы {flt['school']!r} нет")
    if name == "skill-proficiencies" and [v for v in flt.get("values", []) if v not in SKILL_SLUGS]:
        errors.append(f"{where}: навыки {flt['values']} не из словаря")
    if name == "feats" and flt.get("category") not in (None, *known["feat-categories"]):
        errors.append(f"{where}: категории черт {flt['category']!r} нет")
    if name == "weapons" and flt.get("type") not in (None, "melee", "ranged"):
        errors.append(f"{where}: типа оружия {flt['type']!r} нет")
    if name == "class-options" and (flt.get("class"), flt.get("feature")) not in known["option-groups"]:
        errors.append(f"{where}: группы вариантов {flt.get('class')}/{flt.get('feature')} нет")
    if name == "subclasses" and flt.get("class") not in known["subclass-classes"]:
        errors.append(f"{where}: подклассов класса {flt.get('class')!r} нет")
    if name == "species-lineages" and flt.get("species") not in known["lineage-species"]:
        errors.append(f"{where}: наследий вида {flt.get('species')!r} нет")
    if name == "equipment" and flt.get("group") not in known["equipment-groups"]:
        errors.append(f"{where}: группы снаряжения {flt.get('group')!r} нет")


def _check(choice, where, known, ids, errors):
    """Ссылки объявления разрешаются: список, ресурс или своё с фильтром, id другого выбора, слаги."""
    if choice["kind"] not in KINDS or choice["replace"] not in REPLACE:
        errors.append(f"{where}: вид {choice['kind']!r} или замена {choice['replace']!r} вне словаря")
    for source in [choice["from"]] + ([choice["or"]] if "or" in choice else []):
        if "list" in source:
            allowed = known["lists"].get(source["list"])
            if source["list"] not in LISTS:
                errors.append(f"{where}: список {source['list']!r} вне словаря")
            elif allowed is None:
                errors.append(f"{where}: списка {source['list']!r} нет в choice-lists")
            elif source["values"] is not None and (not source["values"] or [v for v in source["values"] if v not in allowed]):
                errors.append(f"{where}: значения {source['values']} не из списка {source['list']!r}")
        elif "resource" in source:
            if source["resource"] not in RESOURCES or source["resource"] not in known["resources"]:
                errors.append(f"{where}: ресурса {source['resource']!r} нет")
            else:
                _check_filter(source["resource"], source["filter"], where, known, ids, errors)
        elif source.get("character") not in CHARACTER:
            errors.append(f"{where}: источник {source!r} вне словаря")
        else:
            _check_filter(source["character"], source["filter"], where, known, ids, errors)
    suggest = choice.get("suggest", {})
    if "slug" in suggest and choice["kind"] not in SUGGESTED:
        errors.append(f"{where}: подсказка у выбора вида {choice['kind']!r} не поддерживается")
    elif "slug" in suggest and suggest["slug"] not in known[SUGGESTED[choice["kind"]][0]]:
        errors.append(f"{where}: {SUGGESTED[choice['kind']][1]}-подсказки {suggest['slug']!r} нет")
    if set(suggest) - {"slug"}:
        errors.append(f"{where}: подсказка — только слаг записи, получено {sorted(suggest)}")


def attach_choices(all_data: dict) -> list[str]:
    """Пишет `choices` классам и их умениям, подклассам, видам, их особенностям и наследиям, предысториям,
    чертам и вариантам умений. EN — из объявлений этого файла, RU — копией EN по слагу и позиции.

    Объявления написаны для редакции, у которой есть ресурс классов; остальные версии не трогаются."""
    errors: list[str] = []
    for ver in sorted({key[0] for key in all_data if key[1:] == ("en", "classes")}):
        errors += _attach(all_data, ver)
    return errors


def _attach(all_data: dict, ver: str) -> list[str]:
    errors: list[str] = []
    en = {res_: all_data.get((ver, "en", res_), []) for res_ in
          ("classes", "subclasses", "species", "species-lineages", "backgrounds", "feats", "class-options",
           "spells", "weapons", "equipment", "equipment-groups", "choice-lists")}
    known = {
        "resources": {name for name, items in en.items() if items},
        "classes": {c["slug"] for c in en["classes"]},
        "feats": {f["slug"] for f in en["feats"]},
        "spells": {sp["slug"] for sp in en["spells"]},
        "feat-categories": {f["category"] for f in en["feats"]},
        "option-groups": {(o["class"], o["feature"]["key"]) for o in en["class-options"] if o["selection"] == "learned"},
        "subclass-classes": {s["class"] for s in en["subclasses"]},
        "lineage-species": {l["species"] for l in en["species-lineages"]},
        "equipment-groups": {g["slug"] for g in en["equipment-groups"]},
        "equipment": {e["slug"] for e in en["equipment"]},
        "lists": {lst_["slug"]: {m["slug"] for m in lst_["members"]} for lst_ in en["choice-lists"]},
    }
    used: set = set()

    def put(owner, declared, context, where, cls=None, levels=None):
        owner["choices"] = _build(declared, context, where, errors, cls, levels)
        ids = {choice["id"] for choice in owner["choices"]}
        for choice in owner["choices"]:
            _check(choice, where, known, ids, errors)

    for cls in en["classes"]:
        slug = cls["slug"]
        context = {"{class}": slug, "{class-skills}": cls["proficiencies"]["skills"]["options"],
                   "{epic-boon}": EPIC_BOON.get(slug, "")}
        put(cls, CLASSES.get(slug, []), context, f"classes/{slug}")
        put(cls["multiclass"], MULTICLASS.get(slug, []), context, f"classes/{slug}/multiclass")
        used.add(("class", slug))
        used.add(("multiclass", slug))
        for owner, choices_of in (("proficiencies", cls), ("multiclass", cls["multiclass"])):
            tools = cls[owner]["tools"]
            if tools and tools["slug"] is not None and tools["slug"] not in known["equipment"]:
                errors.append(f"classes/{slug}/{owner}: инструмента {tools['slug']!r} нет в equipment")
            if bool(tools and tools["slug"] is None) != any(c["kind"] == "tool" for c in choices_of["choices"]):
                errors.append(f"classes/{slug}/{owner}: инструмент на выбор в тексте и в объявлении расходятся")
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
        owners = 0
        for feature in sub["features"]:
            key = (sub["slug"], feature["name"])
            put(feature, SUBCLASS_FEATURES.get(key, []), context, f"subclasses/{sub['slug']}/{feature['name']}")
            if key in SUBCLASS_FEATURES:
                used.add(("subclass-feature", key))
            feature["always_prepared"] = key in ALWAYS_PREPARED_OWNERS
            if feature["always_prepared"]:
                owners += 1
                used.add(("always-prepared", key))
        if sub["always_prepared"] and owners != 1:
            errors.append(f"subclasses/{sub['slug']}: у таблицы always_prepared умений-владельцев {owners}, ждали одно")
        if owners and not sub["always_prepared"]:
            errors.append(f"subclasses/{sub['slug']}: умение-владелец объявлено, а таблицы always_prepared нет")
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
    for lineage in en["species-lineages"]:
        where = f"species-lineages/{lineage['slug']}"
        put(lineage, LINEAGES.get(lineage["slug"], []), {}, where)
        ids = {choice["id"] for choice in lineage["choices"]}
        for spell in lineage["grants"]["spells"]:
            spell.pop("choice", None)
            key = (lineage["slug"], spell["slug"])
            if key in LINEAGE_GRANT_CHOICES:
                used.add(("lineage-grant", key))
                if LINEAGE_GRANT_CHOICES[key] in ids:
                    spell["choice"] = LINEAGE_GRANT_CHOICES[key]
                else:
                    errors.append(f"{where}: заклинание {spell['slug']!r} связано с выбором "
                                  f"{LINEAGE_GRANT_CHOICES[key]!r}, а такого выбора у наследия нет")
        for choice in lineage["choices"]:
            hint = choice.get("suggest", {}).get("slug")
            if any(sp["slug"] == hint and sp.get("choice") != choice["id"] for sp in lineage["grants"]["spells"]):
                errors.append(f"{where}: заклинание {hint!r} в grants — подсказка выбора {choice['id']!r}, а связи choice нет")
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
        if variant and not any(variant in (values if values is not None else known["classes"]) for values in lists):
            errors.append(f"backgrounds/{bg['slug']}: варианта черты {variant!r} нет среди выборов «{bg['feat']['slug']}»")
    for option in en["class-options"]:
        put(option, CLASS_OPTIONS.get(option["slug"], []), {}, f"class-options/{option['slug']}")

    declared = ({("class", k) for k in CLASSES} | {("multiclass", k) for k in MULTICLASS}
                | {("class-feature", k) for k in CLASS_FEATURES}
                | {("subclass-feature", k) for k in SUBCLASS_FEATURES} | {("species-trait", k) for k in SPECIES_TRAITS}
                | {("always-prepared", k) for k in ALWAYS_PREPARED_OWNERS}
                | {("lineage-grant", k) for k in LINEAGE_GRANT_CHOICES})
    for kind, key in sorted(declared - used, key=str):
        errors.append(f"объявление без хозяина: {kind} {key}")
    for name, table in (("backgrounds", BACKGROUNDS), ("feats", FEATS), ("class-options", CLASS_OPTIONS),
                        ("species-lineages", LINEAGES)):
        for slug in sorted(set(table) - {e["slug"] for e in en[name]}):
            errors.append(f"объявление без хозяина: {name}/{slug}")

    # RU: те же выборы, что у EN — по слагу записи и по позиции умения или особенности.
    for name, nested in (("classes", "features"), ("subclasses", "features"), ("species", "traits"),
                         ("backgrounds", None), ("feats", None), ("class-options", None), ("species-lineages", None)):
        source = {e["slug"]: e for e in en[name]}
        for entity in all_data.get((ver, "ru", name), []):
            origin = source.get(entity["slug"])
            if origin is None or (nested and len(origin[nested]) != len(entity[nested])):
                errors.append(f"ru/{name}/{entity['slug']}: нет пары в EN для выборов")
                continue
            if "choices" in origin:
                entity["choices"] = origin["choices"]
            if name == "classes":
                entity["multiclass"]["choices"] = origin["multiclass"]["choices"]
            if name == "species-lineages":
                for spell, pair in zip(entity["grants"]["spells"], origin["grants"]["spells"]):
                    spell.pop("choice", None)
                    if "choice" in pair:
                        spell["choice"] = pair["choice"]
            for item, pair in zip(entity[nested], origin[nested]) if nested else ():
                item["choices"] = pair["choices"]
                if "always_prepared" in pair:
                    item["always_prepared"] = pair["always_prepared"]
    return errors
