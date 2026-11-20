#!/usr/bin/env python3
"""Гейт разбора Rules Glossary SRD 5.2: каждый заголовок `####` попадает ровно в один ресурс API.

Термин с тегом, которого нет ни у одного источника `config.py`, молча выпадал из API:
`parse_untagged_defs` пропускает любой тег, а `parse_tagged_defs` берёт только названные.

Запуск: python3 .github/scripts/test_glossary_tags.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import SOURCES  # noqa: E402

ROOT = Path(__file__).resolve().parents[2] / "src" / "dnd"
CONDITION_TAGS = {"en": "Condition", "ru": "Состояние"}
failures = []


def tags_in(text: str) -> dict[str, int]:
    found: dict[str, int] = {}
    for heading in re.findall(r"^#### (.+)$", text, flags=re.M):
        m = re.search(r"\[([^\]]+)\]\s*$", heading.strip())
        if m:
            found[m.group(1)] = found.get(m.group(1), 0) + 1
    return found


for lang in ("en", "ru"):
    file = f"srd-5.2/{lang}/08_RulesGlossary.md"
    sources = [s for s in SOURCES if s.get("ver") == "srd52" and s.get("lang") == lang and s.get("file") == file]
    claimed: dict[str, list[str]] = {}
    for s in sources:
        if s["type"] == "tagged_defs":
            for tag in s["tags"]:
                claimed.setdefault(tag, []).append(s["out"])
        elif s["type"] == "condition":
            claimed.setdefault(CONDITION_TAGS[lang], []).append("conditions")
    if sum(s["type"] == "untagged_defs" for s in sources) != 1:
        failures.append(f"{lang}: expected one untagged_defs source of {file}")
    found = tags_in((ROOT / file).read_text(encoding="utf-8"))
    if not found:
        failures.append(f"{lang}: no tagged heading found in {file}")
    for tag, count in sorted(found.items()):
        outs = claimed.get(tag, [])
        if len(outs) != 1:
            failures.append(f"{lang}: tag [{tag}] ({count} headings) goes to {outs or 'no resource'}")
    for tag in sorted(set(claimed) - set(found)):
        failures.append(f"{lang}: config names tag [{tag}] that {file} does not have")

if failures:
    print("\n".join(failures))
    sys.exit(1)
print("glossary tags: every tagged heading of SRD 5.2 has one resource")
