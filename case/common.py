"""Shared helpers and parameter loading for solaxpico case parts.

Edit this file (and the per-part modules) to change the design, then in
FreeCAD open solaxpico.FCStd and run rebuild.py, or recompute the document
(scripted objects load geometry from these files).
"""

import os
import sys

# Ensure the case directory is importable when FreeCAD opens the document
# from elsewhere (e.g. via double-click).
CASE_DIR = os.path.dirname(os.path.abspath(__file__))
if CASE_DIR not in sys.path:
    sys.path.insert(0, CASE_DIR)

try:
    import FreeCAD as App
    import Part
except Exception:  # allow linting/import outside FreeCAD
    App = None
    Part = None


def get_doc(doc=None):
    if doc is not None:
        return doc
    if App is None:
        return None
    doc = App.ActiveDocument
    if doc is None:
        doc = App.getDocument("solaxpico")
    return doc


def P(sheet, name, default):
    try:
        return float(sheet.get(name))
    except Exception:
        return float(default)


def load_params(doc=None):
    doc = get_doc(doc)
    sheet = doc.getObject("Parameters") if doc else None

    p = {}
    p["PICO_WIDTH"] = P(sheet, "PICO_WIDTH", 51.4)
    p["PICO_DEPTH"] = P(sheet, "PICO_DEPTH", 21.1)
    p["PICO_CLEARANCE"] = P(sheet, "PICO_CLEARANCE", 0.5)
    p["WALL_WIDTH"] = P(sheet, "WALL_WIDTH", 1.0)
    p["POCKET_DEPTH"] = P(sheet, "POCKET_DEPTH", 1.8)
    p["FLOOR_THICKNESS"] = P(sheet, "FLOOR_THICKNESS", 2.2)
    p["BASE_BRIM_HEIGHT"] = P(sheet, "BASE_BRIM_HEIGHT", 1.2)
    p["TRAY_CLEARANCE_XY"] = P(sheet, "TRAY_CLEARANCE_XY", 0.1)
    p["TRAY_WALL"] = P(sheet, "TRAY_WALL", 1.2)
    p["FRAME_RAIL_Z"] = P(sheet, "FRAME_RAIL_Z", 5.0)
    p["FRAME_RAIL_HEIGHT"] = P(sheet, "FRAME_RAIL_HEIGHT", 1.0)
    p["FRAME_RAIL_GAP"] = P(sheet, "FRAME_RAIL_GAP", 20.3)
    p["FRAME_TAB_RAIL_Z"] = P(sheet, "FRAME_TAB_RAIL_Z", 17.0)
    p["FRAME_TAB_RAIL_HEIGHT"] = P(sheet, "FRAME_TAB_RAIL_HEIGHT", 1.0)
    p["FRAME_TAB_RAIL_GAP"] = P(sheet, "FRAME_TAB_RAIL_GAP", 20.3)
    p["FRAME_TAB_WALL_ABOVE"] = P(sheet, "FRAME_TAB_WALL_ABOVE", 6.0)
    p["FRAME_LIP_DEPTH"] = P(sheet, "FRAME_LIP_DEPTH", 3.0)
    p["FRAME_LIP_HEIGHT"] = P(sheet, "FRAME_LIP_HEIGHT", 3.5)
    p["FRAME_LIP_THICKNESS"] = P(sheet, "FRAME_LIP_THICKNESS", 0.6)
    p["FRAME_LIP_CLEARANCE"] = P(sheet, "FRAME_LIP_CLEARANCE", 0.2)
    p["FRAME_LIP_TRAY_GAP"] = P(sheet, "FRAME_LIP_TRAY_GAP", 0.5)
    p["FRAME_LIP_RAIL_GAP"] = P(sheet, "FRAME_LIP_RAIL_GAP", 0.3)
    p["FRAME_END_HOLE_DIAMETER"] = P(sheet, "FRAME_END_HOLE_DIAMETER", 6.0)
    p["BASE_SKIRT_DEPTH"] = P(sheet, "BASE_SKIRT_DEPTH", 5.0)
    p["BASE_SKIRT_WALL"] = P(sheet, "BASE_SKIRT_WALL", 1.2)
    p["BASE_SKIRT_CLEARANCE"] = P(sheet, "BASE_SKIRT_CLEARANCE", 0.15)
    p["LID_PLATE_THICKNESS"] = P(sheet, "LID_PLATE_THICKNESS", 2.0)
    p["LID_SKIRT_DEPTH"] = P(sheet, "LID_SKIRT_DEPTH", 4.0)
    p["LID_SKIRT_WALL"] = P(sheet, "LID_SKIRT_WALL", 1.2)
    p["LID_SKIRT_CLEARANCE"] = P(sheet, "LID_SKIRT_CLEARANCE", 0.15)
    p["TRAY_FLOOR"] = P(sheet, "TRAY_FLOOR", 2.0)

    # constants (kept in sync with pico_specs)
    p.update({
        "CORNER_FILLET_R": 1.0,
        "BASEPLATE_TOP_CHAMFER": 0.5,
        "PICO_HOLE_SPACING_X": 47.0,
        "PICO_HOLE_SPACING_Y": 11.2,
        "POST_BASE_DIAMETER": 2.5,
        "POST_SHAFT_DIAMETER": 1.9,
        "POST_BARB_DIAMETER": 2.1,
        "POST_SLOT_WIDTH": 0.6,
        "POST_BARB_HEIGHT": 2.0,
        "POST_BARB_CHAMFER": 0.4,
        "POST_SLOT_OVERLAP": 0.4,
        "AIRFLOW_SLIT_WIDTH": 2.5,
        "AIRFLOW_BRIDGE_WIDTH": 1.5,
        "USB_NOTCH_WIDTH": 10.0,
        "USB_NOTCH_CLEARANCE": 0.5,
        "FRAME_CATCH_PROTRUSION": 2.0,
        "FRAME_CATCH_LENGTH": 2.5,
        "FRAME_CATCH_CLEARANCE": 0.1,
        "FRAME_CATCH_HEIGHT": 0.6,
        "WALL_FRAME_TOP_CHAMFER": 0.5,
        "TRAY_BRIM_CLEARANCE": 0.1,
        "TRAY_CORNER_R": 2.0,
        "LID_SLIT_MARGIN": 2.0,
        "CONVERTER_LENGTH": 29.9,
        "CONVERTER_WIDTH": 18.2,
        "CONVERTER_CLEARANCE": 0.2,
        "CONVERTER_BALCONY_LENGTH": 15.0,
        "CONVERTER_BALCONY_PROTRUSION": 3.0,
        "CONVERTER_WALL_THICKNESS": 1.2,
        "CONVERTER_WALL_HEIGHT": 5.4,
        "CONVERTER_PCB_HEIGHT": 1.7,
        "CONVERTER_TAB_WIDTH": 0.4,
        "CONVERTER_TAB_DEPTH": 4.0,
        "CONVERTER_TAB_HEIGHT": 1.0,
        "CONV_POCKET_FILLET": 0.5,
        "CABLE_HOLE_DIAMETER_X": 6.0,
        "CABLE_HOLE_DIAMETER_Y": 18.0,
        "MAX485_LENGTH_X": 44.0,
        "MAX485_LENGTH_Y": 15.6,
        "MAX485_CLEARANCE": 0.1,
        "MAX485_TAB_DEPTH": 4.0,
        "MAX485_TAB_WIDTH": 0.4,
        "MAX485_TAB_HEIGHT": 1.0,
        "MAX485_PCB_HEIGHT": 0.8,
        "MAX485_BRIDGE_WIDTH": 2.0,
        "MAX485_BALCONY_LENGTH": 15.0,
        "MAX485_BALCONY_PROTRUSION": 3.0,
    })

    # derived
    p["POCKET_WIDTH"] = p["PICO_WIDTH"] + 2 * p["PICO_CLEARANCE"]
    p["POCKET_LENGTH"] = p["PICO_DEPTH"] + 2 * p["PICO_CLEARANCE"]
    p["BASE_W"] = p["POCKET_WIDTH"] + 2 * p["WALL_WIDTH"]
    p["BASE_D"] = p["POCKET_LENGTH"] + 2 * p["WALL_WIDTH"]
    p["BASE_THICKNESS"] = p["POCKET_DEPTH"] + p["FLOOR_THICKNESS"]
    p["FRAME_INNER_W"] = p["BASE_W"] + 2 * p["TRAY_CLEARANCE_XY"]
    p["FRAME_INNER_D"] = p["BASE_D"] + 2 * p["TRAY_CLEARANCE_XY"]
    p["OUTER_W"] = p["FRAME_INNER_W"] + 2 * p["TRAY_WALL"]
    p["OUTER_D"] = p["FRAME_INNER_D"] + 2 * p["TRAY_WALL"]
    p["OUTER_FILLET"] = p["CORNER_FILLET_R"] + p["TRAY_WALL"]
    p["OUTER_HEIGHT"] = (
        p["FRAME_TAB_RAIL_Z"] + p["FRAME_TAB_RAIL_HEIGHT"] + p["FRAME_TAB_WALL_ABOVE"]
    )
    p["RAIL_WIDTH"] = (p["FRAME_INNER_D"] - p["FRAME_RAIL_GAP"]) / 2
    p["TAB_RAIL_WIDTH"] = (p["FRAME_INNER_D"] - p["FRAME_TAB_RAIL_GAP"]) / 2
    p["RAIL_TOP_Z"] = p["FRAME_RAIL_Z"] + p["FRAME_RAIL_HEIGHT"]
    p["TAB_RAIL_TOP_Z"] = p["FRAME_TAB_RAIL_Z"] + p["FRAME_TAB_RAIL_HEIGHT"]
    p["TRAY_TOP_Z"] = p["RAIL_TOP_Z"] + p["TRAY_FLOOR"]
    p["CATCH_Z_BASE"] = (
        p["RAIL_TOP_Z"] + p["TRAY_FLOOR"] + p["FRAME_CATCH_CLEARANCE"]
    )
    p["TAB_CATCH_Z_BASE"] = (
        p["TAB_RAIL_TOP_Z"] + p["TRAY_FLOOR"] + p["FRAME_CATCH_CLEARANCE"]
    )
    p["TRAY_PLATE_W"] = p["FRAME_INNER_W"] - 2 * p["TRAY_BRIM_CLEARANCE"]
    p["TRAY_PLATE_D"] = p["FRAME_INNER_D"] - 2 * p["TRAY_BRIM_CLEARANCE"]
    return p


def fillet_v_edges(shape, r):
    try:
        edges = [
            e for e in shape.Edges
            if abs(e.Vertexes[0].Point.z - e.Vertexes[1].Point.z) > 0.001
            and abs(e.Vertexes[0].Point.x - e.Vertexes[1].Point.x) < 0.001
            and abs(e.Vertexes[0].Point.y - e.Vertexes[1].Point.y) < 0.001
        ]
        if edges:
            return shape.makeFillet(r, edges)
    except Exception:
        pass
    return shape


def ensure_part(doc, name, label=None):
    obj = doc.getObject(name)
    if obj is None:
        obj = doc.addObject("Part::Feature", name)
    if label:
        obj.Label = label
    return obj
