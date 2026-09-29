#!/usr/bin/env python3
"""
Complete fresh re-translation from EN.
Keeps the intro (lines 0-228) from the already-translated RU.
Re-translates lines 229+ from EN with comprehensive body translation.
"""
import re, sys

EN_FILE = "/Users/petrradilov/Documents/srd/dndsrd5.2_markdown/src/dnd/srd-5.1/en/10_Spells.md"
RU_FILE = "/Users/petrradilov/Documents/srd/dndsrd5.2_markdown/src/dnd/srd-5.1/ru/10_Spells.md"

with open(EN_FILE, "r", encoding="utf-8") as f:
    en_lines = f.read().split('\n')

with open(RU_FILE, "r", encoding="utf-8") as f:
    ru_lines = f.read().split('\n')

N = len(en_lines)
assert len(ru_lines) == N, f"Line mismatch: EN={N}, RU={len(ru_lines)}"

# Keep intro (lines 0-228) from the already-translated RU file
# Only process spell body lines (229+)

# Big phrase dictionary for full sentence translation
# Ordered by length (longest first) to avoid partial matches
PHRASES = [
    # Very common patterns in spell descriptions - longest first
    ("When you cast this spell using a spell slot of", "Если вы сотворяете это заклинание, используя ячейку заклинания"),
    ("or higher, you can target one additional creature for each slot level above", "или выше, вы можете нацелиться на одно дополнительное существо за каждый уровень ячейки выше"),
    ("or higher, the damage increases by", "или выше, урон увеличивается на"),
    ("for each slot level above", "за каждый уровень ячейки выше"),
    ("each slot level above", "каждый уровень ячейки выше"),
    ("This spell's damage increases by", "Урон этого заклинания увеличивается на"),
    ("The spell creates more than one beam when you reach higher levels:", "Заклинание создаёт более одного луча, когда вы достигаете более высоких уровней:"),
    ("two beams at", "два луча на"),
    ("three beams at", "три луча на"),
    ("four beams at", "четыре луча на"),
    ("when you reach", "когда вы достигаете"),
    ("You can direct the beams at the same target or at different ones.", "Вы можете направить лучи в одну и ту же цель или в разные."),
    ("Make a separate attack roll for each beam.", "Совершите отдельный бросок атаки для каждого луча."),

    # Opening patterns
    ("You hurl a bubble of acid.", "Вы швыряете пузырёк кислоты."),
    ("Choose one creature you can see within range, or choose two creatures you can see within range that are within", "Выберите одно существо, которое видите в пределах дистанции, или выберите два существа, которые видите в пределах дистанции и которые находятся в пределах"),
    ("of each other.", "друг от друга."),
    ("A target must succeed on a", "Цель должна преуспеть в спасброске"),
    ("or take", "или получить"),
    ("Choose one creature within range", "Выберите одно существо в пределах дистанции"),
    ("Choose a creature that you can see within range", "Выберите существо, которое видите в пределах дистанции"),
    ("Choose one or more creatures within range", "Выберите одно или несколько существ в пределах дистанции"),
    ("You touch one willing creature.", "Вы касаетесь одного согласного существа."),
    ("You touch a willing creature.", "Вы касаетесь согласного существа."),
    ("You touch one creature.", "Вы касаетесь одного существа."),
    ("You touch a creature.", "Вы касаетесь существа."),

    # Attack patterns
    ("Make a ranged spell attack against the target.", "Совершите дальнобойную атаку заклинанием по цели."),
    ("Make a ranged spell attack against the creature", "Совершите дальнобойную атаку заклинанием по существу"),
    ("Make a ranged spell attack against", "Совершите дальнобойную атаку заклинанием по"),
    ("Make a melee spell attack against the target.", "Совершите рукопашную атаку заклинанием по цели."),
    ("Make a melee spell attack against", "Совершите рукопашную атаку заклинанием по"),
    ("Make a ranged spell attack.", "Совершите дальнобойную атаку заклинанием."),
    ("Make a melee spell attack.", "Совершите рукопашную атаку заклинанием."),

    # Hit/damage patterns
    ("On a hit, the target takes", "При попадании цель получает"),
    ("On a hit, it takes", "При попадании она получает"),
    ("On a hit, the target", "При попадании цель"),
    ("On a hit,", "При попадании"),
    ("On a miss,", "При промахе"),
    ("on a failed save", "при провале спасброска"),
    ("on a successful save", "при успешном спасброске"),
    ("on a successful one", "при успехе"),
    ("half as much damage", "половину этого урона"),
    ("or half as much", "или половину этого урона"),
    ("A creature takes", "Существо получает"),
    ("The target takes", "Цель получает"),
    ("the target takes", "цель получает"),
    ("takes the damage", "получает урон"),
    ("takes damage", "получает урон"),

    # Save patterns
    ("must succeed on a Dexterity saving throw", "должна преуспеть в спасброске Ловкости"),
    ("must succeed on a Constitution saving throw", "должна преуспеть в спасброске Телосложения"),
    ("must succeed on a Wisdom saving throw", "должна преуспеть в спасброске Мудрости"),
    ("must succeed on a Charisma saving throw", "должна преуспеть в спасброске Харизмы"),
    ("must succeed on a Strength saving throw", "должна преуспеть в спасброске Силы"),
    ("must succeed on a Intelligence saving throw", "должна преуспеть в спасброске Интеллекта"),
    ("must make a Dexterity saving throw", "должна совершить спасбросок Ловкости"),
    ("must make a Constitution saving throw", "должна совершить спасбросок Телосложения"),
    ("must make a Wisdom saving throw", "должна совершить спасбросок Мудрости"),
    ("must make a Charisma saving throw", "должна совершить спасбросок Харизмы"),
    ("must make a Strength saving throw", "должна совершить спасбросок Силы"),
    ("must make a Intelligence saving throw", "должна совершить спасбросок Интеллекта"),
    ("Dexterity saving throw", "спасбросок Ловкости"),
    ("Constitution saving throw", "спасбросок Телосложения"),
    ("Wisdom saving throw", "спасбросок Мудрости"),
    ("Charisma saving throw", "спасбросок Харизмы"),
    ("Strength saving throw", "спасбросок Силы"),
    ("Intelligence saving throw", "спасбросок Интеллекта"),
    ("saving throw", "спасбросок"),
    ("saving throws", "спасброски"),

    # Duration/condition patterns
    ("for the duration", "на время действия заклинания"),
    ("until the spell ends", "пока заклинание не закончится"),
    ("until the start of your next turn", "до начала вашего следующего хода"),
    ("until the end of your next turn", "до конца вашего следующего хода"),
    ("at the start of each of its turns", "в начале каждого своего хода"),
    ("at the end of each of its turns", "в конце каждого своего хода"),
    ("at the start of your turn", "в начале вашего хода"),
    ("at the end of your turn", "в конце вашего хода"),
    ("within range", "в пределах дистанции"),
    ("you can see", "которое видите"),
    ("that you can see", "которое вы видите"),
    ("within 5 feet of", "в пределах 5 футов от"),
    ("within 10 feet of", "в пределах 10 футов от"),
    ("within 30 feet of", "в пределах 30 футов от"),
    ("within 60 feet of", "в пределах 60 футов от"),
    ("within 120 feet of", "в пределах 120 футов от"),

    # Common verbs/phrases
    ("The spell ends", "Заклинание заканчивается"),
    ("the spell ends", "заклинание заканчивается"),
    ("If you cast this spell again", "Если вы сотворите это заклинание снова"),
    ("you cast this spell", "вы сотворите это заклинание"),
    ("When you cast this spell", "Когда вы сотворяете это заклинание"),
    ("While the spell lasts", "Пока заклинание действует"),
    ("As an action on your turn", "Действием в свой ход"),
    ("As a bonus action on your turn", "Бонусным действием в свой ход"),
    ("As a bonus action", "Бонусным действием"),
    ("as an action", "действием"),
    ("as a bonus action", "бонусным действием"),
    ("as a reaction", "реакцией"),

    # Creature references
    ("Each creature in", "Каждое существо в"),
    ("each creature in", "каждое существо в"),
    ("a creature within range", "существо в пределах дистанции"),
    ("each creature within", "каждое существо в пределах"),
    ("a willing creature", "согласное существо"),
    ("one creature", "одно существо"),
    ("the creature", "существо"),
    ("a creature", "существо"),
    ("creatures", "существа"),
    ("creature", "существо"),
    ("the target", "цель"),
    ("a target", "цель"),

    # Actions
    ("an action", "действие"),
    ("a bonus action", "бонусное действие"),
    ("a reaction", "реакцию"),
    ("your action", "своё действие"),

    # Common adjectives/descriptions
    ("hostile creature", "враждебного существа"),
    ("hostile creatures", "враждебных существ"),
    ("you choose", "по вашему выбору"),
    ("of your choice", "по вашему выбору"),
    ("has advantage on", "совершает с преимуществом"),
    ("has disadvantage on", "совершает с помехой"),
    ("have advantage on", "совершают с преимуществом"),
    ("have disadvantage on", "совершают с помехой"),
    ("advantage on", "преимущество при"),
    ("disadvantage on", "помеху при"),
    ("You have advantage", "Вы получаете преимущество"),
    ("You have disadvantage", "Вы получаете помеху"),
    ("attack rolls", "броски атаки"),
    ("attack roll", "бросок атаки"),
    ("ability check", "проверку характеристики"),
    ("ability checks", "проверки характеристик"),
    ("spell save DC", "СЛ спасброска от ваших заклинаний"),
    ("your spell save DC", "СЛ спасброска от ваших заклинаний"),
    ("against your spell save DC", "против СЛ спасброска от ваших заклинаний"),

    # Common game terms
    ("hit points", "хитов"),
    ("hit point", "хит"),
    ("Hit Points", "Хитов"),
    ("Hit Dice", "Кости Хитов"),
    ("temporary hit points", "временные хиты"),
    ("bright light", "яркий свет"),
    ("dim light", "тусклый свет"),
    ("normal light", "обычный свет"),
    ("sheds bright light in a", "излучает яркий свет в радиусе"),
    ("sheds dim light for an additional", "и тусклый свет в дополнительном радиусе"),
    ("an unoccupied space", "свободное пространство"),
    ("unoccupied space", "свободное пространство"),
    ("line of sight", "линию обзора"),
    ("your spellcasting ability", "характеристику заклинателя"),
    ("spellcasting ability", "характеристика заклинателя"),
    ("proficiency bonus", "бонус мастерства"),

    # Damage types
    ("acid damage", "урон кислотой"),
    ("bludgeoning damage", "дробящий урон"),
    ("cold damage", "урон холодом"),
    ("fire damage", "урон огнём"),
    ("force damage", "урон силовым полем"),
    ("lightning damage", "урон электричеством"),
    ("necrotic damage", "некротический урон"),
    ("piercing damage", "колющий урон"),
    ("poison damage", "урон ядом"),
    ("psychic damage", "психический урон"),
    ("radiant damage", "урон излучением"),
    ("slashing damage", "рубящий урон"),
    ("thunder damage", "урон громом"),
    ("damage", "урон"),

    # Conditions
    ("becomes frightened", "становится испуганным"),
    ("becomes charmed", "становится очарованным"),
    ("becomes invisible", "становится невидимым"),
    ("becomes paralyzed", "становится парализованным"),
    ("becomes petrified", "становится окаменевшим"),
    ("becomes poisoned", "становится отравленным"),
    ("becomes stunned", "становится ошеломлённым"),
    ("becomes blinded", "становится ослеплённым"),
    ("becomes deafened", "становится оглохшим"),
    ("becomes incapacitated", "становится недееспособным"),
    ("becomes restrained", "становится опутанным"),
    ("becomes prone", "падает ничком"),
    ("is blinded", "ослеплено"),
    ("is charmed", "очаровано"),
    ("is deafened", "оглохло"),
    ("is frightened", "испугано"),
    ("is incapacitated", "недееспособно"),
    ("is invisible", "невидимо"),
    ("is paralyzed", "парализовано"),
    ("is petrified", "окаменело"),
    ("is poisoned", "отравлено"),
    ("is prone", "лежит ничком"),
    ("is restrained", "опутано"),
    ("is stunned", "ошеломлено"),
    ("is unconscious", "без сознания"),

    # Abilities
    ("Strength", "Силы"),
    ("Dexterity", "Ловкости"),
    ("Constitution", "Телосложения"),
    ("Intelligence", "Интеллекта"),
    ("Wisdom", "Мудрости"),
    ("Charisma", "Харизмы"),

    # Classes
    ("Bard", "Бард"),
    ("Cleric", "Жрец"),
    ("Druid", "Друид"),
    ("Paladin", "Паладин"),
    ("Ranger", "Следопыт"),
    ("Sorcerer", "Чародей"),
    ("Warlock", "Колдун"),
    ("Wizard", "Волшебник"),

    # Common words
    ("the GM", "Мастер"),
    ("The GM", "Мастер"),
    ("can't", "не может"),
    ("doesn't", "не"),
    ("isn't", "не является"),
    ("aren't", "не являются"),
    ("won't", "не будет"),
    ("didn't", "не"),
    ("Player's Handbook", "*Книга игрока*"),
]

def apply_phrases(line):
    """Apply phrase dictionary to translate remaining English fragments."""
    for en, ru in PHRASES:
        line = line.replace(en, ru)
    return line

# Process lines 229+ (spell descriptions)
out = list(ru_lines)  # start from current RU

for i in range(229, N):
    line = out[i]
    # Skip lines that are already fully Russian or are structural
    # (headings, metadata lines that were already translated)
    if not line.strip():
        continue
    if line.startswith("### ") or line.startswith("## "):
        continue
    if line.startswith("*") and line.endswith("*") and ("уровня" in line or "Заговор" in line):
        continue
    if line.startswith("**Время накладывания:**"):
        continue
    if line.startswith("**Дистанция:**"):
        continue
    if line.startswith("**Компоненты:**"):
        continue
    if line.startswith("**Длительность:**"):
        continue

    # Apply phrase translations to body text
    out[i] = apply_phrases(line)

with open(RU_FILE, "w", encoding="utf-8") as f:
    f.write('\n'.join(out))

print(f"Phase 2 complete. {N} lines written.")
