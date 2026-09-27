#!/usr/bin/env python
"""analyze.py -- the time map of the song.

    <PY> song/analyze.py [--print]   -> song/reading.json (+ a printed report)
    (PY = the kit's python: `python tools/film.py PY` prints its path)

Needs song/audio.wav and the Demucs stems (song/separate.py). The tempo search starts at film.json bpmHint.

LYRIC-FREE: vocal activity is measured as TIMES from the vocal stem's loudness; no words, ever.

1. GRID. A high-resolution attack envelope of the drum stem (hop 64 samples = 1.45 ms, log-energy rise) so the grid
   sits on the transients themselves (librosa's onset_detect is ~20 ms late, beat_track ~27 ms: measured with a click
   track). Tempo = the autocorrelation peak near film.json bpmHint, then a fine grid search over (period, phase)
   maximising the attack energy under every predicted beat. One straight line: it assumes a DAW production at one
   fixed tempo.
2. DOWNBEAT. 4 candidate phases scored by kick energy on beat 1 + bass-chroma change at the bar line.
3. PER BAR: loudness of mix / drums / bass / other / vocals (dB), vocal coverage (fraction of the bar sung).
4. HITS: onsets of drums and other with LOCAL strength (+-3 s normalisation, so a quiet verse's hits still count),
   ACCENTS = the strongest (min gap 0.18 s); KICKS / SNARES from the drum stem split by band (low < 150 Hz vs 1.5-6 kHz).
5. STOPS: the band stem under -38 dBFS (relative) for >= 0.2 s.
"""
import json
import os
import sys

import librosa
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__)).replace(os.sep, '/')
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'tools'))
from film import FILM  # noqa: E402
SR = 44100


def load(name):
    x, sr = sf.read(f'{HERE}/{name}', dtype='float32', always_2d=True)
    x = x.mean(1)
    if sr != SR:
        x = librosa.resample(x, orig_sr=sr, target_sr=SR)
    return x


def attack_env(x, hop=64, smooth=0.004):
    """log-energy rise per hop: a transient's leading edge, no centering lag."""
    n = len(x) // hop
    e = np.add.reduceat(x[:n * hop] ** 2, np.arange(0, n * hop, hop)) / hop
    k = max(1, int(smooth * SR / hop))
    e = np.convolve(e, np.ones(k) / k, mode='same')
    le = 10 * np.log10(e + 1e-10)
    d = np.diff(le, prepend=le[0])
    d[d < 0] = 0
    t = (np.arange(n) * hop + hop / 2) / SR
    return t, d


def fit_grid(t, d, bpm0, dur):
    """grid search (period, phase) maximising attack energy within +-6 ms of each predicted beat."""
    dt = t[1] - t[0]
    best = None
    for bpm in np.arange(bpm0 - 0.8, bpm0 + 0.8, 0.005):
        p = 60.0 / bpm
        for ph in np.arange(0, p, 0.002):
            beats = np.arange(ph, dur - 0.05, p)
            idx = np.round((beats - t[0]) / dt).astype(int)
            idx = idx[(idx > 4) & (idx < len(d) - 5)]
            s = sum(d[idx + o] for o in range(-4, 5)).sum()
            if best is None or s > best[0]:
                best = (s, bpm, ph)
    # refine phase at 0.25 ms
    s0, bpm, ph = best
    p = 60.0 / bpm
    for ph2 in np.arange(ph - 0.004, ph + 0.004, 0.00025):
        beats = np.arange(ph2, dur - 0.05, p)
        idx = np.round((beats - t[0]) / dt).astype(int)
        idx = idx[(idx > 4) & (idx < len(d) - 5)]
        s = sum(d[idx + o] for o in range(-2, 3)).sum()
        if s > s0:
            s0, ph = s, ph2
    return bpm, ph


def db(x):
    return float(10 * np.log10(np.mean(x ** 2) + 1e-12))


def onsets_local(y, sr=22050, hop=256, lag=0.020):
    env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    idx = librosa.onset.onset_detect(onset_envelope=env, sr=sr, hop_length=hop, backtrack=False, units='frames')
    t = librosa.frames_to_time(idx, sr=sr, hop_length=hop) - lag      # librosa's measured lag
    raw = env[idx]
    s = np.zeros(len(idx))
    for i, a in enumerate(t):
        near = raw[(t > a - 3) & (t < a + 3)]
        s[i] = raw[i] / (np.percentile(near, 90) + 1e-9)
    glob = raw / (np.percentile(raw, 98) + 1e-9)
    s = np.clip(0.6 * s / 1.25 + 0.4 * glob, 0, 1)
    return [(round(float(a), 3), round(float(b), 3)) for a, b in zip(t, s) if a >= 0]


def band_onsets(x, lo, hi, thresh=0.35, gap=0.09):
    """kick/snare picker: attack envelope of a band-passed drum stem, peaks over a local threshold."""
    S = np.abs(librosa.stft(x, n_fft=1024, hop_length=128))
    f = librosa.fft_frequencies(sr=SR, n_fft=1024)
    e = S[(f >= lo) & (f < hi)].sum(0)
    le = np.log(e + 1e-6)
    d = np.diff(le, prepend=le[0])
    d[d < 0] = 0
    d = d / (np.percentile(d, 99.5) + 1e-9)
    t = librosa.frames_to_time(np.arange(len(d)), sr=SR, hop_length=128) - 1024 / 2 / SR  # centred frames
    out, last = [], -1
    for i in range(1, len(d) - 1):
        if d[i] > thresh and d[i] >= d[i - 1] and d[i] >= d[i + 1] and t[i] - last > gap:
            out.append((round(float(t[i]), 3), round(float(min(1.0, d[i])), 3)))
            last = t[i]
    return out


def main():
    mix = load('audio.wav')
    st = {n: load(f'stems/{n}.wav') for n in ('drums', 'bass', 'other', 'vocals', 'band')}
    dur = len(mix) / SR
    # 1. tempo prior from librosa, then the fine fit on the drum stem's attacks
    y22 = librosa.resample(st['drums'], orig_sr=SR, target_sr=22050)
    oenv = librosa.onset.onset_strength(y=y22, sr=22050, hop_length=256)
    bpm0 = float(librosa.feature.tempo(onset_envelope=oenv, sr=22050, hop_length=256, start_bpm=float(FILM.get('bpmHint', 120)))[0])
    t, d = attack_env(st['drums'])
    bpm, ph = fit_grid(t, d, bpm0, dur)
    P = 60.0 / bpm
    beats = np.arange(ph, dur, P)
    # 2. downbeat phase: kick energy on beat 1 + bass chroma change at the bar line
    kicks = band_onsets(st['drums'], 30, 150, thresh=0.3)
    snares = band_onsets(st['drums'], 1500, 6000, thresh=0.3)
    kt = np.array([k for k, _ in kicks])
    C = librosa.feature.chroma_cqt(y=librosa.resample(st['bass'], orig_sr=SR, target_sr=22050), sr=22050, hop_length=512)
    ct = librosa.frames_to_time(np.arange(C.shape[1]), sr=22050, hop_length=512)
    score = []
    for q in range(4):
        s = 0.0
        for b in beats[q::4]:
            if len(kt) and np.min(np.abs(kt - b)) < 0.03:
                s += 1
            a = C[:, (ct > b - 0.25) & (ct < b)].mean(1) if np.any((ct > b - 0.25) & (ct < b)) else None
            c = C[:, (ct > b) & (ct < b + 0.25)].mean(1) if np.any((ct > b) & (ct < b + 0.25)) else None
            if a is not None and c is not None:
                s += 2 * float(np.linalg.norm(c / (c.sum() + 1e-9) - a / (a.sum() + 1e-9)))
        score.append(round(s, 2))
    q = int(np.argmax(score))
    bars = beats[q::4]
    # 3. per bar
    rows = []
    for i, b0 in enumerate(bars):
        b1 = b0 + 4 * P
        i0, i1 = int(b0 * SR), int(min(b1, dur) * SR)
        if i1 - i0 < SR * 0.2:
            continue
        v = st['vocals'][i0:i1]
        # vocal coverage: 20 ms windows over -35 dB relative to the song's vocal peak
        w = int(0.02 * SR)
        n = len(v) // w
        vr = 10 * np.log10(np.mean(v[:n * w].reshape(n, w) ** 2, 1) + 1e-12) if n else np.array([-99])
        rows.append(dict(bar=i, t=round(float(b0), 3), mix=round(db(mix[i0:i1]), 1), drums=round(db(st['drums'][i0:i1]), 1),
                         bass=round(db(st['bass'][i0:i1]), 1), other=round(db(st['other'][i0:i1]), 1),
                         vox=round(db(v), 1), vcov=vr))
    vpk = max(float(np.max(r['vcov'])) for r in rows)
    for r in rows:
        r['vcov'] = round(float(np.mean(r['vcov'] > vpk - 30)), 2)
    # vocal phrases (times only): runs of 20 ms windows over the threshold, merged across gaps < 0.25 s
    v = st['vocals']
    w = int(0.02 * SR)
    n = len(v) // w
    vr = 10 * np.log10(np.mean(v[:n * w].reshape(n, w) ** 2, 1) + 1e-12)
    on = vr > vpk - 30
    phrases, i = [], 0
    while i < n:
        if on[i]:
            j = i
            while j < n and on[j]:
                j += 1
            phrases.append([i * 0.02, j * 0.02])
            i = j
        else:
            i += 1
    merged = []
    for a, b in phrases:
        if merged and a - merged[-1][1] < 0.25:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    merged = [[round(a, 2), round(b, 2)] for a, b in merged if b - a >= 0.15]
    # 4. hits
    y22o = librosa.resample(st['other'], orig_sr=SR, target_sr=22050)
    dh = onsets_local(y22)
    oh = onsets_local(y22o)
    allh = sorted([(a, s, 'd') for a, s in dh] + [(a, s, 'o') for a, s in oh], key=lambda z: -z[1])
    acc = []
    for a, s, k in allh:
        if s < 0.55:
            break
        if all(abs(a - b) > 0.18 for b, _, _ in acc):
            acc.append((a, s, k))
    acc.sort()
    # 5. stops: band stem quiet
    bd = st['band']
    w = int(0.01 * SR)
    n = len(bd) // w
    br = 10 * np.log10(np.mean(bd[:n * w].reshape(n, w) ** 2, 1) + 1e-12)
    bpk = np.percentile(br, 99)
    quiet = br < bpk - 38
    stops, i = [], 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if (j - i) * 0.01 >= 0.2:
                stops.append([round(i * 0.01, 2), round(j * 0.01, 2)])
            i = j
        else:
            i += 1
    out = dict(duration=round(dur, 3), bpm=round(bpm, 4), beat_period=round(P, 5), beat0=round(float(ph), 4),
               bpm_librosa=round(bpm0, 2), downbeat_phase=q, downbeat_scores=score, bar0=round(float(bars[0]), 4),
               beats=[round(float(b), 4) for b in beats], bars=rows, vocal_phrases=merged, kicks=kicks, snares=snares,
               drum_onsets=dh, other_onsets=oh, accents=[(a, s, k) for a, s, k in acc], stops=stops)
    json.dump(out, open(f'{HERE}/reading.json', 'w'), indent=1)
    if '--print' in sys.argv or True:
        print(f'duration {dur:.3f}  librosa bpm {bpm0:.2f}  fitted bpm {bpm:.4f}  beat0 {ph:.4f}  period {P:.5f}')
        print(f'downbeat phase {q} (scores {score})  bar0 {bars[0]:.3f}')
        print('bar   t      mix  drums  bass other  vox  vcov')
        for r in rows:
            print(f"{r['bar']:3d} {r['t']:7.3f} {r['mix']:6.1f} {r['drums']:6.1f} {r['bass']:6.1f} {r['other']:6.1f} {r['vox']:6.1f}  {r['vcov']:.2f}")
        print('vocal phrases:', ' '.join(f'{a:.2f}-{b:.2f}' for a, b in merged))
        print('stops:', stops)
        print(f'accents ({len(acc)}):', ' '.join(f'{a:.2f}{k}' for a, s, k in acc))
        print(f'kicks {len(kicks)} snares {len(snares)}')


if __name__ == '__main__':
    main()
