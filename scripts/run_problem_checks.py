"""Wykonaj zwykłe komórki Pythona notebooka kontrolnego problemów."""
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import io
import json
import os
import traceback

root = Path(__file__).resolve().parents[1]
os.chdir(root)
path = root / "notebooks/fala_d_problem_checks.ipynb"
nb = json.loads(path.read_text(encoding="utf-8"))
for cell in nb["cells"]:
    if cell["cell_type"] == "code":
        cell["outputs"] = []
        cell["execution_count"] = None
scope = {"__name__": "__main__"}
count = 0
failure = None
for cell in nb["cells"]:
    if cell["cell_type"] != "code":
        continue
    count += 1
    cell["execution_count"] = count
    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exec(compile("".join(cell["source"]), cell["id"], "exec"), scope)
    except Exception as error:
        failure = error
        cell["outputs"].append({
            "output_type": "error", "ename": type(error).__name__,
            "evalue": str(error), "traceback": traceback.format_exc().splitlines(),
        })
    for name, stream in [("stdout", stdout), ("stderr", stderr)]:
        value = stream.getvalue()
        if value:
            cell["outputs"].insert(0, {
                "output_type": "stream", "name": name,
                "text": value.splitlines(keepends=True),
            })
            print(value, end="")
    if failure is not None:
        break
path.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
if failure is not None:
    raise RuntimeError(f"Przerwano wykonanie w komórce {cell['id']}") from failure
print(f"Wykonano {count} komórek kodu w świeżym procesie Pythona.")
