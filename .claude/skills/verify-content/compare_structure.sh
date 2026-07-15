#!/bin/bash
# Compare structural correspondence between EN and RU files.
# Usage: bash compare_structure.sh <en_dir> <ru_dir>
#
# Checks for each pair: line count, headings (#/##/###/####), table rows, blockquotes.
# Exit code: 0 if all match, 1 if any mismatch found.
#
# EXCLUDE_STRUCT (env, space-separated relative paths): для перечисленных файлов проверяем
# только НАЛИЧИЕ RU-пары, но НЕ сверяем строки/заголовки/таблицы. Нужно для файлов, где
# строгая парность легитимно нарушена: (а) индекс-файлы, пересортированные по алфавиту языка
# (заклинания/монстры/животные — RU-порядок ≠ EN, число буквенных секций разное); (б) legal с
# RU-приложением (неофициальный перевод OGL обязан идти сверх EN-текста). Для таких файлов
# осмысленный гейт — slug-парность (verify_ru_en_parity.py), а не построчная сверка.

set -euo pipefail

EN_DIR="${1:?Usage: compare_structure.sh <en_dir> <ru_dir>}"
RU_DIR="${2:?Usage: compare_structure.sh <en_dir> <ru_dir>}"
EXCLUDE_STRUCT="${EXCLUDE_STRUCT:-}"

errors=0
checked=0
skipped=0

for en_file in $(find "$EN_DIR" -name "*.md" -not -path "*_Glossary/*" | sort); do
    rel_path="${en_file#$EN_DIR/}"
    ru_file="$RU_DIR/$rel_path"

    if [ ! -f "$ru_file" ]; then
        echo "MISSING: $rel_path — RU file not found"
        errors=$((errors + 1))
        continue
    fi

    # Исключённые из структурной сверки (легитимно расходятся) — проверили наличие, идём дальше.
    for excl in $EXCLUDE_STRUCT; do
        if [ "$rel_path" = "$excl" ]; then
            echo "SKIP (structural)  $rel_path — исключён (алфавит-пересортировка / legal-приложение)"
            skipped=$((skipped + 1))
            continue 2
        fi
    done

    checked=$((checked + 1))
    file_ok=true

    # Line count (strict, tolerance 0)
    en_lines=$(wc -l < "$en_file")
    ru_lines=$(wc -l < "$ru_file")
    if [ "$en_lines" -ne "$ru_lines" ]; then
        printf "MISMATCH %-40s lines: EN=%d RU=%d (diff=%+d)\n" "$rel_path" "$en_lines" "$ru_lines" "$((ru_lines - en_lines))"
        file_ok=false
    fi

    # Headings by level
    for level in 1 2 3 4; do
        prefix=$(printf '#%.0s' $(seq 1 $level))
        en_count=$(grep -c "^${prefix} " "$en_file" 2>/dev/null || true)
        ru_count=$(grep -c "^${prefix} " "$ru_file" 2>/dev/null || true)
        if [ "$en_count" -ne "$ru_count" ]; then
            printf "MISMATCH %-40s H%d: EN=%d RU=%d\n" "$rel_path" "$level" "$en_count" "$ru_count"
            file_ok=false
        fi
    done

    # Table rows (lines starting with |)
    en_tables=$(grep -c '^|' "$en_file" 2>/dev/null || true)
    ru_tables=$(grep -c '^|' "$ru_file" 2>/dev/null || true)
    if [ "$en_tables" -ne "$ru_tables" ]; then
        printf "MISMATCH %-40s tables: EN=%d RU=%d\n" "$rel_path" "$en_tables" "$ru_tables"
        file_ok=false
    fi

    if [ "$file_ok" = false ]; then
        errors=$((errors + 1))
    fi
done

echo ""
echo "Checked: $checked files (skipped structural: $skipped)"
if [ "$errors" -eq 0 ]; then
    echo "Result: ALL OK"
    exit 0
else
    echo "Result: $errors file(s) with mismatches"
    exit 1
fi
