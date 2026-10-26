# Listening feedback: melody, balance and presentation

Use these working defaults for this user's SongMap compositions and revisions. The current brief takes precedence. Paths below are relative to the repository root. This guide is also bundled with the Codex `songmap-compose` skill.

## Apply the feedback to the requested scope

The first Golden Worlds review praised the bass lines, chords and comping, but found the melodies obnoxious and the leads too loud and shrill. Preserve the praised material when rewriting a melody. Archive the previous score and compare the unaffected backing's pitches, rhythms and harmony after revision; a changed whole-file hash cannot show whether the accompaniment was preserved.

The user later approved the golden cathedral piece, `songs/golden_cathedral/as_above_so_below.sm`, and selected B, Forward Lilt, in `songs/golden_adagio/motif_ab_studio.sm` for its forward motion. Those are specific listening verdicts. Selecting a motif does not approve its later orchestration, and approval of one golden piece does not establish that every golden melody works. Read current score review comments before describing an example as approved.

Intricacy should come from developed phrases, counterpoint, replies, voice leading and changes of texture. Keep a recognizable idea through those changes. More notes, more modes and a different patch on the same loop do not establish development.

## Write a melody with an audible hierarchy

- Establish a small set of anchor tones and a memorable rhythmic/intervallic cell. Let repeated notes and altered answers make the line recognizable before adding more of the scale.
- Give the phrase a destination and a breath. Use held arrivals, pickups, rests and space for another instrument's reply. Forward motion can come from rhythm, anticipation and harmonic direction at a moderate tempo.
- Start in a comfortable middle register and reserve higher or more exposed notes for a reason. A supported, moderate leap can sing; repeated wide leaps and continuous upper-register activity can exhaust the listener.
- Check the actual intervals and chord beneath each long or accented note. Adjacent golden scale degrees have unequal sizes; a scale walk or an automatic modal transform is not necessarily a singable continuation.
- Develop selected features of the theme through a longer phrase: change the ending, delay the answer, move it to another voice, stretch a rhythm or reharmonize a return. Keep enough identity for the return to be heard.
- Review melody rhythm and contour in a simple timbre, then with its accompaniment. Treat note choice, register, density, articulation, spectrum and level as separate revision decisions. A softer patch can help an unfamiliar interval, but does not complete a melodic rewrite.

For golden7, the full mode is the available vocabulary rather than a requirement to use every pitch. In golden10, try a smaller anchor set or complementary pentatonics and introduce the remaining pitches at purposeful moments. A pure-golden brief still stays golden: improve its hierarchy, phrasing and arrangement without inserting an unrequested Western cadence.

## Make golden tension intelligible

For a Western/golden blend, write the preparation, altered tone and arrival explicitly. For example, `vDg7 -> Dm9` can release `^F -> F`; `vDg7 -> Dmaj9` can open `^F -> F#`. The line and the chord must both support that change. A repeated altered pitch without an audible arrival can feel stuck.

During a golden chord, adjust every active part whose unaltered pitch would grind against its replacement. Inspect held notes, inherited figures and release tails at transitions. A shared tone, a rest or a newly voiced chord can bridge the change. Decide whether a semitone suspension is prepared and resolved; the rub checker alone cannot decide that.

For sevenths and ninths, voice the close relationships across registers and choose which extensions the melody foregrounds. In 36-ET a golden seventh stacks `0,11,22,33` sixth-steps; a golden ninth stacks `0,11,22,33,44`. The parser accepts the ninth as `Cmaj9(v3,^5,^^9)`. Verify expanded pitches; `rel:9` on `Cg7` supplies a Western ninth when that extension is absent. Do not invent a `g9` token.

Plan modulation around retained notes, a pivot gesture or an audible melodic transformation. Rewrite absolute chords and letter notes when moving a degree-based theme to a new key. A mode change should have a musical role beyond demonstrating its pitch list.

If a blend percentage is requested, audit harmonic duration and state the basis, including how an unscored decay is treated. The adagio's 75% Western / 25% golden split was one brief, not a general default. Entirely golden pieces and other blends remain valid.

## Calmer timbres and ensemble balance

Use current installed instruments and presets, including newer sampled voices when they suit the part. Lower flute, cello, horn, piano, harp or mallets can offer gentler colors; inspect the actual instrument and register rather than assuming a family is always soft. Recorded samples retain their timbre, vibrato and tuning characteristics. Golden harmony permits ordinary timbres and does not require a golden partial spectrum.

For a calming or lyrical brief, begin with restrained lead level, a moderate register, rounded attacks and breathing space. Review bright partials, hard attacks, high doubles, vibrato/detune and long releases together. Do not repair a generic lead-range or balance warning by restoring an unwanted high octave or boosting a shrill voice. A valid lower sampled range may deserve a documented exception.

Inspect the rendered stems and featured passages after changing instruments. Fader values do not transfer between patches. Whole-piece stem LUFS are useful evidence, but different activity patterns and registers also matter. Lower competing organ, wind or cello layers when they cover the theme; use rests, register separation and replies before relying on level alone. At a cello solo, let the violin yield the foreground.

Make an epic climax through preparation, harmonic arrival, register, orchestration and expression. Keep room for it in the opening, while making the opening audible at a reasonable playback setting. A continuously loud, bright lead is not the required route to intensity.

`master standard` targets its configured loudness; `master clean` applies sample-peak normalization without loudness normalization or limiting. Check delivered LUFS, true peak and clipping in either case. Preserve intentional dynamics and use a common master gain for comparisons; do not normalize each quiet stem or binaural-only track to full-mix loudness.

## Use a controlled motif audition when it resolves a real choice

When the user requests A/B testing, or the main melody remains the consequential open choice for a long piece, make short alternatives in SongMap Studio before expanding the form. Keep harmony, backing, instrumentation and timing comparable; vary the intended melodic idea. Label the choices and their times, provide usable section loops, and check melody-only as well as ensemble playback.

Use AI Lab's native comparison types for these choices: Instrument keeps the notes fixed; Riff changes one part's notes/expression with backing fixed; Arrangement changes the ensemble with aligned section timing; Song snippet compares saved sources with independent start offsets. Prefer a saved comparison link (`?lab=1&comparison=ID`) with stable take audio and scoped feedback over asking the listener to seek manually between sequential A/B sections. For an existing sequential audition, choose each section's start and the same duration in Song snippet mode. Riff/arrangement edits can span the score; their 1–30 second window is the audition, and full source previews precede application. See `docs/AI_LAB.md` for the current UI and API.

Check section loudness so an unintended level difference does not decide the comparison. A common master gain preserves the written dynamics but is not proof of exact loudness matching. Disclose meaningful differences or make a separate matched audition when needed.

Preserve the chosen motif's identity in the full piece. When promising an intact opening, verify its authored pitches and rhythms against the selected version. Develop subsequent returns rather than copying that opening throughout. Record the user's choice, then continue the authorized composition; do not turn this technique into a mandatory permission gate for every score.

## Chord-following binaural layers, when requested

Keep the headphone layer musically connected to the sounding harmony, including Western chords in a mixed piece. For a strict octave reduction, derive a center from a scored note as `f / 2^n`, with positive integer `n`. Audit its source note, chord membership and transition. If choosing an audible octave-folded pitch-class center that can lie above a bass fundamental, describe that accurately rather than claiming every carrier is below its source.

The user's intended beat difference also derives from the note itself: `difference = center / 2^n`, with one shared integer octave reduction held throughout the piece. Use `beat=octave octaves=5` (the default): 220 Hz produces 6.875 Hz, and 329.628 Hz produces about 10.301 Hz. Choose a common octave reduction that puts the piece's carrier range in the desired difference band; verify the resulting range. The differences then track Western and golden note ratios automatically, including modulations and a common note moving between carrier-list positions. Do not substitute an independent fixed 10 Hz rate, a golden ladder of arbitrary rates, or unrelated section-rate ramps. Explicit numeric `beat`/`ladder` controls remain a legacy fixed-Hz technique for briefs that specifically request it.

For a symmetric pair, `fL = center - difference/2` and `fR = center + difference/2`. Use the existing renderer, smooth carrier crossfades, restrained levels and an intentional ending. Verify `difference * 2^n = center` in the plan, rendered audio and displayed frequencies. Several pairs can interact within each ear; increased level or pair count is not a demonstrated neurological benefit. Describe the artistic headphone effect without promising entrainment, induced bliss or a maximum brain response.

For comparisons, the exported `binaural` difference stem may include subtractive carrier notches. Generate a genuine isolated positive-pair layer with the existing renderer. State whether music-only is the uncarved bed; that bed plus the isolated pairs may not reconstruct the full mix. Keep comparison gain consistent. Measure a few steady audio windows away from chord crossfades to verify left/right frequencies and rates.

## Explain and show what is actually playing

When a presentation is requested, prefer a compact synchronized HTML player if it meets the brief; this user liked its space efficiency. Retain useful chord/key information and musical explanations while improving the visuals. Static instrument portraits can accompany individual note names underneath; cartoon musicians and notation bubbles remain optional future work unless requested.

Use readable per-instrument panels, a compact active pitch region or the current bar, and highlighting that includes rests. Avoid spending most of the screen on unused keyboard/pitch range. A master chord label alone does not show each instrument's notes. For video, preserve the same readability and information hierarchy.

Drive labels and timing from the performed score events, including gate and timing changes. Show binaural transitions from the renderer's frequency curves. Verify seeking, pause/play, version switching at the same time, image loading, and mobile or target-video readability. Test the real rendered page or video, not only its data file. Preserve other Songbook players when publishing an incremental addition; a full `--no-audio` build can remove them.

Keep claims separate: successful parsing, pitch audits, zero clipping and browser checks establish those technical results. They do not establish a likeable melody or human listening approval. Record the listener's actual verdict and revise within its scope.
