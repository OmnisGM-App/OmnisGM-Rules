#!/usr/bin/env python3
"""
Deterministic markdown structure validator for the SRD import/translation pipeline.

Usage:
    python3 validate_markdown.py <path> [<path> ...]
    python3 validate_markdown.py --pair <en_dir> <ru_dir>
    python3 validate_markdown.py --glossary-index <index.md> --chapter <chapter.md>
    python3 validate_markdown.py <path> --fix

Runs the checks that need no human judgement — table shape, heading hierarchy,
unbalanced **/*/`/[](), whitespace noise, EN<->RU structural parity, glossary index
coverage — and prints one line per finding as `file:line — категория: описание`.

Exit code: 0 when clean, 1 when any error/warning is reported. Note-level
findings (typography suggestions, bare `[Tag]` references, trailing whitespace)
are printed but do not affect the exit code — released SRD text legitimately
contains bracketed rule tags and long-dash variants.

Parity exception: files named `00_Legal*` are excluded from EN<->RU structural
parity — the RU legal notice legitimately diverges (translation addendum).

--fix applies only the context-free repairs (trailing whitespace, 3+ blank lines
collapsed to 2, missing space after `#`). Everything else is left for a human /
the LLM because the fix needs context the script does not have.
"""

import argparse
import re
import sys
from pathlib import Path

# Categories (Russian, shown in output).
CAT_TABLE = "таблицы"
CAT_HEADING = "заголовки"
CAT_FORMAT = "форматирование"
CAT_SPACE = "пробелы"
CAT_PARITY = "паритет"
CAT_INDEX = "индекс"
CAT_PAIR = "пары"

ERROR, WARNING, NOTE = "error", "warning", "note"


class Finding:
    __slots__ = ("file", "line", "category", "severity", "message")

    def __init__(self, file, line, category, severity, message):
        self.file = file
        self.line = line
        self.category = category
        self.severity = severity
        self.message = message

    def format(self):
        return f"{self.file}:{self.line} — {self.category}: {self.message}"


# --- shared helpers ---------------------------------------------------------


HEADING_RE = re.compile(r"^(#{1,6})\s+\S")
NOSPACE_HEADING_RE = re.compile(r"^#{1,6}[^\s#]")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
LIST_ITEM_RE = re.compile(r"^\s*([-*+]\s+\S|\d+\.\s+\S)")


HTML_BLOCK_OPEN_RE = re.compile(r"<(style|script)\b", re.IGNORECASE)
HTML_BLOCK_CLOSE_RE = re.compile(r"</(style|script)>", re.IGNORECASE)


def code_fence_mask(lines):
    """Line indices inside fenced code blocks or raw <style>/<script> HTML."""
    inside = set()
    fenced = False
    html_block = False
    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            inside.add(i)  # the fence line itself is not prose either
            fenced = not fenced
            continue
        if fenced:
            inside.add(i)
            continue
        if html_block:
            inside.add(i)
            if HTML_BLOCK_CLOSE_RE.search(line):
                html_block = False
            continue
        if HTML_BLOCK_OPEN_RE.search(line):
            inside.add(i)
            if not HTML_BLOCK_CLOSE_RE.search(line):
                html_block = True
    return inside


def strip_blockquote(line):
    """Stat blocks embed tables inside blockquotes (`> | Str | ... |`)."""
    s = line.strip()
    while s.startswith(">"):
        s = s[1:].lstrip()
    return s


def is_table_row(line):
    return strip_blockquote(line).startswith("|")


def table_columns(row):
    s = strip_blockquote(row)
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return len(re.split(r"(?<!\\)\|", s))


def is_separator_row(row):
    s = strip_blockquote(row)
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    cells = re.split(r"(?<!\\)\|", s)
    return all(re.fullmatch(r"\s*:?-+:?\s*", c) for c in cells)


# --- per-file checks --------------------------------------------------------


def check_tables(name, lines, in_code, findings):
    """Group consecutive table rows into blocks and validate each block."""
    i = 0
    n = len(lines)
    prev_block_proper = False
    prev_block_end = -10
    while i < n:
        if not is_table_row(lines[i]) or i in in_code:
            i += 1
            continue
        start = i
        while i < n and is_table_row(lines[i]) and i not in in_code:
            i += 1
        block = list(range(start, i))  # line indices of this block

        header_cols = table_columns(lines[start])
        has_sep = len(block) >= 2 and is_separator_row(lines[block[1]])

        if not has_sep:
            # A table block with no separator on its second row is either a broken
            # (blank-split) continuation of the previous table, or a table missing
            # its `|---|` divider.
            only_blanks = all(lines[k].strip() == "" for k in range(prev_block_end + 1, start))
            if prev_block_proper and only_blanks and prev_block_end >= 0:
                findings.append(Finding(
                    name, start + 1, CAT_TABLE, WARNING,
                    "таблица разорвана пустой строкой (продолжение предыдущей таблицы)",
                ))
            else:
                findings.append(Finding(
                    name, start + 1, CAT_TABLE, ERROR,
                    "отсутствует разделительная строка `|---|` после заголовка",
                ))
            prev_block_proper = False
            prev_block_end = block[-1]
            continue

        # Proper table: every row (incl. separator) must match the header width.
        for k in block:
            cols = table_columns(lines[k])
            if cols != header_cols:
                findings.append(Finding(
                    name, k + 1, CAT_TABLE, ERROR,
                    f"строка имеет {cols} колонок, заголовок — {header_cols}",
                ))
        prev_block_proper = True
        prev_block_end = block[-1]


def check_headings(name, lines, in_code, findings):
    prev_level = None
    prev_text = None
    first_heading_seen = False
    for i, line in enumerate(lines):
        if i in in_code:
            continue
        if NOSPACE_HEADING_RE.match(line):
            hashes = len(line) - len(line.lstrip("#"))
            findings.append(Finding(
                name, i + 1, CAT_HEADING, WARNING,
                f"нет пробела после `{'#' * hashes}`",
            ))
            continue
        m = HEADING_RE.match(line)
        if not m:
            continue
        level = len(m.group(1))
        text = line.strip().lstrip("#").strip()

        if not first_heading_seen:
            first_heading_seen = True
            if level != 1:
                findings.append(Finding(
                    name, i + 1, CAT_HEADING, NOTE,
                    f"файл начинается с заголовка уровня {level}, а не `#`",
                ))
        elif level > prev_level + 1:
            # Выпущенный канон (5.1) намеренно использует прыжки уровней в
            # stat-блоках — note; потерю уровня в RU ловит паритет по уровням.
            findings.append(Finding(
                name, i + 1, CAT_HEADING, NOTE,
                f"прыжок уровня: `{'#' * level}` после `{'#' * prev_level}` "
                f"(пропущено {level - prev_level - 1})",
            ))

        # Missing blank line before a heading — but back-to-back headings are a
        # separate (deliberate) shape, so only flag when real content precedes.
        if i > 0:
            prev = lines[i - 1]
            if prev.strip() != "" and not HEADING_RE.match(prev):
                findings.append(Finding(
                    name, i + 1, CAT_HEADING, NOTE,
                    "нет пустой строки перед заголовком",
                ))

        if prev_text is not None and text == prev_text and level == prev_level:
            findings.append(Finding(
                name, i + 1, CAT_HEADING, NOTE,
                f"дублирующийся заголовок подряд: `{text}`",
            ))
        prev_level = level
        prev_text = text


LINK_RE = re.compile(r"(?<!\!)\[([^\]]*)\]")
LIST_MARKER_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")
HR_RE = re.compile(r"^\s*(\*{3,}|-{3,}|_{3,})\s*$")


def check_formatting(name, lines, in_code, findings):
    for i, line in enumerate(lines):
        if i in in_code or is_table_row(line) or HR_RE.match(line):
            continue

        # Inline code: an odd number of backticks means one is unclosed.
        if line.count("`") % 2 == 1:
            findings.append(Finding(
                name, i + 1, CAT_FORMAT, ERROR,
                "незакрытый inline-код (нечётное число `` ` ``)",
            ))

        # A `* ` list marker is not an italic asterisk — strip it before counting;
        # escaped `\*` (сноски таблиц) — тоже не маркер форматирования.
        prose = LIST_MARKER_RE.sub("", line).replace("\\*", "")

        # Bold: odd count of `**` tokens.
        bold_tokens = prose.count("**")
        stripped_bold = prose.replace("**", "")
        if bold_tokens % 2 == 1:
            findings.append(Finding(
                name, i + 1, CAT_FORMAT, ERROR,
                "незакрытый `**` (bold без закрывающего маркера)",
            ))
        # Italic: after removing bold tokens, odd count of single `*`.
        elif stripped_bold.count("*") % 2 == 1:
            findings.append(Finding(
                name, i + 1, CAT_FORMAT, ERROR,
                "незакрытый `*` (italic без закрывающего маркера)",
            ))

        # Spaces inside bold markers: regex can't tell a closing `**` from the
        # next opening one, so split into segments — odd indices are bold text.
        if bold_tokens and bold_tokens % 2 == 0:
            segments = prose.split("**")
            for k in range(1, len(segments), 2):
                seg = segments[k]
                if seg.strip() and seg != seg.strip():
                    findings.append(Finding(
                        name, i + 1, CAT_FORMAT, WARNING,
                        "пробелы внутри bold-маркеров (`** text **`)",
                    ))
                    break

        for m in LINK_RE.finditer(line):
            inner = m.group(1).strip()
            if inner in ("", " ", "x", "X"):  # task-list checkbox, not a link
                continue
            after = line[m.end():m.end() + 1]
            if after not in ("(", "[", ":"):
                # SRD-текст легитимно содержит теги в скобках ([Action],
                # [Condition], [d10s] — «Tags in Brackets»), поэтому note.
                findings.append(Finding(
                    name, i + 1, CAT_FORMAT, NOTE,
                    f"`[{inner}]` без `(url)` — битая ссылка или тег правил",
                ))
                break


DASH_DASH_RE = re.compile(r"(?<!-)--(?!-)")
SPACE_HYPHEN_RE = re.compile(r"\S - \S")
DOUBLE_SPACE_RE = re.compile(r"\S  +\S")


def check_whitespace(name, lines, in_code, findings):
    blank_run = 0
    for i, line in enumerate(lines):
        if line.strip() == "" and line != "":
            findings.append(Finding(
                name, i + 1, CAT_SPACE, NOTE, "строка состоит только из пробелов",
            ))
        elif line != line.rstrip():
            findings.append(Finding(
                name, i + 1, CAT_SPACE, NOTE, "trailing whitespace",
            ))

        if line.strip() == "":
            blank_run += 1
            if blank_run == 3:
                findings.append(Finding(
                    name, i + 1, CAT_SPACE, WARNING, "3+ пустых строк подряд",
                ))
        else:
            blank_run = 0

        if i in in_code:
            continue
        if not is_table_row(line):
            # Table rows keep alignment padding — double spaces there are noise.
            if DOUBLE_SPACE_RE.search(line):
                findings.append(Finding(
                    name, i + 1, CAT_SPACE, WARNING, "двойные пробелы в тексте",
                ))
            if DASH_DASH_RE.search(line):
                findings.append(Finding(
                    name, i + 1, CAT_SPACE, NOTE, "`--` вместо `—` (em dash)",
                ))
            if SPACE_HYPHEN_RE.search(line):
                findings.append(Finding(
                    name, i + 1, CAT_SPACE, NOTE, "` - ` вместо ` — ` в предложении",
                ))


# Алфавитные «корзины» (`## Monsters: A` / `## Монстры: А`): при переводе
# монстры пересортированы по RU-именам, и число буквенных заголовков легитимно
# расходится — исключаем их из паритета уровней (симметрично для EN и RU).
ALPHA_BUCKET_RE = re.compile(r":\s*\S$")


def file_profile(lines, in_code):
    """Structural counts used for EN<->RU parity."""
    prof = {"h": [0, 0, 0, 0, 0, 0], "blockquotes": 0, "list_items": 0,
            "table_data": 0, "table_cols": [], "lines": len(lines)}
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if i in in_code:
            i += 1
            continue
        m = HEADING_RE.match(line)
        if m and not ALPHA_BUCKET_RE.search(line.strip()):
            prof["h"][len(m.group(1)) - 1] += 1
        if line.strip().startswith(">"):
            prof["blockquotes"] += 1
        if LIST_ITEM_RE.match(line):
            prof["list_items"] += 1
        if is_table_row(line):
            start = i
            while i < n and is_table_row(lines[i]) and i not in in_code:
                i += 1
            block = list(range(start, i))
            if len(block) >= 2 and is_separator_row(lines[block[1]]):
                prof["table_data"] += len(block) - 2  # minus header + separator
                prof["table_cols"].append(table_columns(lines[start]))
            continue
        i += 1
    return prof


def check_file(path, findings):
    """Run all per-file structural checks; return the file's parity profile."""
    text = Path(path).read_text(encoding="utf-8")
    lines = text.split("\n")
    in_code = code_fence_mask(lines)
    name = str(path)
    check_tables(name, lines, in_code, findings)
    check_headings(name, lines, in_code, findings)
    check_formatting(name, lines, in_code, findings)
    check_whitespace(name, lines, in_code, findings)
    return file_profile(lines, in_code)


# --- parity + coverage ------------------------------------------------------


def check_parity(en_name, ru_name, en_prof, ru_prof, findings):
    for lvl in range(6):
        if en_prof["h"][lvl] != ru_prof["h"][lvl]:
            findings.append(Finding(
                ru_name, 1, CAT_PARITY, ERROR,
                f"заголовков уровня {lvl + 1}: EN={en_prof['h'][lvl]}, "
                f"RU={ru_prof['h'][lvl]}",
            ))
    if en_prof["table_data"] != ru_prof["table_data"]:
        findings.append(Finding(
            ru_name, 1, CAT_PARITY, ERROR,
            f"строк таблиц: EN={en_prof['table_data']}, RU={ru_prof['table_data']}",
        ))
    if en_prof["blockquotes"] != ru_prof["blockquotes"]:
        findings.append(Finding(
            ru_name, 1, CAT_PARITY, ERROR,
            f"строк blockquote: EN={en_prof['blockquotes']}, "
            f"RU={ru_prof['blockquotes']}",
        ))
    if en_prof["list_items"] != ru_prof["list_items"]:
        findings.append(Finding(
            ru_name, 1, CAT_PARITY, ERROR,
            f"элементов списков: EN={en_prof['list_items']}, "
            f"RU={ru_prof['list_items']}",
        ))
    en_cols, ru_cols = en_prof["table_cols"], ru_prof["table_cols"]
    if len(en_cols) != len(ru_cols):
        findings.append(Finding(
            ru_name, 1, CAT_PARITY, ERROR,
            f"таблиц: EN={len(en_cols)}, RU={len(ru_cols)}",
        ))
    else:
        # Позиционное сравнение ловит сдвиг порядка таблиц как каскад ложных
        # расхождений — сравниваем отсортированные мультимножества ширин.
        for ec, rc in zip(sorted(en_cols), sorted(ru_cols)):
            # RU glossary tables carry an extra «Оригинал» column → EN+1 is fine.
            if rc not in (ec, ec + 1):
                findings.append(Finding(
                    ru_name, 1, CAT_PARITY, ERROR,
                    f"набор ширин таблиц расходится: EN={sorted(en_cols)}, "
                    f"RU={sorted(ru_cols)} (допустимо EN или EN+1 по-таблично)",
                ))
                break
    en_lines, ru_lines = en_prof["lines"], ru_prof["lines"]
    if en_lines and abs(ru_lines - en_lines) / en_lines > 0.05:
        findings.append(Finding(
            ru_name, 1, CAT_PARITY, WARNING,
            f"число строк расходится >5%: EN={en_lines}, RU={ru_lines}",
        ))


def check_glossary_coverage(index_path, chapter_path, findings):
    index_lines = Path(index_path).read_text(encoding="utf-8").split("\n")
    chapter_lines = Path(chapter_path).read_text(encoding="utf-8").split("\n")
    in_code = code_fence_mask(chapter_lines)

    # Data rows across all proper tables in the index.
    index_rows, i, n = 0, 0, len(index_lines)
    while i < n:
        if is_table_row(index_lines[i]):
            start = i
            while i < n and is_table_row(index_lines[i]):
                i += 1
            block = list(range(start, i))
            if len(block) >= 2 and is_separator_row(index_lines[block[1]]):
                index_rows += len(block) - 2
            continue
        i += 1

    # Entities in the chapter: denser of ### / #### (mirrors extract_entities.py).
    h3 = [l for l in chapter_lines if l.startswith("### ")]
    h4 = [l for l in chapter_lines if l.startswith("#### ")]
    entities = len(h3) if len(h3) >= len(h4) else len(h4)

    if index_rows != entities:
        findings.append(Finding(
            str(index_path), 1, CAT_INDEX, ERROR,
            f"строк в индексе {index_rows}, сущностей в главе {entities} "
            f"({Path(chapter_path).name})",
        ))


# --- fix --------------------------------------------------------------------


def apply_fixes(path):
    """Context-free repairs only. Returns the number of lines changed."""
    text = Path(path).read_text(encoding="utf-8")
    lines = text.split("\n")
    in_code = code_fence_mask(lines)
    changed = 0
    out = []
    blank_run = 0
    for i, line in enumerate(lines):
        if i in in_code:  # never rewrite fenced code (`#comment`, значимые пробелы)
            out.append(line)
            blank_run = 0
            continue
        new = line.rstrip()  # trailing whitespace + whitespace-only lines
        m = NOSPACE_HEADING_RE.match(new)
        if m:
            hashes = len(new) - len(new.lstrip("#"))
            new = new[:hashes] + " " + new[hashes:]
        if new.strip() == "":
            blank_run += 1
            if blank_run > 2:
                changed += 1
                continue  # drop 3rd+ consecutive blank
        else:
            blank_run = 0
        if new != line:
            changed += 1
        out.append(new)
    Path(path).write_text("\n".join(out), encoding="utf-8")
    return changed


# --- driver -----------------------------------------------------------------


def collect_md(path):
    p = Path(path)
    if p.is_dir():
        return sorted(p.rglob("*.md"))
    if p.suffix == ".md":
        return [p]
    return []


def main():
    parser = argparse.ArgumentParser(
        description="Deterministic markdown structure validator.")
    parser.add_argument("paths", nargs="*", help="files or directories to check")
    parser.add_argument("--pair", nargs=2, metavar=("EN", "RU"),
                        help="EN and RU dirs/files to check for structural parity")
    parser.add_argument("--glossary-index", metavar="FILE",
                        help="glossary index file for coverage check")
    parser.add_argument("--chapter", metavar="FILE",
                        help="source chapter for glossary coverage check")
    parser.add_argument("--fix", action="store_true",
                        help="apply context-free repairs in place")
    args = parser.parse_args()

    findings = []
    profiles = {}

    def run_file(p):
        key = str(p)
        if key not in profiles:
            profiles[key] = check_file(p, findings)
        return profiles[key]

    if args.fix:
        targets = []
        for path in args.paths:
            targets.extend(collect_md(path))
        if args.pair:
            targets.extend(collect_md(args.pair[0]))
            targets.extend(collect_md(args.pair[1]))
        total = sum(apply_fixes(t) for t in targets)
        print(f"--fix: изменено строк — {total} в {len(targets)} файл(ах)")
        return 0

    for path in args.paths:
        for p in collect_md(path):
            run_file(p)

    if args.pair:
        en_root, ru_root = Path(args.pair[0]), Path(args.pair[1])
        if en_root.is_file() and ru_root.is_file():
            # Two explicit files pair directly regardless of name.
            en_map = {"": en_root}
            ru_map = {"": ru_root}
        else:
            def rel(p, root):
                return str(p.relative_to(root))

            en_map = {rel(p, en_root): p for p in collect_md(en_root)}
            ru_map = {rel(p, ru_root): p for p in collect_md(ru_root)}
        for key in sorted(set(en_map) | set(ru_map)):
            if key not in ru_map:
                findings.append(Finding(str(en_map[key]), 1, CAT_PAIR, ERROR,
                                        "нет пары RU"))
                continue
            if key not in en_map:
                findings.append(Finding(str(ru_map[key]), 1, CAT_PAIR, ERROR,
                                        "нет пары EN"))
                continue
            en_prof = run_file(en_map[key])
            ru_prof = run_file(ru_map[key])
            rel_path = Path(key) if key else en_map[key]
            # RU 00_Legal легитимно расходится (примечание о переводе);
            # структуру *_Glossary/ (RU = EN + «Оригинал», своя разбивка)
            # проверяет доменный check_glossary.py, а не generic-паритет.
            if rel_path.name.startswith("00_Legal") or any(
                    part.endswith("_Glossary") for part in rel_path.parts):
                continue
            check_parity(str(en_map[key]), str(ru_map[key]), en_prof, ru_prof,
                         findings)

    if args.glossary_index and args.chapter:
        check_glossary_coverage(args.glossary_index, args.chapter, findings)
    elif args.glossary_index or args.chapter:
        print("Ошибка: --glossary-index и --chapter используются вместе",
              file=sys.stderr)
        return 2

    findings.sort(key=lambda f: (f.file, f.line))
    gating = [f for f in findings if f.severity in (ERROR, WARNING)]
    notes = [f for f in findings if f.severity == NOTE]
    for f in gating:
        print(f.format())
    if notes:
        print()
        print("Заметки (не влияют на exit-код):")
        for f in notes:
            print(f.format())

    by_cat = {}
    for f in gating:
        by_cat[f.category] = by_cat.get(f.category, 0) + 1

    print()
    print(f"Файлов проверено: {len(profiles)}")
    print(f"Найдено проблем: {len(gating)} (+ заметок: {len(notes)})")
    if by_cat:
        print("По категориям: " + ", ".join(
            f"{c} — {n}" for c, n in sorted(by_cat.items())))
    print("Статус: " + ("✗ Найдены проблемы" if gating else "✓ Все проверки пройдены"))
    return 1 if gating else 0


if __name__ == "__main__":
    sys.exit(main())
