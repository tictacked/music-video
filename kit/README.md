# The kit: the engine, the template film, the tools

Everything the films share: a **template film** that renders on day one, the engine (Canvas2D scenes + a WebGL
finishing pass, rendered frame by frame by headless Chrome), the song, picture, clip and delivery tools, `setup.py`
for the runtimes, and a regression test. The how-to lives in the skill (`../SKILL.md` and the topic files); this is the
kit's own manual.

**The rule: a film is a COPY.** `new_film.py` copies `template/` into a new folder. From then on the film owns its
files, and nothing a later film or a kit change does can alter it: finished films stay frozen and reproducible.
Improve the kit, not old films.

## Once per machine
    python setup.py            # the runtimes: node_modules, env/py, env/sep, fonts, machine.json, models
    python setup.py --check    # what's installed, what's missing, and how to get it

## Start a film
    python <kit>/new_film.py <name> --title "TITLE" --song "Song -- Artist (year)" [--bpm 126] [--dest <folder>]

This creates `~/music-videos/<name>/` (or `--dest`, or `$MV_FILMS`) with:
- `film.json` filled in;
- `node_modules` linked to the kit's (a junction on Windows, a symlink elsewhere) and the fonts copied in;
- a placeholder timing (12 s at the given BPM), so the testcard reel renders at once;
- the docs with the film's name in them;
- a first git commit.

Look at it with `node render/serve.mjs` (http://127.0.0.1:<port>/web/index.html), then follow the skill's order of work.

## film.json: the one place a film's settings live
Every tool reads it (`tools/film.py`, `render/film.mjs`; the page gets it as `/film.js` from `render/serve.mjs`). No
tool hardcodes a film's name.

| key | what |
|---|---|
| name | the folder, and `out/<name>.mp4` / `_share` / `_discord` |
| title, subtitle | the page's title and cover |
| song | "Song -- Artist (year)" (timing.json, docs) |
| credit | the one on-screen credit, exactly (read it at full resolution) |
| audio | what the master muxes (`song/audio.m4a`, or a version with a held tail: see holdAfter) |
| port | `render/serve.mjs`'s port (new_film picks a free one) |
| clipLists | the clip lists (`notes/clips/clips.json`) |
| clipSkip | clips the upscale leaves alone (unused ones, or ones a painter has drawn over frame by frame) |
| posterT | the discord cut's frame 0 = the frame at this second (chat apps thumbnail frame 0; 0 = no swap) |
| holdAfter | seconds held after the song ends (song/timing.py adds it to the duration) |
| share, discord | `targetMiB` / `maxMiB` / `audio` / `scale` (+ `vb` to override the bitrate, `denoise` for hqdn3d) |
| bpmHint | where `song/analyze.py` starts its tempo search |
| whole, nocutPrefixes, keycut | which pictures are never cut out, and which are keyed from their flat ground instead of rembg |
| reservedColour | the colour only one character owns (`render/final_check.py` lists every second it's on screen) |
| pictures | the picture recipe: `generator` (novelai / a1111 / other), `quality`, and for tools/gen.py `model`, `sampler`, `scheduler`, `steps`, `cfg`, `shift`, `neg`, `loras` |
| kit, kitCommit | where the kit is and which commit the film was made from (`drift.py`) |

## What's in the template
- `web/`
  - `index.html`: the page (live player; `?mode=render`; `?scene=` sandbox; `?trtest=` a transition alone).
  - `lib/engine.js`: the engine (its header lists the looks and transitions).
  - `lib/kit.js`: K.*, the pop vocabulary. `lib/shaft.js`: K.s, cards, RP lines, clip handles (`K.s.use`), hits.
  - `lib/cast.js`: picks and whole pictures. `lib/vocab.js`: K.v, this film's own vocabulary.
  - `timeline.js`: the reels and the assembler, with B<n> bar anchors.
  - `scenes/`: `_index.js`, `shared.js`, `testcard.js`, and the placeholder `reel1.js`.
- `render/`
  - `serve.mjs`, `render.mjs` (chunked, strict, resumable; `--from B7 --to END`), `stills.mjs`, `shots.mjs`,
    `check_assets.mjs`, `browser.mjs` (the headless Chrome flags per platform), `film.mjs`.
  - `share.py`: the delivery cuts (bitrates from the length, the poster frame). `final_check.py`: the checklist.
  - `qa.py` (BLANK / POP / FROZEN), `reelsheet.py`, `keeper.sh` (render slots).
- `song/`: `separate.py` (Demucs, CPU), `analyze.py` (the drum-attack grid), `timing.py` (timing.json + web/timing.js,
  TIMES only), `ear.py` and `listen.py` (measuring), `words.py` (faster-whisper; the words go to `song/private/` only).
- `tools/`
  - the film's settings: `film.py` (`python tools/film.py PY` prints the kit's python);
  - pictures: `assets.py` (the job lists), `promptsheet.py` (generate by hand), `intake.py` (file hand-made pictures),
    `gen.py` (a local A1111/Forge), `cutout.py` + `holekey.py` + `depink.py` + `retouch.py` (cut-outs),
    `crownpad.py`, `mask.py`, `unbar.py`, `photos.py`, `pencil.py`, `sketchcut.py`, `castsheet.py`, `pickboard.py`,
    `sweepsheet.py`, `assetsmd.py`;
  - clips: `ff.py`, `ffboard.py` (first frames), `clips_in.py` (bring clips in), `rawframes.py`, `upscale.py`,
    `upstill.py`, `clipsjs.py`, `keyclip.py`, `keystill.py`, `cutplate.py`, `refboard.py`, `platereel.py`,
    `platereview.py`, `pairs.py`, `motion.py`, `snap.py`, `strip.py`;
  - review: `board.py`, `clipgrid.py`, `reel.py`, `review.py`, `contact.py`.
- Docs: `README.md`, `PLAN.md` ("Who are they, really?"), `STORYBOARD.md` (the notes table), `STYLE.md` (the painters'
  bible), and `notes/`: `BRIEF.md`, `SPAWN.md`, `CREW.md`, `BUGS.md`, `REELNOTES.md`, `NOTES.md` (every note the
  user gives, verbatim).
- `.gitignore` (git keeps what we wrote; media stays on disk) and `.gitattributes` (`* -text`: byte-exact scripts).

## Runtimes (the kit's, shared by every film)
- `node_modules/`: puppeteer (its Chrome lives in puppeteer's cache) + roughjs. Each film links to it.
- `env/py/`: numpy, pillow, opencv, librosa, soundfile, scipy, scikit-image, rembg + onnxruntime, yt-dlp (+
  faster-whisper with `setup.py --whisper`).
- `env/sep/`: Demucs + torch, CPU.
- `fonts/`: the 30 Google Fonts families, copied into each film's `assets/fonts/`.
- `machine.json`: this machine's settings: `a1111` (a local WebUI's address for tools/gen.py), `upscale_python` and
  `upscale_models` (a python with torch + spandrel, and a folder with `realesr-animevideov3.pth`, for tools/upscale.py).
  Never shared.

## Changing the kit
1. Edit `template/` (or add a vocabulary to `vocab/`).
2. Render the testcard pages before and after (`node render/stills.mjs --scene testcard --params '{"page":"looks"}'`
   in a scratch film) and, once you have finished films, compare one frame by frame:

       node test/regress.mjs <film folder>          # the film's own engine vs the kit's, every frame
       <PY> test/sheet.py test/out/<film>           # the two side by side, to look at

   Expect 0 DIFFERENT frames. "Render noise" (up to 1/255 on scattered pixels) is the same page rendering twice.
   `--self` renders a film against itself (the noise floor); `--swap engine.js` swaps one file (bisecting).
3. `python drift.py <film>` shows how a film differs from the kit it came from.
4. A film made later records the kit's commit in `film.json`.

## Disk
`python sweep.py [--root <folder of films>]` (a dry run) sizes the regenerable scratch in finished films: render
chunks, previews, and painter stills no scene reads. `--delete` deletes, only after the user says so.
