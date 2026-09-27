#!/usr/bin/env python
"""promptsheet.py -- a page of every picture job, for generating BY HAND (NovelAI, any web generator, or the user's
own art): notes/prompts.html, with copy buttons, the sizes, per-character prompts and their positions, the reference
picture to use, and how many pictures each job already has.

    python tools/promptsheet.py                      # every tools/jobs/*.json -> notes/prompts.html
    python tools/promptsheet.py tools/jobs/cast.json # just these lists
Open notes/prompts.html in a browser (double-click it, or serve the film: node render/serve.mjs -> /notes/prompts.html).
Save what you make into assets/inbox/ (any file names), then:  python tools/intake.py   (it files each picture under
its job by reading the prompt stored inside the PNG). Rerun this script to refresh the counts.

Why by hand: NovelAI's terms require every generation to be started by a person, so the kit never calls it itself.
It also keeps the user's own tools in play (Character Reference, Vibe Transfer, inpainting, picking favourites).
"""
import glob
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from film import FILM, ROOT  # noqa: E402

COLS = 'ABCDE'


def grid_cell(c):
    """NovelAI V4.5's character position grid: columns A-E (x 0.1..0.9), rows 1-5 (y 0.1..0.9)"""
    x, y = c
    return f'{COLS[min(4, max(0, round((x - 0.1) / 0.2)))]}{min(5, max(1, round((y - 0.1) / 0.2) + 1))}'


def where(c):
    """a position in words (NovelAI V5 places character prompts freely on the canvas)"""
    x, y = c
    h = 'left' if x < 0.4 else 'right' if x > 0.6 else 'centre'
    v = 'top' if y < 0.4 else 'bottom' if y > 0.6 else 'middle'
    return f'{v} {h}'.replace('middle centre', 'centre')


def count(job):
    d = os.path.join(ROOT, 'assets', 'gen', job)
    return len([f for f in os.listdir(d) if f.endswith('.png') and not f.startswith('_')]) if os.path.isdir(d) else 0


def rel(p):
    """a path from notes/ (where the page lives) to a film file"""
    if not p:
        return ''
    ap = p if os.path.isabs(p) else os.path.join(ROOT, p)
    return os.path.relpath(ap, os.path.join(ROOT, 'notes')).replace(os.sep, '/')


def field(label, text, big=False):
    t = html.escape(text or '')
    rows = max(2, min(10, len(text or '') // 90 + 1)) if big else 2
    return (f'<div class="f"><div class="lab">{label}<button onclick="cp(this)">copy</button></div>'
            f'<textarea readonly rows="{rows}">{t}</textarea></div>')


def card(j):
    job = j['job']
    want = len(j.get('seeds') or []) or int(j.get('n', 4))
    have = count(job)
    w, h = int(j.get('w', 832)), int(j.get('h', 1216))
    free = w * h <= 1024 * 1024
    out = [f'<section class="card{" done" if have >= want else ""}" id="{html.escape(job)}">',
           f'<h2><code>{html.escape(job)}</code> <span class="n">{have} / {want}</span></h2>']
    if j.get('note'):
        out.append(f'<p class="note">{html.escape(j["note"])}</p>')
    out.append(f'<p class="meta">size <b>{w} x {h}</b>' + (' <span class="ok">(NovelAI: free size)</span>' if free else
               ' <span class="warn">(over 1 MP: NovelAI charges Anlas)</span>') + '</p>')
    out.append(field('prompt', j.get('prompt', ''), big=True))
    for i, c in enumerate(j.get('chars') or []):
        pos = c.get('center', [0.5, 0.5])
        out.append(field(f'character {i + 1} &middot; place: {where(pos)} (x {pos[0]}, y {pos[1]}; V4.5 grid '
                         f'{grid_cell(pos)})', c.get('prompt', ''), big=True))
    out.append(field('undesired content / negative', j.get('neg', '')))
    extra = []
    if j.get('ref'):
        extra.append(f'<figure><img src="{html.escape(rel(j["ref"]))}" alt=""><figcaption>reference: '
                     f'<code>{html.escape(j["ref"])}</code> (Precise Reference / Vibe Transfer: on NovelAI V4.5 until '
                     f'V5 has them)</figcaption></figure>')
    if j.get('init'):
        extra.append(f'<figure><img src="{html.escape(rel(j["init"]))}" alt=""><figcaption>start from: '
                     f'<code>{html.escape(j["init"])}</code> (Image2Image, strength {j.get("denoise", 0.45)})'
                     f'</figcaption></figure>')
    sheet = os.path.join(ROOT, 'assets', 'gen', job, '_sheet.jpg')
    if have and os.path.isfile(sheet):
        extra.append(f'<figure><img src="{html.escape(rel(sheet))}" alt=""><figcaption>what it has</figcaption></figure>')
    if extra:
        out.append('<div class="figs">' + ''.join(extra) + '</div>')
    out.append(f'<p class="save">save into <code>assets/inbox/</code> (or <code>assets/inbox/{html.escape(job)}/</code>)</p>')
    out.append('</section>')
    return '\n'.join(out)


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prompts: {title}</title><style>
:root {{ --bg:#f6f4ef; --fg:#1d1b20; --dim:#6b6670; --card:#fff; --line:#ddd6cc; --ok:#1d7a46; --warn:#a4460f; --acc:#4b3fb5; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#16151a; --fg:#ece8e1; --dim:#a39d97; --card:#1f1e24; --line:#34323a; --ok:#6fd49a; --warn:#f0a36b; --acc:#a99cff; }} }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.5 system-ui, sans-serif; }}
main {{ max-width:980px; margin:0 auto; padding:24px 16px 80px; }} h1 {{ margin:0 0 4px; font-size:26px; }}
.intro {{ color:var(--dim); }} .intro ol {{ padding-left:20px; }} code {{ font-family:ui-monospace, Consolas, monospace; font-size:.92em; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; margin:14px 0; }}
.card.done {{ opacity:.55; }} .card h2 {{ margin:0; font-size:18px; display:flex; justify-content:space-between; }}
.n {{ color:var(--acc); font-variant-numeric:tabular-nums; }} .note {{ margin:4px 0; }} .meta {{ margin:4px 0; color:var(--dim); }}
.ok {{ color:var(--ok); }} .warn {{ color:var(--warn); }} .f {{ margin:8px 0; }}
.lab {{ font-size:12px; text-transform:uppercase; letter-spacing:.04em; color:var(--dim); display:flex; gap:8px; align-items:center; }}
button {{ font:inherit; font-size:12px; border:1px solid var(--line); background:transparent; color:var(--fg); border-radius:6px; padding:1px 8px; cursor:pointer; }}
button.did {{ color:var(--ok); border-color:var(--ok); }}
textarea {{ width:100%; font:13px/1.45 ui-monospace, Consolas, monospace; background:var(--bg); color:var(--fg); border:1px solid var(--line); border-radius:6px; padding:6px 8px; resize:vertical; }}
.figs {{ display:flex; gap:12px; flex-wrap:wrap; }} figure {{ margin:0; max-width:300px; }} figure img {{ max-width:100%; max-height:220px; border-radius:6px; display:block; }}
figcaption {{ font-size:12px; color:var(--dim); }} .save {{ font-size:13px; color:var(--dim); margin:6px 0 0; }}
</style></head><body><main>
<h1>Prompts &middot; {title}</h1>
<div class="intro"><p>{njobs} jobs, {have} of {want} pictures so far. Generate each job by hand, keep the ones you like, save them into
<code>assets/inbox/</code>, then run <code>python tools/intake.py</code> (it reads the prompt inside each PNG to file it under its job).</p>
<ol><li><b>NovelAI:</b> the prompt into the prompt box, the negative into Undesired Content, the size as shown. Two or more people:
one Character Prompt per person, placed where the card says (V5 places them freely; V4.5 uses the grid cell). Tags and plain sentences both work on V5.
A reference picture: Precise Reference or Vibe Transfer (NovelAI V4.5 until V5 gets them).</li>
<li><b>Figures to cut out</b> ask for <code>transparent background</code> (NovelAI V5 paints a real see-through PNG: the cut-out uses its own alpha)
or a flat coloured ground (every other generator: the cutter keys it out). Never white, black or a busy background.</li>
<li><b>Other generators:</b> add your usual quality words: <code>{quality}</code></li>
<li>Keep the files as PNG: the prompt stored inside is how intake.py sorts them.</li></ol></div>
{cards}
</main><script>
function cp(b) {{
  const t = b.closest('.f').querySelector('textarea');
  const done = () => {{ b.textContent = 'copied'; b.classList.add('did'); setTimeout(() => {{ b.textContent = 'copy'; b.classList.remove('did'); }}, 1200); }};
  if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(t.value).then(done, () => {{ t.select(); document.execCommand('copy'); done(); }});
  else {{ t.select(); document.execCommand('copy'); done(); }}
}}
</script></body></html>
"""


def main():
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, 'tools', 'jobs', '*.json')))
    jobs = []
    for f in files:
        jobs += json.load(open(f, encoding='utf-8'))
    if not jobs:
        sys.exit('no jobs: write tools/assets.py, run it, then this')
    want = sum(len(j.get('seeds') or []) or int(j.get('n', 4)) for j in jobs)
    have = sum(min(count(j['job']), len(j.get('seeds') or []) or int(j.get('n', 4))) for j in jobs)
    quality = (FILM.get('pictures') or {}).get('quality', 'masterpiece, best quality, highres')
    page = PAGE.format(title=html.escape(FILM.get('title', 'film')), njobs=len(jobs), have=have, want=want,
                       quality=html.escape(quality), cards='\n'.join(card(j) for j in jobs))
    out = os.path.join(ROOT, 'notes', 'prompts.html')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write(page)
    print(f'{out}: {len(jobs)} jobs, {have}/{want} pictures so far')
    print('  open it in a browser; save pictures into assets/inbox/, then: python tools/intake.py')


if __name__ == '__main__':
    main()
