#!/usr/bin/env python3
"""Сверка ВСЕХ полей статблоков ОБЕИХ редакций с эталоном из официального PDF (issue #260).

Версии проверяются одним и тем же кодом: различия форм (у 5.1 нет инициативы и снаряжения,
спасброски стоят отдельной строкой, таблица характеристик пишется как «21 (+5)», а PDF
печатает весь блок со строчной) живут в конфигурации `VERSIONS`, а не в копии проверок.

Чем это отличается от `test_statblock_headers.py`. Тот держит одну строку блока —
«размер тип, мировоззрение», — и держит её строго, но только в ГЛАВАХ монстров и
указателях: врезок в главах предметов и заклинаний он не видит вовсе, поэтому их шапку
сверяет этот гейт (#271). Всё остальное (КД, инициатива, хиты,
скорость, навыки, чувства, языки, ПО, иммунитеты, сопротивления, уязвимости, снаряжение)
до сих пор не сверялось ни с чем, хотя текст приехал не из PDF, а из стороннего
перегона. У 5.2 сверка нашла 255 расхождений: у 30 существ инициатива была равна
модификатору Ловкости вместо значения из PDF, у 29 в ПО не было бонуса мастерства,
у 27 стояло обобщённое «XP 0 or 10» вместо конкретного значения, у 129 не было строки
языков, у пятерых в скорости висела заглушка `?`, плюс точечные ошибки в навыках и
уязвимостях. У 5.1 — ещё 26 расхождений на 12 блоках (11 правок): спасброски одной наги
уехали в блок соседней, у Архимага сопротивления стояли абзацем вместо пункта списка,
у Жреца разошлись скорость и Религия, плюс потерянные строки навыков и чувств.

Эталонов два, по одному на редакцию: `fixtures/srd-5.2-statblock-fields.json` (336 блоков,
9229 ячеек) снят с официального PDF 5.2.1 четырьмя независимыми выемками (marker,
pymupdf4llm, docling и постраничная резка `pdftotext` по колонкам — конвертеры теряют
разные поля на двухколоночной вёрстке), `fixtures/srd-5.1-statblock-fields.json`
(320 блоков, 6639 ячеек) — с PDF 5.1 постраничной резкой по колонкам. Оба пересобираются
и сверяются `build_statblock_fields.py` — тот прогон воспроизводит КАЖДОЕ значение эталона
из PDF и падает, если хоть одно перестало воспроизводиться.

Что проверяем:
  1) EN — каждое поле каждого блока против эталона (включая таблицу характеристик:
     у 5.2 это значение/модификатор/спасбросок, у 5.1 — значение/модификатор, а
     спасброски стоят отдельной строкой), и лишних полей в тексте нет;
  2) состав эталона — обязательные ключи у всех блоков, число ячеек ПО КАЖДОМУ полю и
     отпечаток структуры «блок → набор полей» (иначе согласованное удаление поля из
     эталона и обоих текстов, а равно обмен полями между блоками, проходили бы молча);
  3) RU-зеркало — все числа обязаны совпадать с EN, у каждого поля EN обязана быть
     RU-строка, лишних RU-полей и выдуманных RU-блоков нет; у ВРЕЗОК сверяется вся шапка:
     размер (значение, род и регистр прилагательного), тип с подтипом и связками — по
     словарю и целиком, мировоззрение — по значению и по форме главы своей редакции (#271);
  4) форма строк текста, которую сравнение значений намеренно не видит (хвостовая
     пунктуация скорости, метки полей);
  5) колонки указателей (ПО, КД, хиты) — против тех же блоков;
  6) ПО против официальной таблицы «ПО → опыт и бонус мастерства», а характеристики —
     против двух производных инвариантов: модификатор выводится из значения, спасбросок
     отличается от модификатора на 0, бонус мастерства или удвоенный бонус (у 5.1 бонус
     берётся из той же таблицы — в статблоке 5.1 он не печатается);
  7) опечатки САМОГО PDF объявляются в эталоне (`cr_note`/`cr_repo`/`xp_note`/`pb_note`/
     `abilities_note`/`abilities_repo`/`saves_note`/`saves_repo`),
     а не молча терпятся: «3 (700 XP)» в PDF против нашего «3 (XP 700)». Пометка — это
     утверждение: она обязана назвать спорные числа И сказать словами, что в источнике.

Запуск: python3 .github/scripts/test_statblock_fields.py
"""
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]
sys.path.insert(0, str(SCRIPTS))
from parsers.monster import SIZES_EN, SIZES_RU_TO_EN, _parse_type_line   # noqa: E402
from statblock_meta import (EN_LABELS_51, META_KEYS, NOTE_KEYS,  # noqa: E402
                            OBJECT_BLOCKS_51, RU_LABELS_51, STRIP_TAIL,
                            en_name_from_ru_heading, titlecase_header)
# Шапку врезки гейт шапок не видит (он читает главы монстров и указатели), поэтому её
# тип и мировоззрение сверяются здесь — ТЕМИ ЖЕ словарями, что и там (#271).
from statblock_terms import (DICT, SUBTYPE_DICT, align_to_en,  # noqa: E402
                             check_dictionary_sections, dict_table, size_agreement,
                             skeleton, split_header)

# Тип существа переводится только словарём: копия в коде разошлась бы с ним молча (#256).
# Поломку САМОГО словаря гейт обязан назвать сам: он объявляет словарь источником правды,
# а гоняется отдельным шагом CI — молчать о битом источнике и краснеть его следствиями
# («EN-тип не из словаря») значит показывать симптом вместо причины.
TYPES_RU, DICT_PROBLEMS = dict_table(DICT, "Типы существ")
# Подтипы лежат отдельным файлом (их ключи совпадают с именами классов и рас) — и тоже
# читаются, а не копируются: подтип врезки сверяется наравне с типом.
SUBTYPES_RU, _SUB_PROBLEMS = dict_table(SUBTYPE_DICT, None)
# Мировоззрения и размеры словарь тоже держит: код хранит их формы по родам, которых в
# словаре нет, но базовая форма обязана сходиться — иначе правка перевода в словаре
# молчит (ревью #281).
DICT_PROBLEMS = DICT_PROBLEMS + _SUB_PROBLEMS + check_dictionary_sections()

# Отпечаток `_source.extraction` эталона: способ выемки — часть провенанса, и подменять
# его молча нельзя (у 5.2 это четыре выемки, у 5.1 — две команды резки и две заметки).
EXTRACTION_SHA_52 = "4bf3eb51f9cb2f4a5f19102ad264f58f688d0abb7732f6719db1066a2d27c985"
STRUCTURE_SHA_52 = "ed3a6cce774ba14f871d23502c358bebf83b353e5ca7609e41e221b07b0d57a9"
FIELD_COUNTS_52 = {"header": 336, "abilities": 336, "ac": 336, "hp": 336, "speed": 336, "senses": 336,
                "languages": 336, "cr": 336, "initiative": 332, "skills": 216,
                "immunities": 150, "resistances": 71, "gear": 45, "vulnerabilities": 15}

# Во врезках метки короткие («**AC** 11»), в главах — полные («- **Armor Class:** 11»).
EN_LABELS_52 = {"Gear": "gear", "Armor Class": "ac", "AC": "ac", "Hit Points": "hp",
             "HP": "hp", "Speed": "speed",
             "Initiative": "initiative", "Skills": "skills", "Senses": "senses",
             "Languages": "languages", "Immunities": "immunities",
             "Resistances": "resistances", "Vulnerabilities": "vulnerabilities"}
# RU читаем ПОЛНЫМ набором полей: числа сверяются со значением, остальные — по наличию.
# Без этого удаление 130 RU-строк «Языки: —» проходило зелёным весь CI, то есть RU-половина
# правок #260 не была защищена ничем.
RU_LABELS_52 = {"Класс доспеха": "ac", "КД": "ac", "Хиты": "hp", "Скорость": "speed",
             "Инициатива": "initiative", "Навыки": "skills", "Снаряжение": "gear",
             "Чувства": "senses", "Языки": "languages", "Иммунитеты": "immunities",
             "Сопротивления": "resistances", "Уязвимости": "vulnerabilities"}
# Заголовки внутри статблока — не имена блоков: «#### Actions» закрывает поля, а не
# открывает новый блок.
SERVICE_HEADINGS = {"traits", "actions", "bonus actions", "reactions", "legendary actions",
                    "особенности", "действия", "бонусные действия", "реакции",
                    "легендарные действия", "свойства"}
ABIL = ("str", "dex", "con", "int", "wis", "cha")
# Метки таблицы характеристик в обоих языках и в обеих формах записи.
ABIL_ROWS = {"SCORE": "score", "MOD": "mod", "SAVE": "save",
             "ЗНАЧ": "score", "МОД": "mod", "СПАС": "save"}
# Пара «характеристика — спасбросок» строки 5.1. Знаки перечислены ЯВНО: «[+-−]» — это
# диапазон U+002B…U+2212 из 8680 символов, он ловил и «Con q7», и запись вовсе без знака.
SAVE_PAIR = re.compile(r"\b(Str|Dex|Con|Int|Wis|Cha)\s+([+\u2212-]\d+)")


def signed(value: str) -> int:
    """«−6» / «+6» → −6 / 6.

    Минус U+2212 в записи законен (ради него и расширен класс знаков), поэтому
    нормализуем его ВЕЗДЕ, где запись превращается в число: неучтённый int() уносит
    трейсбеком весь накопленный отчёт, включая расхождения другой редакции.
    """
    return int(value.replace("−", "-").replace("+", ""))
ABILITIES = {"str": "str", "dex": "dex", "con": "con", "int": "int", "wis": "wis",
             "cha": "cha", "сил": "str", "лов": "dex", "тел": "con", "инт": "int",
             "мдр": "wis", "хар": "cha"}
# Первое слово шапки — размер; словари канонические, из продукционного парсера.
SIZE_PREFIX = "|".join(sorted(set(SIZES_EN) | set(SIZES_RU_TO_EN), key=len, reverse=True))
failures = []


def canon(field: str, value: str, lower_fields=("senses",), senses_comma=False,
          dash_fold=False) -> str:
    """Приведение перед сравнением — послабления этого гейта, ВСЕ СЕМЬ.

    ПЯТЬ общих и ДВА версионных. Версионное послабление включается только той редакцией,
    которой оно нужно: включённое для обеих, оно молча снимает сверку у той, где различия
    нет (так «;» → «,» сняло разделитель чувств у 255 блоков 5.2 из 336, а тире — знак
    в инициативе).

    Гасятся ровно эти вещи, и каждая намеренно:
      1) повторные пробелы схлопываются в один — перенос строки в PDF рвёт значение
         в произвольном месте;
      2) ХВОСТОВАЯ точка/запятая/точка с запятой — конвертеры теряют и добавляют её
         произвольно, поэтому в эталоне её нет ни у одного значения скорости.
         Ведущая пунктуация НЕ гасится, и форму строки в тексте держит проверка формы
         (раздел 3 ниже): без неё потерянная точка у Глиняного голема проходила молча;
      3) ПАРНЫЙ курсив («*Bless*» у Ракшаса): PDF-выемка разметки не несёт. Непарная
         звёздочка остаётся в значении и делает расхождение видимым;
      4) регистр у ЧУВСТВ — PDF пишет «Darkvision 120 ft.», мы «darkvision 120 ft.»;
         различие живёт в 252 строках чувств и не является данными;
      5) «Thieves' Cant» → «Thieves' cant» в языках: та же стилистика, 3 строки в скоупе;
      6) ВЕРСИОННОЕ: тире сводятся к одному знаку («—», «–», «−» → «-»). PDF 5.1 пишет
         «—» там, где поля нет, импорт — «-»; у 5.2 знаки совпадают, и там сверяются;
      7) ВЕРСИОННОЕ: разделитель перед пассивной Внимательностью в чувствах («;» → «,»).
         PDF 5.1 пишет запятую, импорт — точку с запятой; у 5.2 послабления нет.
    Кроме них версия может
    объявить поля, у которых не сверяется РЕГИСТР (`lower_fields`): у 5.2 это одни чувства,
    у 5.1 — семь полей, потому что PDF 5.1 печатает весь статблок со строчной. Всё
    остальное — порядок слов, скобки, числа и регистр в прочих полях — сверяется как есть.
    Регистрозависимость нашла четыре «And» в языках (Гигантский лось, Гигантская сова,
    Кошмар, Пегас), которых не видел ни один прогон до неё.
    """
    value = re.sub(r"\s+", " ", value).strip()
    if dash_fold:
        # Тире: PDF 5.1 пишет «—» там, где поля нет, импорт — «-». Знак один и тот же.
        value = value.replace("—", "-").replace("–", "-").replace("−", "-")
    value = re.sub(r"[.;,]+$", "", value)
    value = re.sub(r"\*([^*]+)\*", r"\1", value)
    if field == "senses" and senses_comma:
        # Разделитель перед пассивной Внимательностью: PDF 5.1 пишет запятую, импорт —
        # точку с запятой (как у 5.2). Различие оформления, не данных — и оно есть только
        # у 5.1: у 5.2 PDF пишет ту же точку с запятой, что и мы, поэтому там сверяется.
        value = value.replace(";", ",")
    if field in lower_fields:
        return value.lower()
    if field == "languages":
        value = value.replace("Thieves' Cant", "Thieves' cant")
    return value


def declared(note, values) -> str:
    """Проверка пометки-исключения. Пустая строка = пометка законна.

    Пометка (`xp_note`, `pb_note`) — не выключатель, а УТВЕРЖДЕНИЕ о том, что напечатано
    в PDF. Поэтому от неё требуется и то и другое: назвать все спорные числа И объяснить
    словами, что именно в источнике. Голые числа не годятся — их печатает сам текст
    расхождения, и «выполнить совет буквально» снова стало бы рецептом.
    """
    if not note:
        return ("это расхождение с таблицей. Так напечатано в PDF? Тогда объявите пометку: "
                "она обязана назвать спорные числа И сказать словами, что в источнике")
    text = str(note)
    said = {int(x) for x in numbers(text)}
    if not set(values) <= said:
        return (f"пометка «{text}» не называет все спорные числа "
                f"({', '.join(str(v) for v in values)}) — это не утверждение о PDF")
    if len(re.sub(r"[^A-Za-zА-Яа-яЁё]", "", text)) < 12:
        return f"пометка «{text}» — голые числа без утверждения о том, что в PDF"
    return ""


def numbers(value: str) -> list:
    """Числа значения; разряды пишутся по-разному («22,000» и «22 000»)."""
    return re.findall(r"[+-]?\d+", re.sub(r"(?<=\d)[,   ](?=\d\d\d\b)", "", value))


HEADINGS = {}
SEEN_IN = {}


def read_blocks(path: Path, labels: dict, ru: bool, where: str = "",
                strict_headings: bool = True, cr_labels: str = "CR|ПО",
                foreign_labels=()) -> list:
    """[(EN-имя, {поле: значение})] из главы статблоков или из блока-врезки.

    Возвращаем СПИСОК, а не словарь: дубли имён ловятся при слиянии, поэтому терять их
    здесь нельзя. Шесть блоков живут вне глав монстров — в заклинаниях и магпредметах,
    оформленные цитатой (`> #### Giant Fly`). Их поля те же, поэтому снимаем префикс
    цитаты и читаем так же; в эталоне они помечены `outside_chapters`.
    """
    where = where or path.name
    out, names, name, block, closed = [], [], None, None, None

    def flush():
        if name is not None:
            names.append(name)
        if name and block:
            out.append((name, block))

    for line in path.read_text(encoding="utf-8").split("\n"):
        s = re.sub(r"^>\s?", "", line).strip()
        m = re.match(r"^#{2,6} (.+)$", s)
        if m and m.group(1).strip().rstrip(":.").lower() in SERVICE_HEADINGS:
            # «#### Actions» внутри блока — конец полей блока, а не новый блок. Имя
            # запоминаем: строка поля ПОСЛЕ служебного заголовка — расхождение, а не
            # молчаливый пропуск (её видит только читатель, но не сверка).
            closed = name or closed
            flush()
            name, block = None, None
            continue
        m = re.match(r"^#{2,4} (.+)$", s)
        if m:
            flush()
            closed = None
            title = m.group(1).strip()
            if ru:
                # RU-заголовок несёт оригинал в скобках: «Аболет (Aboleth)», а у 5.1 ещё и
                # с таксономическим хвостом — «(Adult Black Dragon (Chromatic))». Разбор
                # общий с гейтом шапок, поэтому имена сходятся у обоих.
                # У 5.1 таксономический хвост стоит и в EN-заголовке, и в RU («… (Adult
                # Black Dragon) (Цветной)»), причём по-разному, поэтому сводим обе стороны
                # к имени без хвоста и подставляем EN-ключ (см. by_stripped ниже).
                name = en_name_from_ru_heading(title) if "(" in title else None
            else:
                name = title
            block = {}
            continue
        for label in foreign_labels:
            # Метка ЧУЖОЙ редакции («- **Initiative:**» в главе 5.1, «- **Saving Throws:**»
            # в главе 5.2) не разбирается словарём версии, поэтому дописанная строка была бы
            # невидима для сверки — ровно тот дефект импорта, ради которого заведён гейт.
            # Проверяем ДО ветки «блок ещё не открыт»: форма строки не зависит от того,
            # открыт ли блок, а осиротевшая строка после служебного заголовка — самая
            # частая форма импортного мусора, и на пересечении двух проверок она терялась.
            if re.match(rf"^(?:- )?\*\*{label}:?\*\*", s):
                # Совет буквально: почините МЕТКУ, а не удаляйте строку. Собственные метки
                # редакций местами различаются лишь регистром («Класс доспеха» у 5.2 против
                # «Класс Доспеха» у 5.1), поэтому сюда попадает и опечатка в своей метке.
                failures.append(f"{where} «{name or closed or 'до первого блока'}»: "
                                f"строка «{s[:40]}» — метка не той редакции SRD (или "
                                f"опечатка в своей): почините метку")
        if block is None:
            if closed and re.match(r"^(?:- )?\*\*(?:%s|%s):?\*\*"
                                   % ("|".join(labels), cr_labels), s):
                failures.append(f"{where} «{closed}»: строка поля «{s[:40]}» стоит после "
                                f"служебного заголовка — в сверку она не попадает")
            continue
        m = re.match(r"^\*([^*]+)\*$", s)
        if m and "header" not in block and re.match(SIZE_PREFIX, m.group(1), re.I):
            block["header"] = m.group(1).strip()
            continue
        for label, key in labels.items():
            # «Gear» и «CR» в наших файлах записаны без двоеточия, остальные поля — с ним;
            # форма одинакова в обоих языках и проверяется ниже, в разделе 3.
            # В главах поля идут списком («- **Speed:** …»), во врезках — абзацами.
            m = re.match(rf"^(?:- )?\*\*{label}:?\*\*:?\s*(.+)$", s)
            if not m:
                continue
            if key in block:
                # Повторная строка того же поля: в сверку идёт первая, вторая живёт в
                # тексте невидимкой для гейта — поэтому она сама по себе расхождение.
                failures.append(f"{where} «{name}»: поле «{key}» записано дважды "
                                f"(«{block[key]}» и «{m.group(1).strip()}»)")
                continue
            block[key] = m.group(1).strip()
        # Таблица характеристик. В главах она транспонирована (строки ЗНАЧ/МОД/СПАС по
        # колонкам характеристик), во врезках — обычная, строка на характеристику.
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            row = cells[0].upper() if cells else ""
            head = [ABILITIES.get(c.lower()) for c in cells[1:7]]
            # Хвостовая колонка с чужим именем давала None и гасила ветку целиком —
            # поэтому шапкой считаем строку, где имена характеристик стоят хотя бы в трёх
            # первых ячейках, а длину сверяем ниже вместе с порядком.
            head_51 = [ABILITIES.get(c.lower()) for c in cells]
            if len(cells) > 2 and all(head_51[:3]) and cells[0]:
                # Шапка формы 5.1 («| STR | DEX | … |», без ведущей пустой ячейки): разбор
                # строки значений ниже позиционный, поэтому и перестановка колонок, и
                # ОБРЕЗКА шапки обязаны быть видны — оба типовые артефакты колонной резки,
                # из которой этот текст и приехал.
                if len(cells) != 6 or head_51 != list(ABIL):
                    failures.append(f"{where} «{name}»: колонки таблицы характеристик идут "
                                    f"{cells} — ожидался порядок СИЛ ЛОВ ТЕЛ ИНТ МДР ХАР "
                                    f"(шесть колонок)")
                continue
            if not cells[0] and len(cells) > 6 and all(head):
                # Шапка таблицы: порядок колонок держит весь разбор ниже (он позиционный),
                # поэтому перестановка колонок обязана быть видна.
                if head != list(ABIL):
                    failures.append(f"{where} «{name}»: колонки таблицы характеристик идут "
                                    f"{cells[1:7]} — ожидался порядок СИЛ ЛОВ ТЕЛ ИНТ МДР ХАР")
            # Знаки перечислены явно, как и в SAVE_PAIR: «[+-−]» — диапазон из 8680
            # символов, в который попадают «9 (q1)» и «9 (Ω1)».
            paired = [re.fullmatch(r"(\d+) \(([+\u2212-]?\d+)\)", c) for c in cells[:6]]
            if len(cells) >= 6 and all(paired):
                # Форма 5.1: одна строка «21 (+5)» на характеристику, спасброски живут
                # отдельным полем. Форма 5.2 — три строки на таблицу, см. ниже.
                block["abilities"] = {a: [m.group(1), m.group(2).replace("−", "-")]
                                      for a, m in zip(ABIL, paired)}
            if row in ABIL_ROWS and len(cells) > 6:
                block.setdefault("_rows", {})[ABIL_ROWS[row]] = cells[1:7]
            elif cells and ABILITIES.get(cells[0].lower()) and len(cells) > 3:
                block.setdefault("abilities", {})[ABILITIES[cells[0].lower()]] = cells[1:4]
            continue
        m = re.match(rf"^(?:- )?\*\*(?:{cr_labels}):?\*\*:?\s*(.+)$", s)
        if m:
            if "cr" in block:
                failures.append(f"{where} «{name}»: поле «cr» записано дважды")
            else:
                block["cr"] = m.group(1).strip()
    flush()
    for _n, _b in out:
        rows = _b.pop("_rows", None)
        if rows and set(rows) == {"score", "mod", "save"}:
            _b["abilities"] = {a: [rows["score"][i], rows["mod"][i], rows["save"][i]]
                               for i, a in enumerate(ABIL)}
        elif rows:
            failures.append(f"{where} «{_n}»: в таблице характеристик нет строк "
                            f"{', '.join(sorted({'score', 'mod', 'save'} - set(rows)))}")
    # Дубль ЗАГОЛОВКА — сверх дубля блока: скопированный заголовок без полей блоком не
    # становится и иначе был бы невидим. В главах монстров каждый заголовок — статблок,
    # а во врезочных главах имя существа законно совпадает с именем заклинания
    # («### Giant Insect» и врезка `> #### Giant Insect`), поэтому там проверки нет.
    if strict_headings:
        seen = HEADINGS.setdefault(where.rsplit("/", 1)[0], {})
        for n in names:
            if not n:
                continue
            if n in seen:
                failures.append(f"{where}: заголовок «{n}» уже был в {seen[n]}")
            else:
                seen[n] = where
    return out


def merge(dst: dict, pairs: list, where: str, only=None):
    """Слияние блоков с проверкой дублей — по ВСЕМ главам сразу.

    Дубль опасен не сам по себе: второй блок молча вытесняет первый из сверки, и порча
    настоящего блока уезжает в прод-API незамеченной. Поэтому проверка живёт здесь, а не
    на переходе к следующему заголовку внутри одного файла.
    """
    for name, block in pairs:
        if only is not None and name not in only:
            continue
        lang = where.rsplit("/", 1)[0]
        if name in dst:
            failures.append(f"{where}: статблок «{name}» уже прочитан "
                            f"из {SEEN_IN.get((lang, name), 'другой главы')}")
            continue
        SEEN_IN[(lang, name)] = where
        dst[name] = block


def index_rows(path: Path) -> list:
    rows = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        if not line.startswith("| ") or line.startswith("|---"):
            continue
        rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows[1:]


def cr_value(cr: str) -> str:
    """«10 (XP 5,900, or 7,200 in lair; PB +4)» → «10»."""
    m = re.match(r"^([\d/]+)", cr.strip())
    return m.group(1) if m else cr.strip()


def ac_value(ac: str) -> str:
    """«17 (natural armor)» → «17»: указатель 5.1 несёт только число.

    Послабление ВЕРСИОННОЕ (`ac_bare_in_index`): у 5.1 скобка с видом доспеха стоит в
    статблоке у 209 значений из 320 и в указателе её нет, у 5.2 таких значений ноль — там
    указатель обязан совпадать со статблоком дословно. Безусловное, оно снимало бы
    сверку формы у 5.2 «про запас», а импорт как раз такие хвосты и приносит.
    """
    m = re.match(r"^(\d+)", ac.strip())
    return m.group(1) if m else ac.strip()


def hp_value(hp: str) -> str:
    """«150 (20d10 + 40)» → «150»."""
    m = re.match(r"^(\d+)", hp.strip())
    return m.group(1) if m else hp.strip()


def md_table(path: Path, title: str) -> list:
    """Строки таблицы markdown, идущей за строкой «Table: <title>»/«Таблица: <title>».

    Разделитель шапки в корпусе пишется двумя формами — `|---|` и выравненной `|:---:|`,
    поэтому распознаём обе: иначе строка выравнивания уезжает в данные и валит разбор
    стектрейсом на легальной разметке.
    """
    rows, inside = [], False
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.strip().endswith(title):
            inside = True
            continue
        if not inside:
            continue
        if line.startswith("|"):
            if not re.match(r"^\|[\s:|-]+$", line.strip()):
                rows.append([c.strip() for c in line.strip().strip("|").split("|")])
            continue
        if rows:
            break
    if not rows:
        failures.append(f"канон: в {path.name} нет таблицы «{title}» — сверять ПО нечем")
    return rows[1:]


def read_xp_table(path: Path, title: str) -> dict:
    """{ПО: (варианты опыта)} из публикуемой таблицы «Опыт по показателю опасности»."""
    out = {}
    for cells in md_table(path, title):
        if len(cells) < 2 or not re.search(r"\d", cells[1]):
            failures.append(f"канон: в таблице «{title}» ({path.name}) строка "
                            f"«{' | '.join(cells)}» без значения опыта")
            continue
        if cells[0] in out:
            failures.append(f"канон: в таблице «{title}» ({path.name}) ПО «{cells[0]}» дважды")
        out[cells[0]] = tuple(int(x) for x in numbers(cells[1]))
    return out


def read_pb_table(path: Path, title: str) -> dict:
    """{ПО: бонус} из публикуемой таблицы «Бонус мастерства», диапазоны развёрнуты."""
    out = {}
    for cells in md_table(path, title):
        label = cells[0].strip() if cells else ""
        digits = re.sub(r"[^\d]", "", cells[1]) if len(cells) > 1 else ""
        if not label or not digits:
            failures.append(f"канон: в таблице «{title}» ({path.name}) строка "
                            f"«{' | '.join(cells)}» без ПО или без бонуса")
            continue
        if "/" in label:
            # Дробный ПО — одна строка, а не диапазон: «1/8» это не «с 1 по 8».
            if label in out:
                failures.append(f"канон: в таблице «{title}» ({path.name}) ПО {label} дважды")
            out[label] = int(digits)
            continue
        bounds = [int(x) for x in re.findall(r"\d+", label)]
        if not bounds:
            failures.append(f"канон: в таблице «{title}» ({path.name}) строка "
                            f"«{' | '.join(cells)}» без ПО")
            continue
        for value in range(bounds[0], bounds[-1] + 1):
            if str(value) in out:
                failures.append(f"канон: в таблице «{title}» ({path.name}) ПО {value} дважды")
            out[str(value)] = int(digits)
    return out


CHECKED = []
# Сколько сравнений гасит каждое версионное послабление — счётчик носителей для пина.
SAVED = Counter()



def gender_option(version: str) -> set:
    """Объявленные послабления из фикстуры ГЕЙТА ШАПОК этой редакции.

    Версионные послабления живут в шапке фикстуры («# опция: …»), а не в коде, — и оба
    гейта обязаны читать одно и то же объявление, иначе редакция с разрешённым разнобоем
    рода красится здесь на верном тексте (ревью #281).
    """
    fixture = SCRIPTS / f"fixtures/{version}-statblock-headers.tsv"
    if not fixture.is_file():
        return set()
    return set(re.findall(r"^#\s*опция:\s*(\S+)\s*$",
                          fixture.read_text(encoding="utf-8"), re.M))


def sidebar_header(name: str, en_header: str, ru_header: str, chapter_aligns: dict,
                   neuter_ok: bool = False) -> list:
    """Расхождения ТИПА, МИРОВОЗЗРЕНИЯ и согласования РАЗМЕРА в шапке врезки.

    Значение размера (сведение к EN) сверяется выше, у вызывающего; здесь — род
    прилагательного и регистр, как это делает гейт шапок для главы.

    Тип сверяется со словарём перевода — тем же, что у гейта шапок, — и порегистрово:
    в шапке он пишется словарным термином с прописной. Мировоззрение сверяется дважды:
    по ЗНАЧЕНИЮ (сводится к EN) и по ФОРМЕ (как пишет глава монстров этой редакции) —
    иначе врезка молча жила бы по своей конвенции, как и было до #271.
    """
    out = []
    # Пробельный мусор конвертации: разделитель шапки — запятая с ОДНИМ обычным пробелом.
    # Сравнение его не видит по построению (разрез нормализует, токенайзер пробелы
    # отбрасывает), поэтому сверяем сырую строку до разбора (ревью #281).
    if "\u00a0" in ru_header:
        out.append(f"RU «{name}» шапка: неразрывный пробел (U+00A0) — мусор конвертации")
    if re.search(r"\s{2,}", ru_header):
        out.append(f"RU «{name}» шапка: двойной пробел — мусор конвертации")
    if not re.search(r",\u0020", ru_header) and "," in ru_header:
        out.append(f"RU «{name}» шапка: после запятой мировоззрения нет пробела")
    en_parts, ru_parts = split_header(en_header), split_header(ru_header)
    if en_parts is None or ru_parts is None:
        side = "у EN" if en_parts is None else "у перевода"
        out.append(f"RU «{name}» шапка: мировоззрение не отделено запятой {side}: "
                   f"«{en_header if en_parts is None else ru_header}»")
        return out
    # Род и регистр прилагательного размера — та же сверка, что у главы: до ревью #281
    # у врезки размер сводился к EN («средний» и «Средняя» одинаково дают Medium), и
    # ни «*Средний Нежить*», ни «*большой Дракон*» не были видны.
    problem, _unknown, _kind = size_agreement(ru_header, TYPES_RU.values(), SIZES_RU_TO_EN)
    if problem:
        out.append(f"RU «{name}» шапка: {problem}")
    if ru_parts[0][:1].islower():
        out.append(f"RU «{name}» шапка: «{ru_parts[0]}» начинается со строчной — размер "
                   f"в шапке пишется с прописной")
    en_skeleton = skeleton(en_parts[0], "en", TYPES_RU, SUBTYPES_RU, SIZES_RU_TO_EN)
    ru_skeleton = skeleton(ru_parts[0], "ru", TYPES_RU, SUBTYPES_RU, SIZES_RU_TO_EN)
    unknown = [word for kind, word in ru_skeleton if kind == "?"]
    if any(kind == "?" for kind, _ in en_skeleton):
        out.append(f"RU «{name}» шапка: EN-тип «{en_parts[0]}» разбирается не целиком "
                   f"({[w for k, w in en_skeleton if k == '?']}) — сверять перевод не с чем")
    elif ru_skeleton != en_skeleton:
        # Сравниваем шапку ЦЕЛИКОМ, а не набор найденных терминов: иначе постороннее
        # слово («Зверь-мутант»), подмена связки («или» → «и») и правка подтипа в скобках
        # остаются невидимыми — тип сверялся бы слабее, чем в главе.
        detail = (f"не из словаря: {unknown}" if unknown
                  else f"разбор «{ru_skeleton}» ≠ EN «{en_skeleton}»")
        out.append(f"RU «{name}» шапка: тип «{ru_parts[0]}» ≠ EN «{en_parts[0]}» — {detail}")
    ru_align, _ = align_to_en(ru_parts[1], neuter_ok=neuter_ok)
    if ru_align is None:
        out.append(f"RU «{name}» шапка: мировоззрение «{ru_parts[1]}» не из словаря "
                   f"(EN «{en_parts[1]}»)")
    elif ru_align.lower() != en_parts[1].lower():
        out.append(f"RU «{name}» шапка: мировоззрение «{ru_parts[1]}» ({ru_align}) "
                   f"≠ EN «{en_parts[1]}»")
    else:
        forms = chapter_aligns.get(ru_align.lower())
        if not forms:
            out.append(f"RU «{name}» шапка: форму мировоззрения «{ru_parts[1]}» сверить "
                       f"не с чем — глава монстров не пишет «{ru_align}» ни разу")
        elif ru_parts[1] not in forms:
            out.append(f"RU «{name}» шапка: мировоззрение «{ru_parts[1]}» написано не как "
                       f"в главе монстров — там {sorted(forms)}. Форму главы держит "
                       f"ALIGN_CASE в гейте шапок: если он зелёный, расходится врезка")
    return out


def check_version(V: dict) -> None:
    """Все проверки одной версии SRD. Различия версий живут в конфигурации, а не в копии
    кода: 5.1 и 5.2 пишут статблок по-разному (у 5.1 нет инициативы и снаряжения, зато
    есть спасброски отдельной строкой, а характеристики стоят одной строкой «21 (+5)»),
    но проверяем мы их одинаково строго.
    """
    # Официальная таблица «ПО → опыт» читается ИЗ ПУБЛИКУЕМОГО КОНТЕНТА (глава «Монстры»), а не
    # держится литералом: иначе экземпляров знания становится два и порча канона — та, что уедет
    # читателю, — не краснеет нигде. Она же делает значение ПО проверяемым САМО ПО СЕБЕ:
    # согласованная подделка `cr` в эталоне и в тексте больше не проходит.
    MONSTERS_EN = ROOT / f'src/dnd/{V['version']}/en/{V['monsters_chapter']}'
    MONSTERS_RU = ROOT / f'src/dnd/{V['version']}/ru/{V['monsters_chapter']}'
    XP_BY_CR = read_xp_table(MONSTERS_EN, "Experience Points by Challenge Rating")
    PB_BY_CR = read_pb_table(MONSTERS_EN, "Proficiency Bonus by Challenge Rating")
    # RU-копия таблиц — не «перевод той же таблицы», а второй экземпляр тех же чисел, и он
    # тоже уезжает читателю. Сверяем поэлементно: иначе порча русской половины зелёная.
    XP_BY_CR_RU = read_xp_table(MONSTERS_RU, "Очки опыта по показателю опасности")
    PB_BY_CR_RU = read_pb_table(MONSTERS_RU, "Бонус мастерства по показателю опасности")
    for _table, _en, _ru in (("опыта", XP_BY_CR, XP_BY_CR_RU), ("бонуса", PB_BY_CR, PB_BY_CR_RU)):
        for _cr in sorted(set(_en) | set(_ru)):
            if _en.get(_cr) != _ru.get(_cr):
                failures.append(f"канон: таблица {_table}, ПО {_cr} — EN «{_en.get(_cr)}», "
                                f"RU «{_ru.get(_cr)}»")
    # ПОЛНОТА таблиц пришпилена: пустая или обрезанная таблица — это не «нечего проверять»,
    # а исчезнувший канон. Без этого удаление строки главы гасило всю сверку ПО молча.
    CR_LADDER = ["0", "1/8", "1/4", "1/2"] + [str(_i) for _i in range(1, 31)]
    for _cr in CR_LADDER:
        if _cr not in XP_BY_CR:
            failures.append(f"канон: в таблице опыта нет ПО {_cr} — таблица неполна")
        if _cr not in PB_BY_CR and ("/" not in _cr or V['pb_table_fractions']):
            failures.append(f"канон: в таблице бонуса мастерства нет ПО {_cr} — таблица неполна")
    # Дробные строки — тоже носитель, и он версионный: 5.1 печатает «1/8», «1/4», «1/2»
    # отдельными строками, 5.2 задаёт бонус диапазонами и дробей не печатает вовсе.
    if V['pb_table_fractions'] != any("/" in _cr for _cr in PB_BY_CR):
        failures.append("канон: дробные строки таблицы бонуса мастерства есть/нет вопреки "
                        "конфигурации редакции")
    # Бонус мастерства выводится из ПО формулой (2 + (ПО−1)//4, у ПО 0 и дробного — 2),
    # поэтому согласованная порча ОБЕИХ половин таблицы ловится и там, где производному
    # инварианту не за что зацепиться: у ПО 18 и 25–29 носителей со спасбросками нет.
    for _cr, _pb in sorted(PB_BY_CR.items()):
        _want_pb = 2 if "/" in _cr or _cr == "0" else 2 + (int(_cr) - 1) // 4
        if _pb != _want_pb:
            failures.append(f"канон: бонус мастерства ПО {_cr} — +{_pb}, а по правилу "
                            f"+{_want_pb} (2 + (ПО−1)//4, у ПО 0 и дробного — 2)")
    if len(XP_BY_CR) != len(CR_LADDER):
        failures.append(f"канон: в таблице опыта {len(XP_BY_CR)} строк вместо {len(CR_LADDER)}")
    # ПО дробное — бонус тот же, что у ПО 0. Подставляем ТОЛЬКО если таблица редакции
    # своей строки не дала: у 5.1 дробные ПО напечатаны отдельными строками, и
    # безусловная подстановка выбрасывала прочитанное — три строки канона, уезжающие
    # читателю, не сверялись ничем, даже согласованно испорченные в обоих языках.
    # Прочитанное значение дробной строки сверяет формула выше — своей проверки здесь
    # больше нет: она дублировала формулу на порче и лгала на пропаже строки ПО 0
    # («+2 ≠ +None» тремя строками). Подставляем только там, где редакция дробей не
    # печатает (5.2 задаёт бонус диапазонами ПО).
    for _fraction in ("1/8", "1/4", "1/2"):
        PB_BY_CR.setdefault(_fraction, PB_BY_CR.get("0", 2))


    def pb_by_cr(cr):
        """Бонус мастерства по ПО — по таблице из главы «Монстры»."""
        return PB_BY_CR.get(cr, 0)

    cr_labels = f"{V['cr_label_en']}|{V['cr_label_ru']}"
    # Имена блоков у редакций пересекаются (214 общих, среди них Аболет, Лич, Анкег),
    # поэтому каждое расхождение обязано назвать редакцию. Одна обёртка вместо префикса
    # в восьмидесяти вызовах: помечаем всё, что добавилось за этот прогон.

    try:
        _fixture = json.loads(V['fixture'].read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        # Самый вероятный вход — не «файл не той формы», а «файла нет / файл битый»
        # (оборванный checkout, конфликт слияния). Гейт общий для двух редакций и падать
        # из-за одной фикстуры, гася отчёт другой, не должен.
        failures.append(f"эталон {V['version']} ({V['fixture'].name}) не читается: {exc}")
        return
    # Эталон — выемка из PDF, поэтому у него есть шапка с источником и лицензией;
    # сами блоки лежат под ключом «blocks», чтобы служебные поля не путались с именами существ.
    if (not isinstance(_fixture, dict)
            or "blocks" not in _fixture or "_source" not in _fixture):
        # Не выход из процесса: гейт общий для двух редакций, и упавшая фикстура одной
        # иначе гасит отчёт другой. Сообщение называет и редакцию, и файл.
        failures.append(f"эталон {V['version']} ({V['fixture'].name}): нет ключа «blocks» "
                        f"или «_source» — файл не той формы")
        return
    expected = _fixture["blocks"]
    _src = _fixture["_source"]
    for _key, _want in (("pdf", V['pdf']), ("sha256", V['sha256']),
                        ("pages", V['pages']), ("page_size_pt", V['page_size'])):
        if _src.get(_key) != _want:
            failures.append(f"эталон: _source.{_key} = «{_src.get(_key)}», ожидалось «{_want}»")
    # Лицензия и способ пересборки — тоже пара «имя → значение»: «непустое» пропускает
    # и «Proprietary», и путь в никуда.
    if _src.get("license") != V['license']:
        failures.append(f"эталон: _source.license «{_src.get('license')}» ≠ «{V['license']}»")
    else:
        # Файл лицензии — артефакт комплаенса, и путь к нему берётся из САМОЙ шапки эталона
        # (иначе увод пути в шапке ничего не меняет), а содержимое сверяется отпечатком:
        # существование файла не отличает лицензию от пустого файла и от текста с обратным
        # смыслом. Отпечаток меняется только вместе с текстом лицензии — осознанно.
        _lic = re.search(r"src/dnd/\S+/LICENSE\.md", _src["license"])
        _lic_path = ROOT / _lic.group(0) if _lic else None
        if _lic_path is None:
            failures.append("эталон: _source.license не называет файл лицензии редакции")
        elif not _lic_path.is_file():
            failures.append(f"эталон: файла лицензии {_lic.group(0)} нет")
        elif hashlib.sha256(_lic_path.read_bytes()).hexdigest() != V['license_sha']:
            failures.append(f"эталон: содержимое {_lic.group(0)} не то, которым снят эталон "
                            f"(отпечаток файла лицензии не сошёлся)")
    if _src.get("regenerate") != V['regenerate']:
        failures.append(f"эталон: _source.regenerate «{_src.get('regenerate')}» ≠ «{V['regenerate']}»")
    elif not (ROOT / V['regenerate']).is_file():
        failures.append(f"эталон: скрипта пересборки «{V['regenerate']}» нет")
    # Состав шапки целиком: удаление служебной заметки (или дописывание своих ключей)
    # иначе не оставляет следа — пришпилены только перечисленные выше пары.
    if set(_src) != {"pdf", "sha256", "pages", "page_size_pt", "license", "extraction",
                     "regenerate", "note"}:
        failures.append(f"эталон: набор ключей _source = {sorted(_src)}")
    else:
        # …и заметка обязана НАЗЫВАТЬ каждую пометку, которой эталон разрешает объявлять
        # опечатку источника: пометка, о которой шапка эталона не знает, объявлением не
        # является. Длины мало — она пропускала любую отписку в сорок букв.
        _note = str(_src.get("note"))
        _unnamed = [k for k in NOTE_KEYS if k not in _note]
        if _unnamed:
            failures.append(f"эталон: _source.note не называет пометки {', '.join(_unnamed)} "
                            f"— шапка эталона не знает, чем объявляются опечатки PDF")
        # Буквы считаем ПОСЛЕ вычёркивания самих имён пометок: иначе голое перечисление
        # ключей проходит обе половины проверки, ничего при этом не объясняя.
        elif len(re.sub(r"[^A-Za-zА-Яа-яЁё]", "",
                        re.sub("|".join(NOTE_KEYS), " ", _note))) < 40:
            failures.append("эталон: _source.note не объясняет словами, как объявляются "
                            "опечатки самого PDF")
    _extraction = _src.get("extraction")
    # Записи сверяются ЦЕЛИКОМ (отпечатком): по первым двадцати символам две команды
    # `pdftotext` неразличимы, и подмена параметров резки проходила молча.
    _ex_sha = hashlib.sha256(json.dumps(_extraction, ensure_ascii=False).encode("utf-8")).hexdigest()
    if not isinstance(_extraction, list) or _ex_sha != V['extraction_sha']:
        failures.append("эталон: _source.extraction — не тот способ выемки, которым снят "
                        "эталон (отпечаток списка не сошёлся)")

    # --- 0. Состав эталона ----------------------------------------------------------------
    # Без этого согласованное удаление поля из эталона И из обоих текстов было зелёным:
    # поле просто переставало существовать для гейта.
    # Считаем ПО ПОЛЯМ: сумма компенсируется (снял поле у одного блока, выдумал у другого),
    # состав — нет. Текст расхождения называет поле и обе стороны, чтобы правка эталона была
    # видна ревьюеру, а не выглядела подгонкой константы.
    # Отпечаток СТРУКТУРЫ (какой блок какие поля несёт): счётчик по полям не видит обмена —
    # снял «resistances» у одного блока, выдумал у другого, сумма и состав те же.
    _structure = "\n".join(f"{n}\t{','.join(sorted(k for k in f if k not in META_KEYS))}"
                           for n, f in sorted(expected.items()))
    _digest = hashlib.sha256(_structure.encode("utf-8")).hexdigest()
    if _digest != V['structure_sha']:
        failures.append("состав эталона по блокам изменился: набор полей у блоков не тот, "
                        "что снят с PDF (отпечаток структуры не сошёлся)")
    # Версионный выключатель обязан иметь НОСИТЕЛЯ: без пина случайный (или скопированный
    # в конфигурацию будущей редакции) `pb_in_cr: False` молча снимает сверку бонуса
    # мастерства — у 5.2 бонус стоит в ПО у 331 блока, а инвариант спасбросков прикрывает
    # лишь те из них, где спасбросок выше модификатора.
    # …то же и для послабления указателя: скобка с видом доспеха либо есть у редакции,
    # либо нет, и переворот флага не должен проходить молча.
    _ac_paren = sum(1 for f in expected.values() if "(" in f.get("ac", ""))
    if V['ac_bare_in_index'] and not _ac_paren:
        failures.append("состав эталона: ac_bare_in_index включён, а скобки в КД нет ни у "
                        "одного блока — послаблению нечего гасить")
    if not V['ac_bare_in_index'] and _ac_paren:
        failures.append(f"состав эталона: ac_bare_in_index выключен, а скобка в КД стоит "
                        f"у {_ac_paren} блоков — указатель сверяется не с той формой")
    _with_pb = sum(1 for f in expected.values() if re.search(r"PB \+\d+", f.get("cr", "")))
    if V['pb_in_cr'] and not _with_pb:
        failures.append("состав эталона: pb_in_cr включён, а бонуса мастерства нет ни в "
                        "одной строке ПО — сверять нечего")
    if not V['pb_in_cr'] and _with_pb:
        failures.append(f"состав эталона: pb_in_cr выключен, а бонус мастерства стоит в ПО "
                        f"у {_with_pb} блоков — сверка снята с носителей")
    _lair = sum(1 for f in expected.values() if "in lair" in f.get("cr", ""))
    if _lair != V['lair_blocks']:
        failures.append(f"состав эталона: логовая оговорка у {_lair} блоков, а по PDF "
                        f"у {V['lair_blocks']}")
    _have = Counter(k for f in expected.values() for k in f if k not in META_KEYS)
    _ability_cells = sum(len(v) for f in expected.values()
                         for v in f.get("abilities", {}).values())
    if _ability_cells != V['ability_cells']:
        failures.append(f"состав эталона: ячеек характеристик {_ability_cells}, "
                        f"а по PDF {V['ability_cells']}")
    for _name, _f in expected.items():
        if "saves_note" in _f and "saves_repo" not in _f:
            # Пометка без предмета — объявление без утверждения: объявлять нечего, пока
            # текст и PDF совпадают.
            failures.append(f"эталон «{_name}»: saves_note объявлена, а saves_repo нет — "
                            f"пометке нечего объявлять")
    # Считаем по ТОЙ стороне, которую ждём в тексте: иначе дописанная через saves_repo
    # пара не попадала в счётчик и подмена состава оставалась невидимой.
    _saves_pairs = sum(len(SAVE_PAIR.findall(f.get("saves_repo", f.get("saves", ""))))
                       for f in expected.values())
    if _saves_pairs != V['saves_pairs']:
        failures.append(f"состав эталона: пар «характеристика — спасбросок» {_saves_pairs}, "
                        f"а по PDF {V['saves_pairs']}")
    _cells = sum(_have.values()) - _have.get("abilities", 0) + _ability_cells
    for _key in sorted(set(_have) | set(V['field_counts'])):
        if _have.get(_key, 0) != V['field_counts'].get(_key, 0):
            failures.append(f"состав эталона: поле «{_key}» у {_have.get(_key, 0)} блоков, "
                            f"а по PDF у {V['field_counts'].get(_key, 0)}")
    for _name, _f in sorted(expected.items()):
        # Статблок ОБЪЕКТА (аппарат краба во врезке магпредметов) — не существо: у него нет
        # ни шапки «размер тип, мировоззрение», ни таблицы характеристик, ни чувств с
        # языками. Он объявлен пометкой, а не выпал из состава молча.
        for _key in (V['object_required'] if _f.get("object_block") else V['required']):
            if _key not in _f:
                failures.append(f"эталон «{_name}»: нет обязательного поля «{_key}»")
        for _key in V.get('required_in_chapters', ()):
            if _key not in _f and not _f.get("outside_chapters"):
                failures.append(f"эталон «{_name}»: нет поля «{_key}» (его нет только у врезок)")

    en_dir = ROOT / f'src/dnd/{V['version']}/en'
    ru_dir = ROOT / f'src/dnd/{V['version']}/ru'
    en_blocks, ru_blocks = {}, {}
    for chapter in V['chapters']:
        merge(en_blocks, read_blocks(en_dir / chapter, V['en_labels'], False, f"{V['version']} en/{chapter}",
                     cr_labels=cr_labels, foreign_labels=V['foreign_labels']['en']),
              f"{V['version']} en/{chapter}")
        merge(ru_blocks, read_blocks(ru_dir / chapter, V['ru_labels'], True, f"{V['version']} ru/{chapter}",
                     cr_labels=cr_labels, foreign_labels=V['foreign_labels']['ru']),
              f"{V['version']} ru/{chapter}")
    # Блоки-врезки: заклинания и магические предметы. Список ЗАКРЫТ и живёт в конфигурации
    # версии, а не выводится из фикстуры: иначе удаление врезки из эталона молча
    # выключало бы её проверку.
    for _name in V['outside']:
        if not expected.get(_name, {}).get("outside_chapters"):
            failures.append(f"эталон: блок-врезка «{_name}» пропал или потерял пометку")
    # Пометка `object_block` снимает с блока ВСЕ обязательные поля, поэтому её список тоже
    # закрыт и живёт в конфигурации: иначе одна строка в эталоне снимала бы последнего
    # сторожа состава с любого блока — счётчики и отпечаток структуры автор перегенерирует
    # штатно, а требование обязательных полей перегенерации не поддаётся.
    for _name in V['object_blocks']:
        if not expected.get(_name, {}).get("object_block"):
            failures.append(f"эталон: статблок объекта «{_name}» пропал или потерял пометку")
    for _name, _f in expected.items():
        if _f.get("object_block") and _name not in V['object_blocks']:
            failures.append(f"эталон: блок «{_name}» помечен статблоком объекта, но нет в "
                            f"списке V['object_blocks']")
    for _name, _f in expected.items():
        if _f.get("outside_chapters") and _name not in V['outside']:
            failures.append(f"эталон: блок «{_name}» помечен как врезка, но нет в списке V['outside']")
    for chapter in V['sidebar_chapters']:
        for src, dst, labels, ru, lang in ((en_dir, en_blocks, V['en_labels'], False, "en"),
                                           (ru_dir, ru_blocks, V['ru_labels'], True, "ru")):
            path = src / chapter
            if not path.exists():
                continue
            pairs = read_blocks(path, labels, ru, f"{V['version']} {lang}/{chapter}", strict_headings=False,
                            cr_labels=cr_labels, foreign_labels=V['foreign_labels'][lang])
            # Врезочные главы читаются тем же разбором, что и главы монстров, поэтому в них
            # тоже видно «блок есть в тексте, но не в эталоне»: статблоком считаем всё, у
            # чего есть шапка и КД с хитами — прочие `####` в заклинаниях этому не отвечают.
            for name, block in pairs:
                # Статблоком считаем и блок БЕЗ шапки размера: у объектов её нет вовсе,
                # и по прежнему критерию аппарат краба был невидим и для сверки, и для
                # сторожа полноты — четыре его поля не держало ничто.
                if name not in V['outside'] and ("header" in block
                                                 or {"ac", "hp"} <= set(block)):
                    failures.append(
                        f"{lang}/{chapter}: статблок «{name}» есть в тексте, но не в эталоне PDF")
            merge(dst, pairs, f"{V['version']} {lang}/{chapter}", only=set(V['outside']))

    # --- 1. EN против эталона PDF ---------------------------------------------------------
    for name, fields in sorted(expected.items()):
        got = en_blocks.get(name)
        if got is None:
            failures.append(f"EN: статблок «{name}» из эталона не найден")
            continue
        # Лишнее поле в тексте — тоже расхождение: эталон описывает блок целиком.
        for field in sorted(set(got) - set(fields) - {"header"}):
            failures.append(f"EN «{name}»: поле «{field}» = «{got[field]}» есть в тексте, "
                            f"но не в эталоне PDF — расходятся текст и эталон")
        for field, want in fields.items():
            if field in META_KEYS:
                continue
            if field == "abilities":
                # Ячейки таблицы сверяем поимённо, иначе одна правка внутри таблицы
                # растворяется в «таблица не совпала».
                got_table = got.get("abilities")
                if not got_table:
                    failures.append(f"EN «{name}»: таблицы характеристик нет в тексте")
                    continue
                override = fields.get("abilities_repo", {})
                for abil in ABIL:
                    pdf_cells = want.get(abil)
                    want_cells = override.get(abil, pdf_cells)
                    text_cells = got_table.get(abil)
                    if pdf_cells is None or text_cells is None:
                        failures.append(f"EN «{name}»: в таблице характеристик нет «{abil}»")
                        continue
                    if len(text_cells) != len(pdf_cells):
                        failures.append(f"EN «{name}» {abil}: в таблице {len(text_cells)} "
                                        f"ячеек, а в PDF {len(pdf_cells)}")
                        continue
                    parts = ("значение", "модификатор", "спасбросок")[:len(pdf_cells)]
                    for idx, part in enumerate(parts):
                        if text_cells[idx].replace("−", "-") != want_cells[idx]:
                            source = (f"PDF «{pdf_cells[idx]}», у нас ждём «{want_cells[idx]}»"
                                      if want_cells[idx] != pdf_cells[idx]
                                      else f"PDF «{pdf_cells[idx]}»")
                            failures.append(f"EN «{name}» {abil} {part}: "
                                            f"«{text_cells[idx]}» ≠ {source}")
                    if abil in override:
                        problem = declared(fields.get("abilities_note"),
                                           (signed(pdf_cells[-1]), signed(override[abil][-1])))
                        if problem:
                            failures.append(f"эталон «{name}»: правка таблицы характеристик "
                                            f"объявлена, но {problem}")
                continue
            # Эталон хранит строку PDF; если у PDF там опечатка, в тексте ждём исправленную
            # форму, объявленную в самом эталоне.
            if field == "saves" and "saves_repo" in fields:
                # Та же пара, что abilities_note/abilities_repo: если опечатка в строке
                # спасбросков стоит в самом PDF, в тексте ждём исправленную форму, а
                # пометка обязана назвать спорные числа и сказать словами, что в источнике.
                pdf_pairs = dict(SAVE_PAIR.findall(fields["saves"]))
                repo_pairs = dict(SAVE_PAIR.findall(fields["saves_repo"]))
                # saves_repo — не свободный белый список: набор характеристик обязан
                # совпасть с PDF, отличаться разрешено только числу. Иначе пометкой можно
                # было бы дописать блоку владение, которого в источнике нет.
                if set(pdf_pairs) != set(repo_pairs):
                    failures.append(f"эталон «{name}»: saves_repo «{fields['saves_repo']}» "
                                    f"меняет НАБОР спасбросков против PDF «{fields['saves']}» "
                                    f"— объявлять можно только число")
                # В пометку идут только РАСХОЖДЕНИЯ (обе стороны каждой спорной пары), а
                # не все модификаторы строки: иначе автор одной правки обязан перечислить
                # восемь чисел, семь из которых ничем не спорны.
                problem = declared(fields.get("saves_note"),
                                   [signed(v) for k, v in pdf_pairs.items()
                                    if repo_pairs.get(k) != v]
                                   + [signed(v) for k, v in repo_pairs.items()
                                      if pdf_pairs.get(k) != v])
                if problem:
                    failures.append(f"эталон «{name}»: правка строки спасбросков объявлена, "
                                    f"но {problem}")
                want = fields["saves_repo"]
            if field == "cr" and "cr_repo" in fields:
                # cr_repo — не свободный белый список: это ровно cr с исправленным порядком
                # «700 XP» → «XP 700». Иначе им можно было бы узаконить любое значение.
                fixed = re.sub(r"\((\d[\d,]*)\s+XP", r"(XP \1", fields["cr"])
                if len(re.sub(r"[^A-Za-zА-Яа-яЁё]", "", str(fields.get("cr_note", "")))) < 12:
                    failures.append(f"эталон «{name}»: cr_repo объявлен, а cr_note не говорит, "
                                    f"что напечатано в PDF")
                if fields["cr_repo"] != fixed:
                    failures.append(
                        f"эталон «{name}»: cr_repo «{fields['cr_repo']}» не выводится из PDF "
                        f"«{fields['cr']}» — ожидалось «{fixed}»")
                want = fields["cr_repo"]
            normalized = False
            if field == "header" and V['titlecase_header']:
                # Эталон хранит строку PDF, а PDF 5.1 пишет тип и мировоззрение со
                # строчной — все 319 шапок. Нормализация та же и из того же модуля, что у
                # гейта шапок, и включается ТОЛЬКО версией, которой она нужна: у 5.2 она
                # погасила бы ровно одну шапку (Avatar of Death, «Neutral evil» в PDF).
                want = titlecase_header(want)
                normalized = True
            value = got.get(field)
            if value is not None:
                # Считаем НОСИТЕЛЕЙ послаблений: сравнение, которое сходится с послаблением
                # и разошлось бы без него. Пин ниже требует, чтобы у включённого послабления
                # такой носитель был хотя бы один.
                for _flag, _pos in (("senses_comma", 3), ("dash_fold", 4)):
                    if not V[_flag]:
                        continue
                    args_on = [V['lower_fields'], V['senses_comma'], V['dash_fold']]
                    args_off = list(args_on)
                    args_off[_pos - 2] = False
                    if (canon(field, value, *args_on) == canon(field, want, *args_on)
                            and canon(field, value, *args_off) != canon(field, want, *args_off)):
                        SAVED[V['version'], _flag] += 1
            if value is None:
                failures.append(f"EN «{name}»: поле «{field}» потеряно (в PDF «{want}»)")
            elif (canon(field, value, V['lower_fields'], V['senses_comma'], V['dash_fold'])
                  != canon(field, want, V['lower_fields'], V['senses_comma'], V['dash_fold'])):
                source = (f"PDF «{fields['cr']}», у нас ждём «{want}» ({fields.get('cr_note', '')})"
                          if field == "cr" and "cr_repo" in fields
                          else f"эталон после titlecase_header «{want}» (в PDF «{fields[field]}»)"
                          if normalized else f"PDF «{want}»")
                failures.append(f"EN «{name}» {field}: «{value}» ≠ {source}")
        # ПО против официальной таблицы: опыт и бонус мастерства выводятся из самого ПО.
        cr = fields.get("cr", "")
        lead = cr_value(cr)
        if re.match(r"^[\d/]+$", lead) and lead not in XP_BY_CR:
            # Не «нечего проверять», а «канон не прочитан»: пустая или обрезанная таблица
            # раньше молча снимала все четыре сверки ниже.
            failures.append(f"эталон «{name}»: ПО {lead} нет в таблице опыта главы «Монстры»")
        if lead in XP_BY_CR:
            xp = [int(x) for x in numbers(re.sub(r"^[\d/]+", "", cr.split(";")[0]))]
            if not xp:
                failures.append(f"эталон «{name}»: в ПО «{cr}» нет опыта "
                                f"(по таблице {XP_BY_CR[lead][0]})")
            elif xp[0] not in XP_BY_CR[lead]:
                problem = declared(fields.get("xp_note"), (xp[0], XP_BY_CR[lead][0]))
                if problem:
                    failures.append(
                        f"эталон «{name}»: ПО {lead} — опыт {xp[0]}, а по таблице "
                        f"{XP_BY_CR[lead][0]}; {problem}")
            # Логовый опыт: «или 7,200 в логове» — это опыт ПО на ступень выше. Сам факт
            # наличия логовой оговорки пришпилен ниже счётчиком V['lair_blocks']: её стирание
            # согласованно из эталона и обоих текстов иначе было бы невидимо.
            if len(xp) > 1:
                step = XP_BY_CR.get(str(int(lead) + 1)) if "/" not in lead else None
                if step is None:
                    failures.append(f"эталон «{name}»: логовый опыт {xp[1]} при ПО {lead} — "
                                    f"проверить нечем, у ПО на ступень выше нет строки в таблице")
                elif xp[1] != step[0]:
                    failures.append(f"эталон «{name}»: логовый опыт {xp[1]}, а по таблице "
                                    f"{step[0]} (опыт ПО {int(lead) + 1})")
            # Бонус мастерства печатается в самом ПО только у 5.2; у 5.1 он выводится из
            # таблицы главы «Монстры» и в статблоке не стоит вовсе.
            pb = re.search(r"PB \+(\d+)", cr) if V['pb_in_cr'] else None
            want_pb = pb_by_cr(lead)
            if V['pb_in_cr'] and not pb:
                # СТИРАНИЕ бонуса мастерства — то же расхождение, что подделка: «29 ПО без
                # бонуса мастерства» были вторым по величине классом правок #260.
                problem = declared(fields.get("pb_note"), (want_pb,))
                if problem:
                    failures.append(f"эталон «{name}»: в ПО «{cr}» нет бонуса мастерства "
                                    f"(по таблице +{want_pb}); {problem}")
            elif pb and int(pb.group(1)) != want_pb:
                problem = declared(fields.get("pb_note"), (int(pb.group(1)), want_pb))
                if problem:
                    failures.append(f"эталон «{name}»: ПО {lead} — бонус мастерства "
                                    f"+{pb.group(1)}, а по таблице +{want_pb}; {problem}")
    for name in sorted(set(en_blocks) - set(expected)):
        failures.append(f"EN: статблок «{name}» есть в тексте, но не в эталоне PDF")

        # RU-заголовок несёт имя без таксономического хвоста, EN-заголовок — с ним:
    # «Werebear (Lycanthrope)» и «Вермедведь (Werebear) (Ликантроп)». Сводим по имени
    # без хвоста; коллизия имён — расхождение, а не молчаливая склейка.
    by_stripped = {}
    for _en_name in en_blocks:
        _short = STRIP_TAIL.sub("", _en_name).strip()
        if _short in by_stripped:
            failures.append(f"EN: имена «{by_stripped[_short]}» и «{_en_name}» "
                            f"неразличимы без таксономического хвоста")
        by_stripped[_short] = _en_name
    ru_blocks = {by_stripped.get(_n, _n): _b for _n, _b in ru_blocks.items()}

    # Носитель послаблений сравнения: включённое послабление обязано хоть что-то гасить.
    # Без этого копия конфигурации 5.1 в будущей редакции молча снимает сверку разделителя
    # чувств и знака тире — ровно те дефекты, которые уже ловились как живые.
    for _flag in ("senses_comma", "dash_fold"):
        if V[_flag] and not SAVED[V['version'], _flag]:
            failures.append(f"конфигурация: послабление «{_flag}» включено, а ни одного "
                            f"сравнения оно не гасит — послаблению нет носителя")

    # Формы мировоззрения, как их пишет ГЛАВА монстров этой редакции: 5.1 переводит их
    # с прописной («Нейтрально-злой»), 5.2 — со строчной («нейтрально-злой»). Врезка
    # обязана писать так же, как глава своей редакции.
    #
    # Что здесь проверяется: согласие врезки с главой. Саму форму главы держит гейт шапок
    # (`ALIGN_CASE`, пара «редакция + место»), поэтому расхождение ЗДЕСЬ при зелёном гейте
    # шапок означает, что разошлась именно врезка.
    #
    # Два условия делают эту опору честной. Первое: форма у значения обязана быть ОДНА —
    # разнобой внутри главы означал бы, что «как в главе» не определено, и сверять врезку
    # не с чем. Второе: если глава не пишет такого мировоззрения вовсе, форма врезки
    # молча НЕ проверялась бы — вместо тишины гейт говорит об этом прямо (у 5.2 глава не
    # использует «Любое … мировоззрение», и врезка с ним попала бы ровно в эту дыру).
    # Послабление по роду мировоззрения объявляется в фикстуре ГЕЙТА ШАПОК (`# опция:`),
    # и гейт полей обязан читать то же объявление: иначе редакция, которой оно разрешено,
    # получала бы здесь «не из словаря» на верной врезке, а безусловное послабление,
    # наоборот, само создавало бы «разнобой главы» (ревью #281).
    neuter_ok = "род-мировоззрения-несогласован" in gender_option(V['version'])
    sidebars_checked: set = set()
    chapter_aligns: dict = {}
    for _n, _b in sorted(ru_blocks.items()):
        if _n in V['outside'] or "header" not in _b:
            continue
        _parts = split_header(_b["header"])
        if not _parts:
            continue
        _en_align, _ = align_to_en(_parts[1], neuter_ok=neuter_ok)
        if _en_align:
            chapter_aligns.setdefault(_en_align.lower(), set()).add(_parts[1])
    for _value, _forms in sorted(chapter_aligns.items()):
        if len(_forms) > 1:
            failures.append(f"глава монстров: мировоззрение «{_value}» пишется по-разному "
                            f"({sorted(_forms)}) — конвенция главы неоднородна, и форма "
                            f"врезки сверяется не с чем")

    # --- 2. RU-зеркало --------------------------------------------------------------------
    for name, fields in sorted(en_blocks.items()):
        got = ru_blocks.get(name)
        if got is None:
            failures.append(f"RU: статблок «{name}» не найден")
            continue
        # Присутствие: у каждого поля эталона обязана быть RU-строка. Перевод свой, но
        # СТРОКА должна быть — иначе поле молча исчезает только из русской половины.
        for field in expected.get(name, {}):
            if field in META_KEYS or field == "cr":
                continue
            if field in fields and field not in got:
                failures.append(f"RU «{name}»: нет строки поля «{field}» (в EN «{fields[field]}»)")
        if "cr" in fields and "cr" not in got:
            failures.append(f"RU «{name}»: нет строки ПО (в EN «{fields['cr']}»)")
        # …и наоборот: лишнее RU-поле — такое же расхождение, как лишнее EN.
        for field in sorted(set(got) - set(fields) - {"header"}):
            failures.append(f"RU «{name}»: поле «{field}» = «{got[field]}» есть в переводе, "
                            f"но не в EN")
        # Числа общие для обеих половин: перевод свой только у слов.
        for field, value in sorted(fields.items()):
            if field in ("header", "abilities") or field not in got:
                continue
            if numbers(value) != numbers(got[field]):
                failures.append(f"RU «{name}» {field}: «{got[field]}» ≠ EN «{value}» (числа)")
        # Таблица характеристик — чистые числа: перевода в ней нет вовсе, поэтому RU обязана
        # совпадать с EN ячейка в ячейку.
        en_table, ru_table = fields.get("abilities"), got.get("abilities")
        if en_table and not ru_table:
            failures.append(f"RU «{name}»: таблицы характеристик нет в переводе")
        elif en_table and ru_table:
            for abil in ABIL:
                en_cells, ru_cells = en_table.get(abil), ru_table.get(abil)
                if not ru_cells or not en_cells:
                    # Обе стороны, а не одна: обрезанная ячейка EN («18(+4)») даёт частично
                    # собранный разбор, и несимметричная защита валила гейт трейсбеком,
                    # унося весь накопленный отчёт — включая расхождения другой редакции.
                    side = "переводе" if not ru_cells else "EN"
                    failures.append(f"RU «{name}»: в таблице характеристик нет «{abil}» "
                                    f"({side})")
                elif [c.replace("−", "-") for c in ru_cells] != [c.replace("−", "-") for c in en_cells]:
                    failures.append(f"RU «{name}» {abil}: {ru_cells} ≠ EN {en_cells}")
        # Снаряжение: количество пишется скобкой («Daggers (10)» / «Кинжалы (10)»), и это
        # форма записи, а не перевод, — иначе откат к «Кинжал x 10» виден только глазами.
        if "gear" in fields and "gear" in got and fields["gear"].count("(") != got["gear"].count("("):
            failures.append(f"RU «{name}» снаряжение: «{got['gear']}» записано иначе, чем "
                            f"EN «{fields['gear']}» — количество пишется скобкой")
        # Шапка врезок не сверяется гейтом шапок (тот читает только главы монстров и
        # указатели), поэтому размер, ТИП и МИРОВОЗЗРЕНИЕ сверяем здесь — по тем же
        # словарям. До #271 сверялся один размер, и подмена типа с мировоззрением
        # в RU-врезке проходила зелёной.
        if "header" in fields and "header" in got:
            ru_size = _parse_type_line(got["header"], "ru")["size"].split()
            en_size = _parse_type_line(fields["header"], "en")["size"].split()
            ru_first = SIZES_RU_TO_EN.get(ru_size[0].lower()) if ru_size else None
            if not ru_size:
                failures.append(f"RU «{name}» шапка: «{got['header']}» — размера нет")
            elif ru_first is None:
                # Незнакомое слово раньше давало None и молча пропускалось — то есть любой
                # непереводной размер («Гигантский», «Титанический», «Huge») проходил.
                failures.append(f"RU «{name}» шапка: размер «{ru_size[0]}» не из словаря "
                                f"(EN «{en_size[0] if en_size else ''}»)")
            elif en_size and ru_first.lower() != en_size[0].lower():
                failures.append(f"RU «{name}» шапка: размер «{ru_size[0]}» ({ru_first}) "
                                f"≠ EN «{en_size[0]}»")
            if name in V['outside']:
                sidebars_checked.add(name)
                failures.extend(sidebar_header(name, fields["header"], got["header"],
                                               chapter_aligns, neuter_ok))
    for name in sorted(set(ru_blocks) - set(en_blocks)):
        failures.append(f"RU: статблок «{name}» есть в переводе, но не в EN")
    # Сама СВЕРКА врезок тоже носитель: выключенный вызов оставлял бы гейт зелёным, а
    # самопроверка ниже продолжала бы отчитываться об успехе (ревью #281). Объекты без
    # шапки (аппарат краба) в счёт не идут — у них шапки нет по построению.
    _want_sidebars = {n for n in V['outside'] if n not in V['object_blocks']}
    if sidebars_checked != _want_sidebars:
        failures.append(f"сверка врезок не дошла до {sorted(_want_sidebars - sidebars_checked)} "
                        f"— проверено {len(sidebars_checked)} из {len(_want_sidebars)}")

    # --- 2.5. Характеристики: инварианты, не зависящие от эталона -------------------------
    # Модификатор выводится из значения, а спасбросок — из модификатора и бонуса мастерства.
    # Эти две проверки не смотрят в эталон вовсе: согласованная подделка эталона и обоих
    # текстов ими всё равно ловится, если подделка нарушает правила игры.
    for name, block in sorted(en_blocks.items()):
        table = block.get("abilities")
        if not table:
            continue
        pb = re.search(r"PB \+(\d+)", block.get("cr", ""))
        bonus = int(pb.group(1)) if pb else None
        for abil in ABIL:
            cells = table.get(abil)
            if not cells:
                continue
            try:
                values = [signed(c) for c in cells]
            except ValueError:
                failures.append(f"EN «{name}» {abil}: в таблице характеристик не числа {cells}")
                continue
            # У 5.2 в таблице три ячейки (значение, модификатор, спасбросок), у 5.1 — две:
            # спасброски там стоят отдельной строкой и сверяются своей проверкой ниже.
            score, mod = values[0], values[1]
            save = values[2] if len(values) > 2 else None
            if mod != (score - 10) // 2:
                failures.append(f"EN «{name}» {abil}: модификатор {mod:+d} не выводится из "
                                f"значения {score} — ожидался {(score - 10) // 2:+d}")
            if save is None:
                continue
            gap = save - mod
            if gap < 0:
                failures.append(f"EN «{name}» {abil}: спасбросок {save:+d} ниже модификатора "
                                f"{mod:+d}")
            elif gap and bonus is None:
                failures.append(f"EN «{name}» {abil}: спасбросок {save:+d} выше модификатора, "
                                f"а бонуса мастерства в ПО «{block.get('cr')}» нет")
            elif gap and (gap % bonus or gap // bonus > 2):
                failures.append(f"EN «{name}» {abil}: спасбросок {save:+d} на {gap} выше "
                                f"модификатора {mod:+d} — не 0, не бонус мастерства (+{bonus}) "
                                f"и не удвоенный бонус")

        # Спасброски 5.1 стоят отдельной строкой («Con +6, Int +8, Wis +6»), а не в таблице.
    # Инвариант тот же: спасбросок = модификатор + бонус мастерства (или удвоенный),
    # причём бонус берётся из таблицы канона по ПО — в статблоке 5.1 его нет.
    for name, block in sorted(en_blocks.items()):
        saves, table = block.get("saves"), block.get("abilities")
        if not saves or not table:
            continue
        bonus = pb_by_cr(cr_value(block.get("cr", "")))
        for abil, value in SAVE_PAIR.findall(saves):
            cells = table.get(abil.lower())
            if not cells:
                continue
            try:
                mod = signed(cells[1])
                save = signed(value)
            except ValueError:
                # Нераспознанная форма — расхождение с адресной строкой, а не исключение:
                # трейсбек уносит с собой ВЕСЬ накопленный отчёт, включая другую редакцию.
                failures.append(f"EN «{name}» {abil.lower()}: спасбросок «{value}» или "
                                f"модификатор «{cells[1]}» записаны не числом")
                continue
            gap = save - mod
            if not bonus:
                failures.append(f"EN «{name}» {abil.lower()}: спасбросок {save:+d} есть, "
                                f"а бонуса мастерства по ПО «{block.get('cr')}» нет")
            elif gap not in (bonus, 2 * bonus):
                # Штатный выход — объявить опечатку PDF пометкой, как у ПО и характеристик:
                # инвариант производный, и первая же опечатка источника в этой строке иначе
                # упиралась бы в правку кода или текста.
                problem = declared(expected.get(name, {}).get("saves_note"), (save, mod, bonus))
                if problem:
                    failures.append(f"EN «{name}» {abil.lower()}: спасбросок {save:+d} на {gap} "
                                    f"выше модификатора {mod:+d} — не бонус мастерства "
                                    f"(+{bonus}) и не удвоенный бонус; {problem}")

# --- 3. Форма строк, которую сравнение значений намеренно не видит ---------------------
    # canon() снимает хвостовую пунктуацию (в эталоне её нет ни у одной скорости), поэтому
    # потерянная точка была бы невидима. Держим форму самим текстом: значение скорости
    # кончается либо точкой сокращения «ft.»/«фт.», либо закрывающей скобкой «(hover)».
    # Проверка на EN-половине и по ЗНАЧЕНИЯМ блоков, а не по строкам главы: так в неё попадают
    # и шесть врезок (в них метка пишется без двоеточия, и регулярка по главам их не видела).
    # RU пишет слово «футов» без точки, поэтому форму русской строки держит сверка чисел с EN.
    for name, block in sorted(en_blocks.items()):
        value = block.get("speed", "").strip()
        if value and value[-1] not in ".)":
            failures.append(f"EN «{name}»: скорость «{value}» не кончается точкой или скобкой")
    # Битая жирная метка («**Sense**s darkvision 60 ft.» вместо «- **Senses:** …»): такую
    # строку не разбирает ни одна метка словаря, поэтому для сверки её как бы нет — а
    # читатель видит поле дважды. Ловим саму ФОРМУ носителя во всех главах версии, во всех
    # обёртках, в которых строка поля вообще встречается: пунктом списка, абзацем и внутри
    # цитатной врезки, — и с ПРОБЕЛАМИ в метке («**Damage Immunitie**s»).
    # Хвостовой класс — ЛЮБАЯ буква: разрыв по пробелу многословной EN-метки оставляет
    # после «**» прописную («- **Armor **Class», «> **A**C»), а это основная форма 5.1.
    torn = re.compile(r"^(?:[>\-]\s*)*\*\*[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё ]*\*\*[A-Za-zА-Яа-яЁё]")
    # …и вторая форма того же класса: строка поля, записанная абзацем вместо пункта списка.
    # Метка при этом цела, значение сверяется, но список рвётся надвое — читатель видит
    # поле выпавшим из блока.
    para = re.compile(r"^(?:> ?)?\*\*(?:%s):?\*\*" % "|".join(
        sorted(set(V['en_labels']) | set(V['ru_labels'])
               | {V['cr_label_en'], V['cr_label_ru']}, key=len, reverse=True)))
    for lang, folder in (("en", en_dir), ("ru", ru_dir)):
        for chapter in V['chapters'] + V['sidebar_chapters']:
            path = folder / chapter
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").split("\n"):
                if torn.match(line.strip()):
                    failures.append(f"{lang}/{chapter}: строка «{line.strip()[:40]}» — "
                                    f"жирная метка разорвана, поле в сверку не попадает")
                elif chapter in V['chapters'] and para.match(line.strip()):
                    failures.append(f"{lang}/{chapter}: строка «{line.strip()[:40]}» — "
                                    f"поле записано абзацем, а не пунктом списка: "
                                    f"список блока рвётся надвое")
    # Метки полей: «Gear»/«CR» без двоеточия, остальные с ним — и одинаково в обоих языках.
    # Проверяем ВСЕ метки глав; врезки живут по другой форме (там двоеточия нет ни у одной
    # метки), поэтому их строки сюда не входят.
    for lang, folder, labels in (("en", en_dir, V['en_labels']), ("ru", ru_dir, V['ru_labels'])):
        pairs = [(label, label not in ("Gear", "Снаряжение")) for label in labels]
        # Метка ПО у версий своя («CR» без двоеточия у 5.2, «Challenge:» у 5.1) и живёт
        # в конфигурации версии — литерал «CR»/«ПО» делал проверку 5.1 слепой.
        pairs += [(V[f'cr_label_{lang}'], V['cr_colon'])]
        for chapter in V['chapters']:
            text = (folder / chapter).read_text(encoding="utf-8")
            for label, colon in pairs:
                # Ищем строку ПОЛЯ, а не любое вхождение: «Monsters with **Skills** are…» —
                # проза, а не метка, и ложным красным быть не должна.
                form = rf"^- \*\*{label}\*\*" if colon else rf"^- \*\*{label}:\*\*"
                wrong = len(re.findall(form, text, re.M))
                if wrong:
                    failures.append(f"{lang}/{chapter}: метка «{label}» "
                                    f"{'без двоеточия' if colon else 'с двоеточием'} — {wrong} строк")

    # --- 4. Колонки указателей: ПО, КД, хиты ----------------------------------------------
    # Формат строки: EN — имя, размер, тип[, мировоззрение], ПО, КД, хиты;
    #                RU — имя, оригинал, размер, тип[, мировоззрение], ПО, КД, хиты.
    CHECKED.append((V['version'], len(expected), _cells))
    for lang, gloss_dir, offset in (("en", en_dir, 0), ("ru", ru_dir, 1)):
        for index, has_align in V['indexes']:
            path = next(iter(gloss_dir.glob(f"*Glossary/{index}")), None)
            if path is None:
                failures.append(f"{lang}-указатель {index} не найден")
                continue
            for cells in index_rows(path):
                if len(cells) <= (1 if lang == "ru" else 0):
                    failures.append(f"{lang}-указатель {index}: в строке «{'|'.join(cells)}» "
                                    f"нет колонки имени")
                    continue
                name = cells[1] if lang == "ru" else cells[0]
                block = en_blocks.get(name)
                if block is None:
                    continue           # имена сверяет test_statblock_headers.py
                tail = 3 + offset + (1 if has_align else 0)
                if len(cells) < tail + 3:
                    # Обрезанная строка раньше молча выключала сверку — а ширину строки
                    # соседний гейт держит только на RU-половине.
                    failures.append(f"{lang}-указатель {index}, «{name}»: в строке {len(cells)} "
                                    f"колонок, а нужно {tail + 3}")
                    continue
                cr, ac, hp = cells[tail], cells[tail + 1], cells[tail + 2]
                if "cr" in block and cr != cr_value(block["cr"]):
                    failures.append(
                        f"{lang}-указатель {index}, «{name}»: ПО «{cr}» ≠ «{cr_value(block['cr'])}»")
                if "ac" in block:
                    # Значение считаем ВНУТРИ охраны: блок без строки КД (ровно тот дефект
                    # импорта, ради которого писан гейт) иначе ронял прогон трейсбеком и
                    # уносил весь накопленный отчёт обеих редакций.
                    want_ac = ac_value(block["ac"]) if V['ac_bare_in_index'] else block["ac"]
                    if ac != want_ac:
                        failures.append(
                            f"{lang}-указатель {index}, «{name}»: КД «{ac}» ≠ «{want_ac}»")
                if "hp" in block and hp != hp_value(block["hp"]):
                    failures.append(
                        f"{lang}-указатель {index}, «{name}»: хиты «{hp}» ≠ «{hp_value(block['hp'])}»")


def check_version_labeled(V: dict) -> None:
    """`check_version` + пометка редакции на всех её расхождениях."""
    start = len(failures)
    check_version(V)
    failures[start:] = [m if m.startswith(V['version']) else f"{V['version']}: {m}"
                        for m in failures[start:]]


# 320 блоков: 317 существ главы, две врезки-существа и статблок ОБЪЕКТА (аппарат краба),
# у которого есть только КД, хиты, скорость и иммунитеты к урону.
FIELD_COUNTS_51 = {"abilities": 319, "ac": 320, "condition_immunities": 89, "cr": 318, "damage_immunities": 128, "damage_resistances": 64, "damage_vulnerabilities": 15, "header": 319, "hp": 320, "languages": 319, "saves": 92, "senses": 319, "skills": 188, "speed": 320}
STRUCTURE_SHA_51 = "ea3fbf5e0359157a7f2cac902aa08eaba94e7846ac2d62f345c0d47306cc2156"
EXTRACTION_SHA_51 = "efdc7c73984135716608cfb0ff341f4d4562bdec7945f836cc1110466707105a"


# Конфигурация версий: различия форм живут здесь, а проверки — общие (см. check_version).
VERSIONS = [
    {
        "version": "srd-5.2",
        "fixture": SCRIPTS / "fixtures/srd-5.2-statblock-fields.json",
        "pdf": "https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf",
        "sha256": "8974902d109d6e63672d7c490bde9ccf052410503d9cfa768237154fbc5e3d87",
        "pages": 364,
        "page_size": "594 x 783",
        "license": "CC BY 4.0; формула атрибуции — src/dnd/srd-5.2/LICENSE.md",
        "license_sha": "22ce079c48db402e3ff7c8c779788463a0bc1d50ca84154bf7ff0a3348ae1312",
        "regenerate": ".github/scripts/build_statblock_fields.py",
        "extraction_sha": EXTRACTION_SHA_52,
        "chapters": ("12_MonstersA-Z.md", "13_Animals.md"),
        "sidebar_chapters": ("07_Spells.md", "10_MagicItems.md"),
        "monsters_chapter": "11_Monsters.md",
        "indexes": (("04_Monsters.md", True), ("05_Animals.md", False)),
        "en_labels": EN_LABELS_52,
        "ru_labels": RU_LABELS_52,
        "outside": ["Animated Object", "Avatar of Death", "Draconic Spirit", "Giant Fly",
                    "Giant Insect", "Otherworldly Steed"],
        "object_blocks": [],
        "object_required": (),
        # Поля, которые есть у КАЖДОГО статблока: отсутствие любого из них в эталоне —
        # дыра эталона (та, из-за которой «Mimic Languages» и «Animated Object AC» молчали).
        "required": ("header", "abilities", "ac", "hp", "speed", "senses", "languages", "cr"),
        "field_counts": FIELD_COUNTS_52,
        "structure_sha": STRUCTURE_SHA_52,
        # Ячеек в таблицах характеристик: 336 блоков × 6 характеристик ×
        # (значение, модификатор, спасбросок). Пришпилено рядом с составом полей.
        "ability_cells": 6048,
        # Сколько блоков несут логовую оговорку («or 7,200 in lair»): её стирание
        # согласованно из эталона и обоих текстов иначе не оставляет следа.
        "lair_blocks": 27,
        "cr_label_en": "CR",
        "cr_label_ru": "ПО",
        "cr_colon": False,
        "required_in_chapters": ("initiative",),
        "lower_fields": ("senses",),
        # PDF 5.2 пишет тот же разделитель чувств и ту же шапку, что и мы, поэтому оба
        # послабления, нужные 5.1, здесь выключены — иначе они молча ослабляют 5.2.
        "senses_comma": False,
        "dash_fold": False,
        "ac_bare_in_index": False,
        # Бонус мастерства 5.2 задан диапазонами ПО («0–4»), дробных строк в таблице нет —
        # для дробного ПО он выводится (бонус тот же, что у ПО 0).
        "pb_table_fractions": False,
        "titlecase_header": False,
        "pb_in_cr": True,
        # Спасброски 5.2 живут в таблице характеристик и посчитаны в ability_cells.
        "saves_pairs": 0,
    },
    {
        "version": "srd-5.1",
        "fixture": SCRIPTS / "fixtures/srd-5.1-statblock-fields.json",
        "pdf": "https://media.wizards.com/2023/downloads/dnd/SRD_CC_v5.1.pdf",
        "sha256": "2504d2a0abb0a4d491a939be4f17910a2dde0312570ab8d208080225ccf0a1f0",
        "pages": 403,
        "page_size": "612 x 792",
        "license": "CC BY 4.0; формула атрибуции — src/dnd/srd-5.1/LICENSE.md",
        "license_sha": "39dc3d747ac3a357525aca274b6e5ec7e2f8f63af77634f5ecf9cd60e2dc8b18",
        "regenerate": ".github/scripts/build_statblock_fields.py",
        "extraction_sha": EXTRACTION_SHA_51,
        "chapters": ("15_MonstersA-Z.md",),
        "sidebar_chapters": ("13_MagicItems.md",),
        "monsters_chapter": "14_Monsters.md",
        "indexes": (("04_Monsters.md", True),),
        "en_labels": EN_LABELS_51,
        "ru_labels": RU_LABELS_51,
        "outside": ["Apparatus of the Crab", "Avatar of Death", "Giant Fly"],
        # Статблок ОБЪЕКТА: ни шапки «размер тип, мировоззрение», ни характеристик, ни
        # чувств с языками — обязательные поля к нему не применяются.
        "object_blocks": list(OBJECT_BLOCKS_51),
        # …но СВОИ обязательные поля у него есть: без них пометка снимала последнего
        # сторожа состава, который не сводится к перегенерации константы.
        "object_required": ("ac", "hp", "speed"),
        "required": ("header", "abilities", "ac", "hp", "speed", "senses", "languages"),
        "field_counts": FIELD_COUNTS_51,
        "structure_sha": STRUCTURE_SHA_51,
        # 319 блоков × 6 характеристик × (значение, модификатор): спасбросков в
        # таблице 5.1 нет, они стоят отдельной строкой и считаются в saves_pairs.
        "ability_cells": 3828,
        # Логовой оговорки в 5.1 нет ни у одного блока — это тоже утверждение о PDF.
        "lair_blocks": 0,
        "cr_label_en": "Challenge",
        "cr_label_ru": "Показатель опасности",
        "cr_colon": True,
        # ПО есть у всех, кроме врезки Гигантской мухи: у неё в PDF строки «Challenge» нет.
        "required_in_chapters": ("cr",),
        # PDF 5.1 пишет весь статблок со строчной, импорт — с прописной: различие
        # оформления, а не данных, и оно сплошное (317 блоков). Регистр ИМЁН и чисел от
        # этого не страдает: шапка сверяется после той же нормализации, что у гейта шапок.
        # Список закрытый и проверенный поштучно: снятие любого из семи даёт расхождения,
        # а «languages» и мёртвый «damage_resistance» сняты — регистр языков сверяется.
        "lower_fields": ("senses", "speed", "ac", "damage_immunities",
                         "condition_immunities", "damage_resistances",
                         "damage_vulnerabilities"),
        "senses_comma": True,
        "dash_fold": True,
        # В указателе 5.1 КД — голое число, а в статблоке к нему приписан вид доспеха
        # («17 (natural armor)»): 209 значений из 320.
        "ac_bare_in_index": True,
        # …а 5.1 печатает «1/8», «1/4», «1/2» отдельными строками — значит, они читаются
        # из главы и сверяются, а не подставляются.
        "pb_table_fractions": True,
        "titlecase_header": True,
        # …а раз PB в строке ПО нет, то и объявить его правку нечем: пометка `pb_note`
        # относится только к редакциям, печатающим бонус мастерства в строке ПО.
        "pb_in_cr": False,
        # Пар «характеристика — спасбросок» во всех строках спасбросков эталона. Пришпилено
        # по той же причине, что ability_cells: удаление пары из строки и из эталона
        # согласованно проходило молча — арифметика проверяет лишь то, что уже написано.
        "saves_pairs": 315,
    },
]

# Эталон, положенный рядом, но не объявленный в VERSIONS, иначе игнорируется молча —
# при том что соседний гейт шапок находит свои фикстуры глобом и сразу их читает.
_declared = {v['fixture'].name for v in VERSIONS}
for _found in sorted((SCRIPTS / "fixtures").glob("srd-*-statblock-fields.json")):
    if _found.name not in _declared:
        failures.append(f"эталон {_found.name} лежит рядом, но не объявлен в VERSIONS — "
                        f"его не читает никто")

for _V in VERSIONS:
    # Метки ЧУЖОЙ редакции: строка «- **Initiative:**» в главе 5.1 (и «- **Saving Throws:**»
    # в главе 5.2) не разбирается словарём своей версии и потому была бы невидима.
    _other = [o for o in VERSIONS if o is not _V]
    # Метка ПО живёт ВНЕ словарей полей (у редакций разошлась именно она), поэтому её
    # добавляем к чужим руками — иначе «- **CR** …» в главе 5.1 не разбирается никем.
    _V['foreign_labels'] = {
        lang: sorted(({lab for o in _other for lab in o[f'{lang}_labels']}
                      | {o[f'cr_label_{lang}'] for o in _other})
                     - set(_V[f'{lang}_labels']) - {_V[f'cr_label_{lang}']})
        for lang in ("en", "ru")}
# Поломка словаря — причина, а не следствие: она попадает в отчёт первой, до расхождений
# редакций (у её строк нет префикса версии, поэтому и потолок печати у них свой).
failures.extend(DICT_PROBLEMS)

# --- Самопроверка сверки врезки ---------------------------------------------------------
# Живой корпус сегодня ВЕРЕН, поэтому `sidebar_header` на нём молчит — и молчала бы, даже
# если бы её вырезали целиком (мутация `return []` проходила все гейты зелёной, ревью
# #281). Ниже — таблица входов, где расхождение известно заранее: она держит саму функцию,
# а не текст. Первая строка контрольная — на верной паре сообщений быть не должно.
SIDEBAR_CASES = [
    # (метка, EN-шапка, RU-шапка, [куски сообщений, которые обязаны прозвучать])
    # Пустой список — сообщений быть не должно вовсе: это контрольные строки таблицы.
    ("верная пара", "Medium Undead, Neutral Evil", "Средняя Нежить, Нейтрально-злой", []),
    ("подменён тип", "Medium Undead, Neutral Evil",
     "Средняя Аберрация, Нейтрально-злой", ["'type', 'Aberration'"]),
    # Две строки на один дефект: о нём говорят и сверка согласования размера (ей тип нужен
    # словарным термином), и разбор шапки целиком.
    ("тип со строчной", "Medium Undead, Neutral Evil",
     "Средняя нежить, Нейтрально-злой",
     ["не из словаря — в шапке", "не из словаря: ['нежить']"]),
    ("постороннее слово в типе", "Medium Undead, Neutral Evil",
     "Средняя Нежить-мутант, Нейтрально-злой", ["не из словаря — в шапке", "'мутант'"]),
    ("мусор конвертации", "Medium Undead, Neutral Evil",
     "Средняя Нежить 12, Нейтрально-злой", ["'1', '2'"]),
    ("неразрывный пробел", "Medium Undead, Neutral Evil",
     "Средняя\u00a0Нежить, Нейтрально-злой", ["U+00A0"]),
    ("нет пробела после запятой", "Medium Undead, Neutral Evil",
     "Средняя Нежить,Нейтрально-злой", ["нет пробела"]),
    ("подменено мировоззрение", "Medium Undead, Neutral Evil",
     "Средняя Нежить, Принципиально-добрый", ["(Lawful Good) ≠ EN «Neutral Evil»"]),
    ("форма мировоззрения не как в главе", "Medium Undead, Neutral Evil",
     "Средняя Нежить, нейтрально-злой", ["написано не как в главе монстров"]),
    ("мировоззрения нет в главе", "Medium Undead, Unaligned",
     "Средняя Нежить, Без мировоззрения", ["сверить не с чем"]),
    ("род размера", "Medium Undead, Neutral Evil",
     "Средний Нежить, Нейтрально-злой", ["не согласован с «Нежить»"]),
    ("регистр размера", "Medium Undead, Neutral Evil",
     "средняя Нежить, Нейтрально-злой", ["не согласован", "начинается со строчной"]),
    ("нет запятой", "Medium Undead, Neutral Evil", "Средняя Нежить Нейтрально-злой",
     ["не отделено запятой"]),
    ("подменена связка", "Large Celestial, Fey, or Fiend (Your Choice), Neutral",
     "Большой Небожитель, Фея и Исчадие (на ваш выбор), нейтральный", ["'service', 'AND'"]),
    ("снят один тип", "Large Celestial, Fey, or Fiend (Your Choice), Neutral",
     "Большой Небожитель или Исчадие (на ваш выбор), нейтральный",
     ["≠ EN «Large Celestial"]),
    ("подменена оговорка", "Large Celestial, Fey, or Fiend (Your Choice), Neutral",
     "Большой Небожитель, Фея или Исчадие (на выбор Мастера), нейтральный",
     ["'на выбор Мастера'"]),
    ("составной подтип", "Large Fiend (Demon, Shapechanger), Chaotic Evil",
     "Большое Исчадие (демон, перевёртыш), Хаотично-злой", []),
    ("подменён подтип", "Large Fiend (Demon, Shapechanger), Chaotic Evil",
     "Большое Исчадие (ангел, перевёртыш), Хаотично-злой",
     ["'subtype', 'Angel, Shapechanger'"]),
    ("недопереведённый подтип", "Large Fiend (Demon, Shapechanger), Chaotic Evil",
     "Большое Исчадие (Demon, перевёртыш), Хаотично-злой", ["'Demon, перевёртыш'"]),
]
# Снимок конвенции главы СМЕШАННЫЙ намеренно: у большинства значений форма 5.1 (с
# прописной), а у «neutral» — форма 5.2 (со строчной), потому что строки составного типа
# проверяют РАЗБОР, и лишнее срабатывание по регистру мешало бы читать их ожидания.
# «Unaligned» снимок не знает вовсе — на нём проверяется ветка «сверить форму не с чем».
SIDEBAR_ALIGNS = {"neutral evil": {"Нейтрально-злой"},
                  "lawful good": {"Принципиально-добрый"},
                  "chaotic evil": {"Хаотично-злой"},
                  "neutral": {"нейтральный"}}
for _label, _en, _ru, _want in SIDEBAR_CASES:
    _got = sidebar_header(_label, _en, _ru, SIDEBAR_ALIGNS)
    # Сверяем ПРИЧИНУ, а не только счётчик: иначе подмена смысла сообщения (например,
    # снятие регистрочувствительности типа) не отличалась бы от нормы (ревью #281).
    if len(_got) != len(_want):
        failures.append(f"самопроверка врезки «{_label}»: сообщений {len(_got)}, "
                        f"ожидалось {len(_want)} — {_got}")
        continue
    for _piece in _want:
        if not any(_piece in _line for _line in _got):
            failures.append(f"самопроверка врезки «{_label}»: в сообщениях нет «{_piece}» "
                            f"— {_got}")
for _V in VERSIONS:
    check_version_labeled(_V)


if failures:
    print(f"❌ Поля статблоков разошлись с эталоном PDF ({len(failures)}):")
    # Потолок печати делится МЕЖДУ РЕДАКЦИЯМИ поровну: один класс расхождений в одной
    # редакции легко даёт больше сорока строк (235 разорванных меток — реалистичная
    # мутация), и тогда единственная правка в другой редакции не попадала в отчёт вовсе.
    by_version, order = {}, []
    for f in failures:
        # Ключ — ровно редакция: сообщения из read_blocks несут в префиксе ещё главу и имя
        # блока, и «всё до первого двоеточия» давало свой ключ на каждый блок — потолок
        # схлопывался в одну строку на класс, а шум печатался целиком.
        key = f.split()[0].rstrip(":") if f.startswith("srd-") else ""
        if key not in by_version:
            by_version[key], _ = [], order.append(key)
        by_version[key].append(f)
    quota = max(1, 40 // len(by_version))
    shown = 0
    for key in order:
        for f in by_version[key][:quota]:
            print(f"  — {f}")
            shown += 1
        if len(by_version[key]) > quota:
            print(f"  … и ещё {len(by_version[key]) - quota} по {key or 'без редакции'}")
    sys.exit(1)

print(f"✅ Поля статблоков ({len(SIDEBAR_CASES)} самопроверок врезки): " + "; ".join(
    f"{v} — блоков {b}, ячеек {c}" for v, b, c in CHECKED) +
    "; RU-зеркало и указатели сходятся")
