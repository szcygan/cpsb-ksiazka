"""Wykonaj kod notebooka w świeżym procesie i zapisz wyjścia tekstowe."""
import argparse
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--development-only", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
os.chdir(root)
os.environ.setdefault("MPLBACKEND", "Agg")
path = root / "notebooks/ch10_validation_reproducibility.ipynb"
notebook = json.loads(path.read_text(encoding="utf-8"))
scope = {"__name__": "__main__"}
count = 0
for cell in notebook["cells"]:
    if cell["cell_type"] != "code":
        continue
    source = "".join(cell["source"])
    if args.development_only and "# CH10_LOCKED_TEST:" in source:
        break
    count += 1
    captured = io.StringIO()
    with redirect_stdout(captured):
        exec(compile(source, cell["id"], "exec"), scope)
    output = captured.getvalue()
    cell["execution_count"] = count
    cell["outputs"] = [
        {"output_type": "stream", "name": "stdout", "text": output.splitlines(keepends=True)}
    ] if output else []
    print(output, end="")
if not args.development_only:
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"Wykonano {count} komórek kodu.")
