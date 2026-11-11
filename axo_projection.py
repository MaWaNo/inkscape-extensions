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
Axonometric projection of flat-drawn faces for Inkscape 1.3+

Oblique axonometry with x horizontal, z vertical (same scale) and the
depth axis y at an angle, foreshortened by k = ly / lx.

  side : flat strip right of a vertical edge -> side face (y-z)
         horizontal (1,0) -> k*(cos a, -sin a), vertical unchanged
  top  : flat strip above a horizontal edge -> top face (x-y)
         upward (0,-1) -> k*(cos a, -sin a), horizontal unchanged

The joint line (a bbox edge of the selection) stays fixed. The matrix is
prepended to each selected object's transform in document coordinates.

Author: Markus Wallner-Novak, AI-assisted by Claude Code
"""

import math
import inkex
from inkex import Transform

__version__ = "1.0.1"


def _linear(mode, k, a):
    """2x2 linear part (a, b, c, d) in SVG convention (y down)."""
    ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
    if mode == "side":
        return (k * ca, -k * sa, 0.0, 1.0)
    if mode == "top":
        return (1.0, 0.0, -k * ca, k * sa)
    raise ValueError(mode)


def _inverse(m):
    a, b, c, d = m
    det = a * d - b * c
    if abs(det) < 1e-12:
        raise inkex.AbortExtension("Projection matrix is singular.")
    return (d / det, -b / det, -c / det, a / det)


class AxoProjection(inkex.EffectExtension):
    def add_arguments(self, pars):
        pars.add_argument("--tab")
        pars.add_argument("--mode", default="side")
        pars.add_argument("--pivot", default="auto")
        pars.add_argument("--lx", type=float, default=80.0)
        pars.add_argument("--ly", type=float, default=35.66)
        pars.add_argument("--angle", type=float, default=35.0)
        pars.add_argument("--use_grid", type=inkex.Boolean, default=False)
        pars.add_argument("--grid_pick", type=int, default=0)

    def _axo_grids(self):
        """All axonometric grids in the document, in document order.

        Inkscape writes them in the namedview as
        <inkscape:grid type="axonomgrid" gridanglex=".." gridanglez=".."/>.
        """
        out = []
        for g in self.svg.xpath("//inkscape:grid"):
            if g.get("type") != "axonomgrid":
                continue
            try:
                ax = float(g.get("gridanglex", "0"))
                az = float(g.get("gridanglez", "0"))
            except ValueError:
                continue
            out.append({
                "label": (g.get(inkex.addNS("label", "inkscape"))
                          or g.get("id") or "axonomgrid"),
                "ax": ax, "az": az,
                "enabled": g.get("enabled", "true") != "false",
            })
        return out

    def _pick_grid(self, grids):
        """Choose one grid: explicit 1-based 'Grid #', else first enabled."""
        pick = self.options.grid_pick
        if pick and 1 <= pick <= len(grids):
            return grids[pick - 1]
        for g in grids:
            if g["enabled"]:
                return g
        return grids[0]

    def _grid_setup(self, base):
        """(angle, k, report-text) from the chosen document grid."""
        grids = self._axo_grids()
        if not grids:
            raise inkex.AbortExtension(
                "No axonometric grid found. Add one via File > Document "
                "Properties > Grids (type: Axonometric), or switch off "
                "'Align to document axonometric grid'.")
        g = self._pick_grid(grids)
        # side face recedes along Z, top face along X; if that axis is flat
        # (0 deg), fall back to whichever axis actually recedes.
        a = g["az"] if base == "side" else g["ax"]
        if not 0.0 < a < 90.0:
            a = g["az"] if 0.0 < g["az"] < 90.0 else g["ax"]
        if not 0.0 < a < 90.0:
            raise inkex.AbortExtension(
                "The axonometric grid has no usable depth angle for this "
                "face (both grid angles are 0 or degenerate).")
        k = 1.0 / math.sin(math.radians(a))

        lines = ["Axonometric grid alignment"]
        if len(grids) > 1:
            lines.append("%d axonometric grids in the document:" % len(grids))
            for i, gg in enumerate(grids, 1):
                lines.append("  %d. %s  (x %.3f deg, z %.3f deg)%s%s" % (
                    i, gg["label"], gg["ax"], gg["az"],
                    "" if gg["enabled"] else " [disabled]",
                    "  <= used" if gg is g else ""))
            lines.append("Set 'Grid #' on the Options tab to choose another.")
        lines.append(
            "Recalculated for this face:  y angle = %.3f deg,  "
            "x length = 1,  y length = %.4f  (k = 1/sin = %.4f)" % (a, k, k))
        return a, k, "\n".join(lines)

    def _iso_setup(self, mode):
        """Linear map + report for a true-isometric face from both grid
        angles. Unlike the oblique modes, no axis stays horizontal: the two
        in-plane axes follow the grid's two diagonals, so the top face is a
        rhombus. Needs an axonometric grid with both angles in (0, 90)."""
        if not self.options.use_grid:
            raise inkex.AbortExtension(
                "Isometric modes read the grid's two angles. Tick 'Align to "
                "document axonometric grid' (and have an Axonometric grid in "
                "the document).")
        grids = self._axo_grids()
        if not grids:
            raise inkex.AbortExtension(
                "No axonometric grid found. Add one via File > Document "
                "Properties > Grids (type: Axonometric).")
        g = self._pick_grid(grids)
        ax, az = g["ax"], g["az"]
        if not (0.0 < ax < 90.0 and 0.0 < az < 90.0):
            raise inkex.AbortExtension(
                "Isometric modes need BOTH grid angles strictly between 0 and "
                "90 deg. This grid has an axis at 0 deg (an oblique grid) - "
                "use the plain 'side' / 'top' modes for that.")
        # EQUAL foreshortening on every axis (true isometric: a cube reads
        # as a cube). Each in-plane unit maps to a unit-length vector along
        # its grid diagonal; the vertical axis stays unit length. (This is
        # different from the oblique modes, which foreshorten the depth by
        # 1/sin so a true-shape face stays true.)
        cax, sax = math.cos(math.radians(ax)), math.sin(math.radians(ax))
        caz, saz = math.cos(math.radians(az)), math.sin(math.radians(az))
        if mode == "iso_top":                       # x-y plane -> rhombus
            lin = (caz, -saz, cax, sax)
            face = "top (x-y rhombus)"
        elif mode == "iso_right":                   # x-z plane, right axis
            lin = (caz, -saz, 0.0, 1.0)
            face = "right face (x-z)"
        elif mode == "iso_left":                    # y-z plane, left axis
            lin = (-cax, -sax, 0.0, 1.0)
            face = "left face (y-z)"
        else:
            raise inkex.AbortExtension("Unknown isometric mode.")
        report = ("Isometric %s\nGrid '%s': left axis (x) %.3f deg, right "
                  "axis (z) %.3f deg.\nEqual foreshortening on all axes; draw "
                  "the face in the grid's Spacing-Y unit so corners land on "
                  "the grid." % (face, g["label"], ax, az))
        return lin, report

    def effect(self):
        items = [e for e in self.svg.selection.values()
                 if isinstance(e, inkex.ShapeElement)]
        if not items:
            raise inkex.AbortExtension("Select the flat-drawn face (paths or groups) first.")
        # raw transforms first: touching inkex' wrapped e.transform (e.g. for the
        # bbox) rewrites the attribute rounded to 6 significant digits
        raw = {id(e): Transform(inkex.etree.ElementBase.get(e, "transform") or "") for e in items}

        mode = self.options.mode
        base = mode.replace("_inv", "")
        iso = mode.startswith("iso_")
        if iso:
            # True isometric: two diagonals from the grid (top = rhombus).
            lin, report = self._iso_setup(mode)
            self.msg(report)
        elif self.options.use_grid:
            # Oblique, snapped to the grid: depth angle from the grid,
            # foreshortening k = 1/sin(angle) so one flat drawing-unit step
            # rises exactly one grid row and corners land on the grid.
            angle, k, report = self._grid_setup(base)
            self.msg(report)       # show the recalculated values in a window
            lin = _linear(base, k, angle)
        else:
            # Oblique, manual tripod.
            lin = _linear(base, self.options.ly / self.options.lx,
                          self.options.angle)
        if mode.endswith("_inv"):
            lin = _inverse(lin)

        # selection bbox in document (root user) coordinates
        bbox = None
        for e in items:
            parent = e.getparent()
            pt = parent.composed_transform() if isinstance(parent, inkex.ShapeElement) else Transform()
            bb = e.bounding_box(pt)
            if bb is not None:
                bbox = bb if bbox is None else bbox + bb
        if bbox is None:
            raise inkex.AbortExtension("Selection has no bounding box.")

        pivot = self.options.pivot
        if pivot == "auto":
            if iso:                           # keep the bottom-left corner
                px, py = bbox.left, bbox.bottom
            elif base == "side":
                px, py = bbox.left, bbox.center_y
            else:                             # top
                px, py = bbox.center_x, bbox.bottom
        else:
            px = {"left": bbox.left, "right": bbox.right}.get(pivot, bbox.center_x)
            py = {"top": bbox.top, "bottom": bbox.bottom}.get(pivot, bbox.center_y)

        a, b, c, d = lin
        # P = T(p) * A * T(-p)
        P = Transform((a, b, c, d, px - (a * px + c * py), py - (b * px + d * py)))

        for e in items:
            parent = e.getparent()
            pt = parent.composed_transform() if isinstance(parent, inkex.ShapeElement) else Transform()
            # new local = Pt^-1 * P * Pt * old
            t = (-pt) @ P @ pt @ raw[id(e)]
            # write with full precision (inkex rounds to 6 significant digits)
            inkex.etree.ElementBase.set(e, "transform", "matrix(%s)" % ",".join("%.12g" % v for v in t.to_hexad()))


if __name__ == "__main__":
    AxoProjection().run()
