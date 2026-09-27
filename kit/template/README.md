# {TITLE}

**A music video for {SONG} over ... (what it is, over what, in one line).** Made {DATE} with Claude (director) and
painter Claudes, with the user giving notes.

- **Watch:** `out/{NAME}.mp4` (the 1080p24 master) · `out/{NAME}_share.mp4` (1080p, sized to share) ·
  `out/{NAME}_discord.mp4` (720p, under Discord's free limit, frame 0 = the poster). Live in a browser:
  `node render/serve.mjs` → http://127.0.0.1:{PORT}/web/index.html (`?t=53` starts there).
- **The why:** `PLAN.md`. **The what/when:** `STORYBOARD.md` (with the notes table). **The how:** `STYLE.md` (the
  painters' bible). Every note, as it came: `notes/NOTES.md`.
- **Change a shot:** edit its scene, delete the affected `out/chunks-full/cNNNN.mp4` (chunk N = frames 240N..240N+239 =
  seconds 10N..10N+10), rerun `node render/render.mjs` (only missing chunks render), then `python render/share.py` and
  `<PY> render/final_check.py` (`python tools/film.py PY` prints the kit's python).
- Made with the music-video kit (`film.json` kit, kitCommit). Git keeps what we wrote; pictures, clips, audio and
  renders stay on disk (`.gitignore`). Commit at the milestones: first cut, each round of notes, delivery.

## The idea

## The rule

## The reels
| reel | span | what |
|---|---|---|

## Credits
