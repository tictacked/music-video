// film.mjs -- this film's settings (film.json at the film root) for the node renderers. See tools/film.py.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const FILM = JSON.parse(fs.readFileSync(path.join(ROOT, 'film.json'), 'utf8'));

// The scripts web/index.html loads, in order, as paths relative to ROOT (node_modules bundles skipped; '/film.js' is
// served from film.json by serve.mjs). shots.mjs and check tools load exactly this list, so a film's own vocab file can
// never be left out of them (a hand-kept list in shots.mjs once missed one).
export function pageScripts() {
  const html = fs.readFileSync(path.join(ROOT, 'web', 'index.html'), 'utf8');
  const out = [];
  for (const m of html.matchAll(/<script\s+src="([^"]+)"/g)) {
    const src = m[1];
    if (src.includes('node_modules')) continue;
    out.push(src.startsWith('/') ? src.slice(1) : path.posix.join('web', src));
  }
  return out;
}
