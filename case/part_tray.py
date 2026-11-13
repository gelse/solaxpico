"""Converter snap-fit tray."""

import FreeCAD as App
import Part

from common import load_params, fillet_v_edges


def make_shape(doc=None, p=None):
    if p is None:
        p = load_params(doc)

    tw = p["TRAY_PLATE_W"]
    td = p["TRAY_PLATE_D"]
    tf = p["TRAY_FLOOR"]

    tray = Part.makeBox(tw, td, tf, App.Vector(-tw / 2, -td / 2, 0))
    tray = fillet_v_edges(tray, p["TRAY_CORNER_R"])

    # converter pocket (I-like simplified as through pocket + walls above)
    cpl = p["CONVERTER_LENGTH"] + 2 * p["CONVERTER_CLEARANCE"]
    cpw = p["CONVERTER_WIDTH"] + 2 * p["CONVERTER_CLEARANCE"]
    pocket = Part.makeBox(cpl, cpw, tf + 0.2,
                          App.Vector(-cpl / 2, -cpw / 2, -0.1))
    tray = tray.cut(pocket)

    # cable holes (rectangular approximations on +/-X)
    wall_outer_x = cpl / 2 + p["CONVERTER_WALL_THICKNESS"]
    hc = wall_outer_x + (tw / 2 - wall_outer_x) / 2
    hx = p["CABLE_HOLE_DIAMETER_X"]
    hy = p["CABLE_HOLE_DIAMETER_Y"]
    for sx in (1, -1):
        hole = Part.makeBox(hx, hy, tf + 0.2,
                            App.Vector(sx * hc - hx / 2, -hy / 2, -0.1))
        tray = tray.cut(hole)

    # snap walls
    wh = p["CONVERTER_WALL_HEIGHT"]
    wt = p["CONVERTER_WALL_THICKNESS"]
    wall_x_pos = Part.makeBox(cpl, wt, wh, App.Vector(-cpl / 2, cpw / 2, tf))
    wall_x_neg = Part.makeBox(cpl, wt, wh, App.Vector(-cpl / 2, -cpw / 2 - wt, tf))
    wall_y_pos = Part.makeBox(wt, cpw, wh, App.Vector(cpl / 2, -cpw / 2, tf))
    wall_y_neg = Part.makeBox(wt, cpw, wh, App.Vector(-cpl / 2 - wt, -cpw / 2, tf))
    tray = tray.fuse(wall_x_pos).fuse(wall_x_neg).fuse(wall_y_pos).fuse(wall_y_neg)

    # snap tabs on short (Y) walls, inward
    tab_w = p["CONVERTER_TAB_WIDTH"]
    tab_d = p["CONVERTER_TAB_DEPTH"]
    tab_h = p["CONVERTER_TAB_HEIGHT"]
    tab_z = tf + p["CONVERTER_PCB_HEIGHT"]
    # tabs protrude inward (-x from +Y wall outer face? inward means toward pocket center)
    for sx in (1, -1):
        # on +x end wall, inward is -x; on -x end wall inward is +x
        if sx == 1:
            tx = cpl / 2 - tab_w
        else:
            tx = -cpl / 2
        t = Part.makeBox(tab_w, tab_d, tab_h,
                         App.Vector(tx, -tab_d / 2, tab_z))
        tray = tray.fuse(t)

    return tray
