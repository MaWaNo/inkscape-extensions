# Changelog

All notable changes to these Inkscape extensions are documented here.
Versions apply to the set as a whole.

## [1.0.1] — 2026-11-11

- Set the author line to "Markus Wallner-Novak, AI-assisted by Claude
  Code" (was a placeholder). No functional change.

## [1.0.0] — 2026-11-11

First tagged release.

### Dimension Line
- Dimension a single drawn line (first node → last node); also two
  objects (path endpoints or bbox centers).
- Geometry in mm, font size in px.
- End marks: arrow, open arrow, tick (45° architect), dot, none.
- Text position above / below / centered (white backing box); text
  orientation horizontal or aligned to the line; upright index for
  variable text (`t_CLT`, `f_{m,CLT}`, ISO 80000 style); font picker.
- Each dimension is a tagged group (`dimline:*`); re-run rebuilds it from
  the source's current position; source line hidden via `stroke:none`.
- Copy a style from another dimension (donor); one saved default style
  via the **Dimension Line: Save Style** command.
- Works inside transformed groups/layers.

### Axonometric Projection
- Oblique modes (`side` / `top`) for an oblique grid (one grid angle 0).
- True isometric modes (`iso_right` / `iso_left` / `iso_top`, top =
  rhombus) for grids with both angles non-zero, with equal foreshortening
  on all axes (a cube reads as a cube, circles → correct ellipses).
- Aligns to the document's axonometric grid; picks among several grids;
  reports the values used.

### Wall Cavity Insulation
- Batt (looped) and rigid (zig-zag) insulation between two wall faces;
  follows curved walls.

[1.0.1]: https://github.com/MaWaNo/inkscape-extensions/releases/tag/v1.0.1
[1.0.0]: https://github.com/MaWaNo/inkscape-extensions/releases/tag/v1.0.0
