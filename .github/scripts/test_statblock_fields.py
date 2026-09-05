#!/usr/bin/env python3
"""Сверка ВСЕХ полей статблоков с эталоном из официального PDF (issue #260).

Чем это отличается от `test_statblock_headers.py`. Тот держит одну строку блока —
«размер тип, мировоззрение», — и держит её строго. Всё остальное (КД, инициатива, хиты,
скорость, навыки, чувства, языки, ПО, иммунитеты, сопротивления, уязвимости, снаряжение)
до сих пор не сверялось ни с чем, хотя текст 5.2 приехал не из PDF, а из стороннего
перегона. Сверка нашла ~200 расхождений: у 30 существ инициатива была равна модификатору
Ловкости вместо значения из PDF, у 29 в ПО не было бонуса мастерства, у 27 стояло
обобщённое «XP 0 or 10» вместо конкретного значения, у 129 не было строки языков,
у пятерых в скорости висела заглушка `?`, плюс точечные ошибки в навыках и уязвимостях.

Эталон — `fixtures/srd-5.2-statblock-fields.json`, снятый с официального PDF 5.2.1
четырьмя независимыми выемками (marker, pymupdf4llm, docling и постраничная резка
`pdftotext` по колонкам — конвертеры теряют разные поля на двухколоночной вёрстке).
Пересобирается и сверяется `build_statblock_fields.py` — тот прогон воспроизводит все
3181 значение эталона из PDF и падает, если хоть одно перестало воспроизводиться.

Что проверяем:
  1) EN — каждое поле каждого блока против эталона, и лишних полей в тексте нет;
  2) состав эталона — обязательные ключи у всех блоков и общее число ячеек (иначе
     согласованное удаление поля из эталона и обоих текстов проходило бы молча);
  3) RU-зеркало — все числа обязаны совпадать с EN, у каждого поля EN обязана быть
     RU-строка, лишних RU-полей и выдуманных RU-блоков нет, шапка согласована по размеру;
  4) форма строк текста, которую сравнение значений намеренно не видит (хвостовая
     пунктуация скорости, метки полей);
  5) колонки указателей (ПО, КД, хиты) — против тех же блоков;
  6) ПО против официальной таблицы «ПО → опыт и бонус мастерства»;
  7) опечатки САМОГО PDF объявляются в эталоне (`cr_note`/`cr_repo`/`xp_note`), а не
     молча терпятся: «3 (700 XP)» в PDF против нашего «3 (XP 700)».

Запуск: python3 .github/scripts/test_statblock_fields.py
"""
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]
sys.path.insert(0, str(SCRIPTS))
from parsers.monster import SIZES_RU_TO_EN, _parse_type_line   # noqa: E402

FIXTURE = SCRIPTS / "fixtures/srd-5.2-statblock-fields.json"
VERSION = "srd-5.2"
# Провенанс эталона пришпилен ПАРОЙ «имя → значение»: иначе шапку можно исказить,
# оставив её непустой, и гейт этого не заметит.
PDF_URL = "https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf"
PDF_SHA256 = "8974902d109d6e63672d7c490bde9ccf052410503d9cfa768237154fbc5e3d87"
PDF_PAGES = 364
PDF_PAGE_SIZE = "594 x 783"
# Число ячеек эталона. Пришпилено, потому что усыхание эталона — самый тихий способ
# ослабить эту сверку: удалённое поле перестаёт проверяться, а гейт остаётся зелёным.
EXPECTED_CELLS = 3181

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
META_KEYS = ("cr_note", "cr_repo", "xp_note", "outside_chapters")
# Поля, которые есть у КАЖДОГО статблока. Отсутствие любого из них в эталоне — дыра
# эталона (ровно та, из-за которой «Mimic Languages None» и «Animated Object AC» молчали).
REQUIRED = ("header", "ac", "hp", "speed", "senses", "languages", "cr")
# Заголовки внутри статблока — не имена блоков.
SERVICE_HEADINGS = {"traits", "actions", "bonus actions", "reactions", "legendary actions",
                    "черты", "действия", "бонусные действия", "реакции",
                    "легендарные действия"}
failures = []


def canon(field: str, value: str) -> str:
    """Приведение перед сравнением — послабления этого гейта, все четыре.

    Гасятся ровно эти вещи, и каждая намеренно:
      * хвостовая точка/запятая/точка с запятой — конвертеры теряют и добавляют её
        произвольно, поэтому в эталоне её нет ни у одного из 336 значений скорости.
        Форму строки в тексте держит отдельная проверка `speed_punctuation` ниже —
        без неё потерянная точка (был такой дефект у Глиняного голема) проходила молча;
      * курсив вокруг названия («*Bless*» у Ракшаса): PDF-выемка разметки не несёт;
      * регистр у ЧУВСТВ — PDF пишет «Darkvision 120 ft.», мы «darkvision 120 ft.»;
        различие живёт в 252 строках чувств и не является данными;
      * «Thieves' Cant» → «Thieves' cant» в языках: та же стилистика в 7 строках.
    Всё остальное — включая регистр в остальных полях, порядок слов, скобки и числа —
    сверяется как есть. Это не косметика: «And Primordial» у Кракена и «Sleight of hand»
    у Шпиона были найдены ровно тем, что регистр сверяется.
    """
    value = re.sub(r"\s+", " ", value).strip(" .;,").replace("*", "")
    if field == "senses":
        return value.lower()
    if field == "languages":
        value = value.replace("Thieves' Cant", "Thieves' cant")
    return value


def numbers(value: str) -> list:
    """Числа значения; разряды пишутся по-разному («22,000» и «22 000»)."""
    return re.findall(r"[+-]?\d+", re.sub(r"(?<=\d)[,   ](?=\d\d\d\b)", "", value))


def read_blocks(path: Path, labels: dict, ru: bool) -> list:
    """[(EN-имя, {поле: значение})] из главы статблоков или из блока-врезки.

    Возвращаем СПИСОК, а не словарь: дубли имён ловятся при слиянии, поэтому терять их
    здесь нельзя. Шесть блоков живут вне глав монстров — в заклинаниях и магпредметах,
    оформленные цитатой (`> #### Giant Fly`). Их поля те же, поэтому снимаем префикс
    цитаты и читаем так же; в эталоне они помечены `outside_chapters`.
    """
    out, name, block = [], None, None

    def flush():
        if name and block:
            out.append((name, block))

    for line in path.read_text(encoding="utf-8").split("\n"):
        s = re.sub(r"^>\s?", "", line).strip()
        m = re.match(r"^#{2,4} (.+)$", s)
        if m:
            flush()
            title = m.group(1).strip()
            if title.lower() in SERVICE_HEADINGS:
                # «#### Actions» внутри блока — конец блока, а не новый блок.
                name, block = None, None
                continue
            if ru:
                # RU-заголовок несёт оригинал в скобках: «Аболет (Aboleth)».
                latin = re.findall(r"\(([^()]*[A-Za-z][^()]*)\)", title)
                name = re.sub(r"\s*\([^()]*\)$", "", latin[-1]).strip() if latin else None
            else:
                name = title
            block = {}
            continue
        if block is None:
            continue
        m = re.match(r"^\*([^*]+)\*$", s)
        if m and "header" not in block and re.match(
                r"^(?:Tiny|Small|Medium|Large|Huge|Gargantuan|"
                r"Крошечн|Маленьк|Средн|Больш|Огромн|Громадн)", m.group(1)):
            block["header"] = m.group(1).strip()
            continue
        for label, key in labels.items():
            # «Gear» и «CR» в наших файлах записаны без двоеточия, остальные поля — с ним;
            # форма одинакова в обоих языках и проверяется ниже (`label_style`).
            # В главах поля идут списком («- **Speed:** …»), во врезках — абзацами.
            m = re.match(rf"^(?:- )?\*\*{label}:?\*\*:?\s*(.+)$", s)
            if m and key not in block:
                block[key] = m.group(1).strip()
        m = re.match(r"^(?:- )?\*\*(?:CR|ПО):?\*\*:?\s*(.+)$", s)
        if m and "cr" not in block:
            block["cr"] = m.group(1).strip()
    flush()
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
        if name in dst:
            failures.append(f"{where}: статблок «{name}» встречается дважды")
            continue
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


# Официальная таблица «ПО → опыт»: она делает значение ПО проверяемым САМО ПО СЕБЕ, а не
# только против эталона, — согласованная подделка `cr` в эталоне и в тексте больше не проходит.
XP_BY_CR = {"0": (0, 10), "1/8": (25,), "1/4": (50,), "1/2": (100,)}
for _cr, _xp in enumerate((200, 450, 700, 1100, 1800, 2300, 2900, 3900, 5000, 5900, 7200,
                           8400, 10000, 11500, 13000, 15000, 18000, 20000, 22000, 25000,
                           33000, 41000, 50000, 62000, 75000, 90000, 105000, 120000,
                           135000, 155000), start=1):
    XP_BY_CR[str(_cr)] = (_xp,)


def pb_by_cr(cr: str) -> int:
    """Бонус мастерства по ПО: +2 до ПО 4, дальше +1 каждые четыре ступени."""
    value = 0 if "/" in cr else int(cr)
    return 2 + max(0, (value - 1) // 4)


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
for _key in ("license", "extraction", "regenerate"):
    if not _src.get(_key):
        failures.append(f"эталон: в шапке _source нет «{_key}» — эталон без провенанса")
if not (ROOT / str(_src.get("regenerate", ""))).exists():
    failures.append(f"эталон: _source.regenerate «{_src.get('regenerate')}» — файла нет")

# --- 0. Состав эталона ----------------------------------------------------------------
# Без этого согласованное удаление поля из эталона И из обоих текстов было зелёным:
# поле просто переставало существовать для гейта.
_cells = sum(len([k for k in f if k not in META_KEYS]) for f in expected.values())
if _cells != EXPECTED_CELLS:
    failures.append(f"эталон: {_cells} ячеек вместо {EXPECTED_CELLS} — эталон усох или вырос; "
                    f"если это осознанно, поправьте EXPECTED_CELLS")
for _name, _f in sorted(expected.items()):
    for _key in REQUIRED:
        if _key not in _f:
            failures.append(f"эталон «{_name}»: нет обязательного поля «{_key}»")
    if "initiative" not in _f and not _f.get("outside_chapters"):
        failures.append(f"эталон «{_name}»: нет поля «initiative» (его нет только у врезок)")

en_dir, ru_dir = ROOT / f"src/dnd/{VERSION}/en", ROOT / f"src/dnd/{VERSION}/ru"
en_blocks, ru_blocks = {}, {}
for chapter in ("12_MonstersA-Z.md", "13_Animals.md"):
    merge(en_blocks, read_blocks(en_dir / chapter, EN_LABELS, ru=False), f"en/{chapter}")
    merge(ru_blocks, read_blocks(ru_dir / chapter, RU_LABELS, ru=True), f"ru/{chapter}")
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
        pairs = read_blocks(path, labels, ru)
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
        # Эталон хранит строку PDF; если у PDF там опечатка, в тексте ждём исправленную
        # форму, объявленную в самом эталоне.
        if field == "cr" and "cr_repo" in fields:
            # cr_repo — не свободный белый список: это ровно cr с исправленным порядком
            # «700 XP» → «XP 700». Иначе им можно было бы узаконить любое значение.
            fixed = re.sub(r"\((\d[\d,]*)\s+XP", r"(XP \1", fields["cr"])
            if fields["cr_repo"] != fixed:
                failures.append(
                    f"эталон «{name}»: cr_repo «{fields['cr_repo']}» не выводится из PDF "
                    f"«{fields['cr']}» — ожидалось «{fixed}»")
            want = fields["cr_repo"]
        value = got.get(field)
        if value is None:
            failures.append(f"EN «{name}»: поле «{field}» потеряно (в PDF «{want}»)")
        elif canon(field, value) != canon(field, want):
            source = (f"PDF «{fields['cr']}», у нас ждём «{want}» ({fields['cr_note']})"
                      if field == "cr" and "cr_repo" in fields else f"PDF «{want}»")
            failures.append(f"EN «{name}» {field}: «{value}» ≠ {source}")
    # ПО против официальной таблицы: опыт и бонус мастерства выводятся из самого ПО.
    cr = fields.get("cr", "")
    lead = cr_value(cr)
    if lead in XP_BY_CR:
        xp = numbers(re.sub(r"^[\d/]+", "", cr.split(";")[0]))
        if xp and int(xp[0]) not in XP_BY_CR[lead] and "xp_note" not in fields:
            failures.append(f"эталон «{name}»: ПО {lead} — опыт {xp[0]}, а по таблице "
                            f"{XP_BY_CR[lead][0]}; если так в PDF, объявите xp_note")
        pb = re.search(r"PB \+(\d+)", cr)
        if pb and int(pb.group(1)) != pb_by_cr(lead):
            failures.append(f"эталон «{name}»: ПО {lead} — бонус мастерства +{pb.group(1)}, "
                            f"а по таблице +{pb_by_cr(lead)}")
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
        if field in META_KEYS or field in ("header", "cr"):
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
        if field == "header" or field not in got:
            continue
        if numbers(value) != numbers(got[field]):
            failures.append(f"RU «{name}» {field}: «{got[field]}» ≠ EN «{value}» (числа)")
    # Шапка врезок не сверяется гейтом шапок (тот читает только главы монстров и
    # указатели), поэтому размер сверяем здесь — по тем же словарям.
    if "header" in fields and "header" in got:
        ru_size = _parse_type_line(got["header"], "ru")["size"].split()
        en_size = _parse_type_line(fields["header"], "en")["size"].split()
        ru_first = SIZES_RU_TO_EN.get(ru_size[0].lower()) if ru_size else None
        if ru_first and en_size and ru_first.lower() != en_size[0].lower():
            failures.append(f"RU «{name}» шапка: размер «{ru_size[0]}» ({ru_first}) "
                            f"≠ EN «{en_size[0]}»")
for name in sorted(set(ru_blocks) - set(en_blocks)):
    failures.append(f"RU: статблок «{name}» есть в переводе, но не в EN")

# --- 3. Форма строк, которую сравнение значений намеренно не видит ---------------------
# canon() снимает хвостовую пунктуацию (в эталоне её нет ни у одной скорости), поэтому
# потерянная точка была бы невидима. Держим форму самим текстом: значение скорости
# кончается либо точкой сокращения «ft.»/«фт.», либо закрывающей скобкой «(hover)».
# Проверка на EN-половине: там значение кончается сокращением «ft.» или скобкой
# «(hover)». RU пишет слово «футов» без точки, поэтому форму русской строки держит
# сверка чисел с EN, а не пунктуация.
for chapter in ("12_MonstersA-Z.md", "13_Animals.md"):
    for i, line in enumerate((en_dir / chapter).read_text(encoding="utf-8").split("\n"), 1):
        m = re.match(r"^- \*\*Speed:\*\*\s*(.+)$", line.strip())
        if m and m.group(1).strip()[-1] not in ".)":
            failures.append(f"en/{chapter}:{i}: скорость «{m.group(1)}» "
                            f"не кончается точкой или скобкой")
# Метки полей: «Gear»/«CR» без двоеточия, остальные с ним — и одинаково в обоих языках.
for lang, folder, pairs in (
        ("en", en_dir, (("Gear", False), ("CR", False), ("Speed", True), ("Senses", True))),
        ("ru", ru_dir, (("Снаряжение", False), ("ПО", False), ("Скорость", True),
                        ("Чувства", True)))):
    for chapter in ("12_MonstersA-Z.md", "13_Animals.md"):
        text = (folder / chapter).read_text(encoding="utf-8")
        for label, colon in pairs:
            wrong = len(re.findall(rf"\*\*{label}\*\*" if colon else rf"\*\*{label}:\*\*", text))
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
