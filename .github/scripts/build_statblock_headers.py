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

Фикстуру скрипт НЕ перезаписывает: эталон правится осознанно. `--emit` кладёт РЯДОМ
файл-предложение (`<фикстура>.proposed`), который человек сравнивает и переносит руками.

Как пользоваться (после рецепта из build_statblock_fields.py — те же выемки):

    python3 .github/scripts/build_statblock_headers.py            # обе редакции
    python3 .github/scripts/build_statblock_headers.py srd-5.1    # одна
    python3 .github/scripts/build_statblock_headers.py --emit     # + файлы-предложения

Код возврата: 0 — все строки воспроизведены; 1 — есть расхождения или недостающие
строки; 2 — нет входных выемок (внятная ошибка вместо стектрейса).
"""
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


def check(version: str, emit: bool) -> int:
    path = FIXTURES / f"{version}-statblock-headers.tsv"
    if not path.exists():
        print(f"{version}: фикстуры нет: {path}")
        return 1
    table = rows(path)
    heads = pdf_headers(version)
    # Имя в PDF 5.1 идёт без таксономического хвоста, в тексте и эталонах — с ним:
    # сводим по имени без хвоста, как это делает сборщик полей.
    by_stripped = {STRIP_TAIL.sub("", n).strip(): n for n in heads}
    same, differ, missing, proposed = 0, [], [], []
    for number, cells in table:
        name = cells[0]
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
    print(f"{version}: строк {len(table)}, третья колонка воспроизведена из PDF у {same}, "
          f"расходится {len(differ)}, шапки нет в выемках у {len(missing)}")
    for line in differ + missing:
        print(f"  ≠ {line}")
    if emit:
        # Предложение кладём во временный каталог, а не рядом с фикстурой: файл рядом
        # с эталоном рано или поздно уезжает в коммит и начинает выглядеть эталоном.
        out = Path(os.environ.get("SRD_HEADERS_OUT", f"/tmp/{version}-headers.proposed.tsv"))
        head = [line for line in path.read_text(encoding="utf-8").split("\n")
                if line.startswith("#")]
        out.write_text("\n".join(head + proposed) + "\n", encoding="utf-8")
        print(f"  → предложение: {out}")
    return 1 if differ or missing else 0


if __name__ == "__main__":
    wanted = [v for v in VERSIONS if v in sys.argv] or list(VERSIONS)
    emit = "--emit" in sys.argv
    try:
        code = max(check(version, emit) for version in wanted)
    except SystemExit:
        raise
    except FileNotFoundError as error:
        sys.exit(f"нет входной выемки: {error} — сначала рецепт из build_statblock_fields.py")
    sys.exit(code)
