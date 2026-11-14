"""Wykonaj komórki notebooka i zapisz tekstowe wyniki."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path

root = Path(__file__).resolve().parents[1]
os.chdir(root)
os.environ.setdefault("MPLBACKEND", "Agg")
path = root / "notebooks/ch01_measurement_chain.ipynb"
notebook = json.loads(path.read_text(encoding="utf-8"))
scope = {"__name__": "__main__"}
count = 0
for cell in notebook["cells"]:
    if cell["cell_type"] != "code":
        continue
    count += 1
    captured = io.StringIO()
    with redirect_stdout(captured):
        exec(compile("".join(cell["source"]), cell["id"], "exec"), scope)
    output = captured.getvalue()
    cell["execution_count"] = count
    cell["outputs"] = [
        {"output_type": "stream", "name": "stdout", "text": output.splitlines(keepends=True)}
    ] if output else []
    print(output, end="")
path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"Wykonano {count} komórek kodu.")
