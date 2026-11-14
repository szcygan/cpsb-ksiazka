"""STFT i CWT z jawnym skalowaniem oraz zakresem danych każdej kolumny."""
import numpy as np
import pywt
from scipy import signal


def power_db(power, reference=1., floor=-100.):
    power = np.asarray(power, float)
    ref = float(power.max()) if reference is None else float(reference)
    if ref <= 0 or not np.isfinite(ref) or np.any(power < 0):
        raise ValueError('Wymagana moc nieujemna i dodatnie odniesienie.')
    return np.maximum(10*np.log10(np.maximum(power/ref, np.finfo(float).tiny)), floor)


def stft_map(x, fs=200., length=128, hop=32, nfft=512, window='hann',
             valid=True, padding='zeros'):
    x = np.asarray(x)
    if x.ndim != 1 or not np.all(np.isfinite(x)):
        raise ValueError('Wymagany skończony wektor.')
    if not (0 < hop <= length <= nfft) or len(x) < length:
        raise ValueError('Nieprawidłowy krok, okno lub FFT.')
    w = signal.get_window(window, length, fftbins=True)
    real = not np.iscomplexobj(x)
    # None zachowuje konwencję DFT indeksowanej od początku ramki.
    obj = signal.ShortTimeFFT(w, hop, fs, mfft=nfft, scale_to='psd',
                             fft_mode='onesided2X' if real else 'centered',
                             phase_shift=None)
    midpoint = length//2
    if valid:
        p0 = int(np.ceil(midpoint/hop))
        p1 = int(np.floor((len(x)-length+midpoint)/hop))+1
    else:
        p0, p1 = obj.p_range(len(x))
    if p1 <= p0:
        raise ValueError('Brak pełnych ramek na zadanej siatce.')
    coeff = obj.stft(x, p0=p0, p1=p1, padding=padding)
    centers = np.arange(p0, p1)*hop
    starts = centers-midpoint
    complete = (starts >= 0) & (starts+length <= len(x))
    return {'f': obj.f, 'time': obj.t(len(x), p0=p0, p1=p1),
            'coeff': coeff, 'power': abs(coeff)**2, 'starts': starts,
            'complete': complete, 'window': w,
            'passport': {'fs_Hz': fs, 'window': str(window), 'L': length,
                         'duration_s': length/fs, 'H': hop, 'overlap_samples': length-hop,
                         'overlap_percent': 100*(length-hop)/length, 'NFFT': nfft,
                         'dt_s': hop/fs, 'df_Hz': fs/nfft, 'PSD_unit': '(j.u.)²/Hz',
                         'valid_only': valid, 'padding': padding,
                         'first_time_s': float(centers[0]/fs), 'last_time_s': float(centers[-1]/fs),
                         'frames': len(centers), 'phase_shift': None,
                         'time_convention': 'center sample L//2; even-L geometric center is 0.5 sample earlier',
                         'detrend': 'none', 'FFT_mode': 'onesided2X' if real else 'centered'}}


def manual_psd(x, fs, length, hop, nfft, window='hann'):
    w = signal.get_window(window, length, fftbins=True)
    starts = np.arange(0, len(x)-length+1, hop)
    frames = np.array([x[s:s+length] for s in starts])
    coeff = np.fft.rfft(frames*w, nfft, axis=1).T / np.sqrt(fs*np.sum(w*w))
    if nfft % 2 == 0:
        coeff[1:-1] *= np.sqrt(2.)
    else:
        coeff[1:] *= np.sqrt(2.)
    return coeff, (starts+length//2)/fs


def cwt_map(x, fs=200., frequencies=None, wavelet='cmor1.5-1.0'):
    if frequencies is None:
        frequencies = np.geomspace(5., 80., 128)
    frequencies = np.asarray(frequencies, float)
    if np.any(frequencies <= 0) or np.any(frequencies >= fs/2):
        raise ValueError('Pseudoczęstotliwości muszą należeć do (0, fs/2).')
    scales = pywt.central_frequency(wavelet)*fs/frequencies
    coeff, f = pywt.cwt(x, scales, wavelet, sampling_period=1/fs, method='fft')
    w = pywt.ContinuousWavelet(wavelet)
    guard = max(abs(w.lower_bound), abs(w.upper_bound))*scales/fs
    return {'f': f, 'scales': scales, 'coeff': coeff, 'power': abs(coeff)**2,
            'guard': guard, 'passport': {'fs_Hz': fs, 'wavelet': wavelet,
            'frequencies_Hz': frequencies.tolist(), 'scales': scales.tolist(),
            'central_frequency_normalized': pywt.central_frequency(wavelet),
            'method': 'fft', 'sampling_period_s': 1/fs,
            'boundary': 'zero extension inherent in finite convolution',
            'edge_rule': 'nominal mother support radius * scale / fs; conservative, not universal COI',
            'coefficient_convention': 'PyWavelets discrete L2 scaling; sampling_period changes frequency labels only',
            'PSD': False}}


def connected_width(axis, values, fraction=.5):
    """Szerokość połączonego maksimum; liniowa interpolacja przecięcia progu."""
    axis = np.asarray(axis, float)
    values = np.asarray(values, float)
    i = int(np.argmax(values))
    if values[i] <= 0:
        return {'width': None, 'peak': float(axis[i]), 'clipped': True}
    cut = fraction*values[i]
    left = right = i
    while left > 0 and values[left-1] >= cut:
        left -= 1
    while right < len(values)-1 and values[right+1] >= cut:
        right += 1
    xl, xr = axis[left], axis[right]
    if left > 0:
        xl = axis[left-1]+(cut-values[left-1])/(values[left]-values[left-1])*(axis[left]-axis[left-1])
    if right < len(values)-1:
        xr = axis[right]+(cut-values[right])/(values[right+1]-values[right])*(axis[right+1]-axis[right])
    return {'width': float(xr-xl), 'peak': float(axis[i]),
            'clipped': bool(left == 0 or right == len(values)-1)}


def band_power(result, lower, upper):
    f = result['f']
    return result['power'][(f >= lower) & (f <= upper)].sum(axis=0)*(f[1]-f[0])
