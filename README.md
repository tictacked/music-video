# music-video: a Claude Code skill for music videos of your OCs and roleplays

Give Claude a song and your characters, or one of your SillyTavern roleplays, and it directs a music video: a story
AMV of the chat, an anime-OP-style video, a character PV. It reads the whole RP, finds who your characters really are,
maps the story onto the song's structure, and builds the video frame-exact to the beat. Claude acts as the director,
and several helper Claudes ("painters") each draw one stretch of the song, in code. The result is a 1080p video,
plus smaller cuts sized for sharing.

You make the source: your characters, your RP, your pictures (NovelAI, any generator, or your own art), your notes.
Claude asks what matters to you first, sends you the storyboard and the first finished section early, and takes notes
live while it builds.

## What you need
- **Claude Code** (https://docs.claude.com/en/docs/claude-code). A bigger plan lets it run more painters at once; on
  a smaller plan Claude paints the film itself, one section at a time.
- **Python 3.10-3.13**, **Node.js 22.12 or newer**, **ffmpeg**, and **git** (recommended). On Windows:

      winget install Python.Python.3.12
      winget install OpenJS.NodeJS.LTS
      winget install Gyan.FFmpeg
      winget install Git.Git

  On macOS: `brew install python@3.12 node ffmpeg git`. Open a NEW terminal afterwards so the commands are found.
- About 5 GB of disk for the tools, plus space for your films (a finished film with its pictures is 1-3 GB).
- A graphics card helps but isn't required. Pictures come from wherever you make them (NovelAI works great), so no
  local image model is needed. Clips (real motion) are optional and come from any image-to-video service.

## Install
1. Put this whole folder at `~/.claude/skills/music-video/`. On Windows that's `%USERPROFILE%\.claude\skills\music-video\`
   (your user folder, then `.claude\skills\music-video`): the folder that contains this README and `SKILL.md`.
2. Run the setup once (10-20 minutes; it downloads about 2-3 GB: a headless Chrome, the Python packages, 30 fonts,
   and two small AI models for cut-outs and splitting songs into stems):

       python ~/.claude/skills/music-video/kit/setup.py

   On Windows: `python %USERPROFILE%\.claude\skills\music-video\kit\setup.py` (cmd) or
   `python $HOME\.claude\skills\music-video\kit\setup.py` (PowerShell).
   Add `--whisper` to also install word timing (optional). `setup.py --check` shows what's installed any time.
3. Start Claude Code in any folder and say something like: *"let's make a music video for this song
   (it's in my Downloads, song.mp3) about my SillyTavern chat with Aria"*. Claude picks up the skill from there.

Films are made in `~/music-videos/<name>/` (each its own folder, with its own git history).

## Your first film: have these ready
- the song file (mp3, wav, m4a...);
- the story: a SillyTavern chat (Claude finds it in your SillyTavern folder, or export the chat as .jsonl and the card
  as .png), or pictures and notes about your OCs;
- your picture generator open. With NovelAI, Claude writes a prompt sheet (a page with copy buttons for every picture
  it needs); you generate, keep your favourites, and drop them into the film's `assets/inbox/` folder, and Claude
  files them. NovelAI V5 can paint figures on a transparent background, which the kit uses directly;
- an idea of the lines: what must never be shown, how dark it can get, whose name may appear on screen (by default:
  nobody's, only the credit you choose).

## What stays where
- Everything runs on your computer: the renders, the song analysis, the cut-outs. Your SillyTavern files are only
  read, never changed.
- Claude reads what you give it (the RP, the card, the pictures) in order to make the film. A commercial song's lyrics
  never go on screen or into any file outside the film's private folder.
- Each film is a local git repo. It keeps a copy of your RP (`notes/chat.txt`): check before putting a film's folder
  anywhere public.

## What's in this folder
- `SKILL.md`: what Claude reads first: the order of work, and how to work with you.
- `LOOKS.md`, `SONG.md`, `SOURCE.md`, `PICTURES.md`, `CLIPS.md`, `CREW.md`, `MACHINE.md`, `DELIVERY.md`: the playbook,
  by subject.
- `rp2txt.py`: exports a SillyTavern chat, its card, lorebook and your persona into the film.
- `kit/`: the engine and tools.
  - `kit/setup.py` installs the runtimes into `kit/env/`, `kit/node_modules/` and `kit/fonts/`.
  - `kit/new_film.py` starts a film from `kit/template/`.
  - `kit/README.md` is the kit's own manual.

## Troubleshooting
- `python setup.py --check` names what's missing and how to get it.
- "python not found" right after installing it: open a new terminal (PATH updates only in new windows).
- A render complains it has no WebGL: run `setup.py --check`; on Linux, run
  `sudo npx puppeteer browsers install chrome --install-deps` in the `kit` folder.
- A picture didn't get filed: `python tools/intake.py --dry-run` shows where each picture would go and why. Pictures
  re-saved by another app lose the prompt stored inside them, so put those in `assets/inbox/<job>/` instead.

Fonts are downloaded from Google Fonts by setup.py, under the SIL Open Font License or the Apache License (free to use
in videos).
