"""Funkcje wspólne: charakterystyki, stan, maska DFT i miary zachowania EKG."""
import numpy as np
from scipy import signal


def db_response(h):
    """Wartości poniżej -240 dB są obcinane wyłącznie na wykresach."""
    return 20*np.log10(np.maximum(np.abs(h),1e-12))


def group_delay_sos(sos, f, fs):
    """Numeryczna pochodna rozwiniętej fazy: wynik w próbkach, f w Hz.

    Interpretować tylko w przepuszczanym paśmie, daleko od zer odpowiedzi.
    Nie konwertuje wysokiego rzędu SOS do jednego wielomianu.
    """
    _, h = signal.sosfreqz(sos, worN=f, fs=fs)
    return -np.gradient(np.unwrap(np.angle(h)), 2*np.pi*np.asarray(f)/fs)


def filter_blocks(sos, x, block_size, keep_state=True):
    state = np.zeros((len(sos),2))
    outputs = []
    for start in range(0,len(x),block_size):
        if not keep_state:
            state = np.zeros_like(state)
        y, state = signal.sosfilt(sos,x[start:start+block_size],zi=state)
        outputs.append(y)
    return np.concatenate(outputs)


def fft_mask(x, fs, cutoff, stop=None, nfft=None):
    """Jawna symetryczna maska całego zapisu; nie jest filtrem online."""
    x = np.asarray(x,float)
    nfft = len(x) if nfft is None else int(nfft)
    if nfft < len(x):
        raise ValueError('nfft nie może obcinać danych.')
    f = np.fft.fftfreq(nfft,1/fs)
    af = np.abs(f)
    if stop is None:
        mask = (af<=cutoff).astype(float)
    else:
        if stop<=cutoff:
            raise ValueError('Nieprawidłowe granice przejścia.')
        mask = np.clip((stop-af)/(stop-cutoff),0,1)
    yc = np.fft.ifft(np.fft.fft(x,nfft)*mask)
    return yc[:len(x)].real, float(np.max(np.abs(yc.imag))), f, mask


def tone_fit(x, fs, f0, t0=0.0):
    """Amplituda tonu przez LS sinus/cosinus/stała; jawna siatka czasu.

    Przy obcięciu brzegów LS nie wymaga całkowitej liczby okresów w oknie.
    Nie jest detektorem obecności tonu ani metodą separacji współczęstotliwościowej.
    """
    t = np.arange(len(x))/fs+t0
    basis = np.column_stack([np.sin(2*np.pi*f0*t),np.cos(2*np.pi*f0*t),np.ones(len(t))])
    coef, *_ = np.linalg.lstsq(basis,np.asarray(x,float),rcond=None)
    return float(np.hypot(coef[0],coef[1]))


def psd(x, fs, seconds=4.0, demean=True):
    length = min(len(x),round(seconds*fs))
    w = signal.get_window('hann',length,fftbins=True)
    return signal.welch(x,fs=fs,window=w,nperseg=length,noverlap=length//2,nfft=length,
                        detrend='constant' if demean else False,scaling='density',average='mean')


def band_power(x, fs, low, high, seconds=4.0):
    """Suma PSD*df; włącza oba prążki graniczne, nie reguła trapezów."""
    f,p = psd(x,fs,seconds)
    mask = (f>=low)&(f<=high)
    if not mask.any():
        raise ValueError('Brak punktów PSD w paśmie.')
    return float(p[mask].sum()*(f[1]-f[0]))


def preservation_metrics(reference, test, events, fs, guard=1.0, search=.08, half_qrs=.08):
    """Miary warunkowe przy ZNANYCH zdarzeniach, bez walidacji detektora.

    Czas: lokalne maksimum w ±search od adnotacji; amplituda: wartość maksimum
    względem zera, bez korekty linii bazowej; kształt: osobne wyrównanie do R.
    Nie dopasowuje skali amplitudy ani offsetu okien QRS.
    """
    reference, test = np.asarray(reference,float), np.asarray(test,float)
    if reference.shape!=test.shape or not np.all(np.isfinite(test)):
        raise ValueError('Niezgodne lub niefinitywne sygnały.')
    n=len(reference);g=round(guard*fs);w=round(search*fs);q=round(half_qrs*fs)
    ea=[];signed=[];nr=[]
    for at in events:
        k=int(np.rint(at*fs))
        if k<g or k>=n-g:
            continue
        lo,hi=max(0,k-w),min(n,k+w+1)
        kr=lo+int(np.argmax(reference[lo:hi]));kt=lo+int(np.argmax(test[lo:hi]))
        if min(kr,kt)-q<0 or max(kr,kt)+q>=n:
            continue
        a,b=float(reference[kr]),float(test[kt])
        ea.append(100*abs(b-a)/max(abs(a),1e-12))
        signed.append(1000*(kt-kr)/fs)
        r=reference[kr-q:kr+q+1]; y=test[kt-q:kt+q+1]
        nr.append(np.sqrt(np.mean((y-r)**2))/max(np.ptp(r),1e-12))
    if not ea:
        raise ValueError('Brak zdarzeń w ocenianym obszarze.')
    err=test-reference
    return {'R_amplitude_error_pct':float(np.mean(ea)),
            'R_time_MAE_ms':float(np.mean(np.abs(signed))),
            'R_time_signed_mean_ms':float(np.mean(signed)),
            'R_time_signed_SD_ms':float(np.std(signed,ddof=0)),
            'QRS_NRMSE_aligned':float(np.mean(nr)), 'beats':len(ea),
            'RMSE_center_mV':float(np.sqrt(np.mean(err[g:-g]**2))),
            'RMSE_start_mV':float(np.sqrt(np.mean(err[:g]**2))),
            'RMSE_end_mV':float(np.sqrt(np.mean(err[-g:]**2)))}
