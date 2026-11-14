# Generatory rozdziału 4; zachowany kod funkcji.
"""Syntetyczne dane z jawną prawdą odniesienia; brak danych pacjentów."""
import numpy as np


def colored_background(n, fs, rng):
    """Skończony generator tła ~1/f; średnia 0 i SD=1 (dzielnik N).

    Kształtowanie FFT wprowadza okresową konstrukcję i odcięcie przy 1/T.
    Normalizacja pojedynczego zapisu nie definiuje uniwersalnego modelu EEG.
    """
    f = np.fft.rfftfreq(n, 1/fs)
    shape = np.zeros(f.size)
    shape[1:] = 1 / np.sqrt(f[1:])
    z = np.fft.irfft(np.fft.rfft(rng.normal(size=n)) * shape, n=n)
    z -= z.mean()
    return z / np.std(z, ddof=0)


def pulse_train(fs, duration, period, jitter_sd, noise_sd, seed):
    rng = np.random.default_rng(seed)
    t = np.arange(round(fs*duration)) / fs
    events, at = [], 0.5
    while at < duration-0.3:
        events.append(at)
        at += max(period + rng.normal(0, jitter_sd), 0.3)
    clean = np.zeros(t.size)
    for at in events:
        clean += np.exp(-0.5*((t-at)/0.05)**2)
    return t, clean+rng.normal(0, noise_sd, t.size), np.asarray(events), clean


def evoked_response(t, amplitude=1.0, width=1.0):
    """Trzy gładkie komponenty w µV, t w sekundach; nie model kliniczny."""
    return amplitude * (
        2.2*np.exp(-0.5*((t-0.065)/(0.018*width))**2)
        -4.0*np.exp(-0.5*((t-0.105)/(0.024*width))**2)
        +3.0*np.exp(-0.5*((t-0.165)/(0.038*width))**2)
    )


def delay_zeros(x, delay):
    """Opóźnienie całkowite >=0, bez kołowego zawijania."""
    if delay < 0:
        raise ValueError("Opóźnienie musi być nieujemne.")
    out = np.zeros_like(x)
    if delay == 0:
        out[:] = x
    elif delay < len(x):
        out[delay:] = x[:-delay]
    return out


# Generatory rozdziału 5; zachowany kod funkcji.
"""Jawny generator dydaktyczny z kanonicznego M4, bez danych pacjentów."""
import numpy as np


def synthetic_ecg(fs=1000.0, duration=12.0, heart_rate=72.0, seed=2026):
    t = np.arange(round(fs*duration)) / fs
    events = np.arange(.7, duration-.45, 60/heart_rate)
    params = {'P':(-.200,.12,.045), 'Q':(-.045,-.16,.012),
              'R':(0.,1.,.010), 'S':(.045,-.25,.014), 'T':(.280,.35,.070)}
    clean = np.zeros(t.size)
    for at in events:
        for offset, amplitude, width in params.values():
            clean += amplitude*np.exp(-.5*((t-at-offset)/width)**2)
    baseline = .18*np.sin(2*np.pi*.25*t+.25)+.05*np.sin(2*np.pi*.06*t+1.1)
    mains = .08*np.sin(2*np.pi*50*t+.6)
    noise = np.random.default_rng(seed).normal(0,.028,t.size)
    return t, clean, clean+baseline+mains+noise, events, {
        'baseline':baseline, 'mains':mains, 'noise':noise}


# Generatory rozdziału 6; zachowany kod funkcji.
"""Dydaktyczny model D/Q i powtarzalnych paczek; nie jest modelem klinicznym."""
import numpy as np
from scipy.integrate import cumulative_trapezoid
from .hilbert_complex import packet


def rate_profile(t):
    return 120+40/(1+np.exp(-(t-12)/3))-12/(1+np.exp(-(t-24)/2.5))


def moving_dq(fs=500.,duration=32.,seed=20260719):
    t=np.arange(round(fs*duration))/fs
    phase=cumulative_trapezoid(rate_profile(t)/60,t,initial=0)
    phase-=np.interp(.5,t,phase)
    levels=np.arange(0,np.interp(duration-.5,t,phase),1.)
    events=np.interp(levels,phase,t)
    c=np.zeros(len(t),complex)
    for i,at in enumerate(events):
        amp=1+.12*np.sin(.8*i)
        p,_=packet(t,at,.030,68+3*np.sin(.3*i),1,amp)
        q,_=packet(t,at+.145,.042,52+2*np.cos(.4*i),-1,.75*amp,.4)
        c+=p+q
    drop=(t>=14)&(t<=17);c[drop]*=.03
    rng=np.random.default_rng(seed)
    artifact=(t>=23)&(t<=23.35)
    c[artifact]+=2.5*(rng.normal(size=artifact.sum())+1j*rng.normal(size=artifact.sum()))
    c+=.06*(rng.normal(size=len(t))+1j*rng.normal(size=len(t)))
    return t,c,events,drop,artifact


# Generatory rozdziału 7; zachowany kod funkcji.
"""Generatory kontrolne przyjęte z M6; parametry jawne, jednostki umowne."""
import numpy as np
from scipy.signal import chirp, windows

def gaussian_envelope(t, center, sigma):
    return np.exp(-.5*((np.asarray(t)-center)/sigma)**2)


def make_tf_puzzle(fs=200.0, block_duration=2.0, noise_std=0.03, seed=202606):
    """Tworzy dwa sygnały z tych samych bloków ułożonych od innego punktu startowego."""
    n_block = int(round(block_duration * fs))
    t_local = np.arange(n_block) / fs
    rng = np.random.default_rng(seed)
    taper = windows.tukey(n_block, alpha=0.25)

    blocks = {
        'oscylacja 12 Hz': 0.9 * taper * np.sin(2 * np.pi * 12 * t_local),
        'paczka 35 Hz': (
            1.15 * np.exp(-0.5 * ((t_local - block_duration / 2) / 0.18) ** 2)
            * np.sin(2 * np.pi * 35 * t_local)
        ),
        'świergot 18–45 Hz': (
            0.85 * taper * chirp(
                t_local, f0=18, f1=45, t1=block_duration, method='linear'
            )
        ),
    }

    # Każdy blok otrzymuje własną, stałą realizację szumu.
    # Przestawiamy całe bloki, a nie generujemy nowego szumu.
    for name in list(blocks):
        blocks[name] = blocks[name] + noise_std * rng.standard_normal(n_block)

    order_a = ['oscylacja 12 Hz', 'paczka 35 Hz', 'świergot 18–45 Hz']
    order_b = ['świergot 18–45 Hz', 'oscylacja 12 Hz', 'paczka 35 Hz']
    x_a = np.concatenate([blocks[name] for name in order_a])
    x_b = np.concatenate([blocks[name] for name in order_b])
    t = np.arange(x_a.size) / fs
    return t, x_a, x_b, order_a, order_b, blocks, n_block

def make_stft_intro_signal(fs=200.0, duration=6.0):
    n = int(round(fs * duration))
    t = np.arange(n) / fs
    f0, f1 = 10.0, 50.0
    x_chirp = 0.75 * chirp(t, f0=f0, f1=f1, t1=duration, method='linear')
    f_chirp = f0 + (f1 - f0) * t / duration
    packet_center = 1.70
    packet_sigma = 0.14
    envelope = np.exp(-0.5 * ((t - packet_center) / packet_sigma) ** 2)
    x_packet = 1.15 * envelope * np.sin(2 * np.pi * 35.0 * t)
    x = x_chirp + x_packet
    return t, x, x_chirp, x_packet, f_chirp, packet_center

def make_parameter_signal(fs=200.0, duration=6.0, seed=6301):
    rng = np.random.default_rng(seed)
    t = np.arange(int(round(fs * duration))) / fs

    env_close = gaussian_envelope(t, 2.40, 0.48)
    x_close = (
        0.85 * env_close * np.sin(2 * np.pi * 28.0 * t)
        + 0.75 * env_close * np.sin(2 * np.pi * 32.0 * t)
    )

    short_center = 4.16
    env_short = gaussian_envelope(t, short_center, 0.045)
    x_short = 1.30 * env_short * (
        0.65 * np.sin(2 * np.pi * 62.0 * t)
        + 0.45 * np.sin(2 * np.pi * 72.0 * t)
        + 0.30 * np.sin(2 * np.pi * 82.0 * t)
    )

    env_emg = gaussian_envelope(t, 5.05, 0.20)
    x_emg_like = 0.35 * env_emg * (
        np.sin(2 * np.pi * 45.0 * t)
        + 0.60 * np.sin(2 * np.pi * 55.0 * t)
        + 0.35 * np.sin(2 * np.pi * 68.0 * t)
    )

    noise = 0.015 * rng.normal(size=t.size)
    x = x_close + x_short + x_emg_like + noise
    return t, x, x_close, x_short, x_emg_like, short_center

def make_window_test_signal(fs=200.0, duration=6.0, seed=6302):
    rng = np.random.default_rng(seed)
    t = np.arange(int(round(fs * duration))) / fs
    env = gaussian_envelope(t, 2.40, 0.50)
    x = (
        1.00 * env * np.sin(2 * np.pi * 28.0 * t)
        + 0.06 * env * np.sin(2 * np.pi * 42.0 * t)
        + 0.005 * rng.normal(size=t.size)
    )
    return t, x

def make_eeg_like_case_s4(fs=200.0, duration=8.0, seed=6404):
    rng = np.random.default_rng(seed)
    t = np.arange(int(round(fs * duration))) / fs
    background = (
        0.20 * np.sin(2*np.pi*3.0*t + 0.4)
        + 0.10 * np.sin(2*np.pi*7.0*t + 1.1)
        + 0.06 * rng.normal(size=t.size)
    )
    spindle_center = 3.0
    spindle_env = gaussian_envelope(t, spindle_center, 0.45)
    spindle = 0.75 * spindle_env * np.sin(2*np.pi*13.0*t)
    transient_center = 5.35
    transient = 1.15 * gaussian_envelope(t, transient_center, 0.035)
    x = background + spindle + transient
    return t, x, background, spindle, transient, spindle_center, transient_center

def make_eeg_emg_case_s5(fs=200.0, duration=8.0, seed=6502):
    rng = np.random.default_rng(seed)
    t = np.arange(int(round(fs * duration))) / fs
    background = (
        0.12 * np.sin(2*np.pi*3.0*t + 0.4)
        + 0.05 * np.sin(2*np.pi*7.0*t + 1.1)
        + 0.035 * rng.normal(size=t.size)
    )
    eeg_center, eeg_sigma, eeg_f = 2.40, 0.45, 13.0
    eeg_env = gaussian_envelope(t, eeg_center, eeg_sigma)
    eeg = 0.75 * eeg_env * np.sin(2*np.pi*eeg_f*t)

    emg_center, emg_sigma = 5.30, 0.12
    emg_env = gaussian_envelope(t, emg_center, emg_sigma)
    emg = 0.42 * emg_env * (
        np.sin(2*np.pi*45.0*t + 0.2)
        + 0.75*np.sin(2*np.pi*55.0*t + 1.0)
        + 0.55*np.sin(2*np.pi*68.0*t + 2.0)
    )
    x = background + eeg + emg
    truth = {
        'eeg_center_s': eeg_center, 'eeg_sigma_s': eeg_sigma, 'eeg_frequency_Hz': eeg_f,
        'emg_center_s': emg_center, 'emg_sigma_s': emg_sigma,
    }
    return t, x, background, eeg, emg, truth

def make_two_band_signal(fs=200.0, duration=4.0):
    t = np.arange(int(round(fs*duration))) / fs
    slow = 0.9*np.sin(2*np.pi*4.0*t)
    fast = 0.45*gaussian_envelope(t, 2.15, 0.35)*np.sin(2*np.pi*42.0*t + 0.3)
    pulse = 0.65*gaussian_envelope(t, 1.20, 0.025)
    return t, slow + fast + pulse, slow, fast, pulse

def make_synthetic_ecg(fs=200.0, duration=8.0, seed=6606):
    rng = np.random.default_rng(seed)
    t = np.arange(int(round(fs*duration))) / fs
    clean = np.zeros_like(t)
    beat_times = np.arange(0.75, duration-0.2, 1.0)
    for b in beat_times:
        clean += 0.11*gaussian_envelope(t, b-0.20, 0.035)   # P
        clean += -0.16*gaussian_envelope(t, b-0.035, 0.012) # Q
        clean += 1.00*gaussian_envelope(t, b, 0.014)        # R
        clean += -0.24*gaussian_envelope(t, b+0.028, 0.014) # S
        clean += 0.28*gaussian_envelope(t, b+0.24, 0.075)   # T
    drift = 0.22*np.sin(2*np.pi*0.35*t + 0.5)
    hf = 0.075*np.sin(2*np.pi*58.0*t + 0.2)
    noise = 0.025*rng.normal(size=t.size)
    observed = clean + drift + hf + noise
    return t, clean, observed, drift, hf+noise, beat_times

def make_ecg_wavelet_case(fs=250.0, duration=10.0, seed=6701):
    rng = np.random.default_rng(seed)
    t = np.arange(int(round(fs*duration))) / fs
    clean = np.zeros_like(t)
    r_times = np.arange(0.8, duration-0.3, 1.0)
    for r in r_times:
        clean += 0.10*gaussian_envelope(t, r-0.19, 0.035)
        clean += -0.16*gaussian_envelope(t, r-0.030, 0.010)
        clean += 1.00*gaussian_envelope(t, r, 0.013)
        clean += -0.24*gaussian_envelope(t, r+0.026, 0.013)
        clean += 0.27*gaussian_envelope(t, r+0.24, 0.070)

    white = 0.080*rng.normal(size=t.size)
    hf = 0.045*np.sin(2*np.pi*65*t + 0.2)
    # Dwa krótkie artefakty o amplitudzie porównywalnej z mniejszymi cechami EKG.
    artifacts = (
        0.34*gaussian_envelope(t, 3.35, 0.018)
        - 0.28*gaussian_envelope(t, 7.15, 0.022)
    )
    noise = white + hf + artifacts
    observed = clean + noise
    return t, clean, observed, noise, white+hf, artifacts, r_times

def make_mismatched_case(fs=200.0, duration=8.0, seed=6803):
    rng = np.random.default_rng(seed)
    t = np.arange(int(round(fs*duration)))/fs

    # Dwie nieregularne składowe o zmiennych częstotliwościach, które przecinają się.
    f1 = 7.0 + 16.0*(t/duration) + 2.4*np.sin(2*np.pi*0.43*t)
    f2 = 30.0 - 20.0*(t/duration) + 2.0*np.sin(2*np.pi*0.31*t + 1.1)
    f1 += 2.0*(t > 5.1)  # nagła zmiana prawa częstotliwości
    f2 -= 2.5*(t > 3.0)

    phase1 = 2*np.pi*np.cumsum(f1)/fs
    phase2 = 2*np.pi*np.cumsum(f2)/fs
    a1 = 0.55 + 0.45*gaussian_envelope(t, 2.1, 0.75) + 0.30*gaussian_envelope(t, 6.3, 0.55)
    a2 = 0.25 + 0.65*gaussian_envelope(t, 3.8, 1.15)
    c1 = a1*np.sin(phase1)
    c2 = a2*np.sin(phase2 + 0.4)
    transient = 0.85*gaussian_envelope(t, 4.05, 0.035) - 0.45*gaussian_envelope(t, 4.11, 0.050)
    slow = 0.12*np.sin(2*np.pi*1.2*t + 0.3)
    noise = 0.05*rng.normal(size=t.size)
    x = c1 + c2 + transient + slow + noise
    return t, x, c1, c2, transient, f1, f2, a1, a2

