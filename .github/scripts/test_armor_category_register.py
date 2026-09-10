#!/usr/bin/env python3
"""Регистр категорий доспеха в прозе (issue #323).

Категория доспеха (Light / Medium / Heavy armor) — термин, и его регистр ЗАВИСИТ ОТ РЕДАКЦИИ,
потому что зависит от оригинала (замер и решение — `src/dnd/translate/logs/2026-09-10_armor_log.md`):

  • EN 5.2 (2024) пишет категорию с прописной сплошь — 30 вхождений в середине фразы, строчных 0
    (`if you aren't wearing Heavy armor`). Значит RU 5.2 — прописная везде.
  • EN 5.1 (2014) в середине фразы пишет строчной — 19 против 4, и те 4 суть перечень внутри
    ячейки таблицы владения. Значит RU 5.1 — строчная, а прописная только ПОЗИЦИОННО: в начале
    строки, ячейки, заголовка или предложения.

Почему гейт, а не «проверили и разошлись»: расхождение регистра не роняет ни сборку, ни e2e, ни
парность EN↔RU (она сверяет количества строк и заголовков, а не слова), и вернуться может любой
правкой перевода. Ровно так класс и накопился: 78 строчных вхождений в 16 файлах 5.2.

Что НЕ проверяется здесь: редкость в шапках магических предметов 5.2 (осталась строчной — другой
термин, отдельная работа) и вообще любые категории вне соседства со словом «доспех».

Механизм (разделитель «категория или обычное прилагательное», позиционность, оба исключения)
прогоняется на синтетике — самопроверки внизу файла.
"""
import re
import sys
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[2] / "src" / "dnd"

# Основа категории. Слева — НЕ буква и НЕ `_`: `\w` включает подчёркивание, и `(?<![\w-])`
# молча промахивался бы на markdown-выделении `_Тяжёлые_` (шрам #321).
CAT_RE = re.compile(r"(?<![^\W\d_])([Лл]ёгк|[Сс]редн|[Тт]яжёл)(\w*)")
ARMOR_NEAR = re.compile(r"доспех|брон[ия]|щит", re.I)
ARMOR_WORD = re.compile(r"^(?:доспех\w*|брон\w*)$", re.I)
ADJ = re.compile(r"^(?:[Лл]ёгк|[Сс]редн|[Тт]яжёл)\w*$")
TOKEN = re.compile(r"[^\W_]+|[(),:*_—-]")
# Склейки, через которые прилагательное всё ещё относится к доспеху: перечисление, «любой»,
# материал, «комплект». Список закрытый: пусти сюда что угодно — и `тяжёлый арбалет, кожаный
# доспех` начнёт считаться категорией.
GLUE = {
    "или", "и", "кроме", "другой", "другого", "другим", "либо", "а", "не",
    "любой", "любого", "любым", "любых", "любая", "любые",
    "металлических", "металлического", "комплект",
}
PUNCT = set("(),:*_—-")

# Места, где автомат ошибается. Обе стороны проверены глазами; и тот и другой перечень
# пришпилен ниже (`stale`-проверка): уйдёт строка из корпуса — гейт скажет об этом, а не
# промолчит с устаревшим исключением.
NOT_CATEGORY = (
    ("srd-5.2/ru/12_MonstersA-Z.md", "Шкурный доспех, лёгкие молоты"),   # свойство оружия
    ("srd-5.2/ru/12_MonstersA-Z.md", "Кожаный доспех, лёгкий арбалет"),  # свойство оружия
)
# Каноническое определение категорий: до слова «доспехов» семь токенов, автомат его не видит,
# а это самое важное место главы.
# Маркер — с упоминанием доспехов: у оружия категории тоже есть («относится к категории:
# Простое или Воинское»), и короткий маркер ловил бы и его строку.
CANON = (
    ("srd-5.2/ru/06_Equipment.md", "Каждый тип доспехов относится к категории", True),
    ("srd-5.1/ru/09_Equipment.md", "разделяет их на три категории", False),
)

failures = []
checks_run = 0


def is_category(line: str, word: str) -> bool:
    """Прилагательное `word` в строке относится к слову «доспех» (а не к молоту или кольцам)."""
    tokens = TOKEN.findall(line)
    for i, tok in enumerate(tokens):
        if tok != word:
            continue
        for step in (1, -1):
            j, walked = i + step, 0
            while 0 <= j < len(tokens) and walked < 10:
                cur = tokens[j]
                if ARMOR_WORD.match(cur):
                    return True
                if cur.lower() in GLUE or ADJ.match(cur) or cur in PUNCT:
                    j += step
                    walked += 1
                    continue
                break
    return False


def positional(line: str, start: int) -> bool:
    """Прописная объяснима позицией: начало строки, ячейки, заголовка или предложения."""
    before = line[:start].rstrip()
    if not before:
        return True
    return bool(re.search(r"(?:[.!?:|#>*_\-]|\))\s*$", before))


def hits(text: str, excused: tuple) -> list:
    """Вхождения категории: (номер строки, слово, прописная ли, позиционное ли)."""
    out = []
    for n, line in enumerate(text.split("\n"), 1):
        if not ARMOR_NEAR.search(line):
            continue
        if any(phrase in line for phrase in excused):
            continue
        for m in CAT_RE.finditer(line):
            lo, hi = max(0, m.start() - 60), min(len(line), m.end() + 60)
            if not ARMOR_NEAR.search(line[lo:hi]):
                continue
            if not is_category(line, m.group(0)):
                continue
            out.append((n, m.group(0), m.group(1)[0].isupper(), positional(line, m.start())))
    return out


if not CORPUS.is_dir():
    print(f"❌ Корпус не найден: {CORPUS}")
    sys.exit(1)

docs = sorted(p for p in CORPUS.glob("srd-*/ru/**/*.md"))
if not docs:
    failures.append(f"{CORPUS}: ни одной RU-главы не найдено — обход дерева сломан")

# Исключения не должны протухать молча.
for rel, phrase in NOT_CATEGORY:
    checks_run += 1
    doc = CORPUS / rel
    if not doc.is_file():
        failures.append(f"{rel}: файла нет, а исключение «{phrase}» на него ссылается")
    elif phrase not in doc.read_text(encoding="utf-8"):
        failures.append(f"{rel}: фразы-исключения «{phrase}» больше нет — запись устарела, убрать")

counted = {"5.1": 0, "5.2": 0}
for doc in docs:
    rel = str(doc.relative_to(CORPUS))
    ver = "5.2" if rel.startswith("srd-5.2/") else "5.1" if rel.startswith("srd-5.1/") else None
    if ver is None:
        continue
    excused = tuple(p for r, p in NOT_CATEGORY if r == rel)
    for line_no, word, upper, pos in hits(doc.read_text(encoding="utf-8"), excused):
        counted[ver] += 1
        if ver == "5.2" and not upper:
            failures.append(f"{rel}:{line_no} — категория доспеха со строчной: «{word}» (EN 5.2 — термин с прописной)")
        if ver == "5.1" and upper and not pos:
            failures.append(f"{rel}:{line_no} — категория доспеха с прописной в середине фразы: «{word}» (EN 5.1 — строчная)")

# Канон: определение категорий обязано нести регистр своей редакции на всех трёх словах.
for rel, marker, want_upper in CANON:
    checks_run += 1
    doc = CORPUS / rel
    if not doc.is_file():
        failures.append(f"{rel}: файла нет, а канон категорий ссылается на него")
        continue
    lines = [ln for ln in doc.read_text(encoding="utf-8").split("\n") if marker in ln]
    if not lines:
        failures.append(f"{rel}: определения категорий («{marker}») больше нет — перенесли или переписали")
        continue
    for line in lines:
        for stem, upper_form in (("лёгк", "Лёгк"), ("средн", "Средн"), ("тяжёл", "Тяжёл")):
            want = upper_form if want_upper else stem
            other = stem if want_upper else upper_form
            if re.search(rf"(?<![^\W\d_]){want}\w*", line):
                continue
            found = re.search(rf"(?<![^\W\d_]){other}\w*", line)
            failures.append(
                f"{rel}: в определении категорий нет «{want}…» — "
                f"{'стоит «' + found.group(0) + '»' if found else 'слова нет вовсе'}"
            )

# ——— Самопроверки механизма на синтетике ———

SYN = [
    ("Если вы носите Тяжёлые доспехи, вы не можете", "Тяжёлые", True, False, True),
    ("если не носите тяжёлые доспехи.", "тяжёлые", True, False, False),
    ("| Владение доспехами | Лёгкие и Средние доспехи |", "Лёгкие", True, True, True),
    ("*Доспех (любой Лёгкий, Средний или Тяжёлый), редкий*", "Тяжёлый", True, False, True),
    ("комплект Тяжёлых или Средних металлических доспехов", "Тяжёлых", True, False, True),
    # Markdown-выделение: `\w` включает `_`, и разбор на `\w+` склеивает `_Тяжёлые` в один
    # токен — вхождение выпадало из счёта молча (шрам #321, проверено мутацией).
    ("**_Тяжёлые доспехи._** Такой доспех мешает двигаться", "Тяжёлые", True, True, True),
    # Известный предел автомата: цепочка перескакивает запятую после «доспех» и цепляется к
    # оружию. Поэтому строка и стоит в NOT_CATEGORY — исключение по фразе, а не по догадке.
    ("**Снаряжение** Шкурный доспех, лёгкие молоты (3)", "лёгкие", True, False, False),
    ("Этот доспех представляет кожаный доспех с тяжёлыми кольцами", "тяжёлыми", False, None, None),
    ("Мифрил — лёгкий, гибкий металл. Доспех из этого материала", "лёгкий", False, None, None),
    ("- **Снаряжение** Тяжёлый арбалет, кожаный доспех, булава", "Тяжёлый", False, None, None),
    ("| Оживлённый доспех | Animated Armor | Средний | Конструкт |", "Средний", False, None, None),
]
for text, word, want_cat, want_pos, want_upper in SYN:
    checks_run += 1
    got = is_category(text, word)
    if got != want_cat:
        failures.append(f"самопроверка: «{word}» в «{text[:48]}…» — категория {got}, ожидалось {want_cat}")
        continue
    if not want_cat:
        continue
    checks_run += 1
    start = text.find(word)
    if positional(text, start) != want_pos:
        failures.append(f"самопроверка: позиционность «{word}» в «{text[:48]}…» — {not want_pos} вместо {want_pos}")
    checks_run += 1
    if word[0].isupper() != want_upper:
        failures.append(f"самопроверка: регистр «{word}» распознан неверно")

# Правило редакции целиком, на синтетических «главах».
checks_run += 1
bad_52 = [h for h in hits("если не носите тяжёлые доспехи.", ()) if not h[2]]
if len(bad_52) != 1:
    failures.append(f"самопроверка: строчная категория в тексте 5.2 не поймана ({len(bad_52)})")
checks_run += 1
ok_51 = hits("| Ношение доспехов | Лёгкие доспехи, средние доспехи |", ())
if not (len(ok_51) == 2 and ok_51[0][3] and not ok_51[1][2]):
    failures.append(f"самопроверка: перечень в ячейке 5.1 разобран неверно: {ok_51}")
checks_run += 1
if hits("**Снаряжение** Шкурный доспех, лёгкие молоты (3)", ("Шкурный доспех, лёгкие молоты",)):
    failures.append("самопроверка: исключение по фразе не выключает строку")
checks_run += 1
if len(hits("Доспехи бывают лёгкие, средние и тяжёлые доспехи", ())) != 3:
    failures.append("самопроверка: цепочка из трёх категорий даёт три вхождения")

if failures:
    print(f"❌ Регистр категорий доспеха: {len(failures)} проблем")
    for f in failures:
        print(f"  — {f}")
    print("\nРешение и замер: src/dnd/translate/logs/2026-09-10_armor_log.md")
    sys.exit(1)
print(
    f"✅ Регистр категорий доспеха: 5.2 — {counted['5.2']} вхождений с прописной, "
    f"5.1 — {counted['5.1']} по позиции; {checks_run} самопроверок"
)
