#!/usr/bin/env python3
"""English academic figures: editable SVG + print PNG from one geometry.

Adapted from ../论文配图/render.py (Chinese originals). Same visual grammar:
white paper, navy BLUE, copper COPPER, gray, pale fills, hairlines,
serif titles + sans labels, curved arrows, rounded "field" blobs.
Canvas widened to 900 units (SCALE 3.2 -> 2880 px) for English labels.
Overlap/overflow checks emit warnings instead of raising.
"""
from functools import lru_cache
from math import hypot
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
W, SCALE, PRINT_CM = 900, 3.2, 14.5
PAPER, INK, GRAY = "#FFFFFF", "#1E2939", "#52606F"
BLUE, COPPER = "#344F98", "#925433"
PALE, SILVER, HAIR = "#E9EDF7", "#98A5BA", "#D1D8E3"
FAMILIES = {
    "sans": "Arial, Helvetica, sans-serif",
    "serif": "Georgia, 'Times New Roman', serif",
}
WARNINGS = []


@lru_cache(maxsize=None)
def font(size, bold, kind):
    faces = {
        "sans": [("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold
                  else "/System/Library/Fonts/Supplemental/Arial.ttf", 0),
                 ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 0)],
        "serif": [("/System/Library/Fonts/Supplemental/Georgia Bold.ttf" if bold
                   else "/System/Library/Fonts/Supplemental/Georgia.ttf", 0),
                  ("/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf" if bold
                   else "/System/Library/Fonts/Supplemental/Times New Roman.ttf", 0)],
    }
    for name, idx in faces[kind]:
        if Path(name).is_file():
            return ImageFont.truetype(name, round(size * SCALE), index=idx)
    raise RuntimeError("Install Arial / Georgia (macOS Supplemental fonts).")


def px(point):
    return tuple(round(v * SCALE) for v in point)


def coords(points):
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def bezier(start, c1, c2, end, steps=32):
    points = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        points.append(tuple(u**3*a + 3*u*u*t*b + 3*u*t*t*c + t**3*d
                            for a, b, c, d in zip(start, c1, c2, end)))
    return points


class Figure:
    def __init__(self, stem, name, description, height):
        self.stem, self.h = stem, height
        self.im = Image.new("RGB", (round(W*SCALE), round(height*SCALE)), PAPER)
        self.pen = ImageDraw.Draw(self.im)
        self.labels = []
        self.svg = ET.Element("svg", {
            "xmlns": "http://www.w3.org/2000/svg", "width": str(W), "height": str(height),
            "viewBox": f"0 0 {W} {height}", "role": "img", "aria-labelledby": "name desc",
        })
        ET.SubElement(self.svg, "title", id="name").text = name
        ET.SubElement(self.svg, "desc", id="desc").text = description
        ET.SubElement(self.svg, "rect", width=str(W), height=str(height), fill=PAPER)

    def text(self, x, y, value, size=18, *, bold=False, color=INK, kind="sans", center=False, limit):
        face = font(size, bold, kind)
        anchor = "ms" if center else "ls"
        box = tuple(v / SCALE for v in self.pen.textbbox(px((x, y)), value, font=face, anchor=anchor))
        l, t, r, b = box
        if r - l > limit or l < 2 or t < 2 or r > W - 2 or b > self.h - 2:
            WARNINGS.append(f"{self.stem}: OVERFLOW {value!r} box={tuple(round(v,1) for v in box)} limit={limit}")
        for label, (ll, tt, rr, bb) in self.labels:
            if min(r, rr) > max(l, ll) and min(b, bb) > max(t, tt):
                WARNINGS.append(f"{self.stem}: OVERLAP {value!r} / {label!r}")
        self.labels.append((value, box))
        self.pen.text(px((x, y)), value, font=face, fill=color, anchor=anchor)
        ET.SubElement(self.svg, "text", {
            "x": str(x), "y": str(y), "font-family": FAMILIES[kind], "font-size": str(size),
            "font-weight": "700" if bold else "400", "text-anchor": "middle" if center else "start",
            "fill": color,
        }).text = value

    def path(self, d, points, color=None, width=1.5, fill=None, dash=None):
        attr = {"d": d, "fill": fill or "none", "stroke": color or "none", "stroke-width": str(width),
                "stroke-linejoin": "round", "stroke-linecap": "round" if not dash else "butt"}
        if dash:
            attr["stroke-dasharray"] = " ".join(map(str, dash))
        ET.SubElement(self.svg, "path", attr)
        if fill:
            self.pen.polygon([px(p) for p in points], fill=fill)
        if not color:
            return
        lw = max(1, round(width * SCALE))
        if not dash:
            self.pen.line([px(p) for p in points], fill=color, width=lw, joint="curve")
            return
        phase, left = 0, dash[0]
        for (x, y), (u, v) in zip(points, points[1:]):
            length = hypot(u - x, v - y)
            pos = 0
            while pos < length - 1e-8:
                step = min(left, length - pos)
                if phase == 0:
                    self.pen.line([px((x + (u-x)*s/length, y + (v-y)*s/length)) for s in (pos, pos+step)],
                                  fill=color, width=lw)
                pos += step
                left -= step
                if left < 1e-8:
                    phase = 1 - phase
                    left = dash[phase]

    def line(self, points, color=GRAY, width=1.5, dash=None):
        self.path("M " + coords(points), points, color, width, dash=dash)

    def curve(self, p, a, b, q, color=BLUE, width=2, dash=None, arrow=False):
        self.path("M " + coords([p]) + " C " + coords([a, b, q]), bezier(p, a, b, q), color, width, dash=dash)
        if arrow:
            self.head(b, q, color)

    def head(self, p, q, color):
        dx, dy = q[0] - p[0], q[1] - p[1]
        span = hypot(dx, dy)
        dx, dy = dx / span, dy / span
        a = (q[0] - 9*dx + 3.7*dy, q[1] - 9*dy - 3.7*dx)
        b = (q[0] - 9*dx - 3.7*dy, q[1] - 9*dy + 3.7*dx)
        self.polygon([q, a, b], color)

    def arrow(self, p, q, color=BLUE, width=1.8):
        self.line([p, q], color, width)
        self.head(p, q, color)

    def polygon(self, points, fill, edge=None, width=1.5):
        self.path("M " + coords(points) + " Z", points + [points[0]], edge, width, fill)

    def dot(self, x, y, r, fill, edge=None, width=1.6):
        ET.SubElement(self.svg, "circle", {"cx": str(x), "cy": str(y), "r": str(r), "fill": fill or "none",
                                           "stroke": edge or "none", "stroke-width": str(width)})
        self.pen.ellipse(px((x-r, y-r, x+r, y+r)), fill=fill, outline=edge, width=max(1, round(width*SCALE)))

    def field(self, cx, cy, rx, ry, *, miniature=False, recipient=False):
        shape = [(-.97, -.05), (-.76, -.66), (-.24, -.88), (.31, -.93), (.81, -.62), (.97, -.07),
                 (.84, .43), (.44, .85), (-.09, .92), (-.62, .71), (-.9, .34)]
        for k, shade, edge in [(1, "#F4F6FB", "#AEBBD7"), (.84, "#EBEFF8", "#B5C2DE"), (.68, "#E4EAF6", "#BAC7E2")]:
            pts = [(cx + x*rx*k, cy + y*ry*k) for x, y in shape]
            d, samples = "M " + coords(pts[:1]), [pts[0]]
            for i, p in enumerate(pts):
                prev, q, after = pts[i-1], pts[(i+1) % len(pts)], pts[(i+2) % len(pts)]
                a = tuple(x + (y-z)/6 for x, y, z in zip(p, q, prev))
                b = tuple(x - (y-z)/6 for x, y, z in zip(q, after, p))
                d += " C " + coords([a, b, q]); samples.extend(bezier(p, a, b, q, 12)[1:])
            self.path(d + " Z", samples, edge, 1, shade)
        if miniature:
            if recipient:
                a, b, c, d = (cx-.34*rx, cy-.13*ry), (cx, cy+.15*ry), (cx+.30*rx, cy-.26*ry), (cx+.39*rx, cy+.22*ry)
                self.line([a, b, d], GRAY, 1.2)
                self.line([b, c], BLUE, 2)
                for pos in (a, d):
                    self.dot(*pos, 2.6, PAPER, GRAY, 1.2)
                for pos in (b, c):
                    self.dot(*pos, 2.8, BLUE)
            else:
                a, b, c = (cx-.36*rx, cy+.12*ry), (cx+.04*rx, cy-.25*ry), (cx+.39*rx, cy+.13*ry)
                self.line([a, b, c], BLUE, 1.5)
                for pos in (a, b, c):
                    self.dot(*pos, 2.8, BLUE)

    def save(self):
        ET.indent(self.svg)
        ET.ElementTree(self.svg).write(OUT / (self.stem + ".svg"), encoding="utf-8", xml_declaration=True)
        dpi = W * SCALE * 2.54 / PRINT_CM
        self.im.save(OUT / (self.stem + ".png"), dpi=(dpi, dpi), optimize=True)
        print(f"{self.stem}: {self.im.width} x {self.im.height}")


def mechanism():
    f = Figure("01_mechanism", "Action feedback and cross-agent acquisition in meta-space",
               "Current cues enter the meta-space; execution outcomes feed back into memory. "
               "An articulated artifact is not a copy of competence: the recipient rebuilds links from own experience.", 370)
    f.text(450, 40, "Action feedback and cross-agent acquisition in meta-space",
           24, kind="serif", bold=True, center=True, limit=860)

    f.text(100, 78, "Current cues", 21, kind="serif", bold=True, center=True, limit=180)
    for y in (105, 130, 155):
        f.curve((60, y), (91, y), (108, 130), (139, 130), SILVER, 1.5)
        f.dot(58, y, 4.3, PAPER, BLUE)
    f.arrow((139, 130), (275, 130), BLUE, 1.8)
    f.text(100, 191, "Observation & task", 16, color=GRAY, center=True, limit=180)

    f.field(424, 129, 141, 65)
    f.text(424, 123, "Meta-space", 29, kind="serif", bold=True, center=True, limit=200)
    f.text(424, 153, "M = (G, F)", 18, color=BLUE, center=True, limit=160)
    f.text(410, 214, "G: associative links   F: functional organization", 16, color=GRAY, center=True, limit=400)

    f.text(774, 78, "Action selection", 21, kind="serif", bold=True, center=True, limit=210)
    f.line([(568, 130), (661, 130)], BLUE, 1.9)
    f.curve((661, 130), (701, 130), (711, 105), (775, 105), SILVER, 1.6, dash=(5, 4))
    f.curve((661, 130), (701, 130), (716, 153), (775, 153), BLUE, 2.5)
    f.dot(661, 130, 3.8, BLUE)
    f.dot(780, 105, 5, PAPER, SILVER)
    f.dot(780, 153, 5.7, BLUE)
    f.text(797, 112, "Candidate", 16, color=GRAY, limit=95)
    f.text(797, 160, "Execute", 17, bold=True, limit=95)
    f.curve((780, 164), (778, 214), (611, 235), (512, 183), COPPER, 1.75, arrow=True)
    f.text(688, 199, "Outcome feedback", 16, color=COPPER, center=True, limit=160)

    f.line([(30, 240), (870, 240)], HAIR, 1)
    f.field(115, 295, 52, 29, miniature=True)
    f.field(785, 295, 52, 29, miniature=True, recipient=True)
    f.polygon([(431, 273), (455, 273), (470, 288), (470, 316), (431, 316)], "#F4F6FB", BLUE, 1.5)
    f.line([(455, 273), (455, 288), (470, 288)], BLUE, 1.3)
    for i, length in enumerate((21, 25, 16)):
        f.line([(438, 296 + 7*i), (438 + length, 296 + 7*i)], BLUE, 1.2)
    f.arrow((180, 295), (415, 295), GRAY, 1.5)
    f.arrow((485, 295), (720, 295), GRAY, 1.5)
    f.text(297, 282, "Articulate to listener's need", 16, color=GRAY, center=True, limit=230)
    f.text(602, 282, "Acquire via own experience", 16, color=GRAY, center=True, limit=230)
    for x, label in ((115, "Agent memory"), (450, "Artifact K"), (785, "Recipient memory")):
        f.text(x, 347, label, 18, bold=True, center=True, limit=210)
    f.save()


def association():
    f = Figure("02_association", "Associative activation and the disclosure boundary of information combinations",
               "Route A activates the slower rush-hour expectation; the off-peak link stays stored. "
               "An organizational rule can place a boundary on an otherwise public date-location combination.", 360)
    f.text(450, 38, "Associative activation and the disclosure boundary of information combinations",
           20, kind="serif", bold=True, center=True, limit=870)

    f.text(98, 120, "Route A", 25, kind="serif", bold=True, center=True, limit=140)
    f.text(98, 183, "Route cue", 16, color=GRAY, center=True, limit=150)
    active = ((106, 145), (226, 145), (224, 103), (372, 103))
    f.curve(*active, PALE, 8)
    f.curve(*active, BLUE, 2.5)
    f.curve((106, 145), (226, 145), (224, 188), (372, 188), SILVER, 1.8, dash=(6, 4))
    f.line([(372, 103), (639, 103)], BLUE, 2.5)
    f.line([(372, 188), (639, 188)], SILVER, 1.8, dash=(6, 4))
    f.dot(99, 145, 8, BLUE); f.dot(372, 103, 6, BLUE); f.dot(372, 188, 6, PAPER, SILVER, 1.8)
    f.dot(643, 103, 4.5, BLUE); f.dot(643, 188, 4.5, PAPER, SILVER)
    f.text(372, 86, "Rush hour", 20, bold=True, center=True, limit=140)
    f.text(372, 171, "Off-peak", 19, color=GRAY, center=True, limit=140)
    f.text(520, 89, "Currently active", 16, color=BLUE, center=True, limit=160)
    f.text(520, 174, "Stored, inactive", 16, color=GRAY, center=True, limit=160)
    for y, val, hue in ((103, "22", BLUE), (188, "10", GRAY)):
        f.text(672, y + 5, "~", 16, color=hue, limit=24)
        f.text(695, y + 11, val, 36, kind="serif", bold=True, color=hue, limit=60)
        f.text(748, y + 6, "min", 17, color=hue, limit=60)

    f.line([(30, 225), (870, 225)], HAIR, 1)
    f.text(34, 258, "Organizational special case", 17, bold=True, color=COPPER, limit=280)
    for y, term in ((290, "Date"), (326, "Location")):
        f.dot(45, y - 5, 4, PAPER, COPPER, 1.5)
        f.text(62, y, term, 18, bold=True, limit=100)
        f.text(158, y, "Public", 16, color=GRAY, limit=80)
    f.curve((215, 284), (260, 284), (250, 305), (290, 305), COPPER, 1.7)
    f.curve((215, 320), (260, 320), (250, 305), (290, 305), COPPER, 1.7)
    f.arrow((290, 305), (360, 305), COPPER, 1.7)
    f.text(385, 299, "Full schedule of an unpublished event", 21, kind="serif", bold=True, limit=490)
    f.text(385, 330, "If an applicable rule restricts this combination, it is internal-only.",
           15, color=GRAY, limit=505)
    f.save()


def learning():
    f = Figure("03_learning_dynamics", "Three kinds of feedback-driven memory update",
               "Repeated experience sediments stable links; calibration revises an estimate within a situation; "
               "restructuring redraws situation boundaries. Cross-event persistence distinguishes durable change.", 404)
    f.text(450, 40, "Three kinds of feedback-driven memory update",
           24, kind="serif", bold=True, center=True, limit=860)
    for x, title in ((145, "Sedimentation"), (450, "Calibration"), (756, "Restructuring")):
        f.text(x, 85, title, 24, kind="serif", bold=True, center=True, limit=240)
    for x in (295, 602):
        f.line([(x, 62), (x, 225)], HAIR, 1)

    for y in (117, 143, 170):
        f.curve((55, y), (98, y), (110, 143), (160, 143), SILVER if y != 143 else BLUE, 1.6)
        f.dot(52, y, 4.2, PAPER, BLUE)
    f.line([(158, 143), (244, 143)], PALE, 9)
    f.line([(158, 143), (244, 143)], BLUE, 3.1)
    f.dot(244, 143, 6, BLUE)
    f.text(148, 210, "Repeated experience leaves stable links", 15, center=True, limit=288)

    f.line([(350, 154), (550, 154)], HAIR, 1.6)
    for x in (356, 386, 416, 446, 476, 506, 536):
        f.line([(x, 150), (x, 158)], SILVER, 1)
    f.curve((387, 145), (406, 109), (482, 109), (506, 144), COPPER, 1.9, arrow=True)
    f.dot(386, 154, 5.5, PAPER, GRAY, 1.7); f.dot(506, 154, 6, BLUE)
    f.text(450, 210, "Keep situation, revise estimate", 15, center=True, limit=288)

    f.line([(640, 143), (676, 143)], BLUE, 2)
    f.dot(638, 143, 5.5, BLUE)
    for y, text in ((119, "Rush hour"), (167, "Off-peak")):
        f.curve((676, 143), (712, 143), (716, y), (761, y), BLUE, 1.9)
        f.dot(762, y, 4.8, PAPER, BLUE, 1.8)
        f.text(778, y + 6, text, 16, color=GRAY, limit=112)
    f.text(750, 210, "Redraw situation boundaries by cue", 15, center=True, limit=290)

    f.line([(30, 240), (870, 240)], HAIR, 1)
    f.text(34, 274, "Cross-event test", 19, bold=True, limit=220)
    f.text(315, 273, "This task", 16, color=GRAY, center=True, limit=140)
    f.text(491, 273, "Prompt removed", 16, color=GRAY, center=True, limit=160)
    f.text(756, 273, "New situation", 16, color=GRAY, center=True, limit=160)
    f.line([(491, 285), (491, 361)], SILVER, 1.2, dash=(4, 4))
    f.text(35, 312, "Current prompt", 17, color=GRAY, limit=190)
    f.dot(310, 305, 4.2, GRAY)
    f.line([(315, 305), (480, 305)], SILVER, 1.8)
    f.line([(480, 299), (480, 311)], GRAY, 1.5)
    f.text(756, 312, "Prompt effect fades", 17, color=GRAY, center=True, limit=220)
    f.text(35, 353, "Persistent links", 18, bold=True, color=BLUE, limit=190)
    f.dot(310, 346, 5, BLUE)
    f.arrow((315, 346), (630, 346), BLUE, 2.2)
    f.text(760, 353, "Still usable independently", 18, bold=True, color=BLUE, center=True, limit=260)
    f.text(34, 388, "Authorization or norm changes are a different kind of change, attributed separately.",
           15, color=GRAY, limit=840)
    f.save()


def icon(f, kind, x, y):
    if kind == "route":
        f.polygon([(x-10, y+9), (x+13, y-11), (x+5, y+13), (x+1, y+1)], PAPER, BLUE, 1.7)
        f.line([(x+1, y+1), (x+12, y-10)], BLUE, 1.4)
    elif kind == "time":
        f.dot(x, y, 12, PAPER, BLUE, 1.7)
        f.line([(x, y-7), (x, y), (x+6, y+3)], BLUE, 1.7)
    else:
        f.curve((x-10, y+4), (x-14, y-13), (x+11, y-16), (x+12, y), BLUE, 1.6)
        f.curve((x+12, y), (x+12, y+11), (x-1, y+15), (x-8, y+8), BLUE, 1.6)
        f.line([(x-11, y-3), (x-10, y+4), (x-3, y+2)], BLUE, 1.6)
        f.dot(x, y, 2.6, BLUE)


def articulation():
    f = Figure("04_articulation", "One trip memory, expressed for three communicative tasks",
               "Route A takes about 10 min off-peak and 22 min at rush hour; Route B about 14 min either way. "
               "Each expression selects content for the listener's current task.", 330)
    f.text(450, 40, "One trip memory, expressed for three communicative tasks",
           24, kind="serif", bold=True, center=True, limit=860)
    f.text(31, 82, "Estimated time", 18, bold=True, limit=150)
    f.text(172, 82, "min", 16, color=GRAY, limit=60)
    f.text(438, 82, "Listener & task", 18, bold=True, limit=220)
    f.line([(396, 62), (396, 310)], HAIR, 1)
    x1, x2 = 98, 275
    for x in (x1, x2):
        f.line([(x, 108), (x, 242)], HAIR, 1)
    f.line([(x1, 223), (x2, 115)], BLUE, 2.7)
    f.line([(x1, 187), (x2, 187)], GRAY, 1.8, dash=(6, 4))
    for x, y in ((x1, 223), (x2, 115)):
        f.dot(x, y, 5.3, BLUE)
    for x in (x1, x2):
        f.polygon([(x, 181), (x+6, 187), (x, 193), (x-6, 187)], PAPER, GRAY, 1.7)
    for x, y, num, hue in ((59, 231, "10", BLUE), (312, 123, "22", BLUE), (59, 194, "14", GRAY), (312, 194, "14", GRAY)):
        f.text(x, y, num, 25, kind="serif", bold=True, color=hue, center=True, limit=55)
    f.text(x1, 265, "Off-peak", 17, center=True, limit=120)
    f.text(x2, 265, "Rush hour", 17, center=True, limit=120)
    f.line([(48, 296), (88, 296)], BLUE, 2.4); f.dot(68, 296, 4, BLUE)
    f.text(100, 302, "Route A", 16, color=GRAY, limit=90)
    f.line([(194, 296), (234, 296)], GRAY, 1.6, dash=(4, 3))
    f.polygon([(214, 291), (219, 296), (214, 301), (209, 296)], PAPER, GRAY, 1.5)
    f.text(246, 302, "Route B", 16, color=GRAY, limit=90)
    for y, kind, who, message in [
        (123, "route", "Driver · before departure", "Take B at rush hour; ~14 min."),
        (199, "time", "Pickup · same departure", "If B, arrives ~14 min after departure."),
        (275, "review", "Same driver · review", "Off-peak A is faster; check the time slot next time."),
    ]:
        icon(f, kind, 451, y + 2)
        f.text(489, y - 1, who, 16, bold=True, color=GRAY, limit=395)
        f.text(489, y + 25, message, 17, limit=400)
    f.save()


def overview():
    files = sorted(OUT.glob("0[1-4]_*.png"))
    if len(files) != 4:
        raise ValueError("Overview needs the four figures.")
    width, gap = 1440, 48
    tiles = []
    for file in files:
        with Image.open(file) as im:
            tiles.append(im.resize((width, round(im.height * width / im.width)), Image.Resampling.LANCZOS))
    h1, h2 = max(t.height for t in tiles[:2]), max(t.height for t in tiles[2:])
    sheet = Image.new("RGB", (2*width + 3*gap, h1 + h2 + 3*gap), PAPER)
    pen = ImageDraw.Draw(sheet)
    pen.line([(gap + width + gap//2, gap), (gap + width + gap//2, sheet.height - gap)], fill=HAIR)
    pen.line([(gap, h1 + gap + gap//2), (sheet.width - gap, h1 + gap + gap//2)], fill=HAIR)
    for i, tile in enumerate(tiles):
        rowh = h1 if i < 2 else h2
        sheet.paste(tile, (gap + i % 2 * (width + gap), (gap if i < 2 else 2*gap + h1) + (rowh - tile.height)//2))
    sheet.save(OUT / "overview.png", optimize=True)
    print(f"overview: {sheet.width} x {sheet.height}")


if __name__ == "__main__":
    for draw in (mechanism, association, learning, articulation):
        draw()
    overview()
    if WARNINGS:
        print("\n".join(WARNINGS))
    else:
        print("no layout warnings")