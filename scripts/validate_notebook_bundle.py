"""Check the frozen executable supplement; do not execute notebooks."""
from pathlib import Path
import hashlib
import json
import nbformat

ROOT = Path(__file__).resolve().parents[1]

def main():
    manifest = json.loads((ROOT / "review/notebook_bundle_manifest.json").read_text(encoding="utf-8"))
    failures = []
    for name, expected in manifest["files_sha256"].items():
        p = ROOT / name
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            failures.append(name)
    if failures:
        raise AssertionError("Missing or changed files: " + ", ".join(failures))
    notebooks = sorted((ROOT / "notebooks").glob("*.ipynb"))
    assert len(notebooks) == 12
    cells = 0
    for p in notebooks:
        nb = nbformat.read(p, as_version=4)
        nbformat.validate(nb)
        cells += sum(c.cell_type == "code" for c in nb.cells)
    assert cells == 132
    freeze = json.loads((ROOT / "config/ch10_freeze.json").read_text(encoding="utf-8"))
    for name, expected in freeze["files_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    nb = json.loads((ROOT / "notebooks/ch10_validation_reproducibility.ipynb").read_text(encoding="utf-8"))
    code = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
    assert hashlib.sha256(json.dumps(code, ensure_ascii=False).encode()).hexdigest() == freeze["notebook_code_sha256"]
    print(json.dumps({"status": "passed", "files": len(manifest["files_sha256"]),
                      "notebooks": len(notebooks), "code_cells": cells,
                      "jupyter_executed_by_this_check": False}, indent=2))

if __name__ == "__main__":
    main()
