"""Generic scripted-part proxy used by solaxpico.FCStd.

Each part object stores a `Module` property (e.g. 'part_baseplate') and
rebuilds its Shape by calling <module>.make_shape(doc) on execute.
This keeps geometry logic in external, version-controlled .py files.
"""

import os
import sys

import FreeCAD as App

CASE_DIR = os.path.dirname(os.path.abspath(__file__))
if CASE_DIR not in sys.path:
    sys.path.insert(0, CASE_DIR)


class ScriptedPart:
    def __init__(self, obj, module_name, kwargs=None):
        obj.Proxy = self
        self.ModuleName = module_name
        self.Kwargs = kwargs or {}
        if not hasattr(obj, "SourceModule"):
            obj.addProperty("App::PropertyString", "SourceModule", "Source",
                            "Python module that builds this part's shape")
        obj.SourceModule = module_name
        if kwargs:
            if not hasattr(obj, "SourceArgs"):
                obj.addProperty("App::PropertyString", "SourceArgs", "Source",
                                "Optional comma-separated key=value args for builder")
            obj.SourceArgs = ",".join(f"{k}={v}" for k, v in kwargs.items())

    def execute(self, obj):
        _ensure_path(obj)
        import importlib
        modname = getattr(obj, "SourceModule", None) or getattr(self, "ModuleName", None)
        if not modname:
            return
        mod = importlib.import_module(modname)
        importlib.reload(mod)
        kwargs = dict(getattr(self, "Kwargs", {}) or {})
        # parse SourceArgs if present (overrides/extends stored kwargs)
        sargs = getattr(obj, "SourceArgs", "") or ""
        if sargs:
            for part in sargs.split(","):
                if "=" in part:
                    k, v = part.split("=", 1)
                    kwargs[k.strip()] = _coerce(v.strip())
        doc = obj.Document
        obj.Shape = mod.make_shape(doc, **kwargs)


def _coerce(val):
    if isinstance(val, str):
        low = val.lower()
        if low == "true":
            return True
        if low == "false":
            return False
        try:
            if "." in val:
                return float(val)
            return int(val)
        except Exception:
            return val
    return val

    def onChanged(self, obj, prop):
        # recompute when source changes
        if prop in ("SourceModule", "SourceArgs"):
            pass

    def __getstate__(self):
        return {"ModuleName": getattr(self, "ModuleName", None),
                "Kwargs": getattr(self, "Kwargs", {})}

    def __setstate__(self, state):
        if isinstance(state, dict):
            self.ModuleName = state.get("ModuleName")
            self.Kwargs = state.get("Kwargs", {})
        else:
            self.ModuleName = None
            self.Kwargs = {}


class ViewProviderScriptedPart:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        self.ViewObject = vobj

    def getDisplayModes(self, vobj):
        return ["Flat Lines", "Shaded"]

    def getDefaultDisplayMode(self):
        return "Flat Lines"

    def setDisplayMode(self, mode):
        return mode

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


def _ensure_path(obj=None):
    # try document directory and this file's directory
    dirs = [CASE_DIR]
    try:
        if obj and obj.Document and obj.Document.FileName:
            dirs.append(os.path.dirname(obj.Document.FileName))
    except Exception:
        pass
    try:
        if App.ActiveDocument and App.ActiveDocument.FileName:
            dirs.append(os.path.dirname(App.ActiveDocument.FileName))
    except Exception:
        pass
    for d in dirs:
        if d and d not in sys.path:
            sys.path.insert(0, d)


def create(doc, name, label, module_name, kwargs=None, placement=None):
    """Create or update a scripted part object."""
    _ensure_path()
    obj = doc.getObject(name)
    if obj is None or obj.TypeId != "Part::FeaturePython":
        # replace if wrong type
        if obj is not None:
            old_place = obj.Placement
            doc.removeObject(name)
        else:
            old_place = None
        obj = doc.addObject("Part::FeaturePython", name)
        if old_place is not None and placement is None:
            placement = old_place
    ScriptedPart(obj, module_name, kwargs=kwargs)
    if App.GuiUp:
        ViewProviderScriptedPart(obj.ViewObject)
    obj.Label = label
    if placement is not None:
        obj.Placement = placement
    return obj
