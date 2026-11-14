"""Lokalny okres i jawna jakość wyniku; braków nie zastępuje zerem."""
import numpy as np
from scipy import signal


def lag_bounds(fs,rate_min=80.,rate_max=200.):
    if not(0<rate_min<rate_max) or fs<=0:
        raise ValueError('Nieprawidłowy zakres rytmu lub fs.')
    low=max(1,int(np.ceil(60*fs/rate_max)))
    high=int(np.floor(60*fs/rate_min))
    if high<low:raise ValueError('Brak dopuszczalnego całkowitego opóźnienia.')
    return low,high


def objectives(x,lags):
    x=signal.detrend(np.asarray(x,float),type='linear')
    sd=x.std(ddof=0)
    if not np.isfinite(sd) or sd<1e-10:return None
    x=x/sd;r0=np.mean(x*x)
    out={k:[] for k in ['ACF','SAD','SSD']}
    for lag in lags:
        if not 0<lag<len(x):raise ValueError('Opóźnienie poza zakresem danych.')
        a,b=x[:-lag],x[lag:]
        out['ACF'].append(np.mean(a*b)/r0)
        out['SAD'].append(np.mean(abs(a-b)))
        out['SSD'].append(np.mean((a-b)**2))
    return {k:np.asarray(v) for k,v in out.items()}


def select_optimum(values,lags,method='ACF'):
    raw=np.asarray(values,float) if method=='ACF' else -np.asarray(values,float)
    span=float(raw.max()-raw.min())
    if span<1e-12:return {'lag':None,'quality':0.,'gap':0.,'interior_peak':False,'score':np.zeros(len(raw))}
    score=(raw-raw.min())/span
    idx=int(np.argmax(raw));peaks,_=signal.find_peaks(score)
    interior=idx in peaks
    quality=float(signal.peak_prominences(score,[idx])[0][0]) if interior else 0.
    candidates=[i for i in peaks if abs(i-idx)>=3]
    # 1 oznacza brak konkurenta, a nie dowód jednoznaczności źródła fizycznego.
    gap=float(score[idx]-max(score[candidates])) if candidates else 1.
    return {'lag':int(lags[idx]),'quality':quality,'gap':gap,'interior_peak':bool(interior),'score':score}


def estimate_track(x,fs,window_s=3.,step_s=.25,quality_threshold=.1,activity_threshold=0.,rate_range=(80.,200.)):
    low,high=lag_bounds(fs,*rate_range);lags=np.arange(low,high+1)
    length=round(window_s*fs);step=max(1,round(step_s*fs))
    if length<=high+5:raise ValueError('Zbyt krótkie okno względem zakresu opóźnień.')
    starts=np.arange(0,len(x)-length+1,step);rates=[];selected=[];qualities=[];activities=[];maps=[];raw_rates=[];interior=[]
    for start in starts:
        segment=x[start:start+length]
        activity=float(np.percentile(segment,95)-np.percentile(segment,5))
        obj=objectives(segment,lags)
        result=select_optimum(obj['ACF'],lags) if obj is not None else None
        quality=result['quality'] if result else 0.
        lag=result['lag'] if result else None
        is_peak=result['interior_peak'] if result else False
        accepted=bool(is_peak and quality>=quality_threshold and activity>=activity_threshold)
        rates.append(60*fs/lag if accepted else np.nan);selected.append(lag if accepted else np.nan)
        raw_rates.append(60*fs/lag if lag is not None else np.nan)
        qualities.append(quality);activities.append(activity);interior.append(is_peak)
        maps.append(result['score'] if result else np.zeros(len(lags)))
    return {'time_s':(starts+(length-1)/2)/fs,'rate':np.asarray(rates),'lag':np.asarray(selected),
            'raw_rate':np.asarray(raw_rates),'quality':np.asarray(qualities),'activity':np.asarray(activities),
            'interior_peak':np.asarray(interior),'score_map':np.asarray(maps),'lags':lags,
            'starts':starts,'stops':starts+length,'length':length,'step':step}


def evaluate_track(track,t,reference,usable,min_fraction=.8):
    fraction=np.array([np.mean(usable[a:b]) for a,b in zip(track['starts'],track['stops'])])
    eligible=fraction>=min_fraction
    ref=np.interp(track['time_s'],t,reference)
    accepted=np.isfinite(track['rate']);scored=accepted&eligible
    err=track['rate'][scored]-ref[scored]
    metrics={'MAE_per_min':float(np.mean(abs(err))) if len(err) else None,
             'RMSE_per_min':float(np.sqrt(np.mean(err*err))) if len(err) else None,
             'acceptance_all_windows':float(accepted.mean()),
             'coverage_eligible_windows':float(scored.sum()/eligible.sum()) if eligible.any() else None,
             'false_acceptance_ineligible_fraction':float((accepted&~eligible).sum()/(~eligible).sum()) if (~eligible).any() else None,
             'eligible_count':int(eligible.sum()),'ineligible_count':int((~eligible).sum()),
             'accepted_eligible_count':int(scored.sum()),'false_accept_count':int((accepted&~eligible).sum())}
    return metrics,ref,eligible,fraction


def reject_fast_changes(rate,time,limit=18.):
    out=rate.copy();rejected=np.zeros(len(rate),bool);previous=None;previous_time=None
    for i,(r,t) in enumerate(zip(rate,time)):
        if not np.isfinite(r):continue
        if previous is not None and abs(r-previous)>limit*(t-previous_time):
            out[i]=np.nan;rejected[i]=True;continue
        previous=r;previous_time=t
    return out,rejected
