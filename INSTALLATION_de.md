# Inkscape-Erweiterungen – Installation

Drei Erweiterungen für **Inkscape 1.3 oder neuer**, Menü
**Erweiterungen → Architecture**:

- **Wall Cavity Insulation** – Dämmsymbol zwischen zwei Wandflächen
- **Dimension Line** – Maßlinie mit Maßhilfslinien, Endsymbolen und Maßtext
- **Axonometric Projection** – axonometrische Projektion flach gezeichneter Flächen

## Installation (Windows)

1. Inkscape schließen.

2. Diese **6 Dateien** in den Benutzer-Erweiterungsordner kopieren:

   ```
   wall_insulation.inx     wall_insulation.py
   dimension_line.inx      dimension_line.py
   axo_projection.inx      axo_projection.py
   ```

   Ordner (in den Explorer-Adressbalken einfügen):

   ```
   %APPDATA%\inkscape\extensions
   ```

   Das entspricht `C:\Users\<Benutzername>\AppData\Roaming\inkscape\extensions`.
   Den Ordner findet man in Inkscape auch unter
   **Bearbeiten → Einstellungen → System → Benutzer-Erweiterungen**.

3. Inkscape neu starten.

4. Die Werkzeuge erscheinen unter **Erweiterungen → Architecture**.

> Die `.md`-Dateien (Anleitungen) müssen **nicht** kopiert werden – sie sind
> nur Dokumentation.

### Linux

Ordner: `~/.config/inkscape/extensions/`

### macOS

Ordner:
`~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions/`

## Kurzanleitung

- **Dimension Line:** eine Linie zwischen den zwei zu bemaßenden Punkten
  zeichnen, auswählen, **Erweiterungen → Architecture → Dimension Line**.
  Die Maßlinie geht vom ersten zum letzten Knoten der Linie.
- **Wall Cavity Insulation:** die zwei Wandflächen als zwei Pfade zeichnen,
  beide auswählen, **Erweiterungen → Architecture → Wall Cavity Insulation**.
- **Axonometric Projection:** flach gezeichnete Fläche auswählen,
  **Erweiterungen → Architecture → Axonometric Projection**.

Details zu den Parametern stehen in `dimension_line_README.md` und
`wall_insulation_README.md`.

## Voraussetzung

Nur Inkscape selbst – es bringt sein eigenes Python mit. Es muss **kein**
Python installiert werden.
