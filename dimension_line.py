#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 Markus Wallner-Novak
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 2 of the License, or (at your option)
# any later version. See the LICENSE file for details.
#
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

import os
import json
import math
import inkex
from lxml import etree
from inkex import (PathElement, TextElement, Tspan, Path, Group, Rectangle,
                   Circle)

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
        pars.add_argument("--ends", default="arrow")
        pars.add_argument("--fontsize", type=float, default=10.0)
        pars.add_argument("--fontfamily", default="sans-serif")
        pars.add_argument("--fontcustom", default="")
        pars.add_argument("--stroke_width", type=float, default=0.25)
        pars.add_argument("--stroke_color", type=str, default="#000000")
        pars.add_argument("--notext", type=inkex.Boolean, default=False)
        pars.add_argument("--textpos", default="above")
        pars.add_argument("--textorient", default="horizontal")
        pars.add_argument("--usevar", type=inkex.Boolean, default=False)
        pars.add_argument("--varname", default="{B}")
        pars.add_argument("--var_italic", type=inkex.Boolean, default=True)
        pars.add_argument("--hide_source", type=inkex.Boolean, default=True)
        pars.add_argument("--on_existing", default="refresh")
        pars.add_argument("--preset", default="off")
        pars.add_argument("--save_slot", default="none")

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
            "ends": self.options.ends,
            "sw": self.options.stroke_width,       # mm
            "fontsize": self.options.fontsize,     # px
            "font": (self.options.fontcustom.strip()
                     or self.options.fontfamily),
            "color": self._color_css(),
            "unit": self.options.unit,
            "precision": self.options.precision,
            "suffix": self.options.suffix,
            "notext": self.options.notext,
            "textpos": self.options.textpos,
            "textorient": self.options.textorient,
            "usevar": self.options.usevar,
            "varname": self.options.varname,
            "var_italic": self.options.var_italic,
        }

    def _store_params(self, g, P):
        def s(name, val):
            g.set(_ns(name), str(val))
        s("offset", P["off"])
        s("ext", P["ext"])
        s("arrow", P["arrow"])
        s("ends", P["ends"])
        s("stroke-width", P["sw"])
        s("fontsize", P["fontsize"])
        s("font", P["font"])
        s("color", P["color"])
        s("unit", P["unit"])
        s("precision", P["precision"])
        s("suffix", "true" if P["suffix"] else "false")
        s("notext", "true" if P["notext"] else "false")
        s("textpos", P["textpos"])
        s("textorient", P["textorient"])
        s("usevar", "true" if P["usevar"] else "false")
        s("varname", P["varname"])
        s("var_italic", "true" if P["var_italic"] else "false")

    def _params_from_group(self, g):
        def a(name, default=""):
            v = g.get(_ns(name))
            return default if v is None else v
        return {
            "off": float(a("offset", "0")),
            "ext": float(a("ext", "0")),
            "arrow": float(a("arrow", "0")),
            "ends": a("ends", "arrow"),
            "sw": float(a("stroke-width", "0.25")),
            "fontsize": float(a("fontsize", "10")),
            "font": a("font", "sans-serif"),
            "color": a("color", "#000000"),
            "unit": a("unit", "mm"),
            "precision": int(a("precision", "0")),
            "suffix": a("suffix", "false") == "true",
            "notext": a("notext", "false") == "true",
            "textpos": a("textpos", "above"),
            "textorient": a("textorient", "aligned"),
            "usevar": a("usevar", "false") == "true",
            "varname": a("varname", "{B}"),
            "var_italic": a("var_italic", "true") == "true",
        }

    # ---- style preset slots (JSON file beside the extension) ------------

    def _preset_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "dimension_line_presets.json")

    def _load_all_presets(self):
        try:
            with open(self._preset_path(), "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _load_preset(self, slot):
        """Stored style for a slot, merged over current options for any
        keys a slot saved by an older version might be missing."""
        p = self._load_all_presets().get(str(slot))
        if not isinstance(p, dict):
            return None
        merged = self._params_from_options()
        merged.update(p)
        return merged

    def _save_preset(self, slot, P):
        data = self._load_all_presets()
        data[str(slot)] = P
        try:
            with open(self._preset_path(), "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=1)
        except OSError as exc:
            raise inkex.AbortExtension(
                "Could not write the preset file: %s" % exc)

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

    # ---- main ------------------------------------------------------------

    def effect(self):
        sel = list(self.svg.selection)

        # Split the selection into existing dimensions (via the group, or a
        # selected source line) and everything else (the targets to measure).
        groups, targets = [], []
        for el in sel:
            g = self._as_dim_group(el)
            if g is None:
                g = self._group_for_source(el)
            if g is not None:
                if g not in groups:
                    groups.append(g)
            else:
                targets.append(el)

        # Saving a style to a slot is a stand-alone action (it does not draw
        # a dimension), so a normal Apply never saves and never messages.
        # The style saved is the selected dimension's (if one is selected)
        # else the Options-tab style.
        if self.options.save_slot != "none":
            style = (self._params_from_group(groups[0])
                     if len(groups) == 1 else self._params_from_options())
            self._save_preset(self.options.save_slot, style)
            self.msg("Saved current style to preset slot %s."
                     % self.options.save_slot)
            return

        # Only existing dimension(s) selected -> update from their source.
        if groups and not targets:
            self._update(groups[0])
            return

        if len(groups) > 1:
            inkex.errormsg(
                "Select at most one existing dimension (as the style to copy) "
                "together with the line/objects to dimension.")
            return

        # Style for a new dimension, by precedence:
        #   a selected dimension (donor) > a chosen preset slot > the dialog.
        if len(groups) == 1:
            style = self._params_from_group(groups[0])
        elif self.options.preset != "off":
            style = self._load_preset(self.options.preset)
            if style is None:
                self.msg("Preset slot %s is empty; using the Options-tab "
                         "style." % self.options.preset)
                style = self._params_from_options()
        else:
            style = self._params_from_options()

        self._create(targets, style)

    def _create(self, targets, P):
        """Create a new dimension for the target object(s) with style P."""
        if len(targets) == 1:
            ends = _end_nodes(targets[0])
            if ends is None:
                inkex.errormsg(
                    "Select a single line/path (with at least two nodes) to "
                    "dimension from its start to its end, or select two "
                    "objects.")
                return
            p1, p2 = ends
            mode = "single"
            srcs = [targets[0]]
        elif len(targets) == 2:
            if self.options.frm == "centers":
                p1, p2 = _center(targets[0]), _center(targets[1])
                mode = "centers"
            else:
                p1, p2 = _first_node(targets[0]), _first_node(targets[1])
                mode = "ends"
                if p1 is None or p2 is None:
                    inkex.errormsg(
                        "Endpoint mode needs two paths. Use 'Bounding-box "
                        "centers' for non-path objects, or select two paths.")
                    return
            srcs = [targets[0], targets[1]]
        else:
            inkex.errormsg(
                "Select one line (drawn start -> end) or exactly two objects "
                "to dimension between (optionally plus one existing dimension "
                "whose style to copy).")
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

        self._add_terminators(grp, a1, a2, ux, uy, nx, ny, arrow, sw, P)

        if not P["notext"]:
            grp.add(self._label(a1, a2, length, ux, uy, P))

    # ---- end terminators -------------------------------------------------

    def _add_terminators(self, grp, a1, a2, ux, uy, nx, ny, size, sw, P):
        """Draw the chosen end marks at both ends of the dimension line."""
        style = P["ends"]
        if style == "none" or size <= 1e-9:
            return

        for tip, (dx, dy) in ((a1, (-ux, -uy)), (a2, (ux, uy))):
            if style == "arrow":                       # filled triangle
                head = PathElement()
                head.path = Path(self._arrow(tip, (dx, dy), size, closed=True))
                head.style = {"fill": P["color"], "stroke": "none"}
                head.label = "dimension-arrow"
                grp.add(head)
            elif style == "openarrow":                 # stroked open "<"
                head = PathElement()
                head.path = Path(self._arrow(tip, (dx, dy), size, closed=False))
                head.style = {
                    "fill": "none", "stroke": P["color"],
                    "stroke-width": "{:.4f}".format(sw),
                    "stroke-linecap": "round", "stroke-linejoin": "round",
                }
                head.label = "dimension-arrow"
                grp.add(head)
            elif style == "tick":                      # 45° architect slash
                a = (tip[0] + size * (0.5 * ux - 0.5 * nx),
                     tip[1] + size * (0.5 * uy - 0.5 * ny))
                b = (tip[0] + size * (-0.5 * ux + 0.5 * nx),
                     tip[1] + size * (-0.5 * uy + 0.5 * ny))
                mark = PathElement()
                mark.path = Path(self._fmt(
                    [["M", a[0], a[1]], ["L", b[0], b[1]]]))
                mark.style = {
                    "fill": "none", "stroke": P["color"],
                    "stroke-width": "{:.4f}".format(sw),
                    "stroke-linecap": "round",
                }
                mark.label = "dimension-tick"
                grp.add(mark)
            elif style == "dot":                       # filled circle
                dot = Circle()
                dot.set("cx", "{:.4f}".format(tip[0]))
                dot.set("cy", "{:.4f}".format(tip[1]))
                dot.set("r", "{:.4f}".format(size * 0.4))
                dot.style = {"fill": P["color"], "stroke": "none"}
                dot.label = "dimension-dot"
                grp.add(dot)

    def _arrow(self, tip, direction, size, closed=True):
        ux, uy = direction
        px, py = -uy, ux
        bx, by = tip[0] - ux * size, tip[1] - uy * size
        hw = 0.35 if closed else 0.4
        b1 = (bx + px * size * hw, by + py * size * hw)
        b2 = (bx - px * size * hw, by - py * size * hw)
        if closed:
            cmds = [["M", tip[0], tip[1]], ["L", b1[0], b1[1]],
                    ["L", b2[0], b2[1]], ["Z"]]
        else:
            cmds = [["M", b1[0], b1[1]], ["L", tip[0], tip[1]],
                    ["L", b2[0], b2[1]]]
        return self._fmt(cmds)

    def _value_text(self, length_uu, P):
        if P["usevar"]:
            return P["varname"]
        val = self.svg.uutounit(length_uu, P["unit"])
        txt = "{:.{p}f}".format(val, p=P["precision"])
        if P["suffix"]:
            txt += " " + P["unit"]
        return txt

    @staticmethod
    def _parse_runs(s):
        """Split a label into (text, kind) runs, kind in base/sub/sup.

        `_x`/`^x` take the following run (letters, digits, commas …) as a
        sub/superscript; `_{...}`/`^{...}` group an explicit span. Braces
        without a preceding `_`/`^` stay literal, so `{B}` is unchanged.
        """
        runs = []
        buf = []
        i, n = 0, len(s)

        def flush():
            if buf:
                runs.append(("".join(buf), "base"))
                buf.clear()

        while i < n:
            c = s[i]
            if c in "_^" and i + 1 < n:
                kind = "sub" if c == "_" else "sup"
                i += 1
                if s[i] == "{":
                    j = s.find("}", i + 1)
                    if j == -1:
                        content, i = s[i + 1:], n
                    else:
                        content, i = s[i + 1:j], j + 1
                else:
                    j = i
                    while j < n and s[j] not in " _^{":
                        j += 1
                    content, i = s[i:j], j
                flush()
                if content:
                    runs.append((content, kind))
            else:
                buf.append(c)
                i += 1
        flush()
        return runs or [("", "base")]

    def _label(self, a1, a2, length_uu, ux, uy, P):
        mx, my = (a1[0] + a2[0]) / 2.0, (a1[1] + a2[1]) / 2.0
        angle = math.degrees(math.atan2(uy, ux))
        if angle > 90 or angle < -90:        # keep text upright
            angle += 180
        fs = P["fontsize"]                   # font size stays in px
        rad = math.radians(angle)
        # "up" direction for the upright glyphs (perpendicular to the line)
        upx, upy = math.sin(rad), -math.cos(rad)
        horizontal = P["textorient"] == "horizontal"

        txt = self._value_text(length_uu, P)
        # The variable text may carry sub/superscript markup; the measured
        # value is always a plain run.
        if P["usevar"]:
            runs = self._parse_runs(txt)
            base_italic = P["var_italic"]
        else:
            runs = [(txt, "base")]
            base_italic = False
        plain = "".join(r[0] for r in runs)

        pos = P["textpos"]
        if pos == "center":                  # sits on the line
            cx, cy = mx, my
        else:
            d = fs * 0.6
            # horizontal text beside a steep line must clear it: add the
            # share of the text's half-width that lies along the offset.
            if horizontal:
                d += 0.5 * max(1, len(plain)) * fs * 0.6 * abs(upx)
            sign = 1.0 if pos == "above" else -1.0
            cx, cy = mx + sign * upx * d, my + sign * upy * d

        textangle = 0.0 if horizontal else angle

        grp = Group()
        if abs(textangle) > 1e-9:
            grp.set("transform",
                    "rotate({:.3f} {:.3f} {:.3f})".format(textangle, cx, cy))
        grp.label = "dimension-text"

        # centered text covers the line: white backing box for readability
        if pos == "center":
            w = max(1, len(plain)) * fs * 0.6
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
            "font-family": P["font"],
            "text-anchor": "middle",
            "dominant-baseline": "central",
            "font-style": "italic" if base_italic else "normal",
            "fill": P["color"],
        }
        for content, kind in runs:
            ts = Tspan()
            ts.text = content
            if kind in ("sub", "sup"):
                # indices are kept UPRIGHT (normal), smaller, and shifted
                ts.style = {
                    "font-style": "normal",
                    "font-size": "65%",
                    "baseline-shift": "sub" if kind == "sub" else "super",
                }
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
