#!/usr/bin/env python3
"""Сверка ВСЕХ полей статблоков с эталоном из официального PDF (issue #260).

Чем это отличается от `test_statblock_headers.py`. Тот держит одну строку блока —
«размер тип, мировоззрение», — и держит её строго. Всё остальное (КД, инициатива, хиты,
скорость, навыки, чувства, языки, ПО, иммунитеты, сопротивления, уязвимости, снаряжение)
до сих пор не сверялось ни с чем, хотя текст 5.2 приехал не из PDF, а из стороннего
перегона. Сверка нашла 255 расхождений: у 30 существ инициатива была равна модификатору
Ловкости вместо значения из PDF, у 29 в ПО не было бонуса мастерства, у 27 стояло
обобщённое «XP 0 or 10» вместо конкретного значения, у 129 не было строки языков,
у пятерых в скорости висела заглушка `?`, плюс точечные ошибки в навыках и уязвимостях.

Эталон — `fixtures/srd-5.2-statblock-fields.json`, снятый с официального PDF 5.2.1
четырьмя независимыми выемками (marker, pymupdf4llm, docling и постраничная резка
`pdftotext` по колонкам — конвертеры теряют разные поля на двухколоночной вёрстке).
Пересобирается и сверяется `build_statblock_fields.py` — тот прогон воспроизводит все
3181 значение эталона из PDF и падает, если хоть одно перестало воспроизводиться.

Что проверяем:
  1) EN — каждое поле каждого блока против эталона (включая таблицу характеристик:
     336 × 6 × значение/модификатор/спасбросок), и лишних полей в тексте нет;
  2) состав эталона — обязательные ключи у всех блоков, число ячеек ПО КАЖДОМУ полю и
     отпечаток структуры «блок → набор полей» (иначе согласованное удаление поля из
     эталона и обоих текстов, а равно обмен полями между блоками, проходили бы молча);
  3) RU-зеркало — все числа обязаны совпадать с EN, у каждого поля EN обязана быть
     RU-строка, лишних RU-полей и выдуманных RU-блоков нет, шапка согласована по размеру;
  4) форма строк текста, которую сравнение значений намеренно не видит (хвостовая
     пунктуация скорости, метки полей);
  5) колонки указателей (ПО, КД, хиты) — против тех же блоков;
  6) ПО против официальной таблицы «ПО → опыт и бонус мастерства», а характеристики —
     против двух производных инвариантов: модификатор выводится из значения, спасбросок
     отличается от модификатора на 0, бонус мастерства или удвоенный бонус;
  7) опечатки САМОГО PDF объявляются в эталоне (`cr_note`/`cr_repo`/`xp_note`/`pb_note`/
     `abilities_note`/`abilities_repo`),
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
from statblock_meta import META_KEYS                              # noqa: E402

FIXTURE = SCRIPTS / "fixtures/srd-5.2-statblock-fields.json"
REGENERATE = ".github/scripts/build_statblock_fields.py"
LICENSE = "CC BY 4.0; формула атрибуции — src/dnd/srd-5.2/LICENSE.md"
# Первые слова каждой из четырёх выемок: провенанс пришпилен парой «имя → значение»,
# а не длиной списка — четыре любые строки провенансом не являются.
EXTRACTION_HEADS = ["marker (основная вые", "pymupdf4llm (блоки, ", "docling (поля, потер", "pdftotext -layout -x"]
VERSION = "srd-5.2"
# Провенанс эталона пришпилен ПАРОЙ «имя → значение»: иначе шапку можно исказить,
# оставив её непустой, и гейт этого не заметит.
PDF_URL = "https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf"
PDF_SHA256 = "8974902d109d6e63672d7c490bde9ccf052410503d9cfa768237154fbc5e3d87"
PDF_PAGES = 364
PDF_PAGE_SIZE = "594 x 783"
# Состав эталона ПО ПОЛЯМ, а не одной суммой: усыхание эталона — самый тихий способ
# ослабить сверку (удалённое поле просто перестаёт проверяться), а сумма ещё и
# компенсируется — снял поле у одного блока, выдумал у другого. Это не «настройка»:
# числа выведены из PDF, и менять их можно только вместе с эталоном и с объяснением,
# откуда взялось новое значение.
# Отпечаток структуры эталона: «имя блока → набор полей». Пришпилен рядом со счётчиками,
# потому что счётчики ловят усыхание, а отпечаток — перестановку поля между блоками.
STRUCTURE_SHA = "ed3a6cce774ba14f871d23502c358bebf83b353e5ca7609e41e221b07b0d57a9"
# Сколько блоков несут логовую оговорку («or 7,200 in lair»). Пришпилено: её стирание
# согласованно из эталона и обоих текстов иначе не оставляет следа.
LAIR_BLOCKS = 27
FIELD_COUNTS = {"header": 336, "abilities": 336, "ac": 336, "hp": 336, "speed": 336, "senses": 336,
                "languages": 336, "cr": 336, "initiative": 332, "skills": 216,
                "immunities": 150, "resistances": 71, "gear": 45, "vulnerabilities": 15}

# Во врезках метки короткие («**AC** 11»), в главах — полные («- **Armor Class:** 11»).
EN_LABELS = {"Gear": "gear", "Armor Class": "ac", "AC": "ac", "Hit Points": "hp",
             "HP": "hp", "Speed": "speed",
             "Initiative": "initiative", "Skills": "skills", "Senses": "senses",
             "Languages": "languages", "Immunities": "immunities",
             "Resistances": "resistances", "Vulnerabilities": "vulnerabilities"}
# RU читаем ПОЛНЫМ набором полей: числа сверяются со значением, остальные — по наличию.
# Без этого удаление 130 RU-строк «Языки: —» проходило зелёным весь CI, то есть RU-половина
# правок #260 не была защищена ничем.
RU_LABELS = {"Класс доспеха": "ac", "КД": "ac", "Хиты": "hp", "Скорость": "speed",
             "Инициатива": "initiative", "Навыки": "skills", "Снаряжение": "gear",
             "Чувства": "senses", "Языки": "languages", "Иммунитеты": "immunities",
             "Сопротивления": "resistances", "Уязвимости": "vulnerabilities"}
# Служебные ключи эталона: это не поля статблока, а пометки о самом эталоне.
# Поля, которые есть у КАЖДОГО статблока. Отсутствие любого из них в эталоне — дыра
# эталона (ровно та, из-за которой «Mimic Languages None» и «Animated Object AC» молчали).
REQUIRED = ("header", "abilities", "ac", "hp", "speed", "senses", "languages", "cr")
# Заголовки внутри статблока — не имена блоков.
SERVICE_HEADINGS = {"traits", "actions", "bonus actions", "reactions", "legendary actions",
                    "особенности", "действия", "бонусные действия", "реакции",
                    "легендарные действия", "свойства"}
# Первое слово шапки — размер; словари канонические, из продукционного парсера.
ABIL = ("str", "dex", "con", "int", "wis", "cha")
# Метки таблицы характеристик в обоих языках и в обеих формах записи.
ABIL_ROWS = {"SCORE": "score", "MOD": "mod", "SAVE": "save",
             "ЗНАЧ": "score", "МОД": "mod", "СПАС": "save"}
ABILITIES = {"str": "str", "dex": "dex", "con": "con", "int": "int", "wis": "wis",
             "cha": "cha", "сил": "str", "лов": "dex", "тел": "con", "инт": "int",
             "мдр": "wis", "хар": "cha"}
# Ячеек в таблицах характеристик: 336 блоков × 6 характеристик × (значение, модификатор,
# спасбросок). Пришпилено рядом с составом полей — по той же причине.
ABILITY_CELLS = 6048
SIZE_PREFIX = "|".join(sorted(set(SIZES_EN) | set(SIZES_RU_TO_EN), key=len, reverse=True))
failures = []


def canon(field: str, value: str) -> str:
    """Приведение перед сравнением — послабления этого гейта, ВСЕ ПЯТЬ.

    Гасятся ровно эти вещи, и каждая намеренно:
      1) повторные пробелы схлопываются в один — перенос строки в PDF рвёт значение
         в произвольном месте;
      2) ХВОСТОВАЯ точка/запятая/точка с запятой — конвертеры теряют и добавляют её
         произвольно, поэтому в эталоне её нет ни у одного из 336 значений скорости.
         Ведущая пунктуация НЕ гасится, и форму строки в тексте держит проверка формы
         (раздел 3 ниже): без неё потерянная точка у Глиняного голема проходила молча;
      3) ПАРНЫЙ курсив («*Bless*» у Ракшаса): PDF-выемка разметки не несёт. Непарная
         звёздочка остаётся в значении и делает расхождение видимым;
      4) регистр у ЧУВСТВ — PDF пишет «Darkvision 120 ft.», мы «darkvision 120 ft.»;
         различие живёт в 252 строках чувств и не является данными;
      5) «Thieves' Cant» → «Thieves' cant» в языках: та же стилистика, 3 строки в скоупе.
    Всё остальное — включая регистр в остальных полях, порядок слов, скобки и числа —
    сверяется как есть. Регистрозависимость нашла четыре «And» в языках (Гигантский лось,
    Гигантская сова, Кошмар, Пегас), которых не видел ни один прогон до неё.
    """
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"[.;,]+$", "", value)
    value = re.sub(r"\*([^*]+)\*", r"\1", value)
    if field == "senses":
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
                strict_headings: bool = True) -> list:
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
                # RU-заголовок несёт оригинал в скобках: «Аболет (Aboleth)».
                latin = re.findall(r"\(([^()]*[A-Za-z][^()]*)\)", title)
                name = re.sub(r"\s*\([^()]*\)$", "", latin[-1]).strip() if latin else None
            else:
                name = title
            block = {}
            continue
        if block is None:
            if closed and re.match(r"^(?:- )?\*\*(?:%s|CR|ПО):?\*\*" % "|".join(labels), s):
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
            if not cells[0] and len(cells) > 6 and all(head):
                # Шапка таблицы: порядок колонок держит весь разбор ниже (он позиционный),
                # поэтому перестановка колонок обязана быть видна.
                if head != list(ABIL):
                    failures.append(f"{where} «{name}»: колонки таблицы характеристик идут "
                                    f"{cells[1:7]} — ожидался порядок СИЛ ЛОВ ТЕЛ ИНТ МДР ХАР")
            if row in ABIL_ROWS and len(cells) > 6:
                block.setdefault("_rows", {})[ABIL_ROWS[row]] = cells[1:7]
            elif cells and ABILITIES.get(cells[0].lower()) and len(cells) > 3:
                block.setdefault("abilities", {})[ABILITIES[cells[0].lower()]] = cells[1:4]
            continue
        m = re.match(r"^(?:- )?\*\*(?:CR|ПО):?\*\*:?\s*(.+)$", s)
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
        seen = HEADINGS.setdefault(where.split("/")[0] + ("/ru" if ru else "/en"), {})
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
        lang = where.split("/")[0]
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
        bounds = [int(x) for x in re.findall(r"\d+", cells[0])] if cells else []
        digits = re.sub(r"[^\d]", "", cells[1]) if len(cells) > 1 else ""
        if not bounds or not digits:
            failures.append(f"канон: в таблице «{title}» ({path.name}) строка "
                            f"«{' | '.join(cells)}» без ПО или без бонуса")
            continue
        for value in range(bounds[0], bounds[-1] + 1):
            if str(value) in out:
                failures.append(f"канон: в таблице «{title}» ({path.name}) ПО {value} дважды")
            out[str(value)] = int(digits)
    return out


# Официальная таблица «ПО → опыт» читается ИЗ ПУБЛИКУЕМОГО КОНТЕНТА (глава «Монстры»), а не
# держится литералом: иначе экземпляров знания становится два и порча канона — та, что уедет
# читателю, — не краснеет нигде. Она же делает значение ПО проверяемым САМО ПО СЕБЕ:
# согласованная подделка `cr` в эталоне и в тексте больше не проходит.
MONSTERS_EN = ROOT / f"src/dnd/{VERSION}/en/11_Monsters.md"
MONSTERS_RU = ROOT / f"src/dnd/{VERSION}/ru/11_Monsters.md"
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
    if _cr not in PB_BY_CR and "/" not in _cr:
        failures.append(f"канон: в таблице бонуса мастерства нет ПО {_cr} — таблица неполна")
if len(XP_BY_CR) != len(CR_LADDER):
    failures.append(f"канон: в таблице опыта {len(XP_BY_CR)} строк вместо {len(CR_LADDER)}")
# ПО дробное — бонус тот же, что у ПО 0.
for _fraction in ("1/8", "1/4", "1/2"):
    PB_BY_CR[_fraction] = PB_BY_CR.get("0", 2)


def pb_by_cr(cr: str) -> int:
    """Бонус мастерства по ПО — по таблице из главы «Монстры»."""
    return PB_BY_CR.get(cr, 0)


_fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
# Эталон — выемка из PDF, поэтому у него есть шапка с источником и лицензией;
# сами блоки лежат под ключом «blocks», чтобы служебные поля не путались с именами существ.
if "blocks" not in _fixture or "_source" not in _fixture:
    sys.exit("❌ эталон без ключа «blocks» или «_source» — файл не той формы")
expected = _fixture["blocks"]
_src = _fixture["_source"]
for _key, _want in (("pdf", PDF_URL), ("sha256", PDF_SHA256),
                    ("pages", PDF_PAGES), ("page_size_pt", PDF_PAGE_SIZE)):
    if _src.get(_key) != _want:
        failures.append(f"эталон: _source.{_key} = «{_src.get(_key)}», ожидалось «{_want}»")
# Лицензия и способ пересборки — тоже пара «имя → значение»: «непустое» пропускает
# и «Proprietary», и путь в никуда.
if _src.get("license") != LICENSE:
    failures.append(f"эталон: _source.license «{_src.get('license')}» ≠ «{LICENSE}»")
if _src.get("regenerate") != REGENERATE:
    failures.append(f"эталон: _source.regenerate «{_src.get('regenerate')}» ≠ «{REGENERATE}»")
elif not (ROOT / REGENERATE).is_file():
    failures.append(f"эталон: скрипта пересборки «{REGENERATE}» нет")
_extraction = _src.get("extraction")
if not isinstance(_extraction, list) or [str(x)[:20] for x in _extraction] != EXTRACTION_HEADS:
    failures.append("эталон: _source.extraction — не тот список из четырёх выемок, "
                    "которым снят эталон")

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
if _digest != STRUCTURE_SHA:
    failures.append("состав эталона по блокам изменился: набор полей у блоков не тот, "
                    "что снят с PDF (отпечаток структуры не сошёлся)")
_lair = sum(1 for f in expected.values() if "in lair" in f.get("cr", ""))
if _lair != LAIR_BLOCKS:
    failures.append(f"состав эталона: логовая оговорка у {_lair} блоков, а по PDF "
                    f"у {LAIR_BLOCKS}")
_have = Counter(k for f in expected.values() for k in f if k not in META_KEYS)
_ability_cells = sum(len(v) for f in expected.values()
                     for v in f.get("abilities", {}).values())
if _ability_cells != ABILITY_CELLS:
    failures.append(f"состав эталона: ячеек характеристик {_ability_cells}, "
                    f"а по PDF {ABILITY_CELLS}")
_cells = sum(_have.values()) - _have.get("abilities", 0) + _ability_cells
for _key in sorted(set(_have) | set(FIELD_COUNTS)):
    if _have.get(_key, 0) != FIELD_COUNTS.get(_key, 0):
        failures.append(f"состав эталона: поле «{_key}» у {_have.get(_key, 0)} блоков, "
                        f"а по PDF у {FIELD_COUNTS.get(_key, 0)}")
for _name, _f in sorted(expected.items()):
    for _key in REQUIRED:
        if _key not in _f:
            failures.append(f"эталон «{_name}»: нет обязательного поля «{_key}»")
    if "initiative" not in _f and not _f.get("outside_chapters"):
        failures.append(f"эталон «{_name}»: нет поля «initiative» (его нет только у врезок)")

en_dir, ru_dir = ROOT / f"src/dnd/{VERSION}/en", ROOT / f"src/dnd/{VERSION}/ru"
en_blocks, ru_blocks = {}, {}
for chapter in ("12_MonstersA-Z.md", "13_Animals.md"):
    merge(en_blocks, read_blocks(en_dir / chapter, EN_LABELS, False, f"en/{chapter}"),
          f"en/{chapter}")
    merge(ru_blocks, read_blocks(ru_dir / chapter, RU_LABELS, True, f"ru/{chapter}"),
          f"ru/{chapter}")
# Блоки-врезки: заклинания и магические предметы. Список ЗАКРЫТ и живёт здесь, а не
# выводится из фикстуры: иначе удаление врезки из эталона молча выключало бы её проверку.
OUTSIDE = ["Animated Object", "Avatar of Death", "Draconic Spirit", "Giant Fly",
           "Giant Insect", "Otherworldly Steed"]
for _name in OUTSIDE:
    if not expected.get(_name, {}).get("outside_chapters"):
        failures.append(f"эталон: блок-врезка «{_name}» пропал или потерял пометку")
for _name, _f in expected.items():
    if _f.get("outside_chapters") and _name not in OUTSIDE:
        failures.append(f"эталон: блок «{_name}» помечен как врезка, но нет в списке OUTSIDE")
for chapter in ("07_Spells.md", "10_MagicItems.md"):
    for src, dst, labels, ru, lang in ((en_dir, en_blocks, EN_LABELS, False, "en"),
                                       (ru_dir, ru_blocks, RU_LABELS, True, "ru")):
        path = src / chapter
        if not path.exists():
            continue
        pairs = read_blocks(path, labels, ru, f"{lang}/{chapter}", strict_headings=False)
        # Врезочные главы читаются тем же разбором, что и главы монстров, поэтому в них
        # тоже видно «блок есть в тексте, но не в эталоне»: статблоком считаем всё, у
        # чего есть шапка и КД с хитами — прочие `####` в заклинаниях этому не отвечают.
        for name, block in pairs:
            if name not in OUTSIDE and {"header", "ac", "hp"} <= set(block):
                failures.append(
                    f"{lang}/{chapter}: статблок «{name}» есть в тексте, но не в эталоне PDF")
        merge(dst, pairs, f"{lang}/{chapter}", only=set(OUTSIDE))

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
            # 18 ячеек на блок: сверяем поимённо, иначе одна правка внутри таблицы
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
                for idx, part in enumerate(("значение", "модификатор", "спасбросок")):
                    if text_cells[idx].replace("−", "-") != want_cells[idx]:
                        source = (f"PDF «{pdf_cells[idx]}», у нас ждём «{want_cells[idx]}»"
                                  if want_cells[idx] != pdf_cells[idx]
                                  else f"PDF «{pdf_cells[idx]}»")
                        failures.append(f"EN «{name}» {abil} {part}: "
                                        f"«{text_cells[idx]}» ≠ {source}")
                if abil in override:
                    problem = declared(fields.get("abilities_note"),
                                       (int(pdf_cells[2]), int(override[abil][2])))
                    if problem:
                        failures.append(f"эталон «{name}»: правка таблицы характеристик "
                                        f"объявлена, но {problem}")
            continue
        # Эталон хранит строку PDF; если у PDF там опечатка, в тексте ждём исправленную
        # форму, объявленную в самом эталоне.
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
        value = got.get(field)
        if value is None:
            failures.append(f"EN «{name}»: поле «{field}» потеряно (в PDF «{want}»)")
        elif canon(field, value) != canon(field, want):
            source = (f"PDF «{fields['cr']}», у нас ждём «{want}» ({fields.get('cr_note', '')})"
                      if field == "cr" and "cr_repo" in fields else f"PDF «{want}»")
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
        # наличия логовой оговорки пришпилен ниже счётчиком LAIR_BLOCKS: её стирание
        # согласованно из эталона и обоих текстов иначе было бы невидимо.
        if len(xp) > 1:
            step = XP_BY_CR.get(str(int(lead) + 1)) if "/" not in lead else None
            if step is None:
                failures.append(f"эталон «{name}»: логовый опыт {xp[1]} при ПО {lead} — "
                                f"проверить нечем, у ПО на ступень выше нет строки в таблице")
            elif xp[1] != step[0]:
                failures.append(f"эталон «{name}»: логовый опыт {xp[1]}, а по таблице "
                                f"{step[0]} (опыт ПО {int(lead) + 1})")
        pb = re.search(r"PB \+(\d+)", cr)
        want_pb = pb_by_cr(lead)
        if not pb:
            # СТИРАНИЕ бонуса мастерства — то же расхождение, что подделка: «29 ПО без
            # бонуса мастерства» были вторым по величине классом правок #260.
            problem = declared(fields.get("pb_note"), (want_pb,))
            if problem:
                failures.append(f"эталон «{name}»: в ПО «{cr}» нет бонуса мастерства "
                                f"(по таблице +{want_pb}); {problem}")
        elif int(pb.group(1)) != want_pb:
            problem = declared(fields.get("pb_note"), (int(pb.group(1)), want_pb))
            if problem:
                failures.append(f"эталон «{name}»: ПО {lead} — бонус мастерства "
                                f"+{pb.group(1)}, а по таблице +{want_pb}; {problem}")
for name in sorted(set(en_blocks) - set(expected)):
    failures.append(f"EN: статблок «{name}» есть в тексте, но не в эталоне PDF")

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
            if not ru_cells:
                failures.append(f"RU «{name}»: в таблице характеристик нет «{abil}»")
            elif [c.replace("−", "-") for c in ru_cells] != [c.replace("−", "-") for c in en_cells]:
                failures.append(f"RU «{name}» {abil}: {ru_cells} ≠ EN {en_cells}")
    # Снаряжение: количество пишется скобкой («Daggers (10)» / «Кинжалы (10)»), и это
    # форма записи, а не перевод, — иначе откат к «Кинжал x 10» виден только глазами.
    if "gear" in fields and "gear" in got and fields["gear"].count("(") != got["gear"].count("("):
        failures.append(f"RU «{name}» снаряжение: «{got['gear']}» записано иначе, чем "
                        f"EN «{fields['gear']}» — количество пишется скобкой")
    # Шапка врезок не сверяется гейтом шапок (тот читает только главы монстров и
    # указатели), поэтому размер сверяем здесь — по тем же словарям.
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
for name in sorted(set(ru_blocks) - set(en_blocks)):
    failures.append(f"RU: статблок «{name}» есть в переводе, но не в EN")

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
            score, mod, save = (int(c.replace("−", "-").replace("+", "")) for c in cells)
        except ValueError:
            failures.append(f"EN «{name}» {abil}: в таблице характеристик не числа {cells}")
            continue
        if mod != (score - 10) // 2:
            failures.append(f"EN «{name}» {abil}: модификатор {mod:+d} не выводится из "
                            f"значения {score} — ожидался {(score - 10) // 2:+d}")
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
# Метки полей: «Gear»/«CR» без двоеточия, остальные с ним — и одинаково в обоих языках.
# Проверяем ВСЕ метки глав; врезки живут по другой форме (там двоеточия нет ни у одной
# метки), поэтому их строки сюда не входят.
for lang, folder, labels in (("en", en_dir, EN_LABELS), ("ru", ru_dir, RU_LABELS)):
    pairs = [(label, label not in ("Gear", "Снаряжение")) for label in labels]
    pairs += [("CR", False)] if lang == "en" else [("ПО", False)]
    for chapter in ("12_MonstersA-Z.md", "13_Animals.md"):
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
for lang, gloss_dir, offset in (("en", en_dir, 0), ("ru", ru_dir, 1)):
    for index, has_align in (("04_Monsters.md", True), ("05_Animals.md", False)):
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
            if "ac" in block and ac != block["ac"].strip():
                failures.append(
                    f"{lang}-указатель {index}, «{name}»: КД «{ac}» ≠ «{block['ac']}»")
            if "hp" in block and hp != hp_value(block["hp"]):
                failures.append(
                    f"{lang}-указатель {index}, «{name}»: хиты «{hp}» ≠ «{hp_value(block['hp'])}»")

if failures:
    print(f"❌ Поля статблоков разошлись с эталоном PDF ({len(failures)}):")
    for f in failures[:40]:
        print(f"  — {f}")
    if len(failures) > 40:
        print(f"  … и ещё {len(failures) - 40}")
    sys.exit(1)

print(f"✅ Поля статблоков {VERSION}: сверено блоков — {len(expected)}, ячеек — {_cells}; "
      f"RU-зеркало и указатели сходятся")
