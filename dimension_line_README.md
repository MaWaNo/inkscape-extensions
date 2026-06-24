# Dimension Line — Inkscape 1.3+ extension

Draws an architectural dimension line between two points. The easiest
way is to **draw one line** between the points you want to measure and
run — the dimension goes from that path's first node to its last node.
Selecting **two objects** also works (endpoints or bbox centers). The
result is a dimension line offset parallel to the measured span, with
**witness lines**, **arrowheads** and a **distance label** carrying the
real measured length in the unit you choose.

The numeric value can be swapped for a **variable placeholder**
(e.g. `{B}`, `L1`, `b_eff`) while the geometry is still placed using the
true distance — handy for parametric / templated drawings.

Each dimension is a **single group** that remembers the object it was
measured from, so you can **rebuild it after the source moves** by
re-running the extension on it (give it a keyboard shortcut). In
single-line mode the source/construction line is **hidden** after
dimensioning. See [Editing & live update](#editing--live-update).

Companion to `wall_insulation.py` (same **Architecture** submenu and
conventions).

## Install

Copy both files into your Inkscape **user extensions** folder:

- **Windows:** `%APPDATA%\inkscape\extensions\`
  (i.e. `C:\Users\<you>\AppData\Roaming\inkscape\extensions\`)
- Linux: `~/.config/inkscape/extensions/`
- macOS: `~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions/`

Files to copy:

    dimension_line.inx
    dimension_line.py

Restart Inkscape. The tool appears under
**Extensions → Architecture → Dimension Line**.

You can confirm the folder from inside Inkscape:
**Edit → Preferences → System → User extensions**.

## Use

**Single line (easiest):**

1. Draw a line/path between the two points you want to measure (a plain
   line, a combined path, or one inside a group all work).
2. Select it.
3. **Extensions → Architecture → Dimension Line**.
4. Set the options, optionally enable the variable, click **Apply**.

The dimension is drawn from the path's **first node** to its **last
node**.

**Two objects:**

1. Decide where the two measure points are.
   - For **Path endpoints** mode: draw two short marker strokes and snap
     their *start* nodes to the spots you want to measure.
   - For **Bounding-box centers** mode: any two objects (dots, crosses,
     shapes) work — their bbox centers are used.
2. Select **both** objects, then run as above.

One new **group** (labeled `dimension`) is created in the layer of the
first-selected object, containing a `dimension-line` path (witness lines
+ main line), one or two `dimension-arrow` paths, and a
`dimension-text` group (omitted in *No text* mode). The group also
carries `dimline:*` metadata — see
[Editing & live update](#editing--live-update).

> **Settings are remembered.** Inkscape stores the last-used values of
> every parameter per extension, so the dialog reopens with whatever you
> last entered (across sessions too).

## Units

Geometry is entered in **mm** and converted to document user units:
**line offset, witness extension, arrow size, stroke width**. Only the
**font size** is in **px**.

## Parameters

### Options tab

| Param | Meaning |
|-------|---------|
| Take points from | only used when **two** objects are selected: `ends` (first node of each path) or `centers` (bbox center of each object) |
| Display unit | mm / cm / m / px — the value shown in the label, converted from document units |
| Decimal places | rounding of the displayed value (0–6) |
| Append unit | add the unit string after the number (e.g. `1250 mm`) |
| Line offset (mm) | distance the dimension line sits parallel to the span; `0` = drawn directly on the points; sign sets which side |
| Witness extension (mm) | how far the witness lines run past the dimension line |
| Arrow size (mm) | filled-triangle arrowhead size; `0` = no arrows |
| Stroke width (mm) | line weight of line + witness lines |
| Stroke color | color of line, arrows and text |
| No text | draw only the geometry (line + witness + arrows), no label |
| Text position | `above` / `below` the line, or `center` (sits on the line over a white backing box so it covers the line for readability) |
| Font size (px) | label size in px |
| Hide the source line | single-line mode: set the construction line to `display:none` after dimensioning (it stays in the file) |

### Update tab

| Param | Meaning |
|-------|---------|
| When an existing dimension is selected | `refresh` = rebuild from the source keeping the group's stored style; `restyle` = rebuild and re-apply the current Options-tab settings |

### Variable tab

| Param | Meaning |
|-------|---------|
| Replace value with a variable | use a placeholder instead of the number |
| Variable text | the text to show (e.g. `{B}`, `L1`, `b_eff`) |

When the variable is enabled, only the *displayed* text changes — the
line, offset and label position are still computed from the real
distance, so you can toggle it without anything moving. The label is
plain SVG text, so a later find/replace across the file updates every
instance at once.

## How the points are chosen

- **Single selection** — the first and last on-curve nodes of the path
  (start → end), in document user units. A combined path or a group
  containing paths works too: the very first and very last nodes drawn
  are used.
- **Path endpoints (`ends`)** — the first on-curve node of each selected
  path, taken in document user units (with the element's own transform
  applied). Needs two **paths**; non-path objects fail in this mode.
- **Bounding-box centers (`centers`)** — `(center_x, center_y)` of each
  object's bounding box. Works for any object type.

## Editing & live update

Every dimension is created as **one group** carrying custom
`dimline:*` attributes (its own namespace), the same idea TexText uses
to make its objects re-editable. The group stores:

- the **id(s) of the source object(s)** and the mode (`single` /
  `ends` / `centers`);
- **all the style parameters** (offset, arrow, font size, colour, …).

Inkscape extensions can't react to changes live, so the dependency is a
**one-shot rebuild**:

1. Move or edit the source line (in single-line mode it's hidden — show
   it again from the **Objects** panel, *Object → Objects…*).
2. Select the dimension group (or its hidden source line) and run the
   extension again.
3. It re-reads the source's **current** geometry and redraws the
   dimension in place — same group, no duplicates.

Assign a **keyboard shortcut** under *Edit → Preferences → Interface →
Keyboard*, search "Dimension Line", so a single keypress refreshes the
selected dimension.

On an existing dimension the **Update tab** chooses:

- **Refresh** (default) — keep the look stored in the group, just
  re-fit the geometry to the (moved) source.
- **Re-apply** — also restyle it with the current Options-tab values.
  Inkscape can't pre-load the stored values into the dialog, so use this
  when you deliberately want to change the style.

## Notes / limitations

- Select **one** line/path or **exactly two** objects; anything else
  aborts with a message.
- If the two points coincide (zero distance) nothing is drawn.
- The label is kept upright automatically: when the span points "left",
  the text is rotated an extra 180° so it never reads upside-down.
- The arrowheads are solid triangles whose apex points outward at each
  end of the dimension line.
- Units: the measured pixel length is converted to the chosen display
  unit via the document's own unit scale, so the number matches what
  Inkscape's ruler reports for the same span.

## Adjusting the look

- **Loops too tight / too loose around the geometry?** Change
  **Line offset** and **Witness extension**.
- **Arrowhead proportions** live in `_arrow()` in `dimension_line.py`
  (the `0.35` factor sets the half-width of the triangle base).
- **Text standoff** (above/below) is the `fs * 0.6` term in `_label()`;
  the centered backing-box size is the `w`/`pad` terms there.
