"""Generatory i metody E8.1–E8.15 — rekonstrukcja z 11 listopada 2026 r.

Podstawa: kanoniczny notebook CPSB M7 v.3, tekst rozdziału 8,
zachowany notebook książkowy i paszporty parametrów. To odtworzona
implementacja, a nie odzyskana bajtowo kopia utraconego modułu.
Wszystkie przebiegi są syntetyczne. Amplitudy mają jednostki umowne.
Nie stosujemy zamienników EMD, DWT ani estymatora Yule'a–Walkera.
"""

import numpy as np
from scipy import signal
from scipy.interpolate import CubicSpline
from statsmodels.regression.linear_model import yule_walker
from PyEMD import EMD

__all__ = [
    "ar_case", "fit_ar", "acf_biased", "ar_psd", "order_table",
    "emd_step_case", "one_sift", "decompose", "emd_selection_case",
    "characterize", "select_fast", "regional_errors", "emd_mixing_case",
    "template", "matched_case", "scores", "detect", "match_events",
    "reference_case", "lag_matrix", "wiener_cancel", "lms_cancel",
    "filter_metrics", "echo_source", "linear_echo", "real_cepstrum",
    "estimate_delay", "lift_echo", "periodic_source",
]


def _vector(x):
    x = np.asarray(x, dtype=float)
    if x.ndim != 1 or x.size == 0 or not np.isfinite(x).all():
        raise ValueError("Oczekiwano niepustego, skończonego wektora rzeczywistego.")
    return x


def ar_case():
    """AR(4), dwa sprzężone układy biegunów, 500 próbek rozruchu."""
    fs, n, burnin = 200, 2400, 500
    rng = np.random.default_rng(2026071202)
    den = np.convolve(
        [1, -2 * .96 * np.cos(2 * np.pi * 24 / fs), .96**2],
        [1, -2 * .93 * np.cos(2 * np.pi * 36 / fs), .93**2],
    )
    x = signal.lfilter([1], den, rng.normal(scale=1., size=n + burnin))[burnin:]
    x = (x - x.mean()) / x.std()
    return np.arange(n) / fs, x, den, fs


def fit_ar(x, order, fs=200):
    """YW z dzielnikiem N; a=-rho. Predykcja używa prawdziwej historii."""
    x = _vector(x)
    if not 1 <= order < len(x) or fs <= 0:
        raise ValueError("Wymagane 1 <= rząd < N oraz fs > 0.")
    rho, sigma = yule_walker(x, order=order, method="mle", demean=True)
    x0 = x - x.mean()
    pred = np.full_like(x0, np.nan)
    for n in range(order, len(x0)):
        pred[n] = rho @ x0[n - order:n][::-1]
    return {"rho": rho, "a": -rho, "sigma2": float(sigma**2),
            "pred": pred, "residual": x0[order:] - pred[order:], "fs": fs}


def acf_biased(x, max_lag):
    """Znormalizowana ACF, centrowanie i dzielnik N dla każdego opóźnienia."""
    x = _vector(x)
    if not 0 <= max_lag < len(x):
        raise ValueError("Opóźnienie musi mieścić się w 0..N-1.")
    x = x - x.mean()
    r = signal.correlate(x, x, mode="full", method="auto")
    r = r[len(x) - 1:len(x) + max_lag] / len(x)
    if r[0] <= 0:
        raise ValueError("ACF stałego sygnału nie jest zdefiniowana.")
    return r / r[0]


def ar_psd(fit, nfft=4096):
    """Jednostronna PSD [j.u.²/Hz]; DC i Nyquist bez podwojenia."""
    fs = fit["fs"]
    f = np.fft.rfftfreq(nfft, 1 / fs)
    k = np.arange(1, len(fit["rho"]) + 1)
    den = 1 - np.exp(-2j * np.pi * np.outer(f / fs, k)) @ fit["rho"]
    psd = (fit["sigma2"] / fs) / abs(den)**2
    psd[1:-1 if nfft % 2 == 0 else None] *= 2
    return f, psd


def order_table(x, orders, fs=200):
    """Diagnostyka przy wspólnym N; AIC/BIC używają wariancji YW."""
    rows = []
    for p in orders:
        fit = fit_ar(x, p, fs)
        f, psd = ar_psd(fit)
        band = (f > 5) & (f < 80)
        peaks = signal.find_peaks(psd[band], distance=20)[0]
        top = peaks[np.argsort(psd[band][peaks])[-2:]]
        rows.append({
            "p": p, "sigma2_YW": fit["sigma2"],
            "empirical_residual_variance": float(np.var(fit["residual"])),
            "AIC": float(len(x) * np.log(fit["sigma2"]) + 2 * p),
            "BIC": float(len(x) * np.log(fit["sigma2"]) + p * np.log(len(x))),
            "ACF2": float(np.sum(acf_biased(fit["residual"], 20)[1:]**2)),
            "max_pole": float(max(abs(np.roots(np.r_[1, fit["a"]])))),
            "top_frequencies_Hz": np.sort(f[band][top]).tolist(),
            "peak_count_5_80": len(peaks),
        })
    return rows


def emd_step_case():
    rng = np.random.default_rng(2026071203)
    t = np.arange(0, 6, 1 / 200)
    trend = .45 * np.sin(2 * np.pi * .35 * t)
    chirp = .75 * signal.chirp(t, 5, t[-1], 22) * signal.windows.tukey(len(t), .25)
    burst = .7 * np.exp(-.5 * ((t - 3.2) / .22)**2) * np.sin(2 * np.pi * 34 * t)
    return t, trend + chirp + burst + .08 * rng.normal(size=len(t))


def one_sift(x, t):
    """Ilustracja: oba splajny mają pomocnicze kotwice na końcach."""
    x = _vector(x)
    maxi = np.unique(np.r_[0, signal.find_peaks(x, distance=3)[0], len(x) - 1])
    mini = np.unique(np.r_[0, signal.find_peaks(-x, distance=3)[0], len(x) - 1])
    upper = CubicSpline(t[maxi], x[maxi])(t)
    lower = CubicSpline(t[mini], x[mini])(t)
    mean = (upper + lower) / 2
    return maxi, mini, upper, lower, mean, x - mean


def decompose(x, t, max_imf=6):
    """Pełne PyEMD; reszta pochodzi z API biblioteki, nie z testu sumy."""
    settings = {
        "spline_kind": "cubic", "nbsym": 2, "MAX_ITERATION": 300,
        "std_thr": .2, "svar_thr": .001, "energy_ratio_thr": .2,
        "range_thr": .001, "total_power_thr": .005,
        "extrema_detection": "simple", "FIXE": 0, "FIXE_H": 0,
        "max_imf": max_imf,
    }
    emd = EMD(**{k: v for k, v in settings.items() if k != "max_imf"})
    emd.emd(_vector(x), t, max_imf=max_imf)
    imfs, residue = emd.get_imfs_and_residue()
    return imfs.copy(), residue.copy(), settings


def emd_selection_case():
    rng = np.random.default_rng(2026071204)
    t = np.arange(0, 8, 1 / 200)
    slow = .35 * np.sin(2 * np.pi * .45 * t)
    b1 = np.exp(-.5 * ((t - 2.2) / .7)**2) * signal.chirp(t, 7, t[-1], 16)
    b2 = .8 * np.exp(-.5 * ((t - 5.7) / .38)**2) * np.sin(2 * np.pi * 29 * t)
    clean = slow + b1 + b2
    return t, clean, clean + .12 * rng.normal(size=len(t)), slow, b1, b2


def characterize(imfs, x, fs=200):
    energies = np.sum(imfs**2, axis=1)
    rows = []
    for i, (z, en) in enumerate(zip(imfs, energies)):
        f, p = signal.welch(z, fs, nperseg=min(512, len(z)))
        rows.append({"IMF": i + 1, "dominant_Hz": float(f[np.argmax(p)]),
                     "energy": float(en), "corr_with_input": float(np.corrcoef(z, x)[0, 1]),
                     "fraction_of_IMF_energy_sum": float(en / energies.sum())})
    return rows


def select_fast(imfs, summary):
    selected = [i for i, r in enumerate(summary) if 5 <= r["dominant_Hz"] <= 40]
    return selected, imfs[selected].sum(axis=0)


def regional_errors(x, truth):
    """RMSE: całość, środkowe 80%, oba brzegi po 10% próbek."""
    error = np.asarray(x) - np.asarray(truth)
    edge = int(.1 * len(error))
    if edge < 1:
        raise ValueError("Za krótki sygnał do podziału na brzegi i środek.")
    return {"all": float(np.sqrt(np.mean(error**2))),
            "middle": float(np.sqrt(np.mean(error[edge:-edge]**2))),
            "edges": float(np.sqrt(np.mean(np.r_[error[:edge], error[-edge:]]**2)))}


def emd_mixing_case():
    rng = np.random.default_rng(2026071205)
    t = np.arange(0, 6, 1 / 200)
    a = .75 * signal.chirp(t, 7, t[-1], 22, method="linear")
    b = .65 * signal.chirp(t, 24, t[-1], 9, method="linear")
    b[(t >= 2.75) & (t <= 3.15)] = 0
    return t, a + b + .04 * rng.normal(size=len(t)), a, b


def template(width=.025):
    """120 próbek przy 500 Hz; zadany środek ma indeks 60."""
    t = (np.arange(120) - 60) / 500
    return np.exp(-.5 * (t / width)**2) * np.cos(2 * np.pi * 38 * t)


def matched_case(pat):
    fs = 500
    t = np.arange(0, 5, 1 / fs)
    rng = np.random.default_rng(2026071216)
    x = .65 * rng.normal(size=len(t))
    truth = np.array([.8, 1.75, 2.9, 4.15])
    starts = np.array([int(tt * fs) - len(pat) // 2 for tt in truth])
    for start, amp in zip(starts, [1., .8, 1.2, .65]):
        x[start:start + len(pat)] += amp * pat
    return t, x, truth, starts


def scores(x, pat, fs=500):
    """Pełne wsparcie wzorca; normalizacja bez lokalnego centrowania."""
    x, pat = _vector(x), _vector(pat)
    if len(pat) > len(x):
        raise ValueError("Wzorzec nie może być dłuższy od danych.")
    raw = signal.correlate(x, pat, mode="valid", method="auto")
    local_norm = np.sqrt(signal.convolve(x**2, np.ones(len(pat)), mode="valid"))
    normalized = raw / (np.linalg.norm(pat) * local_norm + 1e-12)
    return {"raw": raw, "normalized": normalized,
            "time": (np.arange(len(raw)) + len(pat) // 2) / fs}


def detect(score, time, threshold, separation_s=.5):
    dt = float(time[1] - time[0])
    ix = signal.find_peaks(score, height=threshold, distance=round(separation_s / dt))[0]
    return time[ix], ix


def match_events(detected, truth, tolerance=.05):
    """Jednokrotne parowanie według rosnącego bezwzględnego błędu czasu."""
    candidates = sorted((abs(d - t), i, j) for i, d in enumerate(detected)
                        for j, t in enumerate(truth) if abs(d - t) <= tolerance)
    used_d, used_t, errors = set(), set(), []
    for _, i, j in candidates:
        if i not in used_d and j not in used_t:
            used_d.add(i)
            used_t.add(j)
            errors.append(float((detected[i] - truth[j]) * 1000))
    return {"TP": len(errors), "FP": len(detected) - len(errors),
            "FN": len(truth) - len(errors), "tolerance_s": tolerance,
            "matched_errors_ms": errors,
            "MAE_matched_ms": float(np.mean(np.abs(errors))) if errors else None}


def reference_case():
    fs = 100
    t = np.arange(0, 24, 1 / fs)
    rng = np.random.default_rng(2026071207)
    s = np.zeros_like(t)
    for tt in np.arange(.6, 24, .82):
        s += np.exp(-.5 * ((t - tt) / .045)**2)
        s += .35 * np.exp(-.5 * ((t - tt - .14) / .07)**2)
    s = (s - s.mean()) / s.std()
    source = signal.lfilter([1], [1, -.96], rng.normal(size=len(t)))
    source /= source.std()  # Bez ponownego centrowania — drugie momenty.
    ref = source + .08 * rng.normal(size=len(t))
    h1, h2 = np.array([.55, -.25, .15, .08]), np.array([.25, .35, -.18, .12])
    n1, n2 = signal.lfilter(h1, [1], source), signal.lfilter(h2, [1], source)
    artifact = np.where(t < 12, n1, n2)
    d = s + artifact + .05 * rng.normal(size=len(t))
    return t, s, d, ref, artifact, source, h1, h2


def lag_matrix(x, length):
    """Wiersz dla n: [u[n], u[n-1], ..., u[n-M+1]]."""
    x = _vector(x)
    if not 1 <= length <= len(x):
        raise ValueError("Długość filtru musi mieścić się w 1..N.")
    return np.vstack([x[length - 1 - k:len(x) - k] for k in range(length)]).T


def wiener_cancel(d, ref, time, length=12, train_until=12., ridge=1e-6):
    U = lag_matrix(ref, length)
    target, time = _vector(d)[length - 1:], np.asarray(time)[length - 1:]
    train = time < train_until
    if len(target) != len(U) or len(time) != len(U) or not train.any():
        raise ValueError("Niezgodne długości lub pusty trening.")
    R = U[train].T @ U[train] / train.sum() + ridge * np.eye(length)
    r = U[train].T @ target[train] / train.sum()
    h = np.linalg.solve(R, r)
    y = U @ h
    return {"output": target - y, "y": y, "h": h, "time": time,
            "train": train, "R": R, "r": r,
            "condition_number": float(np.linalg.cond(R))}


def lms_cancel(d, ref, length=12, mu=.002, guard_norm=1e6):
    """Stały krok LMS. Przekroczenie granicy przerywa, nie obcina wag.

    Wyjście używa wag przed aktualizacją; historia weights zapisuje wagi
    po aktualizacji. Kontrola normy odbywa się przed wyznaczeniem kolejnego
    wyjścia. Wiersz zatrzymania i dalsze są niedostępne.
    """
    U = lag_matrix(ref, length)
    target = _vector(d)[length - 1:]
    if len(target) != len(U):
        raise ValueError("Kanały muszą mieć taką samą długość.")
    h = np.zeros(length)
    y, output = np.full(len(U), np.nan), np.full(len(U), np.nan)
    weights = np.full((len(U), length), np.nan)
    stopped = None
    for i, row in enumerate(U):
        if not np.isfinite(h).all() or np.linalg.norm(h) > guard_norm:
            stopped = i
            break
        yi = h @ row
        ei = target[i] - yi
        new_h = h + mu * ei * row
        y[i], output[i], weights[i] = yi, ei, new_h
        h = new_h
    return {"y": y, "output": output, "weights": weights, "stopped_at_row": stopped}


def filter_metrics(output, truth, mask=None):
    """Miary na wspólnym zakresie; niedostępne próbki raportowane jawnie."""
    output, truth = np.asarray(output), np.asarray(truth)
    mask = np.ones(len(output), dtype=bool) if mask is None else np.asarray(mask, bool)
    finite = mask & np.isfinite(output) & np.isfinite(truth)
    fraction = float(finite.sum() / mask.sum()) if mask.any() else 0.
    if not finite.any():
        return {"MSE": None, "J": None, "G": None, "finite_fraction": fraction}
    z, s = output[finite], truth[finite]
    return {"MSE": float(np.mean((z - s)**2)), "J": float(np.mean(z**2)),
            "G": float(z @ s / (s @ s)), "finite_fraction": fraction}


def echo_source():
    fs = 16000
    t = np.arange(0, 1, 1 / fs)
    rng = np.random.default_rng(2026071208)
    x = .25 * rng.normal(size=len(t)) * np.exp(-.5 * ((t - .35) / .025)**2)
    return t, x, fs


def linear_echo(x, fs, delay_s=.085, gain=.55):
    D = round(delay_s * fs)
    h = np.zeros(D + 1)
    h[0], h[D] = 1., gain
    return signal.fftconvolve(x, h, mode="full"), h, D


def real_cepstrum(x, nfft=32768, eps=1e-10):
    x = _vector(x)
    if nfft < len(x) or eps <= 0:
        raise ValueError("FFT nie może obcinać sygnału; epsilon musi być dodatni.")
    X = np.fft.fft(x, nfft)
    return np.fft.ifft(np.log(abs(X) + eps)).real, X


def estimate_delay(cepstrum, fs, search_s=(.025, .18)):
    """Maksimum modułu, wyłącznie dodatnia pierwsza połowa reprezentacji."""
    c = _vector(cepstrum)
    q = np.arange(len(c)) / fs
    ix = np.flatnonzero((q >= search_s[0]) & (q <= search_s[1]) & (np.arange(len(c)) < len(c) // 2))
    if not len(ix):
        raise ValueError("Pusty zakres poszukiwania opóźnienia.")
    peak = int(ix[np.argmax(abs(c[ix]))])
    return peak, float(q[peak])


def lift_echo(x, fs, nfft=32768, eps=1e-10, half_width=.004, attenuation=.15):
    c, X = real_cepstrum(x, nfft, eps)
    peak, delay_s = estimate_delay(c, fs)
    width = max(1, round(half_width * fs))
    indices = np.arange(nfft)
    # Kołowo symetryczna maska: ta sama modyfikacja dla +D i -D.
    near = np.minimum(abs(indices - peak), nfft - abs(indices - peak)) <= width
    near |= np.minimum(abs(indices - (nfft - peak)), nfft - abs(indices - (nfft - peak))) <= width
    mask = np.where(near, attenuation, 1.)
    modified = mask * c
    Y = np.exp(np.fft.fft(modified).real) * np.exp(1j * np.angle(X))
    full = np.fft.ifft(Y)
    return {"mask": mask, "modified": modified, "X": X, "Y": Y,
            "output": full.real[:len(x)], "full_output": full.real,
            "imaginary_max": float(max(abs(full.imag))), "delay_s": delay_s}


def periodic_source():
    fs, period = 16000, 640
    rng = np.random.default_rng(2026071209)
    block = rng.normal(size=period) * signal.windows.hann(period, sym=False)
    x = np.tile(block, 25) + .005 * rng.normal(size=fs)
    return np.arange(len(x)) / fs, x, fs, period
