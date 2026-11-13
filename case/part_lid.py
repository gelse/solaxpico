"""Lid: clamping skirt and ventilated plate."""

import FreeCAD as App
import Part

from common import load_params, fillet_v_edges


def make_shape(doc=None, p=None):
    if p is None:
        p = load_params(doc)

    scw = p["OUTER_W"] + 2 * p["LID_SKIRT_CLEARANCE"]
    scd = p["OUTER_D"] + 2 * p["LID_SKIRT_CLEARANCE"]
    sow = scw + 2 * p["LID_SKIRT_WALL"]
    sod = scd + 2 * p["LID_SKIRT_WALL"]
    scf = p["OUTER_FILLET"] + p["LID_SKIRT_CLEARANCE"]
    sof = scf + p["LID_SKIRT_WALL"]

    skirt = Part.makeBox(sow, sod, p["LID_SKIRT_DEPTH"],
                         App.Vector(-sow / 2, -sod / 2, 0))
    skirt_cav = Part.makeBox(scw, scd, p["LID_SKIRT_DEPTH"],
                             App.Vector(-scw / 2, -scd / 2, 0))
    skirt = fillet_v_edges(skirt, sof)
    skirt_cav = fillet_v_edges(skirt_cav, scf)
    lid = skirt.cut(skirt_cav)

    plate = Part.makeBox(sow, sod, p["LID_PLATE_THICKNESS"],
                         App.Vector(-sow / 2, -sod / 2, p["LID_SKIRT_DEPTH"]))
    plate = fillet_v_edges(plate, sof)
    lid = lid.fuse(plate)

    try:
        topz = p["LID_SKIRT_DEPTH"] + p["LID_PLATE_THICKNESS"]
        edges = [
            e for e in lid.Edges
            if abs(e.Vertexes[0].Point.z - topz) < 0.01
            and abs(e.Vertexes[1].Point.z - topz) < 0.01
            and (abs(abs(e.Vertexes[0].Point.x) - sow / 2) < 0.5
                 or abs(abs(e.Vertexes[0].Point.y) - sod / 2) < 0.5)
        ]
        if edges:
            lid = lid.makeChamfer(p["WALL_FRAME_TOP_CHAMFER"], edges)
    except Exception:
        pass

    # ventilation slits
    slit_w = p["AIRFLOW_SLIT_WIDTH"]
    slit_len = scw - 2 * p["LID_SLIT_MARGIN"]
    slit_field = scd - 2 * p["LID_SLIT_MARGIN"]
    pitch = slit_w + p["AIRFLOW_BRIDGE_WIDTH"]
    if pitch > 0:
        count = int(slit_field // pitch)
        start_y = -(count - 1) / 2.0 * pitch
        for i in range(count):
            y = start_y + i * pitch
            cx1 = -slit_len / 2 + slit_w / 2
            cx2 = slit_len / 2 - slit_w / 2
            s = Part.makeBox(max(slit_len - slit_w, 0.1), slit_w,
                             p["LID_PLATE_THICKNESS"] + 0.2,
                             App.Vector(cx1, y - slit_w / 2,
                                        p["LID_SKIRT_DEPTH"] - 0.1))
            c1 = Part.makeCylinder(slit_w / 2, p["LID_PLATE_THICKNESS"] + 0.2,
                                   App.Vector(cx1, y, p["LID_SKIRT_DEPTH"] - 0.1),
                                   App.Vector(0, 0, 1))
            c2 = Part.makeCylinder(slit_w / 2, p["LID_PLATE_THICKNESS"] + 0.2,
                                   App.Vector(cx2, y, p["LID_SKIRT_DEPTH"] - 0.1),
                                   App.Vector(0, 0, 1))
            lid = lid.cut(s.fuse(c1).fuse(c2))

    return lid
