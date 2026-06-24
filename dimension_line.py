#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dimension line for Inkscape 1.3+

Select exactly TWO objects and run. A dimension line is drawn between two
points derived from the selection, with witness lines, arrowheads and a
distance label. The label can be replaced by a variable placeholder
(e.g. {B}, L1) while still using the real distance for placement.

Points are taken either from:
  - ends    : the first node of each selected path (snap two short marker
              strokes where you want to measure)
  - centers : the bounding-box center of each object

Companion to wall_insulation.py (same Architecture submenu / conventions).

Author: generated for Markus
"""

import math
import inkex
from inkex import PathElement, TextElement, Tspan, Path


def _first_node(elem):
    """First on-curve point of a path, in document user units, or None."""
    try:
        csp = elem.path.transform(elem.composed_transform()).to_superpath()
    except AttributeError:
        return None
    for sub in csp:
        if sub:
            return (sub[0][1][0], sub[0][1][1])
    return None


def _center(elem):
    """Bounding-box center in document user units, or None."""
    bb = elem.bounding_box()
    if bb is None:
        return None
    return (bb.center_x, bb.center_y)


class DimensionLine(inkex.EffectExtension):

    def add_arguments(self, pars):
        pars.add_argument("--tab")
        pars.add_argument("--from", dest="frm", default="ends")
        pars.add_argument("--unit", default="mm")
        pars.add_argument("--precision", type=int, default=0)
        pars.add_argument("--suffix", type=inkex.Boolean, default=False)
        pars.add_argument("--offset", type=float, default=20.0)
        pars.add_argument("--ext", type=float, default=5.0)
        pars.add_argument("--arrow", type=float, default=8.0)
        pars.add_argument("--fontsize", type=float, default=10.0)
        pars.add_argument("--stroke_width", type=float, default=0.5)
        pars.add_argument("--stroke_color", type=str, default="#000000")
        pars.add_argument("--usevar", type=inkex.Boolean, default=False)
        pars.add_argument("--varname", default="{B}")

    def _color_css(self):
        """Accept either '#rrggbb' or an Inkscape RGBA integer string."""
        c = self.options.stroke_color
        if isinstance(c, str) and c.startswith("#"):
            return c
        try:
            rgba = int(c)
            r = (rgba >> 24) & 0xFF
            g = (rgba >> 16) & 0xFF
            b = (rgba >> 8) & 0xFF
            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, TypeError):
            return "#000000"

    def effect(self):
        sel = list(self.svg.selection)
        if len(sel) != 2:
            inkex.errormsg("Select exactly two objects to dimension between.")
            return

        if self.options.frm == "centers":
            p1, p2 = _center(sel[0]), _center(sel[1])
        else:
            p1, p2 = _first_node(sel[0]), _first_node(sel[1])
            if p1 is None or p2 is None:
                inkex.errormsg(
                    "Endpoint mode needs two paths. Use 'Bounding-box "
                    "centers' for non-path objects, or select two paths.")
                return

        if p1 is None or p2 is None:
            inkex.errormsg("Could not read a point from one of the objects.")
            return

        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length < 1e-9:
            inkex.errormsg("The two points coincide; nothing to dimension.")
            return

        ux, uy = dx / length, dy / length          # along
        nx, ny = -uy, ux                            # perpendicular (normal)
        off = self.options.offset
        ext = self.options.ext
        arrow = self.options.arrow

        # dimension line endpoints (offset parallel to the measured span)
        a1 = (p1[0] + nx * off, p1[1] + ny * off)
        a2 = (p2[0] + nx * off, p2[1] + ny * off)

        cmds = []

        # witness lines from each point out just past the dimension line
        if abs(off) > 1e-9:
            w1 = (p1[0] + nx * (off + math.copysign(ext, off)),
                  p1[1] + ny * (off + math.copysign(ext, off)))
            w2 = (p2[0] + nx * (off + math.copysign(ext, off)),
                  p2[1] + ny * (off + math.copysign(ext, off)))
            cmds += [["M", p1[0], p1[1]], ["L", w1[0], w1[1]]]
            cmds += [["M", p2[0], p2[1]], ["L", w2[0], w2[1]]]

        # main dimension line
        cmds += [["M", a1[0], a1[1]], ["L", a2[0], a2[1]]]

        line_node = PathElement()
        line_node.path = Path(self._fmt(cmds))
        line_node.style = {
            "fill": "none",
            "stroke": self._color_css(),
            "stroke-width": str(self.options.stroke_width),
            "stroke-linejoin": "round",
            "stroke-linecap": "round",
        }
        line_node.label = "dimension"

        parent = sel[0].getparent()
        parent.add(line_node)

        # arrowheads (filled triangles), apex outward at each end
        if arrow > 1e-9:
            for tip, ddir in ((a1, (-ux, -uy)), (a2, (ux, uy))):
                head = PathElement()
                head.path = Path(self._arrow(tip, ddir, arrow))
                head.style = {"fill": self._color_css(), "stroke": "none"}
                head.label = "dimension-arrow"
                parent.add(head)

        # label
        parent.add(self._label(a1, a2, length, ux, uy))

    def _arrow(self, tip, direction, size):
        ux, uy = direction
        px, py = -uy, ux
        bx, by = tip[0] - ux * size, tip[1] - uy * size
        b1 = (bx + px * size * 0.35, by + py * size * 0.35)
        b2 = (bx - px * size * 0.35, by - py * size * 0.35)
        cmds = [["M", tip[0], tip[1]], ["L", b1[0], b1[1]],
                ["L", b2[0], b2[1]], ["Z"]]
        return self._fmt(cmds)

    def _value_text(self, length_px):
        if self.options.usevar:
            return self.options.varname
        val = self.svg.uutounit(length_px, self.options.unit)
        txt = "{:.{p}f}".format(val, p=self.options.precision)
        if self.options.suffix:
            txt += " " + self.options.unit
        return txt

    def _label(self, a1, a2, length_px, ux, uy):
        mx, my = (a1[0] + a2[0]) / 2.0, (a1[1] + a2[1]) / 2.0
        angle = math.degrees(math.atan2(uy, ux))
        if angle > 90 or angle < -90:        # keep text upright
            angle += 180
        fs = self.options.fontsize
        nx, ny = -uy, ux                     # lift text just off the line
        tx, ty = mx + nx * (fs * 0.4), my + ny * (fs * 0.4)

        text = TextElement()
        text.set("x", "{:.3f}".format(tx))
        text.set("y", "{:.3f}".format(ty))
        text.set("transform",
                 "rotate({:.3f} {:.3f} {:.3f})".format(angle, tx, ty))
        text.style = {
            "font-size": "{:.2f}px".format(fs),
            "font-family": "sans-serif",
            "text-anchor": "middle",
            "fill": self._color_css(),
        }
        ts = Tspan()
        ts.text = self._value_text(length_px)
        text.append(ts)
        text.label = "dimension-text"
        return text

    def _fmt(self, cmds):
        parts = []
        for c in cmds:
            if c[0] == "Z":
                parts.append("Z")
            else:
                parts.append(c[0] + " " + " ".join(f"{v:.4f}" for v in c[1:]))
        return " ".join(parts)


if __name__ == "__main__":
    DimensionLine().run()
