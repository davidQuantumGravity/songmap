# Re-scoring the three Oct-13 videos

**Goal:** replace the loop-based soundtracks with **through-composed scores** that follow what happens on screen. Each video keeps its existing themes (the original `m1`–`m4` motifs and chord loops), but the music now develops, orchestrates and *reacts*:
- reveals land on hits;
- lists build note by note;
- caveats get quieter, not louder;
- each act has its own instrumental color.

The scene-by-scene facts (frames, hit points, tone) are in [SCENE_TIMELINES.md](SCENE_TIMELINES.md). This document is the composer's plan built on them.

## 1. What changes, in one table

| | Original scores | Re-scores |
|---|---|---|
| Form | Loop of 4 chords × sections that switch parts on/off | Through-composed: harmony, register and orchestration follow the story; themes recur in new forms |
| Sync | Impacts on flashes only | Every reveal, counter landing, list item and twist is a cue (`cue x=f####`) with a chosen musical device |
| Instruments | 6 synth parts for everything | A palette per act (hardware = analog synths + taiko; simulation = mallets + strings; verification = warm piano + resolved harmony) |
| Expression | Flat velocities, grid timing | Dynamics arcs per section, accents on hits, humanized feel per part, articulations |
| Caveats / honesty beats | Played under full drums | Scored with *less*: thin texture, unresolved harmony, solo instrument |
| Climaxes | Biggest numbers land mid-section with no hit | The single biggest moment of each video gets the single biggest musical moment: riser, stop-time or impact, a key or harmonic arrival, a full tutti |

## 2. Shared musical language (across all three videos)

These are recurring devices, so the weekly series sounds like one composer.

| Device | Musical form | Used on |
|---|---|---|
| **Theme** (per video) | The original `m1`–`m4`, developed with transforms: `:aug` for grandeur, `:frag=1` for questions, `:inv` for "mirrors", `:t+1` for lifts, `:dyn=` for retellings | Throughout |
| **"Verified" cadence** (green) | sus4 → major-3rd resolution (`[0,3,4]/2 [0,#2,4]/2_`), a Picardy lift inside the minor key; soft bell + warm pad; no drums | A: CLEAN, NET FORCE (0,0,0). B: "Every claim still gets checked". C: "= Net ≈ −1.9 nC", the ✓ line |
| **"Caveat" gesture** (red) | Texture drops to 1–2 instruments; falling line ending on the 2nd (`=p 4/2_ 3/4 2/8 1 \| 1/1`), unresolved sus2 underneath; bass out; long reverb | A: the thrust disclaimer. B: the NEGATIVE stamp, "Passing tests ≠ validated physics". C: "Not thrust", HONEST LIMITS |
| **Counter = gesture** | The music *counts*: a rising arpeggio, riser or note cloud that **lands on the counter's landing frame**, not its start | Every counter (167, 2.87 M, 135, 970 M, 64, ~180,000×) |
| **Lists = additive builds** | One new note, chord tone or instrument per list item, at the list's own cadence; resolve on the last item | A: the fixes ×5, feature cuts ×6. B: goals ×5, rules ×4, chips. C: matrix rows, highlight boxes, limits |
| **Lattice ostinato** (A ↔ C) | A minimalist 16th-note mallet/guitar figure derived from C's `m1` degrees: `0/16 2 4 2 4 5 4 2 0 2 4 2 4 7 5 4`, in deg mode so it fits D minor (A) or A minor (C). Density follows the visuals (`:thin=0.25…1`) | A: the Fields act. C: the whole movie act |
| **Act colors → orchestration** | Amber (hardware): analog bass, plucks, taiko, brass. Cyan (simulation): mallets, glassy pads, arps. Green (verified): felt piano, strings, major color. Red (problem): glitch percussion, wavefolded synths, b2 clusters. Violet: B's swarm synths, C's dark low strings | Per act |

**Two constraints we keep:**
- **120 BPM.** All three videos are cut on the 60-frame bar grid. Calm passages use *half-time feel* (kick and snare at 60 BPM, harmony every 2 bars), not a slower tempo.
- **Start at frame 0.** The background pulse is locked to frame 0 and to the beat.

## 3. Video B: "The Swarm" (2:03), first to re-score

It needs the fewest new instruments, so it proves the pipeline. **Concept: a machine that becomes a choir.** The swarm starts as one terminal pulse and grows one voice at a time. In the reflection, the human writing the guardrails (piano and strings) is heard over the quiet machine.

| Bars | Scene | Musical treatment |
|---|---|---|
| 0–4 | Terminal | Solo pulse: muted pluck on 8ths, a filter opening slowly (`auto cutoff 400>1800`). Each terminal line (every 24 f, off-grid) gets a soft typing tick at its exact frame (`!ticks@f40` …). The last line, "spawn subagents --until-done" (f175), triggers a 1-bar riser |
| 4–6 | **THE SWARM** drop | Impact + full kick, sub bass, `m1` stated by lead and pad in octaves at `=f` |
| 6–16 | Five goals | **One layer per goal card** on its downbeat: VI = pad, MT = pluck arp, PK = bell counter-line (`m3:frag=1`), YL = lead `m2`, VI = everything + open hats. Each card's hours counter lands at +56 f, where the arp hits a high accent (`^`). Section starts at **b6**, not b8 |
| 16–18 | "who is actually doing the work?" | Stop: drums out. Unresolved Cmaj7 → D (bVI → bVII) and a held breath |
| 18–21 | Agents: 135 | Impact. **A 135-note cloud** of tiny blips (`!cloud n=135` from f1085 to f1145), scattered in pitch and pan: the agents spawning, ending exactly on the counter landing (b19:1.33) |
| 21–24 | 7 THREADS | `m1:canon=7@16`: seven staggered entries of the theme, matching the 7 lanes |
| 24–28 | Receipts | Five stamp hits on their frames: ACCEPTED and AGREE = bright major stabs; FROZEN = a held cluster; HOLD = sus4; **NEGATIVE (f1575) = a low minor-2nd stab, then 2 beats of silence** (caveat gesture) |
| 28–34 | Rules of the swarm | Rules arrive every 3 beats, so the lead plays a **3-against-4 hemiola** (dotted-half motif). Rule 04 "≠" gets a dissonant b5 in the pad that resolves only in bar 33 |
| 34–36 | "SO WHAT CAME OUT?" | Snare-roll crescendo, then a stop on the last 8th |
| 36–40 | PhD portfolio ×90 | Impact. The arp pulses in **half notes** with the tile ripple, then 16ths. Five list items = five rising bell notes |
| 40–43 | Quantum Espresso | Three quarter-note-triplet stabs on QUANTUM / ESPRESSO / INSTALLED (f2400/2410/2420). The bass locks in, methodical |
| 43–46 | Triality | Three voices (I, II, III) rotate a 3-note ostinato; the kick is featured on each beat with the node pulse; the harmony shifts to Phrygian (F natural): mystery |
| 46–49 | Media platform | 4 chips = 4 instrument entries; riser into b49 |
| 49–52 | **Cumulative** (climax) | Riser lands on 970 M (f3005), then **three stacked impacts** rising in pitch on 970 M / 1,130 / 135 (f3005 / f3025 / f3035). Full tutti, `m1:aug` in the lead, `=ff` (the only ff in the video) |
| 52–56 | Reflection | **Drums out.** Felt piano plays `m1` slowly (`:aug`, `=mp`) with strings; the swarm pulse continues very quietly underneath. "Every claim still gets checked" (b54) gets the *verified* cadence |
| 56–58 | Summary | Flash. Drums back at half energy: `m2` + `m3` in counterpoint |
| 58–61.5 | End card | "THE SWARM": `m4` cadence resolving to E major (Picardy), pad tail, impact |

```
# excerpt — examples/rescore/the_swarm.sm (draft)
song "The Swarm (rescore)" 120 4/4 Em fps=30 mood=techno tail=3 seed=21 video=WeekSwarm:3690
inst blips=pluck(decay=.08,cutoff=5000) bell=bell/glass keys=keys/felt_piano strings=strings/legato
cue title=f240 cards=f360 who=f968 spawn=f1085 landed=f1145 negative=f1575 big=f3005 big2=f3025 big3=f3035
terminal   4 | arp:mute8(cutoff=400) fx:ticks dyn=pp<mp                     | !riser:1@4
title      2 | drums:four_floor bass:sub lead:m1:dyn=f pad:warm             | !impact
goals     10 | like=title drums:full+fill arp:up bell:m3:frag=1 lead:m2 dyn=mf<f
who        2 | pad:dark -drums -bass chords="Cmaj7:1 D:1"                  | !stop:2b@+1:3
agents     3 | drums:full bass:8ths pad:warm                               | !impact !cloud@cue:spawn(to=cue:landed,n=135,part=blips)
threads    3 | like=agents lead:m1:canon=7@16
receipts   4 | like=agents -lead                                           | !hit@f1475(sound=stab) !hit@f1500(sound=stab) !hit@f1525(sound=cluster) !hit@f1550(sound=sus) !hit@cue:negative(sound=low_b2) !stop:2b@cue:negative
...
cumulative 3 | drums:full+fill+hats16 bass:8ths lead:m1:aug pad:warm dyn=ff | !riser:2@cue:big !impact@cue:big !impact@cue:big2(size=l) !impact@cue:big3(size=xl)
reflection 4 | keys:m1:aug:dyn=mp strings:sustain(dyn=p) arp:mute8(dyn=pp) | !hit@54(sound=verified)
qa contrast=who<goals:8,reflection<cumulative:9 hits_audible=on
```

## 4. Video A: "Bench / Fields / Thruster" (2:31)

**Concept: three acts, three instruments of truth.**
- **Bench** (amber): the hardware is the band. Analog bass, plucky synths, and the oscilloscope as a percussion part.
- **Fields** (cyan): the simulation is a music box of fields. Mallets, strings and the lattice ostinato, in half-time.
- **Thruster** (amber, maximum): the cinematic finale, with taiko, brass and the theme at full height, then the **honest hedge**.

| Bars | Scene | Musical treatment |
|---|---|---|
| 0–4 | Cold open | Dark pad + sub. **The Scope is a percussion part:** zaps on the 6 scope/word quarter notes (f120–195), not 8ths. "ONE WEEK." (b1) gets a low hit. `m1:frag=1` on solo felt piano |
| 4–7 | 20 kV drop | Impact + full kit. The 12 scope pulses (f240–405) = 12 quarter-note zaps riding the groove. Spec slams on their frames (f262, f285) |
| 7–13 | Chain / testing | Half-time. **The red strike-through (b8) = a descending tape-stop on the BEFORE chord**, then the NOW chain enters in a new key color (bVI). 5 kV / 200 Hz / AIR = three half-note-triplet plucks |
| 13–16 | The problem | Glitch kit (wavefolded hats, bit-crushed snare), detuned pad, b2 cluster. "ADS1115 not found" stutters in 16th-note ratchets. Red chips on quarters = four dissonant stabs |
| 16–19 | Teardown | Drum fill → the rebuild. The AFTER photo (b17) gets a clean major-chord arrival |
| 19–22 | Fixes ×5 | **Half-note triplets (one per item every 20 f)**: five rising pluck notes building a chord; the last item resolves |
| 22–28 | Dashboard + feature cuts | Full groove, `m1` in the lead. **Six cuts every half bar = six stabs**, alternating cyan (bell) and amber (brass) |
| 28–30 | **CLEAN.** | One beat of stop-time before b28, then the *verified* cadence (D sus4 → D major) + soft impact. Counter 167 lands at b29:2 on a bright bell |
| 30–32 | Lab notebook | Light groove, arp counting up to the 980,946 landing |
| 32–34 | **Jeremiah** | **Drums out.** Felt piano + warm pad play `m2` in F major (relative major), warm and personal |
| 34–36 | "meanwhile, in simulation…" | Only typing ticks following the Typer, plus a reversed cymbal into b36 |
| 36–42 | THE FIELDS | Impact. **Lattice ostinato** on marimba (D minor), strings sustain, half-time. "FIELDS / WRAP / AROUND" = three low string + timpani hits on beats (+5 f) |
| 42–45 | 2.87 M sites | The DotField zoom = **the lattice densifies**: `:thin=0.25 → 0.5 → 1` across 3 bars, then 32nd-note doubling. Riser ending on the counter landing (f2650) + bell cluster |
| 45–48 | Lattice movie | Three counters = three ascending bell notes (f2760, f2785, f2810) |
| 48–52 | **NET FORCE (0, 0, 0)** | "then the adversarial audit:": the texture freezes. Silence on f2915, then the *verified* cadence on "(0, 0, 0)" (f2930): sober, no impact, a single low sub-drop |
| 52–54 | "NOW, THE BIG ONE." | Pedal tone + snare roll, crescendo `p<ff` into b54. "THE BIG ONE." (f3158) = a held breath (stop on 52:3.5) |
| 54–57 | THRUSTER | Flash: taiko + braam + full kit, `m1` in brass `=f`. BUILD / CHARGE / TEST on **the 8th offbeats** (f3322/3337/3352) = three marcato stabs |
| 57–60 | Gauge | The needle crosses 300 MV/m at ≈f3462 (b57:3.75): riser ending there, then **modulate up a whole step (D minor → E minor)** for the rest of the act |
| 60–63 | 15.9 MILLION | The theme an octave up; counter landing (b61:1.75) = impact |
| 63–66 | Corona dock | **Pull back** to half-time and a pad for 3 bars: the calm before the biggest moment |
| 66–68 | **9.4–15.3 N*** | 2-bar riser into b66, **the biggest impact of the video**, full tutti, `m1:aug` `=ff` (the video's only ff); T/W at b66:4.25 = a second hit |
| 67.6–70 | Disclaimer → NEXT | **Caveat gesture:** drums out at b67:3, solo piano falling line over sus2, bass out. "NEXT ▶ CHARGED COUPON TEST" (b68.75) = a gentle bass pulse returns: forward motion, not triumph |
| 70–72 | Summary | Three recap columns (12 f apart) = three instrument entries: amber brass, cyan mallets, green strings |
| 72–75.5 | ONWARD. | `m4` resolving to D major (Picardy), the lattice faintly underneath, fade |

## 5. Video C: "Inside the 56 Movies" (5:03)

**Concept: chamber music for a lattice.** A small acoustic-leaning ensemble (felt piano, nylon guitar, marimba, cello and strings, soft brushes, warm sub) plays a **theme and variations**. Each movie is a variation of the lattice ostinato and `m1`, and the *science is in the music*.

| Bars | Scene | Musical treatment |
|---|---|---|
| 0–6 | Title | Solo piano: `m1` at `=pp`. "56 MOVIES" (b1:1.75) = a soft low bell + cello pizz |
| 6–14 | Geometry | **Each layer = an instrument entering** on its frame: Al backing = sub; Kapton = pad; Al pads = marimba lattice (`:thin=0.25`); traps = high violet string harmonic. Coverage 25 → 50 → 75 → 100% (every 3 beats) = **lattice density 25 → 50 → 75 → 100%** (`:thin=`); "pads overhang" = a gentle dissonance |
| 14–18 | Charging recipe | RAMP = crescendo (`dyn=p<mf`); HOLD = sustained chord; **disconnect (b15:2.33) = everything cuts except the reverb tail**; FLOAT = a single held pad note, the charge "staying put" |
| 18–22 | Experiment grid | 4 matrix rows on beats = 4 pizzicato entries; "64" lands (b19:4.5) = a marimba chord |
| 22–28 | How to read | One instrument per highlight box per bar (cyan, amber, green, violet colors) |
| 28–36 | M1: 100% coverage | Flash. Full lattice + light brushes in half-time + `m1` on guitar: the main statement |
| 36–44 | M2: one cell close-up | The camera zooms in, so the theme goes **low and slow** (`m1:aug:oct-1` on cello). "≈55,000 Pa" = a full chord; **"≈2 Pa" = one quiet high note** |
| 44–52 | M3: where the charge sits | **Call and response:** the piano asks (`m1`); "Kapton answers back" = cello answers (`m1:inv`); "The plate mirrors it" = the strings play the **mirror** (`m1:inv:t+2`) |
| 52–60 | M4: −100 V | Five times less voltage: **the same music at one-fifth the dynamics** (`dyn=pp`), same notes. "Traps still fill ≈183 nC" = the lattice keeps full density |
| 60–66 | M5+6 side by side | Two copies of the lattice, **panned hard left (−100 V, soft) and right (−500 V, loud)**: the same pattern at two levels |
| 66–78 | M7–10 coverage | The 4 tiles pop on beats (b66) = 4 lattice layers at 25/50/75/100% density stacking up. Riser into b78 ("next chart") |
| 78–84 | **Coverage chart** | Four bars = four rising notes: 71.6 → 143.5 → 183.3 → **183.3: the fourth note repeats the third** (the plateau), over a deceptive cadence (V → bVI): the gentle deflation |
| 84–92 | M11: harder contact | **Key color darkens to A Phrygian** (Bb). Low string tremolo; the camera push-in = a slow filter close and crescendo. "hundred-million-fold less" = drop to near silence |
| 92–100 | M12: 5× edge boost | Suspense pedal (A + Bb), heartbeat kick in half-time, static |
| 100–106 | **~180,000×** | Riser from b100 → **the biggest hit of the video** on f6070 (b101:1.75): full ensemble + timpani, `m1:aug` in strings `=ff` |
| 106–114 | Charge bookkeeping | Flash; lift to **C major**. "− Pads" = low minor chord, "+ Plate" = high major chord, **"= Net ≈ −1.9 nC" = the two collapse into a single octave unison**: nearly zero net |
| 114–122 | Forces: tug of war | Two lines in **contrary motion** (rising cello vs falling piano) that meet on a unison: the forces cancel. **"Not thrust" (b117) = caveat gesture** |
| 122–128 | Grounded vs floating | The **same phrase twice**, on piano (GROUNDED, f7340) then guitar (FLOATING, f7360): "nothing changes" |
| 128–138 | Honest limits | Solo cello + piano. Four ✗ lines, one per bar = four falling minor-2nd sighs. **✓ (b132:3) = the verified cadence**, then 5 bars of warm, resolved hold |
| 138–146 | Next | The lattice returns, building upward; light brushes; `m3` (the rising theme) in strings: hopeful |
| 146–151.5 | **THE CONTACT / DECIDES.** | Flash. Two chords on the two words: **Dm (iv) on "THE CONTACT" (b146:1.75) → A major (Picardy I) on "DECIDES." (b146:2.25)**, ring out and fade |

```
# excerpt — examples/rescore/deepdive.sm (draft)
song "Inside the 56 Movies (rescore)" 120 4/4 Am fps=30 mood=documentary tail=4 seed=56 video=DeepDive:9090
inst keys=keys/felt_piano gtr=string_pluck/nylon mallet=marimba/soft cello=bowed/cello strings=strings/chamber
kit  kick=kick(tune=44,decay=.6,click=.1) snare=brushes hat=hat(decay=.03)
groove swing=.5 hum=6,4,.04
feel keys high_loud=.4 arch=.5
motif lattice deg oct=4 "0/16 2 4 2 4 5 4 2 0 2 4 2 4 7 5 4"
motif caveat  deg oct=4 "=p 4/2_ 3/4 2/8 1 | 1/1"
cue disconnect=f920 thesis=f6070 net=f6540 contact=f8770 decides=f8780
title     6 | keys:m1:dyn=pp pad:air                                         | !hit@f70(sound=low_bell)
geometry  8 | like=title bass:sub mallet:lattice dyn=pp<mp auto=mallet.thin:.25@f500,.5@f575,.75@f620,1@f665   # step automation = coverage %
recipe    4 | pad:warm keys:sustain dyn=p<mf                                  | !drop@cue:disconnect(keep=[returns])
...
m3_mirror 8 | mallet:lattice keys:m1 cello:m1:inv strings:m1:inv:t+2 drums:half(brush=on)
m4_100v   8 | like=m3_mirror dyn=pp
barrier  16 | key=A_phrygian strings:tremolo(dyn=p) cello:pedal drums:half_kick auto=strings.cutoff:3000>700 | !drop@+4:3(bars=1)
result    6 | strings:m1:aug(dyn=ff) drums:full timpani:roll                 | !riser:1@cue:thesis !impact@cue:thesis(size=xl)
outro     4 | keys:sustain strings:sustain                                      | !hit@cue:contact(sound=chord,chord=Dm) !hit@cue:decides(sound=chord,chord=A,dyn=f)
qa contrast=barrier<result:8,limits<findings:6 hits_audible=on
```

## 6. How we do it: the production steps

### Engine prerequisites (from [ROADMAP.md](../ROADMAP.md))
- Phases 1–3: parser with cues and positions, performance layer, QA. These are required.
- Phase 4 mastering with `preserve_contrast`. Without it, the drama gets squashed.
- New instruments, by first video that needs them:

| Video | Needs | Stand-ins until then |
|---|---|---|
| B | `bell`, `strings` (ensemble) | `epiano` / `pad` |
| A | + `marimba`, `taiko` / `cinematic_drum`, `brass` / `braam`, `timpani`, glitch FX (`fold`/crush on hats), `tape_stop` | |
| C | + `bowed/cello`, `brushes`, `sub_drop`, a `strings` tremolo articulation | |

### Per video
1. **Spot.**
   - Turn [SCENE_TIMELINES.md](SCENE_TIMELINES.md) into `cue` lines (Phase 8's `songmap cues-from-video` automates this from the TSX source).
   - Confirm section boundaries: B `goals` from b6; C `limits` from b128; A's `thruster+8` riser re-aimed at b66.
2. **Compose.** Write the `.sm` file: the tables above, section by section, using the shared devices of §2. Keep themes recognizable; develop them with transforms rather than new tunes.
3. **Check.** `songmap check`: names, bars, and cue alignment (it warns when a cue snaps more than 1 frame).
4. **Render and self-review** with `songmap render --qa`:
   - Contrast rules: caveats ≥ 6 dB under their preceding peak; the reflection or limits sections ≥ 6 dB under the climax.
   - `hits_audible` on every cue event.
   - Band balance per act.
5. **Mux for review** without re-rendering the video:
   ```bash
   ffmpeg -i Week_Oct13_The_Swarm.mp4 -i build/the_swarm/song.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest Week_Oct13_The_Swarm_v3.mp4
   ```
6. **Listen and iterate** in Studio's song view ([GUI.md](GUI.md) §3.5), with the video synced to the audio and cues draggable. Feedback in musical terms ("the 135 cloud is too busy") becomes one-line edits.
7. **Deliver.** Copy the final `song.wav` into the Remotion project's `public/` (`track_A.wav`, `track_B.wav`, `track_C.wav`) for future video renders, and keep `cues.json` next to it for the Phase 8 Remotion helper.

### Optional picture nudges (small edits that make the score land better)
- A: shift BUILD / CHARGE / TEST by +8 f onto beats, or keep them as offbeat stabs (the plan above keeps them).
- B: quantize the receipt stamps to 8ths (f1470, 1500, 1530, 1560, 1590) and the rules to 2-beat spacing. Or keep the off-grid cadences as syncopation: both work.
- C: none needed. It's already bar-locked.

### Order and effort
1. **B** first (about 1 session once Phases 1–3 exist): electronic, needs 2 new instruments.
2. **A** next (1–2 sessions): needs the cinematic kit.
3. **C** last (2 sessions): longest, needs the chamber instruments.

Each produces a v3 MP4 for review.
