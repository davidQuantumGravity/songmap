# Bass and drum palette

42 editable auditions and groove starters. Open [the listening page](index.html); instrument choices, installation,
licenses and performance guidance are in [the palette guide](../../docs/BASS_DRUM_PALETTE.md).

`bass/` contains recorded electric, plucked/bowed acoustic and electronic bass auditions. `kits/` compares four AVL
setups, a studio alternate-take hybrid and hand percussion. `electronic/` demonstrates eight kick/snare/hat sets.
`templates/` contains eight sixteen-bar arrangements to copy and develop.

Rebuild audio after editing scores with `python tools/rhythm_palette.py --render --gallery --audit`.
Add `--prepare` only to regenerate the original starter scores. Render outputs stay under `renders/`.
