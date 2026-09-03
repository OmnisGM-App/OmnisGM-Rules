#!/usr/bin/env python3
"""Сверка шапок статблоков SRD 5.2 с эталоном из официального PDF (issue #196).

Зачем нужен отдельный гейт. Импортированный текст 5.2 разошёлся с PDF ровно в одной
строке каждого статблока — «размер тип, мировоззрение»: пропал размер Tiny (24 существа),
составной размер «Medium or Small» схлопнулся в «Small» (~40), у роёв потерялся тип
«Swarm of Tiny Beasts», у части НИП — подтип в скобках, у джинна — мировоззрение. Ни одна
из этих потерь не ломает ни markdown, ни схему JSON API: файл валиден, таблицы на месте,
и все прежние проверки проходили. Поймать такое можно только сверкой с источником —
поэтому эталон (`fixtures/srd-5.2-statblock-headers.tsv`) выпилен из PDF и лежит в репе.

Проверяем три уровня, потому что дефект расползается по ним по очереди:
  1) шапки EN — построчно против эталона;
  2) указатели EN (`14_Glossary/04_Monsters.md`, `05_Animals.md`) — колонки размер/тип/
     мировоззрение собираются из шапок, и разъезжаются, если поправить только шапку;
  3) RU-зеркало — размер каждой шапки и указателя должен сводиться к тому же значению,
     что в EN (перевод свой, но размер — не предмет перевода).

Запуск: python3 .github/scripts/test_statblock_headers.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "srd-5.2-statblock-headers.tsv"
EN = ROOT / "src/dnd/srd-5.2/en"
RU = ROOT / "src/dnd/srd-5.2/ru"

SIZES_EN = ["Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"]
# Прилагательное согласуется с родом типа существа, поэтому вариантов больше, чем размеров.
SIZES_RU = {
    "крошечный": "Tiny", "крошечная": "Tiny", "крошечное": "Tiny",
    "маленький": "Small", "маленькая": "Small", "маленькое": "Small",
    "средний": "Medium", "средняя": "Medium", "среднее": "Medium",
    "большой": "Large", "большая": "Large", "большое": "Large",
    "огромный": "Huge", "огромная": "Huge", "огромное": "Huge",
    "громадный": "Gargantuan", "громадная": "Gargantuan", "громадное": "Gargantuan",
}
SIZE_RE = re.compile(rf"^((?:{'|'.join(SIZES_EN)})(?: or (?:{'|'.join(SIZES_EN)}))?)\s+(.*)$")
failures = []


def headers(path: Path, lang: str) -> dict:
    """{имя статблока → строка шапки без звёздочек}. Имя RU-блока — оригинал в скобках."""
    out, name = {}, None
    first_letter = "A-Z" if lang == "en" else "А-ЯЁ"
    for line in path.read_text(encoding="utf-8").split("\n"):
        s = line.strip()
        if s.startswith("#"):
            m = re.match(r"^#{2,4} (.+?)(?:\s*\(([^()]*)\))?$", s)
            if m:
                name = (m.group(2) if lang == "ru" else None) or m.group(1)
            continue
        m = re.match(rf"^\*([{first_letter}][^*]*)\*$", s)
        if m and name and not s.startswith("**"):
            out.setdefault(name, m.group(1))
            name = None
    return out


def size_of(header: str, lang: str) -> str:
    """Строка шапки → размер в терминах EN («Medium or Small»)."""
    first = re.split(r",\s*(?![^(]*\))", header, maxsplit=1)[0]
    if lang == "en":
        m = SIZE_RE.match(first)
        return m.group(1) if m else ""
    words = [w for w in first.split() if w.lower() != "или"]
    parts = []
    for w in words:
        if w.lower() in SIZES_RU:
            parts.append(SIZES_RU[w.lower()])
        else:
            break
    return " or ".join(parts)


def rows(path: Path) -> list:
    """Строки markdown-таблицы указателя как списки ячеек."""
    out = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        if not line.startswith("| ") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        out.append(cells)
    return out[1:]  # шапка таблицы


# --- 1. Шапки EN против эталона ------------------------------------------------------
expected = {}
for line in FIXTURE.read_text(encoding="utf-8").split("\n"):
    if not line.strip() or line.startswith("#"):
        continue
    name, header = line.split("\t")
    expected[name] = header

en_headers = {}
for f in ("12_MonstersA-Z.md", "13_Animals.md"):
    en_headers.update(headers(EN / f, "en"))

for name, header in sorted(expected.items()):
    got = en_headers.get(name)
    if got is None:
        failures.append(f"EN: статблок «{name}» из эталона не найден")
    elif got != header:
        failures.append(f"EN «{name}»: получили «{got}», в PDF «{header}»")
for name in sorted(set(en_headers) - set(expected)):
    failures.append(f"EN: статблок «{name}» есть в тексте, но не в эталоне PDF")

# --- 2. Указатели EN собраны из шапок ------------------------------------------------
for index, has_alignment in (("04_Monsters.md", True), ("05_Animals.md", False)):
    for cells in rows(EN / "14_Glossary" / index):
        header = en_headers.get(cells[0])
        if header is None:
            failures.append(f"EN-указатель {index}: строка «{cells[0]}» без статблока")
            continue
        first, alignment = re.split(r",\s*(?![^(]*\))", header, maxsplit=1)
        m = SIZE_RE.match(first)
        want = [m.group(1), m.group(2).strip()] + ([alignment.strip()] if has_alignment else [])
        got = cells[1:1 + len(want)]
        if got != want:
            failures.append(f"EN-указатель {index}, «{cells[0]}»: {got} ≠ шапка {want}")

# --- 3. RU-зеркало: тот же размер ------------------------------------------------------
ru_headers = {}
for f in ("12_MonstersA-Z.md", "13_Animals.md"):
    ru_headers.update(headers(RU / f, "ru"))

for name, header in sorted(expected.items()):
    got = ru_headers.get(name)
    if got is None:
        failures.append(f"RU: статблок «{name}» не найден")
        continue
    want_size = size_of(header, "en")
    got_size = size_of(got, "ru")
    if got_size != want_size:
        failures.append(f"RU «{name}»: размер «{got}» → {got_size or '?'}, в EN {want_size}")

for index in ("04_Monsters.md", "05_Animals.md"):
    for cells in rows(RU / "14_Glossary" / index):
        name = cells[1]  # колонка «Оригинал (EN)»
        if name not in expected:
            failures.append(f"RU-указатель {index}: «{name}» вне эталона")
            continue
        want_size = size_of(expected[name], "en")
        got_size = size_of(cells[2] + " x", "ru")
        if got_size != want_size:
            failures.append(f"RU-указатель {index}, «{name}»: «{cells[2]}» ≠ {want_size}")

if failures:
    print(f"❌ Шапки статблоков SRD 5.2 разошлись с PDF ({len(failures)}):")
    for f in failures[:40]:
        print(f"  — {f}")
    if len(failures) > 40:
        print(f"  … и ещё {len(failures) - 40}")
    sys.exit(1)

print(f"✅ Шапки статблоков SRD 5.2: {len(expected)} EN сверены с PDF, RU-зеркало сходится")
