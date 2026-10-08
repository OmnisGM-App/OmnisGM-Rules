#!/usr/bin/env python3
"""Проверка attach_images() из generate_api.py (issue #201).

Живьём этот инвариант не проверить: сегодня портрет есть у ВСЕХ существ, поэтому
«ставим поле только при наличии файла» и «ставим всем подряд» дают на реальных данных
один и тот же результат. Разница вылезет в первый же день, когда в SRD добавится
сущность, для которой генератор картинок ещё не отработал, — и потребитель (компендиум
Table, og:image) получит битую ссылку. Поэтому проверяем на синтетике.

Запуск: python3 .github/scripts/test_attach_images.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_api import attach_images  # noqa: E402

ORIGIN = "https://rules.omnisgm.com"
failures = []


def check(name: str, got, want):
    if got != want:
        failures.append(f"{name}: получили {got!r}, ожидали {want!r}")


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "dnd" / "creatures").mkdir(parents=True)
    (root / "dnd" / "creatures" / "aboleth.webp").write_bytes(b"webp")
    (root / "daggerheart" / "creatures").mkdir(parents=True)
    (root / "daggerheart" / "creatures" / "acid-burrower.webp").write_bytes(b"webp")

    # Заклинания (#202) — своя папка на коллекцию.
    (root / "dnd" / "spells").mkdir(parents=True)
    (root / "dnd" / "spells" / "acid-arrow.webp").write_bytes(b"webp")

    # D&D: монстр с файлом, монстр без файла, животное с файлом (та же папка creatures),
    # заклинание с файлом и без, магпредмет (папки нет вовсе).
    with_file = {"slug": "aboleth"}
    without_file = {"slug": "brand-new-monster"}
    animal = {"slug": "aboleth"}
    spell_with = {"slug": "acid-arrow"}
    spell_without = {"slug": "fireball"}
    magic_item = {"slug": "amulet-of-health"}
    dnd = {
        ("srd52", "ru", "monsters"): [with_file, without_file],
        ("srd52", "ru", "animals"): [animal],
        ("srd52", "ru", "spells"): [spell_with, spell_without],
        ("srd52", "ru", "magic-items"): [magic_item],
    }
    count = attach_images(dnd, "dnd", root, ORIGIN)

    check("монстр с файлом", with_file.get("image"), f"{ORIGIN}/img/dnd/creatures/aboleth.webp")
    check("монстр БЕЗ файла не получает поля", "image" in without_file, False)
    check("животное берёт из общей папки", animal.get("image"), f"{ORIGIN}/img/dnd/creatures/aboleth.webp")
    check("заклинание берёт из своей папки", spell_with.get("image"), f"{ORIGIN}/img/dnd/spells/acid-arrow.webp")
    check("заклинание БЕЗ файла не получает поля", "image" in spell_without, False)
    check("магпредмет: папки нет вовсе — поля нет", "image" in magic_item, False)
    check("счётчик", count, 3)

    # Понятия правил и варианты классов (#380): состояние и термин 5.1 с тем же слагом делят
    # папку rules, вариант класса — своя папка.
    (root / "dnd" / "rules").mkdir(parents=True)
    (root / "dnd" / "rules" / "blinded.webp").write_bytes(b"webp")
    (root / "dnd" / "rules" / "dash.webp").write_bytes(b"webp")
    (root / "dnd" / "rules" / "cone.webp").write_bytes(b"webp")
    (root / "dnd" / "class-options").mkdir(parents=True)
    (root / "dnd" / "class-options" / "metamagic-careful-spell.webp").write_bytes(b"webp")
    condition = {"slug": "blinded"}
    term = {"slug": "blinded"}
    action = {"slug": "dash"}
    action_without = {"slug": "dodge"}
    area = {"slug": "cone"}
    option = {"slug": "metamagic-careful-spell"}
    attach_images({
        ("srd52", "en", "conditions"): [condition],
        ("srd51", "en", "rules-terms"): [term],
        ("srd52", "en", "actions"): [action, action_without],
        ("srd52", "en", "areas-of-effect"): [area],
        ("srd52", "en", "class-options"): [option],
    }, "dnd", root, ORIGIN)
    check("состояние — из папки rules", condition.get("image"), f"{ORIGIN}/img/dnd/rules/blinded.webp")
    check("термин 5.1 с тем же слагом — та же картинка", term.get("image"), f"{ORIGIN}/img/dnd/rules/blinded.webp")
    check("действие — из папки rules", action.get("image"), f"{ORIGIN}/img/dnd/rules/dash.webp")
    check("действие без файла не получает поля", "image" in action_without, False)
    check("область воздействия — из папки rules", area.get("image"), f"{ORIGIN}/img/dnd/rules/cone.webp")
    check("вариант класса — из своей папки", option.get("image"), f"{ORIGIN}/img/dnd/class-options/metamagic-careful-spell.webp")

    # Daggerheart: своя игра — свой префикс пути.
    adversary = {"slug": "acid-burrower"}
    environment = {"slug": "haunted-city"}
    dh = {
        ("srd10", "en", "adversaries"): [adversary],
        ("srd10", "en", "environments"): [environment],
    }
    attach_images(dh, "daggerheart", root, ORIGIN)
    check("противник", adversary.get("image"), f"{ORIGIN}/img/daggerheart/creatures/acid-burrower.webp")
    check("окружение — не коллекция с картинками", "image" in environment, False)

    # Игра без картинок вовсе (BRP) — функция не падает и ничего не ставит.
    brp_entity = {"slug": "aboleth"}
    check("игра вне карты", attach_images({("srd10", "en", "monsters"): [brp_entity]}, "brp", root, ORIGIN), 0)
    check("игра вне карты: поля нет", "image" in brp_entity, False)

if failures:
    print("attach_images: ПРОВАЛЕНО", file=sys.stderr)
    for f in failures:
        print(f"  {f}", file=sys.stderr)
    sys.exit(1)
print("attach_images: ок")
