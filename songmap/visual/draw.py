"""One video frame of a Score: chord, letter names, a grand staff and a piano roll, sounding notes highlighted.

Layout (top to bottom):
    header      title, section, bar; the current chord as a pill (gold = golden, silver, bronze, ink = Western)
    letters     the sounding pitches as chips (vE4, ^G4 ...), coloured by 36-ET layer, popping on their onset
    staff       a grand staff in proportional notation: noteheads at their onset, a sustain line for their
                length, accidentals and ups/downs (^ v) before the head; the page turns every few bars, the
                played part is veiled, sounding notes glow and their sustain line fills as they ring
    roll        a scrolling piano roll (one row per step: sixth-steps in 36-ET) with a fixed playhead
Rendering is Pillow only. Each page's static staff is drawn once and reused, so a frame costs a copy plus
the few highlighted notes.
"""
from __future__ import annotations

import math
import os

from PIL import Image, ImageDraw, ImageFont

from .score import Score, ScoreNote, spell

THEMES = {
    "light": dict(bg=(247, 244, 238), panel=(255, 255, 255), ink=(31, 28, 23), muted=(120, 113, 102),
                  line=(178, 168, 150), grid=(240, 236, 228), black_row=(233, 228, 218), veil=0.55,
                  layers=[(70, 86, 104), (196, 132, 26), (40, 136, 166)], gold=(196, 138, 18), golden=(196, 138, 18),
                  silver=(120, 128, 140), bronze=(166, 104, 52), western=(52, 48, 44), cursor=(196, 138, 18)),
    "dark": dict(bg=(18, 17, 15), panel=(28, 26, 23), ink=(236, 231, 220), muted=(150, 143, 130),
                 line=(70, 64, 55), grid=(34, 32, 28), black_row=(40, 37, 32), veil=0.6,
                 layers=[(150, 172, 194), (232, 182, 70), (100, 196, 222)], gold=(227, 181, 74), golden=(227, 181, 74),
                 silver=(170, 178, 190), bronze=(206, 142, 88), western=(90, 84, 76), cursor=(227, 181, 74)),
}
WHITE = (255, 255, 255)

_FONT_DIRS = [os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"), "/usr/share/fonts/truetype/dejavu",
              "/usr/share/fonts/TTF", "/Library/Fonts", "/System/Library/Fonts/Supplemental"]
_TEXT = ["segoeui.ttf", "DejaVuSans.ttf", "Arial.ttf", "arial.ttf"]
_BOLD = ["seguisb.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"]
_BOLD_SYM = ["DejaVuSans-Bold.ttf", "seguisb.ttf", "arialbd.ttf"]          # has ♯ ♭ (note names)
_SYM = ["seguisym.ttf", "DejaVuSans.ttf"]
_font_cache: dict = {}


def _font(names, size):
    key = (tuple(names), int(size))
    if key not in _font_cache:
        f = None
        for d in _FONT_DIRS:
            for n in names:
                p = os.path.join(d, n)
                if os.path.exists(p):
                    f = ImageFont.truetype(p, int(size))
                    break
            if f:
                break
        _font_cache[key] = f or ImageFont.load_default(int(size))
    return _font_cache[key]


def _key(n) -> tuple:
    """Identity of a notehead: onset and pitch (sixth-steps), whatever part plays it."""
    return round(n.start, 3), int(round(n.pitch * 3))


def _mix(a, b, t):
    """t = 0 -> a, 1 -> b."""
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


class Renderer:
    def __init__(self, score: Score, size=(1280, 720), theme: str = "light", page_seconds: float = 6.0):
        self.sc = score
        self.W, self.H = size
        k = self.H / 720
        self.k = k
        self.th = THEMES[theme]
        th = self.th
        m = round(26 * k)
        y = m
        self.r_header = (m, y, self.W - m, y + round(62 * k)); y = self.r_header[3] + round(8 * k)
        self.r_letters = (m, y, self.W - m, y + round(84 * k)); y = self.r_letters[3] + round(10 * k)
        self.r_staff = (m, y, self.W - m, y + round(330 * k)); y = self.r_staff[3] + round(10 * k)
        self.r_roll = (m, y, self.W - m, self.H - m - round(8 * k))
        self.g = 12.5 * k                                   # staff space
        st = self.r_staff
        self.y_F5 = st[1] + 7.0 * self.g                    # treble top line
        self.y_E4 = self.y_F5 + 4 * self.g                  # treble bottom line
        self.y_A3 = self.y_E4 + 5 * self.g                  # bass top line
        self.x0 = st[0] + round(112 * k)                    # first notehead column (after clefs and accidentals)
        self.x1 = st[2] - round(18 * k)
        self.f_title = _font(_BOLD, 22 * k)
        self.f_small = _font(_TEXT, 15 * k)
        self.f_tiny = _font(_TEXT, 12 * k)
        self.f_chord = _font(_BOLD, 32 * k)
        self.f_chip = _font(_BOLD_SYM, 25 * k)
        self.f_label = _font(_BOLD, 14 * k)
        self.f_acc = _font(_SYM, 2.5 * self.g)
        self.f_clef = _font(_SYM, 6.6 * self.g)
        self.pages = self._paginate(page_seconds)
        self._base: dict[int, Image.Image] = {}
        lo = min((n.pitch for n in score.notes), default=48.0)
        hi = max((n.pitch for n in score.notes), default=72.0)
        self.step = 1 / 3 if score.edo == 36 else 1.0
        self.roll_lo, self.roll_hi = lo - 2 * self.step, hi + 2 * self.step
        self.window = (-2.0, 6.0)                           # piano roll: seconds before/after the playhead

    # ---------------------------------------------------------------- pages
    def _paginate(self, target: float):
        bars, end = self.sc.bars, self.sc.seconds
        if len(bars) < 2:
            n = max(1, math.ceil(end / target))
            return [(i * end / n, (i + 1) * end / n) for i in range(n)]
        dur = (bars[-1] - bars[0]) / (len(bars) - 1)
        per = max(1, int(round(target / max(dur, 1e-6))))
        pages = [(bars[i], bars[min(i + per, len(bars) - 1)]) for i in range(0, len(bars) - 1, per)]
        if pages[-1][1] < end - 1e-6:                       # the tail after the last bar joins the last page
            pages[-1] = (pages[-1][0], end)
        return pages

    def page_of(self, t: float) -> int:
        for i, (a, b) in enumerate(self.pages):
            if t < b:
                return i
        return len(self.pages) - 1

    def x_of(self, t: float, page: int) -> float:
        a, b = self.pages[page]
        return self.x0 + (t - a) / max(b - a, 1e-6) * (self.x1 - self.x0)

    # ---------------------------------------------------------------- staff geometry
    def y_of(self, d: int, treble: bool) -> float:
        return self.y_E4 - (d - 30) * self.g / 2 if treble else self.y_A3 - (d - 26) * self.g / 2

    @staticmethod
    def treble(n: ScoreNote) -> bool:
        return n.pitch >= 59.99

    def _ledgers(self, dr: ImageDraw.ImageDraw, x: float, d: int, treble: bool, color):
        hw = 0.95 * self.g
        lines = []
        if treble:
            lines = list(range(40, d + 1, 2)) + list(range(28, d - 1, -2))
        else:
            lines = list(range(28, d + 1, 2)) + list(range(16, d - 1, -2))
        for L in lines:
            y = self.y_of(L, treble)
            dr.line([(x - hw, y), (x + hw, y)], fill=color, width=max(1, round(1.4 * self.k)))

    def _head(self, dr, x, y, color, scale=1.0, outline=None):
        rx, ry, tilt = 0.68 * self.g * scale, 0.47 * self.g * scale, math.radians(-20)
        pts = [(x + rx * math.cos(a) * math.cos(tilt) - ry * math.sin(a) * math.sin(tilt),
                y + rx * math.cos(a) * math.sin(tilt) + ry * math.sin(a) * math.cos(tilt))
               for a in [i * 2 * math.pi / 20 for i in range(20)]]
        dr.polygon(pts, fill=color, outline=outline)

    def _accidental(self, dr, x, y, sp, color):
        """Accidental (♯ ♭) just left of x, and the up/down chevron left of that."""
        if sp.acc:
            glyph = "♯" if sp.acc > 0 else "♭"
            dr.text((x, y + (0.1 if sp.acc > 0 else -0.35) * self.g), glyph, font=self.f_acc, fill=color, anchor="rm")
            x -= 1.05 * self.g
        if sp.ud:
            w, h, s = 0.42 * self.g, 0.38 * self.g, -1 if sp.ud > 0 else 1
            cx = x - w
            dr.line([(cx - w, y - s * h), (cx, y + s * h), (cx + w, y - s * h)], fill=color,
                    width=max(2, round(2.0 * self.k)), joint="curve")

    def _layout_notes(self, notes):
        """[(note, staff_x_offset, accidental_column)] with seconds and unisons displaced."""
        out, seen = [], set()
        groups: dict = {}
        for n in notes:                                     # a unison doubled by two parts is one notehead
            if _key(n) in seen:
                continue
            seen.add(_key(n))
            groups.setdefault((round(n.start, 3), self.treble(n)), []).append(n)
        for (_, tr), grp in groups.items():
            grp = sorted(grp, key=lambda n: (spell(n.pitch).diatonic, n.pitch))
            prev_d, shifted, col = None, False, 0
            for n in grp:
                d = spell(n.pitch).diatonic
                shift = prev_d is not None and d - prev_d <= 1 and not shifted
                shifted = shift
                sp = spell(n.pitch)
                col = col + 1 if (sp.acc or sp.ud) and prev_d is not None and d - prev_d < 6 else 0
                out.append((n, 1.25 * self.g if shift else 0.0, col % 3))
                prev_d = d
        return out

    def _draw_note(self, dr, n, page, xoff, col, color, scale=1.0, outline=None, upto=None, tail_color=None):
        sp = spell(n.pitch)
        tr = self.treble(n)
        a, b = self.pages[page]
        xs = self.x_of(max(n.start, a), page) + xoff + 0.7 * self.g
        y = self.y_of(sp.diatonic, tr)
        xe = self.x_of(min(n.end if upto is None else upto, b), page)
        if tail_color and xe > xs:
            dr.line([(xs, y), (xe, y)], fill=tail_color, width=max(2, round(0.34 * self.g)))
        self._ledgers(dr, xs, sp.diatonic, tr, self.th["line"] if outline is None else self.th["ink"])
        self._head(dr, xs, y, color, scale, outline)
        if n.start >= a - 1e-6:
            self._accidental(dr, xs - 0.95 * self.g - col * 1.6 * self.g, y, sp, color)

    def _page_notes(self, page: int):
        a, b = self.pages[page]
        return [n for n in self.sc.between(a, b) if n.start < b - 1e-6]

    def _base_page(self, page: int) -> Image.Image:
        if page in self._base:
            return self._base[page]
        th, k, sc = self.th, self.k, self.sc
        im = Image.new("RGB", (self.W, self.H), th["bg"])
        dr = ImageDraw.Draw(im)
        for r in (self.r_header, self.r_letters, self.r_staff, self.r_roll):
            dr.rounded_rectangle(r, radius=round(16 * k), fill=th["panel"])
        lw = max(1, round(1.3 * k))
        for i in range(5):
            for y in (self.y_F5 + i * self.g, self.y_A3 + i * self.g):
                dr.line([(self.r_staff[0] + 14 * k, y), (self.x1 + 8 * k, y)], fill=th["line"], width=lw)
        xl = self.r_staff[0] + 14 * k
        dr.line([(xl, self.y_F5), (xl, self.y_A3 + 4 * self.g)], fill=th["line"], width=max(2, round(2.4 * k)))
        dr.text((xl + 6 * k, self.y_F5 + 3.0 * self.g), "\U0001D11E", font=self.f_clef, fill=th["muted"], anchor="lm")
        dr.text((xl + 6 * k, self.y_A3 + 1.05 * self.g), "\U0001D122", font=self.f_clef, fill=th["muted"], anchor="lm")
        a, b = self.pages[page]
        for i, t in enumerate(sc.bars):
            if a - 1e-6 <= t <= b + 1e-6 and t > a + 1e-6:
                x = self.x_of(t, page)
                dr.line([(x, self.y_F5), (x, self.y_A3 + 4 * self.g)], fill=th["line"], width=lw)
            if a - 1e-6 <= t < b - 1e-6:
                dr.text((self.x_of(t, page) + 4 * k, self.y_F5 - 6.2 * self.g), str(i + 1), font=self.f_tiny,
                        fill=th["muted"], anchor="lm")
        last_x = -1e9
        for c in sc.chords:
            if a - 1e-6 <= c.start < b - 1e-6:
                x = self.x_of(c.start, page) + 0.2 * self.g
                if x - last_x < 6 * k:
                    continue
                dr.text((x, self.y_F5 - 4.6 * self.g), c.symbol, font=self.f_label,
                        fill=th[c.kind] if c.kind != "western" else th["ink"], anchor="lm")
                last_x = x + dr.textlength(c.symbol, font=self.f_label)
        for n, xoff, col in self._layout_notes(self._page_notes(page)):
            lc = th["layers"][spell(n.pitch).layer]
            self._draw_note(dr, n, page, xoff, col, _mix(lc, th["panel"], 0.45),
                            tail_color=_mix(lc, th["panel"], 0.78))
        self._base[page] = im
        if len(self._base) > 4:                              # pages are visited in order
            self._base.pop(min(self._base))
        return im

    # ---------------------------------------------------------------- frame
    def frame(self, t: float) -> Image.Image:
        th, k, sc = self.th, self.k, self.sc
        page = self.page_of(t)
        im = self._base_page(page).copy()
        dr = ImageDraw.Draw(im)
        a, b = self.pages[page]
        cx = self.x_of(min(max(t, a), b), page)
        # veil over what has been played on this page
        if cx > self.x0:
            box = (int(self.r_staff[0] + 30 * k), int(self.r_staff[1] + 4 * k), int(cx), int(self.r_staff[3] - 4 * k))
            if box[2] > box[0]:
                region = im.crop(box)
                im.paste(Image.blend(region, Image.new("RGB", region.size, th["panel"]), th["veil"]), box[:2])
                dr = ImageDraw.Draw(im)
        now = sc.sounding(t)
        laid = {_key(n): (xoff, col) for n, xoff, col in self._layout_notes(self._page_notes(page))}
        drawn = set()
        for n in sorted(now, key=lambda n: (n.pitch, -n.end)):
            if _key(n) not in laid or _key(n) in drawn:
                continue
            drawn.add(_key(n))
            xoff, col = laid[_key(n)]
            lc = th["layers"][spell(n.pitch).layer]
            age = t - n.start
            pop = 1.0 + 0.45 * math.exp(-age / 0.11)
            sp = spell(n.pitch)
            xs = self.x_of(max(n.start, a), page) + xoff + 0.7 * self.g
            y = self.y_of(sp.diatonic, self.treble(n))
            r = 1.25 * self.g * pop
            dr.ellipse([xs - r, y - r, xs + r, y + r], fill=_mix(lc, th["panel"], 0.72))
            self._draw_note(dr, n, page, xoff, col, lc, scale=pop, outline=th["ink"], upto=t, tail_color=lc)
        dr.line([(cx, self.y_F5 - 3.6 * self.g), (cx, self.y_A3 + 6.0 * self.g)], fill=th["cursor"],
                width=max(2, round(2.2 * k)))
        self._header(dr, t)
        self._letters(dr, t, now)
        self._roll(dr, t)
        frac = min(1.0, t / max(sc.seconds, 1e-6))
        yb = self.H - round(12 * k)
        dr.line([(self.r_roll[0], yb), (self.r_roll[2], yb)], fill=th["grid"], width=max(2, round(3 * k)))
        dr.line([(self.r_roll[0], yb), (self.r_roll[0] + frac * (self.r_roll[2] - self.r_roll[0]), yb)],
                fill=th["gold"], width=max(2, round(3 * k)))
        return im

    def _header(self, dr, t):
        th, k, sc = self.th, self.k, self.sc
        x0, y0, x1, y1 = self.r_header
        dr.text((x0 + 18 * k, y0 + 20 * k), sc.title, font=self.f_title, fill=th["ink"], anchor="lm")
        sec = sc.section_at(t)
        bar = sc.bar_at(t) + 1
        info = f"{sec}  ·  bar {bar}" if sec else f"bar {bar}"
        dr.text((x0 + 18 * k, y0 + 45 * k), info, font=self.f_small, fill=th["muted"], anchor="lm")
        c = sc.chord_at(t)
        if c is None:
            return
        age = t - c.start
        pop = 1.0 + 0.12 * math.exp(-age / 0.12)
        f = _font(_BOLD, 32 * k * pop)
        w = dr.textlength(c.symbol, font=f) + 34 * k
        h = 46 * k * pop
        cy = (y0 + y1) / 2
        col = th[c.kind]
        dr.rounded_rectangle([x1 - 14 * k - w, cy - h / 2, x1 - 14 * k, cy + h / 2], radius=round(h / 2), fill=col)
        dr.text((x1 - 14 * k - w / 2, cy), c.symbol, font=f, fill=WHITE, anchor="mm")
        label = {"golden": "golden", "silver": "silver", "bronze": "bronze", "western": "chord"}[c.kind]
        dr.text((x1 - 24 * k - w, cy), label, font=self.f_small, fill=th["muted"], anchor="rm")

    def _letters(self, dr, t, now):
        th, k = self.th, self.k
        x0, y0, x1, y1 = self.r_letters
        seen, notes = set(), []
        for n in sorted(now, key=lambda n: n.pitch):
            key = round(n.pitch * 3)
            if key not in seen:
                seen.add(key)
                notes.append(n)
        cy = (y0 + y1) / 2
        if not notes:
            dr.text(((x0 + x1) / 2, cy), "·", font=self.f_chip, fill=th["muted"], anchor="mm")
            return
        f = self.f_chip if len(notes) <= 8 else _font(_BOLD_SYM, 25 * k * 8 / len(notes))
        pad, gap = 16 * k, 10 * k
        widths = [dr.textlength(spell(n.pitch).text, font=f) + 2 * pad for n in notes]
        total = sum(widths) + gap * (len(notes) - 1)
        x = (x0 + x1 - total) / 2
        for n, w in zip(notes, widths):
            sp = spell(n.pitch)
            pop = math.exp(-(t - n.start) / 0.12)
            h = (52 + 12 * pop) * k
            col = _mix(th["layers"][sp.layer], WHITE, 0.25 * pop)
            dr.rounded_rectangle([x, cy - h / 2, x + w, cy + h / 2], radius=round(14 * k), fill=col)
            dr.text((x + w / 2, cy), sp.text, font=f, fill=WHITE, anchor="mm")
            x += w + gap

    def _roll(self, dr, t):
        th, k, sc = self.th, self.k, self.sc
        x0, y0, x1, y1 = self.r_roll
        lx0 = x0 + 52 * k
        span = self.window[1] - self.window[0]
        xo = lambda s: lx0 + (s - (t + self.window[0])) / span * (x1 - 10 * k - lx0)  # noqa: E731
        rows = int(round((self.roll_hi - self.roll_lo) / self.step)) + 1
        rh = (y1 - y0 - 16 * k) / rows
        yo = lambda p: y0 + 8 * k + (self.roll_hi - p) / self.step * rh  # noqa: E731
        for i in range(rows):
            p = self.roll_hi - i * self.step
            st = int(round(p * 3))
            if st % 3 == 0 and (st // 3) % 12 in (1, 3, 6, 8, 10):
                dr.rectangle([lx0, yo(p), x1 - 10 * k, yo(p) + rh], fill=th["black_row"])
            if st % 3 == 0 and (st // 3) % 12 == 0:
                dr.line([(lx0, yo(p) + rh), (x1 - 10 * k, yo(p) + rh)], fill=th["line"], width=1)
                dr.text((lx0 - 6 * k, yo(p) + rh / 2), spell(p).text, font=self.f_tiny, fill=th["muted"], anchor="rm")
        for n in sc.between(t + self.window[0], t + self.window[1]):
            lc = th["layers"][spell(n.pitch).layer]
            on = n.start <= t < n.end
            xa, xb = max(xo(n.start), lx0), min(xo(n.end), x1 - 10 * k)
            if xb <= xa:
                continue
            ya = yo(n.pitch)
            hh = max(rh, 6 * k)
            dr.rounded_rectangle([xa, ya - (hh - rh) / 2, xb, ya + rh + (hh - rh) / 2], radius=round(min(hh / 2, 4 * k)),
                                 fill=lc if on else _mix(lc, th["panel"], 0.5 if n.start > t else 0.72),
                                 outline=th["ink"] if on else None)
        px = xo(t)
        dr.line([(px, y0 + 4 * k), (px, y1 - 4 * k)], fill=th["cursor"], width=max(2, round(2.2 * k)))
