#!/usr/bin/env python3
"""
Regression tests for layout_recovery.py.

Fixtures are real defect samples captured from an alternative D&D SRD 5.2
conversion run (dnd-v2) that regressed relative to the canon: 639 raw <br>
artifacts and glued two-column stat-block fields. The canon (dnd/srd-5.2) had
zero of either. These tests lock in the auto-fixes so future imports don't ship
the same defects.

Run:  python3 test_layout_recovery.py
"""

import layout_recovery as lr


def run(fn, text):
    lr.stats.clear()
    return fn(text)


def check(name, got, want):
    status = "ok" if got == want else "FAIL"
    if got != want:
        print(f"[{status}] {name}\n  want: {want!r}\n  got:  {got!r}")
    else:
        print(f"[{status}] {name}")
    return got == want


def test_br_prose_word_split():
    # PDF forced break inside a word → join without a space
    out = run(lr.fix_br_artifacts, "hindering the charac<br>ter's perception")
    return check("br: prose word split joins", out, "hindering the character's perception")


def test_br_prose_word_boundary():
    # Break before an uppercase letter is a word boundary → single space, not a join
    out = run(lr.fix_br_artifacts, "On a failed Save<br>DC the target")
    return check("br: prose word boundary → space", out, "On a failed Save DC the target")


def test_br_table_cell_space():
    # Inside table cells a break wraps a multi-word value → single space
    out = run(lr.fix_br_artifacts, "| Slot<br>Level | Finesse<br>or Light | 7<br>Wis |")
    return check("br: table cell → space", out, "| Slot Level | Finesse or Light | 7 Wis |")


def test_br_case_insensitive_tag():
    out = run(lr.fix_br_artifacts, "a<BR>b and c<br/>d and e<br />F")
    return check("br: <BR>/<br/>/<br /> all handled", out, "ab and cd and e F")


def test_glued_two_fields():
    out = run(lr.fix_glued_fields, "**Casting Time:** Action **Range:** 90 feet")
    return check("glued: two fields split",
                 out, "**Casting Time:** Action\n\n**Range:** 90 feet")


def test_glued_four_fields():
    out = run(lr.fix_glued_fields,
              "**Casting Time:** Action **Range:** 60 feet **Components:** V, S **Duration:** Instantaneous")
    return check("glued: four fields split", out,
                 "**Casting Time:** Action\n\n**Range:** 60 feet\n\n"
                 "**Components:** V, S\n\n**Duration:** Instantaneous")


def test_glued_single_field_untouched():
    # A lone stat-block field must not be altered
    out = run(lr.fix_glued_fields, "**Duration:** Instantaneous")
    return check("glued: single field untouched", out, "**Duration:** Instantaneous")


def test_glued_prose_inline_untouched():
    # Prose that does not START with a bold label must not be split, even with 2+ labels
    text = "See the **spell:** here and **note:** there"
    out = run(lr.fix_glued_fields, text)
    return check("glued: prose not starting with label untouched", out, text)


def test_glued_table_row_untouched():
    # Table rows contain pipes and must never be split as stat-block fields
    row = "| **Str:** 10 | **Dex:** 14 |"
    out = run(lr.fix_glued_fields, row)
    return check("glued: table row untouched", out, row)


def test_word_per_line_rejoined():
    # marker на узкой колонке кладёт каждое слово на свою строку с одним пробелом
    text = "# **Aboleth**\n\n*Large \n aberration, \n lawful \n evil*\n"
    out = run(lr.fix_word_per_line, text)
    return check("word-per-line: rejoined",
                 out, "# **Aboleth**\n\n*Large aberration, lawful evil*\n")


def test_word_per_line_healthy_file_untouched():
    # Здоровый файл: продолжений с ОДНИМ ведущим пробелом мало — порог не пройден.
    # Фикстура намеренно содержит такую строку, иначе тест был бы вакуумным и не заметил
    # бы снижения порога.
    text = ("Обычный абзац.\n продолжение с отступом\n\n"
            + "".join(f"Строка {i} без отступа.\n" for i in range(10)))
    out = run(lr.fix_word_per_line, text)
    return check("word-per-line: below threshold untouched", out, text)


def test_word_per_line_above_threshold_joins():
    # Ровно та же форма, но продолжений большинство — склейка обязана включиться
    text = "Абзац\n продолжение\n ещё\n слово\n и\n ещё\n одно\n"
    out = run(lr.fix_word_per_line, text)
    return check("word-per-line: above threshold joined",
                 out, "Абзац продолжение ещё слово и ещё одно\n")


def test_word_per_line_hyphen_join_no_space():
    # «any non-\n lawful» → «any non-lawful», а не «any non- lawful»
    text = "any non-\n lawful\n alignment\n здесь\n ещё\n слова\n"
    out = run(lr.fix_word_per_line, text)
    return check("word-per-line: hyphen joined without space",
                 out.startswith("any non-lawful alignment"), True)


def test_word_per_line_fence_and_heading_protected():
    # Фенс не разрушаем, к заголовку продолжение не клеим
    text = ("## Bandit\n *Medium humanoid*\n текст\n дальше\n ещё\n слово\n\n"
            "```\ndef f():\n return 1\n```\n")
    out = run(lr.fix_word_per_line, text)
    ok = ("## Bandit\n *Medium humanoid* текст дальше ещё слово" in out
          and "```\ndef f():\n return 1\n```" in out)
    return check("word-per-line: fence and heading protected", ok, True)


def test_word_per_line_list_item_with_number_kept():
    # «- 3 очка действия» — пункт списка, а не хвост формулы
    text = "Абзац\n продолжение\n ещё\n слово\n и\n ещё\n одно\n - 3 очка действия\n"
    out = run(lr.fix_word_per_line, text)
    return check("word-per-line: numeric list item kept", "\n - 3 очка действия" in out, True)


def test_word_per_line_keeps_lists_and_tables():
    # Даже в разорванном файле список и таблица со отступом остаются отдельными строками
    text = ("*Large \n beast*\n\n"
            "Текст \n продолжение \n ещё \n слово \n здесь \n длинный \n абзац\n\n"
            " - пункт списка\n | ячейка | таблицы |\n")
    out = run(lr.fix_word_per_line, text)
    ok = ("*Large beast*" in out
          and "Текст продолжение ещё слово здесь длинный абзац" in out
          and "\n - пункт списка\n" in out
          and "\n | ячейка | таблицы |\n" in out)
    return check("word-per-line: lists and tables kept", ok, True)


def test_word_per_line_dice_tail_rejoined():
    # «(18d10\n + 36)» — по виду маркер списка, по смыслу хвост формулы
    text = ("*Large \n beast*\n\n**Hit \n Points** 135 \n (18d10 \n + \n 36)\n\n"
            "Текст \n продолжение \n ещё \n слово \n здесь\n")
    out = run(lr.fix_word_per_line, text)
    return check("word-per-line: dice tail rejoined",
                 "**Hit Points** 135 (18d10 + 36)" in out, True)


def test_word_per_line_heading_completed():
    # Ради этого функция и писалась: «### Adult\n Red Dragon» — имя, разорванное по словам.
    # Тест держит МНОГОСЛОВНЫЙ заголовок: на односложном («## Bandit») правило не видно.
    text = ("### Adult \n Red \n Dragon\n\n*Huge \n dragon*\n\n"
            "Текст \n продолжение \n ещё \n слово\n")
    out = run(lr.fix_word_per_line, text)
    ok = "### Adult Red Dragon" in out and "*Huge dragon*" in out
    return check("word-per-line: heading completed", ok, True)


def test_word_per_line_statblock_header_not_glued_to_heading():
    # Обратная сторона того же правила: шапка статблока к заголовку не приклеивается
    text = ("### Adult \n Red \n Dragon\n *Huge \n dragon*\n\n"
            "Текст \n продолжение \n ещё \n слово\n")
    out = run(lr.fix_word_per_line, text)
    ok = "### Adult Red Dragon\n *Huge dragon*" in out
    return check("word-per-line: statblock header kept off heading", ok, True)


def test_word_per_line_minus_tail_keeps_space():
    # «(14d10\n -\n 28)» — минус формулы, а не перенос по дефису: пробел обязан остаться
    text = ("*Large \n beast*\n\n**Hit \n Points** 77 \n (14d10 \n - \n 28)\n\n"
            "Текст \n продолжение \n ещё \n слово\n")
    out = run(lr.fix_word_per_line, text)
    return check("word-per-line: minus tail keeps space",
                 "**Hit Points** 77 (14d10 - 28)" in out, True)


def test_word_per_line_unpaired_fence_does_not_disable():
    # Одинокий открывающий фенс не должен уводить остаток файла в «не трогать»
    text = ("```\nfragment\n\nТекст \n продолжение \n ещё \n слово \n здесь \n длинный\n")
    out = run(lr.fix_word_per_line, text)
    ok = "Текст продолжение ещё слово здесь длинный" in out
    return check("word-per-line: unpaired fence does not disable", ok, True)


def test_word_per_line_table_and_setext_not_receivers():
    # Две оставшиеся ветки NO_APPEND_RE: строка таблицы и подчёркивание setext
    text = ("| ячейка | таблицы |\n продолжение\n\nЗаголовок\n===\n хвост\n"
            "Текст \n дальше \n ещё \n слово\n")
    out = run(lr.fix_word_per_line, text)
    ok = ("| ячейка | таблицы |\n продолжение" in out and "===\n хвост" in out)
    return check("word-per-line: table and setext are not receivers", ok, True)


def main():
    tests = [
        test_br_prose_word_split,
        test_br_prose_word_boundary,
        test_br_table_cell_space,
        test_br_case_insensitive_tag,
        test_glued_two_fields,
        test_glued_four_fields,
        test_glued_single_field_untouched,
        test_glued_prose_inline_untouched,
        test_glued_table_row_untouched,
        test_word_per_line_rejoined,
        test_word_per_line_healthy_file_untouched,
        test_word_per_line_above_threshold_joins,
        test_word_per_line_hyphen_join_no_space,
        test_word_per_line_fence_and_heading_protected,
        test_word_per_line_list_item_with_number_kept,
        test_word_per_line_keeps_lists_and_tables,
        test_word_per_line_dice_tail_rejoined,
        test_word_per_line_heading_completed,
        test_word_per_line_statblock_header_not_glued_to_heading,
        test_word_per_line_minus_tail_keeps_space,
        test_word_per_line_unpaired_fence_does_not_disable,
        test_word_per_line_table_and_setext_not_receivers,
    ]
    results = [t() for t in tests]
    passed = sum(results)
    print(f"\n{passed}/{len(results)} passed")
    raise SystemExit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
