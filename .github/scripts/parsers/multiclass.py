"""Multiclass rules of a D&D edition for the system descriptor (#481), read from its character creation chapter."""

import re

_PREREQUISITE = re.compile(r"you must have a score of at least (\d+) in the primary ability of the new class")
_ROUNDING = re.compile(r"^- Half your levels \(round(?:ed)? (up|down)\) in the ", re.M)
_TABLE_TITLE = "Table: Multiclass Spellcaster: Spell Slots per Spell Level"


def _one(pattern: re.Pattern, text: str, what: str) -> str:
    found = pattern.findall(text)
    if len(found) != 1:
        raise ValueError(f"multiclass rules: {len(found)} matches for {what}")
    return found[0]


def _slot_table(text: str) -> list[dict]:
    lines = text.split("\n")
    if lines.count(_TABLE_TITLE) != 1:
        raise ValueError(f"multiclass rules: {lines.count(_TABLE_TITLE)} «{_TABLE_TITLE}» tables")
    start = lines.index(_TABLE_TITLE) + 1
    while start < len(lines) and not lines[start].startswith("|"):
        start += 1
    block = []
    for line in lines[start:]:
        if not line.startswith("|"):
            break
        block.append([c.strip() for c in line.strip().strip("|").split("|")])
    header, rows = block[0] if block else [], block[2:]
    if header != ["Level", *map(str, range(1, 10))]:
        raise ValueError(f"multiclass rules: slot table header {header!r}")
    out = []
    for cells in rows:
        if len(cells) != 10 or not all(c == "—" or c.isdigit() for c in cells[1:]):
            raise ValueError(f"multiclass rules: slot table row {cells!r}")
        out.append({"level": int(cells[0]), "spell_slots": [0 if c == "—" else int(c) for c in cells[1:]]})
    if [r["level"] for r in out] != list(range(1, 21)):
        raise ValueError(f"multiclass rules: slot table levels {[r['level'] for r in out]}")
    return out


def parse_multiclass_rules(text: str) -> dict:
    """{prerequisite_score, caster_level_rounding: up | down, spell_slots: 20 rows of {level, spell_slots[9]}}.

    Raises ValueError when a rule is missing, repeated or in an unknown form."""
    return {
        "prerequisite_score": int(_one(_PREREQUISITE, text, "the prerequisite score")),
        "caster_level_rounding": _one(_ROUNDING, text, "the half-caster rounding"),
        "spell_slots": _slot_table(text),
    }
