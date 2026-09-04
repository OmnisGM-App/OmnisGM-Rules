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
  4) RU-зеркало — размер, мировоззрение, наличие подтипа и признак роя должны сводиться
     к тем же значениям, что в EN (перевод свой, но это поля данных, а не проза).

Версии берутся из имён фикстур (`srd-<версия>-statblock-headers.tsv`) — чтобы добавить
5.1, достаточно положить рядом её фикстуру, править код не нужно.

Запуск: python3 .github/scripts/test_statblock_headers.py
"""
import re
import sys
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
# Мировоззрение RU → EN. Формы среднего рода («нейтрально-доброе») — след несогласованности
# перевода, а не отдельное значение: принимаем обе, сама несогласованность лечится в #256.
ALIGN_RU = {
    "без мировоззрения": "Unaligned",
    "нейтральный": "Neutral",
    "нейтрально-злой": "Neutral Evil",
    "нейтрально-добрый": "Neutral Good", "нейтрально-доброе": "Neutral Good",
    "хаотично-злой": "Chaotic Evil",
    "хаотично-добрый": "Chaotic Good", "хаотично-доброе": "Chaotic Good",
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
# Таксономический хвост в скобках: в 5.1 он есть и у заголовков статблоков («Deva (Angel)»),
# и у строк указателя — в ключ эталона он не входит.
STRIP_TAIL = re.compile(r"\s*\([^()]*\)$")
failures = []


def align_to_en(text: str):
    """RU-мировоззрение → EN-значение. None, если строка не опознана.

    В 5.1 перевод несогласован по роду («Нейтральное» и «Нейтральный» у одного и того же
    значения) — это дефект перевода, а не разные значения, поэтому окончание нормализуем.
    Отдельно разбираются «Любое … мировоззрение» и составное «X (50%) или Y (50%)»
    (облачный великан).
    """
    t = " ".join(text.strip().lower().split())
    if " или " in t:
        parts = []
        for chunk in t.split(" или "):
            m = PERCENT_RE.match(chunk.strip())
            base, tail = (m.group(1), f" {m.group(2)}") if m else (chunk.strip(), "")
            mapped = align_to_en(base)
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
    if t.endswith("ое"):
        for ending in ("ый", "ой"):
            if t[:-2] + ending in ALIGN_RU:
                return ALIGN_RU[t[:-2] + ending]
    return None


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


def en_name_from_ru_heading(heading: str) -> str:
    """Оригинальное имя из RU-заголовка статблока.

    В 5.2 всё просто: «Летучая мышь (Bat)». В 5.1 заголовки разнородны — «Балор (Balor)
    (Демон)», «Андросфинкс (Androsphinx (Sphinx))», «Гном глубинный (свирфнеблин)
    (Gnome, Deep (Svirfneblin))». Берём последнюю группу скобок с латиницей и снимаем
    её собственный таксономический хвост — так ключ сходится с именем EN-заголовка.
    """
    latin = [g for g in paren_groups(heading) if re.search(r"[A-Za-z]", g)]
    if not latin:
        return heading.strip()
    return STRIP_TAIL.sub("", latin[-1]).strip()


def headers(path: Path, lang: str) -> dict:
    """{имя статблока → строка шапки без звёздочек}. Имя RU-блока — оригинал в скобках."""
    out, name = {}, None
    first_letter = "A-Z" if lang == "en" else "А-ЯЁ"
    for line in path.read_text(encoding="utf-8").split("\n"):
        s = line.strip()
        if s.startswith("#"):
            m = re.match(r"^#{2,4} (.+)$", s)
            if m:
                name = (en_name_from_ru_heading(m.group(1)) if lang == "ru"
                        else STRIP_TAIL.sub("", m.group(1)).strip())
            continue
        m = re.match(rf"^\*([{first_letter}][^*]*)\*$", s)
        if m and name and not s.startswith("**"):
            out.setdefault(name, m.group(1))
            name = None
    return out


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


def parts_ru(header: str):
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
            align_to_en(alignment), rest.strip())


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


def check_version(version: str, fixture: Path) -> None:
    expected = {}
    for number, line in enumerate(fixture.read_text(encoding="utf-8").split("\n"), 1):
        if not line.strip() or line.startswith("#"):
            continue
        # Колонок минимум две; третья (сырая строка PDF) — для глаз рецензента, не для сверки.
        # Разбор битой строки не роняем трейсбеком: фикстура правится руками.
        parts = line.split("\t")
        if len(parts) < 2 or not parts[0].strip() or not parts[1].strip():
            failures.append(f"{version}: строка {number} фикстуры не разбирается: {line!r}")
            continue
        expected[parts[0]] = parts[1]

    en_dir, ru_dir = ROOT / f"src/dnd/{version}/en", ROOT / f"src/dnd/{version}/ru"
    en_headers, ru_headers = {}, {}
    for f in statblock_files(en_dir):
        en_headers.update(headers(f, "en"))
    for f in statblock_files(ru_dir):
        ru_headers.update(headers(f, "ru"))

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
            # Имя строки: в EN-указателе первая колонка, в RU — вторая («Оригинал (EN)»).
            index_names[lang].update(
                STRIP_TAIL.sub("", r[0 if lang == "en" else 1]) for r in rows if len(r) > 1)
            for cells in rows:
                key = STRIP_TAIL.sub("", cells[0] if lang == "en" else
                                     (cells[1] if len(cells) > 1 else cells[0]))
                header = (en_headers if lang == "en" else ru_headers).get(key)
                if header is None:
                    failures.append(f"{version} {lang}-указатель {index}: строка «{key}» без статблока")
                    continue
                if lang == "ru":
                    continue  # колонки RU-указателя сверяются размером ниже, отдельным блоком
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
    for name, header in sorted(expected.items()):
        got = ru_headers.get(name)
        if got is None:
            failures.append(f"{version} RU: статблок «{name}» не найден")
            continue
        want = parts_en(header)
        ru = parts_ru(got)
        if want is None or ru is None:
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

    # --- RU-указатели: размер (тип и подтип RU ждут #256) -------------------------------
    for index in ("04_Monsters.md", "05_Animals.md"):
        path = next(iter(ru_dir.glob(f"*Glossary/{index}")), None)
        if path is None:
            continue
        for cells in index_rows(path):
            key = STRIP_TAIL.sub("", cells[1]) if len(cells) > 1 else ""
            if len(cells) < 3 or key not in expected:
                continue
            want = parts_en(expected[key])
            ru = parts_ru(f"{cells[2]} тип, без мировоззрения")
            if ru is None or ru[0] != want[0]:
                failures.append(
                    f"{version} RU-указатель {index}, «{key}»: размер «{cells[2]}» ≠ {want[0]}")


fixtures = sorted(SCRIPTS.glob("fixtures/srd-*-statblock-headers.tsv"))
if not fixtures:
    print("❌ не найдено ни одной фикстуры шапок — проверять нечего")
    sys.exit(1)

versions = []
for fixture in fixtures:
    version = re.match(r"(srd-[\d.]+)-statblock-headers\.tsv", fixture.name).group(1)
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
