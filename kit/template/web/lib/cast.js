// =============================================================================
// cast.js -- the film's model sheet as data: which picture plays which moment (ASSETS.md is the long version).
// Ids are '<job>/<seed>'; scenes call DT.cast.pick('hero_full') -> 'cut:hero_full/1' (a cut-out, alpha) or
// 'gen:pl_street/2' (a whole picture). Jobs come from tools/jobs/*.json (tools/gen.py).
//   cut out: everything that stands on flat MINT (the cast, faces, props)
//   whole:   jobs starting with film.json nocutPrefixes (plates pl_, the video model's first frames ff_, i2i tests) and
//            the jobs in film.json whole (scene pictures painted on their own ground). ONE list, shared with tools/cutout.py.
// CLIPS: DT.cast.CLIPS (K.s.use(name) plays one; a clip is 124 frames = 5.17 s unless noted).
// =============================================================================
(function () {
  const DT = window.DT;
  const FILM = window.DT_FILM || {};
  const PICKS = {
    // the director's picks (jobs without a pick return their first seed); painters: ask before changing
    // e.g. hero_prop: 3,   // seed 3: seeds 1-2 paint the prop in the rival's colour (a colour = a person)
  };
  const WHOLE = new Set(FILM.whole || []);
  const NOCUT = FILM.nocutPrefixes || ['pl_', 'ff_', 'i2i_', 'sweep', 'test'];
  const job = (k) => k.split('/')[0];
  const cutJob = (j) => !NOCUT.some((p) => j.startsWith(p)) && !WHOLE.has(j);
  const CLIPS = {
    // name: ['what happens', 'where it belongs'] -- filled as the image-to-video clips land (ASSETS.md)
  };
  DT.cast = {
    PICKS, CLIPS, WHOLE,
    init() {},
    // pick() / all() only return pictures that EXIST: a cut job's picture counts once its cut-out is in the manifest
    pick(id, o = {}) {
      const A = window.DT_ASSETS || {};
      const ok = (k) => !!A[k] && (o.raw || !cutJob(job(k)) || !!A[k].cut);
      const kind = (k) => (!o.raw && cutJob(job(k)) ? 'cut' : 'gen');
      const seed = o.seed || PICKS[id];
      if (typeof seed === 'string' && seed.includes('/')) { if (ok(seed)) return `${kind(seed)}:${seed}`; }
      else if (seed) { const k = `${id}/${seed}`; if (ok(k)) return `${kind(k)}:${k}`; if (o.seed) return null; }
      const keys = Object.keys(A).filter((k) => k.startsWith(id + '/') && ok(k)).sort();
      return keys.length ? `${kind(keys[0])}:${keys[0]}` : null;
    },
    all(id, o = {}) {
      const A = window.DT_ASSETS || {};
      const ok = (k) => !!A[k] && (o.raw || !cutJob(job(k)) || !!A[k].cut);
      return Object.keys(A).filter((k) => k.startsWith(id + '/') && ok(k)).sort().map((k) => `${!o.raw && cutJob(job(k)) ? 'cut' : 'gen'}:${k}`);
    },
    meta(key) { const k = key.slice(key.indexOf(':') + 1); return (window.DT_ASSETS || {})[k] || null; },
  };
})();
