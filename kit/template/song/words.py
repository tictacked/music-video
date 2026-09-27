#!/usr/bin/env python
"""words.py -- WHEN the words are sung, from faster-whisper: song/private/words.json + segments.json.

    <PY> song/words.py                           # the vocal stem if it exists (song/stems/vocals.wav), else audio.wav
    <PY> song/words.py --model small             # faster and rougher (default large-v3-turbo: ~1.6 GB on first use)
    <PY> song/words.py --lang ja                 # force the language (whisper picks ONE per file otherwise)
    <PY> song/words.py --prompt song/private/lyrics.txt   # the lyric sheet as a hint (it stays private)
    <PY> song/words.py --from 30 --to 60         # only a window (seconds)
(<PY> = the kit's python: python tools/film.py PY. Needs: python <kit>/setup.py --whisper.)

It prints ONLY counts and times. A song's words stay in song/private/ and nowhere else: not on screen, not in code,
docs, briefs or messages. Lyric text in a painter's context can trip the API's output filter and kill the painter
mid-reel, and a commercial song's lyrics are not ours to reprint. Painters get TIMES (song/timing.json vox, and hooks
named by number), never words.

What whisper can and can't do (measured on real songs):
- it hears maybe 70% of a sung song: backing-vocal parentheticals, asides in a second language and chants go missing;
  it picks ONE language per file (mixed-language songs: run twice with --lang, or use the vocal stem in windows);
- its word STARTS run early: snap a word you cut on to the vocal stem's onset (song/ear.py prints them);
- segment timestamps stay right even where the words are wrong: map lyric lines to segments in order;
- when it hears little (a made-up language, glitch syllables): run it on the vocal STEM, prompt it with the lyric
  sheet, and if that fails write a hand word table (each word's start, '~' = estimate) from song/ear.py.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PRIV = os.path.join(HERE, 'private')


def load_model(name, device):
    from faster_whisper import WhisperModel
    if device == 'auto':
        try:
            import ctranslate2
            device = 'cuda' if ctranslate2.get_cuda_device_count() > 0 else 'cpu'
        except Exception:
            device = 'cpu'
    try:
        return WhisperModel(name, device=device, compute_type='float16' if device == 'cuda' else 'int8'), device
    except Exception as e:
        if device == 'cuda':
            print(f'  (CUDA failed: {str(e)[:120]}; falling back to the CPU)', flush=True)
            return WhisperModel(name, device='cpu', compute_type='int8'), 'cpu'
        raise


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('audio', nargs='?')
    ap.add_argument('--model', default='large-v3-turbo')
    ap.add_argument('--lang')
    ap.add_argument('--prompt', help='a text file with the lyric sheet (kept private)')
    ap.add_argument('--device', default='auto', choices=['auto', 'cpu', 'cuda'])
    ap.add_argument('--from', dest='t0', type=float)
    ap.add_argument('--to', dest='t1', type=float)
    a = ap.parse_args()
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        sys.exit('faster-whisper is not installed: python <kit>/setup.py --whisper')
    src = a.audio or next((p for p in (os.path.join(HERE, 'stems', 'vocals.wav'), os.path.join(HERE, 'audio.wav'))
                           if os.path.isfile(p)), None)
    if not src or not os.path.isfile(src):
        sys.exit('no audio: song/audio.wav (and ideally song/stems/vocals.wav from song/separate.py)')
    clip = None
    if a.t0 is not None or a.t1 is not None:
        import numpy as np
        import soundfile as sf
        x, sr = sf.read(src, dtype='float32', always_2d=True)
        i0, i1 = int((a.t0 or 0) * sr), int(a.t1 * sr) if a.t1 else len(x)
        clip = x[i0:i1].mean(1)
        if sr != 16000:
            import librosa
            clip = librosa.resample(clip, orig_sr=sr, target_sr=16000)
        clip = clip.astype(np.float32)
    prompt = open(a.prompt, encoding='utf-8').read() if a.prompt else None
    t = time.time()
    model, device = load_model(a.model, a.device)
    segs, info = model.transcribe(clip if clip is not None else src, language=a.lang, word_timestamps=True,
                                  initial_prompt=prompt, beam_size=5, vad_filter=False)
    off = a.t0 or 0.0
    words, segments = [], []
    for si, s in enumerate(segs):
        segments.append(dict(i=si, s=round(s.start + off, 3), e=round(s.end + off, 3), text=s.text.strip()))
        for w in (s.words or []):
            words.append(dict(i=len(words), w=w.word.strip(), s=round(w.start + off, 3), e=round(w.end + off, 3),
                              p=round(w.probability, 3), seg=si))
    os.makedirs(PRIV, exist_ok=True)
    tag = '' if clip is None else f'_{int(a.t0 or 0)}-{int(a.t1 or 0)}'
    for name, data in ((f'words{tag}.json', words), (f'segments{tag}.json', segments)):
        with open(os.path.join(PRIV, name), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=0)
    span = f'{words[0]["s"]:.2f}-{words[-1]["e"]:.2f} s' if words else 'no words'
    print(f'{os.path.basename(src)}: {len(words)} words in {len(segments)} segments, {span}; language {info.language} '
          f'({info.language_probability:.2f}); {device}, {time.time() - t:.0f} s')
    print(f'  -> song/private/words{tag}.json, segments{tag}.json (PRIVATE: never quote them anywhere)')


if __name__ == '__main__':
    main()
