#!/usr/bin/env python3
"""
Automated markdown structure checks for imported SRD files.
Catches mechanical issues before the agent does semantic review.

Usage:
    python3 check_markdown.py <directory>
    python3 check_markdown.py <file.md>

Checks:
    - Broken tables (unequal | count in rows)
    - Unclosed bold/italic markers
    - Broken blockquotes (> lines followed by non-> non-empty lines)
    - Files not starting with # heading
    - Heading hierarchy gaps (#### without ### above)
    - Empty files
"""

import re
import sys
from pathlib import Path


def check_file(filepath: Path) -> list:
    issues = []
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")
    name = filepath.name

    # Empty file
    if not text.strip():
        issues.append({"file": name, "line": 0, "type": "empty_file", "msg": "File is empty"})
        return issues

    # File doesn't start with # heading
    first_content = next((l for l in lines if l.strip()), "")
    if not first_content.startswith("#"):
        issues.append({"file": name, "line": 1, "type": "no_heading", "msg": f"File doesn't start with # heading: '{first_content[:50]}'"})

    # Check each line
    in_code_block = False
    table_context = {"in_table": False, "col_count": 0, "start_line": 0}
    last_heading_level = 0

    for i, line in enumerate(lines, 1):
        # Code block tracking
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Table checks
        if line.startswith("|"):
            col_count = line.count("|")
            if not table_context["in_table"]:
                table_context = {"in_table": True, "col_count": col_count, "start_line": i}
            elif col_count != table_context["col_count"]:
                # Skip separator rows like |---|---|
                if not re.match(r"^\|[\s\-:|]+\|$", line):
                    issues.append({
                        "file": name, "line": i, "type": "broken_table",
                        "msg": f"Table column count mismatch: expected {table_context['col_count']}, got {col_count}"
                    })
        else:
            table_context["in_table"] = False

        # Heading hierarchy
        heading_match = re.match(r"^(#{1,6})\s", line)
        if heading_match:
            level = len(heading_match.group(1))
            gap = level - last_heading_level
            # Skip 1 level (## → ####) is common in TTRPG SRDs — only warn on skip 2+
            if gap > 2 and last_heading_level > 0:
                issues.append({
                    "file": name, "line": i, "type": "heading_gap",
                    "msg": f"Heading level jump: {'#' * last_heading_level} → {'#' * level} (skipped {gap - 1} levels)"
                })
            last_heading_level = level

        # Unclosed bold/italic. Guards against known false positives:
        # `- `/`* ` list markers, escaped \*, inline-code spans (`**kwargs`),
        # isolated * with spaces both sides (a * b), horizontal rules.
        if line.startswith("|") or re.match(r"^\s*(\*{3,}|-{3,}|_{3,})\s*$", line):
            continue
        prose = re.sub(r"^\s*(?:[-*+]|\d+\.)\s+", "", line).replace("\\*", "")
        prose = re.sub(r"`[^`]*`", "", prose)
        prose = re.sub(r"(?:(?<=\s)|^)\*{1,2}(?=\s|$)", "", prose)
        bold_count = prose.count("**")
        if bold_count % 2 != 0:
            issues.append({
                "file": name, "line": i, "type": "unclosed_bold",
                "msg": f"Possible unclosed bold marker: {line[:80]}"
            })
        elif prose.replace("**", "").count("*") % 2 != 0:
            issues.append({
                "file": name, "line": i, "type": "unclosed_italic",
                "msg": f"Possible unclosed italic marker: {line[:80]}"
            })

    # Broken blockquote: a non-empty line without `>` sandwiched between `>` lines
    in_code = set()
    fenced = False
    for idx, l in enumerate(lines):
        if l.strip().startswith("```"):
            in_code.add(idx)
            fenced = not fenced
        elif fenced:
            in_code.add(idx)
    for idx in range(1, len(lines) - 1):
        if idx in in_code:
            continue
        cur = lines[idx]
        if (cur.strip() and not cur.lstrip().startswith(">")
                and lines[idx - 1].lstrip().startswith(">")
                and lines[idx + 1].lstrip().startswith(">")):
            issues.append({
                "file": name, "line": idx + 1, "type": "broken_blockquote",
                "msg": f"Non-quoted line inside blockquote: {cur[:80]}"
            })

    return issues


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <directory|file.md>")
        sys.exit(1)

    target = Path(sys.argv[1])

    if target.is_dir():
        files = sorted(target.rglob("*.md"))
        if not files:
            print(f"No .md files found in {target}")
            sys.exit(1)
    elif target.is_file():
        files = [target]
    else:
        print(f"Error: {target} not found")
        sys.exit(1)

    all_issues = []
    for f in files:
        issues = check_file(f)
        all_issues.extend(issues)

    if all_issues:
        print(f"Found {len(all_issues)} issue(s) in {len(files)} file(s):\n")
        for issue in all_issues:
            severity = "ERROR" if issue["type"] in ("broken_table", "empty_file", "no_heading") else "WARNING"
            print(f"  [{severity}] {issue['file']}:{issue['line']} — {issue['type']}: {issue['msg']}")
        print(f"\nTotal: {len(all_issues)} issues")
        sys.exit(1)
    else:
        print(f"All {len(files)} files passed structural checks. 0 issues.")
        sys.exit(0)


if __name__ == "__main__":
    main()
