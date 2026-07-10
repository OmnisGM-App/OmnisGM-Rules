#!/usr/bin/env python3
"""
Layout recovery for merged markdown after PDF extraction.
Fixes structural issues without changing content.

Usage:
    python3 layout_recovery.py <input.md> <output.md>

Fixes applied:
    1. Remove **bold** markers from # headings
    2. Convert <br> line-break artifacts from PDF (join broken words / spaces)
    3. Join hyphenated word breaks across lines (word-\\nrest → word-rest)
    4. Join split spell components/craft/utilize lines
    5. Split glued stat-block fields (**Casting Time:** X **Range:** Y → one per line)
    6. Clean trailing empty table columns
"""

import re
import sys
from collections import Counter

stats = Counter()


def fix_bold_headers(text):
    """Remove **bold** markers from # headings. Handles both full-line and partial bold."""
    def replace_bold_header(m):
        stats['bold_headers'] += 1
        heading_prefix = m.group(1)
        heading_content = m.group(2)
        cleaned = re.sub(r'\*\*(.+?)\*\*', r'\1', heading_content)
        return heading_prefix + cleaned
    return re.sub(r'^(#{1,6}\s+)(.*\*\*.+?\*\*.*)$', replace_bold_header, text, flags=re.MULTILINE)


def fix_hyphen_breaks(text):
    """Join words split with hyphen across lines (e.g., royalty-\\nfree → royalty-free)."""
    lines = text.split('\n')
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Pattern: line ends with letter-hyphen, next non-empty line starts with lowercase
        if (i + 1 < len(lines) and
                re.search(r'[a-zA-Z]-$', line)):
            # Find next non-empty line
            j = i + 1
            while j < len(lines) and lines[j].strip() == '':
                j += 1
            if j < len(lines) and re.match(r'^[a-z]', lines[j]):
                result.append(line[:-1] + lines[j])
                stats['hyphen_breaks'] += 1
                # Skip empty lines between and the continuation line
                i = j + 1
                continue
        result.append(line)
        i += 1
    return '\n'.join(result)


def fix_split_components(text):
    """Join split **Components:**/Craft:/Utilize:/Variants: lines back to previous line."""
    lines = text.split('\n')
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if (i + 1 < len(lines) and
                re.match(r'^\*\*(Components|Craft|Utilize|Variants):\*\*', lines[i + 1])):
            # Check if current line looks like it should continue
            if line.strip() and not line.startswith('#'):
                result.append(line + ' ' + lines[i + 1])
                stats['split_components'] += 1
                i += 2
                continue
        result.append(line)
        i += 1
    return '\n'.join(result)


def fix_br_artifacts(text):
    """Convert <br> line-break artifacts left by PDF extraction.

    Canon markdown must contain no raw <br>. PDF column/line wrapping leaks them:
      - inside prose a break usually splits one word (charac<br>ter → character)
      - inside table cells it wraps a multi-word value (Slot<br>Level → Slot Level,
        7<br>Wis → 7 Wis, Finesse<br>or Light → Finesse or Light)

    Heuristic by context:
      - table lines (start with `|`): every <br> → single space (wrapped value)
      - prose lines: letter directly followed by a lowercase letter → join without
        space (broken word); otherwise → single space (e.g. Save<br>DC → Save DC)
    """
    # Case-sensitive letter classes (tag itself matched case-insensitively via [bB][rR]):
    # only a lowercase letter after the break signals a split word — Save<br>DC stays "Save DC".
    word_join = re.compile(r'([A-Za-zА-Яа-яЁё])<[bB][rR]\s*/?>([a-zа-яё])')
    any_br = re.compile(r'\s*<br\s*/?>\s*', re.IGNORECASE)
    count_br = re.compile(r'<br\s*/?>', re.IGNORECASE)

    result = []
    for line in text.split('\n'):
        n = len(count_br.findall(line))
        if n == 0:
            result.append(line)
            continue
        if line.lstrip().startswith('|'):
            line = any_br.sub(' ', line)
            stats['br_table'] += n
        else:
            line, joined = word_join.subn(r'\1\2', line)
            line = any_br.sub(' ', line)
            stats['br_wordjoin'] += joined
            stats['br_space'] += n - joined
        result.append(line)
    return '\n'.join(result)


def fix_glued_fields(text):
    """Split stat-block lines that glue several **Label:** fields onto one line.

    A two-column PDF layout produces lines like
        **Casting Time:** Action **Range:** 90 feet
        **Components:** V, S **Duration:** Instantaneous
    Canon style keeps one field per line (blank-separated). Only lines that BEGIN
    with a bold label and hold 2+ such labels (and are not table rows) are split, so
    ordinary prose with a single inline **word:** is untouched.
    """
    lead = re.compile(r'^\*\*[^*\n]+?:\*\*')
    label = re.compile(r'\*\*[^*\n]+?:\*\*')
    result = []
    for line in text.split('\n'):
        if '|' not in line and lead.match(line):
            starts = [m.start() for m in label.finditer(line)]
            if len(starts) >= 2:
                parts = [
                    line[starts[k]:(starts[k + 1] if k + 1 < len(starts) else len(line))].strip()
                    for k in range(len(starts))
                ]
                result.append('\n\n'.join(parts))
                stats['glued_fields'] += len(parts) - 1
                continue
        result.append(line)
    return '\n'.join(result)


def fix_trailing_empty_columns(text):
    """Remove trailing empty columns from table rows (|  |  | at end)."""
    def clean_row(m):
        row = m.group(0)
        cleaned = re.sub(r'(\|\s*){2,}$', '|', row)
        if cleaned != row:
            stats['trailing_columns'] += 1
        return cleaned
    return re.sub(r'^\|.*\|$', clean_row, text, flags=re.MULTILINE)


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.md> <output.md>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()

    original_lines = text.count('\n')

    text = fix_bold_headers(text)
    text = fix_br_artifacts(text)
    text = fix_hyphen_breaks(text)
    text = fix_split_components(text)
    text = fix_glued_fields(text)
    text = fix_trailing_empty_columns(text)

    result_lines = text.count('\n')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)

    print(f"Layout recovery complete: {input_path} → {output_path}")
    print(f"Lines: {original_lines} → {result_lines} ({result_lines - original_lines:+d})")
    print(f"Fixes:")
    for key, count in sorted(stats.items()):
        print(f"  {key}: {count}")


if __name__ == '__main__':
    main()
