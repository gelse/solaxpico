"""Rebuild all solaxpico case parts from external per-part Python modules.

Run this inside FreeCAD (GUI or FreeCADCmd) with solaxpico.FCStd open:

    exec(open('/home/werner/dev/solaxpico/case/rebuild.py').read())

Or from the Macro menu after opening the document. It (re)creates scripted
part objects that load geometry from the per-part .py files in this folder.
Edit those .py files or the Parameters spreadsheet, then recompute/rebuild.
"""

import os
import sys

CASE_DIR = os.path.dirname(os.path.abspath(__file__))
if CASE_DIR not in sys.path:
    sys.path.insert(0, CASE_DIR)

import FreeCAD as App
import scripted_part

PARTS = [
    # (object name, label, module, kwargs, (x,y,z), (r,g,b))
    ("baseplate_param", "baseplate", "part_baseplate", {}, (0, 0, 0), (0.20, 0.40, 0.80)),
    ("frame_xneg_param", "frame-half-xneg", "part_frame",
     {"side": "-x", "end_hole": False}, (0, 0, 1.2), (0.90, 0.45, 0.10)),
    ("frame_xpos_param", "frame-half-xpos", "part_frame",
     {"side": "+x", "end_hole": True}, (0, 0, 1.2), (0.95, 0.75, 0.10)),
    ("tray_param", "converter-tray", "part_tray", {}, (0, 0, 7.2), (0.20, 0.70, 0.30)),
    ("max485_param", "max485-tab", "part_max485_tab", {}, (0, 0, 19.2), (0.60, 0.25, 0.75)),
    ("lid_param", "lid", "part_lid", {}, (0, 0, 21.2), (0.75, 0.85, 0.95)),
]


def main(doc=None):
    if doc is None:
        doc = App.ActiveDocument or App.getDocument("solaxpico")
    if doc is None:
        raise RuntimeError("No document open. Open solaxpico.FCStd first.")

    for name, label, module, kwargs, pos, color in PARTS:
        placement = App.Placement(App.Vector(*pos), App.Rotation())
        obj = scripted_part.create(doc, name, label, module, kwargs=kwargs,
                                   placement=placement)
        try:
            if hasattr(obj, "ViewObject") and obj.ViewObject:
                obj.ViewObject.ShapeColor = color
        except Exception:
            pass

    doc.recompute()
    print("Rebuilt parts:", [label for _, label, *_ in PARTS])
    return doc


if __name__ == "__main__":
    main()
