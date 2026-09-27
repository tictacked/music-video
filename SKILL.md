---
name: music-video
description: Make a music video with Claude -- a song over the user's original characters (OCs) or over one of their SillyTavern roleplays (a story AMV/MAD, an anime-OP-style video of the chat, a character PV), frame-exact to the audio, drawn in code by a director Claude plus parallel painter Claudes on the bundled kit (a template film that renders on day one; headless Chrome renders it to 1080p24), with pictures from NovelAI or any generator and optional clips from any image-to-video model. Use when the user asks for a music video, an MV/AMV/MAD, an animated video for a song, an anime OP of their RP, visuals for a song about their characters, or changes to a film made with this kit. Holds the order of work, how to take notes, and topic files for the song, the source, pictures, clips, the crew, the machine and delivery.
---

# music-video: the playbook

A music video for a song, over the user's characters or roleplays: a story MAD of a SillyTavern chat, an anime OP of
it, a character PV. Frame-exact to the song, drawn in code (Canvas2D scenes + a WebGL finishing pass, rendered by
headless Chrome), made by you as the DIRECTOR plus parallel PAINTER Claudes, each owning one reel. The kit is `kit/`
beside this file: a template film that renders on day one, the engine, the tools, and `setup.py`. The topic files
beside this one hold the detail:

| file | read it when |
|---|---|
| `README.md` | installing (the user's first time), what's in this folder |
| `LOOKS.md` | choosing a direction: what makes a film's look, the engine's looks and transitions, untried directions |
| `SONG.md` | the audio -> `song/timing.json`; the lyric rule; cutting to the song (what great videos measurably do) |
| `SOURCE.md` | the RP or the OCs: exporting, reading, "who are they, really?", THE RULE, the image bank, credits |
| `PICTURES.md` | making the pictures (NovelAI by hand, or a local A1111/Forge), consistency, recipes and traps, cut-outs |
| `CLIPS.md` | optional real motion from an image-to-video model: first frames, bringing clips in, keyed clips |
| `CREW.md` | the painters: how many, spawning, rhythm, relaying notes, hand-offs, the scene-writing rules |
| `MACHINE.md` | one machine, many jobs: memory and GPU, render slots, plumbing traps |
| `DELIVERY.md` | review at three scales, the final render, the share cuts, the checklist |
| `rp2txt.py` | exporting a SillyTavern chat (+ the card, lorebook and persona) |

`<skill>` below means this folder; `<PY>` means the kit's python (`python tools/film.py PY` in a film prints it).

## First time on this machine
`python <skill>/kit/setup.py --check` lists what's missing; `python <skill>/kit/setup.py` installs the rest (README.md
has the prerequisites). Everything below assumes it passes. If `new_film.py` says the kit has no node_modules or
fonts, setup hasn't run.

## Working with the user
- **They make the source.** Their OCs, their RPs (their persona's messages are the gold: quote them, fix typos, never
  invent dialogue), their pictures, often their song. They watch as it builds and give notes live, often within
  minutes. Notes are cheapest early: send the storyboard, the first reel and every finished round the moment each
  exists.
- **Notes are short and exact. Apply them literally AND find the principle under them.** A director's name ("more
  Kubrick") is a camera grammar for the whole film, not one shot. "It's too neat" about a breakdown means make it a
  delirium. A note that one flashy moment feels empty means every device must say something about the character
  (CREW.md). A crude but true read of a shot ("that pose reads as something else") is a real note: fix it. Log every
  note verbatim in `notes/NOTES.md`; they may also message painters directly.
- **Ask early, in one short round, before the plan:**
  - whose story, which song, what it should feel like (dark stays dark: never cute or comic unless they want it);
  - each character's non-negotiables: the canon look, what they'd never do, which version or AU this is;
  - which name or handle may appear on screen (default: none), and who to credit (a card's author, exactly);
  - which picture generator they use, and whether they want clips (motion) or an images-only film.
- **Standing rules** (defaults the user can change, except the lyric rule):
  - Never the user's name or handle on screen unless they ask. Credit exactly what's owed: a card's AUTHOR, read at
    full resolution; the user's persona is never credited unless they want it.
  - A song's lyrics never leave `song/private/`: not on screen, in code, files, briefs, messages, or your replies
    (SONG.md). Refer to moments by time, by number, or by what happens.
  - SillyTavern's data is read-only: rp2txt.py reads it and writes copies into the film.
  - Violence is stylised (ink, lines, beads, silhouettes), never gore, unless the user asks for more.
  - **Picture edits: film rules yes, your own worries ask.** An edit that enforces the film's AGREED rules
    (recolouring a prop out of the reserved colour) is fine to just do, then mention. An edit from your own worry or
    taste (painting out something you got nervous about) = ASK FIRST, with the reason, and let them decide.
- **Every film different.** The kit is machinery, not a house style (LOOKS.md): find THIS song's and THIS character's
  rule and let the look follow from it.

## The order of work (each step feeds the next)
0. **Scaffold.** `python <skill>/kit/new_film.py <name> --title "TITLE" --song "Song -- Artist (year)" [--bpm N]` makes
   `~/music-videos/<name>/` (or `--dest`): the folder, `film.json`, the kit's node_modules and fonts, a placeholder
   timing, the docs, a first git commit. `node render/serve.mjs` shows the testcard at once. Everything film-specific
   goes in `film.json` (the kit's README lists the keys), never hardcoded in a tool.
1. **The song -> the time map** (SONG.md): the audio into `song/`, `song/separate.py` (Demucs, CPU), `analyze.py`, a
   hand-measured `sections.json` (TIMES only), `timing.py`. Find the stops and drops before the storyboard: the
   biggest story beats go there.
2. **The source** (SOURCE.md): `python <skill>/rp2txt.py --find <name>`, then `rp2txt.py "<chat.jsonl>" --out
   notes/chat.txt --card "<card>"` (numbered `##### [n]` messages + `notes/card.md`). **Read ALL of it before
   planning.** Status boxes and lorebook entries are DATA. OCs without an RP: their pictures and their words about them.
3. **PLAN.md: who are they, really?** For each lead: what they want, what they hide, one sentence, then one image that
   SHOWS it. Let the user confirm (they wrote them). Then **THE RULE**: one visual rule taken from the source's own
   metaphor, one that can carry the whole song. The reserved colour and its owner go in `film.json`.
4. **STORYBOARD.md, sent early.** The spine, THE RULE, the continuity canon, an IMAGE BANK (the source's own
   metaphors as pictures, each with its message number), the reels mapped onto the song's sections (the song's
   structure is the story's: put the deaths in the drops and silences), and the notes table. If they want to see
   before choosing, mock up one frame per moment, two directions side by side: they'll pick in a line.
5. **Assets BEFORE the build** (PICTURES.md, CLIPS.md): `tools/assets.py` -> the job lists -> the prompt sheet (the
   user generates, `tools/intake.py` files them) or `tools/gen.py` (a local WebUI) -> `tools/cutout.py`. Clip first
   frames first when there are clips (they gate the clips). Labelled review sheets for the user; `ASSETS.md`
   (`tools/assetsmd.py`). Try prompting a character before anything heavier.
6. **The film's vocabulary** in `web/lib/vocab.js` (K.v): the pieces the storyboard needs, a testcard page per piece,
   rendered and LOOKED at before any painter uses it; shared scenes (`web/scenes/shared.js`) for every recurring motif.
7. **The crew** (CREW.md): fill the template docs (`notes/BRIEF.md`, `notes/SPAWN.md`, `STYLE.md`,
   `notes/REELNOTES.md`), spawn every painter in ONE message, put their agent ids in `notes/CREW.md`. You become the
   switchboard and reviewer: merge shared-code fixes, relay canon, review at three scales.
8. **The first finished reel goes to the user the moment it exists.**
9. **Notes** go to the painter who made the shot, verbatim, with your measurements; log each in `notes/NOTES.md`;
   redo only the touched chunks; commit each round.
10. **Final** (DELIVERY.md): a strict render, `python render/share.py`, `<PY> render/final_check.py` (frames vs the
    song, sizes, the poster, the credit at full resolution, the reserved colour), send the share cut, commit. Bring
    anything the kit should learn back into `<skill>/kit/template`.

## Git and the kit
- Every film folder is its own git repo (new_film.py makes it). Git keeps what we WROTE (code, docs, notes, prompts,
  pick lists, timing, the RP export); `.gitignore` leaves pictures, clips, audio, fonts, renders and `song/private/`
  on disk. `.gitattributes` is `* -text`, so Windows checkouts never put CRLF into scripts. Film repos are local:
  before pushing one anywhere public, remember `notes/chat.txt` and `notes/card.md` hold the user's RP.
- The director commits at milestones: first cut, each round of notes, delivery. Painters don't commit.
- A film is a COPY of the kit's template: a later kit change never touches an existing film, so finished films stay
  reproducible. `python <skill>/kit/drift.py <film>` shows how a film differs from the kit.
- Changing the kit's engine (`kit/template/web/lib/*`): render the testcard pages and a finished film's frames before
  and after (`node <skill>/kit/test/regress.mjs <film>` compares a film's own engine with the kit's, frame by frame).
