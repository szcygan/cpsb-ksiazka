"""Zweryfikuj bieżące Ch09 i przywróć przekazanie D01 do regresji Ch10.

Nie zmienia zobowiązania ani parametrów metody. Zapisuje kopię bieżącego
przebiegu, porównanie liczb i jawne pochodzenie stanu używanego przez Ch10.
Nie otwiera danych testowych. Rozbieżność wykraczająca poza kontrakt przerywa
pracę przed zmianą plików data/ i config/.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = 'review/frozen_handoff_D01'
ATOL = 1e-12
RTOL = 1e-12
FROZEN = {
    'data/ch09_run.json': '00fefd6df61101679180eb1c2a598f4f2159de3f9be59572b7fae1e85870be4a',
    'data/ch09_fitted_state.npz': 'bbbc5248a5cf4522c8a29c507da86916813e38ea51c3d5b186c6522dc8f488a5',
    'config/ch09_frozen.json': '7f2c712e3189f2213a64472b126a82a779cc2890f26f40bda66ddddb853cdf72',
}
FREEZE_SHA = '6b13d3b99521f11f68055c4fe9a07c43aac571d2cd8cdfb79d771258b39619d2'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def require(condition, message):
    if not condition:
        raise ValueError('Przekazanie D01: '+message)


def compare_parameters(reference, actual):
    """Klucze, role i liczby całkowite dokładnie; skończone float w tolerancji."""
    rows = []

    def walk(a, b, path):
        if isinstance(a, dict):
            require(isinstance(b, dict) and a.keys() == b.keys(), 'inne pola stanu: '+path)
            for key in a:
                walk(a[key], b[key], path+'/'+key)
        elif isinstance(a, list):
            require(isinstance(b, list) and len(a) == len(b), 'inna lista: '+path)
            for index, (x, y) in enumerate(zip(a, b)):
                walk(x, y, path+'/'+str(index))
        elif isinstance(a, float):
            require(type(b) in (float, int) and math.isfinite(a) and math.isfinite(b),
                    'nieskończona lub nieliczbowa wartość: '+path)
            require(abs(a-b) <= ATOL+RTOL*abs(a), 'zmieniony parametr liczbowy: '+path)
            rows.append({'path': path, 'reference': a, 'actual': b, 'absolute_error': abs(a-b)})
        else:
            require(type(a) is type(b) and a == b, 'zmieniona rola, struktura lub liczba: '+path)
    walk(reference, actual, '')
    return rows


def prepare(root=ROOT):
    root = Path(root).resolve()
    reference = root/REFERENCE
    # Te skróty wskazują istniejący historyczny stan, nie nowy wynik Windows.
    for name, expected in FROZEN.items():
        require(sha((reference/name).read_bytes()) == expected, 'uszkodzony wzorzec: '+name)
    freeze_path = root/'config/ch10_freeze.json'
    require(sha(freeze_path.read_bytes()) == FREEZE_SHA, 'zmienione zobowiązanie Ch10')
    freeze = read_json(freeze_path)
    for name, expected in freeze['files_sha256'].items():
        require(sha((root/name).read_bytes()) == expected, 'zmieniony plik zamrożenia: '+name)
    nb = read_json(root/'notebooks/ch10_validation_reproducibility.ipynb')
    code = [''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code']
    require(sha(json.dumps(code, ensure_ascii=False).encode('utf-8')) == freeze['notebook_code_sha256'],
            'zmieniony kod notebooka Ch10')
    expected_run = read_json(reference/'data/ch09_run.json')
    current_run = read_json(root/'data/ch09_run.json')
    protocol = read_json(root/'config/ch10_protocol.json')
    require(protocol['frozen_handoff_sha256'] == FROZEN['data/ch09_run.json'], 'inny protokół przekazania')
    links = {'data/ch09_fitted_state.npz': 'state_file_sha256',
             'data/ch09_development_manifest.csv': 'manifest_sha256',
             'config/ch09_candidate.json': 'candidate_file_sha256',
             'src/bspsbook/qrs_core.py': 'core_sha256',
             'src/bspsbook/ch09.py': 'orchestration_sha256'}
    for name, key in links.items():
        digest = sha((root/name).read_bytes())
        require(digest == current_run['handoff'][key], 'niespójny bieżący przebieg: '+name)
        if key != 'state_file_sha256':
            require(digest == expected_run['handoff'][key], 'zmienione wejście lub kod Ch09: '+name)
    comparable_run = json.loads(json.dumps(current_run))
    comparable_run['handoff']['state_file_sha256'] = expected_run['handoff']['state_file_sha256']
    require(json.dumps(comparable_run, sort_keys=True, allow_nan=False)
            == json.dumps(expected_run, sort_keys=True, allow_nan=False),
            'zmienione wyniki, progi lub role danych w Ch09; wymagany osobny audyt')
    require(json.dumps(read_json(root/'config/ch09_frozen.json'), sort_keys=True, allow_nan=False)
            == json.dumps(read_json(reference/'config/ch09_frozen.json'), sort_keys=True, allow_nan=False),
            'zmieniona konfiguracja Ch09')
    with np.load(reference/'data/ch09_fitted_state.npz', allow_pickle=False) as a, \
            np.load(root/'data/ch09_fitted_state.npz', allow_pickle=False) as b:
        require(set(a.files) == set(b.files) == {'template', 'state_json'}, 'inne pola archiwum stanu')
        x, y = a['template'], b['template']
        require(x.dtype == y.dtype and x.shape == y.shape, 'inny typ lub kształt szablonu')
        require(np.isfinite(x).all() and np.isfinite(y).all(), 'nieskończony szablon')
        delta = np.abs(x-y)
        require(np.all(delta <= ATOL+RTOL*np.abs(x)), 'zmieniony szablon; wymagany osobny audyt')
        require(a['state_json'].shape == b['state_json'].shape == (), 'inny kształt metadanych stanu')
        parameters = compare_parameters(json.loads(str(a['state_json'])), json.loads(str(b['state_json'])))
        state_comparison = {'template_values': int(x.size), 'template_max_absolute_error': float(delta.max()),
                            'template_exact': bool(np.array_equal(x, y)), 'parameters': parameters,
                            'atol': ATOL, 'rtol': RTOL, 'roles_and_integers': 'exact',
                            'run_except_state_archive_sha256': 'exact', 'config_json': 'exact'}
    before = {name: sha((root/name).read_bytes()) for name in FROZEN}
    report_path = root/'review/handoff_preparation_D01.json'
    restored = before != FROZEN
    backup_name = None
    if restored:
        # Wszystkie kontrole powyżej kończą się przed zapisem danych aktywnych.
        snapshot = sha(json.dumps(before, sort_keys=True).encode('utf-8'))
        backup = root/'review/handoff_D01/backups'/snapshot
        for name, expected in before.items():
            target = backup/name
            if target.exists():
                require(sha(target.read_bytes()) == expected, 'inna istniejąca kopia bezpieczeństwa')
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((root/name).read_bytes())
        backup_name = str(backup.relative_to(root)).replace('\\', '/')
        # Zapis bajtów referencji zachowuje historyczne SHA; nie zaokrąglamy wyniku.
        for name in FROZEN:
            (root/name).write_bytes((reference/name).read_bytes())
        require(all(sha((root/name).read_bytes()) == expected for name, expected in FROZEN.items()),
                'nieudane odtworzenie wzorca; oryginały są w kopii bezpieczeństwa')
    report = {'revision': 'D01', 'status': 'passed',
              'purpose': 'historical book regression; not a new independent validation',
              'ch10_state_origin': REFERENCE, 'reference_sha256': FROZEN,
              'frozen_protocol_and_sources_unchanged': True, 'test_data_read': False,
              'restored_reference': restored, 'before_sha256': before,
              'backup': backup_name, 'comparison': state_comparison}
    if report_path.exists():
        previous = read_json(report_path)
        # Powtórne wywołanie nie usuwa dowodu wcześniejszego odtworzenia.
        if not restored and previous.get('status') == 'passed' and previous.get('backup'):
            return previous
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n',
                           encoding='utf-8', newline='\n')
    print('D01: sprawdzono przebieg Ch09; Ch10 użyje historycznego stanu referencyjnego.', flush=True)
    if backup_name:
        print('Zachowano bieżący wynik i porównanie w review/handoff_D01/.', flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    prepare(parser.parse_args().root)
