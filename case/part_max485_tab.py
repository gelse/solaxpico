"""MAX485 transceiver snap-fit tab."""

import FreeCAD as App
import Part

from common import load_params, fillet_v_edges


def make_shape(doc=None, p=None):
    if p is None:
        p = load_params(doc)

    tw = p["TRAY_PLATE_W"]
    td = p["TRAY_PLATE_D"]
    tf = p["TRAY_FLOOR"]

    tab = Part.makeBox(tw, td, tf, App.Vector(-tw / 2, -td / 2, 0))
    tab = fillet_v_edges(tab, p["TRAY_CORNER_R"])

    pocket_x = p["MAX485_LENGTH_X"] + 2 * p["MAX485_CLEARANCE"]
    pocket_y = p["MAX485_LENGTH_Y"] + 2 * p["MAX485_CLEARANCE"]
    hole = Part.makeBox(pocket_x, pocket_y, tf + 0.2,
                        App.Vector(-pocket_x / 2, -pocket_y / 2, -0.1))
    tab = tab.cut(hole)

    tab_z_base = tf + p["MAX485_PCB_HEIGHT"] + p["MAX485_CLEARANCE"]
    wall_h = tab_z_base + p["MAX485_TAB_HEIGHT"] - tf
    wt = p["CONVERTER_WALL_THICKNESS"]

    wall1 = Part.makeBox(pocket_x, wt, wall_h,
                         App.Vector(-pocket_x / 2, pocket_y / 2, tf))
    wall2 = Part.makeBox(pocket_x, wt, wall_h,
                         App.Vector(-pocket_x / 2, -pocket_y / 2 - wt, tf))
    tab = tab.fuse(wall1).fuse(wall2)

    # snap tabs
    tdpth = p["MAX485_TAB_DEPTH"]
    twd = p["MAX485_TAB_WIDTH"]
    th = p["MAX485_TAB_HEIGHT"]
    t1 = Part.makeBox(tdpth, twd, th,
                      App.Vector(-tdpth / 2, pocket_y / 2 - twd, tab_z_base))
    t2 = Part.makeBox(tdpth, twd, th,
                      App.Vector(-tdpth / 2, -pocket_y / 2, tab_z_base))
    tab = tab.fuse(t1).fuse(t2)

    return tab
