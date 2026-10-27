"""Validated conductor edits. The returned score is an unsaved editor buffer."""
from __future__ import annotations

import math
import re

import yaml

from ..arrange.conductor import FIELDS
from ..arrange.expand import expand
from ..arrange.timeline import parse_tempo
from ..parse import lang, yaml_form
from ..theory.keys import parse_key
from .project import parse_text


def _comment(raw):
    quote, escaped, depth = None, False, 0
    for i, c in enumerate(raw):
        if quote:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        elif c in "({[":
            depth += 1
        elif c in ")}]":
            depth -= 1
        elif c == "#" and depth == 0 and (i == 0 or raw[i-1].isspace()):
            return raw[:i].rstrip(), raw[len(raw[:i].rstrip()):]
    return raw, ""


def _literal(value):
    from ..parse.fmt import value as sm_value
    return sm_value(value)


def _set(text, key, value):
    # A final assignment wins, including over earlier dotted assignments. Replacing only the
    # final matching whole-line assignment keeps structured programs and their comments intact.
    lines = text.splitlines()
    item = f"set {key}={_literal(value)}"
    if lines and re.fullmatch(rf"set {re.escape(key)}=.*", lines[-1]):
        _, comment = _comment(lines[-1])
        lines[-1] = item + comment
        return "\n".join(lines)+"\n"
    return text.rstrip()+"\n"+item+"\n"


def edit(text: str, path: str, *, index=None, values: dict) -> str:
    if not isinstance(values, dict) or not values or set(values)-FIELDS:
        raise ValueError("conductor fields are tempo, meter and key")
    song = parse_text(text, path)
    if index is not None and (isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(song.sections)):
        raise ValueError("select an existing section")
    sec = song.sections[index] if index is not None else None
    for key, value in values.items():
        if value is None:
            if sec is None:
                raise ValueError("song defaults cannot be empty")
            continue
        if key == "tempo":
            if sec is None:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                    raise ValueError("song tempo must be a positive, finite quarter-note BPM")
            else:
                parse_tempo(value, song, sec)
        elif key == "meter":
            meter = yaml_form.parse_meter(value, file=path)
            if sec is None and len(meter) > 2:
                raise ValueError("write additive groups on sections; the song default uses N/D")
        elif key == "key":
            if not isinstance(value, str):
                raise ValueError("key must contain a tonic and scale name")
            parse_key(value)

    if not path.lower().endswith(lang.EXTS):
        raw = yaml_form._plain(yaml_form.load_raw_text(text, path))
        if sec is None:
            raw.update(values)
        elif sec.name in (raw.get("conductor") or {}):
            raw["conductor"][sec.name].update(values)
        else:
            raw["sections"][index].update(values)
        new = yaml.safe_dump(raw, sort_keys=False, allow_unicode=True)
    elif sec is None:
        new = text
        for key, value in values.items():
            new = _set(new, key, value)
    else:
        raw = lang.compile_raw(text, path)
        mapping = dict(raw.get("conductor") or {})
        lines = text.splitlines(keepends=True)
        line = lines[sec.line-1] if sec.line and sec.line <= len(lines) else ""
        body, comment = _comment(line.rstrip("\r\n"))
        fields = lang.split_top(body, "|")
        logical = next((ln for ln in lang._lex(text, path) if ln.no == sec.line), None)
        literal_section = (len(fields) > 1 and re.fullmatch(rf"{re.escape(sec.name)}\s+\d+(?:\.\d+)?\s*", fields[0])
                           and logical and logical.toks[-1].line == sec.line and logical.toks[-1].value != ":"
                           and sum(s.line == sec.line for s in song.sections) == 1
                           and sec.name not in mapping)
        if literal_section:
            remaining = dict(values)
            for i in range(1, len(fields)):
                tokens = lang.split_top(fields[i])
                for j, token in enumerate(tokens):
                    key = token.split("=", 1)[0]
                    if "=" in token and key in values:
                        tokens[j] = f"{key}={_literal(values[key])}"
                        remaining.pop(key, None)
                fields[i] = " ".join(tokens)
            fields[1] += "".join(f" {key}={_literal(value)}" for key, value in remaining.items())
            ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
            lines[sec.line-1] = fields[0].rstrip()+" | "+" | ".join(f.strip() for f in fields[1:])+comment+ending
            new = "".join(lines)
        else:
            mapping[sec.name] = {**mapping.get(sec.name, {}), **values}
            new = _set(text, "conductor", mapping)
    # Validate expansion too: a shorter meter can make a written rhythm invalid.
    expand(parse_text(new, path))
    return new
