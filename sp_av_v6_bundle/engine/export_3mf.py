#!/usr/bin/env python3
"""
export_3mf.py — write a plated, core-spec 3MF.

WHAT 3MF IS
-----------
A 3MF is a ZIP archive of XML. Minimum viable contents:
    [Content_Types].xml   what each file extension means
    _rels/.rels           points the package at the model
    3D/3dmodel.model      the geometry, in millimetres

Why it beats STL for a plate: STL is one anonymous soup of triangles with no
units and no object boundaries, so a plate of ten parts arrives as one blob the
slicer cannot tell apart. 3MF carries NAMED objects, each with its own transform,
in one file. That is the whole reason this is the handoff format.

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
Plate assignment and print-sequence flags are VENDOR EXTENSIONS. Creality Print,
OrcaSlicer and Bambu Studio each store them differently and none of it is in the
core spec. Writing a guess at Creality's namespace would produce a file that
looks right and imports wrong, which is worse than a file that is honestly plain.
So: clean core 3MF, one file per plate, and you tick "print by object" in the
slicer yourself.
"""
from __future__ import annotations

import os
import zipfile

CT_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
    'relationships+xml"/>'
    '<Default Extension="model" ContentType="application/vnd.ms-package.'
    '3dmanufacturing-3dmodel+xml"/>'
    '</Types>'
)
RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
    'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
    '</Relationships>'
)
NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def write_3mf(path, objects, title="plate"):
    """objects: [(name, trimesh.Trimesh)] already positioned on the bed.

    Geometry is BAKED into vertex coordinates and every build item carries the
    identity transform. Baking costs nothing here and removes a whole class of
    row-major/column-major bug at the one point in the pipeline where a silent
    transform error turns into a crashed print.
    """
    out = ['<?xml version="1.0" encoding="UTF-8"?>\n',
           f'<model unit="millimeter" xml:lang="en-US" xmlns="{NS}">',
           '<metadata name="Application">SP assembly-viewer engine v2</metadata>',
           f'<metadata name="Title">{_esc(title)}</metadata>',
           '<resources>']
    items = []
    for oid, (name, mesh) in enumerate(objects, start=1):
        out.append(f'<object id="{oid}" type="model" name="{_esc(name)}"><mesh><vertices>')
        for x, y, z in mesh.vertices:
            out.append(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>')
        out.append('</vertices><triangles>')
        for a, b, c in mesh.faces:
            out.append(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>')
        out.append('</triangles></mesh></object>')
        items.append(f'<item objectid="{oid}"/>')
    out.append('</resources><build>')
    out.extend(items)
    out.append('</build></model>')
    model = "".join(out).encode("utf-8")

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr("[Content_Types].xml", CT_XML)
        z.writestr("_rels/.rels", RELS_XML)
        z.writestr("3D/3dmodel.model", model)
    return os.path.getsize(path)


# ---------------------------------------------------------------------------
def verify_3mf(path):
    """Reopen what we just wrote and report object count + bounding boxes.
    A writer that is never read back is a writer that is wrong."""
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        missing = {"[Content_Types].xml", "_rels/.rels",
                   "3D/3dmodel.model"} - names
        if missing:
            raise AssertionError(f"3MF missing required parts: {missing}")
        root = ET.fromstring(z.read("3D/3dmodel.model"))
    if root.get("unit") != "millimeter":
        raise AssertionError("3MF unit is not millimeter")
    ns = {"m": NS}
    objs = []
    for o in root.findall(".//m:object", ns):
        vs = o.findall(".//m:vertex", ns)
        ts = o.findall(".//m:triangle", ns)
        xs = [float(v.get("x")) for v in vs]
        ys = [float(v.get("y")) for v in vs]
        zs = [float(v.get("z")) for v in vs]
        objs.append({
            "id": o.get("id"), "name": o.get("name"),
            "vertices": len(vs), "triangles": len(ts),
            "min": [min(xs), min(ys), min(zs)],
            "max": [max(xs), max(ys), max(zs)],
        })
    items = len(root.findall(".//m:item", ns))
    return {"objects": objs, "items": items}


# ---------------------------------------------------------------------------
def audit_plates(files, bed_x, bed_y, bed_z, combined_suffix="_plates.3mf",
                 plate_pitch_y=None):
    """Reopen every 3MF we wrote and prove it against the build volume.

    A writer nobody reads back is a writer that is wrong, and a plate file that
    quietly puts a part 3 mm off the bed edge does not announce itself until the
    nozzle is already moving. Returns (ok, lines).

    In the combined file each plate is offset along +Y so the plates do not sit
    on top of each other; that offset is undone here before the bed check, or
    every plate past the first would false-positive.
    """
    pitch = plate_pitch_y if plate_pitch_y is not None else (bed_y + 40.0)
    ok, lines, total = True, [], 0
    for f in files:
        combined = f.endswith(combined_suffix)
        v = verify_3mf(f)
        per = {}
        for o in v["objects"]:
            try:
                pl = int(o["name"].split("_")[0].replace("plate", ""))
            except ValueError:
                pl = 1
            shift = (pl - 1) * pitch if combined else 0.0
            mn = [o["min"][0], o["min"][1] - shift, o["min"][2]]
            mx = [o["max"][0], o["max"][1] - shift, o["max"][2]]
            inside = (-bed_x / 2 - .01 <= mn[0] and mx[0] <= bed_x / 2 + .01 and
                      -bed_y / 2 - .01 <= mn[1] and mx[1] <= bed_y / 2 + .01 and
                      mn[2] >= -.01 and mx[2] <= bed_z + .01)
            if not inside:
                ok = False
                lines.append(f"  OUT OF BED  {f}  {o['name']}  {mn} {mx}")
            per.setdefault(pl, []).append((o["name"], mn, mx))
        overlaps = 0
        for bs in per.values():
            for i in range(len(bs)):
                for j in range(i + 1, len(bs)):
                    n1, a1, b1 = bs[i]
                    n2, a2, b2 = bs[j]
                    gap = max(max(a1[0], a2[0]) - min(b1[0], b2[0]),
                              max(a1[1], a2[1]) - min(b1[1], b2[1]))
                    if gap < -0.01:
                        overlaps += 1
                        ok = False
                        lines.append(f"  OVERLAP  {f}  {n1} / {n2}")
        if not combined:
            total += len(v["objects"])
        lines.append(f"  {f.split('/')[-1]:38s} {len(v['objects']):3d} obj  "
                     f"{v['items']:3d} items  overlaps={overlaps}"
                     f"{'  (combined)' if combined else ''}")
    lines.append(f"  objects across per-plate files: {total}")
    return ok, lines
