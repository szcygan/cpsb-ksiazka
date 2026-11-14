"""Wykonanie od początku: rzeczywiste jądro Jupyter lub zwykły Python.

Bez osadzania figur. Używa bieżącego interpretera i tymczasowego kernelspec,
więc nie zależy od systemowego aliasu python3 ani ręcznej rejestracji jądra.
"""
import argparse
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import sys
import tempfile

import nbformat

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks/ch08_additional_information.ipynb"


def run_plain(notebook):
    scope = {"__name__": "__main__"}
    count = 0
    for cell in notebook.cells:
        if cell.cell_type != "code":
            continue
        count += 1
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            exec(compile(cell.source, cell.id, "exec"), scope)
        cell.execution_count = count
        cell.outputs = []
        for name, buf in [("stdout", out), ("stderr", err)]:
            if buf.getvalue():
                cell.outputs.append(nbformat.v4.new_output("stream", name=name, text=buf.getvalue()))


def run_jupyter(notebook, transport):
    from nbclient import NotebookClient
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpecManager
    with tempfile.TemporaryDirectory(prefix="cpsb-ch08-kernel-") as tmp:
        spec = Path(tmp) / "cpsb-ch08"
        spec.mkdir()
        (spec / "kernel.json").write_text(json.dumps({
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "CPSB ch08", "language": "python",
            "env": {"MPLBACKEND": "Agg"},
        }), encoding='utf-8')
        connection = {"transport": "ipc", "ip": str(Path(tmp) / "kernel-ipc")} if transport == "ipc" else {}
        km = KernelManager(kernel_name="cpsb-ch08", kernel_spec_manager=KernelSpecManager(kernel_dirs=[tmp]), **connection)
        NotebookClient(notebook, km=km, timeout=180, record_timing=False,
                       resources={"metadata": {"path": str(ROOT)}}).execute()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plain-python", action="store_true", help="Jawny wybór domyślnego wykonania komórek przez exec.")
    mode.add_argument("--jupyter", action="store_true", help="Wykonaj przez protokół Jupyter; wymaga dostępnych gniazd lokalnych.")
    parser.add_argument("--transport", choices=["tcp", "ipc"], default="tcp",
                        help="Transport Jupyter; ipc używa lokalnych gniazd Unix zamiast TCP.")
    args = parser.parse_args()
    os.chdir(ROOT)
    os.environ["MPLBACKEND"] = "Agg"
    notebook = nbformat.read(NB, as_version=4)
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
        cell.metadata.pop("execution", None)
    if args.jupyter:
        run_jupyter(notebook, args.transport)
    else:
        run_plain(notebook)
    count = 0
    for cell in notebook.cells:
        if cell.cell_type == "code":
            count += 1
            merged = []
            for output in cell.outputs:
                if output.output_type != "stream":
                    raise RuntimeError("Nieoczekiwany wynik komórki: " + output.output_type)
                if merged and merged[-1].name == output.name:
                    merged[-1].text += output.text
                else:
                    merged.append(output)
            cell.outputs = merged
            for output in cell.outputs:
                print(output.text, end="")
    notebook.metadata.cpsb.update({
        "status": "rekonstrukcja R08, 2026-11-11",
        "execution": {"method": "Jupyter kernel protocol, fresh kernel" if args.jupyter else "plain Python in fresh process",
                      "status": "passed", "kernel_protocol_tested": args.jupyter,
                      "code_cells": count,
                      "transport": args.transport if args.jupyter else None},
    })
    # Usuwamy opcjonalne metadane wersji jądra, aby nie mieszać ich z ENV.
    import platform
    notebook.metadata.language_info = {"name": "python", "version": platform.python_version()}
    nbformat.validate(notebook)
    nbformat.write(notebook, NB)
    print(f"Wykonano {count} komórek kodu; tryb: {'Jupyter' if args.jupyter else 'Python'}.")


if __name__ == "__main__":
    main()
