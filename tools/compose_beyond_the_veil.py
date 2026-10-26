"""Transcribe the authored orchestral parts for Beyond the Veil.

Pitches, rhythms, voicings, entrances and expression below are compositional
decisions. This script checks bar arithmetic and writes editable .sm text;
it does not invent melodies, synthesize audio, or alter the engine.
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from songmap.parse.notes import parse_motif
from songmap.theory.harmony import Chord
from songmap.visual.score import spell

FOLDER = ROOT / "songs/golden_adagio"
SCORE = FOLDER / "beyond_the_veil.sm"
G9 = "maj9(v3,^5,^^9)"

# Four bars per phrase, one golden bar in every phrase. The original chosen B
# occupies phrases 0-1 exactly; subsequent phrases develop its pickup and lilt.
HARMONY = [
    ["Dm9", "Bbmaj9", "Gm9", "vDg7"],
    ["Dm9", "Bbmaj9", "Ag7", "Dm9"],
    ["Fmaj9", "C9", "vFg7", "Fmaj9"],
    ["Gm9", "Dm9", "vAg7", "A7"],
    ["Fmaj9", "Am7", "vBb" + G9, "Bbmaj9"],
    ["Gm9", "C9", "vFg7", "Fmaj9"],
    ["Dm9", "Gm9", "vC" + G9, "C9"],
    ["Fmaj9", "Ebmaj9", "vAb" + G9, "Abmaj9"],
    ["Abmaj9", "Cm7", "vDbg7", "Dbmaj9"],
    ["Bbm9", "Eb9", "vAbg7", "Abmaj9"],
    ["Fm9", "Bbm9", "vEb" + G9, "Eb9"],
    ["Abmaj9", "C7", "vDg7", "Dm9"],
    ["Dm9", "Bbmaj9", "vGg7", "Gm9"],
    ["Em7b5", "A7", "vDg7", "Dm9"],
    ["Dm9", "E9", "vA" + G9, "Amaj9"],
    ["Bm9", "E9", "vAg7", "Amaj9"],
    ["Dmaj9", "Bm9", "vEg7", "Em9"],
    ["Gmaj9", "A9", "vD" + G9, "Dmaj9"],
    ["F#m9", "Bm9", "vG" + G9, "Gmaj9"],
    ["Em9", "A9", "vDg7", "Dmaj9"],
    ["Dmaj9", "F#m9", "vGg7", "Gmaj9"],
    ["Bm9", "Em9", "vA" + G9, "A9"],
    ["Dmaj9", "Gmaj9", "vD" + G9, "Dmaj9"],
    ["Bm9", "Em9", "vDg7", "Dmaj9"],
]
KEYS = ["Dm"] * 2 + ["F"] + ["Dm"] + ["F"] * 3 + ["Ab"] * 5 + ["Dm"] * 2 + ["A"] * 2 + ["D"] * 8
TITLES = ["The chosen theme", "The first answer", "A wider window", "A question left open",
          "Into the sunlight", "The golden plagal glow", "The long ascent", "Beyond the veil",
          "The far choir", "Answer from the chapel", "A darker current", "Remembering home",
          "The still heart", "The returning pulse", "A door in A", "A brighter horizon",
          "The major return", "Vaults opening", "The ascending choir", "Gathering light",
          "The great arch", "The last question", "Benediction", "The final answer"]

# VIOLINS: note pass through all 96 bars, followed by phrase-specific expression.
# First eight bars are the chosen B. Later pickup intervals, sequences, registral
# displacement and a major-third transformation develop it rather than looping it.
STRINGS = [
    "=mp a4 d+4 f+4. e+8 | =p d+2 c+4 d+4 | =mp f+4 g+4 =mf a+4. =mp g+8 | =p ^f+2 a4 vc#+4",
    "=mp d+4 e+4 f+2_ | =mf a+4. =mp g+8 f+4 d+4 | =mp vc#+4 ^e+4 =mf g#+4. =mp ^e+8 | =p e+4 d+2_ r4",
    "=mp c+4 f+4 a+4. g+8 | =p g+2 e+4 d+4 | =mp ^ab+2 c+4 ve+4_ | =p e+4 f+4 g+4 a+4",
    "=mp bb4 d+4 f+4. e+8 | =p f+2 e+4 d+4 | =mp ^c+2 e+4 vg#+4_ | =p g+2 e+4 c#+4",
    "=mp a4 c+4 f+4. e+8 | =p g+2 e+4 c+4 | =mp f+2 va+4 ^c#+4_ | =p d+2 f+4 a+4",
    "=mp d+4 f+4 g+4 a+4 | =mf g+4 bb+4 a+4 g+4 | =mp ve+2 ^ab+4 c+4 | =p c+4 f+4 a+4. g+8",
    "=mp f+2 e+4 d+4 | =p bb4 d+4 f+4 g+4 | =mp ^d+2 ^eb+4 g+4 | =p e+2 d+4 c+8 bb8",
    "=mp a+4 g+4 f+4 e+4 | =p g+2 f+4 eb+4 | =mp ^bb+2 vg+4 ^b4_ | =p c+4 eb+4 g+4 ab+4",
    "=p eb+4 g+4 ab+4. g+8 | =mp eb+4 g+4 bb+4. ab+8 | =p ^e+2 ab+4 vc+4_ | =mp f+2 eb+4 db+4",
    "=p db+4 f+4 ab+4. g+8 | =mp g+2 f+4 eb+4 | =p ^b2_ eb+4 vg+4 | =mp g+4 ab+4 bb+4 ab+4",
    "=mp ab+4 g+4 f+4 c+4 | =p db+4 f+4 ab+4 f+4 | =mp ^f+2 vd+4 bb4 | =p g+2 f+4 eb+8 db+8",
    "=mp c+4 eb+4 g+4 ab+4 | =mf bb+2 g+4 e+4 | =p ^f+2 a+4 vc#+4 | =pp d+4 e+4 f+4 e+4",
    "r1 | r1 | r1 | =pp d+2 r2",
    "r1 | r1 | r1 | =p r2 a4 c+4",
    "=p d+4 e+4 f+4. e+8 | =mp f#+2 e+4 d+4 | =p ^b+2 vg#+4 e+4 | =mp c#+4 e+4 g#+4 a+4",
    "=mp f#+4 b+4 a+4 f#+4 | =mf g#+2 f#+4 e+4 | =p ^c+4 e+4 vg#+4 e+4 | =mp b+4 a+4 g#+4 e+4",
    "=mf a4 d+4 f#+4. e+8 | =mp f#+2 e+4 d+4 | =mf b4 veb+4 ^g+2_ | =mp g+4 f#+4 e+2",
    "=mf b4 d+4 g+4. f#+8 | =mp e+4 g+4 b+4 a+4 | =mf ^e+2 a+4 ^f+4_ | =mp f#+2 e+4 d+4",
    "=mf c#+4 f#+4 a+4. g#+8 | =mp f#+4 a+4 c#++4 b+4 | =mf ^a+2 d+4 ^bb+4_ | =mp b+2 a+4 g+4",
    "=mf g+4 f#+4 e+4 b4 | =mp e+4 g+4 b+4 a+4 | =mf vc#++2 a+4 ^f+4_ | =mp f#+4 d+4 f#+4 a+4",
    "=f a+4 d++2_ c#++4 | =mf c#++2 b+4 a+4 | =mf ^bb+2 d++4 vf#+4_ | =mp f#+2 g+4 b+4",
    "=mf b+4 a+4 f#+4 d+4 | =mp e+4 g+4 b+4 a+4 | =mf ^b+2 vg#+4 ^c+4_ | =mp c#+4 e+4 g+4 e+4",
    "=mp f#+2 e+4 d+4 | =p b4 d+4 f#+4 g+4 | =mp ^e+2 a4 ^f+4_ | =p f#+4 e+4 d+2",
    "=p d+4 c#+4 b4 f#4 | =pp g4 b4 d+4 e+4 | =p ^f+2 vc#+4 a4 | =pp e+4 d+2_ r4",
]

# CELLO: an independently written lower conversation. It carries the chosen
# motif at the still point; the last two movements use firmer contrary motion.
# Breaths, quiet pickups and restrained cadences are written at note level.
CELLO = [
    "=p d-2 a-2 | =pp f-2 d-2 | =p g-2 d4 bb-4 | =pp vd-2 ^f-2",
    "=p f-2 e-4 d-4 | =pp d-2 f-2 | =p a-2 vc#4 ^e4 | =pp e2 d-4 r4",
    "=p f-2 c2 | =mp e-2 bb-2 | =p vf-2 ^ab-2 | =pp a-2 g-4 f-4",
    "=p g-2 bb-4 d4 | =mp a-2 f-2 | =p va-2 ^c2 | =pp e2 c#4 a-4",
    "=p f-2 a-2 | =mp c2 e2 | =p vbb-2 ^c#2 | =pp d2 c2",
    "=mp g-2 d2 | =p bb-2 e-2 | =mp c2 ve2 | =p a-2 c2",
    "=mp d2 c4 a-4 | =p g-2 bb-2 | =mp vc2 ^eb2 | =p e2 d4 bb-4",
    "=mp f-2 a-4 c4 | =p g-2 bb-2 | =mp vab-2 ^b-2 | =pp c2 eb2",
    "=p ab-2 eb2 | =mp g-2 bb-2 | =p vdb2 ^e2 | =pp f2 eb4 db4",
    "=p bb-2 db2 | =mp g-2 db2 | =p vab-2 ^b-2 | =pp c2 bb-4 ab-4",
    "=mp f-2 c2 | =p db2 f2 | =mp veb2 ^f#2 | =p g2 f4 eb4",
    "=mp eb2 c2 | =p bb-2 e2 | =pp vd2 ^f2 | =pp f2 e4 d4",
    "=p a-4 d4 f4. e8 | =pp d2 c4 d4 | =p ^bb-2 d4 vf#4 | =pp f2 bb-4 g-4",
    "=p bb-4 d4 e4 g4 | =mp e2 c#4 a-4 | =p ^f2 a-4 vc#4 | =pp e4 d2 r4",
    "=p d2 f2 | =mp g#-2 b-2 | =p va-2 ^c2 | =mp c#2 e2",
    "=mp b-2 f#2 | =p g#2 f#4 e4 | =mp e2 vg#-2 | =p c#2 b-4 a-4",
    "=mp d2 f#4 a4 | =mf f#2 d2 | =mp ve2 ^g2 | =p b-2 d2",
    "=mf g-2 b-4 d4 | =mp e2 g2 | =mf vd2 ^f2 | =mp f#2 e4 d4",
    "=mf f#2 a4 c#+4 | =mp b-2 d2 | =mf vg-2 ^bb-2 | =mp d2 f#2",
    "=mf e2 g4 b4 | =mp a2 g4 e4 | =mf vc#2 a-4 ^f4 | =mp f#2 e4 d4",
    "=f d2 a4 f#4 | =mf c#2 e2 | =mf vg-2 ^bb-4 d4 | =mp g2 f#4 d4",
    "=mf b-2 d4 f#4 | =mp e2 g2 | =mf va-2 ^c2 | =mp c#2 g-2",
    "=mp f#2 a-2 | =p b-2 d2 | =mp vd2 ^f2 | =p f#2 e4 d4",
    "=p b-2 d2 | =pp e2 b-2 | =p vd2 ^f2 | =pp f#-2 d-2_",
]

# BOWED BASS: deliberately simple pillars, with chosen fifths and inversions
# at the cadences. The golden root replaces its Western neighbor completely.
# Expressions deepen at the late return; short releases leave modulations clear.
BASS = [
    "=p d--2 a--2 | =pp bb---1 | =p g--2 d--2 | =pp vd--1",
    "=p d--2 a--2 | =pp bb---1 | =p a--1 | =pp d--2. r4",
    "=p f--1 | =mp c--2 g--2 | =p vf--1 | =pp f--2 c--2",
    "=p g--1 | =mp d--2 a--2 | =p va--1 | =pp a--2 e--2",
    "=p f--1 | =mp a--1 | =p vbb---1 | =pp bb---1",
    "=mp g--1 | =p c--2 g--2 | =mp vf--1 | =p f--1",
    "=mp d--1 | =p g--1 | =mp vc--1 | =p c--2 g--2",
    "=mp f--1 | =p eb--1 | =mp vab--1 | =pp ab--1",
    "=p ab--1 | =mp c--1 | =p vdb--1 | =pp db--1",
    "=p bb---1 | =mp eb--2 bb---2 | =p vab--1 | =pp ab--1",
    "=mp f--1 | =p bb---1 | =mp veb--1 | =p eb--1",
    "=mp ab--1 | =p c--1 | =pp vd--1 | =pp d--2 r2",
    "=pp d--1 | =pp bb---1 | =pp vg--1 | =pp g--2 r2",
    "=p e--1 | =mp a--2 e--2 | =p vd--1 | =pp d--2 r2",
    "=p d--1 | =mp e--2 b---2 | =p va--1 | =mp a--1",
    "=mp b---1 | =p e--2 b---2 | =mp va--1 | =p a--2 e--2",
    "=mf d--1 | =mp b---1 | =mf ve--1 | =mp e--2 b---2",
    "=mf g--1 | =mp a--2 e--2 | =mf vd--1 | =mp d--1",
    "=mf f#--1 | =mp b---1 | =mf vg--1 | =mp g--2 d--2",
    "=mf e--1 | =mp a--1 | =mf vd--1 | =mp d--1",
    "=f d--2 a--2 | =mf f#--1 | =mf vg--1 | =mp g--2 d--2",
    "=mf b---1 | =mp e--1 | =mf va--1 | =mp a--1",
    "=mp d--1 | =p g--1 | =mp vd--1 | =p d--1",
    "=p b---1 | =pp e--1 | =p vd--1 | =pp d--1_",
]

# Chosen chord voicings for the piano/organ bed. A low ninth's neighboring third
# is separated by an octave. The bass supplies roots omitted by the piano.
VOICINGS = {
    "Dm9": "f-,a-,c,e", "Bbmaj9": "d-,f-,a-,c", "Gm9": "bb-,d,f,a",
    "vDg7": "vd-,^f-,a-,vc#", "Ag7": "g#-,vc#,^e,a", "A7": "g-,c#,e,a",
    "Fmaj9": "a-,c,e,g", "C9": "e-,bb-,d,g", "vFg7": "vf-,^ab-,c,ve",
    "Am7": "c,e,g,a", "vBb" + G9: "vbb--,^c#-,f-,va-,^c", "Em7b5": "g-,bb-,d,e",
    "vAg7": "^c,e,vg#-,va", "vC" + G9: "vc-,^eb-,g-,vb-,^d",
    "Ebmaj9": "g-,bb-,d,f", "vAb" + G9: "vab-,^bb-,eb,vg,^b",
    "Abmaj9": "c-,g-,bb-,eb", "Cm7": "eb-,g-,bb-,c", "vDbg7": "vdb-,^e-,ab-,vc",
    "Dbmaj9": "f-,ab-,c,eb", "Bbm9": "db-,f-,ab-,c", "Eb9": "g-,db,f,bb",
    "Fm9": "ab-,c,eb,g", "vEb" + G9: "veb-,^f#-,bb-,vd,^f", "C7": "e-,bb-,c,g",
    "vGg7": "vg-,^bb-,d,vf#", "E9": "g#-,d,f#,b", "vA" + G9: "^c,e,vg#-,^b",
    "Amaj9": "c#-,g#-,b-,e", "Bm9": "d-,a-,c#,f#", "Dmaj9": "f#-,c#,e,a",
    "Em9": "g-,d,f#,b", "vEg7": "ve-,^g-,b-,veb", "Gmaj9": "b-,d,f#,a",
    "A9": "c#,g,b,e+", "vD" + G9: "vd-,^f-,a-,vc#,^e", "F#m9": "a-,e,g#,c#+",
    "vG" + G9: "vg-,^bb-,d,vf#,^a",
}

# Other instruments and the score writer follow below, after their own full-form
# note/expression passes. The arrays preserve the manuscript's phrase boundaries.

# FLUTE: an occasional answering singer. It leaves the violin's opening alone,
# joins the foreign-key choir, then breathes with the late orchestral return.
# The still-point line is deliberately simple; it does not compete with cello B.
FLUTE = [
    None, "r1 | r1 | r1 | =pp e+4 d+2 r4",
    "r1 | r1 | =pp r2 c+2 | =p a+2 g+4 f+4", None,
    "=pp c+2 r2 | =p e+2 g+2 | =pp f+2 r2 | =p a+2 f+4 r4", None,
    "r1 | r1 | =pp g+2 r2 | =p e+2 d+4 r4",
    "r1 | r1 | r1 | =pp eb+1",
    "=pp eb+2 r2 | =p g+2 eb+4 r4 | =pp ab+2 r2 | =p f+2 eb+4 db+4", None,
    "r1 | r1 | =pp bb+2 r2 | =p bb+2 f+4 r4", None,
    "=pp e+2 d+2 | =p f+2 d+2 | =pp d+1 | =pp d+2 r2", None,
    "r1 | =p b+2 g#+2 | =pp e+2 r2 | =p e+2 c#+4 r4", None, None,
    "=p d+2 r2 | r1 | =pp a+2 r2 | =p a+2 f#+4 r4", None,
    "=mp b+2 g+2 | =p e+2 r2 | =pp a+2 ^f+2 | =p f#+1",
    "=mp d+1 | =p c#+2 r2 | =pp d+1 | =p d+2 r2", None,
    "=p a+2 r2 | =pp d+2 r2 | =p a+2 r2 | =pp f#+2 e+4 r4", None,
]

# HORN: an inner choral voice, in its recorded range, never a fanfare taking
# the violin's place. Golden raised/lowered neighbors resolve in this part too.
HORN = [
    None, None,
    "=p a-2 c4 e4 | =pp bb-2 g-2 | =p c1 | =pp e2 c2",
    "=p bb-2 d4 f4 | =mp a-2 c4 e4 | =p e2 vg#-4 ^c4 | =pp c#2 e4 g-4",
    None,
    "=p bb-2 d2 | =mp e2 bb-2 | =p ve2 c2 | =pp c2 a-2", None,
    "=p a-2 c2 | =mp g-2 bb-2 | =p eb2 vg2 | r1",
    None,
    "=p db2 f2 | =mp g-2 db2 | =p eb2 ^b-2 | =pp g-2 c2",
    None,
    "=p eb2 c2 | =mp e2 bb-2 | =pp ^f2 a-2 | =pp d2 a-2",
    None, None, None,
    "=p f#2 d2 | =mp d2 g#-2 | =p vg#-2 e2 | =pp c#2 e2",
    "=mp f#2 a-2 | =mf d2 f#2 | =mp ^g-2 b-2 | =p g-2 b-2", None,
    "=mp c#2 e2 | =mf f#2 d2 | =mp vf#2 d2 | =p f#2 d2",
    "=mp g-2 b-2 | =mf g-2 c#2 | =mp ^f2 vc#2 | =p f#2 e2",
    "=mf a-2 d2 | =mp e2 c#2 | =mf d2 ^bb-2 | =p b-2 d2",
    "=mp a-2 f#2 | =mf g-2 b-2 | =mp vg#-2 e2 | =p c#2 g-2",
    None, None,
]

# HARP: written answers and isolated ripples, not a continuous eight-note loop.
# Its gold bars use the actual golden tones; it rests through the main apex so
# the string arch and wind choir can carry that event without a competing hook.
HARP = [
    "=pp r2 a8 =p c+8 =pp a4 | r1 | r2 =p d+8 =pp f+8 =p a+4 | r1",
    "=pp r2 e4 =p a4 | =pp r2 f4 =p c+4 | r1 | =pp a2 =p d+4 r4",
    "=pp r2 c+8 e+8 =p a+4 | =pp r2 bb8 d+8 =p g+4 | =pp r2 c+8 ve+8 =p ^ab+4 | r1",
    "=pp r2 d+8 f+8 =p a+4 | r1 | =pp r2 e+8 ^c+8 =p vg#+4 | =pp r2 e+4 c#+4",
    "r1 | r1 | =pp r2 f+8 va+8 =p ^c#++4 | =pp r2 c+8 d+8 =p f+4",
    "=pp bb4 d+4 =p f+4 r4 | =pp r2 g8 bb8 =p d+4 | r1 | =pp r2 c+8 e+8 =p a+4",
    "=pp r2 a4 c+4 | r1 | =pp r2 g8 vb8 =p ^d+4 | =pp r2 g4 d+4",
    "r1 | =pp r2 bb8 d+8 =p f+4 | r1 | =pp r2 eb+8 g+8 =p bb+4",
    "=pp r2 eb4 g4 | r2 =p g4 =pp bb4 | r2 ab4 =p vc+4 | r1",
    "r1 | =pp r2 bb4 db+4 | r1 | =p r2 eb+4 =pp c+4",
    "r1 | =pp r2 db+8 f+8 =p ab+4 | r1 | =pp r2 bb4 =p f+4",
    "=pp r2 c+4 eb+4 | r1 | r1 | r1", None,
    "=pp r2 bb4 g4 | =p r2 e+4 =pp c#+4 | r1 | r1",
    "=pp r2 a4 c+4 | =p r2 b4 =pp d+4 | r2 e+8 vg#+8 =p ^b+4 | r1",
    "=pp r2 f#+8 a+8 =p c#++4 | r1 | =pp r2 e+4 ^c+4 | r2 b4 =p e+4",
    "=pp r2 a8 c#+8 =p e+4 | =pp r2 f#4 a4 | =p r2 b4 =pp ^g4 | r1", None,
    "=pp r2 c#+8 e+8 =p g#+4 | =pp r2 a4 c#+4 | r1 | =p r2 a4 =pp d+4",
    None, None,
    "=pp r2 a4 c#+4 | =p r2 b4 =pp f#+4 | r2 e+8 vg#+8 =p ^b+4 | r1",
    "=pp r2 a8 c#+8 =p e+4 | =pp r2 b8 d+8 =p f#+4 | r1 | =pp r2 e+4 c#+4",
    "r1 | r1 | r1 | =pp a4 e+4 =p d+2_",
]

# PIANO: the explicit voicing bank above is this instrument's pitch pass.
# Here are its separate attack, duration, rest and dynamic decisions. @ means
# that bar's authored voicing; it is expanded to literal notes in the score.
PIANO = [
    "=p @2 =pp @2 | =p @2 =pp @2 | =p @2 =pp @2 | =pp @2 =p @2",
    "=p @2 =pp @2 | =p @2 =pp @2 | =pp @2 =p @2 | =p @2 =pp @2",
    "=p @2 r2 | =pp @1 | =p @2 r2 | =pp @1",
    "=p @2 r2 | =pp @2 r2 | =p @1 | =pp @2 r2",
    "=p @2 =pp @2 | =pp @2 r2 | =p @1 | =pp @2 r2",
    "=p @2 r2 | =pp @2 r2 | =p @1 | =pp @1",
    "=p @2 r2 | =pp @2 r2 | =p @1 | =pp @2 r2",
    None, None, None, None, None,
    "=pp @1 | =pp @2 r2 | =p @1 | =pp @2 r2",
    "=p @2 r2 | =pp @2 r2 | =p @1 | =pp @2 r2",
    "=p @2 =pp @2 | =p @2 r2 | =mp @1 | =p @2 r2",
    "=mp @2 r2 | =p @2 r2 | =mp @1 | =p @2 r2",
    None, None, None, None,
    "=mf @2 r2 | r1 | r1 | r1", None,
    "=p @2 r2 | r1 | =pp @1 | =pp @2 r2",
    "=pp @2 r2 | r1 | =pp @1 | =pp @2 r2",
]

# ORGAN: sustained inner harmony replaces the piano in the far chapel and the
# final orchestral wave. Entries, breaths and register are selected for the form.
# Its harmonic spectrum is deliberately restrained against the acoustic strings.
ORGAN = [
    None, None,
    None, None, None, None,
    None,
    "=p @1 | =pp @1 | =p @1 | =pp @1",
    "=pp @1 | =p @1 | =pp @1 | =p @1",
    "=pp @1 | =p @1 | =pp @1 | =p @1",
    "=p @1 | =pp @1 | =p @1 | =pp @1",
    "=p @1 | =pp @1 | =pp @1 | =pp @1",
    None, None, None, None,
    "=mp @1 | =p @1 | =mp @1 | =p @1",
    "=mp @1 | =p @1 | =mp @1 | =p @1",
    "=mp @1 | =mf @1 | =mp @1 | =p @1",
    "=mf @1 | =mp @1 | =mf @1 | =mp @1",
    "=f @1 | =mf @1 | =mf @1 | =mp @1",
    "=mf @1 | =mp @1 | =mf @1 | =mp @1",
    "=mp @1 | =p @1 | =mp @1 | =p @1",
    "=p @1 | =pp @1 | =p @1 | =pp @1",
]

VOICINGS["vAbg7"] = "vab-,^b-,eb,vg"
PARTS = {"melody": STRINGS, "cello": CELLO, "basslow": BASS, "flute": FLUTE,
         "horn": HORN, "harp": HARP, "piano": PIANO, "organ": ORGAN}

HEADER = '''# Beyond the Veil - five-minute Western/golden adagio developed from the user's chosen motif B.
# review: pending - Full arrangement awaiting listening review; B was selected in the Studio A/B test.
# 96 bars at 80 BPM = 4:48, then a twelve-second resonance tail. No quoted melody from an existing work.
# Harmonic duration: 72 Western bars / 24 golden bars (75% / 25%), excluding the final decay.
# The opening eight-bar violin melody preserves the chosen B. Later phrases develop its pickup, rhythm and answer.
# Keys: D minor, relative F, distant Ab, D minor memory, A major threshold, and a D-major orchestral return.
# Golden shadows replace the Western thirds/other altered tones, then resolve at the next Western arrival.
# All eight parts have separate full-form note/expression passes in tools/compose_beyond_the_veil.py.
# Melodies use phrase breaths and register separation; golden notes are not piled against their unaltered doubles.
# Binaural pairs follow every chord, Western or golden. Their centers use the score's tempered pitch classes.
# Every beat difference is its own carrier frequency / 32: a five-octave reduction that stays proportional.
song "Beyond the Veil" 80 4/4 Dm fps=30 seed=241026 tail=12 tuning=36edo mood=ambient
inst melody=sampler/violins(attack=.065,release_mul=.13) cello=sampler/cello(attack=.065,release_mul=.13) basslow=sampler/double_bass_arco(attack=.08,release_mul=.12) flute=sampler/flute(attack=.06,release_mul=.15) horn=sampler/horn(attack=.08,release_mul=.15) harp=sampler/folk_harp(release_mul=.16) piano=sampler/grand_piano(release_mul=.13) organ=clean/organ(partials=8,rolloff=1.85,attack=.3,release=.16,vel_bright=.08)
groove hum=4,3,.012 metric=.06
feel melody gate=.94 hum=5,3,.014 arch=.2
feel cello gate=.91 hum=5,3,.014 arch=.18
feel basslow gate=.91 hum=2,2,.01 arch=.12
feel flute gate=.91 hum=5,3,.012 arch=.22
feel horn gate=.92 hum=5,3,.014 arch=.18
feel harp gate=.86 hum=3,2,.012 arch=.12
feel piano gate=.9 hum=3,2,.01 arch=.12
feel organ gate=.94 hum=1,1,.008 arch=.1
set returns={hall: {type: reverb, seconds: 3.8, predelay: .045, damping: .7, early: 12, width: 1.12}}
binaural E4 C4 A3 F3 D3 beat=octave octaves=5 level=-15 fade=8 glide=.28 breathe=2 breath=2 carve=true
'''


def bars(phrase, harmony, part, phrase_index):
    if phrase is None:
        return [None] * 4
    chunks = [x.strip() for x in phrase.split("|")]
    assert len(chunks) == 4, (part, phrase_index, len(chunks))
    out = []
    for j, (chunk, chord) in enumerate(zip(chunks, harmony)):
        if "@" in chunk:
            chunk = chunk.replace("@", "[" + VOICINGS[chord] + "]")
        # A one-bar inline fragment otherwise has no printed bar separator, so
        # explicitly check its full written duration, including trailing rests.
        events = parse_motif(chunk, name=f"{part} phrase {phrase_index} bar {j}")
        assert abs(events.length - 4) < 1e-8, (part, phrase_index, j, events.length)
        out.append(chunk)
    return out


def main():
    assert all(len(p) == 24 for p in PARTS.values())
    assert len(KEYS) == 24
    manuscript = {part: [bars(phrase, h, part, i) for i, (phrase, h) in enumerate(zip(phrases, HARMONY))]
                  for part, phrases in PARTS.items()}
    lines = [HEADER]
    info = []
    for i, chords in enumerate(HARMONY):
        lines.append(f"\n# Phrase {i + 1}: {TITLES[i]} - {i * 12 // 60}:{i * 12 % 60:02d}; local key {KEYS[i]}.")
        for j, chord in enumerate(chords):
            name = f"p{i + 1:02d}_{j + 1}"
            parts = []
            for part in PARTS:
                text = manuscript[part][i][j]
                if text is not None and text != "r1":
                    parts.append(f'{part}:{{notes: "{text}"}}')
            h = Chord.parse(chord)
            # One octave-folded center per actual chord tone; the compound ninth
            # stays one octave above the other folded tones when present.
            carrier_pitches = sorted({48 + (h.root + v) % 12 + (12 if v >= 12 else 0) for v in h.intervals}, reverse=True)
            carriers = [round(p, 9) for p in carrier_pitches]
            gain = -1 if i < 7 else -2 if i < 12 else -4 if i < 14 else 0 if i < 19 else 1 if i < 22 else -2
            if i == 23 and j == 3:
                gain = "-4>-18"
            setting = f'binaural={{carriers: {carriers}, gain_db: {json.dumps(gain)}}}'
            lines.append(f'{name} 1 | ' + " ".join(parts) + f' chords="{chord}:1" key="{KEYS[i]}" dyn=mp {setting}')
            info.append({"id": name, "phrase": i, "bar_in_phrase": j, "title": TITLES[i], "chord": chord,
                         "kind": "golden" if "g7" in chord or "(v3,^5,^^9)" in chord else "western",
                         "start": (i * 4 + j) * 3, "end": (i * 4 + j + 1) * 3, "key": KEYS[i]})
    lines += ["\n# Ensemble balance: melody first; horn and bass stay beneath it. The broad apex is phrase 21.",
              "mix melody -3 hall=.28 pan=-.12 | cello -9 hall=.27 pan=.17 | basslow -18 hall=.13 | flute -7 hall=.3 pan=-.28 | horn -13 hall=.3 pan=.28 | harp -4 hall=.32 pan=-.32 | piano -9 hall=.24 pan=.14 | organ -31 hall=.4",
              "master clean ceiling=-2\n"]
    FOLDER.mkdir(exist_ok=True)
    SCORE.write_text("\n".join(lines), encoding="utf-8")
    (FOLDER / "composition.json").write_text(json.dumps(info, indent=2) + "\n")
    print(f"Wrote {SCORE.relative_to(ROOT)}: 24 authored four-bar phrases, 96 binaural harmony states.")


if __name__ == "__main__":
    main()
