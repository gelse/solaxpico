# SolaxPico enclosure (FreeCAD)

This folder contains the FreeCAD case design as a **hull document plus external, version-controlled Python part files**. Geometry is defined in the `part_*.py` modules and referenced by scripted objects in `solaxpico.FCStd`, so the design can be edited without MCP.

## Files

- `solaxpico.FCStd` – FreeCAD document (hull): Parameters spreadsheet + scripted part objects that load shapes from the Python modules in this folder.
- `common.py` – shared parameter loading (from the `Parameters` spreadsheet) and helpers.
- `scripted_part.py` – generic scripted FeaturePython proxy used by the document.
- `part_baseplate.py`, `part_frame.py`, `part_tray.py`, `part_max485_tab.py`, `part_lid.py` – per-part geometry.
- `rebuild.py` – (re)creates/updates all part objects from the modules.

## Editing without MCP

1. Open `solaxpico.FCStd` in FreeCAD.
2. Edit dimensions in the **`Parameters`** spreadsheet (GUI-editable) and/or edit the per-part `.py` files.
3. Recompute the document (or run `rebuild.py`) to regenerate shapes from the external modules:

   In FreeCAD's Python console:

   ```python
   exec(open("/home/werner/dev/solaxpico/case/rebuild.py").read())
   ```

   (Adjust the path if the project lives elsewhere; the modules must be importable from the document's folder.)

4. Save the document.

`solaxpico.static-backup.FCStd` is a backup of the earlier static-shape document.
