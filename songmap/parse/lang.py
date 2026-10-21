"""The SongMap language (`.sml`) -> Song: named beats, parts and sections, `with`, dotted assignment,
`+`-layered drum lanes, the form block, `xN`, `for`, `if`/`every` and small functions (docs/LANGUAGE.md).

A program is evaluated once, top to bottom, and compiled to the v0.2 raw mapping that
`yaml_form.from_raw` turns into a `Song`. So the language adds no new semantics below the song
tree: expand, render and the golden tests see exactly what a YAML song map would give them.

It is deliberately not Turing complete: loops run over static lists or ranges, functions cannot
recurse, and every loop, list and string has a hard size limit. A program always terminates, and
`songmap check` reports its exact length in bars and frames.
"""
from __future__ import annotations

import math
import re
import shlex
from dataclasses import dataclass, field, replace

from ..model import Song
from .errors import SongError, did_you_mean
from .yaml_form import PART_OPTS, PART_SOURCES, VERSION, LineDict, from_raw

EXT = ".sml"
LIMIT = 4096                       # loop iterations, list items, step-string length, sections
SECTION_SETTINGS = ("harmony", "dyn", "feel", "tempo", "key", "bars")
PART_KEYS = PART_SOURCES + PART_OPTS
KEYWORDS = {"for", "in", "if", "elif", "else", "every", "def", "return", "form", "with", "and", "or", "not",
            "true", "false", "none", "as", "at", "bars"}
DIRECTIVES = ("song", "inst", "kit", "chords", "prog", "motif", "cue", "master")
LATER_DIRECTIVES = ("groove", "feel", "mix", "qa")      # compact-format lines this prototype does not read yet
STEP_RANK = {".": 0, "o": 1, "-": 2, "x": 3, "r": 4, "f": 5, "X": 6}


# ----------------------------------------------------------------------------
# lexing: logical lines (brackets join physical lines) with indentation
# ----------------------------------------------------------------------------
_TOKEN = re.compile(r"""
  (?P<ws>[ \t]+)
| (?P<comment>\#[^\n]*)
| (?P<str>"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')
| (?P<num>\d+\.\d+|\d+|\.\d+)
| (?P<name>[A-Za-z_]\w*)
| (?P<op>\.\.|==|!=|<=|>=|\+=|-=|//|[-+*/%<>=()\[\]{},:.|&!@])
| (?P<nl>\n)
""", re.X)


@dataclass
class Tok:
    kind: str                      # num str name op
    value: object
    line: int
    pos: int                       # offset in the file text
    end: int


@dataclass
class Line:
    toks: list[Tok]
    indent: int
    no: int
    text: str                      # the whole file (for raw slices)

    @property
    def raw(self) -> str:
        return self.text[self.toks[0].pos:self.toks[-1].end]

    def sub(self, k: int) -> "Line":
        return Line(self.toks[k:], self.indent, self.toks[k].line, self.text)


def _lex(text: str, file: str | None) -> list[Line]:
    lines, cur, depth, no, line_start = [], [], 0, 1, 0
    indent = None
    pos = 0
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            raise SongError(f"unexpected character '{text[pos]}'", file=file, line=no,
                            suggestion="strings use \"...\"; comments start with #")
        kind = m.lastgroup
        if kind == "nl":
            no += 1
            line_start = m.end()
            if depth == 0 and cur:
                lines.append(Line(cur, indent, cur[0].line, text))
                cur = []
            indent = None
        elif kind == "ws":
            if "\t" in m.group() and not cur and depth == 0:
                raise SongError("tab in indentation", file=file, line=no, suggestion="indent with spaces")
        elif kind != "comment":
            v = m.group()
            if kind == "num":
                v = float(v) if "." in v else int(v)
            elif kind == "str":
                v = bytes(v[1:-1], "utf-8").decode("unicode_escape") if "\\" in v else v[1:-1]
            if not cur and depth == 0:
                indent = m.start() - line_start
            if kind == "op" and v in "([{":
                depth += 1
            elif kind == "op" and v in ")]}":
                depth -= 1
                if depth < 0:
                    raise SongError(f"unmatched '{v}'", file=file, line=no)
            cur.append(Tok(kind, v, no, m.start(), m.end()))
        pos = m.end()
    if depth:
        raise SongError("unclosed bracket at end of file", file=file, line=cur[0].line if cur else no,
                        suggestion="close every ( [ {")
    if cur:
        lines.append(Line(cur, indent, cur[0].line, text))
    return lines


@dataclass
class Node:
    line: Line
    children: list["Node"] = field(default_factory=list)


def _opens_block(line: Line) -> bool:
    t = line.toks[-1]
    return t.kind == "op" and t.value == ":"


def _tree(lines: list[Line], file) -> list[Node]:
    def block(i: int, indent: int) -> tuple[list[Node], int]:
        out = []
        while i < len(lines) and lines[i].indent >= indent:
            ln = lines[i]
            if ln.indent > indent:
                raise SongError("unexpected indent", file=file, line=ln.no,
                                suggestion="only lines after one ending in ':' are indented")
            node = Node(ln)
            i += 1
            if _opens_block(ln):
                if i >= len(lines) or lines[i].indent <= indent:
                    raise SongError("expected an indented block after ':'", file=file, line=ln.no)
                node.children, i = block(i, lines[i].indent)
            out.append(node)
        return out, i

    nodes, i = block(0, 0) if lines else ([], 0)
    if lines and lines[0].indent != 0:
        raise SongError("the first line is indented", file=file, line=lines[0].no)
    if i < len(lines):
        raise SongError("indentation does not match any outer block", file=file, line=lines[i].no)
    return nodes


# ----------------------------------------------------------------------------
# expressions (a Pratt-style recursive descent over one logical line's tokens)
# ----------------------------------------------------------------------------
class _Expr:
    """Parse one expression from tokens[i:]. Node shapes are tuples; [-1] is the source line."""

    CMP = ("==", "!=", "<", "<=", ">", ">=")

    def __init__(self, toks: list[Tok], file, i: int = 0):
        self.t, self.i, self.file = toks, i, file

    # -- token helpers --
    def peek(self, k=0):
        j = self.i + k
        return self.t[j] if j < len(self.t) else None

    def at(self, value, kind=None) -> bool:
        p = self.peek()
        return p is not None and p.value == value and (kind is None or p.kind == kind) and p.kind != "str"

    def eat(self, value):
        if not self.at(value):
            p = self.peek()
            got = f"'{p.value}'" if p else "end of line"
            raise SongError(f"expected '{value}', got {got}", file=self.file, line=(p or self.t[-1]).line)
        self.i += 1
        return self.t[self.i - 1]

    def err(self, msg, suggestion=None):
        p = self.peek() or self.t[-1]
        raise SongError(msg, file=self.file, line=p.line, suggestion=suggestion)

    # -- grammar --
    def expr(self):
        a = self.with_()
        if self.at("if", "name"):
            line = self.eat("if").line
            c = self.with_()
            self.eat("else")
            return ("ifx", c, a, self.expr(), line)
        return a

    def with_(self):
        a = self.or_()
        while self.at("with", "name"):
            line = self.eat("with").line
            a = ("bin", "with", a, self.or_(), line)
        return a

    def or_(self):
        a = self.and_()
        while self.at("or", "name"):
            line = self.eat("or").line
            a = ("or", a, self.and_(), line)
        return a

    def and_(self):
        a = self.not_()
        while self.at("and", "name"):
            line = self.eat("and").line
            a = ("and", a, self.not_(), line)
        return a

    def not_(self):
        if self.at("not", "name"):
            line = self.eat("not").line
            return ("not", self.not_(), line)
        return self.cmp()

    def cmp(self):
        a = self.rng()
        p = self.peek()
        if p and p.kind == "op" and p.value in self.CMP:
            self.i += 1
            a = ("bin", p.value, a, self.rng(), p.line)
        return a

    def rng(self):
        a = self.bar()
        if self.at(".."):
            line = self.eat("..").line
            a = ("bin", "..", a, self.bar(), line)
        return a

    def _left(self, sub, ops):
        a = sub()
        while True:
            p = self.peek()
            if not (p and p.kind == "op" and p.value in ops):
                return a
            self.i += 1
            a = ("bin", p.value, a, sub(), p.line)

    def bar(self):
        return self._left(self.amp, ("|",))

    def amp(self):
        return self._left(self.add, ("&",))

    def add(self):
        return self._left(self.mul, ("+", "-"))

    def mul(self):
        return self._left(self.unary, ("*", "/", "//", "%"))

    def unary(self):
        if self.at("-", "op"):
            line = self.eat("-").line
            return ("neg", self.unary(), line)
        return self.postfix()

    def postfix(self):
        a = self.atom()
        while True:
            if self.at("(", "op"):
                line = self.eat("(").line
                args, kwargs = [], []
                while not self.at(")"):
                    p, q = self.peek(), self.peek(1)
                    if p and p.kind == "name" and q and q.value == "=" and q.kind == "op":
                        self.i += 2
                        kwargs.append((p.value, self.expr()))
                    else:
                        if kwargs:
                            self.err("positional argument after a keyword argument")
                        args.append(self.expr())
                    if not self.at(")"):
                        self.eat(",")
                self.eat(")")
                a = ("call", a, args, kwargs, line)
            elif self.at("[", "op"):
                line = self.eat("[").line
                k = self.expr()
                self.eat("]")
                a = ("idx", a, k, line)
            elif self.at(".", "op"):
                line = self.eat(".").line
                p = self.peek()
                if not p or p.kind != "name":
                    self.err("expected a name after '.'")
                self.i += 1
                a = ("attr", a, p.value, line)
            else:
                return a

    def atom(self):
        p = self.peek()
        if p is None:
            self.err("expected a value, got end of line")
        self.i += 1
        if p.kind == "num":
            return ("lit", p.value, p.line)
        if p.kind == "str":
            return ("lit", p.value, p.line)
        if p.kind == "name":
            if p.value in ("true", "false", "none"):
                return ("lit", {"true": True, "false": False, "none": None}[p.value], p.line)
            if p.value in KEYWORDS:
                self.i -= 1
                self.err(f"'{p.value}' is a keyword, not a value")
            return ("name", p.value, p.line)
        if p.value == "(":
            e = self.expr()
            self.eat(")")
            return e
        if p.value == "[":
            items = []
            while not self.at("]"):
                items.append(self.expr())
                if not self.at("]"):
                    self.eat(",")
            self.eat("]")
            return ("list", items, p.line)
        if p.value == "{":
            items = []
            while not self.at("}"):
                k = self.peek()
                if k is None or k.kind not in ("name", "str"):
                    self.err("map keys are names or strings: {kick: \"x...\", hat: \"-.x.\"}")
                self.i += 1
                self.eat(":")
                items.append((k.value, self.expr()))
                if not self.at("}"):
                    self.eat(",")
            self.eat("}")
            return ("map", items, p.line)
        self.i -= 1
        self.err(f"unexpected '{p.value}'")

    def done(self):
        if self.peek() is not None:
            self.err(f"unexpected '{self.peek().value}' after the expression")


def parse_expr(toks: list[Tok], file) -> tuple:
    if not toks:
        raise SongError("expected a value", file=file)
    p = _Expr(toks, file)
    e = p.expr()
    p.done()
    return e


# ----------------------------------------------------------------------------
# values
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Ref:
    """A bare name that is not a variable: a style, mod or motif, resolved when bound to a role."""
    name: str
    line: int | None = None


@dataclass(frozen=True)
class Part:
    """A part value: a style with mods and options, plus lane edits in order.

    ops: ("set", lane, steps) replaces a lane; ("layer", {lane: steps}) adds hits to lanes
    (on top of the style's own lane when the part has a style)."""
    style: str | None = None
    mods: tuple = ()
    opts: tuple = ()               # ((key, value), ...) part options and sources (order, oct, deg, ...)
    ops: tuple = ()
    line: int | None = None

    def opt_dict(self) -> dict:
        return dict(self.opts)


@dataclass
class Func:
    name: str
    params: list                   # [(name, default value or _REQUIRED)]
    body: object                   # ("expr", node) | [stmts]
    env: dict
    line: int


_REQUIRED = object()


def _kind(v) -> str:
    if isinstance(v, bool):
        return "a boolean"
    if isinstance(v, (int, float)):
        return "a number"
    if isinstance(v, str):
        return "a string"
    if isinstance(v, list):
        return "a list"
    if isinstance(v, dict):
        return "a map"
    if isinstance(v, (Ref, Part)):
        return "a part"
    if isinstance(v, Func):
        return "a function"
    return "none" if v is None else type(v).__name__


# -- step strings -----------------------------------------------------------
def _bars(s: str) -> list[str]:
    return [b.replace(" ", "") for b in s.split("|")]


def _check_len(s: str, what: str):
    if len(s) > LIMIT:
        raise SongError(f"{what} is {len(s)} characters; the limit is {LIMIT}")
    return s


def overlay(a: str, b: str) -> str:
    """Layer two step strings: per step the louder wins (X > f > r > x > - > o > .).

    Bars cycle to the longer pattern; within a bar both are placed on their common grid."""
    ab, bb = _bars(a), _bars(b)
    n = math.lcm(len(ab), len(bb))
    out = []
    for i in range(n):
        x, y = ab[i % len(ab)], bb[i % len(bb)]
        if not x or not y:
            raise SongError(f"can't layer an empty bar ('{a}' & '{b}')")
        L = math.lcm(len(x), len(y))
        if L > 192:
            raise SongError(f"layering '{x}' and '{y}' needs a {L}-step grid", suggestion="use grids that divide 192")
        res = ["."] * L
        for s in (x, y):
            k = L // len(s)
            for j, c in enumerate(s):
                if c not in STEP_RANK:
                    raise SongError(f"unknown step '{c}' in '{s}'", suggestion="steps are X x - o . f r")
                if STEP_RANK[c] > STEP_RANK[res[j * k]]:
                    res[j * k] = c
        out.append("".join(res))
    return _check_len("|".join(out), "a layered step string")


def euclid(k: int, n: int, rot: int = 0) -> str:
    """Bjorklund's even spread of k hits over n steps: euclid(3, 8) = 'x..x..x.'."""
    if not (isinstance(k, int) and isinstance(n, int)) or n <= 0 or n > 192:
        raise SongError(f"euclid({k}, {n}): k and n are whole numbers, 0 < n <= 192")
    k = max(0, min(k, n))
    a, b = [[1] for _ in range(k)], [[0] for _ in range(n - k)]
    while len(b) > 1 and a:
        m = min(len(a), len(b))
        a, b = [a[i] + b[i] for i in range(m)], (a[m:] if len(a) > m else b[m:])
    s = "".join("x" if x else "." for x in sum(a + b, []))
    return rotate(s, rot)


def rotate(s: str, n: int) -> str:
    """Rotate each bar right by n steps (negative: left)."""
    out = []
    for b in _bars(s):
        k = int(n) % len(b) if b else 0
        out.append(b[-k:] + b[:-k] if k else b)
    return "|".join(out)


def reverse(s: str) -> str:
    return "|".join(b[::-1] for b in _bars(s))


BUILTINS = {
    "euclid": lambda k, n, rot=0: euclid(k, n, rot),
    "rot": lambda s, n: rotate(_need_str(s, "rot"), n),
    "rev": lambda s: reverse(_need_str(s, "rev")),
    "len": lambda x: len(x),
    "min": min,
    "max": max,
}


def _need_str(s, fn):
    if not isinstance(s, str):
        raise SongError(f"{fn}() takes a step string, got {_kind(s)}")
    return s


# ----------------------------------------------------------------------------
# statements
# ----------------------------------------------------------------------------
_X = re.compile(r"x(\d+)")
_EVENT = re.compile(r"""\s*!(?P<type>[A-Za-z_]\w*)
    (?::(?P<len>\d+(?:\.\d+)?)(?P<unit>b?))?
    (?:@(?P<pos>cue:\w+|f\d+|[+-]?\d+(?:\.\d+)?(?::\d+(?:\.\d+)?)?|[A-Za-z_]\w*(?:[+-]\d+(?:\.\d+)?)?(?::\d+(?:\.\d+)?)?))?
    (?:\((?P<params>[^)]*)\))?""", re.X)


@dataclass
class EventLit:
    type: str
    length: float | None
    beats: bool
    pos: str | None
    params: dict
    line: int


def _scalar(v: str):
    v = v.strip()
    for f in (int, float):
        try:
            return f(v)
        except ValueError:
            pass
    return {"true": True, "false": False}.get(v, v.strip("\"'"))


def _kv(text: str) -> dict:
    out = {}
    for item in filter(None, (x.strip() for x in text.split(","))):
        k, eq, v = item.partition("=")
        if not eq:
            raise SongError(f"'{item}' is not key=value")
        out[k.strip()] = _scalar(v)
    return out


def _events(raw: str, line: int, file) -> tuple[list[EventLit], str]:
    """Parse '!impact !riser:2 !riser:1@+8(size=xl)' from the start of raw; return events and the rest."""
    out, pos = [], 0
    while True:
        m = _EVENT.match(raw, pos)
        if not m or not m.group("type"):
            break
        try:
            params = _kv(m["params"]) if m["params"] else {}
        except SongError as e:
            raise SongError(e.message, file=file, line=line, suggestion="write !hit(size=xl, keep=drums)") from None
        n = m["len"]
        out.append(EventLit(m["type"], None if n is None else _scalar(n), m["unit"] == "b", m["pos"], params, line))
        pos = m.end()
    rest = raw[pos:].strip()
    if rest.startswith("!"):
        raise SongError(f"event '{rest.split()[0]}' not understood", file=file, line=line,
                        suggestion="write !type[:bars|:beats b][@+bar:beat|@bar|@f123|@cue:x][(k=v)], e.g. !riser:2@+8")
    return out, rest


class _Parser:
    """Logical-line tree -> statement tuples, checking what may appear where."""

    def __init__(self, file):
        self.file = file

    def err(self, msg, line, suggestion=None):
        raise SongError(msg, file=self.file, line=line, suggestion=suggestion)

    def block(self, nodes: list[Node], ctx: str) -> list:
        out, i = [], 0
        while i < len(nodes):
            node = nodes[i]
            t0 = node.line.toks[0]
            if t0.kind == "name" and t0.value == "if":
                arms, else_body = [self.if_arm(node, ctx)], None
                while i + 1 < len(nodes) and nodes[i + 1].line.toks[0].value in ("elif", "else") \
                        and nodes[i + 1].line.toks[0].kind == "name":
                    i += 1
                    nxt = nodes[i]
                    if nxt.line.toks[0].value == "elif":
                        arms.append(self.if_arm(nxt, ctx))
                    else:
                        else_body = self.body_of(nxt, 1, ctx)
                        break
                out.append(("if", arms, else_body or [], node.line.no))
            elif t0.kind == "name" and t0.value in ("elif", "else"):
                self.err(f"'{t0.value}' without an 'if' before it", node.line.no)
            else:
                out.append(self.stmt(node, ctx))
            i += 1
        return out

    def body_of(self, node: Node, k: int, ctx: str) -> list:
        """The statements after the ':' at token k: an indented block, or the rest of the line."""
        toks = node.line.toks
        if k >= len(toks) or toks[k].value != ":" or toks[k].kind != "op":
            self.err("expected ':'", node.line.no)
        if k == len(toks) - 1:
            return self.block(node.children, ctx)
        return self.block([Node(node.line.sub(k + 1))], ctx)

    def colon_at(self, toks, start=1) -> int:
        depth = 0
        for k in range(start, len(toks)):
            t = toks[k]
            if t.kind == "op" and t.value in "([{":
                depth += 1
            elif t.kind == "op" and t.value in ")]}":
                depth -= 1
            elif t.kind == "op" and t.value == ":" and depth == 0:
                return k
        self.err("expected ':'", toks[0].line)

    def if_arm(self, node: Node, ctx: str):
        toks = node.line.toks
        k = self.colon_at(toks)
        return parse_expr(toks[1:k], self.file), self.body_of(node, k, ctx)

    def stmt(self, node: Node, ctx: str):
        ln = node.line
        toks = ln.toks
        t0 = toks[0]
        word = t0.value if t0.kind == "name" else None
        nxt = toks[1] if len(toks) > 1 else None
        is_assign = word and nxt is not None and nxt.kind == "op" and nxt.value in ("=", "+=", "-=", ".")
        if word in DIRECTIVES and not is_assign:
            if ctx != "top":
                self.err(f"'{word}' lines go at the top level, not inside a block", ln.no)
            return ("directive", word, ln.raw, ln.no)
        if word in LATER_DIRECTIVES and not is_assign:
            self.err(f"'{word}' lines are not in the language prototype yet", ln.no,
                     "they arrive with the compact parser (ROADMAP P6); leave them out for now")
        if word == "def":
            if ctx != "top":
                self.err("define functions at the top level", ln.no)
            return self.def_(node)
        if word == "return":
            if ctx != "def":
                self.err("'return' outside a function", ln.no)
            return ("return", parse_expr(toks[1:], self.file), ln.no)
        if word == "form":
            if ctx != "top":
                self.err("'form:' goes at the top level", ln.no)
            if len(toks) != 2 or toks[1].value != ":":
                self.err("write 'form:' and indent the sections under it", ln.no)
            return ("form", self.block(node.children, "form"), ln.no)
        if word == "for":
            if ctx != "form":
                self.err("'for' loops go in the form block", ln.no,
                         "inside a section, use 'every N bars:' or 'if'")
            if len(toks) < 4 or toks[1].kind != "name" or toks[2].value != "in":
                self.err("write 'for i in 1..4:'", ln.no)
            k = self.colon_at(toks, 3)
            return ("for", toks[1].value, parse_expr(toks[3:k], self.file), self.body_of(node, k, "form"), ln.no)
        if word == "every":
            if ctx not in ("form", "inst"):
                self.err("'every' goes in the form block or under a section", ln.no)
            return self.every(node, ctx)
        if t0.kind == "op" and t0.value == "!":
            if ctx not in ("inst", "form"):
                self.err("events go on form lines or under a section in the form", ln.no)
            evs, rest = _events(ln.raw, ln.no, self.file)
            if rest:
                self.err(f"unexpected '{rest}' after the events", ln.no)
            return ("event", evs, ln.no)
        if is_assign:
            return self.assign(ln, ctx)
        if ctx == "form" and word and word not in KEYWORDS:
            return self.instance(node)
        if word in KEYWORDS:
            self.err(f"'{word}' can't start a line here", ln.no)
        self.err("expected a definition (name = value)" if ctx == "top" else "statement not understood", ln.no,
                 {"top": "e.g. verse = {drums: four_floor, bass: sub}",
                  "form": "a form line is '<section> <bars> [xN] [!events]'",
                  "inst": "under a section: drums += fill, drums.kick = \"x...\", every 8 bars: ..., !impact",
                  "def": "a function body is 'name = value' lines and 'return value'"}.get(ctx))

    def assign(self, ln: Line, ctx: str):
        toks, path, k = ln.toks, [ln.toks[0].value], 1
        while k < len(toks) and toks[k].value == "." and toks[k].kind == "op":
            if k + 1 >= len(toks) or toks[k + 1].kind != "name":
                self.err("expected a name after '.'", ln.no)
            path.append(toks[k + 1].value)
            k += 2
        if k >= len(toks) or toks[k].value not in ("=", "+=", "-="):
            self.err("expected '=', '+=' or '-='", ln.no)
        if path[0] in KEYWORDS or path[0] in BUILTINS:
            self.err(f"'{path[0]}' is reserved", ln.no, "pick another name")
        return ("assign", path, toks[k].value, parse_expr(toks[k + 1:], self.file), ln.no)

    def def_(self, node: Node):
        ln, toks = node.line, node.line.toks
        if len(toks) < 4 or toks[1].kind != "name" or toks[2].value != "(":
            self.err("write 'def name(a, b=1):'", ln.no)
        name, params, k = toks[1].value, [], 3
        while toks[k].value != ")":
            if toks[k].kind != "name":
                self.err("parameters are names, optionally with defaults: def four(acc=0.8):", ln.no)
            pname, k = toks[k].value, k + 1
            default = _REQUIRED
            if toks[k].value == "=":
                p = _Expr(toks, self.file, k + 1)
                default = p.expr()
                k = p.i
            params.append((pname, default))
            if toks[k].value == ",":
                k += 1
        k += 1
        if k >= len(toks) or toks[k].value != ":":
            self.err("expected ':' after the parameters", ln.no)
        if k == len(toks) - 1:
            body = self.block(node.children, "def")
            if not any(s[0] == "return" for s in body) and not any(s[0] == "if" for s in body):
                self.err(f"function {name} has no 'return'", ln.no)
        else:
            body = ("expr", parse_expr(toks[k + 1:], self.file))
        return ("def", name, params, body, ln.no)

    def every(self, node: Node, ctx: str):
        ln, toks = node.line, node.line.toks
        k = self.colon_at(toks)
        head = toks[1:k]
        at = None
        if head and head[-1].kind in ("num", "name") and len(head) >= 2 and head[-2].value == "at":
            at, head = parse_expr(head[-1:], self.file), head[:-2]
        if head and head[-1].value == "bars":
            head = head[:-1]
        if not head:
            self.err("write 'every 8 bars: drums += fill' or 'every 4 bars at 1: ...'", ln.no)
        body = self.body_of(node, k, "inst")
        for s in body:
            if s[0] != "assign":
                self.err("'every' takes part edits such as 'drums += fill'", ln.no)
        return ("every", parse_expr(head, self.file), at, body, ln.no)

    def instance(self, node: Node):
        ln, toks = node.line, node.line.toks
        head, k = toks[0].value, 1
        bars = None
        if k < len(toks):
            t = toks[k]
            if t.kind == "num" or (t.kind == "op" and t.value == "(") or (
                    t.kind == "name" and t.value not in KEYWORDS and not _X.fullmatch(t.value)):
                p = _Expr(toks, self.file, k)      # stops at xN, as, ! and ':' (none of them is an operator)
                bars = p.expr()
                k = p.i
        rep = None
        if k < len(toks) and toks[k].kind == "name" and _X.fullmatch(toks[k].value):
            rep, k = int(toks[k].value[1:]), k + 1
            if not 1 <= rep <= LIMIT:
                self.err(f"x{rep}: repeat 1..{LIMIT} times", ln.no)
        name = None
        if k < len(toks) and toks[k].value == "as":
            if k + 1 >= len(toks) or toks[k + 1].kind != "name":
                self.err("write 'as <name>'", ln.no)
            name, k = toks[k + 1].value, k + 2
        events, body = [], []
        if k < len(toks):
            t = toks[k]
            rest_raw = ln.text[t.pos:toks[-1].end]
            if t.value == "!":
                events, rest_raw = _events(rest_raw, ln.no, self.file)
            if rest_raw:
                if not rest_raw.startswith(":"):
                    self.err(f"unexpected '{rest_raw.split()[0]}' on a form line", ln.no,
                             "a form line is '<section> <bars> [xN] [as name] [!events] [: edits]'")
                colon = next(j for j, x in enumerate(toks) if x.pos >= ln.text.index(rest_raw, t.pos) and x.value == ":")
                body = self.body_of(node, colon, "inst")
        elif node.children:
            self.err("expected ':' before the indented block", ln.no)
        return ("inst", head, bars, rep, name, events, body, ln.no)


# ----------------------------------------------------------------------------
# evaluation
# ----------------------------------------------------------------------------
@dataclass
class _Inst:
    base: str
    section: dict
    bars: float
    events: list
    every: list                    # [(n, at, path, op, value, line)] instance-relative
    line: int
    name: str | None = None


class _Interp:
    def __init__(self, file):
        self.file = file
        self.env: dict = {}
        self.song: dict = {}
        self.instances: list[_Inst] = []
        self.song_every: list = []           # form-level 'every' (song bars)
        self.form_line = None
        self.iterations = 0
        self.stack: list[str] = []
        self.scope: dict = {}

    def err(self, msg, line=None, suggestion=None):
        raise SongError(msg, file=self.file, line=line, suggestion=suggestion)

    # -- expressions --
    def ev(self, n, env):
        t = n[0]
        if t == "lit":
            return n[1]
        if t == "name":
            name = n[1]
            if name in env:
                return env[name]
            if name in BUILTINS:
                return BUILTINS[name]
            return Ref(name, n[2])
        if t == "list":
            items = [self.ev(x, env) for x in n[1]]
            return items
        if t == "map":
            return {k: self.ev(v, env) for k, v in n[1]}
        if t == "ifx":
            return self.ev(n[2], env) if self.truth(self.ev(n[1], env), n[-1]) else self.ev(n[3], env)
        if t == "or":
            a = self.ev(n[1], env)
            return a if self.truth(a, n[-1]) else self.ev(n[2], env)
        if t == "and":
            a = self.ev(n[1], env)
            return self.ev(n[2], env) if self.truth(a, n[-1]) else a
        if t == "not":
            return not self.truth(self.ev(n[1], env), n[-1])
        if t == "neg":
            v = self.ev(n[1], env)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                self.err(f"can't negate {_kind(v)}", n[-1])
            return -v
        if t == "bin":
            self.scope = env
            return self.binop(n[1], self.ev(n[2], env), self.ev(n[3], env), n[-1])
        if t == "idx":
            a, k = self.ev(n[1], env), self.ev(n[2], env)
            if isinstance(a, (list, str)) and isinstance(k, int) and not isinstance(k, bool):
                if not a:
                    self.err("index into an empty list", n[-1])
                return a[k % len(a)]                        # cyclic: lists never run out
            if isinstance(a, dict) and isinstance(k, str):
                return self.attr(a, k, n[-1])
            self.err(f"can't index {_kind(a)} with {_kind(k)}", n[-1])
        if t == "attr":
            return self.attr(self.ev(n[1], env), n[2], n[-1])
        if t == "call":
            f = self.ev(n[1], env)
            args = [self.ev(a, env) for a in n[2]]
            kwargs = {k: self.ev(v, env) for k, v in n[3]}
            return self.call(f, args, kwargs, n[-1])
        raise AssertionError(t)

    def truth(self, v, line):
        if isinstance(v, (Ref, Part, Func)):
            self.err(f"a condition must be a number, string, list or boolean, got {_kind(v)} "
                     f"'{getattr(v, 'name', None) or getattr(v, 'style', '')}'", line,
                     "is that name a typo for a loop variable?" if isinstance(v, Ref) else None)
        return bool(v)

    def attr(self, v, key, line):
        if isinstance(v, dict):
            if key not in v:
                self.err(f"no '{key}' in this map", line, did_you_mean(key, v) if v else "the map is empty")
            return v[key]
        if isinstance(v, Part):
            for op in reversed(v.ops):
                if op[0] == "set" and op[1] == key:
                    return op[2]
            if key in v.opt_dict():
                return v.opt_dict()[key]
        if isinstance(v, Ref):
            self.err(f"'{v.name}' is not defined, so '{v.name}.{key}' has no value", line,
                     did_you_mean(v.name, self.env) if self.env else None)
        self.err(f"can't read .{key} of {_kind(v)}", line)

    def call(self, f, args, kwargs, line):
        if isinstance(f, Ref):
            if args:
                self.err(f"style '{f.name}' takes options by name: {f.name}(order=[0, 2, 1])", line)
            return Part(f.name, opts=tuple(kwargs.items()), line=f.line or line)
        if isinstance(f, Part):
            return replace(f, opts=tuple({**f.opt_dict(), **kwargs}.items()))
        if isinstance(f, Func):
            return self.call_func(f, args, kwargs, line)
        if callable(f):
            try:
                return f(*args, **kwargs)
            except SongError as e:
                self.err(e.message, line, e.suggestion)
            except TypeError as e:
                self.err(f"bad arguments: {e}", line)
        self.err(f"can't call {_kind(f)}", line)

    def call_func(self, f: Func, args, kwargs, line):
        if f.name in self.stack:
            self.err(f"{f.name}() calls itself; SongMap functions can't recurse", line,
                     "unroll it with a for loop in the form block")
        if len(args) > len(f.params):
            self.err(f"{f.name}() takes {len(f.params)} arguments, got {len(args)}", line)
        local = dict(f.env)
        names = [p for p, _ in f.params]
        for k in kwargs:
            if k not in names:
                self.err(f"{f.name}() has no parameter '{k}'", line, did_you_mean(k, names))
        for i, (p, default) in enumerate(f.params):
            if i < len(args):
                local[p] = args[i]
            elif p in kwargs:
                local[p] = kwargs[p]
            elif default is not _REQUIRED:
                local[p] = default
            else:
                self.err(f"{f.name}() needs '{p}'", line)
        self.stack.append(f.name)
        try:
            if isinstance(f.body, tuple):
                return self.ev(f.body[1], local)
            out = self.run_def(f.body, local)
            if out is _REQUIRED:
                self.err(f"{f.name}() ended without 'return'", f.line)
            return out
        finally:
            self.stack.pop()

    def run_def(self, stmts, env):
        for s in stmts:
            if s[0] == "return":
                return self.ev(s[1], env)
            if s[0] == "assign":
                self.assign_var(s, env)
            elif s[0] == "if":
                body = self.pick(s, env)
                out = self.run_def(body, env)
                if out is not _REQUIRED:
                    return out
            else:
                self.err("only 'name = value', 'if' and 'return' go in a function", s[-1])
        return _REQUIRED

    def pick(self, s, env):
        for cond, body in s[1]:
            if self.truth(self.ev(cond, env), s[-1]):
                return body
        return s[2]

    # -- operators --
    def binop(self, op, a, b, line):
        num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)  # noqa: E731
        try:
            if op == "with":
                return self.with_(a, b, line)
            if op in ("==", "!="):
                for x in (a, b):
                    if isinstance(x, Ref) and not isinstance(a if x is b else b, (Ref, Part)):
                        names = [k for k, v in self.scope.items() if not isinstance(v, (dict, Func))]
                        self.err(f"'{x.name}' is not defined", line,
                                 did_you_mean(x.name, names) if names else "is it a loop variable?")
                return (a == b) == (op == "==")
            if op in ("<", "<=", ">", ">="):
                if not ((num(a) and num(b)) or (isinstance(a, str) and isinstance(b, str))):
                    self.err(f"can't compare {_kind(a)} and {_kind(b)}", line)
                return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
            if op == "..":
                if not (isinstance(a, int) and isinstance(b, int)) or isinstance(a, bool):
                    self.err(f"a range needs whole numbers: 1..4, got {_kind(a)}..{_kind(b)}", line)
                if abs(b - a) + 1 > LIMIT:
                    self.err(f"range {a}..{b} has more than {LIMIT} steps", line, "loops have static, small bounds")
                return list(range(a, b + 1)) if b >= a else list(range(a, b - 1, -1))
            if num(a) and num(b):
                if op in ("/", "//", "%") and b == 0:
                    self.err("division by zero", line)
                f = {"+": lambda: a + b, "-": lambda: a - b, "*": lambda: a * b, "/": lambda: a / b,
                     "//": lambda: a // b, "%": lambda: a % b}.get(op)
                return f() if f else self.bad(op, a, b, line)
            if op == "+" and isinstance(a, str) and isinstance(b, str):
                return _check_len(a + b, "a step string")
            if op == "+" and isinstance(a, list) and isinstance(b, list):
                return self.cap(a + b, line)
            if op == "*" and isinstance(a, (str, list)) and isinstance(b, int) and not isinstance(b, bool):
                out = a * max(0, b)
                return _check_len(out, "a step string") if isinstance(a, str) else self.cap(out, line)
            if op == "|" and isinstance(a, str) and isinstance(b, str):
                return _check_len(a + "|" + b, "a step string")
            if op == "&" and isinstance(a, str) and isinstance(b, str):
                return overlay(a, b)
            if op == "+" and self.is_kit_value(a) and self.is_kit_value(b):
                return self.layer(a, b, line)
            if op == "-" and isinstance(a, (Ref, Part)) and isinstance(b, Ref):
                p = self.as_part(a, line)
                if b.name not in p.mods:
                    self.err(f"'{b.name}' is not a mod of this part", line,
                             did_you_mean(b.name, p.mods) if p.mods else "it has no mods")
                return replace(p, mods=tuple(m for m in p.mods if m != b.name))
        except SongError as e:
            raise SongError(e.message, file=self.file, line=e.line or line, suggestion=e.suggestion) from None
        return self.bad(op, a, b, line)

    def bad(self, op, a, b, line):
        hint = {"+": "+ adds numbers, joins strings and lists, and layers beats (full + hats16, {kick: ...} + {...})",
                "|": "| joins step strings bar by bar: \"x...\" | \"x.x.\"",
                "&": "& layers two step strings: \"x...\" & \"..x.\"",
                "-": "- subtracts numbers or removes a mod: drums - fill"}.get(op)
        self.err(f"can't use '{op}' on {_kind(a)} and {_kind(b)}", line, hint)

    def cap(self, xs, line):
        if len(xs) > LIMIT:
            self.err(f"list of {len(xs)} items; the limit is {LIMIT}", line)
        return xs

    @staticmethod
    def is_kit_value(v):
        return isinstance(v, (Ref, Part, dict))

    def as_part(self, v, line) -> Part:
        if isinstance(v, Part):
            return v
        if isinstance(v, Ref):
            return Part(v.name, line=v.line or line)
        if isinstance(v, dict):
            p = Part(line=line)
            return self.with_(p, v, line)
        self.err(f"expected a part (a style, beat or map), got {_kind(v)}", line,
                 "a step string needs a lane: {kick: \"x...\"}" if isinstance(v, str) else None)

    def layer(self, a, b, line):
        """`+` on beats: style + mod, beat + lanes, lanes + lanes (hits on the same lane are layered)."""
        if isinstance(a, dict) and isinstance(b, dict):
            out = dict(a)
            for k, v in b.items():
                if k in out:
                    if not (isinstance(out[k], str) and isinstance(v, str)):
                        self.err(f"can't layer lane '{k}': both sides must be step strings", line,
                                 "use 'with' to replace keys, or & to layer two strings")
                    out[k] = overlay(out[k], v)
                else:
                    out[k] = v
            return out
        p = self.as_part(a, line)
        if isinstance(b, Ref):
            return replace(p, mods=p.mods + (b.name,))
        if isinstance(b, dict):
            return replace(p, ops=p.ops + (("layer", dict(b)),))
        q = b
        if p.style and q.style:
            self.err(f"can't layer two styles ('{p.style}' + '{q.style}') in one part", line,
                     f"layer lanes instead: {p.style} + {{kick: \"...\"}}")
        base, top = (p, q) if p.style or not q.style else (q, p)
        return replace(base, mods=base.mods + top.mods, opts=tuple({**top.opt_dict(), **base.opt_dict()}.items()),
                       ops=base.ops + top.ops)

    def with_(self, a, b, line):
        if not isinstance(b, dict):
            self.err(f"'with' takes a map on the right: x with {{drums: half}}, got {_kind(b)}", line)
        if isinstance(a, dict):
            out = dict(a)
            for k, v in b.items():
                if v is None:
                    out.pop(k, None)
                else:
                    out[k] = v
            return out
        if isinstance(a, (Ref, Part)):
            p = self.as_part(a, line)
            opts, ops, style, mods = p.opt_dict(), list(p.ops), p.style, p.mods
            for k, v in b.items():
                if k == "style":
                    if isinstance(v, Ref):
                        style, mods = v.name, ()
                    elif isinstance(v, Part):
                        style, mods = v.style, v.mods
                    elif isinstance(v, str):
                        style, *ms = [x.strip() for x in v.split("+")]
                        mods = tuple(ms)
                    else:
                        self.err(f"style must be a name, got {_kind(v)}", line)
                elif k == "mods":
                    mods = tuple(x.name if isinstance(x, Ref) else str(x) for x in (v if isinstance(v, list) else [v]))
                elif k in PART_KEYS:
                    if v is None:
                        opts.pop(k, None)
                    else:
                        opts[k] = v
                else:
                    ops.append(("set", k, "." if v is None else v))
            return Part(style, mods, tuple(opts.items()), tuple(ops), p.line or line)
        self.err(f"'with' works on sections, beats and parts, not {_kind(a)}", line)

    # -- statements --
    def assign_var(self, s, env):
        _, path, op, expr, line = s
        val = self.ev(expr, env)
        root = path[0]
        if len(path) == 1:
            if op != "=" and root not in env:
                self.err(f"'{root}' is not defined yet", line, did_you_mean(root, env) if env else None)
            env[root] = val if op == "=" else self.binop(op[0], env[root], val, line)
            return
        if root not in env:
            self.err(f"'{root}' is not defined", line, did_you_mean(root, env) if env else "define it first")
        env[root] = self.set_path(env[root], path[1:], op, val, line, root)

    def set_path(self, cur, keys, op, val, line, where):
        """Return a copy of `cur` with the value at `keys` set (=) or combined (+= -=); none removes."""
        if not keys:
            if op == "=":
                return val
            if cur is None:
                if op == "+=":
                    return val
                self.err(f"{where} is not set", line)
            return self.binop(op[0], cur, val, line)
        k, rest = keys[0], keys[1:]
        if isinstance(cur, dict):
            out = dict(cur)
            new = self.set_path(cur.get(k), rest, op, val, line, f"{where}.{k}")
            if new is None:
                out.pop(k, None)
            else:
                out[k] = new
            return out
        if isinstance(cur, (Ref, Part)):
            if rest:
                self.err(f"{where}.{k} is a lane; lanes have no fields", line)
            p = self.as_part(cur, line)
            if k in PART_KEYS:
                old = p.opt_dict().get(k)
                return self.with_(p, {k: self.set_path(old, [], op, val, line, f"{where}.{k}")}, line)
            if op == "=":
                return replace(p, ops=p.ops + (("set", k, "." if val is None else val),))
            if op == "+=":
                if not isinstance(val, str):
                    self.err(f"{where}.{k} += needs a step string, got {_kind(val)}", line)
                return replace(p, ops=p.ops + (("layer", {k: val}),))
            self.err(f"can't use '{op}' on lane {where}.{k}", line, "set it: x.kick = \"x...\"")
        self.err(f"can't set .{k} on {_kind(cur)} ({where})", line)

    def run_top(self, stmts):
        for s in stmts:
            kind = s[0]
            if kind == "directive":
                self.directive(s[1], s[2], s[3])
            elif kind == "assign":
                self.assign_var(s, self.env)
            elif kind == "def":
                _, name, params, body, line = s
                if name in self.env:
                    self.err(f"'{name}' is already defined", line)
                defaults = [(p, d if d is _REQUIRED else self.ev(d, self.env)) for p, d in params]
                self.env[name] = Func(name, defaults, body, dict(self.env), line)   # snapshot: no self-reference
            elif kind == "form":
                if self.form_line is not None:
                    self.err("a second form block", s[2], f"the first is on line {self.form_line}")
                self.form_line = s[2]
                self.run_form(s[1], dict(self.env))
            else:
                self.err(f"'{kind}' at the top level", s[-1])

    def tick(self, line):
        self.iterations += 1
        if self.iterations > LIMIT:
            self.err(f"the form unrolls to more than {LIMIT} steps", line, "loops have static, small bounds")

    def run_form(self, stmts, env):
        for s in stmts:
            kind = s[0]
            if kind == "inst":
                self.place(s, env)
            elif kind == "for":
                _, var, it, body, line = s
                items = self.ev(it, env)
                if not isinstance(items, list):
                    self.err(f"for needs a range or a list (1..4, [a, b]), got {_kind(items)}", line)
                # loop names live in the form's scope only while the loop runs; assignments in the body
                # rebind the form's variables, so they carry into later iterations and lines
                names = (var, "first", "last")
                saved = {k: env[k] for k in names if k in env}
                for x in items:
                    self.tick(line)
                    env.update({var: x, "first": items[0], "last": items[-1]})
                    self.run_form(body, env)
                for k in names:
                    env.pop(k, None)
                env.update(saved)
            elif kind == "if":
                self.run_form(self.pick(s, env), env)
            elif kind == "assign":
                self.assign_var(s, env)
            elif kind == "every":
                for edit in s[3]:
                    self.song_every.append((self.ev(s[1], env), None if s[2] is None else self.ev(s[2], env),
                                            edit[1], edit[2], self.ev(edit[3], env), s[-1]))
            elif kind == "event":
                for e in s[1]:
                    if e.pos is None or e.pos.startswith(("+", "-")):
                        self.err(f"!{e.type} on its own form line needs an absolute position (@12, @f3960, @name+8)",
                                 e.line)
                self.instances.append(_Inst("", {}, 0, list(s[1]), [], s[-1], name=None))
            else:
                self.err(f"'{kind}' in the form block", s[-1])

    def place(self, s, env):
        _, head, bars_n, rep, name, events, body, line = s
        sec = env.get(head)
        if not isinstance(sec, dict):
            maps = [k for k, v in env.items() if isinstance(v, dict)]
            if isinstance(sec, Part) and sec.style and sec.style not in env:
                self.err(f"'{head}' is not a section: it was built from '{sec.style}', which is not defined", sec.line,
                         did_you_mean(sec.style, maps) if maps else None)
            if head in env:
                self.err(f"'{head}' is {_kind(sec)}, not a section", line, "a section is a map: {drums: full, bass: sub}")
            self.err(f"unknown section '{head}'", line, did_you_mean(head, maps) if maps else "define it first: "
                     f"{head} = {{drums: four_floor}}")
        bars = self.ev(bars_n, env) if bars_n is not None else sec.get("bars")
        if bars is None:
            self.err(f"how many bars of '{head}'?", line, f"write '{head} 8'")
        if isinstance(bars, bool) or not isinstance(bars, (int, float)) or bars <= 0:
            self.err(f"bars must be a number > 0, got {bars!r}", line)
        n = rep or 1
        for r in range(1, n + 1):
            self.tick(line)
            inst = _Inst(head, dict(sec), bars, list(events), [], line, name if n == 1 else None)
            if name and n > 1:
                inst.name = f"{name}_{r}" if r > 1 else name
            local = dict(env)
            if rep:
                local.update({"rep": r, "first": 1, "last": n})
            self.run_inst(body, inst, local)
            self.instances.append(inst)

    def run_inst(self, stmts, inst: _Inst, env):
        for s in stmts:
            kind = s[0]
            if kind == "assign":
                _, path, op, expr, line = s
                val = self.ev(expr, env)
                inst.section = self.set_path(inst.section, path, op, val, line, inst.base)
            elif kind == "if":
                self.run_inst(self.pick(s, env), inst, env)
            elif kind == "event":
                inst.events += s[1]
            elif kind == "every":
                n = self.ev(s[1], env)
                at = None if s[2] is None else self.ev(s[2], env)
                for edit in s[3]:
                    inst.every.append((n, at, edit[1], edit[2], self.ev(edit[3], env), s[-1]))
            else:
                self.err(f"'{kind}' under a form line", s[-1])

    # -- directives (the compact .sm header lines) --
    def directive(self, word, raw, line):
        try:
            args = shlex.split(raw, posix=True)[1:]
        except ValueError as e:
            self.err(f"{word}: {e}", line)
        try:
            getattr(self, f"d_{word}")(args, raw, line)
        except SongError as e:
            if e.line:
                raise
            raise SongError(e.message, file=self.file, line=line, suggestion=e.suggestion) from None

    def d_song(self, args, raw, line):
        if not args:
            self.err('write: song "Title" 120 4/4 Em fps=30', line)
        s = self.song
        s["title"] = args[0]
        keys = {"fps": "fps", "seed": "seed", "mood": "mood", "tail": "tail_seconds", "tuning": "tuning"}
        for a in args[1:]:
            k, eq, v = a.partition("=")
            if eq:
                if k == "video":
                    comp, _, frames = v.partition(":")
                    s["video"] = {"composition": comp, **({"frames": int(frames)} if frames else {})}
                elif k in keys:
                    s[keys[k]] = _scalar(v)
                else:
                    self.err(f"song: unknown option '{k}'", line, did_you_mean(k, [*keys, "video"]))
            elif re.fullmatch(r"\d+(\.\d+)?", a):
                s["tempo"] = _scalar(a)
            elif re.fullmatch(r"\d+/\d+", a):
                s["meter"] = a
            else:
                s["key"] = a

    def d_inst(self, args, raw, line):
        body = raw.split(None, 1)[1] if len(raw.split(None, 1)) > 1 else ""
        items = re.findall(r"([A-Za-z_]\w*)(?:=([\w/]+))?(?:\(([^)]*)\))?", body)
        if not items:
            self.err("write: inst bass(cutoff=700) keys=keys/felt_piano", line)
        ins = self.song.setdefault("instruments", {})
        for part, use, params in items:
            p = _kv(params) if params else {}
            ins[part] = ({"use": use, **p} if p else use) if use else p

    def d_kit(self, args, raw, line):
        kit = self.song.setdefault("instruments", {}).setdefault("drums", {"kit": {}})["kit"]
        for a in args:
            piece, eq, use = a.partition("=")
            if not eq:
                self.err(f"kit: write piece=instrument, got '{a}'", line)
            kit[piece] = use

    def d_chords(self, args, raw, line):
        h = self.song.setdefault("harmony", {})
        chords = [a for a in args if not a.startswith("/")]
        per = [a for a in args if a.startswith("/")]
        h["default"] = chords
        if per:
            h["chord_bars"] = _scalar(per[0][1:])

    def d_prog(self, args, raw, line):
        if len(args) != 2:
            self.err('write: prog doubt "Am:2 Dm7:2"', line)
        self.song.setdefault("harmony", {}).setdefault("progressions", {})[args[0]] = args[1]

    def d_motif(self, args, raw, line):
        if len(args) < 2:
            self.err('write: motif m1 deg oct=5 "0 2 4 | 3/2"', line)
        name, mode, m = args[0], "notes", LineDict()
        m.line = line
        for a in args[1:-1]:
            if a in ("deg", "rel"):
                mode = a
            elif a.startswith("oct="):
                m["octave"] = int(a[4:])
            elif a.startswith("key="):
                m["key"] = a[4:]
            else:
                self.err(f"motif {name}: unknown option '{a}'", line, "valid: deg rel oct=<n> key=<key>")
        m[mode] = args[-1]
        self.song.setdefault("motifs", {})[name] = m

    def d_cue(self, args, raw, line):
        for a in args:
            k, eq, v = a.partition("=")
            if not eq:
                self.err(f"cue: write name=position, got '{a}'", line)
            self.song.setdefault("cues", {})[k] = v

    def d_master(self, args, raw, line):
        keys = {"lufs": "target_lufs", "ceiling": "ceiling_db", "glue": "glue", "contrast": "preserve_contrast"}
        m = {}
        for a in args:
            k, eq, v = a.partition("=")
            if not eq:
                m["mode"] = a
            elif k in keys:
                m[keys[k]] = _scalar(v)
            else:
                self.err(f"master: unknown option '{k}'", line, did_you_mean(k, keys))
        self.song["master"] = m["mode"] if list(m) == ["mode"] else m


# ----------------------------------------------------------------------------
# compiling instances -> the v0.2 raw mapping
# ----------------------------------------------------------------------------
def _style_lanes(role: str, style: str | None, mods) -> dict[str, list]:
    """A kit style's lanes after its set/add mods (phrase mods such as `fill` stay per bar in expand)."""
    if not style:
        return {}
    from ..arrange.styles import get_style
    st = get_style(role, style)
    if st.shape != "kit":
        return {}
    lanes = {k: [v] for k, v in (st.get("steps") or {}).items()}
    for mod in mods:
        m = (st.get("mods") or {}).get(mod)
        if m is None:
            raise SongError(f"{role} style '{style}' has no mod '+{mod}'", suggestion=did_you_mean(mod, st.get("mods") or {}))
        for k, v in (m.get("set") or {}).items():
            lanes[k] = [v]
        for k, v in (m.get("add") or {}).items():
            lanes.setdefault(k, []).append(v)
    return lanes


def _flatten(specs: list, lane: str) -> str | dict:
    if len(specs) == 1:
        return specs[0]
    if not all(isinstance(x, str) for x in specs):
        raise SongError(f"lane '{lane}' has a velocity list, so it can't be layered",
                        suggestion=f"replace it instead: .{lane} = \"...\"")
    out = specs[0]
    for s in specs[1:]:
        out = overlay(out, s)
    return out


def _lane_value(v, lane):
    if isinstance(v, str):
        return v
    if isinstance(v, dict) and "steps" in v:
        return _plain(v)
    raise SongError(f"lane '{lane}' must be a step string or {{steps: \"...\", vel: [...]}}, got {_kind(v)}")


def _steps(role: str, p: Part) -> dict:
    """Materialize a part's lane edits into `steps` (each replaces that lane in expand)."""
    steps: dict = {}
    base = None
    for op in p.ops:
        if op[0] == "set":
            steps[op[1]] = _lane_value(op[2], op[1])
            continue
        for lane, v in op[1].items():
            v = _lane_value(v, lane)
            if lane in steps:
                cur = [steps[lane]]
            else:
                base = base if base is not None else _style_lanes(role, p.style, p.mods)
                cur = list(base.get(lane, []))
            steps[lane] = _flatten(cur + [v], lane)
    return steps


def _plain(v):
    if isinstance(v, Ref):
        return v.name
    if isinstance(v, list):
        return [_plain(x) for x in v]
    if isinstance(v, dict):
        return {k: _plain(x) for k, x in v.items()}
    if isinstance(v, (Part, Func)):
        raise SongError(f"expected a plain value here, got {_kind(v)}")
    return v


class _Compiler:
    def __init__(self, it: _Interp):
        self.it, self.file = it, it.file
        self.motifs = set((it.song.get("motifs") or {}))

    def err(self, msg, line, section=None, suggestion=None):
        raise SongError(msg, file=self.file, line=line, section=section, suggestion=suggestion)

    def check_style(self, role, name, line, section, opts):
        from ..arrange.styles import get_style, load_styles
        r = opts.get("role", role)
        try:
            get_style(r, name)
        except SongError as e:
            known = set(load_styles().get(r, {})) | self.motifs | {
                k for k, v in self.it.env.items() if isinstance(v, (Ref, Part))}
            self.err(e.message if r in load_styles() else f"'{name}' is not a style, motif or variable", line,
                     section, did_you_mean(name, known))

    def is_kit(self, role, p: Part, opts) -> bool:
        from ..arrange.styles import get_style
        from ..model import KIT_ROLES
        entry = (self.it.song.get("instruments") or {}).get(role)
        if role in KIT_ROLES or (isinstance(entry, dict) and "kit" in entry):
            return True
        return bool(p.style) and get_style(opts.get("role", role), p.style).shape == "kit"

    def part_raw(self, role, v, line, section):
        """A part value -> the YAML form parse_part reads."""
        if isinstance(v, Ref):
            if v.name not in self.motifs:
                self.check_style(role, v.name, v.line or line, section, {})
            return v.name
        if isinstance(v, list):
            names = []
            for x in v:
                if not isinstance(x, (Ref, str)):
                    self.err(f"{role}: a list is a motif list, got {_kind(x)} in it", line, section)
                n = x.name if isinstance(x, Ref) else x
                if n.split(":")[0] not in self.motifs:
                    self.err(f"unknown motif '{n}'", getattr(x, "line", None) or line, section,
                             did_you_mean(n, self.motifs) if self.motifs else "define it: motif m1 deg \"0 2 4\"")
                names.append(n)
            return names
        if isinstance(v, str):
            self.err(f"{role}: a bare string is ambiguous", line, section,
                     f"steps need a lane ({role}: {{kick: \"{v}\"}}); notes need a mode ({role}: {{notes: \"{v}\"}})")
        if isinstance(v, (dict, Part)):
            p = self.it.as_part(v, line)
            opts = {k: _plain(x) for k, x in p.opts}
            raw = dict(opts)
            if p.style:
                self.check_style(role, p.style, p.line or line, section, opts)
                raw["style"] = "+".join((p.style, *p.mods))
            elif p.mods:
                self.err(f"{role}: mods (+{p.mods[0]}) need a style", line, section,
                         f"write e.g. full + {p.mods[0]}")
            lanes = [op[1] if op[0] == "set" else next(iter(op[1]), "") for op in p.ops]
            if lanes and not self.is_kit(role, p, opts):
                lane = lanes[0]
                self.err(f"{role}: unknown part option '{lane}' ({role} is not a drum kit, so it has no lanes)",
                         p.line or line, section, did_you_mean(lane, PART_KEYS))
            steps = _steps(role, p)
            if steps:
                raw["steps"] = steps
            return raw
        self.err(f"{role}: expected a part, got {_kind(v)}", line, section)

    def apply_every(self, inst: _Inst, start_bar: float, every: list, song_level: bool):
        """Per-bar edits on kit lanes, baked into per-bar step strings ('a|b|...')."""
        for n, at, path, op, val, line in every:
            role = path[0]
            if role not in inst.section:
                if song_level:
                    continue
                self.err(f"every: the section has no '{role}' part", line, inst.name,
                         did_you_mean(role, inst.section) if inst.section else None)
            if not isinstance(n, int) or isinstance(n, bool) or n < 1:
                self.err(f"every {n!r}: write a whole number of bars", line, inst.name)
            k = n if at is None else at
            if not isinstance(k, int) or not 1 <= k <= n:
                self.err(f"every {n} bars at {k!r}: 'at' is a bar 1..{n} of each group", line, inst.name)
            nb = inst.bars
            if nb != int(nb):
                self.err("every needs a whole number of bars in the section", line, inst.name)
            p = self.it.as_part(inst.section[role], line)
            if not self.is_kit(role, p, p.opt_dict()):
                self.err(f"every: per-bar edits work on drum kits, and {role} is not one", line, inst.name,
                         f"split the section instead: {inst.base} {int(nb) - 1} then a 1-bar variant")
            try:
                edits = self.every_edits(role, p, path, op, val)
                steps = _steps(role, p)
                base_lanes = _style_lanes(role, p.style, p.mods)
            except SongError as e:
                self.err(e.message, line, inst.name, e.suggestion)
            ops = []
            for kind, lane, s in edits:
                base = steps.get(lane)
                if base is None and lane in base_lanes:
                    try:
                        base = _flatten(base_lanes[lane], lane)
                    except SongError as e:
                        self.err(e.message, line, inst.name, e.suggestion)
                if isinstance(base, dict) or isinstance(s, dict):
                    self.err(f"every: lane '{lane}' has a velocity list", line, inst.name,
                             "per-bar edits need plain step strings")
                bsegs = _bars(base) if base else None
                xsegs = _bars(s)
                segs, hits = [], 0
                for b in range(int(nb)):
                    bar_no = int(round(start_bar)) + b if song_level else b
                    bseg = bsegs[b % len(bsegs)] if bsegs else None
                    if bar_no % n == k - 1:
                        x = xsegs[hits % len(xsegs)]
                        hits += 1
                        seg = x if kind == "set" or not bseg else overlay(bseg, x)
                    else:
                        seg = bseg or "."
                    segs.append(seg)
                if not hits:
                    continue
                ops.append(("set", lane, _check_len("|".join(segs), f"lane '{lane}'")))
            inst.section[role] = replace(p, ops=p.ops + tuple(ops))

    def every_edits(self, role, p: Part, path, op, val):
        if len(path) == 2:
            if not isinstance(val, str):
                raise SongError(f"every: {role}.{path[1]} needs a step string, got {_kind(val)}")
            return [("set" if op == "=" else "layer", path[1], val)]
        if len(path) != 1 or op != "+=":
            raise SongError("every takes 'role += beat' or 'role.lane = \"...\"'",
                            suggestion="e.g. every 8 bars: drums += fill")
        if isinstance(val, dict):
            return [("layer", lane, _lane_value(v, lane)) for lane, v in val.items()]
        if isinstance(val, Ref):
            from ..arrange.styles import get_style
            if not p.style:
                raise SongError(f"'{val.name}' is a mod, and this part has no style")
            st = get_style(role, p.style)
            m = (st.get("mods") or {}).get(val.name)
            if m is None:
                raise SongError(f"{role} style '{p.style}' has no mod '+{val.name}'",
                                suggestion=did_you_mean(val.name, st.get("mods") or {}))
            if "every" in m:
                raise SongError(f"mod '{val.name}' already plays every {m['every']} bars",
                                suggestion=f"write {role} += {val.name} without 'every'")
            return ([("set", k, v) for k, v in (m.get("set") or {}).items()]
                    + [("layer", k, v) for k, v in (m.get("add") or {}).items()])
        raise SongError(f"every: {role} += needs a beat ({{lane: \"...\"}}) or a mod name, got {_kind(val)}")

    def compile(self) -> dict:
        it = self.it
        if it.form_line is None:
            raise SongError("no form block", file=self.file,
                            suggestion="end the file with 'form:' and one indented line per section: 'verse 8'")
        insts = [x for x in it.instances if x.base]
        if not insts:
            self.err("the form places no sections", it.form_line)
        # names: the first instance of `verse` is `verse`, later ones verse_2, verse_3, ...
        count: dict[str, int] = {}
        taken = {x.name for x in insts if x.name}
        for x in insts:
            if x.name:
                continue
            count[x.base] = count.get(x.base, 0) + 1
            nm = x.base if count[x.base] == 1 else f"{x.base}_{count[x.base]}"
            while nm in taken:
                count[x.base] += 1
                nm = f"{x.base}_{count[x.base]}"
            x.name = nm
            taken.add(nm)
        seen = {}
        for x in insts:
            if x.name in seen:
                self.err(f"two sections are named '{x.name}'", x.line, suggestion=f"the other is on line {seen[x.name]}; "
                         "rename one with 'as <name>'")
            seen[x.name] = x.line
        sections, events, bar = [], [], 0.0
        for x in it.instances:
            if not x.base:                      # a bare event line in the form
                events += [self.event(e, None) for e in x.events]
                continue
            self.apply_every(x, bar, x.every, False)
            self.apply_every(x, bar, it.song_every, True)
            sec = LineDict(name=x.name, bars=x.bars, parts={})
            sec.line = x.line
            for key, v in x.section.items():
                if key in SECTION_SETTINGS:
                    if key != "bars":
                        sec[key] = _plain(v)
                elif v is not None:
                    try:
                        sec["parts"][key] = self.part_raw(key, v, x.line, x.name)
                    except SongError as e:
                        if e.file:
                            raise
                        self.err(e.message, x.line, x.name, e.suggestion)
            sections.append(sec)
            events += [self.event(e, x.name) for e in x.events]
            bar += x.bars
        raw = {"songmap": float(VERSION), **it.song, "sections": sections}
        if events:
            raw["events"] = events
        return raw

    def event(self, e: EventLit, inst: str | None) -> LineDict:
        if e.pos is None:
            at = inst
        elif e.pos.startswith(("+", "-")):
            at = f"{inst}{e.pos}"
        else:
            at = e.pos
        d = LineDict(at=at, type=e.type)
        d.line = e.line
        if e.length is not None:
            d["beats" if e.beats else "bars"] = e.length
        d.update(e.params)
        return d


# ----------------------------------------------------------------------------
# entry points
# ----------------------------------------------------------------------------
def compile_raw(text: str, file: str | None = None) -> dict:
    """Program text -> the v0.2 raw mapping (what a YAML song map would hold)."""
    text = text.replace("\r\n", "\n")
    nodes = _tree(_lex(text, file), file)
    stmts = _Parser(file).block(nodes, "top")
    it = _Interp(file)
    it.run_top(stmts)
    if "title" not in it.song:
        raise SongError("no song line", file=file, suggestion='start with: song "Title" 120 4/4 Em')
    return _Compiler(it).compile()


def loads(text: str, file: str | None = None) -> Song:
    return from_raw(compile_raw(text, file), file=file)


def load(path: str) -> Song:
    with open(path, encoding="utf-8") as f:
        return loads(f.read(), path)


__all__ = ["load", "loads", "compile_raw", "overlay", "euclid", "rotate", "reverse", "EXT"]
