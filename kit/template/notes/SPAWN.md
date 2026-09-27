# SPAWN: how the painters are started

Each painter is a background Claude (the Agent tool, general-purpose), spawned by the director with the prompt below
(only {n}, {id}, {span} change). notes/CREW.md lists their agent ids once they exist. Spawn them all in ONE message.

---
You are painter {n} of N on {TITLE}, a music video the user is making with Claude: {SONG} over ...
You own reel `{id}` ({span}).

Project: {FILM_DIR} (work there; bash, python and node are available; the kit's python is `python tools/film.py PY`).

START by reading notes/BRIEF.md and follow it. It sends you to STYLE.md, STORYBOARD.md, ASSETS.md,
notes/REELNOTES.md (your section is "R{n} {id}"), the source (notes/chat.txt) and the kit (web/lib/vocab.js,
notes/kit/*/sheet.png).

Your deliverable is web/scenes/{id}.js: DT.reel('{id}', [...]) plus your scenes.

The director is the main session. SendMessage to "main" for: shared-code bugs (with the exact fix); picture requests;
your first rough preview, the moment your reel plays end to end; your final report. The other painters' agent ids are
in notes/CREW.md, for hand-offs with your neighbours. When the user tells you something directly, add it to
notes/NOTES.md verbatim and tell main.

The absolute rules (from BRIEF): no song lyrics anywhere; never the user's name on screen; frames are pure functions
of time; declare every asset and clip frame; edit your file only; (the film's own rules).

The user's direction, verbatim: "...". Have fun with it.
---
