#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dimension line for Inkscape 1.3+

Two ways to create one:

  * Select ONE path / line (it may be a combined path or live inside a
    group). The dimension is drawn from its FIRST node to its LAST node
    — i.e. just draw a line between the two points you want to measure.
    The source line is then hidden; the dimension keeps a reference to
    it so it can be rebuilt.

  * Select exactly TWO objects. The two points are then derived per the
    "Take points from" option:
      - ends    : the first node of each selected path
      - centers : the bounding-box center of each object

The whole dimension (line + witness lines + arrowheads + label) is put
into ONE group tagged with custom `dimline:*` attributes that store the
source object id(s) and all the parameters — the same idea TexText uses
to make its objects re-editable.

Re-running the extension on an existing dimension group (assign it a
keyboard shortcut) re-reads the *current* geometry of the source and
redraws it, so after you move or edit the source line a single keypress
updates the dimension.

The distance label can be replaced by a variable placeholder (e.g. {B},
L1) while still using the real distance for placement.

Companion to wall_insulation.py (same Architecture submenu / conventions).

Author: generated for Markus
"""

import math
import inkex
from lxml import etree
from inkex import PathElement, TextElement, Tspan, Path, Group, Rectangle

# Custom namespace for the metadata we tag onto a dimension group, so the
# extension can recognise and rebuild its own objects (cf. TexText).
DIM_NS = "http://www.bemessung.at/namespaces/dimension_line"
inkex.NSS["dimline"] = DIM_NS
etree.register_namespace("dimline", DIM_NS)


def _ns(name):
    return inkex.addNS(name, "dimline")


def _superpath(elem):
    """Composed superpath of an element, or None if it has no path data."""
    try:
        return elem.path.transform(elem.composed_transform()).to_superpath()
    except AttributeError:
        return None


def _first_node(elem):
    """First on-curve point of a path, in document user units, or None."""
    csp = _superpath(elem)
    if csp is None:
        return None
    for sub in csp:
        if sub:
            return (sub[0][1][0], sub[0][1][1])
    return None


def _end_nodes(elem):
    """First and last on-curve points of a path (start -> end), or None.

    Works on a plain path, a combined path (multiple subpaths) and a group
    containing paths — the very first and very last on-curve nodes drawn
    are returned, in document user units.
    """
    sources = [elem]
    if not hasattr(elem, "path") or _superpath(elem) is None:
        # e.g. a group: gather any descendant paths
        try:
            sources = list(elem.iter())
        except AttributeError:
            sources = [elem]

    pts = []
    for node in sources:
        csp = _superpath(node)
        if not csp:
            continue
        for sub in csp:
            for seg in sub:
                pts.append((seg[1][0], seg[1][1]))

    if len(pts) < 2:
        return None
    return pts[0], pts[-1]


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
        pars.add_argument("--offset", type=float, default=5.0)
        pars.add_argument("--ext", type=float, default=1.5)
        pars.add_argument("--arrow", type=float, default=2.5)
        pars.add_argument("--fontsize", type=float, default=10.0)
        pars.add_argument("--stroke_width", type=float, default=0.25)
        pars.add_argument("--stroke_color", type=str, default="#000000")
        pars.add_argument("--notext", type=inkex.Boolean, default=False)
        pars.add_argument("--textpos", default="above")
        pars.add_argument("--usevar", type=inkex.Boolean, default=False)
        pars.add_argument("--varname", default="{B}")
        pars.add_argument("--hide_source", type=inkex.Boolean, default=True)
        pars.add_argument("--on_existing", default="refresh")

    # ---- units / colour helpers -----------------------------------------

    def _mm(self, value):
        """Convert a mm input to document user units."""
        return self.svg.unittouu("{}mm".format(value))

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

    # ---- parameter bundles ----------------------------------------------

    def _params_from_options(self):
        return {
            "off": self.options.offset,            # mm
            "ext": self.options.ext,               # mm
            "arrow": self.options.arrow,           # mm
            "sw": self.options.stroke_width,       # mm
            "fontsize": self.options.fontsize,     # px
            "color": self._color_css(),
            "unit": self.options.unit,
            "precision": self.options.precision,
            "suffix": self.options.suffix,
            "notext": self.options.notext,
            "textpos": self.options.textpos,
            "usevar": self.options.usevar,
            "varname": self.options.varname,
        }

    def _store_params(self, g, P):
        def s(name, val):
            g.set(_ns(name), str(val))
        s("offset", P["off"])
        s("ext", P["ext"])
        s("arrow", P["arrow"])
        s("stroke-width", P["sw"])
        s("fontsize", P["fontsize"])
        s("color", P["color"])
        s("unit", P["unit"])
        s("precision", P["precision"])
        s("suffix", "true" if P["suffix"] else "false")
        s("notext", "true" if P["notext"] else "false")
        s("textpos", P["textpos"])
        s("usevar", "true" if P["usevar"] else "false")
        s("varname", P["varname"])

    def _params_from_group(self, g):
        def a(name, default=""):
            v = g.get(_ns(name))
            return default if v is None else v
        return {
            "off": float(a("offset", "0")),
            "ext": float(a("ext", "0")),
            "arrow": float(a("arrow", "0")),
            "sw": float(a("stroke-width", "0.25")),
            "fontsize": float(a("fontsize", "10")),
            "color": a("color", "#000000"),
            "unit": a("unit", "mm"),
            "precision": int(a("precision", "0")),
            "suffix": a("suffix", "false") == "true",
            "notext": a("notext", "false") == "true",
            "textpos": a("textpos", "above"),
            "usevar": a("usevar", "false") == "true",
            "varname": a("varname", "{B}"),
        }

    # ---- finding our own groups -----------------------------------------

    def _as_dim_group(self, el):
        """Return the dimension group for el (el itself or an ancestor)."""
        node = el
        while node is not None:
            try:
                if node.get(_ns("role")) == "dimension":
                    return node
            except AttributeError:
                return None
            node = node.getparent()
        return None

    def _group_for_source(self, el):
        """If el is a tagged source line, return the group that uses it."""
        if el.get(_ns("is-source")) is None:
            return None
        sid = el.get("id")
        if not sid:
            return None
        for g in self.svg.iter():
            if g.get(_ns("role")) == "dimension":
                if sid in (g.get(_ns("source")) or "").split():
                    return g
        return None

    def _find_dim_group(self, sel):
        for el in sel:
            g = self._as_dim_group(el)
            if g is not None:
                return g
        for el in sel:
            g = self._group_for_source(el)
            if g is not None:
                return g
        return None

    # ---- main ------------------------------------------------------------

    def effect(self):
        sel = list(self.svg.selection)

        # Editing an existing dimension? -> update it from its source.
        dimg = self._find_dim_group(sel)
        if dimg is not None:
            self._update(dimg)
            return

        # Otherwise create a new dimension from the selection.
        if len(sel) == 1:
            ends = _end_nodes(sel[0])
            if ends is None:
                inkex.errormsg(
                    "Select a single line/path (with at least two nodes) to "
                    "dimension from its start to its end, or select two "
                    "objects.")
                return
            p1, p2 = ends
            mode = "single"
            srcs = [sel[0]]
        elif len(sel) == 2:
            if self.options.frm == "centers":
                p1, p2 = _center(sel[0]), _center(sel[1])
                mode = "centers"
            else:
                p1, p2 = _first_node(sel[0]), _first_node(sel[1])
                mode = "ends"
                if p1 is None or p2 is None:
                    inkex.errormsg(
                        "Endpoint mode needs two paths. Use 'Bounding-box "
                        "centers' for non-path objects, or select two paths.")
                    return
            srcs = [sel[0], sel[1]]
        else:
            inkex.errormsg(
                "Select one line (drawn start -> end) or exactly two objects "
                "to dimension between.")
            return

        if p1 is None or p2 is None:
            inkex.errormsg("Could not read a point from the selection.")
            return
        if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) < 1e-9:
            inkex.errormsg("The two points coincide; nothing to dimension.")
            return

        src_ids = [e.get_id() for e in srcs]
        parent = srcs[0].getparent()

        grp = Group()
        grp.label = "dimension"
        grp.set(_ns("role"), "dimension")
        grp.set(_ns("version"), "1")
        grp.set(_ns("mode"), mode)
        grp.set(_ns("source"), " ".join(src_ids))
        P = self._params_from_options()
        self._store_params(grp, P)
        parent.add(grp)

        self._render(grp, p1, p2, P)

        # Hide the construction line (single-line mode only).
        if mode == "single" and self.options.hide_source:
            self._hide(srcs[0])

    def _update(self, g):
        mode = g.get(_ns("mode")) or "single"
        src_ids = (g.get(_ns("source")) or "").split()
        els = [self.svg.getElementById(i) for i in src_ids]
        if not els or any(e is None for e in els):
            inkex.errormsg(
                "Cannot update this dimension: its source object(s) are no "
                "longer in the document.")
            return

        if mode == "single":
            ends = _end_nodes(els[0])
            if ends is None:
                inkex.errormsg("The source line has too few nodes to update.")
                return
            p1, p2 = ends
        elif mode == "centers":
            p1, p2 = _center(els[0]), _center(els[1])
        else:
            p1, p2 = _first_node(els[0]), _first_node(els[1])

        if p1 is None or p2 is None:
            inkex.errormsg("Could not read points from the source object(s).")
            return
        if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) < 1e-9:
            inkex.errormsg("The source points coincide; nothing to dimension.")
            return

        if self.options.on_existing == "restyle":
            P = self._params_from_options()
            self._store_params(g, P)
        else:
            P = self._params_from_group(g)

        self._render(g, p1, p2, P)

    def _hide(self, el):
        # Make the source line invisible but keep it on the canvas so it
        # stays selectable (stroke:none, not display:none) — you can still
        # click/Tab it and edit its nodes, then re-run to update.
        style = el.style
        style["stroke"] = "none"
        style.pop("display", None)       # undo any older display:none
        el.style = style
        el.set(_ns("is-source"), "1")

    # ---- drawing ---------------------------------------------------------

    def _render(self, grp, p1, p2, P):
        """(Re)build the children of a dimension group between p1 and p2.

        p1/p2 are in document (composed) coordinates. The group may live
        inside a transformed container, so we give the group a transform
        that cancels its parent's composed transform — then drawing in
        document coordinates renders correctly (no offset/scale/rotation
        relative to the geometry being measured).
        """
        for child in list(grp):
            grp.remove(child)

        parent = grp.getparent()
        if parent is not None:
            grp.transform = -parent.composed_transform()

        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length < 1e-9:
            return
        ux, uy = dx / length, dy / length          # along
        nx, ny = -uy, ux                            # perpendicular (normal)

        off = self._mm(P["off"])
        ext = self._mm(P["ext"])
        arrow = self._mm(P["arrow"])
        sw = self._mm(P["sw"])

        a1 = (p1[0] + nx * off, p1[1] + ny * off)
        a2 = (p2[0] + nx * off, p2[1] + ny * off)

        cmds = []
        if abs(off) > 1e-9:
            w1 = (p1[0] + nx * (off + math.copysign(ext, off)),
                  p1[1] + ny * (off + math.copysign(ext, off)))
            w2 = (p2[0] + nx * (off + math.copysign(ext, off)),
                  p2[1] + ny * (off + math.copysign(ext, off)))
            cmds += [["M", p1[0], p1[1]], ["L", w1[0], w1[1]]]
            cmds += [["M", p2[0], p2[1]], ["L", w2[0], w2[1]]]
        cmds += [["M", a1[0], a1[1]], ["L", a2[0], a2[1]]]

        line = PathElement()
        line.path = Path(self._fmt(cmds))
        line.style = {
            "fill": "none",
            "stroke": P["color"],
            "stroke-width": "{:.4f}".format(sw),
            "stroke-linejoin": "round",
            "stroke-linecap": "round",
        }
        line.label = "dimension-line"
        grp.add(line)

        if arrow > 1e-9:
            for tip, ddir in ((a1, (-ux, -uy)), (a2, (ux, uy))):
                head = PathElement()
                head.path = Path(self._arrow(tip, ddir, arrow))
                head.style = {"fill": P["color"], "stroke": "none"}
                head.label = "dimension-arrow"
                grp.add(head)

        if not P["notext"]:
            grp.add(self._label(a1, a2, length, ux, uy, P))

    def _arrow(self, tip, direction, size):
        ux, uy = direction
        px, py = -uy, ux
        bx, by = tip[0] - ux * size, tip[1] - uy * size
        b1 = (bx + px * size * 0.35, by + py * size * 0.35)
        b2 = (bx - px * size * 0.35, by - py * size * 0.35)
        cmds = [["M", tip[0], tip[1]], ["L", b1[0], b1[1]],
                ["L", b2[0], b2[1]], ["Z"]]
        return self._fmt(cmds)

    def _value_text(self, length_uu, P):
        if P["usevar"]:
            return P["varname"]
        val = self.svg.uutounit(length_uu, P["unit"])
        txt = "{:.{p}f}".format(val, p=P["precision"])
        if P["suffix"]:
            txt += " " + P["unit"]
        return txt

    def _label(self, a1, a2, length_uu, ux, uy, P):
        mx, my = (a1[0] + a2[0]) / 2.0, (a1[1] + a2[1]) / 2.0
        angle = math.degrees(math.atan2(uy, ux))
        if angle > 90 or angle < -90:        # keep text upright
            angle += 180
        fs = P["fontsize"]                   # font size stays in px
        rad = math.radians(angle)
        # "up" direction for the upright glyphs (perpendicular to the line)
        upx, upy = math.sin(rad), -math.cos(rad)

        pos = P["textpos"]
        if pos == "above":
            cx, cy = mx + upx * (fs * 0.6), my + upy * (fs * 0.6)
        elif pos == "below":
            cx, cy = mx - upx * (fs * 0.6), my - upy * (fs * 0.6)
        else:                                # "center" -> sits on the line
            cx, cy = mx, my

        txt = self._value_text(length_uu, P)

        grp = Group()
        grp.set("transform",
                "rotate({:.3f} {:.3f} {:.3f})".format(angle, cx, cy))
        grp.label = "dimension-text"

        # centered text covers the line: white backing box for readability
        if pos == "center":
            w = max(1, len(txt)) * fs * 0.6
            pad = fs * 0.25
            rect = Rectangle()
            rect.set("x", "{:.3f}".format(cx - w / 2.0 - pad))
            rect.set("y", "{:.3f}".format(cy - fs * 0.6 - pad))
            rect.set("width", "{:.3f}".format(w + 2 * pad))
            rect.set("height", "{:.3f}".format(fs * 1.2 + 2 * pad))
            rect.style = {"fill": "#ffffff", "stroke": "none"}
            grp.add(rect)

        text = TextElement()
        text.set("x", "{:.3f}".format(cx))
        text.set("y", "{:.3f}".format(cy))
        text.style = {
            "font-size": "{:.2f}px".format(fs),
            "font-family": "sans-serif",
            "text-anchor": "middle",
            "dominant-baseline": "central",
            "fill": P["color"],
        }
        ts = Tspan()
        ts.text = txt
        text.append(ts)
        grp.add(text)
        return grp

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
