#!/usr/bin/env python3
"""
Extract entities from SRD markdown files for glossary building.

Usage:
    python3 extract_entities.py <en_directory>

Scans all .md files (excluding *_Glossary/) and extracts:
- H4 headings (####) — spells, magic items, feats
- H2 headings (##) in monster/animal files — creatures
- Stat block metadata (CR, type, size) from blockquote format

Output: JSON to stdout with entity lists by source file.
"""

import json
import re
import sys
from pathlib import Path


def extract_from_file(filepath: Path) -> dict:
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")
    name = filepath.name

    result = {
        "file": name,
        "h1": [],
        "h2": [],
        "h3": [],
        "h4": [],
        "tables": 0,
        "blockquotes": 0,
        "lines": len(lines),
    }

    for line in lines:
        if line.startswith("#### "):
            result["h4"].append(line[5:].strip().rstrip(" #"))
        elif line.startswith("### "):
            result["h3"].append(line[4:].strip().rstrip(" #"))
        elif line.startswith("## "):
            result["h2"].append(line[3:].strip().rstrip(" #"))
        elif line.startswith("# "):
            result["h1"].append(line[2:].strip().rstrip(" #"))
        elif line.startswith("|"):
            result["tables"] += 1
        elif line.startswith(">"):
            result["blockquotes"] += 1

    return result


# Sub-headings that sit at spell/entity heading depth but are NOT entities.
NON_ENTITY_HEADING = re.compile(
    r"Using a Higher-Level Spell Slot|Использование ячейки", re.IGNORECASE
)


def entity_headings(data: dict) -> tuple:
    """Pick the dominant heading level (### or ####) as the entity level.

    Different conversion runs emit spells/items at ### or #### inconsistently. A
    hard-coded level silently drops entities when a run picks the other depth — that
    is how an earlier run lost every cantrip from the glossary index. Choosing the
    denser of the two levels (after removing known non-entity sub-headers such as
    "Using a Higher-Level Spell Slot") adapts to either style. Returns
    (entities, ambiguous) where ambiguous flags a mixed ###/#### structure worth a
    manual look.
    """
    h3 = [h for h in data["h3"] if not NON_ENTITY_HEADING.search(h)]
    h4 = [h for h in data["h4"] if not NON_ENTITY_HEADING.search(h)]
    entities = h3 if len(h3) >= len(h4) else h4
    # Warn only when BOTH depths hold many headings — a real risk that one whole tier
    # (e.g. cantrips at ### while leveled spells are at ####) is about to be dropped.
    # A handful of intro sub-headers (Spell Slots, Verbal (V), Targets…) must not warn.
    # The authoritative guard against a dropped tier is the index↔chapter count
    # cross-check in /validate-markdown, not this heuristic.
    ambiguous = min(len(h3), len(h4)) >= 20
    return entities, ambiguous


def classify_file(data: dict) -> str:
    """Guess entity type based on file structure."""
    name = data["file"].lower()
    h4_count = len(data["h4"])
    h2_count = len(data["h2"])
    bq = data["blockquotes"]

    if "spell" in name:
        return "spells"
    if "monster" in name and h2_count > 10:
        return "monsters"
    if "animal" in name and h2_count > 10:
        return "animals"
    if "magic" in name or "item" in name:
        return "magic_items"
    if "feat" in name:
        return "feats"
    if "equipment" in name:
        return "equipment"
    if h2_count > 20 and bq > 50:
        return "creatures"  # stat blocks
    if h4_count > 20:
        return "entities"
    return "content"


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <en_directory>", file=sys.stderr)
        sys.exit(1)

    en_dir = Path(sys.argv[1])
    if not en_dir.is_dir():
        print(f"Error: {en_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    files = sorted(f for f in en_dir.rglob("*.md") if "_Glossary" not in str(f))

    results = []
    summary = {"total_files": len(files), "entities": {}}

    for f in files:
        data = extract_from_file(f)
        entity_type = classify_file(data)
        data["entity_type"] = entity_type

        # Count entities
        if entity_type in ("spells", "feats", "magic_items", "equipment"):
            entities, ambiguous = entity_headings(data)
            count = len(entities)
            if ambiguous:
                print(
                    f"  WARNING: {data['file']} mixes ### and #### headings — "
                    f"verify no entity tier (e.g. cantrips) was dropped",
                    file=sys.stderr,
                )
        elif entity_type in ("monsters", "animals", "creatures"):
            count = len(data["h2"])
            entities = data["h2"]
        else:
            count = 0
            entities = []

        data["entity_count"] = count
        results.append(data)

        if entity_type != "content":
            if entity_type not in summary["entities"]:
                summary["entities"][entity_type] = {"count": 0, "files": []}
            summary["entities"][entity_type]["count"] += count
            summary["entities"][entity_type]["files"].append(data["file"])

    # Print summary to stderr
    print(f"\nScanned {len(files)} files:", file=sys.stderr)
    for etype, info in sorted(summary["entities"].items()):
        print(f"  {etype}: {info['count']} entities from {', '.join(info['files'])}", file=sys.stderr)

    total = sum(info["count"] for info in summary["entities"].values())
    print(f"  Total entities: {total}", file=sys.stderr)

    # Print full JSON to stdout
    output = {"summary": summary, "files": results}
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
