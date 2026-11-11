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
Wall cavity insulation for Inkscape 1.3+

Select exactly TWO paths that form the two faces of a wall cavity
(e.g. the inner and outer line of a wall). The extension samples both
faces, builds a centerline and a half-thickness, and draws an
insulation symbol filling the cavity.

Styles:
  - batt   : soft looped/wavy ribbon (semicircle loops, alternating)
  - rigid  : diagonal zig-zag hatch

Author: Markus Wallner-Novak, AI-assisted by Claude Code
"""

import math
import inkex
from inkex import PathElement, Path
from inkex.paths import Move, Line, Curve

__version__ = "1.0.1"


def _flatten(elem, tolerance=0.2):
    """Return a flat list of (x,y) points approximating the path,
    in the element's own user units, transformed to document coords."""
    csp = elem.path.transform(elem.composed_transform()).to_superpath()
    pts = []
    for sub in csp:
        # sub is a list of [ctrl_in, knot, ctrl_out]
        sub_pts = _flatten_subpath(sub, tolerance)
        if sub_pts:
            pts.extend(sub_pts)
    return pts


def _flatten_subpath(sub, tol):
    out = []
    for i in range(len(sub) - 1):
        p0 = sub[i][1]
        c0 = sub[i][2]
        c1 = sub[i + 1][0]
        p1 = sub[i + 1][1]
        out.extend(_bezier_points(p0, c0, c1, p1, tol))
    # append final knot
    if sub:
        out.append(tuple(sub[-1][1]))
    return out


def _bezier_points(p0, c0, c1, p1, tol, depth=0):
    """Adaptive subdivision of a single cubic bezier into points (excl. last)."""
    if depth > 18 or _flat_enough(p0, c0, c1, p1, tol):
        return [tuple(p0)]
    # de Casteljau split at t=0.5
    m01 = _mid(p0, c0)
    m12 = _mid(c0, c1)
    m23 = _mid(c1, p1)
    m012 = _mid(m01, m12)
    m123 = _mid(m12, m23)
    m = _mid(m012, m123)
    left = _bezier_points(p0, m01, m012, m, tol, depth + 1)
    right = _bezier_points(m, m123, m23, p1, tol, depth + 1)
    return left + right


def _flat_enough(p0, c0, c1, p1, tol):
    d1 = _line_dist(p0, p1, c0)
    d2 = _line_dist(p0, p1, c1)
    return d1 <= tol and d2 <= tol


def _line_dist(a, b, p):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy)
    if L < 1e-9:
        return math.hypot(px - ax, py - ay)
    return abs((px - ax) * dy - (py - ay) * dx) / L


def _mid(a, b):
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def _resample(pts, n):
    """Resample a polyline to n equally spaced points by arc length."""
    if len(pts) < 2:
        return pts[:] * n
    seg = []
    total = 0.0
    for i in range(len(pts) - 1):
        d = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        seg.append(d)
        total += d
    if total < 1e-9:
        return [pts[0]] * n
    out = []
    step = total / (n - 1)
    target = 0.0
    acc = 0.0
    idx = 0
    out.append(pts[0])
    for k in range(1, n - 1):
        target = step * k
        while idx < len(seg) and acc + seg[idx] < target:
            acc += seg[idx]
            idx += 1
        if idx >= len(seg):
            out.append(pts[-1])
            continue
        rem = target - acc
        t = rem / seg[idx] if seg[idx] > 1e-9 else 0.0
        x = pts[idx][0] + t * (pts[idx + 1][0] - pts[idx][0])
        y = pts[idx][1] + t * (pts[idx + 1][1] - pts[idx][1])
        out.append((x, y))
    out.append(pts[-1])
    return out


def _closest_point_on_polyline(p, poly):
    """Return the point on polyline `poly` closest to point `p`."""
    best = poly[0]
    best_d = float("inf")
    px, py = p
    for i in range(len(poly) - 1):
        ax, ay = poly[i]
        bx, by = poly[i + 1]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        if L2 < 1e-12:
            qx, qy = ax, ay
        else:
            t = ((px - ax) * dx + (py - ay) * dy) / L2
            t = max(0.0, min(1.0, t))
            qx, qy = ax + t * dx, ay + t * dy
        d = (px - qx) ** 2 + (py - qy) ** 2
        if d < best_d:
            best_d = d
            best = (qx, qy)
    return best


def _align(a, b):
    """Reverse b if that makes its start nearer a's start (so both run same way)."""
    d_same = math.hypot(a[0][0] - b[0][0], a[0][1] - b[0][1])
    d_flip = math.hypot(a[0][0] - b[-1][0], a[0][1] - b[-1][1])
    if d_flip < d_same:
        return list(reversed(b))
    return b


class WallInsulation(inkex.EffectExtension):

    def add_arguments(self, pars):
        pars.add_argument("--tab")
        pars.add_argument("--style", default="batt")
        pars.add_argument("--spacing", type=float, default=8.0,
                          help="Loop/zig pitch along the wall, in px")
        pars.add_argument("--inset", type=float, default=0.0,
                          help="Gap left at each cavity face, in px")
        pars.add_argument("--stroke_width", type=float, default=0.5)
        pars.add_argument("--stroke_color", type=str, default="#000000")
        pars.add_argument("--boundaries", type=inkex.Boolean, default=True,
                          help="Also draw the two face lines")

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
        sel = [e for e in self.svg.selection if isinstance(e, PathElement)]
        if len(sel) != 2:
            inkex.errormsg(
                "Select exactly two paths: the two faces of the wall cavity.")
            return

        a = _flatten(sel[0])
        b = _flatten(sel[1])
        if len(a) < 2 or len(b) < 2:
            inkex.errormsg("One of the selected paths has no usable geometry.")
            return

        b = _align(a, b)

        # mean cavity width (used for auto pitch)
        na = min(len(a), len(b))
        widths = [math.hypot(a[i][0] - b[i][0], a[i][1] - b[i][1])
                  for i in range(0, na, max(1, na // 20))]
        cavity = sum(widths) / len(widths) if widths else 0.0

        pitch = self.options.spacing
        if pitch <= 0:
            # DXF batt proportions: cell height = 0.8 * half-width
            # (half-width = cavity / 2), so pitch = 0.4 * cavity
            pitch = max(cavity * 0.4, 1.0)

        # length of side A drives sampling density
        length = sum(math.hypot(a[i + 1][0] - a[i][0], a[i + 1][1] - a[i][1])
                     for i in range(len(a) - 1))
        n_units = max(1, int(round(length / max(pitch, 0.5))))

        # for batt we want 2 points per loop; for rigid 1 per zig
        if self.options.style == "batt":
            samples = n_units * 2 + 1
        else:
            samples = n_units + 1
        samples = max(samples, 3)

        ra = _resample(a, samples)
        # pair each A-station to the closest point on face B, so stations
        # are truly opposing even if the two faces were drawn with
        # different node counts, offsets, or spacing (prevents sheared loops)
        rb = [_closest_point_on_polyline(p, b) for p in ra]

        inset = self.options.inset
        if inset > 0:
            ra, rb = self._apply_inset(ra, rb, inset)

        if self.options.style == "batt":
            d = self._build_batt(ra, rb)
        else:
            d = self._build_rigid(ra, rb)

        if not d:
            inkex.errormsg("Could not build insulation geometry.")
            return

        if self.options.boundaries:
            d = d + " " + self._boundary_lines(ra, rb)

        node = PathElement()
        node.path = Path(d)
        node.style = {
            "fill": "none",
            "stroke": self._color_css(),
            "stroke-width": str(self.options.stroke_width),
            "stroke-linejoin": "round",
            "stroke-linecap": "round",
        }
        node.label = "insulation"
        # place into the layer of the first selection
        parent = sel[0].getparent()
        parent.add(node)

    def _apply_inset(self, ra, rb, inset):
        na, nb = [], []
        for pa, pb in zip(ra, rb):
            vx, vy = pb[0] - pa[0], pb[1] - pa[1]
            L = math.hypot(vx, vy)
            if L < 1e-9:
                na.append(pa)
                nb.append(pb)
                continue
            ux, uy = vx / L, vy / L
            d = min(inset, L / 2.0 - 0.01)
            na.append((pa[0] + ux * d, pa[1] + uy * d))
            nb.append((pb[0] - ux * d, pb[1] - uy * d))
        return na, nb

    # One insulation cell, taken VERBATIM from the reference DXF dynamic
    # block (the wide stretch state), in normalized cell coordinates:
    #   u = across the cavity: -1 = face A, +1 = face B
    #   v = along the wall: 0 = cell start, 1 = cell end
    # Each tuple is (u, v, bulge); bulge applies to the segment starting at
    # that vertex (DXF convention). The cell is an hourglass/teardrop: it
    # pinches (the two strands cross) near face A and swells into a large
    # rounded bulb whose nose reaches face B. Stacking identical cells makes
    # the bulbs interleave with the neighbouring pinches -> the classic
    # overlapping-teardrop batt pattern.
    _BATT_CELL = [
        (-1.0000, 0.0000, -0.4142),
        (-0.5265, 0.4998, -0.1094),
        (0.0000, 0.2499,  0.1094),
        (0.5265, 0.0000,  0.9200),   # bulb -> nose just kisses face B (no overlap)
        (0.5265, 1.0000,  0.1094),
        (0.0000, 0.7501, -0.1094),
        (-0.5265, 0.4998, -0.4142),
        (-1.0000, 1.0000,  0.0000),  # last vertex, no trailing segment
    ]

    def _build_batt(self, ra, rb):
        """Overlapping-teardrop batt symbol, replicating the reference DXF.

        ra/rb are paired opposing points (face A / face B). Cells are laid
        end to end along the wall and mapped through the centerline frame
        so the symbol follows curves. Each cell is its own subpath, so
        there are no cross-cavity divider lines between cells.
        """
        n = len(ra)
        if n < 2:
            return ""

        # Build a centerline + per-station frame (along-wall tangent and
        # across-cavity vector) so the template can be mapped onto curves.
        mids = [((ra[i][0] + rb[i][0]) / 2.0, (ra[i][1] + rb[i][1]) / 2.0)
                for i in range(n)]
        # across vector at each station: from face A to face B
        across = [(rb[i][0] - ra[i][0], rb[i][1] - ra[i][1]) for i in range(n)]

        # cumulative arc length along the centerline
        cum = [0.0]
        for i in range(1, n):
            cum.append(cum[-1] + math.hypot(mids[i][0] - mids[i - 1][0],
                                            mids[i][1] - mids[i - 1][1]))
        total = cum[-1]
        if total < 1e-9:
            return ""

        # one cell per pitch; DXF proportion is cell height ~= 0.95 * cavity
        # width (2.605 tall for 5.5 wide), i.e. ~0.47 * cavity.
        cell_len = max(self.options.spacing, 1.0) if self.options.spacing > 0 \
            else total / max(1, round(total /
                                      (0.95 * self._mean_halfwidth(across))))
        n_cells = max(1, int(round(total / cell_len)))
        cell_len = total / n_cells  # exact fit

        def frame_at(s):
            """Interpolate centerline point + across-vector at arc length s."""
            s = max(0.0, min(total, s))
            lo, hi = 0, n - 1
            for i in range(n - 1):
                if cum[i + 1] >= s:
                    lo, hi = i, i + 1
                    break
            seg = cum[hi] - cum[lo]
            t = (s - cum[lo]) / seg if seg > 1e-9 else 0.0
            mx = mids[lo][0] + t * (mids[hi][0] - mids[lo][0])
            my = mids[lo][1] + t * (mids[hi][1] - mids[lo][1])
            ax = across[lo][0] + t * (across[hi][0] - across[lo][0])
            ay = across[lo][1] + t * (across[hi][1] - across[lo][1])
            return (mx, my), (ax, ay)

        cmds = []
        for c in range(n_cells):
            s0 = c * cell_len
            # Determine the handedness of the local (along-wall, across-cavity)
            # frame at this cell. The bulge signs in _BATT_CELL are defined for
            # a right-handed (along x, across y) frame; if the actual frame is
            # left-handed (e.g. wall runs the other way, or across points the
            # opposite screen direction), every arc must flip side. Without
            # this, the symbol renders correctly on vertical walls but breaks
            # (squashed bulbs, curls) on horizontal ones.
            sc = s0 + 0.5 * cell_len
            (m0x, m0y), (ax, ay) = frame_at(sc)
            # along-wall tangent (direction of increasing s)
            (n0x, n0y), _ = frame_at(min(total, sc + 0.01 * cell_len))
            tx, ty = (n0x - m0x), (n0y - m0y)
            cross = tx * ay - ty * ax  # z of (tangent x across)
            # Calibrated so the known-good vertical wall (tangent up, across
            # pointing right -> cross < 0) maps to orient = +1.
            hand = 1.0 if cross < 0 else -1.0

            cell_pts = []
            for (u, v, bulge) in self._BATT_CELL:
                s = s0 + v * cell_len
                (mx, my), (ax2, ay2) = frame_at(s)
                px = mx + 0.5 * u * ax2
                py = my + 0.5 * u * ay2
                cell_pts.append((px, py, bulge))
            cmds.append(["M", cell_pts[0][0], cell_pts[0][1]])
            for k in range(len(cell_pts) - 1):
                x0, y0, b = cell_pts[k]
                x1, y1, _ = cell_pts[k + 1]
                self._emit_bulge(cmds, x0, y0, x1, y1, b, orient=hand)
        return self._fmt(cmds)

    def _mean_halfwidth(self, across):
        vals = [math.hypot(a[0], a[1]) / 2.0 for a in across if (a[0] or a[1])]
        return (sum(vals) / len(vals)) if vals else 1.0

    @staticmethod
    def _emit_bulge(cmds, x0, y0, x1, y1, bulge, orient=1.0):
        """Append an SVG arc (A) replicating a DXF bulge segment.

        `orient` is +1 for a right-handed local frame, -1 for left-handed;
        it flips the sweep direction so the arc bulges to the correct side
        regardless of which way the wall runs (otherwise the symbol only
        renders correctly for one wall orientation).
        """
        if abs(bulge) < 1e-9:
            cmds.append(["L", x1, y1])
            return
        chord = math.hypot(x1 - x0, y1 - y0)
        if chord < 1e-12:
            return
        incl = 4.0 * math.atan(abs(bulge))      # included arc angle
        r = chord / (2.0 * math.sin(incl / 2.0))
        large = 1 if incl > math.pi else 0
        sweep = 1 if bulge > 0 else 0
        if orient < 0:
            sweep = 1 - sweep
        cmds.append(["A", r, r, 0, large, sweep, x1, y1])

    def _build_batt_OLD(self, ra, rb):
        """(unused) previous teardrop construction kept for reference."""
        return ""

    def _boundary_lines(self, ra, rb):
        cmds = [["M", ra[0][0], ra[0][1]]]
        for p in ra[1:]:
            cmds.append(["L", p[0], p[1]])
        cmds.append(["M", rb[0][0], rb[0][1]])
        for p in rb[1:]:
            cmds.append(["L", p[0], p[1]])
        return self._fmt(cmds)

    def _build_rigid(self, ra, rb):
        """Diagonal zig-zag: alternate touching face A and face B."""
        cmds = []
        cmds.append(["M", ra[0][0], ra[0][1]])
        for i in range(1, len(ra)):
            if i % 2 == 1:
                cmds.append(["L", rb[i][0], rb[i][1]])
            else:
                cmds.append(["L", ra[i][0], ra[i][1]])
        return self._fmt(cmds)

    def _fmt(self, cmds):
        parts = []
        for c in cmds:
            if c[0] == "Z":
                parts.append("Z")
            elif c[0] == "A":
                # A rx ry x-rot large sweep x y
                rx, ry, rot, large, sweep, x, y = c[1:]
                parts.append(f"A {rx:.4f} {ry:.4f} {rot:g} {large:d} {sweep:d} "
                             f"{x:.4f} {y:.4f}")
            else:
                parts.append(c[0] + " " + " ".join(f"{v:.4f}" for v in c[1:]))
        return " ".join(parts)


if __name__ == "__main__":
    WallInsulation().run()
