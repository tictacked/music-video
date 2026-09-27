// =============================================================================
// timeline.js -- the REELS (director) + the assembler. Each painter registers their own shots from their own scene file:
//
//     DT.reel('verse1', [
//       { id: 'verse1_title', scene: 'verse1_title', at: 'B7' },
//       { id: 'verse1_window', scene: 'verse1_window', at: 'B8', trans: { type: 'shatter', dur: 0.3, at: [0.6, 0.4] } },
//     ]);
//
// Rules: the FIRST shot of a reel must start at the reel's own `at` (the assembler snaps it there and warns if you
// differ); every other shot must start inside [reel start, next reel start). Shot ids are globally unique: prefix them
// with the reel id. The first shot's `trans` is the transition INTO your reel. A reel that has registered nothing yet
// shows the animatic card (and is FATAL in strict mode).
// Anchors: B<n> = bar n (beat0 + (4n + barOffset) beats, from song/timing.json), S<n> section, END, +/-Nb beats,
// +/-NB bars, +/-Ns, |b |B |h snaps. NO LYRICS: DT.timing.lines is empty on purpose (vox = phrase TIMES).
// =============================================================================
(function () {
  const DT = window.DT;
  // the film in reels (STORYBOARD.md), on the song's own sections: {id, at (an anchor), owner, rp (the RP messages the
  // painter reads, '##### [n]'), what (the reel in one line)}. The placeholder shows the testcard (scenes/reel1.js).
  DT.REELS = [
    { id: 'reel1', at: 0, owner: 'director', rp: '', what: 'placeholder: the testcard, until the storyboard exists' },
  ];
  const reg = {};
  DT.reel = function (id, shots) { reg[id] = shots; };
  DT.assembleTimeline = function () {
    const out = [];
    DT.REELS.forEach((R, i) => {
      const t0 = DT.anchor(R.at), t1 = i + 1 < DT.REELS.length ? DT.anchor(DT.REELS[i + 1].at) : DT.timing.duration;
      R.start = t0; R.end = t1;
      const shots = reg[R.id];
      if (!shots || !shots.length) { out.push({ id: R.id + '_todo', scene: '__missing', at: t0, params: { reel: R.id } }); return; }
      shots.forEach((s, k) => {
        const t = DT.anchor(s.at);
        if (k === 0 && Math.abs(t - t0) > 1 / 48) console.warn(`reel ${R.id}: first shot ${s.id} starts at ${t.toFixed(3)}, reel starts at ${t0.toFixed(3)} -- snapped`);
        if (k > 0 && (t < t0 - 1e-6 || t >= t1 - 1e-6)) console.warn(`reel ${R.id}: shot ${s.id} at ${t.toFixed(3)} is outside the reel [${t0.toFixed(3)}, ${t1.toFixed(3)})`);
        out.push({ ...s, reel: R.id, at: k === 0 ? t0 : s.at });
      });
    });
    out.sort((a, b) => DT.anchor(a.at) - DT.anchor(b.at));
    return out;
  };
})();
