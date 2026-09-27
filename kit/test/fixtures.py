#!/usr/bin/env python
"""fixtures.py -- made-up test material for smoke.py (run with the kit's python: numpy, PIL, soundfile).

    <PY> fixtures.py song <film>       a 24 s song at 120 BPM: intro, verse, a 2 s STOP at 12-14 s, a drop, an end
                                       -> song/audio.wav + song/sections.json (the map smoke.py checks against)
    <PY> fixtures.py pictures <film>   assets/inbox/nai_hero.png (a transparent figure carrying NovelAI-style
                                       metadata whose prompt matches the hero_full job), assets/inbox/stray.png (a
                                       prompt that matches nothing), assets/gen/hero_mint/1.png (a figure on mint:
                                       the rembg path), assets/gen/pl_room/1.png (a plate)
    <PY> fixtures.py st <folder>       a made-up SillyTavern folder: a chat, a card with a lorebook, a world, a persona
Everything here is invented: the song is synthesised, the characters (Aria, Wren) exist only in this file.
"""
import base64
import json
import math
import os
import sys

import numpy as np

SR = 44100
BPM = 120.0
BEAT = 60 / BPM


# ------------------------------------------------------------------ the song
def env(n, decay):
    return np.exp(-np.arange(n) / (decay * SR))


def kick():
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    f = 45 + 75 * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.07)


def snare(rng):
    n = int(0.14 * SR)
    noise = rng.standard_normal(n)
    noise = np.diff(noise, prepend=0)                     # a crude high-pass: brighter
    tone = np.sin(2 * np.pi * 185 * np.arange(n) / SR)
    return (0.55 * noise / 3 + 0.45 * tone) * env(n, 0.045)


def hat(rng):
    n = int(0.035 * SR)
    x = np.diff(np.diff(rng.standard_normal(n), prepend=0), prepend=0)
    return x / 6 * env(n, 0.012)


def tone(freq, dur, kind='sine', amp=1.0, vib=0.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    ph = 2 * np.pi * freq * t + (vib * np.sin(2 * np.pi * 5.5 * t) if vib else 0)
    if kind == 'saw':
        x = 2 * ((freq * t) % 1.0) - 1
    else:
        x = np.sin(ph)
    a = np.minimum(1, t / 0.01) * np.minimum(1, (dur - t) / 0.05)
    return amp * x * np.clip(a, 0, 1)


def add(buf, x, at):
    i = int(round(at * SR))
    j = min(len(buf), i + len(x))
    if i < len(buf):
        buf[i:j] += x[:j - i]


def song(film):
    rng = np.random.default_rng(7)
    dur = 24.0
    L = np.zeros(int(dur * SR))
    K, S, Hh = kick(), snare(rng), hat(rng)
    roots = [55.0, 43.65, 65.41, 49.0]                   # A1 F1 C2 G1
    for b in range(int(dur / BEAT)):
        t = b * BEAT
        bar = b // 4
        stop = 12.0 <= t < 14.0
        if stop or t >= 23.5:
            continue
        add(L, Hh * 0.5, t)
        add(L, Hh * 0.35, t + BEAT / 2)
        if bar >= 2:                                      # verse on: kick 1 & 3, snare 2 & 4, bass
            add(L, K * (1.0 if bar >= 7 else 0.8), t) if b % 2 == 0 else add(L, S * 0.7, t)
            add(L, tone(roots[bar % 4], BEAT * 0.9, 'saw', 0.18), t)
        if bar >= 7:                                      # the drop: a pad and a sung-ish line
            for f in (220.0, 277.18, 329.63):
                add(L, tone(f * (roots[bar % 4] / 55.0), BEAT, 'sine', 0.05), t)
            if b % 2 == 0:
                add(L, tone([440, 494, 523, 587][(b // 2) % 4], BEAT * 1.6, 'sine', 0.12, vib=0.35), t)
    L /= max(1e-9, np.abs(L).max()) / 0.85
    st = np.stack([L, np.roll(L, 7)], 1).astype(np.float32)
    import soundfile as sf
    os.makedirs(os.path.join(film, 'song'), exist_ok=True)
    sf.write(os.path.join(film, 'song', 'audio.wav'), st, SR, subtype='PCM_16')
    sections = {'sections': [
        {'id': 'intro', 'bars': '0-1', 't0': 0.0, 't1': 4.0, 'story': 'hats alone'},
        {'id': 'verse', 'bars': '2-5', 't0': 4.0, 't1': 12.0, 'story': 'the beat comes in'},
        {'id': 'stop', 'bars': '6', 't0': 12.0, 't1': 14.0, 'story': 'silence'},
        {'id': 'drop', 'bars': '7-11', 't0': 14.0, 't1': 24.0, 'story': 'everything'}],
        'stops': [[12.0, 14.0]]}
    with open(os.path.join(film, 'song', 'sections.json'), 'w', encoding='utf-8') as f:
        json.dump(sections, f, indent=1)
    print(f'song: {dur} s at {BPM} BPM (a stop at 12-14 s) -> song/audio.wav + song/sections.json')


# ------------------------------------------------------------------ pictures
def figure(w=832, h=1216, ground=None):
    """a crude standing figure (hair, face, coat, legs) on a flat ground, or on transparency when ground is None"""
    from PIL import Image, ImageDraw
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0) if ground is None else ground + (255,))
    d = ImageDraw.Draw(im)
    cx = w // 2
    d.ellipse([cx - 95, 150, cx + 95, 360], fill=(40, 32, 44, 255))                 # hair
    d.ellipse([cx - 70, 190, cx + 70, 350], fill=(246, 214, 190, 255))             # face
    d.ellipse([cx - 40, 250, cx - 22, 272], fill=(60, 90, 160, 255))               # eyes
    d.ellipse([cx + 22, 250, cx + 40, 272], fill=(60, 90, 160, 255))
    d.rounded_rectangle([cx - 150, 360, cx + 150, 800], 60, fill=(120, 40, 60, 255))    # coat
    d.rectangle([cx - 110, 790, cx - 35, 1100], fill=(35, 35, 45, 255))           # legs
    d.rectangle([cx + 35, 790, cx + 110, 1100], fill=(35, 35, 45, 255))
    d.rounded_rectangle([cx - 125, 1080, cx - 25, 1125], 12, fill=(20, 20, 24, 255))   # shoes
    d.rounded_rectangle([cx + 25, 1080, cx + 125, 1125], 12, fill=(20, 20, 24, 255))
    d.rounded_rectangle([cx - 210, 380, cx - 150, 760], 30, fill=(120, 40, 60, 255))    # arms
    d.rounded_rectangle([cx + 150, 380, cx + 210, 760], 30, fill=(120, 40, 60, 255))
    return im


def nai_meta(prompt, seed, uc='lowres, bad anatomy'):
    from PIL import PngImagePlugin
    comment = {'prompt': prompt, 'steps': 28, 'height': 1216, 'width': 832, 'scale': 5.0, 'seed': seed,
               'sampler': 'k_euler_ancestral', 'n_samples': 1, 'uc': uc, 'noise_schedule': 'karras',
               'v4_prompt': {'caption': {'base_caption': prompt, 'char_captions': []}, 'use_coords': False, 'use_order': True},
               'v4_negative_prompt': {'caption': {'base_caption': uc, 'char_captions': []}, 'legacy_uc': False}}
    info = PngImagePlugin.PngInfo()
    info.add_text('Title', 'NovelAI generated image')
    info.add_text('Description', prompt)
    info.add_text('Software', 'NovelAI')
    info.add_text('Source', 'NovelAI Diffusion V5')
    info.add_text('Comment', json.dumps(comment))
    return info


def pictures(film):
    from PIL import Image
    jobs = json.load(open(os.path.join(film, 'tools', 'jobs', 'cast.json'), encoding='utf-8'))
    hero = next(j for j in jobs if j['job'] == 'hero_full')
    inbox = os.path.join(film, 'assets', 'inbox')
    os.makedirs(inbox, exist_ok=True)
    # a NovelAI V5 picture: the job's prompt + NovelAI's own appended quality words, on a transparent background
    p = hero['prompt'] + ', very aesthetic, masterpiece, no text'
    figure().save(os.path.join(inbox, 'nai_hero s-1234567890.png'), pnginfo=nai_meta(p, 1234567890))
    figure(ground=(240, 150, 190)).convert('RGB').save(os.path.join(inbox, 'stray.png'),
                                                      pnginfo=nai_meta('a bowl of fruit on a table, still life', 42))
    mint = os.path.join(film, 'assets', 'gen', 'hero_mint')
    os.makedirs(mint, exist_ok=True)
    figure(ground=(127, 224, 192)).convert('RGB').save(os.path.join(mint, '1.png'))
    plate = os.path.join(film, 'assets', 'gen', 'pl_room')
    os.makedirs(plate, exist_ok=True)
    y = np.linspace(0, 1, 768)[:, None, None]
    x = np.linspace(0, 1, 1344)[None, :, None]
    rgb = (np.array([30, 24, 60]) * (1 - y) + np.array([230, 140, 90]) * y) * (0.8 + 0.2 * np.cos(x * 3.1))
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).save(os.path.join(plate, '1.png'))
    print('pictures: inbox/nai_hero s-1234567890.png, inbox/stray.png, gen/hero_mint/1.png, gen/pl_room/1.png')


# ------------------------------------------------------------------ a SillyTavern folder
def st(folder):
    from PIL import Image, PngImagePlugin
    user = os.path.join(folder, 'SillyTavern', 'data', 'default-user')
    for d in ('chats/Aria', 'characters', 'worlds'):
        os.makedirs(os.path.join(user, d), exist_ok=True)
    lines = [{'user_name': 'Wren', 'character_name': 'Aria', 'create_date': '2020-01-01@12h00m00s', 'chat_metadata': {}}]
    msgs = [('Aria', False, 'The lamp at the top of the lighthouse has been dark for a week.'),
            ('Wren', True, '*climbs the last stair, out of breath* Then we light it tonight.'),
            ('Aria', False, 'You say that like it is easy. *she hands over the brass key*'),
            ('Wren', True, 'Nothing about you is easy. That is why I keep coming back.'),
            ('Aria', False, '*the wick catches; the beam swings out over the harbor*'),
            ('Wren', True, 'There. Now the ships can find us.')]
    for i, (name, is_user, mes) in enumerate(msgs):
        lines.append({'name': name, 'is_user': is_user, 'is_system': False, 'send_date': f'2020-01-01 12:{i:02d}',
                      'mes': mes, 'swipes': [mes, 'an unused swipe'], 'swipe_id': 0})
    with open(os.path.join(user, 'chats', 'Aria', 'Aria - 2020-01-01@12h00m00s.jsonl'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(json.dumps(x) for x in lines) + '\n')
    card = {'spec': 'chara_card_v2', 'spec_version': '2.0', 'data': {
        'name': 'Aria', 'creator': 'test-author', 'description': 'The keeper of a dark lighthouse.',
        'personality': 'guarded, dry, kind underneath', 'scenario': 'A storm is coming.',
        'first_mes': 'The lamp at the top of the lighthouse has been dark for a week.', 'mes_example': '',
        'creator_notes': 'A test card.', 'alternate_greetings': ['Another night, another storm.'],
        'character_book': {'entries': [{'keys': ['lighthouse'], 'content': 'The lighthouse stands on the north cliff.',
                                        'comment': 'Lighthouse', 'enabled': True}]}}}
    info = PngImagePlugin.PngInfo()
    info.add_text('chara', base64.b64encode(json.dumps(card).encode('utf-8')).decode('ascii'))
    Image.new('RGB', (400, 600), (40, 60, 90)).save(os.path.join(user, 'characters', 'Aria.png'), pnginfo=info)
    world = {'entries': {'0': {'key': ['harbor'], 'content': 'The harbor freezes in winter.', 'comment': 'Harbor'}}}
    json.dump(world, open(os.path.join(user, 'worlds', 'Coast.json'), 'w', encoding='utf-8'))
    settings = {'power_user': {'personas': {'wren.png': 'Wren'},
                               'persona_descriptions': {'wren.png': {'description': "Wren is the keeper's apprentice."}}}}
    json.dump(settings, open(os.path.join(user, 'settings.json'), 'w', encoding='utf-8'))
    print(f'st: {os.path.join(folder, "SillyTavern")} (1 chat of {len(msgs)} messages, a card, a world, a persona)')


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] not in ('song', 'pictures', 'st'):
        sys.exit(__doc__)
    {'song': song, 'pictures': pictures, 'st': st}[sys.argv[1]](sys.argv[2])
