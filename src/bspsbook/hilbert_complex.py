"""Reprezentacja analityczna i D/Q; jawne prążki DC/Nyquista."""
import numpy as np
from scipy import signal


def analytic_dft(x):
    x=np.asarray(x)
    if np.iscomplexobj(x) or x.ndim!=1 or len(x)<3 or not np.all(np.isfinite(x)):
        raise ValueError('Wymagany rzeczywisty skończony wektor co najmniej 3 próbek.')
    n=len(x);m=np.zeros(n);m[0]=1
    if n%2==0:
        m[1:n//2]=2;m[n//2]=1
    else:
        m[1:(n+1)//2]=2
    return np.fft.ifft(np.fft.fft(x)*m),m


def split_directions(c,fs):
    c=np.asarray(c,complex);n=len(c)
    f=np.fft.fftfreq(n,1/fs);C=np.fft.fft(c)
    positive=f>0;negative=f<0
    if n%2==0:negative[n//2]=False
    cp=np.fft.ifft(C*positive);cn=np.fft.ifft(C*negative)
    return cp,cn,c-cp-cn


def analytic_features(x,fs,amplitude_fraction=0.,guard_s=0.):
    z=signal.hilbert(np.asarray(x,float))
    amp=np.abs(z);wrapped=np.angle(z);phase=np.unwrap(wrapped)
    freq=np.gradient(phase,1/fs)/(2*np.pi)
    good=amp>amplitude_fraction*amp.max()
    # Różnica centralna wymaga także wiarygodnych sąsiadów.
    stencil=good.copy();stencil[1:-1]&=good[:-2]&good[2:]
    stencil[0]=False;stencil[-1]=False
    guard=max(1,int(np.ceil(guard_s*fs)))
    stencil[:guard]=False;stencil[-guard:]=False
    masked=np.where(stencil,freq,np.nan)
    return {'z':z,'amplitude':amp,'wrapped':wrapped,'phase':phase,
            'frequency_raw':freq,'frequency':masked,'valid':stencil,
            'amplitude_threshold':float(amplitude_fraction*amp.max())}


def packet(t,center,width,frequency,sign=1,amplitude=1.,phase=0.):
    env=amplitude*np.exp(-.5*((t-center)/width)**2)
    return env*np.exp(1j*(sign*2*np.pi*frequency*t+phase)),env


def centered_spectrum(x,fs):
    return np.fft.fftshift(np.fft.fftfreq(len(x),1/fs)),np.fft.fftshift(np.fft.fft(x))/len(x)
