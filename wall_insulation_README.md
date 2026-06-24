# Wall Cavity Insulation — Inkscape 1.3+ extension

Fills the space between two selected paths (the two faces of a wall
cavity) with an architectural insulation symbol. Two styles:

- **Batt / soft** — alternating looped ribbon (blanket insulation)
- **Rigid** — diagonal zig-zag hatch

It follows curved walls, not just straight ones.

## Install

Copy both files into your Inkscape **user extensions** folder:

- **Windows:** `%APPDATA%\inkscape\extensions\`
  (i.e. `C:\Users\<you>\AppData\Roaming\inkscape\extensions\`)
- Linux: `~/.config/inkscape/extensions/`
- macOS: `~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions/`

Files to copy:

    wall_insulation.inx
    wall_insulation.py

Restart Inkscape. The tool appears under
**Extensions → Architecture → Wall Cavity Insulation**.

You can confirm the folder from inside Inkscape:
**Edit → Preferences → System → User extensions**.

## Use

1. Draw the two faces of the wall as two separate paths
   (e.g. the inner and outer line of the cavity).
2. Select **both** paths.
3. **Extensions → Architecture → Wall Cavity Insulation**.
4. Pick style, set pitch / inset / stroke, click **Apply**.

A single new path named `insulation` is created in the layer of the
first-selected path.

## Parameters

| Param | Meaning |
|-------|---------|
| Style | batt (looped) or rigid (zig-zag) |
| Pitch along wall | spacing of loops/zigs, measured along the wall, in px |
| Inset from each face | gap left at both faces, in px |
| Stroke width | line weight of the symbol |
| Stroke color | symbol color |

## Notes / limitations

- The two paths should run roughly parallel and span the same extent.
  The extension auto-detects if the second path is drawn in the
  opposite direction and flips it.
- Sampling density is driven by the **pitch**; very small pitch on a
  long wall makes a heavier path.
- Open paths work best. If you select closed shapes, only the outline
  ordering is used — for a rectangular wall, draw the two long faces
  as separate open paths rather than one closed rectangle.
- Units are SVG user units (px). If your document is mm-based, the px
  values map to mm at 96dpi unless you've changed the document scale;
  adjust pitch/inset to taste after a first run.

## Adjusting the look

If you want denser/looser loops, change **Pitch**. If the loops feel
too flat or too round, the controlling code is `_build_batt()` in
`wall_insulation.py` (the `0.10` tangent factors set how fat each
loop is). `_build_rigid()` is the zig-zag.
