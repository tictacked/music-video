#!/usr/bin/env python
"""assets.py -- the film's picture list, in one place. Writes the job files every picture tool reads.

    python tools/assets.py                     # -> tools/jobs/cast.json, plates.json (+ ff.json: clip first frames)
    then EITHER  python tools/promptsheet.py   # a page of prompts to generate BY HAND (NovelAI or any web generator,
                                               #   or the user's own art); save the results into assets/inbox/
             OR  python tools/gen.py --jobs tools/jobs/cast.json    # a LOCAL A1111/Forge generates them itself
    then         python tools/intake.py        # assets/inbox/ -> assets/gen/<job>/<n>.png (reads each PNG's prompt)
                 <PY> tools/cutout.py          # figures on flat ground -> cut-outs + assets/manifest.js

ORDER: whatever gates the next stage goes first. Clip first frames (ff_) before the cast when there are clips;
the cast before the plates; the plates painters need first (their reels' openings) before the rest.

A JOB is one picture idea, made several times so there is a choice:
  job      the folder: assets/gen/<job>/<n>.png. Its prefix decides cutting (film.json nocutPrefixes: pl_ plates,
           ff_ first frames, i2i_ tests are used whole; everything else is cut out of its flat ground)
  prompt   the picture, in the generator's language (tags and/or sentences), WITHOUT quality words
  chars    optional: [{"prompt": "...", "center": [x, y]}] one per character, for two-shots and groups. NovelAI has
           these ("Character Prompts": V5 places them freely, V4.5 on a 5x5 grid 0.1..0.9); they cut the bleed of
           hair, eyes and clothes between people. For A1111 they're joined onto the prompt
  neg      what must not appear (added to the base negative)
  w, h     size. NovelAI's free sizes (Opus tier: <= 1024x1024 pixels, <= 28 steps): 832x1216 portrait,
           1216x832 landscape, 1344x768 wide (plates), 1024x1024 square
  n        how many to make (A1111: seeds 1..n unless `seeds` is given)
  ref      optional: the character's reference picture (NovelAI: Precise Reference / Vibe Transfer, on V4.5 until V5
           gets them; without them, consistency rides on the character block in every prompt)
  init, denoise, mask    img2img / inpaint (A1111; NovelAI's UI: Image2Image, Inpaint)
  note     what it's for (the shot, the moment): the prompt sheet shows it

What twelve-plus films taught (the skill's PICTURES.md has the why of each):
  - one CHARACTER BLOCK per person (hair, eyes, outfit, build, props) + a NEGATIVE block (the colours and features that
    must never drift onto them). Put the outfit in EVERY prompt: without it, clothes wander or vanish.
  - figures to cut out stand on a FLAT SATURATED ground (GROUND below: mint; pink or sky if the character wears mint),
    full body, wide shot. Never white, cream, black or red grounds: the mattes fail.
  - two-shots bleed (hair, eyes, clothes swap between people): paint singles and composite, or shot/reverse-shot, or
    use per-character prompts with positions and check every picture.
  - wide canvases grow twins: ANTI_TWIN in the negative.
  - a face that must not look comic: HITCHCOCK in the prompt + NOT_COMIC in the negative.
  - a figure seen from behind: BACK_VIEW + NO_FACE (and check how the pose READS: a back view can suggest something
    else entirely).
  - pictures with pillarbox / letterbox bars happen: BARS in the negative, tools/unbar.py moves barred ones out.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- recipe words (edit for this film)
# Figures to cut out need a ground the cutter can remove. NovelAI V5 paints a REAL transparent background when asked
# ("transparent background" / "has alpha"): cutout.py then keeps the picture's own alpha. Every other generator: a
# flat saturated colour (mint; pink or sky if a character wears mint), which cutout.py keys out.
ALPHA = 'transparent background, has alpha'
MINT = 'simple background, plain flat mint green background'
GROUND = MINT            # NovelAI V5: GROUND = ALPHA
ANTI_TWIN = 'twins, duplicate, clone, multiple views'                   # safe in every negative
SOLO_NEG = '2girls, 2boys, multiple girls, multiple boys'              # ONLY for one-person pictures
HITCHCOCK = 'psychological thriller, dramatic composition, harsh light and deep shadow, high angle'
NOT_COMIC = 'comedic, cartoonish, chibi, exaggerated expression, O_O, round eyes, tiny pupils, eye level, straight on'
BACK_VIEW = 'from behind, back view, rear view, facing away'
NO_FACE = 'face, eyes, looking at viewer, looking back'
BARS = 'pillarboxing, letterboxing, black bars, black borders, frame, border'
FULL = 'full body, wide shot, feet visible'

FIG = (832, 1216)       # a figure to cut out (portrait)
LAND = (1216, 832)      # landscape
WIDE = (1344, 768)      # a plate: close to 16:9, crop to 1344x756 and scale to 1920x1080
SQUARE = (1024, 1024)

# ---- the cast: one block per person. Describe them from the user's OWN pictures of them (hair, eyes, outfit,
# build), never from the archetype the card's words evoke. Ask the user for each character's non-negotiables.
HERO = '1girl, solo, <hair>, <eyes>, <outfit>'
HERO_NEG = 'multiple views, character sheet, <colours that must never appear on them>'
HERO_REF = ''            # e.g. 'source/hero_ref.png': the user's canonical picture of them (NovelAI Character Reference)


def job(name, prompt, neg='', size=FIG, n=4, note='', **kw):
    j = dict(job=name, prompt=prompt, neg=neg, w=size[0], h=size[1], n=n, note=note)
    j.update({k: v for k, v in kw.items() if v not in (None, '')})
    return j


def figure(name, pose, neg='', n=4, note='', ref=HERO_REF, who=HERO, who_neg=HERO_NEG):
    """a figure to CUT OUT: the character block + the pose + full body on the cut-out ground"""
    negs = ', '.join(x for x in (who_neg, SOLO_NEG, ANTI_TWIN, neg) if x)
    return job(name, f'{who}, {pose}, {FULL}, {GROUND}', negs, FIG, n, note, ref=ref)


def plate(name, place, neg='people, person, 1girl, 1boy', n=3, note=''):
    """a PLACE with nobody in it, used whole (pl_ prefix: never cut)"""
    assert name.startswith('pl_'), 'plates start with pl_ so the cutter leaves them whole'
    return job(name, place, f'{neg}, {BARS}', WIDE, n, note)


def two_shot(name, scene, a, b, n=4, note='', neg=''):
    """two people in one frame: per-character prompts with positions (NovelAI); A1111 joins them onto the prompt.
    Put each character's colours on the right person, and negative the bleed you fear ('kiss, kissing' up front)."""
    return job(name, scene, ', '.join(x for x in (ANTI_TWIN, neg) if x), LAND, n, note,
               chars=[{'prompt': a, 'center': [0.3, 0.5]}, {'prompt': b, 'center': [0.7, 0.5]}])


# ---- the lists (examples: write this film's own, in REEL order)
CAST = [
    figure('hero_full', 'standing, arms at sides, neutral expression', note='the lead, the default pose'),
]
PLATES = [
    plate('pl_room', 'an empty bedroom at night, soft window light, no humans', note='reel 1 opening'),
]
FF = []                  # clip first frames: job('ff_<clip>', ..., size=WIDE) -- used whole


def main():
    d = os.path.join(ROOT, 'tools', 'jobs')
    os.makedirs(d, exist_ok=True)
    total = 0
    for fname, jobs in (('cast.json', CAST), ('plates.json', PLATES), ('ff.json', FF)):
        if not jobs:
            continue
        with open(os.path.join(d, fname), 'w', encoding='utf-8', newline='\n') as f:
            json.dump(jobs, f, indent=1, ensure_ascii=False)
        total += sum(j.get('n', 1) for j in jobs)
        print(f'tools/jobs/{fname}: {len(jobs)} jobs')
    print(f'{total} pictures wanted. Next: python tools/promptsheet.py  (by hand)  or  python tools/gen.py --jobs ...')


if __name__ == '__main__':
    main()
