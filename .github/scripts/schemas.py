"""JSON Schema definitions for D&D SRD API entities.

Schemas follow JSON Schema Draft 7 (subset supported by the ``jsonschema`` library).
Each schema describes a single entity object produced by the corresponding parser.
"""

# -- Shared sub-schemas -------------------------------------------------------

_SECTION_ENTRY = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "text_md": {"type": "string"},
    },
    "required": ["name", "text_md"],
    "additionalProperties": False,
}

_ABILITY = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "mod": {"type": "integer"},
        "save": {"type": "integer"},
    },
    "required": ["score", "mod", "save"],
    "additionalProperties": False,
}

# -- Spell schema --------------------------------------------------------------

SPELL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Spell",
    "type": "object",
    "properties": {
        "slug": {"type": "string"},
        "name": {"type": "string"},
        "name_en": {"type": ["string", "null"]},
        "level": {"type": "integer", "minimum": 0, "maximum": 9},
        "school": {
            "type": "string",
            "enum": [
                "Abjuration", "Conjuration", "Divination", "Enchantment",
                "Evocation", "Illusion", "Necromancy", "Transmutation",
                # RU SRD 5.1 genitive forms (not mapped by parser)
                "Ограждения", "Вызова", "Прорицания", "Очарования",
                "Воплощения", "Иллюзии", "Некромантии", "Преобразования",
            ],
        },
        "classes": {
            "type": "array",
            "items": {"type": "string"},
        },
        "subclasses": {
            "type": "array",
            "items": {"type": "string"},
        },
        "casting_time": {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": ["action", "bonus_action", "reaction", "minute", "hour", "special"],
                },
                "ritual": {"type": "boolean"},
                "condition": {"type": ["string", "null"]},
            },
            "required": ["value", "type", "ritual", "condition"],
            "additionalProperties": False,
        },
        "range": {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": ["self", "touch", "sight", "unlimited", "distance", "special"],
                },
                "distance_ft": {"type": ["integer", "null"]},
                "shape": {
                    "anyOf": [
                        {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["cone", "line", "cube", "sphere", "hemisphere"],
                                },
                                "size_ft": {"type": "integer"},
                            },
                            "required": ["type", "size_ft"],
                            "additionalProperties": False,
                        },
                        {"type": "null"},
                    ],
                },
            },
            "required": ["value", "type", "distance_ft", "shape"],
            "additionalProperties": False,
        },
        "components": {
            "type": "object",
            "properties": {
                "verbal": {"type": "boolean"},
                "somatic": {"type": "boolean"},
                "material": {"type": "boolean"},
                "material_desc": {"type": ["string", "null"]},
                "material_cost_gp": {"type": ["number", "null"]},
                "material_consumed": {"type": "boolean"},
            },
            "required": ["verbal", "somatic", "material", "material_desc",
                         "material_cost_gp", "material_consumed"],
            "additionalProperties": False,
        },
        "duration": {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": ["instantaneous", "timed", "until_dispelled", "special"],
                },
                "concentration": {"type": "boolean"},
            },
            "required": ["value", "type", "concentration"],
            "additionalProperties": False,
        },
        # Область эффекта (форма из EN-описания; null — у заклинания нет измеренной AoE).
        "area": {
            "type": ["object", "null"],
            "properties": {
                "shape": {
                    "type": "string",
                    "enum": ["cone", "cube", "cylinder", "emanation", "line", "sphere"],
                },
                "size_ft": {"type": "integer"},
                "radius": {"type": "boolean"},
            },
            "required": ["shape", "size_ft", "radius"],
            "additionalProperties": False,
        },
        "description_md": {"type": ["string", "null"]},
        "higher_levels_md": {"type": ["string", "null"]},
        "cantrip_upgrade_md": {"type": ["string", "null"]},
        "has_stat_block": {"type": "boolean"},
    },
    "required": [
        "slug", "name", "name_en", "level", "school", "classes",
        "casting_time", "range", "components", "duration", "area",
        "description_md", "higher_levels_md", "cantrip_upgrade_md", "has_stat_block",
    ],
    "additionalProperties": False,
}

# -- Monster / Animal schema ---------------------------------------------------

MONSTER_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Monster",
    "type": "object",
    "properties": {
        "slug": {"type": "string"},
        "name": {"type": "string"},
        "name_en": {"type": ["string", "null"]},
        "size": {"type": "string"},
        "type": {"type": "string"},
        "subtype": {"type": ["string", "null"]},
        "alignment": {"type": ["string", "null"]},
        "ac": {
            "type": "object",
            "properties": {
                "value": {"type": "integer"},
                "source": {"type": ["string", "null"]},
            },
            "required": ["value", "source"],
            "additionalProperties": False,
        },
        "hp": {
            "type": "object",
            "properties": {
                "average": {"type": "integer"},
                "formula": {"type": "string"},
            },
            "required": ["average", "formula"],
            "additionalProperties": False,
        },
        "speed": {
            "type": "object",
            "properties": {
                "walk": {"type": ["integer", "null"]},
                "swim": {"type": ["integer", "null"]},
                "fly": {"type": ["integer", "null"]},
                "burrow": {"type": ["integer", "null"]},
                "climb": {"type": ["integer", "null"]},
                "hover": {"type": "boolean"},
                "raw": {"type": "string"},
            },
            "required": ["walk", "swim", "fly", "burrow", "climb", "hover", "raw"],
            "additionalProperties": False,
        },
        "initiative": {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {
                        "mod": {"type": "integer"},
                        "score": {"type": "integer"},
                    },
                    "required": ["mod", "score"],
                    "additionalProperties": False,
                },
                {"type": "null"},
            ],
        },
        "abilities": {
            "type": "object",
            "properties": {
                "str": _ABILITY, "dex": _ABILITY, "con": _ABILITY,
                "int": _ABILITY, "wis": _ABILITY, "cha": _ABILITY,
            },
            "additionalProperties": False,
        },
        "saving_throws": {"type": "array", "items": {"type": "string"}},
        "skills": {"type": "array", "items": {"type": "string"}},
        "damage_resistances": {"type": "array", "items": {"type": "string"}},
        "damage_immunities": {"type": "array", "items": {"type": "string"}},
        "damage_vulnerabilities": {"type": "array", "items": {"type": "string"}},
        "condition_immunities": {"type": "array", "items": {"type": "string"}},
        "senses": {
            "type": "object",
            "properties": {
                "darkvision_ft": {"type": ["integer", "null"]},
                "blindsight_ft": {"type": ["integer", "null"]},
                "tremorsense_ft": {"type": ["integer", "null"]},
                "truesight_ft": {"type": ["integer", "null"]},
                "passive_perception": {"type": ["integer", "null"]},
                "raw": {"type": "string"},
            },
            "required": ["darkvision_ft", "blindsight_ft", "tremorsense_ft",
                         "truesight_ft", "passive_perception", "raw"],
            "additionalProperties": False,
        },
        "languages": {"type": ["string", "null"]},
        "cr": {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
                "xp": {"type": "integer"},
                "proficiency_bonus": {"type": ["integer", "null"]},
            },
            "required": ["value", "xp", "proficiency_bonus"],
            "additionalProperties": False,
        },
        "traits_md": {"type": "array", "items": _SECTION_ENTRY},
        "actions_md": {"type": "array", "items": _SECTION_ENTRY},
        "legendary_actions_md": {"type": "array", "items": _SECTION_ENTRY},
        "reactions_md": {"type": "array", "items": _SECTION_ENTRY},
        "bonus_actions_md": {"type": "array", "items": _SECTION_ENTRY},
        "lair_actions_md": {"type": ["string", "null"]},
        "spells": {"type": "array", "items": {"type": "string"}},
        "group": {"type": "string"},
    },
    "required": [
        "slug", "name", "name_en", "size", "type", "subtype", "alignment",
        "ac", "hp", "speed", "initiative", "abilities",
        "saving_throws", "skills", "damage_resistances", "damage_immunities",
        "condition_immunities", "senses", "languages", "cr",
        "traits_md", "actions_md", "legendary_actions_md",
        "reactions_md", "bonus_actions_md", "lair_actions_md",
        "spells", "group",
    ],
    "additionalProperties": False,
}

# -- Magic Item schema ---------------------------------------------------------

MAGIC_ITEM_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Magic Item",
    "type": "object",
    "properties": {
        "slug": {"type": "string"},
        "name": {"type": "string"},
        "name_en": {"type": ["string", "null"]},
        "type": {"type": "string"},
        "subtype": {"type": ["string", "null"]},
        "rarity": {
            "anyOf": [
                {
                    "type": "string",
                    "enum": ["common", "uncommon", "rare", "very rare",
                             "legendary", "artifact"],
                },
                {"type": "null"},
            ],
        },
        "attunement": {
            "type": "object",
            "properties": {
                "required": {"type": "boolean"},
                "condition": {"type": ["string", "null"]},
            },
            "required": ["required", "condition"],
            "additionalProperties": False,
        },
        "description_md": {"type": "string"},
        "spells": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "slug", "name", "name_en", "type", "subtype", "rarity",
        "attunement", "description_md", "spells",
    ],
    "additionalProperties": False,
}

# -- Weapon schema -------------------------------------------------------------

WEAPON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Weapon",
    "type": "object",
    "properties": {
        "slug": {"type": "string"},
        "name": {"type": "string"},
        "name_en": {"type": ["string", "null"]},
        "category": {"type": "string", "enum": ["simple", "martial"]},
        "type": {"type": "string", "enum": ["melee", "ranged"]},
        "damage_dice": {"type": "string"},
        "damage_type": {"type": ["string", "null"]},
        "properties": {"type": "array", "items": {"type": "string"}},
        "mastery": {"type": ["string", "null"]},
        "range_normal": {"type": ["integer", "null"]},
        "range_long": {"type": ["integer", "null"]},
        "weight": {"type": ["string", "null"]},
        "cost": {"type": "string"},
    },
    "required": [
        "slug", "name", "name_en", "category", "type",
        "damage_dice", "damage_type", "properties", "mastery",
        "range_normal", "range_long", "weight", "cost",
    ],
    "additionalProperties": False,
}

# -- Armor schema --------------------------------------------------------------

ARMOR_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Armor",
    "type": "object",
    "properties": {
        "slug": {"type": "string"},
        "name": {"type": "string"},
        "name_en": {"type": ["string", "null"]},
        "category": {
            "type": "string",
            "enum": ["light", "medium", "heavy", "shield"],
        },
        "ac_base": {"type": "integer"},
        "ac_dex_bonus": {"type": "boolean"},
        "ac_max_dex": {"type": ["integer", "null"]},
        "strength_req": {"type": ["integer", "null"]},
        "stealth_disadvantage": {"type": "boolean"},
        "weight": {"type": ["string", "null"]},
        "cost": {"type": "string"},
    },
    "required": [
        "slug", "name", "name_en", "category",
        "ac_base", "ac_dex_bonus", "ac_max_dex",
        "strength_req", "stealth_disadvantage", "weight", "cost",
    ],
    "additionalProperties": False,
}

# -- Equipment schema ----------------------------------------------------------

EQUIPMENT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Equipment",
    "type": "object",
    "properties": {
        "slug": {"type": "string"},
        "name": {"type": "string"},
        "name_en": {"type": ["string", "null"]},
        "section": {"type": "string", "enum": ["tools", "adventuring_gear"]},
        "cost": {"type": ["string", "null"]},
        "weight": {"type": ["string", "null"]},
        "ability": {"type": ["string", "null"]},
        "utilize": {"type": ["string", "null"]},
        "craft": {"type": "array", "items": {"type": "string"}},
        "variants": {"type": ["string", "null"]},
        "description_md": {"type": "string"},
    },
    "required": [
        "slug", "name", "name_en", "section", "cost", "weight",
        "ability", "utilize", "craft", "variants", "description_md",
    ],
    "additionalProperties": False,
}

# -- Condition schema ----------------------------------------------------------

CONDITION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Condition",
    "type": "object",
    "properties": {
        "slug": {"type": "string"},
        "name": {"type": "string"},
        "name_en": {"type": ["string", "null"]},
        "description_md": {"type": "string"},
    },
    "required": ["slug", "name", "name_en", "description_md"],
    "additionalProperties": False,
}

# -- Feat schema ---------------------------------------------------------------

FEAT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Feat",
    "type": "object",
    "properties": {
        "slug": {"type": "string"},
        "name": {"type": "string"},
        "name_en": {"type": ["string", "null"]},
        "category": {"type": ["string", "null"]},
        "prerequisite": {"type": ["string", "null"]},
        "repeatable": {"type": "boolean"},
        "benefits": {"type": "array", "items": _SECTION_ENTRY},
        "description_md": {"type": "string"},
    },
    "required": [
        "slug", "name", "name_en", "category", "prerequisite",
        "repeatable", "benefits", "description_md",
    ],
    "additionalProperties": False,
}

# -- Daggerheart schemas -------------------------------------------------------
# Имена ресурсов DH (ancestries/communities/domain-cards/adversaries/environments)
# не пересекаются с D&D → схемы применяются только к Daggerheart. rules-terms НЕ
# схемируем (коллизия имени с D&D untagged-defs; у прозаических ресурсов схем нет —
# как у D&D actions/rules-terms/weapon-properties).

# Плоская именованная секция с прозаическим телом (ancestries, communities).
DH_SECTION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Daggerheart Section",
    "type": "object",
    "properties": {
        "slug": {"type": "string"},
        "name": {"type": "string"},
        "name_en": {"type": ["string", "null"]},
        "description_md": {"type": "string"},
    },
    "required": ["slug", "name", "name_en", "description_md"],
    "additionalProperties": False,
}

# Доменная карта. level/recall_cost — обязательные integer (НЕ null): ловит дрейф
# парсинга мета-строки «**_Level N_** _…._ **_Recall Cost_** _M._» (нит ревью #147).
DH_DOMAIN_CARD_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Daggerheart Domain Card",
    "type": "object",
    "properties": {
        "slug": {"type": "string"},
        "name": {"type": "string"},
        "name_en": {"type": ["string", "null"]},
        "domain": {"type": "string"},
        "domain_en": {"type": "string"},
        "domain_slug": {"type": "string"},
        "level": {"type": "integer", "minimum": 1, "maximum": 10},
        "recall_cost": {"type": "integer", "minimum": 0},
        "card_type": {"type": ["string", "null"]},
        "description_md": {"type": "string"},
    },
    "required": [
        "slug", "name", "name_en", "domain", "domain_en", "domain_slug",
        "level", "recall_cost", "card_type", "description_md",
    ],
    "additionalProperties": False,
}

# Стат-блок по тиру (adversaries, environments).
DH_STATBLOCK_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Daggerheart Stat Block",
    "type": "object",
    "properties": {
        "slug": {"type": "string"},
        "name": {"type": "string"},
        "name_en": {"type": ["string", "null"]},
        "tier": {"type": "integer", "minimum": 1, "maximum": 4},
        # Тип противника (Solo/Bruiser/Minion/…) — локализованное слово; только у adversaries.
        "type": {"type": ["string", "null"]},
        "description_md": {"type": "string"},
    },
    "required": ["slug", "name", "name_en", "tier", "description_md"],
    "additionalProperties": False,
}

# -- Basic Roleplaying (BRP) schemas ------------------------------------------
# Имена ресурсов (skills/professions/spot-rules) не пересекаются с D&D/DH.

BRP_SKILL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "BRP Skill",
    "type": "object",
    "properties": {
        "slug": {"type": "string"},
        "name": {"type": "string"},
        "name_en": {"type": ["string", "null"]},
        "base_chance": {"type": "string"},
        "category": {"type": "string"},
        "category_en": {"type": "string"},
        "category_slug": {"type": "string"},
        "description_md": {"type": "string"},
    },
    "required": [
        "slug", "name", "name_en", "base_chance", "category",
        "category_en", "category_slug", "description_md",
    ],
    "additionalProperties": False,
}

# Плоская именованная секция BRP с прозаическим телом (professions, spot-rules).
BRP_SECTION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "BRP Section",
    "type": "object",
    "properties": {
        "slug": {"type": "string"},
        "name": {"type": "string"},
        "name_en": {"type": ["string", "null"]},
        "description_md": {"type": "string"},
    },
    "required": ["slug", "name", "name_en", "description_md"],
    "additionalProperties": False,
}

# -- Mapping resource name → schema (used by generate_api.py) -----------------

RESOURCE_SCHEMAS = {
    "spells": SPELL_SCHEMA,
    "monsters": MONSTER_SCHEMA,
    "magic-items": MAGIC_ITEM_SCHEMA,
    "animals": MONSTER_SCHEMA,
    "weapons": WEAPON_SCHEMA,
    "armor": ARMOR_SCHEMA,
    "equipment": EQUIPMENT_SCHEMA,
    "conditions": CONDITION_SCHEMA,
    "feats": FEAT_SCHEMA,
    # Daggerheart (имена не пересекаются с D&D).
    "ancestries": DH_SECTION_SCHEMA,
    "communities": DH_SECTION_SCHEMA,
    "domain-cards": DH_DOMAIN_CARD_SCHEMA,
    "adversaries": DH_STATBLOCK_SCHEMA,
    "environments": DH_STATBLOCK_SCHEMA,
    # BRP (имена не пересекаются с D&D/DH).
    "skills": BRP_SKILL_SCHEMA,
    "professions": BRP_SECTION_SCHEMA,
    "spot-rules": BRP_SECTION_SCHEMA,
}
