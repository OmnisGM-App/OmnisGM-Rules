#!/usr/bin/env python3
"""Сборка эталона полей статблоков из официального PDF (issue #260).

Как пользоваться:

    # 1. Скачать PDF и прогнать три конвертера (скилл /convert-pdf):
    curl -sL -o /tmp/srd-5.2.1.pdf \
      https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf
    python3 .claude/skills/convert-pdf/convert_pdf.py /tmp/srd-5.2.1.pdf dnd_srd-5.2.1
    python3 .claude/skills/cleanup-artifacts/layout_recovery.py \
      /tmp/dnd_srd-5.2.1_marker.md /tmp/dnd_srd-5.2.1_recovered.md

    # 2. Четвёртая выемка — сам PDF, разрезанный по колонкам:
    pdftotext -layout -x 0   -W 297 -H 783 /tmp/srd-5.2.1.pdf /tmp/col_l.txt
    pdftotext -layout -x 297 -W 297 -H 783 /tmp/srd-5.2.1.pdf /tmp/col_r.txt
    # страницы склеиваются попарно в /tmp/srd-5.2.1_cols.txt (см. cols_from_pdf ниже)

    # 3. Собрать эталон:
    python3 .github/scripts/build_statblock_fields.py

Почему четыре выемки. Конвертеры теряют РАЗНЫЕ поля на двухколоночной вёрстке: marker
склеивает часть заголовков, pymupdf4llm и docling уносят AC/HP за таблицу характеристик.
Ни один из них в одиночку не даёт всех 3181 значений; вместе — дают.

Скрипт печатает расхождения с текущим текстом репозитория и пишет JSON рядом с фикстурой;
сама фикстура правится осознанно, не автоперезаписью.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PDF_MD = Path("/tmp/dnd_srd-5.2.1_recovered.md")
SIZE = r"(?:Tiny|Small|Medium|Large|Huge|Gargantuan)"
ABIL = ["Str", "Dex", "Con", "Int", "Wis", "Cha"]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"<!--.*?-->|```+", " ", s)          # артефакты конвертеров
    s = s.replace("−", "-").replace("–", "-").replace("—", "-").replace("’", "'")
    return " ".join(s.split()).strip(" .;,")


def clean_heading(line: str) -> str:
    line = re.sub(r"<[^>]+>", "", line)
    return re.sub(r"[#*_]+", " ", line).strip()


PDF_ALT = Path("/tmp/dnd_srd-5.2.1_pymupdf.md")
PDF_ALT2 = Path("/tmp/dnd_srd-5.2.1_docling.md")
# Четвёртый источник — сам PDF, разрезанный по колонкам (`pdftotext -layout -x/-W`):
# им добираются поля, которые конвертеры теряют на двухколоночной вёрстке.
PDF_COLS = Path("/tmp/srd-5.2.1_cols.txt")
LABELS = ["AC", "Initiative", "HP", "Speed", "Skills", "Senses", "Languages", "CR",
          "Immunities", "Resistances", "Vulnerabilities", "Gear"]


def pdf_blocks(path=None, bare=False) -> dict:
    """{имя: {поле: значение}} из перегона PDF (по умолчанию marker).

    bare=True — для docling: он пишет метки полей без разметки («AC 13 HP 36 …»),
    поэтому перед разбором их приходится обернуть самим.
    """
    lines = unicodedata.normalize("NFKC", (path or PDF_MD).read_text(encoding="utf-8")).split("\n")
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
        if bare and not name:
            # В голом тексте заголовков нет: имя — ближайшая непустая строка выше.
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
        body, stats = ([head_tail] if head_tail else []), []
        for j in range(i + 1, len(lines)):
            t = lines[j].strip()
            if re.match(r"^#{1,3}\s", t) or re.match(r"^#{4,6}\s*(Traits|Actions|Bonus Actions|Reactions|Legendary)", t):
                break
            if t.startswith("|"):
                if "Str" in t or "Int" in t:
                    stats.append(t)
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
        if bare:
            text = re.sub(rf"(?<![*\w])({'|'.join(LABELS)})(?=\s)", r"**\1**", text)
        labels = ["AC", "Initiative", "HP", "Speed", "Skills", "Senses", "Languages", "CR",
                  "Immunities", "Resistances", "Vulnerabilities", "Gear"]
        alt = "|".join(labels)
        parts = re.split(rf"\*\*({alt})\*\*", text)
        key_of = {"AC": "ac", "Initiative": "initiative", "HP": "hp", "Speed": "speed",
                  "Skills": "skills", "Senses": "senses", "Languages": "languages",
                  "CR": "cr", "Immunities": "immunities", "Resistances": "resistances",
                  "Vulnerabilities": "vulnerabilities", "Gear": "gear"}
        # Хвост поля обрезаем на первом признаке следующей секции: строка характеристик
        # без разметки таблицы («MOD SAVE …»), заголовок или начало черты («*Bite.*»).
        cut = re.compile(r"\s(?:<u>|MOD\s+SAVE|#{3,6}\s|\*[A-Z][^*]{0,60}?\.\*)")
        for k in range(1, len(parts) - 1, 2):
            key = key_of[parts[k]]
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
    out = {}
    for rel in ("src/dnd/srd-5.2/en/12_MonstersA-Z.md", "src/dnd/srd-5.2/en/13_Animals.md"):
        lines = (ROOT / rel).read_text(encoding="utf-8").split("\n")
        name, block, table = None, None, []
        for line in lines + ["### END"]:
            s = line.strip()
            m = re.match(r"^#{2,4} (.+)$", s)
            if m:
                if name and block:
                    if table:
                        block["abilities"] = parse_repo_table(table)
                    out[name] = block
                name, block, table = m.group(1).strip(), {}, []
                continue
            if block is None:
                continue
            m = re.match(rf"^\*({SIZE}[^*]*)\*$", s)
            if m and "header" not in block:
                block["header"] = norm(m.group(1))
                continue
            m = re.match(r"^- \*\*(Armor Class|Hit Points|Speed|Initiative|Skills|Senses|Languages|Immunities|Resistances|Vulnerabilities|Gear):\*\*\s*(.+)$", s)
            if m:
                key = {"Armor Class": "ac", "Hit Points": "hp", "Speed": "speed",
                       "Initiative": "initiative", "Skills": "skills", "Senses": "senses",
                       "Languages": "languages", "Immunities": "immunities",
                       "Resistances": "resistances", "Vulnerabilities": "vulnerabilities",
                       "Gear": "gear"}[m.group(1)]
                block[key] = norm(m.group(2))
                continue
            m = re.match(r"^- \*\*CR\*\*\s*(.+)$", s)
            if m:
                block["cr"] = norm(m.group(1))
                continue
            if s.startswith("|") and not s.startswith("|:"):
                table.append(s)
    return out


def parse_repo_table(rows: list) -> dict:
    """Таблица репозитория: строки SCORE/MOD/SAVE по колонкам STR…CHA."""
    data = {}
    for row in rows:
        cells = [norm(c) for c in row.strip().strip("|").split("|")]
        if not cells:
            continue
        head = cells[0].upper()
        if head in ("SCORE", "MOD", "SAVE"):
            data[head] = cells[1:7]
    if "SCORE" not in data:
        return {}
    return {a: (data["SCORE"][i] if i < len(data.get("SCORE", [])) else "",
                data["MOD"][i] if i < len(data.get("MOD", [])) else "",
                data["SAVE"][i] if i < len(data.get("SAVE", [])) else "")
            for i, a in enumerate(ABIL)}


if __name__ == "__main__":
    pdf, repo = pdf_blocks(), repo_blocks()
    # marker теряет часть заголовков (склеивает их с текстом) — недостающие блоки
    # добираем вторым перегоном: он тот же PDF, разобранный другим инструментом.
    alt = pdf_blocks(PDF_ALT)
    alt2 = pdf_blocks(PDF_ALT2, bare=True)
    for _name in set(repo) - set(pdf):
        if _name in alt:
            pdf[_name] = alt[_name]
    # Поля, потерянные обоими первыми перегонами (двухколоночная вёрстка ставит AC/HP
    # после таблицы характеристик), добираем третьим.
    for _name, _block in pdf.items():
        for _f in ("ac", "hp", "speed", "initiative", "cr", "skills", "senses", "languages"):
            if _f not in _block and _name in alt2 and _f in alt2[_name]:
                _block[_f] = alt2[_name][_f]
    for _name in set(repo) - set(pdf):
        if _name in alt2:
            pdf[_name] = alt2[_name]
    if PDF_COLS.exists():
        cols = pdf_blocks(PDF_COLS, bare=True)
        for _name, _block in pdf.items():
            for _f in ("ac", "hp", "speed", "initiative", "cr", "skills", "senses",
                       "languages", "immunities", "resistances", "vulnerabilities", "gear"):
                if _f not in _block and _name in cols and _f in cols[_name]:
                    _block[_f] = cols[_name][_f]
    print(f"блоков: PDF {len(pdf)}, репозиторий {len(repo)}, общих {len(set(pdf) & set(repo))}")
    Path("/tmp/pdf_blocks.json").write_text(json.dumps(pdf, ensure_ascii=False, indent=1), encoding="utf-8")
    Path("/tmp/repo_blocks.json").write_text(json.dumps(repo, ensure_ascii=False, indent=1), encoding="utf-8")
    missing = sorted(set(repo) - set(pdf))
    print(f"нет в перегоне: {len(missing)} {missing[:6]}")
