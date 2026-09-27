#!/bin/sh
# keeper.sh -- hold render slots so the crew shares fewer of them (machine etiquette: while a local video model or any
# other heavy job owns the GPU and RAM, the painters get ONE slot). Usage: sh render/keeper.sh 1 2   (default: slot 1)
# Runs while notes/.render-slots/KEEP exists: claims each slotN.lock only when it's free, then refreshes it every 20 s
# so it never goes stale (stills.mjs/render.mjs reclaim locks older than 6 min). Stop: rm notes/.render-slots/KEEP.
cd "$(dirname "$0")/.."
D=notes/.render-slots
SLOTS="${*:-1}"
mkdir -p $D; touch $D/KEEP
while [ -f $D/KEEP ]; do
  for n in $SLOTS; do
    L=$D/slot$n.lock
    if [ ! -f $L ]; then (set -C; echo keeper > $L) 2>/dev/null; fi
    if [ -f $L ] && [ "$(cat $L 2>/dev/null)" = "keeper" ]; then touch $L; fi
  done
  sleep 20
done
for n in $SLOTS; do L=$D/slot$n.lock; [ "$(cat $L 2>/dev/null)" = "keeper" ] && rm -f $L; done
echo "keeper stopped"
