# CLIPS: real motion from an image-to-video model (optional)

A film doesn't need clips: the engine animates stills (camera moves, parallax, cut-outs, boil, squash, transitions),
and an images-only film can be the best one. Clips add REAL motion: a head turning, hair in wind, a dance, a serve.
They are RAW MATERIAL, not the film: painters build shots from them (`K.s.use`). Make them BEFORE the build as an
asset phase (a film with dozens of picked clips was the best-looking of its batch), and during it as notes come in.

## Where they come from
Any image-to-video model: an online service the user already uses, or a local model on their GPU. The kit doesn't
care: it takes the downloaded files. Ask the user which service, what it costs them, and its content rules.

## The loop (the film's tools)
1. **First frames** (`ff_` jobs, used whole): the picture each clip starts from, 16:9 at the model's size.
   `<PY> tools/ff.py` composes first frames from picked pictures (a plate + cut-outs, `mirror`, `fit: contain`) into
   `notes/clips/ff/`; `tools/ffboard.py` puts them on one board to check.
2. **The clip list** `notes/clips/clips.json` (film.json `clipLists`): name, first frame, prompt (what MOVES, in plain
   words), seconds, and what moment it's for. Write prompts about motion, not appearance: the first frame already says
   what things look like.
3. **The user generates** each clip from its first frame + prompt, and saves it as `assets/clips_in/<name>.mp4`
   (a re-roll as `<name>_r2.mp4`: it waits until it's renamed to `<name>.mp4`).
4. **`<PY> tools/clips_in.py`**: frames at 24 fps, scaled to 1920 wide, into `assets/clips/<name>/00000.jpg ...`,
   usable at once; an upscale in place if the machine has one (`machine.json` `upscale_python`: `tools/upscale.py`,
   Real-ESRGAN on a GPU); then `assets/clips/clips.js`.
5. Scenes: `const c = K.s.use(name, {from, speed, hold, reverse, map})`, DECLARE `c.key(ctx)`, draw
   `c.draw(g, ctx, {x, y, w, h, crop, zoom, focus, fit})`. Frames are `clip:<name>/<n>` JPGs; keyed clips are
   `clipa:<name>/<n>` PNGs with alpha. The engine's clip cache is capped, so a scene only asks for the frames it draws.

## Modes that worked
- **First frame + words**: our picture + a plain prompt of what moves. The workhorse.
- **Borrowed motion**: if the model takes a motion reference, our first frame + a reference video's movement nails
  choreography (a sports swing, a dance, a curtsy). Cut the reference with `<PY> tools/cutplate.py` to the model's
  length and size (the reference's aspect must match the output); `--freeze-in` lands every plate's KEY MOMENT (the
  contact, the turn) at the same time, so every clip cuts onto its beat with one offset.
- **References + words**: character pictures as references and the scene in words, never a pasted composite (a
  character pasted into a scene came out tiny and stiff).
- **Hero clips at the model's higher resolution**: fine lines hold, identity survives fast motion, and the upscale to
  1080p is gentler. A keyed figure that fills the screen NEEDS it. A close-up zoomed 2x goes soft: re-roll from a
  CLOSER first frame instead.
- **Chained clips for a longer action**: the next clip's first frame = the previous clip's LAST frame
  (`ffmpeg -sseof -0.05 -i a.mp4 -frames:v 1 last.png`), so a car arrives and drives on with no seam. Keep a moving
  thing's DIRECTION between clips (a vehicle that arrives head-on and "leaves" tail-first reads as a transformation).

## Motion references from real video
`tools/cutplate.py` cuts a reference (yt-dlp is in the kit's env) to the right length and size. Modern TV animation has
real body motion; older limited animation is held drawings and speed lines (take INSERTS from it: hands, feet, a
string snapping, not full swings). Check a plate's FIRST frame (a window that starts one frame early carries the
previous shot) and scan for SEE-THROUGH OVERLAYS (an aura behind a figure becomes a second figure). Review with
`tools/refboard.py` (zoom strips stamped with source times), `tools/platereel.py`, `tools/platereview.py`, and
`tools/pairs.py` (source | our version, side by side).

## Review, and the user's picks
- Look at REAL-SIZE frames: `tools/board.py` (4 frames per clip) or `tools/clipgrid.py` (2x2 full size); `tools/strip.py`
  (8 frames in a grid). Thumbnail strips lie.
- `tools/reel.py` strings clips into a labelled reel in storyboard order, with their own sound, for the USER: every clip
  they don't flag is a pick; flagged ones become re-rolls. `<PY> tools/assetsmd.py` writes `ASSETS.md`, the inventory
  painters build from.
- `tools/motion.py` charts how snappy a move is; `tools/snap.py` retimes a slow head turn into a snap (the head moves
  in 6-10 frames: anime timing).

## What video models do that you have to catch
- Clips often start with a BOUNCE (the figure rises and drifts for ~20 frames): find a clean stretch after it and never
  show the start. Some add a PUSH-IN: measure the top of the head per frame and use the clean frames only.
- They keep whatever the first frame has: a cropped crown, a pillarbox, a second figure from a reference overlay.
- They sometimes cut to a SECOND shot after ~2 s: use the first part.
- Vehicles and signs sprout invented banners and fake lettering: roll 2-3 seeds and pick, then smear the text.
- Check every hero clip frame by frame against the story's limits: clothes stay on through a transformation; a kiss
  clip must not START on the kiss; a near-kiss can pass through faces touching (cut so it reads as intended).
- Broken outputs (blocky, a grey haze): re-roll, and rename the broken file `<name>_BROKEN.mp4` so nothing picks it up.

## Keyed clips (figures on flat colour -> alpha)
Shoot figures on flat mint or pink first frames, then `<PY> tools/keyclip.py <name>`: the ground per row from the
border strips, alpha from colour distance, the largest blob, an OPAQUE CORE, a spill clamp -> `clipa:` frames.
- Flat grounds DRIFT during a clip (a hot-pink ground came back peach), and skin can key out, punching holes in a face
  or a hand. `--fill auto` (the default) fills holes that aren't the ground. Check every keyed clip's holes, one frame
  each.
- `tools/clipsjs.py` writes each keyed clip's figure box to `DT_CLIPA`, so feet anchors work on clip frames (without
  it, keyed figures floated ~30 px).
- A still the camera dives into (2x and more): upscale it (`tools/upstill.py`) and DRAW IT AT SOURCE SIZE (a fixed
  source width x scale, never `img.naturalWidth`), so the upscale drops in without moving anything.
