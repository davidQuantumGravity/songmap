"""Song -> text: the YAML form and the `.sm` form (ROADMAP P6, `songmap fmt`).

Printing is lossless: parsing the printed text gives back the same song (`song_to_raw` equal, so
the same notes, events, ensemble, mix and master). `.sm` output uses section lines, with `like=`
where that makes a line shorter, header directives where they can say the value exactly, and
`set path=value` for whatever has no directive (returns, harmony voicing, odd instrument shapes).
"""
from __future__ import annotations

import math
import re
from dataclasses import fields

from ..model import KIT_ROLES, MasterSpec, PartSpec, Song
from .errors import SongError

_WORD = re.compile(r"[A-Za-z_][\w.-]*")
_IDENT = re.compile(r"[A-Za-z_]\w*")
_USE = re.compile(r"[\w/.-]+")


# ----------------------------------------------------------------------------
# Song -> the v0.2 raw mapping (what a YAML file loads into)
# ----------------------------------------------------------------------------
def part_to_raw(p: PartSpec, motifs=()) -> object:
    body: dict = {}
    if p.style:
        body["style"] = "+".join([p.style, *p.mods])
    if p.motifs:
        body["motifs"] = list(p.motifs)
    if p.notes is not None:
        body[{"letter": "notes"}.get(p.notes_mode, p.notes_mode)] = p.notes
    if p.steps:
        body["steps"] = dict(p.steps)
    body.update(p.opts)
    if p.variants:
        body["vary"] = [{"bars": list(b), "part": part_to_raw(v, motifs)} for b, v in p.variants]
    if list(body) == ["style"] and p.style not in motifs:
        return body["style"]
    if list(body) == ["motifs"]:
        return body["motifs"]
    return body


def _master_raw(m: MasterSpec):
    default = MasterSpec()
    d = {f.name: getattr(m, f.name) for f in fields(m) if getattr(m, f.name) != getattr(default, f.name)}
    if not d:
        return None
    return d["mode"] if list(d) == ["mode"] else d


def _bin_word(v) -> str:
    """A binaural value as a bare word when it reads back the same (10, 16.18>10), else quoted/structured."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return _num(v)
    if isinstance(v, str) and re.fullmatch(r"\d+(\.\d+)?>\d+(\.\d+)?|[A-Za-z_]\w*", v) and v not in ("true", "false", "none"):
        return v
    return value(v)


def song_to_raw(song: Song) -> dict:
    """The mapping `yaml_form.from_raw` reads, without line numbers: the comparison key for round trips."""
    raw: dict = {"songmap": 0.2, "title": song.title, "tempo": song.tempo,
                 "meter": f"{song.meter[0]}/{song.meter[1]}", "key": song.key}
    if song.tuning != "12edo":
        raw["tuning"] = song.tuning
    raw.update(fps=song.fps, seed=song.seed, tail_seconds=song.tail_seconds)
    if song.mood is not None:
        raw["mood"] = song.mood
    for k in ("video", "instruments", "groove", "parts_feel"):
        if getattr(song, k):
            raw[k] = getattr(song, k)
    h = song.harmony
    harmony = {}
    if h.default:
        harmony["default"] = list(h.default)
    if h.chord_bars != 1:
        harmony["chord_bars"] = h.chord_bars
    if h.progressions:
        harmony["progressions"] = dict(h.progressions)
    if h.voicing:
        harmony["voicing"] = h.voicing
    if harmony:
        raw["harmony"] = harmony
    if song.motifs:
        raw["motifs"] = {}
        for name, m in song.motifs.items():
            mode = {"letter": "notes"}.get(m.mode, m.mode)
            d = {mode: m.text}
            if m.octave != 4:
                d["octave"] = m.octave
            if m.key:
                d["key"] = m.key
            raw["motifs"][name] = m.text if list(d) == ["notes"] else d
    raw["sections"] = []
    for s in song.sections:
        d = {"name": s.name, "bars": s.bars, "parts": {r: part_to_raw(p, song.motifs) for r, p in s.parts.items()}}
        for k in ("harmony", "dyn", "tempo", "key"):
            if getattr(s, k) is not None:
                d[k] = getattr(s, k)
        if s.meter is not None:
            d["meter"] = f"{s.meter[0]}/{s.meter[1]}" + (" " + "+".join(map(str, s.meter[2])) if len(s.meter) > 2 else "")
        if s.feel:
            d["feel"] = s.feel
        if s.binaural:
            d["binaural"] = s.binaural
        raw["sections"].append(d)
    if song.events:
        raw["events"] = [{"at": e.at, "type": e.type, **e.params} for e in song.events]
    for k in ("cues", "mix", "returns", "patches"):
        if getattr(song, k):
            raw[k] = getattr(song, k)
    master = _master_raw(song.master)
    if master is not None:
        raw["master"] = master
    if song.qa:
        raw["qa"] = song.qa
    if song.binaural:
        raw["binaural"] = song.binaural
    return raw


def to_yaml(song: Song, header: str = "") -> str:
    from .yaml_form import dump
    return dump(song_to_raw(song), header)


# ----------------------------------------------------------------------------
# values in .sm syntax
# ----------------------------------------------------------------------------
def _num(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    r = repr(float(v))
    if "e" in r or "inf" in r or "nan" in r:
        if not math.isfinite(v):
            raise SongError(f"can't write the number {v} in .sm")
        r = f"{v:.12f}".rstrip("0").rstrip(".")
    return r


def _quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def value(v, top: bool = True) -> str:
    """A value as `.sm` reads it back exactly: numbers, true/false/none, "strings", [lists], {maps}.
    At the top of a `k=v`, a plain word may go unquoted."""
    if v is None:
        return "none"
    if isinstance(v, (bool, int, float)):
        return _num(v)
    if isinstance(v, str):
        if top and _WORD.fullmatch(v) and v not in ("true", "false", "none") and not re.fullmatch(r"[\d.]+", v):
            return v
        return _quote(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(value(x, False) for x in v) + "]"
    if isinstance(v, dict):
        items = []
        for k, x in v.items():
            if not isinstance(k, str):
                raise SongError(f"can't write the map key {k!r} in .sm (keys are names or strings)")
            items.append(f"{k if _IDENT.fullmatch(k) else _quote(k)}: {value(x, False)}")
        return "{" + ", ".join(items) + "}"
    raise SongError(f"can't write {type(v).__name__} in .sm")


def _kv(d: dict) -> str:
    return ", ".join(f"{k}={value(v)}" for k, v in d.items())


def _simple(v) -> bool:
    """A value `_value` reads back unchanged at the top of k=v inside (...) (no ')' in it)."""
    return ")" not in value(v)


# ----------------------------------------------------------------------------
# Song -> .sm
# ----------------------------------------------------------------------------
class _Printer:
    def __init__(self, song: Song):
        self.song = song
        self.lines: list[str] = []
        self.sets: list[str] = []
        self.vars: dict[str, str] = {}          # value(raw part) -> variable name

    def set(self, path: str, v):
        self.sets.append(f"set {path}={value(v, False) if isinstance(v, str) else value(v)}")

    # -- header --
    def header(self):
        s = self.song
        key = s.key if _WORD.fullmatch(s.key) else _quote(s.key)
        line = f"song {_quote(s.title)} {_num(s.tempo)} {s.meter[0]}/{s.meter[1]} {key} fps={s.fps} seed={s.seed}"
        if s.mood is not None:
            line += f" mood={value(s.mood)}"
        line += f" tail={_num(s.tail_seconds)}"
        if s.tuning != "12edo":
            line += f" tuning={value(s.tuning)}"
        v = s.video
        if v:
            if set(v) <= {"composition", "frames"} and "composition" in v and _IDENT.fullmatch(str(v["composition"])) \
                    and isinstance(v.get("frames", 0), int) and not isinstance(v.get("frames"), bool):
                line += f" video={v['composition']}" + (f":{v['frames']}" if "frames" in v else "")
            else:
                self.set("video", v)
        self.lines.append(line)
        self.instruments()
        self.groove()
        h = s.harmony
        if h.default:
            per = f" /{_num(int(h.chord_bars) if h.chord_bars == int(h.chord_bars) else h.chord_bars)}" \
                if h.chord_bars != 1 else ""
            if all(re.fullmatch(r"[^\s\"'/]\S*", c) for c in h.default):
                self.lines.append("chords " + " ".join(h.default) + per)
            else:
                self.set("harmony.default", list(h.default))
                if h.chord_bars != 1:
                    self.set("harmony.chord_bars", h.chord_bars)
        elif h.chord_bars != 1:
            self.set("harmony.chord_bars", h.chord_bars)
        for name, text in h.progressions.items():
            self.lines.append(f"prog {name} {_quote(text)}")
        if h.voicing:
            self.set("harmony.voicing", h.voicing)
        for name, m in s.motifs.items():
            opts = ([m.mode] if m.mode != "letter" else []) + ([f"oct={m.octave}"] if m.octave != 4 else [])
            if m.key:
                opts.append(f"key={m.key}" if _WORD.fullmatch(m.key) else f"key={_quote(m.key)}")
            self.lines.append(" ".join(["motif", name, *opts, _quote(m.text)]))
        for name, pos in s.cues.items():
            p = value(pos)
            if " " in p or not _IDENT.fullmatch(name):
                self.set(f"cues.{name}", pos)
            else:
                self.lines.append(f"cue {name}={p}")

    def instruments(self):
        inst, kit = [], []
        for part, e in self.song.instruments.items():
            if isinstance(e, str) and _USE.fullmatch(e):
                inst.append(f"{part}={e}")
            elif isinstance(e, dict) and part == "drums" and list(e) == ["kit"] and isinstance(e["kit"], dict) \
                    and e["kit"] and all(self.voice(v) is not None for v in e["kit"].values()):   # an empty kit has no `kit` line
                kit += [f"{piece}={self.voice(v)}" for piece, v in e["kit"].items()]
            elif isinstance(e, dict) and not ("kit" in e or (part in KIT_ROLES and "use" not in e)):
                params = {k: v for k, v in e.items() if k != "use"}
                use = e.get("use")
                if params and all(_simple(v) for v in params.values()) and (use is None or _USE.fullmatch(str(use))):
                    inst.append(f"{part}={use}({_kv(params)})" if use else f"{part}({_kv(params)})")
                else:
                    self.set(f"instruments.{part}", e)
            else:
                self.set(f"instruments.{part}", e)
        if inst:
            self.lines.append("inst " + " ".join(inst))
        if kit:
            self.lines.append("kit " + " ".join(kit))

    @staticmethod
    def voice(v) -> str | None:
        if isinstance(v, str) and _USE.fullmatch(v):
            return v
        if isinstance(v, dict) and isinstance(v.get("use"), str) and _USE.fullmatch(v["use"]) and len(v) > 1:
            params = {k: x for k, x in v.items() if k != "use"}
            if all(_simple(x) for x in params.values()):
                return f"{v['use']}({_kv(params)})"
        return None

    @staticmethod
    def _hum(h) -> str | None:
        if isinstance(h, dict) and list(h) == ["time_ms", "drift_ms", "vel"] and all(
                isinstance(x, (int, float)) and not isinstance(x, bool) for x in h.values()):
            return ",".join(_num(x) for x in h.values())
        return None

    def groove(self):
        g = self.song.groove
        if g:
            ok = set(g) <= {"swing", "swing_grid", "template", "humanize", "metric"} and (
                "swing_grid" not in g or "swing" in g) and ("humanize" not in g or self._hum(g["humanize"])) and (
                "template" not in g or _WORD.fullmatch(str(g["template"])))
            if ok:
                parts = []
                if "swing" in g:
                    parts.append(f"swing={_num(g['swing'])}" + (f"/{_num(g['swing_grid'])}" if "swing_grid" in g else ""))
                if "template" in g:
                    parts.append(f"tpl={g['template']}")
                if "humanize" in g:
                    parts.append(f"hum={self._hum(g['humanize'])}")
                if "metric" in g:
                    parts.append(f"metric={_num(g['metric'])}")
                self.lines.append("groove " + " ".join(parts))
            else:
                self.set("groove", g)
        names = {"offset_ms": "offset", "gate": "gate", "high_loud": "high_loud", "arch": "arch"}
        for part, f in self.song.parts_feel.items():
            if isinstance(f, dict) and f and set(f) <= {*names, "humanize"} and all(
                    isinstance(x, (int, float)) and not isinstance(x, bool) for k, x in f.items() if k != "humanize") \
                    and ("humanize" not in f or self._hum(f["humanize"])):
                parts = [f"hum={self._hum(x)}" if k == "humanize" else f"{names[k]}={_num(x)}" for k, x in f.items()]
                self.lines.append(f"feel {part} " + " ".join(parts))
            else:
                self.set(f"parts_feel.{part}", f)

    def trailer(self):
        s = self.song
        chains = {}
        for part, m in s.mix.items():
            if isinstance(m, dict) and isinstance(m.get("inserts"), list) and all(
                    isinstance(u, dict) and isinstance(u.get("fx"), str) and all(
                        isinstance(v, (int, float)) and not isinstance(v, bool) for k, v in u.items() if k != "fx")
                    for u in m["inserts"]):
                chains[part] = m["inserts"]
                m = {k: v for k, v in m.items() if k != "inserts"}
                if not m:
                    continue
            ok = isinstance(m, dict) and isinstance(m.get("gain_db"), (int, float)) and not isinstance(
                m.get("gain_db"), bool) and set(m) <= {"gain_db", "pan", "width", "send", "sidechain", "eq", "bus_comp"}
            if ok:
                rest = " ".join(f"{k}={value(v)}" for k, v in m.items() if k != "gain_db")
                self.lines.append(f"mix {part} {_num(m['gain_db'])}" + (f" {rest}" if rest else ""))
            else:
                self.set(f"mix.{part}", m)
        if chains:
            unit = lambda u: u["fx"] + ("(" + ", ".join(f"{k}={_num(v)}" for k, v in u.items() if k != "fx") + ")"  # noqa: E731
                                        if len(u) > 1 else "")
            self.lines.append("inserts " + " | ".join(f"{p} " + " ".join(unit(u) for u in c) for p, c in chains.items()))
        if s.returns:
            self.set("returns", s.returns)
        if s.patches:
            from ..instruments.patch import to_text, validate
            for pname, spec in s.patches.items():
                self.lines.extend(to_text(pname, validate(spec, pname)))
        master = _master_raw(s.master)
        if master is not None:
            if isinstance(master, str):
                self.lines.append(f"master {master}")
            else:
                keys = {"target_lufs": "lufs", "ceiling_db": "ceiling", "glue": "glue", "preserve_contrast": "contrast"}
                words = [master["mode"]] if "mode" in master else []
                bad = [k for k in master if k != "mode" and k not in keys]
                if bad or not _WORD.fullmatch(str(master.get("mode", "x"))):
                    self.set("master", master)
                else:
                    words += [f"{keys[k]}={value(v)}" for k, v in master.items() if k != "mode"]
                    self.lines.append("master " + " ".join(words))
        if s.qa:
            words = []
            for k, v in s.qa.items():
                w = self.qa_word(k, v)
                if w:
                    words.append(w)
                else:
                    self.set(f"qa.{k}", v)
            if words:
                self.lines.append("qa " + " ".join(words))
        if s.binaural:
            line = self.binaural_line(s.binaural)
            if line:
                self.lines.append(line)
            else:
                self.set("binaural", s.binaural)

    @staticmethod
    def binaural_line(b: dict) -> str | None:
        names = {"beat": "beat", "ladder": "ladder", "level_db": "level", "fade": "fade", "glide": "glide",
                 "gain_db": "gain", "breathe": "breathe", "breath_db": "breath", "carve": "carve", "octaves": "octaves"}
        cs = b.get("carriers")
        if not isinstance(cs, list) or not cs or set(b) - {"carriers", *names}:
            return None
        words = []
        for c in cs:
            if isinstance(c, (int, float)) and not isinstance(c, bool):
                words.append(_num(c))
            elif isinstance(c, str) and re.fullmatch(r"[\^v]*[A-Za-z][\w#.*^]*", c):
                words.append(c)
            else:
                return None
        for k, v in b.items():
            if k != "carriers":
                words.append(f"{names[k]}={_bin_word(v)}")
        return "binaural " + " ".join(words)

    @staticmethod
    def qa_word(k, v) -> str | None:
        num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)  # noqa: E731
        if k == "target_lufs":
            if num(v):
                return f"lufs={_num(v)}"
            if isinstance(v, list) and len(v) == 2 and all(num(x) for x in v):
                return f"lufs={_num(v[0])}..{_num(v[1])}"
        if k == "contrast" and isinstance(v, list) and v and all(
                isinstance(r, list) and len(r) == 3 and _IDENT.fullmatch(str(r[0])) and _IDENT.fullmatch(str(r[1]))
                and num(r[2]) for r in v):
            return "contrast=" + ",".join(f"{a}<{b}:{_num(n)}" for a, b, n in v)
        if k == "never_silent" and isinstance(v, list) and v and all(_IDENT.fullmatch(str(x)) for x in v):
            return "silent!=" + ",".join(v)
        if k == "max_low_ratio" and num(v):
            return f"low<={_num(v)}"
        if k == "true_peak_max_db" and num(v):
            return f"peak<={_num(v)}"
        if k == "hits_audible" and isinstance(v, bool):
            return f"hits={_num(v)}"
        return None

    # -- sections and events --
    def part_token(self, role, raw, taken: set) -> str:
        if isinstance(raw, dict) and value(raw) in self.vars:
            return f"{role}:{self.vars[value(raw)]}"
        if isinstance(raw, str):
            names = raw.split("+")
            if all(re.fullmatch(r"\w+", n) for n in names) and not set(names) & taken:
                return f"{role}:{raw}"
        elif isinstance(raw, list) and raw and all(isinstance(x, str) for x in raw):
            ok = all(re.fullmatch(r"[A-Za-z_]\w*(:[^\s,:=()\[\]{}\"']+)*", x) for x in raw)
            if ok and not (len(raw) == 1 and ":" not in raw[0] and raw[0] in taken):
                return f"{role}:{','.join(raw)}"
        if isinstance(raw, str):
            raw = {"style": raw}
        elif isinstance(raw, list):
            raw = {"motifs": raw}
        return f"{role}:{value(raw)}"

    def settings(self, d: dict) -> list[str]:
        out = []
        for k, v in d.items():
            if k == "harmony":
                out.append(f"prog={v}" if v in self.song.harmony.progressions and _IDENT.fullmatch(v)
                           else f"chords={_quote(v)}")
            elif k == "dyn":
                out.append(f"dyn={v}" if re.fullmatch(r"[^\s\"'|]+", str(v)) else f"dyn={_quote(str(v))}")
            elif k == "feel":
                if set(v) <= {"template", "swing"} and all(_WORD.fullmatch(str(x)) or isinstance(x, (int, float))
                                                            for x in v.values()):
                    out += [f"feel={v['template']}"] if "template" in v else []
                    out += [f"swing={_num(v['swing'])}"] if "swing" in v else []
                else:
                    out.append(f"feel={value(v)}")
            elif k == "tempo":
                out.append(f"tempo={_num(v)}" if isinstance(v, (int, float)) else f"tempo={_quote(str(v))}")
            elif k == "key":
                out.append(f"key={v}" if _WORD.fullmatch(str(v)) else f"key={_quote(str(v))}")
            elif k == "meter":
                out.append(f"meter={v}" if " " not in str(v) else f"meter={_quote(str(v))}")
            elif k == "binaural":
                out.append(f"beat={_bin_word(v['beat'])}" if list(v) == ["beat"] else f"binaural={value(v)}")
        return out

    def tokens(self, d: dict, taken: set) -> list[str]:
        return [self.part_token(r, p, taken) for r, p in d["parts"].items()] + self.settings(
            {k: d[k] for k in ("harmony", "dyn", "feel", "tempo", "key", "meter", "binaural") if k in d})

    def like_tokens(self, d, base, taken) -> list[str] | None:
        """Tokens for `like=<base>` + the differences, or None when like= can't express d."""
        settings = ("harmony", "dyn", "feel", "tempo", "key", "meter", "binaural")
        for k in settings:
            if k in base and k not in d:
                return None                     # a setting can't be removed
            if k in ("feel", "binaural") and k in base and not all(
                    x in d[k] and d[k][x] == v for x, v in base[k].items()):
                return None                     # feel= and binaural= merge, so the base's must be part of d's
        # like= keeps the base's part order, so changed parts follow it and new parts come last (a printed
        # file prints the same again)
        roles = [r for r in base["parts"] if r in d["parts"]] + [r for r in d["parts"] if r not in base["parts"]]
        parts = [self.part_token(r, d["parts"][r], taken) for r in roles
                 if base["parts"].get(r, object()) != d["parts"][r]]
        parts += [f"-{r}" for r in base["parts"] if r not in d["parts"]]
        sets = self.settings({k: d[k] for k in settings if k in d and d[k] != base.get(k)})
        return [f"like={base['name']}"] + parts + sets

    def event_token(self, e: dict, sec: str | None) -> str:
        params = {k: v for k, v in e.items() if k not in ("at", "type")}
        length = ""
        for k, unit in (("bars", ""), ("beats", "b")):
            v = params.get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0 and "e" not in _num(v):
                length = f":{_num(params.pop(k))}{unit}"
                break
        at, pos = e["at"], None
        if sec is not None and isinstance(at, str):
            if at == sec:
                pos = ""
            else:
                m = re.fullmatch(re.escape(sec) + r"([+-]\d+(?:\.\d+)?(?::\d+(?:\.\d+)?)?)", at)
                if m:
                    pos = "@" + m[1]
        if pos is None:
            text = _num(at) if isinstance(at, (int, float)) and not isinstance(at, bool) else str(at)
            if not re.fullmatch(r"cue:\w+|f\d+|\d+(?:\.\d+)?(?::\d+(?:\.\d+)?)?"
                                r"|[A-Za-z_]\w*(?:[+-]\d+(?:\.\d+)?)?(?::\d+(?:\.\d+)?)?", text) \
                    or (isinstance(at, str) and re.fullmatch(r"\d+(\.\d+)?", at)):
                raise SongError(f"event {e['type']} at '{at}': this position can't be written in .sm",
                                suggestion="write positions as 12, 12:3, name+8:2, f3960 or cue:name")
            pos = "@" + text
        if any(not _simple(v) for v in params.values()):
            raise SongError(f"event {e['type']}: an option value contains ')', which .sm can't write")
        return f"!{e['type']}{length}{pos}" + (f"({_kv(params)})" if params else "")

    def factor(self, secs):
        """Name part values that are maps and repeat (arp: {style: up, order: [...]} -> lit = up(order=[...]))."""
        from .lang import BUILTINS, DIRECTIVES, KEYWORDS
        count: dict[str, list] = {}
        for d in secs:
            for role, raw in d["parts"].items():
                if isinstance(raw, dict):
                    count.setdefault(value(raw), [role, raw, 0])[2] += 1
        names = {d["name"] for d in secs} | set(self.song.motifs) | KEYWORDS | set(DIRECTIVES) | set(BUILTINS)
        for text, (role, raw, n) in count.items():
            if n < 2:
                continue
            base = f"{role}_{raw.get('style', 'part').split('+')[0]}" if isinstance(raw.get("style"), str) else role
            name, i = base, 2
            while name in names or name in self.vars.values() or not _IDENT.fullmatch(name):
                name, i = f"{base}_{i}", i + 1
            style = raw.get("style")
            rest = {k: v for k, v in raw.items() if k != "style"}
            words = style.split("+") if isinstance(style, str) else []
            if words and all(_IDENT.fullmatch(w) for w in words) and not set(words) & set(self.vars.values()) \
                    and rest and all(_IDENT.fullmatch(k) for k in rest) and all(_simple(v) for v in rest.values()) \
                    and not set(rest) & {"style", "mods"}:
                expr = (style if len(words) == 1 else f"({' + '.join(words)})") + f"({_kv(rest)})"
            else:
                expr = value(raw)
            self.vars[text] = name
            self.lines.append(f"{name} = {expr}")

    def sections(self, raw: dict):
        from .lang import BUILTINS, KEYWORDS
        secs = raw["sections"]
        index = {d["name"]: i for i, d in enumerate(secs)}
        for d in secs:
            n = d["name"]
            if not _IDENT.fullmatch(n) or n in KEYWORDS or n in BUILTINS:
                raise SongError(f"section '{n}' can't be a .sm section name (it is reserved)",
                                suggestion="rename the section")
        attach: list[list[str]] = [[] for _ in secs]
        after: list[list[str]] = [[] for _ in secs]
        p, standalone = 0, False
        for e in raw.get("events", []):
            at = e["at"]
            m = re.match(r"[A-Za-z_]\w*", at) if isinstance(at, str) and not at.startswith("cue:") \
                and not re.fullmatch(r"f\d+", at) else None
            k = index.get(m[0]) if m else None
            target = p if k is None else k
            if target > p or (target == p and not standalone):
                if target > p:
                    p, standalone = target, False
                attach[p].append(self.event_token(e, secs[p]["name"]))
            else:
                after[p].append(self.event_token(e, None))
                standalone = True
        self.factor(secs)
        rows, taken = [], set()
        for i, d in enumerate(secs):
            plain = self.tokens(d, taken)
            best = plain
            for b in secs[:i]:
                alt = self.like_tokens(d, b, taken)
                if alt is not None and len(" ".join(alt)) < len(" ".join(best)):
                    best = alt
            rows.append((d["name"], _num(d["bars"]), best, attach[i]))
            taken.add(d["name"])
            rows += [(None, None, None, [x]) for x in after[i]]
        w = max([len(n) for n, *_ in rows if n] + [1])
        wb = max([len(b) for _, b, *_ in rows if b] + [1])
        pw = max([len(" ".join(t)) for n, _, t, ev in rows if n and ev and len(" ".join(t)) <= 64] + [0])
        for name, bars, toks, evs in rows:
            if name is None:
                self.lines.append(evs[0])
                continue
            line = f"{name.ljust(w)} {bars.rjust(wb)} | {' '.join(toks)}"
            if evs:
                line = line.ljust(w + wb + 4 + pw) + " | " + " ".join(evs)
            self.lines.append(line.rstrip())


def to_sm(song: Song, header: str = "") -> str:
    raw = song_to_raw(song)
    pr = _Printer(song)
    pr.header()
    head_end = len(pr.lines)
    pr.sections(raw)
    pr.trailer()
    lines = pr.lines[:head_end] + pr.sets + pr.lines[head_end:]
    text = "\n".join(lines) + "\n"
    return (header.rstrip("\n") + "\n" if header else "") + text


__all__ = ["song_to_raw", "part_to_raw", "to_yaml", "to_sm", "value"]
