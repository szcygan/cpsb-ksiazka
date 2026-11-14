"""Wykonuje zwykłe komórki Python notebooka kolejno w świeżym procesie.

Nie emuluje protokołu Jupyter. Uruchomienie: python scripts/run_ch05.py
Obsługuje wyłącznie ten notebook, bez magic commands i bez osadzania obrazów.
Przerywa przy pierwszym błędzie; zapisuje tekstowe outputs i liczniki wykonania.
"""
from pathlib import Path
import contextlib
import io
import json
import os
import sys
import traceback
import time

os.environ.setdefault('MPLBACKEND', 'Agg')
root = Path(__file__).resolve().parents[1]
os.chdir(root)
path = root/'notebooks/ch05_filtering_resampling.ipynb'
nb = json.loads(path.read_text(encoding='utf-8'))
namespace = {'__name__': '__main__'}
start = time.monotonic()
count = 0
try:
    for cell in nb['cells']:
        if cell['cell_type'] != 'code':
            continue
        count += 1
        cell['execution_count'] = count
        cell['outputs'] = []
        stdout, stderr = io.StringIO(), io.StringIO()
        failure = None
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                exec(compile(''.join(cell['source']), f'ch05_cell_{count}', 'exec'), namespace)
            except Exception as error:
                failure = error
                traceback.print_exc()
        for name, output in [('stdout',stdout.getvalue()),('stderr',stderr.getvalue())]:
            if output:
                cell['outputs'].append({'output_type':'stream','name':name,'text':output.splitlines(keepends=True)})
        if failure:
            raise RuntimeError(f'Błąd w komórce kodu {count}: {failure}') from failure
        print(f'Wykonano komórkę {count}', flush=True)
    nb['metadata']['cpsb']['execution'] = {
        'method': 'sequential plain Python cells in fresh process',
        'code_cells': count, 'status':'passed',
        'kernel_protocol_tested':False,
    }
finally:
    path.write_text(json.dumps(nb,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
print(f'Wykonano {count} komórek; czas {time.monotonic()-start:.1f} s.')
