"""Общие константы эталона полей статблоков.

Живут отдельно, потому что их читают двое: гейт `test_statblock_fields.py` и сборщик
`build_statblock_fields.py`. Копия в каждом из них уже разъезжалась.
"""

# Служебные ключи эталона: это не поля статблока, а пометки о самом эталоне —
# объявленные опечатки PDF (`cr_note`/`cr_repo`/`xp_note`/`pb_note`) и признак врезки.
META_KEYS = ("cr_note", "cr_repo", "xp_note", "pb_note", "abilities_note", "abilities_repo",
              "outside_chapters")
