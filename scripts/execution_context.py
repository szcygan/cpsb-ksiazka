"""Odcisk rzeczywistych wejść obliczeń; kod notebooka jest sprawdzany osobno."""
import hashlib
import json
from pathlib import Path


def input_context(root, notebook_name):
    root = Path(root)
    paths = set((root/'src/bspsbook').glob('*.py')) | {root/'requirements.txt'}
    if notebook_name.startswith(('ch01_', 'ch02_')):
        paths |= {root/'data/ch01_manifest.json', root/'data/100_normal.npz',
                  root/'data/100_normal_annotations.csv'}
    if notebook_name.startswith(('ch09_', 'ch10_')):
        paths |= {root/'data/ch09_development_manifest.csv', root/'config/ch09_candidate.json'}
        paths |= {p for part in ['train', 'validation'] for p in (root/'data'/part).glob('*') if p.is_file()}
    if notebook_name.startswith('ch10_'):
        paths |= {root/name for name in ['data/ch09_run.json', 'data/ch09_fitted_state.npz',
                  'config/ch09_frozen.json', 'config/ch10_protocol.json', 'config/ch10_freeze.json',
                  'data/ch10_test_manifest.csv', 'scripts/prepare_frozen_handoff.py']}
        paths |= {p for p in (root/'data/test_locked').glob('*') if p.is_file()}
    if notebook_name == 'appendices_checks.ipynb':
        paths.add(root/'scripts/audit_package.py')
    hashes = {str(p.relative_to(root)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(paths)}
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode('utf-8')).hexdigest()
    return {'schema': 'D01-input-context-v1', 'sha256': digest, 'files_sha256': hashes}
