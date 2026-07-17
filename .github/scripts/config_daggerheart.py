"""Configuration for Daggerheart SRD API generation.

Отдельный конфиг, чтобы D&D-пайплайн (config.py) оставался нетронутым. Ключ версии `srd10`
→ URL-сегмент `srd-1.0` (см. web VERSION_SLUG). name_en у RU-сущностей берётся из
inline-English в заголовках (`## Дварф (Dwarf)`), как в D&D SRD 5.1.
"""

SYSTEM = "daggerheart"
SYSTEM_NAME = "Daggerheart"
# Ключ версии = слаг URL без разделителей (srd-1.0 → srd10), как srd-5.2 → srd52 в D&D.
# Инвариант держит verKeyOf() в автолинке/ховеркардах: путь данных = api/{game}/{verKey}/…
VERSION_NAMES = {"srd10": "SRD 1.0"}

SOURCES = [
    # Daggerheart SRD 1.0 EN
    {"ver": "srd10", "lang": "en", "type": "ancestry",    "file": "srd-1.0/en/05_Ancestries.md"},
    {"ver": "srd10", "lang": "en", "type": "community",   "file": "srd-1.0/en/06_Communities.md"},
    {"ver": "srd10", "lang": "en", "type": "domain_card", "file": "srd-1.0/en/16_DomainCardReference.md"},
    {"ver": "srd10", "lang": "en", "type": "adversary",   "file": "srd-1.0/en/13_Adversaries.md"},
    {"ver": "srd10", "lang": "en", "type": "environment", "file": "srd-1.0/en/14_Environments.md"},
    {"ver": "srd10", "lang": "en", "type": "dh_glossary", "file": "srd-1.0/en/17_Glossary/00_Glossary.md"},
    # Daggerheart SRD 1.0 RU
    {"ver": "srd10", "lang": "ru", "type": "ancestry",    "file": "srd-1.0/ru/05_Ancestries.md"},
    {"ver": "srd10", "lang": "ru", "type": "community",   "file": "srd-1.0/ru/06_Communities.md"},
    {"ver": "srd10", "lang": "ru", "type": "domain_card", "file": "srd-1.0/ru/16_DomainCardReference.md"},
    {"ver": "srd10", "lang": "ru", "type": "adversary",   "file": "srd-1.0/ru/13_Adversaries.md"},
    {"ver": "srd10", "lang": "ru", "type": "environment", "file": "srd-1.0/ru/14_Environments.md"},
    {"ver": "srd10", "lang": "ru", "type": "dh_glossary", "file": "srd-1.0/ru/17_Glossary/00_Glossary.md"},
]
