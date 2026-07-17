"""Configuration for D&D SRD API generation."""

SOURCES = [
    # SRD 5.2 RU
    {"ver": "srd52", "lang": "ru", "type": "spell",      "file": "srd-5.2/ru/07_Spells.md",       "h": 3},
    {"ver": "srd52", "lang": "ru", "type": "monster",     "file": "srd-5.2/ru/12_MonstersA-Z.md",  "h": 3},
    {"ver": "srd52", "lang": "ru", "type": "magic_item",  "file": "srd-5.2/ru/10_MagicItems.md",   "h": 4, "after": "## Магические предметы от А до Я"},
    {"ver": "srd52", "lang": "ru", "type": "monster",     "file": "srd-5.2/ru/13_Animals.md",      "h": 3, "out": "animals"},
    {"ver": "srd52", "lang": "ru", "type": "weapon",      "file": "srd-5.2/ru/06_Equipment.md",    "h": 0},
    {"ver": "srd52", "lang": "ru", "type": "armor",       "file": "srd-5.2/ru/06_Equipment.md",    "h": 0},
    {"ver": "srd52", "lang": "ru", "type": "equipment",   "file": "srd-5.2/ru/06_Equipment.md",    "h": 4, "after": "## Инструменты"},
    {"ver": "srd52", "lang": "ru", "type": "condition",   "file": "srd-5.2/ru/08_RulesGlossary.md","h": 4},
    {"ver": "srd52", "lang": "ru", "type": "feat",        "file": "srd-5.2/ru/05_Feats.md",        "h": 4, "after": "## Описания черт"},
    {"ver": "srd52", "lang": "ru", "type": "glossary_defs","file": "srd-5.2/ru/06_Equipment.md",   "section": "Свойства",         "out": "weapon-properties"},
    {"ver": "srd52", "lang": "ru", "type": "glossary_defs","file": "srd-5.2/ru/06_Equipment.md",   "section": "Свойства мастерства", "out": "masteries"},
    {"ver": "srd52", "lang": "ru", "type": "tagged_defs",  "file": "srd-5.2/ru/08_RulesGlossary.md","tags": ["Действие"],           "out": "actions"},
    {"ver": "srd52", "lang": "ru", "type": "untagged_defs","file": "srd-5.2/ru/08_RulesGlossary.md","out": "rules-terms"},
    {"ver": "srd52", "lang": "ru", "type": "tagged_defs",  "file": "srd-5.2/ru/08_RulesGlossary.md","tags": ["Область воздействия"], "out": "areas-of-effect"},
    # SRD 5.2 EN
    {"ver": "srd52", "lang": "en", "type": "spell",      "file": "srd-5.2/en/07_Spells.md",       "h": 3},
    {"ver": "srd52", "lang": "en", "type": "monster",     "file": "srd-5.2/en/12_MonstersA-Z.md",  "h": 3},
    {"ver": "srd52", "lang": "en", "type": "magic_item",  "file": "srd-5.2/en/10_MagicItems.md",   "h": 4, "after": "## Magic Items A\u2013Z"},
    {"ver": "srd52", "lang": "en", "type": "monster",     "file": "srd-5.2/en/13_Animals.md",      "h": 3, "out": "animals"},
    {"ver": "srd52", "lang": "en", "type": "weapon",      "file": "srd-5.2/en/06_Equipment.md",    "h": 0},
    {"ver": "srd52", "lang": "en", "type": "armor",       "file": "srd-5.2/en/06_Equipment.md",    "h": 0},
    {"ver": "srd52", "lang": "en", "type": "equipment",   "file": "srd-5.2/en/06_Equipment.md",    "h": 4, "after": "## Tools"},
    {"ver": "srd52", "lang": "en", "type": "condition",   "file": "srd-5.2/en/08_RulesGlossary.md","h": 4},
    {"ver": "srd52", "lang": "en", "type": "feat",        "file": "srd-5.2/en/05_Feats.md",        "h": 4, "after": "## Feat Descriptions"},
    {"ver": "srd52", "lang": "en", "type": "glossary_defs","file": "srd-5.2/en/06_Equipment.md",   "section": "Properties",          "out": "weapon-properties"},
    {"ver": "srd52", "lang": "en", "type": "glossary_defs","file": "srd-5.2/en/06_Equipment.md",   "section": "Mastery Properties",  "out": "masteries"},
    {"ver": "srd52", "lang": "en", "type": "tagged_defs",  "file": "srd-5.2/en/08_RulesGlossary.md","tags": ["Action"],             "out": "actions"},
    {"ver": "srd52", "lang": "en", "type": "untagged_defs","file": "srd-5.2/en/08_RulesGlossary.md","out": "rules-terms"},
    {"ver": "srd52", "lang": "en", "type": "tagged_defs",  "file": "srd-5.2/en/08_RulesGlossary.md","tags": ["Area of Effect"], "out": "areas-of-effect"},
    # SRD 5.1 RU
    {"ver": "srd51", "lang": "ru", "type": "spell",      "file": "srd-5.1/ru/10_Spells.md",       "h": 3},
    {"ver": "srd51", "lang": "ru", "type": "monster",     "file": "srd-5.1/ru/15_MonstersA-Z.md",  "h": 3},
    {"ver": "srd51", "lang": "ru", "type": "magic_item",  "file": "srd-5.1/ru/13_MagicItems.md",   "h": 4},
    {"ver": "srd51", "lang": "ru", "type": "weapon",      "file": "srd-5.1/ru/09_Equipment.md",    "h": 0},
    {"ver": "srd51", "lang": "ru", "type": "armor",       "file": "srd-5.1/ru/09_Equipment.md",    "h": 0},
    {"ver": "srd51", "lang": "ru", "type": "equipment",  "file": "srd-5.1/ru/09_Equipment.md",    "h": 0},
    {"ver": "srd51", "lang": "ru", "type": "condition",   "file": "srd-5.1/ru/11_Conditions.md",   "h": 4},
    {"ver": "srd51", "lang": "ru", "type": "feat",        "file": "srd-5.1/ru/08_Feats.md",        "h": 4},
    {"ver": "srd51", "lang": "ru", "type": "race",        "file": "srd-5.1/ru/04_Races.md",        "h": 2},
    # SRD 5.1 EN
    {"ver": "srd51", "lang": "en", "type": "spell",      "file": "srd-5.1/en/10_Spells.md",       "h": 3},
    {"ver": "srd51", "lang": "en", "type": "monster",     "file": "srd-5.1/en/15_MonstersA-Z.md",  "h": 3},
    {"ver": "srd51", "lang": "en", "type": "magic_item",  "file": "srd-5.1/en/13_MagicItems.md",   "h": 4},
    {"ver": "srd51", "lang": "en", "type": "weapon",      "file": "srd-5.1/en/09_Equipment.md",    "h": 0},
    {"ver": "srd51", "lang": "en", "type": "armor",       "file": "srd-5.1/en/09_Equipment.md",    "h": 0},
    {"ver": "srd51", "lang": "en", "type": "equipment",  "file": "srd-5.1/en/09_Equipment.md",    "h": 0},
    {"ver": "srd51", "lang": "en", "type": "condition",   "file": "srd-5.1/en/11_Conditions.md",   "h": 4},
    {"ver": "srd51", "lang": "en", "type": "feat",        "file": "srd-5.1/en/08_Feats.md",        "h": 4},
    {"ver": "srd51", "lang": "en", "type": "race",        "file": "srd-5.1/en/04_Races.md",        "h": 2},
]

# Heading patterns that are NOT entity entries (section headers, rules text, etc.)
# Used to filter out non-entity headings from spell/monster/magic_item files.
SKIP_HEADINGS_SPELL = {
    # EN SRD 5.2
    "Preparing Spells", "Always-Prepared Spells", "Spell Level",
    "School of Magic", "Class Spell Lists", "Casting Time", "Range",
    "Components", "Duration", "Effects", "Gaining Spells",
    # EN SRD 5.1
    "Spell Level", "Known and Prepared Spells", "Spell Slots",
    "Casting Time", "Spell Range", "Components", "Duration",
    "Targets", "Areas of Effect", "Spell Saving Throws",
    "Spell Attack Rolls", "Combining Magical Effects",
    # RU SRD 5.2
    "Подготовка заклинаний", "Всегда подготовленные заклинания",
    "Уровень заклинания", "Школа магии", "Списки заклинаний классов",
    "Время накладывания", "Дистанция", "Компоненты", "Длительность",
    "Эффекты", "Получение заклинаний",
    # RU SRD 5.1
    "Уровень заклинания", "Известные и подготовленные заклинания",
    "Ячейки заклинаний", "Время накладывания", "Дистанция заклинания",
    "Компоненты", "Длительность", "Цели", "Области воздействия",
    "Спасброски от заклинаний", "Броски атаки заклинаниями",
    "Комбинирование магических эффектов",
}

SKIP_HEADINGS_MONSTER = {
    "Customizing NPCs", "Настройка НИП",
}

# Equipment: non-item #### headings (weapon/armor properties, rules, etc.)
SKIP_HEADINGS_EQUIPMENT = {
    # EN — weapon properties
    "Ammunition", "Finesse", "Heavy", "Light", "Loading", "Range", "Reach",
    "Thrown", "Two-Handed", "Versatile",
    # EN — mastery properties
    "Cleave", "Graze", "Nick", "Push", "Sap", "Slow", "Topple", "Vex",
    # EN — armor rules
    "Light, Medium, or Heavy Armor", "Shield",
    # EN — vehicle/mount rules
    "Speed", "Crew", "Passengers", "Damage Threshold", "Ship Repair",
    # EN — magic item rules
    "Attune during a Short Rest", "No More Than Three Items",
    "Ending Attunement", "Multiple Items of the Same Kind", "Paired Items",
    # RU — weapon properties
    "Боеприпас", "Фехтовальное", "Тяжёлое", "Лёгкое", "Перезарядка",
    "Дистанция", "Досягаемость", "Метательное", "Двуручное", "Универсальное",
    # RU — mastery properties
    "Рассечение", "Скольжение", "Порез", "Толчок", "Оглушение",
    "Замедление", "Опрокидывание", "Досаждение",
    # RU — armor rules
    "Лёгкие, средние или тяжёлые доспехи", "Щит",
    # RU — vehicle/mount rules
    "Скорость", "Экипаж", "Пассажиры", "Порог урона", "Ремонт корабля",
    # RU — magic item rules
    "Настройка во время короткого отдыха", "Не более трёх предметов",
    "Окончание настройки", "Несколько предметов одного вида", "Парные предметы",
}

# Feat: non-feat #### headings inside feat files
SKIP_HEADINGS_FEAT = {
    # EN — parts of feat description
    "Parts of a Feat",
    # RU
    "Составляющие черты",
}

# Resource type to output directory name mapping
RESOURCE_DIR = {
    "spell": "spells",
    "monster": "monsters",
    "magic_item": "magic-items",
    "weapon": "weapons",
    "armor": "armor",
    "equipment": "equipment",
    "condition": "conditions",
    "feat": "feats",
    "race": "races",
}
