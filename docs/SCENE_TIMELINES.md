# Scene timelines for the three Oct-13 videos (scoring reference)

Extracted from the Remotion source (`weekly_video_source.tar.gz` → `proj/src/VideoA|B|C.tsx`, `lib.tsx`) on 2026-10-20.

**Conventions.** 30 fps, 120 BPM, so 1 bar = 60 frames and 1 beat = 15 frames. `b` = bar counted from 0 (b4.25 = frame 255).
- **Hit points** are the frames where something lands. For counters that is the *landing* frame, not the start.
- **Event semantics:** a riser ends at its `at`; an impact starts at its `at`.

**Shared layer.** `Background` pulses on every beat (`beatPulse`: on `f % 15 == 0`, decay 6 frames), locked to frame 0, so the music must start at frame 0. In A and B the pulse runs at intensity 0.3 until f240, then 1.0: a built-in visual "drop" at b4. In C it stays at 0.5.

**VideoA gotcha:** everything after Act 1 sits inside `<Sequence from={840}>`, so the code's local `at` values are +840. All frames below are absolute.

---

## Video A: WeekBench "Bench / Fields / Thruster" (4530 f = 75.5 bars, D minor)

**Theme colours:** amber #ffb23d (bench, thruster, emphasis) · cyan #29d3ff (simulation, fields, UI) · green #3dffa2 (fixed, clean, verified) · red #ff3b5c (problem).
**White flashes:** 240, 780, 960, 2160, 3240, 4200, 4320. **Green flash:** 1680.

| Bars | Frames | Scene | On screen / hit points | Tone |
|---|---|---|---|---|
| 0–4 | 0–240 | Cold open | Green `Scope` trace. Typer "WEEK OF OCT 13, 2026" f12. Slam "ONE WEEK." f60 (b1). WordReveal "THE BENCH. THE FIELDS. THE THRUSTER." words at 122/136/150/164/178/192. **Scope pulses on quarters at 120–195**, matching the words | Dark lab ambience → title statement |
| 4–7 | 240–420 | Pulser specs | Flash + Slam **"20 kV"** f240. "<10 ns RISE" f262. "UP TO 1 kHz" f285. Scope keeps **12 quarter pulses 240–405** | First drop: energetic, confident |
| 7–10 | 420–600 | Signal chain | "NEW SIGNAL CHAIN" f420. BEFORE chain f440. **Red strike-through f480–495 (b8)**. NOW chain f490 (amber) | Before/after, matter-of-fact |
| 10–13 | 600–780 | What we tested | "5 kV" f620, "200 Hz" f640, "AIR" f660 (half-note triplets). Chips on quarters f690/705/720 | Methodical |
| 13–16 | 780–960 | The problem | Flash, red "THE PROBLEM:", wiring photo. Glitch **"ADS1115 not found at 0x48"** f815. Red chips on quarters f850–895 | Tension, error |
| 16–19 | 960–1140 | Teardown | Flash, "DAQ: TORN DOWN & REBUILT". BEFORE photo f970. **AFTER photo f1020 (b17)** | Turnaround |
| 19–22 | 1140–1320 | The fixes | Green "THE FIXES". **5 list items every 20 f** (1160–1240, triplet feel), then hold | List: rising, resolving |
| 22–25 | 1320–1500 | Dashboard hero | "REAL-TIME DAQ VIEWER", screenshot. Chips on quarters f1385–1430 | Upbeat showcase |
| 25–28 | 1500–1680 | Feature cuts | **6 hard cuts, every half bar** (1500…1650) | Rhythmic montage (A's most rhythmic edit) |
| 28–30 | 1680–1800 | Clean result | **Green flash + "CLEAN."** f1680. Counter **167 lands f1755** "SOFTWARE TESTS PASSING" | Payoff, triumph |
| 30–32 | 1800–1920 | Auto lab notebook | 980,946 lands f1875; 42 lands f1870 | Stats flourish |
| 32–34 | 1920–2040 | Shout-out | "THANK YOU," **"JEREMIAH"** f1940, "…quad-eutectic solder…" | **Warm, personal** |
| 34–36 | 2045–2158 | Sim break | Typer "> meanwhile, in simulation..." | Breath, transition |
| 36–39 | 2160–2340 | THE FIELDS | Flash, Slam "THE FIELDS". Potential map f2222, "−500 V pad · 25 µm Kapton" | New chapter, scientific |
| 39–42 | 2340–2520 | Fields wrap | "FIELDS" f2345, "WRAP" f2360, "AROUND" f2375 (on beats +5 f) | Wonder |
| 42–45 | 2520–2700 | 2.87 M sites | DotField zoom build. Counter **2,869,636 lands f2650 (b44.17)** | Build → awe |
| 45–48 | 2700–2880 | Lattice movie | Counters land at f2760 (56 movies), 2785 (17.1M cells), 2810 (64 cases) | Triple cascade |
| 48–52 | 2880–3120 | Adversarial audit | "then the adversarial audit:". **"NET FORCE" f2915, "(0, 0, 0)" f2930**. "…mesh artifact. Caught, fixed, documented." | **Twist / debunk** |
| 52–54 | 3125–3238 | "Now, the big one" | "NOW," f3125. **"THE BIG ONE." f3158** | Anticipation |
| 54–55.3 | 3240–3318 | THRUSTER opener | Flash, "DIGITAL" f3240, "THRUSTER" f3250 | Act-3 drop, max energy |
| 55.3–57 | 3318–3420 | Build/Charge/Test | "BUILD." 3322, "CHARGE." 3337, "TEST." 3352 (**on the 8th off-beats**) | Mantra |
| 57–60 | 3420–3600 | Gauge | Counter 131. Needle sweeps; **crosses the 300 MV/m target ≈ f3462 (b57.7)**, settles at 368.8 f3515 | Target hit, triumph |
| 60–63 | 3600–3780 | 15.9 M sites | **15.9 MILLION lands f3670**. Chips on quarters f3670–3715 | Scale |
| 63–66 | 3780–3960 | Corona dock | "room temperature · no vacuum oven" | Calmer process |
| 66–70 | 3960–4200 | Thrust numbers | **"9.4–15.3 N*" f3960 (b66)**. **"T/W 105–171*" f4010**. Disclaimer f4055 (b67.6). "NEXT ▶ CHARGED COUPON TEST" f4125 | **Climax → honest hedge** |
| 70–72 | 4200–4320 | Summary | Flash. 3 recap columns f4202/4214/4226 (amber, cyan, green) | Resolution |
| 72–75.5 | 4320–4530 | End card | Flash, **"ONWARD."** f4330, credits f4360. Fade 4440–4520 | Hopeful closure |

**Arc:** a tension point at b13–16; payoff at b28; the Fields peak at b44 then the twist at b48.6; the overall peak b57.7 → b61 → **b66**. Breaths at b32–36 and b52–54, and a tonal step-down at b67.6.

**Where the original score misses (A):**
1. The zaps are 8ths, but the Scope and words pulse in quarters (b2–3.25 and b4–6.75). The b7 zaps land as the scope fades.
2. **CLEAN at b28 has no hit**, mid-`dashboard`.
3. The **Jeremiah shout-out plays under full drums and lead**.
4. **NET FORCE (0,0,0) at b48.6 has no hit.**
5. **"9.4–15.3 N" at b66 has no impact.** The `thruster+8` riser ends at b62 instead.
6. The disclaimer plays under the densest texture.

## Video B: WeekSwarm "The Swarm" (3690 f = 61.5 bars, E minor)

**Theme colours:** violet #a77bff (goals, swarm identity) · mint #2bf5c8 (agents, process) · pink #ff5fa2 (output, ≠, checked) · yellow #ffd84a (HOLD) · red #ff4d6a (NEGATIVE).
**Lavender flashes:** 240, 1080, 2160, 3360, 3480.

| Bars | Frames | Scene | On screen / hit points | Tone |
|---|---|---|---|---|
| 0–4 | 0–240 | Terminal | `codex goal list`. Lines at f8, 40, 64, 88, 112, 136, 175 (**every 24 f, off-grid**); "$ spawn subagents --until-done" f175 | Machine ramp-up |
| 4–6 | 240–360 | Title drop | Flash + **"THE SWARM"** f240; background to full | Drop, awe |
| 6–16 | 360–960 | Five goals | **GoalCards every 2 bars** at b6/8/10/12/14, each landing on the downbeat. Hours counters land at +56 f (f416, 536, 656, 776, 896). Card colours VI, MT, PK, YL, VI | List, driving |
| 16–18 | 960–1080 | Question | Typer "> who is actually doing the work?" | Breath |
| 18–21.17 | 1080–1270 | Agents | Flash. NameRain (80 thinkers). Counter **135 lands f1145 (b19.08)** | Scale, wonder |
| 21.17–24 | 1270–1440 | Peak parallel | **"7 THREADS" f1280**. 7 Lanes | Momentum |
| 24–28 | 1440–1680 | Receipts | "EVERY CLAIM GETS A RECEIPT". Stamps land ≈ f1475, 1500, 1525, 1550, **1575 (LINNAEUS — NEGATIVE, red)** | Rigour: hits, with a minor twist on the last |
| 28–34 | 1680–2040 | Rules | 4 rules **every 45 f (3 beats)** f1710–1845; "04 Passing tests ≠ validated physics"; then ~3 bars hold | Earnest principles |
| 34–36 | 2050–2158 | Question | Slam "SO WHAT CAME OUT?" | Break |
| 36–40 | 2160–2400 | PhD portfolio | Flash. 90 tiles ripple; **highlighted tiles pulse every half note**. List on quarters f2230–2290 | Abundance |
| 40–43 | 2400–2580 | Quantum Espresso | "QUANTUM/ESPRESSO/INSTALLED" **10 f apart (quarter-note triplets)** | Precise, methodical |
| 43–46 | 2580–2760 | Triality | Triangle **nodes pulse every beat**; "Can one 128 give three generations?" | Speculative, mysterious |
| 46–49 | 2760–2940 | Media platform | 4 chips f2810/2830/2850/2875 | Breadth |
| 49–52 | 2940–3120 | Cumulative | **970M lands f3005**, **1,130 f3025**, **135 f3035** | **Climax** |
| 52–56 | 3120–3360 | Reflection | One line per bar: "I set the goals and the guardrails." / "The swarm does the grinding." / "Every claim still gets checked." | Reflective, humane |
| 56–58 | 3360–3480 | Summary | Flash "135 AGENTS · 5 GOALS · 7 THREADS" | Recap |
| 58–61.5 | 3480–3690 | End card | Flash, "THE SWARM" f3488. Fade 3600–3680 | Closure |

**Where the original score misses (B):**
1. Goal card 01 enters at b6, but `goals` (full arrangement and riser) starts at b8.
2. The `agents+8` riser ends at b26, between stamps, not on NEGATIVE (f1575).
3. The output scenes are 4/3/3/3/3 bars, cutting against 8-bar phrases; the `output+8` riser ends at b44, where nothing happens.
4. **The climax counters (b49–50.6) have no hit.**
5. The Triality beat-pulse invites a featured kick or lead accent.

## Video C: DeepDive "Inside the 56 Movies" (9090 f = 151.5 bars, A minor)

Every boundary is on a bar line (`B(n) = n*60`).

**Theme colours:** cyan #4cc9ff (setup, explanation) · amber #ffb23d (the movies) · violet #b48cff (contact barrier) · green #3dffa2 (findings, next) · red #ff5a6e (limits).
**Flashes:** 360 (b6), 1680 (b28), 6360 (b106), 8760 (b146).
**Scene template:** heading Slam on the bar line; 3 explainer cards at about +0.5, +2.3 and +4.6 bars; slow-motion movie frames with eased camera moves; the last 2–3 bars of each 8-bar movie are visually static.

| Bars | Scene | Hit points | Tone |
|---|---|---|---|
| 0–6 | Title | **"56 MOVIES" f70 (b1.17)**. Long WordReveal from f130 | Calm invitation |
| 6–14 | Geometry | Layers every 20 f (f400–460). Top view f500. **Coverage steps 25→50→75→100% at f575, 620, 665 (every 3 beats)**; "pads now overhang" at 75% | Step-by-step build |
| 14–18 | Charging recipe | RAMP f880, HOLD f910, **red disconnect line f920–930 (b15.33)**, FLOAT f940. "Like charging a battery, then unplugging it…" | Gentle analogy |
| 18–22 | Experiment grid | Matrix rows ~every beat f1090–1132. **"64" lands f1192 (b19.87)** → "56 movies" | Combinatorial build → small hit |
| 22–28 | How to read | 4 highlight boxes **once per bar** (b22.33…25.33). Rows note at b26.17 | Tutorial |
| 28–36 | M1: 100% coverage | Flash. Cards at b28.5, b30.33, b32.67 | Calm observation |
| 36–44 | M2: one cell close-up | "≈55,000 Pa" (amber) vs **"≈2 Pa" (red, b40.5)** | Close-up contrast |
| 44–52 | M3: where charge sits | "Pads + traps: negative" / **"Kapton answers back"** / "The plate mirrors it" | Call and response |
| 52–60 | M4: −100 V | "But traps still fill ≈183 nC" / "the difference is the metal" | Comparison, question |
| 60–66 | M5+6 side by side | b61 "Same pattern, same trapped dose…" | Quiet answer |
| 66–78 | M7–10 coverage | **4 tiles pop on beats b66–66.75**. Cards b68, b71.5, b74.67 ("Watch the payoff… next chart") | Expansion, curiosity |
| 78–84 | Coverage chart | Bars finish f4720/4738/4756/4774: 71.6 → 143.5 → 183.3 → **183.3 (plateau)** | Result: slightly deflating |
| 84–92 | M11: harder contact | Camera pushes in. "Read the color bar! … a hundred-million-fold less". "Lesson: always check the scale" | Twist: darker, suspicious |
| 92–100 | M12: 5× edge boost | "≈0.001 nC". Static b95–100 | Stark suspense |
| 100–106 | Barrier result | Log bars. **"~180,000×" f6070 (b101.17)**. "…the #1 unknown" | **Intellectual climax** |
| 106–114 | Charge bookkeeping | Flash. Ledger cards every 70 f; **"= Net ≈ −1.9 nC" f6540 (b109)** | An equation lands, resolution |
| 114–122 | Forces | Arrows 20 f apart (−39 / +37 / +8 N). **"Not thrust" (red) b117** | Tension that cancels |
| 122–128 | Grounded vs floating | **GROUNDED −1.9172 (f7340) / FLOATING −1.9172 (f7360)**: call and response | Dry "nothing changes" |
| 128–138 | Honest limits | 4 red ✗ lines one per bar, then **green ✓ "Bookkeeping is solid…" b132.5**; 5 bars hold | Sober → small lift |
| 138–146 | Next | 3 items every 70 f | Hopeful lift |
| 146–151.5 | Outro | Flash "64 SCENARIOS · 56 MOVIES · 2.87 M PADS". **"THE CONTACT" f8770 / "DECIDES." f8780** | Thesis, resolved |

**Where the original score misses (C):**
1. **"~180,000×" (b101.17) has no hit.** It is the most important number in the video.
2. `limits` starts at b122, but "HONEST LIMITS" appears at b128.
3. No marker at b78 (the result chart).
4. `movies_a` is 38 flat bars of four-on-the-floor. The movie boundaries at b36/44/52/60 are free phrase points.
5. The "56 MOVIES" title slam gets no accent.

---

## Cross-video motifs

1. **Shared skeleton (A, B):**
   - A dim 4-bar intro, then the title drop at b4.
   - Act tags with flashes.
   - 2-bar text-only breaks before acts.
   - A 2-bar summary and a 2-bar end card.
   - C uses the same grammar at 6- and 8-bar scale.
2. **Beat-locked visuals:**
   - The background pulse in all three.
   - A's Scope (quarters).
   - B's Triality nodes (beats) and PhD tiles (half notes).
   - Everything else is free-running.
3. **Reveal grammar:**
   - Slam stacks 10–20 f apart.
   - Counters whose **landing** is the hit.
   - Lists on a steady cadence (20 f, 25 f, 45 f, 60 f, 70 f, 120 f).
   - Chips on quarters.
   - WordReveal at 2–5 f per word: a 16th–32nd "typing" texture.
4. **Colour = theme:**
   - Amber = hardware, thruster, the movies.
   - Cyan = simulation, explanation.
   - Green = verified, resolved.
   - Red = problem, caveat.
   - Violet = the swarm (B) and the contact barrier (C).
5. **Shared content:** A's Fields act (b36–52) previews C (same −500 V / 25 µm Kapton, 2,869,636 sites, 56 movies / 64 cases). That justifies **one shared lattice leitmotif** across A and C.
6. **Honesty beats in all three:**
   - A: the asterisked thrust numbers and the mesh-artifact debunk.
   - B: the NEGATIVE stamp, "Passing tests ≠ validated physics", "Every claim still gets checked".
   - C: "Not thrust", HONEST LIMITS, the failed checks kept.
   - The current scores put these under full energy. Scoring them with *less* is the most consistent opportunity.
7. **Systematic gap:** every video's biggest number reveal lands mid-section with no event: A at b66 (and b28), B at b49–50.6, C at b101.17.
