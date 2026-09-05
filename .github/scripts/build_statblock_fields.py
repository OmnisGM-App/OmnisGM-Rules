#!/usr/bin/env python3
"""Сборка и сверка эталона полей статблоков из официального PDF (issue #260).

Что скрипт делает и чего НЕ делает. Он снимает поля статблоков из четырёх выемок
официального PDF, сверяет их с текстом репозитория и — ключевое — с самой фикстурой
`fixtures/srd-5.2-statblock-fields.json`, печатая поячеечный отчёт: сколько значений
эталона выемки воспроизводят, какие расходятся и какие не достаются вовсе. Фикстуру он
НЕ перезаписывает: эталон правится осознанно, а не автоперезаписью с выхлопа конвертера.
Часть ячеек (см. отчёт `--report`) конвертерами не достаётся ни одним из четырёх путей —
они сняты из колонной выемки вручную и в отчёте перечислены поимённо.

Как пользоваться:

    # 1. Скачать PDF и прогнать конвертеры (скилл /convert-pdf):
    curl -sL -o /tmp/srd-5.2.1.pdf \
      https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf
    shasum -a 256 /tmp/srd-5.2.1.pdf   # обязан совпасть с _source.sha256 фикстуры
    python3 .claude/skills/convert-pdf/convert_pdf.py /tmp/srd-5.2.1.pdf dnd_srd-5.2.1
    python3 .claude/skills/cleanup-artifacts/layout_recovery.py \
      /tmp/dnd_srd-5.2.1_marker.md /tmp/dnd_srd-5.2.1_recovered.md

    # 2. Четвёртая выемка — сам PDF, разрезанный по колонкам, страницы склеены подряд:
    pdftotext -layout -x 0   -W 297 -H 783 /tmp/srd-5.2.1.pdf /tmp/col_l.txt
    pdftotext -layout -x 297 -W 297 -H 783 /tmp/srd-5.2.1.pdf /tmp/col_r.txt
    cat /tmp/col_l.txt /tmp/col_r.txt > /tmp/srd-5.2.1_cols.txt

    # 3. Сверить выемки с фикстурой и с текстом:
    python3 .github/scripts/build_statblock_fields.py --report

Пути к выемкам берутся из переменных окружения (`SRD_MARKER`, `SRD_PYMUPDF`,
`SRD_DOCLING`, `SRD_COLS`) — значения по умолчанию те, что оставляет рецепт выше.
Отсутствие файла — внятная ошибка, а не стектрейс.

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
    return out


def extractions() -> dict:
    """Слияние четырёх выемок: каждая добирает то, что потеряли предыдущие."""
    marker = pdf_blocks(source("SRD_MARKER", "/tmp/dnd_srd-5.2.1_recovered.md"))
    alt = pdf_blocks(source("SRD_PYMUPDF", "/tmp/dnd_srd-5.2.1_pymupdf.md"))
    docling = pdf_blocks(source("SRD_DOCLING", "/tmp/dnd_srd-5.2.1_docling.md"), bare=True)
    cols = pdf_blocks(source("SRD_COLS", "/tmp/srd-5.2.1_cols.txt"), bare=True)
    merged = dict(marker)
    for extra in (alt, docling, cols):
        for name, block in extra.items():
            if name not in merged:
                merged[name] = dict(block)
                continue
            for field, value in block.items():
                merged[name].setdefault(field, value)
    return merged


if __name__ == "__main__":
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))["blocks"]
    pdf, repo = extractions(), repo_blocks()
    print(f"блоков: выемки {len(pdf)}, репозиторий {len(repo)}, эталон {len(fixture)}, "
          f"общих с эталоном {len(set(pdf) & set(fixture))}")

    # Главное: сверка выемок с САМОЙ фикстурой — иначе «способ пересборки» ничего не значит.
    same, differ, unreachable = 0, [], []
    for name, fields in sorted(fixture.items()):
        for field, want in fields.items():
            if field in ("cr_note", "cr_repo", "xp_note", "outside_chapters"):
                continue
            got = pdf.get(name, {}).get(field)
            if got is None:
                unreachable.append(f"{name}.{field}")
            elif norm(got) == norm(want):
                same += 1
            else:
                differ.append(f"{name}.{field}: выемка «{got}» ≠ эталон «{want}»")
    total = same + len(differ) + len(unreachable)
    print(f"ячеек эталона {total}: воспроизведено выемками {same}, расходится {len(differ)}, "
          f"не достаётся конвертерами {len(unreachable)}")
    if "--report" in sys.argv:
        for line in differ:
            print(f"  ≠ {line}")
        for cell in unreachable:
            print(f"  ? {cell} — снято из колонной выемки вручную")

    # И сверка текста репозитория с выемками — то, ради чего скрипт писался изначально.
    missing = sorted(set(repo) - set(pdf))
    print(f"нет в выемках: {len(missing)} {missing[:6]}")
    # Ненулевой код возврата — чтобы «эталон воспроизводится» было утверждением,
    # которое можно прогнать, а не обещанием в докстроке.
    sys.exit(1 if differ or unreachable or missing else 0)
