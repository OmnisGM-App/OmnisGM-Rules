"""Parsers for Daggerheart SRD entities.

Даггерхарт-контент — прозаические главы; сущности погребены в больших файлах без
собственного URL. Достаём именованные записи (ancestries, communities, domain cards,
adversaries, environments) в structured JSON для programmatic-страниц (аналог D&D issue #20).

name_en у RU-сущностей берётся из inline-English в заголовках (`## Дварф (Dwarf)`,
`### Кислотный землерой (Acid Burrower)`), как в D&D SRD 5.1 — так EN/RU слаги совпадают.
"""

import re

from .base import split_blocks, extract_names


# ── Ancestries / Communities: плоские `## Имя` секции ──────────────────────────
# Тело (описание + `### Ancestry/Community Feature`) целиком идёт в description_md.

def _parse_flat_sections(text: str, lang: str) -> list[dict]:
    out = []
    for heading, body in split_blocks(text, 2):
        name, name_en, slug = extract_names(heading.strip(), lang)
        out.append({
            "slug": slug,
            "name": name,
            "name_en": name_en,
            "description_md": body.strip(),
        })
    return out


def parse_ancestries(text: str, lang: str) -> list[dict]:
    """Происхождения (`## Clank`, `## Drakona`, …) — плоские секции."""
    return _parse_flat_sections(text, lang)


def parse_communities(text: str, lang: str) -> list[dict]:
    """Сообщества (`## Highborne`, `## Loreborne`, …) — плоские секции."""
    return _parse_flat_sections(text, lang)


# ── Domain Cards: `## Домен` → `### Карта` ─────────────────────────────────────
# Домен — фасет (для by-domain хаба). Первая строка тела карты несёт мету:
# «**_Level 1_** _Arcana Spell._ **_Recall Cost_** _0._»

def _card_meta(body: str) -> dict:
    """Уровень / стоимость отзыва / тип из первой мета-строки карты (EN+RU метки)."""
    level = recall = card_type = None
    m = re.search(r"(?:Level|Уровень)\s+(\d+)", body)
    if m:
        level = int(m.group(1))
    m = re.search(r"(?:Recall Cost|Стоимость Отзыва)_?\*\*\s*_?(\d+)", body)
    if m:
        recall = int(m.group(1))
    # Тип — курсив между уровнем и стоимостью отзыва: «_Arcana Spell._» → «Arcana Spell».
    m = re.search(r"(?:Level|Уровень)\s+\d+_?\*\*\s*_([^_]+?)\._", body)
    if m:
        card_type = m.group(1).strip()
    return {"level": level, "recall_cost": recall, "card_type": card_type}


def parse_domain_cards(text: str, lang: str) -> list[dict]:
    """Доменные карты: `## Домен (Domain)` → `### Карта (Card)`.

    Домен — фасет: display + канонический (английский) слаг для by-domain хаба.
    """
    out = []
    for dom_heading, dom_body in split_blocks(text, 2):
        dom_name, dom_en, dom_slug = extract_names(dom_heading.strip(), lang)
        for heading, body in split_blocks(dom_body, 3):
            name, name_en, slug = extract_names(heading.strip(), lang)
            meta = _card_meta(body)
            out.append({
                "slug": slug,
                "name": name,
                "name_en": name_en,
                "domain": dom_name,
                "domain_en": dom_en or dom_name,
                "domain_slug": dom_slug,
                "level": meta["level"],
                "recall_cost": meta["recall_cost"],
                "card_type": meta["card_type"],
                "description_md": body.strip(),
            })
    return out


# ── Adversaries / Environments: `## Ранг N` → `### Имя` (→ `#### Способности`) ──
# Тир — фасет. Вводная секция «Using …» / «Использование …» без номера — пропускается.

def _parse_tiered(text: str, lang: str) -> list[dict]:
    out = []
    for parent_heading, parent_body in split_blocks(text, 2):
        m = re.search(r"(?:Tier|Ранга?)\s+(\d+)", parent_heading)
        if not m:
            continue  # «Using Adversaries» / «Использование Противников» — не сущность
        tier = int(m.group(1))
        for heading, body in split_blocks(parent_body, 3):
            name, name_en, slug = extract_names(heading.strip(), lang)
            out.append({
                "slug": slug,
                "name": name,
                "name_en": name_en,
                "tier": tier,
                "description_md": body.strip(),
            })
    return out


def parse_adversaries(text: str, lang: str) -> list[dict]:
    """Противники — стат-блоки по тирам."""
    return _parse_tiered(text, lang)


def parse_environments(text: str, lang: str) -> list[dict]:
    """Окружения — стат-блоки по тирам."""
    return _parse_tiered(text, lang)


# ── Глоссарий: `### Термин (English)` с прозаическим определением ──────────────
# Файл начинается табличными секциями (Сокращения/Состояния/…), затем идут
# индивидуальные термины прозой. Берём только прозаические (тело не таблица) →
# ресурс rules-terms для gloss-подсказок. name_en из inline-English → слаг EN↔RU.

def parse_dh_glossary(text: str, lang: str) -> list[dict]:
    out = []
    for heading, body in split_blocks(text, 3):
        stripped = body.strip()
        # Пропускаем табличные секции (Состояния/Типы урона/…) и пустые.
        if not stripped or stripped.lstrip().startswith("|"):
            continue
        name, name_en, slug = extract_names(heading.strip(), lang)
        out.append({
            "slug": slug,
            "name": name,
            "name_en": name_en,
            "description_md": stripped,
        })
    return out
