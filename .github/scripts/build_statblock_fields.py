#!/usr/bin/env python3
"""Сборка и сверка эталона полей статблоков из официального PDF (issue #260).

Версия задаётся аргументом: `srd-5.2` (по умолчанию) или `srd-5.1`. Вёрстка и состав полей
у них разные, поэтому разбор свой у каждой, а сверка выемки с эталоном — общая.

Что скрипт делает и чего НЕ делает. Он снимает поля статблоков из четырёх выемок
официального PDF, сверяет их с текстом репозитория и — ключевое — с самой фикстурой
`fixtures/srd-5.2-statblock-fields.json`, печатая поячеечный отчёт: сколько значений
эталона выемки воспроизводят и какие расходятся. Фикстуру он НЕ перезаписывает: эталон
правится осознанно, а не автоперезаписью с выхлопа конвертера. Сегодня выемки
воспроизводят КАЖДОЕ значение обоих эталонов (9229 у 5.2 и 6635 у 5.1), поэтому любой
ненулевой остаток — расхождение, и код
возврата ненулевой: «эталон воспроизводится» — утверждение, которое можно прогнать.

Как пользоваться:

    # 1. Скачать PDF и прогнать конвертеры (скилл /convert-pdf):
    curl -sL -o /tmp/srd-5.2.1.pdf \
      https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf
    shasum -a 256 /tmp/srd-5.2.1.pdf   # обязан совпасть с _source.sha256 фикстуры
    python3 .claude/skills/convert-pdf/convert_pdf.py /tmp/srd-5.2.1.pdf dnd_srd-5.2.1
    python3 .claude/skills/cleanup-artifacts/layout_recovery.py \
      /tmp/dnd_srd-5.2.1_marker.md /tmp/dnd_srd-5.2.1_recovered.md

    # 2. Четвёртая выемка — сам PDF, разрезанный по колонкам. Страницы чередуются
    #    ПОПАРНО (левая колонка страницы N, затем правая колонка страницы N) — просто
    #    склеить файлы нельзя: тогда правые колонки уезжают на 350 страниц вперёд и
    #    поля статблока разрываются. Чередование делает сам скрипт:
    pdftotext -layout -x 0   -W 297 -H 783 /tmp/srd-5.2.1.pdf /tmp/col_l.txt
    pdftotext -layout -x 297 -W 297 -H 783 /tmp/srd-5.2.1.pdf /tmp/col_r.txt
    #    (-H 783 обязателен: без него pdftotext отдаёт по одному переводу страницы на
    #     страницу — 364 байта на файл, проверено на этом PDF)

    # 3. Сверить выемки с фикстурой и с текстом:
    python3 .github/scripts/build_statblock_fields.py --report

    # Для 5.1 нужен свой PDF и своя резка колонок (страница 612 x 792):
    curl -sL -o /tmp/srd-5.1.pdf https://media.wizards.com/2023/downloads/dnd/SRD_CC_v5.1.pdf
    pdftotext -layout -x 0   -W 306 -H 792 /tmp/srd-5.1.pdf /tmp/51_col_l.txt
    pdftotext -layout -x 306 -W 306 -H 792 /tmp/srd-5.1.pdf /tmp/51_col_r.txt
    python3 .github/scripts/build_statblock_fields.py srd-5.1 --report

Пути берутся из переменных окружения: ВХОДЫ — `SRD_MARKER`, `SRD_PYMUPDF`, `SRD_DOCLING`,
`SRD_COL_L`, `SRD_COL_R`; ВЫХОД — `SRD_COLS` (склеенная колонная выемка, файл по этому
пути перезаписывается; по умолчанию `/tmp/srd-5.2.1_cols.txt`). Значения по умолчанию те,
что оставляет рецепт выше.
Отсутствие файла — внятная ошибка, а не стектрейс. Скрипт не гоняется в CI: ему нужен
сам PDF и три конвертера, которых на раннере нет, — это второй эшелон для правки эталона.

Почему четыре выемки. Конвертеры теряют РАЗНЫЕ поля на двухколоночной вёрстке: marker
склеивает часть заголовков, pymupdf4llm и docling уносят AC/HP за таблицу характеристик.
Ни один из них в одиночку не даёт всех значений; мерило — не число выемок, а нулевой
остаток непрочитанных полей.
"""

import json
import os
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from statblock_meta import EN_LABELS_51, META_KEYS, STRIP_TAIL   # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).resolve().parent / "fixtures/srd-5.2-statblock-fields.json"
SIZE = r"(?:Tiny|Small|Medium|Large|Huge|Gargantuan)"
# Главы репозитория со статблоками: две главы монстров и две главы с блоками-врезками.
CHAPTERS = ("12_MonstersA-Z.md", "13_Animals.md", "07_Spells.md", "10_MagicItems.md")
LABELS = ["AC", "Initiative", "HP", "Speed", "Skills", "Senses", "Languages", "CR",
          "Immunities", "Resistances", "Vulnerabilities", "Gear"]
KEY_OF = {"AC": "ac", "Initiative": "initiative", "HP": "hp", "Speed": "speed",
          "Skills": "skills", "Senses": "senses", "Languages": "languages",
          "CR": "cr", "Immunities": "immunities", "Resistances": "resistances",
          "Vulnerabilities": "vulnerabilities", "Gear": "gear"}


def source(env: str, default: str) -> Path:
    path = Path(os.environ.get(env, default))
    if not path.exists():
        sys.exit(f"нет выемки {path} (переменная {env}) — прогоните шаги 1–2 из докстроки")
    return path


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"<!--.*?-->|```+", " ", s)          # артефакты конвертеров
    s = s.replace("−", "-").replace("–", "-").replace("—", "-").replace("’", "'")
    return " ".join(s.split()).strip(" .;,")


def clean_heading(line: str) -> str:
    line = re.sub(r"<[^>]+>", "", line)
    return re.sub(r"[#*_]+", " ", line).strip()


def pdf_blocks(path: "Path", bare: bool = False) -> dict:
    """{имя: {поле: значение}} из перегона PDF (по умолчанию marker).

    bare=True — для docling и для колонной выемки: они пишут метки полей без разметки
    («AC 13 HP 36 …»), поэтому перед разбором их приходится обернуть самим.
    """
    lines = unicodedata.normalize("NFKC", path.read_text(encoding="utf-8")).split("\n")
    out, name = {}, None
    for i, line in enumerate(lines):
        s = line.strip()
        if re.match(r"^#{1,6}\s", s):
            name = clean_heading(s)
            continue
        # У marker шапка стоит отдельной строкой, у pymupdf — вместе с первыми полями.
        pat = rf"^#{{0,6}}\s*[*_]?({SIZE}[^*_|]*?)[*_]?\s*$" if bare else rf"^#{{0,6}}\s*[*_]({SIZE}[^*_]*)[*_]\s*(.*)$"
        m = re.match(pat, s)
        if not m:
            continue
        if bare:
            # В голом тексте заголовков нет: имя — ближайшая непустая строка выше.
            # Считаем его ЗАНОВО для каждого блока: имя от предыдущего (пропущенного)
            # блока иначе прилипает к следующему и уносит его поля под чужим ключом.
            name = None
            for back in range(i - 1, max(i - 4, -1), -1):
                cand = clean_heading(lines[back])
                if cand and not re.search(r"\d", cand) and len(cand) < 60:
                    name = cand
                    break
        if not name or name in out:
            continue
        block = {"header": norm(m.group(1))}
        head_tail = "" if bare else m.group(2).strip()
        # Тело блока: до следующего заголовка уровня 1-3 или до «#### Traits/Actions».
        body = [head_tail] if head_tail else []
        for j in range(i + 1, len(lines)):
            t = lines[j].strip()
            if re.match(r"^#{1,3}\s", t) or re.match(r"^#{4,6}\s*(Traits|Actions|Bonus Actions|Reactions|Legendary)", t):
                break
            if t.startswith("|"):
                continue
            # «#### Vulnerabilities Fire» — то же поле, оформленное заголовком.
            mm = re.match(r"^#{3,6}\s*(Immunities|Resistances|Vulnerabilities|Gear)\s*(.*)$", t)
            if mm:
                body.append(f"**{mm.group(1)}** {mm.group(2)}")
                continue
            if t:
                body.append(t)
        # Поля идут подряд, длинные переносятся: склеиваем и режем по меткам.
        text = re.sub(r"</?u>|</?mark>", " ", " ".join(body))
        # Колонтитул «357 System Reference Document 5.2.1» приклеивается к последнему
        # полю страницы — режем его до разбора, иначе он уезжает в значение.
        text = re.sub(r"\s*\**\d{1,3}\**\s*System Reference Document [\d.]+\s*", " ", text)
        text = re.sub(r"\s*System Reference Document [\d.]+\s*\**\d{1,3}\**\s*", " ", text)
        if bare:
            text = re.sub(rf"(?<![*\w])({'|'.join(LABELS)})(?=\s)", r"**\1**", text)
        parts = re.split(rf"\*\*({'|'.join(LABELS)})\*\*", text)
        # Хвост поля обрезаем на первом признаке следующей секции: строка характеристик
        # без разметки таблицы («MOD SAVE …»), заголовок или начало черты («*Bite.*»).
        cut = re.compile(r"\s(?:<u>|MOD\s+SAVE|#{3,6}\s|"
                         r"\*[A-Z][^*]{0,80}?(?:\.\*|Attack Roll:|Saving Throw:))")
        for k in range(1, len(parts) - 1, 2):
            key = KEY_OF[parts[k]]
            if key in block:
                continue
            value = parts[k + 1]
            if key == "cr":
                # «10 (XP 5,900, or 7,200 in lair; PB +4)» — значение кончается скобкой.
                m2 = re.match(r"^\s*([\d/]+\s*\([^)]*\))", value)
                value = m2.group(1) if m2 else value
            m2 = cut.search(value)
            if m2:
                value = value[:m2.start()]
            if key == "speed":
                # Инициатива без метки, приклеенная конвертером: «50 ft., Climb 40 ft. +1 (11)».
                value = re.sub(r"\s[+-]\d+\s*\(\d+\).*$", "", value)
            block[key] = norm(value)
        out[name] = block
        if bare:
            name = None
    return out


duplicates = []


ABIL = ("Str", "Dex", "Con", "Int", "Wis", "Cha")
# Строка характеристик колонной выемки: «Str 18 +4 +4   Dex 10 +0 +3   Con 18 +4 +4».
# Знак минуса в PDF типографский (U+2212), пробел между меткой и значением бывает съеден
# («Con22»), а у Молодого белого дракона в самом PDF потерян минус спасброска Интеллекта.
ABIL_ROW = re.compile(r"(Str|Dex|Con|Int|Wis|Cha)\s*(\d+)\s+([+\-−]?\d+)\s+([+\-−]?\d+)")


def pdf_abilities(path: Path) -> dict:
    """{имя: {характеристика: [значение, модификатор, спасбросок]}} из колонной выемки.

    Таблица характеристик — единственное поле блока, которое конвертеры дают только в
    колонной выемке: в двухколоночной вёрстке она стоит между полями и разрывается.
    """
    lines = unicodedata.normalize("NFKC", path.read_text(encoding="utf-8")).replace("’", "'")
    lines = lines.split("\n")
    out = {}
    for i, line in enumerate(lines):
        if not re.match(rf"^\s*{SIZE}\b", line.strip()):
            continue
        name = None
        for back in range(i - 1, max(i - 4, -1), -1):
            cand = lines[back].strip()
            if cand and not re.search(r"\d", cand) and len(cand) < 60:
                name = cand
                break
        if not name or name in out:
            continue
        vals = {}
        for j in range(i + 1, min(i + 40, len(lines))):
            if re.match(r"^\s*(Str|Dex|Con|Int|Wis|Cha)\s*\d", lines[j]):
                for m in ABIL_ROW.finditer(lines[j]):
                    vals.setdefault(m.group(1).lower(),
                                    [m.group(2), m.group(3).replace("−", "-"),
                                     m.group(4).replace("−", "-")])
            if len(vals) == 6:
                break
        if len(vals) == 6:
            out[name] = vals
    return out


def repo_blocks() -> dict:
    """Поля статблоков из текста репозитория — все четыре главы, включая врезки.

    Врезки (`> #### Giant Fly` в заклинаниях и магпредметах) оформлены цитатой и метками
    без двоеточия — без них выборка была бы на шесть блоков короче эталона.
    """
    out = {}
    label_re = "|".join(["Armor Class", "AC", "Hit Points", "HP", "Speed", "Initiative",
                         "Skills", "Senses", "Languages", "Immunities", "Resistances",
                         "Vulnerabilities", "Gear"])
    key_of = dict(KEY_OF, **{"Armor Class": "ac", "Hit Points": "hp"})
    for chapter in CHAPTERS:
        path = ROOT / "src/dnd/srd-5.2/en" / chapter
        name, block = None, None
        for line in path.read_text(encoding="utf-8").split("\n") + ["### END"]:
            s = re.sub(r"^>\s?", "", line).strip()
            m = re.match(r"^#{2,4} (.+)$", s)
            if m:
                if name and block:
                    if name in out:
                        duplicates.append(f"{chapter}: статблок «{name}» встречается дважды")
                    out.setdefault(name, block)
                name, block = m.group(1).strip(), {}
                continue
            if block is None:
                continue
            m = re.match(rf"^\*({SIZE}[^*]*)\*$", s)
            if m and "header" not in block:
                block["header"] = norm(m.group(1))
                continue
            m = re.match(rf"^(?:- )?\*\*({label_re}):?\*\*\s*(.+)$", s)
            if m and key_of[m.group(1)] not in block:
                block[key_of[m.group(1)]] = norm(m.group(2))
                continue
            m = re.match(r"^(?:- )?\*\*CR:?\*\*\s*(.+)$", s)
            if m and "cr" not in block:
                block["cr"] = norm(m.group(1))
                continue
            # Таблица характеристик: в главах она транспонирована (строки SCORE/MOD/SAVE),
            # во врезках обычная (строка на характеристику).
            if s.startswith("|"):
                cells = [c.strip() for c in s.strip("|").split("|")]
                if cells and cells[0].upper() in ("SCORE", "MOD", "SAVE") and len(cells) > 6:
                    block.setdefault("_rows", {})[cells[0].upper()] = cells[1:7]
                elif cells and cells[0].capitalize() in ABIL and len(cells) > 3:
                    block.setdefault("abilities", {})[cells[0].lower()] = cells[1:4]
        if name and block:
            out.setdefault(name, block)
    for block in out.values():
        rows = block.pop("_rows", None)
        if rows and set(rows) == {"SCORE", "MOD", "SAVE"}:
            block["abilities"] = {a.lower(): [rows["SCORE"][i], rows["MOD"][i], rows["SAVE"][i]]
                                  for i, a in enumerate(ABIL)}
    return out


def interleave_columns() -> Path:
    """Склейка колонной выемки: левая и правая колонки чередуются ПОСТРАНИЧНО.

    `pdftotext` пишет страницы через перевод формата (\f), поэтому просто сложить два
    файла нельзя — правые колонки уедут на весь документ вперёд и разорвут статблоки.
    """
    left = source("SRD_COL_L", "/tmp/col_l.txt").read_text(encoding="utf-8").split("\f")
    right = source("SRD_COL_R", "/tmp/col_r.txt").read_text(encoding="utf-8").split("\f")
    if len(left) != len(right):
        sys.exit(f"колонки не сошлись: слева {len(left)} страниц, справа {len(right)} — "
                 f"выемки сделаны разными командами или из разных PDF")
    if len(left) < 2:
        sys.exit("в левой колонне одна страница — похоже, забыт -H 783 у pdftotext")
    pages = [page for pair in zip(left, right) for page in pair]
    out = guarded_out("SRD_COLS", "/tmp/srd-5.2.1_cols.txt")
    out.write_text("\n".join(pages), encoding="utf-8")
    print(f"склеенная колонная выемка → {out} ({len(left)} страниц)")
    return out


def guarded_out(env: str, default: str) -> Path:
    """Путь для склеенной выемки — с отказом затирать ЧУЖОЙ файл.

    Проверять «похоже ли содержимое на выемку» бесполезно: маркер SRD стоит и в колонных
    половинах, и в выхлопе конвертеров — то есть ровно в тех файлах, которые жальче всего
    потерять. Поэтому правило простое: существующий файл не перезаписывается без --force,
    а каталог по пути — это ошибка с сообщением, а не трейсбек.
    """
    out = Path(os.environ.get(env, default))
    if out.is_dir():
        sys.exit(f"{env}={out} — это каталог, а не файл")
    if out.exists() and "--force" not in sys.argv:
        sys.exit(f"{out} уже существует — перезапись отменена. Уберите файл, задайте "
                 f"другой путь в {env} или прогоните с --force")
    return out


def extractions() -> dict:
    """Слияние четырёх выемок: каждая добирает то, что потеряли предыдущие."""
    marker = pdf_blocks(source("SRD_MARKER", "/tmp/dnd_srd-5.2.1_recovered.md"))
    alt = pdf_blocks(source("SRD_PYMUPDF", "/tmp/dnd_srd-5.2.1_pymupdf.md"))
    docling = pdf_blocks(source("SRD_DOCLING", "/tmp/dnd_srd-5.2.1_docling.md"), bare=True)
    cols_file = interleave_columns()
    cols = pdf_blocks(cols_file, bare=True)
    abilities = pdf_abilities(cols_file)
    merged = dict(marker)
    for extra in (alt, docling, cols):
        for name, block in extra.items():
            if name not in merged:
                merged[name] = dict(block)
                continue
            for field, value in block.items():
                merged[name].setdefault(field, value)
    for name, table in abilities.items():
        if name in merged:
            merged[name].setdefault("abilities", table)
    return merged



# --- SRD 5.1: своя вёрстка, свой набор полей ------------------------------------------
# 5.1 свёрстана в две колонки с табуляцией между словами и мягкими переносами внутри слов,
# а поля у неё другие: спасброски отдельной строкой, иммунитеты разделены на урон и
# состояния, инициативы и снаряжения нет. Поэтому разбор отдельный — общей у версий
# остаётся сверка выемки с эталоном (см. main).
# Метки полей 5.1 — из общего модуля, чтобы сборщик и гейт не разъехались молча (метка
# ПО живёт в гейте отдельным параметром, поэтому здесь она добавляется руками).
# «Challenge» и «Damage Resistance» (единственное число, у одного Архимага) — формы
# ИСТОЧНИКА: в гейте первая живёт отдельным параметром, второй в нашем корпусе нет вовсе.
LAB_51 = list(EN_LABELS_51) + ["Challenge", "Damage Resistance"]
KEY_51 = {l: l.lower().replace(" ", "_") for l in LAB_51}
def blocks_51(lines):
    heads=[i for i,l in enumerate(lines) if re.match(rf"^{SIZE} [a-z]",l)]
    out={}
    for n,i in enumerate(heads):
        name=None
        for b in range(i-1,max(i-4,-1),-1):
            c=lines[b]
            if c and not re.search(r"\d",c) and 0<len(c)<50 and not c.startswith(("Monsters","System")):
                name=c.rstrip(","); break
        if not name: continue
        end=heads[n+1] if n+1<len(heads) else len(lines)
        head=lines[i]
        if "," not in head and i+1<len(lines) and lines[i+1] and lines[i+1][0].islower():
            head=head+" "+lines[i+1]
        elif i+1<len(lines) and re.match(r"^(alignment|evil|good|neutral)\b", lines[i+1]):
            # Мировоззрение перенеслось на следующую строку («any non-lawful» + «alignment»).
            head=head+" "+lines[i+1]
        blk={"header":head}
        last=None
        for j in range(i+1,end):
            s=lines[j]
            m=re.match(rf"^({'|'.join(LAB_51)}) (.+)$",s)
            if m:
                last=KEY_51[m.group(1)]
                if last not in blk: blk[last]=m.group(2)
                continue
            ma=re.fullmatch(r"((?:\d+ \([+-]?\d+\) ?){6})",s)
            if ma and "abilities" not in blk:
                blk["abilities"]=[list(x) for x in re.findall(r"(\d+) \(([+-]?\d+)\)",s)]
                last=None
                continue
            # Продолжение значения: PDF переносит длинные списки на следующую строку.
            # Признак конца — пустая строка, начало черты («Amphibious.») или новая метка.
            if last and s and not re.match(r"^[A-Z][^.]{0,40}\.( |$)", s) and not s.startswith(("STR","System","Monsters")):
                # Метка может стоять ПОСРЕДИ строки переноса («… silvered weapons Senses
                # passive Perception 12»): режем строку по ней, иначе поле съедает соседа.
                inner=re.search(rf" ({'|'.join(LAB_51)}|Damage Resistance) ",s)
                if inner:
                    blk[last]=blk[last]+" "+s[:inner.start()]
                    tail=s[inner.start()+1:]
                    m2=re.match(rf"^({'|'.join(LAB_51)}|Damage Resistance) (.+)$",tail)
                    if m2:
                        last=KEY_51.get(m2.group(1),"damage_resistance")
                        if last not in blk: blk[last]=m2.group(2)
                    continue
                blk[last]=blk[last]+" "+s
            else:
                last=None
        out.setdefault(name,blk)
    return out


def interleave_columns_51() -> Path:
    """Колонная выемка 5.1: страница 612 x 792, колонки по 306 пунктов."""
    left = source("SRD51_COL_L", "/tmp/51_col_l.txt").read_text(encoding="utf-8")
    right = source("SRD51_COL_R", "/tmp/51_col_r.txt").read_text(encoding="utf-8")
    def prep(text):
        text = unicodedata.normalize("NFKC", text)
        # PDF 5.1 режет слова мягким переносом (U+00AD) и типографским дефисом — из-за них
        # не сходятся даже имена статблоков («Saber-\xad‐Toothed Tiger»).
        text = (text.replace("−", "-").replace("’", "'").replace("\xad", "")
                .replace("‐", "-").replace("–", "-"))
        text = re.sub(r"-{2,}", "-", text)
        text = re.sub(r"\t[ \t]*\n[ \t]*", " ", text)
        return [re.sub(r"[ \t]+", " ", p) for p in text.split("\f")]
    left, right = prep(left), prep(right)
    if len(left) != len(right):
        sys.exit(f"колонки 5.1 не сошлись: слева {len(left)}, справа {len(right)}")
    out = guarded_out("SRD51_COLS", "/tmp/51_cols.txt")
    out.write_text("\n".join(p for pair in zip(left, right) for p in pair), encoding="utf-8")
    print(f"склеенная колонная выемка 5.1 → {out} ({len(left)} страниц)")
    return out


ABIL_51 = ("str", "dex", "con", "int", "wis", "cha")
KEYMAP_51 = {"armor_class": "ac", "hit_points": "hp", "speed": "speed", "senses": "senses",
             "languages": "languages", "skills": "skills", "challenge": "cr",
             "abilities": "abilities", "saving_throws": "saves", "header": "header",
             "damage_immunities": "damage_immunities",
             "condition_immunities": "condition_immunities",
             "damage_resistances": "damage_resistances",
             "damage_vulnerabilities": "damage_vulnerabilities",
             "damage_resistance": "damage_resistances"}


def extractions_51() -> dict:
    """Блоки 5.1 из колонной выемки, ключи полей — как в эталоне."""
    lines = [line.strip() for line in
             interleave_columns_51().read_text(encoding="utf-8").split("\n")]
    out = {}
    for name, block in blocks_51(lines).items():
        converted = {}
        for key, value in block.items():
            mapped = KEYMAP_51.get(key)
            if not mapped:
                continue
            converted[mapped] = ({a: [c[0], c[1]] for a, c in zip(ABIL_51, value)}
                                 if mapped == "abilities" else norm(value))
        out[name] = converted
    return out


def repo_blocks_51() -> list:
    """ИМЕНА статблоков 5.1 из текста репозитория — глава монстров и врезки магпредметов.

    Поля здесь разбираются только затем, чтобы отличить статблок от прочих заголовков
    (у статблока есть таблица характеристик). Сверку значений делает гейт: он сравнивает
    текст с эталоном, а этот скрипт — эталон с выемкой из PDF, и вместе они замкнуты.
    """
    label_re = "|".join(sorted(KEY_51, key=len, reverse=True))
    out = {}
    for chapter in ("15_MonstersA-Z.md", "13_MagicItems.md"):
        path = ROOT / "src/dnd/srd-5.1/en" / chapter
        name, block = None, None
        for line in path.read_text(encoding="utf-8").split("\n") + ["### END"]:
            s = line.strip()
            m = re.match(r"^#{2,4} (.+)$", s)
            if m:
                if name and block:
                    if name in out:
                        duplicates.append(f"{chapter}: статблок «{name}» встречается дважды")
                    out.setdefault(name, block)
                name, block = m.group(1).strip(), {}
                continue
            if block is None:
                continue
            m = re.match(rf"^\*({SIZE}[^*]*)\*$", s)
            if m and "header" not in block:
                block["header"] = norm(m.group(1))
                continue
            m = re.match(rf"^(?:- )?\*\*({label_re}):?\*\*\s*(.+)$", s)
            if m:
                block.setdefault(KEYMAP_51[KEY_51[m.group(1)]], norm(m.group(2)))
                continue
            if s.startswith("|") and re.search(r"\d+ \([+-]?\d+\)", s):
                cells = [c.strip() for c in s.strip("|").split("|")]
                pairs = [re.match(r"(\d+) \(([+-]?\d+)\)", c) for c in cells[:6]]
                if len(cells) >= 6 and all(pairs):
                    block["abilities"] = {a: [p.group(1), p.group(2)]
                                          for a, p in zip(ABIL_51, pairs)}
    return sorted(k for k, v in out.items() if "abilities" in v)


if __name__ == "__main__":
    version = "srd-5.1" if "srd-5.1" in sys.argv else "srd-5.2"
    fixture_path = (FIXTURE if version == "srd-5.2"
                    else Path(__file__).resolve().parent
                    / "fixtures/srd-5.1-statblock-fields.json")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))["blocks"]
    pdf, repo = ((extractions(), repo_blocks()) if version == "srd-5.2"
                 else (extractions_51(), repo_blocks_51()))
    # Имя в PDF 5.1 идёт без таксономического хвоста («Adult Black Dragon»), а в тексте и
    # в эталоне — с ним («Adult Black Dragon (Chromatic)»): сводим по имени без хвоста.
    by_stripped = {STRIP_TAIL.sub("", n).strip(): n for n in fixture}
    for source_map in (pdf, repo):
        # Источники разной формы: выемка — словарь «имя → поля», текст репозитория 5.1 —
        # список имён. Ветка обязана работать с обоими: хвост несут 77 из 319 имён 5.1,
        # то есть падал бы ровно тот класс, ради которого она написана.
        for name in [n for n in source_map if n not in fixture]:
            target = by_stripped.get(STRIP_TAIL.sub("", name).strip())
            if not target or target in source_map:
                continue
            if isinstance(source_map, dict):
                source_map[target] = source_map.pop(name)
            else:
                source_map[source_map.index(name)] = target
    print(f"{version}: блоков — выемки {len(pdf)}, репозиторий {len(repo)}, "
          f"эталон {len(fixture)}, "
          f"общих с эталоном {len(set(pdf) & set(fixture))}")

    # Главное: сверка выемок с САМОЙ фикстурой — иначе «способ пересборки» ничего не значит.
    same, differ, unreachable = 0, [], []
    for name, fields in sorted(fixture.items()):
        for field, want in fields.items():
            if field in META_KEYS:
                continue
            got = pdf.get(name, {}).get(field)
            if field == "abilities":
                # У характеристик 18 ячеек на блок — считаем их поимённо, иначе одна
                # правка внутри таблицы теряется в одном общем «совпало».
                for abil in ABIL:
                    key = abil.lower()
                    want_cells = (want or {}).get(key)
                    got_cells = (got or {}).get(key)
                    parts = ("значение", "модификатор", "спасбросок")[:len(want_cells or ())]
                    for idx, part in enumerate(parts):
                        w = want_cells[idx] if want_cells else None
                        g = got_cells[idx] if got_cells else None
                        if w is None:
                            continue
                        if g is None:
                            unreachable.append(f"{name}.{key}.{part}")
                        elif norm(g) == norm(w):
                            same += 1
                        else:
                            differ.append(f"{name}.{key}.{part}: выемка «{g}» ≠ эталон «{w}»")
                continue
            if got is None:
                unreachable.append(f"{name}.{field}")
            elif norm(got) == norm(want):
                same += 1
            else:
                differ.append(f"{name}.{field}: выемка «{got}» ≠ эталон «{want}»")
    total = same + len(differ) + len(unreachable)
    print(f"ячеек эталона {total}: воспроизведено выемками {same}, расходится {len(differ)}, "
          f"не достаётся конвертерами {len(unreachable)}")
    # Сегодня и то и другое равно нулю, поэтому любой остаток — расхождение, а не сноска.
    if "--report" in sys.argv:
        for line in differ:
            print(f"  ≠ {line}")
        for cell in unreachable:
            print(f"  ? {cell} — выемки не дают этого значения")

    # И сверка текста репозитория с выемками — то, ради чего скрипт писался изначально.
    missing = sorted(set(repo) - set(pdf))
    print(f"нет в выемках: {len(missing)} {missing[:6]}")
    # …и обратная сторона: блок есть в выемке, но не доехал до эталона. «Эталон недобрал
    # блок» иначе выглядело бы так же, как «блоков ровно столько, сколько нужно».
    # Имена сводим так же, как значения (апостроф выемки — типографский): иначе
    # «Will-o’-Wisp» выглядит блоком, которого в эталоне нет.
    fixture_names = {norm(n) for n in fixture}
    extra = sorted(n for n in pdf if norm(n) not in fixture_names)
    print(f"есть в выемках, но не в эталоне: {len(extra)}")
    for name in extra:
        print(f"  + {name}")
    for line in duplicates:
        print(f"  ! {line}")
    # Ненулевой код возврата — чтобы «эталон воспроизводится» было утверждением,
    # которое можно прогнать, а не обещанием в докстроке.
    sys.exit(1 if differ or unreachable or missing or duplicates else 0)
