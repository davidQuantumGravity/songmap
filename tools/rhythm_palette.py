"""Build editable bass/drum auditions, groove templates and their local listening page.

Run with --prepare, --render, --gallery, --audit (flags can be combined).
The samples installer remains the only downloader. This tool writes musical .sm scores.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import html
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLLECTION = ROOT / "songs/rhythm_palette"
BASSES = ["jazz_bass", "jazz_bass_staccato", "flatwound_bass", "roundwound_bass",
          "bass_vi_roundwound", "bass_vi_pick", "bass_vi_muted", "bass_vi_finger"]
SYNTH_BASSES = ["round_sub", "rubber", "acid", "mellow_square", "disco_pluck", "warm_saw", "reedy", "growl"]
ACOUSTIC_BASSES = ["double_bass", "upright_bass", "upright_bass_arco", "double_bass_arco"]
KITS = ["black_pearl", "red_zeppelin", "blonde_bop", "blonde_bop_rods"]
ELECTRONIC = list(zip(
    ["deep_808", "tight_808", "club_909", "dry_punch", "soft_sine", "hard_click", "low_thud", "distorted"],
    ["soft_wires", "tight_pop", "fat_808", "bright_909", "dry_rim", "dusty", "noisy", "industrial"],
    ["fine_closed", "dark_closed", "bright_closed", "loose_closed", "fine_closed", "bright_closed", "dark_closed", "grain"],
    ["soft_open", "metal_open", "metal_open", "soft_open", "sizzle", "sizzle", "soft_open", "metal_open"]))


def acoustic_kit(name: str) -> str:
    lanes = {"kick": "kick", "snare": "snare", "rim": "sidestick", "fill": "snare_edge",
             "hat": "hat", "hat16": "hat", "ohat": "hat_open", "pedal": "hat_pedal", "semi": "hat_semi",
             "tom_high": "tom", "tom_low": "floor_tom", "tom_edge": "tom_edge",
             "crash": "crash", "ride": "ride", "bell": "ride_bell", "splash": "splash", "china": "china"}
    return "kit " + " ".join(f"{lane}=sampler/{name}_{piece}(gain_db=0,pan=0)" for lane, piece in lanes.items())


def electronic_kit(index: int) -> str:
    kick, snare, hat, opened = ELECTRONIC[index]
    return (f"kit kick=kick/{kick}(gain_db=0) snare=snare/{snare}(gain_db=-3) "
            f"fill=snare/{snare}(gain_db=-3) rim=snare/dry_rim(gain_db=-6) "
            f"hat=hat/{hat}(gain_db=-8) ohat=hat/{opened}(gain_db=-10)")


def _write(relative: str, score: str, group: str, title: str, description: str, rows: list) -> None:
    path = COLLECTION / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(score.rstrip() + "\n", encoding="utf-8")
    rows.append({"source": relative, "id": path.stem, "group": group, "title": title, "description": description})


def prepare() -> list[dict]:
    from songmap.instruments.sampler.library import manifest
    rows: list[dict] = []
    voices = [(name, "sampler/" + name, manifest()["voices"][name]["title"],
               manifest()["voices"][name]["description"]) for name in BASSES + ACOUSTIC_BASSES]
    voices += [("synth_" + name, "bass/" + name, name.replace("_", " ").title(),
                "Synthesized bass; compare its envelope and harmonic colour on the same phrase.") for name in SYNTH_BASSES]
    for name, ref, title, description in voices:
        score = f'''# {title}: {description}
# Compare the soft and firm phrases; then listen to short notes and space between answers.
song "Bass: {title}" 100 4/4 Dm fps=30 seed=82 tail=2 mood=balanced
inst bass={ref}(gain_db=0)
chords Dm
soft 2 | bass:{{rel: "R/4. r/8 5/8 R+/8 5/4 | R/4 r/8 5/8 R/4 r/4", oct: -2}} dyn=p<mp
answer 2 | bass:{{rel: "R/8' R r/8 5/8 R+/4 r/4 | 5/4 R/2 r/4", oct: -2}} dyn=mf>mp
mix bass -4 sc=0
master standard lufs=-18 glue=none
'''
        if name.endswith("_arco"):
            score = score.replace('R/4. r/8 5/8 R+/8 5/4 | R/4 r/8 5/8 R/4 r/4',
                                  'R/2_ 5/2_ | R/2. r/4')
            score = score.replace("R/8' R r/8 5/8 R+/4 r/4 | 5/4 R/2 r/4",
                                  'R/2_ R+/2_ | 5/2_ R/4 r/4')
        _write("bass/" + name + ".sm", score, "Acoustic bass" if name in ACOUSTIC_BASSES else
               "Recorded bass" if ref.startswith("sampler") else "Synth bass", title, description, rows)
    for name in KITS:
        title = name.replace("_", " ").title()
        score = f'''# {title}: hear the kit in a pocket, then exposed articulations.
# Hat strokes stop during the two-hand tom answer; each cymbal gets room to decay.
song "Kit: {title}" 100 4/4 Dm fps=30 seed=82 tail=3 mood=balanced
{acoustic_kit(name)}
groove swing=.54/16
feel snare offset=7
pocket 2 | drums:pocket dyn=mp<mf
edges 1 | drums:{{rim: "x...x...x...x...", semi: "..x...x...x...x."}} dyn=mp
hands 1 | drums:{{tom_high: "x...x...........", tom_edge: "........x.x.....", tom_low: "............x.x.", kick: "X..............."}} dyn=mp<f
pedal 1 | drums:{{ohat: "x.......x.......", pedal: "....x.......x..."}} dyn=mp
metal 2 | drums:{{ride: {{steps: "x.x.x.x.x.x.x.x.", vel: [.52,.3,.44,.28]}}, bell: "......x.......x.", kick: "X.......x.......", snare: "....X.......X..."}} dyn=mf
ending 1 | drums:{{kick: "X...............", crash: "X...............", splash: "....x...........", china: "........x......."}} dyn=mf>p
mix drums -5 hall=.025
master standard lufs=-18 glue=none
'''
        _write("kits/" + name + ".sm", score, "Acoustic kits", title,
               "Five recorded dynamic layers per piece. Center/edge hits, pedal/open hats, toms and cymbals. No recorded round robins.", rows)
    studio = (COLLECTION / "kits/black_pearl.sm").read_text(encoding="utf-8")
    studio = studio.replace('song "Kit: Black Pearl"', 'song "Kit: Studio alternate takes"')
    studio = studio.replace("groove swing", "kit snare=sampler/studio_snare_2(gain_db=0) fill=sampler/studio_snare_3(gain_db=0) rim=sampler/studio_snare_2_rim(gain_db=0) tom_high=sampler/studio_tom_high_stick(gain_db=0) tom_low=sampler/studio_tom_low_stick(gain_db=0) tom_edge=sampler/studio_tom_high_mallet(gain_db=0)\ngroove swing")
    _write("kits/studio_takes.sm", studio, "Acoustic kits", "Studio alternate takes",
           "VCSL snares and stick/mallet toms with recorded alternate takes, over Black Pearl kick and cymbals.", rows)
    busk = '''# Hand percussion: left/right cajon and conga samples, played as a conversation.
song "Kit: Buskman hand percussion" 100 4/4 Dm fps=30 seed=82 tail=2 mood=balanced
kit kick=sampler/busk_cajon_bass(gain_db=0) snare=sampler/busk_cajon_left(gain_db=0) right=sampler/busk_cajon_right(gain_db=0) low=sampler/busk_conga_low_left(gain_db=0) high=sampler/busk_conga_high_right(gain_db=0) hat=sampler/busk_shaker(gain_db=0,pan=0) bell=sampler/busk_cowbell(gain_db=0)
groove swing=.55/16
call 2 | drums:{kick: "X.......x.......", snare: "....x.......x...", right: ".......o.......o", hat: "x-x-x-x-x-x-x-x-"} dyn=p<mp
answer 2 | drums:{low: "x.....x.........", high: "....x....x..x...", bell: "x...x...x...x..."} dyn=mp<mf
reply 2 | drums:{kick: "X.....x.........", snare: "....x.......x...", right: ".......o......o.", hat: "x.x.x.x.x.x.x.x."} dyn=mf>p
mix drums -6 hall=.04
master standard lufs=-18 glue=none
'''
    _write("kits/busk.sm", busk, "Acoustic kits", "Buskman hand percussion", "Cajon, alternating-hand congas, shaker and cowbell; ten recorded velocity layers.", rows)
    for i, bass in enumerate(SYNTH_BASSES):
        title = f"Electronic set {i+1}: {ELECTRONIC[i][0]} / {ELECTRONIC[i][1]}"
        score = f'''# {title}. These are synthesis recipes, not sampled hardware clones.
song "{title}" 120 4/4 Dm fps=30 seed=82 tail=2 mood=balanced
inst bass=bass/{bass}(gain_db=0)
{electronic_kit(i)}
chords Dm Bb F C
groove swing=.53/16
setup 2 | drums:broken_beat bass:syncopated dyn=mp
answer 2 | drums:{{kick: "X.......x.x.....", snare: "....X..o....X...", hat: "x.x.x.x.x.x.x.x.", ohat: "..............x."}} bass:pocket dyn=mf>mp
mix bass -6 sc=.15 | drums -5 hall=.02
master standard lufs=-18 glue=none
'''
        _write(f"electronic/set_{i+1:02}.sm", score, "Electronic kits", title, "Distinct kick/snare/closed/open-hat presets and synth bass on a broken groove.", rows)
    templates = [
        ("01_soul_pocket", "Soul pocket", "black_pearl", BASSES[2], "soul", "pocket", 96, ".54", "Dm7 Bbmaj7 Fmaj7 C7"),
        ("02_dry_funk", "Dry funk", "black_pearl", BASSES[6], "dry_funk", "syncopated", 108, ".55", "Dm7 G7 Dm7 A7"),
        ("03_big_rock", "Big rock", "red_zeppelin", BASSES[0], "pocket", "root5", 112, ".51", "Dm Bb F C"),
        ("04_ride_shuffle", "Ride shuffle", "blonde_bop", "double_bass", "ride_shuffle", "root5", 96, ".5", "Dm7 G7 Cmaj7 A7"),
        ("05_quiet_rods", "Quiet hot rods", "blonde_bop_rods", BASSES[7], "light_rods", "half_time", 84, ".54", "Dm7 Bbmaj7 Fmaj7 C7"),
        ("06_broken_electric", "Broken electric", None, BASSES[5], "broken_beat", "syncopated", 116, ".55", "Dm7 Bbmaj7 Fmaj7 C7"),
        ("07_dub_space", "Dub space", "black_pearl", BASSES[3], "dub_space", "dub", 80, ".53", "Dm7 Gm7 Dm7 A7"),
        ("08_half_time", "Half-time room", "red_zeppelin", BASSES[4], "half_time", "half_time", 120, ".54", "Dm Bb F C"),
    ]
    for i, (name, title, kit, bass, style, bass_style, tempo, swing, chords) in enumerate(templates):
        kit_line = acoustic_kit(kit) if kit else electronic_kit(2)
        if i == 3:
            kit_line += "\nkit hat=sampler/blonde_bop_ride(gain_db=0,pan=0)"
        if i == 6:
            kit_line += "\nkit snare=sampler/black_pearl_sidestick(gain_db=0,pan=0)"
        bass_fader = [6, -1.5, 1, 6, 2, -.5, -.5, -5][i]
        score = f'''# {title}: editable sixteen-bar arrangement, with an opening, reply, lift and landing.
# Listen for accents, ghost pickups, a bass rest before the reply, and a change of orchestration.
song "Template: {title}" {tempo} 4/4 Dm fps=30 seed={180+i} tail=3 mood=balanced
inst bass=sampler/{bass}(gain_db=0) keys=sampler/fm_piano
{kit_line}
chords {chords}
groove swing={swing}/16
feel snare offset=7
feel bass hum=2,3,.018 gate=.9
opening 4 | drums:{style} bass:{bass_style} dyn=p<mp
reply 4 | drums:{style} bass:{{rel: "R/4. r/8 5/4 R+/8 r/8 | R/4 r/4 5/8 R/8 r/4", oct: -2}} keys:{{rel: "r/4 [3,7]/4 r/4 [3,7]/8 r/8", oct: 0}} dyn=mp
lift 3 | drums:{style} bass:{bass_style} keys:{{rel: "[3,7]/2 r/4 [3,7]/4", oct: 0}} dyn=mp<mf
landing 3 | drums:{style} bass:{{rel: "R/2 r/4 5/8 R/8", oct: -2}} keys:{{rel: "[3,7]/2 r/2", oct: 0}} dyn=mf>mp
last 1 | drums:{{kick: "X...............", snare: "....o..........."}} bass:{{rel: "R/2. r/4", oct: -2}} keys:{{rel: "[R,3,5]/2. r/4", oct: 0}} chords="Dm7:1" dyn=p
mix bass {bass_fader} sc=0 | drums -7 hall=.035 | keys -2 hall=.12
master standard lufs=-16 glue=none
'''
        # A written fill replaces the hats/snare for the last bar of the lift. Two hands,
        # two toms; the kick remains independent. No hats continue beneath the tom run.
        turn = ('{kick: "X...............", tom_high: "....x.x.........", tom_low: "........x.x.....", '
                'tom_edge: "............x.x."}' if kit else
                '{kick: "X...............", snare: "....x..o..x.o.X."}')
        score = score.replace("landing 3", f'turn 1 | drums:{turn} bass:{{rel: "R/2 r/2", oct: -2}} dyn=mf\nlanding 3')
        _write("templates/" + name + ".sm", score, "Groove templates", title,
               "16-bar starter: " + style + " drums, " + bass_style + " bass, sparse FM chords and a resolved stop.", rows)
    COLLECTION.mkdir(parents=True, exist_ok=True)
    (COLLECTION / "palette.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return rows


def render_one(row: dict) -> dict:
    from songmap.arrange.expand import expand
    from songmap.instruments.sampler.library import SAMPLES
    from songmap.listen import listen
    from songmap.parse.lang import load
    from songmap.render import render, write_outputs
    song = load(str(COLLECTION / row["source"]))
    arr = expand(song)
    arr.ensemble.check(song.parts())
    written = listen(arr)
    result = render(song)
    output = COLLECTION / "renders" / row["id"]
    write_outputs(result, str(output), mp3=True, stems=row["group"] == "Groove templates")
    record = {"source": row["source"], "source_sha256": hashlib.sha256((COLLECTION / row["source"]).read_bytes()).hexdigest(),
              "digest": arr.digest(), "frames": arr.timeline.frames, "listen": written.counts()}
    SAMPLES._data.clear()
    del result, arr
    gc.collect()
    return record


def render_all(rows: list, jobs: int) -> list:
    previous = COLLECTION / "render_receipt.json"
    records = {r["source"]: r for r in json.loads(previous.read_text())} if previous.is_file() else {}
    def collect(results):
        for row, record in zip(rows, results):
            print("rendered", row["source"], record["listen"], flush=True)
            records[row["source"]] = record
    if jobs == 1:
        collect(map(render_one, rows))
    else:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            collect(pool.map(render_one, rows))
    previous.write_text(json.dumps(list(records.values()), indent=2) + "\n", encoding="utf-8")
    return list(records.values())


def gallery(rows: list) -> None:
    groups = list(dict.fromkeys(r["group"] for r in rows))
    cards = []
    for row in rows:
        base = "renders/" + row["id"]
        credits = f' · <a href="{base}/LICENSES.md">Sample credits</a>' if row["group"] not in ("Synth bass", "Electronic kits") else ""
        cards.append(f'''<article data-group="{html.escape(row['group'])}"><h3>{html.escape(row['title'])}</h3>
<p>{html.escape(row['description'])}</p><audio controls preload="none" src="{base}/song.mp3"></audio>
<p><a href="{row['source']}">Editable score / template</a> · <a href="{base}/qa.png">Audio QA</a>{credits}</p></article>''')
    options = "".join(f'<option>{html.escape(group)}</option>' for group in groups)
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SongMap · Bass & drums</title><style>
*{box-sizing:border-box}body{background:#10151b;color:#e8edf3;font:16px/1.55 system-ui;margin:0}main{max-width:1150px;margin:auto;padding:36px 24px}h1{font-size:clamp(2rem,5vw,3.5rem);line-height:1.1;margin:15px 0}h2{margin-top:35px}p{color:#bdc9d6;max-width:75ch}a{color:#9bd9c3}nav{display:flex;gap:16px;flex-wrap:wrap}select{font:inherit;background:#202c38;color:inherit;border:1px solid #64758b;padding:9px;border-radius:6px}#grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:18px;margin-top:22px}article{border:1px solid #344355;border-radius:12px;padding:21px;background:#19222c}article h3{margin:0 0 10px}article p{font-size:.9rem}audio{width:100%;margin:8px 0}article[hidden]{display:none}code{color:#e2dbb0}li{margin-bottom:6px}.tag{color:#9bd9c3;letter-spacing:.15em;text-transform:uppercase;font-size:.8rem}
</style><main><div class="tag">SongMap sound library</div><h1>Bass & drums, with room to breathe.</h1>
<p>Eight recorded electric-bass voices, four acoustic-bass voices (two plucked, two bowed), eight synth basses, four acoustic kit setups, an alternate-take hybrid kit, a hand-percussion set, eight electronic sets, and eight editable groove templates. Auditions target −18 LUFS; full templates target −16 LUFS.</p>
<nav><a href="../sfz_revisited/index.html#comparisons">Earlier song comparisons</a><a href="../../docs/BASS_DRUM_PALETTE.md">Palette and performance guide</a><a href="../../textbook_site/">Textbook</a></nav>
<h2>Choose a family. Listen to the soft notes too.</h2><p>Recorded alternate takes help the electric basses and the additional studio snares/toms. AVL kits use 5 recorded dynamic layers, with separate center/edge and hat articulations; they do not have recorded round robins. Some kit setups share cymbal recordings. Electronic sets are synthesis presets, not hardware recordings.</p>
<label>Show <select id="family"><option>Everything</option>OPTIONS</select></label><section id="grid">CARDS</section>
<h2>What makes these grooves feel played?</h2><ul><li>Strong and weak strokes have different jobs. Ghost notes stay below the backbeat.</li><li>Bass lines leave rests, change note lengths and answer the drummer.</li><li>Open hats close with the pedal. Tom answers leave space for the drummer's hands.</li><li>Sections change in density and dynamics. Timing variation stays small and repeatable.</li></ul>
<p>Technical checks cover source integrity, supported mappings, finite audio, clipping and score structure. Musical realism remains a listening judgment. Templates are starting arrangements; revise their phrases for each song.</p></main>
<script>document.querySelector('#family').onchange=e=>document.querySelectorAll('article').forEach(a=>a.hidden=e.target.value!=='Everything'&&a.dataset.group!==e.target.value);document.addEventListener('play',e=>{if(e.target.tagName==='AUDIO')document.querySelectorAll('audio').forEach(a=>{if(a!==e.target)a.pause()})},true)</script></html>'''
    (COLLECTION / "index.html").write_text(page.replace("OPTIONS", options).replace("CARDS", "\n".join(cards)), encoding="utf-8")


def audit(rows: list) -> dict:
    errors = []
    clips = 0
    receipt = COLLECTION / "render_receipt.json"
    records = {r["source"]: r for r in json.loads(receipt.read_text())} if receipt.is_file() else {}
    for row in rows:
        out = COLLECTION / "renders" / row["id"]
        digest = hashlib.sha256((COLLECTION / row["source"]).read_bytes()).hexdigest()
        if records.get(row["source"], {}).get("source_sha256") != digest:
            errors.append(f"{row['id']}: render is missing or stale")
        for name in ("song.mp3", "qa.json", "review.json", "qa.png"):
            if not (out / name).is_file():
                errors.append(f"{row['id']}: missing {name}")
        if (out / "qa.json").is_file():
            qa = json.loads((out / "qa.json").read_text())
            clips += qa.get("clipped_samples", 0)
            if qa.get("clipped_samples", 0):
                errors.append(f"{row['id']}: clipping")
    result = {"scores": len(rows), "clipped_samples": clips, "errors": errors, "ok": not errors}
    (COLLECTION / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("prepare", "render", "gallery", "audit"):
        parser.add_argument("--" + flag, action="store_true")
    parser.add_argument("--jobs", type=int, default=2, choices=(1, 2))
    parser.add_argument("--only", nargs="*", help="Render only these score IDs; gallery and audit still cover the full collection")
    args = parser.parse_args()
    rows = prepare() if args.prepare else json.loads((COLLECTION / "palette.json").read_text())
    if args.render:
        render_all([r for r in rows if not args.only or r["id"] in args.only], args.jobs)
    if args.gallery:
        gallery(rows)
    if args.audit:
        result = audit(rows)
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result["ok"] else 1)
