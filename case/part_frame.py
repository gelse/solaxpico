"""Split wall frame: rails, catches, finger joints, optional end cable hole."""

import FreeCAD as App
import Part

from common import load_params, fillet_v_edges


def make_shape(doc=None, p=None, side="-x", end_hole=False):
    """Build one frame half. side is '-x' or '+x'."""
    if p is None:
        p = load_params(doc)

    frame = _build_full_frame(p)
    return _split_half(frame, p, side, end_hole=end_hole)


def _build_full_frame(p):
    outer = Part.makeBox(
        p["OUTER_W"], p["OUTER_D"], p["OUTER_HEIGHT"],
        App.Vector(-p["OUTER_W"] / 2, -p["OUTER_D"] / 2, 0),
    )
    outer = fillet_v_edges(outer, p["OUTER_FILLET"])
    cavity = Part.makeBox(
        p["FRAME_INNER_W"], p["FRAME_INNER_D"], p["OUTER_HEIGHT"],
        App.Vector(-p["FRAME_INNER_W"] / 2, -p["FRAME_INNER_D"] / 2, 0),
    )
    cavity = fillet_v_edges(cavity, p["CORNER_FILLET_R"])
    frame = outer.cut(cavity)

    try:
        topz = p["OUTER_HEIGHT"]
        edges = [
            e for e in frame.Edges
            if abs(e.Vertexes[0].Point.z - topz) < 0.01
            and abs(e.Vertexes[1].Point.z - topz) < 0.01
            and (abs(abs(e.Vertexes[0].Point.x) - p["OUTER_W"] / 2) < 0.6
                 or abs(abs(e.Vertexes[0].Point.y) - p["OUTER_D"] / 2) < 0.6)
        ]
        if edges:
            frame = frame.makeChamfer(p["WALL_FRAME_TOP_CHAMFER"], edges)
    except Exception:
        pass

    frame = frame.fuse(_rail_pair(p, p["FRAME_RAIL_Z"], p["FRAME_RAIL_HEIGHT"], p["RAIL_WIDTH"]))
    frame = frame.fuse(_rail_pair(p, p["FRAME_TAB_RAIL_Z"], p["FRAME_TAB_RAIL_HEIGHT"], p["TAB_RAIL_WIDTH"]))
    frame = frame.fuse(_catch_quad(p, p["CATCH_Z_BASE"]))
    frame = frame.fuse(_catch_quad(p, p["TAB_CATCH_Z_BASE"]))
    return frame


def _rail_pair(p, z_base, rh, rw):
    y = p["FRAME_INNER_D"] / 2 - rw / 2
    r1 = Part.makeBox(p["FRAME_INNER_W"], rw, rh,
                      App.Vector(-p["FRAME_INNER_W"] / 2, y - rw / 2, z_base))
    r2 = Part.makeBox(p["FRAME_INNER_W"], rw, rh,
                      App.Vector(-p["FRAME_INNER_W"] / 2, -y - rw / 2, z_base))
    return r1.fuse(r2)


def _catch_quad(p, z_base):
    y = p["FRAME_INNER_D"] / 2 - p["FRAME_CATCH_PROTRUSION"] / 2
    x = p["FRAME_INNER_W"] / 2 - p["FRAME_CATCH_LENGTH"] / 2
    res = None
    for sx in (1, -1):
        for sy in (1, -1):
            c = Part.makeBox(
                p["FRAME_CATCH_LENGTH"], p["FRAME_CATCH_PROTRUSION"], p["FRAME_CATCH_HEIGHT"],
                App.Vector(sx * x - p["FRAME_CATCH_LENGTH"] / 2,
                           sy * y - p["FRAME_CATCH_PROTRUSION"] / 2,
                           z_base),
            )
            res = c if res is None else res.fuse(c)
    return res


def _split_half(frame, p, side, end_hole=False):
    sign = -1.0 if side == "-x" else 1.0
    keep = Part.makeBox(
        p["OUTER_W"], p["OUTER_D"] + 2, p["OUTER_HEIGHT"] + 2,
        App.Vector(sign * p["OUTER_W"] / 2 - p["OUTER_W"] / 2,
                   -(p["OUTER_D"] + 2) / 2, -1),
    )
    half = frame.common(keep)

    inner_face_y = p["FRAME_INNER_D"] / 2
    mid_wall_y = inner_face_y + p["FRAME_LIP_THICKNESS"]
    # Double lip thickness to the inside: finger/notch extend inward by one
    # extra FRAME_LIP_THICKNESS (protrudes into cavity) for more stability.
    inner_protrusion = p["FRAME_LIP_THICKNESS"]
    finger_y0 = inner_face_y - inner_protrusion
    finger_y1 = mid_wall_y
    notch_y0 = inner_face_y - inner_protrusion - p["FRAME_LIP_CLEARANCE"]
    notch_y1 = mid_wall_y + p["FRAME_LIP_CLEARANCE"]

    tray_top = p["RAIL_TOP_Z"] + p["TRAY_FLOOR"]
    upper_rail_underside = p["FRAME_TAB_RAIL_Z"]
    lip_z0_lower = tray_top + p["FRAME_LIP_TRAY_GAP"]
    lip_z1_lower = lip_z0_lower + p["FRAME_LIP_HEIGHT"]
    lip_z1_upper = upper_rail_underside - p["FRAME_LIP_RAIL_GAP"]
    lip_z0_upper = lip_z1_upper - p["FRAME_LIP_HEIGHT"]
    bands = {"lower": (lip_z0_lower, lip_z1_lower), "upper": (lip_z0_upper, lip_z1_upper)}
    notch_depth = p["FRAME_LIP_DEPTH"] + p["FRAME_LIP_CLEARANCE"]

    def finger_solid(x_center, depth, z0, z1, outward):
        f = Part.makeBox(depth, finger_y1 - finger_y0, z1 - z0,
                         App.Vector(x_center - depth / 2, finger_y0, z0))
        tip_r = min(p["FRAME_LIP_THICKNESS"], z1 - z0) / 2 - 0.05
        if tip_r > 0.1:
            try:
                selx = (x_center + depth / 2) if outward == "+x" else (x_center - depth / 2)
                edges = [e for e in f.Edges
                         if abs(e.Vertexes[0].Point.x - selx) < 0.01
                         and abs(e.Vertexes[1].Point.x - selx) < 0.01]
                if edges:
                    f = f.makeFillet(tip_r, edges)
            except Exception:
                pass
        return f

    def finger_pair(x_center, depth, z0, z1, outward):
        a = finger_solid(x_center, depth, z0, z1, outward)
        b = a.mirror(App.Vector(0, 0, 0), App.Vector(0, 1, 0))
        return a.fuse(b)

    def notch_pair(x_center, depth, z0, z1):
        n = Part.makeBox(depth, notch_y1 - notch_y0, z1 - z0,
                         App.Vector(x_center - depth / 2, notch_y0, z0))
        m = n.mirror(App.Vector(0, 0, 0), App.Vector(0, 1, 0))
        return n.fuse(m)

    if side == "-x":
        finger_band = bands["lower"]
        notch_band = bands["upper"]
        finger_x = p["FRAME_LIP_DEPTH"] / 2
        finger_out = "+x"
        notch_x = -notch_depth / 2
    else:
        finger_band = bands["upper"]
        notch_band = bands["lower"]
        finger_x = -p["FRAME_LIP_DEPTH"] / 2
        finger_out = "-x"
        notch_x = notch_depth / 2

    half = half.cut(notch_pair(notch_x, notch_depth, *notch_band))
    half = half.fuse(finger_pair(finger_x, p["FRAME_LIP_DEPTH"], *finger_band, finger_out))

    if end_hole:
        end_hole_z = p["OUTER_HEIGHT"] / 2
        hole = Part.makeCylinder(
            p["FRAME_END_HOLE_DIAMETER"] / 2, 2 * p["OUTER_W"],
            App.Vector(-p["OUTER_W"], 0, end_hole_z), App.Vector(1, 0, 0),
        )
        half = half.cut(hole)

    return half
