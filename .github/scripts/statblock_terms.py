#!/usr/bin/env python3
"""Словари шапки статблока: типы существ из словаря перевода и мировоззрения.

Гейтов, читающих шапку, два — шапок (`test_statblock_headers.py`, главы монстров и
указатели) и полей (`test_statblock_fields.py`, в том числе ВРЕЗКИ в главах предметов и
заклинаний, которых первый не видит). Пока разбор жил только в гейте шапок, у врезки
сверялся один размер: подмена типа и мировоззрения в RU-врезке проходила зелёной (#271).
Копировать разбор во второй гейт значило бы завести второе место для расхождения —
поэтому он здесь, а оба гейта его импортируют.

Разрез шапки («размер тип» | мировоззрение) сюда НЕ скопирован: его реализация одна —
`parsers.monster.split_header`, продукционная, и оба гейта зовут её отсюда (#290). Здесь
разрезов было ДВА: верный `split_header` (он и переехал в парсер) и разрез по ПЕРВОЙ
запятой внутри `parts_en` и `size_agreement` — тот же дефект, что в `parts_ru` гейта
шапок: на составном типе вне скобок мировоззрение получалось из куска типа.

Тип существа переводится ТОЛЬКО словарём `src/dnd/translate/01_dictionary_base.md`:
он читается, а не копируется в код (#256).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Разрез шапки на «размер тип» и мировоззрение — ОДИН на репозиторий и берётся из
# продукционного парсера: здесь своих было две, и одна из них — внутри `parts_en` —
# резала по первой запятой и разрывала составной тип пополам (#290).
from parsers.monster import split_header  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DICT = ROOT / "src/dnd/translate/01_dictionary_base.md"
# Подтипы лежат ОТДЕЛЬНО от словаря: семь их ключей («Cleric», «Wizard», «Dwarf»…)
# совпадают с именами классов и рас, а пишутся со строчной, и в общем namespace
# `build_term_map.py` они перекрывали переводы сущностей («Орк» → «орк»).
SUBTYPE_DICT = ROOT / "src/dnd/translate/statblock_subtypes.md"

SIZES_EN = ["Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"]
SIZE_ALT = "|".join(SIZES_EN)
SIZE_RE = re.compile(rf"^((?:{SIZE_ALT})(?: or (?:{SIZE_ALT}))?)\s+(.*)$")

# Мировоззрение RU → EN. Только мужской род: средние формы принимаются лишь у версий,
# объявивших послабление (см. `neuter_ok`).
ALIGN_RU = {
    "без мировоззрения": "Unaligned",
    "нейтральный": "Neutral",
    "нейтрально-злой": "Neutral Evil",
    "нейтрально-добрый": "Neutral Good",
    "хаотично-злой": "Chaotic Evil",
    "хаотично-добрый": "Chaotic Good",
    "хаотично-нейтральный": "Chaotic Neutral",
    "принципиально-злой": "Lawful Evil",
    "принципиально-добрый": "Lawful Good",
    "принципиально-нейтральный": "Lawful Neutral",
}
# «Любое не-доброе мировоззрение» → «Any Non-good Alignment» (форма 5.1).
ANY_RU = {
    "": "Any Alignment",
    "не-доброе": "Any Non-good Alignment",
    "не-принципиальное": "Any Non-lawful Alignment",
    "хаотичное": "Any Chaotic Alignment",
    "злое": "Any Evil Alignment",
}
ANY_RE = re.compile(r"^любое(?: (.+?))? мировоззрение$")
PERCENT_RE = re.compile(r"^(.*?)\s*(\(\d+%\))$")

DASH = {"-", "—"}


def check_dictionary_sections() -> list:
    """Расхождения кода со словарём по мировоззрениям и размерам.

    `ALIGN_RU` и `SIZE_FORMS` — формы, которых словарь не хранит (склонение по роду и
    строчная запись мировоззрения), поэтому копиями они и остаются. Но БАЗОВАЯ форма у
    словаря есть, и молча разъезжаться она не должна: до этой сверки правка «Lawful Evil →
    Законно-злой» в словаре не красила ни один гейт, хотя ровно этот класс (#256) считался
    закрытым (ревью #281).
    """
    problems = []
    aligns, trouble = dict_table(DICT, "Мировоззрение (Alignment)")
    sizes, trouble_sizes = dict_table(DICT, "Размеры (Sizes)")
    problems += trouble + trouble_sizes
    for en, ru in sorted(aligns.items()):
        # Синонимы источника («Neutral / True Neutral») ведут на один перевод; берём
        # первую форму — именно её печатают шапки.
        key = en.split(" / ")[0]
        got = ALIGN_RU.get(ru.lower())
        if got is None:
            problems.append(f"{DICT.name}: перевод мировоззрения «{ru}» (для «{key}») "
                            f"коду неизвестен — ALIGN_RU его не разберёт")
        elif got != key:
            problems.append(f"{DICT.name}: «{ru}» — это «{key}» по словарю и «{got}» "
                            f"по ALIGN_RU: перевод разъехался с кодом")
    for en, ru in sorted(sizes.items()):
        if en not in SIZE_FORMS:
            continue
        if ru not in SIZE_FORMS[en]:
            problems.append(f"{DICT.name}: размер «{en}» → «{ru}» в словаре, а SIZE_FORMS "
                            f"знает формы {SIZE_FORMS[en]} — перевод разъехался с кодом")
    return problems


def relative(path: Path) -> str:
    """Путь от корня репозитория, если он внутри; иначе — как есть."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def align_to_en(text: str, neuter_ok: bool = False):
    """(EN-мировоззрение или None, сработало ли послабление среднего рода).

    Отдельно разбираются «Любое … мировоззрение» и составное «X (50%) или Y (50%)»
    (облачный великан).
    """
    t = " ".join(text.strip().lower().split())
    if " или " in t:
        parts, used = [], False
        for chunk in t.split(" или "):
            m = PERCENT_RE.match(chunk.strip())
            base, tail = (m.group(1), f" {m.group(2)}") if m else (chunk.strip(), "")
            mapped, used_here = align_to_en(base, neuter_ok)
            if mapped is None:
                return None, used
            used = used or used_here
            parts.append(mapped + tail)
        return " or ".join(parts), used
    m = ANY_RE.match(t)
    if m:
        return ANY_RU.get(m.group(1) or ""), False
    if t in ALIGN_RU:
        return ALIGN_RU[t], False
    # Средний род («Хаотично-злое», «Нейтральное») — тот же термин, другое согласование:
    # пробуем оба мужских окончания, ударение в них разное («злой», но «добрый»).
    if neuter_ok and t.endswith("ое"):
        for ending in ("ый", "ой"):
            if t[:-2] + ending in ALIGN_RU:
                return ALIGN_RU[t[:-2] + ending], True
    return None, False


def dict_table(path: Path, section, report: bool = True):
    """({EN → RU}, [проблемы]) из таблицы файла словаря; section — заголовок или None.

    report=False читает молча: в словаре есть законные омонимы с пометкой в комментарии
    («Ammunition» — предмет «Боеприпасы» и свойство оружия «Боеприпас»), и жаловаться на
    них — не дело гейта, они и так видны в отчёте `build_term_map.py`.

    Колонки: оригинал 5.2, оригинал 5.1, перевод, источник 5.2, источник 5.1, комментарий.
    Оба оригинала ведут на один перевод, прочерк — «в этой редакции термина нет».
    """
    problems = []
    if not path.exists():
        # Путь ОТ КОРНЯ репозитория: абсолютный путь раннера («/home/runner/work/…»)
        # в логе CI не говорит читателю ничего.
        problems.append(f"словарь не найден: {relative(path)} — сверять не с чем")
        return {}, problems
    out, inside, rows_ru = {}, section is None, []
    for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        if section is not None and line.startswith("## "):
            inside = section in line
            continue
        if not inside or not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells[0].startswith("---") or cells[0].startswith("Оригинал"):
            continue
        # Ровно шесть колонок: лишняя проходила молча, потерянная давала «род для типа
        # «srd-5.2» не найден» — диагностику мимо причины.
        if len(cells) != 6:
            if report:
                problems.append(
                    f"{path.name}, строка {number}: колонок {len(cells)}, "
                    f"а должно быть 6: {line!r}")
            continue
        if not cells[2] or cells[2] in DASH:
            if report:
                problems.append(f"{path.name}, строка {number}: пустой перевод: {line!r}")
            continue
        rows_ru.append((number, cells[2], " / ".join(c for c in cells[:2] if c and c not in DASH)))
        reported = False
        for en in cells[:2]:
            if not en or en in DASH:
                continue
            # Противоречие внутри словаря разрешалось порядком строк: дубль ниже живой
            # строки молча игнорировался. Единственный источник правды не может зависеть
            # от того, куда редактор вставил строку.
            if en in out and out[en] != cells[2]:
                if report and not reported:
                    problems.append(
                        f"{path.name}, строка {number}: «{en}» переведён и как «{out[en]}», "
                        f"и как «{cells[2]}»")
                    reported = True
                continue
            out[en] = cells[2]
    # Коллизия в ОБРАТНУЮ сторону: два разных EN-термина с одним RU-переводом. Направление
    # RU→EN читает сверка врезки, и без этой проверки дефект словаря предъявлялся бы как
    # дефект текста — на правильных врезках (ревью #281).
    #
    # Считается только коллизия МЕЖДУ СТРОКАМИ: две колонки оригинала в одной строке —
    # это и есть формат («5.2 назвал так, 5.1 иначе»), и переименование термина между
    # редакциями не дефект (ревью #281, раунд 4).
    if report:
        seen: dict = {}
        for number, ru, keys in rows_ru:
            if ru in seen and seen[ru][0] != number:
                problems.append(f"{path.name}, строки {seen[ru][0]} и {number}: "
                                f"«{seen[ru][1]}» и «{keys}» переведены одинаково («{ru}») "
                                f"— обратный перевод неоднозначен")
            seen.setdefault(ru, (number, keys))
    return out, problems


def parts_en(header: str):
    """«Large Swarm of Tiny Beasts, Unaligned» → (размер, тип, подтип, мировоззрение).

    Разрез общий (`split_header`), а РАЗБОР левой части — свой: этой функцией гейт шапок
    сверяет продукционный парсер, и построй её поверх `_parse_type_line`, проверка стала
    бы сверкой парсера с самим собой.
    """
    split = split_header(header)
    if not split:
        return None
    left, alignment = split
    m = SIZE_RE.match(left)
    if not m:
        return None
    rest = m.group(2).strip()
    sub = re.match(r"^(.+?)\s*\((.+)\)$", rest)
    return (m.group(1), sub.group(1).strip() if sub else rest,
            sub.group(2).strip() if sub else None, alignment)


def type_terms(expr: str, terms) -> list:
    """Термины типа существа из выражения типа, в порядке появления.

    `terms` — набор терминов одного языка (ключи или значения словаря). Многословный
    термин («Swarm of Tiny Beasts», «Рой Крошечных зверей») берётся целиком: иначе его
    слова считались бы по отдельности и счёт терминов разошёлся бы с другой половиной.
    Сравнение ПОРЕГИСТРОВОЕ: тип пишется словарным термином с прописной, и спуск регистра —
    такой же дефект, как подмена слова (#256, #271).
    """
    alt = "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True))
    if not alt:
        return []
    pattern = re.compile(rf"(?<![A-Za-zА-Яа-яЁё])(?:{alt})(?![A-Za-zА-Яа-яЁё])")
    return [m.group(0) for m in pattern.finditer(expr)]


# Служебные слова шапки — всё, что в ней стоит помимо размера, типа и подтипа. Список
# ЗАКРЫТЫЙ: он и есть граница проверки «шапка сверяется строкой целиком», а не набором
# найденных терминов. Незнакомое слово в шапке — расхождение, а не служебная связка.
SERVICE = {
    "en": {"or": "OR", "smaller": "SMALLER", "and": "AND", "any": "ANY"},
    "ru": {"или": "OR", "меньший": "SMALLER", "меньшая": "SMALLER", "меньшее": "SMALLER",
           "и": "AND", "любой": "ANY", "любая": "ANY", "любое": "ANY"},
}
# Скобочные группы, которые НЕ являются подтипом («(Your Choice)» у Потустороннего
# скакуна): подтипы переводятся своим словарём, а это — служебная оговорка выбора.
PAREN_SERVICE = {"your choice": "на ваш выбор"}


def skeleton(expr: str, lang: str, types: dict, subtypes: dict, sizes_ru: dict) -> list:
    """Выражение типа как последовательность помеченных кусков, сведённых к EN.

    Каждое слово шапки относится ровно к одной категории: размер, термин типа, подтип
    в скобках, служебная связка. Всё, что не опознано, попадает в список как («?», слово)
    и потому не может совпасть с другой половиной: именно так дописка постороннего слова
    («Зверь-мутант») перестаёт быть невидимой. Значения приводятся к EN, поэтому списки
    половин сравниваются напрямую.

    `types` и `subtypes` — словарные карты EN → RU; `sizes_ru` — формы размера RU → EN.
    """
    to_en_type = {ru: en for en, ru in types.items()}
    to_en_sub = {ru: en for en, ru in subtypes.items()}
    paren_to_en = {ru: en for en, ru in PAREN_SERVICE.items()}
    out, rest, groups = [], expr, []
    for group in re.findall(r"\(([^()]*)\)", expr):
        rest = rest.replace(f"({group})", " ⟪PAREN⟫ ", 1)
        # Составной подтип пишется через запятую («(Demon, Shapechanger)»): режем группу
        # так же, как гейт шапок, иначе целая форма из семи шапок 5.1 не разбирается —
        # и «сверять не с чем» звучало бы одинаково и на верном тексте, и на подмене.
        parts = [part.strip() for part in group.split(",")] if "," in group else None
        # Словарь выбирается ПО ЯЗЫКУ: «часть есть хоть в одной карте» пускало сюда
        # EN-часть недопереведённого RU-подтипа («(Demon, перевёртыш)»), и обратная карта
        # роняла прогон KeyError'ом вместо строки отчёта (ревью #281).
        known = subtypes if lang == "en" else to_en_sub
        if parts and all(part in known for part in parts):
            groups.append(("subtype", ", ".join(part if lang == "en" else to_en_sub[part]
                                                for part in parts)))
            continue
        raw = group.strip()
        if lang == "en":
            # EN-половина читается из PDF, и регистр служебной оговорки там свой
            # («(Your Choice)»); RU-форма — наша конвенция, поэтому сверяется порегистрово,
            # как и термины: «(На ваш выбор)» — такое же расхождение, как «(демон)» вместо
            # «(перевёртыш)» (ревью #281).
            if raw in subtypes:
                groups.append(("subtype", raw))
            elif raw.lower() in PAREN_SERVICE:
                groups.append(("paren", raw.lower()))
            else:
                groups.append(("?", raw))
        elif raw in to_en_sub:
            groups.append(("subtype", to_en_sub[raw]))
        elif raw in paren_to_en:
            groups.append(("paren", paren_to_en[raw]))
        else:
            groups.append(("?", raw))
    # Термины типа (в том числе многословные) вынимаем ДО разбора по словам: иначе
    # «Рой Крошечных зверей» рассыпался бы на неопознанные слова.
    terms = type_terms(rest, types.keys() if lang == "en" else types.values())
    for term in terms:
        rest = rest.replace(term, " ⟪TERM⟫ ", 1)
    term_i = paren_i = 0
    # В поток токенов попадает ВСЁ, кроме пробелов: цифра или знак препинания, приклеенные
    # к слову конвертером PDF («Дракон 12», «Нежить!!!»), обязаны стать видимым «?»-токеном,
    # а не исчезнуть до классификации (ревью #281). Ровно этот класс мусора и есть причина,
    # по которой гейт вообще написан (#196).
    for token in re.findall(r"⟪TERM⟫|⟪PAREN⟫|[A-Za-zА-Яа-яЁё]+|\S", rest):
        if token == "⟪TERM⟫" and term_i < len(terms):
            term = terms[term_i]
            term_i += 1
            out.append(("type", term if lang == "en" else to_en_type.get(term, f"?{term}")))
        elif token == "⟪PAREN⟫" and paren_i < len(groups):
            out.append(groups[paren_i])
            paren_i += 1
        elif token in ("⟪TERM⟫", "⟪PAREN⟫"):
            # Такой же маркер, но ПРИШЕДШИЙ ИЗ ТЕКСТА: своих кусков на него не осталось.
            # Индексация без охраны роняла бы весь прогон трейсбеком — вместе с уже
            # накопленным отчётом о настоящих дефектах.
            out.append(("?", token))
        elif token == ",":
            out.append(("sep", ","))
        elif lang == "en" and token in SIZES_EN:
            out.append(("size", token))
        elif lang == "ru" and token.lower() in sizes_ru:
            out.append(("size", sizes_ru[token.lower()]))
        elif lang == "ru" and token in SERVICE["ru"]:
            out.append(("service", SERVICE["ru"][token]))
        elif lang == "en" and token.lower() in SERVICE["en"]:
            out.append(("service", SERVICE["en"][token.lower()]))
        else:
            out.append(("?", token))
    # Серийная запятая — английская типографика («Celestial, Fey, or Fiend»); в русском её
    # нет. Поэтому снимаем её ТОЛЬКО у английской половины: сняв у обеих, мы разрешили бы
    # лишнюю запятую в переводе («Фея, или Исчадие») — а это уже не типографика источника,
    # а расхождение перевода (ревью #281).
    if lang != "en":
        return out
    return [item for n, item in enumerate(out)
            if not (item == ("sep", ",") and out[n + 1:n + 2] == [("service", "OR")])]


# Формы размера по роду: (мужской, женский, средний). Обратная сторона SIZES_RU_TO_EN —
# она сводит все три рода к одному EN-значению, поэтому рассогласование («Большое Фея»)
# ей не видно вовсе.
SIZE_FORMS = {
    "Tiny": ("Крошечный", "Крошечная", "Крошечное"),
    "Small": ("Маленький", "Маленькая", "Маленькое"),
    "Medium": ("Средний", "Средняя", "Среднее"),
    "Large": ("Большой", "Большая", "Большое"),
    "Huge": ("Огромный", "Огромная", "Огромное"),
    "Gargantuan": ("Громадный", "Громадная", "Громадное"),
}
# Род русского термина типа — грамматика, а не терминология, поэтому таблица живёт здесь,
# а не в словаре. Полноту таблицы проверяет гейт шапок: тип из словаря, которого тут нет,
# — расхождение.
GENDER_RU = {
    "Зверь": 0, "Дракон": 0, "Гуманоид": 0, "Великан": 0, "Конструкт": 0,
    "Элементаль": 0, "Небожитель": 0, "Рой": 0,
    "Аберрация": 1, "Фея": 1, "Слизь": 1, "Нежить": 1,
    "Растение": 2, "Исчадие": 2, "Чудовище": 2,
}


# Формы связки границы диапазона по роду — тот же порядок, что у SIZE_FORMS.
SMALLER_FORMS = ("меньший", "меньшая", "меньшее")


def size_agreement(header: str, types_ru, sizes_ru: dict):
    """(сообщение или None, тип без рода в таблице или None, вид дефекта) — размер.

    «Большая Фея» верно, «Большое Фея» — нет. Составной размер проверяется по обоим
    прилагательным («Средняя или Маленькая Нежить»). Второе значение кортежа — термин,
    которого нет в таблице родов: звать его дефектом шапки нельзя, это дыра таблицы,
    и вызывающий копит такие термины отдельно. Третье — ВИД дефекта («род» или «тип»):
    версионное послабление выбирается по нему, а не грепом русского текста сообщения.
    """
    split = split_header(header)
    left = split[0] if split else header.strip()
    words, sizes, smaller, i = left.split(), [], [], 0
    while i < len(words):
        if words[i].lower() in sizes_ru:
            sizes.append(words[i]); i += 1
        elif words[i].lower() == "или" and sizes:
            i += 1
        elif words[i].lower() in SMALLER_FORMS and sizes:
            smaller.append(words[i]); i += 1
        else:
            break
    rest = words[i:]
    if not sizes or not rest:
        return None, None, None
    term = rest[0].strip("(),")
    gender = GENDER_RU.get(term)
    if gender is None:
        # Два разных дефекта — два разных сообщения. Если термин В СЛОВАРЕ есть, виновата
        # таблица родов; если нет — виновата шапка, и советовать «допишите в GENDER_RU»
        # значило бы предложить снять проверку, которую #256 только что поставил.
        # Сравниваем по первому слову словарного термина: тип роя записан целиком
        # («Рой Крошечных зверей»), а в шапке от него стоит «Рой».
        if term in {v.split()[0] for v in types_ru}:
            return None, term, None
        return (f"тип «{term}» не из словаря — в шапке он пишется словарным термином "
                f"с прописной (#256)"), None, "тип"
    for word in sizes:
        want = SIZE_FORMS[sizes_ru[word.lower()]][gender]
        if word != want:
            return (f"размер «{word}» не согласован с «{term}» — "
                    f"ожидалось «{want}»"), None, "род"
    # Связка границы диапазона — то же прилагательное и тот же род: «Огромный или меньший
    # Конструкт», но «Огромная или меньшая тварь». Без этой сверки род связки был свободен
    # (ревью #281).
    for word in smaller:
        want = SMALLER_FORMS[gender]
        if word != want:
            return (f"граница диапазона «{word}» не согласована с «{term}» — "
                    f"ожидалось «{want}»"), None, "род"
    return None, None, None
