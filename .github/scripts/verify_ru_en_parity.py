#!/usr/bin/env python3
"""Верификация паритета RU↔EN по длинам каждой сущности.

Ловит рассинхрон перевода (напр. остатки 5.1: пропущенный контент, урезанные
описания) независимо от ПОРЯДКА сущностей в главе — сверка идёт по slug, а не по
строкам. Для каждого ресурса и каждого slug сравнивает суммарную длину текста
(description_md + все *_md/list text_md) EN vs RU.

Использование:
    python3 .github/scripts/verify_ru_en_parity.py [--api-dir DIR] [--game dnd]
            [--version srd52] [--low 0.8] [--high 1.4] [--strict]

--api-dir  корень сгенерированного JSON API (по умолчанию web/src/data/api)
--strict   ненулевой код возврата и при length-флагах (по умолчанию — только при
           отсутствующих/лишних slug)

Выход: отчёт по ресурсам + список подозрительных сущностей. Код возврата 1, если
есть отсутствующие slug (или length-флаги при --strict).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ресурсы для проверки (у которых есть переводимый текст). Порядок — для отчёта.
RESOURCES = ["spells", "monsters", "magic-items", "conditions", "feats", "equipment"]


def text_len(entity: dict) -> int:
    """Суммарная длина переводимого текста сущности (все *_md поля)."""
    total = 0
    for key, val in entity.items():
        if not key.endswith("_md"):
            continue
        if isinstance(val, str):
            total += len(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict) and isinstance(item.get("text_md"), str):
                    total += len(item["text_md"])
    return total


def load(api_dir: Path, game: str, version: str, lang: str, resource: str) -> dict[str, dict]:
    path = api_dir / game / version / lang / resource / "all.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {e["slug"]: e for e in data if e.get("slug")}


def check_resource(api_dir: Path, game: str, version: str, resource: str,
                   low: float, high: float) -> tuple[list[str], list[str]]:
    """Возвращает (hard_errors, warnings) для ресурса."""
    en = load(api_dir, game, version, "en", resource)
    ru = load(api_dir, game, version, "ru", resource)
    if not en and not ru:
        return [], []  # ресурса нет — пропускаем

    hard: list[str] = []
    warn: list[str] = []

    only_en = sorted(set(en) - set(ru))
    only_ru = sorted(set(ru) - set(en))
    for s in only_en:
        hard.append(f"[{resource}] slug есть в EN, нет в RU: {s}")
    for s in only_ru:
        hard.append(f"[{resource}] slug есть в RU, нет в EN: {s}")

    flagged = []
    for slug in sorted(set(en) & set(ru)):
        le, lr = text_len(en[slug]), text_len(ru[slug])
        if le < 120:  # слишком короткие (напр. только стат-блок) — пропускаем
            continue
        ratio = lr / le if le else 0
        if ratio < low or ratio > high:
            flagged.append((ratio, slug, le, lr))
    flagged.sort()
    for ratio, slug, le, lr in flagged:
        warn.append(f"[{resource}] {slug}: RU/EN={ratio:.2f} (EN {le} / RU {lr})")

    shared = len(set(en) & set(ru))
    print(f"  {resource}: EN {len(en)} / RU {len(ru)}, общих {shared}, "
          f"вне [{low}, {high}]: {len(flagged)}"
          + (f", ОТСУТСТВУЮТ: {len(only_en) + len(only_ru)}" if (only_en or only_ru) else ""))
    return hard, warn


def main() -> int:
    ap = argparse.ArgumentParser(description="Верификация паритета RU↔EN по длинам сущностей")
    ap.add_argument("--api-dir", default="web/src/data/api")
    ap.add_argument("--game", default="dnd")
    ap.add_argument("--version", default="srd52")
    ap.add_argument("--low", type=float, default=0.8,
                    help="нижний порог RU/EN (короче — подозрение на потерю контента)")
    ap.add_argument("--high", type=float, default=1.4, help="верхний порог RU/EN")
    ap.add_argument("--strict", action="store_true", help="ошибка и при length-флагах")
    args = ap.parse_args()

    api_dir = Path(args.api_dir)
    if not api_dir.exists():
        print(f"ОШИБКА: не найден API-каталог {api_dir}. Сгенерируйте данные "
              f"(web/scripts/gen-entity-data.mjs).", file=sys.stderr)
        return 2

    print(f"Верификация паритета RU↔EN: {args.game}/{args.version} (порог RU/EN [{args.low}, {args.high}])")
    all_hard: list[str] = []
    all_warn: list[str] = []
    for resource in RESOURCES:
        hard, warn = check_resource(api_dir, args.game, args.version, resource, args.low, args.high)
        all_hard += hard
        all_warn += warn

    if all_warn:
        print(f"\nПодозрительные по длине ({len(all_warn)}) — сверьте контент EN↔RU:")
        for w in all_warn:
            print("  ⚠ " + w)
    if all_hard:
        print(f"\nОТСУТСТВУЮЩИЕ/ЛИШНИЕ slug ({len(all_hard)}):", file=sys.stderr)
        for h in all_hard:
            print("  ✗ " + h, file=sys.stderr)

    ok = not all_hard and (not args.strict or not all_warn)
    print("\n" + ("✓ Паритет в норме" if ok else "✗ Есть расхождения (см. выше)"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
