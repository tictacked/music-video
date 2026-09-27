#!/usr/bin/env python
"""intake.py -- file hand-made pictures into the film: assets/inbox/ -> assets/gen/<job>/<n>.png + a .json sidecar.

    python tools/intake.py                          # everything in assets/inbox/ (and its subfolders)
    python tools/intake.py ~/Downloads/a.png b.png  # or name files / folders directly (they are copied, not moved)
    python tools/intake.py --job hero_full x.png    # force the job
    python tools/intake.py --dry-run                # show where each picture would go, change nothing

Which job each picture belongs to, in this order:
  1. --job
  2. the folder it's in: assets/inbox/<job>/...
  3. the prompt stored INSIDE the picture: NovelAI and A1111/Forge PNGs carry it (ComfyUI PNGs carry their
     workflow). Each picture goes to the job (tools/jobs/*.json) whose prompt it contains the most of, if that match
     is clear. Pictures that match nothing clearly stay in the inbox, with the closest guesses printed.
Pictures are numbered 1, 2, 3... per job (the engine's keys: 'cut:<job>/3'); the generator's own seed, prompt and
settings go into the .json sidecar. JPG/WebP become PNG (alpha kept). Originals from the inbox move to
assets/inbox/_filed/<job>/ (nothing is deleted). Afterwards each touched job gets a fresh _sheet.jpg.
Then: <PY> tools/cutout.py (cut-outs + the manifest), and look at the sheets.
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from film import ROOT  # noqa: E402

INBOX = os.path.join(ROOT, 'assets', 'inbox')
GEN = os.path.join(ROOT, 'assets', 'gen')
EXTS = ('.png', '.jpg', '.jpeg', '.webp')


# ------------------------------------------------------------------ what the picture says about itself
def metadata(path):
    """-> dict(generator, prompt, negative, seed, width, height, model, raw) from the picture's own text chunks"""
    from PIL import Image
    im = Image.open(path)
    info = dict(getattr(im, 'text', {}) or {})
    for k, v in (im.info or {}).items():
        if isinstance(v, str) and k not in info:
            info[k] = v
    out = dict(generator='unknown', prompt='', negative='', seed=None, width=im.width, height=im.height, model='',
               raw={})
    if 'Comment' in info and ('NovelAI' in info.get('Software', '') or info.get('Comment', '').lstrip().startswith('{')):
        try:
            c = json.loads(info['Comment'])
        except ValueError:
            c = {}
        cap = ((c.get('v4_prompt') or {}).get('caption') or {})
        chars = [x.get('char_caption', '') for x in (cap.get('char_captions') or [])]
        prompt = c.get('prompt') or cap.get('base_caption') or info.get('Description', '')
        out.update(generator='novelai', prompt=', '.join([prompt] + [x for x in chars if x]),
                   negative=c.get('uc') or ((c.get('v4_negative_prompt') or {}).get('caption') or {}).get('base_caption', ''),
                   seed=c.get('seed'), model=info.get('Source', ''), raw=c)
        return out
    if 'parameters' in info:                     # A1111 / Forge: "prompt\nNegative prompt: ...\nSteps: .., Seed: .."
        p = info['parameters']
        body, sep, _ = p.rpartition('\nSteps:')          # the settings line comes last
        if not sep:
            body = p
        prompt, _, neg = body.partition('\nNegative prompt:')
        seed = re.search(r'Seed:\s*(\d+)', p)
        model = re.search(r'Model:\s*([^,\n]+)', p)
        out.update(generator='a1111', prompt=prompt.strip(), negative=neg.strip(),
                   seed=int(seed.group(1)) if seed else None, model=model.group(1).strip() if model else '',
                   raw={'parameters': p})
        return out
    if 'prompt' in info:                         # ComfyUI: the API workflow; take every text-encoder's text
        try:
            wf = json.loads(info['prompt'])
            texts = [n['inputs']['text'] for n in wf.values()
                     if isinstance(n, dict) and isinstance((n.get('inputs') or {}).get('text'), str)]
            seeds = [n['inputs'].get('seed') or n['inputs'].get('noise_seed') for n in wf.values()
                     if isinstance(n, dict) and isinstance(n.get('inputs'), dict)
                     and (n['inputs'].get('seed') is not None or n['inputs'].get('noise_seed') is not None)]
            out.update(generator='comfyui', prompt=', '.join(texts), seed=seeds[0] if seeds else None,
                       raw={'prompt': wf})
        except (ValueError, KeyError, AttributeError):
            pass
        return out
    if info.get('Description'):
        out.update(prompt=info['Description'])
    return out


def seed_from_name(name):
    m = re.search(r's-(\d{3,})', name) or re.match(r'\d{5}-(\d+)', name)
    return int(m.group(1)) if m else None


# ------------------------------------------------------------------ matching a prompt to a job
def tags(s):
    s = (s or '').lower()
    s = re.sub(r'<lora:[^>]+>', ' ', s)
    s = re.sub(r'-?\d+(\.\d+)?::', ' ', s).replace('::', ' ')         # NovelAI weights: 1.2::tag::
    s = re.sub(r':\s*-?\d+(\.\d+)?\s*\)', ')', s)                      # A1111 weights: (tag:1.2)
    s = re.sub(r'[{}\[\]()]', ' ', s)
    return {t.strip() for t in re.split(r'[,\n|]', s) if t.strip()}


def words(s):
    return {w for w in re.findall(r"[a-z0-9']+", (s or '').lower()) if len(w) > 2}


def score(job_prompt, pic_prompt):
    jt, pt = tags(job_prompt), tags(pic_prompt)
    jw, pw = words(job_prompt), words(pic_prompt)
    if not jt or not pt:
        return 0.0
    tag_c = len(jt & pt) / len(jt)
    word_c = len(jw & pw) / max(1, len(jw))
    return 0.6 * tag_c + 0.4 * word_c


def load_jobs():
    jobs = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'tools', 'jobs', '*.json'))):
        for j in json.load(open(f, encoding='utf-8')):
            text = j.get('prompt', '') + ''.join(', ' + c.get('prompt', '') for c in (j.get('chars') or []))
            jobs[j['job']] = dict(prompt=text, want=len(j.get('seeds') or []) or int(j.get('n', 4)))
    return jobs


def jaccard(a, b):
    ta, tb = tags(a), tags(b)
    return len(ta & tb) / max(1, len(ta | tb))


def choose(meta, jobs):
    ranked = sorted(((score(v['prompt'], meta['prompt']), k) for k, v in jobs.items()), reverse=True)
    if not ranked or not meta['prompt']:
        return None, ranked[:3]
    best = ranked[0]
    second = ranked[1][0] if len(ranked) > 1 else 0.0
    if best[0] >= 0.5 and best[0] - second >= 0.1:
        return best[1], ranked[:3]
    if best[0] >= 0.5 and len(ranked) > 1:
        # near-twin jobs (the same character "standing" vs "looking away", mint vs transparent): containment can't
        # tell them apart, so compare the WHOLE prompts both ways; the one the picture's prompt matches best wins
        top = [k for s, k in ranked if best[0] - s < 0.1]
        sims = sorted(((jaccard(jobs[k]['prompt'], meta['prompt']), k) for k in top), reverse=True)
        if len(sims) == 1 or sims[0][0] - sims[1][0] >= 0.05:
            return sims[0][1], ranked[:3]
    return None, ranked[:3]


# ------------------------------------------------------------------ filing
def next_number(folder):
    nums = [int(m.group(1)) for f in os.listdir(folder) for m in [re.match(r'(\d+)\.png$', f)] if m] \
        if os.path.isdir(folder) else []
    return max(nums, default=0) + 1


def same_picture(a, b):
    from PIL import Image, ImageChops
    try:
        ia, ib = Image.open(a).convert('RGBA'), Image.open(b).convert('RGBA')
        return ia.size == ib.size and ImageChops.difference(ia, ib).getbbox() is None
    except OSError:
        return False


def file_one(src, job, meta, how, sc, dry, move):
    from PIL import Image
    folder = os.path.join(GEN, job)
    if os.path.isdir(folder):
        for f in os.listdir(folder):
            if f.endswith('.json') and not f.startswith('_'):
                try:
                    side = json.load(open(os.path.join(folder, f), encoding='utf-8'))
                except ValueError:
                    continue
                if side.get('source') == os.path.basename(src) and os.path.isfile(os.path.join(folder, f[:-5] + '.png')) \
                        and same_picture(src, os.path.join(folder, f[:-5] + '.png')):
                    return None                          # already filed
    n = next_number(folder)
    dst = os.path.join(folder, f'{n}.png')
    if dry:
        return dst
    os.makedirs(folder, exist_ok=True)
    im = Image.open(src)
    im = im.convert('RGBA' if ('A' in im.getbands() or 'transparency' in im.info) else 'RGB')
    im.save(dst)
    side = dict(job=job, n=n, source=os.path.basename(src), generator=meta['generator'], prompt=meta['prompt'],
                negative=meta['negative'], seed=meta['seed'] if meta['seed'] is not None else seed_from_name(src),
                width=meta['width'], height=meta['height'], model=meta['model'], match=dict(how=how, score=round(sc, 3)),
                meta=meta['raw'])
    with open(dst[:-4] + '.json', 'w', encoding='utf-8') as f:
        json.dump(side, f, ensure_ascii=False, indent=1)
    if move:
        keep = os.path.join(INBOX, '_filed', job)
        os.makedirs(keep, exist_ok=True)
        tgt = os.path.join(keep, os.path.basename(src))
        if os.path.exists(tgt):
            base, ext = os.path.splitext(tgt)
            tgt = f'{base}_{n}{ext}'
        shutil.move(src, tgt)
    return dst


def gather(paths):
    """-> [(file, folder job or None, lives in the inbox?)]"""
    out = []
    for p in paths:
        p = os.path.abspath(p)
        in_inbox = os.path.abspath(p).startswith(os.path.abspath(INBOX))
        if os.path.isdir(p):
            for d, dirs, files in os.walk(p):
                dirs[:] = [x for x in dirs if not x.startswith('_')]
                for f in sorted(files):
                    if f.lower().endswith(EXTS):
                        fp = os.path.join(d, f)
                        sub = os.path.relpath(d, INBOX) if in_inbox else '.'
                        first = sub.split(os.sep)[0] if sub != '.' else None
                        out.append((fp, first if first and not first.startswith('_') else None, in_inbox))
        elif p.lower().endswith(EXTS):
            sub = os.path.relpath(os.path.dirname(p), INBOX).split(os.sep)[0] if in_inbox else '.'
            job = sub if in_inbox and sub not in ('.', '') and not sub.startswith('_') else None
            out.append((p, job, in_inbox))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('paths', nargs='*')
    ap.add_argument('--job', help='file every picture under this job')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    os.makedirs(INBOX, exist_ok=True)
    jobs = load_jobs()
    items = gather(a.paths or [INBOX])
    if not items:
        print(f'nothing to file in {a.paths or [INBOX]}')
        return
    touched, left = {}, []
    for src, folder_job, in_inbox in items:
        meta = metadata(src)
        if a.job:
            job, how, sc, guesses = a.job, 'forced', 1.0, []
        elif folder_job:
            job, how, sc, guesses = folder_job, 'folder', 1.0, []
        else:
            job, guesses = choose(meta, jobs)
            how, sc = 'prompt', (guesses[0][0] if guesses else 0.0)
        if not job:
            left.append((src, meta, guesses))
            continue
        dst = file_one(src, job, meta, how, sc, a.dry_run, move=in_inbox)
        if dst is None:
            print(f'  already filed: {os.path.basename(src)}')
            continue
        touched[job] = touched.get(job, 0) + 1
        rel = os.path.relpath(dst, ROOT).replace(os.sep, '/')
        print(f'  {os.path.basename(src)[:60]:60s} -> {rel}  ({how}{"" if how != "prompt" else f" {sc:.2f}"}, '
              f'{meta["generator"]})')
    if not a.dry_run:
        from gen import sheet
        for job in touched:
            sheet(os.path.join(GEN, job))
    print()
    for job, n in touched.items():
        have = len([f for f in os.listdir(os.path.join(GEN, job)) if f.endswith('.png') and not f.startswith('_')]) \
            if os.path.isdir(os.path.join(GEN, job)) else n
        want = jobs.get(job, {}).get('want', '?')
        print(f'{job}: +{n} (now {have} / wanted {want})' + ('' if job in jobs else '   (not in tools/jobs: a new job)'))
    for src, meta, guesses in left:
        g = ', '.join(f'{k} {s:.2f}' for s, k in guesses) or 'no prompt inside the picture'
        print(f'UNMATCHED {os.path.basename(src)}: {g}  -> move it into assets/inbox/<job>/ or rerun with --job')
    if touched and not a.dry_run:
        print('\nNext: look at each assets/gen/<job>/_sheet.jpg, then <PY> tools/cutout.py')


if __name__ == '__main__':
    main()
