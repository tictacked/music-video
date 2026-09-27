#!/usr/bin/env python
"""separate.py -- split song/audio.wav into its four Demucs stems (htdemucs, CPU) + band (= everything but vocals).

    <SEP> song/separate.py   -> song/stems/{drums,bass,other,vocals,band}.wav
    (SEP = the kit's Demucs python: `python tools/film.py SEP` prints its path. The first run downloads the model.)

Kicks/snares come from the DRUM stem (on the mix, vocal plosives read as ghost kicks), accents from drums + other,
vocal phrase TIMES (never words) from the vocal stem. About 30 s for a 2:30 song on a fast desktop CPU."""
import os
import time

import numpy as np
import soundfile as sf
import torch
from demucs.apply import apply_model
from demucs.pretrained import get_model

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    x, sr = sf.read(os.path.join(HERE, 'audio.wav'), dtype='float32', always_2d=True)
    model = get_model('htdemucs')
    model.eval()
    if sr != model.samplerate:
        import julius
        xt = julius.resample_frac(torch.from_numpy(x.T.copy()), sr, model.samplerate)
    else:
        xt = torch.from_numpy(x.T.copy())
    ref = xt.mean(0)
    mu, sd = ref.mean(), ref.std()
    t0 = time.time()
    with torch.no_grad():
        out = apply_model(model, ((xt - mu) / sd)[None], device='cpu', shifts=1, split=True, overlap=0.25,
                          progress=False, num_workers=0)[0]
    out = out * sd + mu
    names = model.sources
    os.makedirs(os.path.join(HERE, 'stems'), exist_ok=True)
    for i, n in enumerate(names):
        sf.write(os.path.join(HERE, 'stems', f'{n}.wav'), out[i].numpy().T, model.samplerate)
    band = (out.sum(0) - out[names.index('vocals')]).numpy().T
    sf.write(os.path.join(HERE, 'stems', 'band.wav'), band, model.samplerate)
    print(f'separated in {time.time() - t0:.0f}s: sources {names}')


if __name__ == '__main__':
    main()
