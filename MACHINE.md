# MACHINE: one computer, many jobs

A film runs several heavy things on one machine: an image generator (maybe), a video model (maybe), headless Chrome
renders (always), Demucs and whisper (once each). Most trouble is plumbing, not art.

## Memory and the GPU
- Each headless render (a painter's stills or preview, the final render) is a Chrome with ~0.8 GB of VRAM and a few
  GB of RAM. `notes/.render-slots` (2 slots by default) keeps a crew from stacking browsers: "waiting for a slot" is
  normal. `sh render/keeper.sh 1` holds a slot so the crew shares fewer while something else needs the GPU; stop it
  with `rm notes/.render-slots/KEEP`.
- **Measure before starting anything heavy on the GPU** (a local image generator, a local video model, the final
  render): free VRAM (`nvidia-smi`) and free memory. On Windows the limit that bites is COMMIT (RAM + page file), not
  RAM: Task Manager -> Performance -> Memory -> "Committed". A local image model plus a video model plus a render crew
  can run a 64 GB machine out of commit.
- **Sequence the heavy things**: image batches, video batches and the master render never overlap. When the GPU is
  busy, do the CPU work: Demucs (`song/separate.py`), `analyze.py`, whisper on the CPU, the plan, `sections.json`.
- No GPU at all: everything still works. Renders use Chrome's software WebGL (slower), Demucs and whisper run on the
  CPU, pictures and clips come from online services.

## Platforms
- **Windows**: the kit uses ANGLE on Direct3D for WebGL; node_modules is linked into each film with a directory
  junction (no admin needed). Run the tools from PowerShell, cmd, or Git Bash. Git Bash rewrites arguments that look
  like `/c/...` or `/mnt/...` paths: prefix `MSYS_NO_PATHCONV=1` when passing such a path to a Windows program.
- **macOS**: ANGLE on Metal. Chrome's first launch may ask for permission.
- **Linux**: Chrome may need system libraries (`sudo npx puppeteer browsers install chrome --install-deps` in the kit
  folder). Stem separation installs the CPU build of torch.
- **No usable GPU** (a VM, a container, WSL, many Linux boxes): Chrome then hands out WebGL contexts that are already
  LOST, and every frame would render blank. `render/browser.mjs` probes WebGL at every launch (a draw and a
  read-back) and falls back to SwiftShader, Chrome's software WebGL, by itself: it prints a note, and renders take
  a few times longer. The engine also refuses to render on a lost context (strict renders fail instead of writing
  black frames).
- `MV_CHROME_ARGS` (space-separated) REPLACES the browser flags and skips the probe, so give the whole list: e.g.
  running as root in a Linux container needs
  `MV_CHROME_ARGS="--no-sandbox --use-angle=swiftshader --enable-unsafe-swiftshader"`.
- Only compare renders made with the same flags: GPU and software WebGL frames look the same but aren't bit-identical.

## Plumbing traps (each cost someone an hour)
- `render.mjs` loads the page ONCE per worker: a scene saved after a render started is not in its chunks. Compare file
  times with the render's start and redo those chunks.
- Never `node -e "import('./render/render.mjs')"` to syntax-check: it RUNS a full render. Use `node --check`.
- A background watcher that outlives its parent keeps running (and two can race on one folder). Before starting a
  loop again, check the old one is gone. Never auto-restart a process that was killed on purpose.
- A headless Chrome can hang in `browser.close()`: the renderers close with a deadline, then kill it.
- The first import of rembg or librosa compiles numba caches inside the kit's env; two processes doing it at the same
  moment can collide (`No such file or directory: ...nbi.tmp...`). It's transient: run the command again.
- `render.mjs` refuses flags it doesn't know (a typo used to start a full render): `node render/render.mjs --help`.
- Writing files through layers of quoting (ssh, heredocs, `sed`, `python -c`) mangles backslashes: write files with
  the editor tools, use forward slashes in paths, and read the bytes back.
- A folder name ending in '.' (a timestamp with a trailing dot) can't be listed on Windows: the stills tool strips it.
- Git with `core.autocrlf=true` (common on Windows) rewrites scripts with CRLF on checkout and bash fails on the `\r`:
  every film carries `.gitattributes` `* -text`.
- An inbox or clip folder that fills with files named alike (`image (3).png`): intake.py and clips_in.py go by the
  contents and the names you give; re-rolls wait as `<name>_r2.mp4` until renamed.
