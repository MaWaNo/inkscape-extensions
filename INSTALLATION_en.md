# Inkscape extensions – installation

Three extensions for **Inkscape 1.3 or newer**, menu
**Extensions → Architecture**:

- **Wall Cavity Insulation** – insulation symbol between two wall faces
- **Dimension Line** – dimension line with witness lines, end marks and a label
- **Axonometric Projection** – axonometric projection of flat-drawn faces

## Installation (Windows)

1. Close Inkscape.

2. Copy these **7 files** into the user extensions folder:

   ```
   wall_insulation.inx          wall_insulation.py
   dimension_line.inx           dimension_line.py
   dimension_line_savestyle.inx
   axo_projection.inx           axo_projection.py
   ```

   (`dimension_line_savestyle.inx` is the optional "Save Style" command;
   it reuses `dimension_line.py`.)

   Folder (paste into the Explorer address bar):

   ```
   %APPDATA%\inkscape\extensions
   ```

   This is `C:\Users\<username>\AppData\Roaming\inkscape\extensions`.
   You can also find the folder from inside Inkscape under
   **Edit → Preferences → System → User extensions**.

3. Restart Inkscape.

4. The tools appear under **Extensions → Architecture**.

> The `.md` files (documentation) do **not** need to be copied – they are
> reference only.

### Linux

Folder: `~/.config/inkscape/extensions/`

### macOS

Folder:
`~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions/`

## Quick guide

- **Dimension Line:** draw a line between the two points to be measured,
  select it, **Extensions → Architecture → Dimension Line**. The
  dimension runs from the line's first node to its last node.
- **Wall Cavity Insulation:** draw the two wall faces as two paths,
  select both, **Extensions → Architecture → Wall Cavity Insulation**.
- **Axonometric Projection:** select the flat-drawn face,
  **Extensions → Architecture → Axonometric Projection**.

Details on the parameters are in `dimension_line_README.md` and
`wall_insulation_README.md`.

## Requirement

Only Inkscape itself – it ships with its own Python. There is **no** need
to install Python.
