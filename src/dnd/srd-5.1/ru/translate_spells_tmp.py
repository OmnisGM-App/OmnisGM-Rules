#!/usr/bin/env python3
"""
Phase 2: Post-process the partially translated RU file to translate remaining English fragments.
Reads from and writes to the same RU file.
"""
import re, sys

# Read from the already partially-translated file
INPUT = "/Users/petrradilov/Documents/srd/dndsrd5.2_markdown/src/dnd/srd-5.1/ru/10_Spells.md"
OUTPUT = "/Users/petrradilov/Documents/srd/dndsrd5.2_markdown/src/dnd/srd-5.1/ru/10_Spells.md"
# We also need the EN original to do sentence-level translation
EN_INPUT = "/Users/petrradilov/Documents/srd/dndsrd5.2_markdown/src/dnd/srd-5.1/en/10_Spells.md"

# Spell name mapping
SN = {
    "Acid Splash":"Кислотные брызги","Chill Touch":"Могильный холод","Dancing Lights":"Танцующие огоньки",
    "Druidcraft":"Искусство друидов","Eldritch Blast":"Мистический заряд","Fire Bolt":"Огненный снаряд",
    "Guidance":"Указание","Light":"Свет","Mage Hand":"Волшебная рука","Mending":"Починка",
    "Message":"Сообщение","Minor Illusion":"Малая иллюзия","Poison Spray":"Ядовитые брызги",
    "Prestidigitation":"Фокусы","Produce Flame":"Сотворение пламени","Ray of Frost":"Луч холода",
    "Resistance":"Сопротивление","Sacred Flame":"Священное пламя","Shillelagh":"Дубинка",
    "Shocking Grasp":"Шоковый захват","Spare the Dying":"Сопровождение умирающего",
    "Thaumaturgy":"Тауматургия","True Strike":"Верный удар","Vicious Mockery":"Язвительная насмешка",
    "Alarm":"Тревога","Animal Friendship":"Дружба с животными","Bane":"Порча","Bless":"Благословение",
    "Burning Hands":"Огненные руки","Charm Person":"Очарование личности","Color Spray":"Цветные брызги",
    "Command":"Приказ","Comprehend Languages":"Понимание языков",
    "Create or Destroy Water":"Сотворение или уничтожение воды","Cure Wounds":"Лечение ран",
    "Detect Evil and Good":"Обнаружение добра и зла","Detect Magic":"Обнаружение магии",
    "Detect Poison and Disease":"Обнаружение яда и болезни","Disguise Self":"Маскировка",
    "Divine Favor":"Божественное благоволение","Entangle":"Опутывание",
    "Expeditious Retreat":"Поспешное отступление","Faerie Fire":"Огонь фей","False Life":"Псевдожизнь",
    "Feather Fall":"Падение пёрышком","Find Familiar":"Поиск фамильяра","Floating Disk":"Парящий диск",
    "Fog Cloud":"Туманное облако","Goodberry":"Чудо-ягоды","Grease":"Скольжение",
    "Guiding Bolt":"Направляющий снаряд","Healing Word":"Целебное слово",
    "Hellish Rebuke":"Адское возмездие","Heroism":"Героизм","Hideous Laughter":"Жуткий смех",
    "Hunter's Mark":"Метка охотника","Identify":"Опознание","Illusory Script":"Иллюзорный текст",
    "Inflict Wounds":"Нанесение ран","Jump":"Прыжок","Longstrider":"Скороход",
    "Mage Armor":"Доспехи мага","Magic Missile":"Магическая стрела",
    "Protection from Evil and Good":"Защита от добра и зла","Purify Food and Drink":"Очистить пищу и питьё",
    "Sanctuary":"Святилище","Shield":"Щит","Shield of Faith":"Щит веры","Silent Image":"Немой образ",
    "Sleep":"Усыпление","Speak with Animals":"Разговор с животными","Thunderwave":"Волна грома",
    "Unseen Servant":"Невидимый слуга","Acid Arrow":"Кислотная стрела","Aid":"Помощь",
    "Alter Self":"Смена обличья","Animal Messenger":"Животный посланник","Arcane Lock":"Арканный замок",
    "Arcanist's Magic Aura":"Аура арканиста","Augury":"Предсказание","Barkskin":"Кора",
    "Blindness/Deafness":"Слепота/Глухота","Blur":"Размытость","Branding Smite":"Клеймящая кара",
    "Calm Emotions":"Успокоение эмоций","Continual Flame":"Вечный огонь","Darkness":"Тьма",
    "Darkvision":"Тёмное зрение","Detect Thoughts":"Обнаружение мыслей",
    "Enhance Ability":"Улучшение характеристики","Enlarge/Reduce":"Увеличение/уменьшение",
    "Enthrall":"Завораживание","Find Steed":"Поиск скакуна","Find Traps":"Поиск ловушек",
    "Flame Blade":"Пылающий клинок","Flaming Sphere":"Пылающая сфера",
    "Gentle Repose":"Бальзамирование","Gust of Wind":"Порыв ветра","Heat Metal":"Раскалённый металл",
    "Hold Person":"Удержание личности","Invisibility":"Невидимость","Knock":"Открывание",
    "Lesser Restoration":"Малое восстановление","Levitate":"Левитация",
    "Locate Animals or Plants":"Поиск животных или растений","Locate Object":"Поиск объекта",
    "Magic Mouth":"Волшебные уста","Magic Weapon":"Волшебное оружие","Mirror Image":"Отражения",
    "Misty Step":"Туманный шаг","Moonbeam":"Лунный луч","Pass without Trace":"Бесследное передвижение",
    "Prayer of Healing":"Молитва исцеления","Protection from Poison":"Защита от яда",
    "Ray of Enfeeblement":"Луч ослабления","Rope Trick":"Верёвочный фокус",
    "Scorching Ray":"Палящий луч","See Invisibility":"Видение невидимого","Shatter":"Дребезги",
    "Silence":"Тишина","Spider Climb":"Паучье лазание","Spike Growth":"Шипы",
    "Spiritual Weapon":"Духовное оружие","Suggestion":"Внушение","Warding Bond":"Защитные узы",
    "Web":"Паутина","Zone of Truth":"Зона правды","Animate Dead":"Оживление мёртвых",
    "Beacon of Hope":"Маяк надежды","Bestow Curse":"Наложение проклятия","Blink":"Мерцание",
    "Call Lightning":"Молния с небес","Clairvoyance":"Ясновидение",
    "Conjure Animals":"Призыв животных","Counterspell":"Контрзаклинание",
    "Create Food and Water":"Сотворение пищи и воды","Daylight":"Дневной свет",
    "Dispel Magic":"Рассеивание магии","Fear":"Страх","Fireball":"Огненный шар","Fly":"Полёт",
    "Gaseous Form":"Газообразная форма","Glyph of Warding":"Охранные руны","Haste":"Ускорение",
    "Hypnotic Pattern":"Гипнотический узор","Lightning Bolt":"Молния",
    "Magic Circle":"Магический круг","Major Image":"Высший образ",
    "Mass Healing Word":"Массовое целебное слово","Meld into Stone":"Слияние с камнем",
    "Nondetection":"Необнаружимость","Phantom Steed":"Призрачный скакун",
    "Plant Growth":"Рост растений","Protection from Energy":"Защита от энергии",
    "Remove Curse":"Снятие проклятия","Revivify":"Возвращение к жизни","Sending":"Послание",
    "Sleet Storm":"Слякотный дождь","Slow":"Замедление","Speak with Dead":"Разговор с мёртвыми",
    "Speak with Plants":"Разговор с растениями","Spirit Guardians":"Духовные стражи",
    "Stinking Cloud":"Удушающее облако","Tiny Hut":"Крошечная хижина","Tongues":"Языки",
    "Vampiric Touch":"Прикосновение вампира","Water Breathing":"Дыхание под водой",
    "Water Walk":"Хождение по воде","Wind Wall":"Стена ветра","Arcane Eye":"Арканный глаз",
    "Banishment":"Изгнание","Black Tentacles":"Чёрные щупальца","Blight":"Гниль",
    "Compulsion":"Принуждение","Confusion":"Замешательство",
    "Conjure Minor Elementals":"Призыв малых элементалей",
    "Conjure Woodland Beings":"Призыв лесных существ","Control Water":"Власть над водой",
    "Death Ward":"Защита от смерти","Dimension Door":"Дверь измерений","Divination":"Гадание",
    "Dominate Beast":"Подчинение зверя","Fabricate":"Фабрикация","Faithful Hound":"Верный пёс",
    "Fire Shield":"Огненный щит","Freedom of Movement":"Свобода перемещения",
    "Giant Insect":"Гигантское насекомое","Greater Invisibility":"Высшая невидимость",
    "Guardian of Faith":"Страж веры","Hallucinatory Terrain":"Иллюзорная местность",
    "Ice Storm":"Град","Locate Creature":"Поиск существа","Phantasmal Killer":"Призрачный убийца",
    "Polymorph":"Превращение","Private Sanctum":"Личное убежище",
    "Resilient Sphere":"Упругая сфера","Secret Chest":"Тайный сундук",
    "Stone Shape":"Изменение формы камня","Stoneskin":"Каменная кожа","Wall of Fire":"Стена огня",
    "Animate Objects":"Оживление предметов","Antilife Shell":"Барьер жизни",
    "Arcane Hand":"Арканная рука","Awaken":"Пробуждение","Cloudkill":"Облако убийства",
    "Commune":"Причастие","Commune with Nature":"Связь с природой","Cone of Cold":"Конус холода",
    "Conjure Elemental":"Сотворение элементаля","Contact Other Plane":"Связь с иным планом",
    "Contagion":"Заражение","Creation":"Сотворение","Dispel Evil and Good":"Рассеивание добра и зла",
    "Dominate Person":"Подчинение личности","Dream":"Сон","Flame Strike":"Небесный огонь",
    "Geas":"Обет","Greater Restoration":"Высшее восстановление","Hallow":"Освящение",
    "Hold Monster":"Удержание чудовища","Insect Plague":"Нашествие насекомых",
    "Legend Lore":"Знание легенд","Mass Cure Wounds":"Массовое исцеление ран",
    "Mislead":"Введение в заблуждение","Modify Memory":"Изменение памяти","Passwall":"Проход",
    "Planar Binding":"Планарные узы","Raise Dead":"Воскрешение мёртвых",
    "Reincarnate":"Реинкарнация","Scrying":"Наблюдение","Seeming":"Ложный облик",
    "Telekinesis":"Телекинез","Telepathic Bond":"Телепатическая связь",
    "Teleportation Circle":"Круг телепортации","Tree Stride":"Шаг сквозь деревья",
    "Wall of Force":"Стена силы","Wall of Stone":"Каменная стена",
    "Blade Barrier":"Стена клинков","Chain Lightning":"Цепная молния",
    "Circle of Death":"Круг смерти","Conjure Fey":"Сотворение феи",
    "Contingency":"Предусмотрительность","Create Undead":"Создание нежити",
    "Disintegrate":"Распыление","Eyebite":"Зловещий взгляд","Find the Path":"Поиск пути",
    "Flesh to Stone":"Окаменение","Forbiddance":"Запрет","Freezing Sphere":"Морозная сфера",
    "Globe of Invulnerability":"Сфера неуязвимости","Guards and Wards":"Стражи и обереги",
    "Harm":"Нанесение вреда","Heal":"Исцеление","Heroes' Feast":"Пир героев",
    "Instant Summons":"Мгновенный призыв","Irresistible Dance":"Непреодолимый танец",
    "Magic Jar":"Волшебный сосуд","Mass Suggestion":"Массовое внушение",
    "Move Earth":"Движение земли","Planar Ally":"Планарный союзник",
    "Programmed Illusion":"Запрограммированная иллюзия","Sunbeam":"Солнечный луч",
    "Transport via Plants":"Перемещение растениями","True Seeing":"Видение истины",
    "Wall of Ice":"Стена льда","Wall of Thorns":"Стена тернов","Wind Walk":"Хождение по ветру",
    "Word of Recall":"Слово возврата","Arcane Sword":"Арканный меч",
    "Conjure Celestial":"Призыв небожителя","Delayed Blast Fireball":"Замедленный огненный шар",
    "Divine Word":"Божественное слово","Etherealness":"Эфирность","Finger of Death":"Перст смерти",
    "Fire Storm":"Огненная буря","Forcecage":"Силовая клетка",
    "Magnificent Mansion":"Великолепный особняк","Mirage Arcane":"Мираж",
    "Plane Shift":"Переход между планами","Prismatic Spray":"Радужные брызги",
    "Project Image":"Проецирование образа","Regenerate":"Регенерация",
    "Resurrection":"Воскрешение","Reverse Gravity":"Разворот гравитации","Sequester":"Изоляция",
    "Simulacrum":"Симулякр","Symbol":"Символ","Teleport":"Телепорт",
    "Animal Shapes":"Животные формы","Antimagic Field":"Антимагическое поле",
    "Antipathy/Sympathy":"Антипатия/Симпатия","Clone":"Клон",
    "Control Weather":"Власть над погодой","Demiplane":"Полуплан",
    "Dominate Monster":"Подчинение чудовища","Earthquake":"Землетрясение",
    "Feeblemind":"Помрачение","Glibness":"Дар красноречия","Holy Aura":"Аура святости",
    "Incendiary Cloud":"Огненное облако","Maze":"Лабиринт","Mind Blank":"Пустой разум",
    "Power Word Stun":"Слово силы: оглушение","Sunburst":"Солнечный удар",
    "Astral Projection":"Астральная проекция","Foresight":"Предвидение","Gate":"Врата",
    "Imprisonment":"Заточение","Mass Heal":"Массовое исцеление","Meteor Swarm":"Метеоритный дождь",
    "Power Word Kill":"Слово силы: смерть","Prismatic Wall":"Радужная стена",
    "Shapechange":"Изменение формы","Storm of Vengeance":"Буря возмездия",
    "Time Stop":"Остановка времени","True Polymorph":"Истинный полиморф",
    "True Resurrection":"Истинное воскрешение","Weird":"Кошмар","Wish":"Исполнение желаний",
}

CN = {"Bard":"Бард","Cleric":"Жрец","Druid":"Друид","Paladin":"Паладин","Ranger":"Следопыт",
      "Sorcerer":"Чародей","Warlock":"Колдун","Wizard":"Волшебник"}

SCH = {"Abjuration":"Ограждение","Conjuration":"Вызов","Divination":"Прорицание",
       "Enchantment":"Очарование","Evocation":"Воплощение","Illusion":"Иллюзия",
       "Necromancy":"Некромантия","Transmutation":"Преобразование"}

SCH_GEN = {"Ограждение":"Ограждения","Вызов":"Вызова","Прорицание":"Прорицания",
           "Очарование":"Очарования","Воплощение":"Воплощения","Иллюзия":"Иллюзии",
           "Некромантия":"Некромантии","Преобразование":"Преобразования"}

FIXED = {
    "# Spells":"# Заклинания",
    "## Spellcasting":"## Сотворение заклинаний",
    "## What Is a Spell?":"## Что такое заклинание?",
    "### Spell Level":"### Уровень заклинания",
    "### Known and Prepared Spells":"### Известные и подготовленные заклинания",
    "### Spell Slots":"### Ячейки заклинаний",
    "#### Casting a Spell at a Higher Level":"#### Сотворение заклинания с помощью ячейки более высокого уровня",
    "## Cantrips":"## Заговоры",
    "## Rituals":"## Ритуалы",
    "## Casting a Spell":"## Сотворение заклинания",
    "### Casting Time":"### Время накладывания",
    "#### Bonus Action":"#### Бонусное действие",
    "#### Reactions":"#### Реакции",
    "#### Longer Casting Times":"#### Более долгое время накладывания",
    "### Spell Range":"### Дистанция заклинания",
    "### Components":"### Компоненты",
    "#### Verbal (V)":"#### Вербальный (В)",
    "#### Somatic (S)":"#### Соматический (С)",
    "#### Material (M)":"#### Материальный (М)",
    "### Duration":"### Длительность",
    "#### Instantaneous":"#### Мгновенная",
    "#### Concentration":"#### Концентрация",
    "### Targets":"### Цели",
    "#### A Clear Path to the Target":"#### Чистый путь до цели",
    "#### Targeting Yourself":"#### Нацеливание на себя",
    "### Areas of Effect":"### Области воздействия",
    "#### Cone":"#### Конус",
    "#### Cube":"#### Куб",
    "#### Cylinder":"#### Цилиндр",
    "#### Line":"#### Линия",
    "#### Sphere":"#### Сфера",
    "## Spell Saving Throws":"## Спасброски от заклинаний",
    "## Spell Attack Rolls":"## Броски атаки заклинанием",
    "## Combining Magical Effects":"## Комбинирование магических эффектов",
    "## Cantrips (Level 0)":"## Заговоры (уровень 0)",
    "## Level 1 Spells":"## Заклинания 1-го уровня",
    "## Level 2 Spells":"## Заклинания 2-го уровня",
    "## Level 3 Spells":"## Заклинания 3-го уровня",
    "## Level 4 Spells":"## Заклинания 4-го уровня",
    "## Level 5 Spells":"## Заклинания 5-го уровня",
    "## Level 6 Spells":"## Заклинания 6-го уровня",
    "## Level 7 Spells":"## Заклинания 7-го уровня",
    "## Level 8 Spells":"## Заклинания 8-го уровня",
    "## Level 9 Spells":"## Заклинания 9-го уровня",
}

# ---- Material components ----
MATS = {
    "(a tiny bell and a piece of fine silver wire)":"(крошечный колокольчик и кусочек тонкой серебряной проволоки)",
    "(a bit of phosphorus or wychwood, or a glowworm)":"(кусочек фосфора или гнилушки, или светлячок)",
    "(a firefly or phosphorescent moss)":"(светлячок или фосфоресцирующий мох)",
    "(two lodestones)":"(два магнитных камня)",
    "(a short piece of copper wire)":"(короткий кусок медной проволоки)",
    "(a bit of fleece)":"(кусочек овечьей шерсти)",
    "(mistletoe, a shamrock leaf, and a club or quarterstaff)":"(омела, лист клевера и дубинка или боевой посох)",
    "(a miniature cloak)":"(миниатюрный плащ)",
    "(a drop of blood)":"(капля крови)",
    "(a sprinkling of holy water)":"(капля святой воды)",
    "(a tiny strip of white cloth)":"(крошечная полоска белой ткани)",
    "(a pinch of fine sand, rose petals, or crickets)":"(щепотка мелкого песка, лепестки роз или сверчки)",
    "(a piece of cured leather)":"(кусок выделанной кожи)",
    "(ruby dust worth 50 gp)":"(рубиновая пыль стоимостью 50 зм)",
    "(a morsel of food)":"(кусочек пищи)",
    "(a small piece of mirror)":"(маленький кусочек зеркала)",
    "(a small bit of honeycomb and jade dust worth at least 10 gp, which the spell consumes)":"(кусочек медовых сот и нефритовая пыль стоимостью не менее 10 зм, расходуемые заклинанием)",
    "(a white feather or the heart of a hen)":"(белое перо или куриное сердце)",
    "(a grasshopper's hind leg)":"(задняя нога кузнечика)",
    "(a pinch of talc and a small sprinkling of powdered silver)":"(щепотка талька и немного порошкового серебра)",
    "(a shaving of licorice root)":"(стружка корня лакрицы)",
    "(a small clay model of a ziggurat)":"(маленькая глиняная модель зиккурата)",
    "(a small leather loop)":"(маленькая кожаная петля)",
    "(a bit of sponge)":"(кусочек губки)",
    "(a copper piece)":"(медная монета)",
    "(a bit of fur and a rod of amber, crystal, or glass)":"(кусочек меха и стержень из янтаря, хрусталя или стекла)",
    "(a pinch of powder made of dried leaves and a small amount of vermillion)":"(щепотка порошка из сухих листьев и немного киновари)",
    "(incense and a sacrificial offering appropriate to your religion, together worth at least 25 gp, which the spell consumes)":"(благовоние и жертвоприношение, подходящее для вашей религии, общей стоимостью не менее 25 зм, расходуемые заклинанием)",
    "(a set of divinatory tools)":"(набор инструментов для гадания)",
    "(a focus worth at least 100 gp, either a jeweled horn for hearing or a glass eye for seeing)":"(фокусировка стоимостью не менее 100 зм — украшенный самоцветами рог для слуха или стеклянный глаз для зрения)",
    "(a pearl worth at least 100 gp and an owl feather)":"(жемчужина стоимостью не менее 100 зм и перо совы)",
    "(a lead-based ink worth at least 10 gp, which the spell consumes)":"(чернила на основе свинца стоимостью не менее 10 зм, расходуемые заклинанием)",
    "(a bit of bat fur and a drop of pitch or piece of coal)":"(кусочек шерсти летучей мыши и капля смолы или кусочек угля)",
    "(a bit of fur; a piece of amber, glass, or a crystal rod; and three silver pins)":"(кусочек меха; кусок янтаря, стекла или хрустальный стержень; и три серебряные булавки)",
    "(a sprig of mistletoe)":"(веточка омелы)",
    "(tallow, a piece of cloth, and powdered charcoal)":"(жир, кусок ткани и порошковый уголь)",
    "(a small piece of mirror and a miniature clay portal)":"(маленький кусочек зеркала и миниатюрный глиняный портал)",
    "(a tiny ball of bat guano and sulfur)":"(крошечный шарик из помёта летучей мыши и серы)",
    "(a piece of string and a bit of wood)":"(кусок верёвки и щепка дерева)",
    "(a pinch of sand)":"(щепотка песка)",
    "(a snake's tongue and either a bit of honeycomb or a drop of sweet oil)":"(змеиный язык и либо кусочек медовых сот, либо капля сладкого масла)",
    "(a small square piece of silk)":"(маленький квадратный кусок шёлка)",
    "(a bit of spider web)":"(кусочек паутины)",
    "(diamonds worth 300 gp, which the spell consumes)":"(бриллианты стоимостью 300 зм, расходуемые заклинанием)",
    "(a bit of phosphorus)":"(кусочек фосфора)",
    "(a miniature hand sculpted from clay)":"(миниатюрная рука, вылепленная из глины)",
    "(a tiny fan and a feather of exotic origin)":"(крошечный веер и перо экзотического происхождения)",
    "(a handful of clay, crystal, glass, or mineral spheres)":"(горсть глиняных, хрустальных, стеклянных или минеральных шариков)",
    "(a wing feather from any bird)":"(маховое перо любой птицы)",
    "(fur or a feather from a beast)":"(мех или перо зверя)",
    "(a piece of iron and a flame)":"(кусок железа и огонь)",
    "(a leather strap, bound around the arm or a similar appendage)":"(кожаный ремешок, обёрнутый вокруг руки или подобного придатка)",
    "(incense worth at least 250 gp, which the spell consumes, and four ivory strips worth at least 50 gp each)":"(благовоние стоимостью не менее 250 зм, расходуемое заклинанием, и четыре костяные полоски стоимостью не менее 50 зм каждая)",
    "(a small crystal or glass cone)":"(маленький конус из хрусталя или стекла)",
    "(a gem-encrusted bowl worth at least 1,000 gp)":"(украшенная самоцветами чаша стоимостью не менее 1 000 зм)",
    "(a caterpillar cocoon)":"(кокон гусеницы)",
    "(a glass or crystal bead that shatters when the spell ends)":"(стеклянная или хрустальная бусина, разбивающаяся по окончании заклинания)",
    "(a forked, metal rod worth at least 250 gp, attuned to a particular plane of existence)":"(раздвоенный металлический стержень стоимостью не менее 250 зм, настроенный на определённый план существования)",
    "(holy water or powdered silver and iron, which the spell consumes)":"(святая вода или порошковые серебро и железо, расходуемые заклинанием)",
    "(a small parchment with a bit of holy text written on it)":"(маленький пергамент с фрагментом священного текста)",
    "(a pinch of dust)":"(щепотка пыли)",
    "(a small, straight piece of iron)":"(маленький прямой кусок железа)",
    "(a bit of gauze and a wisp of smoke)":"(кусочек марли и клубок дыма)",
    "(a small piece of parchment with a bit of honey)":"(маленький кусочек пергамента с каплей мёда)",
    "(a drop of giant slug bile)":"(капля жёлчи гигантского слизня)",
    "(a lodestone and a pinch of dust)":"(магнитный камень и щепотка пыли)",
    "(a pinch of sesame seeds)":"(щепотка кунжутных семян)",
    "(an eggshell and a snakeskin glove)":"(яичная скорлупа и перчатка из змеиной кожи)",
    "(a small amount of phosphorus)":"(немного фосфора)",
    "(rare chalks and inks infused with precious gems worth 50 gp, which the spell consumes)":"(редкие мелки и чернила, насыщенные драгоценными камнями стоимостью 50 зм, расходуемые заклинанием)",
    "(mercury, phosphorus, and powdered diamond and opal worth at least 5,000 gp total, which the spell consumes)":"(ртуть, фосфор, порошковый алмаз и опал общей стоимостью не менее 5 000 зм, расходуемые заклинанием)",
    "(powdered diamond worth at least 100 gp, which the spell consumes)":"(алмазная пыль стоимостью не менее 100 зм, расходуемая заклинанием)",
    "(diamond dust worth 100 gp, which the spell consumes)":"(алмазная пыль стоимостью 100 зм, расходуемая заклинанием)",
    "(a diamond worth at least 1,000 gp, which the spell consumes)":"(бриллиант стоимостью не менее 1 000 зм, расходуемый заклинанием)",
    "(a diamond worth at least 500 gp, which the spell consumes)":"(бриллиант стоимостью не менее 500 зм, расходуемый заклинанием)",
    "(a diamond worth at least 300 gp, which the spell consumes)":"(бриллиант стоимостью не менее 300 зм, расходуемый заклинанием)",
    "(a jeweled horn worth at least 1,000 gp)":"(украшенный самоцветами рог стоимостью не менее 1 000 зм)",
    "(a silver rod worth at least 10 gp)":"(серебряный стержень стоимостью не менее 10 зм)",
    "(a tiny silver mirror)":"(крошечное серебряное зеркало)",
    "(a small replica of you made from materials worth at least 5 gp)":"(маленькая ваша копия из материалов стоимостью не менее 5 зм)",
    "(a small crystal hemisphere)":"(маленькая хрустальная полусфера)",
    "(a bit of bat fur and a chip of amber)":"(кусочек шерсти летучей мыши и осколок янтаря)",
    "(jade dust worth at least 25 gp)":"(нефритовая пыль стоимостью не менее 25 зм)",
    "(a small piece of iron)":"(маленький кусок железа)",
    "(holly berry)":"(ягода остролиста)",
    "(a thin sheet of lead, a piece of opaque glass, a small bit of cotton or cloth, and powdered chrysolite)":"(тонкий лист свинца, кусок непрозрачного стекла, маленький кусочек ваты или ткани и порошковый хризолит)",
    "(a sprinkling of holy water, rare incense, and powdered ruby worth at least 1,000 gp)":"(капля святой воды, редкое благовоние и порошковый рубин стоимостью не менее 1 000 зм)",
    "(a pinch of graveyard dirt, a drop of bile, and a vial of unholy water)":"(щепотка кладбищенской земли, капля жёлчи и пузырёк нечестивой воды)",
    "(a small piece of quartz)":"(маленький кусок кварца)",
    "(a prayer wheel and holy water)":"(молитвенное колесо и святая вода)",
    "(incense and powdered diamond worth at least 200 gp, which the spell consumes)":"(благовоние и алмазная пыль стоимостью не менее 200 зм, расходуемые заклинанием)",
    "(a focus worth at least 1,000 gp, such as a crystal ball, a silver mirror, or a font filled with holy water)":"(фокусировка стоимостью не менее 1 000 зм — хрустальный шар, серебряное зеркало или купель, наполненная святой водой)",
    "(a gem worth at least 1,000 gp, which the spell consumes)":"(драгоценный камень стоимостью не менее 1 000 зм, расходуемый заклинанием)",
    "(a jade circlet worth at least 1,500 gp, which you must place on your head before you cast the spell)":"(нефритовый венец стоимостью не менее 1 500 зм, который нужно надеть на голову до сотворения заклинания)",
    "(a small amount of makeup applied to the face as this spell is cast)":"(немного грима, нанесённого на лицо при сотворении заклинания)",
    "(for each object you touch, diamond dust worth at least 25 gp, which the spell consumes)":"(для каждого затрагиваемого объекта — алмазная пыль стоимостью не менее 25 зм, расходуемая заклинанием)",
    "(a pinch of fine sand)":"(щепотка мелкого песка)",
    "(a handful of oak bark)":"(горсть дубовой коры)",
    "(a piece of amber)":"(кусок янтаря)",
    "(incense and a vial of holy or unholy water)":"(благовоние и пузырёк святой или нечестивой воды)",
    "(a sunburst pendant worth at least 100 gp)":"(подвеска в виде солнечного луча стоимостью не менее 100 зм)",
    "(a gilded flower worth at least 100 gp)":"(позолоченный цветок стоимостью не менее 100 зм)",
    "(an object engraved with a symbol of the Outer Planes, worth at least 500 gp)":"(предмет с выгравированным символом Внешних Планов, стоимостью не менее 500 зм)",
    "(a gilded skull worth at least 300 gp)":"(позолоченный череп стоимостью не менее 300 зм)",
    "(a small amount of powdered iron)":"(немного порошкового железа)",
    "(a piece of string)":"(кусок верёвки)",
    "(rare oils and unguents worth at least 1,000 gp, which the spell consumes)":"(редкие масла и притирания стоимостью не менее 1 000 зм, расходуемые заклинанием)",
    "(a crystal sphere worth at least 1,000 gp)":"(хрустальная сфера стоимостью не менее 1 000 зм)",
    "(a sapphire worth at least 1,000 gp)":"(сапфир стоимостью не менее 1 000 зм)",
    "(a miniature platinum sword with a grip and pommel of copper and zinc, worth 250 gp)":"(миниатюрный платиновый меч с рукоятью и навершием из меди и цинка, стоимостью 250 зм)",
    "(a gem or other ornamental container worth at least 500 gp)":"(драгоценный камень или декоративный контейнер стоимостью не менее 500 зм)",
    "(a pinch of soot and salt)":"(щепотка сажи и соли)",
    "(a silver whistle)":"(серебряный свисток)",
    "(a piece of opal worth at least 1,000 gp and a silver needle)":"(опал стоимостью не менее 1 000 зм и серебряная игла)",
    "(holly or a plant with thorns)":"(остролист или колючее растение)",
    "(a chip of mica)":"(осколок слюды)",
    "(a sprinkle of holy water and diamonds worth at least 25,000 gp, which the spell consumes)":"(капля святой воды и бриллианты стоимостью не менее 25 000 зм, расходуемые заклинанием)",
    "(powdered diamond worth at least 25,000 gp, which the target absorbs)":"(алмазная пыль стоимостью не менее 25 000 зм, поглощаемая целью)",
    "(a diamond worth at least 25,000 gp, which the spell consumes)":"(бриллиант стоимостью не менее 25 000 зм, расходуемый заклинанием)",
    "(a reliquary containing a sacred relic)":"(реликвария, содержащая священную реликвию)",
    "(chalk or sand)":"(мел или песок)",
    "(a piece of polished marble)":"(кусок полированного мрамора)",
    "(a gem worth at least 50 gp)":"(драгоценный камень стоимостью не менее 50 зм)",
    "(food and water)":"(пища и вода)",
    "(burning incense for prayer and holy water)":"(горящее благовоние для молитвы и святая вода)",
    "(bat guano and sulfur)":"(помёт летучей мыши и сера)",
    "(a piece of sunstone and a naked flame)":"(кусок солнечного камня и открытое пламя)",
    "(a drop of bitumen and a spider)":"(капля битума и паук)",
    "(a sprinkle of flour or similar powdery substance)":"(щепотка муки или подобного порошкообразного вещества)",
    "(an iron blade and a small piece of opal worth at least 500 gp each)":"(железный клинок и маленький опал стоимостью не менее 500 зм каждый)",
    "(a tiny piece of target matter or an item distasteful to the target)":"(крошечный кусочек целевого вещества или предмет, неприятный цели)",
    "(a tiny piece of matter of the same type of the item you plan to create)":"(крошечный кусочек вещества того же типа, что и предмет, который вы планируете создать)",
    "(a pinch of lime, water, and earth)":"(щепотка извести, воды и земли)",
    "(a tiny reliquary worth at least 1,000 gp containing a sacred relic, such as a scrap of cloth from a saint's robe or a piece of parchment from a religious text)":"(крошечная реликвария стоимостью не менее 1 000 зм, содержащая священную реликвию — обрывок ткани с одежды святого или кусочек пергамента из священного текста)",
    "(a vellum depiction or a carved statuette in the likeness of the target, and a special component that varies according to the version of the spell you choose, worth at least 500 gp per Hit Die of the target)":"(изображение на пергаменте или вырезанная статуэтка, похожая на цель, и особый компонент, зависящий от версии заклинания, стоимостью не менее 500 зм за Кость Хитов цели)",
}

# ---- Helpers ----
def tr_school_line(line):
    m = re.match(r'^\*(Level (\d+) )?(\w+)( Cantrip)? \(([^)]+)\)\*\s*$', line)
    if not m: return line
    lvl = m.group(2); sch = m.group(3); cantrip = m.group(4); cls = m.group(5)
    sch_ru = SCH.get(sch, sch)
    cls_parts = [c.strip() for c in cls.split(",")]
    cls_ru = ", ".join(CN.get(c, c) for c in cls_parts)
    if cantrip:
        return f"*Заговор {SCH_GEN.get(sch_ru, sch_ru)} ({cls_ru})*"
    return f"*{sch_ru} {lvl}-го уровня ({cls_ru})*"

def tr_ct(rest):
    rest = rest.replace("Bonus Action", "Бонусное действие")
    rest = rest.replace("Action", "Действие")
    rest = rest.replace("Reaction", "Реакция")
    rest = rest.replace("or Ritual", "или Ритуал")
    rest = re.sub(r'(\d+) minutes?\b', lambda m: f"{m.group(1)} минута" if int(m.group(1))==1 else f"{m.group(1)} минут", rest)
    rest = re.sub(r'(\d+) hours?\b', lambda m: f"{m.group(1)} час" if int(m.group(1))==1 else f"{m.group(1)} часов" if int(m.group(1))>=5 else f"{m.group(1)} часа", rest)
    return rest

def tr_range(rest):
    rest = re.sub(r'Self \((\d+)-foot cone\)', lambda m: f'На себя ({m.group(1)}-футовый конус)', rest)
    rest = re.sub(r'Self \((\d+)-foot-radius sphere\)', lambda m: f'На себя (сфера радиусом {m.group(1)} футов)', rest)
    rest = re.sub(r'Self \((\d+)-foot radius\)', lambda m: f'На себя (радиус {m.group(1)} футов)', rest)
    rest = re.sub(r'Self \((\d+)-foot line\)', lambda m: f'На себя ({m.group(1)}-футовая линия)', rest)
    rest = re.sub(r'Self \((\d+)-foot-radius hemisphere\)', lambda m: f'На себя (полусфера радиусом {m.group(1)} футов)', rest)
    rest = re.sub(r'Self \((\d+)-foot cube\)', lambda m: f'На себя ({m.group(1)}-футовый куб)', rest)
    rest = rest.replace("Self", "На себя").replace("Touch", "Касание").replace("Unlimited", "Неограниченная").replace("Special", "Особая").replace("Sight", "Зрение")
    rest = re.sub(r'(\d+) feet\b', lambda m: f"{m.group(1)} футов", rest)
    rest = re.sub(r'(\d+)-foot\b', lambda m: f"{m.group(1)}-футов", rest)
    rest = re.sub(r'(\d+) miles?\b', lambda m: f"{m.group(1)} миль" if int(m.group(1))>=5 else f"{m.group(1)} мили" if int(m.group(1))>=2 else f"{m.group(1)} миля", rest)
    return rest

def tr_comp(rest):
    rest = re.sub(r'\bV\b', 'В', rest)
    rest = re.sub(r'\bS\b', 'С', rest)
    rest = re.sub(r'\bM\b', 'М', rest)
    for en, ru in MATS.items():
        if en in rest:
            rest = rest.replace(en, ru)
            break
    return rest

def tr_dur(text):
    text = text.replace("Instantaneous", "Мгновенная")
    text = text.replace("Concentration, up to ", "Концентрация, вплоть до ")
    text = text.replace("Up to ", "Вплоть до ")
    text = text.replace("Until dispelled or triggered", "Пока не будет рассеяно или активировано")
    text = text.replace("Until dispelled", "Пока не будет рассеяно")
    text = text.replace("Special", "Особая")
    text = text.replace("one minute", "1 минуту")
    text = text.replace("one hour", "1 час")
    def ru_min(m):
        n=int(m.group(1))
        if n==1: return f"{n} минуту"
        elif 2<=n<=4: return f"{n} минуты"
        else: return f"{n} минут"
    def ru_hr(m):
        n=int(m.group(1))
        if n==1: return f"{n} час"
        elif 2<=n<=4: return f"{n} часа"
        else: return f"{n} часов"
    def ru_rnd(m):
        n=int(m.group(1))
        if n==1: return f"{n} раунд"
        elif 2<=n<=4: return f"{n} раунда"
        else: return f"{n} раундов"
    def ru_day(m):
        n=int(m.group(1))
        if n==1: return f"{n} день"
        elif 2<=n<=4: return f"{n} дня"
        else: return f"{n} дней"
    text = re.sub(r'(\d+) minutes?\b', ru_min, text)
    text = re.sub(r'(\d+) hours?\b', ru_hr, text)
    text = re.sub(r'(\d+) rounds?\b', ru_rnd, text)
    text = re.sub(r'(\d+) days?\b', ru_day, text)
    return text

def tr_body(line):
    """Translate body text - game terms, dice, units, etc."""
    # Structural markers
    line = line.replace("**_At Higher Levels._**", "**_На более высоких уровнях._**")
    line = line.replace("**_Using a Higher-Level Spell Slot._**", "**_Использование ячейки более высокого уровня._**")
    line = line.replace("**_Cantrip Upgrade._**", "**_Усиление заговора._**")
    line = line.replace("**_The Schools of Magic._**", "**_Школы магии._**")
    line = line.replace("**Casting in Armor**", "**Сотворение заклинаний в доспехах**")

    # School names in bold (sidebar)
    for en_s, ru_s in SCH.items():
        line = line.replace(f"**{en_s}**", f"**{ru_s}**")

    # Dice: d4->к4 etc.
    line = re.sub(r'(\d*)d(\d+)', lambda m: f"{m.group(1)}к{m.group(2)}", line)

    # Currency
    line = re.sub(r'(\d[\d,]*) gp\b', lambda m: f"{m.group(1)} зм", line)
    line = re.sub(r'(\d[\d,]*) sp\b', lambda m: f"{m.group(1)} см", line)
    line = re.sub(r'(\d[\d,]*) cp\b', lambda m: f"{m.group(1)} мм", line)

    # Feet
    line = re.sub(r'(\d+) feet\b', lambda m: f"{m.group(1)} футов", line)
    line = re.sub(r'(\d+)-foot\b', lambda m: f"{m.group(1)}-футов", line)
    line = re.sub(r'(\d+) foot\b', lambda m: f"{m.group(1)} фут", line)

    # Miles
    line = re.sub(r'(\d+) miles?\b', lambda m: f"{m.group(1)} миль" if int(m.group(1))>=5 else f"{m.group(1)} мили" if int(m.group(1))>=2 else f"{m.group(1)} миля", line)

    # Spell names in italics (longest first to avoid partial matches)
    for en_n, ru_n in sorted(SN.items(), key=lambda x: -len(x[0])):
        line = re.sub(r'\*' + re.escape(en_n) + r'\*', f'*{ru_n}*', line)
        line = re.sub(r'\*' + re.escape(en_n.lower()) + r'\*', f'*{ru_n.lower()}*', line, flags=re.IGNORECASE)

    # Saving throws
    st = {"Strength":"Силы","Dexterity":"Ловкости","Constitution":"Телосложения",
          "Intelligence":"Интеллекта","Wisdom":"Мудрости","Charisma":"Харизмы"}
    for en_a, ru_a in st.items():
        line = re.sub(r'\b' + en_a + r' saving throws?\b', ru_a + ' спасбросок', line)
        line = re.sub(r'\b' + en_a + r' \((\w+)\) checks?\b', ru_a + r' (\1) проверку', line)
    line = re.sub(r'\bsaving throws\b', 'спасброски', line)
    line = re.sub(r'\bsaving throw\b', 'спасбросок', line)

    # Attacks
    line = re.sub(r'\branged spell attack\b', 'дальнобойную атаку заклинанием', line)
    line = re.sub(r'\bmelee spell attack\b', 'рукопашную атаку заклинанием', line)
    line = re.sub(r'\bspell attack\b', 'атаку заклинанием', line)
    line = re.sub(r'\battack rolls?\b', 'бросок атаки', line)

    # DC/AC
    line = re.sub(r'\bDC\b', 'СЛ', line)
    line = re.sub(r'\bAC\b', 'КД', line)

    # Hit points
    line = re.sub(r'\bhit points?\b', 'хитов', line)
    line = re.sub(r'\bHit Points?\b', 'Хитов', line)
    line = re.sub(r'\bHit Dice\b', 'Кости Хитов', line)
    line = re.sub(r'\bhit dice\b', 'кости хитов', line)

    # Damage types
    dt = {"acid damage":"урон кислотой","bludgeoning damage":"дробящий урон","cold damage":"урон холодом",
          "fire damage":"урон огнём","force damage":"урон силовым полем","lightning damage":"урон электричеством",
          "necrotic damage":"некротический урон","piercing damage":"колющий урон","poison damage":"урон ядом",
          "psychic damage":"психический урон","radiant damage":"урон излучением","slashing damage":"рубящий урон",
          "thunder damage":"урон громом"}
    for en_d, ru_d in dt.items():
        line = re.sub(re.escape(en_d), ru_d, line, flags=re.IGNORECASE)

    # Conditions
    cond = {"blinded":"ослеплённым","charmed":"очарованным","deafened":"оглохшим","frightened":"испуганным",
            "grappled":"схваченным","incapacitated":"недееспособным","invisible":"невидимым",
            "paralyzed":"парализованным","petrified":"окаменевшим","poisoned":"отравленным",
            "prone":"лежащим ничком","restrained":"опутанным","stunned":"ошеломлённым","unconscious":"без сознания"}
    for en_c, ru_c in cond.items():
        line = re.sub(r'\b' + en_c + r'\b', ru_c, line, flags=re.IGNORECASE)

    # Class names
    for en_cl, ru_cl in CN.items():
        line = re.sub(r'\b' + en_cl + r's?\b', ru_cl, line)

    # Ability names
    for en_a, ru_a in st.items():
        line = re.sub(r'\b' + en_a + r'\b', ru_a, line)

    # Advantage/disadvantage
    line = re.sub(r'\badvantage\b', 'преимущество', line)
    line = re.sub(r'\bdisadvantage\b', 'помеху', line)

    # Level refs
    line = re.sub(r'\b(\d+)(?:st|nd|rd|th) level\b', lambda m: f"{m.group(1)}-го уровня", line)
    line = re.sub(r'\b(\d+)(?:st|nd|rd|th)-level\b', lambda m: f"{m.group(1)}-го уровня", line)

    # Common phrases
    line = line.replace("on a failed save", "при провале спасброска")
    line = line.replace("on a successful save", "при успешном спасброске")
    line = line.replace("on a successful one", "при успехе")
    line = line.replace("half as much damage", "половину этого урона")
    line = line.replace("half as much урон", "половину этого урона")

    # "the GM" / "GM"
    line = re.sub(r'\bthe GM\b', 'Мастер', line)
    line = re.sub(r'\bThe GM\b', 'Мастер', line)

    # Player's Handbook
    line = line.replace("Player's Handbook", "*Книга игрока*")

    return line

# ============================================================
# MAIN
# ============================================================
with open(INPUT, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split('\n')
N = len(lines)
out = []

for raw in lines:
    line = raw

    # Empty
    if line.strip() == "":
        out.append(line); continue

    # Fixed headings
    if line in FIXED:
        out.append(FIXED[line]); continue

    # Spell heading ### SpellName
    m = re.match(r'^(###) ([A-Z].+)$', line)
    if m:
        sn = m.group(2).strip()
        sr = SN.get(sn)
        if sr:
            out.append(f"### {sr} ({sn})")
        else:
            out.append(line)
        continue

    # School/level line
    if re.match(r'^\*(Level \d+ )?\w+( Cantrip)? \(', line):
        out.append(tr_school_line(line)); continue

    # Casting Time
    if line.startswith("**Casting Time:**"):
        rest = line[len("**Casting Time:**"):].strip()
        out.append(f"**Время накладывания:** {tr_ct(rest)}"); continue

    # Range
    if line.startswith("**Range:**"):
        rest = line[len("**Range:**"):].strip()
        out.append(f"**Дистанция:** {tr_range(rest)}"); continue

    # Components
    if line.startswith("**Components:**"):
        rest = line[len("**Components:**"):].strip()
        out.append(f"**Компоненты:** {tr_comp(rest)}"); continue

    # Duration
    if line.startswith("**Duration:**"):
        rest = line[len("**Duration:**"):].strip()
        out.append(f"**Длительность:** {tr_dur(rest)}"); continue

    # Everything else: body text translation
    out.append(tr_body(line))

# Verify line count
if len(out) != N:
    print(f"ERROR: Line count mismatch! Original: {N}, Output: {len(out)}", file=sys.stderr)
    while len(out) < N: out.append("")
    out = out[:N]
else:
    print(f"OK: {N} lines match")

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write('\n'.join(out))

print(f"Written to {OUTPUT}")
