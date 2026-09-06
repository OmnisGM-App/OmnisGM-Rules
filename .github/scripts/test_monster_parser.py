#!/usr/bin/env python3
"""Регресс-тесты разбора строки типа и строки скорости статблока (issue #260).

Уникальное покрытие дают ДВЕ формы, и обе — из врезок, которых не видит ни один соседний
гейт: граница диапазона («Huge or Smaller», RU «Огромный или меньший») и составной тип
(«Large Celestial, Fey, or Fiend (Your Choice), Neutral») — откат склейки типа по последней
запятой вне скобок оставляет гейты шапок и полей зелёными, красным становится только этот
файл. Форма 5.1 с запятой ВНУТРИ скобок подтипа стоит здесь как контракт: сама по себе она
и без lookahead собирается обратно склейкой, поэтому её откат не краснеет нигде — это
известная дыра, а не покрытие. Остальные формы держит и гейт шапок.
Помимо положительных форм фиксируем отрицательные: мусор не должен превращаться в размер.

Вторая половина файла — формы строки СКОРОСТИ, и покрытие у них такое же уникальное:
их откат виден только в собранном JSON API, которого не читает ни один гейт. «Climb or
Fly 20 ft.» (число относится к ОБОИМ режимам) живёт у одного Роя насекомых, а русские
«лазанье» и «лазание» — две живые формы расщеплённого корпуса 5.2: «лазанье» пишут
30 строк скорости (22 в `13_Animals.md`, 8 в `12_MonstersA-Z.md`), «лазание» — 23
(22 в `12_MonstersA-Z.md` и одна во врезке `07_Spells.md`), см. #270:
пока словарь знал одну, у 30 блоков climb молча уезжал пустым.

Запуск: python3 .github/scripts/test_monster_parser.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parsers.monster import _parse_speed, _parse_type_line  # noqa: E402

CASES = [
    # (строка, язык, размер, тип, подтип, мировоззрение)
    ("*Large Aberration, Lawful Evil*", "en",
     "Large", "Aberration", None, "Lawful Evil"),
    ("*Medium or Small Humanoid, Neutral*", "en",
     "Medium or Small", "Humanoid", None, "Neutral"),
    # Граница диапазона: без неё размер уезжал в тип («or Smaller Construct»).
    ("*Huge or Smaller Construct, Unaligned*", "en",
     "Huge or Smaller", "Construct", None, "Unaligned"),
    # Составной тип: мировоззрение — после ПОСЛЕДНЕЙ запятой вне скобок, иначе тип
    # рвался по первой и «Fey, or Fiend (Your Choice)» уезжало в мировоззрение.
    ("*Large Celestial, Fey, or Fiend (Your Choice), Neutral*", "en",
     "Large", "Celestial, Fey, or Fiend", "Your Choice", "Neutral"),
    # Запятая ВНУТРИ скобок разделителем не считается (5.1).
    ("*Medium Fiend (Demon, Shapechanger), Chaotic Evil*", "en",
     "Medium", "Fiend", "Demon, Shapechanger", "Chaotic Evil"),
    ("*Огромный или меньший конструкт, без мировоззрения*", "ru",
     "Огромный или меньший", "конструкт", None, "без мировоззрения"),
    # Род границы согласуется с типом: женский и средний — такие же законные формы.
    ("*Огромная или меньшая тварь, без мировоззрения*", "ru",
     "Огромная или меньшая", "тварь", None, "без мировоззрения"),
    ("*Огромное или меньшее чудовище, без мировоззрения*", "ru",
     "Огромное или меньшее", "чудовище", None, "без мировоззрения"),
    ("*Среднее или Маленькое Чудовище (ликантроп), нейтрально-добрый*", "ru",
     "Среднее или Маленькое", "Чудовище", "ликантроп", "нейтрально-добрый"),
]

# Отрицательные: строка без размера разбирается как есть и НЕ выдумывает составной размер.
NEGATIVE = [
    ("*Conjuration Level 4 (Druid)*", "en", "Conjuration"),
    ("*Вызов 4-го уровня (Друид)*", "ru", "Вызов"),
    ("*Medium or Cheese Humanoid, Neutral*", "en", "Medium"),
    ("", "en", ""),
]

# Скорость «Climb or Fly 20 ft.»: число относится к обоим режимам. Живого гейта на JSON API
# нет, а в тексте это единственный такой блок (Рой насекомых), поэтому форма — здесь.
# Строки взяты из корпуса БАЙТ В БАЙТ — кроме одной, помеченной ниже синтетической.
# Корпус RU 5.2 расщеплён по слову (#270): «лазанье» — 30 строк скорости (22 в главе
# животных, 8 в главе монстров), «лазание» — 23 (22 в главе монстров и одна во врезке
# заклинания), — поэтому в словаре живут обе формы, и
# закреплены здесь тоже обе. До этого словарь знал только «лазание», и у 30 блоков с
# «лазанье» climb уезжал пустым, а тест этого не видел.
SPEEDS = [
    ("20 ft., Climb or Fly 20 ft. (GM's choice)", "en", {"walk": 20, "climb": 20, "fly": 20}),
    ("20 футов, лазанье или полёт 20 футов (на выбор Мастера)", "ru",
     {"walk": 20, "climb": 20, "fly": 20}),
    # Единственная СИНТЕТИЧЕСКАЯ запись здесь: такой строки в корпусе нет (у Аватара
    # смерти написано «60 ft., fly 60 ft. (hover)»), но комбинация «парение + нет лазанья»
    # проверяет, что модификатор в скобках не утаскивает за собой чужой режим.
    ("30 ft., Fly 60 ft. (hover)", "en", {"walk": 30, "fly": 60, "climb": None}),
    # Вторая живая форма того же режима — из `12_MonstersA-Z.md`.
    ("10 футов, лазание 20 футов", "ru", {"walk": 10, "climb": 20}),
]

failures = []
for line, lang, want_speed in SPEEDS:
    got = _parse_speed(line, lang)
    for key, value in want_speed.items():
        if got.get(key) != value:
            failures.append(f"скорость «{line}» [{lang}] {key}: получили {got.get(key)!r}, "
                            f"ждали {value!r}")
for line, lang, size in NEGATIVE:
    got = _parse_type_line(line, lang)
    if got.get("size") != size:
        failures.append(f"«{line}» [{lang}] size: получили {got.get('size')!r}, ждали {size!r}")
for line, lang, size, ctype, subtype, alignment in CASES:
    got = _parse_type_line(line, lang)
    want = {"size": size, "type": ctype, "subtype": subtype, "alignment": alignment}
    for key, value in want.items():
        if got.get(key) != value:
            failures.append(f"«{line}» [{lang}] {key}: получили {got.get(key)!r}, ждали {value!r}")

if failures:
    print(f"❌ Разбор строки типа ({len(failures)}):")
    for f in failures:
        print(f"  — {f}")
    sys.exit(1)
print(f"✅ Разбор статблока: {len(CASES)} форм строки типа, {len(NEGATIVE)} отрицательных "
      f"случая, {len(SPEEDS)} формы скорости")
