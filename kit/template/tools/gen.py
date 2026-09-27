#!/usr/bin/env python
"""gen.py -- generate a job list's pictures with a LOCAL Stable Diffusion WebUI API (AUTOMATIC1111, Forge, reForge,
SD.Next: anything that serves /sdapi/v1/txt2img). For NovelAI or any web generator, use tools/promptsheet.py (you
generate by hand) and tools/intake.py instead.

    python tools/gen.py --jobs tools/jobs/cast.json [--only hero_full,pl_room] [--force]
    python tools/gen.py --sheet assets/gen/<job>          # just (re)make a job's contact sheet
    python tools/gen.py --check                           # is the WebUI answering, with which model and LoRAs?

The WebUI must be running with its API on (A1111/Forge: launch with --api). Its address comes from the kit's
machine.json "a1111" (default http://127.0.0.1:7860) or the MV_A1111 environment variable.

A GUEST: it never changes the WebUI's settings. It sends plain txt2img/img2img requests with the film's recipe
(film.json "pictures": model, sampler, scheduler, steps, cfg, quality, neg, loras). If "model" is set and a
different checkpoint is loaded, it stops and says so (load it in the WebUI yourself, or pass --switch to let this
tool change the loaded checkpoint once). LoRAs ride in the prompt per request, so nothing global changes.

Pictures land in assets/gen/<job>/<seed>.png, each with a .json sidecar (the exact prompt, seed and settings), plus a
labelled contact sheet assets/gen/<job>/_sheet.jpg. Existing pictures are skipped (--force redoes them).
Job keys: see tools/assets.py (job, prompt, chars, neg, w, h, n or seeds, init, denoise, mask, loras, steps, cfg).
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from film import FILM, MACHINE, ROOT  # noqa: E402

URL = (os.environ.get('MV_A1111') or MACHINE.get('a1111') or 'http://127.0.0.1:7860').rstrip('/')
CFG = FILM.get('pictures') or {}
QUALITY = CFG.get('quality', 'masterpiece, best quality, highres')
NEG = CFG.get('neg', 'worst quality, low quality, lowres, jpeg artifacts, watermark, signature, artist name, logo, text, '
                     'pillarboxing, letterboxing, black bars, black borders, frame')
RECIPE = dict(sampler_name=CFG.get('sampler', 'Euler a'), scheduler=CFG.get('scheduler', 'Automatic'),
              steps=CFG.get('steps', 28), cfg=CFG.get('cfg', 5.0))
LORAS = [tuple(x) for x in (CFG.get('loras') or [])]          # [[name, weight, trigger words], ...] for every picture


def api(path, payload=None, timeout=1800):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(URL + path, data=data, headers={'Content-Type': 'application/json'},
                                 method='POST' if data is not None else 'GET')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def check(loras, switch=False):
    try:
        o = api('/sdapi/v1/options', timeout=10)
    except Exception as e:
        sys.exit(f'no WebUI API at {URL} ({e}).\n  Start A1111/Forge with --api, or set "a1111" in the kit\'s '
                 f'machine.json. For NovelAI or a web generator: python tools/promptsheet.py')
    loaded = o.get('sd_model_checkpoint') or '?'
    want = CFG.get('model')
    if want and want not in loaded:
        if not switch:
            sys.exit(f'the WebUI has {loaded!r} loaded; film.json pictures.model wants {want!r}.\n'
                     f'  Load it in the WebUI, or rerun with --switch to let gen.py change the checkpoint.')
        names = [m['title'] for m in api('/sdapi/v1/sd-models', timeout=60)]
        match = [n for n in names if want in n]
        if not match:
            sys.exit(f'no checkpoint matching {want!r}. The WebUI has: {names}')
        print(f'  switching the WebUI to {match[0]} (asked with --switch)', flush=True)
        api('/sdapi/v1/options', {'sd_model_checkpoint': match[0]}, timeout=900)
    if loras:
        have = {x['name'] for x in api('/sdapi/v1/loras', timeout=60)}
        missing = sorted({n for n, _, _ in loras} - have)
        if missing:
            sys.exit(f'LoRAs the WebUI does not have: {missing}')
    return loaded


def full_prompt(j, loras):
    tags = ''.join(f'<lora:{n}:{w}> ' for n, w, _ in loras)
    trig = ''.join(f'{t}, ' for _, _, t in loras if t)
    q = (QUALITY + ', ') if j.get('quality', True) and QUALITY else ''
    body = j['prompt']
    for c in j.get('chars') or []:              # per-character prompts: A1111 has no regions, so they join the prompt
        body += ', ' + c['prompt']
    return f'{tags}{trig}{q}{body}'


def run_job(j, force=False):
    job = j['job']
    out = os.path.join(ROOT, 'assets', 'gen', job)
    os.makedirs(out, exist_ok=True)
    loras = LORAS + [tuple(x) for x in (j.get('loras') or [])]
    w, h = int(j.get('w', 832)), int(j.get('h', 1216))
    neg = NEG + (', ' + j['neg'] if j.get('neg') else '')
    prompt = full_prompt(j, loras)
    seeds = j.get('seeds') or list(range(1, int(j.get('n', 4)) + 1))
    made = 0
    for seed in seeds:
        fn = os.path.join(out, f"{j.get('tag', '')}{seed}.png")
        if os.path.exists(fn) and not (force or j.get('force')):
            continue
        payload = dict(prompt=prompt, negative_prompt=neg, seed=int(seed), steps=int(j.get('steps', RECIPE['steps'])),
                       cfg_scale=float(j.get('cfg', RECIPE['cfg'])), width=w, height=h,
                       sampler_name=RECIPE['sampler_name'], scheduler=RECIPE['scheduler'], n_iter=1, batch_size=1,
                       save_images=False, send_images=True)
        if CFG.get('shift') is not None:        # Forge: flow-matching models' shift rides in distilled_cfg_scale
            payload['distilled_cfg_scale'] = float(CFG['shift'])
        if j.get('init'):
            src = j['init'] if os.path.isabs(j['init']) else os.path.join(ROOT, j['init'])
            with open(src, 'rb') as f:
                payload['init_images'] = [base64.b64encode(f.read()).decode()]
            payload['denoising_strength'] = float(j.get('denoise', 0.45))
            if j.get('mask'):   # inpaint: white = repaint, black = keep (tools/mask.py draws one)
                msrc = j['mask'] if os.path.isabs(j['mask']) else os.path.join(ROOT, j['mask'])
                with open(msrc, 'rb') as f:
                    payload['mask'] = base64.b64encode(f.read()).decode()
                payload.update(mask_blur=int(j.get('mask_blur', 8)), inpainting_fill=int(j.get('inpainting_fill', 1)),
                               inpaint_full_res=bool(j.get('only_masked', False)),   # True = crop the masked area,
                               inpaint_full_res_padding=int(j.get('padding', 64)),   # paint it at w x h, paste back
                               inpainting_mask_invert=0, resize_mode=0)
        r = None
        t0 = time.time()
        for attempt in range(4):
            try:
                r = api('/sdapi/v1/img2img' if j.get('init') else '/sdapi/v1/txt2img', payload)
                break
            except Exception as e:      # the WebUI restarting or busy: wait, then redo this seed
                print(f'  request failed ({str(e)[:120]}); retrying in 20 s', flush=True)
                time.sleep(20)
        if r is None:
            sys.exit(f'{job}/{os.path.basename(fn)}: 4 attempts failed')
        with open(fn, 'wb') as f:
            f.write(base64.b64decode(r['images'][0]))
        side = {k: v for k, v in payload.items() if k not in ('init_images', 'mask')}
        side.update(job=job, init=j.get('init'), mask=j.get('mask'), loras=loras, generator='a1111',
                    secs=round(time.time() - t0, 1))
        with open(fn[:-4] + '.json', 'w', encoding='utf-8') as f:
            json.dump(side, f, ensure_ascii=False, indent=1)
        made += 1
        print(f"  {job}/{os.path.basename(fn)}  {time.time() - t0:.1f}s", flush=True)
    sheet(out)
    return made


def sheet(folder, cols=4, cell=420):
    """a labelled contact sheet of a job's pictures: <folder>/_sheet.jpg"""
    from PIL import Image, ImageDraw
    files = sorted(f for f in os.listdir(folder) if f.endswith('.png') and not f.startswith('_'))
    if not files:
        return None
    ims = []
    for f in files:
        im = Image.open(os.path.join(folder, f)).convert('RGB')
        im.thumbnail((cell, cell))
        ims.append((f, im))
    rows = (len(ims) + cols - 1) // cols
    S = Image.new('RGB', (cols * cell, rows * (cell + 22)), (20, 20, 22))
    d = ImageDraw.Draw(S)
    for i, (f, im) in enumerate(ims):
        x, y = (i % cols) * cell, (i // cols) * (cell + 22)
        S.paste(im, (x + (cell - im.width) // 2, y + 22 + (cell - im.height) // 2))
        d.text((x + 6, y + 4), f, fill=(255, 210, 120))
    p = os.path.join(folder, '_sheet.jpg')
    S.save(p, quality=88)
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--jobs', action='append', help='a job list (tools/jobs/*.json); repeatable')
    ap.add_argument('--only', help='comma-separated job names')
    ap.add_argument('--force', action='store_true', help='redo pictures that already exist')
    ap.add_argument('--switch', action='store_true', help='let gen.py change the loaded checkpoint to pictures.model')
    ap.add_argument('--sheet')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.sheet:
        print(sheet(a.sheet))
        return
    if a.check:
        print(f'{URL}: {check(LORAS)} loaded')
        return
    if not a.jobs:
        sys.exit('give --jobs tools/jobs/<list>.json (tools/assets.py writes them)')
    only = set(a.only.split(',')) if a.only else None
    jobs = [j for f in a.jobs for j in json.load(open(f, encoding='utf-8')) if not only or j['job'] in only]
    loaded = check(LORAS + [tuple(x) for j in jobs for x in (j.get('loras') or [])], a.switch)
    print(f'{URL}: {loaded}; {len(jobs)} jobs', flush=True)
    made = sum(run_job(j, a.force) for j in jobs)
    print(f'{made} new pictures. Next: look at each job\'s _sheet.jpg, then <PY> tools/cutout.py')


if __name__ == '__main__':
    main()
