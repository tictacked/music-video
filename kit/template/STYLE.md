# STYLE: how to paint a shot of {TITLE}

## The user's direction (verbatim)

## THE RULE (the short form; STORYBOARD.md has the whole of it)

## THE LOOK of the pictures and clips

## Pace
- **Cut pace follows the song's energy**: choruses fast (0.4-0.8 s shots, stutters of 2-6 frames on drum fills),
  verses breathe (0.8-1.5 s) but every shot MOVES, hero shots can hold 2-4 beats, the stops are SILENCE.
- **Cut ON the sound**: bar lines, beats, and `DT.timing.accents` ([t, strength 0..1, 'd' drum | 'o' other]). Pin a
  moment by ear with `<PY> song/ear.py T0 T1` (the song's hits in a window, measured).
- **Eye-trace**: faces and eyes land near the same spot across fast cuts. Plan where each shot's subject sits at its
  start and its end.
- Nothing dead: every shot has a move (a clip, a push, a slam, a whip, boil on twos with `ctx.jitter`).
- **Readability**: a line that carries a joke or a story beat stays up >= 0.3 s + 0.25 s per word (never under ~0.7 s;
  more than ~6 words: split it). Every key beat passes the MUTE-AND-BLUR test: it reads from the picture alone. Who
  is speaking must be obvious (their colour, their tag, a tail at their mouth).

## Pictures, clips, words
- Pictures: `DT.cast.pick('hero_full')` -> `'cut:hero_full/1'` (cut out, alpha) or `'gen:pl_room/2'` (whole). The jobs
  are in `tools/jobs/*.json` and `ASSETS.md`. Draw with `K.img(g, key, x, y, {h, anchor: 'feet'|'center'|'head'})` or
  `g.drawImage(DT.img(key), ...)`. **Declare every key in your scene's `assets`.**
- Clips (if the film has any): `const c = K.s.use('clip_name', {from, speed, hold, reverse, map})` -> declare
  `c.key(ctx)`, draw with `c.draw(g, ctx, {x, y, w, h, crop, zoom, focus, fit})`. `DT_CLIPS[name]` exists once a clip is
  usable. Until yours lands, paint with its first frame as a still: `'file:notes/clips/ff/<clip>.png'`.
- Words on screen: few. The story's own objects (the title, the credit, UI, props, the RP's own lines when the
  storyboard says so).
- RP lines: `K.s.say(g, ctx, who, text, t0, {...})` draws a line with the speaker's colour bar; when `who` has a colour
  in `DT.pal.who` it ALSO prints the speaker's NAME above the line (`tag: false` hides it, `tagText` renames it).
  If the film's rule is "no names on screen", pass `tag: false`. Text that must fit a box is MEASURED (the same font, weight and letterSpacing it's drawn with,
  the widest of all its lines), never eyeballed.

## The hard rules
1. **No song lyrics anywhere**: not on screen, not in code, comments, reports or messages. Timing is TIMES only;
   moments are named by number or by what happens.
2. **Never the user's name or handle on screen.** The only credit is the film's credit (film.json `credit`).
3. **A frame is a pure function of its index.** Time from `ctx`, randomness from seeds (`ctx.rnd`, `U.h01`), never
   `Math.random()` / `Date`. Compare frame times with a guard: `x < n / FPS - 1e-6` (without it, about half of all
   frames land a hair on the wrong side and a flash lasts one frame too long).
4. **Declare every asset** (pictures AND each clip frame via `handle.key(ctx)`), or strict mode fails the render.
5. **Your file only** (`web/scenes/<reel>.js`). Shared code is the director's: send fixes, don't edit.
6. (the film's own: the reserved colour and its owner, what is never shown, what is never cute, the content limits)

## Commands (from the film folder; <PY> = `python tools/film.py PY`)
    node render/stills.mjs --shots r1_a,r1_b --n 4 --sheet --label --out notes/work/<reel>/a
    node render/stills.mjs --times 14.1,15.0 --out ...          # timeline mode, song times
    node render/stills.mjs --scene <id> --dur 4 --n 6 --params '{"k":1}' --sheet   # a scene alone (sandbox)
    node render/render.mjs --preview --from B7 --to B16 --workers 1   # your reel as a 960x540 video with the song
    <PY> render/reelsheet.py <reel> out/range_preview_B7-B16.mp4 --from 14.03   # one frame per shot
    <PY> render/qa.py out/range_preview_B7-B16.mp4               # BLANK / POP / FROZEN detector on a render
    <PY> song/ear.py 29.2 31.3 [--band]                          # the song's hits in a window, measured
    node render/check_assets.mjs 337 748                         # every frame of a range: undeclared assets + page errors
    node render/shots.mjs                                        # the whole resolved shot list
    web/index.html?trtest=shatter                                # a transition alone (node render/serve.mjs, :{PORT})
**LOOK at every render** (open the PNGs). A still can't show timing: render a preview of your reel and QA it.
The kit, rendered: `notes/kit/<page>/sheet.png`.

## Kit tips (add yours)
- `render.mjs --preview` redoes a preview chunk that is older than the newest web/ or manifest file; the full render
  keeps finished chunks (delete one to redo it).
- A scene saved after a render started is NOT in that render's chunks (each worker loads the page once): redo them.
- Never `node -e "import('./render/render.mjs')"` to syntax-check: it RUNS a full render. Use `node --check`.
- `S.hit(ctx, t, {impact: 0})` means NO impact frame.
- `node render/check_assets.mjs F0 F1` walks every frame and lists the undeclared assets that `--loose` previews hide.
- `keepRed` darkens even a pure red to ~0.72x: draw graphic reds brighter, or draw them in `over` (above the look).
- Transition masks must be exactly 0 at p=0 and 1 at p=1; typed reveals lay out the WHOLE line and draw the first n
  letters (a centred partial string slides as it grows); every light effect scales with the light's power.

## Finishing
Send the director (SendMessage to `main`, or your final report): your shot list (id, time, what), what you're proud
of, what you'd still fix, any shared bugs (with the exact fix).
