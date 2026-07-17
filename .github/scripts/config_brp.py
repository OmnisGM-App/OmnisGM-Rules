"""Configuration for Basic Roleplaying (BRP) SRD API generation.

Отдельный конфиг (мультиигровой генератор). Ключ версии `srd10` → URL `srd-1.0`
(тот же slug, что Daggerheart, но game=brp → путь api/brp/srd10/… изолирован).
Табличные ресурсы (skills) несут английское имя в колонке «Оригинал» → паритет
слагов by construction; проза (professions/spot-rules) — inline-English в заголовках.
"""

SYSTEM = "brp"
SYSTEM_NAME = "Basic Roleplaying"
VERSION_NAMES = {"srd10": "SRD 1.0"}

SOURCES = [
    # BRP SRD 1.0 EN
    {"ver": "srd10", "lang": "en", "type": "brp_skill",      "file": "srd-1.0/en/09_Glossary/01_Skills.md"},
    {"ver": "srd10", "lang": "en", "type": "brp_profession", "file": "srd-1.0/en/09_Glossary/04_Professions.md"},
    {"ver": "srd10", "lang": "en", "type": "brp_spot_rule",  "file": "srd-1.0/en/06_SpotRules.md"},
    # BRP SRD 1.0 RU
    {"ver": "srd10", "lang": "ru", "type": "brp_skill",      "file": "srd-1.0/ru/09_Glossary/01_Skills.md"},
    {"ver": "srd10", "lang": "ru", "type": "brp_profession", "file": "srd-1.0/ru/09_Glossary/04_Professions.md"},
    {"ver": "srd10", "lang": "ru", "type": "brp_spot_rule",  "file": "srd-1.0/ru/06_SpotRules.md"},
]
