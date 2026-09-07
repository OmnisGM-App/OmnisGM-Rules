#!/usr/bin/env python3
"""Сверка ТРЕТЬЕЙ колонки фикстур шапок статблоков с официальным PDF (issue #273).

Зачем отдельный скрипт. Фикстура шапок (`fixtures/srd-*-statblock-headers.tsv`) держит
три колонки: имя, ожидаемая шапка и строка PDF как есть. Гейт сверяет вторую с третьей
после нормализации регистра — но сам к первоисточнику не ходит: PDF и три конвертера на
раннере CI недоступны. Значит, согласованная правка ОБЕИХ колонок гейту не видна, и
«третья колонка — это PDF» до сих пор было утверждением без прогона. Здесь оно
становится прогоном: каждая строка третьей колонки воспроизводится из выемок PDF, и
любой остаток — расхождение, а не сноска.

Выемки берутся у сборщика полей (`build_statblock_fields.py`) — те же самые, с теми же
переменными окружения и той же нормализацией. Своя копия разбора PDF была бы вторым
местом для расхождения ровно там, где мы боремся именно с расхождениями.

Фикстуру скрипт НЕ перезаписывает: эталон правится осознанно. `--emit` кладёт файл-
предложение во временный каталог (`/tmp/<редакция>-headers.proposed.tsv`, путь можно
задать переменными `SRD51_HEADERS_OUT` / `SRD52_HEADERS_OUT`), который человек сравнивает
и переносит руками. Чужой файл по этому пути не затирается — только своё прежнее
предложение, узнаваемое по первой строке-маркеру (перезаписать всё равно — `--force`).

Как пользоваться (после рецепта из build_statblock_fields.py — те же выемки):

    python3 .github/scripts/build_statblock_headers.py            # обе редакции
    python3 .github/scripts/build_statblock_headers.py srd-5.1    # одна
    python3 .github/scripts/build_statblock_headers.py --emit     # + файлы-предложения

Код возврата: 0 — все строки воспроизведены и состав сошёлся с эталоном полей;
1 — расхождение, недостающая строка или лишний блок. Отсутствие входной выемки — не код
возврата, а внятное сообщение с выходом (`sys.exit` со строкой), как и отказ записать
предложение поверх чужого файла.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_statblock_fields as B  # noqa: E402
from statblock_meta import STRIP_TAIL  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
VERSIONS = ("srd-5.1", "srd-5.2")


def rows(path: Path) -> list:
    """[(номер строки, [колонки])] — комментарии и пустые строки пропущены."""
    out = []
    for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        if not line.strip() or line.startswith("#"):
            continue
        out.append((number, line.rstrip("\n").split("\t")))
    return out


def pdf_headers(version: str) -> dict:
    """{имя → шапка} из выемок PDF этой редакции."""
    blocks = B.extractions_51() if version == "srd-5.1" else B.extractions()
    return {name: block["header"] for name, block in blocks.items() if "header" in block}


def chapter_blocks(version: str):
    """({имя → блок} глав монстров из эталона полей, проблема чтения или None).

    Это то, что обязано иметь строку в фикстуре шапок: врезки (`outside_chapters`) и
    статблоки объектов (`object_block`) исключены — первые живут в главах предметов и
    заклинаний, у вторых шапки нет вовсе.

    Битый или неполный эталон полей — реальный вход второго эшелона (сборщик полей
    прерван на середине записи, файл правится руками), и ронять им отчёт трейсбеком
    нельзя: тогда пропадает и всё, что уже найдено по этой редакции.
    """
    path = FIXTURES / f"{version}-statblock-fields.json"
    try:
        blocks = json.loads(path.read_text(encoding="utf-8"))["blocks"]
        items = list(blocks.items())
    except (OSError, ValueError, KeyError, AttributeError) as error:
        return {}, f"эталон полей не читается ({error}) — состав сверить не с чем"
    return {name: block for name, block in items
            if "header" in block and not block.get("outside_chapters")
            and not block.get("object_block")}, None


def check(version: str, emit: bool) -> int:
    path = FIXTURES / f"{version}-statblock-headers.tsv"
    if not path.exists():
        print(f"{version}: фикстуры нет: {path}")
        return 1
    table = rows(path)
    heads = pdf_headers(version)
    # Имя в PDF 5.1 идёт без таксономического хвоста; в фикстурах ШАПОК его нет ни у
    # одной строки, поэтому сегодня имена совпадают напрямую и эта ветка не срабатывает.
    # Оставлена защитой на случай, когда хвост появится с одной из сторон, — как он уже
    # есть в эталоне ПОЛЕЙ (77 имён 5.1).
    by_stripped = {STRIP_TAIL.sub("", n).strip(): n for n in heads}
    same, differ, missing, proposed = 0, [], [], []
    for number, cells in table:
        name = cells[0]
        # Битую строку не роняем трейсбеком, а называем: фикстура правится руками, и
        # первая же строка из одной колонки иначе уносила бы весь прогон, включая
        # вторую редакцию.
        if len(cells) < 2 or not cells[1].strip():
            differ.append(f"строка {number}: «{name}» — строка фикстуры не разбирается, "
                          f"колонок {len(cells)}")
            continue
        raw = cells[2] if len(cells) > 2 and cells[2].strip() else None
        got = heads.get(name) or heads.get(by_stripped.get(STRIP_TAIL.sub("", name).strip(), ""))
        proposed.append("\t".join([name, cells[1], got if got else (raw or "")]))
        if got is None:
            missing.append(f"строка {number}: «{name}» — выемки PDF не дают шапки")
            continue
        if raw is None:
            differ.append(f"строка {number}: «{name}» — третьей колонки нет, в PDF «{got}»")
        elif B.norm(raw) != B.norm(got):
            differ.append(f"строка {number}: «{name}»: фикстура «{raw}» ≠ PDF «{got}»")
        else:
            same += 1
    # Полнота — В ОБЕ стороны: недобравший эталон иначе неотличим от полного. Что именно
    # обязано быть в фикстуре шапок, спрашиваем у эталона ПОЛЕЙ: он знает состав блоков
    # поимённо и отдельно помечает врезки (`outside_chapters`), которых в фикстуре шапок
    # нет по построению. Сама выемка PDF на эту роль не годится — в ней есть строки прозы,
    # начинающиеся со слова размера («many as twenty Medium creatures can surround a»).
    in_fixture = {STRIP_TAIL.sub("", cells[0]).strip() for _, cells in table}
    chapters, problem = chapter_blocks(version)
    if problem:
        differ.append(problem)
    extra = sorted(STRIP_TAIL.sub("", name).strip() for name in chapters
                   if STRIP_TAIL.sub("", name).strip() not in in_fixture)
    # «Воспроизведена» — с точностью до нормализации `norm()` (пробелы и хвостовая
    # пунктуация): точное равенство держит CI-гейт, здесь сверяется содержание.
    print(f"{version}: строк {len(table)}, третья колонка воспроизведена из PDF "
          f"(с точностью до пробелов и хвостовой пунктуации) у {same}, "
          f"расходится {len(differ)}, шапки нет в выемках у {len(missing)}, "
          f"нет строки в фикстуре у {len(extra)} блоков глав")
    for line in differ + missing:
        print(f"  ≠ {line}")
    for name in extra:
        print(f"  + «{name}» — блок главы есть в эталоне полей, строки в фикстуре шапок нет")
    if emit:
        write_proposal(version, path, proposed)
    return 1 if differ or missing or extra else 0


MARKER = "# предложение build_statblock_headers.py — НЕ эталон, переносить руками"


def write_proposal(version: str, fixture: Path, proposed: list) -> None:
    """Файл-предложение на диск: свой прежний перезаписываем, чужой — нет.

    Путь у каждой редакции СВОЙ (переменные `SRD51_HEADERS_OUT` / `SRD52_HEADERS_OUT`):
    общий путь на обе редакции молча оставлял в файле только последнюю. Провенанс из
    шапки фикстуры не копируем: предложение пересобирают как раз тогда, когда сменился
    PDF, и старые `_source` в нём — метаданные ПРЕЖНЕГО источника.
    """
    env = "SRD51_HEADERS_OUT" if version == "srd-5.1" else "SRD52_HEADERS_OUT"
    out = Path(os.environ.get(env, f"/tmp/{version}-headers.proposed.tsv"))
    if os.path.isdir(out):
        sys.exit(f"{env}={out} — это каталог, а не файл: предложение не записано")
    # lexists, а не exists: висячий симлинк «не существует» для exists(), и запись по нему
    # создала бы цель ссылки — худшая форма «затереть чужое».
    if os.path.lexists(out) and "--force" not in sys.argv:
        try:
            with open(out, encoding="utf-8", errors="replace") as fh:
                head = fh.readline()
        except OSError as error:
            sys.exit(f"{env}={out} существует, но не читается ({error}) — перезапись отменена")
        if head.rstrip("\r\n") != MARKER:
            sys.exit(f"{out} — не выход этого скрипта по {env} (первая строка не та): "
                     f"перезапись отменена. Задайте другой путь в {env} или прогоните "
                     f"с --force")
    body = [MARKER, f"# редакция {version}, эталон рядом: {fixture.name}"] + proposed
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text("\n".join(body) + "\n", encoding="utf-8")
    os.replace(tmp, out)
    print(f"  → предложение: {out}")


if __name__ == "__main__":
    unknown = [a for a in sys.argv[1:]
               if a.startswith("srd-") and a not in VERSIONS]
    if unknown:
        sys.exit(f"неизвестная редакция: {', '.join(unknown)} — известны {', '.join(VERSIONS)}")
    wanted = [v for v in VERSIONS if v in sys.argv] or list(VERSIONS)
    emit = "--emit" in sys.argv
    try:
        code = max(check(version, emit) for version in wanted)
    except SystemExit:
        raise
    except FileNotFoundError as error:
        # Только ЧТЕНИЕ входов: ошибки записи предложения свои и сообщают о себе сами,
        # иначе успешная сверка заканчивалась бы советом «прогоните конвертеры».
        sys.exit(f"нет входа: {error} — сначала рецепт из build_statblock_fields.py")
    sys.exit(code)
