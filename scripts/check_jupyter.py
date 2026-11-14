"""Sprawdź protokół Jupyter bez nadpisywania źródłowych notebooków.

Uruchomienie w docelowym środowisku: python scripts/check_jupyter.py --all
Wymaga lokalnych gniazd TCP. Błąd startu jądra nie jest zaliczeniem testu.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from prepare_frozen_handoff import prepare
from execution_context import input_context

ROOT = Path(__file__).resolve().parents[1]


def code_hash(notebook):
    sources = [c.source for c in notebook.cells if c.cell_type == 'code']
    return hashlib.sha256(json.dumps(sources, ensure_ascii=False).encode('utf-8')).hexdigest()


def resumed_results(paths, source):
    """Reuse only explicit successful evidence with matching source code."""
    if source is None:
        return {}
    raw = source.read_bytes()
    try:
        text = raw.decode('utf-8-sig')
        evidence_encoding = 'utf-8'
    except UnicodeDecodeError:
        # Raport pierwszej wersji skryptu na polskim Windows mógł być cp1250.
        text = raw.decode('cp1250')
        evidence_encoding = 'cp1250 (legacy report)'
    previous = json.loads(text)
    if previous.get('execution') != 'actual Jupyter kernel protocol':
        raise ValueError('Raport wznowienia nie pochodzi z rzeczywistego protokołu Jupyter.')
    legacy = json.loads((ROOT/'review/utf8_patch_U01.json').read_text(encoding='utf-8'))['legacy_resume_allowlist']
    selected = {p.name: p for p in paths}
    unchanged = json.loads((ROOT/'review/d01/legacy_unaffected_notebooks.json').read_text(encoding='utf-8'))
    protected = json.loads(((ROOT/'review/b05_03/scope_guard.json' if (ROOT/'review/b05_03/scope_guard.json').exists() else ROOT/'review/b05_02/scope_guard.json' if (ROOT/'review/b05_02/scope_guard.json').exists() else ROOT/'review/d01/scope_guard.json')).read_text(encoding='utf-8'))['protected_files_sha256']
    legacy_inputs_unchanged = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == digest
                                  for p,digest in protected.items())
    restored = {}
    for row in previous.get('results', []):
        name = row.get('notebook')
        if row.get('status') != 'passed' or name not in selected:
            continue
        if name in restored:
            raise ValueError('Powtórzona pozycja w raporcie wznowienia: '+name)
        nb = nbformat.read(selected[name], as_version=4)
        digest = code_hash(nb)
        expected = row.get('source_code_sha256') or legacy.get(name)
        if expected != digest or row.get('code_cells') != sum(c.cell_type == 'code' for c in nb.cells):
            raise ValueError('Wynik wznowienia nie pasuje do bieżącego kodu: '+name)
        context = input_context(ROOT, name)
        prior_context = row.get('input_context', {}).get('sha256')
        if prior_context is not None and prior_context != context['sha256']:
            continue
        if prior_context is None and (unchanged.get(name) != digest or not legacy_inputs_unchanged):
            # Zmiana wejść unieważnia wynik również przy identycznym kodzie.
            continue
        restored[name] = {**row, 'source_code_sha256': digest, 'execution_reused': True,
                          'input_context': context,
                          'evidence_report': source.name, 'evidence_encoding': evidence_encoding}
    return restored


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selected = parser.add_mutually_exclusive_group(required=True)
    selected.add_argument('--all', action='store_true')
    selected.add_argument('--chapters', nargs='+', type=int, choices=range(1, 11))
    parser.add_argument('--resume-from', type=Path, help='Zachowaj potwierdzone wyniki wskazanego raportu; wykonaj pozostałe notebooki.')
    parser.add_argument('--dry-run', action='store_true', help='Pokaż plan wznowienia bez uruchamiania jądra i bez zapisywania statusu wykonania.')
    args = parser.parse_args()
    chapters = list(range(1, 11)) if args.all else sorted(set(args.chapters))
    paths = [next((ROOT/'notebooks').glob(f'ch{ch:02d}_*.ipynb')) for ch in chapters]
    if args.all:
        paths += [ROOT/'notebooks/appendices_checks.ipynb', ROOT/'notebooks/fala_d_problem_checks.ipynb']
    resume = args.resume_from
    if resume is not None and not resume.is_absolute():
        resume = ROOT/resume
    completed = resumed_results(paths, resume)
    if args.dry_run:
        print(json.dumps({'execution': 'plan only; no kernel started',
                          'reuse': [p.name for p in paths if p.name in completed],
                          'execute': [p.name for p in paths if p.name not in completed]}, ensure_ascii=False, indent=2))
        return
    out = ROOT/'review/jupyter'
    out.mkdir(parents=True, exist_ok=True)
    report = {'execution': 'actual Jupyter kernel protocol', 'revision': 'I01-D01', 'status': 'running',
              'all_requested_passed': False, 'requested': [p.name for p in paths],
              'resume_from': resume.name if resume is not None else None,
              'python_utf8_requested': True, 'results': list(completed.values())}
    report_path = ROOT/'review/jupyter_protocol.json'
    os.environ.setdefault('MPLBACKEND', 'Agg')
    os.environ['PYTHONUTF8'] = '1'
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    current = None

    def save_report():
        report['results'] = [completed[p.name] for p in paths if p.name in completed]
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')

    save_report()
    try:
        with tempfile.TemporaryDirectory(prefix='cpsb-book-kernel-') as tmp:
            spec = Path(tmp)/'cpsb-book'
            spec.mkdir()
            (spec/'kernel.json').write_text(json.dumps({
                'argv': [sys.executable, '-X', 'utf8', '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
                'display_name': 'CPSB book', 'language': 'python',
                'env': {'MPLBACKEND': 'Agg', 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'},
            }), encoding='utf-8', newline='\n')
            for path in paths:
                if path.name in completed:
                    print('Zachowano wynik:', path.name, flush=True)
                    continue
                current = path.name
                if path.name == 'ch10_validation_reproducibility.ipynb':
                    report['handoff_preparation'] = prepare(ROOT)
                    save_report()
                print('Jupyter:', path.name, flush=True)
                nb = nbformat.read(path, as_version=4)
                for cell in nb.cells:
                    if cell.cell_type == 'code':
                        cell.outputs = []
                        cell.execution_count = None
                        cell.metadata.pop('execution', None)
                km = KernelManager(kernel_name='cpsb-book', kernel_spec_manager=KernelSpecManager(kernel_dirs=[tmp]))
                cwd = ROOT/'notebooks' if path.name == 'ch03_fourier.ipynb' else ROOT
                NotebookClient(nb, km=km, timeout=600, startup_timeout=60, record_timing=False,
                               resources={'metadata': {'path': str(cwd)}}).execute()
                nbformat.validate(nb)
                # Tylko wyjścia tekstowe; rysunki są odrębnymi plikami.
                for cell in nb.cells:
                    if cell.cell_type == 'code':
                        cell.outputs = [o for o in cell.outputs if o.output_type == 'stream']
                nbformat.write(nb, out/path.name)
                completed[path.name] = {'notebook': path.name, 'status': 'passed',
                    'code_cells': sum(c.cell_type == 'code' for c in nb.cells),
                    'source_code_sha256': code_hash(nb), 'execution_reused': False,
                    'input_context': input_context(ROOT, path.name)}
                save_report()
        report.update(status='passed', all_requested_passed=True)
    except Exception as error:
        report.update(status='failed', failed_notebook=current, error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        save_report()


if __name__ == '__main__':
    main()
