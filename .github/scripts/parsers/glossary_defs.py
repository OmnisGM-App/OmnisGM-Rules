"""Parser for glossary-style definition sections (#### Name + body text).

Используется для свойств оружия и свойств мастерства (глава «Снаряжение», секции
«Properties»/«Свойства» и «Mastery Properties»/«Свойства мастерства»): каждое
определение — заголовок #### и абзац(ы) под ним. Питает hovercard-подсказки.
"""

import re

from .base import slugify


# ── Канонизация слага термина 5.1 под слаги 5.2 ───────────────────────────────
# Слаг rules-terms — общий ключ и hovercard-бакета, и gloss-гейта на стороне ридера
# (CORE_TERMS матчатся по слагу). Глоссарий 5.1 кодирует аббревиатуру прямо в имени
# («Armor Class (AC)», «Challenge Rating (CR)»), из-за чего слаг выходил armor-class-ac
# и НЕ совпадал с каноническим armor-class из 5.2 → термин не глоссился, хотя карточка
# есть. Снимаем хвост «(ABBR)» (короткая всезаглавная аббревиатура в скобках) + точечные
# орфографические синонимы 5.1→5.2, которые снятие скобок не покрывает.
_ABBR_TAIL = re.compile(r"\s*\([A-Z]{1,6}\)\s*$")
# Орфографические различия 5.1↔5.2, не сводимые снятием «(ABBR)» (число, формулировка).
_SLUG_ALIASES = {
    "opportunity-attack": "opportunity-attacks",  # 5.1 ед.ч. → канон 5.2 мн.ч.
}


def canonical_term_slug(name: str) -> str:
    """Канонический (5.2-совместимый) слаг термина из его EN-имени."""
    base = slugify(_ABBR_TAIL.sub("", name))
    return _SLUG_ALIASES.get(base, base)


def parse_defs(text: str, section: str) -> list[dict]:
    """Собрать определения #### внутри секции ### {section}.

    Возвращает [{slug, name, name_en, description_md}]. name_en=None — RU-выравнивание
    (по позиции с EN) делается на уровне generate_api (порядок определений одинаков —
    построчный паритет).
    """
    lines = text.split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.strip() == f"### {section}":
            start = i + 1
            break
    if start is None:
        return []

    body = []
    for line in lines[start:]:
        # Заголовок уровня 1–3 завершает секцию; #### (уровень 4) остаётся внутри.
        if re.match(r"^#{1,3} \S", line):
            break
        body.append(line)

    section_text = "\n".join(body)
    # parts: [pre, name1, body1, name2, body2, …]
    parts = re.split(r"^#### (.+)$", section_text, flags=re.M)
    defs = []
    for j in range(1, len(parts), 2):
        name = parts[j].strip()
        desc = parts[j + 1].strip() if j + 1 < len(parts) else ""
        defs.append({
            "slug": slugify(name),
            "name": name,
            "name_en": None,
            "description_md": desc,
        })
    return defs


def parse_untagged_defs(text: str) -> list[dict]:
    """Собрать определения #### БЕЗ тега [..] (термины ядра Rules Glossary).

    Состояния/действия/AoE/… помечены тегом и парсятся отдельно; здесь — прочие термины
    (Преимущество, Укрытие, Концентрация…). name_en=None — RU-выравнивание по позиции
    (глоссарий в EN-алфавите) в generate_api.
    """
    parts = re.split(r"^#### (.+)$", text, flags=re.M)
    defs = []
    for j in range(1, len(parts), 2):
        heading = parts[j].strip()
        if re.search(r"\[[^\]]+\]\s*$", heading):
            continue  # тегированный термин — не сюда
        desc = parts[j + 1].strip() if j + 1 < len(parts) else ""
        defs.append({
            "slug": slugify(heading),
            "name": heading,
            "name_en": None,
            "description_md": desc,
        })
    return defs


def parse_section_tables(text: str, lang: str) -> list[dict]:
    """Глоссарий 5.1: секции ### с таблицами → термины ядра (rules-terms).

    В отличие от 5.2 (08_RulesGlossary: #### Имя + абзац), глоссарий 5.1 (16_Glossary/
    00_Glossary) — компактные таблицы по секциям. Формат колонок:
      • EN: | Термин | Эффект |          → slug из термина.
      • RU: | Термин | Original | Эффект | → RU-таблицы содержат колонку EN-оригинала (col 1),
        поэтому канонический (EN) слаг и name_en берём ПРЯМО из неё — без позиционного
        выравнивания EN↔RU (глоссарии не идеально параллельны построчно).

    Заголовки/разделители таблиц пропускаем. Питает gloss-подсказки 5.1 (частичное покрытие:
    глоссятся лишь термы, чей слаг ∈ CORE_TERMS — по-слаговый гейт на стороне ридера).
    """
    defs = []
    seen = set()
    lines = text.split("\n")
    i, n = 0, len(lines)
    while i < n:
        if not lines[i].strip().startswith("|"):
            i += 1
            continue
        block = []
        while i < n and lines[i].strip().startswith("|"):
            block.append(lines[i])
            i += 1
        for row_idx, ln in enumerate(block):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if row_idx == 0:
                continue  # строка-заголовок таблицы
            if not any(cells) or all(set(c) <= set("-: ") for c in cells if c):
                continue  # разделитель |---|---|
            if not cells[0]:
                continue
            if lang == "ru":
                if len(cells) < 2:
                    continue  # нет EN-оригинала → слаг не вывести, пропускаем
                name = cells[0]
                name_en = cells[1]
                effect = cells[2] if len(cells) >= 3 else ""
                slug = canonical_term_slug(name_en)
            else:
                name = cells[0]
                name_en = None
                effect = cells[1] if len(cells) >= 2 else ""
                slug = canonical_term_slug(name)
            # Пустой эффект = строка-список имён без определения (Damage Types, Schools of Magic
            # и пр. одноколоночные EN-таблицы / 2-колоночные RU). Такие термы — не «карточка»;
            # выкидываем, чтобы гейт по-слагу не мог однажды показать пустую подсказку.
            if not effect or not slug or slug in seen:
                continue
            seen.add(slug)
            defs.append({
                "slug": slug,
                "name": name,
                "name_en": name_en,
                "description_md": effect,
            })
    return defs


def parse_tagged_defs(text: str, tags: list[str]) -> list[dict]:
    """Собрать определения #### «Имя [Тег]» по всему файлу, где Тег ∈ tags.

    Rules Glossary размечает термины тегами: «Dash [Action]» / «Рывок [Действие]».
    Имя = без тега. name_en=None — RU-выравнивание по позиции (порядок в глоссарии
    одинаков: EN-алфавит) делается в generate_api.
    """
    parts = re.split(r"^#### (.+)$", text, flags=re.M)
    tagset = set(tags)
    defs = []
    for j in range(1, len(parts), 2):
        heading = parts[j].strip()
        m = re.search(r"\[([^\]]+)\]\s*$", heading)
        if not m or m.group(1) not in tagset:
            continue
        name = heading[:m.start()].strip()
        desc = parts[j + 1].strip() if j + 1 < len(parts) else ""
        defs.append({
            "slug": slugify(name),
            "name": name,
            "name_en": None,
            "description_md": desc,
        })
    return defs
