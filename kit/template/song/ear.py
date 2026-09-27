#!/usr/bin/env python
"""ear.py -- look at the VOCAL STEM between two times, at sixteenth-note resolution, to measure syllables by hand.

    <PY> song/ear.py 28.3 31.6          # loudness strip per 16th + onsets (vocal-stem spectral flux peaks)
    <PY> song/ear.py 28.3 31.6 --band   # the same for the band (drums/bass/other) instead of the voice
    (PY = the kit's python: `python tools/film.py PY` prints its path)

Every row is one beat (at 120 BPM, 0.5 s): 4 sixteenths, each drawn as a loudness glyph (' .:-=+*#%@', -60..-20
dB) followed by the onsets inside that beat (seconds). The grid is song/timing.json's (bpm, beat0, barOffset); before
it exists, song/sections.json's "beat" and "bar0". The measuring tape for the moments a transcript blurs (a fast
three-hit figure, a count-in, echoes). Hand the director TIMES, never words.
"""
import json
import os
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))


def onsets(x, sr, t0, t1):
    a = x[int(max(0, t0 - 0.2) * sr):int((t1 + 0.2) * sr)]
    n, hop = 1024, 128
    win = np.hanning(n).astype(np.float32)
    fr = 1 + (len(a) - n) // hop
    if fr < 3:
        return []
    idx = np.arange(n)[None, :] + hop * np.arange(fr)[:, None]
    S = np.log1p(10 * np.abs(np.fft.rfft(a[idx] * win, axis=1)))
    f = np.maximum(0, np.diff(S, axis=0)).sum(axis=1)
    f = np.concatenate([[0], f])
    k = 9
    base = np.convolve(f, np.ones(k * 4) / (k * 4), mode='same')
    g = f - base
    th = np.quantile(g, 0.80)
    out = []
    gap = int(0.07 * sr / hop)
    for i in range(1, len(g) - 1):
        if g[i] > th and g[i] >= g[max(0, i - gap):i + gap + 1].max():
            t = max(0, t0 - 0.2) + i * hop / sr
            if t0 <= t < t1 and (not out or t - out[-1] > 0.06):
                out.append(round(t, 3))
    return out


def main():
    t0, t1 = float(sys.argv[1]), float(sys.argv[2])
    stem = 'band.wav' if '--band' in sys.argv else 'vocals.wav'
    x, sr = sf.read(os.path.join(HERE, 'stems', stem), dtype='float32')
    x = x.mean(axis=1) if x.ndim > 1 else x
    sj = os.path.join(HERE, 'sections.json')
    SJ = json.load(open(sj, encoding='utf-8')) if os.path.exists(sj) else {}
    P, b0 = SJ.get('beat', 0.5), SJ.get('bar0', 0.0)
    tj = os.path.join(HERE, 'timing.json')
    if os.path.exists(tj):     # sections.json usually has no beat/bar0; and timing.json's bars start at barOffset
        T = json.load(open(tj, encoding='utf-8'))
        P = 60 / T['bpm']
        b0 = T['beat0'] + T.get('barOffset', 0) * P
    ons = onsets(x, sr, t0, t1)
    chars = ' .:-=+*#%@'
    k0 = int(np.floor((t0 - b0) / P))
    k1 = int(np.ceil((t1 - b0) / P))
    for k in range(k0, k1):
        bt = b0 + k * P
        if bt < 0:
            continue
        cells = ''
        for q in range(4):
            a = x[int((bt + q * P / 4) * sr):int((bt + (q + 1) * P / 4) * sr)]
            db = 20 * np.log10(np.sqrt((a ** 2).mean()) + 1e-9) if len(a) else -99
            cells += chars[int(np.clip((db + 60) / 40 * 9, 0, 9))]
        mark = '|' if k % 4 == 0 else ' '
        here = [o for o in ons if bt <= o < bt + P]
        print(f"{mark}bar {k // 4:3d}.{k % 4 + 1}  {bt:8.3f}  [{cells}]  " + ' '.join(f'{o:.3f}' for o in here))


if __name__ == '__main__':
    main()
