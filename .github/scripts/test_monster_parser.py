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
Fly 20 ft.» (число относится к ОБОИМ режимам) живёт у одного Роя насекомых. Русская
форма лазанья одна, словарная («Скорость лазания», «Паучье лазание»): корпус 5.2 был
расщеплён по «лазанье»/«лазание» и сведён к ней (#270), а до этого словарь парсера знал
только одну из двух форм, и у 30 блоков climb молча уезжал пустым.

Запуск: python3 .github/scripts/test_monster_parser.py
"""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]
sys.path.insert(0, str(SCRIPTS))
import config  # noqa: E402
from parsers.monster import _parse_speed, _parse_type_line, parse_monsters  # noqa: E402

# Строки, кроме перечисленных в SYNTHETIC, взяты из корпуса ДОСЛОВНО — и это проверяется
# ниже, а не обещается комментарием: правка корпуса без правки таблицы отнимала у неё
# свойство «эталон воспроизводит источник» молча (так разъехалась строка «Огромный или
# меньший Конструкт» при сведении регистра врезок — #271, ревью #281).
SYNTHETIC = {
    # Подтип с запятой внутри скобок: такой пары в корпусе нет, форма из PDF 5.1.
    "*Medium Fiend (Demon, Shapechanger), Chaotic Evil*",
    # Женский и средний род границы диапазона: в корпусе живёт только мужской, а согласие
    # рода — правило языка, а не факт корпуса.
    "*Огромная или меньшая тварь, без мировоззрения*",
    "*Огромное или меньшее чудовище, без мировоззрения*",
}
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
    ("*Огромный или меньший Конструкт, без мировоззрения*", "ru",
     "Огромный или меньший", "Конструкт", None, "без мировоззрения"),
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
# Корпус RU 5.2 был расщеплён по слову: «лазанье» против «лазание» — 30 строк скорости
# против 23. Сведён к словарной форме «лазание» (#270), она же закреплена здесь. До этого
# словарь знал только «лазание», и у 30 блоков с «лазанье» climb уезжал пустым, а тест
# этого не видел.
SPEEDS = [
    ("20 ft., Climb or Fly 20 ft. (GM's choice)", "en", {"walk": 20, "climb": 20, "fly": 20}),
    ("20 футов, лазание или полёт 20 футов (на выбор Мастера)", "ru",
     {"walk": 20, "climb": 20, "fly": 20}),
    # Единственная СИНТЕТИЧЕСКАЯ запись здесь: такой строки в корпусе нет (у Аватара
    # смерти написано «60 ft., fly 60 ft. (hover)»), но комбинация «парение + нет лазанья»
    # проверяет, что модификатор в скобках не утаскивает за собой чужой режим.
    ("30 ft., Fly 60 ft. (hover)", "en", {"walk": 30, "fly": 60, "climb": None}),
    # Простая форма того же режима — из `12_MonstersA-Z.md`.
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
# Провенанс таблицы: несинтетическая строка обязана встречаться в корпусе ДОСЛОВНО.
# Иначе таблица тихо превращается в набор придуманных форм — а её ценность именно в том,
# что разбор проверяется на том, что реально написано в главах.
# Корпус для провенанса — только ГЛАВЫ редакций: логи перевода и словари сами цитируют
# формы шапок, и строка, убранная из главы, но дописанная в лог, засчитывалась бы
# корпусом (ревью #281).
_corpus = "\n".join(p.read_text(encoding="utf-8")
                    for p in sorted((ROOT / "src/dnd").glob("srd-*/[er][nu]/**/*.md")))
for _line in sorted(SYNTHETIC - {c[0] for c in CASES}):
    failures.append(f"«{_line}» объявлена синтетической, но такой строки в CASES нет — "
                    f"уберите её из SYNTHETIC (иначе число «из корпуса дословно» занижено)")
for line, *_ in CASES:
    if line not in SYNTHETIC and line not in _corpus:
        failures.append(f"«{line}» — строки нет в корпусе: либо правьте таблицу под текст, "
                        f"либо объявите её синтетической в SYNTHETIC")
    if line in SYNTHETIC and line in _corpus:
        failures.append(f"«{line}» объявлена синтетической, но в корпусе она есть — "
                        f"снимите её из SYNTHETIC")
for line, lang, size, ctype, subtype, alignment in CASES:
    got = _parse_type_line(line, lang)
    want = {"size": size, "type": ctype, "subtype": subtype, "alignment": alignment}
    for key, value in want.items():
        if got.get(key) != value:
            failures.append(f"«{line}» [{lang}] {key}: получили {got.get(key)!r}, ждали {value!r}")

# --- Зеркало полей EN↔RU на ЖИВОМ корпусе ---------------------------------------------
# Синтетические формы выше проверяют разбор строки, но не то, что разобранное доезжает до
# JSON API у обеих половин. Метки RU у редакций расходятся числом («Сопротивления» у 5.2,
# «Сопротивление к урону» у 5.1), и пока словарь знал одну форму, четыре поля защит у 317
# монстров 5.1 уезжали в API пустыми — молча, потому что живого гейта на API нет (#269).
# Считаем ПО ПОЛЯМ: у скольких блоков поле непустое. Числа обязаны совпасть у EN и RU.
DECLARED_GAPS = {
    # Русское имя оригинала есть только у RU-половины — так устроен формат.
    "name_en",
}
# Зеркало сверяет ЧИСЛА, а не состав, поэтому согласованная потеря у ОБЕИХ половин
# (EN 0 = RU 0) ему не видна. Для полей статблока вторую половину класса держит эталон
# полей (`test_statblock_fields.py`), а ссылки на заклинания в эталон не входят — их
# держит этот пин: минимум непустых значений по главе.
MIN_NON_EMPTY = {
    ("srd51", "monsters"): {"spells": 36},
}
by_source = {}
for src in getattr(config, "SOURCES", []):
    if src["type"] != "monster":
        continue
    text = (ROOT / "src/dnd" / src["file"]).read_text(encoding="utf-8")
    entities = parse_monsters(text, src["h"], src["lang"], src.get("after"),
                              getattr(config, "SKIP_HEADINGS_MONSTER", set()))
    by_source.setdefault((src["ver"], src.get("out", "monsters")), {})[src["lang"]] = entities

for (ver, out), halves in sorted(by_source.items()):
    if set(halves) != {"en", "ru"}:
        failures.append(f"{ver}/{out}: нет обеих половин корпуса ({sorted(halves)})")
        continue
    if len(halves["en"]) != len(halves["ru"]):
        failures.append(f"{ver}/{out}: блоков EN {len(halves['en'])}, RU {len(halves['ru'])}")
    # Поля верхнего уровня — и ОТДЕЛЬНО режимы внутри скорости: «speed» непусто у обеих
    # половин, даже когда режим потерян, поэтому счёт по полю climb/fly/swim не видит.
    # Ровно так и терялся climb у 30 блоков, пока корпус писал слово двумя способами.
    fields = sorted({k for e in halves["en"] for k in e} | DECLARED_GAPS)
    fields += [f"speed.{mode}" for mode in ("walk", "fly", "swim", "climb", "burrow")]
    for field in fields:
        if field in DECLARED_GAPS:
            continue
        if field.startswith("speed."):
            mode = field.split(".", 1)[1]
            counts = {lang: sum(1 for e in halves[lang] if (e.get("speed") or {}).get(mode))
                      for lang in ("en", "ru")}
        else:
            counts = {lang: sum(1 for e in halves[lang]
                                if e.get(field) not in (None, "", [], {}))
                      for lang in ("en", "ru")}
        if counts["en"] != counts["ru"]:
            failures.append(f"{ver}/{out}: поле «{field}» непусто у EN {counts['en']} блоков, "
                            f"у RU {counts['ru']} — половины JSON API разошлись")
        floor = MIN_NON_EMPTY.get((ver, out), {}).get(field)
        if floor is not None and min(counts.values()) < floor:
            failures.append(f"{ver}/{out}: поле «{field}» непусто у EN {counts['en']} и RU "
                            f"{counts['ru']} блоков, а по корпусу должно быть хотя бы "
                            f"{floor} — потеряно у обеих половин сразу")

if failures:
    print(f"❌ Разбор статблока ({len(failures)}):")
    for f in failures:
        print(f"  — {f}")
    sys.exit(1)
print(f"✅ Разбор статблока: {len(CASES)} форм строки типа "
      f"({len(CASES) - len(SYNTHETIC)} из корпуса дословно), {len(NEGATIVE)} отрицательных "
      f"случая, {len(SPEEDS)} формы скорости; зеркало полей EN↔RU сходится на "
      f"{len(by_source)} главах корпуса")
