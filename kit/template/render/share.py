#!/usr/bin/env python
"""share.py -- the delivery cuts, encoded from the master out/<name>.mp4 (settings in film.json: share, discord,
posterT):

    python render/share.py            both cuts
    python render/share.py share      out/<name>_share.mp4    1080p two-pass, sized to share.targetMiB
    python render/share.py discord    out/<name>_discord.mp4  720p two-pass, sized to discord.targetMiB, frame 0 = POSTER

Any python works (stdlib only); ffmpeg and ffprobe must be on PATH.

The video bitrate is worked out from the film's length: (target size / duration) - audio, minus 3% for x264's two-pass
overshoot and the mp4 overhead. A `vb` (e.g. "1400k") in a cut's block overrides it. hqdn3d runs BEFORE the scale, so
the bits go to the picture, not to grain or static (a grainy film needs a stronger "denoise", e.g. "3:3:6:6").
Defaults: share = 1080p for anything with a ~50 MB limit; discord = 720p under Discord's free 10 MB limit.

POSTER: Discord (and many chat apps) thumbnail a video from its FIRST decoded frame, with no seek and no black-skip,
so a film that opens on black shows as a black box. If film.json posterT > 0, frame 0 of the discord cut is the frame
at posterT (the title card): one frame, so frame count, duration and sync are unchanged. The master and the share cut
stay pure.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILM = json.load(open(os.path.join(ROOT, 'film.json'), encoding='utf-8'))
DEFAULTS = {'share': {'targetMiB': 45, 'maxMiB': 49, 'audio': '160k', 'scale': '1920:1080'},
            'discord': {'targetMiB': 9.0, 'maxMiB': 9.5, 'audio': '96k', 'scale': '1280:720'}}


def duration(path):
    out = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path])
    return float(out.decode().strip())


def vb_for(target_mib, dur, audio):
    a = float(str(audio).rstrip('k'))
    return f'{max(200, min(8000, int(((target_mib * 8 * 1048.576) / dur - a) * 0.97)))}k'


def encode(which, src, dur):
    cfg = dict(DEFAULTS[which], **(FILM.get(which) or {}))
    name = FILM['name']
    out = os.path.join(ROOT, 'out', f'{name}_{which}.mp4')
    tmp = out[:-4] + '.tmp.mp4'
    log = os.path.join(ROOT, 'out', f'pass_{name}_{which}')
    vb = cfg.get('vb') or vb_for(float(cfg['targetMiB']), dur, cfg['audio'])
    chain = f"hqdn3d={cfg.get('denoise', '1:1:3:3')},scale={cfg['scale']}:flags=lanczos"
    poster = float(FILM.get('posterT') or 0) if which == 'discord' else 0
    inputs = ['-i', src]
    graph = f'[0:v]{chain}[v]'
    if poster > 0:
        inputs += ['-ss', str(poster), '-i', src]
        graph = (f'[0:v]{chain}[m];[1:v]trim=end_frame=1,setpts=PTS-STARTPTS,{chain}[p];'
                 f"[m][p]overlay=enable='eq(n,0)'[v]")
    print(f'{os.path.basename(out)}: {cfg["scale"]}, video {vb} + audio {cfg["audio"]} for {dur:.1f} s '
          f'(target {cfg["targetMiB"]} MiB)' + (f', poster from {poster} s' if poster > 0 else ''), flush=True)
    base = ['ffmpeg', '-v', 'error', '-y'] + inputs + ['-filter_complex', graph, '-map', '[v]', '-c:v', 'libx264',
                                                       '-preset', 'slow', '-b:v', vb, '-passlogfile', log]
    subprocess.run(base + ['-pass', '1', '-an', '-f', 'mp4', os.devnull], check=True)
    subprocess.run(base + ['-pass', '2', '-map', '0:a', '-c:a', 'aac', '-b:a', cfg['audio'], '-movflags', '+faststart',
                           tmp], check=True)
    os.replace(tmp, out)
    for f in os.listdir(os.path.join(ROOT, 'out')):
        if f.startswith(os.path.basename(log)):
            try:
                os.remove(os.path.join(ROOT, 'out', f))
            except OSError:
                pass
    size = os.path.getsize(out) / 2 ** 20
    limit = float(cfg.get('maxMiB') or float(cfg['targetMiB']) * 1.05)
    print(f'  {out}  {size:.2f} MiB' + (f'  OVER {limit} MiB: set a lower "vb" in film.json {which}' if size > limit else ''))
    return size <= limit


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    src = os.path.join(ROOT, 'out', f"{FILM['name']}.mp4")
    if not os.path.isfile(src):
        sys.exit(f'no master at {src} (run node render/render.mjs first)')
    dur = duration(src)
    ok = True
    for w in ('share', 'discord'):
        if which in ('all', w):
            ok = encode(w, src, dur) and ok
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
