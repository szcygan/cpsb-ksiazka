"""Weryfikacja osi, metadanych i adnotacji oraz dekodowanie licznika."""
from hashlib import sha256
import csv
import json

import numpy as np


def file_digest(path):
    return sha256(path.read_bytes()).hexdigest()


def check_axis(time, fs, n):
    expected = np.arange(n) / fs
    if np.shape(time) != expected.shape or not np.allclose(time, expected, rtol=0, atol=1e-10):
        raise ValueError("Niezgodna lokalna oś czasu.")


def load_ecg(data):
    manifest = json.loads((data / "ch01_manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["files_sha256"].items():
        if file_digest(data / name) != expected:
            raise ValueError(f"Niezgodny skrót pliku {name}.")
    with np.load(data / "100_normal.npz", allow_pickle=False) as source:
        ecg = {k: source[k] for k in source.files}
    meta = json.loads(str(ecg.pop("metadata_json")))
    fs = manifest["fs_hz"]
    start, stop = manifest["record_start_sample"], manifest["record_stop_sample"]
    x, valid, refs = ecg["signal_mV"], ecg["valid_mask"], ecg["r_samples"]
    if (
        meta["fragment_id"] != manifest["fragment_id"]
        or meta["record_id"] != manifest["record_id"]
        or meta["source_doi"] != manifest["doi"]
        or meta["channel"] != manifest["channel"] or meta["units"] != manifest["unit"]
        or meta["fs_hz"] != fs or fs <= 0
        or meta["start_sample_record"] != start or meta["end_sample_record_exclusive"] != stop
        or stop <= start or x.shape != (stop - start,)
        or valid.shape != x.shape or valid.dtype != bool or not np.isfinite(x[valid]).all()
        or refs.ndim != 1 or not np.issubdtype(refs.dtype, np.integer)
        or len(refs) != manifest["reference_beats"]
        or np.any((refs < 0) | (refs >= len(x))) or np.any(np.diff(refs) <= 0)
    ):
        raise ValueError("Niespójne metadane, sygnał lub adnotacje.")
    check_axis(ecg["time_s"], fs, len(x))
    with (data / "100_normal_annotations.csv").open(encoding="utf-8-sig", newline="") as file:
        beats = [r for r in csv.DictReader(file) if r["is_reference_beat"] == "True"]
    if (
        [int(r["local_sample"]) for r in beats] != refs.tolist()
        or [int(r["absolute_sample"]) for r in beats] != (refs + start).tolist()
        or [r["symbol"] for r in beats] != ecg["r_symbols"].tolist()
    ):
        raise ValueError("Niespójność odniesienia z indeksem próbek.")
    return ecg, manifest


def unwrap_ordered_counter(values, modulus=256):
    """Indeksy względem pierwszego pakietu przy odstępach od 1 do modulus−1."""
    counter = np.asarray(values)
    if (
        counter.ndim != 1 or counter.size == 0 or not np.issubdtype(counter.dtype, np.integer)
        or np.any((counter < 0) | (counter >= modulus))
    ):
        raise ValueError("Licznik musi być niepustą sekwencją poprawnych liczb całkowitych.")
    steps = np.diff(counter.astype(np.int64)) % modulus
    if np.any(steps == 0):
        raise ValueError("Powtórzona wartość licznika jest niejednoznaczna.")
    return np.r_[0, np.cumsum(steps)]
