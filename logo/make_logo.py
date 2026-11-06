"""Draw the Dactyloscopy logo: the fingerprint mark plus the wordmark as outlines.

The wordmark is set in Iowan Old Style Roman (as on the page) and converted to SVG paths,
so the logo renders the same everywhere. Needs macOS (for the font) and fontTools:
  python3 -m venv /tmp/logo-venv && /tmp/logo-venv/bin/pip install fonttools
  /tmp/logo-venv/bin/python logo/make_logo.py
Writes logo/dactyloscopy-logo.svg (dark text, for light backgrounds) and
logo/dactyloscopy-logo-dark.svg (light text, for dark backgrounds), and
logo/dactyloscopy-card.svg: the logo centered on white at 1200x600, for project cards that
crop with object-fit: cover (render to PNG with headless Chrome at 1200x600).
"""
import math
import os

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTCollection

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "/System/Library/Fonts/Supplemental/Iowan Old Style.ttc"
WORD = "Dactyloscopy"

# Palettes: the page's colors for light backgrounds; brighter ink and a muted outer
# ridge for dark backgrounds, so red and green stay the strongest marks.
LIGHT = {"text": "#1A2233", "red": "#B3261E", "green": "#1E7A46", "ridge": "#CDD3DE"}
DARK = {"text": "#F3F5F8", "red": "#E0473C", "green": "#34A867", "ridge": "#4B566B"}

# Mark: the page's ridge construction with fewer, slightly heavier ridges.
RIDGE_PATTERN = ["green", "red", "green", "green", "red", "green", "red", "ridge", "ridge"]
STROKE = 3.0
CAP_HEIGHT = 46.0          # wordmark cap height, in logo units
GAP = 24.0                 # space between mark and wordmark


def mark_paths(cx, cy, palette):
    out = []
    for i, role in enumerate(RIDGE_PATTERN):
        color = palette[role]
        rx = 3.6 + i * 4.7
        ry = rx * 1.22
        tilt = math.radians(-10 + i * 1.2)
        gap_at = math.radians((i * 137) % 360)
        gap = 0.6 + (i % 3) * 0.14
        a0, a1 = gap_at + gap / 2, gap_at + 2 * math.pi - gap / 2

        def pt(a):
            x, y = rx * math.cos(a), ry * math.sin(a)
            return cx + x * math.cos(tilt) - y * math.sin(tilt), cy + x * math.sin(tilt) + y * math.cos(tilt)

        (x0, y0), (x1, y1) = pt(a0), pt(a1)
        out.append(f'<path d="M{x0:.2f} {y0:.2f}A{rx:.2f} {ry:.2f} {math.degrees(tilt):.2f} 1 1 {x1:.2f} {y1:.2f}" stroke="{color}"/>')
    outer_rx = 3.6 + (len(RIDGE_PATTERN) - 1) * 4.7
    return out, outer_rx, outer_rx * 1.22


def kerning(font):
    """Pair kerning from the GPOS 'kern' feature (PairPos formats 1 and 2)."""
    gpos = font["GPOS"].table
    lookups = set()
    for fr in gpos.FeatureList.FeatureRecord:
        if fr.FeatureTag == "kern":
            lookups.update(fr.Feature.LookupListIndex)
    subtables = []
    for li in sorted(lookups):
        lookup = gpos.LookupList.Lookup[li]
        for st in lookup.SubTable:
            if lookup.LookupType == 9:          # extension
                st = st.ExtSubTable
            if getattr(st, "LookupType", 2) == 2 or st.__class__.__name__ == "PairPos":
                subtables.append(st)

    def value(left, right):
        for st in subtables:
            cov = st.Coverage.glyphs
            if left not in cov:
                continue
            if st.Format == 1:
                for pvr in st.PairSet[cov.index(left)].PairValueRecord:
                    if pvr.SecondGlyph == right and pvr.Value1 is not None:
                        return getattr(pvr.Value1, "XAdvance", 0) or 0
            elif st.Format == 2:
                c1 = st.ClassDef1.classDefs.get(left, 0)
                c2 = st.ClassDef2.classDefs.get(right, 0)
                rec = st.Class1Record[c1].Class2Record[c2]
                if rec.Value1 is not None:
                    v = getattr(rec.Value1, "XAdvance", 0) or 0
                    if v:
                        return v
        return 0

    return value


def wordmark(font):
    """Glyph paths for WORD, laid out with advances and kerning, in font units."""
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    kern = kerning(font)
    names = [cmap[ord(ch)] for ch in WORD]
    x, items = 0, []
    bounds = [math.inf, math.inf, -math.inf, -math.inf]
    for i, name in enumerate(names):
        pen = SVGPathPen(glyphs)
        glyphs[name].draw(pen)
        bp = BoundsPen(glyphs)
        glyphs[name].draw(bp)
        if bp.bounds:
            xmin, ymin, xmax, ymax = bp.bounds
            bounds = [min(bounds[0], x + xmin), min(bounds[1], ymin), max(bounds[2], x + xmax), max(bounds[3], ymax)]
        items.append((x, pen.getCommands()))
        x += hmtx[name][0]
        if i + 1 < len(names):
            x += kern(name, names[i + 1])
    return items, bounds


def build(palette):
    font = TTCollection(FONT).fonts[0]          # Iowan Old Style Roman
    # Cap height measured from "H" (this font's OS/2 table predates the cap-height field).
    glyphs = font.getGlyphSet()
    bp = BoundsPen(glyphs)
    glyphs[font.getBestCmap()[ord("H")]].draw(bp)
    scale = CAP_HEIGHT / bp.bounds[3]

    items, (bx0, by0, bx1, by1) = wordmark(font)
    paths, rx, ry = mark_paths(0, 0, palette)

    pad = STROKE
    mark_w, mark_h = 2 * rx + 2 * pad, 2 * ry + 2 * pad
    text_top = by1 * scale                       # ascender above baseline (ink extent)
    text_bottom = -by0 * scale                   # descender below baseline
    # Center the cap height on the mark's center.
    mark_cy = max(mark_h / 2, text_top - CAP_HEIGHT / 2)
    baseline = mark_cy + CAP_HEIGHT / 2
    height = max(mark_cy + mark_h / 2, baseline + text_bottom) + 2
    top = min(0, baseline - text_top) - 2
    text_x = mark_w + GAP - bx0 * scale
    width = text_x + bx1 * scale + 2

    mark = (f'<g transform="translate({mark_w / 2:.2f} {mark_cy:.2f})" fill="none" '
            f'stroke-width="{STROKE}" stroke-linecap="round">' + "".join(paths) + "</g>")
    glyphs = "".join(
        f'<path transform="translate({text_x + gx * scale:.2f} {baseline:.2f}) scale({scale:.5f} {-scale:.5f})" d="{d}"/>'
        for gx, d in items if d
    )
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 {top:.2f} {width:.2f} {height - top:.2f}" '
            f'role="img" aria-label="Dactyloscopy">'
            f'<title>Dactyloscopy</title>{mark}<g fill="{palette['text']}">{glyphs}</g></svg>\n')


def build_card(width=1200, height=600, logo_share=0.62):
    """Logo centered on white, for image boxes that crop with object-fit: cover.

    btcpp.dev project cards show images at roughly 2.7:1 (grid) or squarer (winner card),
    so the logo stays inside the middle ~62% of the width and well inside the height.
    """
    logo = build(LIGHT)
    vb = logo.split('viewBox="', 1)[1].split('"', 1)[0]
    _, _, vw, vh = (float(n) for n in vb.split())
    w = width * logo_share
    h = w * vh / vw
    x, y = (width - w) / 2, (height - h) / 2
    inner = logo.split(">", 1)[1].rsplit("</svg>", 1)[0]      # drop the outer <svg ...> wrapper
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
            f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>'
            f'<svg x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" viewBox="{vb}">{inner}</svg></svg>\n')


if __name__ == "__main__":
    card = os.path.join(HERE, "dactyloscopy-card.svg")
    open(card, "w").write(build_card())
    print("wrote", card)
    for name, palette in (("dactyloscopy-logo.svg", LIGHT), ("dactyloscopy-logo-dark.svg", DARK)):
        path = os.path.join(HERE, name)
        open(path, "w").write(build(palette))
        print("wrote", path)
