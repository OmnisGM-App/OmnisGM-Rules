#!/usr/bin/env python3
"""
PDF to Markdown converter — runs 3 converters and produces statistics.

Usage:
    python3 convert_pdf.py <pdf_path> <prefix>

`prefix` — opaque имя для /tmp-артефактов; пайплайн передаёт `{game}_{version}`
(см. SKILL.md), чтобы прогоны разных версий не перезаписывали друг друга.

Output files:
    /tmp/{prefix}_marker.md
    /tmp/{prefix}_pymupdf.md
    /tmp/{prefix}_docling.md

Each converter runs in its own venv (/tmp/venv-{tool}/).
Missing venvs are created automatically.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


def check_venv(tool: str) -> bool:
    venv = Path(f"/tmp/venv-{tool}")
    return venv.exists() and (venv / "bin" / "python3").exists()


def install_venv(tool: str) -> bool:
    pkg_map = {"marker": "marker-pdf", "pymupdf": "pymupdf4llm", "docling": "docling"}
    venv = f"/tmp/venv-{tool}"
    pkg = pkg_map[tool]
    print(f"  Installing {pkg} into {venv}...")
    try:
        subprocess.run(["python3", "-m", "venv", venv], check=True, capture_output=True)
        subprocess.run([f"{venv}/bin/pip", "install", "-q", pkg], check=True, capture_output=True, timeout=300)
        print(f"  {tool}: installed OK")
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"  {tool}: INSTALL FAILED — {e}")
        return False


def run_marker(pdf_path: str, game: str) -> dict:
    output_dir = f"/tmp/{game}_marker"
    output_file = f"/tmp/{game}_marker.md"
    if Path(output_dir).exists():
        shutil.rmtree(output_dir)
    Path(output_dir).mkdir(parents=True)

    env = os.environ.copy()
    env["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"

    cmd = [
        f"/tmp/venv-marker/bin/marker_single", pdf_path,
        "--output_dir", output_dir,
        "--disable_ocr", "--disable_image_extraction"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)
        # Find output .md
        md_files = list(Path(output_dir).rglob("*.md"))
        if md_files:
            shutil.copy(md_files[0], output_file)
            return {"status": "ok", "file": output_file, "stderr": result.stderr[-500:] if result.stderr else ""}
        return {"status": "error", "error": "No .md output found", "stderr": result.stderr[-500:] if result.stderr else ""}
    except subprocess.TimeoutExpired:
        # Fallback: try with CPU
        env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
        cmd.extend(["--lowres_image_dpi", "72"])
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)
            md_files = list(Path(output_dir).rglob("*.md"))
            if md_files:
                shutil.copy(md_files[0], output_file)
                return {"status": "ok", "file": output_file, "note": "CPU fallback used"}
            return {"status": "error", "error": "No .md output (CPU fallback)"}
        except Exception as e:
            return {"status": "error", "error": f"CPU fallback failed: {e}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def run_pymupdf(pdf_path: str, game: str) -> dict:
    output_file = f"/tmp/{game}_pymupdf.md"
    script = f"""
import pymupdf4llm
import pathlib
md_text = pymupdf4llm.to_markdown('{pdf_path}')
pathlib.Path('{output_file}').write_text(md_text)
print(f'OK: {{len(md_text)}} chars, {{md_text.count(chr(10))}} lines')
"""
    try:
        result = subprocess.run(
            ["/tmp/venv-pymupdf/bin/python3", "-c", script],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0 and Path(output_file).exists():
            return {"status": "ok", "file": output_file}
        return {"status": "error", "error": result.stderr[-500:] if result.stderr else "Unknown error"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def run_docling(pdf_path: str, game: str) -> dict:
    output_file = f"/tmp/{game}_docling.md"
    script = f"""
from docling.document_converter import DocumentConverter
converter = DocumentConverter()
result = converter.convert('{pdf_path}')
md_text = result.document.export_to_markdown()
with open('{output_file}', 'w') as f:
    f.write(md_text)
print(f'OK: {{len(md_text)}} chars, {{md_text.count(chr(10))}} lines')
"""
    try:
        result = subprocess.run(
            ["/tmp/venv-docling/bin/python3", "-c", script],
            capture_output=True, text=True, timeout=3600  # docling is slow
        )
        if result.returncode == 0 and Path(output_file).exists():
            return {"status": "ok", "file": output_file}
        return {"status": "error", "error": result.stderr[-500:] if result.stderr else "Unknown error"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def file_stats(filepath: str) -> dict:
    if not Path(filepath).exists():
        return {"lines": 0, "headings": 0, "tables": 0, "size_kb": 0}
    text = Path(filepath).read_text(encoding="utf-8")
    lines = text.count("\n")
    headings = len(re.findall(r"^#+\s", text, re.MULTILINE))
    tables = len(re.findall(r"^\|", text, re.MULTILINE))
    size_kb = Path(filepath).stat().st_size // 1024
    return {"lines": lines, "headings": headings, "tables": tables, "size_kb": size_kb}


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <pdf_path> <game>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    game = sys.argv[2]

    if not Path(pdf_path).exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    print(f"Converting: {pdf_path} (game={game})")
    print()

    # Check/install venvs
    tools = ["marker", "pymupdf", "docling"]
    for tool in tools:
        if check_venv(tool):
            print(f"  {tool}: venv OK")
        else:
            if not install_venv(tool):
                print(f"  WARNING: {tool} not available")
    print()

    # Run converters
    converters = {
        "marker": run_marker,
        "pymupdf": run_pymupdf,
        "docling": run_docling,
    }

    results = {}
    for name, func in converters.items():
        if not check_venv(name):
            results[name] = {"status": "skipped", "error": "venv not installed"}
            continue
        print(f"Running {name}...")
        start = time.time()
        results[name] = func(pdf_path, game)
        elapsed = time.time() - start
        results[name]["time_seconds"] = round(elapsed, 1)
        status = results[name]["status"]
        print(f"  {name}: {status} ({elapsed:.1f}s)")
    print()

    # Statistics
    ok_count = sum(1 for r in results.values() if r["status"] == "ok")
    if ok_count < 2:
        print(f"ERROR: Only {ok_count} converter(s) succeeded. Minimum 2 required.")
        sys.exit(1)

    print("| Конвертер   | Строк | Заголовков | Таблиц | Размер  | Время   |")
    print("|-------------|-------|------------|--------|---------|---------|")
    for name in tools:
        r = results[name]
        if r["status"] == "ok":
            s = file_stats(r["file"])
            print(f"| {name:<11} | {s['lines']:>5} | {s['headings']:>10} | {s['tables']:>6} | {s['size_kb']:>4} KB | {r['time_seconds']:>5.0f}s  |")
        else:
            print(f"| {name:<11} | FAIL  | —          | —      | —       | —       |")
    print()

    print("Файлы:")
    for name in tools:
        r = results[name]
        if r["status"] == "ok":
            print(f"  /tmp/{game}_{name}.md")
        else:
            print(f"  /tmp/{game}_{name}.md — НЕ СОЗДАН ({r.get('error', 'unknown')})")

    # Save results JSON for downstream use
    summary = {
        "pdf_path": pdf_path,
        "game": game,
        "converters": {
            name: {
                "status": r["status"],
                "file": r.get("file"),
                "time_seconds": r.get("time_seconds"),
                "stats": file_stats(r["file"]) if r["status"] == "ok" else None,
                "error": r.get("error"),
            }
            for name, r in results.items()
        },
        "ok_count": ok_count,
    }
    summary_path = f"/tmp/{game}_convert_summary.json"
    Path(summary_path).write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nСводка: {summary_path}")


if __name__ == "__main__":
    main()
