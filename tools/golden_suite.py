"""Write and render the golden-harmony audio suite as SongMap songs (36edo), then build the HTML index.

    python tools/golden_suite.py                      # everything
    python tools/golden_suite.py --only portfolios    # portfolios | dictionary | wtc | refs

Every piece is a SongMap song file in examples/golden/suite/ (36edo, `~` / `~g` passing placeholders,
`voiced` styles, stable instruments, `master: clean`), rendered by the engine to MP3 in golden_audio/.
golden_audio/index.html lists every file with a description.

Placeholders (songmap/theory/passing.py):
    System 1  `~`  : the strict (unique) sub-chromatic path; at most one golden chord per transition
    System 2  `~g` : the natural path; two different golden chords can follow each other
"""
from __future__ import annotations

import argparse
import re
import html
import json
import os
import shutil
import subprocess
import sys
import time

import yaml

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from songmap.arrange.expand import expand            # noqa: E402
from songmap.parse import yaml_form                  # noqa: E402
from songmap.render import render, write_outputs     # noqa: E402
from songmap.theory.keys import MODES                # noqa: E402
from songmap.theory.passing import name36            # noqa: E402

SONGS = os.path.join(ROOT, "examples", "golden", "suite")
BUILD = os.path.join(ROOT, "build", "golden_suite")
AUDIO = os.path.join(ROOT, "golden_audio")

# Stable instruments (no detune, drift, tremolo, vibrato or per-hit variation)
PIANO = "keys/still"
EP = "epiano/still"
WASH = "pad/still"
GTR = "string_pluck/still"
ORGAN = "clean/organ"
BELL = "clean/glass"
GPAD = "clean/golden_pad"
CBASS = "clean/bass"
LEAD = "clean/lead"
CKEYS = "clean/keys"

LEVEL = {"organ": -6, "piano": -5, "ep": -6, "wash": -11, "low": -4, "bell": -7, "melody": -5, "guitar": -6,
         "drums": -14, "gpad": -6, "chords": -6}
SEND = {"organ": 0.25, "piano": 0.25, "ep": 0.25, "wash": 0.35, "bell": 0.4, "melody": 0.3, "guitar": 0.25,
        "drums": 0.08, "gpad": 0.35, "low": 0.05, "chords": 0.2}

MOTIFS = {
    "lull": {"rel": "5/4 3 R+/2 | 3/4 5 3/2", "octave": 5},
    "hymn": {"rel": "R+/2 5 | 3/2 5"},
    "esc": {"rel": "R8 3 5 R+ 5 3 R 3"},
    "ballad": {"rel": "3/4. 5/8 R+/4 5/4 | 3/2 R/2"},
    "horizon": {"rel": "R+/2 5/4 3 | 5/1"},
    "shimmer": {"rel": "7/4 5 3 5 | R+/2 7/2"},
    "andal": {"rel": "R+8 5 3 R 3 5 R+ 5"},
    "bell_slow": {"rel": "5/2 3+ R+ 5"},
    "circle_bell": {"rel": "R+/1 | 5/2 3+ | 5/1"},
    "shade": {"rel": "3/2 5/4 3 | R+/2 3/2"},
    "metal": {"rel": "5/2 3 | R+/1"},
    "g7a": {"deg": "0/4 1 2 4 | 3/2 2/4 1 | 0/4 2 4 5 | 4/1", "octave": 5, "key": "C golden7"},
    "g7run": {"deg": "0/8 1 2 3 4 5 6 7 | 7/8 6 5 4 3 2 1 0", "octave": 4, "key": "C golden7"},
    "arp_up": {"rel": "R8 3 5 R+ 5 3 R 3"},
    "arp_wave": {"rel": "R8 5 3+ 5 R+ 5 3 5"},
}

CHORDS = {
    "I": (0, ""), "ii": (2, "m"), "iii": (4, "m"), "IV": (5, ""), "V": (7, ""), "vi": (9, "m"), "vii°": (11, "dim"),
    "Imaj7": (0, "maj7"), "ii7": (2, "m7"), "iii7": (4, "m7"), "IVmaj7": (5, "maj7"), "V7": (7, "7"),
    "vi7": (9, "m7"), "viiø7": (11, "m7b5"),
    "i": (0, "m"), "iv": (5, "m"), "bIII": (3, ""), "bVI": (8, ""), "bVII": (10, ""), "bII": (1, ""),
    "II": (2, ""), "III": (4, ""), "VI": (9, ""), "V7/V": (2, "7"), "V7/vi": (4, "7"), "V7/IV": (0, "7"),
    "iiø7": (2, "m7b5"), "bVImaj7": (8, "maj7"), "I+": (0, "aug"), "vii°7": (11, "dim7"),
}
DIATONIC_TRIADS = ["I", "ii", "iii", "IV", "V", "vi", "vii°"]
DIATONIC_7THS = ["Imaj7", "ii7", "iii7", "IVmaj7", "V7", "vi7", "viiø7"]
CHROMATIC = [k for k in CHORDS if k not in DIATONIC_TRIADS + DIATONIC_7THS]
COMMON = [("V", "I"), ("V7", "I"), ("IV", "I"), ("I", "IV"), ("I", "V"), ("ii", "V"), ("ii7", "V7"), ("IV", "V"),
          ("V", "vi"), ("V7", "vi"), ("I", "vi"), ("vi", "IV"), ("vi", "ii"), ("ii", "vi"), ("iii", "vi"),
          ("I", "ii"), ("IV", "ii"), ("vii°", "I"), ("V7", "Imaj7"), ("I", "bVI"), ("bVI", "I"), ("bVII", "I"),
          ("iv", "I"), ("IV", "iv"), ("V7/V", "V7"), ("bII", "I"), ("V7/vi", "vi"), ("IVmaj7", "V7"),
          ("iii7", "vi7"), ("vi7", "ii7"), ("Imaj7", "IVmaj7"), ("I", "iii"), ("iii", "IV")]


def sym(roman: str, tonic_steps: int = 0) -> str:
    r, q = CHORDS[roman]
    return name36(tonic_steps + 3 * r) + q


def safe(s: str) -> str:
    """Section names from chord/roman symbols: ^ -> up, v (before a note letter) -> dn, # -> s."""
    s = re.sub(r"v(?=[A-G])", "dn", s.replace("^", "up"))
    for a, b in (("#", "s"), ("°", "o"), ("ø", "h"), ("/", "_of_"), ("+", "aug"), (" ", "_")):
        s = s.replace(a, b)
    return s


def slug(s: str) -> str:
    """File names from titles."""
    s = s.lower().replace("♭", "b").replace("→", "to").replace("↔", "to")
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def song(title, tempo, seed, inst: dict, sections, *, dry=False, tail=3.0, harmony=None, key="C major"):
    """A SongMap song dict: 36edo, clean master, per-part levels and hall sends."""
    mix = {}
    for part in inst:
        kind = part.rstrip("0123456789")
        m = {"gain_db": LEVEL.get(kind, -6)}
        if not dry and SEND.get(kind):
            m["send"] = {"hall": SEND[kind]}
        mix[part] = m
    s = {"songmap": 0.2, "title": title, "tempo": tempo, "meter": "4/4", "key": key, "tuning": "36edo",
         "seed": seed, "tail_seconds": tail, "instruments": inst, "motifs": MOTIFS, "mix": mix,
         "returns": {"hall": {"type": "reverb", "seconds": 2.8, "predelay": 0.025, "damping": 0.5}},
         "master": "clean"}
    if harmony:
        s["harmony"] = harmony
    s["sections"] = sections
    return s


def definition(title, tempo, prog, seed=1):
    """A definition clip: dry clean organ chords (4 voices) and the voicing's lowest line as bass."""
    bars = 0.0
    for tok in prog.split():
        sym_, _, b = tok.partition(":")
        bars += float(b or 1)
    return song(title, tempo, seed, {"organ": ORGAN, "low": CBASS},
                [{"name": "definition", "bars": bars, "harmony": prog,
                  "parts": {"organ": "hold", "low": "bassline"}}], dry=True, tail=2.0)


def sec(name, bars, prog, parts, dyn=None):
    d = {"name": name, "bars": bars, "harmony": prog, "parts": parts}
    if dyn:
        d["dyn"] = dyn
    return d


ARP = lambda style="gentle8", **kw: {"style": style, "role": "arp", **kw}      # noqa: E731
MEL = lambda *ms, oct=0: {"motifs": list(ms), "oct": oct}                        # noqa: E731
BASS = lambda style: {"style": style, "role": "bass"}                             # noqa: E731
DR_SOFT = {"kick": "X.......x.......", "hat": "..x...x...x...x."}
DR_GROOVE = {"kick": "X.....x...x.....", "snare": "....x.......x...", "hat": "x.x.x.x.x.x.x.x."}
DR_FLAMENCO = {"kick": "X..x..x...x.x...", "clap": "...x..x....x..x."}


# ------------------------------------------------------------------------------------------------
# portfolios: one technique each = definition clip + a musical piece built on one motif
# ------------------------------------------------------------------------------------------------
def portfolios():
    P = []

    # 1 golden six-four (System 1)
    v = "C:1 Am:1 F:1 G:0.5 ~:0.25 ~:0.25 C:1 Em:1 Dm:1 G:0.5 ~:0.25 ~:0.25"
    P.append(dict(
        id="P01", title="The golden six-four (V → vIg/V → I)", system="System 1",
        technique="On the strict path from V to I, the leading tone climbs B → ^B → vC → C and the second degree climbs "
                  "D → vE♭ → ^E♭ → E over the held dominant bass. The second passing chord is <b>vCg</b>, the golden triad "
                  "a sixth-step below the tonic, sitting over the dominant like a classical cadential six-four. Its "
                  "partner, the first passing chord, is the bronze triad vE♭T13.",
        definition=definition("Definition: the golden six-four", 80,
                              "G:1 ~:0.5 ~:0.5 C:1.5 N.C.:0.5 Bb:1 ~:0.5 ~:0.5 Eb:1.5 N.C.:0.5 E:1 ~:0.5 ~:0.5 A:1.5 N.C.:0.5"),
        def_text="V → I in C, E♭ and A: the dominant, the bronze partner, the golden six-four, then the tonic. Dry, sustained organ.",
        piece=song("Lullaby in Gold", 76, 101,
                   {"piano": PIANO, "wash": WASH, "low": CBASS, "bell": BELL, "guitar": GTR},
                   [sec("intro", 4, v, {"piano": ARP(), "wash": "hold"}, dyn="p"),
                    sec("verse", 8, v, {"piano": ARP(), "wash": "hold", "low": "bassline", "bell": MEL("lull", oct=1)}, dyn="mp"),
                    sec("bloom", 8, v, {"piano": "comp", "guitar": ARP("roll16"), "low": "bassline", "bell": "top", "wash": "hold"}, dyn="mf"),
                    sec("outro", 4, v, {"piano": ARP(), "wash": "hold", "bell": MEL("lull", oct=1)}, dyn="mp>p")]),
        piece_text="A lullaby that ends every phrase on the golden six-four. Piano arpeggios carry the passing chords as quick "
                   "sixteenths, a glass bell sings a two-bar chord-tone motif, then the bell takes the soprano line itself "
                   "(top voice) over plucked-string rolls."))

    # 2 golden plagal amen (System 1)
    v = "C:0.75 ~:0.25 F:0.75 ~:0.25 C:0.75 ~:0.25 G:0.75 ~:0.25 Am:0.75 ~:0.25 Dm:0.75 ~:0.25 G:0.75 ~:0.25 C:1"
    P.append(dict(
        id="P02", title="Golden plagal glow (I ↔ IV through vFg)", system="System 1",
        technique="I → IV and IV → I are two major triads a fourth apart, so the quality theorem guarantees exactly one golden "
                  "passing chord: <b>vFg</b> (vF ^A♭ C), rooted a sixth-step below the subdominant. Going up, it leans into "
                  "IV; coming home, it colors the amen cadence.",
        definition=definition("Definition: golden plagal motion", 72, "C:1.5 ~:0.5 F:1.5 ~:0.5 C:2 G:1.5 ~:0.5 C:1.5 ~:0.5 G:2"),
        def_text="C → vFg → F → vFg/F → C, then the same in G. One strict passing chord per move.",
        piece=song("Amen in Gold", 66, 102, {"organ": ORGAN, "wash": WASH, "low": CBASS, "bell": BELL},
                   [sec("hymn", 8, v, {"organ": "hold", "low": "bassline"}, dyn="p<mp"),
                    sec("verse", 8, v, {"organ": "hold", "low": "bassline", "bell": "top", "wash": "hold"}, dyn="mp"),
                    sec("amen", 8, v, {"organ": "hold", "low": "bassline", "bell": MEL("hymn", oct=1), "wash": "hold"}, dyn="mf>p")]),
        piece_text="A hymn in which every move between neighbouring chords passes through its strict golden or sub-chromatic "
                   "chord: I–IV–I–V–vi–ii–V–I. Organ chorale, then the bell doubles the soprano, then a slow bell hymn line."))

    # 3 golden escalator (System 2)
    v = ("C:0.75 ~g:0.125 ~g:0.125 Dm:0.75 ~g:0.125 ~g:0.125 Em:0.75 ~:0.125 ~:0.125 F:0.75 ~g:0.125 ~g:0.125 "
         "G:0.75 ~g:0.125 ~g:0.125 Am:0.75 ~g:0.125 ~g:0.125 F:0.75 ~g:0.125 ~g:0.125 G:0.75 ~g:0.125 ~g:0.125")
    P.append(dict(
        id="P03", title="The golden escalator (roots a whole step apart)", system="System 2",
        technique="When roots climb by a whole step (I→ii, ii→iii, IV→V, V→vi), the natural path splits each voice's "
                  "whole step unevenly. The two passing chords are then <b>two different golden triads on the chromatic "
                  "root between</b>, crossing from the v layer to the ^ layer: F – vF#g – ^F#g – G. A half-step move "
                  "(iii→IV) can't be golden (the half-step theorem), so it planes sub-chromatically instead.",
        definition=definition("Definition: the golden escalator", 84,
                              "F:1 ~g:0.5 ~g:0.5 G:2 G:1 ~g:0.5 ~g:0.5 Am:2 C:1 ~g:0.5 ~g:0.5 Dm:2"),
        def_text="IV → V, V → vi and I → ii, each through two golden chords on the root between.",
        piece=song("Escalator", 104, 103, {"guitar": GTR, "ep": EP, "low": CBASS, "bell": BELL, "drums": {"kit": {}}},
                   [sec("intro", 4, v, {"guitar": ARP("roll16"), "low": "bassline"}, dyn="p"),
                    sec("climb", 8, v, {"guitar": ARP("roll16"), "ep": "comp", "low": BASS("root5"), "drums": DR_SOFT}, dyn="mp<mf"),
                    sec("soar", 8, v, {"guitar": ARP("roll16"), "ep": "comp", "low": BASS("root5"), "drums": DR_GROOVE,
                                       "bell": MEL("esc", oct=1)}, dyn="mf"),
                    sec("land", 4, v, {"ep": "hold", "bell": "top", "low": "bassline"}, dyn="mp>p")]),
        piece_text="A rising chord ladder C–Dm–Em–F–G–Am–F–G, every whole step an escalator of two golden chords. Plucked "
                   "16ths, electric-piano comping, a root-and-fifth bass (golden fifths on golden chords), and a bell "
                   "arpeggio that follows every passing chord."))

    # 4 golden deceptive (System 2)
    v = "F:1 G:0.75 ~g:0.125 ~g:0.125 Am:1 Em:1 F:1 G:0.75 ~g:0.125 ~g:0.125 Am:1.5 G:0.5"
    P.append(dict(
        id="P04", title="The golden deceptive cadence (V → v♭VIg → ♭VIg → vi)", system="System 2",
        technique="The deceptive cadence V → vi moves its roots up a whole step, so it becomes an escalator: "
                  "G – <b>vA♭g – A♭g</b> – Am. The golden chords sit on ♭VI, so the deception is foreshadowed by the "
                  "Romantic flat-six color before the minor chord arrives.",
        definition=definition("Definition: the golden deceptive cadence", 80,
                              "G:1 ~g:0.5 ~g:0.5 Am:2 D:1 ~g:0.5 ~g:0.5 Em:2 E:1 ~g:0.5 ~g:0.5 F#m:2"),
        def_text="V → vi in C, G and A, each through two golden chords on ♭VI.",
        piece=song("Deception", 72, 104, {"ep": EP, "wash": WASH, "low": CBASS, "melody": LEAD},
                   [sec("intro", 4, v, {"ep": "hold"}, dyn="p"),
                    sec("verse", 8, v, {"ep": "comp", "low": "bassline", "melody": "top"}, dyn="mp"),
                    sec("chorus", 8, v, {"ep": "comp", "wash": "hold", "low": BASS("root5"), "melody": MEL("ballad", oct=1)}, dyn="mf"),
                    sec("outro", 4, v, {"ep": "hold", "wash": "hold"}, dyn="mp>pp")]),
        piece_text="A ballad loop F–G–Am–Em–F–G–Am in which each G → Am is a golden deceptive escalator. Electric piano, "
                   "a clean lead on the soprano line, then a ballad motif over a warm pad."))

    # 5 mediant gold (System 1)
    v = "C:1.5 ~:0.5 Ab:1.5 ~:0.5 C:1.5 ~:0.5 E:1.5 ~:0.5 C:1.5 ~:0.5 Eb:1.5 ~:0.5 C:1.5 ~:0.5 A:1.5 ~:0.5"
    P.append(dict(
        id="P05", title="Mediant gold (chromatic mediants)", system="System 1",
        technique="Every chromatic mediant (two major triads a third apart) has exactly one golden passing chord:<ul>"
                  "<li>C → A♭ via <b>Cg</b>, the 1/3 point of the move;</li>"
                  "<li>C → E via <b>Eg</b>;</li>"
                  "<li>C → A via <b>^Cg</b>;</li>"
                  "<li>C → E♭ via <b>^E♭g</b>.</li></ul>"
                  "Golden harmony is native to Romantic and film-score mediant harmony.",
        definition=definition("Definition: mediant gold", 90, "C:1.5 ~:0.5 Ab:2 C:1.5 ~:0.5 E:2 C:1.5 ~:0.5 A:2 C:1.5 ~:0.5 Eb:2"),
        def_text="C to each of its four chromatic mediants, through the unique golden chord of each move.",
        piece=song("Mediant Horizons", 66, 105, {"organ": ORGAN, "wash": WASH, "low": CBASS, "bell": BELL, "piano": PIANO},
                   [sec("dawn", 8, v, {"organ": "hold", "wash": "hold", "low": BASS("roots")}, dyn="pp<mp"),
                    sec("rise", 8, v, {"organ": "hold", "wash": "hold", "low": BASS("roots"), "bell": MEL("horizon", oct=1)}, dyn="mp<mf"),
                    sec("vista", 8, v, {"piano": ARP("roll16"), "organ": "hold", "low": "bassline", "bell": "top"}, dyn="mf>p")]),
        piece_text="A cinematic cycle C–A♭–C–E–C–E♭–C–A, each mediant move through its golden chord, building from organ "
                   "and pad to a rolling piano with the bell on the soprano line."))

    # 6 light and shade: golden centroid, modal mixture, Picardy
    v = "C:1 Cg:1 Cm:1 Fm:1 Ab:1 Fm:1 Cm(^3):0.5 Cg:0.5 C:1"
    P.append(dict(
        id="P06", title="Light and shade: the golden centroid (C – Cg – Cm)", system="averaging",
        technique="The averaging principle: <b>Cg is the exact average of C major, C minor and C augmented</b> (third "
                  "(12+9+12)/3 = 11, fifth (21+21+24)/3 = 22 sixth-steps). It is 2 sixth-steps from C and 3 from Cm, a "
                  "pivot for modal mixture. The golden Picardy climbs the third through every sixth-step: "
                  "Cm (9) → C(^m3) (10) → Cg (11) → C (12).",
        definition=definition("Definition: centroid and Picardy", 70, "C:1 Cg:1 Cm:1 Cg:1 C:2 Cm:1 Cm(^3):1 Cg:1 C:2"),
        def_text="C → Cg → Cm → Cg → C, then the golden Picardy Cm → C(^m3) → Cg → C.",
        piece=song("Light and Shade", 80, 106, {"piano": PIANO, "wash": WASH, "low": CBASS, "bell": BELL},
                   [sec("light", 8, v, {"piano": "hold", "low": "bassline"}, dyn="mp"),
                    sec("shade", 8, v, {"piano": "comp", "wash": "hold", "low": "bassline", "bell": MEL("shade", oct=1)}, dyn="mf"),
                    sec("light2", 8, v, {"piano": ARP(), "wash": "hold", "bell": "top", "low": BASS("roots")}, dyn="mp>p")]),
        piece_text="Major and minor trade places through their golden centroid: C – Cg – Cm – Fm – A♭ – Fm, then the golden "
                   "Picardy back to C. The bell motif leans on the chord's third, so you hear it slide 9 → 10 → 11 → 12."))

    # 7 the equal-third line: silver and bronze
    v = "Caug:1 Cg:1 Cs:1 Cdim:1 Ebaug:1 Ebg:1 Ebs:1 Ebdim:1 Dm:1 G:1 ~:0.5 ~:0.5 C:2"
    P.append(dict(
        id="P07", title="Metallic means: the equal-third line (silver, golden, bronze)", system="averaging",
        technique="Stacking two equal thirds of n sixth-steps gives one straight line through chord space: diminished (9), "
                  "<b>silver</b> (10: C ^E♭ vG, the average of major, minor and diminished), <b>golden</b> (11), "
                  "augmented (12) and <b>bronze</b> (13: C ^E vA, golden mirrored through augmented). One uniform path "
                  "runs Caug → Cg → Cs → Cdim, with the third falling one sixth-step and the fifth two per chord. On every "
                  "strict path between two major triads, golden's passing partner is bronze (V–I: G – vE♭T13 – vCg – C).",
        definition=definition("Definition: the equal-third line", 66, "Caug:1 Cg:1 Cs:1 Cdim:1 Cs:1 Cg:1 Caug:2 G:1 ~:0.5 ~:0.5 C:2"),
        def_text="Augmented → golden → silver → diminished and back, then V → I with its bronze-then-golden passing pair.",
        piece=song("Metallic Means", 60, 107, {"organ": ORGAN, "gpad": GPAD, "low": CBASS, "bell": BELL},
                   [sec("descent", 12, v, {"organ": "hold", "low": "bassline"}, dyn="p<mp"),
                    sec("glint", 12, v, {"organ": "hold", "gpad": "hold", "bell": MEL("metal", oct=1), "low": "bassline"}, dyn="mp>p")]),
        piece_text="Two slow descents down the equal-third line (on C, then on E♭), resolving through Dm and the bronze/golden "
                   "V–I. Organ chorale, a golden-spectrum pad and a bell."))

    # 8 golden seventh shimmer
    v = "Cmaj7:1 Cg7:1 Fmaj7:1 Fg7:1 Am7:1 Ag7:1 Dm7:0.5 Dg7:0.5 G7:0.75 ~g:0.25"
    P.append(dict(
        id="P08", title="Golden seventh shimmer (maj7 ↔ g7)", system="averaging",
        technique="The golden seventh is three stacked golden thirds, 1 : 2/φ : 4/φ² : 8/φ³. Its seventh, 8/φ³ = 1100.73 c, "
                  "is rendered by 36-ET as exactly the major seventh (1100 c; the exact value is 0.73 c sharper). So in "
                  "36-ET <b>Cg7 = Cmaj7 with its inner voices bent</b>: the third down a sixth-step, the fifth up a "
                  "sixth-step. Alternating maj7 and g7 keeps the outer voices still while the middle shimmers. "
                  "Octave-equivalently, Cg7 is the chain chord 1 : φ : φ² : φ³.",
        definition=definition("Definition: golden seventh shimmer", 66, "Cmaj7:2 Cg7:2 Cmaj7:2 Fmaj7:2 Fg7:2 Fmaj7:2"),
        def_text="Cmaj7 ↔ Cg7 and Fmaj7 ↔ Fg7: only the inner voices move.",
        piece=song("Shimmer", 72, 108, {"ep": EP, "bell": BELL, "wash": WASH, "low": CBASS},
                   [sec("haze", 8, v, {"ep": "hold", "wash": "hold", "low": BASS("roots")}, dyn="p"),
                    sec("glow", 8, v, {"ep": "comp", "bell": ARP(), "low": "bassline", "wash": "hold"}, dyn="mp"),
                    sec("glitter", 8, v, {"ep": "comp", "bell": MEL("shimmer", oct=1), "low": "bassline"}, dyn="mf>p")]),
        piece_text="A dream-pop loop of major and minor sevenths, each followed by its golden seventh. Electric piano, "
                   "glass-bell arpeggios and a sevenths motif."))

    # 9 golden andalusian
    v = "Am:0.75 ~g:0.125 ~g:0.125 G:0.75 ~g:0.125 ~g:0.125 F:0.75 ~:0.125 ~:0.125 E:1"
    P.append(dict(
        id="P09", title="Golden Andalusian (vi–V–IV–III)", system="System 2",
        technique="The Andalusian descent Am–G–F–E: two descending escalators through golden chords on A♭ and F#, then the "
                  "half-step theorem in action. F → E can't pass through golden, so it planes sub-chromatically "
                  "(F → vF → ^E → E) into the Phrygian cadence.",
        definition=definition("Definition: golden Andalusian", 84, "Am:1 ~g:0.5 ~g:0.5 G:1 ~g:0.5 ~g:0.5 F:1 ~:0.5 ~:0.5 E:2"),
        def_text="Am – A♭g – vA♭g – G – ^F#g – vF#g – F – (planing) – E.",
        piece=song("Andalusian Gold", 100, 109, {"guitar": GTR, "low": CBASS, "melody": LEAD, "drums": {"kit": {}}, "wash": WASH},
                   [sec("rasgueado", 8, v, {"guitar": "pulse", "low": BASS("roots")}, dyn="mp"),
                    sec("cante", 12, v, {"guitar": "pulse", "low": BASS("root5"), "melody": MEL("andal", oct=1), "drums": DR_FLAMENCO}, dyn="mf"),
                    sec("final", 8, v, {"guitar": ARP("roll16"), "wash": "hold", "melody": "top", "low": BASS("roots")}, dyn="mf>p")]),
        piece_text="Flamenco-flavoured: strummed plucked-string chords, a clap pattern, and a lead line that rides the golden "
                   "chords, then plucked rolls with the soprano line."))

    # 10 golden circle walk (golden home)
    circ = [name36(11 * k) + "g" for k in range(12)]
    v = " ".join(f"{c}:2.5" for c in circ)
    P.append(dict(
        id="P10", title="The golden circle (golden home)", system="golden home",
        technique="When golden harmony is home, it moves by <b>circle steps</b>. Cg → vEg → ^Gg → Bg → …: neighbours share two "
                  "notes, one voice moves down a semitone, and the circle visits all 36 golden triads. On real, harmonic instruments "
                  "each golden triad is a delicate local rest above C major's deeper home; on the digital golden-spectrum pad "
                  "used here (partials 2^m·φ^n, a laboratory timbre no physical instrument has) these chords measure "
                  "smoothest, so the walk sounds calm.",
        definition=song("Definition: the golden circle", 60, 110, {"gpad": GPAD, "low": CBASS},
                        [{"name": "definition", "bars": 6, "harmony": " ".join(f"{c}:1" for c in circ[:5]) + " Cg:1",
                          "parts": {"gpad": "hold", "low": "bassline"}}], dry=True),
        def_text="Five steps around the golden circle on the golden-spectrum pad, dry.",
        piece=song("Golden Circle", 60, 111, {"gpad": GPAD, "bell": BELL, "low": {"use": CBASS, "decay": 0, "attack": 0.8, "release": 2.0}},
                   [sec("walk", 28, v, {"gpad": "hold", "low": "bassline", "bell": MEL("circle_bell", oct=1)}, dyn="p<mp>p")], tail=6),
        piece_text="Two minutes on the golden circle: twelve chords of 10 seconds each, sustained golden-spectrum pads, a bass "
                   "on the lowest voice and a slow bell on chord tones."))

    # 11 golden breathing with timbre flip
    v = " ".join(f"{name36(11 * k)}g:2 {name36(11 * k)}g7:2" for k in range(6))
    P.append(dict(
        id="P11", title="Golden breathing and the timbre flip", system="golden home",
        technique="<b>Breathing</b>: the triad gains its chain neighbour (Cg + B = Cg7) and then drops its root (= vEg), so "
                  "the harmony inhales and exhales one golden tone at a time. Played first on the digital golden-spectrum pad "
                  "(the laboratory, where golden chords measure smoothest), then on a harmonic organ (a real-instrument "
                  "spectrum, where they are delicate, unstable rests), then golden again: <b>timbre decides how deep each "
                  "rest is</b>.",
        definition=song("Definition: golden breathing", 60, 112, {"gpad": GPAD, "low": CBASS},
                        [{"name": "definition", "bars": 6, "harmony": "Cg:1 Cg7:1 vEg:1 vEg7:1 ^Gg:2",
                          "parts": {"gpad": "hold", "low": "bassline"}}], dry=True),
        def_text="Cg – Cg7 – vEg – vEg7 – ^Gg on the golden-spectrum pad.",
        piece=song("Breathing", 60, 113, {"gpad": GPAD, "organ": {"use": ORGAN, "attack": 0.8, "release": 1.5}, "bell": BELL, "low": CBASS},
                   [sec("golden", 10, v, {"gpad": "hold", "low": "bassline"}, dyn="p<mp"),
                    sec("harmonic", 10, v, {"organ": "hold", "low": "bassline"}, dyn="mp"),
                    sec("golden2", 10, v, {"gpad": "hold", "bell": MEL("bell_slow", oct=1), "low": "bassline"}, dyn="mp>p")], tail=6),
        piece_text="The same breathing progression three times: golden-spectrum pad, harmonic organ, then golden pad with bells. "
                   "Listen to how roughness and calm swap places."))

    # 12 layer prism (planing)
    v = "Cg:2 ^Cg:2 vC#g:2 C#g:2 vC#g:2 ^Cg:2 Cg:4"
    P.append(dict(
        id="P12", title="Layer prism (sixth-step planing)", system="golden home",
        technique="<b>Planing</b> moves the whole golden triad up a sixth-step, Cg → ^Cg → vC#g → C#g. The shape is unchanged, "
                  "but each move shifts every note onto another of 36-ET's three 12-ET layers, so the chord changes color "
                  "like light through a prism.",
        definition=song("Definition: layer prism", 60, 114, {"gpad": GPAD, "low": CBASS},
                        [{"name": "definition", "bars": 7, "harmony": "Cg:1 ^Cg:1 vC#g:1 C#g:1 vC#g:1 ^Cg:1 Cg:1",
                          "parts": {"gpad": "hold", "low": "bassline"}}], dry=True),
        def_text="Cg planed up three sixth-steps and back.",
        piece=song("Prism", 66, 115, {"gpad": GPAD, "bell": BELL, "piano": {"use": CKEYS}, "low": CBASS},
                   [sec("refract", 15, v, {"gpad": "hold", "low": "bassline", "bell": MEL("bell_slow", oct=1)}, dyn="p<mp"),
                    sec("scatter", 15, v, {"gpad": "hold", "piano": ARP("roll16"), "low": "bassline"}, dyn="mp>p")], tail=6),
        piece_text="Slow prism planing with bells, then clean-keys sixteenths that make each layer shift sparkle."))

    # 13 rational visitation
    v = "Cg:3 C:1 Cg:3 Ab:1 Cg:3 Cm:1 Cg:3 Caug:1"
    P.append(dict(
        id="P13", title="Rational visitation (golden home, rational release)", system="golden home",
        technique="The inversion of ordinary harmony. A golden home opens briefly onto its nearest rational chords, 2–4 "
                  "sixth-steps away: C, A♭, Cm and Caug. On real, harmonic instruments each Western chord is a moment of "
                  "release (C major the deepest), and the return re-enters the golden local rest. This version plays on the "
                  "digital golden-spectrum pad, the laboratory, where the roles flip and Cg measures smoother than its visitors.",
        definition=song("Definition: rational visitation", 60, 116, {"gpad": GPAD, "low": CBASS},
                        [{"name": "definition", "bars": 8, "harmony": "Cg:1.5 C:0.5 Cg:1.5 Ab:0.5 Cg:1.5 Cm:0.5 Cg:2",
                          "parts": {"gpad": "hold", "low": "bassline"}}], dry=True),
        def_text="Cg → C → Cg → A♭ → Cg → Cm → Cg.",
        piece=song("Visitors", 64, 117, {"gpad": GPAD, "bell": BELL, "low": CBASS},
                   [sec("home", 15, v, {"gpad": "hold", "low": "bassline", "bell": MEL("circle_bell", oct=1)}, dyn="p<mp"),
                    sec("guests", 15, v, {"gpad": "hold", "low": "bassline", "bell": "top"}, dyn="mp>p")], tail=6),
        piece_text="A golden drone that briefly opens onto a Western chord every four bars, then returns home."))

    # 14 golden diatonic (golden7 scale)
    v = "Cg:1 ^Abg:1 vFg:1 C#g:1 vEg:1 vFg7:1 ^Abg7:1 Cg7:1"
    P.append(dict(
        id="P14", title="The golden diatonic (golden7 scale)", system="golden scale",
        technique="The golden chain forms well-formed (two-step) scales only at sizes 2, 3, 4, <b>7</b>, 10, 13, 23 and 36. "
                  "The 7-note one, <b>C C# vE vF ^G ^A♭ B</b>, is the golden counterpart of the diatonic. Its steps are "
                  "99.3 c and 267.6 c, and it contains five golden triads (vEg, Cg, ^A♭g, vFg, C#g) and four golden "
                  "sevenths, including the tonic Cg7. These chords and melodies stay inside the golden Pythagorean system.",
        definition=song("Definition: the golden diatonic", 72, 118, {"bell": BELL, "gpad": GPAD},
                        [{"name": "scale", "bars": 4, "harmony": "Cg:4", "parts": {"bell": MEL("g7run"), "gpad": "hold"}},
                         {"name": "chords", "bars": 6, "harmony": "Cg:1 ^Abg:1 vFg:1 C#g:1 vEg:1 Cg7:1", "parts": {"gpad": "hold"}}],
                        dry=True),
        def_text="The golden7 scale up and down over Cg, then its golden triads and the tonic golden seventh.",
        piece=song("Golden Diatonic", 84, 119, {"gpad": GPAD, "bell": BELL, "low": CBASS, "piano": {"use": CKEYS, "spectrum": 1}},
                   [sec("motif", 8, v, {"gpad": "hold", "bell": MEL("g7a"), "low": "bassline"}, dyn="mp"),
                    sec("weave", 8, v, {"gpad": "hold", "piano": ARP(), "bell": MEL("g7a"), "low": BASS("roots")}, dyn="mf"),
                    sec("rest", 8, v, {"gpad": "hold", "bell": "top", "low": "bassline"}, dyn="mp>p")], tail=5),
        piece_text="Everything comes from golden7: melodies in scale degrees, the scale's own golden triads and sevenths, "
                   "golden-spectrum bells, pads and keys."))

    # 15 beating golden seventh
    v = "Cg7:4 vEg7:4 ^Gg7:4 Cg7:4"
    P.append(dict(
        id="P15", title="Golden beats (close-voiced golden sevenths)", system="golden home",
        technique="On harmonic tones a close golden seventh (1 : 2/φ : 4/φ² : 8/φ³) beats at "
                  "<b>f₀·φ⁻⁶ × (1, 2/φ, 4/φ²)</b>, the golden <i>triad</i> in rhythm. It also beats at 2f₀·φ⁻⁶, the "
                  "golden seventh against the root's octave, because 8/φ³ = 2 − 2φ⁻⁶ (the golden seventh sits exactly "
                  "2φ⁻⁶ below the octave). Register sets the band: near 110 Hz the beats fall at 6.13, 7.58, 9.37 and "
                  "12.26 Hz. The beating itself becomes the pulse, with no drums.",
        definition=song("Definition: golden beats", 60, 120, {"organ": {"use": ORGAN, "attack": 1.0, "release": 2.0}},
                        [{"name": "definition", "bars": 6, "harmony": "Cg7:6",
                          "parts": {"organ": {"style": "hold", "range": [44, 60]}}}], dry=True),
        def_text="One close-voiced Cg7 around 110 Hz on a harmonic organ, held for 24 seconds so the beats speak.",
        piece=song("Beat Cathedral", 60, 121, {"organ": {"use": ORGAN, "attack": 1.0, "release": 2.0}, "bell": BELL, "gpad": GPAD},
                   [sec("low", 14, v, {"organ": {"style": "hold", "range": [44, 60]}, "bell": MEL("metal", oct=1)}, dyn="p<mp"),
                    sec("high", 14, v, {"organ": {"style": "hold", "range": [55, 72]}, "gpad": "hold"}, dyn="mp>p")], tail=6),
        piece_text="Golden sevenths walking the circle in a low register (beats near theta and alpha), then an octave higher "
                   "(faster beats) under a golden pad."))
    return P


# ------------------------------------------------------------------------------------------------
# dictionary suites: System 1 then System 2
# ------------------------------------------------------------------------------------------------
FAMILIES = [
    ("diatonic_triads", "diatonic triads", [(a, b) for a in DIATONIC_TRIADS for b in DIATONIC_TRIADS if a != b]),
    ("diatonic_sevenths", "diatonic seventh chords", [(a, b) for a in DIATONIC_7THS for b in DIATONIC_7THS if a != b]),
    ("triads_and_sevenths", "triads to sevenths and back",
     [(a, b) for a in DIATONIC_TRIADS for b in DIATONIC_7THS] + [(a, b) for a in DIATONIC_7THS for b in DIATONIC_TRIADS]),
    ("diatonic_to_chromatic", "diatonic to chromatic", [(a, b) for a in DIATONIC_TRIADS + DIATONIC_7THS for b in CHROMATIC]),
    ("chromatic_to_diatonic", "chromatic to diatonic", [(a, b) for a in CHROMATIC for b in DIATONIC_TRIADS + DIATONIC_7THS]),
    ("chromatic", "chromatic to chromatic", [(a, b) for a in CHROMATIC for b in CHROMATIC if a != b]),
]
SYSTEMS = [
    ("S1", "~:0.125 ~:0.125", "System 1 (strict)",
     "System 1, the strict path: every half step splits into three equal sixth-steps and every whole step into three "
     "double sixth-steps, so the two passing chords are unique and at most one is golden. Where the quality theorem "
     "allows (same-quality chords a third or fifth apart) you hear exactly one golden chord with its bronze or silver "
     "partner. Elsewhere you hear what the voice leading dictates: micro-altered chords, or planing for half-step moves."),
    ("S2", "~g:0.125 ~g:0.125", "System 2 (natural)",
     "System 2, the natural path: half steps still split evenly, but whole steps may split unevenly, so two different "
     "golden chords can follow each other (46 pairs get two, 181 at least one). Roots a whole step apart pass through "
     "two golden chords on the chromatic root between."),
]


def dictionary_songs():
    out = []
    inst = {"organ": ORGAN, "low": CBASS, "melody": LEAD}
    secs = []
    for a, b in COMMON:
        for tag, mid in (("strict", "~:0.125 ~:0.125"), ("natural", "~g:0.125 ~g:0.125")):
            secs.append({"name": safe(f"{a}_to_{b}_{tag}"), "bars": 1, "harmony": f"{sym(a)}:0.375 {mid} {sym(b)}:0.375",
                         "parts": {"organ": "hold", "low": "bassline", "melody": "top"}})
    out.append(("D00_common_moves_system1_then_system2",
                song("Common moves: System 1 then System 2", 96, 2, inst, secs, dry=True),
                {"group": "Dictionary", "title": "The 33 common moves, System 1 then System 2",
                 "text": "The 33 most common moves in C major (classical cadences, pop and jazz moves, chromatic colors), each "
                         "played twice: first on System 1 (strict, unique path), then on System 2 (natural)."}))
    for sysid, mid, label, systext in SYSTEMS:
        for i, (key, desc, pairs) in enumerate(FAMILIES):
            secs = [{"name": safe(f"{a}_to_{b}"), "bars": 1, "harmony": f"{sym(a)}:0.375 {mid} {sym(b)}:0.375",
                     "parts": {"organ": "hold", "low": "bassline", "melody": "top"}} for a, b in pairs]
            name = f"D{sysid[1]}{i + 1}_{sysid}_{key}"
            out.append((name, song(f"All transitions, {label}: {desc}", 112, 3, inst, secs, dry=True),
                        {"group": f"Dictionary: {label}", "title": f"{label}: {desc} ({len(pairs)} pairs)",
                         "text": f"Every ordered pair of {desc} in C major, {len(pairs)} transitions, one bar each at 112 "
                                 "BPM: first chord, two passing chords, second chord. " + systext}))
    return out


# ------------------------------------------------------------------------------------------------
# the well-tempered golden clavier: Book I (System 1) and Book II (System 2)
# ------------------------------------------------------------------------------------------------
MAJOR_T = [
    [("I", .375), "P", ("IV", .25), "P", ("V", .375), "P", ("I", .25)],
    [("I", .25), "P", ("vi", .25), "P", ("ii", .25), "P", ("V", .25), "P"],
    [("iii", .25), "P", ("vi", .25), "P", ("ii", .25), "P", ("V", .25), "P"],
    [("I", .25), "P", ("ii", .25), "P", ("iii", .25), "P", ("IV", .25), "P"],
]
MINOR_ROMAN = {"i": (0, "m"), "iv": (5, "m"), "V": (7, ""), "VI": (8, ""), "III": (3, ""), "VII": (10, "")}
MINOR_T = [
    [("i", .375), "P", ("iv", .25), "P", ("V", .375), "P", ("i", .25)],
    [("i", .25), "P", ("VI", .25), "P", ("iv", .25), "P", ("V", .25), "P"],
    [("i", .25), "P", ("VII", .25), "P", ("VI", .25), "P", ("V", .25), "P"],
]


def wtc_song():
    s13 = sorted({round(x * 3) for x in MODES["silver13"]})
    silver_roots = [r for r in s13 if all((r + i) % 36 in s13 for i in (0, 10, 20))]
    toks, secs, plan = [], [], []

    def slot(book):
        return ["~:0.25"] if book == 1 else ["~g:0.125", "~g:0.125"]

    for idx, T in enumerate(range(36)):
        book = 1 if idx < 18 else 2
        tn = name36(T)
        for tmpl, table, mode in ((MAJOR_T[idx % 4], None, "major"), (MINOR_T[idx % 3], MINOR_ROMAN, "minor")):
            for item in tmpl:
                if item == "P":
                    toks += slot(book)
                else:
                    r, b = item
                    if table:
                        st, q = table[r]
                        toks.append(f"{name36(T + 3 * st)}{q}:{b}")
                    else:
                        toks.append(f"{sym(r, T)}:{b}")
            mel = "top" if (idx + (mode == "minor")) % 2 == 0 else {"motifs": ["arp_up" if mode == "major" else "arp_wave"], "oct": 1}
            secs.append({"name": safe(f"{tn}_{mode}"), "bars": 2,
                         "parts": {"chords": "comp", "low": "bassline", "melody": mel}})
            plan.append(f"{tn} {mode} (Book {'I' if book == 1 else 'II'})")
        gt = ([(0, "g", .375), (11, "g", .25), (22, "g", .25), (0, "g7", .25), (25, "g", .25), (14, "g", .25), (0, "", .125), (0, "g", .25)]
              if idx % 2 == 0 else
              [(0, "g", .25), (0, "g7", .25), (11, "g", .25), (11, "g7", .25), (22, "g", .25), (33, "g", .25), (25, "g", .25), (0, "g", .25)])
        toks += [f"{name36(T + o)}{q}:{b}" for o, q, b in gt]
        secs.append({"name": safe(f"{tn}_golden13"), "bars": 2,
                     "parts": {"chords": "comp", "low": "bassline", "bell": {"motifs": ["arp_up"], "oct": 1}}})
        plan.append(f"{tn} golden13")
        order = [0] + [r for r in sorted(silver_roots) if r != 0][:4]
        st = [(o, "s", .25) for o in order] + [(0, "m", .25), (0, "s", .25)]
        toks += [f"{name36(T + o)}{q}:{b}" for o, q, b in st]
        toks += slot(book)
        secs.append({"name": safe(f"{tn}_silver13"), "bars": 2,
                     "parts": {"chords": "comp", "low": "bassline", "bell": {"motifs": ["arp_wave"], "oct": 1}}})
        plan.append(f"{tn} silver13")
    s = song("The Well-Tempered Golden Clavier", 132, 144,
             {"chords": CKEYS, "low": CBASS, "melody": CKEYS, "bell": BELL}, secs, harmony={"default": " ".join(toks)}, tail=4)
    s["mix"]["melody"]["gain_db"] = -2
    text = ("One continuous piece through every key of 36-ET. Each of the 36 tonics (C, ^C, vC#, C#, …, rising by "
            "sixth-steps) is heard in four modes, two fast bars each:"
            "<ul>"
            "<li><b>Major</b>: I–IV–V–I and relatives.</li>"
            "<li><b>Parallel minor</b>: i–iv–V–i, i–VI–iv–V and the Andalusian line.</li>"
            "<li><b>Golden13</b>: the golden Pythagorean scale's golden triads and sevenths on the golden circle, with "
            "one brief rational visit.</li>"
            "<li><b>Silver13</b>: the layer-mirrored scale's silver triads, with a minor visit.</li>"
            "</ul>"
            "<b>Book I</b> (the first 18 tonics) uses System 1: one strict passing chord per transition. <b>Book II</b> (the "
            "last 18) uses System 2: two natural passing chords, so golden chords can follow each other. Passing chords "
            "also bridge each key to the next, a sixth-step higher. In all that is 72 major and minor keys, 36 golden13 "
            "and 36 silver13 scales at 132 BPM, with chord changes as fast as eighth notes: a fast-jazz flow rather than "
            "Bach's pace. Clean struck keys, with a glass bell in the golden and silver sections.")
    return [("W1_well_tempered_golden_clavier", s,
             {"group": "The Well-Tempered Golden Clavier", "title": "The Well-Tempered Golden Clavier (Books I and II)",
              "text": text, "plan": plan})]


# ------------------------------------------------------------------------------------------------
# clean references (exact frequencies; reference/golden/render_examples.py)
# ------------------------------------------------------------------------------------------------
REFS = [
    ("R1_authentic_cadence_dry", "01_golden_authentic_cadence", "V → I on the strict path (dry, exact 36-ET)",
     "The strict V → I path held long on a sustained clean organ tone, with no reverb, compression or modulation, "
     "so any beating comes from the intervals themselves."),
    ("R2_full_cadence_dry", "02_golden_full_cadence", "I–IV–V–I (dry)", "The full cadence with its golden passing chords, dry."),
    ("R3_staircase_dry", "04_golden_staircase", "Golden staircase (dry)", "The diatonic ladder with eight golden passing chords, dry."),
    ("R4_exact_phi_circle_drone", "07_golden_circle_drone", "Exact-φ golden circle drone",
     "The golden circle in EXACT golden ratios (55·φʲ Hz, octave-folded) rather than 36-ET: chain windows of three tones "
     "on the golden-spectrum clean tone, 13 s per chord."),
    ("R5_exact_beating_golden_seventh", "08_beating_golden_seventh", "Exact beating golden seventh",
     "Close-voiced Cg → Cg7 → vEg at 110 Hz in exact ratios on a harmonic tone. The golden seventh is "
     "1 : 2/φ : 4/φ² : 8/φ³. Its beats fall at 6.13, 7.58 and 9.37 Hz = 110·φ⁻⁶ × (1, 2/φ, 4/φ²), the golden triad in "
     "rhythm. There is also a beat at 12.26 Hz = 2 × 110·φ⁻⁶, the golden seventh against the root's octave, because "
     "8/φ³ = 2 − 2φ⁻⁶. No beat occurs at the golden seventh's own ratio."),
]


# ------------------------------------------------------------------------------------------------
# render + html
# ------------------------------------------------------------------------------------------------
def write_song(name: str, s: dict, comment: str) -> str:
    os.makedirs(SONGS, exist_ok=True)
    path = os.path.join(SONGS, name + ".songmap.yaml")
    head = (f"{comment}\nGenerated by tools/golden_suite.py. Render: songmap render "
            f"examples/golden/suite/{name}.songmap.yaml --mp3")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(f"# {ln}\n" for ln in head.splitlines()))
        f.write(yaml.safe_dump(s, sort_keys=False, allow_unicode=True, width=150))
    return path


def render_song(name: str, s: dict, comment: str) -> dict:
    path = write_song(name, s, comment)
    t0 = time.time()
    sm = yaml_form.load(path)
    r = render(sm)
    paths = write_outputs(r, os.path.join(BUILD, name), stems=False, mp3=True)
    shutil.copy(paths["mp3"], os.path.join(AUDIO, name + ".mp3"))
    spb = 60.0 / sm.tempo
    chords = [(round(sp.start * spb, 2), sp.chord.symbol) for sp in r.arrangement.harmony.spans if sp.chord and sp.onset]
    secs = round(len(r.audio) / 48000, 1)
    print(f"  {name}: {secs:.1f}s audio in {time.time() - t0:.1f}s")
    return {"file": name + ".mp3", "song": os.path.relpath(path, ROOT).replace("\\", "/"), "seconds": secs,
            "chords": chords}


def build_refs() -> list:
    src = os.path.join(ROOT, "reference", "golden", "out")
    out = []
    for name, wav, title, text in REFS:
        w = os.path.join(src, wav + ".wav")
        if not os.path.exists(w):
            continue
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", w, "-codec:a", "libmp3lame", "-q:a", "2",
                        os.path.join(AUDIO, name + ".mp3")], check=True)
        out.append({"kind": "single", "group": "Clean references", "title": title, "text": text,
                    "audio": [{"file": name + ".mp3", "song": "reference/golden/render_examples.py (exact frequencies)"}]})
    return out


def fmt_time(s):
    m, x = divmod(int(s), 60)
    return f"{m}:{x:02d}"



INTRO = """
<section id="intro">
<h2>Introduction</h2>

<h3>1. Notes: 36-ET and sixth-steps</h3>
<p>Ordinary Western tuning (12-ET) divides the octave into 12 equal semitones of 100 cents each. <b>36-ET</b> divides
every semitone into three equal <b>sixth-steps</b> of 33.3 cents (a sixth of a whole tone). 36-ET contains all twelve
ordinary notes exactly, plus two shifted copies of them: one a sixth-step higher and one a sixth-step lower. These are
the three <b>layers</b>.</p>
<table>
<tr><th>Mark</th><th>Meaning</th><th>Example</th></tr>
<tr><td><code>^</code></td><td>up one sixth-step (+33.3 c)</td><td>^C = C + 33 c, halfway-and-a-bit toward C#</td></tr>
<tr><td><code>v</code></td><td>down one sixth-step (−33.3 c)</td><td>vE = E − 33 c</td></tr>
<tr><td><code>^^</code>, <code>vv</code></td><td>two sixth-steps (±66.7 c)</td><td>^^G = G + 67 c = vA♭</td></tr>
</table>
<p>The marks are written <i>before</i> the note (ups-and-downs notation). Chord sizes are also given in sixth-steps above
the root: a major triad is (0, 12, 21), i.e. root, a third of 12 sixth-steps = 400 c, a fifth of 21 = 700 c.</p>

<h3>2. The golden ratio and the golden intervals</h3>
<p>φ = (1+√5)/2 ≈ 1.618. Played as a frequency ratio, φ is a sixth of 833.09 c, between the minor sixth (800) and the
major sixth (900). The <b>golden Pythagorean</b> system builds harmony from φ the way Pythagoras built it from the fifth 3/2.</p>
<table>
<tr><th>Interval</th><th>Exact ratio</th><th>Exact</th><th>36-ET</th><th>From C</th><th>Reading</th></tr>
<tr><td>golden sixth</td><td>φ</td><td>833.09 c</td><td>25 steps (833.33)</td><td>^A♭</td><td>the generator</td></tr>
<tr><td>golden third</td><td>2/φ</td><td>366.91 c</td><td>11 steps (366.67)</td><td>vE</td><td>2/3 of the way from minor to major third</td></tr>
<tr><td>golden fifth</td><td>4/φ²</td><td>733.82 c</td><td>22 steps (733.33)</td><td>^G</td><td>2/3 perfect, 1/3 augmented</td></tr>
<tr><td>golden seventh</td><td>8/φ³</td><td>1100.73 c</td><td>33 steps (1100.00)</td><td>B</td><td>three golden thirds; 8/φ³ = 2 − 2φ⁻⁶</td></tr>
<tr><td>silver (golden minor) third</td><td>chain distance 14</td><td>336.74 c</td><td>10 steps (333.33)</td><td>^E♭</td><td>2/3 minor, 1/3 major</td></tr>
<tr><td>bronze third</td><td>chain distance 11</td><td>436.01 c</td><td>13 steps (433.33)</td><td>^E</td><td>≈ 9/7, a third above major</td></tr>
</table>
<p>36-ET renders every golden interval within 0.75 c, well below what the ear can tell apart, so it hosts golden and
Western harmony together.</p>

<h3>3. Chords</h3>
<table>
<tr><th>Symbol</th><th>Notes on C</th><th>Sixth-steps</th><th>What it is</th></tr>
<tr><td><b>Cg</b> golden triad</td><td>C vE ^G</td><td>0, 11, 22</td><td>two stacked golden thirds, 1 : 2/φ : 4/φ²</td></tr>
<tr><td><b>Cg7</b> golden seventh</td><td>C vE ^G B</td><td>0, 11, 22, 33</td><td>three stacked golden thirds, 1 : 2/φ : 4/φ² : 8/φ³. In 36-ET this is Cmaj7 with the third bent down and the fifth bent up</td></tr>
<tr><td><b>Cs</b> silver triad</td><td>C ^E♭ vG</td><td>0, 10, 20</td><td>two stacked golden minor thirds</td></tr>
<tr><td><b>CT13</b> bronze triad</td><td>C ^E vA</td><td>0, 13, 26</td><td>two stacked bronze thirds; golden's mirror image through the augmented triad</td></tr>
</table>
<p><b>Reading chord names:</b>
<ul>
<li><code>vCg/G</code> is a golden triad rooted on vC with G in the bass.</li>
<li><code>C(v3,^5)</code> is C major with its third lowered and its fifth raised a sixth-step (= Cg).</li>
<li>Roman numerals carry the same marks: <code>vIg</code> is the golden triad a sixth-step below the tonic.</li>
</ul></p>
<p><b>The averaging principle.</b> Golden and silver chords are exact averages of ordinary triads, voice by voice:</p>
<ul>
<li><b>Cg = (C + Cm + Caug) / 3</b>: the third is (12+9+12)/3 = 11 and the fifth (21+21+24)/3 = 22.</li>
<li><b>Cs = (C + Cm + Cdim) / 3</b>: third 10, fifth 20.</li>
</ul>
<p>Golden is the balance point of the bright triads, silver of the dark ones. Along one straight line, diminished (9),
silver (10), golden (11), augmented (12) and bronze (13) are all chords of two equal stacked thirds of that many
sixth-steps.</p>

<h3>4. Scales</h3>
<p>Stacking golden sixths and folding them into one octave gives the golden chain. It forms well-formed scales (only two
step sizes) at 2, 3, 4, 7, 10, 13, 23 and 36 notes:</p>
<ul>
<li><b>golden7, the golden diatonic</b> = C C# vE vF ^G ^A♭ B. Its steps are 99.3 c and 267.6 c. It contains five
golden triads and four golden sevenths, including Cg7.</li>
<li><b>golden13, the golden "chromatic"</b> = C C# D vE♭ vE vF vF# ^F# ^G ^A♭ ^A B♭ B. Its steps are the golden
apotome φ³/4 = 99.27 c and the golden limma 2⁷/φ¹⁰ = 69.10 c. Thirteen golden sixths overshoot nine octaves by the
<b>golden comma</b> φ¹³/2⁹ = 30.17 c, just as twelve fifths overshoot seven octaves by the Pythagorean comma (23.46 c).
golden13 has 36 transpositions in 36-ET.</li>
<li><b>silver13</b> = golden13 with every ^ and v swapped. It contains silver triads instead of golden ones.</li>
</ul>

<h3>5. Golden passing harmony (diatonic home)</h3>
<p>Between two ordinary chords, each voice's half step is split into three sixth-steps. A whole step is split into three
double sixth-steps, or unevenly. The chords that appear on the way are <b>passing chords</b>, and the voice leading
itself decides which ones they are. Two systems:</p>
<ul>
<li><b>System 1 (strict):</b> every move is split evenly, so the path is unique.
  <ul>
  <li>At most one passing chord is golden.</li>
  <li>That happens exactly between two major (or two minor) triads whose roots are a third or a fifth apart (I–IV, I–V, ii–vi, iii–vi, and the chromatic mediants).</li>
  <li>The other passing chord is then bronze, or silver between augmented and diminished.</li>
  </ul></li>
<li><b>System 2 (natural):</b> half steps stay even, but whole steps may split unevenly.
  <ul>
  <li>Two different golden chords can follow each other.</li>
  <li>Roots a whole step apart pass through two golden chords on the chromatic root between, e.g. F – vF#g – ^F#g – G (the golden escalator).</li>
  </ul></li>
</ul>
<p><b>Example, V → I, System 1, four voices:</b></p>
<table>
<tr><th></th><th>G</th><th>passing 1</th><th>passing 2</th><th>C</th></tr>
<tr><td>soprano</td><td>D4</td><td>vE♭4</td><td>^E♭4</td><td>E4</td></tr>
<tr><td>alto</td><td>B3</td><td>^B3</td><td>vC4</td><td>C4</td></tr>
<tr><td>tenor</td><td>G3</td><td>G3</td><td>G3</td><td>G3</td></tr>
<tr><td>bass</td><td>G2</td><td>G2</td><td>G2</td><td>C3</td></tr>
<tr><td>chord</td><td>G</td><td>vE♭T13/G (bronze)</td><td><b>vCg/G</b> (golden)</td><td>C</td></tr>
</table>
<p>The golden chord vCg sits a sixth-step below the tonic, over the dominant bass, like a classical cadential six-four.</p>

<h3>6. Golden home (the inversion)</h3>
<p>Golden chords can also be the place of rest. They then move by their own steps:</p>
<ul>
<li>the <b>golden circle</b> (Cg → vEg → ^Gg …): neighbours share two notes, and the circle visits all 36 golden triads;</li>
<li><b>breathing</b> (Cg → Cg7 → vEg): add the next golden tone, then drop the oldest;</li>
<li><b>planing</b> (Cg → ^Cg): the whole chord glides a sixth-step.</li>
</ul>
<p><b>Timbre decides which world is at rest.</b> On tones with harmonic overtones, golden chords are rough and passing.
On golden-spectrum tones (overtones at 2^m·φ^n) the golden triad is the smoothest chord, and the ordinary triads become
the tension.</p>
<p><b>Beats.</b> A close golden seventh on harmonic tones beats at f₀·φ⁻⁶ × (1, 2/φ, 4/φ²), the golden <i>triad</i> in
rhythm. It also beats at 2f₀·φ⁻⁶, which is the golden seventh beating against the root's octave (because 8/φ³ = 2 − 2φ⁻⁶).
At f₀ = 110 Hz those rates are 6.13, 7.58, 9.37 and 12.26 Hz. Any calming effect of such beating is a hypothesis for
listening, not a claim.</p>

<h3>7. How these files were made</h3>
<ul>
<li>Every piece except the clean references is a SongMap song in 36-ET (<code>examples/golden/suite/</code>), rendered by the SongMap engine.</li>
<li>Instruments are stable: exact partials, with no vibrato, detune, drift or saturation.</li>
<li>The master is peak normalization only, with no compression.</li>
<li>The clean references use exact φ ratios instead of 36-ET.</li>
<li>Each technique card gives a short dry <b>definition</b>, then a piece showing the technique <b>in music</b>.</li>
</ul>
<p>Full theory: <code>docs/GOLDEN_THEORY.md</code> · math and history: <code>docs/GOLDEN_MATH.md</code> · every chord pair:
<code>docs/GOLDEN_PROGRESSIONS.md</code>.</p>
</section>
"""


def build_html(entries: list):
    groups = []
    for e in entries:
        if e["group"] not in groups:
            groups.append(e["group"])
    css = """
:root{--bg:#fbfaf7;--fg:#1f1d1a;--muted:#6b665d;--card:#fff;--line:#e6e1d8;--accent:#9a7414;--tag:#f3ead2}
@media (prefers-color-scheme: dark){:root{--bg:#161512;--fg:#ece8df;--muted:#a39d91;--card:#201e1a;--line:#34302a;--accent:#d9b24a;--tag:#3a3220}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:900px;margin:0 auto;padding:36px 16px 96px}h1{font-size:30px;margin:0 0 8px}
h2{font-size:21px;margin:44px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin:16px 0}
.card h3{margin:0 0 6px;font-size:18px}.tag{display:inline-block;background:var(--tag);color:var(--accent);border-radius:99px;
padding:1px 10px;font-size:12px;margin-left:8px;vertical-align:middle}.lbl{font-weight:600;margin-top:14px}
.meta{color:var(--muted);font-size:13px}audio{width:100%;margin:6px 0 2px}details{margin-top:8px}summary{cursor:pointer;color:var(--accent)}
code{font-size:12.5px}.cl{columns:3 190px;font-size:12.5px;color:var(--muted);margin-top:6px}p.lead{color:var(--muted)}
nav a{color:var(--accent);text-decoration:none;margin-right:14px;font-size:14px}
#intro h3{font-size:17px;margin:22px 0 6px}#intro table{border-collapse:collapse;width:100%;margin:8px 0 12px;font-size:14px}
#intro th,#intro td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}
#intro th{color:var(--muted);font-weight:600}.wrap{overflow-x:auto}"""
    H = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
         f"<title>Golden Harmony Audio</title><style>{css}</style></head><body><main>",
         "<h1>Golden Harmony: the audio suite</h1>",
         "<p class='lead'>Golden-ratio harmony in 36-ET, the sixth-step tuning, where ^ and v raise and lower a note by "
         "a sixth of a tone (33 c). Golden chords are stacked golden thirds (1 : 2/φ : 4/φ²), e.g. Cg = C vE ^G; Cg is "
         "also the exact average of C major, C minor and C augmented. Every piece except the clean references is a "
         "SongMap song (examples/golden/suite/) rendered by the SongMap engine. Instruments are stable, with no "
         "vibrato, detune, drift or saturation, and the master is peak normalization only. Theory: "
         "docs/GOLDEN_THEORY.md, docs/GOLDEN_MATH.md · dictionary: docs/GOLDEN_PROGRESSIONS.md.</p>",
         "<nav><a href='#intro'>Introduction</a>" + "".join(f"<a href='#g{i}'>{html.escape(g)}</a>" for i, g in enumerate(groups)) + "</nav>",
         INTRO.replace("<table>", "<div class='wrap'><table>").replace("</table>", "</table></div>")]
    for gi, g in enumerate(groups):
        H.append(f"<h2 id='g{gi}'>{html.escape(g)}</h2>")
        for e in [x for x in entries if x["group"] == g]:
            H.append("<div class='card'>")
            tag = f"<span class='tag'>{html.escape(e['system'])}</span>" if e.get("system") else ""
            H.append(f"<h3>{html.escape(e['title'])}{tag}</h3><div>{e['text']}</div>")
            for a in e["audio"]:
                if a.get("label"):
                    H.append(f"<div class='lbl'>{html.escape(a['label'])}</div>")
                if a.get("text"):
                    H.append(f"<div>{a['text']}</div>")
                H.append(f"<audio controls preload='none' src='{html.escape(a['file'])}'></audio>")
                bits = [f"<code>{html.escape(a['file'])}</code>"]
                if a.get("seconds"):
                    bits.append(fmt_time(a["seconds"]))
                bits.append(f"source <code>{html.escape(a['song'])}</code>")
                H.append(f"<div class='meta'>{' · '.join(bits)}</div>")
                if a.get("chords") and len(a["chords"]) > 8:
                    H.append("<details><summary>Chord timeline</summary><div class='cl'>"
                             + "<br>".join(f"{fmt_time(t)}.{int((t % 1) * 100):02d} {html.escape(c)}" for t, c in a["chords"])
                             + "</div></details>")
            if e.get("plan"):
                H.append("<details><summary>Key plan (144 sections, 2 bars each)</summary><div class='cl'>"
                         + "<br>".join(f"{i + 1}. {html.escape(p)}" for i, p in enumerate(e["plan"])) + "</div></details>")
            H.append("</div>")
    H.append("</main></body></html>")
    with open(os.path.join(AUDIO, "index.html"), "w", encoding="utf-8") as f:
        f.write("\n".join(H))


GROUP_OF = {"portfolios": lambda g: g == "Techniques: portfolios",
            "dictionary": lambda g: g.startswith("Dictionary"),
            "wtc": lambda g: g == "The Well-Tempered Golden Clavier",
            "refs": lambda g: g == "Clean references"}


def run_group(name: str) -> list:
    out = []
    if name == "portfolios":
        for p in portfolios():
            stem = p["id"] + "a_" + slug(p["title"].split(" (")[0].split(":")[0])[:40]
            d = render_song(stem + "_definition", p["definition"], p["title"] + " (definition)")
            q = render_song(p["id"] + "b_" + slug(p["piece"]["title"]), p["piece"], p["title"] + " (piece)")
            d.update(label="Definition", text=p["def_text"])
            q.update(label=f"In music: “{p['piece']['title']}”", text=p["piece_text"])
            out.append({"group": "Techniques: portfolios", "title": p["title"], "system": p["system"],
                        "text": p["technique"], "audio": [d, q]})
    elif name == "dictionary":
        for nm, s_, info in dictionary_songs():
            out.append({"group": info["group"], "title": info["title"], "text": info["text"],
                        "audio": [render_song(nm, s_, info["title"])]})
    elif name == "wtc":
        for nm, s_, info in wtc_song():
            out.append({"group": info["group"], "title": info["title"], "text": info["text"],
                        "audio": [render_song(nm, s_, info["title"])], "plan": info["plan"]})
    elif name == "refs":
        out = build_refs()
    return out


def refresh_texts(entries: list) -> list:
    """Re-read every description from the source definitions (no rendering)."""
    by_title, by_id = {}, {}
    for p in portfolios():
        by_title[p["title"]] = by_id[p["id"]] = {
            "title": p["title"], "text": p["technique"], "system": p["system"],
            "audio": [{"text": p["def_text"]}, {"text": p["piece_text"], "label": f"In music: “{p['piece']['title']}”"}]}
    for _, _, info in dictionary_songs() + wtc_song():
        by_title[info["title"]] = {"text": info["text"]}
    for _, _, title, text in REFS:
        by_title[title] = {"text": text}
    for e in entries:
        src = by_title.get(e["title"])
        if not src and e.get("audio"):                       # a retitled portfolio: match by its file id (P13a_...)
            src = by_id.get(str(e["audio"][0].get("file", ""))[:3])
            if src:
                e["title"] = src["title"]
        if not src:
            print("  (no source for)", e["title"])
            continue
        e["text"] = src["text"]
        if "system" in src:
            e["system"] = src["system"]
        for a_, s_ in zip(e["audio"], src.get("audio", [])):
            a_.update(s_)
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", choices=list(GROUP_OF))
    ap.add_argument("--html-only", action="store_true", help="refresh descriptions and rebuild index.html, no rendering")
    args = ap.parse_args()
    os.makedirs(AUDIO, exist_ok=True)
    meta_path = os.path.join(AUDIO, "entries.json")
    if args.html_only:
        entries = refresh_texts(json.load(open(meta_path, encoding="utf-8")))
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=1)
        build_html(entries)
        print(f"rebuilt {os.path.join(AUDIO, 'index.html')} ({len(entries)} entries)")
        return
    todo = args.only or list(GROUP_OF)
    old = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else []
    entries = [e for e in old if not any(GROUP_OF[t](e["group"]) for t in todo)]
    for t in todo:
        print(f"[{t}]")
        entries += run_group(t)
    order = ["Techniques: portfolios", "The Well-Tempered Golden Clavier", "Dictionary", "Dictionary: System 1 (strict)",
             "Dictionary: System 2 (natural)", "Clean references"]
    entries.sort(key=lambda e: order.index(e["group"]) if e["group"] in order else 99)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=1)
    build_html(entries)
    n = sum(len(e["audio"]) for e in entries)
    print(f"wrote {os.path.join(AUDIO, 'index.html')}: {len(entries)} entries, {n} audio files")


if __name__ == "__main__":
    main()
