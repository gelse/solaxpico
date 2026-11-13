"""Baseplate part: skirted base, Pico pocket, posts, slits, USB notch."""

import FreeCAD as App
import Part

from common import load_params, fillet_v_edges


def make_shape(doc=None, p=None):
    if p is None:
        p = load_params(doc)

    # Skirt dims
    scw = p["OUTER_W"] + 2 * p["BASE_SKIRT_CLEARANCE"]
    scd = p["OUTER_D"] + 2 * p["BASE_SKIRT_CLEARANCE"]
    sow = scw + 2 * p["BASE_SKIRT_WALL"]
    sod = scd + 2 * p["BASE_SKIRT_WALL"]
    scf = p["OUTER_FILLET"] + p["BASE_SKIRT_CLEARANCE"]
    sof = scf + p["BASE_SKIRT_WALL"]
    skirt_top_z = p["BASE_BRIM_HEIGHT"] + p["BASE_SKIRT_DEPTH"]

    base = Part.makeBox(sow, sod, skirt_top_z, App.Vector(-sow / 2, -sod / 2, 0))
    skirt_cav = Part.makeBox(
        scw, scd, p["BASE_SKIRT_DEPTH"],
        App.Vector(-scw / 2, -scd / 2, p["BASE_BRIM_HEIGHT"]),
    )
    base = fillet_v_edges(base, sof)
    skirt_cav = fillet_v_edges(skirt_cav, scf)
    result = base.cut(skirt_cav)

    # chamfer skirt top outer edges
    try:
        topz = skirt_top_z
        edges = [
            e for e in result.Edges
            if abs(e.Vertexes[0].Point.z - topz) < 0.01
            and abs(e.Vertexes[1].Point.z - topz) < 0.01
            and (abs(abs(e.Vertexes[0].Point.x) - sow / 2) < 0.6
                 or abs(abs(e.Vertexes[0].Point.y) - sod / 2) < 0.6)
        ]
        if edges:
            result = result.makeChamfer(p["BASEPLATE_TOP_CHAMFER"], edges)
    except Exception:
        pass

    body = Part.makeBox(
        p["BASE_W"], p["BASE_D"], p["BASE_THICKNESS"],
        App.Vector(-p["BASE_W"] / 2, -p["BASE_D"] / 2, 0),
    )
    body = fillet_v_edges(body, p["CORNER_FILLET_R"])
    result = result.fuse(body)

    # pocket
    pocket = Part.makeBox(
        p["POCKET_WIDTH"], p["POCKET_LENGTH"], p["POCKET_DEPTH"],
        App.Vector(-p["POCKET_WIDTH"] / 2, -p["POCKET_LENGTH"] / 2,
                   p["BASE_THICKNESS"] - p["POCKET_DEPTH"]),
    )
    pocket = fillet_v_edges(pocket, p["CORNER_FILLET_R"])
    result = result.cut(pocket)

    # USB notch
    nd = p["WALL_WIDTH"] + p["USB_NOTCH_CLEARANCE"]
    notch = Part.makeBox(
        nd, p["USB_NOTCH_WIDTH"], p["POCKET_DEPTH"],
        App.Vector(p["PICO_WIDTH"] / 2 + p["PICO_CLEARANCE"],
                   -p["USB_NOTCH_WIDTH"] / 2,
                   p["BASE_THICKNESS"] - p["POCKET_DEPTH"]),
    )
    result = result.cut(notch)

    # airflow slits
    slit_w = p["AIRFLOW_SLIT_WIDTH"]
    bridge = p["AIRFLOW_BRIDGE_WIDTH"]
    margin = bridge / 3.0
    slit_len = (p["PICO_HOLE_SPACING_X"] - p["POST_BASE_DIAMETER"]
                - 2 * margin - slit_w)
    pitch = slit_w + bridge
    count = int((p["POCKET_LENGTH"] + bridge / 3) // pitch)
    start_y = -(count - 1) / 2.0 * pitch
    for i in range(count):
        y = start_y + i * pitch
        cx1 = -slit_len / 2 + slit_w / 2
        cx2 = slit_len / 2 - slit_w / 2
        s = Part.makeBox(max(slit_len - slit_w, 0.1), slit_w,
                         p["FLOOR_THICKNESS"],
                         App.Vector(cx1, y - slit_w / 2, 0))
        c1 = Part.makeCylinder(slit_w / 2, p["FLOOR_THICKNESS"],
                               App.Vector(cx1, y, 0), App.Vector(0, 0, 1))
        c2 = Part.makeCylinder(slit_w / 2, p["FLOOR_THICKNESS"],
                               App.Vector(cx2, y, 0), App.Vector(0, 0, 1))
        result = result.cut(s.fuse(c1).fuse(c2))

    # snap posts
    post = _make_post(p)
    pz = p["BASE_THICKNESS"] - p["POCKET_DEPTH"]
    for dx, dy in [
        (p["PICO_HOLE_SPACING_X"] / 2, p["PICO_HOLE_SPACING_Y"] / 2),
        (p["PICO_HOLE_SPACING_X"] / 2, -p["PICO_HOLE_SPACING_Y"] / 2),
        (-p["PICO_HOLE_SPACING_X"] / 2, p["PICO_HOLE_SPACING_Y"] / 2),
        (-p["PICO_HOLE_SPACING_X"] / 2, -p["PICO_HOLE_SPACING_Y"] / 2),
    ]:
        pp = post.copy()
        pp.translate(App.Vector(dx, dy, pz))
        result = result.fuse(pp)

    return result


def _make_post(p):
    base_h = 0.5
    shaft_h = 0.9
    barb_h = p["POST_BARB_HEIGHT"]
    post = Part.makeCylinder(p["POST_BASE_DIAMETER"] / 2, base_h)
    post = post.fuse(Part.makeCylinder(
        p["POST_SHAFT_DIAMETER"] / 2, shaft_h,
        App.Vector(0, 0, base_h), App.Vector(0, 0, 1)))
    barb_z = base_h + shaft_h
    barb = Part.makeCylinder(
        p["POST_BARB_DIAMETER"] / 2, barb_h,
        App.Vector(0, 0, barb_z), App.Vector(0, 0, 1))
    post = post.fuse(barb)
    try:
        top = barb_z + barb_h
        edges = [e for e in post.Edges
                 if abs(e.Vertexes[0].Point.z - top) < 0.01
                 and abs(e.Vertexes[1].Point.z - top) < 0.01]
        if edges:
            post = post.makeChamfer(p["POST_BARB_CHAMFER"], edges)
    except Exception:
        pass
    slot = Part.makeBox(
        p["POST_SLOT_WIDTH"],
        p["POST_BARB_DIAMETER"] + p["POST_SLOT_OVERLAP"],
        barb_h + 0.02,
        App.Vector(-p["POST_SLOT_WIDTH"] / 2,
                   -(p["POST_BARB_DIAMETER"] + p["POST_SLOT_OVERLAP"]) / 2,
                   barb_z - 0.01),
    )
    post = post.cut(slot)
    return post
