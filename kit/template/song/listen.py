#!/usr/bin/env python
"""listen.py -- a first real reading of the song from its Demucs stems (use it before analyze.py: for an
instrumental, with no words to lean on, or to find the stops).

    <PY> song/listen.py [--from 0 --to 123 --step 1]
    (PY = the kit's python: `python tools/film.py PY` prints its path)

Prints: tempo candidates (drum-stem attack autocorrelation), then per step: dB of mix / drums / bass / other /
vocals-band, the mix's spectral centroid, the share of energy under 150 Hz, and a loudness bar. Then the STOPS (mix
more than 18 dB under its +-4 s median for >= 0.2 s). Instrumental: the "vocals" stem is whatever Demucs heard as
voice-like (screeches, leads, samples) -- a layer, not words.
"""
import argparse
import os

import librosa
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__)).replace(os.sep, '/')
SR = 22050


def load(p):
    x, sr = sf.read(p, dtype='float32', always_2d=True)
    x = x.mean(1)
    return librosa.resample(x, orig_sr=sr, target_sr=SR) if sr != SR else x


def db(seg):
    return 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='t0', type=float, default=0)
    ap.add_argument('--to', dest='t1', type=float, default=None)
    ap.add_argument('--step', type=float, default=1.0)
    a = ap.parse_args()
    mix = load(f'{HERE}/audio.wav')
    st = {n: load(f'{HERE}/stems/{n}.wav') for n in ('drums', 'bass', 'other', 'vocals')}
    dur = len(mix) / SR
    t1 = a.t1 if a.t1 is not None else dur
    peak = np.abs(mix).max()
    print(f'duration {dur:.2f} s   mix peak {20 * np.log10(peak):.1f} dBFS')

    # tempo: autocorrelation of the drum stem's onset strength
    hop = 256
    on = librosa.onset.onset_strength(y=st['drums'], sr=SR, hop_length=hop)
    on = (on - on.mean()) / (on.std() + 1e-9)
    ac = np.correlate(on, on, 'full')[len(on) - 1:]
    lag_s = np.arange(len(ac)) * hop / SR
    ok = (lag_s >= 60 / 200) & (lag_s <= 60 / 55)
    idx = np.argsort(ac[ok])[::-1]
    cands = []
    for i in idx:
        bpm = 60 / lag_s[ok][i]
        if all(abs(bpm - c) > 2 for c, _ in cands):
            cands.append((bpm, ac[ok][i] / ac[0]))
        if len(cands) == 8:
            break
    print('tempo candidates (drums):', ', '.join(f'{b:.1f} ({s:.2f})' for b, s in cands))
    on_m = librosa.onset.onset_strength(y=mix, sr=SR, hop_length=hop)
    tempo_m = librosa.feature.tempo(onset_envelope=on_m, sr=SR, hop_length=hop, aggregate=None)
    print(f'librosa tempo (mix, median of local): {np.median(tempo_m):.1f}')

    print('\n   t    mix  drums  bass  other  voxL  cent  <150')
    step = a.step
    t = a.t0
    while t < t1 - 1e-6:
        i0, i1 = int(t * SR), int(min(t + step, dur) * SR)
        seg = mix[i0:i1]
        S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
        f = np.fft.rfftfreq(len(seg), 1 / SR)
        cen = float((f * S).sum() / (S.sum() + 1e-12))
        lo = float(S[f < 150].sum() / (S.sum() + 1e-12))
        row = [db(seg)] + [db(st[n][i0:i1]) for n in ('drums', 'bass', 'other', 'vocals')]
        bar = '#' * int(max(0, (row[0] + 45) * 1.2))
        print(f'{t:6.1f} ' + ' '.join(f'{v:5.1f}' for v in row) + f' {cen:5.0f} {lo:5.2f}  {bar}')
        t += step

    # stops: short-time dB vs a +-4 s median
    h = int(0.01 * SR)
    n = len(mix) // h
    e = np.array([db(mix[k * h:(k + 1) * h]) for k in range(n)])
    w = 400
    med = np.array([np.median(e[max(0, k - w):k + w]) for k in range(0, n, 10)])
    med = np.repeat(med, 10)[:n]
    low = e < med - 18
    stops, k = [], 0
    while k < n:
        if low[k]:
            j = k
            while j < n and low[j]:
                j += 1
            if (j - k) * 0.01 >= 0.2:
                stops.append((k * 0.01, j * 0.01))
            k = j
        else:
            k += 1
    print('\nSTOPS (mix >18 dB under its local median, >=0.2 s):', ', '.join(f'{s:.2f}-{e_:.2f}' for s, e_ in stops) or 'none')


if __name__ == '__main__':
    main()
