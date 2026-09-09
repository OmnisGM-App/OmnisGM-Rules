#!/bin/bash
# Build a single combined markdown file from all content files in a directory.
# Excludes glossary (*_Glossary/) files.
#
# Usage: bash build_combined_md.sh <source_dir> <output_file>
# Example: bash build_combined_md.sh src/dnd/srd-5.2/ru SRD_5.2_RU.md

set -euo pipefail

SOURCE_DIR="${1:?Usage: build_combined_md.sh <source_dir> <output_file>}"
OUTPUT_FILE="${2:?Usage: build_combined_md.sh <source_dir> <output_file>}"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Directory not found: $SOURCE_DIR"
    exit 1
fi

: > "$OUTPUT_FILE"

count=0
for f in $(find "$SOURCE_DIR" -name "*.md" -not -path "*_Glossary/*" | sort); do
    cat "$f" >> "$OUTPUT_FILE"
    printf "\n\n" >> "$OUTPUT_FILE"
    count=$((count + 1))
done

lines=$(wc -l < "$OUTPUT_FILE")
echo "Built: $OUTPUT_FILE ($count files, $lines lines)"
