"""Wejście, decyzje rozwojowe i ślad wykonania w rozdziale 9."""

from copy import deepcopy
import csv
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

from .qrs_core import (
    baseline_detector,
    evaluate_result,
    fit_pipeline_state,
    hash_config,
    load_fragment,
    matched_filter_detector,
    window_quality_metrics,
)


DETECTORS = {
    "baseline": baseline_detector,
    "matched_filter": matched_filter_detector,
}

LABELS = {
    "baseline": "energia",
    "matched_filter": "wzorzec",
}


def checksum(path):
    return sha256(path.read_bytes()).hexdigest()


def check_time_axis(t, fs, n):
    expected = np.arange(n) / fs
    if t.shape != expected.shape or not np.allclose(t, expected, rtol=0, atol=1e-10):
        raise ValueError("Oś lokalna musi zaczynać się w zerze i mieć krok 1/fs.")


def load_development(root):
    manifest = root / "data/ch09_development_manifest.csv"
    with manifest.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    expected = {"train": {"100", "103"}, "validation": {"105"}}
    if {r["split"] for r in rows} != set(expected) or len(rows) != 6:
        raise ValueError("Manifest ma zawierać sześć fragmentów rozwojowych.")
    for split, record_ids in expected.items():
        if {r["record_id"] for r in rows if r["split"] == split} != record_ids:
            raise ValueError("Role rekordów muszą być zgodne z podziałem M8.")
    if len({r["fragment_id"] for r in rows}) != len(rows):
        raise ValueError("Identyfikatory fragmentów muszą być unikatowe.")

    groups = {"train": [], "validation": []}
    audits = []
    for row in rows:
        name, split = row["fragment_id"], row["split"]
        if Path(name).name != name or not name.startswith(row["record_id"] + "_"):
            raise ValueError(f"Identyfikator fragmentu nie odpowiada rekordowi: {name}")
        data_path = root / "data" / split / (name + ".npz")
        annotation_path = root / "data" / split / (name + "_annotations.csv")
        if checksum(data_path) != row["segment_sha256"]:
            raise ValueError(f"Niezgodny skrót sygnału: {name}")
        if checksum(annotation_path) != row["annotation_sha256"]:
            raise ValueError(f"Niezgodny skrót adnotacji: {name}")
        fragment = load_fragment(root, name, split)
        x = fragment["signal_mV"]
        t = fragment["time_s"]
        valid = fragment["valid_mask"]
        refs = fragment["r_samples"]
        metadata = fragment["metadata"]
        fs = float(metadata["fs_hz"])
        n0 = int(row["start_sample"])
        n1 = int(row["end_sample_exclusive"])
        n = n1 - n0
        if fs <= 0 or fs != float(row["fs_hz"]):
            raise ValueError(f"Niezgodna częstotliwość próbkowania: {name}")
        if metadata["units"] != "mV" or metadata["channel"] != row["channel"] or row["channel"] != "MLII":
            raise ValueError(f"Niezgodny kanał lub jednostka: {name}")
        if (
            str(metadata["record_id"]) != row["record_id"]
            or metadata["split"] != split
            or metadata["start_sample_record"] != n0
            or metadata["end_sample_record_exclusive"] != n1
            or n <= 0
            or x.shape != (n,)
            or valid.shape != (n,)
            or valid.dtype != bool
            or not np.isfinite(x[valid]).all()
        ):
            raise ValueError(f"Niespójny sygnał, maska lub metadane: {name}")
        check_time_axis(t, fs, n)
        if (
            refs.ndim != 1
            or len(refs) != int(row["n_reference_beats"])
            or np.any((refs < 0) | (refs >= n))
            or np.any(np.diff(refs) <= 0)
        ):
            raise ValueError(f"Niespójne adnotacje: {name}")
        with annotation_path.open(encoding="utf-8-sig", newline="") as file:
            annotations = [r for r in csv.DictReader(file) if r["is_reference_beat"] == "True"]
        if (
            [int(r["local_sample"]) for r in annotations] != refs.tolist()
            or [int(r["absolute_sample"]) for r in annotations] != (refs + n0).tolist()
            or [r["symbol"] for r in annotations] != fragment["r_symbols"].tolist()
        ):
            raise ValueError(f"Adnotacje CSV i NPZ są niespójne: {name}")
        groups[split].append(fragment)
        audits.append({
            "fragment_id": name,
            "record_id": row["record_id"],
            "split": split,
            "channel": row["channel"],
            "fs_hz": fs,
            "start_sample": n0,
            "end_sample_exclusive": n1,
            "samples": n,
            "n_reference_beats": len(refs),
            "valid_sample_fraction": float(np.mean(valid)),
            "min_mV": float(np.min(x)),
            "max_mV": float(np.max(x)),
        })
    return groups["train"], groups["validation"], audits


def fit_train(train, config):
    if {d["split"] for d in train} != {"train"}:
        raise ValueError("Dopasowanie wymaga wyłącznie części train.")
    if {d["metadata"]["record_id"] for d in train} != {"100", "103"}:
        raise ValueError("Wzorzec i statystyki pochodzą z rekordów 100 i 103.")
    return fit_pipeline_state(train, config)


def detect(fragment, method, config, state):
    fs = float(fragment["metadata"]["fs_hz"])
    if method == "matched_filter" and fs != state["template_meta"]["fs_hz"]:
        raise ValueError("Wzorzec i zapis muszą mieć wspólną siatkę próbkowania.")
    result = DETECTORS[method](
        fragment["signal_mV"], fragment["valid_mask"], fs, config, state,
    )
    n = len(fragment["signal_mV"])
    for vector in (result.filtered, result.score, result.threshold_trace, result.evaluation_mask):
        if vector.shape != (n,):
            raise ValueError("Wynik pośredni utracił oś próbek wejścia.")
    if np.any(np.diff(result.r_samples) < result.metadata["refractory_samples"]):
        raise ValueError("Detekcje naruszają warunek minimalnego odstępu.")
    if not result.evaluation_mask[result.r_samples].all():
        raise ValueError("Detekcja w zakresie wyłączonym z oceny.")
    return result


def score_development(validation, candidate, state):
    if {d["split"] for d in validation} != {"validation"}:
        raise ValueError("Wybór progów wymaga części validation.")
    if {d["metadata"]["record_id"] for d in validation} != {"105"}:
        raise ValueError("Wybór progów jest przypisany do rekordu 105.")
    selected = deepcopy(candidate)
    rows = []
    for method, grid_name in (
        ("baseline", "threshold_grid_baseline"),
        ("matched_filter", "threshold_grid_matched"),
    ):
        method_rows = []
        for k in candidate["validation"][grid_name]:
            config = deepcopy(candidate)
            config[method]["threshold_k_mad"] = k
            tp, fp, fn, errors_ms = 0, 0, 0, []
            for fragment in validation:
                result = detect(fragment, method, config, state)
                metrics, pairs, _ = evaluate_result(fragment, result, config)
                tp += metrics["tp"]
                fp += metrics["fp"]
                fn += metrics["fn"]
                errors_ms.extend(pairs.errors_samples * (1000 / fragment["metadata"]["fs_hz"]))
            method_rows.append({
                "method": method,
                "k": k,
                "tp": tp, "fp": fp, "fn": fn,
                "micro_f1": 2 * tp / (2 * tp + fp + fn),
                "timing_mae_ms": float(np.mean(np.abs(errors_ms))) if errors_ms else None,
            })
        best = min(
            method_rows,
            key=lambda r: (-r["micro_f1"], r["timing_mae_ms"] if r["timing_mae_ms"] is not None else np.inf, r["k"]),
        )
        selected[method]["threshold_k_mad"] = best["k"]
        for row in method_rows:
            row["selected"] = row is best
        rows.extend(method_rows)
    return selected, rows


def quality_windows(fragment, result, config):
    """Odmowa dotyczy HR. Lista zdarzeń i domena oceny pozostają dostępne."""
    x = fragment["signal_mV"]
    fs = float(fragment["metadata"]["fs_hz"])
    length = round(config["features"]["window_s"] * fs)
    step = round(config["features"]["step_s"] * fs)
    for lo in range(0, len(x) - length + 1, step):
        hi = lo + length
        row = window_quality_metrics(result, x, fragment["valid_mask"], lo, hi, fs, config)
        events = result.r_samples[(result.r_samples >= lo) & (result.r_samples < hi)]
        rr = [
            (b - a) / fs for a, b in zip(events[:-1], events[1:])
            if result.evaluation_mask[a:b + 1].all()
        ]
        if row["result_available"] and not rr:
            row["result_available"] = False
            row["missing_reason"] = "no_contiguous_rr"
        yield {
            "fragment_id": fragment["fragment_id"],
            "method": result.metadata["method"],
            "start_s": lo / fs,
            "end_s": hi / fs,
            **row,
            "n_usable_rr": len(rr),
            "hr_bpm": float(60 / np.median(rr)) if row["result_available"] else None,
        }


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def save_design(root, config, state):
    """Przechowuje konfigurację wraz z identyfikatorami wejść i stanem dopasowanym."""
    config_path = root / "config/ch09_frozen.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state_path = root / "data/ch09_fitted_state.npz"
    np.savez_compressed(
        state_path,
        template=state["template"],
        state_json=json.dumps({k: v for k, v in state.items() if k != "template"}, sort_keys=True),
    )
    return {
        "config_sha256_canonical": hash_config(config),
        "state_file_sha256": checksum(state_path),
        "manifest_sha256": checksum(root / "data/ch09_development_manifest.csv"),
        "candidate_file_sha256": checksum(root / "config/ch09_candidate.json"),
        "core_sha256": checksum(root / "src/bspsbook/qrs_core.py"),
        "orchestration_sha256": checksum(root / "src/bspsbook/ch09.py"),
        "fit_records": state["fit_records"],
        "selection_records": ["105"],
        "reserved_test_record": "200",
    }
