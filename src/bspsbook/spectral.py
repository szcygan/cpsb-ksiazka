"""Jawne normalizacje PSD i korelacji dla rzeczywistych sygnałów."""
import numpy as np
from scipy import signal


def _vector(x):
    x = np.asarray(x, dtype=float)
    if x.ndim != 1 or x.size < 2 or not np.all(np.isfinite(x)):
        raise ValueError("Wymagany skończony wektor co najmniej 2 próbek.")
    return x


def one_sided(p_two, nfft):
    """Składa dwustronną PSD w jednostronną, z kontrolą parzystości FFT."""
    out = np.array(p_two[:nfft // 2 + 1], dtype=float, copy=True)
    if nfft % 2 == 0:
        out[1:-1] *= 2
    else:
        out[1:] *= 2
    return out


def periodogram_density(x, fs, window="hann", nfft=None, demean=True):
    """Wzór (4.8); wynik jednostronny i kontrolna moc ważona (4.9)."""
    x = _vector(x)
    if not np.isfinite(fs) or fs <= 0:
        raise ValueError("fs musi być dodatnie.")
    nfft = x.size if nfft is None else int(nfft)
    if nfft < x.size:
        raise ValueError("nfft nie może obcinać danych.")
    xd = x - x.mean() if demean else x.copy()
    w = signal.get_window(window, x.size, fftbins=True)
    u = np.dot(w, w)
    p2 = np.abs(np.fft.fft(w * xd, nfft))**2 / (fs * u)
    p1 = one_sided(p2, nfft)
    return np.fft.rfftfreq(nfft, 1/fs), p1, np.dot(w*w, xd*xd) / u


def segment_starts(n, length, overlap):
    if not (isinstance(length, (int, np.integer)) and isinstance(overlap, (int, np.integer))):
        raise ValueError("Długości muszą być całkowite.")
    if not (2 <= length <= n and 0 <= overlap < length):
        raise ValueError("Wymagane: 2 <= L <= N oraz 0 <= O < L.")
    return np.arange(0, n - length + 1, length - overlap)


def welch_manual(x, fs, length, overlap, window="hann", nfft=None):
    """Średnia periodogramów pełnych segmentów; odjęcie średniej w segmencie."""
    x = _vector(x)
    starts = segment_starts(x.size, length, overlap)
    powers = []
    for start in starts:
        f, p, _ = periodogram_density(x[start:start+length], fs, window, nfft, True)
        powers.append(p)
    return f, np.mean(powers, axis=0), starts


def autocorrelation(x, divisor="N", demean=True):
    """Autokowariancja po centrowaniu; dzielnik N lub N-k."""
    x = _vector(x)
    x0 = x - x.mean() if demean else x.copy()
    n = x0.size
    raw = signal.correlate(x0, x0, mode="full", method="fft")[n-1:]
    if divisor == "N":
        c = raw / n
    elif divisor == "N-k":
        c = raw / np.arange(n, 0, -1)
    else:
        raise ValueError("Dzielnik: 'N' lub 'N-k'.")
    if c[0] <= 0:
        raise ValueError("Korelacja znormalizowana wymaga niezerowej wariancji.")
    return np.arange(n), c / c[0], c


def cross_correlation(x, y, max_lag, min_pairs=3):
    """Wzór (4.19): dodatni lag oznacza opóźnienie y względem x.

    Centrowanie globalne. Wspólne fragmenty są normalizowane energetycznie,
    bez ponownego centrowania. Zwraca NaN dla za małej liczby par lub zerowej energii.
    """
    x, y = _vector(x), _vector(y)
    if x.size != y.size:
        raise ValueError("Kanały muszą mieć wspólną siatkę i długość.")
    if max_lag < 0 or max_lag >= x.size or min_pairs < 2:
        raise ValueError("Nieprawidłowy zakres lub minimalna liczba par.")
    x0, y0 = x-x.mean(), y-y.mean()
    lags = np.arange(-int(max_lag), int(max_lag)+1)
    rho = np.full(lags.size, np.nan)
    pairs = x.size - np.abs(lags)
    for j, lag in enumerate(lags):
        if pairs[j] < min_pairs:
            continue
        if lag >= 0:
            a, b = x0[:x.size-lag], y0[lag:]
        else:
            a, b = x0[-lag:], y0[:y.size+lag]
        den = np.linalg.norm(a) * np.linalg.norm(b)
        if den > 0:
            rho[j] = np.dot(a, b) / den
    return lags, rho, pairs
