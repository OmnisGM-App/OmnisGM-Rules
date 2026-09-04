#!/usr/bin/env python3
"""
Layout recovery for merged markdown after PDF extraction.
Fixes structural issues without changing content.

Usage:
    python3 layout_recovery.py <input.md> <output.md>

Fixes applied (in call order):
    0. Rejoin word-per-line output (narrow PDF columns break every word onto its own line)
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


# Доля строк-продолжений, начиная с которой считаем, что документ разорван по словам.
# У здорового markdown отступом начинаются вложенные списки и блоки кода — единицы процентов;
# у разорванного (marker на узкой колонке SRD 5.1) таких строк 89%.
WORD_PER_LINE_RATIO = 0.30
# Продолжение строки — ровно один ведущий пробел и не разметка: список, таблица, заголовок
# или цитата с отступом остаются на своих строках, иначе схлопнется вложенность.
CONTINUATION_RE = re.compile(r"^ (?![ \t])(?![-*+] )(?!\d+[.)] )(?![|#>`])(\S.*)$")
# Хвост формулы кубов — «(18d10\n + \n 36)»: по виду маркер списка, по смыслу продолжение.
# Строка целиком должна выглядеть арифметикой: знак, знак с числом, число со скобкой.
# «- 3 очка действия» под это не подходит и остаётся пунктом списка.
ARITHMETIC_RE = re.compile(r"^ ([-+](?:\s*\d[\d\s]*\)?)?)\s*$")
# Приёмник склейки: к заголовку, строке таблицы, подчёркиванию setext и фенсу не клеим —
# продолжение туда не относится, а разметку это ломает.
NO_APPEND_RE = re.compile(r"^\s*(?:#{1,6}\s|\||```|~~~|=+\s*$|-{3,}\s*$)")


def fix_word_per_line(text):
    """Rejoin lines broken mid-sentence by the converter.

    Узкая колонка PDF (стат-блоки SRD) заставляет marker класть КАЖДОЕ слово на свою
    строку с одним ведущим пробелом: «*Large \n aberration, \n lawful \n evil*».
    Формально markdown валиден и рендерится в один абзац, но такой файл нельзя ни
    сверить построчно, ни разрезать на разделы, ни прочитать глазами в diff.

    Склеиваем только там, где документ разорван целиком (см. WORD_PER_LINE_RATIO) —
    иначе на здоровом файле мы бы съели легитимные отступы.
    """
    lines = text.split("\n")
    nonempty = [l for l in lines if l.strip()]
    if not nonempty:
        return text
    broken = sum(1 for l in nonempty if CONTINUATION_RE.match(l))
    if broken / len(nonempty) < WORD_PER_LINE_RATIO:
        return text

    out, in_fence = [], False
    for line in lines:
        if re.match(r"^\s*(?:```|~~~)", line):
            in_fence = not in_fence
            out.append(line)
            continue
        m = None if in_fence else (CONTINUATION_RE.match(line) or ARITHMETIC_RE.match(line))
        if m and out and out[-1].strip() and not NO_APPEND_RE.match(out[-1]):
            prev, tail = out[-1].rstrip(), m.group(1).strip()
            # Перенос по дефису склеиваем без пробела: иначе «any non-\n lawful» станет
            # «any non- lawful» — слово так и останется битым, но уже внутри строки, где
            # ни глазами, ни fix_hyphen_breaks его больше не найти.
            out[-1] = prev + tail if prev.endswith("-") else prev + " " + tail
            stats["word_per_line"] += 1
        else:
            out.append(line)
    return "\n".join(out)


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

    # Склейка — первой: остальные правила построчные и на разорванном тексте слепы.
    text = fix_word_per_line(text)
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
