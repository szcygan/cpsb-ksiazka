"""Ocena zapisanego detektora QRS według protokołu rozdziału 10."""

import csv
import json
import platform
import sys

import matplotlib
import numpy as np
import scipy

from .ch09 import check_time_axis, checksum, detect, quality_windows
from .qrs_core import hash_config, load_fragment, match_events_1to1


def load_handoff(root, protocol):
    handoff_path = root / "data/ch09_run.json"
    if checksum(handoff_path) != protocol["frozen_handoff_sha256"]:
        raise ValueError("Inna wersja przekazania z rozdziału 9.")
    run = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff = run["handoff"]
    config = json.loads((root / "config/ch09_frozen.json").read_text(encoding="utf-8"))
    state_path = root / "data/ch09_fitted_state.npz"
    expected_files = {
        state_path: "state_file_sha256",
        root / "data/ch09_development_manifest.csv": "manifest_sha256",
        root / "config/ch09_candidate.json": "candidate_file_sha256",
        root / "src/bspsbook/qrs_core.py": "core_sha256",
        root / "src/bspsbook/ch09.py": "orchestration_sha256",
    }
    for path, key in expected_files.items():
        if checksum(path) != handoff[key]:
            raise ValueError(f"Niezgodny skrót pliku z rozdziału 9: {path.name}")
    if hash_config(config) != handoff["config_sha256_canonical"] or run["test_executed"]:
        raise ValueError("Konfiguracja lub stan etapu rozwojowego jest niezgodny.")
    if (
        config["locked_test"]["run"]
        or config["locked_test"]["required_fragments"] != protocol["locked_fragments"]
        or config["event_tolerance_ms"] != protocol["event_tolerance_ms"]
        or config["features"]["window_s"] != protocol["window_s"]
        or config["features"]["step_s"] != protocol["step_s"]
    ):
        raise ValueError("Rozdziały muszą mieć zgodny zakres oceny.")
    with np.load(state_path, allow_pickle=False) as source:
        state = json.loads(str(source["state_json"]))
        state["template"] = source["template"].copy()
    if (
        state["fit_records"] != handoff["fit_records"]
        or set(state["fit_records"]) != {"100", "103"}
        or handoff["selection_records"] != ["105"]
        or handoff["reserved_test_record"] != "200"
    ):
        raise ValueError("Niezgodne rozdzielenie ról danych.")
    return config, state


def load_locked(root, protocol):
    with (root / "data/ch10_test_manifest.csv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    if [r["fragment_id"] for r in rows] != protocol["locked_fragments"]:
        raise ValueError("Manifest testu musi zachować ustalony zakres i kolejność.")
    fragments = []
    for row in rows:
        name = row["fragment_id"]
        if row["split"] != "test" or row["record_id"] != "200" or row["channel"] != "MLII":
            raise ValueError("Nieprawidłowa rola, rekord lub kanał.")
        base = root / "data/test_locked"
        signal_path = base / (name + ".npz")
        annotations = base / (name + "_annotations.csv")
        if checksum(signal_path) != row["segment_sha256"] or checksum(annotations) != row["annotation_sha256"]:
            raise ValueError(f"Niezgodny skrót danych testowych: {name}")
        frag = load_fragment(root, name, "test")
        meta = frag["metadata"]
        n0, n1 = int(row["start_sample"]), int(row["end_sample_exclusive"])
        fs = float(row["fs_hz"])
        x, valid, refs = frag["signal_mV"], frag["valid_mask"], frag["r_samples"]
        if (
            str(meta["record_id"]) != "200" or meta["split"] != "test"
            or meta["channel"] != "MLII" or meta["units"] != "mV"
            or fs != 360 or float(meta["fs_hz"]) != fs
            or meta["start_sample_record"] != n0 or meta["end_sample_record_exclusive"] != n1
            or n1 <= n0 or x.shape != (n1 - n0,) or valid.shape != x.shape
            or valid.dtype != bool or not np.isfinite(x[valid]).all()
            or refs.ndim != 1 or len(refs) != int(row["n_reference_beats"])
            or np.any((refs < 0) | (refs >= len(x))) or np.any(np.diff(refs) <= 0)
        ):
            raise ValueError(f"Niezgodne metadane testu: {name}")
        check_time_axis(frag["time_s"], fs, len(x))
        with annotations.open(encoding="utf-8-sig", newline="") as file:
            beats = [r for r in csv.DictReader(file) if r["is_reference_beat"] == "True"]
        if (
            [int(r["local_sample"]) for r in beats] != refs.tolist()
            or [int(r["absolute_sample"]) for r in beats] != (refs + n0).tolist()
            or [r["symbol"] for r in beats] != frag["r_symbols"].tolist()
        ):
            raise ValueError(f"Niezgodne adnotacje testowe: {name}")
        fragments.append(frag)
    return fragments


def divide(a, b):
    return a / b if b else None


def mean(values):
    return float(np.mean(values)) if len(values) else None


def count_metrics(tp, fp, fn):
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "sensitivity": divide(tp, tp + fn),
        "ppv": divide(tp, tp + fp),
        "f1": divide(2 * tp, 2 * tp + fp + fn),
    }


def inside_rr(events, mask, fs):
    return [
        (b - a) / fs for a, b in zip(events[:-1], events[1:]) if mask[a:b + 1].all()
    ]


def compare(fragment, result, config):
    fs = float(fragment["metadata"]["fs_hz"])
    all_ref = fragment["r_samples"]
    mask = result.evaluation_mask
    original_ids = np.flatnonzero(mask[all_ref])
    ref = all_ref[original_ids]
    det = result.r_samples
    D = round(config["event_tolerance_ms"] * fs / 1000)
    match = match_events_1to1(ref, det, D)
    ref_pos, det_pos = match.reference_indices, match.detected_indices
    error = match.errors_samples * (1000 / fs)
    rr_error = []
    for p, q, u, v in zip(ref_pos[:-1], ref_pos[1:], det_pos[:-1], det_pos[1:]):
        if (
            original_ids[q] == original_ids[p] + 1
            and v == u + 1
            and mask[ref[p]:ref[q] + 1].all()
            and mask[det[u]:det[v] + 1].all()
        ):
            rr_error.append(float(((det[v] - det[u]) - (ref[q] - ref[p])) * (1000 / fs)))
    prefix = {
        "fragment_id": fragment["fragment_id"],
        "record_id": fragment["metadata"]["record_id"],
        "split": fragment["split"],
        "method": result.metadata["method"],
    }
    pairs = []
    for status, r_positions, d_positions in (
        ("TP", ref_pos, det_pos),
        ("FP", [None] * len(match.unmatched_detected_indices), match.unmatched_detected_indices),
        ("FN", match.unmatched_reference_indices, [None] * len(match.unmatched_reference_indices)),
    ):
        for r, d in zip(r_positions, d_positions):
            ri = int(ref[r]) if r is not None else None
            di = int(det[d]) if d is not None else None
            pairs.append({
                **prefix, "status": status,
                "reference_sample": ri, "detected_sample": di,
                "reference_symbol": str(fragment["r_symbols"][original_ids[r]]) if r is not None else "",
                "time_error_ms": (di - ri) * (1000 / fs) if status == "TP" else None,
            })
    windows = []
    for row in quality_windows(fragment, result, config):
        lo, hi = round(row["start_s"] * fs), round(row["end_s"] * fs)
        events = all_ref[(all_ref >= lo) & (all_ref < hi)]
        rr = inside_rr(events, mask, fs)
        hr_ref = float(60 / np.median(rr)) if rr else None
        hr_det = row["hr_bpm"]
        windows.append({
            **prefix, **row, "reference_hr_bpm": hr_ref, "n_reference_rr": len(rr),
            "abs_hr_error_bpm": abs(hr_det - hr_ref) if hr_det is not None and hr_ref is not None else None,
        })
    tp = len(ref_pos)
    summary = {
        **prefix,
        **count_metrics(tp, len(det) - tp, len(ref) - tp),
        "reference_all": len(all_ref), "reference_evaluated": len(ref),
        "evaluation_sample_fraction": float(np.mean(mask)),
        "timing_mae_ms": mean(np.abs(error)), "timing_bias_ms": mean(error),
        "timing_p95_abs_ms": float(np.quantile(np.abs(error), .95)) if tp else None,
        "rr_pairs": len(rr_error), "rr_mae_ms": mean(np.abs(rr_error)),
        **window_summary(windows),
    }
    return {"summary": summary, "pairs": pairs, "windows": windows, "rr_error_ms": rr_error}


def window_summary(windows):
    available = sum(r["result_available"] for r in windows)
    errors = [r["abs_hr_error_bpm"] for r in windows if r["abs_hr_error_bpm"] is not None]
    return {
        "windows": len(windows),
        "available_windows": available,
        "reference_defined_windows": sum(r["reference_hr_bpm"] is not None for r in windows),
        "hr_error_windows": len(errors),
        "result_coverage": divide(available, len(windows)),
        "window_hr_mae_bpm": mean(errors),
    }


def evaluate(fragment, method, config, state):
    result = detect(fragment, method, config, state)
    return result, compare(fragment, result, config)


def aggregate(items):
    rows = [item["summary"] for item in items]
    method, = {r["method"] for r in rows}
    split, = {r["split"] for r in rows}
    errors = [p["time_error_ms"] for item in items for p in item["pairs"] if p["status"] == "TP"]
    rr_error = [e for item in items for e in item["rr_error_ms"]]
    windows = [w for item in items for w in item["windows"]]
    return {
        "method": method, "split": split,
        **count_metrics(*(sum(r[key] for r in rows) for key in ("tp", "fp", "fn"))),
        "reference_all": sum(r["reference_all"] for r in rows),
        "reference_evaluated": sum(r["reference_evaluated"] for r in rows),
        "timing_mae_ms": mean(np.abs(errors)), "timing_bias_ms": mean(errors),
        "timing_p95_abs_ms": float(np.quantile(np.abs(errors), .95)) if errors else None,
        "rr_pairs": len(rr_error), "rr_mae_ms": mean(np.abs(rr_error)),
        **window_summary(windows),
        "fragment_macro_f1": mean([r["f1"] for r in rows if r["f1"] is not None]),
        "min_fragment_f1": min((r["f1"] for r in rows if r["f1"] is not None), default=None),
    }


def didactic_checks(row, targets):
    rules = {
        "sensitivity": ("sensitivity_min", True),
        "ppv": ("ppv_min", True),
        "f1": ("f1_min", True),
        "timing_mae_ms": ("timing_mae_ms_max", False),
        "window_hr_mae_bpm": ("window_hr_mae_bpm_max", False),
        "result_coverage": ("result_coverage_min", True),
        "min_fragment_f1": ("per_fragment_f1_min", True),
    }
    for metric, (target, minimum) in rules.items():
        value, limit = row[metric], targets[target]
        yield {
            "method": row["method"], "metric": metric, "value": value,
            "comparison": ">=" if minimum else "<=", "target": limit,
            "met": value is not None and (value >= limit if minimum else value <= limit),
        }


def choose_failure(items, order):
    pairs = [row for item in items for row in item["pairs"]]
    for key in order:
        if key == "largest_timing_error":
            return max((p for p in pairs if p["status"] == "TP"),
                       key=lambda p: abs(p["time_error_ms"]), default=None)
        first = next((p for p in pairs if (
            p["status"] == key or (
                key == "FN_V" and p["status"] == "FN" and p["reference_symbol"] == "V"
            )
        )), None)
        if first is not None:
            return first
    return None


def environment():
    return {
        "python": platform.python_version(), "python_implementation": sys.implementation.name,
        "platform": platform.system(), "machine": platform.machine(),
        "numpy": np.__version__, "scipy": scipy.__version__, "matplotlib": matplotlib.__version__,
    }
