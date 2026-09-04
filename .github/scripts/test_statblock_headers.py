#!/usr/bin/env python3
"""Сверка шапок статблоков с эталоном, выпиленным из официального PDF (issue #196).

Зачем нужен отдельный гейт. Импортированный текст 5.2 разошёлся с PDF ровно в одной
строке каждого статблока — «размер тип, мировоззрение»: пропал размер Tiny (25 существ),
составной размер «Medium or Small» схлопнулся в «Small» (36, из них 26 гуманоидов), у
семи роёв потерялся тип «Swarm of Tiny Beasts/Undead», у одиннадцати НИП — подтип в
скобках, у джинна — мировоззрение. Ни одна из потерь не ломает ни markdown, ни схему
JSON API: файл валиден, таблицы на месте, и все прежние проверки проходили. Поймать
такое можно только сверкой с источником — поэтому эталон лежит в репозитории.

Проверяем четыре уровня, потому что дефект расползается по ним по очереди:
  1) шапки EN — построчно против эталона;
  2) РАЗБОР шапки продукционным парсером JSON API (`parsers.monster._parse_type_line`) —
     иначе откат самого парсера проходит гейт: данные-то в файле верные, а `size`/`type`
     в API уезжают («Medium or Small Humanoid» → size=Medium, type=«or Small Humanoid»),
     и веб печатает битые ссылки на несуществующий хаб;
  3) указатели (`14_Glossary/04_Monsters.md`, `05_Animals.md`) — колонки собираются из
     шапок, плюс сверка САМОГО НАБОРА строк: пропажу строки целиком иначе не видно;
  4) RU-зеркало — размер, мировоззрение, подтип и признак роя сводятся к тем же значениям,
     что в EN, а САМИ ТЕРМИНЫ типа и подтипа сверяются со словарём
     (`src/dnd/translate/01_dictionary_base.md`); там же проверяется согласование рода
     прилагательного размера с типом. Второй источник правды здесь — словарь: он читается,
     а не копируется в код, иначе расхождение словаря и текста осталось бы незамеченным.

Версии берутся из имён фикстур (`srd-<версия>-statblock-headers.tsv`). Новая версия
подхватывается сама, но рассчитывать, что правки кода не потребуется, не стоит: у 5.1
свои формы заголовков, свой регистр в PDF и свой разнобой в переводе мировоззрения —
всё это пришлось учить. Послабления, нужные одной версии, объявляются В ФИКСТУРЕ
(строка «# опция: …»), чтобы не снимать проверку с остальных.

Запуск: python3 .github/scripts/test_statblock_headers.py
"""
import re
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]
sys.path.insert(0, str(SCRIPTS))
from parsers.monster import _parse_type_line  # noqa: E402

SIZES_EN = ["Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"]
SIZE_ALT = "|".join(SIZES_EN)
SIZE_RE = re.compile(rf"^((?:{SIZE_ALT})(?: or (?:{SIZE_ALT}))?)\s+(.*)$")
# Прилагательное согласуется с родом типа существа, поэтому вариантов больше, чем размеров.
SIZES_RU = {
    "крошечный": "Tiny", "крошечная": "Tiny", "крошечное": "Tiny",
    "маленький": "Small", "маленькая": "Small", "маленькое": "Small",
    "средний": "Medium", "средняя": "Medium", "среднее": "Medium",
    "большой": "Large", "большая": "Large", "большое": "Large",
    "огромный": "Huge", "огромная": "Huge", "огромное": "Huge",
    "громадный": "Gargantuan", "громадная": "Gargantuan", "громадное": "Gargantuan",
}
# Формы размера по роду: (мужской, женский, средний). Обратная сторона SIZES_RU — она
# сводит все три рода к одному EN-значению, поэтому рассогласование («Большое Фея»)
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
# а не в словаре. Полнота таблицы проверяется: тип из словаря, которого тут нет, — failure.
GENDER_RU = {
    "Зверь": 0, "Дракон": 0, "Гуманоид": 0, "Великан": 0, "Конструкт": 0,
    "Элементаль": 0, "Небожитель": 0, "Рой": 0,
    "Аберрация": 1, "Фея": 1, "Слизь": 1, "Нежить": 1,
    "Растение": 2, "Исчадие": 2, "Чудовище": 2,
}
# Мировоззрение RU → EN. Только мужской род: две средние формы, которые здесь стояли ради
# Древеня и Вермедведя из 5.2, сняты вместе с правкой их шапок — послаблением в коде
# держать нечего, а версиям, где перевод действительно несогласован, служит опция
# фикстуры (см. GENDER_DRIFT).
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

SPLIT_ALIGN = re.compile(r",\s*(?![^(]*\))")   # запятая мировоззрения, но не внутри скобок
# Словарь терминов — единственный источник правды для перевода типов существ. Гейт читает
# ЕГО, а не свою копию: иначе расхождение словаря и текста осталось бы незамеченным (#256).
DICT = ROOT / "src/dnd/translate/01_dictionary_base.md"
# Таксономический хвост в скобках: в 5.1 он есть и у заголовков статблоков («Deva (Angel)»),
# и у строк указателя — в ключ эталона он не входит.
STRIP_TAIL = re.compile(r"\s*\([^()]*\)$")
failures = []


# Версии, где перевод мировоззрения несогласован по роду («Нейтральное» и «Нейтральный»
# у одного значения). Послабление объявляется В ФИКСТУРЕ, а не в коде: 5.2 переведён
# согласованно, и молча разрешить ему «нейтральное» значило бы снять с него проверку.
GENDER_DRIFT: set = set()
# Сколько раз послабление реально спасло разбор. Ноль у версии, объявившей опцию, — это
# либо опция, скопированная в фикстуру, которой она не нужна (и тогда версия молча теряет
# строгость), либо перевод, уже починенный в #256. Оба случая требуют снять строку.
GENDER_USED: Counter = Counter()
# То же для рода ПРИЛАГАТЕЛЬНОГО РАЗМЕРА («Средний Нежить» вместо «Средняя»). В 5.2
# согласование починено, у 5.1 это отдельная правка — до неё версия объявляет опцию.
SIZE_DRIFT: set = set()
SIZE_USED: Counter = Counter()


def align_to_en(text: str, version: str):
    """RU-мировоззрение → EN-значение. None, если строка не опознана.

    Отдельно разбираются «Любое … мировоззрение» и составное «X (50%) или Y (50%)»
    (облачный великан). Средний род принимается только у версий из GENDER_DRIFT.
    """
    t = " ".join(text.strip().lower().split())
    if " или " in t:
        parts = []
        for chunk in t.split(" или "):
            m = PERCENT_RE.match(chunk.strip())
            base, tail = (m.group(1), f" {m.group(2)}") if m else (chunk.strip(), "")
            mapped = align_to_en(base, version)
            if mapped is None:
                return None
            parts.append(mapped + tail)
        return " or ".join(parts)
    m = ANY_RE.match(t)
    if m:
        return ANY_RU.get(m.group(1) or "")
    if t in ALIGN_RU:
        return ALIGN_RU[t]
    # Средний род («Хаотично-злое», «Нейтральное») — тот же термин, другое согласование:
    # пробуем оба мужских окончания, ударение в них разное («злой», но «добрый»).
    if version in GENDER_DRIFT and t.endswith("ое"):
        for ending in ("ый", "ой"):
            if t[:-2] + ending in ALIGN_RU:
                GENDER_USED[version] += 1
                return ALIGN_RU[t[:-2] + ending]
    return None


# Служебные слова, которые в наших шапках остаются со строчной («Swarm of Tiny Beasts»).
TITLE_LOWER = {"of", "or"}


def titlecase_header(raw: str) -> str:
    """Строка PDF → наш формат: каждое слово с прописной, кроме служебных.

    PDF 5.1 пишет тип и мировоззрение со строчной («Large aberration, lawful evil»),
    импорт приводит их к прописным. Преобразование механическое, поэтому его можно
    проверять, а не принимать на веру.
    """
    out = []
    for token in raw.split(" "):
        if out and token.lower().strip("(),") in TITLE_LOWER:
            out.append(token)
            continue
        m = re.search(r"[A-Za-z]", token)
        out.append(token if not m else token[:m.start()] + token[m.start()].upper()
                   + token[m.start() + 1:])
    return " ".join(out)


DASH = {"-", "—"}


def creature_types():
    """({EN-тип → RU}, {EN-подтип → RU}) из раздела «Типы существ» словаря.

    Колонки: оригинал 5.2, оригинал 5.1, перевод, источник 5.2, источник 5.1, комментарий.
    Оба оригинала ведут на один перевод, прочерк — «в этой редакции термина нет».
    Подтипы («Dragon (Chromatic)» → цветной) живут в подразделе «Подтипы» того же
    раздела — разделяет их заголовок, а не формулировка комментария: пометка прозой
    ломалась от любой правки текста, а показывала при этом на таблицу родов.
    """
    if not DICT.exists():
        failures.append(f"словарь не найден: {DICT.relative_to(ROOT)} — сверять типы не с чем")
        return {}, {}
    types, subtypes, inside, is_sub = {}, {}, False, False
    for number, line in enumerate(DICT.read_text(encoding="utf-8").split("\n"), 1):
        if line.startswith("## "):
            inside, is_sub = "Типы существ" in line, False
            continue
        if line.startswith("### "):
            is_sub = "Подтипы" in line
            continue
        if not inside or not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells[0].startswith("---") or cells[0] == "Оригинал 5.2":
            continue
        # Ровно шесть колонок: лишняя проходила молча, потерянная давала «род для типа
        # «srd-5.2» не найден» — диагностику мимо причины.
        if len(cells) != 6:
            failures.append(
                f"словарь, строка {number}: колонок {len(cells)}, а должно быть 6: {line!r}")
            continue
        target = subtypes if is_sub else types
        for en in cells[:2]:
            if not en or en in DASH:
                continue
            # Противоречие внутри словаря разрешалось порядком строк: дубль ниже живой
            # строки молча игнорировался. Единственный источник правды не может зависеть
            # от того, куда редактор вставил строку.
            if en in target and target[en] != cells[2]:
                failures.append(
                    f"словарь, строка {number}: «{en}» переведён и как «{target[en]}», "
                    f"и как «{cells[2]}»")
                continue
            target[en] = cells[2]
    return types, subtypes


TYPES_RU, SUBTYPES_RU = creature_types()


def paren_groups(text: str) -> list:
    """Группы верхнего уровня в скобках, с учётом вложенности."""
    out, depth, start = [], 0, None
    for i, ch in enumerate(text):
        if ch == "(":
            if depth == 0:
                start = i + 1
            depth += 1
        elif ch == ")" and depth:
            depth -= 1
            if depth == 0:
                out.append(text[start:i])
    return out


def en_group_from_ru_heading(heading: str) -> str:
    """Последняя группа скобок с латиницей — имя оригинала КАК НАПИСАНО, с хвостом."""
    latin = [g for g in paren_groups(heading) if re.search(r"[A-Za-z]", g)]
    return latin[-1].strip() if latin else heading.strip()


def en_name_from_ru_heading(heading: str) -> str:
    """Оригинальное имя из RU-заголовка статблока.

    В 5.2 всё просто: «Летучая мышь (Bat)». В 5.1 заголовки разнородны — «Балор (Balor)
    (Демон)», «Андросфинкс (Androsphinx (Sphinx))», «Гном глубинный (свирфнеблин)
    (Gnome, Deep (Svirfneblin))». Берём последнюю группу скобок с латиницей и снимаем
    её собственный таксономический хвост — так ключ сходится с именем EN-заголовка.
    """
    return STRIP_TAIL.sub("", en_group_from_ru_heading(heading)).strip()


def ru_part_from_heading(heading: str) -> str:
    """RU-имя из заголовка: всё до последней группы скобок с латиницей.

    «Взрослый золотой дракон (Металлический) (Adult Gold Dragon (Metallic))» →
    «Взрослый золотой дракон (Металлический)».
    """
    latin = [g for g in paren_groups(heading) if re.search(r"[A-Za-z]", g)]
    if not latin:
        return heading.strip()
    idx = heading.rfind("(" + latin[-1])
    return heading[:idx].strip() if idx > 0 else heading.strip()


def headers(path: Path, lang: str):
    """({ключ → шапка}, {как написано в заголовке → ключ}).

    Ключ — имя без таксономического хвоста («Deva» для «### Deva (Angel)»), потому что в
    эталоне PDF хвоста нет. Вторую карту держим отдельно: строки указателей сверяются по
    ПОЛНОМУ имени, иначе подмена хвоста («Aboleth» → «Aboleth (Angel)») пройдёт молча.
    """
    out, alias, name, full = {}, {}, None, None
    first_letter = "A-Z" if lang == "en" else "А-ЯЁ"
    for line in path.read_text(encoding="utf-8").split("\n"):
        s = line.strip()
        if s.startswith("#"):
            m = re.match(r"^#{2,4} (.+)$", s)
            if m:
                full = m.group(1).strip()
                name = (en_name_from_ru_heading(full) if lang == "ru"
                        else STRIP_TAIL.sub("", full).strip())
            continue
        m = re.match(rf"^\*([{first_letter}][^*]*)\*$", s)
        if m and name and not s.startswith("**"):
            out.setdefault(name, m.group(1))
            # Только ПОЛНОЕ имя заголовка. Короткий ключ («Deva» рядом с «Deva (Angel)»)
            # не нужен ни одной из 1294 строк указателей и делает карту односторонней:
            # с ним и снятие хвоста из строки указателя, и его дописывание проходят молча.
            alias.setdefault(full, name)
            if lang == "ru":
                # Колонка «Монстр» RU-указателя несёт RU-имя — по конвенции указателя без
                # таксономического хвоста («Взрослый золотой дракон» против «… (Металлический)»
                # в заголовке), поэтому в карту кладём обе формы. ДОПИСАННЫЙ хвост ключа
                # не найдёт и останется красным.
                ru_part = ru_part_from_heading(full)
                alias.setdefault(ru_part, name)
                alias.setdefault(STRIP_TAIL.sub("", ru_part).strip(), name)
            name = None
    return out, alias


def parts_en(header: str):
    """«Large Swarm of Tiny Beasts, Unaligned» → (размер, тип, подтип, мировоззрение)."""
    chunks = SPLIT_ALIGN.split(header, maxsplit=1)
    if len(chunks) != 2:
        return None
    m = SIZE_RE.match(chunks[0].strip())
    if not m:
        return None
    rest = m.group(2).strip()
    sub = re.match(r"^(.+?)\s*\((.+)\)$", rest)
    return (m.group(1), sub.group(1).strip() if sub else rest,
            sub.group(2).strip() if sub else None, chunks[1].strip())


def parts_ru(header: str, version: str):
    """То же для RU, но значения приводятся к EN.

    Возвращает (размер, подтип, мировоззрение, сырой тип). Последний элемент — RU-строка
    типа как есть: сверять её со словарём пока нельзя (термины расщеплены, #256), но по
    ней проверяется признак роя.
    """
    chunks = SPLIT_ALIGN.split(header, maxsplit=1)
    if len(chunks) != 2:
        return None
    first, alignment = chunks[0].strip(), chunks[1].strip()
    words = first.split()
    # Составной размер разбирается ТЕМ ЖЕ шаблоном, что EN «X or Y»: союз обязателен,
    # иначе «Средний Маленький гуманоид» (потерянное «или») прошло бы молча, а парсер
    # JSON API разобрал бы это как size=Средний, type=«Маленький гуманоид».
    if len(words) > 3 and words[1].lower() == "или" \
            and words[0].lower() in SIZES_RU and words[2].lower() in SIZES_RU:
        size = f"{SIZES_RU[words[0].lower()]} or {SIZES_RU[words[2].lower()]}"
        rest = " ".join(words[3:])
    elif words and words[0].lower() in SIZES_RU:
        size, rest = SIZES_RU[words[0].lower()], " ".join(words[1:])
    else:
        return None
    sub = re.match(r"^(.+?)\s*\((.+)\)$", rest.strip())
    return (size, sub.group(2).strip() if sub else None,
            align_to_en(alignment, version), rest.strip())


def size_agreement(header: str, version: str):
    """Ошибка согласования размера с родом типа, либо None.

    «Большая Фея» верно, «Большое Фея» — нет. Составной размер проверяется по обоим
    прилагательным: «Средняя или Маленькая Нежить».
    """
    left = SPLIT_ALIGN.split(header, maxsplit=1)[0]
    words, sizes, i = left.split(), [], 0
    while i < len(words):
        if words[i].lower() in SIZES_RU:
            sizes.append(words[i]); i += 1
        elif words[i].lower() == "или" and sizes:
            i += 1
        else:
            break
    rest = words[i:]
    if not sizes or not rest:
        return None
    term = rest[0].strip("(),")
    gender = GENDER_RU.get(term)
    if gender is None:
        # Не «допишите в GENDER_RU»: почти всегда сюда приводит расщеплённый или
        # написанный со строчной термин в самой шапке, и совет править таблицу означал бы
        # снять проверку, которую #256 только что поставил.
        return (f"тип «{term}» не из словаря — в шапке он пишется словарным термином "
                f"с прописной (#256); таблицу родов правят, только когда тип НОВЫЙ")
    for word in sizes:
        want = SIZE_FORMS[SIZES_RU[word.lower()]][gender]
        if word != want:
            if version in SIZE_DRIFT:
                SIZE_USED[version] += 1
                return None
            return f"размер «{word}» не согласован с «{term}» — ожидалось «{want}»"
    return None


def index_rows(path: Path) -> list:
    """Строки markdown-таблицы указателя как списки ячеек (без шапки таблицы)."""
    out = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        if not line.startswith("| ") or line.startswith("|---"):
            continue
        out.append([c.strip() for c in line.strip().strip("|").split("|")])
    return out[1:]


def statblock_files(version_dir: Path) -> list:
    files = sorted(version_dir.glob("*MonstersA-Z.md")) + sorted(version_dir.glob("*Animals.md"))
    return files


# Объявления в шапке фикстуры: «# опция: <имя>».
OPTION_RE = re.compile(r"^#\s*опция:\s*(\S+)\s*$")
OPTIONS = {"род-мировоззрения-несогласован", "род-размера-несогласован"}


def check_version(version: str, fixture: Path) -> None:
    expected, raw_pdf, seen = {}, {}, {}
    for number, line in enumerate(fixture.read_text(encoding="utf-8").split("\n"), 1):
        if line.startswith("#"):
            m = OPTION_RE.match(line)
            if m:
                if m.group(1) not in OPTIONS:
                    failures.append(f"{version}: неизвестная опция фикстуры «{m.group(1)}»")
                elif m.group(1) == "род-мировоззрения-несогласован":
                    GENDER_DRIFT.add(version)
                elif m.group(1) == "род-размера-несогласован":
                    SIZE_DRIFT.add(version)
            continue
        if not line.strip():
            continue
        # Колонок минимум две; третья (сырая строка PDF) не обязательна, но если она есть
        # у одной строки — обязана быть у всех (см. сверку ниже). Разбор битой строки
        # не роняем трейсбеком: фикстура правится руками.
        parts = line.split("\t")
        if len(parts) < 2 or not parts[0].strip() or not parts[1].strip():
            failures.append(f"{version}: строка {number} фикстуры не разбирается: {line!r}")
            continue
        if parts[0] in seen:
            failures.append(
                f"{version}: имя «{parts[0]}» в фикстуре дважды (строки {seen[parts[0]]} и {number})")
            continue
        seen[parts[0]] = number
        expected[parts[0]] = parts[1]
        if len(parts) > 2 and parts[2].strip():
            raw_pdf[parts[0]] = parts[2]

    # Третья колонка — сырая строка PDF. Вторая обязана быть ею же, приведённой к нашему
    # регистру, иначе эталон разъедется с источником молча. Инвариант применяется построчно,
    # поэтому удаление колонки у одной строки его просто выключало бы — требуем «у всех
    # или ни у одной».
    if raw_pdf and len(raw_pdf) != len(expected):
        failures.append(
            f"{version}: третья колонка (строка PDF) есть у {len(raw_pdf)} строк "
            f"из {len(expected)} — она либо у всех, либо ни у одной")
    for name, raw in raw_pdf.items():
        if titlecase_header(raw) != expected[name]:
            failures.append(
                f"{version} эталон «{name}»: ожидаемая шапка «{expected[name]}» ≠ строке PDF "
                f"«{raw}» после нормализации регистра")

    en_dir, ru_dir = ROOT / f"src/dnd/{version}/en", ROOT / f"src/dnd/{version}/ru"
    en_headers, ru_headers, alias = {}, {}, {"en": {}, "ru": {}}
    for f in statblock_files(en_dir):
        found, names = headers(f, "en")
        en_headers.update(found)
        alias["en"].update(names)
    for f in statblock_files(ru_dir):
        found, names = headers(f, "ru")
        ru_headers.update(found)
        alias["ru"].update(names)

    # --- 1+2. Шапки EN против эталона и разбор их продукционным парсером ----------------
    for name, header in sorted(expected.items()):
        got = en_headers.get(name)
        if got is None:
            failures.append(f"{version} EN: статблок «{name}» из эталона не найден")
            continue
        if got != header:
            failures.append(f"{version} EN «{name}»: получили «{got}», в PDF «{header}»")
            continue
        want = parts_en(header)
        if want is None:
            failures.append(f"{version} эталон «{name}»: шапка «{header}» не разбирается")
            continue
        parsed = _parse_type_line(f"*{header}*", "en")
        got_parts = (parsed["size"], parsed["type"], parsed["subtype"], parsed["alignment"])
        if got_parts != want:
            failures.append(
                f"{version} EN «{name}»: парсер JSON API разобрал шапку как {got_parts}, "
                f"а она значит {want}")
    for name in sorted(set(en_headers) - set(expected)):
        failures.append(f"{version} EN: статблок «{name}» есть в тексте, но не в эталоне PDF")
    # Симметрично для RU: обход зеркала идёт по эталону, поэтому ЛИШНИЙ RU-статблок
    # не видела ни одна проверка — ни словарная, ни род, ни мировоззрение.
    for name in sorted(set(ru_headers) - set(expected)):
        failures.append(f"{version} RU: статблок «{name}» есть в тексте, но не в эталоне PDF")

    # --- 3. Указатели: и содержимое колонок, и сам набор строк --------------------------
    # Имена, перечисленные в указателях версии, копим по языкам: указатель монстров и
    # указатель животных делят один эталон, поэтому недостачу считаем по их объединению.
    index_names: dict = {"en": set(), "ru": set()}
    for lang, gloss_dir in (("en", en_dir), ("ru", ru_dir)):
        for index, has_alignment in (("04_Monsters.md", True), ("05_Animals.md", False)):
            path = next(iter(gloss_dir.glob(f"*Glossary/{index}")), None)
            if path is None:
                continue
            rows = index_rows(path)
            # Подпись под таблицей — тоже данные: пока её никто не сверял, «Total: 277»
            # под 317 строками жило в репозитории и уехало на прод.
            total = re.search(r"^(?:Total|Всего):\s*(\d+)\s", path.read_text(encoding="utf-8"),
                              re.MULTILINE)
            if total is None:
                failures.append(f"{version} {lang}-указатель {index}: нет подписи с числом строк")
            elif int(total.group(1)) != len(rows):
                failures.append(
                    f"{version} {lang}-указатель {index}: подпись обещает {total.group(1)}, "
                    f"строк в таблице {len(rows)}")
            for cells in rows:
                # Имя строки: в EN-указателе первая колонка, в RU — вторая («Оригинал (EN)»).
                listed = cells[0] if lang == "en" else (cells[1] if len(cells) > 1 else cells[0])
                # Сверяем по ТОМУ ЖЕ имени, что стоит в заголовке статблока, включая
                # таксономический хвост: срезать его вслепую значит пропустить подмену
                # («Aboleth» → «Aboleth (Angel)» — строка указателя врёт, гейт молчит).
                # Колонка «Оригинал (EN)» RU-указателя несёт ИМЕННО EN-имя, поэтому
                # разрешаем её по EN-карте имён, а не по RU.
                key = alias["en"].get(listed)
                if key is None:
                    failures.append(
                        f"{version} {lang}-указатель {index}: строка «{listed}» без статблока")
                    continue
                index_names[lang].add(key)
                header = (en_headers if lang == "en" else ru_headers).get(key)
                if header is None:
                    failures.append(f"{version} {lang}-указатель {index}: строка «{listed}» без шапки")
                    continue
                if lang == "ru":
                    # Колонка «Монстр» до сих пор не сверялась ничем: подмена RU-имени и
                    # рассинхрон пары «Монстр»/«Оригинал (EN)» проходили молча.
                    ru_key = alias["ru"].get(cells[0])
                    if ru_key is None:
                        failures.append(
                            f"{version} ru-указатель {index}: имя «{cells[0]}» не совпадает "
                            f"ни с одним RU-заголовком статблока")
                    elif ru_key != key:
                        failures.append(
                            f"{version} ru-указатель {index}: «{cells[0]}» — это статблок "
                            f"«{ru_key}», а в колонке «Оригинал (EN)» стоит «{listed}»")
                    continue  # размер и мировоззрение сверяются ниже, отдельным блоком
                want = parts_en(header)
                if want is None:
                    failures.append(f"{version} EN «{key}»: шапка «{header}» не разбирается")
                    continue
                size, ctype, sub, alignment = want
                full_type = f"{ctype} ({sub})" if sub else ctype
                cols = [size, full_type] + ([alignment] if has_alignment else [])
                if cells[1:1 + len(cols)] != cols:
                    failures.append(
                        f"{version} EN-указатель {index}, «{key}»: {cells[1:1 + len(cols)]} ≠ шапка {cols}")

    # Пропажа строки указателя целиком: обход по строкам таблицы её по определению не видит.
    for lang in ("en", "ru"):
        missing = sorted(set(expected) - index_names[lang])
        if missing:
            failures.append(
                f"{version} {lang}-указатели: нет строк для {len(missing)} статблоков "
                f"({', '.join(missing[:5])}{'…' if len(missing) > 5 else ''})")

    # --- 4. RU-зеркало: размер, мировоззрение, подтип, признак роя ----------------------
    # Незнакомые словарю термины копим и печатаем ОДНОЙ строкой на версию: внутри цикла
    # одна удалённая строка словаря давала сотни одинаковых сообщений и вытесняла из
    # отчёта настоящие дефекты — ровно на том входе, ради которого гейт и написан.
    unknown_types, unknown_subtypes = set(), set()
    for name, header in sorted(expected.items()):
        got = ru_headers.get(name)
        if got is None:
            failures.append(f"{version} RU: статблок «{name}» не найден")
            continue
        want = parts_en(header)
        if want is None:
            failures.append(f"{version} эталон «{name}»: шапка «{header}» не разбирается")
            continue
        ru = parts_ru(got, version)
        if ru is None:
            failures.append(f"{version} RU «{name}»: шапка «{got}» не разбирается")
            continue
        want_size, want_type, want_sub, want_align = want
        ru_size, ru_sub, ru_align, ru_type = ru
        if ru_size != want_size:
            failures.append(f"{version} RU «{name}»: размер «{got}» → {ru_size}, в EN {want_size}")
        if ru_align is None:
            failures.append(f"{version} RU «{name}»: мировоззрение «{got}» не из списка")
        elif ru_align != want_align:
            failures.append(f"{version} RU «{name}»: мировоззрение {ru_align}, в EN {want_align}")
        if (ru_sub is None) != (want_sub is None):
            failures.append(
                f"{version} RU «{name}»: подтип {'потерян' if want_sub else 'лишний'} "
                f"(EN {want_sub or 'без подтипа'}, RU «{got}»)")
        if want_type.startswith("Swarm of") and "рой" not in ru_type.lower():
            failures.append(f"{version} RU «{name}»: тип роя потерян — «{got}»")
        # Согласование прилагательного размера с родом типа: «Большая Фея», не «Большое».
        problem = size_agreement(got, version)
        if problem:
            failures.append(f"{version} RU «{name}»: {problem} (шапка «{got}»)")
        # Термин типа против словаря. Ровно этим гейт не занимался, и в 5.2 накопилось
        # расщепление: «чудовищность» и «чудовище» у одного Monstrosity, «конструкция»
        # рядом с «конструкт» (#256).
        want_ru = TYPES_RU.get(want_type)
        got_ru = re.sub(r"\s*\(.*\)\s*$", "", ru_type).strip()
        if want_ru is None:
            unknown_types.add(want_type)
        elif got_ru != want_ru:
            failures.append(
                f"{version} RU «{name}»: тип «{got_ru}», в словаре {want_type} → «{want_ru}»")
        # Подтип в скобках — свой термин и свой раздел словаря. Без этой сверки
        # согласованная подмена «(цветной)» → «(хроматический)» СРАЗУ в шапках и в
        # указателе проходила молча, а три строки подтипов в словаре никто не читал.
        if want_sub is not None and ru_sub is not None:
            # Составной подтип («Demon, Shapechanger») сверяется покомпонентно.
            want_parts = [p.strip() for p in want_sub.split(",")]
            got_parts = [p.strip() for p in ru_sub.split(",")]
            want_sub_ru = [SUBTYPES_RU.get(p) for p in want_parts]
            for part, mapped in zip(want_parts, want_sub_ru):
                if mapped is None:
                    unknown_subtypes.add(part)
            if all(want_sub_ru) and (len(want_parts) != len(got_parts) or any(
                    a.lower() != b.lower() for a, b in zip(got_parts, want_sub_ru))):
                failures.append(
                    f"{version} RU «{name}»: подтип «{ru_sub}», в словаре {want_sub} → "
                    f"«{', '.join(want_sub_ru)}»")

    # --- RU-указатели: размер, тип и мировоззрение --------------------------------------
    # Мировоззрение здесь — не украшение: именно этой колонкой в 5.1 проехала форма
    # «Принципиально-злый», которой в русском нет, — значение при этом «узнаваемое».
    for term in sorted(unknown_types):
        failures.append(f"{version} словарь: типа существа «{term}» нет в «Типы существ»")
    for term in sorted(unknown_subtypes):
        failures.append(
            f"{version} словарь: подтипа «{term}» нет в подразделе «Подтипы» "
            f"раздела «Типы существ»")

    # Послабление, которым никто не пользуется, — это снятая строгость без причины.
    for option, used in (("род-мировоззрения-несогласован", GENDER_USED),
                         ("род-размера-несогласован", SIZE_USED)):
        drift = GENDER_DRIFT if used is GENDER_USED else SIZE_DRIFT
        if version in drift and not used[version]:
            failures.append(
                f"{version}: опция «{option}» ни разу не понадобилась — "
                f"удалите её из фикстуры")

    for index, align_col in (("04_Monsters.md", 4), ("05_Animals.md", None)):
        path = next(iter(ru_dir.glob(f"*Glossary/{index}")), None)
        if path is None:
            continue
        width = 5 if align_col is not None else 4   # имя, оригинал, размер, тип [, мировоззрение]
        for cells in index_rows(path):
            key = alias["en"].get(cells[1]) if len(cells) > 1 else None
            if key is None or key not in expected:
                continue
            # Раньше короткая строка молча выключала все сверки ниже — а «строка потеряла
            # хвост колонок» это ровно тот класс, ради которого живёт layout recovery.
            if len(cells) < width:
                failures.append(
                    f"{version} RU-указатель {index}, «{key}»: колонок {len(cells)}, "
                    f"а нужно минимум {width} — строка обрезана")
                continue
            want = parts_en(expected[key])
            if want is None:
                failures.append(f"{version} эталон «{key}»: шапка не разбирается")
                continue
            ru = parts_ru(f"{cells[2]} тип, без мировоззрения", version)
            if ru is None or ru[0] != want[0]:
                failures.append(
                    f"{version} RU-указатель {index}, «{key}»: размер «{cells[2]}» ≠ {want[0]}")
            # Колонка «Тип» — та же строка, что в шапке статблока. Пока её не сверяли,
            # четыре животных 5.2 стояли в указателе «Зверь» при «Небожитель»/«Чудовище»
            # в шапке и в EN (#256).
            ru_head = parts_ru(ru_headers.get(key, ""), version)
            if ru_head is not None and cells[3] != ru_head[3]:
                failures.append(
                    f"{version} RU-указатель {index}, «{key}»: тип «{cells[3]}» ≠ "
                    f"шапке «{ru_head[3]}»")
            if align_col is not None:
                # Версия намеренно пустая: послабление по роду объявлено для ШАПОК
                # статблоков, а в колонках указателей средних форм нет ни одной —
                # гасить их здесь значило бы расширить опцию за пределы обоснования.
                got = align_to_en(cells[align_col], "")
                if got is None:
                    failures.append(
                        f"{version} RU-указатель {index}, «{key}»: мировоззрение "
                        f"«{cells[align_col]}» не из списка")
                elif got != want[3]:
                    failures.append(
                        f"{version} RU-указатель {index}, «{key}»: мировоззрение {got}, "
                        f"в EN {want[3]}")


def other_type_maps() -> list:
    """Копии карты «тип существа → RU» вне словаря: (что это, {EN: RU}).

    Их четыре штуки на репозиторий, и до сих пор они не сверялись ни с чем: откат
    правки «Фея» в вебе проходил зелёным, хотя метка идёт в <title>, <h1> и крошки
    хабов. E2E тут страховкой быть не могут — в CI они не гоняются.
    """
    maps = []
    for path, en_first in ((ROOT / "src/dnd/srd-5.2/ru/14_Glossary/00_Glossary.md", True),
                           (ROOT / "src/dnd/srd-5.1/ru/16_Glossary/00_Glossary.md", False)):
        if not path.exists():
            continue
        table, inside = {}, False
        for line in path.read_text(encoding="utf-8").split("\n"):
            if line.startswith("#"):
                inside = "Типы существ" in line
                continue
            if not inside or not line.startswith("| ") or line.startswith("|---"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 2 or cells[0] in {"English", "Тип"}:
                continue
            en, ru = (cells[0], cells[1]) if en_first else (cells[1], cells[0])
            table[en] = ru
        maps.append((f"глоссарий {path.relative_to(ROOT)}", table))

    hubs = ROOT / "web/src/lib/monster-hubs.ts"
    if hubs.exists():
        table = {m.group(1): m.group(2) for m in re.finditer(
            r"en:\s*'([^']+)',\s*ru:\s*'([^']+)'", hubs.read_text(encoding="utf-8"))}
        maps.append(("web/src/lib/monster-hubs.ts", table))
    return maps


# Копии карты обязаны совпадать со словарём — там, где термин им известен. Своих терминов
# у копий хватает («Swarm» у хабов), поэтому сверяем пересечение, а не равенство.
for _what, _table in other_type_maps():
    for _en, _ru in sorted(_table.items()):
        _want = TYPES_RU.get(_en)
        if _want is not None and _ru != _want:
            failures.append(
                f"{_what}: «{_en}» → «{_ru}», а в словаре «{_want}»")

# Таблица родов обязана покрывать словарь целиком: иначе новый тип существа молча
# выпадет из сверки согласования.
for _ru in sorted(set(TYPES_RU.values())):
    if _ru.split()[0] not in GENDER_RU:
        failures.append(f"GENDER_RU: нет рода для типа «{_ru}» из словаря")

fixtures = sorted(SCRIPTS.glob("fixtures/srd-*-statblock-headers.tsv"))
if not fixtures:
    print("❌ не найдено ни одной фикстуры шапок — проверять нечего")
    sys.exit(1)

versions = []
for fixture in fixtures:
    m = re.match(r"(srd-[\d.]+)-statblock-headers\.tsv", fixture.name)
    if not m:
        failures.append(f"фикстура «{fixture.name}»: имя не по шаблону srd-<версия>-statblock-headers.tsv")
        continue
    version = m.group(1)
    check_version(version, fixture)
    versions.append(version)

if failures:
    print(f"❌ Шапки статблоков разошлись с эталоном ({len(failures)}):")
    for f in failures[:40]:
        print(f"  — {f}")
    if len(failures) > 40:
        print(f"  … и ещё {len(failures) - 40}")
    sys.exit(1)

print(f"✅ Шапки статблоков ({', '.join(versions)}): сверены с PDF, разбор парсером и "
      f"RU-зеркало сходятся")
