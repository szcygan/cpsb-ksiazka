"""Rekonstrukcja DWT i audyt progowania względem znanego odniesienia."""
import numpy as np
import pywt


def components(x, wavelet='db4', level=4, mode='symmetric'):
    if level > pywt.dwt_max_level(len(x), pywt.Wavelet(wavelet).dec_len):
        raise ValueError('Poziom przekracza limit przyjętej obsługi brzegów.')
    coeff = pywt.wavedec(x, wavelet, level=level, mode=mode)
    labels = [f'A{level}']+[f'D{j}' for j in range(level, 0, -1)]
    parts = {}
    for k, name in enumerate(labels):
        kept = [np.zeros_like(c) for c in coeff]
        kept[k] = coeff[k].copy()
        parts[name] = pywt.waverec(kept, wavelet, mode=mode)[:len(x)]
    full = pywt.waverec(coeff, wavelet, mode=mode)[:len(x)]
    return coeff, parts, full


def denoise(x, wavelet='db4', level=4, rule='soft', alpha=1., max_detail=None):
    coeff = pywt.wavedec(x, wavelet, level=level, mode='symmetric')
    sigma = float(np.median(abs(coeff[-1]))/.6745)
    threshold = float(alpha*sigma*np.sqrt(2*np.log(len(x))))
    kept = [coeff[0].copy()]
    for i, c in enumerate(coeff[1:], 1):
        j = level-i+1
        kept.append(pywt.threshold(c, threshold, mode=rule)
                    if max_detail is None or j <= max_detail else c.copy())
    y = pywt.waverec(kept, wavelet, mode='symmetric')[:len(x)]
    return y, coeff, kept, sigma, threshold


def metrics(reference, estimate, fs, events, edge_s=.5):
    error = np.asarray(estimate)-reference
    edge = np.zeros(len(reference), bool)
    size = round(edge_s*fs)
    edge[:size] = True
    edge[-size:] = True
    amplitude_errors, time_errors = [], []
    for event in events:
        a = max(0, round((event-.07)*fs))
        b = min(len(reference), round((event+.07)*fs)+1)
        ir = a+int(np.argmax(reference[a:b]))
        ie = a+int(np.argmax(estimate[a:b]))
        amplitude_errors.append(float(estimate[ie]-reference[ir]))
        time_errors.append(float((ie-ir)/fs*1000))
    return {'RMSE': float(np.sqrt(np.mean(error**2))),
            'SNR_dB': float(10*np.log10(np.sum(reference**2)/max(np.sum(error**2),np.finfo(float).tiny))),
            'edge_RMSE': float(np.sqrt(np.mean(error[edge]**2))),
            'R_amp_median_abs': float(np.median(abs(np.asarray(amplitude_errors)))),
            'R_amp_max_abs': float(np.max(abs(np.asarray(amplitude_errors)))),
            'R_time_median_abs_ms': float(np.median(abs(np.asarray(time_errors)))),
            'R_time_max_abs_ms': float(np.max(abs(np.asarray(time_errors)))),
            'R_amplitude_signed_errors': amplitude_errors, 'R_time_signed_errors_ms': time_errors}
