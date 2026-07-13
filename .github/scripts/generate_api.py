#!/usr/bin/env python3
"""Generate static JSON API from D&D SRD Markdown sources.

Usage:
    python3 .github/scripts/generate_api.py --src-root src/dnd --output-dir site/api
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Add scripts dir to path so parsers package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

# jsonschema is only needed for validation. Keep it optional so build-time data
# generation (Astro prebuild → getStaticPaths) can run with plain python3, without
# installing pip packages in CI.
try:
    import jsonschema
except ImportError:
    jsonschema = None

from config import (SOURCES, SKIP_HEADINGS_SPELL, SKIP_HEADINGS_MONSTER,
                    SKIP_HEADINGS_EQUIPMENT, SKIP_HEADINGS_FEAT)
from parsers import (parse_spells, parse_monsters, parse_magic_items,
                     parse_weapons, parse_armor, parse_equipment,
                     parse_conditions, parse_feats)
from parsers.base import slugify
from schemas import RESOURCE_SCHEMAS

SYSTEM = "dnd"
SYSTEM_NAME = "Dungeons & Dragons"

VERSION_NAMES = {"srd52": "SRD 5.2.1", "srd51": "SRD 5.1"}


_RU_EN_MAP_CACHE: dict[str, dict[str, str]] = {}


def load_ru_to_en_map(src_root: Path) -> dict[str, str]:
    """Build {RU term → EN term} from the authoritative base dictionary.

    Used to backfill name_en (and thus a canonical English slug) for RU entities
    whose headings lack the "(English)" suffix — notably conditions, which read
    "#### Ослеплённый [Состояние]" with no inline English. Columns:
    | Оригинал 5.2 | Оригинал 5.1 | Перевод | ... |  → map[Перевод] = Оригинал 5.2.
    """
    key = str(src_root)
    if key in _RU_EN_MAP_CACHE:
        return _RU_EN_MAP_CACHE[key]

    mapping: dict[str, str] = {}
    dict_path = src_root / "translate" / "01_dictionary_base.md"
    if dict_path.is_file():
        for line in dict_path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|") or "---" in line:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and cells[0] not in ("Оригинал 5.2", "Оригинал"):
                en, ru = cells[0], cells[2]
                if en and ru and en != "—" and ru not in mapping:
                    mapping[ru] = en
    _RU_EN_MAP_CACHE[key] = mapping
    return mapping


def backfill_name_en(entities: list[dict], src_root: Path) -> None:
    """For RU entities missing name_en, fill it from the base dictionary and
    re-slug on the canonical English name (so /ru and /en share one slug)."""
    mapping = load_ru_to_en_map(src_root)
    for entity in entities:
        if entity.get("name_en"):
            continue
        en = mapping.get(entity.get("name", ""))
        if en:
            entity["name_en"] = en
            entity["slug"] = slugify(en)


def _num_key(s: str | None) -> str | None:
    """Языко-инвариантный числовой ключ: только цифры («10 GP»/«10 зм» → «10»,
    «1,500 GP»/«1500 зм» → «1500», «4 lb.»/«4 фнт.» → «4»)."""
    if not s:
        return None
    digits = re.sub(r"[^\d]", "", str(s))
    return digits or None


def _weapon_fp(e: dict) -> tuple:
    return (e["category"], e["type"], e["damage_dice"], e["damage_type"],
            _num_key(e.get("weight")), _num_key(e.get("cost")),
            e.get("range_normal"), e.get("range_long"))


def _armor_fp(e: dict) -> tuple:
    return (e["category"], e["ac_base"], e.get("ac_dex_bonus"), e.get("ac_max_dex"),
            e.get("strength_req"), e.get("stealth_disadvantage"),
            _num_key(e.get("weight")), _num_key(e.get("cost")))


_STAT_TABLE_FP = {"weapons": _weapon_fp, "armor": _armor_fp}


def align_stat_table_name_en(all_data: dict) -> None:
    """Проставить RU-оружию/доспехам name_en + канонический (англ.) слаг.

    Их имена — в ячейках таблиц (не в заголовках со скобкой «(English)»), а таблицы
    отсортированы по алфавиту КАЖДОГО языка отдельно → позиционная сверка EN↔RU неверна,
    в словаре имён нет. Зато стат-блок языко-инвариантен: сверяем RU→EN по «отпечатку»
    (категория/урон/вес/цена-число/…). Механически-идентичные пары (Glaive/Halberd — один
    отпечаток) разводим по мастерству: 1-й проход учит карту «RU-мастерство → EN» на
    однозначных строках (Greatsword→Graze, Greataxe→Cleave), 2-й — разрешает коллизии.
    """
    for (ver, lang, resource), ru_entities in all_data.items():
        if lang != "ru" or resource not in _STAT_TABLE_FP:
            continue
        en_entities = all_data.get((ver, "en", resource))
        if not en_entities:
            continue
        fp = _STAT_TABLE_FP[resource]
        en_by_fp: dict[tuple, list[dict]] = {}
        for e in en_entities:
            en_by_fp.setdefault(fp(e), []).append(e)

        mastery_ru_en: dict[str, str] = {}
        pending: list[dict] = []
        for r in ru_entities:
            bucket = en_by_fp.get(fp(r), [])
            if len(bucket) == 1:
                e = bucket[0]
                r["name_en"] = e["name"]
                r["slug"] = e["slug"]
                if resource == "weapons" and r.get("mastery") and e.get("mastery"):
                    mastery_ru_en[r["mastery"]] = e["mastery"]
            else:
                pending.append(r)

        for r in pending:
            bucket = en_by_fp.get(fp(r), [])
            target = None
            if resource == "weapons":
                want = mastery_ru_en.get(r.get("mastery"))
                target = next((e for e in bucket if e.get("mastery") == want), None)
            if target is None:
                target = bucket[0] if bucket else None
                print(f"  Warning: неоднозначный name_en для RU {resource} "
                      f"{r.get('name')!r} — взят первый кандидат", file=sys.stderr)
            if target:
                r["name_en"] = target["name"]
                r["slug"] = target["slug"]
            else:
                print(f"  Warning: не найден EN-аналог для RU {resource} "
                      f"{r.get('name')!r}", file=sys.stderr)


def resolve_cross_refs(all_data: dict) -> None:
    """Resolve spell name → slug cross-references for monsters and magic items."""
    spell_lookup: dict[tuple[str, str], dict[str, str]] = {}

    for key, entities in all_data.items():
        ver, lang, resource = key
        if resource != "spells":
            continue
        lookup = {}
        for spell in entities:
            lookup[spell["name"].lower()] = spell["slug"]
            if spell.get("name_en"):
                lookup[spell["name_en"].lower()] = spell["slug"]
        spell_lookup[(ver, lang)] = lookup

    for key, entities in all_data.items():
        ver, lang, resource = key
        if resource not in ("monsters", "animals", "magic-items"):
            continue
        lookup = spell_lookup.get((ver, lang), {})
        if not lookup:
            continue
        for entity in entities:
            if "spells" in entity and entity["spells"]:
                resolved = []
                for spell_name in entity["spells"]:
                    slug = lookup.get(spell_name.lower())
                    if slug:
                        resolved.append(slug)
                entity["spells"] = resolved


# Подклассы SRD 5.2, которые дают доступ к заклинаниям (спелл-гранты в 03_Classes/*.md).
# Заголовок таблицы в EN — `Table: <Name> Spells`; RU-название берём из этого мапа.
# ver-каталог для класс-файлов (ver → префикс пути в src).
VER_DIR = {"srd52": "srd-5.2", "srd51": "srd-5.1"}
SUBCLASS_LABELS = {
    "Life Domain":      {"en": "Life Domain",      "ru": "Домен жизни"},
    "Oath of Devotion": {"en": "Oath of Devotion", "ru": "Клятва преданности"},
    "Fiend":            {"en": "Fiend",            "ru": "Исчадие"},
    "Draconic":         {"en": "Draconic",         "ru": "Драконье чародейство"},
}


def _parse_subclass_spell_tables(text: str) -> dict[str, set[str]]:
    """Из EN-разметки класса извлечь {подкласс: {имена заклинаний}} по таблицам спелл-грантов.

    Таблица подкласса: строка `Table: <Name> Spells`, где <Name> — не базовый список
    (`Level N <Class>` / `Cantrips`). Имена заклинаний — в последнем столбце (через запятую).
    """
    out: dict[str, set[str]] = {}
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        m = re.match(r"^Table:\s+(.+?)\s+Spells\s*$", lines[i].strip())
        if m and not re.search(r"Level \d|Cantrips", m.group(1)):
            name = m.group(1).strip()
            spells: set[str] = set()
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("|"):
                j += 1
            seen_sep = False
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
                joined = "".join(cells)
                if joined and set(joined) <= set("-: "):
                    seen_sep = True
                elif seen_sep and len(cells) >= 2:
                    for sp in cells[-1].split(","):
                        sp = sp.strip()
                        if sp:
                            spells.add(sp)
                j += 1
            if spells:
                out[name] = spells
        i += 1
    return out


def inject_spell_subclasses(all_data: dict, src_root: Path) -> None:
    """Добавить полю заклинания `subclasses` — подклассы, дающие к нему доступ (по слагу)."""
    versions = {ver for (ver, lang, res) in all_data if res == "spells"}
    for ver in versions:
        vdir = VER_DIR.get(ver)
        if not vdir:
            continue
        classes_dir = src_root / vdir / "en" / "03_Classes"
        if not classes_dir.is_dir():
            continue
        # подкласс(EN) → {EN-имена заклинаний}
        sub_spells: dict[str, set[str]] = {}
        for f in sorted(classes_dir.glob("*.md")):
            for name, spells in _parse_subclass_spell_tables(f.read_text(encoding="utf-8")).items():
                if name in SUBCLASS_LABELS:
                    sub_spells.setdefault(name, set()).update(spells)
        if not sub_spells:
            continue
        # EN-имя заклинания → slug
        en_lookup = {sp["name"].lower(): sp["slug"] for sp in all_data.get((ver, "en", "spells"), [])}
        # slug → [подкласс(EN)]
        slug_subs: dict[str, list[str]] = {}
        for name, spells in sub_spells.items():
            for sp in spells:
                slug = en_lookup.get(sp.lower())
                if slug:
                    slug_subs.setdefault(slug, []).append(name)
        # инжект в заклинания всех языков этой версии (локализованное имя подкласса)
        for (k_ver, k_lang, k_res), entities in all_data.items():
            if k_ver != ver or k_res != "spells":
                continue
            for e in entities:
                subs = slug_subs.get(e["slug"])
                if subs:
                    e["subclasses"] = [
                        SUBCLASS_LABELS[n].get(k_lang, n) for n in sorted(set(subs))
                    ]


def write_json(path: Path, data) -> None:
    """Write data as JSON with consistent formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def validate_entities(entities: list[dict], schema: dict, resource: str, label: str) -> None:
    """Validate every entity against a JSON Schema. Exit on first error."""
    for entity in entities:
        try:
            jsonschema.validate(entity, schema)
        except jsonschema.ValidationError as exc:
            print(f"\nSchema validation error in {label} — {resource}, "
                  f"entity '{entity.get('slug', '?')}':\n  {exc.message}",
                  file=sys.stderr)
            if exc.absolute_path:
                print(f"  Path: {'.'.join(str(p) for p in exc.absolute_path)}", file=sys.stderr)
            sys.exit(1)


def write_index_html(path: Path, title: str, links: list[dict],
                     breadcrumbs: list[dict] | None = None,
                     schema: dict | None = None) -> None:
    """Write an index.html navigation page.

    links: list of {"href": "...", "label": "...", "badge": "..." (optional)}
    breadcrumbs: list of {"href": "...", "label": "..."} for navigation trail
    schema: if provided, show JSON Schema block describing the entity format
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    bc_html = ""
    if breadcrumbs:
        parts = []
        for bc in breadcrumbs:
            if bc.get("href"):
                parts.append(f'<a href="{bc["href"]}">{bc["label"]}</a>')
            else:
                parts.append(f'<span>{bc["label"]}</span>')
        bc_html = f'<nav class="breadcrumbs">{"&nbsp;/&nbsp;".join(parts)}</nav>'

    items = []
    for link in links:
        badge = f' <span class="badge">{link["badge"]}</span>' if link.get("badge") else ""
        items.append(f'<li><a href="{link["href"]}">{link["label"]}</a>{badge}</li>')

    schema_html = ""
    if schema:
        import html as html_mod
        formatted = json.dumps(schema, ensure_ascii=False, indent=2)
        escaped = html_mod.escape(formatted)
        schema_html = f"""
<details open>
<summary><strong>JSON Schema</strong></summary>
<pre><code>{escaped}</code></pre>
</details>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; color: #1a1a2e; background: #fafafa; }}
  h1 {{ font-size: 1.5rem; margin-bottom: .5rem; }}
  .breadcrumbs {{ font-size: .85rem; color: #666; margin-bottom: 1.5rem; }}
  .breadcrumbs a {{ color: #4361ee; text-decoration: none; }}
  .breadcrumbs a:hover {{ text-decoration: underline; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ margin: .4rem 0; }}
  li a {{ color: #4361ee; text-decoration: none; font-size: 1.05rem; }}
  li a:hover {{ text-decoration: underline; }}
  .badge {{ background: #e8eaf6; color: #3949ab; padding: .15rem .5rem; border-radius: .75rem; font-size: .8rem; margin-left: .5rem; }}
  details {{ margin: 1.5rem 0; }}
  summary {{ cursor: pointer; font-size: 1.05rem; margin-bottom: .5rem; }}
  pre {{ background: #f0f0f4; padding: 1rem; border-radius: .5rem; overflow-x: auto; font-size: .85rem; line-height: 1.4; }}
  footer {{ margin-top: 2rem; font-size: .75rem; color: #999; }}
</style>
</head>
<body>
{bc_html}
<h1>{title}</h1>
{schema_html}
<ul>
{"".join(items)}
</ul>
<footer>TTRPG SRD Markdown &mdash; Static JSON API</footer>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    parser = argparse.ArgumentParser(description="Generate D&D SRD JSON API")
    parser.add_argument("--src-root", required=True, help="Root directory of SRD markdown sources")
    parser.add_argument("--output-dir", required=True, help="Output directory for JSON API (e.g. site/api)")
    parser.add_argument("--individual", action="store_true",
                        help="Generate individual {slug}.json files (default: only all.json per resource)")
    parser.add_argument("--no-validate", action="store_true",
                        help="Skip JSON Schema validation (for build-time data generation without jsonschema)")
    args = parser.parse_args()

    src_root = Path(args.src_root)
    output_dir = Path(args.output_dir)

    if not src_root.is_dir():
        print(f"Error: source root '{src_root}' not found", file=sys.stderr)
        sys.exit(1)

    system_dir = output_dir / SYSTEM

    # Parse all sources
    all_data: dict[tuple[str, str, str], list[dict]] = {}
    total_entities = 0

    for source in SOURCES:
        ver = source["ver"]
        lang = source["lang"]
        entity_type = source["type"]
        filepath = src_root / source["file"]
        heading_level = source["h"]
        after = source.get("after")
        out_resource = source.get("out")

        if not filepath.is_file():
            print(f"  Warning: {filepath} not found, skipping", file=sys.stderr)
            continue

        text = filepath.read_text(encoding="utf-8")

        if entity_type == "spell":
            entities = parse_spells(text, heading_level, lang, after, SKIP_HEADINGS_SPELL)
            resource = "spells"
        elif entity_type == "monster":
            entities = parse_monsters(text, heading_level, lang, after, SKIP_HEADINGS_MONSTER)
            resource = out_resource or "monsters"
        elif entity_type == "magic_item":
            entities = parse_magic_items(text, heading_level, lang, after)
            resource = "magic-items"
        elif entity_type == "weapon":
            entities = parse_weapons(text, lang)
            resource = "weapons"
        elif entity_type == "armor":
            entities = parse_armor(text, lang)
            resource = "armor"
        elif entity_type == "equipment":
            entities = parse_equipment(text, heading_level, lang, after, SKIP_HEADINGS_EQUIPMENT)
            resource = "equipment"
        elif entity_type == "condition":
            entities = parse_conditions(text, heading_level, lang, after)
            resource = "conditions"
            if lang == "ru":
                backfill_name_en(entities, src_root)
        elif entity_type == "feat":
            entities = parse_feats(text, heading_level, lang, after, SKIP_HEADINGS_FEAT)
            resource = "feats"
        else:
            print(f"  Warning: unknown type '{entity_type}', skipping", file=sys.stderr)
            continue

        key = (ver, lang, resource)
        if key in all_data:
            all_data[key].extend(entities)
        else:
            all_data[key] = entities

        count = len(entities)
        total_entities += count
        print(f"  {ver}/{lang}/{resource}: {count} entities from {source['file']}")

    # RU-оружию/доспехам — name_en + канонический слаг (сверка стат-блоков EN↔RU).
    align_stat_table_name_en(all_data)

    # Resolve cross-references
    resolve_cross_refs(all_data)
    inject_spell_subclasses(all_data, src_root)

    # Write files and collect hierarchy info
    file_count = 0

    # Validate all parsed entities against JSON Schemas
    if args.no_validate:
        print("  (schema validation skipped: --no-validate)", file=sys.stderr)
    elif jsonschema is None:
        print("  Warning: jsonschema not installed — skipping validation", file=sys.stderr)
    else:
        for (ver, lang, resource), entities in all_data.items():
            schema = RESOURCE_SCHEMAS.get(resource)
            if schema:
                validate_entities(entities, schema, resource, f"{ver}/{lang}")

    # Collectors for hierarchical meta files
    # ver → lang → resource → slugs
    hierarchy: dict[str, dict[str, dict[str, list[str]]]] = {}

    for (ver, lang, resource), entities in sorted(all_data.items()):
        hierarchy.setdefault(ver, {}).setdefault(lang, {})[resource] = []

        slugs = []
        for entity in entities:
            slug = entity["slug"]
            slugs.append(slug)
            if args.individual:
                write_json(system_dir / ver / lang / resource / f"{slug}.json", entity)
                file_count += 1

        slugs.sort()
        hierarchy[ver][lang][resource] = slugs

        # all.json
        write_json(
            system_dir / ver / lang / resource / "all.json",
            sorted(entities, key=lambda e: e["slug"]),
        )
        file_count += 1

    # --- Hierarchical meta.json + index.html files ---

    base_url = "."  # relative links

    # Level 5: /dnd/{ver}/{lang}/{resource}/ — list of slugs
    for ver, langs in sorted(hierarchy.items()):
        for lang, resources in sorted(langs.items()):
            for resource, slugs in sorted(resources.items()):
                res_dir = system_dir / ver / lang / resource
                write_json(res_dir / "meta.json", {
                    "resource": resource,
                    "total": len(slugs),
                    "slugs": slugs,
                })
                file_count += 1

                links = [{"href": "all.json", "label": "all.json", "badge": f"{len(slugs)} items"}]
                if args.individual:
                    for slug in slugs:
                        links.append({"href": f"{slug}.json", "label": slug})
                bc = [
                    {"href": "../../../../", "label": "api"},
                    {"href": "../../../", "label": SYSTEM},
                    {"href": "../../", "label": VERSION_NAMES.get(ver, ver)},
                    {"href": "../", "label": lang},
                    {"href": None, "label": resource},
                ]
                write_index_html(res_dir / "index.html",
                                 f"{resource} — {lang} — {VERSION_NAMES.get(ver, ver)}",
                                 links, bc,
                                 schema=RESOURCE_SCHEMAS.get(resource))
                file_count += 1

    # Level 4: /dnd/{ver}/{lang}/ — available resources
    for ver, langs in sorted(hierarchy.items()):
        for lang, resources in sorted(langs.items()):
            lang_dir = system_dir / ver / lang
            links = []
            for resource, slugs in sorted(resources.items()):
                links.append({"href": f"{resource}/", "label": resource, "badge": str(len(slugs))})

            bc = [
                {"href": "../../../", "label": "api"},
                {"href": "../../", "label": SYSTEM},
                {"href": "../", "label": VERSION_NAMES.get(ver, ver)},
                {"href": None, "label": lang},
            ]
            write_index_html(lang_dir / "index.html",
                             f"{lang} — {VERSION_NAMES.get(ver, ver)}",
                             links, bc)
            file_count += 1

    # Level 3: /dnd/{ver}/ — available languages
    for ver, langs in sorted(hierarchy.items()):
        ver_dir = system_dir / ver
        links = []
        for lang in sorted(langs):
            links.append({"href": f"{lang}/", "label": lang})

        bc = [
            {"href": "../../", "label": "api"},
            {"href": "../", "label": SYSTEM},
            {"href": None, "label": VERSION_NAMES.get(ver, ver)},
        ]
        write_index_html(ver_dir / "index.html",
                         VERSION_NAMES.get(ver, ver),
                         links, bc)
        file_count += 1

    # Level 2: /dnd/ — available versions
    links = []
    for ver in sorted(hierarchy):
        links.append({"href": f"{ver}/", "label": VERSION_NAMES.get(ver, ver)})

    bc = [
        {"href": "../", "label": "api"},
        {"href": None, "label": SYSTEM_NAME},
    ]
    write_index_html(system_dir / "index.html",
                     SYSTEM_NAME,
                     links, bc)
    file_count += 1

    # Level 1: /api/ — available systems
    write_index_html(output_dir / "index.html",
                     "TTRPG SRD API",
                     [{"href": f"{SYSTEM}/", "label": SYSTEM_NAME}])
    file_count += 1

    print(f"\nDone: {file_count} files written ({total_entities} entities)")


if __name__ == "__main__":
    main()
