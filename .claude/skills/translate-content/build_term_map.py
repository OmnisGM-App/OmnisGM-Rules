#!/usr/bin/env python3
"""Build a {EN: RU} term map from translate/ dictionaries and logs.

Usage:
    python3 build_term_map.py <game> <version>
    python3 build_term_map.py --game dnd --version srd-5.2 [--src src] [--out PATH]

Sources, from lowest to highest priority (later overrides earlier) — the ladder
from .claude/rules/translate-dictionaries.md:

    src/{game}/translate/02+_dictionary_*.md    entity dictionaries
    src/translate/01_dictionary_base.md         common base dictionary
    src/{game}/translate/01_dictionary_base.md  system base dictionary
    src/translate/logs/*.md                     common logs (latest date wins)
    src/{game}/translate/logs/*.md              system logs (absolute priority)

A log record `### EN → RU` overrides the dictionaries; among logs the latest date
wins. Table columns: `Оригинал*` → EN key, `Перевод*` → RU value. The
multiversion format (D&D) carries several `Оригинал {version}` columns — the
current {version} column is the primary key, other versions are kept as aliases.

Output: /tmp/{game}_{version}_term_map.json
    {"terms": {EN: RU}, "sources": {label: count}, "conflicts": [...]}
Exit 1 if no dictionaries are found.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

# Priority tiers, lowest to highest. The master map applies them in this order,
# so a later tier overrides an earlier one for the same EN key.
ENTITY_DICTS = "system_entity_dicts"
COMMON_BASE = "common_base_dict"
SYSTEM_BASE = "system_base_dict"
COMMON_LOGS = "common_logs"
SYSTEM_LOGS = "system_logs"
LOG_TIERS = (COMMON_LOGS, SYSTEM_LOGS)

_SEP_CELL = re.compile(r"^:?-+:?$")
_LOG_HEADER = re.compile(r"^###\s+(.*?)\s*(?:→|->)\s*(.*?)\s*$")
_TRAILING_PAREN = re.compile(r"\s*\([^)]*\)\s*$")
_LOG_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
# A cell that is empty or only dash characters marks "term absent in this version".
_ABSENT = re.compile(r"^[-–—]*$")


def version_number(version: str) -> str:
    """`srd-5.2` → `5.2`; a bare `5.2` stays `5.2`."""
    return version[4:] if version.startswith("srd-") else version


def split_row(line: str) -> list:
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def is_separator(line: str) -> bool:
    cells = split_row(line)
    return bool(cells) and all(_SEP_CELL.match(c) for c in cells)


def iter_tables(text: str):
    """Yield (headers, rows) for each GitHub-style pipe table."""
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if (
            line.lstrip().startswith("|")
            and i + 1 < len(lines)
            and is_separator(lines[i + 1])
        ):
            headers = split_row(line)
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                rows.append(split_row(lines[j]))
                j += 1
            yield headers, rows
            i = j
        else:
            i += 1


def _pick_versioned(cols: list, headers: list, ver_num: str) -> int:
    """Column matching the current version (`… 5.2`), else the first candidate."""
    for idx in cols:
        if headers[idx].split()[-1] == ver_num:
            return idx
    return cols[0]


def terms_from_table(headers: list, rows: list, ver_num: str):
    orig_cols = [i for i, h in enumerate(headers) if h.startswith("Оригинал")]
    perevod_cols = [i for i, h in enumerate(headers) if h.startswith("Перевод")]
    if not orig_cols or not perevod_cols:
        return
    ru_idx = _pick_versioned(perevod_cols, headers, ver_num)
    primary = _pick_versioned(orig_cols, headers, ver_num)
    ordered = [primary] + [c for c in orig_cols if c != primary]
    for row in rows:
        if ru_idx >= len(row):
            continue
        ru = row[ru_idx]
        if _ABSENT.match(ru):
            continue
        for c in ordered:
            if c < len(row):
                en = row[c]
                if not _ABSENT.match(en):
                    yield en, ru


def terms_from_dict_file(path: Path, ver_num: str):
    text = path.read_text(encoding="utf-8")
    for headers, rows in iter_tables(text):
        yield from terms_from_table(headers, rows, ver_num)


def _clean_term(s: str) -> str:
    return _TRAILING_PAREN.sub("", s).strip()


def terms_from_log_line(left: str, right: str):
    """A `### EN → RU` header, splitting balanced `A/B → X/Y` compounds."""
    left, right = _clean_term(left), _clean_term(right)
    if not left or not right:
        return
    if "/" in left and "/" in right:
        ls, rs = left.split("/"), right.split("/")
        if len(ls) == len(rs):
            for en, ru in zip(ls, rs):
                en, ru = en.strip(), ru.strip()
                if en and ru:
                    yield en, ru
            return
    # An EN term is a short noun phrase, not a sentence — guards against a prose
    # header that happens to contain an arrow.
    if len(left) <= 60:
        yield left, right


def terms_from_log_file(path: Path):
    for line in path.read_text(encoding="utf-8").split("\n"):
        m = _LOG_HEADER.match(line)
        if m:
            yield from terms_from_log_line(m.group(1), m.group(2))


def log_files_sorted(log_dir: Path) -> list:
    """Log files oldest → newest by the date in the filename."""
    if not log_dir.is_dir():
        return []
    files = [f for f in log_dir.glob("*.md")]

    def key(f):
        m = _LOG_DATE.search(f.name)
        return (m.group(1) if m else "", f.name)

    return sorted(files, key=key)


def aggregate_dict_tier(files: list, ver_num: str, conflicts: list, label: str):
    """Merge one dictionary tier; same EN → different RU within it is a conflict."""
    tier = {}
    seen = set()  # один и тот же конфликт из повторяющихся строк — один раз
    for path in files:
        for en, ru in terms_from_dict_file(path, ver_num):
            if en in tier and tier[en] != ru:
                key = (label, en, frozenset((tier[en], ru)))
                if key not in seen:
                    seen.add(key)
                    conflicts.append(
                        {"term": en, "tier": label, "values": [tier[en], ru]}
                    )
                continue
            tier.setdefault(en, ru)
    return tier


def aggregate_log_tier(files: list):
    """Merge one log tier chronologically — later date/record wins (a revision,
    not a conflict)."""
    tier = {}
    for path in files:
        for en, ru in terms_from_log_file(path):
            tier[en] = ru
    return tier


def build(game: str, version: str, src: Path):
    ver_num = version_number(version)
    game_tr = src / game / "translate"
    common_tr = src / "translate"

    entity_files = sorted(
        # [0-9]*, а не 0* — иначе 10_dictionary_*.md молча выпадет из карты
        f for f in game_tr.glob("[0-9]*_dictionary_*.md")
        if not f.name.startswith("01_")
    )
    system_base = [f for f in [game_tr / "01_dictionary_base.md"] if f.is_file()]
    common_base = [f for f in [common_tr / "01_dictionary_base.md"] if f.is_file()]
    common_log_files = log_files_sorted(common_tr / "logs")
    system_log_files = log_files_sorted(game_tr / "logs")

    # The common base alone is not a game dictionary — require the game's own dicts.
    if not (entity_files or system_base):
        return None

    conflicts = []
    # Ascending priority — order matters, later tiers overwrite earlier ones.
    tiers = [
        (ENTITY_DICTS, aggregate_dict_tier(entity_files, ver_num, conflicts, ENTITY_DICTS)),
        (COMMON_BASE, aggregate_dict_tier(common_base, ver_num, conflicts, COMMON_BASE)),
        (SYSTEM_BASE, aggregate_dict_tier(system_base, ver_num, conflicts, SYSTEM_BASE)),
        (COMMON_LOGS, aggregate_log_tier(common_log_files)),
        (SYSTEM_LOGS, aggregate_log_tier(system_log_files)),
    ]

    terms = {}
    source_of = {}
    dict_snapshot = {}
    # Перекрытия МЕЖДУ тирами словарей: внутри тира это конфликт, а между тирами —
    # штатный приоритет, и до сих пор оно нигде не показывалось. Ровно так подтипы,
    # положенные в общий словарь, молча перекрыли бы переводы сущностей (#256).
    cross_tier = []
    for label, tier in tiers:
        if label == COMMON_LOGS:
            dict_snapshot = dict(terms)  # freeze dictionary-only state before logs
        for en, ru in tier.items():
            if en in terms and terms[en] != ru and label not in LOG_TIERS:
                cross_tier.append({"term": en, "from": source_of.get(en), "to": label,
                                   "values": [terms[en], ru]})
            terms[en] = ru
            source_of[en] = label

    overridden_by_logs = sorted(
        en
        for en, src_label in source_of.items()
        if src_label in LOG_TIERS
        and en in dict_snapshot
        and dict_snapshot[en] != terms[en]
    )

    # Алиасы без скобочного хвоста: «Armor Class (AC)» → также «Armor Class»,
    # чтобы потребитель по голому ключу не решил, что термина в словаре нет.
    # setdefault: явная словарная запись всегда побеждает алиас.
    paren = re.compile(r"^(.+?)\s*\([^)]*\)$")
    aliases = 0
    for en in list(terms):
        m = paren.match(en)
        if m and m.group(1) not in terms:
            terms[m.group(1)] = terms[en]
            source_of[m.group(1)] = source_of[en]
            aliases += 1

    counts = Counter(source_of.values())
    files_read = (
        entity_files + common_base + system_base + common_log_files + system_log_files
    )
    result = {
        "game": game,
        "version": version,
        "terms": dict(sorted(terms.items())),
        "sources": {label: counts.get(label, 0) for label, _ in tiers},
        "aliases": aliases,
        "conflicts": conflicts,
        # Термины, для которых запись лога перебила словарь, и перекрытия между тирами
        # словарей — то и другое читает гейт `.github/scripts/test_term_map.py`.
        "overridden_by_logs": overridden_by_logs,
        "cross_tier_overrides": cross_tier,
        # Ключи, пришедшие ИЗ ЛОГОВ: заголовок записи лога — самое лёгкое место, где в
        # карту попадает не термин, а фраза.
        "log_terms": sorted(en for en, lbl in source_of.items() if lbl in LOG_TIERS),
    }
    return result, files_read, overridden_by_logs


def main():
    ap = argparse.ArgumentParser(description="Build a {EN: RU} term map.")
    ap.add_argument("game", nargs="?", help="game slug, e.g. dnd")
    ap.add_argument("version", nargs="?", help="version, e.g. srd-5.2")
    ap.add_argument("--game", dest="game_opt")
    ap.add_argument("--version", dest="version_opt")
    ap.add_argument("--src", default="src", help="src root (default: src)")
    ap.add_argument("--out", help="output JSON path")
    args = ap.parse_args()

    game = args.game_opt or args.game
    version = args.version_opt or args.version
    if not game or not version:
        ap.error("game and version are required")

    src = Path(args.src)
    built = build(game, version, src)
    if built is None:
        print(
            f"Словари не найдены в {src}/{game}/translate/ и {src}/translate/",
            file=sys.stderr,
        )
        sys.exit(1)

    result, files_read, overridden = built
    out = Path(args.out) if args.out else Path(f"/tmp/{game}_{version}_term_map.json")
    out.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    n_terms = len(result["terms"])
    n_files = len(files_read)
    n_conflicts = len(result["conflicts"])
    print(
        f"{n_terms} терминов из {n_files} файлов "
        f"(в т.ч. {result['aliases']} алиасов без скобок), "
        f"{len(overridden)} переопределено логами, конфликты: {n_conflicts}"
    )
    print(f"JSON: {out}")
    for label, count in result["sources"].items():
        print(f"  {label}: {count}")
    if n_conflicts:
        print("Конфликты (один EN → разные RU в источниках одного приоритета):")
        for c in result["conflicts"]:
            print(f"  [{c['tier']}] {c['term']}: {' | '.join(c['values'])}")


if __name__ == "__main__":
    main()
