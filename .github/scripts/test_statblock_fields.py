#!/usr/bin/env python3
"""Сверка ВСЕХ полей статблоков с эталоном из официального PDF (issue #260).

Чем это отличается от `test_statblock_headers.py`. Тот держит одну строку блока —
«размер тип, мировоззрение», — и держит её строго. Всё остальное (КД, инициатива, хиты,
скорость, навыки, чувства, языки, ПО, иммунитеты, сопротивления, уязвимости, снаряжение)
до сих пор не сверялось ни с чем, хотя текст 5.2 приехал не из PDF, а из стороннего
перегона. Сверка нашла 72 расхождения: у 30 существ инициатива была равна модификатору
Ловкости вместо значения из PDF, у 28 в ПО не было бонуса мастерства, у 24 стояло
обобщённое «XP 0 or 10» вместо конкретного значения, у пятерых в скорости висела
заглушка `?`, плюс точечные ошибки в навыках, языках и уязвимостях.

Эталон — `fixtures/srd-5.2-statblock-fields.json`, снятый с официального PDF 5.2.1
четырьмя независимыми выемками (marker, pymupdf4llm, docling и постраничная резка
`pdftotext` по колонкам — конвертеры теряют разные поля на двухколоночной вёрстке).

Что проверяем:
  1) EN — каждое поле каждого блока против эталона;
  2) RU-зеркало — числовые поля (КД, инициатива, хиты, ПО) обязаны совпадать с EN:
     перевод там свой только у слов, а числа общие;
  3) колонки указателей (ПО, КД, хиты) — против тех же блоков;
  4) опечатки САМОГО PDF объявляются в эталоне (`cr_note`/`cr_repo`), а не молча
     терпятся: «3 (700 XP)» в PDF против нашего «3 (XP 700)».

Запуск: python3 .github/scripts/test_statblock_fields.py
"""
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]
FIXTURE = SCRIPTS / "fixtures/srd-5.2-statblock-fields.json"
VERSION = "srd-5.2"

# Во врезках метки короткие («**AC** 11»), в главах — полные («- **Armor Class:** 11»).
EN_LABELS = {"Gear": "gear", "Armor Class": "ac", "AC": "ac", "Hit Points": "hp",
             "HP": "hp", "Speed": "speed",
             "Initiative": "initiative", "Skills": "skills", "Senses": "senses",
             "Languages": "languages", "Immunities": "immunities",
             "Resistances": "resistances", "Vulnerabilities": "vulnerabilities"}
# RU читаем ПОЛНЫМ набором полей: числа сверяются со значением, остальные — по наличию.
# Без этого удаление 91 RU-строки «Языки: —» проходило зелёным весь CI, то есть RU-половина
# правок #260 не была защищена ничем.
RU_LABELS = {"Класс доспеха": "ac", "КД": "ac", "Хиты": "hp", "Скорость": "speed",
             "Инициатива": "initiative", "Навыки": "skills", "Снаряжение": "gear",
             "Чувства": "senses", "Языки": "languages", "Иммунитеты": "immunities",
             "Сопротивления": "resistances", "Уязвимости": "vulnerabilities"}
# Поля, которые в RU обязаны совпадать с EN ПОБУКВЕННО (это числа, а не проза).
RU_NUMERIC = ("ac", "hp", "initiative")
failures = []


def canon(field: str, value: str) -> str:
    """Приведение перед сравнением — ЕДИНСТВЕННОЕ послабление этого гейта.

    Гасятся ровно две вещи, и обе намеренно:
      * регистр (кроме шапки) — PDF пишет «Darkvision 120 ft.», мы «darkvision 120 ft.»;
        различие живёт в 252 строках чувств и не является данными;
      * хвостовая точка/запятая — конвертеры её теряют и добавляют произвольно.
    Всё остальное — включая порядок слов, скобки и числа — сверяется как есть.
    """
    value = re.sub(r"\s+", " ", value).strip(" .;,")
    value = value.replace("*", "").replace("((", "(").replace("))", ")")
    return value if field == "header" else value.lower()


def read_blocks(path: Path, labels: dict, ru: bool) -> dict:
    """{EN-имя: {поле: значение}} из главы статблоков или из блока-врезки.

    Шесть блоков живут вне глав монстров — в заклинаниях и магпредметах, оформленные
    цитатой (`> #### Giant Fly`). Их поля те же, поэтому снимаем префикс цитаты и
    читаем так же; в эталоне они помечены `outside_chapters`.
    """
    out, name, block = {}, None, None
    for line in path.read_text(encoding="utf-8").split("\n"):
        s = re.sub(r"^>\s?", "", line).strip()
        m = re.match(r"^#{2,4} (.+)$", s)
        if m:
            if name and block:
                if name in out:
                    failures.append(f"{path.name}: статблок «{name}» встречается дважды")
                out.setdefault(name, block)
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
            continue
        m = re.match(r"^\*((?:Tiny|Small|Medium|Large|Huge|Gargantuan|Huge or Smaller)[^*]*)\*$", s)
        if m and "header" not in block:
            block["header"] = s.strip("*")
            continue
        for label, key in labels.items():
            # «Gear» в наших файлах записан без двоеточия — как и «CR»; остальные поля
            # с двоеточием. Формат пре-существующий и одинаковый в обоих языках.
            # В главах поля идут списком («- **Speed:** …»), во врезках — абзацами
            # («**Speed** …»), а «Gear» и «CR» пишутся без двоеточия.
            m = re.match(rf"^(?:- )?\*\*{label}:?\*\*:?\s*(.+)$", s)
            if m and key not in block:
                block[key] = m.group(1).strip()
        m = re.match(r"^(?:- )?\*\*(?:CR|ПО):?\*\*:?\s*(.+)$", s)
        if m and "cr" not in block:
            block["cr"] = m.group(1).strip()
    if name and block:
        out.setdefault(name, block)
    return out


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


_fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
# Эталон — дословная выемка из PDF, поэтому у него есть шапка с источником и лицензией;
# сами блоки лежат под ключом «blocks», чтобы служебные поля не путались с именами существ.
expected = _fixture["blocks"]
for _key in ("pdf", "sha256", "license", "extraction", "regenerate"):
    if not _fixture.get("_source", {}).get(_key):
        failures.append(f"эталон: в шапке _source нет «{_key}» — эталон без провенанса")
en_dir, ru_dir = ROOT / f"src/dnd/{VERSION}/en", ROOT / f"src/dnd/{VERSION}/ru"
en_blocks, ru_blocks = {}, {}
for chapter in ("12_MonstersA-Z.md", "13_Animals.md"):
    en_blocks.update(read_blocks(en_dir / chapter, EN_LABELS, ru=False))
    ru_blocks.update(read_blocks(ru_dir / chapter, RU_LABELS, ru=True))
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
    for src, dst, labels, ru in ((en_dir, en_blocks, EN_LABELS, False),
                                 (ru_dir, ru_blocks, RU_LABELS, True)):
        path = src / chapter
        if path.exists():
            for key, value in read_blocks(path, labels, ru).items():
                if key in OUTSIDE:
                    dst.setdefault(key, value)

# --- 1. EN против эталона PDF ---------------------------------------------------------
for name, fields in sorted(expected.items()):
    got = en_blocks.get(name)
    if got is None:
        failures.append(f"EN: статблок «{name}» из эталона не найден")
        continue
    # Лишнее поле в тексте — тоже расхождение: эталон описывает блок целиком.
    for field in sorted(set(got) - set(fields) - {"header"}):
        failures.append(f"EN «{name}»: поле «{field}» = «{got[field]}» есть в тексте, но не в PDF")
    for field, want in fields.items():
        if field in ("cr_note", "cr_repo", "abilities", "outside_chapters"):
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
for name in sorted(set(en_blocks) - set(expected)):
    failures.append(f"EN: статблок «{name}» есть в тексте, но не в эталоне PDF")

# --- 2. RU-зеркало: числа общие -------------------------------------------------------
for name, fields in sorted(en_blocks.items()):
    got = ru_blocks.get(name)
    if got is None:
        failures.append(f"RU: статблок «{name}» не найден")
        continue
    # Присутствие: у каждого поля эталона обязана быть RU-строка. Перевод свой, но
    # СТРОКА должна быть — иначе поле молча исчезает только из русской половины.
    for field in expected.get(name, {}):
        if field in ("cr_note", "cr_repo", "abilities", "outside_chapters", "header", "cr"):
            continue
        if field in fields and field not in got:
            failures.append(f"RU «{name}»: нет строки поля «{field}» (в EN «{fields[field]}»)")
    if "cr" in fields and "cr" not in got:
        failures.append(f"RU «{name}»: нет строки ПО (в EN «{fields['cr']}»)")
    for field in RU_NUMERIC:
        if field not in fields or field not in got:
            continue
        # Сверяем ЧИСЛА и знак модификатора, но не пунктуацию перевода: у врезок
        # значение бывает фразой («50 + 10 за каждый уровень заклинания выше 5-го»).
        a = re.findall(r"[+-]?\d+", fields[field])
        b = re.findall(r"[+-]?\d+", got[field])
        if a != b:
            failures.append(f"RU «{name}» {field}: «{got[field]}» ≠ EN «{fields[field]}»")
    # ПО сверяем числом; у врезок оно бывает словом («None» / «Нет») — там сверять нечего.
    if ("cr" in fields and "cr" in got and re.match(r"^[\d/]", fields["cr"].strip())
            and cr_value(fields["cr"]) != cr_value(got["cr"])):
        failures.append(f"RU «{name}» ПО: «{got['cr']}» ≠ EN «{fields['cr']}»")

# --- 3. Колонки указателей: ПО, КД, хиты ----------------------------------------------
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
                continue           # ширину строки сверяет test_statblock_headers.py
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

print(f"✅ Поля статблоков {VERSION}: {len(expected)} блоков сверены с PDF, "
      f"RU-зеркало и указатели сходятся")
