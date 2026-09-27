# DELIVERY: review, the final render, the share cuts, the checklist

## Review at three scales (stills can't see time)
1. The whole film as a sheet, one frame per shot: `node render/stills.mjs --shots <all ids> --n 1 --sheet`, or
   `<PY> tools/review.py film|cuts` (it keeps going past a reel that's mid-edit).
2. Before and after every cut: continuity, eye-trace, hand-offs.
3. A rendered preview through `<PY> render/qa.py` (BLANK / POP / FROZEN): it has caught a teleporting hand. Check POPs
   against the timing: nearly all of them should sit within a couple of frames of a hit, a beat or a mark (painted
   hits). A transition's whole window counts as a cut.
Open the PNGs yourself (read them). Painters do the same for their reels.

## The final render
- **Rebuild the manifest after the LAST picture batch** (`<PY> tools/cutout.py --manifest`): pick helpers fall back
  silently to another picture when a pick isn't in the manifest yet. Still-check a few pick moments before the master.
- Measure memory first (MACHINE.md). `node render/render.mjs --workers 2`: strict by default (a failed script load or
  an undeclared asset is FATAL, never a silent placeholder), chunked (240 frames = 10 s a chunk), resumable. A 1.5-4.5
  minute film takes 3.5-7.5 minutes on 2-3 workers with a GPU; much longer on software WebGL.
- A note after the final: edit the scene, delete the touched `out/chunks-full/cNNNN.mp4` (chunk N = frames
  240N..240N+239 = seconds 10N..10N+10), rerun render.mjs (only missing chunks render; nothing left to render = a
  re-mux with no browser), then share.py and final_check.py again.
- Pre-render finished reels' chunks while the last painters work (chunk indices are absolute).
- The master holds every frame of the song: the renderer never trims to the shorter stream (that once cut 1-4 frames of
  black or credit off the end of every film).

## The cuts (`python render/share.py`)
- `out/<name>_share.mp4`: 1080p, sized to film.json `share.targetMiB` (default 45 MiB: fits most ~50 MB limits).
- `out/<name>_discord.mp4`: 720p, under Discord's free 10 MB upload limit (`discord.targetMiB`, default 9 MiB). A
  long film at 9 MiB looks soft: say so, and offer the share cut for anywhere with a higher limit.
- The bitrate is worked out from the film's length (target size / duration - audio, minus 3%). A cut's `vb` overrides
  it; `maxMiB` is what final_check enforces.
- **Chat apps show FRAME 0 as the preview** (no seek, no black-skip), so a film that opens on black is a black box.
  The discord cut swaps frame 0 for the title card (film.json `posterT`: the second the title is on screen). One frame:
  same frame count, duration and sync. The master and the share cut stay pure.
- Grain and static eat bits: `hqdn3d` runs BEFORE the scale (`"denoise": "3:3:6:6"` in a cut's block for a grainy
  film).
- The master (CRF 15, 400 MB-2 GB) stays on disk. Send the share cut; mention the discord cut.

## The checklist (`<PY> render/final_check.py`)
PASS/FAIL:
- the master holds every frame of the song (ceil(duration x 24));
- it is 1920x1080, 24 fps, yuv420p;
- the audio is as long as the song;
- the share cuts are under their maxMiB, with the master's frame count;
- the discord cut's frame 0 is not black.
LOOK:
- the credit, pulled at FULL resolution: read every letter (a name in another script can lose characters at small
  sizes, and at 960x540 nobody can tell);
- every second the reserved colour is on screen (film.json `reservedColour`): check each span belongs to its owner;
- qa.py;
- git.

## After the user has it
1. Commit the delivered state in the film's repo (first cut, each round of notes, delivery: the director commits,
   painters don't).
2. Anything the kit should learn (a fixed tool, a new vocab piece, an engine fix): bring it into
   `<skill>/kit/template` (or `kit/vocab/`), check it on the testcard pages and a finished film
   (`node <skill>/kit/test/regress.mjs <film>`), and commit the kit if it's a git repo.
3. Months later, disk: `python <skill>/kit/sweep.py` sizes the regenerable scratch in finished films (render chunks,
   previews, painter stills no scene reads); it deletes only with `--delete`, and only after the user says so. After a
   sweep, a fix to that film re-renders it whole.
