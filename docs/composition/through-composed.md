# Write a continuous passage

Use when the music should unfold through its full span without automatically
restarting a short phrase. A passage can be an eight-bar melody, a bridge, a solo,
or an entire piece. Familiar motives and deliberate local ostinatos remain useful.

Start with the entry state, an emotional or harmonic destination and a time budget.
Plan two or three meaningful arrivals rather than forcing a verse–chorus template.
Decide which idea connects the beginning and ending: contour, rhythm, interval,
common tone, register or an answering gesture.

1. Trace a phrase arc across the whole assigned span, including breaths and rests.
   Let fragments return in changed contexts; do not substitute constant novelty
   for coherence or constant busy notes for forward motion.
2. For each instrument, author the complete line and then a separate expression
   pass. Give long notes, silences and transitions as much intent as fast figures.
3. Coordinate harmony, bass and melody at arrivals. Prepare unfamiliar golden
   suspensions and give them audible destinations. Preserve the brief's tuning
   and the approved motif's identity where protected.
4. Support the lead with calm timbre, reasonable register and a measured mix.
   Maintain a singable contour and room around emphasized unfamiliar pitches.
5. Check the entry, internal joins and final release in their ensemble context.

In current `.sm`, an inline part shorter than its section is automatically tiled.
To write one continuous section today, supply the complete line, including written
rests, through its whole declared length. A `form:` block containing one placement
is sufficient for a whole-piece node; there is no `through_composed=true` directive.
The proposed future writing policy will reject accidental under-length material.

This eight-bar technical example has one piano part and one placed section; its
written line lasts all eight bars. It demonstrates span accounting, not a finished
song, a supported new syntax, or a listening-approved melody.

```sm
song "Continuous span study" 80 4/4 C seed=25 tail=2
chords Cmaj7 Am7 Fmaj7 G7 Em7 A7 Dm7 Cmaj7
inst keys=keys/still
mix keys -8
unfolding = {keys: {notes: "=p e2 g4 r4 | a4 g e2 | f2 a4 g4 | d2 r4 g4 | =mp b4 g e4 r4 | a2 g4 e4 | f4 e d2 | =p e2 c2"}, dyn: "p"}
form:
  unfolding 8
```

For a long piece, one visible continuous node can still hold named rehearsal
markers and local writing regions. Those aid navigation and AI context without
creating executable repetition. Keep a larger arc summary available when working
on a small region. A new occurrence inside an outer repeat must be composed and
saved in advance; it is not fresh improvisation on every playback.

Review both short contextual excerpts and the uninterrupted arc. Technical checks
prove length, pitch validity and audio properties; the listener judges phrasing,
memorability, pacing and whether the piece earns its arrivals.
