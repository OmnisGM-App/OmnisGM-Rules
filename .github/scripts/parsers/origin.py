"""Parser for D&D SRD 5.2 character origins — species and backgrounds."""

import re

from .base import extract_names, slugify


def parse_origins(text: str, section: str, lang: str) -> list[dict]:
    """Parse origin entries (#### Name) from a given `### {section}` block.

    section — «Background Descriptions» / «Species Descriptions» (и их RU-эквиваленты).
    Границей секции служит следующий `## ` (h2) либо конец файла, поэтому общие
    подразделы «Parts of a …» (#### Ability Scores и т.п.) вне Descriptions не попадают.
    Тело сущности (черты/особенности) → description_md.
    """
    start = text.find(f"### {section}")
    if start < 0:
        return []
    body = text[start + len(f"### {section}"):]
    # Обрезаем по следующему разделу верхнего уровня (## …).
    nxt = re.search(r"\n## ", body)
    if nxt:
        body = body[:nxt.start()]

    origins = []
    for block in re.split(r"(?m)^#### ", body)[1:]:
        heading, _, rest = block.partition("\n")
        name, name_en, slug = extract_names(heading.strip(), lang)
        origins.append({
            "slug": slug,
            "name": name,
            "name_en": name_en,
            "description_md": rest.strip(),
        })
    return origins


# --- Виды структурой и наследия (#413) --------------------------------------------------------
# Три факта вида стоят первыми строками «**Метка:** значение».
_FACTS = {"en": ("Creature Type", "Size", "Speed"), "ru": ("Тип существа", "Размер", "Скорость")}
_SIZES = {"Medium": "medium", "Small": "small", "Средний": "medium", "Маленький": "small"}
# Особенность, варианты которой — наследия вида: таблицей (строка на наследие) или абзацами
# «**Имя.**» сразу за особенностью. Объявлено руками: в тексте вариант-абзац не отличить от особенности.
# Четвёртое поле — шаблон EN-имени варианта-абзаца: абзац-вариант обязан ему отвечать, а абзац сразу
# за последним вариантом — нет, иначе пропавший или лишний вариант прошёл бы молча.
SPECIES_LINEAGES = {
    "dragonborn": ("Draconic Ancestry", "table", 10, None),
    "elf": ("Elven Lineage", "table", 3, None),
    "gnome": ("Gnomish Lineage", "paragraphs", 2, r" Gnome$"),
    "goliath": ("Giant Ancestry", "paragraphs", 6, r"\(\w+ Giant\)$"),
    "tiefling": ("Fiendish Legacy", "table", 3, None),
}
_LEAD = re.compile(r"^\*\*_?(.+?)\._?\*\*\s*(.*)$")


def _species_paragraphs(body: str) -> tuple[dict[str, str], list[dict], list[dict]]:
    """Тело вида → факты, абзацы «**Имя.** текст» по порядку и таблицы (заголовок + строки)."""
    facts: dict[str, str] = {}
    paragraphs: list[dict] = []
    tables: list[dict] = []
    lines = body.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        fact = re.match(r"^\*\*(.+?):\*\*\s*(.+)$", line)
        lead = _LEAD.match(line)
        if fact:
            facts[fact.group(1)] = fact.group(2).strip()
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not set("".join(cells)) <= set("-: "):
                    rows.append(cells)
                i += 1
            tables.append({"header": rows[0], "rows": rows[1:]})
            continue
        elif lead:
            paragraphs.append({"name": lead.group(1).strip(), "text": [lead.group(2).strip()]})
        elif line and paragraphs and not re.match(r"^(Table|Таблица):", line):
            paragraphs[-1]["text"].append(line)
        i += 1
    return facts, paragraphs, tables


def structure_species(species: list[dict], lang: str, shape: list | None = None) -> tuple[list[dict], list]:
    """Дописывает видам факты и `traits`; возвращает записи `species-lineages` и форму разбора.

    Форма — на вид `(индекс абзаца особенности с наследиями, вид, число)` или None. EN находит
    особенность по объявлению `SPECIES_LINEAGES`; RU получает форму EN и берёт те же абзацы по
    позиции. Размер RU читает из своего текста; слаги наследий RU дописывает generate_api из EN.
    `traits[].lineages` — у особенности есть варианты в `species-lineages`; сами варианты в `traits`
    не попадают. У наследия-строки таблицы её колонки лежат в `details` и собраны в текст.
    """
    en = lang == "en"
    labels = _FACTS[lang]
    if shape is not None and len(shape) != len(species):
        raise ValueError(f"species: {len(species)} in {lang}, {len(shape)} in en")
    lineages: list[dict] = []
    out_shape: list = []
    for position, sp in enumerate(species):
        name = sp["name"]
        facts, paragraphs, tables = _species_paragraphs(sp["description_md"])
        missing = [label for label in labels if label not in facts]
        if missing:
            raise ValueError(f"{name}: species facts lack {missing}")
        sizes = [code for word, code in _SIZES.items() if re.search(rf"\b{word}\b", facts[labels[1]])]
        speed = re.search(r"\d+", facts[labels[2]])
        if not sizes or not speed:
            raise ValueError(f"{name}: size {facts[labels[1]]!r} or speed {facts[labels[2]]!r} not read")
        sp["creature_type"] = facts[labels[0]]
        sp["size"] = {"text": facts[labels[1]], "options": sizes}
        sp["speed"] = int(speed.group())

        if shape is None:
            declared = SPECIES_LINEAGES.get(sp["slug"])
            spec = None
            if declared:
                index = next((i for i, par in enumerate(paragraphs) if par["name"] == declared[0]), None)
                if index is None:
                    raise ValueError(f"{name}: lineage trait {declared[0]!r} not found")
                spec = (index, declared[1], declared[2])
                if declared[3]:
                    names = [par["name"] for par in paragraphs[index + 1:index + 2 + declared[2]]]
                    stray = [n for n in names[:declared[2]] if not re.search(declared[3], n)]
                    extra = [n for n in names[declared[2]:] if re.search(declared[3], n)]
                    if stray or extra:
                        raise ValueError(f"{name}: lineages of {declared[0]!r} do not match the declaration: "
                                         f"{stray + extra}")
        else:
            spec = shape[position]
        out_shape.append(spec)

        owner_index, kind, count = spec or (None, None, 0)
        if owner_index is not None and owner_index >= len(paragraphs):
            raise ValueError(f"{name}: no paragraph {owner_index} for the lineage trait")
        inline = range(owner_index + 1, owner_index + 1 + count) if kind == "paragraphs" else range(0)
        traits: list[dict] = []
        variants: list[dict] = []
        for index, paragraph in enumerate(paragraphs):
            entry = {"name": paragraph["name"], "description_md": "\n\n".join(t for t in paragraph["text"] if t)}
            if index in inline:
                variants.append({**entry, "details": []})
            else:
                traits.append({**entry, "lineages": index == owner_index})
        if kind == "table":
            if len(tables) != 1:
                raise ValueError(f"{name}: expected one lineage table, found {len(tables)}")
            header = tables[0]["header"]
            variants = []
            for row in tables[0]["rows"]:
                if len(row) != len(header):
                    raise ValueError(f"{name}: lineage row {row[0]!r} has {len(row)} cells, the header has {len(header)}")
                details = [{"label": label, "text": cell} for label, cell in zip(header[1:], row[1:])]
                variants.append({"name": row[0], "details": details,
                                 "description_md": "\n\n".join(f"**{d['label']}:** {d['text']}" for d in details)})
        elif tables:
            raise ValueError(f"{name}: a table in a species without a declared lineage table")
        if len(variants) != count:
            raise ValueError(f"{name}: {len(variants)} lineages, declared {count}")
        sp["traits"] = traits
        owner = paragraphs[owner_index]["name"] if owner_index is not None else None
        for variant in variants:
            key = re.search(r"\(([^)]+)\)$", variant["name"])
            lineages.append({
                "slug": f"{sp['slug']}-{slugify(key.group(1) if key else variant['name'])}" if en else None,
                "name": variant["name"],
                "name_en": None,
                "species": sp["slug"],
                "trait": owner,
                "description_md": variant["description_md"],
                "details": variant["details"],
            })
    return lineages, out_shape
