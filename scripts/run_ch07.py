"""Wykonuje notebook w świeżym procesie Python; opcja --jupyter używa jądra."""
from pathlib import Path
import contextlib
import io
import json
import os
import sys
import traceback
import nbformat

root = Path(__file__).resolve().parents[1]
path = root/'notebooks/ch07_time_frequency_wavelets.ipynb'
os.environ.setdefault('MPLBACKEND', 'Agg')
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ.setdefault('PYDEVD_DISABLE_FILE_VALIDATION', '1')
os.chdir(root)
nb = nbformat.read(path, as_version=4)
for cell in nb.cells:
    if cell.cell_type == 'code':
        cell.outputs = []
        cell.execution_count = None
        cell.metadata.pop('execution', None)
nbformat.validate(nb)
if '--jupyter' in sys.argv:
    from nbclient import NotebookClient
    client = NotebookClient(nb, timeout=180, kernel_name='python3',
                            resources={'metadata': {'path': str(root)}}, record_timing=False)
    client.execute()
    method = 'nbclient, fresh Jupyter ipykernel, all code cells in order'
    kernel_tested = True
else:
    namespace = {'__name__': '__main__'}
    count = 0
    for cell in nb.cells:
        if cell.cell_type != 'code':
            continue
        count += 1
        cell.execution_count = count
        stdout, stderr = io.StringIO(), io.StringIO()
        failure = None
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                exec(compile(cell.source, f'ch07_cell_{count}', 'exec'), namespace)
            except Exception as error:
                failure = error
                traceback.print_exc()
        for name, output in [('stdout', stdout.getvalue()), ('stderr', stderr.getvalue())]:
            if output:
                cell.outputs.append(nbformat.v4.new_output('stream', name=name, text=output))
        if failure:
            raise RuntimeError(f'Błąd w komórce {count}: {failure}') from failure
        print(f'Wykonano komórkę {count}', flush=True)
    method = 'all plain Python cells in order, fresh process; nbformat schema validation'
    kernel_tested = False
nb.metadata['cpsb']['execution'] = {'method': method, 'status': 'passed',
    'kernel_protocol_tested': kernel_tested,
    'code_cells': sum(c.cell_type == 'code' for c in nb.cells)}
nbformat.validate(nb)
path.write_text(json.dumps(dict(nb), ensure_ascii=False, indent=1)+'\n', encoding='utf-8')
print('Wykonano notebook:', nb.metadata['cpsb']['execution']['code_cells'], 'komórek kodu.')
