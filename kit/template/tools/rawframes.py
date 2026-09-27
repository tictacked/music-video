#!/usr/bin/env python
"""rawframes.py -- make every downloaded clip usable at once: frames the engine can draw, before (or without) the
GPU upscale.

    python tools/rawframes.py        # assets/clips_in/<name>.mp4 -> assets/clips/<name>/00000.jpg ... (24 fps, 1920 wide)

    from rawframes import make_frames                              # in another tool: one clip, returns its frame count
    n = make_frames('hero_turn', 'assets/clips_in/hero_turn.mp4')

Clips come from any image-to-video model, online or local, at whatever frame rate it makes (16, 24, 25, 30 fps...).
Every clip is resampled to the film's 24 fps (the engine shows clip frame N at N/24 s into the clip) and scaled with
Lanczos to 1920 wide on the CPU: the SAME frame count and size tools/upscale.py writes, so a later upscale overwrites
these frames in place (same names) and the painters' code never changes. The folder is marked with a `.raw` file,
written only AFTER ffmpeg has finished (a folder without it may be half-written), then assets/clips/clips.js is
rebuilt. The batch skips clips that already have frames, and re-rolls (<name>_r2.mp4) until one is picked: rename the
keeper to <name>.mp4."""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE).replace(os.sep, '/')
SRC = f'{ROOT}/assets/clips_in'
OUT = f'{ROOT}/assets/clips'
FPS = 24


def _clear(d):
    for x in os.listdir(d):
        if x.endswith('.jpg') or x == '.raw':
            os.remove(os.path.join(d, x))


def make_frames(name, src_path):
    """src_path (any video) -> assets/clips/<name>/00000.jpg ... at 24 fps, 1920 wide, plus the .raw marker.
    Returns the frame count, or 0 if ffmpeg failed (its error is printed and no partial frames are left behind, so a
    later run tries again). Frames already in the folder are replaced. clips.js is NOT rebuilt here: run
    tools/clipsjs.py once after a batch."""
    d = f'{OUT}/{name}'
    os.makedirs(d, exist_ok=True)
    _clear(d)
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src_path, '-vf', f'fps={FPS},scale=1920:-2:flags=lanczos',
                        '-q:v', '2', '-start_number', '0', f'{d}/%05d.jpg'], capture_output=True, text=True)
    if r.returncode:
        print('FAILED', name, r.stderr[-300:])
        _clear(d)
        try:
            os.rmdir(d)                          # only if nothing else is in it
        except OSError:
            pass
        return 0
    with open(f'{d}/.raw', 'w') as f:
        f.write('lanczos placeholder frames; tools/upscale.py replaces them in place\n')
    return len([x for x in os.listdir(d) if x.endswith('.jpg')])


def main():
    made = 0
    for f in sorted(os.listdir(SRC)) if os.path.isdir(SRC) else []:
        name = f[:-4]
        if not f.endswith('.mp4') or re.search(r'_r[0-9]+$', name):     # re-rolls (<name>_r2.mp4) wait for a verdict
            continue
        d = f'{OUT}/{name}'
        if os.path.isdir(d) and any(x.endswith('.jpg') for x in os.listdir(d)):
            continue
        n = make_frames(name, f'{SRC}/{f}')
        if n:
            print(f'{name}: {n} raw frames', flush=True)
            made += 1
    subprocess.run([sys.executable, f'{HERE}/clipsjs.py'])
    print(made, 'clips made usable')


if __name__ == '__main__':
    main()
