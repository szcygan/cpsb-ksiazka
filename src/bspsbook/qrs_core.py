"""Funkcje przejęte z M8_pipeline_core.py (CPSB), w zakresie rozdziału 9."""

from __future__ import annotations

import json

from dataclasses import dataclass

from pathlib import Path

import numpy as np

from scipy.ndimage import binary_dilation, median_filter

from scipy.signal import butter, fftconvolve, find_peaks, peak_prominences, sosfiltfilt

from typing import Sequence

def robust_mad(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float("nan")
    med = np.median(x)
    return float(np.median(np.abs(x - med)))

def robust_scale(x: np.ndarray, floor: float = 1e-12) -> float:
    value = 1.4826 * robust_mad(x)
    return float(max(value if np.isfinite(value) else 0.0, floor))

def odd_samples(duration_ms: float, fs: float, minimum: int = 1) -> int:
    n = max(minimum, int(round(duration_ms / 1000.0 * fs)))
    return n if n % 2 == 1 else n + 1

def fill_invalid_linear(x: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    valid = np.asarray(valid_mask, dtype=bool) & np.isfinite(x)
    if valid.sum() < 2:
        return np.zeros_like(x, dtype=float)
    idx = np.arange(len(x))
    return np.interp(idx, idx[valid], x[valid]).astype(float)

def bandpass_sos(x: np.ndarray, fs: float, filter_cfg: dict) -> np.ndarray:
    sos = butter(
        int(filter_cfg["order"]),
        [float(filter_cfg["low_hz"]), float(filter_cfg["high_hz"])],
        btype="bandpass",
        fs=float(fs),
        output="sos",
    )
    return sosfiltfilt(sos, np.asarray(x, dtype=float))

def centered_moving_average(x: np.ndarray, length_samples: int) -> tuple[np.ndarray, int]:
    length_samples = max(1, int(length_samples))
    if length_samples % 2 == 0:
        length_samples += 1
    kernel = np.ones(length_samples, dtype=float) / length_samples
    return np.convolve(np.asarray(x, dtype=float), kernel, mode="same"), length_samples

def local_robust_normalize(x: np.ndarray, window_samples: int, scale_floor: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    window_samples = max(3, int(window_samples))
    if window_samples % 2 == 0:
        window_samples += 1
    x = np.asarray(x, dtype=float)
    center = median_filter(x, size=window_samples, mode="nearest")
    mad = median_filter(np.abs(x - center), size=window_samples, mode="nearest")
    scale = np.maximum(1.4826 * mad, float(scale_floor))
    z = (x - center) / scale
    return z, center, scale

def make_evaluation_mask(
    signal: np.ndarray,
    valid_mask: np.ndarray,
    fs: float,
    quality_cfg: dict,
    extra_edge_samples: int = 0,
) -> np.ndarray:
    signal = np.asarray(signal, dtype=float)
    valid = np.asarray(valid_mask, dtype=bool) & np.isfinite(signal)
    saturation_abs_mV = float(quality_cfg.get("saturation_abs_mV", np.inf))
    valid &= np.abs(signal) < saturation_abs_mV

    guard = int(round(float(quality_cfg.get("invalid_guard_s", 0.5)) * fs))
    if guard > 0 and (~valid).any():
        invalid = binary_dilation(~valid, iterations=guard)
        valid &= ~invalid

    edge = max(
        int(round(float(quality_cfg.get("edge_margin_s", 1.0)) * fs)),
        int(extra_edge_samples),
    )
    if edge > 0:
        valid[: min(edge, len(valid))] = False
        valid[max(0, len(valid) - edge) :] = False
    return valid

def load_fragment(package_root: Path, fragment_id: str, split: str) -> dict:
    folder = "test_locked" if split == "test" else split
    path = Path(package_root) / "data" / folder / f"{fragment_id}.npz"
    with np.load(path, allow_pickle=False) as z:
        data = {key: z[key] for key in z.files}
    data["metadata"] = json.loads(str(data.pop("metadata_json")))
    data["fragment_id"] = fragment_id
    data["split"] = split
    return data

@dataclass
class MatchResult:
    reference_indices: np.ndarray
    detected_indices: np.ndarray
    unmatched_reference_indices: np.ndarray
    unmatched_detected_indices: np.ndarray
    errors_samples: np.ndarray

@dataclass
class DetectorResult:
    filtered: np.ndarray
    score: np.ndarray
    threshold_trace: np.ndarray
    score_peak_samples: np.ndarray
    candidate_r_samples: np.ndarray
    r_samples: np.ndarray
    evaluation_mask: np.ndarray
    local_center: np.ndarray | None
    local_scale: np.ndarray | None
    metadata: dict

def match_events_1to1(reference: np.ndarray, detected: np.ndarray, tolerance_samples: int) -> MatchResult:
    reference = np.asarray(reference, dtype=int)
    detected = np.asarray(detected, dtype=int)
    if reference.ndim != 1 or detected.ndim != 1:
        raise ValueError("reference and detected must be one-dimensional")
    if len(reference) and np.any(np.diff(reference) <= 0):
        raise ValueError("reference must be strictly increasing")
    if len(detected) and np.any(np.diff(detected) <= 0):
        raise ValueError("detected must be strictly increasing")
    if tolerance_samples < 0:
        raise ValueError("tolerance_samples must be non-negative")

    n, m = len(reference), len(detected)
    matches = np.zeros((n + 1, m + 1), dtype=np.int32)
    costs = np.zeros((n + 1, m + 1), dtype=np.int64)
    action = np.zeros((n + 1, m + 1), dtype=np.int8)
    action[1:, 0] = 1  # skip reference
    action[0, 1:] = 2  # skip detection

    # Deterministic priority for exact ties: pair > skip detection > skip reference.
    priorities = {3: 3, 2: 2, 1: 1}

    def better(cand_m: int, cand_c: int, cand_a: int, best_m: int, best_c: int, best_a: int) -> bool:
        if cand_m != best_m:
            return cand_m > best_m
        if cand_c != best_c:
            return cand_c < best_c
        return priorities[cand_a] > priorities[best_a]

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            best_m, best_c, best_a = int(matches[i - 1, j]), int(costs[i - 1, j]), 1
            cand_m, cand_c, cand_a = int(matches[i, j - 1]), int(costs[i, j - 1]), 2
            if better(cand_m, cand_c, cand_a, best_m, best_c, best_a):
                best_m, best_c, best_a = cand_m, cand_c, cand_a
            distance = abs(int(reference[i - 1]) - int(detected[j - 1]))
            if distance <= tolerance_samples:
                cand_m = int(matches[i - 1, j - 1]) + 1
                cand_c = int(costs[i - 1, j - 1]) + distance
                cand_a = 3
                if better(cand_m, cand_c, cand_a, best_m, best_c, best_a):
                    best_m, best_c, best_a = cand_m, cand_c, cand_a
            matches[i, j], costs[i, j], action[i, j] = best_m, best_c, best_a

    i, j = n, m
    pairs: list[tuple[int, int]] = []
    while i > 0 or j > 0:
        a = int(action[i, j])
        if a == 3:
            pairs.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif a == 1:
            i -= 1
        elif a == 2:
            j -= 1
        else:
            break
    pairs.reverse()

    ref_idx = np.asarray([p[0] for p in pairs], dtype=int)
    det_idx = np.asarray([p[1] for p in pairs], dtype=int)
    unmatched_ref = np.setdiff1d(np.arange(n, dtype=int), ref_idx, assume_unique=True)
    unmatched_det = np.setdiff1d(np.arange(m, dtype=int), det_idx, assume_unique=True)
    errors = detected[det_idx] - reference[ref_idx] if len(ref_idx) else np.array([], dtype=int)
    return MatchResult(ref_idx, det_idx, unmatched_ref, unmatched_det, errors)

def event_metrics(reference: np.ndarray, detected: np.ndarray, fs: float, tolerance_ms: float = 50.0) -> tuple[dict, MatchResult]:
    reference = np.asarray(reference, dtype=int)
    detected = np.asarray(detected, dtype=int)
    tolerance_samples = int(round(float(tolerance_ms) / 1000.0 * fs))
    match = match_events_1to1(reference, detected, tolerance_samples)
    tp = len(match.reference_indices)
    fp = len(match.unmatched_detected_indices)
    fn = len(match.unmatched_reference_indices)
    se = tp / (tp + fn) if tp + fn else np.nan
    ppv = tp / (tp + fp) if tp + fp else np.nan
    total = 2 * tp + fp + fn
    f1 = 2 * tp / total if total else np.nan
    errors_ms = match.errors_samples / fs * 1000.0

    # RR/HR are compared only when two consecutive reference beats are both matched
    # and their corresponding detections are also consecutive.
    rr_ref: list[float] = []
    rr_det: list[float] = []
    for k in range(len(match.reference_indices) - 1):
        ri0, ri1 = int(match.reference_indices[k]), int(match.reference_indices[k + 1])
        di0, di1 = int(match.detected_indices[k]), int(match.detected_indices[k + 1])
        if ri1 == ri0 + 1 and di1 == di0 + 1:
            rr_ref.append((reference[ri1] - reference[ri0]) / fs)
            rr_det.append((detected[di1] - detected[di0]) / fs)
    rr_ref_a = np.asarray(rr_ref, dtype=float)
    rr_det_a = np.asarray(rr_det, dtype=float)
    hr_ref = 60.0 / rr_ref_a if len(rr_ref_a) else np.array([], dtype=float)
    hr_det = 60.0 / rr_det_a if len(rr_det_a) else np.array([], dtype=float)

    metrics = {
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "sensitivity": float(se),
        "ppv": float(ppv),
        "f1": float(f1),
        "timing_mae_ms": float(np.mean(np.abs(errors_ms))) if len(errors_ms) else np.nan,
        "timing_bias_ms": float(np.mean(errors_ms)) if len(errors_ms) else np.nan,
        "timing_p95_abs_ms": float(np.quantile(np.abs(errors_ms), 0.95)) if len(errors_ms) else np.nan,
        "n_rr_pairs": int(len(rr_ref_a)),
        "rr_mae_ms": float(np.mean(np.abs(rr_det_a - rr_ref_a)) * 1000.0) if len(rr_ref_a) else np.nan,
        "hr_mae_bpm": float(np.mean(np.abs(hr_det - hr_ref))) if len(hr_ref) else np.nan,
    }
    return metrics, match

def refine_r_locations(filtered: np.ndarray, candidates: np.ndarray, fs: float, radius_ms: float) -> np.ndarray:
    radius = int(round(float(radius_ms) / 1000.0 * fs))
    filtered = np.asarray(filtered, dtype=float)
    refined: list[int] = []
    for candidate in np.asarray(candidates, dtype=int):
        lo = max(0, int(candidate) - radius)
        hi = min(len(filtered), int(candidate) + radius + 1)
        if hi <= lo:
            continue
        local = filtered[lo:hi]
        # QRS polarity may vary. Select the largest absolute deviation from the local median.
        centered = local - np.median(local)
        refined.append(lo + int(np.argmax(np.abs(centered))))
    return np.asarray(sorted(set(refined)), dtype=int)

def enforce_refractory(events: np.ndarray, strengths: np.ndarray, refractory_samples: int) -> np.ndarray:
    events = np.asarray(events, dtype=int)
    strengths = np.asarray(strengths, dtype=float)
    if len(events) != len(strengths):
        raise ValueError("events and strengths must have equal length")
    if len(events) == 0:
        return np.array([], dtype=int)
    order = np.lexsort((events, -strengths))
    accepted: list[int] = []
    for idx in order:
        event = int(events[idx])
        if all(abs(event - other) >= refractory_samples for other in accepted):
            accepted.append(event)
    return np.asarray(sorted(accepted), dtype=int)

def _mask_reference(reference: np.ndarray, evaluation_mask: np.ndarray) -> np.ndarray:
    reference = np.asarray(reference, dtype=int)
    keep = (reference >= 0) & (reference < len(evaluation_mask))
    reference = reference[keep]
    return reference[evaluation_mask[reference]]

def fit_baseline_state(train_fragments: Sequence[dict], config: dict) -> dict:
    pooled: list[np.ndarray] = []
    window_samples_used: list[int] = []
    for d in train_fragments:
        fs = float(d["metadata"]["fs_hz"])
        x = np.asarray(d["signal_mV"], dtype=float)
        valid = np.asarray(d["valid_mask"], dtype=bool)
        filled = fill_invalid_linear(x, valid)
        filtered = bandpass_sos(filled, fs, config["filter"])
        energy, n = centered_moving_average(filtered ** 2, odd_samples(config["baseline"]["energy_window_ms"], fs))
        evaluation_mask = make_evaluation_mask(x, valid, fs, config["quality"], n // 2)
        pooled.append(energy[evaluation_mask])
        window_samples_used.append(n)
    values = np.concatenate(pooled)
    center = float(np.median(values))
    scale = robust_scale(values, floor=1e-12)
    return {
        "energy_center_train": center,
        "energy_scale_train": scale,
        "energy_window_samples_by_fs": {str(int(train_fragments[0]["metadata"]["fs_hz"])): int(np.median(window_samples_used))},
        "n_train_score_samples": int(len(values)),
    }

def build_training_template(train_fragments: Sequence[dict], config: dict) -> tuple[np.ndarray, dict]:
    beats: list[np.ndarray] = []
    fs_expected: float | None = None
    pre_samples = post_samples = None
    for d in train_fragments:
        fs = float(d["metadata"]["fs_hz"])
        if fs_expected is None:
            fs_expected = fs
        if not np.isclose(fs, fs_expected):
            raise ValueError("All template fragments must have the same sampling frequency")
        pre_samples = int(round(config["matched_filter"]["template_pre_ms"] / 1000.0 * fs))
        post_samples = int(round(config["matched_filter"]["template_post_ms"] / 1000.0 * fs))
        x = np.asarray(d["signal_mV"], dtype=float)
        valid = np.asarray(d["valid_mask"], dtype=bool)
        filled = fill_invalid_linear(x, valid)
        filtered = bandpass_sos(filled, fs, config["filter"])
        evaluation_mask = make_evaluation_mask(x, valid, fs, config["quality"], max(pre_samples, post_samples))
        for r in np.asarray(d["r_samples"], dtype=int):
            lo, hi = int(r - pre_samples), int(r + post_samples + 1)
            if lo < 0 or hi > len(filtered) or not evaluation_mask[r] or not valid[lo:hi].all():
                continue
            beat = filtered[lo:hi].copy()
            beat -= np.median(beat)
            norm = np.linalg.norm(beat)
            if norm > 1e-10:
                beats.append(beat / norm)
    if not beats or fs_expected is None or pre_samples is None or post_samples is None:
        raise RuntimeError("No valid training beats for template")
    template = np.median(np.vstack(beats), axis=0)
    template -= np.mean(template)
    template /= np.linalg.norm(template) + 1e-12
    meta = {
        "fs_hz": float(fs_expected),
        "r_anchor_sample": int(pre_samples),
        "post_samples": int(post_samples),
        "n_training_beats": int(len(beats)),
        "template_length_samples": int(len(template)),
    }
    return template.astype(float), meta

def fit_matched_scale_floor(train_fragments: Sequence[dict], template: np.ndarray, template_meta: dict, config: dict) -> dict:
    scales: list[np.ndarray] = []
    fs_expected = float(template_meta["fs_hz"])
    local_window = odd_samples(config["matched_filter"]["local_background_window_ms"], fs_expected, minimum=3)
    for d in train_fragments:
        fs = float(d["metadata"]["fs_hz"])
        x = np.asarray(d["signal_mV"], dtype=float)
        valid = np.asarray(d["valid_mask"], dtype=bool)
        filled = fill_invalid_linear(x, valid)
        filtered = bandpass_sos(filled, fs, config["filter"])
        corr = fftconvolve(filtered, template[::-1], mode="same")
        center = median_filter(corr, size=local_window, mode="nearest")
        local_mad = median_filter(np.abs(corr - center), size=local_window, mode="nearest")
        evaluation_mask = make_evaluation_mask(x, valid, fs, config["quality"], len(template) // 2)
        scales.append((1.4826 * local_mad)[evaluation_mask])
    values = np.concatenate(scales)
    positive = values[values > 0]
    median_scale = float(np.median(positive)) if len(positive) else 1e-6
    floor = max(1e-8, 0.10 * median_scale)
    return {
        "matched_local_scale_floor": float(floor),
        "matched_local_scale_train_median": median_scale,
        "local_background_window_samples": int(local_window),
    }

def fit_pipeline_state(train_fragments: Sequence[dict], config: dict) -> dict:
    baseline = fit_baseline_state(train_fragments, config)
    template, template_meta = build_training_template(train_fragments, config)
    matched_scale = fit_matched_scale_floor(train_fragments, template, template_meta, config)
    return {
        "baseline": baseline,
        "template": template,
        "template_meta": template_meta,
        "matched": matched_scale,
        "fit_records": sorted({str(d["metadata"]["record_id"]) for d in train_fragments}),
        "fit_fragments": sorted(str(d["fragment_id"]) for d in train_fragments),
    }

def baseline_detector(x: np.ndarray, valid_mask: np.ndarray, fs: float, config: dict, fitted_state: dict) -> DetectorResult:
    x = np.asarray(x, dtype=float)
    valid = np.asarray(valid_mask, dtype=bool)
    filled = fill_invalid_linear(x, valid)
    filtered = bandpass_sos(filled, fs, config["filter"])
    n = odd_samples(config["baseline"]["energy_window_ms"], fs)
    energy, n = centered_moving_average(filtered ** 2, n)
    center = float(fitted_state["baseline"]["energy_center_train"])
    scale = float(fitted_state["baseline"]["energy_scale_train"])
    score = (energy - center) / scale
    threshold = float(config["baseline"]["threshold_k_mad"])
    threshold_trace = np.full(len(score), threshold, dtype=float)
    evaluation_mask = make_evaluation_mask(x, valid, fs, config["quality"], n // 2)
    score_for_peaks = score.copy()
    score_for_peaks[~evaluation_mask] = -np.inf
    refractory = int(round(config["shared"]["refractory_ms"] / 1000.0 * fs))
    peak_samples, _ = find_peaks(score_for_peaks, height=threshold, distance=max(1, refractory))
    candidate_r = peak_samples.copy()
    refined = refine_r_locations(filtered, candidate_r, fs, config["shared"]["r_refine_ms"])
    refined = refined[evaluation_mask[np.clip(refined, 0, len(evaluation_mask) - 1)]] if len(refined) else refined
    if len(refined):
        strengths = np.array([np.max(score[max(0, r - n // 2): min(len(score), r + n // 2 + 1)]) for r in refined])
        refined = enforce_refractory(refined, strengths, refractory)
    return DetectorResult(
        filtered=filtered,
        score=score,
        threshold_trace=threshold_trace,
        score_peak_samples=peak_samples,
        candidate_r_samples=candidate_r,
        r_samples=refined,
        evaluation_mask=evaluation_mask,
        local_center=None,
        local_scale=None,
        metadata={
            "method": "baseline",
            "energy_window_samples": int(n),
            "refractory_samples": int(refractory),
            "threshold_k_mad": threshold,
            "score_center_source": "training_only",
            "score_scale_source": "training_only",
        },
    )

def matched_filter_detector(x: np.ndarray, valid_mask: np.ndarray, fs: float, config: dict, fitted_state: dict) -> DetectorResult:
    x = np.asarray(x, dtype=float)
    valid = np.asarray(valid_mask, dtype=bool)
    template = np.asarray(fitted_state["template"], dtype=float)
    template_meta = fitted_state["template_meta"]
    filled = fill_invalid_linear(x, valid)
    filtered = bandpass_sos(filled, fs, config["filter"])
    corr = fftconvolve(filtered, template[::-1], mode="same")
    local_window = odd_samples(config["matched_filter"]["local_background_window_ms"], fs, minimum=3)
    floor = float(fitted_state["matched"]["matched_local_scale_floor"])
    score, local_center, local_scale = local_robust_normalize(corr, local_window, floor)
    threshold = float(config["matched_filter"]["threshold_k_mad"])
    threshold_trace = np.full(len(score), threshold, dtype=float)

    template_center = (len(template) - 1) // 2
    anchor_shift = int(template_meta["r_anchor_sample"] - template_center)
    evaluation_mask = make_evaluation_mask(x, valid, fs, config["quality"], len(template) // 2)
    score_mask = np.roll(evaluation_mask, -anchor_shift)
    if anchor_shift > 0:
        score_mask[-anchor_shift:] = False
    elif anchor_shift < 0:
        score_mask[:-anchor_shift] = False
    score_for_peaks = score.copy()
    score_for_peaks[~score_mask] = -np.inf

    refractory = int(round(config["shared"]["refractory_ms"] / 1000.0 * fs))
    peak_samples, _ = find_peaks(score_for_peaks, height=threshold, distance=max(1, refractory))
    candidate_r = peak_samples + anchor_shift
    keep = (candidate_r >= 0) & (candidate_r < len(x))
    peak_samples = peak_samples[keep]
    candidate_r = candidate_r[keep]
    keep = evaluation_mask[candidate_r]
    peak_samples = peak_samples[keep]
    candidate_r = candidate_r[keep]

    refined = refine_r_locations(filtered, candidate_r, fs, config["shared"]["r_refine_ms"])
    refined = refined[evaluation_mask[np.clip(refined, 0, len(evaluation_mask) - 1)]] if len(refined) else refined
    if len(refined):
        # Map each refined R to the strongest nearby correlation peak for refractory selection.
        strengths = []
        radius = int(round(config["shared"]["r_refine_ms"] / 1000.0 * fs))
        for r in refined:
            score_center = int(r - anchor_shift)
            lo, hi = max(0, score_center - radius), min(len(score), score_center + radius + 1)
            strengths.append(float(np.max(score[lo:hi])) if hi > lo else -np.inf)
        refined = enforce_refractory(refined, np.asarray(strengths), refractory)

    return DetectorResult(
        filtered=filtered,
        score=score,
        threshold_trace=threshold_trace,
        score_peak_samples=peak_samples,
        candidate_r_samples=candidate_r,
        r_samples=refined,
        evaluation_mask=evaluation_mask,
        local_center=local_center,
        local_scale=local_scale,
        metadata={
            "method": "matched_filter",
            "template_center_sample": int(template_center),
            "template_r_anchor_sample": int(template_meta["r_anchor_sample"]),
            "anchor_shift_samples": int(anchor_shift),
            "local_background_window_samples": int(local_window),
            "refractory_samples": int(refractory),
            "threshold_k_mad": threshold,
            "correlation_polarity": "signed",
        },
    )

def evaluate_result(fragment: dict, result: DetectorResult, config: dict) -> tuple[dict, MatchResult, np.ndarray]:
    fs = float(fragment["metadata"]["fs_hz"])
    reference = _mask_reference(fragment["r_samples"], result.evaluation_mask)
    detected = result.r_samples[result.evaluation_mask[result.r_samples]] if len(result.r_samples) else result.r_samples
    metrics, match = event_metrics(reference, detected, fs, config["event_tolerance_ms"])
    metrics.update({
        "n_reference_evaluated": int(len(reference)),
        "n_detected_evaluated": int(len(detected)),
        "valid_sample_fraction": float(np.mean(fragment["valid_mask"])),
        "evaluation_sample_fraction": float(np.mean(result.evaluation_mask)),
    })
    return metrics, match, reference

def _event_peak_z(result: DetectorResult, event: int, fs: float) -> float:
    anchor_shift = int(result.metadata.get("anchor_shift_samples", 0))
    center = int(event - anchor_shift)
    radius = max(1, int(round(0.06 * fs)))
    lo, hi = max(0, center - radius), min(len(result.score), center + radius + 1)
    return float(np.max(result.score[lo:hi])) if hi > lo else float("-inf")

def window_quality_metrics(result: DetectorResult, signal: np.ndarray, valid_mask: np.ndarray, start: int, end: int, fs: float, config: dict) -> dict:
    start, end = int(start), int(end)
    valid_fraction = float(np.mean(np.asarray(valid_mask, dtype=bool)[start:end])) if end > start else 0.0
    evaluation_fraction = float(np.mean(result.evaluation_mask[start:end])) if end > start else 0.0
    events = result.r_samples[(result.r_samples >= start) & (result.r_samples < end)]
    z_values = np.asarray([_event_peak_z(result, int(e), fs) for e in events], dtype=float)
    threshold = float(config[result.metadata["method"]]["threshold_k_mad"] if result.metadata["method"] in config else 0.0)
    peak_margin = float(np.median(np.maximum(z_values - threshold, 0.0))) if len(z_values) else 0.0
    prominence_component = float(np.clip(np.log1p(peak_margin) / np.log1p(8.0), 0.0, 1.0))

    rr_s = np.diff(events) / fs
    rr_plausible = float(np.mean((rr_s >= 0.30) & (rr_s <= 2.0))) if len(rr_s) else 0.0

    score_window = result.score[start:end]
    finite_score = score_window[np.isfinite(score_window)]
    if len(finite_score):
        background_q90 = float(np.quantile(np.abs(finite_score), 0.90))
        background_component = float(1.0 / (1.0 + max(0.0, background_q90 - threshold)))
    else:
        background_q90 = np.nan
        background_component = 0.0

    saturation_abs = float(config["quality"].get("saturation_abs_mV", np.inf))
    signal_window = np.asarray(signal, dtype=float)[start:end]
    saturation_fraction = float(np.mean(np.abs(signal_window) >= saturation_abs)) if len(signal_window) else 1.0
    completeness_component = float(np.clip(min(valid_fraction, evaluation_fraction) * (1.0 - saturation_fraction), 0.0, 1.0))

    weights = config["quality"]["sqi_weights"]
    sqi = (
        float(weights["peak_prominence"]) * prominence_component
        + float(weights["background_stability"]) * background_component
        + float(weights["rr_plausibility"]) * rr_plausible
        + float(weights["completeness"]) * completeness_component
    )
    min_valid = float(config["quality"]["window_valid_sample_fraction_min"])
    sqi_min = float(config["quality"]["sqi_min"])
    min_beats = int(config["quality"]["minimum_detected_beats"])
    available = bool(valid_fraction >= min_valid and evaluation_fraction >= min_valid and sqi >= sqi_min and len(events) >= min_beats)
    reason = ""
    if not available:
        reasons = []
        if valid_fraction < min_valid or evaluation_fraction < min_valid:
            reasons.append("incomplete_data")
        if saturation_fraction > 0:
            reasons.append("saturation")
        if sqi < sqi_min:
            reasons.append("low_sqi")
        if len(events) < min_beats:
            reasons.append("too_few_beats")
        reason = "+".join(reasons)
    return {
        "valid_sample_fraction": valid_fraction,
        "evaluation_sample_fraction": evaluation_fraction,
        "peak_margin_median": peak_margin,
        "background_q90": background_q90,
        "rr_plausible_fraction": rr_plausible,
        "saturation_fraction": saturation_fraction,
        "sqi": float(sqi),
        "result_available": available,
        "missing_reason": reason,
        "n_detected_beats": int(len(events)),
    }

def make_semisynthetic_variant(fragment: dict, variant: str, level: float, seed: int, config: dict) -> dict:
    rng = np.random.default_rng(int(seed))
    out = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in fragment.items()}
    out["metadata"] = dict(fragment["metadata"])
    out["fragment_id"] = f"{fragment['fragment_id']}__{variant}_{level:g}_s{seed}"
    out["split"] = "validation"
    x = np.asarray(fragment["signal_mV"], dtype=float).copy()
    valid = np.asarray(fragment["valid_mask"], dtype=bool).copy()
    fs = float(fragment["metadata"]["fs_hz"])
    t = np.arange(len(x)) / fs

    if variant == "white_noise_mV":
        x += float(level) * rng.standard_normal(len(x))
    elif variant == "baseline_drift_mV":
        x += float(level) * np.sin(2 * np.pi * 0.25 * t + 0.3)
    elif variant == "impulse_artifacts_mV":
        n_artifacts = max(1, int(round(len(x) / fs / 12)))
        protected = np.zeros(len(x), dtype=bool)
        radius = int(round(0.15 * fs))
        for r in fragment["r_samples"]:
            protected[max(0, r-radius):min(len(x), r+radius+1)] = True
        choices = np.flatnonzero(~protected)
        starts = rng.choice(choices, size=min(n_artifacts, len(choices)), replace=False)
        width = max(1, int(round(0.08 * fs)))
        for s in starts:
            hi = min(len(x), int(s) + width)
            x[int(s):hi] += float(level) * np.hanning(max(2, 2*(hi-int(s))))[:hi-int(s)]
    elif variant == "gap_s":
        duration = int(round(float(level) * fs))
        start = int(round(0.45 * len(x)))
        end = min(len(x), start + duration)
        valid[start:end] = False
        # Keep finite values for filtering; mask carries the missingness.
        x[start:end] = np.interp(np.arange(start, end), [max(0, start-1), min(len(x)-1, end)], [x[max(0, start-1)], x[min(len(x)-1, end)]])
    elif variant == "saturation_s":
        duration = int(round(float(level) * fs))
        start = int(round(0.62 * len(x)))
        end = min(len(x), start + duration)
        x[start:end] = np.sign(np.median(x[start:end]) or 1.0) * float(config["quality"]["saturation_abs_mV"])
        valid[start:end] = False
    elif variant == "polarity":
        x *= float(level)
    elif variant == "qrs_broadening":
        factor = float(level)
        original = x.copy()
        half = int(round(0.18 * fs))
        for r in np.asarray(fragment["r_samples"], dtype=int):
            lo, hi = max(0, r-half), min(len(x), r+half+1)
            beat = original[lo:hi]
            if len(beat) < 8:
                continue
            centered_t = np.linspace(-1, 1, len(beat))
            source_t = np.clip(centered_t / factor, -1, 1)
            broadened = np.interp(source_t, centered_t, beat)
            window = np.hanning(len(beat))
            x[lo:hi] = (1-window)*x[lo:hi] + window*broadened
    else:
        raise ValueError(f"Unknown variant: {variant}")

    out["signal_mV"] = x.astype(np.float32)
    out["valid_mask"] = valid
    out["time_s"] = np.arange(len(x), dtype=float) / fs
    out["metadata"].update({"data_type": "semisynthetic", "variant": variant, "level": float(level), "seed": int(seed)})
    return out

def hash_config(config: dict) -> str:
    import hashlib
    payload = json.dumps(config, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
