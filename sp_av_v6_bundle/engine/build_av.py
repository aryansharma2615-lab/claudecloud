#!/usr/bin/env python3
"""
build_av.py — config JSON (+ STLs) -> one self-contained HTML assembly viewer,
              plus the plated 3MF that goes with it.

    python3 build_av.py path/to/av_config.json

Everything project-specific lives in the config. If shipping a new product needs
an edit to viewer_template.html, the schema is missing a field — add the field.
See CONFIG_SCHEMA.md.
"""
from __future__ import annotations

import base64
import json
import math
import os
import sys
import datetime

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import av_geom as G                                     # noqa: E402
import av_pack as PK                                    # noqa: E402
import export_3mf as X3                                 # noqa: E402

TEMPLATE = os.path.join(HERE, "viewer_template.html")

# Fallbacks only. A real config states its own machine.
# Fallbacks only. A real config states its own machine.
# `sequential` = the machine prints one object to full height before the next.
# The SP Ender 3 S1 Pro does NOT; Creality Print slices the plate as one job.
# Leave it false and the gantry/skirt hazard audit never runs.
DEF_BED = {"name": "Creality Ender 3 S1 Pro", "x": 220.0, "y": 220.0, "z": 270.0,
           "gap": 8.0, "margin": 5.0, "nozzle": 0.4, "sequential": False,
           "gantry": None, "skirt": None}


# ---------------------------------------------------------------------------
def normalise_sp(cfg):
    """Accept the config shape documented in /sp-assembly-viewer verbatim.

    That standard specifies per-part `fasteners`, per-part `bom`, and
    `print.supports` as a boolean. The engine's own richer shape (a top-level
    `fasteners` array so a callout can be gated by build step, and a `cost`
    object with provenance fields) is a SUPERSET, not a replacement — so this
    translates the documented shape up rather than making a project choose.
    Write either; both build.
    """
    fasteners = list(cfg.get("fasteners", []))
    for p in cfg.get("parts", []):
        pr = p.get("print")
        if isinstance(pr, dict) and "supports" in pr:
            # bool -> the string the inspector renders
            sup = pr.pop("supports")
            pr.setdefault("support", ("required" if sup else "none"))

        # per-part fasteners -> top-level, back-referenced to this part
        for i, f in enumerate(p.pop("fasteners", []) or []):
            spec = f.get("spec") or f.get("label") or "fastener"
            fasteners.append({
                "id": f.get("id", f"{p['id']}_f{i}"),
                "label": f.get("label", spec),
                "spec": f.get("spec", spec),
                "qty": f.get("qty", 1),
                "at": f.get("at", [0, 0, 0]),
                "part": f.get("part", p["id"]),
                "step": f.get("step", p.get("step")),
                "note": f.get("note", ""),
                "gid": f.get("gid", spec),
            })

        # per-part bom {qty, cost, link, bulk} -> qty + cost{each, url, bulk}
        bom = p.get("bom")
        if isinstance(bom, dict):
            p["qty"] = bom.get("qty", p.get("qty", 1))
            if bom.get("cost") is not None and not p.get("cost"):
                p["cost"] = {
                    "each": bom["cost"],
                    "url": bom.get("link"),
                    "supplier": bom.get("supplier"),
                    "bulk": {str(k): v for k, v in (bom.get("bulk") or {}).items()},
                    "est": bom.get("est", False),
                    "checked": bom.get("checked"),
                    "formula": bom.get("formula"),
                }
            p.pop("bom")            # a dict here would read as the bom:false flag

    # An SP fastener may carry qty 4 at one point instead of four points. Split
    # it so each bolt gets its own callout, which is what feature 7 asks for.
    expanded = []
    for f in fasteners:
        n = int(f.get("qty", 1) or 1)
        if n > 1 and f.get("split", True) and isinstance(f.get("at"), list)                 and f["at"] and isinstance(f["at"][0], list):
            for k, at in enumerate(f["at"]):          # at = [[x,y,z], ...]
                g = dict(f, id=f"{f['id']}_{k}", at=at, qty=1)
                expanded.append(g)
        else:
            expanded.append(f)
    cfg["fasteners"] = expanded
    return cfg


def _steps(cfg):
    """Accept both the v1 shape  [[n, title, body], ...]  and the v2 dict shape."""
    out = []
    for s in cfg.get("steps", []):
        if isinstance(s, (list, tuple)):
            out.append({"n": s[0], "title": s[1], "caption": s[2]})
        else:
            out.append({"n": s["n"], "title": s["title"],
                        "caption": s.get("caption", ""),
                        "tool": s.get("tool"), "spec": s.get("spec"),
                        "time": s.get("time")})
    return out


# ---------------------------------------------------------------------------
# WIRE TABLE — AWG is a real standard, so these are looked-up constants, not
# estimates. Conductor diameter and DC resistance are from the AWG definition
# (d = 0.127 mm x 92^((36-n)/39)); the chassis figure is the conventional
# single-conductor-in-free-air rating, the power figure the conservative
# bundled/power-transmission rating.
AWG = {
    16: {"d": 1.291, "ohm_m": 0.01318, "chassis": 22.0, "power": 3.7},
    18: {"d": 1.024, "ohm_m": 0.02095, "chassis": 16.0, "power": 2.3},
    20: {"d": 0.812, "ohm_m": 0.03331, "chassis": 11.0, "power": 1.5},
    22: {"d": 0.644, "ohm_m": 0.05300, "chassis": 7.0,  "power": 0.92},
    24: {"d": 0.511, "ohm_m": 0.08422, "chassis": 3.5,  "power": 0.577},
    26: {"d": 0.405, "ohm_m": 0.13390, "chassis": 2.2,  "power": 0.361},
}
INSULATION_MM = 0.7          # thin-wall PVC, added to conductor diameter


def wire_facts(run, volts):
    """Gauge -> real radius, resistance, drop, and whether it is undersized.

    The run is drawn at its ACTUAL insulated diameter. A wire exaggerated for
    visibility is a wire that fits through a 6 mm gland on screen and not on
    the bench.
    """
    g = int(str(run.get("gauge", "24")).split()[0])
    a = AWG.get(g, AWG[24])
    length_m = run["_len"] / 1000.0
    amps = float(run.get("amps", 0) or 0)
    ohms = a["ohm_m"] * length_m
    drop = ohms * amps
    return {
        "awg": g,
        "radius": (a["d"] + INSULATION_MM) / 2.0,
        "length_mm": round(run["_len"], 1),
        "amps": amps,
        "ohms": round(ohms, 4),
        "drop_v": round(drop, 3),
        "drop_pct": round(100.0 * drop / volts, 2) if volts else None,
        "chassis_a": a["chassis"],
        "undersized": bool(amps and amps > a["chassis"]),
    }


def build_wiring(cfg, log):
    """Config `wiring` block -> tube meshes + per-run electrical facts.

    Wires are packed into the SAME int16 vertex buffer as every other part and
    carry kind:"wire", so picking, ghosting, isolate and section all work on
    them for free. They are excluded from the parts list, the BOM plate logic
    and the bed packer by that kind.
    """
    w = cfg.get("wiring")
    if not w or not w.get("runs"):
        return None, []
    volts = float(w.get("volts", 12))
    meshes, runs = [], []
    for r in w["runs"]:
        path = r["path"]
        r["_len"] = G.polyline_length(path)
        f = wire_facts(r, volts)
        mesh = G.tube(path, radius=f["radius"], sections=8)
        pid = "wire_" + r["id"]
        meshes.append((pid, mesh))
        runs.append({**{k: v for k, v in r.items() if not k.startswith("_")},
                     "part": pid, **f})
    log(f"wiring:  {len(runs)} runs, "
        f"{sum(x['length_mm'] for x in runs)/1000:.2f} m of wire, "
        f"{sum(len(m.faces) for _, m in meshes):,} triangles")
    for x in runs:
        if x["undersized"]:
            log(f"  UNDERSIZED: {x['id']} carries {x['amps']} A on "
                f"{x['awg']} AWG (chassis rating {x['chassis_a']} A)")
    return {"nodes": w.get("nodes", []), "runs": runs, "volts": volts,
            "note": w.get("note", "")}, meshes


def printed_facts(part, facts, mats, bed):
    """Grams and minutes for a printed part. Density is physics and geometry is
    measured, so these exist whether or not anybody has priced the filament —
    the plate view needs them even when the BOM line says TBD."""
    mat = mats.get(part.get("material", ""), None)
    if not mat:
        return None
    pr = part.setdefault("print", {})
    dens = mat["density"]                                # g/cm3
    v_cm3 = facts["volume_mm3"] / 1000.0
    if v_cm3 <= 0:
        return None

    if pr.get("grams"):
        grams, how = float(pr["grams"]), f"{float(pr['grams']):.0f} g from the sliced estimate"
    else:
        walls = pr.get("walls", 3)
        t_cm = walls * bed["nozzle"] / 10.0
        area_cm2 = facts.get("area_mm2", 0.0) / 100.0
        v_shell = min(v_cm3, area_cm2 * t_cm)
        infill = pr.get("infill", 20) / 100.0
        v_mat = v_shell + (v_cm3 - v_shell) * infill
        grams = v_mat * dens
        how = (f"shell {v_shell:.1f} cm³ ({walls}×{bed['nozzle']} mm walls over "
               f"{area_cm2:.0f} cm² surface) + {pr.get('infill',20)}% of the "
               f"{v_cm3 - v_shell:.1f} cm³ interior = {v_mat:.1f} cm³ × "
               f"{dens} g/cm³ = {grams:.0f} g")
    if pr.get("time_min"):
        mins, tsrc = float(pr["time_min"]), "sliced"
    else:
        flow = bed.get("flow_mm3s", 8.0)
        mins = (grams / dens * 1000.0) / flow / 60.0
        tsrc = f"{flow:g} mm³/s effective"
    pr["grams"] = round(grams, 1)
    pr["time_min"] = round(mins)
    return {"grams": grams, "mins": mins, "how": how, "tsrc": tsrc, "mat": mat}


def printed_cost(part, facts, mats, bed, rate):
    """Dollars for a printed part. The formula string is rendered in the
    inspector so the number can be argued with rather than believed."""
    pf = printed_facts(part, facts, mats, bed)
    if not pf:
        return None
    mat = pf["mat"]
    # No spool price means no filament cost, and no number beats a made-up one.
    if mat.get("price") is None:
        return None
    per_g = mat["price"] / mat["spool_g"]                # $/g
    grams, mins, how, tsrc = pf["grams"], pf["mins"], pf["how"], pf["tsrc"]

    fil = grams * per_g
    machine = mins / 60.0 * rate
    return {
        "each": round(fil + machine, 2),
        "est": True,
        "supplier": mat.get("supplier"),
        "url": mat.get("url"),
        "checked": mat.get("checked"),
        "bulk": {"10": round(fil + machine, 2), "50": round(fil + machine, 2),
                 "100": round(fil + machine, 2)},
        "formula": (f"{how}. Filament {grams:.0f} g × ${per_g:.4f}/g = "
                    f"${fil:.2f}. Machine {mins:.0f} min ({tsrc}) × "
                    f"${rate:.2f}/h = ${machine:.2f}. Total ${fil+machine:.2f}. "
                    f"Printed-part cost does not fall with volume — it is the "
                    f"same at ×1 and ×100, which is exactly why bought parts "
                    f"are where the bulk saving is."),
    }


# ---------------------------------------------------------------------------
def build(cfg_path, out_html=None, out_3mf=None, quiet=False):
    cfg = normalise_sp(json.load(open(cfg_path, encoding="utf-8")))
    base = cfg.get("base_dir") or os.path.dirname(os.path.abspath(cfg_path))
    if not os.path.isabs(base):
        base = os.path.join(os.path.dirname(os.path.abspath(cfg_path)), base)
    log = (lambda *a: None) if quiet else print

    bed = {**DEF_BED, **cfg.get("printer", {})}
    mats = cfg.get("materials", {})
    rate = cfg.get("machine_rate_per_h", 0.0)
    report = {"tbd": [], "oversize": [], "warn": []}

    # ---- geometry ---------------------------------------------------------
    meshes, mats_by_id = [], {}
    for p in cfg["parts"]:
        m = G.load_part_mesh(p, base)
        meshes.append((p["id"], m))
        mats_by_id[p["id"]] = m
    # Wires ride in the same buffer as the parts. One buffer, one binding, and
    # every existing behaviour (pick, ghost, isolate, section) works on a cable
    # run without a line of special-case code.
    wiring, wire_meshes = build_wiring(cfg, log)
    meshes.extend(wire_meshes)
    blob, rec = G.pack(meshes)
    log(f"geometry: {len(cfg['parts'])} parts, "
        f"{sum(r['tris'] for r in rec.values()):,} triangles, "
        f"{len(blob)/1048576:.2f} MB raw")

    # ---- per-part facts, matrices, plate placement ------------------------
    items, src_meshes = [], {}
    for p in cfg["parts"]:
        A = G.transform_matrix(p.get("transform"))
        p["_A"] = A
        p["_srcM"] = G.col_major(np.linalg.inv(A))
        sm = G.source_mesh(p, base)
        src_meshes[p["id"]] = sm
        f = G.mesh_facts(sm)
        f["area_mm2"] = float(sm.area)
        p["_facts"] = f
        if p.get("kind") == "printed":
            rot = (p.get("print", {}) or {}).get("rot", [0, 0, 0])
            om = G.oriented(sm, rot)
            w, d, h = om.extents
            # qty 2 means TWO of them on the bed. Packing one and printing two
            # is how you discover at slice time that the plate was never real.
            for k in range(int(p.get("qty", 1))):
                items.append({"id": f"{p['id']}#{k}", "pid": p["id"],
                              "w": float(w), "d": float(d), "h": float(h)})

    by_item = {i["id"]: i for i in items}
    plates, placed = PK.pack_plates(items, bed["x"], bed["y"],
                                    gap=bed["gap"], margin=bed["margin"])

    # The packer is allowed to turn a part 90 degrees about Z to make it fit.
    # That turn is part of the print orientation, so fold it in before anything
    # downstream (plate matrix, 3MF, footprint readout) uses the mesh.
    for p in cfg["parts"]:
        if p.get("kind") != "printed":
            continue
        base_rot = list((p.get("print", {}) or {}).get("rot", [0, 0, 0]))
        p["_inst"] = []
        for k in range(int(p.get("qty", 1))):
            key = f"{p['id']}#{k}"
            pos = placed[key]
            rot = list(base_rot)
            if pos.get("rot"):
                rot[2] = rot[2] + 90.0
            om = G.oriented(src_meshes[p["id"]], rot)
            w, d, h = om.extents
            by_item[key].update({"w": float(w), "d": float(d), "h": float(h)})
            p["_inst"].append({"key": key, "rot": rot, "om": om, "pos": pos})

    for pl in plates:
        PK.audit_plate(pl, by_item, placed, bed.get("gantry"), bed.get("skirt"),
                       sequential=bool(bed.get("sequential")))

    # ---- meta -------------------------------------------------------------
    out_parts = []
    for p in cfg["parts"]:
        r = rec[p["id"]]
        e = {
            "id": p["id"], "label": p["label"], "color": p["color"],
            "group": p.get("group", "all"), "step": p.get("step", 1),
            "note": p.get("note", ""), "explode": p.get("explode", [0, 0, 0]),
            "off": r["off"], "n": r["n"], "lo": r["lo"], "span": r["span"],
            "tris": r["tris"],
            "kind": p.get("kind", "bought"),
            "qty": p.get("qty", 1),
            "material": p.get("material"),
            "mates": p.get("mates", []),
            "fast": p.get("fast", []),
            "srcM": p["_srcM"],
        }
        if p.get("stl"):
            e["stlPath"] = os.path.abspath(
                p["stl"] if os.path.isabs(p["stl"]) else os.path.join(base, p["stl"]))
        if p.get("kind") == "printed":
            printed_facts(p, p["_facts"], mats, bed)   # fills print.grams/time_min
            inst = []
            for I in p["_inst"]:
                it, pos = by_item[I["key"]], I["pos"]
                # assembly -> plate:  T_place . T_drop . R . A^-1
                #   A^-1   undoes the assembly transform (back to STL space)
                #   R      the print orientation, incl. any 90 deg the packer added
                #   T_drop centres it in XY and sits its lowest facet on z = 0
                #   T_place moves it to its spot on the bed
                R = np.eye(4)
                for ang, ax in zip(I["rot"], ([1, 0, 0], [0, 1, 0], [0, 0, 1])):
                    if ang:
                        R = trimesh.transformations.rotation_matrix(
                            math.radians(ang), ax) @ R
                rot_bb = sm_bounds(src_meshes[p["id"]], R)
                drop = np.eye(4)
                drop[:3, 3] = [-(rot_bb[0][0] + rot_bb[1][0]) / 2,
                               -(rot_bb[0][1] + rot_bb[1][1]) / 2,
                               -rot_bb[0][2]]
                place = np.eye(4)
                place[:3, 3] = [pos["x"], pos["y"], 0.0]
                Mp = place @ drop @ R @ np.linalg.inv(p["_A"])
                inst.append({"m": G.col_major(Mp), "idx": pos["plate"]})
            it0 = by_item[p["_inst"][0]["key"]]
            e["plate"] = {
                "inst": inst,
                "idx": inst[0]["idx"],
                "plates": sorted({i["idx"] for i in inst}),
                "w": round(it0["w"], 2), "d": round(it0["d"], 2),
                "h": round(it0["h"], 2),
                "fits": bool(p["_inst"][0]["pos"]["fits"] and it0["h"] <= bed["z"]),
                "tall": bool(bed.get("sequential") and bed.get("gantry")
                             and it0["h"] > bed["gantry"]),
            }
            if not e["plate"]["fits"]:
                report["oversize"].append(
                    f"{p['label']}: {it0['w']:.0f}×{it0['d']:.0f}×{it0['h']:.0f} mm "
                    f"exceeds {bed['x']:.0f}×{bed['y']:.0f}×{bed['z']:.0f}")
            p["print"] = p.get("print", {})
            e["print"] = {k: v for k, v in p["print"].items() if k != "rot"}

        # cost
        if p.get("cost"):
            e["cost"] = p["cost"]
        elif p.get("kind") == "printed":
            c = printed_cost(p, p["_facts"], mats, bed, rate)
            e["print"] = {k: v for k, v in p.get("print", {}).items() if k != "rot"}
            if c:
                e["cost"] = c
            else:
                report["tbd"].append(p["label"] + " (material not priced)")
        elif p.get("bom") is not False:
            report["tbd"].append(p["label"])
        out_parts.append(e)

    # ---- wire pseudo-parts -------------------------------------------------
    if wiring:
        kindcol = cfg.get("wiring", {}).get("colors", {})
        for r in wiring["runs"]:
            rr = rec[r["part"]]
            out_parts.append({
                "id": r["part"], "label": r.get("label", r["id"]),
                "color": r.get("color") or kindcol.get(r.get("kind"), "#8e9a93"),
                "group": "_wire", "step": r.get("step", 0),
                "note": r.get("note", ""), "explode": [0, 0, 0],
                "off": rr["off"], "n": rr["n"], "lo": rr["lo"],
                "span": rr["span"], "tris": rr["tris"],
                "kind": "wire", "qty": 1, "bom": False,
                "wire": {k: r[k] for k in
                         ("id", "net", "kind", "gauge", "awg", "length_mm",
                          "amps", "ohms", "drop_v", "drop_pct", "chassis_a",
                          "undersized", "from", "to")
                         if k in r},
            })

    centre = cfg.get("centre")
    if centre is None:
        solid = [e for e in out_parts if e.get("kind") != "wire"] or out_parts
        lo = np.min([[e["lo"][i] for i in range(3)] for e in solid], axis=0)
        hi = np.max([[e["lo"][i] + e["span"][i] for i in range(3)] for e in solid], axis=0)
        centre = [round(float(x), 3) for x in (lo + hi) / 2]

    slug = cfg.get("slug", os.path.splitext(os.path.basename(cfg_path))[0])
    meta = {
        "title": cfg["title"], "subtitle": cfg.get("subtitle", ""),
        "slug": slug,
        "groups": cfg.get("groups", {}),
        "steps": _steps(cfg),
        "fasteners": cfg.get("fasteners", []),
        "bomExtra": cfg.get("bom_extra", []),
        "parts": out_parts,
        # the viewer speaks part ids, the packer speaks instance keys
        "plates": [{"idx": pl["idx"],
                    "parts": [k.split("#")[0] for k in pl["parts"]],
                    "warn": pl["warn"], "minGap": pl.get("minGap"),
                    "maxH": pl.get("maxH")} for pl in plates],
        "centre": centre,
        "home": cfg.get("home", {}),
        "explodeScale": cfg.get("explode_scale", 16),
        "bed": {"name": bed["name"], "x": bed["x"], "y": bed["y"], "z": bed["z"],
                "gap": bed["gap"], "nozzle": bed["nozzle"],
                "sequential": bool(bed.get("sequential")),
                "gantry": bed.get("gantry"), "skirt": bed.get("skirt")},
        "wiring": wiring,
        "currency": cfg.get("currency", "$"),
        "priceNote": cfg.get("price_note", ""),
        "built": datetime.date.today().isoformat(),
    }

    # ---- 3MF -------------------------------------------------------------
    mf_report = []
    if out_3mf is None:
        out_3mf = os.path.join(os.path.dirname(os.path.abspath(cfg_path)),
                               slug + "_plates.3mf")
    all_objs = []
    for pl in plates:
        objs = []
        for key in pl["parts"]:
            pid = key.split("#")[0]
            p = next(x for x in cfg["parts"] if x["id"] == pid)
            I = next(i for i in p["_inst"] if i["key"] == key)
            om = I["om"].copy()
            om.apply_translation([I["pos"]["x"], I["pos"]["y"], 0.0])
            objs.append((f"plate{pl['idx']}_{key.replace('#','_')}", om))
        if not objs:
            continue
        per = out_3mf.replace(".3mf", f"_plate{pl['idx']}.3mf")
        sz = X3.write_3mf(per, objs, title=f"{cfg['title']} — plate {pl['idx']}")
        v = X3.verify_3mf(per)
        mf_report.append({"plate": pl["idx"], "file": per, "bytes": sz,
                          "objects": len(v["objects"]), "items": v["items"],
                          "verify": v})
        # the combined file separates plates along +Y so nothing overlaps
        for name, m in objs:
            mm = m.copy()
            mm.apply_translation([0.0, (pl["idx"] - 1) * (bed["y"] + 40.0), 0.0])
            all_objs.append((name, mm))
    if all_objs:
        sz = X3.write_3mf(out_3mf, all_objs, title=cfg["title"])
        vall = X3.verify_3mf(out_3mf)
        mf_report.append({"plate": "all", "file": out_3mf, "bytes": sz,
                          "objects": len(vall["objects"]), "items": vall["items"],
                          "verify": vall})
    meta["plateFile"] = os.path.abspath(out_3mf)

    # Reopen everything we just wrote and check it against the build volume.
    # This runs on every build, not just when someone remembers to check.
    if mf_report:
        mf_ok, mf_lines = X3.audit_plates([m["file"] for m in mf_report],
                                          bed["x"], bed["y"], bed["z"])
        report["mf_ok"] = mf_ok
        if not mf_ok:
            report["warn"].append("3MF audit FAILED")

    # ---- emit HTML --------------------------------------------------------
    tpl = open(TEMPLATE, encoding="utf-8").read()
    html = (tpl
            .replace("__AV_TITLE__", esc_html(cfg["title"]))
            .replace("__AV_SUBTITLE__", esc_html(cfg.get("subtitle", "")))
            .replace("__AV_DESC__", esc_html(cfg.get("description",
                                                     cfg.get("subtitle", ""))))
            .replace("__AV_META__", json.dumps(meta, separators=(",", ":")))
            .replace("__AV_GEO__", base64.b64encode(blob).decode("ascii")))
    if out_html is None:
        out_html = os.path.join(os.path.dirname(os.path.abspath(cfg_path)),
                                slug + "_av.html")
    open(out_html, "w", encoding="utf-8").write(html)

    # Two outputs from one template, because they are read in two places:
    #   *.html           standalone — double-click it, it opens
    #   *_fragment.html  for the artifact publisher, which supplies its own
    #                    <!doctype>/<head>/<body> and would nest a second
    #                    document if handed the standalone.
    # Dark stays the default in the fragment because the dark values live on
    # bare `:root`; the viewer's theme toggle stamps data-theme and the
    # light override picks it up, so both directions still work without the
    # attribute we drop here.
    frag_path = os.path.splitext(out_html)[0] + "_fragment.html"
    open(frag_path, "w", encoding="utf-8").write(as_fragment(html))

    log(f"html:     {out_html}  ({os.path.getsize(out_html)/1048576:.2f} MB)")
    for m in mf_report:
        log(f"3mf:      plate {m['plate']}: {m['objects']} objects, "
            f"{m['bytes']/1024:.0f} kB  {os.path.basename(m['file'])}")
    if mf_report:
        log("3mf audit: " + ("PASS" if report.get("mf_ok") else "FAIL"))
        for l in mf_lines:
            log(l)
    for pl in plates:
        log(f"plate {pl['idx']}: {len(pl['parts'])} objects, tallest "
            f"{pl.get('maxH')} mm"
            + ("  WARN: " + " | ".join(pl["warn"]) if pl["warn"] else ""))
    if report["tbd"]:
        log("TBD (unsourced, shown as TBD in the UI): " + ", ".join(report["tbd"]))
    if report["oversize"]:
        log("OVERSIZE: " + "; ".join(report["oversize"]))
    return {"html": out_html, "meta": meta, "plates": plates,
            "mf": mf_report, "report": report, "blob": len(blob)}


def as_fragment(html):
    """Strip the document wrapper, keep styles + body + scripts."""
    import re
    i = html.index("<style>")
    head = html[:i]
    body = html[i:]
    body = body.replace("</head>", "").replace("<body>", "")
    body = re.sub(r"</body>\s*</html>\s*$", "", body).rstrip()
    # carry the description across as a comment so the source is traceable
    m = re.search(r'<title>(.*?)</title>', head, re.S)
    title = m.group(1) if m else "assembly viewer"
    return f"<!-- {title} · SP assembly-viewer engine v2 -->\n" + body + "\n"


def sm_bounds(mesh, R):
    v = np.asarray(mesh.vertices)
    v = (R[:3, :3] @ v.T).T
    return v.min(axis=0), v.max(axis=0)


def esc_html(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    out = sys.argv[2] if len(sys.argv) > 2 else None
    build(sys.argv[1], out_html=out)
